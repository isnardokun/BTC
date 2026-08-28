from pathlib import Path

import duckdb
import polars as pl


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.path))
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS candles (
                symbol VARCHAR,
                interval VARCHAR,
                ts BIGINT,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                PRIMARY KEY(symbol, interval, ts)
            )
            """
        )

    def upsert_candles(self, symbol: str, interval: str, df: pl.DataFrame) -> int:
        if df.is_empty():
            return 0
        tmp = df.with_columns(
            pl.lit(symbol.upper()).alias("symbol"),
            pl.lit(interval).alias("interval"),
        ).select(
            ["symbol", "interval", "ts", "open", "high", "low", "close", "volume"]
        )
        self.con.register("incoming", tmp.to_arrow())
        self.con.execute("INSERT OR REPLACE INTO candles SELECT * FROM incoming")
        return len(tmp)

    def candles(self, symbol: str, interval: str) -> pl.DataFrame:
        return self.con.execute(
            """
            SELECT ts, open, high, low, close, volume FROM candles
            WHERE symbol = ? AND interval = ? ORDER BY ts
            """,
            [symbol.upper(), interval],
        ).pl()

    def last_ts(self, symbol: str, interval: str) -> int | None:
        row = self.con.execute(
            "SELECT max(ts) FROM candles WHERE symbol = ? AND interval = ?",
            [symbol.upper(), interval],
        ).fetchone()
        return row[0] if row and row[0] is not None else None
