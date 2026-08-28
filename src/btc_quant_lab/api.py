from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from btc_quant_lab.config import settings
from btc_quant_lab.data.store import Store
from btc_quant_lab.service import sync_market
from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.pivots import detect_pivots
from btc_quant_lab.research.backtest import reversal_backtest, trade_dicts
from btc_quant_lab.research.optimizer import optimize
from btc_quant_lab.experiments import list_experiments, record_experiment
from btc_quant_lab.ai.agent import propose_iteration

app = FastAPI(title="Bitcoin Quant Research Lab")
store = Store(settings.bqr_db_path)
WEB = Path(__file__).parent / "web"

@app.get("/api/health")
def health(): return {"ok": True}

@app.post("/api/sync")
async def sync(symbol: str = "BTCUSDT", interval: str = "1d"):
    return await sync_market(symbol, interval)

@app.get("/api/chart")
def chart(symbol: str = "BTCUSDT", interval: str = "1d", motor: str = "M1", range_mode: str = "R8", min_bars: int = 3, max_pending: int = 3):
    df = store.candles(symbol, interval)
    if df.is_empty(): raise HTTPException(404, "No hay datos. Ejecuta sync primero.")
    cfg = PivotConfig(motor=motor, range_mode=range_mode, min_bars=min_bars, max_pending=max_pending)
    sigs = detect_pivots(df, cfg)
    trades, metrics = reversal_backtest(sigs)
    candles = [{"time": int(r["ts"] // 1000), "open": r["open"], "high": r["high"], "low": r["low"], "close": r["close"]} for r in df.iter_rows(named=True)]
    pivots = [{"time": int(s.ts // 1000), "direction": s.direction, "top": s.top, "bottom": s.bottom, "price": s.confirm_price, "bars_to_confirm": s.bars_to_confirm} for s in sigs]
    return {"candles": candles, "pivots": pivots, "trades": trade_dicts(trades), "metrics": metrics}

@app.post("/api/optimize")
def run_optimize(symbol: str = "BTCUSDT", interval: str = "1d", min_trades: int = 20):
    df = store.candles(symbol, interval)
    if df.is_empty(): raise HTTPException(404, "No hay datos.")
    rows = optimize(df, min_trades=min_trades)
    exp = record_experiment({"kind":"optimizer","symbol":symbol,"interval":interval,"status":"completed","best":rows[0] if rows else None})
    return {"experiment_id": exp["id"], "rows": rows[:25]}

@app.get("/api/experiments")
def experiments(): return list_experiments()

@app.post("/api/ai/iterate")
async def ai_iterate(symbol: str = "BTCUSDT", interval: str = "1d"):
    df = store.candles(symbol, interval)
    if df.is_empty(): raise HTTPException(404, "No hay datos.")
    rows = optimize(df, min_trades=settings.bqr_ai_min_trades)
    context = {"symbol":symbol,"interval":interval,"candles":len(df),"top_configurations":rows[:10],"recent_experiments":list_experiments(20),"objective":"capturar movimientos sostenidos de BTC con señales operables de reversión"}
    return await propose_iteration(context)

@app.get("/")
def index(): return FileResponse(WEB / "index.html")

app.mount("/static", StaticFiles(directory=WEB), name="static")
