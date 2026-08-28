from btc_quant_lab.config import settings
from btc_quant_lab.data.binance import fetch_klines
from btc_quant_lab.data.store import Store


async def sync_market(symbol: str, interval: str) -> dict:
    store = Store(settings.bqr_db_path)
    last = store.last_ts(symbol, interval)
    # Binance startTime is inclusive; skip one millisecond beyond last stored candle.
    start = last + 1 if last is not None else 0
    df = await fetch_klines(settings.bqr_binance_base_url, symbol=symbol, interval=interval, start_ms=start)
    n = store.upsert_candles(symbol, interval, df)
    return {"inserted": n, "total": len(store.candles(symbol, interval))}
