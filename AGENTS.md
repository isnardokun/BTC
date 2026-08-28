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
- El `final_holdout` nunca se entrega al agente proponente ni al crítico durante las iteraciones.
- Todos los candidatos de una misma investigación deben usar exactamente el mismo modelo de fees/slippage.
- La estructura HH/HL/LH/LL debe usar swings confirmados con retraso causal; nunca pivotes perfectos retrospectivos.
- La referencia Purged+Embargo es evidencia adicional de fragilidad de frontera, no sustituto del holdout final.

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
- `max_drawdown_pct` se calcula sobre equity compuesta;
- `BQR_FEE_BPS` y `BQR_SLIPPAGE_BPS` se aplican por lado y el backtest descuenta el costo round-trip.

### Robustez
- `research/walkforward.py`: train/test cronológico + `purged_walk_forward`;
- `research/features.py`: features causales, regímenes y estructura HH/HL/LH/LL;
- `research/filters.py`: filtros declarativos incluyendo estructura/BOS;
- `research/analytics.py`: resultados anuales y Buy & Hold;
- `research/sensitivity.py`: meseta de parámetros;
- `research/montecarlo.py`: bootstrap IID y por bloques;
- `research/cost_stress.py`: degradación por fees/slippage;
- `research/stability.py`: estabilidad temporal/champion decay;
- `ai/research_loop.py`: development set + referencia purged/embargo + holdout final invisible.

### Features estructurales
- `last_swing_high_type`: H/HH/LH/EH;
- `last_swing_low_type`: L/HL/LL/EL;
- `market_structure`: bull/bear/transition/unknown;
- `structure_break`: bullish_bos/bearish_bos/none;
- barras desde último swing alto/bajo;
- distancia al último swing en % y ATR.

### IA
- `ai/agent.py`: investigador que propone;
- `ai/sandbox.py`: ejecuta código restringido de política de señales;
- `ai/critic.py`: crítico independiente que revisa OOS, estructura y purged/embargo;
- `ai/research_loop.py`: propone → ejecuta → OOS → crítico → acepta/rechaza → holdout final.

## Comandos de referencia

```bash
uv run pytest -q
uv run ruff check .
bqrl sync --symbol BTCUSDT --interval 1d
bqrl optimize --symbol BTCUSDT --interval 1d
bqrl walk-forward --symbol BTCUSDT --interval 1d
bqrl purged-walk-forward --symbol BTCUSDT --interval 1d
bqrl features --symbol BTCUSDT --interval 1d
bqrl robustness --symbol BTCUSDT --interval 1d
bqrl ai-research --symbol BTCUSDT --interval 1d --iterations 3
```

## Flujo
```text
baseline
  → hipótesis
  → parámetros/filtro/código restringido
  → OOS desarrollo
  → referencia purged/embargo
  → crítico
  → aceptar/rechazar
  → holdout final invisible
```

## Próximas prioridades
1. bootstrap y resultados estratificados por régimen/estructura;
2. scoring explícito de contradicción tendencial de una señal;
3. promoción asistida de champion con manifest reproducible;
4. sandbox de proceso para mutaciones completas del detector;
5. exportador de una variante aprobada a Pine Script;
6. rama/tag `stable` solo después de pasar holdout y stress tests.
