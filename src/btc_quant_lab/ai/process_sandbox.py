from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path

import polars as pl

from btc_quant_lab.models import PivotConfig, PivotSignal
from btc_quant_lab.research.backtest import reversal_backtest

FORKS_ROOT = Path("experiments/forks")
DEFAULT_IMAGE = "docker.io/library/python:3.12-slim"
FORK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class DetectorSandboxError(RuntimeError):
    pass


def _fork_directory(fork_id: str) -> Path:
    if not FORK_ID_RE.fullmatch(fork_id):
        raise DetectorSandboxError("invalid fork id")
    root = FORKS_ROOT.resolve()
    directory = (root / fork_id).resolve()
    if root not in directory.parents:
        raise DetectorSandboxError("fork path escapes experiments/forks")
    if not directory.is_dir():
        raise DetectorSandboxError(f"fork does not exist: {fork_id}")
    variant = directory / "detector_variant.py"
    if not variant.is_file():
        raise DetectorSandboxError("fork must contain detector_variant.py")
    return directory


def podman_available() -> bool:
    return shutil.which("podman") is not None


def build_podman_command(
    fork_directory: Path,
    request_path: Path,
    result_path: Path,
    runner_path: Path,
    image: str = DEFAULT_IMAGE,
    memory_mb: int = 512,
    cpus: float = 1.0,
    pids_limit: int = 64,
) -> list[str]:
    if memory_mb < 128 or memory_mb > 4096:
        raise ValueError("memory_mb must be between 128 and 4096")
    if cpus <= 0 or cpus > 4:
        raise ValueError("cpus must be > 0 and <= 4")
    if pids_limit < 16 or pids_limit > 512:
        raise ValueError("pids_limit must be between 16 and 512")

    return [
        "podman",
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--userns=keep-id",
        f"--memory={memory_mb}m",
        f"--cpus={cpus}",
        f"--pids-limit={pids_limit}",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        f"--volume={fork_directory.resolve()}:/workspace:ro",
        f"--volume={request_path.resolve()}:/input/request.json:ro",
        f"--volume={result_path.resolve()}:/output/result.json:rw",
        f"--volume={runner_path.resolve()}:/runner.py:ro",
        "--workdir=/workspace",
        image,
        "python",
        "/runner.py",
    ]


def _candles_payload(df: pl.DataFrame) -> list[dict]:
    required = ["ts", "open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise DetectorSandboxError(f"market data missing columns: {missing}")
    if len(df) > 100_000:
        raise DetectorSandboxError("sandbox input exceeds 100000 candles")
    return [
        {
            "ts": int(row["ts"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for row in df.select(required).iter_rows(named=True)
    ]


def validate_detector_result(payload: dict) -> list[PivotSignal]:
    raw = payload.get("signals")
    if not isinstance(raw, list):
        raise DetectorSandboxError("sandbox output must contain a signals list")
    if len(raw) > 100_000:
        raise DetectorSandboxError("sandbox returned too many signals")

    signals: list[PivotSignal] = []
    previous_ts = -1
    for item in raw:
        if not isinstance(item, dict):
            raise DetectorSandboxError("every sandbox signal must be a dict")
        try:
            signal = PivotSignal(
                ts=int(item["ts"]),
                direction=int(item["direction"]),
                top=float(item["top"]),
                bottom=float(item["bottom"]),
                candidate_ts=int(item["candidate_ts"]),
                confirm_price=float(item["confirm_price"]),
                bars_to_confirm=int(item["bars_to_confirm"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DetectorSandboxError(f"invalid sandbox signal: {exc}") from exc

        if signal.direction not in {-1, 1}:
            raise DetectorSandboxError("direction must be -1 or 1")
        if signal.top < signal.bottom:
            raise DetectorSandboxError("signal top cannot be below bottom")
        if signal.candidate_ts > signal.ts:
            raise DetectorSandboxError("candidate_ts cannot be after confirmation ts")
        if signal.ts < previous_ts:
            raise DetectorSandboxError("signals must be sorted by ts")
        previous_ts = signal.ts
        signals.append(signal)
    return signals


def run_detector_fork(
    df: pl.DataFrame,
    fork_id: str,
    config: PivotConfig | dict | None = None,
    image: str = DEFAULT_IMAGE,
    timeout_seconds: int = 30,
    memory_mb: int = 512,
    cpus: float = 1.0,
) -> list[PivotSignal]:
    """Run a full detector fork inside a networkless rootless Podman container.

    The trusted container image must already exist locally. The function uses
    `--pull=never`, so executing an AI fork never triggers a network image pull.
    """
    if not podman_available():
        raise DetectorSandboxError("podman is required for full detector sandbox execution")
    if timeout_seconds < 1 or timeout_seconds > 300:
        raise ValueError("timeout_seconds must be between 1 and 300")

    fork_directory = _fork_directory(fork_id)
    runner_path = Path(__file__).with_name("detector_runner.py").resolve()
    cfg = asdict(config) if isinstance(config, PivotConfig) else (config or {})
    request = {"candles": _candles_payload(df), "config": cfg}

    with tempfile.TemporaryDirectory(prefix="bqrl-detector-") as tmp:
        tmp_path = Path(tmp)
        request_path = tmp_path / "request.json"
        result_path = tmp_path / "result.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        result_path.write_text("{}", encoding="utf-8")

        command = build_podman_command(
            fork_directory,
            request_path,
            result_path,
            runner_path,
            image=image,
            memory_mb=memory_mb,
            cpus=cpus,
        )
        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv, no shell; container is the security boundary
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise DetectorSandboxError("detector sandbox timed out") from exc

        if completed.returncode != 0:
            stderr = completed.stderr[-4000:]
            raise DetectorSandboxError(
                f"detector sandbox failed with code {completed.returncode}: {stderr}"
            )
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DetectorSandboxError("detector sandbox returned invalid JSON") from exc
        return validate_detector_result(payload)


def evaluate_detector_fork(
    df: pl.DataFrame,
    fork_id: str,
    config: PivotConfig | dict | None = None,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
    **sandbox_kwargs,
) -> dict:
    signals = run_detector_fork(
        df,
        fork_id,
        config=config,
        **sandbox_kwargs,
    )
    trades, metrics = reversal_backtest(
        signals,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    return {
        "fork_id": fork_id,
        "signals": len(signals),
        "trades": len(trades),
        "metrics": metrics,
    }
