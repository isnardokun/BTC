# CachyOS / Arch Linux

```bash
chmod +x scripts/bootstrap_arch.sh
./scripts/bootstrap_arch.sh
source .venv/bin/activate
bqrl sync --symbol BTCUSDT --interval 1d
bqrl optimize --symbol BTCUSDT --interval 1d
bqrl serve
```

Tests:
```bash
pytest
```

Lint:
```bash
ruff check .
```
