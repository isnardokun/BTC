# Investigador IA

La IA dispone programáticamente de histórico, señales, trades, métricas, configuraciones y experimentos previos.

## Ciclo
1. observar;
2. detectar patrón de fallos/éxitos;
3. formular hipótesis falsable;
4. crear experimento;
5. medir;
6. comparar con baseline;
7. registrar conclusión;
8. opcionalmente crear fork de código.

## Forks
`experiments/forks/<id>/` contiene `manifest.json`, `hypothesis.md`, `strategy_variant.py` opcional y resultados.

## Objetivo
Encontrar reglas simples y reproducibles que aumenten la probabilidad de movimientos sostenidos después de una señal, reduciendo ruido y reversión prematura.
