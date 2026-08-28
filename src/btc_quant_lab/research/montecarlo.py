from __future__ import annotations

import numpy as np

from btc_quant_lab.models import Trade


def _path_metrics(returns_pct: np.ndarray) -> tuple[float, float]:
    growth = 1.0 + returns_pct / 100.0
    equity = np.cumprod(growth)
    equity_with_start = np.concatenate(([1.0], equity))
    peak = np.maximum.accumulate(equity_with_start)
    dd = (peak - equity_with_start) / peak * 100.0
    compounded = (equity[-1] - 1.0) * 100.0 if len(equity) else 0.0
    return float(compounded), float(dd.max()) if len(dd) else 0.0


def bootstrap_trade_paths(
    trades: list[Trade],
    simulations: int = 2000,
    seed: int = 42,
) -> dict:
    if simulations < 100 or simulations > 100_000:
        raise ValueError("simulations must be between 100 and 100000")
    if not trades:
        return {"simulations": simulations, "trades": 0, "error": "no_trades"}

    returns = np.array([float(t.return_pct) for t in trades], dtype=float)
    rng = np.random.default_rng(seed)
    ending_returns = np.empty(simulations, dtype=float)
    max_dds = np.empty(simulations, dtype=float)

    for i in range(simulations):
        sampled = rng.choice(returns, size=len(returns), replace=True)
        ending_returns[i], max_dds[i] = _path_metrics(sampled)

    q = [5, 25, 50, 75, 95]
    return {
        "simulations": simulations,
        "trades": len(trades),
        "seed": seed,
        "ending_return_pct": {
            f"p{x}": float(np.percentile(ending_returns, x)) for x in q
        },
        "max_drawdown_pct": {
            f"p{x}": float(np.percentile(max_dds, x)) for x in q
        },
        "probability_profitable_pct": float((ending_returns > 0).mean() * 100.0),
        "probability_drawdown_gt_30_pct": float((max_dds > 30.0).mean() * 100.0),
        "probability_drawdown_gt_50_pct": float((max_dds > 50.0).mean() * 100.0),
    }
