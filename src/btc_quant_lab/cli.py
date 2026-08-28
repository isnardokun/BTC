import asyncio
import json

import typer
import uvicorn
from rich import print

from btc_quant_lab.ai.agent import propose_iteration
from btc_quant_lab.ai.research_loop import run_autonomous_research
from btc_quant_lab.config import settings
from btc_quant_lab.data.store import Store
from btc_quant_lab.experiments import list_experiments, record_experiment
from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.analytics import (
    buy_and_hold_benchmark,
    strategy_vs_buy_hold,
    yearly_performance,
)
from btc_quant_lab.research.backtest import reversal_backtest
from btc_quant_lab.research.features import build_feature_rows, summarize_feature_outcomes
from btc_quant_lab.research.montecarlo import bootstrap_trade_paths
from btc_quant_lab.research.optimizer import optimize
from btc_quant_lab.research.pivots import detect_pivots
from btc_quant_lab.research.sensitivity import parameter_sensitivity
from btc_quant_lab.research.walkforward import walk_forward
from btc_quant_lab.service import sync_market

app = typer.Typer(no_args_is_help=True)


def _costs() -> dict:
    return {"fee_bps": settings.bqr_fee_bps, "slippage_bps": settings.bqr_slippage_bps}


@app.command()
def serve(reload: bool = False):
    uvicorn.run(
        "btc_quant_lab.api:app",
        host=settings.bqr_host,
        port=settings.bqr_port,
        reload=reload,
    )


@app.command()
def sync(symbol: str = "BTCUSDT", interval: str = "1d"):
    print(asyncio.run(sync_market(symbol, interval)))


@app.command("optimize")
def optimize_cmd(symbol: str = "BTCUSDT", interval: str = "1d", min_trades: int = 20):
    rows = optimize(
        Store(settings.bqr_db_path).candles(symbol, interval),
        min_trades=min_trades,
        fee_bps=settings.bqr_fee_bps,
        slippage_bps=settings.bqr_slippage_bps,
    )
    print(json.dumps({"cost_model": _costs(), "rows": rows[:15]}, indent=2))


@app.command("walk-forward")
def walk_forward_cmd(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    train_bars: int = 1095,
    test_bars: int = 365,
    min_train_trades: int = 10,
):
    df = Store(settings.bqr_db_path).candles(symbol, interval)
    result = walk_forward(
        df,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=test_bars,
        min_train_trades=min_train_trades,
        fee_bps=settings.bqr_fee_bps,
        slippage_bps=settings.bqr_slippage_bps,
    )
    record_experiment(
        {
            "kind": "walk_forward_cli",
            "symbol": symbol,
            "interval": interval,
            "status": "completed",
            "method": result.get("method"),
            "aggregate": result.get("aggregate"),
            "selection_frequency": result.get("selection_frequency"),
        }
    )
    print(json.dumps(result, indent=2))


@app.command("features")
def features_cmd(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    motor: str = "M1",
    range_mode: str = "R8",
    min_bars: int = 3,
    max_pending: int = 3,
):
    df = Store(settings.bqr_db_path).candles(symbol, interval)
    cfg = PivotConfig(
        motor=motor,
        range_mode=range_mode,
        min_bars=min_bars,
        max_pending=max_pending,
    )
    signals = detect_pivots(df, cfg)
    trades, _ = reversal_backtest(
        signals,
        fee_bps=settings.bqr_fee_bps,
        slippage_bps=settings.bqr_slippage_bps,
    )
    rows = build_feature_rows(df, signals, trades)
    print(json.dumps({"cost_model": _costs(), "summary": summarize_feature_outcomes(rows), "rows": rows}, indent=2))


@app.command("robustness")
def robustness_cmd(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    motor: str = "M1",
    range_mode: str = "R8",
    min_bars: int = 3,
    max_pending: int = 3,
    simulations: int = 2000,
):
    df = Store(settings.bqr_db_path).candles(symbol, interval)
    cfg = PivotConfig(
        motor=motor,
        range_mode=range_mode,
        min_bars=min_bars,
        max_pending=max_pending,
    )
    signals = detect_pivots(df, cfg)
    trades, metrics = reversal_backtest(
        signals,
        fee_bps=settings.bqr_fee_bps,
        slippage_bps=settings.bqr_slippage_bps,
    )
    benchmark = buy_and_hold_benchmark(df)
    result = {
        "config": {
            "motor": motor,
            "range_mode": range_mode,
            "min_bars": min_bars,
            "max_pending": max_pending,
        },
        "cost_model": _costs(),
        "metrics": metrics,
        "yearly": yearly_performance(trades),
        "benchmark": benchmark,
        "comparison": strategy_vs_buy_hold(metrics, benchmark),
        "sensitivity": parameter_sensitivity(
            df,
            min_trades=max(10, min(20, len(trades))),
            fee_bps=settings.bqr_fee_bps,
            slippage_bps=settings.bqr_slippage_bps,
        ),
        "monte_carlo": bootstrap_trade_paths(trades, simulations=simulations) if trades else None,
    }
    print(json.dumps(result, indent=2))


@app.command("ai-iterate")
def ai_iterate(symbol: str = "BTCUSDT", interval: str = "1d"):
    store = Store(settings.bqr_db_path)
    df = store.candles(symbol, interval)
    rows = optimize(
        df,
        min_trades=settings.bqr_ai_min_trades,
        fee_bps=settings.bqr_fee_bps,
        slippage_bps=settings.bqr_slippage_bps,
    )
    wf = walk_forward(
        df,
        train_bars=min(1095, max(365, len(df) // 2)),
        test_bars=min(365, max(90, len(df) // 6)),
        min_train_trades=max(5, settings.bqr_ai_min_trades // 2),
        fee_bps=settings.bqr_fee_bps,
        slippage_bps=settings.bqr_slippage_bps,
    )

    feature_context = None
    if rows:
        cfg = PivotConfig(**rows[0]["config"])
        signals = detect_pivots(df, cfg)
        trades, _ = reversal_backtest(
            signals,
            fee_bps=settings.bqr_fee_bps,
            slippage_bps=settings.bqr_slippage_bps,
        )
        feature_context = summarize_feature_outcomes(build_feature_rows(df, signals, trades))

    context = {
        "symbol": symbol,
        "interval": interval,
        "candles": len(df),
        "cost_model": _costs(),
        "top_configurations_in_sample": rows[:10],
        "parameter_sensitivity": parameter_sensitivity(
            df,
            min_trades=max(10, settings.bqr_ai_min_trades // 2),
            fee_bps=settings.bqr_fee_bps,
            slippage_bps=settings.bqr_slippage_bps,
        ),
        "walk_forward": {
            "method": wf.get("method"),
            "aggregate": wf.get("aggregate"),
            "selection_frequency": wf.get("selection_frequency"),
            "windows": wf.get("windows", [])[-5:],
        },
        "feature_outcomes_for_current_best": feature_context,
        "recent_experiments": list_experiments(20),
    }
    print(asyncio.run(propose_iteration(context)))


@app.command("ai-research")
def ai_research(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    iterations: int = 3,
):
    df = Store(settings.bqr_db_path).candles(symbol, interval)
    iterations = min(iterations, settings.bqr_ai_max_iterations)
    result = asyncio.run(
        run_autonomous_research(
            df,
            symbol=symbol,
            interval=interval,
            iterations=iterations,
            min_trades=max(10, settings.bqr_ai_min_trades // 2),
            fee_bps=settings.bqr_fee_bps,
            slippage_bps=settings.bqr_slippage_bps,
        )
    )
    print(json.dumps(result, indent=2))
