# Bitcoin Quant Research Lab

Laboratorio cuantitativo para investigar, validar y evolucionar detectores de pivotes de Bitcoin fuera de las limitaciones de Pine Script.

## Qué incluye

- descarga pública de `BTCUSDT` desde Binance;
- histórico OHLCV en DuckDB;
- detector baseline M1/M3 con rangos R4/R7/R8;
- backtest por reversión: la señal contraria cierra y revierte la posición;
- retorno porcentual real por operación;
- equity compuesta y drawdown porcentual;
- fees/slippage configurables;
- optimizador de 96 configuraciones;
- walk-forward cronológico train/test;
- validación adicional Purged + Embargo;
- holdout final invisible para la IA durante las iteraciones;
- features causales de ATR, volatilidad, volumen y EMA;
- estructura causal HH/HL/LH/LL mediante fractales confirmados;
- Break of Structure causal;
- `signal_context` aligned/mixed/contrarian y `trend_contradiction_score` 0..3;
- filtros experimentales sobre esas features;
- resultados por año y Buy & Hold;
- sensibilidad/mesetas de parámetros;
- Monte Carlo IID y moving-block bootstrap;
- validación estratificada por régimen/contexto;
- stress de fees/slippage;
- estabilidad temporal/champion decay;
- API FastAPI e interfaz web;
- integración opcional con MiniMax;
- agente investigador + agente crítico independiente;
- sandbox AST restringido para políticas de señal;
- sandbox rootless Podman para mutaciones completas del detector;
- auditoría causal prefix-invariance de detectores generados;
- Deep Detector Research autónomo;
- manifests de promoción auditables;
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
bqrl purged-walk-forward --symbol BTCUSDT --interval 1d
bqrl robustness --symbol BTCUSDT --interval 1d
bqrl serve
```

Abre `http://127.0.0.1:8765`.

## Costos de ejecución

Por defecto permanecen en cero para reproducir los experimentos iniciales. En `.env` pueden definirse en basis points **por lado**:

```bash
BQR_FEE_BPS=5
BQR_SLIPPAGE_BPS=5
```

Con esos valores, cada operación completa soporta aproximadamente `0.20%` de fricción round-trip. El mismo modelo se propaga al optimizador, walk-forward, agentes, sandboxes y holdout final.

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

Tres iteraciones autónomas del loop estable:

```bash
bqrl ai-research --symbol BTCUSDT --interval 1d --iterations 3
```

## Protocolo autónomo estable

El loop estándar trabaja sobre parámetros, filtros y políticas restringidas:

1. separa el histórico en **development** y un **final holdout**;
2. el holdout final no se entrega ni al investigador ni al crítico;
3. dentro de development construye baseline, OOS, sensibilidad y referencia Purged+Embargo;
4. analiza estructura HH/HL/LH/LL, BOS y contradicción tendencial;
5. MiniMax formula una hipótesis;
6. propone parámetros, filtro declarativo o una política de señal restringida;
7. el candidato usa el mismo modelo de costos;
8. se mide su robustez global y por régimen/contexto;
9. debe superar el `robustness_score` OOS;
10. un segundo agente crítico revisa OOS, regímenes, estructura y Purged+Embargo;
11. solo entonces puede sustituir al champion;
12. al terminar, el champion se mide una vez en el holdout final;
13. se genera un manifest de promoción con gates y advertencias.

## Deep Detector Research

Para que la IA pueda cambiar **la lógica que genera los pivotes**, y no únicamente parámetros o filtros, existe un flujo separado con Podman rootless.

Primero prepara explícitamente el sandbox:

```bash
bash scripts/setup_detector_sandbox_arch.sh
```

Después:

```bash
bqrl-detector-research \
  --symbol BTCUSDT \
  --interval 1d \
  --iterations 3 \
  --min-trades 10
```

En este modo cada iteración debe proponer `detector_code` con:

```python
def detect(candles, config):
    return signals
```

El código se ejecuta en un contenedor con red deshabilitada, rootfs read-only, límites de CPU/memoria/PIDs y sin montar carpetas personales del host.

Además del aislamiento, el detector debe superar:

- validación de timestamps y precios contra OHLCV real;
- `confirm_price == close` de la vela de confirmación;
- consistencia de `candidate_ts` y `bars_to_confirm`;
- auditoría causal por prefijos;
- OOS cronológico;
- OOS con zona Purge + Embargo;
- resultados por régimen/contexto;
- agente crítico;
- comprobación development→full antes de revelar el holdout;
- holdout final oculto durante la investigación.

Los forks quedan en `experiments/forks/<id>/` y los manifests de promoción en `experiments/promotions/<id>.json`.

Este modo todavía está separado del botón principal de la UI hasta completar pruebas reales de Podman en CachyOS. Ver `docs/DETECTOR_SANDBOX.md`.

## Estructura causal

Los swings HH/HL/LH/LL no se obtienen con pivotes retrospectivos perfectos. Un fractal solo entra al estado de mercado después de cerrar las velas derechas necesarias para confirmarlo.

Ejemplos de hipótesis:

```text
SHORT + estructura HH/HL intacta + bullish BOS → alta contradicción
LONG + estructura LH/LL intacta + bearish BOS → alta contradicción
```

`trend_contradiction_score` cuenta cuántas capas causales conocidas contradicen la dirección propuesta: régimen EMA, estructura y BOS. Debe demostrar utilidad OOS; no es una regla fija.

## Dos fronteras de ejecución de IA

### Policy sandbox

Para modificar solo la aceptación de señales:

```python
def accept_signal(signal, features):
    if features["trend_contradiction_score"] >= 2:
        return False
    return True
```

El AST restringido no permite imports, llamadas, atributos, archivos, red, loops, comprehensions ni builtins.

### Full detector sandbox

Para modificar el generador completo, la frontera de seguridad es un proceso rootless aislado. El aislamiento no sustituye la causalidad: por eso todo detector completo debe pasar prefix-invariance antes de ser medido.

## Benchmark operativo

Un pivote retrospectivamente bien ubicado no equivale a una entrada operable. El benchmark utiliza precios conocidos al confirmar la señal:

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

El ranking in-sample sirve para explorar. Las decisiones se apoyan en:

- walk-forward;
- Purged + Embargo;
- tamaño de muestra;
- expectancy y Profit Factor OOS;
- drawdown sobre equity compuesta;
- porcentaje de ventanas rentables;
- estabilidad/meseta de parámetros;
- Monte Carlo y block bootstrap;
- robustez por estructura/régimen;
- comparación Buy & Hold;
- stress de costos;
- champion decay;
- revisión crítica independiente;
- holdout final oculto durante investigación.

## Promoción

Al terminar una investigación se crea localmente:

```text
experiments/promotions/<promotion_id>.json
```

El manifest queda `eligible_for_review` o `rejected_for_promotion`. **No crea ni mueve automáticamente una rama/tag `stable`.**

Ver `docs/PROMOTION.md`.

## Documentación

- `docs/ARCHITECTURE.md`
- `docs/STRATEGY.md`
- `docs/RESEARCH.md`
- `docs/WALK_FORWARD.md`
- `docs/AI_RESEARCHER.md`
- `docs/DETECTOR_SANDBOX.md`
- `docs/PROMOTION.md`
- `docs/LINUX_ARCH.md`
- `docs/ROADMAP.md`
- `AGENTS.md`
- `CLAUDE.md`

## Seguridad del agente

La IA nunca sobrescribe la estrategia estable directamente. Los cambios experimentales permanecen en `experiments/forks/<id>/`. Un resultado `eligible_for_review` significa únicamente que pasó gates cuantitativos para revisión; no es autorización para operar ni para crear `stable` automáticamente.
