import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

LEDGER = Path("experiments/ledger.jsonl")
FORKS = Path("experiments/forks")
ALLOWED_CODE_FILENAMES = {"strategy_variant.py", "detector_variant.py"}


def record_experiment(payload: dict) -> dict:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": payload.get("id") or uuid.uuid4().hex[:12],
        "created_at": datetime.now(UTC).isoformat(),
        **payload,
    }
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def list_experiments(limit: int = 100) -> list[dict]:
    if not LEDGER.exists():
        return []
    rows = [
        json.loads(line)
        for line in LEDGER.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return rows[-limit:][::-1]


def create_fork(
    experiment: dict,
    hypothesis: str,
    code_proposal: str | None = None,
    code_filename: str = "strategy_variant.py",
) -> Path:
    if code_filename not in ALLOWED_CODE_FILENAMES:
        raise ValueError(f"unsupported fork code filename: {code_filename}")

    directory = FORKS / experiment["id"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(
        json.dumps(experiment, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (directory / "hypothesis.md").write_text(hypothesis, encoding="utf-8")
    if code_proposal:
        (directory / code_filename).write_text(code_proposal, encoding="utf-8")
    return directory


def write_fork_result(experiment_id: str, payload: dict) -> Path | None:
    directory = FORKS / experiment_id
    if not directory.exists():
        return None
    path = directory / "result.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
