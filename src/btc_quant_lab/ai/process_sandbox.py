from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path

import polars as pl

from btc_quant_lab.models import PivotConfig, PivotSignal, Trade
from btc_quant_lab.research.backtest import metrics_from_trades, reversal_backtest

FORKS_ROOT = Path("experiments/forks")
DEFAULT_IMAGE = "docker.io/library/python:3.12-slim"
FORK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class DetectorSandboxError(RuntimeError):
    pass


def _fork_directory(fork_id: str) -> Path:
    if not FORK_ID_RE.fullmatch(fork_id):
        raise DetectorSandboxError("invalid fork id")
    root = FORKS_ROOT.resolve()
    directory = (root / fork_id).resolve()
    if root not in directory.parents:
        raise DetectorSandboxError("fork path escapes experiments/forks")
    if not directory.is_dir():
        raise DetectorSandboxError(f"fork does not exist: {fork_id}")
    variant = directory / "detector_variant.py"
    if not variant.is_file():
        raise DetectorSandboxError("fork must contain detector_variant.py")
    return directory


def podman_available() -> bool:
    return shutil.which("podman") is not None


def podman_image_available(image: str = DEFAULT_IMAGE) -> bool:
    executable = shutil.which("podman")
    if executable is None:
        return False
    try:
        completed = subprocess.run(  # noqa: S603 - fixed trusted executable and argv, no shell
            [executable, "image", "exists", image],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return completed.returncode == 0


def sandbox_ready(image: str = DEFAULT_IMAGE) -> bool:
    return podman_available() and podman_image_available(image)


def build_podman_command(
    fork_directory: Path,
    request_path: Path,
    result_path: Path,
    runner_path: Path,
    image: str = DEFAULT_IMAGE,
    memory_mb: int = 512,
    cpus: float = 1.0,
    pids_limit: int = 64,
    podman_executable: str = "podman",
) -> list[str]:
    if memory_mb < 128 or memory_mb > 4096:
        raise ValueError("memory_mb must be between 128 and 4096")
    if cpus <= 0 or cpus > 4:
        raise ValueError("cpus must be > 0 and <= 4")
    if pids_limit < 16 or pids_limit > 512:
        raise ValueError("pids_limit must be between 16 and 512")

    return [
        podman_executable,
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--userns=keep-id",
        f"--memory={memory_mb}m",
        f"--cpus={cpus}",
        f"--pids-limit={pids_limit}",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        f"--volume={fork_directory.resolve()}:/workspace:ro",
        f"--volume={request_path.resolve()}:/input/request.json:ro",
        f"--volume={result_path.resolve()}:/output/result.json:rw",
        f"--volume={runner_path.resolve()}:/runner.py:ro",
        "--workdir=/workspace",
        image,
        "python",
        "/runner.py",
    ]


def _candles_payload(df: pl.DataFrame) -> list[dict]:
    required = ["ts", "open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise DetectorSandboxError(f"market data missing columns: {missing}")
    if len(df) > 100_000:
        raise DetectorSandboxError("sandbox input exceeds 100000 candles")
    return [
        {
            "ts": int(row["ts"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for row in df.select(required).iter_rows(named=True)
    ]


def validate_detector_result(payload: dict) -> list[PivotSignal]:
    raw = payload.get("signals")
    if not isinstance(raw, list):
        raise DetectorSandboxError("sandbox output must contain a signals list")
    if len(raw) > 100_000:
        raise DetectorSandboxError("sandbox returned too many signals")

    signals: list[PivotSignal] = []
    previous_ts = -1
    for item in raw:
        if not isinstance(item, dict):
            raise DetectorSandboxError("every sandbox signal must be a dict")
        try:
            signal = PivotSignal(
                ts=int(item["ts"]),
                direction=int(item["direction"]),
                top=float(item["top"]),
                bottom=float(item["bottom"]),
                candidate_ts=int(item["candidate_ts"]),
                confirm_price=float(item["confirm_price"]),
                bars_to_confirm=int(item["bars_to_confirm"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DetectorSandboxError(f"invalid sandbox signal: {exc}") from exc

        numeric = (signal.top, signal.bottom, signal.confirm_price)
        if not all(math.isfinite(value) for value in numeric):
            raise DetectorSandboxError("signal prices must be finite")
        if signal.direction not in {-1, 1}:
            raise DetectorSandboxError("direction must be -1 or 1")
        if signal.top < signal.bottom:
            raise DetectorSandboxError("signal top cannot be below bottom")
        if signal.candidate_ts > signal.ts:
            raise DetectorSandboxError("candidate_ts cannot be after confirmation ts")
        if signal.bars_to_confirm < 0:
            raise DetectorSandboxError("bars_to_confirm cannot be negative")
        if signal.ts < previous_ts:
            raise DetectorSandboxError("signals must be sorted by ts")
        previous_ts = signal.ts
        signals.append(signal)
    return signals


def validate_signals_against_market(
    df: pl.DataFrame,
    signals: list[PivotSignal],
    price_tolerance: float = 1e-8,
) -> None:
    timestamps = [int(value) for value in df["ts"].to_list()]
    index_by_ts = {timestamp: i for i, timestamp in enumerate(timestamps)}
    close_by_ts = {
        int(timestamp): float(close)
        for timestamp, close in zip(timestamps, df["close"].to_list(), strict=True)
    }

    for signal in signals:
        if signal.ts not in index_by_ts:
            raise DetectorSandboxError("signal confirmation timestamp is not a market candle")
        if signal.candidate_ts not in index_by_ts:
            raise DetectorSandboxError("signal candidate timestamp is not a market candle")
        candidate_index = index_by_ts[signal.candidate_ts]
        confirmation_index = index_by_ts[signal.ts]
        expected_bars = confirmation_index - candidate_index
        if expected_bars != signal.bars_to_confirm:
            raise DetectorSandboxError("bars_to_confirm does not match market timestamps")

        close_price = close_by_ts[signal.ts]
        tolerance = max(price_tolerance, abs(close_price) * price_tolerance)
        if abs(signal.confirm_price - close_price) > tolerance:
            raise DetectorSandboxError(
                "confirm_price must equal the close of the confirmation candle"
            )


def _signal_signature(signal: PivotSignal) -> tuple:
    return (
        signal.ts,
        signal.direction,
        round(signal.top, 10),
        round(signal.bottom, 10),
        signal.candidate_ts,
        round(signal.confirm_price, 10),
        signal.bars_to_confirm,
    )


def assert_prefix_causal(
    earlier_signals: list[PivotSignal],
    later_signals: list[PivotSignal],
    earlier_end_ts: int,
) -> None:
    earlier = [_signal_signature(signal) for signal in earlier_signals]
    later_prefix = [
        _signal_signature(signal)
        for signal in later_signals
        if signal.ts <= earlier_end_ts
    ]
    if earlier != later_prefix:
        raise DetectorSandboxError(
            "causality audit failed: past signals changed after future candles were added"
        )


def run_detector_fork(
    df: pl.DataFrame,
    fork_id: str,
    config: PivotConfig | dict | None = None,
    image: str = DEFAULT_IMAGE,
    timeout_seconds: int = 30,
    memory_mb: int = 512,
    cpus: float = 1.0,
) -> list[PivotSignal]:
    """Run a full detector fork inside a networkless rootless Podman container.

    The trusted container image must already exist locally. The function uses
    `--pull=never`, so executing an AI fork never triggers a network image pull.
    """
    executable = shutil.which("podman")
    if executable is None:
        raise DetectorSandboxError("podman is required for full detector sandbox execution")
    if not podman_image_available(image):
        raise DetectorSandboxError(
            f"sandbox image is not available locally: {image}; run the explicit setup first"
        )
    if timeout_seconds < 1 or timeout_seconds > 300:
        raise ValueError("timeout_seconds must be between 1 and 300")

    fork_directory = _fork_directory(fork_id)
    runner_path = Path(__file__).with_name("detector_runner.py").resolve()
    cfg = asdict(config) if isinstance(config, PivotConfig) else (config or {})
    request = {"candles": _candles_payload(df), "config": cfg}

    with tempfile.TemporaryDirectory(prefix="bqrl-detector-") as tmp:
        tmp_path = Path(tmp)
        request_path = tmp_path / "request.json"
        result_path = tmp_path / "result.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        result_path.write_text("{}", encoding="utf-8")

        command = build_podman_command(
            fork_directory,
            request_path,
            result_path,
            runner_path,
            image=image,
            memory_mb=memory_mb,
            cpus=cpus,
            podman_executable=executable,
        )
        try:
            completed = subprocess.run(  # noqa: S603 - argv only; isolated rootless container is the boundary
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise DetectorSandboxError("detector sandbox timed out") from exc

        if completed.returncode != 0:
            stderr = completed.stderr[-4000:]
            raise DetectorSandboxError(
                f"detector sandbox failed with code {completed.returncode}: {stderr}"
            )
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DetectorSandboxError("detector sandbox returned invalid JSON") from exc
        signals = validate_detector_result(payload)
        validate_signals_against_market(df, signals)
        return signals


def audit_detector_causality(
    df: pl.DataFrame,
    fork_id: str,
    config: PivotConfig | dict | None = None,
    checkpoints: int = 4,
    min_prefix_bars: int = 200,
    **sandbox_kwargs,
) -> dict:
    """Run prefix-invariance checks to detect historical lookahead in a detector fork."""
    if checkpoints < 2 or checkpoints > 10:
        raise ValueError("checkpoints must be between 2 and 10")
    if len(df) < min_prefix_bars + checkpoints:
        raise DetectorSandboxError("not enough candles for detector causality audit")

    remaining = len(df) - min_prefix_bars
    sizes = sorted(
        {
            min_prefix_bars + round(remaining * i / checkpoints)
            for i in range(checkpoints + 1)
        }
    )
    previous_signals: list[PivotSignal] | None = None
    previous_end_ts: int | None = None
    runs: list[dict] = []

    for size in sizes:
        prefix = df.slice(0, size)
        signals = run_detector_fork(
            prefix,
            fork_id,
            config=config,
            **sandbox_kwargs,
        )
        if previous_signals is not None and previous_end_ts is not None:
            assert_prefix_causal(previous_signals, signals, previous_end_ts)
        previous_signals = signals
        previous_end_ts = int(prefix["ts"][-1])
        runs.append({"bars": size, "signals": len(signals), "end_ts": previous_end_ts})

    return {
        "passed": True,
        "method": "prefix_invariance",
        "checkpoints": len(runs),
        "runs": runs,
    }


def _trades_in_window(
    trades: list[Trade],
    start_ts: int,
    end_ts: int,
) -> list[Trade]:
    return [
        trade
        for trade in trades
        if int(trade.entry_ts) >= start_ts and int(trade.exit_ts) <= end_ts
    ]


def evaluate_detector_fork_oos(
    df: pl.DataFrame,
    fork_id: str,
    config: PivotConfig | dict | None = None,
    warmup_bars: int = 1095,
    test_bars: int = 365,
    step_bars: int | None = None,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
    **sandbox_kwargs,
) -> dict:
    """Evaluate a mutated detector on chronological prefixes and OOS windows.

    Each test window executes the fork only with candles available up to that window's end.
    Consecutive prefix outputs are compared, so changing past signals is rejected as lookahead.
    """
    step_bars = step_bars or test_bars
    if warmup_bars < 100 or test_bars < 30 or step_bars < 1:
        raise ValueError("evaluation windows are too small")
    if len(df) < warmup_bars + test_bars:
        return {
            "windows": [],
            "aggregate": metrics_from_trades([]),
            "error": "not_enough_history",
        }

    timestamps = [int(value) for value in df["ts"].to_list()]
    windows: list[dict] = []
    all_trades: list[Trade] = []
    test_start = warmup_bars
    previous_signals: list[PivotSignal] | None = None
    previous_end_ts: int | None = None

    while test_start + test_bars <= len(df):
        test_end = test_start + test_bars
        prefix = df.slice(0, test_end)
        signals = run_detector_fork(
            prefix,
            fork_id,
            config=config,
            **sandbox_kwargs,
        )
        if previous_signals is not None and previous_end_ts is not None:
            assert_prefix_causal(previous_signals, signals, previous_end_ts)

        trades, _ = reversal_backtest(
            signals,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )
        start_ts = timestamps[test_start]
        end_ts = timestamps[test_end - 1]
        oos_trades = _trades_in_window(trades, start_ts, end_ts)
        all_trades.extend(oos_trades)
        windows.append(
            {
                "test": {"start_ts": start_ts, "end_ts": end_ts, "bars": test_bars},
                "metrics": metrics_from_trades(oos_trades),
            }
        )
        previous_signals = signals
        previous_end_ts = end_ts
        test_start += step_bars

    aggregate = metrics_from_trades(all_trades)
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
            "type": "detector_fork_prefix_oos",
            "warmup_bars": warmup_bars,
            "test_bars": test_bars,
            "step_bars": step_bars,
            "prefix_causality_enforced": True,
        },
        "windows": windows,
        "aggregate": aggregate,
    }


def evaluate_detector_fork(
    df: pl.DataFrame,
    fork_id: str,
    config: PivotConfig | dict | None = None,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
    **sandbox_kwargs,
) -> dict:
    signals = run_detector_fork(
        df,
        fork_id,
        config=config,
        **sandbox_kwargs,
    )
    trades, metrics = reversal_backtest(
        signals,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    return {
        "fork_id": fork_id,
        "signals": len(signals),
        "trades": len(trades),
        "metrics": metrics,
    }
