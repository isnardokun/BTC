import polars as pl

from btc_quant_lab.models import PivotSignal, Trade
from btc_quant_lab.research.features import _signal_context
from btc_quant_lab.research.filters import validate_filter_spec
from btc_quant_lab.research.regime_validation import validate_by_regime


def test_signal_context_scores_alignment_and_contradiction():
    context, score = _signal_context(1, "bull", "bull", "bullish_bos")
    assert context == "aligned"
    assert score == 0

    context, score = _signal_context(-1, "bull", "bull", "bullish_bos")
    assert context == "contrarian"
    assert score == 3

    context, score = _signal_context(-1, "bull", "transition", "bearish_bos")
    assert context == "mixed"
    assert score == 1


def test_contradiction_score_is_available_to_filters():
    spec = validate_filter_spec(
        {
            "feature": "trend_contradiction_score",
            "operator": "<=",
            "value": 1,
            "applies_to": "all",
        }
    )
    assert spec["feature"] == "trend_contradiction_score"
    assert spec["value"] == 1


def test_regime_validation_groups_trades_by_entry_context():
    n = 40
    close = [100.0 + (i % 8) * 2.0 + i * 0.2 for i in range(n)]
    df = pl.DataFrame(
        {
            "ts": [1_700_000_000_000 + i * 86_400_000 for i in range(n)],
            "open": [x - 0.5 for x in close],
            "high": [x + 1.0 for x in close],
            "low": [x - 1.0 for x in close],
            "close": close,
            "volume": [1000.0 + i * 10 for i in range(n)],
        }
    )
    ts = df["ts"].to_list()
    signals = [
        PivotSignal(
            ts=ts[20],
            direction=1,
            top=close[20] + 1.0,
            bottom=close[20] - 1.0,
            candidate_ts=ts[19],
            confirm_price=close[20],
            bars_to_confirm=1,
        ),
        PivotSignal(
            ts=ts[25],
            direction=-1,
            top=close[25] + 1.0,
            bottom=close[25] - 1.0,
            candidate_ts=ts[24],
            confirm_price=close[25],
            bars_to_confirm=1,
        ),
        PivotSignal(
            ts=ts[30],
            direction=1,
            top=close[30] + 1.0,
            bottom=close[30] - 1.0,
            candidate_ts=ts[29],
            confirm_price=close[30],
            bars_to_confirm=1,
        ),
    ]
    trades = [
        Trade(
            direction=1,
            entry_ts=ts[20],
            entry=close[20],
            exit_ts=ts[25],
            exit=close[25],
            return_pct=2.0,
        ),
        Trade(
            direction=-1,
            entry_ts=ts[25],
            entry=close[25],
            exit_ts=ts[30],
            exit=close[30],
            return_pct=-1.0,
        ),
    ]

    result = validate_by_regime(
        df,
        signals,
        trades,
        simulations=100,
        min_bootstrap_trades=2,
        block_size=2,
    )

    assert result["matched_trades"] == 2
    assert result["match_rate_pct"] == 100.0
    assert set(result["groups"]) >= {"signal_context", "trend_contradiction_score", "direction"}
    assert sum(
        bucket["metrics"]["trades"]
        for bucket in result["groups"]["direction"].values()
    ) == 2
