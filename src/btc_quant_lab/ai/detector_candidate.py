from __future__ import annotations

import polars as pl

from btc_quant_lab.ai.process_sandbox import (
    DetectorSandboxError,
    audit_detector_causality,
    evaluate_detector_fork_oos,
    run_detector_fork,
    sandbox_ready,
)
from btc_quant_lab.models import PivotConfig, PivotSignal, Trade
from btc_quant_lab.research.backtest import reversal_backtest


def full_detector_sandbox_ready() -> bool:
    """Return whether the explicitly prepared local Podman sandbox can execute forks."""
    return sandbox_ready()


def collect_detector_candidate_evidence(
    df: pl.DataFrame,
    fork_id: str,
    cfg: PivotConfig,
    warmup_bars: int,
    test_bars: int,
    fee_bps: float,
    slippage_bps: float,
) -> tuple[list[PivotSignal], list[Trade], dict, dict, dict]:
    """Execute and audit a full-detector fork before quantitative promotion review.

    Returns `(signals, trades, full_metrics, oos, causality_audit)`. The fork is
    rejected before scoring if the process sandbox is unavailable, market output is
    invalid, or historical signals change when future candles are appended.
    """
    if not full_detector_sandbox_ready():
        raise DetectorSandboxError(
            "full detector sandbox is not ready; run scripts/setup_detector_sandbox_arch.sh"
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
    )
    signals = run_detector_fork(df, fork_id, config=cfg)
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
    )
    return signals, trades, full_metrics, oos, causality
