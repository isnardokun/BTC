# Roadmap

## H1 — MVP
- [x] datos públicos BTC
- [x] DuckDB
- [x] detector
- [x] backtest por reversión
- [x] optimizador
- [x] API + web UI
- [x] MiniMax opcional
- [x] ledger y forks

## H2 — Robustez
- [x] walk-forward cronológico train/test
- [x] Monte Carlo/bootstrap de secuencias de trades
- [ ] costos/slippage
- [x] resultados por régimen tendencial y volatilidad
- [x] resultados agregados por año
- [x] benchmark buy-and-hold
- [x] análisis de estabilidad/mesetas de parámetros
- [x] equity compuesta y drawdown porcentual real

## H3 — Contexto
- [x] ATR y ATR %
- [x] volatilidad realizada 20 barras
- [x] EMA20/EMA50/EMA200 y distancias relativas
- [x] volumen relativo z-score
- [x] tamaño de cuerpo/rango normalizado por ATR
- [x] régimen bull/bear/transition
- [x] régimen de volatilidad
- [x] filtros causales experimentales sobre features
- [ ] estructura HH-HL-LH-LL explícita
- [ ] drawdown desde máximos
- [ ] features temporales/cíclicas
- [ ] funding/on-chain opcional

## H4 — Agente autónomo
- [x] contexto IA con ranking in-sample + walk-forward + regímenes
- [x] bucle multi-iteración para parámetros y filtros
- [x] aceptación/rechazo automático por score OOS
- [x] agente crítico independiente
- [x] sandbox ejecutable restringido para forks de política de señales
- [ ] sandbox de mutaciones completas del detector
- [ ] promoción asistida de variantes a stable

## H5 — Calidad de ingeniería
- [x] CI con pytest + ruff
- [x] tests de fórmula SHORT, equity compuesta y sandbox
- [ ] cobertura ampliada de API/IA
- [ ] benchmarks de rendimiento
- [ ] cache de optimizaciones costosas

## H6 — Próxima capa cuantitativa
- [ ] costos, slippage y fees configurables
- [ ] validación purged/embargo para experimentos con features
- [ ] bootstrap por bloques/regímenes, no solo IID trades
- [ ] estabilidad temporal del champion
- [ ] comparación contra estrategias triviales long-only/EMA
- [ ] promoción por múltiples semillas de Monte Carlo

## H7 — Exportación
- [ ] Pine Script
- [ ] estrategia TradingView equivalente
- [ ] alertas/webhooks
