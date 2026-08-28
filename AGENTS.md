# AGENTS.md

## Misión
Continuar Bitcoin Quant Research Lab como plataforma cuantitativa auditable para encontrar reglas simples y robustas que capturen movimientos sostenidos de Bitcoin.

## Leer antes de modificar
1. `README.md`
2. `docs/STRATEGY.md`
3. `docs/RESEARCH.md`
4. `docs/WALK_FORWARD.md`
5. `docs/AI_RESEARCHER.md`
6. `experiments/ledger.jsonl`
7. tests

## Reglas
- No usar lookahead ni datos futuros.
- No promover una variante por una sola métrica.
- Mantener baseline reproducible.
- Todo experimento debe declarar una hipótesis falsable.
- Cambios experimentales van en `experiments/forks/`.
- Añadir tests cuando cambie la semántica del detector.
- Preferir regiones estables de parámetros a un único máximo in-sample.
- `trade_return_pct` es un label futuro de investigación y nunca puede ser una feature de entrada.
- El código generado por IA se guarda en fork y NO se ejecuta automáticamente hasta disponer de sandbox.

## Estado actual

### Detector
- motores: M1, M3;
- rangos: R4, R7, R8;
- `min_bars`: 2, 3, 4, 5;
- `max_pending`: 0, 3, 5, 8.

### Benchmark
- pivote alcista confirmado → LONG;
- pivote bajista confirmado → SHORT;
- señal contraria cierra y revierte;
- retorno medido desde el precio real de confirmación;
- retorno SHORT = `(entry - exit) / entry * 100`.

### Robustez
- `research/walkforward.py` implementa train/test cronológico;
- `evaluate_fixed_config()` mide una configuración congelada en ventanas posteriores;
- `research/features.py` genera features causales y regímenes;
- `research/filters.py` permite filtros causales seguros para experimentos.

### IA
- `ai/agent.py`: propone una hipótesis;
- `ai/research_loop.py`: propone → evalúa OOS → acepta/rechaza parámetros/filtros;
- propuestas de código quedan `awaiting_sandbox`.

## Comandos de referencia

```bash
uv run pytest -q
uv run ruff check .
bqrl sync --symbol BTCUSDT --interval 1d
bqrl optimize --symbol BTCUSDT --interval 1d
bqrl walk-forward --symbol BTCUSDT --interval 1d
bqrl features --symbol BTCUSDT --interval 1d
bqrl ai-research --symbol BTCUSDT --interval 1d --iterations 3
```

## Flujo
```text
baseline → hipótesis → parámetros/filtro/fork → tests → OOS → comparación → aceptar/rechazar
```

## Próximas prioridades
1. hacer ejecutable el sandbox de forks de código;
2. añadir resultados por año y benchmark buy-and-hold;
3. sensibilidad/mesetas de parámetros;
4. Monte Carlo/bootstrap de secuencias de trades;
5. agente crítico independiente antes de promover una variante.
