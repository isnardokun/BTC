import polars as pl
import pytest

from btc_quant_lab.ai import detector_candidate
from btc_quant_lab.ai.process_sandbox import DetectorSandboxError
from btc_quant_lab.models import PivotConfig, PivotSignal


def _market(n: int = 520) -> pl.DataFrame:
    close = [100.0 + i * 0.25 for i in range(n)]
    return pl.DataFrame(
        {
            "ts": [1_700_000_000_000 + i * 86_400_000 for i in range(n)],
            "open": [value - 0.2 for value in close],
            "high": [value + 0.5 for value in close],
            "low": [value - 0.5 for value in close],
            "close": close,
            "volume": [1000.0 + i for i in range(n)],
        }
    )


def _stable_fake_detector(df, _fork_id, config=None, image=None):
    del config, image
    signals = []
    for i in range(120, len(df), 40):
        signals.append(
            PivotSignal(
                ts=int(df["ts"][i]),
                direction=1 if (i // 40) % 2 == 0 else -1,
                top=float(df["high"][i - 1]),
                bottom=float(df["low"][i - 1]),
                candidate_ts=int(df["ts"][i - 1]),
                confirm_price=float(df["close"][i]),
                bars_to_confirm=1,
            )
        )
    return signals


def test_boundary_gap_oos_excludes_boundary_bars(monkeypatch):
    monkeypatch.setattr(detector_candidate, "run_detector_fork", _stable_fake_detector)
    df = _market()
    result = detector_candidate.evaluate_detector_boundary_gap_oos(
        df,
        "fork-a",
        PivotConfig(),
        warmup_bars=220,
        test_bars=60,
        purge_bars=5,
        embargo_bars=7,
        fee_bps=0.0,
        slippage_bps=0.0,
        step_bars=60,
    )

    assert result["method"]["purge_bars"] == 5
    assert result["method"]["embargo_bars"] == 7
    assert result["windows"]
    first = result["windows"][0]["boundary"]
    assert first["pre_boundary_end_index"] == 215
    assert first["anchor_index"] == 220
    assert first["test_start_index"] == 227
    assert result["aggregate"]["windows"] == len(result["windows"])


def test_collect_detector_evidence_requires_prepared_sandbox(monkeypatch):
    monkeypatch.setattr(detector_candidate, "full_detector_sandbox_ready", lambda: False)
    monkeypatch.setattr(detector_candidate, "sandbox_ready", lambda _image: False)
    with pytest.raises(DetectorSandboxError, match="setup_detector_sandbox_arch"):
        detector_candidate.collect_detector_candidate_evidence(
            _market(),
            "fork-a",
            PivotConfig(),
            warmup_bars=220,
            test_bars=60,
            purge_bars=5,
            embargo_bars=5,
            fee_bps=0.0,
            slippage_bps=0.0,
        )
