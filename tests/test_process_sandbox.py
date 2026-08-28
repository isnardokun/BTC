from pathlib import Path

import pytest

from btc_quant_lab.ai.process_sandbox import (
    DetectorSandboxError,
    build_podman_command,
    validate_detector_result,
)


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
