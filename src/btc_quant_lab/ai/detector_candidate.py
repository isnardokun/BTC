from __future__ import annotations

import polars as pl

from btc_quant_lab.ai.process_sandbox import (
    DetectorSandboxError,
    assert_prefix_causal,
    audit_detector_causality,
    evaluate_detector_fork_oos,
    run_detector_fork,
    sandbox_ready,
)
from btc_quant_lab.ai.sandbox_image import (
    configured_detector_image,
    detector_image_metadata,
    runtime_default_matches_pinned,
)
from btc_quant_lab.models import PivotConfig, PivotSignal, Trade
from btc_quant_lab.research.backtest import metrics_from_trades, reversal_backtest


def full_detector_sandbox_ready() -> bool:
    """Return whether every detector call will resolve to the same pinned image."""
    image = configured_detector_image()
    return sandbox_ready(image) and runtime_default_matches_pinned()


def full_detector_sandbox_metadata() -> dict:
    metadata = detector_image_metadata()
    metadata["ready"] = sandbox_ready(metadata["configured_image"]) and metadata[
        "default_runtime_matches_pinned"
    ]
    return metadata


def _trades_inside(trades: list[Trade], start_ts: int, end_ts: int) -> list[Trade]:
    return [
        trade
        for trade in trades
        if int(trade.entry_ts) >= start_ts and int(trade.exit_ts) <= end_ts
    ]


def evaluate_detector_boundary_gap_oos(
    df: pl.DataFrame,
    fork_id: str,
    cfg: PivotConfig,
    warmup_bars: int,
    test_bars: int,
    purge_bars: int,
    embargo_bars: int,
    fee_bps: float,
    slippage_bps: float,
    step_bars: int | None = None,
    image: str | None = None,
) -> dict:
    """Evaluate a fixed detector with an excluded zone around each OOS boundary."""
    step_bars = step_bars or test_bars
    image = image or configured_detector_image()
    if warmup_bars < 100 or test_bars < 30 or step_bars < 1:
        raise ValueError("evaluation windows are too small")
    if purge_bars < 0 or embargo_bars < 0:
        raise ValueError("purge and embargo must be non-negative")
    if len(df) < warmup_bars + embargo_bars + test_bars:
        return {
            "windows": [],
            "aggregate": metrics_from_trades([]),
            "error": "not_enough_history",
        }

    timestamps = [int(value) for value in df["ts"].to_list()]
    windows: list[dict] = []
    all_trades: list[Trade] = []
    anchor = warmup_bars
    previous_signals: list[PivotSignal] | None = None
    previous_end_ts: int | None = None

    while anchor + embargo_bars + test_bars <= len(df):
        pre_boundary_end = max(0, anchor - purge_bars)
        test_start = anchor + embargo_bars
        test_end = test_start + test_bars
        prefix = df.slice(0, test_end)
        signals = run_detector_fork(prefix, fork_id, config=cfg, image=image)
        if previous_signals is not None and previous_end_ts is not None:
            assert_prefix_causal(previous_signals, signals, previous_end_ts)

        trades, _ = reversal_backtest(
            signals,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )
        start_ts = timestamps[test_start]
        end_ts = timestamps[test_end - 1]
        oos_trades = _trades_inside(trades, start_ts, end_ts)
        all_trades.extend(oos_trades)
        windows.append(
            {
                "boundary": {
                    "pre_boundary_end_index": pre_boundary_end,
                    "anchor_index": anchor,
                    "test_start_index": test_start,
                    "purge_bars": purge_bars,
                    "embargo_bars": embargo_bars,
                },
                "test": {"start_ts": start_ts, "end_ts": end_ts, "bars": test_bars},
                "metrics": metrics_from_trades(oos_trades),
            }
        )
        previous_signals = signals
        previous_end_ts = end_ts
        anchor += step_bars

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
            "type": "detector_fork_boundary_gap_oos",
            "warmup_bars": warmup_bars,
            "test_bars": test_bars,
            "step_bars": step_bars,
            "purge_bars": purge_bars,
            "embargo_bars": embargo_bars,
            "prefix_causality_enforced": True,
            "sandbox_image": image,
        },
        "windows": windows,
        "aggregate": aggregate,
    }


def collect_detector_candidate_evidence(
    df: pl.DataFrame,
    fork_id: str,
    cfg: PivotConfig,
    warmup_bars: int,
    test_bars: int,
    purge_bars: int,
    embargo_bars: int,
    fee_bps: float,
    slippage_bps: float,
) -> tuple[list[PivotSignal], list[Trade], dict, dict, dict, dict]:
    """Execute and audit a full-detector fork before quantitative promotion review."""
    image = configured_detector_image()
    if not full_detector_sandbox_ready():
        raise DetectorSandboxError(
            "full detector sandbox is not reproducible; rerun scripts/setup_detector_sandbox_arch.sh"
        )

    min_prefix_bars = min(
        max(200, warmup_bars // 2),
        max(100, len(df) - 4),
    )
    causality = audit_detector_causality(
        df,
        fork_id,
        config=cfg,
        checkpoints=3,
        min_prefix_bars=min_prefix_bars,
        image=image,
    )
    causality["sandbox_image"] = detector_image_metadata()
    signals = run_detector_fork(df, fork_id, config=cfg, image=image)
    trades, full_metrics = reversal_backtest(
        signals,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    oos = evaluate_detector_fork_oos(
        df,
        fork_id,
        config=cfg,
        warmup_bars=warmup_bars,
        test_bars=test_bars,
        step_bars=test_bars,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        image=image,
    )
    oos.setdefault("method", {})["sandbox_image"] = image
    boundary_gap_oos = evaluate_detector_boundary_gap_oos(
        df,
        fork_id,
        cfg,
        warmup_bars=warmup_bars,
        test_bars=test_bars,
        purge_bars=purge_bars,
        embargo_bars=embargo_bars,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        step_bars=test_bars,
        image=image,
    )
    return signals, trades, full_metrics, oos, boundary_gap_oos, causality
