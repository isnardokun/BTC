# Walk-forward y features causales

## Objetivo

Evitar que el laboratorio elija una configuración porque funciona bien sobre el mismo histórico que se utilizó para ajustarla.

## Procedimiento por defecto en gráfico diario

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

La tabla final muestra:

- trades OOS;
- retorno neto OOS;
- expectancy OOS;
- profit factor OOS;
- max drawdown OOS;
- porcentaje de ventanas rentables;
- frecuencia con la que cada configuración fue seleccionada.

Una configuración interesante debería aparecer repetidamente o pertenecer a una región estable de parámetros. Un único máximo in-sample no es suficiente.

## Features causales

`research/features.py` calcula las features en el momento exacto de confirmación del pivote. Ninguna requiere velas futuras.

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
- régimen `bull`, `bear`, `transition`;
- régimen de volatilidad `normal/high`.

`trade_return_pct` puede acompañar cada fila únicamente como **label de investigación**. Está prohibido utilizarlo como variable de entrada o condición de señal.

## Comandos

```bash
bqrl walk-forward --symbol BTCUSDT --interval 1d
```

```bash
bqrl features --symbol BTCUSDT --interval 1d --motor M1 --range-mode R8 --min-bars 3 --max-pending 3
```

Desde la UI web existen los botones `Walk-forward` e `IA: experimento`.

## Siguiente nivel

El paso posterior es convertir las features en hipótesis medibles, por ejemplo:

> Los pivotes bajistas R8 confirmados durante régimen bull tienen peor expectancy cuando la distancia a EMA50 es pequeña.

La IA puede proponer esa regla, pero deberá probarse en ventanas fuera de muestra antes de incorporarla al detector estable.
