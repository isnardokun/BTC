from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
from btc_quant_lab.research.backtest import reversal_backtest, trade_dicts
from btc_quant_lab.research.features import build_feature_rows, summarize_feature_outcomes
from btc_quant_lab.research.montecarlo import bootstrap_trade_paths
from btc_quant_lab.research.optimizer import optimize
from btc_quant_lab.research.pivots import detect_pivots
from btc_quant_lab.research.sensitivity import parameter_sensitivity
from btc_quant_lab.research.walkforward import walk_forward
from btc_quant_lab.service import sync_market

app = FastAPI(title="Bitcoin Quant Research Lab")
store = Store(settings.bqr_db_path)
WEB = Path(__file__).parent / "web"


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/sync")
async def sync(symbol: str = "BTCUSDT", interval: str = "1d"):
    return await sync_market(symbol, interval)


def _load(symbol: str, interval: str):
    df = store.candles(symbol, interval)
    if df.is_empty():
        raise HTTPException(404, "No hay datos. Ejecuta sync primero.")
    return df


def _config(motor: str, range_mode: str, min_bars: int, max_pending: int) -> PivotConfig:
    try:
        return PivotConfig(
            motor=motor,
            range_mode=range_mode,
            min_bars=min_bars,
            max_pending=max_pending,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/chart")
def chart(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    motor: str = "M1",
    range_mode: str = "R8",
    min_bars: int = 3,
    max_pending: int = 3,
):
    df = _load(symbol, interval)
    cfg = _config(motor, range_mode, min_bars, max_pending)
    sigs = detect_pivots(df, cfg)
    trades, metrics = reversal_backtest(sigs)

    candles = [
        {
            "time": int(r["ts"] // 1000),
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
        }
        for r in df.iter_rows(named=True)
    ]
    pivots = [
        {
            "time": int(s.ts // 1000),
            "direction": s.direction,
            "top": s.top,
            "bottom": s.bottom,
            "price": s.confirm_price,
            "bars_to_confirm": s.bars_to_confirm,
        }
        for s in sigs
    ]
    return {
        "candles": candles,
        "pivots": pivots,
        "trades": trade_dicts(trades),
        "metrics": metrics,
    }


@app.get("/api/features")
def features(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    motor: str = "M1",
    range_mode: str = "R8",
    min_bars: int = 3,
    max_pending: int = 3,
):
    df = _load(symbol, interval)
    cfg = _config(motor, range_mode, min_bars, max_pending)
    signals = detect_pivots(df, cfg)
    trades, _ = reversal_backtest(signals)
    rows = build_feature_rows(df, signals, trades)
    return {
        "config": {
            "motor": motor,
            "range_mode": range_mode,
            "min_bars": min_bars,
            "max_pending": max_pending,
        },
        "summary": summarize_feature_outcomes(rows),
        "rows": rows,
    }


@app.get("/api/robustness")
def robustness(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    motor: str = "M1",
    range_mode: str = "R8",
    min_bars: int = 3,
    max_pending: int = 3,
    simulations: int = 2000,
):
    df = _load(symbol, interval)
    cfg = _config(motor, range_mode, min_bars, max_pending)
    signals = detect_pivots(df, cfg)
    trades, metrics = reversal_backtest(signals)
    benchmark = buy_and_hold_benchmark(df)
    result = {
        "config": {
            "motor": motor,
            "range_mode": range_mode,
            "min_bars": min_bars,
            "max_pending": max_pending,
        },
        "metrics": metrics,
        "yearly": yearly_performance(trades),
        "benchmark": benchmark,
        "comparison": strategy_vs_buy_hold(metrics, benchmark),
        "sensitivity": parameter_sensitivity(df, min_trades=max(10, min(20, len(trades)))),
        "monte_carlo": bootstrap_trade_paths(trades, simulations=simulations) if trades else None,
    }
    return result


@app.post("/api/optimize")
def run_optimize(symbol: str = "BTCUSDT", interval: str = "1d", min_trades: int = 20):
    df = _load(symbol, interval)
    rows = optimize(df, min_trades=min_trades)
    exp = record_experiment(
        {
            "kind": "optimizer",
            "symbol": symbol,
            "interval": interval,
            "status": "completed",
            "best": rows[0] if rows else None,
        }
    )
    return {"experiment_id": exp["id"], "rows": rows[:25]}


@app.post("/api/walk-forward")
def run_walk_forward(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    train_bars: int = 1095,
    test_bars: int = 365,
    min_train_trades: int = 10,
):
    df = _load(symbol, interval)
    result = walk_forward(
        df,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=test_bars,
        min_train_trades=min_train_trades,
    )
    exp = record_experiment(
        {
            "kind": "walk_forward",
            "symbol": symbol,
            "interval": interval,
            "status": "completed",
            "method": result.get("method"),
            "aggregate": result.get("aggregate"),
            "selection_frequency": result.get("selection_frequency"),
        }
    )
    return {"experiment_id": exp["id"], **result}


@app.get("/api/experiments")
def experiments():
    return list_experiments()


@app.post("/api/ai/iterate")
async def ai_iterate(symbol: str = "BTCUSDT", interval: str = "1d"):
    df = _load(symbol, interval)
    rows = optimize(df, min_trades=settings.bqr_ai_min_trades)
    wf = walk_forward(
        df,
        train_bars=min(1095, max(365, len(df) // 2)),
        test_bars=min(365, max(90, len(df) // 6)),
        min_train_trades=max(5, settings.bqr_ai_min_trades // 2),
    )

    feature_context = None
    if rows:
        best_cfg = PivotConfig(**rows[0]["config"])
        signals = detect_pivots(df, best_cfg)
        trades, _ = reversal_backtest(signals)
        feature_rows = build_feature_rows(df, signals, trades)
        feature_context = summarize_feature_outcomes(feature_rows)

    context = {
        "symbol": symbol,
        "interval": interval,
        "candles": len(df),
        "objective": "capturar movimientos sostenidos de BTC con señales operables de reversión",
        "top_configurations_in_sample": rows[:10],
        "parameter_sensitivity": parameter_sensitivity(
            df, min_trades=max(10, settings.bqr_ai_min_trades // 2)
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
    return await propose_iteration(context)


@app.post("/api/ai/research")
async def ai_research(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    iterations: int = 3,
):
    df = _load(symbol, interval)
    iterations = min(iterations, settings.bqr_ai_max_iterations)
    return await run_autonomous_research(
        df,
        symbol=symbol,
        interval=interval,
        iterations=iterations,
        min_trades=max(10, settings.bqr_ai_min_trades // 2),
    )


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")
