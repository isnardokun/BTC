from __future__ import annotations

from collections import defaultdict

import polars as pl

from btc_quant_lab.models import PivotSignal, Trade
from btc_quant_lab.research.backtest import metrics_from_trades
from btc_quant_lab.research.features import build_feature_rows
from btc_quant_lab.research.montecarlo import bootstrap_trade_blocks

DEFAULT_GROUPS = (
    "trend_regime",
    "volatility_regime",
    "market_structure",
    "structure_break",
    "signal_context",
    "trend_contradiction_score",
    "direction",
)


def validate_by_regime(
    df: pl.DataFrame,
    signals: list[PivotSignal],
    trades: list[Trade],
    groups: tuple[str, ...] = DEFAULT_GROUPS,
    simulations: int = 1000,
    min_bootstrap_trades: int = 8,
    block_size: int = 4,
) -> dict:
    """Evaluate completed trades by causal context known at trade entry.

    Context is attached using the pivot signal timestamp that opened the trade. No exit
    information is used to define a regime bucket; trade outcome is only the label measured.
    """
    if min_bootstrap_trades < 2:
        raise ValueError("min_bootstrap_trades must be at least 2")

    feature_rows = build_feature_rows(df, signals, trades)
    feature_by_ts = {int(row["ts"]): row for row in feature_rows}
    trade_by_entry = {int(trade.entry_ts): trade for trade in trades}

    matched: list[tuple[Trade, dict]] = []
    for entry_ts, trade in trade_by_entry.items():
        features = feature_by_ts.get(entry_ts)
        if features is not None:
            matched.append((trade, features))

    result: dict[str, dict] = {}
    for group in groups:
        buckets: dict[str, list[Trade]] = defaultdict(list)
        for trade, features in matched:
            value = features.get(group)
            name = "unknown" if value is None else str(value)
            buckets[name].append(trade)

        group_result: dict[str, dict] = {}
        for name, bucket_trades in sorted(buckets.items()):
            metrics = metrics_from_trades(bucket_trades)
            bootstrap = None
            if len(bucket_trades) >= min_bootstrap_trades:
                bootstrap = bootstrap_trade_blocks(
                    bucket_trades,
                    simulations=simulations,
                    block_size=min(block_size, len(bucket_trades)),
                )
            group_result[name] = {
                "metrics": metrics,
                "block_bootstrap": bootstrap,
            }
        result[group] = group_result

    return {
        "matched_trades": len(matched),
        "total_trades": len(trades),
        "match_rate_pct": len(matched) * 100.0 / len(trades) if trades else None,
        "method": {
            "context_timestamp": "trade_entry_signal_confirmation",
            "causal_context_only": True,
            "simulations": simulations,
            "min_bootstrap_trades": min_bootstrap_trades,
            "block_size": block_size,
        },
        "groups": result,
    }
