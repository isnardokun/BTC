# Roadmap

## H1 — MVP
- [x] datos públicos BTC
- [x] DuckDB
- [x] detector baseline
- [x] backtest por reversión
- [x] optimizador
- [x] API + web UI
- [x] MiniMax opcional
- [x] ledger y forks

## H2 — Robustez
- [x] walk-forward cronológico train/test
- [x] Purged + Embargo de referencia
- [x] holdout final invisible durante investigación autónoma
- [x] Monte Carlo IID
- [x] moving-block bootstrap
- [x] fees y slippage configurables
- [x] resultados por régimen/contexto
- [x] resultados agregados por año
- [x] benchmark Buy & Hold
- [x] análisis de estabilidad/mesetas de parámetros
- [x] equity compuesta y drawdown porcentual real
- [x] stress de costos
- [x] champion decay

## H3 — Contexto causal
- [x] ATR y ATR %
- [x] volatilidad realizada 20 barras
- [x] EMA20/EMA50/EMA200 y distancias relativas
- [x] volumen relativo z-score
- [x] tamaño de cuerpo/rango normalizado por ATR
- [x] régimen bull/bear/transition
- [x] régimen de volatilidad
- [x] filtros causales experimentales
- [x] estructura HH/HL/LH/LL confirmada causalmente
- [x] Break of Structure causal
- [x] `signal_context` aligned/mixed/contrarian
- [x] `trend_contradiction_score` 0..3
- [ ] features temporales/cíclicas si demuestran utilidad OOS
- [ ] funding/on-chain opcional y siempre con timestamp de disponibilidad real

## H4 — Agente autónomo estable
- [x] contexto IA con ranking + walk-forward + regímenes
- [x] bucle multi-iteración para parámetros y filtros
- [x] políticas AST restringidas `accept_signal`
- [x] aceptación/rechazo por score OOS
- [x] agente crítico independiente
- [x] holdout final no expuesto hasta terminar iteraciones
- [x] manifest de promoción auditable

## H5 — Mutaciones completas del detector
- [x] Podman rootless sin red y con rootfs read-only
- [x] contrato `detect(candles, config)`
- [x] límites CPU/memoria/PIDs + timeout
- [x] validación timestamps/precios/bars_to_confirm
- [x] auditoría causal prefix-invariance
- [x] OOS del detector usando prefijos causales
- [x] boundary-gap OOS con Purge + Embargo
- [x] Deep Detector Research separado del loop estable
- [x] crítico independiente y holdout final para detector mutado
- [x] comprobación development→full antes de puntuar holdout
- [ ] smoke test real en CachyOS/Podman
- [ ] benchmark de 1/3/10 iteraciones y consumo de recursos
- [ ] registrar ID/digest exacto de la imagen de sandbox
- [ ] integrar Deep Detector Research en la UI tras validación local

## H6 — Calidad de ingeniería
- [x] CI con pytest + ruff
- [x] tests de fórmula SHORT, equity, costos y sandboxes
- [x] tests de estructura causal
- [x] tests Purged+Embargo
- [x] tests de promoción
- [x] tests de contrato/causalidad del detector completo sin Podman real
- [ ] cobertura ampliada API/IA
- [ ] benchmarks de rendimiento persistentes
- [ ] cache de optimizaciones costosas
- [ ] telemetría local de runtime del sandbox

## H7 — Exportación
- [ ] exportador Pine v6 para detector baseline/configuraciones
- [ ] traducción segura de policies AST compatibles a Pine
- [ ] estrategia TradingView equivalente para backtest visual
- [ ] contrato de exportación específico para champions `detector_code`
- [ ] alertas/webhooks

## H8 — Stable / release
- [x] gates cuantitativos y `eligible_for_review`
- [ ] revisión explícita de manifest
- [ ] acción controlada para crear rama/tag `stable`
- [ ] guardar commit, datos, costos, imagen sandbox y evidencia exacta de cada release
- [ ] nunca promover automáticamente por una única corrida
