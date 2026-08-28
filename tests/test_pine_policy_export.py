import pytest

from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.pine_policy_export import (
    PinePolicyExportError,
    compile_policy_to_pine_expression,
    export_policy_pine,
)


def test_policy_if_return_translates_to_pine_ternary():
    policy = '''
def accept_signal(signal, features):
    if signal["direction"] == -1:
        return features["trend_contradiction_score"] < 2
    return features["market_structure"] != "bear"
'''
    expression = compile_policy_to_pine_expression(policy)

    assert "bqrSignalDir == -1.0" in expression
    assert "bqrContradictionScore < 2.0" in expression
    assert 'bqrMarketStructure != "bear"' in expression
    assert "?" in expression


def test_policy_membership_translates_without_runtime_calls():
    policy = '''
def accept_signal(signal, features):
    return features["signal_context"] in ["aligned", "mixed"]
'''
    expression = compile_policy_to_pine_expression(policy)
    assert 'bqrSignalContext == "aligned"' in expression
    assert 'bqrSignalContext == "mixed"' in expression
    assert " or " in expression


def test_policy_export_filters_before_strategy_entry():
    policy = '''
def accept_signal(signal, features):
    return features["trend_regime"] != "transition"
'''
    source = export_policy_pine(PivotConfig(), policy, strategy=True)
    assert source.index("bool bqrPolicyAccepted") < source.index(
        'strategy.entry("BQR Short", strategy.short)'
    )
    assert 'bqrTrendRegime != "transition"' in source


def test_policy_export_rejects_local_assignments_for_now():
    policy = '''
def accept_signal(signal, features):
    threshold = 2
    return features["trend_contradiction_score"] < threshold
'''
    with pytest.raises(PinePolicyExportError, match="local assignments"):
        compile_policy_to_pine_expression(policy)


def test_policy_export_rejects_timestamp_fields():
    policy = '''
def accept_signal(signal, features):
    return signal["ts"] > 0
'''
    with pytest.raises(PinePolicyExportError, match="signal field"):
        compile_policy_to_pine_expression(policy)
