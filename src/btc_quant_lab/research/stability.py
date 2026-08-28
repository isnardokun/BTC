from __future__ import annotations

from statistics import median

import polars as pl

from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.walkforward import evaluate_fixed_config


def temporal_stability(
    df: pl.DataFrame,
    cfg: PivotConfig,
    warmup_bars: int = 730,
    window_bars: int = 365,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> dict:
    """Measure a frozen configuration across non-overlapping chronological windows."""
    result = evaluate_fixed_config(
        df,
        cfg,
        warmup_bars=warmup_bars,
        test_bars=window_bars,
        step_bars=window_bars,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    windows = result.get("windows", [])
    if not windows:
        return {
            "config": result.get("config"),
            "method": result.get("method"),
            "windows": [],
            "summary": {"error": result.get("error", "no_windows")},
        }

    expectancies = [
        float(window["metrics"]["expectancy_pct"])
        for window in windows
        if window["metrics"].get("expectancy_pct") is not None
    ]
    compounded = [float(window["metrics"]["compounded_return_pct"]) for window in windows]
    profit_factors = [
        float(window["metrics"]["profit_factor"])
        for window in windows
        if window["metrics"].get("profit_factor") is not None
    ]

    recent = windows[-1]["metrics"]
    prior_windows = windows[:-1]
    prior_expectancies = [
        float(window["metrics"]["expectancy_pct"])
        for window in prior_windows
        if window["metrics"].get("expectancy_pct") is not None
    ]
    prior_median_expectancy = median(prior_expectancies) if prior_expectancies else None
    recent_expectancy = recent.get("expectancy_pct")
    expectancy_decay = (
        float(recent_expectancy) - float(prior_median_expectancy)
        if recent_expectancy is not None and prior_median_expectancy is not None
        else None
    )

    positive_windows = sum(1 for value in compounded if value > 0)
    quality_windows = sum(
        1
        for window in windows
        if (window["metrics"].get("expectancy_pct") or 0.0) > 0
        and (window["metrics"].get("profit_factor") or 0.0) > 1.0
    )

    if expectancy_decay is None:
        decay_state = "unknown"
    elif expectancy_decay < -1.0:
        decay_state = "material_decay"
    elif expectancy_decay < -0.25:
        decay_state = "mild_decay"
    else:
        decay_state = "stable"

    return {
        "config": result.get("config"),
        "method": result.get("method"),
        "windows": windows,
        "summary": {
            "window_count": len(windows),
            "positive_windows_pct": positive_windows * 100.0 / len(windows),
            "quality_windows_pct": quality_windows * 100.0 / len(windows),
            "median_expectancy_pct": median(expectancies) if expectancies else None,
            "median_compounded_return_pct": median(compounded) if compounded else None,
            "median_profit_factor": median(profit_factors) if profit_factors else None,
            "recent_expectancy_pct": recent_expectancy,
            "prior_median_expectancy_pct": prior_median_expectancy,
            "expectancy_decay_pct_points": expectancy_decay,
            "decay_state": decay_state,
        },
    }
