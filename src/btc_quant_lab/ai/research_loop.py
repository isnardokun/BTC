from __future__ import annotations

import math

import polars as pl

from btc_quant_lab.ai.agent import propose_iteration
from btc_quant_lab.ai.critic import review_candidate
from btc_quant_lab.ai.sandbox import (
    SandboxPolicyError,
    apply_signal_policy,
    evaluate_sandbox_policy,
)
from btc_quant_lab.experiments import list_experiments, record_experiment
from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.analytics import (
    buy_and_hold_benchmark,
    strategy_vs_buy_hold,
    yearly_performance,
)
from btc_quant_lab.research.backtest import reversal_backtest
from btc_quant_lab.research.features import build_feature_rows, summarize_feature_outcomes
from btc_quant_lab.research.filters import filter_signals, validate_filter_spec
from btc_quant_lab.research.montecarlo import bootstrap_trade_paths
from btc_quant_lab.research.optimizer import optimize
from btc_quant_lab.research.pivots import detect_pivots
from btc_quant_lab.research.sensitivity import parameter_sensitivity
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


def _config_dict(cfg: PivotConfig) -> dict:
    return {
        "motor": cfg.motor,
        "range_mode": cfg.range_mode,
        "min_bars": cfg.min_bars,
        "max_pending": cfg.max_pending,
    }


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
    benchmark = buy_and_hold_benchmark(df)
    return {
        "kind": "parameters_or_filter",
        "config": _config_dict(cfg),
        "filter": signal_filter,
        "full_history": full_metrics,
        "out_of_sample": oos,
        "robustness_score": robustness_score(oos["aggregate"], min_trades=min_trades),
        "feature_summary": summarize_feature_outcomes(build_feature_rows(df, signals, trades)),
        "yearly": yearly_performance(trades),
        "benchmark": benchmark,
        "vs_buy_hold": strategy_vs_buy_hold(full_metrics, benchmark),
        "monte_carlo": bootstrap_trade_paths(trades, simulations=1000) if trades else None,
    }


def _evaluate_code_candidate(
    df: pl.DataFrame,
    cfg: PivotConfig,
    source: str,
    warmup_bars: int,
    test_bars: int,
    min_trades: int,
) -> dict:
    signals = detect_pivots(df, cfg)
    signals = apply_signal_policy(df, signals, source)
    trades, full_metrics = reversal_backtest(signals)
    oos = evaluate_sandbox_policy(
        df,
        cfg,
        source,
        warmup_bars=warmup_bars,
        test_bars=test_bars,
        step_bars=test_bars,
    )
    benchmark = buy_and_hold_benchmark(df)
    return {
        "kind": "sandbox_code_policy",
        "config": _config_dict(cfg),
        "filter": None,
        "code_policy": source,
        "full_history": full_metrics,
        "out_of_sample": oos,
        "robustness_score": robustness_score(oos["aggregate"], min_trades=min_trades),
        "feature_summary": summarize_feature_outcomes(build_feature_rows(df, signals, trades)),
        "yearly": yearly_performance(trades),
        "benchmark": benchmark,
        "vs_buy_hold": strategy_vs_buy_hold(full_metrics, benchmark),
        "monte_carlo": bootstrap_trade_paths(trades, simulations=1000) if trades else None,
    }


def _critic_payload(champion: dict, candidate: dict, sensitivity: dict) -> dict:
    def compact(item: dict) -> dict:
        return {
            "kind": item.get("kind"),
            "config": item.get("config"),
            "filter": item.get("filter"),
            "robustness_score": item.get("robustness_score"),
            "full_history": item.get("full_history"),
            "oos_aggregate": item.get("out_of_sample", {}).get("aggregate"),
            "vs_buy_hold": item.get("vs_buy_hold"),
            "monte_carlo": item.get("monte_carlo"),
            "yearly": item.get("yearly"),
        }

    return {
        "champion": compact(champion),
        "candidate": compact(candidate),
        "parameter_sensitivity": sensitivity.get("plateau"),
        "rule": "approve only if evidence suggests a robust improvement, not merely in-sample optimization",
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
    sensitivity = parameter_sensitivity(df, min_trades=min_trades)

    outcomes: list[dict] = []
    for iteration in range(1, iterations + 1):
        context = {
            "symbol": symbol,
            "interval": interval,
            "iteration": iteration,
            "objective": "capturar movimientos sostenidos de BTC con señales de reversión robustas fuera de muestra",
            "current_champion": champion,
            "top_in_sample": ranked[:10],
            "parameter_sensitivity": sensitivity,
            "recent_experiments": list_experiments(30),
            "rules": {
                "no_lookahead": True,
                "candidate_must_beat_champion_out_of_sample": True,
                "minimum_oos_trades": min_trades,
                "critic_must_approve": True,
                "stable_branch_is_immutable": True,
            },
        }
        proposal_exp = await propose_iteration(context)
        proposal = proposal_exp.get("proposal", {})
        proposal_type = proposal.get("proposal_type")

        try:
            raw_params = proposal.get("parameters") or champion["config"]
            cfg = _validate_parameters(raw_params)

            if proposal_type == "code":
                source = proposal.get("code_proposal")
                if not source:
                    raise ValueError("code proposal is empty")
                candidate = _evaluate_code_candidate(
                    df,
                    cfg,
                    source,
                    warmup_bars,
                    test_bars,
                    min_trades,
                )
            else:
                signal_filter = None
                if proposal_type == "filter":
                    signal_filter = validate_filter_spec(proposal.get("filter_proposal"))
                elif proposal_type != "parameters":
                    raise ValueError(f"unsupported proposal_type: {proposal_type}")

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
            score_improved = candidate_score > champion_score

            critic = None
            critic_approved = False
            if score_improved:
                critic = await review_candidate(_critic_payload(champion, candidate, sensitivity))
                critic_approved = critic.get("verdict") == "approve"

            accepted = score_improved and critic_approved
            status = "accepted_candidate" if accepted else "rejected"
            evaluation = record_experiment(
                {
                    "kind": "ai_evaluation",
                    "parent_id": proposal_exp["id"],
                    "status": status,
                    "hypothesis": proposal.get("hypothesis"),
                    "candidate": candidate,
                    "champion_score_before": champion_score,
                    "score_improved": score_improved,
                    "critic": critic,
                    "decision_rule": "OOS robustness must improve and independent critic must approve",
                }
            )
            outcomes.append(evaluation)
            if accepted:
                champion = {**candidate, "source": evaluation["id"]}

        except (TypeError, ValueError, SandboxPolicyError) as exc:
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
        "parameter_sensitivity": sensitivity,
        "evaluations": outcomes,
    }
