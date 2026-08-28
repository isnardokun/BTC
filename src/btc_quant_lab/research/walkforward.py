from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone

import polars as pl

from btc_quant_lab.models import PivotConfig, Trade
from btc_quant_lab.research.backtest import metrics_from_trades, reversal_backtest
from btc_quant_lab.research.filters import filter_signals
from btc_quant_lab.research.optimizer import optimize
from btc_quant_lab.research.pivots import detect_pivots


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).date().isoformat()


def _config_from_row(row: dict) -> PivotConfig:
    return PivotConfig(**row["config"])


def _config_key(cfg: PivotConfig) -> str:
    return f"{cfg.motor}/{cfg.range_mode}/min{cfg.min_bars}/pend{cfg.max_pending}"


def _trades_inside_window(
    df: pl.DataFrame,
    cfg: PivotConfig,
    test_start: int,
    test_end: int,
    signal_filter: dict | None = None,
) -> list[Trade]:
    timestamps = df["ts"].to_list()
    history_to_test_end = df.slice(0, test_end)
    signals = detect_pivots(history_to_test_end, cfg)
    signals = filter_signals(history_to_test_end, signals, signal_filter)
    trades, _ = reversal_backtest(signals)
    test_start_ts = int(timestamps[test_start])
    test_end_ts = int(timestamps[test_end - 1])
    return [
        trade
        for trade in trades
        if trade.entry_ts >= test_start_ts and trade.exit_ts <= test_end_ts
    ]


def evaluate_fixed_config(
    df: pl.DataFrame,
    cfg: PivotConfig,
    warmup_bars: int = 1095,
    test_bars: int = 365,
    step_bars: int | None = None,
    signal_filter: dict | None = None,
) -> dict:
    """Evaluate one frozen configuration on chronological windows after a warmup period."""
    step_bars = step_bars or test_bars
    if warmup_bars < 100 or test_bars < 30 or step_bars < 1:
        raise ValueError("evaluation windows are too small")
    if len(df) < warmup_bars + test_bars:
        return {
            "config": asdict(cfg),
            "filter": signal_filter,
            "windows": [],
            "aggregate": metrics_from_trades([]),
            "error": "not_enough_history",
        }

    timestamps = df["ts"].to_list()
    windows: list[dict] = []
    all_trades: list[Trade] = []
    test_start = warmup_bars

    while test_start + test_bars <= len(df):
        test_end = test_start + test_bars
        oos_trades = _trades_inside_window(
            df,
            cfg,
            test_start,
            test_end,
            signal_filter=signal_filter,
        )
        metrics = metrics_from_trades(oos_trades)
        all_trades.extend(oos_trades)
        windows.append(
            {
                "test": {
                    "start": _iso(int(timestamps[test_start])),
                    "end": _iso(int(timestamps[test_end - 1])),
                    "bars": test_bars,
                },
                "metrics": metrics,
            }
        )
        test_start += step_bars

    aggregate = metrics_from_trades(all_trades)
    profitable_windows = sum(1 for w in windows if w["metrics"]["net_return_pct"] > 0)
    aggregate["windows"] = len(windows)
    aggregate["profitable_windows"] = profitable_windows
    aggregate["profitable_windows_pct"] = (
        profitable_windows * 100.0 / len(windows) if windows else None
    )

    return {
        "config": asdict(cfg),
        "filter": signal_filter,
        "method": {
            "warmup_bars": warmup_bars,
            "test_bars": test_bars,
            "step_bars": step_bars,
        },
        "windows": windows,
        "aggregate": aggregate,
    }


def walk_forward(
    df: pl.DataFrame,
    train_bars: int = 1095,
    test_bars: int = 365,
    step_bars: int | None = None,
    min_train_trades: int = 10,
) -> dict:
    """Select parameters on train windows and evaluate only on subsequent unseen data.

    Defaults are designed for daily BTC: 3 years train, 1 year test, 1 year step.
    Test windows do not overlap unless the caller explicitly chooses a smaller step.
    """
    step_bars = step_bars or test_bars
    if train_bars < 100 or test_bars < 30 or step_bars < 1:
        raise ValueError("walk-forward windows are too small")
    if len(df) < train_bars + test_bars:
        return {
            "windows": [],
            "aggregate": metrics_from_trades([]),
            "selection_frequency": {},
            "error": "not_enough_history",
        }

    timestamps = df["ts"].to_list()
    windows: list[dict] = []
    all_oos_trades: list[Trade] = []
    selected: Counter[str] = Counter()

    train_start = 0
    while train_start + train_bars + test_bars <= len(df):
        train_end = train_start + train_bars
        test_start = train_end
        test_end = test_start + test_bars

        train_df = df.slice(train_start, train_bars)
        ranked = optimize(train_df, min_trades=min_train_trades)
        if not ranked:
            break

        best = ranked[0]
        cfg = _config_from_row(best)
        selected[_config_key(cfg)] += 1
        oos_trades = _trades_inside_window(df, cfg, test_start, test_end)
        oos_metrics = metrics_from_trades(oos_trades)
        all_oos_trades.extend(oos_trades)

        test_start_ts = int(timestamps[test_start])
        test_end_ts = int(timestamps[test_end - 1])
        windows.append(
            {
                "train": {
                    "start": _iso(int(timestamps[train_start])),
                    "end": _iso(int(timestamps[train_end - 1])),
                    "bars": train_bars,
                },
                "test": {
                    "start": _iso(test_start_ts),
                    "end": _iso(test_end_ts),
                    "bars": test_bars,
                },
                "selected_config": asdict(cfg),
                "in_sample": {
                    key: best.get(key)
                    for key in (
                        "trades",
                        "win_rate",
                        "net_return_pct",
                        "expectancy_pct",
                        "profit_factor",
                        "max_drawdown_pct",
                        "score",
                    )
                },
                "out_of_sample": oos_metrics,
            }
        )

        train_start += step_bars

    aggregate = metrics_from_trades(all_oos_trades)
    profitable_windows = sum(1 for w in windows if w["out_of_sample"]["net_return_pct"] > 0)
    aggregate["windows"] = len(windows)
    aggregate["profitable_windows"] = profitable_windows
    aggregate["profitable_windows_pct"] = (
        profitable_windows * 100.0 / len(windows) if windows else None
    )

    return {
        "method": {
            "train_bars": train_bars,
            "test_bars": test_bars,
            "step_bars": step_bars,
            "min_train_trades": min_train_trades,
        },
        "windows": windows,
        "aggregate": aggregate,
        "selection_frequency": dict(selected.most_common()),
    }
