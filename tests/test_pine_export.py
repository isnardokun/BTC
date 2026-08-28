import pytest

from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.pine_export import export_baseline_pine, export_baseline_strategy_pine


def test_pine_export_contains_close_only_resolution_and_frozen_config():
    source = export_baseline_pine(
        PivotConfig(motor="M1", range_mode="R8", min_bars=3, max_pending=5)
    )

    assert source.startswith("//@version=6")
    assert 'const string BQR_MOTOR = "M1"' in source
    assert 'const string BQR_RANGE = "R8"' in source
    assert "const int BQR_MIN_BARS = 3" in source
    assert "const int BQR_MAX_PENDING = 5" in source
    assert "close < pendingBottom" in source
    assert "close > pendingTop" in source
    assert "high < pending" not in source
    assert "low > pending" not in source
    assert "if candidateFound and not pending" in source
    assert "pendingAge >= 5" in source


def test_m3_export_replaces_pending_candidate():
    source = export_baseline_pine(
        PivotConfig(motor="M3", range_mode="R7", min_bars=2, max_pending=0)
    )

    assert "if candidateFound\n" in source
    assert "if pending and not na(pendingBox)" in source
    assert "box.delete(pendingBox)" in source
    assert "bool timedOut = false" in source
    assert "bearCandidate ? high[1]" in source
    assert "bearCandidate ? math.min(open, close) : low[1]" in source


@pytest.mark.parametrize(
    ("range_mode", "expected"),
    [
        ("R4", "candidateTop := math.max(open, close)"),
        ("R7", "candidateTop := bearCandidate ? high[1]"),
        ("R8", "candidateTop := bearCandidate ? math.max(open[1], close[1]) : high"),
    ],
)
def test_each_range_mode_exports_expected_geometry(range_mode: str, expected: str):
    source = export_baseline_pine(PivotConfig(range_mode=range_mode))
    assert expected in source


def test_strategy_export_reverses_only_when_direction_changes():
    source = export_baseline_strategy_pine(
        PivotConfig(motor="M3", range_mode="R8", min_bars=2, max_pending=0)
    )

    assert "strategy(" in source
    assert "process_orders_on_close=true" in source
    assert "commission_value=0" in source
    assert "slippage=0" in source
    assert "if confirmedBear and bqrPositionDir != -1" in source
    assert 'strategy.entry("BQR Short", strategy.short)' in source
    assert "if confirmedBull and bqrPositionDir != 1" in source
    assert 'strategy.entry("BQR Long", strategy.long)' in source
    assert "(close - bqrEntryPrice) / bqrEntryPrice * 100.0" in source
    assert "(bqrEntryPrice - close) / bqrEntryPrice * 100.0" in source


def test_export_rejects_invalid_pending_value():
    cfg = PivotConfig(max_pending=-1)
    with pytest.raises(ValueError, match="max_pending"):
        export_baseline_pine(cfg)
