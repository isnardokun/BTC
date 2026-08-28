from __future__ import annotations

from pathlib import Path

import typer

from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.pine_export import export_baseline_pine, export_baseline_strategy_pine


def main(
    motor: str = "M1",
    range_mode: str = "R8",
    min_bars: int = 3,
    max_pending: int = 3,
    strategy: bool = False,
    output: Path | None = None,
):
    """Export one baseline detector configuration as Pine Script v6."""
    cfg = PivotConfig(
        motor=motor,
        range_mode=range_mode,
        min_bars=min_bars,
        max_pending=max_pending,
    )
    source = export_baseline_strategy_pine(cfg) if strategy else export_baseline_pine(cfg)
    suffix = "strategy" if strategy else "indicator"
    target = output or Path(
        f"exports/BQR_{cfg.motor}_{cfg.range_mode}_min{cfg.min_bars}_"
        f"pend{cfg.max_pending}_{suffix}.pine"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    typer.echo(str(target))


def app():
    typer.run(main)
