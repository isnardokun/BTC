# Bitcoin Quant Research Lab

Laboratorio cuantitativo para investigar, validar y evolucionar una familia de detectores de pivotes de Bitcoin fuera de las limitaciones de Pine Script.

## Qué incluye

- descarga pública de `BTCUSDT` desde Binance;
- histórico OHLCV en DuckDB;
- detector de pivotes M1/M3 con rangos R4/R7/R8;
- backtest por reversión: la señal contraria cierra y revierte la posición;
- retorno porcentual por operación;
- optimizador de configuraciones;
- API FastAPI;
- interfaz web con gráfico de velas y señales;
- integración opcional con MiniMax;
- ledger de experimentos y forks aislados;
- archivos de continuidad para OpenCode, Codex y Claude Code.

## Inicio rápido — CachyOS / Arch

```bash
unzip bitcoin-quant-research-lab.zip
cd bitcoin-quant-research-lab
chmod +x scripts/bootstrap_arch.sh
./scripts/bootstrap_arch.sh
source .venv/bin/activate
cp .env.example .env   # solo si el instalador no lo hizo
bqrl sync --symbol BTCUSDT --interval 1d
bqrl optimize --symbol BTCUSDT --interval 1d
bqrl serve
```

Abre `http://127.0.0.1:8765`.

## MiniMax

En `.env`:

```bash
MINIMAX_API_KEY=tu_token
MINIMAX_MODEL=MiniMax-M2.5
```

Luego:

```bash
bqrl ai-iterate --symbol BTCUSDT --interval 1d
```

El agente consulta directamente el estado del laboratorio: histórico OHLCV, pivotes, operaciones, métricas y experimentos previos. No depende de que el usuario le pase manualmente capturas o tablas.

## Principio de investigación

Un pivote retrospectivamente bien ubicado no equivale a una entrada operable. Por eso el benchmark usa precios conocidos al confirmar la señal:

- pivote alcista confirmado → LONG;
- pivote bajista confirmado → SHORT;
- el pivote contrario cierra y revierte;
- no hay TP/SL en el benchmark base;
- cada trade registra su retorno real, incluso si es negativo.

## Documentación

- `docs/ARCHITECTURE.md`
- `docs/STRATEGY.md`
- `docs/RESEARCH.md`
- `docs/AI_RESEARCHER.md`
- `docs/LINUX_ARCH.md`
- `docs/ROADMAP.md`
- `AGENTS.md`
- `CLAUDE.md`

## Seguridad del agente

La IA nunca debe sobrescribir la estrategia estable directamente. Los cambios experimentales se guardan en `experiments/forks/<id>/` y deben ser medidos antes de promoverse.
