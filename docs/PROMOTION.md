# Protocolo de promoción de champions

## Objetivo

Separar claramente tres estados:

1. **champion de investigación**: mejor variante aceptada dentro de una sesión;
2. **eligible_for_review**: superó gates cuantitativos mínimos y puede ser revisada;
3. **stable**: versión explícitamente aprobada y congelada para uso posterior.

`eligible_for_review` **no significa** recomendación de trading ni despliegue automático.

## Manifest

Al terminar `bqrl ai-research`, el research loop crea:

```text
experiments/promotions/<promotion_id>.json
```

El manifest contiene:

- configuración y/o política del champion;
- protocolo de investigación;
- modelo de fees/slippage;
- OOS de desarrollo;
- holdout final invisible durante las iteraciones;
- Monte Carlo del holdout;
- comparación Buy & Hold;
- meseta de parámetros;
- gates aprobados/fallidos;
- advertencias.

## Gates actuales

Para quedar `eligible_for_review` se exige como mínimo:

- muestra mínima OOS de desarrollo;
- expectancy OOS positiva;
- Profit Factor OOS > 1;
- consistencia mínima entre ventanas;
- muestra mínima en holdout;
- expectancy positiva en holdout;
- Profit Factor > 1 en holdout;
- retorno compuesto positivo en holdout;
- drawdown del holdout dentro del límite;
- soporte Monte Carlo cuando existe muestra suficiente;
- confirmación de que el holdout no fue expuesto a los agentes durante la investigación.

## Advertencias que no son gates automáticos

Actualmente se registran, pero no bloquean por sí solas:

- meseta de parámetros frágil;
- underperformance frente a Buy & Hold;
- falta de muestra suficiente para Monte Carlo.

Estas advertencias deben pesar en la revisión humana/harness.

## Stable

El sistema **no crea ni mueve una rama/tag `stable` automáticamente**.

Antes de promover una variante debe verificarse:

1. CI verde;
2. manifest `eligible_for_review`;
3. coherencia entre OOS estándar y Purged+Embargo;
4. ausencia de dependencia extrema de un solo régimen;
5. costos realistas;
6. ausencia de lookahead;
7. revisión del diff de estrategia si existe código experimental;
8. decisión explícita de promoción.

Después de esa revisión se podrá implementar una acción separada de promoción a `stable` y, posteriormente, el exportador Pine.
