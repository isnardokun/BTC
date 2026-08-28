# Exportación Pine Script v6

## Objetivo

El laboratorio puede exportar el detector baseline a Pine Script v6 para comparar visualmente TradingView contra la lógica Python que se investiga localmente.

La fuente de verdad sigue siendo:

```text
src/btc_quant_lab/research/pivots.py
```

El exportador congela:

- M1 o M3;
- R4, R7 o R8;
- `min_bars`;
- `max_pending`;
- confirmación por `close`;
- invalidación por `close`;
- mechas fuera de la zona sin resolución;
- resolución del pending antes de crear el candidato de la misma vela;
- reemplazo M3 y bloqueo M1.

## Indicador

Ejemplo:

```bash
bqrl-pine-export \
  --motor M3 \
  --range-mode R8 \
  --min-bars 2 \
  --max-pending 0
```

Genera por defecto:

```text
exports/BQR_M3_R8_min2_pend0_indicator.pine
```

Las cajas pendientes son amarillas. Para conservar la convención visual del indicador de referencia:

- pivote superior/bajista confirmado: verde;
- pivote inferior/alcista confirmado: rojo.

## Estrategia de verificación

```bash
bqrl-pine-export \
  --motor M3 \
  --range-mode R8 \
  --min-bars 2 \
  --max-pending 0 \
  --strategy
```

Genera:

```text
exports/BQR_M3_R8_min2_pend0_strategy.pine
```

La estrategia usa:

```text
process_orders_on_close = true
pyramiding = 0
```

La primera señal abre posición. Una señal de la misma dirección no reinicia la entrada. La señal contraria cierra/revierte, igual que el benchmark Python.

También dibuja el porcentaje bruto capturado entre ambos cierres:

```text
LONG  = (exit - entry) / entry * 100
SHORT = (entry - exit) / entry * 100
```

## Costos: diferencia deliberada

El backtest Python permite:

```text
BQR_FEE_BPS
BQR_SLIPPAGE_BPS
```

por lado.

TradingView puede representar comisión porcentual, pero su parámetro nativo `slippage` se expresa en **ticks**, no en basis points variables con el precio. Por eso la estrategia exportada fija comisión y slippage nativos a cero y se usa para validar la secuencia de señales/reversiones.

Las decisiones cuantitativas deben seguir usando las métricas del laboratorio Python con el modelo de costos configurado.

## Limitación de compilación

El proyecto genera Pine v6 y lo cubre con tests estructurales, pero el CI no dispone del compilador propietario de TradingView. Cada nueva familia exportada debe probarse al menos una vez en el Pine Editor antes de considerarse validada visualmente.

## Policies y detectores completos

### Baseline/parámetros

Exportación determinista: implementada.

### Policy `accept_signal`

Pendiente: traducir de forma segura el subconjunto AST soportado y generar también las features causales necesarias en Pine.

### `detector_code`

No se debe asumir que Python arbitrario generado dentro del sandbox puede traducirse exactamente a Pine. Para un champion de detector completo se requerirá un artefacto Pine separado y una validación de equivalencia por señales sobre el mismo tramo histórico antes de promoción.
