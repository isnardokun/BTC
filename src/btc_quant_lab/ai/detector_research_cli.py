from __future__ import annotations

import asyncio
import json

import typer

from btc_quant_lab.ai.detector_research_loop import run_autonomous_detector_research
from btc_quant_lab.config import settings
from btc_quant_lab.data.store import Store


def main(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    iterations: int = 3,
    min_trades: int = 10,
):
    """Run autonomous full-detector research inside the prepared Podman sandbox."""
    df = Store(settings.bqr_db_path).candles(symbol, interval)
    result = asyncio.run(
        run_autonomous_detector_research(
            df,
            symbol=symbol,
            interval=interval,
            iterations=iterations,
            min_trades=min_trades,
            fee_bps=settings.bqr_fee_bps,
            slippage_bps=settings.bqr_slippage_bps,
        )
    )
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


def app():
    typer.run(main)
