import json
import re
from btc_quant_lab.ai.minimax import MiniMaxClient
from btc_quant_lab.experiments import record_experiment, create_fork

SYSTEM = """
Eres el investigador cuantitativo autónomo de Bitcoin Quant Research Lab.
Formula una hipótesis falsable. Evita lookahead, sobreajuste y muestras pequeñas.
Devuelve JSON estricto:
{
  "hypothesis": "...",
  "reasoning_summary": "...",
  "proposal_type": "parameters" | "code",
  "parameters": {"motor":"M1|M3","range_mode":"R4|R7|R8","min_bars":2,"max_pending":3},
  "code_proposal": null,
  "success_criteria": ["..."]
}
Si propones código, code_proposal debe ser una variante experimental completa y autocontenida; nunca modifiques la estable.
"""


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


async def propose_iteration(context: dict) -> dict:
    response = await MiniMaxClient().complete(SYSTEM, "Propón exactamente un siguiente experimento:\n" + json.dumps(context, ensure_ascii=False, indent=2))
    proposal = _extract_json(response)
    exp = record_experiment({"kind": "ai_proposal", "hypothesis": proposal.get("hypothesis"), "proposal": proposal, "status": "proposed"})
    if proposal.get("proposal_type") == "code" and proposal.get("code_proposal"):
        create_fork(exp, proposal["hypothesis"], proposal["code_proposal"])
    return exp
