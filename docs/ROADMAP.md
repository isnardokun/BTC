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
- [ ] Monte Carlo/bootstrap
- [ ] costos/slippage
- [x] resultados por régimen tendencial y volatilidad
- [ ] resultados agregados por año
- [ ] benchmark buy-and-hold
- [ ] análisis de estabilidad/mesetas de parámetros

## H3 — Contexto
- [x] ATR y ATR %
- [x] volatilidad realizada 20 barras
- [x] EMA20/EMA50/EMA200 y distancias relativas
- [x] volumen relativo z-score
- [x] tamaño de cuerpo/rango normalizado por ATR
- [x] régimen bull/bear/transition
- [x] régimen de volatilidad
- [ ] estructura HH-HL-LH-LL explícita
- [ ] drawdown desde máximos
- [ ] features temporales/cíclicas
- [ ] funding/on-chain opcional

## H4 — Agente autónomo
- [x] contexto IA con ranking in-sample + walk-forward + regímenes
- [ ] bucle multi-iteración que ejecute y evalúe propuestas automáticamente
- [ ] agente crítico independiente
- [ ] sandbox ejecutable de forks de código
- [ ] promoción asistida de variantes

## H5 — Exportación
- [ ] Pine Script
- [ ] estrategia TradingView equivalente
- [ ] alertas/webhooks
