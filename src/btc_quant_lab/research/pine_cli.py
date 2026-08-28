from __future__ import annotations

import json
from pathlib import Path

import typer

from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.pine_export import export_baseline_pine, export_baseline_strategy_pine
from btc_quant_lab.research.pine_filter_export import export_filtered_pine


def main(
    motor: str = "M1",
    range_mode: str = "R8",
    min_bars: int = 3,
    max_pending: int = 3,
    strategy: bool = False,
    filter_json: str | None = None,
    output: Path | None = None,
):
    """Export a baseline detector, optionally with one causal filter, as Pine v6."""
    cfg = PivotConfig(
        motor=motor,
        range_mode=range_mode,
        min_bars=min_bars,
        max_pending=max_pending,
    )
    if filter_json:
        try:
            filter_spec = json.loads(filter_json)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"filter-json is not valid JSON: {exc}") from exc
        if not isinstance(filter_spec, dict):
            raise typer.BadParameter("filter-json must decode to an object")
        source = export_filtered_pine(cfg, filter_spec, strategy=strategy)
        filtered = "_filtered"
    else:
        source = export_baseline_strategy_pine(cfg) if strategy else export_baseline_pine(cfg)
        filtered = ""

    suffix = "strategy" if strategy else "indicator"
    target = output or Path(
        f"exports/BQR_{cfg.motor}_{cfg.range_mode}_min{cfg.min_bars}_"
        f"pend{cfg.max_pending}{filtered}_{suffix}.pine"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    typer.echo(str(target))


def app():
    typer.run(main)
