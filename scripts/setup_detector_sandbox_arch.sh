#!/usr/bin/env bash
set -euo pipefail

IMAGE="${BQR_DETECTOR_SANDBOX_IMAGE:-docker.io/library/python:3.12-slim}"

echo "[1/3] Instalando Podman rootless"
sudo pacman -S --needed podman

echo "[2/3] Verificando Podman"
podman info >/dev/null

echo "[3/3] Descargando imagen confiable del sandbox"
podman pull "$IMAGE"
podman image inspect "$IMAGE" --format '{{.Id}}'

echo
echo "Sandbox preparado."
echo "Imagen: $IMAGE"
echo "Las ejecuciones del research lab usarán --pull=never y --network=none."
