from __future__ import annotations

import operator

import polars as pl

from btc_quant_lab.models import PivotSignal
from btc_quant_lab.research.features import build_feature_rows

ALLOWED_FEATURES = {
    "bars_to_confirm",
    "prior_run_bars",
    "atr_pct",
    "realized_vol20_pct",
    "volume_z20",
    "body_atr",
    "candle_range_atr",
    "signal_range_atr",
    "distance_ema20_pct",
    "distance_ema50_pct",
    "distance_ema200_pct",
    "ema20_vs_ema50_pct",
    "trend_regime",
    "volatility_regime",
}

OPS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


def validate_filter_spec(spec: dict | None) -> dict | None:
    if spec is None:
        return None
    feature = spec.get("feature")
    op = spec.get("operator")
    applies_to = spec.get("applies_to", "all")
    if feature not in ALLOWED_FEATURES:
        raise ValueError(f"feature not allowed: {feature}")
    if op not in OPS:
        raise ValueError(f"operator not allowed: {op}")
    if applies_to not in {"all", "long", "short"}:
        raise ValueError(f"applies_to not allowed: {applies_to}")
    if "value" not in spec:
        raise ValueError("filter value is required")
    return {
        "feature": feature,
        "operator": op,
        "value": spec["value"],
        "applies_to": applies_to,
    }


def _coerce(reference, value):
    if isinstance(reference, (int, float)) and not isinstance(reference, bool):
        return float(value)
    return value


def filter_signals(
    df: pl.DataFrame,
    signals: list[PivotSignal],
    spec: dict | None,
) -> list[PivotSignal]:
    spec = validate_filter_spec(spec)
    if spec is None or not signals:
        return signals

    rows = build_feature_rows(df, signals)
    feature_by_ts = {int(row["ts"]): row for row in rows}
    compare = OPS[spec["operator"]]
    kept: list[PivotSignal] = []

    for signal in signals:
        if spec["applies_to"] == "long" and signal.direction != 1:
            kept.append(signal)
            continue
        if spec["applies_to"] == "short" and signal.direction != -1:
            kept.append(signal)
            continue

        row = feature_by_ts.get(int(signal.ts))
        if row is None:
            continue
        actual = row.get(spec["feature"])
        if actual is None:
            continue
        expected = _coerce(actual, spec["value"])
        try:
            if compare(actual, expected):
                kept.append(signal)
        except (TypeError, ValueError):
            continue

    return kept
