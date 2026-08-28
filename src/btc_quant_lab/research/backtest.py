from dataclasses import asdict
import numpy as np
from btc_quant_lab.models import PivotSignal, Trade


def reversal_backtest(signals: list[PivotSignal]) -> tuple[list[Trade], dict]:
    trades: list[Trade] = []
    position_dir = 0
    entry = None
    entry_ts = None
    for sig in signals:
        new_dir = sig.direction
        px = sig.confirm_price
        if position_dir != 0 and new_dir != position_dir and entry is not None:
            ret = ((px / entry - 1.0) * 100.0) if position_dir == 1 else ((entry / px - 1.0) * 100.0)
            trades.append(Trade(position_dir, entry_ts, entry, sig.ts, px, ret))
        if new_dir != position_dir:
            position_dir = new_dir
            entry = px
            entry_ts = sig.ts

    returns = np.array([t.return_pct for t in trades], dtype=float)
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    equity = np.cumsum(returns) if len(returns) else np.array([])
    peak = np.maximum.accumulate(equity) if len(equity) else np.array([])
    dd = peak - equity if len(equity) else np.array([])
    metrics = {
        "trades": len(trades),
        "wins": int((returns > 0).sum()) if len(returns) else 0,
        "losses": int((returns < 0).sum()) if len(returns) else 0,
        "win_rate": float((returns > 0).mean() * 100) if len(returns) else None,
        "net_return_pct": float(returns.sum()) if len(returns) else 0.0,
        "expectancy_pct": float(returns.mean()) if len(returns) else None,
        "profit_factor": float(wins.sum() / abs(losses.sum())) if len(losses) and abs(losses.sum()) > 0 else None,
        "max_drawdown_pct": float(dd.max()) if len(dd) else 0.0,
        "best_trade_pct": float(returns.max()) if len(returns) else None,
        "worst_trade_pct": float(returns.min()) if len(returns) else None,
    }
    return trades, metrics


def trade_dicts(trades: list[Trade]) -> list[dict]:
    return [asdict(t) for t in trades]
