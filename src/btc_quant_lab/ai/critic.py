from __future__ import annotations

import json
import re

from btc_quant_lab.ai.minimax import MiniMaxClient


SYSTEM = """
Eres el agente crítico independiente de Bitcoin Quant Research Lab.
No propones estrategias. Tu única tarea es revisar si un candidato merece sustituir al champion.
Debes priorizar robustez fuera de muestra, tamaño de muestra, drawdown, consistencia entre ventanas,
sensibilidad de parámetros y riesgo de sobreajuste. Un mayor retorno in-sample no es evidencia suficiente.

Devuelve JSON estricto:
{
  "verdict": "approve" | "reject",
  "rationale": "...",
  "concerns": ["..."],
  "required_followups": ["..."]
}
"""


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


async def review_candidate(payload: dict) -> dict:
    response = await MiniMaxClient().complete(
        SYSTEM,
        "Revisa esta comparación y decide si el candidato puede sustituir al champion:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2),
    )
    result = _extract_json(response)
    verdict = result.get("verdict")
    if verdict not in {"approve", "reject"}:
        raise ValueError(f"critic returned invalid verdict: {verdict}")
    result.setdefault("concerns", [])
    result.setdefault("required_followups", [])
    return result
