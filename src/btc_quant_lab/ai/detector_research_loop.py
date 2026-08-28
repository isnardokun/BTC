from __future__ import annotations

import math

import polars as pl

from btc_quant_lab.ai.agent import propose_iteration
from btc_quant_lab.ai.critic import review_candidate
from btc_quant_lab.ai.detector_candidate import (
    collect_detector_candidate_evidence,
    full_detector_sandbox_ready,
)
from btc_quant_lab.ai.process_sandbox import (
    DetectorSandboxError,
    assert_prefix_causal,
    run_detector_fork,
)
from btc_quant_lab.experiments import list_experiments, record_experiment, write_fork_result
from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.analytics import (
    buy_and_hold_benchmark,
    strategy_vs_buy_hold,
    yearly_performance,
)
from btc_quant_lab.research.backtest import metrics_from_trades, reversal_backtest
from btc_quant_lab.research.features import build_feature_rows, summarize_feature_outcomes
from btc_quant_lab.research.montecarlo import bootstrap_trade_paths
from btc_quant_lab.research.optimizer import optimize
from btc_quant_lab.research.pivots import detect_pivots
from btc_quant_lab.research.promotion import assess_promotion, write_promotion_manifest
from btc_quant_lab.research.regime_validation import validate_by_regime
from btc_quant_lab.research.sensitivity import parameter_sensitivity
from btc_quant_lab.research.walkforward import evaluate_fixed_config, purged_walk_forward

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


def _config_dict(cfg: PivotConfig) -> dict:
    return {
        "motor": cfg.motor,
        "range_mode": cfg.range_mode,
        "min_bars": cfg.min_bars,
        "max_pending": cfg.max_pending,
    }


def _robustness_score(aggregate: dict, min_trades: int) -> float:
    trades = int(aggregate.get("trades") or 0)
    if trades < min_trades:
        return float("-inf")
    expectancy = float(aggregate.get("expectancy_pct") or 0.0)
    profit_factor = min(float(aggregate.get("profit_factor") or 0.0), 5.0)
    drawdown = max(float(aggregate.get("max_drawdown_pct") or 0.0), 1.0)
    profitable_windows = aggregate.get("profitable_windows_pct")
    stability = max(float(profitable_windows or 0.0) / 100.0, 0.20)
    return expectancy * max(profit_factor, 0.1) * math.sqrt(trades) * stability / math.sqrt(
        drawdown
    )


def _regime_evidence(df: pl.DataFrame, signals, trades, min_trades: int) -> dict:
    return validate_by_regime(
        df,
        signals,
        trades,
        simulations=300,
        min_bootstrap_trades=max(5, min_trades // 2),
        block_size=4,
    )


def _evaluate_baseline(
    df: pl.DataFrame,
    cfg: PivotConfig,
    warmup_bars: int,
    test_bars: int,
    min_trades: int,
    fee_bps: float,
    slippage_bps: float,
) -> dict:
    signals = detect_pivots(df, cfg)
    trades, full_metrics = reversal_backtest(
        signals,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    oos = evaluate_fixed_config(
        df,
        cfg,
        warmup_bars=warmup_bars,
        test_bars=test_bars,
        step_bars=test_bars,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    benchmark = buy_and_hold_benchmark(df)
    return {
        "kind": "baseline_detector",
        "config": _config_dict(cfg),
        "filter": None,
        "cost_model": {"fee_bps": fee_bps, "slippage_bps": slippage_bps},
        "full_history": full_metrics,
        "out_of_sample": oos,
        "robustness_score": _robustness_score(oos["aggregate"], min_trades),
        "feature_summary": summarize_feature_outcomes(build_feature_rows(df, signals, trades)),
        "regime_validation": _regime_evidence(df, signals, trades, min_trades),
        "yearly": yearly_performance(trades),
        "benchmark": benchmark,
        "vs_buy_hold": strategy_vs_buy_hold(full_metrics, benchmark),
        "monte_carlo": bootstrap_trade_paths(trades, simulations=1000) if trades else None,
    }


def _evaluate_detector_candidate(
    df: pl.DataFrame,
    fork_id: str,
    cfg: PivotConfig,
    warmup_bars: int,
    test_bars: int,
    purge_bars: int,
    embargo_bars: int,
    min_trades: int,
    fee_bps: float,
    slippage_bps: float,
) -> dict:
    (
        signals,
        trades,
        full_metrics,
        oos,
        boundary_gap_oos,
        causality,
    ) = collect_detector_candidate_evidence(
        df,
        fork_id,
        cfg,
        warmup_bars=warmup_bars,
        test_bars=test_bars,
        purge_bars=purge_bars,
        embargo_bars=embargo_bars,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    benchmark = buy_and_hold_benchmark(df)
    return {
        "kind": "detector_process_sandbox",
        "fork_id": fork_id,
        "config": _config_dict(cfg),
        "filter": None,
        "cost_model": {"fee_bps": fee_bps, "slippage_bps": slippage_bps},
        "causality_audit": causality,
        "full_history": full_metrics,
        "out_of_sample": oos,
        "boundary_gap_oos": boundary_gap_oos,
        "robustness_score": _robustness_score(oos["aggregate"], min_trades),
        "feature_summary": summarize_feature_outcomes(build_feature_rows(df, signals, trades)),
        "regime_validation": _regime_evidence(df, signals, trades, min_trades),
        "yearly": yearly_performance(trades),
        "benchmark": benchmark,
        "vs_buy_hold": strategy_vs_buy_hold(full_metrics, benchmark),
        "monte_carlo": bootstrap_trade_paths(trades, simulations=1000) if trades else None,
    }


def _compact_candidate(item: dict) -> dict:
    groups = item.get("regime_validation", {}).get("groups", {})
    return {
        "kind": item.get("kind"),
        "fork_id": item.get("fork_id"),
        "config": item.get("config"),
        "robustness_score": item.get("robustness_score"),
        "causality_audit": item.get("causality_audit"),
        "full_history": item.get("full_history"),
        "oos_aggregate": item.get("out_of_sample", {}).get("aggregate"),
        "boundary_gap_oos": item.get("boundary_gap_oos", {}).get("aggregate"),
        "feature_summary": item.get("feature_summary"),
        "regime_validation": {
            "signal_context": groups.get("signal_context"),
            "trend_contradiction_score": groups.get("trend_contradiction_score"),
            "market_structure": groups.get("market_structure"),
        },
        "vs_buy_hold": item.get("vs_buy_hold"),
        "monte_carlo": item.get("monte_carlo"),
        "yearly": item.get("yearly"),
    }


def _signals_for_candidate(df: pl.DataFrame, candidate: dict):
    cfg = PivotConfig(**candidate["config"])
    if candidate.get("kind") == "detector_process_sandbox":
        return run_detector_fork(df, candidate["fork_id"], config=cfg)
    return detect_pivots(df, cfg)


def _final_holdout(
    full_df: pl.DataFrame,
    development_df: pl.DataFrame,
    champion: dict,
    holdout_start_index: int,
    fee_bps: float,
    slippage_bps: float,
) -> dict:
    if champion.get("kind") == "detector_process_sandbox":
        development_signals = _signals_for_candidate(development_df, champion)
        signals = _signals_for_candidate(full_df, champion)
        assert_prefix_causal(
            development_signals,
            signals,
            int(development_df["ts"][-1]),
        )
    else:
        signals = _signals_for_candidate(full_df, champion)

    trades, _ = reversal_backtest(
        signals,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    timestamps = full_df["ts"].to_list()
    start_ts = int(timestamps[holdout_start_index])
    end_ts = int(timestamps[-1])
    holdout_trades = [
        trade
        for trade in trades
        if int(trade.entry_ts) >= start_ts and int(trade.exit_ts) <= end_ts
    ]
    holdout_signals = [signal for signal in signals if int(signal.ts) >= start_ts]
    metrics = metrics_from_trades(holdout_trades)
    holdout_df = full_df.slice(holdout_start_index, len(full_df) - holdout_start_index)
    benchmark = buy_and_hold_benchmark(holdout_df)
    return {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "bars": len(holdout_df),
        "cost_model": {"fee_bps": fee_bps, "slippage_bps": slippage_bps},
        "metrics": metrics,
        "yearly": yearly_performance(holdout_trades),
        "benchmark": benchmark,
        "vs_buy_hold": strategy_vs_buy_hold(metrics, benchmark),
        "regime_validation": validate_by_regime(
            full_df,
            holdout_signals,
            holdout_trades,
            simulations=500,
            min_bootstrap_trades=5,
            block_size=4,
        ),
        "monte_carlo": (
            bootstrap_trade_paths(holdout_trades, simulations=2000)
            if holdout_trades
            else None
        ),
        "note": (
            "final holdout was hidden during proposal/critique; detector forks also passed "
            "a development-to-full prefix-invariance check before holdout scoring"
        ),
    }


async def run_autonomous_detector_research(
    df: pl.DataFrame,
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    iterations: int = 3,
    min_trades: int = 15,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> dict:
    """Research full detector mutations without exposing the final holdout to the AI."""
    if df.is_empty():
        raise ValueError("market data is empty")
    if iterations < 1 or iterations > 10:
        raise ValueError("iterations must be between 1 and 10")
    if len(df) < 700:
        raise ValueError("detector research needs at least 700 bars")
    if not full_detector_sandbox_ready():
        raise DetectorSandboxError(
            "full detector sandbox is not ready; run scripts/setup_detector_sandbox_arch.sh"
        )

    holdout_bars = min(730, max(180, len(df) // 6))
    development_end = len(df) - holdout_bars
    if development_end < 500:
        holdout_bars = max(120, len(df) // 5)
        development_end = len(df) - holdout_bars
    development_df = df.slice(0, development_end)

    warmup_bars = min(1095, max(365, len(development_df) // 2))
    test_bars = min(365, max(90, len(development_df) // 6))
    if warmup_bars + test_bars > len(development_df):
        warmup_bars = max(100, len(development_df) // 2)
        test_bars = max(30, min(len(development_df) - warmup_bars, len(development_df) // 4))
    purge_bars = min(10, max(2, test_bars // 30))
    embargo_bars = purge_bars

    ranked = optimize(
        development_df,
        min_trades=min_trades,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    if not ranked:
        raise ValueError("optimizer produced no baseline")
    baseline_cfg = PivotConfig(**ranked[0]["config"])
    champion = _evaluate_baseline(
        development_df,
        baseline_cfg,
        warmup_bars,
        test_bars,
        min_trades,
        fee_bps,
        slippage_bps,
    )
    champion["source"] = "baseline"

    sensitivity = parameter_sensitivity(
        development_df,
        min_trades=min_trades,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    purged_reference = purged_walk_forward(
        development_df,
        train_bars=warmup_bars,
        test_bars=test_bars,
        purge_bars=purge_bars,
        embargo_bars=embargo_bars,
        step_bars=test_bars,
        min_train_trades=max(5, min_trades // 2),
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )

    outcomes: list[dict] = []
    for iteration in range(1, iterations + 1):
        context = {
            "symbol": symbol,
            "interval": interval,
            "iteration": iteration,
            "objective": (
                "crear una modificación causal del detector que capture movimientos sostenidos "
                "mejor que el champion sin depender de filtros retrospectivos"
            ),
            "research_protocol": {
                "mode": "full_detector_mutation",
                "full_detector_sandbox_ready": True,
                "development_bars": len(development_df),
                "final_holdout_bars": holdout_bars,
                "final_holdout_is_hidden": True,
                "purge_bars": purge_bars,
                "embargo_bars": embargo_bars,
                "cost_model": {"fee_bps": fee_bps, "slippage_bps": slippage_bps},
            },
            "current_champion": _compact_candidate(champion),
            "top_in_sample": ranked[:10],
            "parameter_sensitivity": sensitivity,
            "purged_embargo_reference": {
                "method": purged_reference.get("method"),
                "aggregate": purged_reference.get("aggregate"),
                "selection_frequency": purged_reference.get("selection_frequency"),
            },
            "recent_experiments": list_experiments(30),
            "rules": {
                "proposal_type_must_be_detector_code": True,
                "no_lookahead": True,
                "prefix_invariance_must_pass": True,
                "market_timestamp_and_confirmation_price_validation": True,
                "candidate_must_beat_champion_out_of_sample": True,
                "candidate_boundary_gap_oos_is_reviewed": True,
                "critic_must_approve": True,
                "final_holdout_must_remain_hidden_until_iterations_finish": True,
            },
        }
        proposal_exp = await propose_iteration(context)
        proposal = proposal_exp.get("proposal", {})

        if proposal.get("proposal_type") != "detector_code":
            evaluation = record_experiment(
                {
                    "kind": "detector_ai_evaluation",
                    "parent_id": proposal_exp["id"],
                    "status": "invalid_proposal",
                    "error": "deep detector research requires proposal_type=detector_code",
                }
            )
            outcomes.append(evaluation)
            continue

        try:
            cfg = _validate_parameters(proposal.get("parameters") or champion["config"])
            candidate = _evaluate_detector_candidate(
                development_df,
                proposal_exp["id"],
                cfg,
                warmup_bars,
                test_bars,
                purge_bars,
                embargo_bars,
                min_trades,
                fee_bps,
                slippage_bps,
            )
            write_fork_result(proposal_exp["id"], candidate)

            champion_score = float(champion.get("robustness_score", float("-inf")))
            candidate_score = float(candidate["robustness_score"])
            score_improved = candidate_score > champion_score
            critic = None
            critic_approved = False
            if score_improved:
                try:
                    critic = await review_candidate(
                        {
                            "champion": _compact_candidate(champion),
                            "candidate": _compact_candidate(candidate),
                            "parameter_sensitivity": sensitivity.get("plateau"),
                            "baseline_purged_embargo_reference": {
                                "aggregate": purged_reference.get("aggregate"),
                                "selection_frequency": purged_reference.get(
                                    "selection_frequency"
                                ),
                            },
                            "rule": (
                                "approve only if OOS improvement survives causality audit, "
                                "boundary-gap OOS, regime review and reasonable drawdown"
                            ),
                        }
                    )
                    critic_approved = critic.get("verdict") == "approve"
                except Exception as exc:  # noqa: BLE001 - model boundary; reject conservatively
                    critic = {
                        "verdict": "reject",
                        "rationale": "critic execution failed; conservative rejection",
                        "concerns": [str(exc)],
                        "required_followups": ["retry critic before promotion"],
                    }

            accepted = score_improved and critic_approved
            evaluation = record_experiment(
                {
                    "kind": "detector_ai_evaluation",
                    "parent_id": proposal_exp["id"],
                    "status": "accepted_candidate" if accepted else "rejected",
                    "hypothesis": proposal.get("hypothesis"),
                    "candidate": candidate,
                    "champion_score_before": champion_score,
                    "score_improved": score_improved,
                    "critic": critic,
                    "decision_rule": (
                        "prefix causality + valid market signals + OOS score improvement + "
                        "boundary-gap evidence + independent critic approval"
                    ),
                }
            )
            outcomes.append(evaluation)
            if accepted:
                champion = {**candidate, "source": evaluation["id"]}

        except (DetectorSandboxError, TypeError, ValueError) as exc:
            evaluation = record_experiment(
                {
                    "kind": "detector_ai_evaluation",
                    "parent_id": proposal_exp["id"],
                    "status": "invalid_detector",
                    "error": str(exc),
                }
            )
            outcomes.append(evaluation)

    final_holdout = _final_holdout(
        df,
        development_df,
        champion,
        development_end,
        fee_bps,
        slippage_bps,
    )
    protocol = {
        "mode": "full_detector_mutation",
        "total_bars": len(df),
        "development_bars": len(development_df),
        "final_holdout_bars": holdout_bars,
        "holdout_exposed_during_research": False,
        "purge_bars": purge_bars,
        "embargo_bars": embargo_bars,
        "process_sandbox": "rootless_podman_networkless_readonly",
        "prefix_causality_enforced": True,
        "cost_model": {"fee_bps": fee_bps, "slippage_bps": slippage_bps},
    }
    promotion_assessment = assess_promotion(
        champion,
        final_holdout,
        protocol,
        parameter_sensitivity=sensitivity,
        min_development_trades=min_trades,
        min_holdout_trades=max(5, min_trades // 2),
    )
    promotion_candidate = write_promotion_manifest(
        champion,
        final_holdout,
        protocol,
        promotion_assessment,
        symbol=symbol,
        interval=interval,
    )
    record_experiment(
        {
            "kind": "detector_promotion_assessment",
            "status": promotion_assessment["status"],
            "symbol": symbol,
            "interval": interval,
            "promotion_id": promotion_candidate["promotion_id"],
            "champion_kind": champion.get("kind"),
            "champion_fork_id": champion.get("fork_id"),
            "gates": promotion_assessment["gates"],
            "failed_gates": promotion_assessment["failed_gates"],
            "warnings": promotion_assessment["warnings"],
        }
    )

    return {
        "symbol": symbol,
        "interval": interval,
        "iterations": iterations,
        "protocol": protocol,
        "champion": champion,
        "parameter_sensitivity": sensitivity,
        "purged_embargo_reference": {
            "method": purged_reference.get("method"),
            "aggregate": purged_reference.get("aggregate"),
            "selection_frequency": purged_reference.get("selection_frequency"),
        },
        "evaluations": outcomes,
        "final_holdout": final_holdout,
        "promotion_candidate": promotion_candidate,
    }
