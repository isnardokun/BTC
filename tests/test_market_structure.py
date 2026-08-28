import numpy as np
import polars as pl

from btc_quant_lab.models import PivotSignal
from btc_quant_lab.research.features import _causal_market_structure, build_feature_rows
from btc_quant_lab.research.filters import validate_filter_spec


def test_confirmed_structure_classifies_bull_and_bear_sequences():
    high = np.array([1.0, 3.0, 2.0, 4.0, 3.0, 5.0, 4.0, 4.5, 3.0, 3.5, 2.5])
    low = np.array([0.0, 1.0, 0.5, 2.0, 1.5, 3.0, 2.5, 2.0, 1.0, 1.5, 0.5])
    close = (high + low) / 2.0

    structure = _causal_market_structure(high, low, close, left=1, right=1)

    assert structure["last_swing_high_type"][5] == "HH"
    assert structure["last_swing_low_type"][5] == "HL"
    assert structure["market_structure"][5] == "bull"

    assert structure["last_swing_high_type"][9] == "LH"
    assert structure["last_swing_low_type"][9] == "LL"
    assert structure["market_structure"][9] == "bear"


def _frame(future_multiplier: float) -> pl.DataFrame:
    close = [
        100.0,
        102.0,
        101.0,
        104.0,
        103.0,
        106.0,
        104.0,
        107.0,
        105.0,
        108.0,
        106.0,
        109.0,
        107.0,
        110.0,
    ]
    open_ = [x - 0.5 for x in close]
    high = [x + 1.0 for x in close]
    low = [x - 1.0 for x in close]

    for i in range(10, len(close)):
        close[i] *= future_multiplier
        open_[i] *= future_multiplier
        high[i] *= future_multiplier
        low[i] *= future_multiplier

    return pl.DataFrame(
        {
            "ts": [1_700_000_000_000 + i * 86_400_000 for i in range(len(close))],
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": [1000.0 + i for i in range(len(close))],
        }
    )


def test_market_structure_features_do_not_change_when_future_candles_change():
    base = _frame(1.0)
    altered_future = _frame(2.0)
    ts = int(base["ts"][8])
    price = float(base["close"][8])
    signal = PivotSignal(
        ts=ts,
        direction=-1,
        top=price + 2,
        bottom=price - 2,
        candidate_ts=int(base["ts"][7]),
        confirm_price=price,
        bars_to_confirm=1,
    )

    row_a = build_feature_rows(base, [signal])[0]
    row_b = build_feature_rows(altered_future, [signal])[0]
    causal_keys = {
        "last_swing_high_type",
        "last_swing_low_type",
        "market_structure",
        "structure_break",
        "bars_since_swing_high",
        "bars_since_swing_low",
        "distance_swing_high_pct",
        "distance_swing_low_pct",
        "distance_swing_high_atr",
        "distance_swing_low_atr",
    }

    for key in causal_keys:
        assert row_a[key] == row_b[key]


def test_market_structure_features_are_available_to_experimental_filters():
    spec = validate_filter_spec(
        {
            "feature": "market_structure",
            "operator": "!=",
            "value": "bull",
            "applies_to": "short",
        }
    )
    assert spec["feature"] == "market_structure"
