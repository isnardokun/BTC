from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import math

import polars as pl

from btc_quant_lab.models import Trade
from btc_quant_lab.research.backtest import metrics_from_trades


def _year(ts_ms: int) -> int:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).year


def yearly_performance(trades: list[Trade]) -> list[dict]:
    grouped: dict[int, list[Trade]] = defaultdict(list)
    for trade in trades:
        grouped[_year(int(trade.exit_ts))].append(trade)

    rows = []
    for year in sorted(grouped):
        metrics = metrics_from_trades(grouped[year])
        rows.append({"year": year, **metrics})
    return rows


def buy_and_hold_benchmark(df: pl.DataFrame) -> dict:
    if len(df) < 2:
        return {
            "bars": len(df),
            "return_pct": None,
            "cagr_pct": None,
            "max_drawdown_pct": None,
        }

    first = df.row(0, named=True)
    last = df.row(-1, named=True)
    first_close = float(first["close"])
    last_close = float(last["close"])
    total_return = (last_close / first_close - 1.0) * 100.0

    elapsed_days = max((int(last["ts"]) - int(first["ts"])) / 86_400_000.0, 1.0)
    years = elapsed_days / 365.25
    cagr = ((last_close / first_close) ** (1.0 / years) - 1.0) * 100.0 if years > 0 else None

    closes = [float(x) for x in df["close"].to_list()]
    peak = closes[0]
    max_dd = 0.0
    for close in closes:
        peak = max(peak, close)
        if peak > 0:
            max_dd = max(max_dd, (peak - close) / peak * 100.0)

    return {
        "bars": len(df),
        "start_ts": int(first["ts"]),
        "end_ts": int(last["ts"]),
        "start_price": first_close,
        "end_price": last_close,
        "return_pct": total_return,
        "cagr_pct": cagr,
        "max_drawdown_pct": max_dd,
    }


def strategy_vs_buy_hold(strategy_metrics: dict, benchmark: dict) -> dict:
    strategy_return = strategy_metrics.get("compounded_return_pct")
    benchmark_return = benchmark.get("return_pct")
    return {
        "strategy_compounded_return_pct": strategy_return,
        "buy_hold_return_pct": benchmark_return,
        "excess_return_pct_points": (
            float(strategy_return) - float(benchmark_return)
            if strategy_return is not None and benchmark_return is not None
            else None
        ),
        "strategy_max_drawdown_pct": strategy_metrics.get("max_drawdown_pct"),
        "buy_hold_max_drawdown_pct": benchmark.get("max_drawdown_pct"),
    }
