# Handoff

Proyecto: Bitcoin Quant Research Lab.

## Estado completado

- histórico BTC + DuckDB;
- detector M1/M3 + R4/R7/R8;
- backtest por reversión;
- retorno LONG/SHORT simétrico;
- equity compuesta y drawdown real;
- optimizador de 96 configuraciones;
- walk-forward cronológico;
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

1. costos/slippage/fees configurables;
2. purged/embargo validation cuando se usen features para selección;
3. bootstrap por bloques y por régimen;
4. estructura HH/HL/LH/LL explícita;
5. estabilidad temporal/champion decay;
6. sandbox de proceso para mutaciones completas del detector;
7. promoción asistida a stable;
8. exportador Pine Script.

## Regla operativa

Nunca asumir que el mejor resultado in-sample es robusto. Antes de promoción exigir OOS + muestra suficiente + estabilidad + revisión crítica.

Leer `AGENTS.md` para el contrato completo del harness.
