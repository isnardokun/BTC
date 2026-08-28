# AGENTS.md

## Misión
Continuar Bitcoin Quant Research Lab como plataforma cuantitativa auditable para encontrar reglas simples y robustas que capturen movimientos sostenidos de Bitcoin.

## Leer antes de modificar
1. `README.md`
2. `docs/STRATEGY.md`
3. `docs/RESEARCH.md`
4. `docs/AI_RESEARCHER.md`
5. `experiments/ledger.jsonl`
6. tests

## Reglas
- No usar lookahead ni datos futuros.
- No promover una variante por una sola métrica.
- Mantener baseline reproducible.
- Todo experimento debe declarar una hipótesis falsable.
- Cambios experimentales van en `experiments/forks/`.
- Añadir tests cuando cambie la semántica del detector.
- Preferir regiones estables de parámetros a un único máximo in-sample.

## Flujo
```text
baseline → hipótesis → fork → tests → backtest → comparación → aceptar/rechazar
```

## Benchmark operativo actual
La señal contraria cierra y revierte la posición. El retorno empieza en el precio de confirmación, nunca en el máximo/mínimo retrospectivo del pivote.
