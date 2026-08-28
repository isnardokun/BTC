# Handoff

Proyecto: Bitcoin Quant Research Lab.

## Estado completado

- histórico BTC + DuckDB;
- detector M1/M3 + R4/R7/R8;
- backtest por reversión;
- retorno LONG/SHORT simétrico;
- equity compuesta y drawdown real;
- fees/slippage configurables y propagados por el pipeline;
- optimizador de 96 configuraciones;
- walk-forward cronológico;
- holdout final invisible durante investigación autónoma;
- features causales y regímenes;
- filtros declarativos;
- resultados por año;
- Buy & Hold;
- sensibilidad/mesetas;
- Monte Carlo IID de trades;
- agente investigador MiniMax;
- sandbox AST ejecutable para `accept_signal(signal, features)`;
- agente crítico independiente;
- UI de robustez;
- CI + tests base.

## Próximas prioridades

1. dejar CI completamente verde y ampliar cobertura;
2. purged/embargo validation para selección basada en features;
3. bootstrap por bloques y por régimen;
4. estructura HH/HL/LH/LL explícita;
5. estabilidad temporal/champion decay;
6. stress test de costos;
7. sandbox de proceso para mutaciones completas del detector;
8. promoción asistida a stable;
9. exportador Pine Script.

## Regla operativa

Nunca asumir que el mejor resultado in-sample es robusto. Antes de promoción exigir OOS de desarrollo + muestra suficiente + estabilidad + revisión crítica. El holdout final se revela solo después de terminar las iteraciones y no debe reutilizarse como objetivo de optimización.

Leer `AGENTS.md` para el contrato completo del harness.
