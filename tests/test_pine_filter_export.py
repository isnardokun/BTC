from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.pine_filter_export import export_filtered_pine


def test_numeric_contradiction_filter_is_exported_after_causal_context():
    source = export_filtered_pine(
        PivotConfig(motor="M3", range_mode="R8", min_bars=2, max_pending=0),
        {
            "feature": "trend_contradiction_score",
            "operator": "<",
            "value": 2,
            "applies_to": "all",
        },
    )

    assert "bqrFractalHigh" in source
    assert 'bqrCurrentHighType := na(bqrPreviousSwingHigh) ? "H"' in source
    assert "int bqrContradictionScore = 0" in source
    assert "bqrContradictionScore < 2.0" in source
    assert "confirmedBear := false" in source
    assert "confirmedBull := false" in source


def test_categorical_filter_preserves_other_direction_when_scoped():
    source = export_filtered_pine(
        PivotConfig(),
        {
            "feature": "market_structure",
            "operator": "!=",
            "value": "bull",
            "applies_to": "short",
        },
    )

    assert "bool bqrFilterApplies = bqrSignalDir == -1" in source
    assert 'bqrMarketStructure != "bull"' in source


def test_filtered_strategy_applies_filter_before_strategy_entries():
    source = export_filtered_pine(
        PivotConfig(),
        {
            "feature": "signal_context",
            "operator": "!=",
            "value": "contrarian",
            "applies_to": "all",
        },
        strategy=True,
    )

    filter_pos = source.index("bool bqrFilterComparison")
    strategy_pos = source.index('strategy.entry("BQR Short", strategy.short)')
    assert filter_pos < strategy_pos
    assert 'bqrSignalContext != "contrarian"' in source
