from __future__ import annotations

from statistics import median

import polars as pl

from btc_quant_lab.research.optimizer import optimize

MOTORS = ["M1", "M3"]
RANGES = ["R4", "R7", "R8"]
MIN_BARS = [2, 3, 4, 5]
MAX_PENDING = [0, 3, 5, 8]


def _index(values: list, value) -> int:
    return values.index(value)


def _distance(a: dict, b: dict) -> int:
    """Manhattan-like distance in the discrete parameter grid."""
    return (
        abs(_index(MOTORS, a["motor"]) - _index(MOTORS, b["motor"]))
        + abs(_index(RANGES, a["range_mode"]) - _index(RANGES, b["range_mode"]))
        + abs(_index(MIN_BARS, a["min_bars"]) - _index(MIN_BARS, b["min_bars"]))
        + abs(_index(MAX_PENDING, a["max_pending"]) - _index(MAX_PENDING, b["max_pending"]))
    )


def parameter_sensitivity(
    df: pl.DataFrame,
    min_trades: int = 20,
    neighborhood_radius: int = 1,
    plateau_ratio: float = 0.80,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> dict:
    rows = optimize(
        df,
        min_trades=min_trades,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    finite = [r for r in rows if r["score"] != float("-inf")]
    if not finite:
        return {"best": None, "neighbors": [], "plateau": None}

    best = finite[0]
    best_score = float(best["score"])
    neighbors = [
        row
        for row in finite
        if _distance(best["config"], row["config"]) <= neighborhood_radius
    ]

    scores = [float(r["score"]) for r in neighbors]
    expectancies = [
        float(r["expectancy_pct"])
        for r in neighbors
        if r.get("expectancy_pct") is not None
    ]
    pfs = [
        float(r["profit_factor"])
        for r in neighbors
        if r.get("profit_factor") is not None
    ]

    if best_score > 0:
        threshold = best_score * plateau_ratio
        near_best = [r for r in neighbors if float(r["score"]) >= threshold]
    else:
        near_best = []

    positive_quality = [
        r
        for r in neighbors
        if (r.get("expectancy_pct") or 0.0) > 0
        and (r.get("profit_factor") or 0.0) > 1.0
    ]

    return {
        "best": best,
        "neighbors": neighbors,
        "cost_model": {"fee_bps": fee_bps, "slippage_bps": slippage_bps},
        "plateau": {
            "radius": neighborhood_radius,
            "neighbor_count": len(neighbors),
            "near_best_count": len(near_best),
            "near_best_pct": len(near_best) * 100.0 / len(neighbors) if neighbors else None,
            "positive_quality_count": len(positive_quality),
            "positive_quality_pct": (
                len(positive_quality) * 100.0 / len(neighbors) if neighbors else None
            ),
            "median_score": median(scores) if scores else None,
            "median_expectancy_pct": median(expectancies) if expectancies else None,
            "median_profit_factor": median(pfs) if pfs else None,
            "interpretation": (
                "broad"
                if neighbors and len(near_best) / len(neighbors) >= 0.60
                else "moderate"
                if neighbors and len(near_best) / len(neighbors) >= 0.35
                else "fragile"
            ),
        },
    }
