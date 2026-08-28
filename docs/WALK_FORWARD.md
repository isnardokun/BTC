# Walk-forward, Purged+Embargo y features causales

## Objetivo

Evitar que el laboratorio elija una configuración porque funciona bien sobre el mismo histórico que se utilizó para ajustarla, y reducir además la dependencia artificial entre observaciones pegadas al límite train/test.

## Walk-forward estándar

Configuración por defecto en gráfico diario:

- entrenamiento: 1095 barras (~3 años);
- prueba: 365 barras (~1 año);
- avance: 365 barras;
- las ventanas de prueba no se superponen.

En cada ciclo:

1. el optimizador evalúa las 96 configuraciones únicamente sobre `train`;
2. selecciona una configuración;
3. esa configuración queda congelada;
4. se reconstruyen señales causalmente hasta el final de `test`;
5. solo se contabilizan operaciones cuya entrada y salida ocurren dentro de `test`;
6. se avanza al siguiente período.

## Purged + Embargo

`purged_walk_forward()` añade dos separaciones adicionales:

- `purge_bars`: elimina las últimas barras del train antes de seleccionar parámetros;
- `embargo_bars`: deja un hueco completamente fuera de train y test antes de iniciar la evaluación OOS.

Esquema:

```text
TRAIN USADO | PURGE | EMBARGO | TEST OOS
```

El objetivo es comprobar si una aparente ventaja depende demasiado de la proximidad temporal de los datos alrededor de la frontera. No sustituye el holdout final invisible del research loop.

Comando:

```bash
bqrl purged-walk-forward --symbol BTCUSDT --interval 1d --purge-bars 5 --embargo-bars 5
```

## Métricas

Ambos métodos reportan:

- trades OOS;
- retorno compuesto OOS;
- expectancy OOS;
- profit factor OOS;
- max drawdown OOS;
- porcentaje de ventanas rentables;
- frecuencia con la que cada configuración fue seleccionada.

Una configuración interesante debería aparecer repetidamente o pertenecer a una región estable de parámetros. Un único máximo in-sample no es suficiente.

## Features causales

`research/features.py` calcula las features en el momento exacto de confirmación del pivote. Ninguna requiere velas posteriores al instante en que la feature queda disponible.

Incluye:

- ATR14 y ATR %;
- volatilidad realizada 20 barras;
- z-score de volumen 20 barras;
- cuerpo/ATR;
- rango de vela/ATR;
- rango de la señal/ATR;
- distancia a EMA20, EMA50 y EMA200;
- separación EMA20 vs EMA50;
- cantidad de velas consecutivas previas;
- régimen EMA `bull`, `bear`, `transition`;
- régimen de volatilidad `normal/high`.

### Estructura HH/HL/LH/LL

La estructura no usa swings retrospectivos perfectos. Usa fractales confirmados con retraso causal. Un swing situado en `k` se incorpora al estado únicamente después de cerrar las barras derechas necesarias para confirmarlo.

Features:

- `last_swing_high_type`: H, HH, LH, EH;
- `last_swing_low_type`: L, HL, LL, EL;
- `market_structure`: bull, bear, transition, unknown;
- `structure_break`: bullish_bos, bearish_bos, none;
- `bars_since_swing_high`;
- `bars_since_swing_low`;
- distancia al swing alto/bajo en porcentaje;
- distancia al swing alto/bajo en ATR.

Interpretación base:

```text
HH + HL → estructura bull
LH + LL → estructura bear
otras combinaciones → transition
```

Estas variables permiten probar hipótesis como:

> Ignorar un pivote bajista mientras HH+HL sigue intacto, salvo que ya exista bearish BOS.

La hipótesis debe validarse OOS; no se incorpora por intuición visual.

## Label futuro

`trade_return_pct` puede acompañar cada fila únicamente como **label de investigación**. Está prohibido utilizarlo como variable de entrada o condición de señal.

## Comandos

```bash
bqrl walk-forward --symbol BTCUSDT --interval 1d
bqrl purged-walk-forward --symbol BTCUSDT --interval 1d
bqrl features --symbol BTCUSDT --interval 1d --motor M1 --range-mode R8 --min-bars 3 --max-pending 3
```

Desde la UI web existen controles separados para `Walk-forward` y `Purged + Embargo`, y el panel de contexto muestra rendimiento por estructura de mercado y BOS.
