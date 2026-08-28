# Sandbox de mutaciones completas del detector

## Propósito

El sandbox AST existente permite a la IA modificar únicamente una política de aceptación de señales. El sandbox de proceso permite un nivel superior: un fork puede implementar un detector completo en `detector_variant.py`.

Ese código **no se ejecuta directamente en el host**.

## Requisitos

En CachyOS / Arch:

```bash
bash scripts/setup_detector_sandbox_arch.sh
```

Esto instala Podman y descarga explícitamente la imagen confiable configurada. Las ejecuciones posteriores usan:

```text
--pull=never
--network=none
```

por lo que un fork generado por IA no puede provocar una descarga de imagen ni acceder a red durante su ejecución.

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
- todas las capabilities eliminadas;
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

Esto reduce de forma importante la superficie de riesgo, pero no convierte código no confiable en matemáticamente seguro. La imagen y Podman deben mantenerse actualizados.

## Defensa contra lookahead

El aislamiento del proceso no basta: un detector podría leer todo el histórico recibido y modificar señales pasadas usando velas futuras.

Por eso existen dos controles adicionales.

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

Si una señal pasada cambia al añadir futuro, el fork falla la auditoría causal.

## OOS de un detector mutado

`evaluate_detector_fork_oos()` ejecuta cada ventana con un prefijo que termina exactamente al final de ese test. Nunca entrega al detector velas posteriores a la ventana que está evaluando y compara la invariancia de señales entre prefijos consecutivos.

Solo después de superar esa capa puede un detector completo compararse con el baseline.

## Estado

La infraestructura de aislamiento, contrato, validación de mercado y auditoría causal está implementada. La siguiente integración es permitir que el agente proponga `proposal_type = detector_code` únicamente cuando `sandbox_ready()` confirme que Podman y la imagen local están disponibles.
