from itertools import product
import math

import polars as pl

from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.backtest import reversal_backtest
from btc_quant_lab.research.pivots import detect_pivots


def trading_score(m: dict, min_trades: int = 20) -> float:
    n = m["trades"]
    if n < min_trades:
        return float("-inf")
    exp = m["expectancy_pct"] or 0.0
    pf = min(m["profit_factor"] or 0.0, 5.0)
    dd = max(m["max_drawdown_pct"], 1.0)
    return exp * max(pf, 0.1) * math.sqrt(n) / math.sqrt(dd)


def optimize(
    df: pl.DataFrame,
    min_trades: int = 20,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> list[dict]:
    rows = []
    for motor, range_mode, min_bars, max_pending in product(
        ["M1", "M3"],
        ["R4", "R7", "R8"],
        [2, 3, 4, 5],
        [0, 3, 5, 8],
    ):
        cfg = PivotConfig(
            motor=motor,
            range_mode=range_mode,
            min_bars=min_bars,
            max_pending=max_pending,
        )
        sigs = detect_pivots(df, cfg)
        _, metrics = reversal_backtest(
            sigs,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )
        rows.append(
            {
                "config": {
                    "motor": motor,
                    "range_mode": range_mode,
                    "min_bars": min_bars,
                    "max_pending": max_pending,
                },
                **metrics,
                "score": trading_score(metrics, min_trades),
                "signals": len(sigs),
                "cost_model": {"fee_bps": fee_bps, "slippage_bps": slippage_bps},
            }
        )
    return sorted(rows, key=lambda x: x["score"], reverse=True)
