# AGENTS.md

## Misión
Continuar Bitcoin Quant Research Lab como plataforma cuantitativa auditable para encontrar reglas simples y robustas que capturen movimientos sostenidos de Bitcoin.

## Leer antes de modificar
1. `README.md`
2. `docs/STRATEGY.md`
3. `docs/RESEARCH.md`
4. `docs/WALK_FORWARD.md`
5. `docs/AI_RESEARCHER.md`
6. `docs/ROADMAP.md`
7. `experiments/ledger.jsonl`
8. tests

## Reglas
- No usar lookahead ni datos futuros.
- No promover una variante por una sola métrica.
- Mantener baseline reproducible.
- Todo experimento debe declarar una hipótesis falsable.
- Cambios experimentales van en `experiments/forks/`.
- Añadir tests cuando cambie la semántica del detector.
- Preferir regiones estables de parámetros a un único máximo in-sample.
- `trade_return_pct` es un label futuro y nunca puede ser una feature de entrada.
- Un candidato autónomo debe mejorar OOS y ser aprobado por el agente crítico.
- El sandbox actual solo admite políticas `accept_signal(signal, features)` con AST restringido; no convertirlo silenciosamente en ejecución Python arbitraria.

## Estado actual

### Detector
- motores: M1, M3;
- rangos: R4, R7, R8;
- `min_bars`: 2, 3, 4, 5;
- `max_pending`: 0, 3, 5, 8.

### Benchmark operativo
- pivote alcista confirmado → LONG;
- pivote bajista confirmado → SHORT;
- señal contraria cierra y revierte;
- retorno medido desde el precio real de confirmación;
- LONG = `(exit - entry) / entry * 100`;
- SHORT = `(entry - exit) / entry * 100`;
- `compounded_return_pct` modela reinversión secuencial;
- `max_drawdown_pct` se calcula sobre equity compuesta.

### Robustez
- `research/walkforward.py`: train/test cronológico;
- `research/features.py`: features causales y regímenes;
- `research/filters.py`: filtros declarativos;
- `research/analytics.py`: resultados anuales y Buy & Hold;
- `research/sensitivity.py`: meseta de parámetros;
- `research/montecarlo.py`: bootstrap de secuencias de trades.

### IA
- `ai/agent.py`: investigador que propone;
- `ai/sandbox.py`: ejecuta código restringido de política de señales;
- `ai/critic.py`: crítico independiente;
- `ai/research_loop.py`: propone → ejecuta → OOS → crítico → acepta/rechaza.

## Comandos de referencia

```bash
uv run pytest -q
uv run ruff check .
bqrl sync --symbol BTCUSDT --interval 1d
bqrl optimize --symbol BTCUSDT --interval 1d
bqrl walk-forward --symbol BTCUSDT --interval 1d
bqrl features --symbol BTCUSDT --interval 1d
bqrl robustness --symbol BTCUSDT --interval 1d
bqrl ai-research --symbol BTCUSDT --interval 1d --iterations 3
```

## Flujo
```text
baseline → hipótesis → parámetros/filtro/código restringido → OOS → robustez → crítico → aceptar/rechazar
```

## Próximas prioridades
1. costos/slippage/fees configurables;
2. purged/embargo validation para features;
3. bootstrap por bloques y regímenes;
4. estructura HH/HL/LH/LL explícita;
5. estabilidad temporal del champion;
6. sandbox de mutaciones completas del detector mediante proceso/contenedor aislado;
7. promoción asistida a una rama/tag `stable`.
