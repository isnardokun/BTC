# Investigador IA

La IA dispone programáticamente de histórico, señales, trades, métricas, configuraciones, walk-forward, regímenes y experimentos previos.

## Ciclo autónomo actual

`ai/research_loop.py` implementa:

1. construir baseline;
2. medirlo fuera de muestra;
3. entregar a MiniMax el champion, ranking in-sample, OOS y regímenes;
4. formular una hipótesis falsable;
5. proponer parámetros, filtro causal o código;
6. ejecutar automáticamente parámetros/filtros;
7. comparar el `robustness_score` contra el champion;
8. registrar `accepted_candidate`, `rejected` o `invalid_proposal`;
9. repetir la siguiente iteración usando el nuevo champion si mejoró.

## Parámetros

Las propuestas de parámetros se restringen a la familia experimental vigente:

- M1 / M3;
- R4 / R7 / R8;
- min bars 2–5;
- max pending 0 / 3 / 5 / 8.

## Filtros causales

La IA también puede probar condiciones sobre features calculadas en la confirmación, entre ellas:

- ATR %;
- volatilidad realizada;
- volumen z-score;
- cuerpo/rango normalizado por ATR;
- distancia a EMA20/50/200;
- régimen bull/bear/transition;
- régimen de volatilidad.

La variable `trade_return_pct` está explícitamente excluida de las features permitidas porque contiene información futura.

## Robustness score

El score de investigación combina:

- expectancy OOS;
- profit factor OOS;
- tamaño de muestra;
- porcentaje de ventanas rentables;
- penalización por drawdown.

Su función es ordenar experimentos, no demostrar significancia estadística.

## Forks de código

`experiments/forks/<id>/` contiene el manifiesto, hipótesis y `strategy_variant.py` cuando MiniMax propone modificar código.

Por seguridad, el código arbitrario generado por el modelo **todavía no se ejecuta automáticamente**. La evaluación queda `awaiting_sandbox`. El siguiente hito es un sandbox aislado con timeout, interfaz restringida y tests obligatorios.

## Ejecución

Una iteración:

```bash
bqrl ai-iterate --symbol BTCUSDT --interval 1d
```

Bucle autónomo de tres experimentos:

```bash
bqrl ai-research --symbol BTCUSDT --interval 1d --iterations 3
```

En la interfaz web existe el botón `IA autónoma ×3`.

## Objetivo

Encontrar reglas simples y reproducibles que aumenten la capacidad de capturar movimientos sostenidos después de una señal, reduciendo ruido, reversión prematura y sobreajuste.
