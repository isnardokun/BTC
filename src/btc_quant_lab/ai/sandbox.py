from __future__ import annotations

import ast
from dataclasses import asdict
from datetime import UTC, datetime

import polars as pl

from btc_quant_lab.models import PivotConfig, PivotSignal, Trade
from btc_quant_lab.research.backtest import metrics_from_trades, reversal_backtest
from btc_quant_lab.research.features import build_feature_rows
from btc_quant_lab.research.pivots import detect_pivots


class SandboxPolicyError(ValueError):
    pass


_ALLOWED_NODES = {
    ast.Module,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.If,
    ast.IfExp,
    ast.Assign,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.Subscript,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.USub,
    ast.UAdd,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.List,
    ast.Tuple,
    ast.Dict,
}


def validate_sandbox_source(source: str) -> None:
    if len(source) > 12_000:
        raise SandboxPolicyError("sandbox source exceeds 12000 characters")
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise SandboxPolicyError(f"invalid Python syntax: {exc}") from exc

    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "accept_signal":
        raise SandboxPolicyError(
            "source must define exactly one function: accept_signal(signal, features)"
        )
    fn = functions[0]
    if len(fn.args.args) != 2 or [arg.arg for arg in fn.args.args] != [
        "signal",
        "features",
    ]:
        raise SandboxPolicyError(
            "accept_signal must have exactly (signal, features) arguments"
        )
    if fn.decorator_list:
        raise SandboxPolicyError("decorators are not allowed")

    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_NODES:
            raise SandboxPolicyError(f"AST node not allowed: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise SandboxPolicyError("dunder names are not allowed")
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str) and len(node.value) > 128:
                raise SandboxPolicyError(
                    "string constants longer than 128 chars are not allowed"
                )
            if (
                isinstance(node.value, (int, float))
                and not isinstance(node.value, bool)
                and abs(float(node.value)) > 1_000_000
            ):
                raise SandboxPolicyError("numeric constants above 1e6 are not allowed")


def compile_signal_policy(source: str):
    validate_sandbox_source(source)
    namespace: dict = {"__builtins__": {}}
    code = compile(source, "<ai-sandbox>", "exec")
    exec(code, namespace, namespace)  # noqa: S102 -- validated restricted AST, no builtins.
    fn = namespace.get("accept_signal")
    if not callable(fn):
        raise SandboxPolicyError("accept_signal was not created")
    return fn


def apply_signal_policy(
    df: pl.DataFrame,
    signals: list[PivotSignal],
    source: str,
) -> list[PivotSignal]:
    if not signals:
        return []
    policy = compile_signal_policy(source)
    rows = build_feature_rows(df, signals)
    feature_by_ts = {int(row["ts"]): dict(row) for row in rows}
    kept: list[PivotSignal] = []

    for signal in signals:
        features = feature_by_ts.get(int(signal.ts))
        if features is None:
            continue
        features.pop("trade_return_pct", None)
        signal_dict = asdict(signal)
        try:
            decision = policy(signal_dict, features)
        except Exception as exc:
            raise SandboxPolicyError(
                f"policy failed on signal {signal.ts}: {exc}"
            ) from exc
        if not isinstance(decision, bool):
            raise SandboxPolicyError("accept_signal must return bool")
        if decision:
            kept.append(signal)
    return kept


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC).date().isoformat()


def evaluate_sandbox_policy(
    df: pl.DataFrame,
    cfg: PivotConfig,
    source: str,
    warmup_bars: int,
    test_bars: int,
    step_bars: int | None = None,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> dict:
    """Evaluate a restricted code policy in chronological unseen windows."""
    validate_sandbox_source(source)
    step_bars = step_bars or test_bars
    if warmup_bars < 100 or test_bars < 30:
        raise ValueError("sandbox evaluation windows are too small")
    if len(df) < warmup_bars + test_bars:
        return {
            "windows": [],
            "aggregate": metrics_from_trades([]),
            "error": "not_enough_history",
        }

    timestamps = df["ts"].to_list()
    windows: list[dict] = []
    all_oos_trades: list[Trade] = []
    test_start = warmup_bars

    while test_start + test_bars <= len(df):
        test_end = test_start + test_bars
        history = df.slice(0, test_end)
        signals = detect_pivots(history, cfg)
        signals = apply_signal_policy(history, signals, source)
        trades, _ = reversal_backtest(
            signals,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )
        start_ts = int(timestamps[test_start])
        end_ts = int(timestamps[test_end - 1])
        oos = [
            trade
            for trade in trades
            if int(trade.entry_ts) >= start_ts and int(trade.exit_ts) <= end_ts
        ]
        metrics = metrics_from_trades(oos)
        all_oos_trades.extend(oos)
        windows.append(
            {
                "test": {
                    "start": _iso(start_ts),
                    "end": _iso(end_ts),
                    "bars": test_bars,
                },
                "metrics": metrics,
            }
        )
        test_start += step_bars

    aggregate = metrics_from_trades(all_oos_trades)
    profitable = sum(
        1 for window in windows if window["metrics"]["compounded_return_pct"] > 0
    )
    aggregate["windows"] = len(windows)
    aggregate["profitable_windows"] = profitable
    aggregate["profitable_windows_pct"] = (
        profitable * 100.0 / len(windows) if windows else None
    )
    return {
        "method": {
            "warmup_bars": warmup_bars,
            "test_bars": test_bars,
            "step_bars": step_bars,
            "fee_bps": fee_bps,
            "slippage_bps": slippage_bps,
            "sandbox": "restricted_ast_signal_policy",
        },
        "windows": windows,
        "aggregate": aggregate,
    }
