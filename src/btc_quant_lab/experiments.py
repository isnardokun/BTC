from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

LEDGER = Path("experiments/ledger.jsonl")
FORKS = Path("experiments/forks")


def record_experiment(payload: dict) -> dict:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    payload = {"id": payload.get("id") or uuid.uuid4().hex[:12], "created_at": datetime.now(timezone.utc).isoformat(), **payload}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def list_experiments(limit: int = 100) -> list[dict]:
    if not LEDGER.exists():
        return []
    rows = [json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[-limit:][::-1]


def create_fork(experiment: dict, hypothesis: str, code_proposal: str | None = None) -> Path:
    d = FORKS / experiment["id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(experiment, indent=2, ensure_ascii=False), encoding="utf-8")
    (d / "hypothesis.md").write_text(hypothesis, encoding="utf-8")
    if code_proposal:
        (d / "strategy_variant.py").write_text(code_proposal, encoding="utf-8")
    return d
