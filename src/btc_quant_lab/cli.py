import asyncio
import json
import typer
import uvicorn
from rich import print
from btc_quant_lab.config import settings
from btc_quant_lab.service import sync_market
from btc_quant_lab.data.store import Store
from btc_quant_lab.research.optimizer import optimize
from btc_quant_lab.experiments import list_experiments
from btc_quant_lab.ai.agent import propose_iteration

app = typer.Typer(no_args_is_help=True)

@app.command()
def serve(reload: bool = False):
    uvicorn.run("btc_quant_lab.api:app", host=settings.bqr_host, port=settings.bqr_port, reload=reload)

@app.command()
def sync(symbol: str = "BTCUSDT", interval: str = "1d"):
    print(asyncio.run(sync_market(symbol, interval)))

@app.command("optimize")
def optimize_cmd(symbol: str = "BTCUSDT", interval: str = "1d", min_trades: int = 20):
    rows = optimize(Store(settings.bqr_db_path).candles(symbol, interval), min_trades=min_trades)
    print(json.dumps(rows[:15], indent=2))

@app.command("ai-iterate")
def ai_iterate(symbol: str = "BTCUSDT", interval: str = "1d"):
    store = Store(settings.bqr_db_path)
    rows = optimize(store.candles(symbol, interval), min_trades=settings.bqr_ai_min_trades)
    context = {"symbol":symbol,"interval":interval,"top_configurations":rows[:10],"recent_experiments":list_experiments(20)}
    print(asyncio.run(propose_iteration(context)))
