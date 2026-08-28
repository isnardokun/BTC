import polars as pl
from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.pivots import detect_pivots


def test_detector_runs():
    df = pl.DataFrame({
        "ts": list(range(12)),
        "open": [1,2,3,4,5,4,3,2,1,2,3,4],
        "high": [2,3,4,5,6,5,4,3,2,3,4,5],
        "low": [0,1,2,3,4,3,2,1,0,1,2,3],
        "close": [2,3,4,5,4,3,2,1,2,3,4,3],
        "volume": [1]*12,
    })
    sigs = detect_pivots(df, PivotConfig(motor="M1", range_mode="R4", min_bars=2, max_pending=3))
    assert isinstance(sigs, list)
