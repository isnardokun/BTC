#!/usr/bin/env bash
set -euo pipefail
sudo pacman -S --needed --noconfirm python python-pip git curl base-devel
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
uv venv .venv
source .venv/bin/activate
uv sync --extra dev
mkdir -p data experiments/forks
[ -f .env ] || cp .env.example .env
echo "Listo. Ejecuta:"
echo "source .venv/bin/activate"
echo "bqrl sync --symbol BTCUSDT --interval 1d"
echo "bqrl optimize --symbol BTCUSDT --interval 1d"
echo "bqrl serve"
