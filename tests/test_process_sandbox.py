from pathlib import Path

import polars as pl
import pytest

from btc_quant_lab.ai.process_sandbox import (
    DetectorSandboxError,
    assert_prefix_causal,
    build_podman_command,
    validate_detector_result,
    validate_signals_against_market,
)
from btc_quant_lab.models import PivotSignal


def test_podman_command_disables_network_and_limits_host_access(tmp_path: Path):
    fork = tmp_path / "fork"
    fork.mkdir()
    request = tmp_path / "request.json"
    result = tmp_path / "result.json"
    runner = tmp_path / "runner.py"
    request.write_text("{}", encoding="utf-8")
    result.write_text("{}", encoding="utf-8")
    runner.write_text("pass", encoding="utf-8")

    command = build_podman_command(fork, request, result, runner)
    joined = " ".join(command)

    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--pull=never" in command
    assert "--pids-limit=64" in command
    assert "--memory=512m" in command
    assert "/workspace:ro" in joined
    assert "/input/request.json:ro" in joined
    assert "/output/result.json:rw" in joined
    assert "--volume=/:" not in joined


def test_detector_result_validation_accepts_sorted_signals():
    signals = validate_detector_result(
        {
            "signals": [
                {
                    "ts": 20,
                    "direction": -1,
                    "top": 105.0,
                    "bottom": 100.0,
                    "candidate_ts": 19,
                    "confirm_price": 99.0,
                    "bars_to_confirm": 1,
                },
                {
                    "ts": 30,
                    "direction": 1,
                    "top": 101.0,
                    "bottom": 95.0,
                    "candidate_ts": 29,
                    "confirm_price": 102.0,
                    "bars_to_confirm": 1,
                },
            ]
        }
    )
    assert len(signals) == 2
    assert signals[0].direction == -1
    assert signals[1].direction == 1


def test_detector_result_validation_rejects_future_candidate_timestamp():
    with pytest.raises(DetectorSandboxError, match="candidate_ts"):
        validate_detector_result(
            {
                "signals": [
                    {
                        "ts": 20,
                        "direction": 1,
                        "top": 105.0,
                        "bottom": 100.0,
                        "candidate_ts": 21,
                        "confirm_price": 106.0,
                        "bars_to_confirm": 1,
                    }
                ]
            }
        )


def _market() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ts": [10, 20, 30, 40],
            "open": [99.0, 100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0, 104.0],
            "low": [98.0, 99.0, 100.0, 101.0],
            "close": [100.0, 101.0, 102.0, 103.0],
            "volume": [1.0, 1.0, 1.0, 1.0],
        }
    )


def test_market_validation_requires_real_confirmation_close():
    signal = PivotSignal(
        ts=30,
        direction=1,
        top=103.0,
        bottom=100.0,
        candidate_ts=20,
        confirm_price=999.0,
        bars_to_confirm=1,
    )
    with pytest.raises(DetectorSandboxError, match="confirm_price"):
        validate_signals_against_market(_market(), [signal])


def test_market_validation_checks_bars_to_confirm():
    signal = PivotSignal(
        ts=40,
        direction=-1,
        top=104.0,
        bottom=101.0,
        candidate_ts=20,
        confirm_price=103.0,
        bars_to_confirm=1,
    )
    with pytest.raises(DetectorSandboxError, match="bars_to_confirm"):
        validate_signals_against_market(_market(), [signal])


def test_prefix_causality_rejects_rewritten_past_signal():
    earlier = [
        PivotSignal(
            ts=20,
            direction=1,
            top=102.0,
            bottom=99.0,
            candidate_ts=10,
            confirm_price=101.0,
            bars_to_confirm=1,
        )
    ]
    later = [
        PivotSignal(
            ts=20,
            direction=-1,
            top=102.0,
            bottom=99.0,
            candidate_ts=10,
            confirm_price=101.0,
            bars_to_confirm=1,
        )
    ]
    with pytest.raises(DetectorSandboxError, match="causality audit failed"):
        assert_prefix_causal(earlier, later, earlier_end_ts=20)


def test_prefix_causality_allows_new_future_signals():
    earlier = [
        PivotSignal(
            ts=20,
            direction=1,
            top=102.0,
            bottom=99.0,
            candidate_ts=10,
            confirm_price=101.0,
            bars_to_confirm=1,
        )
    ]
    later = earlier + [
        PivotSignal(
            ts=40,
            direction=-1,
            top=104.0,
            bottom=101.0,
            candidate_ts=30,
            confirm_price=103.0,
            bars_to_confirm=1,
        )
    ]
    assert_prefix_causal(earlier, later, earlier_end_ts=20)
