# Bitcoin Quant Research Lab

Laboratorio cuantitativo para investigar, validar y evolucionar una familia de detectores de pivotes de Bitcoin fuera de las limitaciones de Pine Script.

## Qué incluye

- descarga pública de `BTCUSDT` desde Binance;
- histórico OHLCV en DuckDB;
- detector de pivotes M1/M3 con rangos R4/R7/R8;
- backtest por reversión: la señal contraria cierra y revierte la posición;
- retorno porcentual real por operación;
- equity compuesta y drawdown porcentual;
- fees/slippage configurables;
- optimizador de 96 configuraciones;
- walk-forward cronológico train/test;
- holdout final que permanece invisible para la IA durante las iteraciones;
- features causales y regímenes de mercado;
- filtros experimentales sobre ATR, volatilidad, volumen, EMA y régimen;
- resultados por año, Buy & Hold, sensibilidad/mesetas y Monte Carlo;
- API FastAPI;
- interfaz web con gráfico de velas, pivotes y % de cada trade cerrado;
- integración opcional con MiniMax;
- agente investigador + agente crítico independiente;
- sandbox AST restringido para políticas de señal generadas por IA;
- ledger de experimentos y forks aislados;
- CI con `pytest` + `ruff`;
- archivos de continuidad para OpenCode, Codex y Claude Code.

## Inicio rápido — CachyOS / Arch

```bash
chmod +x scripts/bootstrap_arch.sh
./scripts/bootstrap_arch.sh
source .venv/bin/activate
bqrl sync --symbol BTCUSDT --interval 1d
bqrl optimize --symbol BTCUSDT --interval 1d
bqrl walk-forward --symbol BTCUSDT --interval 1d
bqrl robustness --symbol BTCUSDT --interval 1d
bqrl serve
```

Abre `http://127.0.0.1:8765`.

## Costos de ejecución

Por defecto se mantienen en cero para reproducir los experimentos iniciales. En `.env` puedes definirlos en basis points **por lado**:

```bash
BQR_FEE_BPS=5
BQR_SLIPPAGE_BPS=5
```

Con esos valores, cada operación completa soporta aproximadamente `0.20%` de fricción round-trip. El mismo modelo se propaga al optimizador, walk-forward, sandbox, agente IA y holdout final.

## MiniMax

En `.env`:

```bash
MINIMAX_API_KEY=tu_token
MINIMAX_MODEL=MiniMax-M2.5
```

Una propuesta aislada:

```bash
bqrl ai-iterate --symbol BTCUSDT --interval 1d
```

Tres iteraciones autónomas:

```bash
bqrl ai-research --symbol BTCUSDT --interval 1d --iterations 3
```

## Protocolo autónomo

El research loop no necesita que le pases manualmente capturas ni tablas:

1. separa el histórico en **development** y un **final holdout**;
2. el holdout final no se entrega ni al agente investigador ni al crítico;
3. dentro de development construye baseline, OOS y sensibilidad;
4. MiniMax formula una hipótesis;
5. puede proponer parámetros, filtro declarativo o una política de código restringido;
6. el candidato se ejecuta con el mismo modelo de costos;
7. debe superar el `robustness_score` OOS;
8. un segundo agente crítico independiente debe aprobarlo;
9. se convierte en champion solo si cumple ambas condiciones;
10. al terminar todas las iteraciones, el champion se mide **una sola vez** en el holdout final que no vio.

El objetivo es reducir el riesgo de que el propio proceso autónomo termine sobreajustando el supuesto OOS después de muchas iteraciones.

## Sandbox de código

La IA puede crear forks que definan exclusivamente:

```python
def accept_signal(signal, features):
    if signal["direction"] == -1:
        return features["atr_pct"] > 2 and features["distance_ema50_pct"] > 5
    return features["trend_regime"] != "bull"
```

El sandbox valida el AST antes de ejecutar. No permite imports, llamadas a funciones, atributos, archivos, red, loops, comprehensions ni builtins. Este sandbox sirve para evolucionar **políticas de aceptación de señales**; todavía no permite reemplazar arbitrariamente todo el detector.

## Principio de investigación

Un pivote retrospectivamente bien ubicado no equivale a una entrada operable. El benchmark usa precios conocidos al confirmar la señal:

- pivote alcista confirmado → LONG;
- pivote bajista confirmado → SHORT;
- el pivote contrario cierra y revierte;
- no hay TP/SL en el benchmark base;
- cada trade registra su retorno aunque sea negativo.

Retorno LONG:

```text
(exit - entry) / entry * 100
```

Retorno SHORT:

```text
(entry - exit) / entry * 100
```

## Validación

El ranking in-sample sirve para explorar. La decisión importante se apoya en:

- walk-forward;
- tamaño de muestra;
- expectancy OOS;
- profit factor OOS;
- drawdown sobre equity compuesta;
- porcentaje de ventanas rentables;
- estabilidad/meseta de parámetros;
- Monte Carlo;
- comparación Buy & Hold;
- costos;
- revisión crítica independiente;
- holdout final.

## Documentación

- `docs/ARCHITECTURE.md`
- `docs/STRATEGY.md`
- `docs/RESEARCH.md`
- `docs/WALK_FORWARD.md`
- `docs/AI_RESEARCHER.md`
- `docs/LINUX_ARCH.md`
- `docs/ROADMAP.md`
- `AGENTS.md`
- `CLAUDE.md`

## Seguridad del agente

La IA nunca sobrescribe la estrategia estable directamente. Los cambios experimentales se guardan en `experiments/forks/<id>/`. El sandbox ejecutable actual está deliberadamente restringido a funciones puras de aceptación de señales.
