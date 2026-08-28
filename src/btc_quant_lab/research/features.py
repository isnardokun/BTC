from __future__ import annotations

import math

import numpy as np
import polars as pl

from btc_quant_lab.models import PivotSignal, Trade


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=float)
    if len(values) == 0:
        return out
    alpha = 2.0 / (period + 1.0)
    out[0] = values[0]
    for i in range(1, len(values)):
        out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]
    return out


def _rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=float)
    csum = np.cumsum(np.insert(values.astype(float), 0, 0.0))
    for i in range(window - 1, len(values)):
        out[i] = (csum[i + 1] - csum[i + 1 - window]) / window
    return out


def _rolling_std(values: np.ndarray, window: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=float)
    for i in range(window - 1, len(values)):
        out[i] = float(np.std(values[i + 1 - window : i + 1], ddof=0))
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    tr = np.zeros(len(close), dtype=float)
    if len(close) == 0:
        return tr
    tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    return _ema(tr, period)


def _prior_run(open_: np.ndarray, close: np.ndarray, i: int) -> int:
    if i <= 0:
        return 0
    bullish = close[i - 1] > open_[i - 1]
    n = 0
    j = i - 1
    while j >= 0:
        same = (close[j] > open_[j]) == bullish and close[j] != open_[j]
        if not same:
            break
        n += 1
        j -= 1
    return n


def _safe_pct(num: float, den: float) -> float | None:
    if den == 0 or math.isnan(den):
        return None
    return float(num / den * 100.0)


def build_feature_rows(
    df: pl.DataFrame,
    signals: list[PivotSignal],
    trades: list[Trade] | None = None,
) -> list[dict]:
    """Build causal features at each signal confirmation.

    Every feature uses candles at or before the confirmation timestamp. Trade return,
    when supplied, is a label for research and must never be used as an input feature.
    """
    if df.is_empty() or not signals:
        return []

    ts = np.array(df["ts"].to_list(), dtype=np.int64)
    open_ = np.array(df["open"].to_list(), dtype=float)
    high = np.array(df["high"].to_list(), dtype=float)
    low = np.array(df["low"].to_list(), dtype=float)
    close = np.array(df["close"].to_list(), dtype=float)
    volume = np.array(df["volume"].to_list(), dtype=float)

    ema20 = _ema(close, 20)
    ema50 = _ema(close, 50)
    ema200 = _ema(close, 200)
    atr14 = _atr(high, low, close, 14)
    atr_pct = np.divide(atr14, close, out=np.zeros_like(atr14), where=close != 0) * 100.0

    log_ret = np.zeros(len(close), dtype=float)
    if len(close) > 1:
        log_ret[1:] = np.diff(np.log(close))
    vol20 = _rolling_std(log_ret, 20) * math.sqrt(365.0) * 100.0
    vol_mean20 = _rolling_mean(volume, 20)
    vol_std20 = _rolling_std(volume, 20)
    atr_mean100 = _rolling_mean(atr_pct, 100)

    trade_by_entry = {t.entry_ts: t.return_pct for t in (trades or [])}
    index_by_ts = {int(v): i for i, v in enumerate(ts)}

    rows: list[dict] = []
    for sig in signals:
        i = index_by_ts.get(int(sig.ts))
        if i is None:
            continue

        if close[i] > ema50[i] > ema200[i]:
            trend_regime = "bull"
        elif close[i] < ema50[i] < ema200[i]:
            trend_regime = "bear"
        else:
            trend_regime = "transition"

        if i >= 99 and not np.isnan(atr_mean100[i]):
            volatility_regime = "high" if atr_pct[i] > atr_mean100[i] else "normal"
        else:
            volatility_regime = "unknown"

        volume_z = None
        if i >= 19 and not np.isnan(vol_std20[i]) and vol_std20[i] > 0:
            volume_z = float((volume[i] - vol_mean20[i]) / vol_std20[i])

        body = abs(close[i] - open_[i])
        candle_range = high[i] - low[i]
        signal_range = sig.top - sig.bottom

        rows.append(
            {
                "ts": int(sig.ts),
                "direction": int(sig.direction),
                "confirm_price": float(sig.confirm_price),
                "bars_to_confirm": int(sig.bars_to_confirm),
                "prior_run_bars": _prior_run(open_, close, i),
                "atr14": float(atr14[i]),
                "atr_pct": float(atr_pct[i]),
                "realized_vol20_pct": None if np.isnan(vol20[i]) else float(vol20[i]),
                "volume_z20": volume_z,
                "body_atr": float(body / atr14[i]) if atr14[i] > 0 else None,
                "candle_range_atr": float(candle_range / atr14[i]) if atr14[i] > 0 else None,
                "signal_range_atr": float(signal_range / atr14[i]) if atr14[i] > 0 else None,
                "distance_ema20_pct": _safe_pct(close[i] - ema20[i], ema20[i]),
                "distance_ema50_pct": _safe_pct(close[i] - ema50[i], ema50[i]),
                "distance_ema200_pct": _safe_pct(close[i] - ema200[i], ema200[i]),
                "ema20_vs_ema50_pct": _safe_pct(ema20[i] - ema50[i], ema50[i]),
                "trend_regime": trend_regime,
                "volatility_regime": volatility_regime,
                "trade_return_pct": trade_by_entry.get(int(sig.ts)),
            }
        )

    return rows


def summarize_feature_outcomes(rows: list[dict]) -> dict:
    labeled = [r for r in rows if r.get("trade_return_pct") is not None]
    if not labeled:
        return {"labeled_signals": 0, "by_trend_regime": {}, "by_volatility_regime": {}}

    def group(key: str) -> dict:
        result: dict[str, dict] = {}
        for row in labeled:
            name = str(row[key])
            bucket = result.setdefault(name, {"trades": 0, "wins": 0, "return_sum": 0.0})
            ret = float(row["trade_return_pct"])
            bucket["trades"] += 1
            bucket["wins"] += int(ret > 0)
            bucket["return_sum"] += ret
        for bucket in result.values():
            n = bucket["trades"]
            bucket["win_rate"] = bucket["wins"] * 100.0 / n
            bucket["expectancy_pct"] = bucket["return_sum"] / n
        return result

    return {
        "labeled_signals": len(labeled),
        "by_trend_regime": group("trend_regime"),
        "by_volatility_regime": group("volatility_regime"),
    }
