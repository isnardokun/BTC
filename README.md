# Bitcoin Quant Research Lab

Laboratorio cuantitativo para investigar, validar y evolucionar una familia de detectores de pivotes de Bitcoin fuera de las limitaciones de Pine Script.

## Qué incluye

- descarga pública de `BTCUSDT` desde Binance;
- histórico OHLCV en DuckDB;
- detector de pivotes M1/M3 con rangos R4/R7/R8;
- backtest por reversión: la señal contraria cierra y revierte la posición;
- retorno porcentual real por operación;
- optimizador de 96 configuraciones;
- walk-forward cronológico train/test;
- features causales y regímenes de mercado;
- filtros experimentales sobre ATR, volatilidad, volumen, EMA y régimen;
- API FastAPI;
- interfaz web con gráfico de velas, pivotes y % de cada trade cerrado;
- integración opcional con MiniMax;
- bucle IA autónomo para proponer, probar y aceptar/rechazar parámetros y filtros;
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
bqrl serve
```

Abre `http://127.0.0.1:8765`.

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

El research loop recibe directamente el estado del laboratorio. No necesitas pasar manualmente capturas ni tablas. En cada iteración puede:

1. observar champion, ranking, resultados OOS y regímenes;
2. formular una hipótesis;
3. proponer parámetros o un filtro causal;
4. ejecutar el candidato;
5. medirlo en ventanas posteriores;
6. aceptar/rechazar según robustez;
7. guardar la decisión en `experiments/ledger.jsonl`.

Si propone código Python, se crea un fork en `experiments/forks/<id>/`, pero ese código todavía no se ejecuta automáticamente hasta implementar el sandbox.

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

El ranking in-sample sirve para explorar. La decisión importante debe apoyarse en:

- walk-forward;
- tamaño de muestra;
- expectancy OOS;
- profit factor OOS;
- drawdown;
- porcentaje de ventanas rentables;
- estabilidad de parámetros.

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

La IA nunca debe sobrescribir la estrategia estable directamente. Los cambios experimentales se guardan en `experiments/forks/<id>/` y deben ser medidos antes de promoverse. El código arbitrario generado por un modelo no se ejecuta todavía sin sandbox.
