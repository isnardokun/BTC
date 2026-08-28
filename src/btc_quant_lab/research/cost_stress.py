from __future__ import annotations

from collections.abc import Iterable

from btc_quant_lab.models import PivotSignal
from btc_quant_lab.research.backtest import reversal_backtest, round_trip_cost_pct


def execution_cost_stress(
    signals: list[PivotSignal],
    fee_bps_values: Iterable[float] = (0.0, 5.0, 10.0, 20.0),
    slippage_bps_values: Iterable[float] = (0.0, 5.0, 10.0),
) -> dict:
    scenarios: list[dict] = []
    for fee_bps in fee_bps_values:
        for slippage_bps in slippage_bps_values:
            trades, metrics = reversal_backtest(
                signals,
                fee_bps=float(fee_bps),
                slippage_bps=float(slippage_bps),
            )
            scenarios.append(
                {
                    "fee_bps": float(fee_bps),
                    "slippage_bps": float(slippage_bps),
                    "round_trip_cost_pct": round_trip_cost_pct(
                        float(fee_bps),
                        float(slippage_bps),
                    ),
                    "trades": len(trades),
                    "compounded_return_pct": metrics["compounded_return_pct"],
                    "expectancy_pct": metrics["expectancy_pct"],
                    "profit_factor": metrics["profit_factor"],
                    "max_drawdown_pct": metrics["max_drawdown_pct"],
                }
            )

    positive = [row for row in scenarios if row["compounded_return_pct"] > 0]
    profitable_costs = [row["round_trip_cost_pct"] for row in positive]
    return {
        "scenarios": scenarios,
        "summary": {
            "scenario_count": len(scenarios),
            "profitable_scenarios": len(positive),
            "profitable_scenarios_pct": (
                len(positive) * 100.0 / len(scenarios) if scenarios else None
            ),
            "highest_profitable_round_trip_cost_pct": (
                max(profitable_costs) if profitable_costs else None
            ),
            "worst_compounded_return_pct": (
                min(row["compounded_return_pct"] for row in scenarios)
                if scenarios
                else None
            ),
            "worst_max_drawdown_pct": (
                max(row["max_drawdown_pct"] for row in scenarios)
                if scenarios
                else None
            ),
        },
    }
