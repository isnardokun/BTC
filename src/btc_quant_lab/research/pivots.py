import polars as pl
from btc_quant_lab.models import PivotConfig, PivotSignal


def _prior_same_color(opens: list[float], closes: list[float], i: int, bullish: bool) -> int:
    n = 0
    j = i - 1
    while j >= 0:
        ok = closes[j] > opens[j] if bullish else closes[j] < opens[j]
        if not ok:
            break
        n += 1
        j -= 1
    return n


def _bounds(cfg: PivotConfig, bear: bool, i: int, o, h, l, c) -> tuple[float, float]:
    prev_body_top = max(o[i - 1], c[i - 1])
    prev_body_bottom = min(o[i - 1], c[i - 1])
    curr_body_top = max(o[i], c[i])
    curr_body_bottom = min(o[i], c[i])
    if cfg.range_mode == "R4":
        return curr_body_top, curr_body_bottom
    if cfg.range_mode == "R7":
        return (h[i - 1], curr_body_bottom) if bear else (curr_body_top, l[i - 1])
    if cfg.range_mode == "R8":
        return (prev_body_top, l[i]) if bear else (h[i], prev_body_bottom)
    raise ValueError(cfg.range_mode)


def detect_pivots(df: pl.DataFrame, cfg: PivotConfig) -> list[PivotSignal]:
    if len(df) < 3:
        return []
    ts = df["ts"].to_list(); o = df["open"].to_list(); h = df["high"].to_list(); l = df["low"].to_list(); c = df["close"].to_list()
    pending: dict | None = None
    signals: list[PivotSignal] = []

    for i in range(1, len(df)):
        if pending is not None:
            age = i - pending["i"]
            confirmed = c[i] < pending["bottom"] if pending["dir"] == -1 else c[i] > pending["top"]
            invalid = c[i] > pending["top"] if pending["dir"] == -1 else c[i] < pending["bottom"]
            timed_out = cfg.max_pending > 0 and age >= cfg.max_pending
            if confirmed:
                signals.append(PivotSignal(
                    ts=ts[i], direction=pending["dir"], top=pending["top"], bottom=pending["bottom"],
                    candidate_ts=ts[pending["i"]], confirm_price=c[i], bars_to_confirm=age,
                ))
                pending = None
            elif invalid or timed_out:
                pending = None

        prior_bull = _prior_same_color(o, c, i, True)
        prior_bear = _prior_same_color(o, c, i, False)
        bear_candidate = c[i] < o[i] and prior_bull >= cfg.min_bars
        bull_candidate = c[i] > o[i] and prior_bear >= cfg.min_bars

        candidate = None
        if bear_candidate:
            top, bottom = _bounds(cfg, True, i, o, h, l, c)
            candidate = {"dir": -1, "top": top, "bottom": bottom, "i": i}
        elif bull_candidate:
            top, bottom = _bounds(cfg, False, i, o, h, l, c)
            candidate = {"dir": 1, "top": top, "bottom": bottom, "i": i}

        if candidate:
            if cfg.motor == "M3":
                pending = candidate
            elif cfg.motor == "M1" and pending is None:
                pending = candidate

    return signals
