from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

PROMOTIONS = Path("experiments/promotions")


def assess_promotion(
    champion: dict,
    final_holdout: dict,
    protocol: dict,
    parameter_sensitivity: dict | None = None,
    min_development_trades: int = 15,
    min_holdout_trades: int = 8,
    max_holdout_drawdown_pct: float = 50.0,
    min_mc_probability_profitable_pct: float = 60.0,
) -> dict:
    """Assess whether a research champion is eligible for human promotion review.

    Passing this function never deploys or tags a strategy. It only creates an
    auditable gate report based on evidence already produced by the research loop.
    """
    development = champion.get("out_of_sample", {}).get("aggregate", {})
    holdout = final_holdout.get("metrics", {})
    holdout_mc = final_holdout.get("monte_carlo") or {}
    plateau = (parameter_sensitivity or {}).get("plateau") or {}

    dev_trades = int(development.get("trades") or 0)
    holdout_trades = int(holdout.get("trades") or 0)
    dev_expectancy = float(development.get("expectancy_pct") or 0.0)
    holdout_expectancy = float(holdout.get("expectancy_pct") or 0.0)
    dev_pf = float(development.get("profit_factor") or 0.0)
    holdout_pf = float(holdout.get("profit_factor") or 0.0)
    holdout_compounded = float(holdout.get("compounded_return_pct") or 0.0)
    holdout_dd = float(holdout.get("max_drawdown_pct") or 0.0)
    profitable_windows = development.get("profitable_windows_pct")
    mc_prob = holdout_mc.get("probability_profitable_pct")

    gates = {
        "development_sample": dev_trades >= min_development_trades,
        "development_expectancy_positive": dev_expectancy > 0,
        "development_profit_factor_above_1": dev_pf > 1.0,
        "development_window_consistency": (
            profitable_windows is None or float(profitable_windows) >= 50.0
        ),
        "holdout_sample": holdout_trades >= min_holdout_trades,
        "holdout_expectancy_positive": holdout_expectancy > 0,
        "holdout_profit_factor_above_1": holdout_pf > 1.0,
        "holdout_compounded_return_positive": holdout_compounded > 0,
        "holdout_drawdown_within_limit": holdout_dd <= max_holdout_drawdown_pct,
        "holdout_monte_carlo_support": (
            mc_prob is None or float(mc_prob) >= min_mc_probability_profitable_pct
        ),
        "holdout_was_hidden": protocol.get("holdout_exposed_during_research") is False,
    }

    warnings: list[str] = []
    interpretation = plateau.get("interpretation")
    if interpretation == "fragile":
        warnings.append("parameter plateau is fragile")
    excess = final_holdout.get("vs_buy_hold", {}).get("excess_return_pct_points")
    if excess is not None and float(excess) < 0:
        warnings.append("strategy underperformed Buy & Hold on final holdout")
    if mc_prob is None:
        warnings.append("final holdout has insufficient trades for Monte Carlo evidence")

    failed = [name for name, passed in gates.items() if not passed]
    eligible = not failed

    return {
        "status": "eligible_for_review" if eligible else "rejected_for_promotion",
        "eligible": eligible,
        "gates": gates,
        "failed_gates": failed,
        "warnings": warnings,
        "thresholds": {
            "min_development_trades": min_development_trades,
            "min_holdout_trades": min_holdout_trades,
            "max_holdout_drawdown_pct": max_holdout_drawdown_pct,
            "min_mc_probability_profitable_pct": min_mc_probability_profitable_pct,
        },
        "evidence": {
            "development_oos": development,
            "final_holdout": holdout,
            "final_holdout_vs_buy_hold": final_holdout.get("vs_buy_hold"),
            "final_holdout_monte_carlo": holdout_mc,
            "parameter_plateau": plateau,
        },
        "note": "eligibility requires explicit human or harness review before creating stable",
    }


def write_promotion_manifest(
    champion: dict,
    final_holdout: dict,
    protocol: dict,
    assessment: dict,
    symbol: str,
    interval: str,
) -> dict:
    PROMOTIONS.mkdir(parents=True, exist_ok=True)
    promotion_id = uuid.uuid4().hex[:12]
    payload = {
        "promotion_id": promotion_id,
        "created_at": datetime.now(UTC).isoformat(),
        "symbol": symbol,
        "interval": interval,
        "status": assessment["status"],
        "protocol": protocol,
        "champion": champion,
        "final_holdout": final_holdout,
        "assessment": assessment,
    }
    path = PROMOTIONS / f"{promotion_id}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"promotion_id": promotion_id, "path": str(path), **assessment}
