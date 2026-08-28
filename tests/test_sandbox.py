import pytest

from btc_quant_lab.ai.sandbox import SandboxPolicyError, compile_signal_policy


def test_sandbox_accepts_simple_signal_policy():
    source = '''
def accept_signal(signal, features):
    if signal["direction"] == -1:
        return features["atr_pct"] > 2 and features["distance_ema50_pct"] > 5
    return features["trend_regime"] != "bull"
'''
    policy = compile_signal_policy(source)
    assert policy(
        {"direction": -1},
        {"atr_pct": 3.0, "distance_ema50_pct": 7.0, "trend_regime": "bear"},
    ) is True


def test_sandbox_rejects_imports():
    source = '''
import os

def accept_signal(signal, features):
    return True
'''
    with pytest.raises(SandboxPolicyError):
        compile_signal_policy(source)


def test_sandbox_rejects_function_calls_and_attributes():
    source = '''
def accept_signal(signal, features):
    return features.get("atr_pct", 0) > 2
'''
    with pytest.raises(SandboxPolicyError):
        compile_signal_policy(source)
