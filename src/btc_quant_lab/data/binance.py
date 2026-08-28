import time
import httpx
import polars as pl

_INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


async def fetch_klines(base_url: str, symbol: str = "BTCUSDT", interval: str = "1d", start_ms: int = 0, end_ms: int | None = None) -> pl.DataFrame:
    if interval not in _INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    rows: list[list] = []
    cursor = start_ms or 0
    end_ms = end_ms or int(time.time() * 1000)
    async with httpx.AsyncClient(timeout=30.0) as client:
        while cursor < end_ms:
            params = {"symbol": symbol.upper(), "interval": interval, "limit": 1000, "endTime": end_ms}
            if cursor:
                params["startTime"] = cursor
            r = await client.get(f"{base_url}/api/v3/klines", params=params)
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            rows.extend(batch)
            last_open = int(batch[-1][0])
            next_cursor = last_open + _INTERVAL_MS[interval]
            if next_cursor <= cursor:
                break
            cursor = next_cursor
            if len(batch) < 1000:
                break
    if not rows:
        return pl.DataFrame(schema={"ts": pl.Int64,"open": pl.Float64,"high": pl.Float64,"low": pl.Float64,"close": pl.Float64,"volume": pl.Float64})
    return pl.DataFrame({
        "ts": [int(r[0]) for r in rows],
        "open": [float(r[1]) for r in rows],
        "high": [float(r[2]) for r in rows],
        "low": [float(r[3]) for r in rows],
        "close": [float(r[4]) for r in rows],
        "volume": [float(r[5]) for r in rows],
    }).unique(subset=["ts"]).sort("ts")
