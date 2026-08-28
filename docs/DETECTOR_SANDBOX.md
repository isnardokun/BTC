# Sandbox de mutaciones completas del detector

## Propósito

El sandbox AST existente permite a la IA modificar una política de aceptación de señales. El sandbox de proceso permite un nivel superior: un fork puede implementar un detector completo en `detector_variant.py`.

Ese código **no se ejecuta directamente en el host**.

## Preparación en CachyOS / Arch

```bash
bash scripts/setup_detector_sandbox_arch.sh
```

El script instala Podman y descarga explícitamente la imagen confiable:

```text
docker.io/library/python:3.12-slim
```

Después guarda localmente el **ID inmutable** resuelto por Podman en:

```text
.sandbox/detector_image_id.txt
```

Las ejecuciones generadas por IA usan `--pull=never` y `--network=none`. Además, antes de iniciar Deep Detector Research el preflight comprueba que el tag default todavía apunta exactamente al ID fijado. Si el tag cambió, el modo profundo se niega a ejecutar hasta repetir el setup.

Las imágenes personalizadas están deliberadamente deshabilitadas en esta fase para impedir que distintas rutas internas del research loop terminen usando entornos diferentes. Se podrán reactivar cuando absolutamente todos los call sites reciban el ID explícito.

## Contrato del plugin

Cada fork de detector vive en:

```text
experiments/forks/<id>/detector_variant.py
```

y debe definir:

```python
def detect(candles, config):
    return signals
```

`candles` es una lista cronológica de diccionarios con:

```text
ts, open, high, low, close, volume
```

Cada señal devuelta debe contener:

```text
ts
direction              # +1 long, -1 short
top
bottom
candidate_ts
confirm_price
bars_to_confirm
```

## Frontera de seguridad

El proceso se ejecuta con Podman rootless y:

- red deshabilitada;
- root filesystem read-only;
- capabilities eliminadas;
- `no-new-privileges`;
- namespace de usuario rootless;
- límite de memoria;
- límite de CPU;
- límite de PIDs;
- `/tmp` pequeño y aislado;
- fork montado solo lectura;
- input montado solo lectura;
- únicamente `result.json` es escribible;
- timeout desde el host;
- ninguna carpeta personal del host se monta dentro del contenedor.

El aislamiento reduce de forma importante la superficie de riesgo, pero Podman y la imagen deben mantenerse actualizados.

## Defensa contra lookahead

El aislamiento del proceso no basta: un detector podría leer todo el histórico recibido y modificar señales pasadas utilizando velas futuras.

Por eso hay controles separados.

### Integridad de mercado

Una señal solo se acepta si:

- `ts` corresponde a una vela real;
- `candidate_ts` corresponde a una vela real;
- `candidate_ts <= ts`;
- `bars_to_confirm` coincide con la distancia real entre ambas velas;
- `confirm_price` coincide con el cierre real de la vela de confirmación;
- los precios son finitos;
- las señales están cronológicamente ordenadas.

### Prefix invariance

El mismo detector se ejecuta sobre prefijos crecientes:

```text
histórico A
histórico A + futuro B
histórico A + futuro B + futuro C
```

Las señales cuya confirmación pertenecía a `A` deben ser idénticas en todas las ejecuciones posteriores.

Si una señal pasada cambia al añadir futuro, el fork falla la auditoría causal y se descarta antes del scoring.

La comprobación vuelve a realizarse al pasar de `development` al histórico completo antes de medir el holdout final. Esto evita que un detector cambie artificialmente su historia solo cuando detecta una longitud de dataset mayor.

## Evaluación cuantitativa

Un `detector_code` debe superar varias capas:

1. ejecución aislada;
2. validación de señales contra OHLCV real;
3. auditoría causal por prefijos;
4. backtest completo de development;
5. OOS cronológico ejecutando solo datos disponibles hasta cada ventana;
6. OOS con zona excluida Purge + Embargo alrededor de las fronteras;
7. análisis por régimen/estructura;
8. comparación contra champion;
9. revisión de un agente crítico independiente;
10. holdout final oculto durante las iteraciones;
11. manifest de promoción, sin crear `stable` automáticamente.

## Deep Detector Research

Este flujo está deliberadamente separado del loop web estable mientras validamos Podman en hardware real.

Después de sincronizar BTC y configurar MiniMax:

```bash
bash scripts/setup_detector_sandbox_arch.sh
source .venv/bin/activate
bqrl-detector-research \
  --symbol BTCUSDT \
  --interval 1d \
  --iterations 3 \
  --min-trades 10
```

Cada iteración exige `proposal_type = detector_code`. MiniMax crea un `detector_variant.py`, el sistema lo ejecuta en el contenedor y registra el resultado en:

```text
experiments/forks/<experiment_id>/
├── manifest.json
├── hypothesis.md
├── detector_variant.py
└── result.json
```

Si un candidato se convierte en champion, el holdout final se evalúa una sola vez al terminar las iteraciones. El resultado genera además un manifest en:

```text
experiments/promotions/<promotion_id>.json
```

`eligible_for_review` sigue significando únicamente **candidato para revisión**, no estrategia aprobada para operar.

## Estado actual

Implementado:

- sandbox rootless de proceso;
- identidad de imagen fijada por ID local;
- contrato de plugin `detect(candles, config)`;
- validación de mercado;
- auditoría prefix-invariance;
- OOS del detector mutado;
- OOS con Purge + Embargo;
- research loop autónomo exclusivo para `detector_code`;
- crítico independiente;
- holdout final con auditoría development→full;
- manifest de promoción.

Pendiente antes de fusionarlo con el botón principal de la UI:

- ejecutar pruebas reales de Podman en CachyOS;
- medir tiempos/consumo de 1, 3 y 10 iteraciones;
- revisar al menos varios forks generados por MiniMax;
- endurecer límites si la telemetría local lo aconseja;
- después integrar el modo profundo en la interfaz web.
