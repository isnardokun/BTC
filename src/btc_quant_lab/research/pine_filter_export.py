from __future__ import annotations

from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.filters import validate_filter_spec
from btc_quant_lab.research.pine_export import export_baseline_pine, export_baseline_strategy_pine

_NUMERIC_FEATURES = {
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
    "trend_contradiction_score",
    "bars_since_swing_high",
    "bars_since_swing_low",
    "distance_swing_high_pct",
    "distance_swing_low_pct",
    "distance_swing_high_atr",
    "distance_swing_low_atr",
}

_FEATURE_EXPR = {
    "bars_to_confirm": "confirmedAge",
    "prior_run_bars": "bqrPriorRunBars",
    "atr_pct": "bqrAtrPct",
    "realized_vol20_pct": "bqrRealizedVol20Pct",
    "volume_z20": "bqrVolumeZ20",
    "body_atr": "bqrBodyAtr",
    "candle_range_atr": "bqrCandleRangeAtr",
    "signal_range_atr": "bqrSignalRangeAtr",
    "distance_ema20_pct": "bqrDistanceEma20Pct",
    "distance_ema50_pct": "bqrDistanceEma50Pct",
    "distance_ema200_pct": "bqrDistanceEma200Pct",
    "ema20_vs_ema50_pct": "bqrEma20VsEma50Pct",
    "trend_regime": "bqrTrendRegime",
    "volatility_regime": "bqrVolatilityRegime",
    "last_swing_high_type": "bqrCurrentHighType",
    "last_swing_low_type": "bqrCurrentLowType",
    "market_structure": "bqrMarketStructure",
    "structure_break": "bqrStructureBreak",
    "signal_context": "bqrSignalContext",
    "trend_contradiction_score": "bqrContradictionScore",
    "bars_since_swing_high": "bqrBarsSinceSwingHigh",
    "bars_since_swing_low": "bqrBarsSinceSwingLow",
    "distance_swing_high_pct": "bqrDistanceSwingHighPct",
    "distance_swing_low_pct": "bqrDistanceSwingLowPct",
    "distance_swing_high_atr": "bqrDistanceSwingHighAtr",
    "distance_swing_low_atr": "bqrDistanceSwingLowAtr",
}

_CONTEXT_PREAMBLE = r'''// BQR causal feature state. Mirrors research/features.py.
float bqrAlpha20 = 2.0 / 21.0
float bqrAlpha50 = 2.0 / 51.0
float bqrAlpha200 = 2.0 / 201.0
float bqrAlpha14 = 2.0 / 15.0

var float bqrEma20 = na
var float bqrEma50 = na
var float bqrEma200 = na
var float bqrAtr14 = na

bqrEma20 := bar_index == 0 ? close : bqrAlpha20 * close + (1.0 - bqrAlpha20) * bqrEma20[1]
bqrEma50 := bar_index == 0 ? close : bqrAlpha50 * close + (1.0 - bqrAlpha50) * bqrEma50[1]
bqrEma200 := bar_index == 0 ? close : bqrAlpha200 * close + (1.0 - bqrAlpha200) * bqrEma200[1]

float bqrTr = bar_index == 0 ? high - low : math.max(high - low, math.max(math.abs(high - close[1]), math.abs(low - close[1])))
bqrAtr14 := bar_index == 0 ? bqrTr : bqrAlpha14 * bqrTr + (1.0 - bqrAlpha14) * bqrAtr14[1]
float bqrAtrPct = close != 0 ? bqrAtr14 / close * 100.0 : na

float bqrLogRet = bar_index == 0 ? 0.0 : math.log(close) - math.log(close[1])
float bqrRealizedVol20Pct = bar_index >= 19 ? ta.stdev(bqrLogRet, 20, true) * math.sqrt(365.0) * 100.0 : na
float bqrVolumeMean20 = ta.sma(volume, 20)
float bqrVolumeStd20 = ta.stdev(volume, 20, true)
float bqrVolumeZ20 = bar_index >= 19 and bqrVolumeStd20 > 0 ? (volume - bqrVolumeMean20) / bqrVolumeStd20 : na
float bqrAtrMean100 = ta.sma(bqrAtrPct, 100)

string bqrTrendRegime = close > bqrEma50 and bqrEma50 > bqrEma200 ? "bull" : close < bqrEma50 and bqrEma50 < bqrEma200 ? "bear" : "transition"
string bqrVolatilityRegime = bar_index >= 99 and not na(bqrAtrMean100) ? (bqrAtrPct > bqrAtrMean100 ? "high" : "normal") : "unknown"

var float bqrPreviousSwingHigh = na
var float bqrPreviousSwingLow = na
var float bqrCurrentSwingHigh = na
var float bqrCurrentSwingLow = na
var string bqrCurrentHighType = na
var string bqrCurrentLowType = na
var int bqrCurrentHighIndex = na
var int bqrCurrentLowIndex = na

bool bqrFractalHigh = bar_index >= 4 and high[2] > math.max(high[3], high[4]) and high[2] >= math.max(high[1], high)
bool bqrFractalLow = bar_index >= 4 and low[2] < math.min(low[3], low[4]) and low[2] <= math.min(low[1], low)

if bqrFractalHigh
    float bqrSwingValue = high[2]
    bqrCurrentHighType := na(bqrPreviousSwingHigh) ? "H" : bqrSwingValue > bqrPreviousSwingHigh ? "HH" : bqrSwingValue < bqrPreviousSwingHigh ? "LH" : "EH"
    bqrPreviousSwingHigh := bqrSwingValue
    bqrCurrentSwingHigh := bqrSwingValue
    bqrCurrentHighIndex := bar_index - 2

if bqrFractalLow
    float bqrSwingValue = low[2]
    bqrCurrentLowType := na(bqrPreviousSwingLow) ? "L" : bqrSwingValue > bqrPreviousSwingLow ? "HL" : bqrSwingValue < bqrPreviousSwingLow ? "LL" : "EL"
    bqrPreviousSwingLow := bqrSwingValue
    bqrCurrentSwingLow := bqrSwingValue
    bqrCurrentLowIndex := bar_index - 2

string bqrMarketStructure = bqrCurrentHighType == "HH" and bqrCurrentLowType == "HL" ? "bull" : bqrCurrentHighType == "LH" and bqrCurrentLowType == "LL" ? "bear" : not na(bqrCurrentHighType) and not na(bqrCurrentLowType) ? "transition" : "unknown"
string bqrStructureBreak = not na(bqrCurrentSwingHigh) and close > bqrCurrentSwingHigh ? "bullish_bos" : not na(bqrCurrentSwingLow) and close < bqrCurrentSwingLow ? "bearish_bos" : "none"

int bqrBarsSinceSwingHigh = na(bqrCurrentHighIndex) ? na : bar_index - bqrCurrentHighIndex
int bqrBarsSinceSwingLow = na(bqrCurrentLowIndex) ? na : bar_index - bqrCurrentLowIndex
float bqrDistanceSwingHighPct = na(bqrCurrentSwingHigh) or bqrCurrentSwingHigh == 0 ? na : (close - bqrCurrentSwingHigh) / bqrCurrentSwingHigh * 100.0
float bqrDistanceSwingLowPct = na(bqrCurrentSwingLow) or bqrCurrentSwingLow == 0 ? na : (close - bqrCurrentSwingLow) / bqrCurrentSwingLow * 100.0
float bqrDistanceSwingHighAtr = na(bqrCurrentSwingHigh) or bqrAtr14 <= 0 ? na : (close - bqrCurrentSwingHigh) / bqrAtr14
float bqrDistanceSwingLowAtr = na(bqrCurrentSwingLow) or bqrAtr14 <= 0 ? na : (close - bqrCurrentSwingLow) / bqrAtr14
float bqrDistanceEma20Pct = bqrEma20 == 0 ? na : (close - bqrEma20) / bqrEma20 * 100.0
float bqrDistanceEma50Pct = bqrEma50 == 0 ? na : (close - bqrEma50) / bqrEma50 * 100.0
float bqrDistanceEma200Pct = bqrEma200 == 0 ? na : (close - bqrEma200) / bqrEma200 * 100.0
float bqrEma20VsEma50Pct = bqrEma50 == 0 ? na : (bqrEma20 - bqrEma50) / bqrEma50 * 100.0
float bqrBodyAtr = bqrAtr14 > 0 ? math.abs(close - open) / bqrAtr14 : na
float bqrCandleRangeAtr = bqrAtr14 > 0 ? (high - low) / bqrAtr14 : na

'''


def _literal(feature: str, value) -> str:
    if feature in _NUMERIC_FEATURES:
        return repr(float(value))
    return '"' + str(value).replace('"', "'") + '"'


def _filter_block(spec: dict) -> str:
    feature = spec["feature"]
    expr = _FEATURE_EXPR.get(feature)
    if expr is None:
        raise ValueError(f"feature is not Pine-exportable: {feature}")
    op = spec["operator"]
    expected = _literal(feature, spec["value"])
    availability = f"not na({expr})" if feature not in {
        "trend_regime",
        "volatility_regime",
        "market_structure",
        "structure_break",
        "signal_context",
    } else "true"
    applies = {
        "all": "true",
        "long": "bqrSignalDir == 1",
        "short": "bqrSignalDir == -1",
    }[spec["applies_to"]]

    return f'''// Apply the same post-detector causal filter used by research/filters.py.
bool bqrRawConfirmedBear = confirmedBear
bool bqrRawConfirmedBull = confirmedBull
bool bqrFilterRejectedBear = false
bool bqrFilterRejectedBull = false

if bqrRawConfirmedBear or bqrRawConfirmedBull
    int bqrSignalDir = bqrRawConfirmedBear ? -1 : 1
    int bqrPriorRunBars = bar_index > 0 ? (close[1] > open[1] ? bullRun : close[1] < open[1] ? bearRun : 0) : 0
    float bqrSignalRangeAtr = bqrAtr14 > 0 ? (confirmedTop - confirmedBottom) / bqrAtr14 : na

    int bqrKnownLayers = 0
    int bqrContradictionScore = 0
    if bqrTrendRegime == "bull" or bqrTrendRegime == "bear"
        bqrKnownLayers += 1
        if (bqrSignalDir == 1 and bqrTrendRegime == "bear") or (bqrSignalDir == -1 and bqrTrendRegime == "bull")
            bqrContradictionScore += 1
    if bqrMarketStructure == "bull" or bqrMarketStructure == "bear"
        bqrKnownLayers += 1
        if (bqrSignalDir == 1 and bqrMarketStructure == "bear") or (bqrSignalDir == -1 and bqrMarketStructure == "bull")
            bqrContradictionScore += 1
    if bqrStructureBreak == "bullish_bos" or bqrStructureBreak == "bearish_bos"
        bqrKnownLayers += 1
        if (bqrSignalDir == 1 and bqrStructureBreak == "bearish_bos") or (bqrSignalDir == -1 and bqrStructureBreak == "bullish_bos")
            bqrContradictionScore += 1

    string bqrSignalContext = bqrKnownLayers == 0 ? "unknown" : bqrContradictionScore == 0 ? "aligned" : bqrContradictionScore == bqrKnownLayers ? "contrarian" : "mixed"
    bool bqrFilterApplies = {applies}
    bool bqrFeatureAvailable = {availability}
    bool bqrFilterComparison = bqrFeatureAvailable and ({expr} {op} {expected})
    bool bqrAccepted = not bqrFilterApplies or bqrFilterComparison

    if not bqrAccepted
        bqrFilterRejectedBear := bqrRawConfirmedBear
        bqrFilterRejectedBull := bqrRawConfirmedBull
        confirmedBear := false
        confirmedBull := false

'''


def export_filtered_pine(
    cfg: PivotConfig,
    filter_spec: dict,
    *,
    strategy: bool = False,
    title: str | None = None,
) -> str:
    """Export a baseline detector plus one validated declarative causal filter."""
    spec = validate_filter_spec(filter_spec)
    if spec is None:
        raise ValueError("filter spec is required")

    if strategy:
        source = export_baseline_strategy_pine(
            cfg,
            title=title or "BQR Filtered Reversal Strategy",
        )
        filter_marker = "// Strategy verification layer: opposite confirmation closes/reverses."
    else:
        source = export_baseline_pine(cfg, title=title or "BQR Filtered Pivot")
        filter_marker = "// 2) Detect a new transition using only the prior run and the current candle."

    context_marker = "// 1) Resolve the candidate that already existed before this bar."
    if context_marker not in source or filter_marker not in source:
        raise ValueError("unexpected baseline Pine template")

    source = source.replace(context_marker, _CONTEXT_PREAMBLE + context_marker, 1)
    source = source.replace(filter_marker, _filter_block(spec) + filter_marker, 1)
    source += '''
plotshape(bqrFilterRejectedBear, title="BQR filtro rechazó pivote bajista", style=shape.xcross, location=location.abovebar, color=color.gray, size=size.tiny)
plotshape(bqrFilterRejectedBull, title="BQR filtro rechazó pivote alcista", style=shape.xcross, location=location.belowbar, color=color.gray, size=size.tiny)
'''
    return source
