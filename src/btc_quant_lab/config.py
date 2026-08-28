from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bqr_host: str = "127.0.0.1"
    bqr_port: int = 8765
    bqr_db_path: Path = Path("data/research.duckdb")
    bqr_binance_base_url: str = "https://api.binance.com"
    bqr_default_symbol: str = "BTCUSDT"
    bqr_default_interval: str = "1d"

    # Execution-cost model. Zero keeps legacy comparisons unchanged.
    bqr_fee_bps: float = 0.0
    bqr_slippage_bps: float = 0.0

    minimax_api_key: str | None = None
    minimax_model: str = "MiniMax-M2.5"
    minimax_base_url: str = "https://api.minimax.io/v1/text/chatcompletion_v2"

    bqr_ai_allow_code_forks: bool = True
    bqr_ai_max_iterations: int = 10
    bqr_ai_min_trades: int = 30


settings = Settings()
