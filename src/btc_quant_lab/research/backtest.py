from dataclasses import asdict

import numpy as np

from btc_quant_lab.models import PivotSignal, Trade


def trade_return_pct(direction: int, entry: float, exit_price: float) -> float:
    """Signed price return captured by a position, measured from entry price."""
    if direction == 1:
        return (exit_price - entry) / entry * 100.0
    return (entry - exit_price) / entry * 100.0


def round_trip_cost_pct(fee_bps: float = 0.0, slippage_bps: float = 0.0) -> float:
    """Approximate entry+exit execution drag in percentage points."""
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("fees and slippage must be non-negative")
    return 2.0 * (fee_bps + slippage_bps) / 100.0


def metrics_from_trades(trades: list[Trade]) -> dict:
    returns = np.array([t.return_pct for t in trades], dtype=float)
    wins = returns[returns > 0]
    losses = returns[returns < 0]

    if len(returns):
        growth = 1.0 + returns / 100.0
        equity = np.cumprod(growth)
        peak = np.maximum.accumulate(np.concatenate(([1.0], equity)))
        equity_with_start = np.concatenate(([1.0], equity))
        drawdown = (peak - equity_with_start) / peak * 100.0
        compounded_return = (equity[-1] - 1.0) * 100.0
        max_drawdown = float(drawdown.max())
    else:
        compounded_return = 0.0
        max_drawdown = 0.0

    total_cost = float(sum(t.cost_pct for t in trades)) if trades else 0.0
    gross_returns = [
        float(t.gross_return_pct)
        for t in trades
        if t.gross_return_pct is not None
    ]

    return {
        "trades": len(trades),
        "wins": int((returns > 0).sum()) if len(returns) else 0,
        "losses": int((returns < 0).sum()) if len(returns) else 0,
        "win_rate": float((returns > 0).mean() * 100) if len(returns) else None,
        "net_return_pct": float(returns.sum()) if len(returns) else 0.0,
        "compounded_return_pct": float(compounded_return),
        "gross_return_sum_pct": float(sum(gross_returns)) if gross_returns else None,
        "execution_cost_sum_pct": total_cost,
        "expectancy_pct": float(returns.mean()) if len(returns) else None,
        "profit_factor": (
            float(wins.sum() / abs(losses.sum()))
            if len(losses) and abs(losses.sum()) > 0
            else None
        ),
        "max_drawdown_pct": max_drawdown,
        "best_trade_pct": float(returns.max()) if len(returns) else None,
        "worst_trade_pct": float(returns.min()) if len(returns) else None,
    }


def reversal_backtest(
    signals: list[PivotSignal],
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> tuple[list[Trade], dict]:
    trades: list[Trade] = []
    position_dir = 0
    entry = None
    entry_ts = None
    cost_pct = round_trip_cost_pct(fee_bps=fee_bps, slippage_bps=slippage_bps)

    for sig in signals:
        new_dir = sig.direction
        px = sig.confirm_price

        if position_dir != 0 and new_dir != position_dir and entry is not None:
            gross = trade_return_pct(position_dir, entry, px)
            net = gross - cost_pct
            trades.append(
                Trade(
                    direction=position_dir,
                    entry_ts=entry_ts,
                    entry=entry,
                    exit_ts=sig.ts,
                    exit=px,
                    return_pct=net,
                    gross_return_pct=gross,
                    cost_pct=cost_pct,
                )
            )

        if new_dir != position_dir:
            position_dir = new_dir
            entry = px
            entry_ts = sig.ts

    return trades, metrics_from_trades(trades)


def trade_dicts(trades: list[Trade]) -> list[dict]:
    return [asdict(t) for t in trades]
