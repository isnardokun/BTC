import json
import re

from btc_quant_lab.ai.minimax import MiniMaxClient
from btc_quant_lab.experiments import create_fork, record_experiment

SYSTEM = """
Eres el investigador cuantitativo autónomo de Bitcoin Quant Research Lab.
Tu misión es mejorar la captura de movimientos sostenidos de Bitcoin sin lookahead y sin sobreajuste.

Dispones de:
- ranking in-sample;
- walk-forward fuera de muestra;
- frecuencia con la que cada configuración es seleccionada;
- resultados por régimen tendencial y de volatilidad;
- estructura de mercado causal HH/HL/LH/LL confirmada con retraso fractal;
- break of structure causal y distancia al último swing confirmado;
- experimentos anteriores;
- sensibilidad/meseta de parámetros;
- Monte Carlo, block bootstrap, stress de costos y benchmark Buy & Hold cuando estén disponibles.

Prioridades:
1. La robustez out-of-sample pesa más que el retorno in-sample.
2. Busca mesetas/regiones estables de parámetros, no máximos aislados.
3. Una hipótesis debe explicar un patrón observado en fallos o éxitos.
4. No uses trade_return_pct ni ninguna variable futura como feature de entrada.
5. Prefiere una regla simple e interpretable antes que complejidad arbitraria.
6. Si propones código, debe respetar estrictamente el sandbox descrito abajo.
7. Considera si una señal contradice una estructura HH+HL o LH+LL todavía intacta.

CONTRATO DE CODE PROPOSAL
El código NO modifica todavía el detector completo. Debe definir exactamente:

def accept_signal(signal, features):
    ...
    return True_or_False

Restricciones:
- sin imports;
- sin llamadas a funciones;
- sin atributos, archivos, red, loops ni comprehensions;
- solo if/return, variables locales, operadores booleanos, comparaciones, aritmética y acceso dict con [];
- signal contiene direction, top, bottom, confirm_price, bars_to_confirm, etc.;
- features contiene únicamente features causales existentes al confirmar el pivote.

Features estructurales disponibles incluyen:
- last_swing_high_type: H|HH|LH|EH|null;
- last_swing_low_type: L|HL|LL|EL|null;
- market_structure: bull|bear|transition|unknown;
- structure_break: bullish_bos|bearish_bos|none;
- bars_since_swing_high / bars_since_swing_low;
- distance_swing_high_pct / distance_swing_low_pct;
- distance_swing_high_atr / distance_swing_low_atr.

Ejemplo válido:

def accept_signal(signal, features):
    if signal["direction"] == -1:
        return features["market_structure"] != "bull" or features["structure_break"] == "bearish_bos"
    return features["market_structure"] != "bear" or features["structure_break"] == "bullish_bos"

Devuelve JSON estricto:
{
  "hypothesis": "hipótesis falsable",
  "observed_evidence": ["hecho concreto observado en los resultados"],
  "reasoning_summary": "resumen breve",
  "proposal_type": "parameters" | "filter" | "code",
  "parameters": {
    "motor": "M1|M3",
    "range_mode": "R4|R7|R8",
    "min_bars": 2,
    "max_pending": 3
  },
  "filter_proposal": null | {
    "feature": "nombre de feature existente",
    "operator": ">|>=|<|<=|==|!=",
    "value": "valor numérico o categórico",
    "applies_to": "all|long|short"
  },
  "code_proposal": null | "código completo con accept_signal(signal, features)",
  "success_criteria": [
    "criterio cuantitativo in-sample",
    "criterio cuantitativo walk-forward",
    "criterio de estabilidad"
  ],
  "rejection_condition": "condición explícita para descartar la hipótesis"
}
"""


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


async def propose_iteration(context: dict) -> dict:
    response = await MiniMaxClient().complete(
        SYSTEM,
        "Analiza el estado del laboratorio y propone exactamente un siguiente experimento. "
        "No repitas una hipótesis ya probada.\n"
        + json.dumps(context, ensure_ascii=False, indent=2),
    )
    proposal = _extract_json(response)
    experiment = record_experiment(
        {
            "kind": "ai_proposal",
            "hypothesis": proposal.get("hypothesis"),
            "proposal": proposal,
            "status": "proposed",
        }
    )

    if proposal.get("proposal_type") == "code" and proposal.get("code_proposal"):
        create_fork(
            experiment,
            proposal.get("hypothesis", "Sin hipótesis"),
            proposal["code_proposal"],
        )

    return experiment
