from __future__ import annotations

import math

import polars as pl

from btc_quant_lab.ai.agent import propose_iteration
from btc_quant_lab.experiments import list_experiments, record_experiment
from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.backtest import reversal_backtest
from btc_quant_lab.research.features import build_feature_rows, summarize_feature_outcomes
from btc_quant_lab.research.filters import filter_signals, validate_filter_spec
from btc_quant_lab.research.optimizer import optimize
from btc_quant_lab.research.pivots import detect_pivots
from btc_quant_lab.research.walkforward import evaluate_fixed_config

ALLOWED_MOTORS = {"M1", "M3"}
ALLOWED_RANGES = {"R4", "R7", "R8"}
ALLOWED_MIN_BARS = {2, 3, 4, 5}
ALLOWED_MAX_PENDING = {0, 3, 5, 8}


def _validate_parameters(raw: dict) -> PivotConfig:
    motor = raw.get("motor")
    range_mode = raw.get("range_mode")
    min_bars = int(raw.get("min_bars"))
    max_pending = int(raw.get("max_pending"))
    if motor not in ALLOWED_MOTORS:
        raise ValueError(f"invalid motor: {motor}")
    if range_mode not in ALLOWED_RANGES:
        raise ValueError(f"invalid range_mode: {range_mode}")
    if min_bars not in ALLOWED_MIN_BARS:
        raise ValueError(f"invalid min_bars: {min_bars}")
    if max_pending not in ALLOWED_MAX_PENDING:
        raise ValueError(f"invalid max_pending: {max_pending}")
    return PivotConfig(
        motor=motor,
        range_mode=range_mode,
        min_bars=min_bars,
        max_pending=max_pending,
    )


def robustness_score(aggregate: dict, min_trades: int = 15) -> float:
    trades = int(aggregate.get("trades") or 0)
    if trades < min_trades:
        return float("-inf")
    expectancy = float(aggregate.get("expectancy_pct") or 0.0)
    profit_factor = min(float(aggregate.get("profit_factor") or 0.0), 5.0)
    drawdown = max(float(aggregate.get("max_drawdown_pct") or 0.0), 1.0)
    profitable_windows = aggregate.get("profitable_windows_pct")
    stability = max(float(profitable_windows or 0.0) / 100.0, 0.20)
    return expectancy * max(profit_factor, 0.1) * math.sqrt(trades) * stability / math.sqrt(drawdown)


def _evaluate_candidate(
    df: pl.DataFrame,
    cfg: PivotConfig,
    signal_filter: dict | None,
    warmup_bars: int,
    test_bars: int,
    min_trades: int,
) -> dict:
    signals = detect_pivots(df, cfg)
    signals = filter_signals(df, signals, signal_filter)
    trades, full_metrics = reversal_backtest(signals)
    oos = evaluate_fixed_config(
        df,
        cfg,
        warmup_bars=warmup_bars,
        test_bars=test_bars,
        step_bars=test_bars,
        signal_filter=signal_filter,
    )
    return {
        "config": {
            "motor": cfg.motor,
            "range_mode": cfg.range_mode,
            "min_bars": cfg.min_bars,
            "max_pending": cfg.max_pending,
        },
        "filter": signal_filter,
        "full_history": full_metrics,
        "out_of_sample": oos,
        "robustness_score": robustness_score(oos["aggregate"], min_trades=min_trades),
        "feature_summary": summarize_feature_outcomes(build_feature_rows(df, signals, trades)),
    }


async def run_autonomous_research(
    df: pl.DataFrame,
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    iterations: int = 3,
    min_trades: int = 15,
) -> dict:
    if df.is_empty():
        raise ValueError("market data is empty")
    if iterations < 1 or iterations > 20:
        raise ValueError("iterations must be between 1 and 20")

    # Daily defaults adapt down for short histories while preserving chronology.
    warmup_bars = min(1095, max(365, len(df) // 2))
    test_bars = min(365, max(90, len(df) // 6))
    if warmup_bars + test_bars > len(df):
        warmup_bars = max(100, len(df) // 2)
        test_bars = max(30, min(len(df) - warmup_bars, len(df) // 4))

    ranked = optimize(df, min_trades=min_trades)
    if not ranked:
        raise ValueError("optimizer produced no baseline")

    baseline_cfg = PivotConfig(**ranked[0]["config"])
    champion = _evaluate_candidate(
        df,
        baseline_cfg,
        None,
        warmup_bars,
        test_bars,
        min_trades,
    )
    champion["source"] = "baseline"

    outcomes: list[dict] = []
    for iteration in range(1, iterations + 1):
        context = {
            "symbol": symbol,
            "interval": interval,
            "iteration": iteration,
            "objective": "capturar movimientos sostenidos de BTC con señales de reversión robustas fuera de muestra",
            "current_champion": champion,
            "top_in_sample": ranked[:10],
            "recent_experiments": list_experiments(30),
            "rules": {
                "no_lookahead": True,
                "candidate_must_beat_champion_out_of_sample": True,
                "minimum_oos_trades": min_trades,
                "stable_branch_is_immutable": True,
            },
        }
        proposal_exp = await propose_iteration(context)
        proposal = proposal_exp.get("proposal", {})
        proposal_type = proposal.get("proposal_type")

        if proposal_type == "code":
            evaluation = record_experiment(
                {
                    "kind": "ai_evaluation",
                    "parent_id": proposal_exp["id"],
                    "status": "awaiting_sandbox",
                    "reason": "code proposal stored as fork; automatic code execution is intentionally disabled until sandbox validation is implemented",
                }
            )
            outcomes.append(evaluation)
            continue

        try:
            raw_params = proposal.get("parameters") or champion["config"]
            cfg = _validate_parameters(raw_params)
            signal_filter = None
            if proposal_type == "filter":
                signal_filter = validate_filter_spec(proposal.get("filter_proposal"))

            candidate = _evaluate_candidate(
                df,
                cfg,
                signal_filter,
                warmup_bars,
                test_bars,
                min_trades,
            )
            champion_score = float(champion.get("robustness_score", float("-inf")))
            candidate_score = float(candidate["robustness_score"])
            accepted = candidate_score > champion_score
            status = "accepted_candidate" if accepted else "rejected"

            evaluation = record_experiment(
                {
                    "kind": "ai_evaluation",
                    "parent_id": proposal_exp["id"],
                    "status": status,
                    "hypothesis": proposal.get("hypothesis"),
                    "candidate": candidate,
                    "champion_score_before": champion_score,
                    "decision_rule": "candidate robustness_score must exceed current champion",
                }
            )
            outcomes.append(evaluation)
            if accepted:
                champion = {**candidate, "source": evaluation["id"]}

        except (TypeError, ValueError) as exc:
            evaluation = record_experiment(
                {
                    "kind": "ai_evaluation",
                    "parent_id": proposal_exp["id"],
                    "status": "invalid_proposal",
                    "error": str(exc),
                }
            )
            outcomes.append(evaluation)

    return {
        "symbol": symbol,
        "interval": interval,
        "iterations": iterations,
        "champion": champion,
        "evaluations": outcomes,
    }
