from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PivotConfig:
    motor: Literal["M1", "M3"] = "M1"
    range_mode: Literal["R4", "R7", "R8"] = "R8"
    min_bars: int = 3
    max_pending: int = 3


@dataclass
class PivotSignal:
    ts: int
    direction: int
    top: float
    bottom: float
    candidate_ts: int
    confirm_price: float
    bars_to_confirm: int


@dataclass
class Trade:
    direction: int
    entry_ts: int
    entry: float
    exit_ts: int
    exit: float
    return_pct: float
