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
- referencia purged + embargo;
- frecuencia con la que cada configuración es seleccionada;
- resultados por régimen tendencial y de volatilidad;
- estructura de mercado causal HH/HL/LH/LL confirmada con retraso fractal;
- break of structure causal y distancia al último swing confirmado;
- contexto agregado de la señal frente a la tendencia;
- experimentos anteriores;
- sensibilidad/meseta de parámetros;
- Monte Carlo, block bootstrap, stress de costos y benchmark Buy & Hold cuando estén disponibles.

Prioridades:
1. La robustez out-of-sample pesa más que el retorno in-sample.
2. Busca mesetas/regiones estables de parámetros, no máximos aislados.
3. Una hipótesis debe explicar un patrón observado en fallos o éxitos.
4. No uses trade_return_pct ni ninguna variable futura como feature de entrada.
5. Prefiere una regla simple e interpretable antes que complejidad arbitraria.
6. Si propones código, respeta el contrato del sandbox correspondiente.
7. Considera si una señal contradice una estructura HH+HL o LH+LL todavía intacta.
8. Usa signal_context y trend_contradiction_score como hipótesis, no como dogmas: deben demostrar mejora OOS.
9. Solo puedes proponer detector_code si research_protocol.full_detector_sandbox_ready es true.

CONTRATO DE CODE PROPOSAL
Para proposal_type = code debes definir exactamente:

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

CONTRATO DE DETECTOR_CODE
Para proposal_type = detector_code debes devolver un detector completo que defina exactamente:

def detect(candles, config):
    ...
    return signals

Reglas del detector completo:
- solo puede depender de candles y config;
- debe ser determinista;
- no debe leer reloj, variables de entorno, archivos ni fuentes externas;
- no debe depender de paquetes externos; la imagen base contiene Python estándar;
- cada señal debe confirmarse usando información disponible hasta su ts;
- confirm_price debe ser exactamente el close de la vela ts;
- candidate_ts y ts deben existir en candles;
- bars_to_confirm debe coincidir con la distancia real entre candidate_ts y ts;
- señales cronológicamente ordenadas;
- no puede reescribir señales pasadas cuando se añaden velas futuras.

El sistema ejecuta detector_code en Podman rootless, sin red, rootfs read-only, con límites de recursos,
y además hace una auditoría prefix-invariance. Un detector que cambie señales pasadas al añadir futuro es rechazado.

Features estructurales disponibles para filtros/code incluyen:
- last_swing_high_type: H|HH|LH|EH|null;
- last_swing_low_type: L|HL|LL|EL|null;
- market_structure: bull|bear|transition|unknown;
- structure_break: bullish_bos|bearish_bos|none;
- signal_context: aligned|mixed|contrarian|unknown;
- trend_contradiction_score: entero 0..3;
- bars_since_swing_high / bars_since_swing_low;
- distance_swing_high_pct / distance_swing_low_pct;
- distance_swing_high_atr / distance_swing_low_atr.

Ejemplo válido de policy code:

def accept_signal(signal, features):
    if features["trend_contradiction_score"] >= 2:
        return False
    if signal["direction"] == -1:
        return features["market_structure"] != "bull" or features["structure_break"] == "bearish_bos"
    return features["market_structure"] != "bear" or features["structure_break"] == "bullish_bos"

Devuelve JSON estricto:
{
  "hypothesis": "hipótesis falsable",
  "observed_evidence": ["hecho concreto observado en los resultados"],
  "reasoning_summary": "resumen breve",
  "proposal_type": "parameters" | "filter" | "code" | "detector_code",
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
  "code_proposal": null | "código completo para el contrato seleccionado",
  "success_criteria": [
    "criterio cuantitativo in-sample",
    "criterio cuantitativo walk-forward",
    "criterio purged/embargo",
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

    proposal_type = proposal.get("proposal_type")
    code_proposal = proposal.get("code_proposal")
    if proposal_type == "code" and code_proposal:
        create_fork(
            experiment,
            proposal.get("hypothesis", "Sin hipótesis"),
            code_proposal,
            code_filename="strategy_variant.py",
        )
    elif proposal_type == "detector_code" and code_proposal:
        create_fork(
            experiment,
            proposal.get("hypothesis", "Sin hipótesis"),
            code_proposal,
            code_filename="detector_variant.py",
        )

    return experiment
