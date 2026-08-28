# Investigador IA

La IA dispone programáticamente de histórico, señales, trades, métricas, configuraciones, walk-forward, regímenes, sensibilidad, Monte Carlo, benchmark y experimentos previos.

## Ciclo autónomo actual

`ai/research_loop.py` implementa:

1. construir baseline;
2. medirlo fuera de muestra;
3. calcular sensibilidad/meseta del espacio de parámetros;
4. entregar a MiniMax champion, ranking, OOS, regímenes y robustez;
5. formular una hipótesis falsable;
6. proponer parámetros, filtro causal o política de código restringido;
7. ejecutar automáticamente el candidato;
8. medir full history + OOS + años + Buy & Hold + Monte Carlo;
9. exigir mejora de `robustness_score`;
10. enviar el candidato a un **agente crítico independiente**;
11. promoverlo solamente si el crítico devuelve `approve`;
12. registrar aceptación/rechazo y continuar.

## Parámetros

La familia experimental base sigue siendo:

- M1 / M3;
- R4 / R7 / R8;
- min bars 2–5;
- max pending 0 / 3 / 5 / 8.

## Filtros causales

La IA puede probar condiciones sobre features calculadas al confirmar el pivote, entre ellas:

- ATR %;
- volatilidad realizada;
- volumen z-score;
- cuerpo/rango normalizado por ATR;
- distancia a EMA20/50/200;
- régimen bull/bear/transition;
- régimen de volatilidad.

`trade_return_pct` está excluido porque es un label futuro.

## Sandbox de código ejecutable

Los forks de código de esta fase implementan una política de aceptación de señales:

```python
def accept_signal(signal, features):
    if signal["direction"] == -1:
        return features["distance_ema50_pct"] > 5 and features["atr_pct"] > 2
    return features["trend_regime"] != "bull"
```

El AST se valida antes de compilarse. Se prohíben:

- imports;
- llamadas a funciones;
- acceso a atributos;
- archivos;
- red;
- loops;
- comprehensions;
- dunder names.

Se permiten únicamente operaciones deterministas sobre `signal` y `features` causales. El código se ejecuta con `__builtins__` vacío.

Esto **no es todavía un sandbox para reemplazar arbitrariamente todo el detector**. Es un primer sandbox ejecutable para permitir que la IA escriba reglas nuevas sin darle capacidad de ejecutar código general del sistema.

## Agente crítico

`ai/critic.py` no propone estrategias. Revisa al candidato contra el champion usando:

- resultados OOS;
- tamaño de muestra;
- drawdown;
- consistencia anual;
- Monte Carlo;
- benchmark;
- sensibilidad/meseta.

Una mejora matemática sin aprobación del crítico no se promueve.

## Robustness score

Combina:

- expectancy OOS;
- profit factor OOS;
- tamaño de muestra;
- porcentaje de ventanas rentables;
- penalización por drawdown.

Es una heurística de ranking, no una prueba de significancia.

## Ejecución

```bash
bqrl ai-research --symbol BTCUSDT --interval 1d --iterations 3
```

La interfaz web expone `IA autónoma ×3` y el panel `Robustez`.

## Objetivo

Encontrar reglas simples y reproducibles que aumenten la captura de movimientos sostenidos después de una señal, reduciendo ruido, reversión prematura y sobreajuste.
