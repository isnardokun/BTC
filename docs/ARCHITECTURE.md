# Arquitectura

```text
Market API → Data Provider → DuckDB → Pivot Engine → Backtest → Optimizer
                                                      ↘ Web UI
                                                      ↘ AI Researcher → Forks
```

## Capas

### Datos
`src/btc_quant_lab/data/` contiene proveedores y persistencia. Binance Spot público es el proveedor inicial.

### Detector
`research/pivots.py` implementa la máquina de estados sin depender de UI o IA.

### Backtest
`research/backtest.py` convierte pivotes confirmados en operaciones por reversión.

### Optimizador
`research/optimizer.py` ejecuta combinaciones reproducibles y ordena por métricas operables.

### IA
`ai/` observa estado, propone hipótesis y registra experimentos. Los cambios de código se aíslan en forks.

## Principio
La IA propone; el motor cuantitativo mide; el usuario o un proceso explícito promueve.
