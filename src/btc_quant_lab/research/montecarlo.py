from __future__ import annotations

import numpy as np

from btc_quant_lab.models import Trade


def _path_metrics(returns_pct: np.ndarray) -> tuple[float, float]:
    growth = 1.0 + returns_pct / 100.0
    equity = np.cumprod(growth)
    equity_with_start = np.concatenate(([1.0], equity))
    peak = np.maximum.accumulate(equity_with_start)
    drawdown = (peak - equity_with_start) / peak * 100.0
    compounded = (equity[-1] - 1.0) * 100.0 if len(equity) else 0.0
    return float(compounded), float(drawdown.max()) if len(drawdown) else 0.0


def _summarize_paths(
    ending_returns: np.ndarray,
    max_drawdowns: np.ndarray,
    simulations: int,
    trades: int,
    seed: int,
    method: str,
    block_size: int | None = None,
) -> dict:
    quantiles = [5, 25, 50, 75, 95]
    result = {
        "method": method,
        "simulations": simulations,
        "trades": trades,
        "seed": seed,
        "ending_return_pct": {
            f"p{x}": float(np.percentile(ending_returns, x)) for x in quantiles
        },
        "max_drawdown_pct": {
            f"p{x}": float(np.percentile(max_drawdowns, x)) for x in quantiles
        },
        "probability_profitable_pct": float((ending_returns > 0).mean() * 100.0),
        "probability_drawdown_gt_30_pct": float((max_drawdowns > 30.0).mean() * 100.0),
        "probability_drawdown_gt_50_pct": float((max_drawdowns > 50.0).mean() * 100.0),
    }
    if block_size is not None:
        result["block_size"] = block_size
    return result


def bootstrap_trade_paths(
    trades: list[Trade],
    simulations: int = 2000,
    seed: int = 42,
) -> dict:
    """IID bootstrap. Useful baseline, but does not preserve streak clustering."""
    if simulations < 100 or simulations > 100_000:
        raise ValueError("simulations must be between 100 and 100000")
    if not trades:
        return {
            "method": "iid",
            "simulations": simulations,
            "trades": 0,
            "error": "no_trades",
        }

    returns = np.array([float(trade.return_pct) for trade in trades], dtype=float)
    rng = np.random.default_rng(seed)
    ending_returns = np.empty(simulations, dtype=float)
    max_drawdowns = np.empty(simulations, dtype=float)

    for i in range(simulations):
        sampled = rng.choice(returns, size=len(returns), replace=True)
        ending_returns[i], max_drawdowns[i] = _path_metrics(sampled)

    return _summarize_paths(
        ending_returns,
        max_drawdowns,
        simulations,
        len(trades),
        seed,
        "iid",
    )


def bootstrap_trade_blocks(
    trades: list[Trade],
    simulations: int = 2000,
    block_size: int = 4,
    seed: int = 43,
) -> dict:
    """Moving-block bootstrap that preserves short runs of wins/losses.

    Blocks are sampled from the observed chronological trade-return sequence and
    concatenated until each synthetic path has the original number of trades.
    """
    if simulations < 100 or simulations > 100_000:
        raise ValueError("simulations must be between 100 and 100000")
    if block_size < 2 or block_size > 50:
        raise ValueError("block_size must be between 2 and 50")
    if not trades:
        return {
            "method": "moving_block",
            "simulations": simulations,
            "trades": 0,
            "block_size": block_size,
            "error": "no_trades",
        }

    returns = np.array([float(trade.return_pct) for trade in trades], dtype=float)
    n = len(returns)
    effective_block = min(block_size, n)
    starts = np.arange(max(1, n - effective_block + 1))
    rng = np.random.default_rng(seed)
    ending_returns = np.empty(simulations, dtype=float)
    max_drawdowns = np.empty(simulations, dtype=float)

    for i in range(simulations):
        sampled_parts: list[np.ndarray] = []
        collected = 0
        while collected < n:
            start = int(rng.choice(starts))
            block = returns[start : start + effective_block]
            sampled_parts.append(block)
            collected += len(block)
        sampled = np.concatenate(sampled_parts)[:n]
        ending_returns[i], max_drawdowns[i] = _path_metrics(sampled)

    return _summarize_paths(
        ending_returns,
        max_drawdowns,
        simulations,
        n,
        seed,
        "moving_block",
        block_size=effective_block,
    )
