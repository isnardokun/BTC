#!/usr/bin/env bash
set -euo pipefail

IMAGE="${BQR_DETECTOR_SANDBOX_IMAGE:-docker.io/library/python:3.12-slim}"
STATE_DIR=".sandbox"

echo "[1/4] Instalando Podman rootless"
sudo pacman -S --needed podman

echo "[2/4] Verificando Podman"
podman info >/dev/null

echo "[3/4] Descargando explícitamente la imagen confiable del sandbox"
podman pull "$IMAGE"
IMAGE_ID="$(podman image inspect "$IMAGE" --format '{{.Id}}')"

if [[ -z "$IMAGE_ID" ]]; then
  echo "No fue posible resolver el ID de la imagen." >&2
  exit 1
fi

echo "[4/4] Fijando identidad local del sandbox"
mkdir -p "$STATE_DIR"
printf '%s\n' "$IMAGE_ID" > "$STATE_DIR/detector_image_id.txt"
printf '%s\n' "$IMAGE" > "$STATE_DIR/detector_image_name.txt"

echo
echo "Sandbox preparado."
echo "Imagen solicitada: $IMAGE"
echo "ID fijado: $IMAGE_ID"
echo "Estado local: $STATE_DIR/detector_image_id.txt"
echo "Las ejecuciones usarán ese ID con --pull=never y --network=none."
