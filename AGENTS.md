# AGENTS.md

## Misión
Continuar Bitcoin Quant Research Lab como plataforma cuantitativa auditable para encontrar reglas simples y robustas que capturen movimientos sostenidos de Bitcoin.

## Leer antes de modificar
1. `README.md`
2. `docs/STRATEGY.md`
3. `docs/RESEARCH.md`
4. `docs/WALK_FORWARD.md`
5. `docs/AI_RESEARCHER.md`
6. `docs/DETECTOR_SANDBOX.md`
7. `docs/PROMOTION.md`
8. `docs/ROADMAP.md`
9. `experiments/ledger.jsonl`
10. tests

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
- El sandbox AST solo admite políticas `accept_signal(signal, features)`; no convertirlo silenciosamente en ejecución Python arbitraria.
- El sandbox de detector completo debe seguir aislado en Podman rootless, sin red y con límites de recursos.
- Todo `detector_code` debe pasar validación de mercado y prefix-invariance antes de scoring.
- El `final_holdout` nunca se entrega al agente proponente ni al crítico durante las iteraciones.
- Para un detector completo, volver a comprobar prefix-invariance entre development y dataset completo antes de puntuar el holdout.
- Todos los candidatos de una misma investigación deben usar exactamente el mismo modelo de fees/slippage.
- La estructura HH/HL/LH/LL debe usar swings confirmados con retraso causal; nunca pivotes perfectos retrospectivos.
- La referencia Purged+Embargo es evidencia adicional de fragilidad de frontera, no sustituto del holdout final.
- `eligible_for_review` no equivale a `stable` ni a autorización para operar.

## Estado actual

### Detector baseline
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
- `research/features.py`: features causales, HH/HL/LH/LL, BOS y score de contradicción;
- `research/filters.py`: filtros declarativos incluyendo estructura/contexto;
- `research/regime_validation.py`: métricas + block bootstrap por régimen/contexto;
- `research/analytics.py`: resultados anuales y Buy & Hold;
- `research/sensitivity.py`: meseta de parámetros;
- `research/montecarlo.py`: bootstrap IID y por bloques;
- `research/cost_stress.py`: degradación por fees/slippage;
- `research/stability.py`: estabilidad temporal/champion decay;
- `research/promotion.py`: gates y manifest reproducible de promoción.

### Features estructurales
- `last_swing_high_type`: H/HH/LH/EH;
- `last_swing_low_type`: L/HL/LL/EL;
- `market_structure`: bull/bear/transition/unknown;
- `structure_break`: bullish_bos/bearish_bos/none;
- `signal_context`: aligned/mixed/contrarian/unknown;
- `trend_contradiction_score`: 0..3;
- barras desde último swing alto/bajo;
- distancia al último swing en % y ATR.

### IA — loop estable
- `ai/agent.py`: investigador que propone parámetros/filtro/policy y conoce el contrato `detector_code`;
- `ai/sandbox.py`: ejecuta código AST restringido de política de señales;
- `ai/critic.py`: crítico independiente;
- `ai/research_loop.py`: parámetros/filtros/policy → OOS → regímenes → crítico → holdout → promotion manifest.

### IA — Deep Detector Research
- `ai/process_sandbox.py`: ejecución de `detector_variant.py` en Podman rootless sin red, read-only y con límites;
- `ai/detector_runner.py`: contrato `detect(candles, config)` dentro del contenedor;
- `ai/detector_candidate.py`: causalidad, OOS y boundary-gap Purge+Embargo del detector completo;
- `ai/detector_research_loop.py`: iteraciones exclusivamente `detector_code` con crítico y holdout oculto;
- `ai/detector_research_cli.py`: CLI separado del loop web estable;
- `scripts/setup_detector_sandbox_arch.sh`: preparación explícita de Podman/imagen.

Controles de detector completo:
- timestamps de confirmación/candidato deben existir en OHLCV;
- `confirm_price` debe coincidir con el close real;
- `bars_to_confirm` debe coincidir con distancia real;
- precios finitos y señales ordenadas;
- prefix-invariance en development;
- OOS con prefijos causales;
- boundary-gap OOS con Purge+Embargo;
- nueva comprobación development→full antes del holdout.

### Promoción
- `experiments/promotions/<id>.json` se genera al final de los research loops;
- estados: `eligible_for_review` o `rejected_for_promotion`;
- nunca se crea/mueve `stable` automáticamente.

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
bash scripts/setup_detector_sandbox_arch.sh
bqrl-detector-research --symbol BTCUSDT --interval 1d --iterations 3 --min-trades 10
```

## Flujos

### Estable
```text
baseline
  → hipótesis
  → parámetros/filtro/policy restringida
  → OOS desarrollo
  → regímenes + block bootstrap
  → referencia purged/embargo
  → crítico
  → aceptar/rechazar
  → holdout final invisible
  → promotion manifest
```

### Deep Detector Research
```text
baseline
  → hipótesis detector_code
  → fork detector_variant.py
  → Podman rootless
  → validación OHLCV
  → prefix-invariance
  → OOS causal
  → boundary-gap Purge+Embargo
  → regímenes
  → crítico
  → aceptar/rechazar
  → auditoría development→full
  → holdout final invisible
  → promotion manifest
```

## Próximas prioridades
1. hacer smoke/performance test real del Deep Detector Research en CachyOS con Podman (1, 3 y 10 iteraciones);
2. fijar/registrar de forma reproducible la imagen exacta del sandbox y su ID/digest;
3. integrar el modo profundo en la UI solo después de pruebas locales satisfactorias;
4. crear exportador Pine Script para baseline/parámetros y después policy traducible;
5. para champions `detector_code`, definir contrato de exportación Pine separado: no asumir traducción Python→Pine automática exacta;
6. añadir acción explícita y revisable para crear rama/tag `stable` únicamente desde un manifest `eligible_for_review` aprobado;
7. ampliar benchmarks triviales (long-only/EMA) y cobertura API/IA.
