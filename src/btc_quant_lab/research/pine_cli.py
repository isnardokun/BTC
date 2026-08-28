from __future__ import annotations

import json
from pathlib import Path

import typer

from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.pine_export import export_baseline_pine, export_baseline_strategy_pine
from btc_quant_lab.research.pine_filter_export import export_filtered_pine
from btc_quant_lab.research.pine_policy_export import export_policy_pine


def main(
    motor: str = "M1",
    range_mode: str = "R8",
    min_bars: int = 3,
    max_pending: int = 3,
    strategy: bool = False,
    filter_json: str | None = None,
    policy_file: Path | None = None,
    output: Path | None = None,
):
    """Export baseline, declarative filter, or safe AST policy as Pine v6."""
    if filter_json and policy_file is not None:
        raise typer.BadParameter("use either --filter-json or --policy-file, not both")

    cfg = PivotConfig(
        motor=motor,
        range_mode=range_mode,
        min_bars=min_bars,
        max_pending=max_pending,
    )
    flavor = ""
    if policy_file is not None:
        if not policy_file.is_file():
            raise typer.BadParameter(f"policy file does not exist: {policy_file}")
        source = export_policy_pine(
            cfg,
            policy_file.read_text(encoding="utf-8"),
            strategy=strategy,
        )
        flavor = "_policy"
    elif filter_json:
        try:
            filter_spec = json.loads(filter_json)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"filter-json is not valid JSON: {exc}") from exc
        if not isinstance(filter_spec, dict):
            raise typer.BadParameter("filter-json must decode to an object")
        source = export_filtered_pine(cfg, filter_spec, strategy=strategy)
        flavor = "_filtered"
    else:
        source = export_baseline_strategy_pine(cfg) if strategy else export_baseline_pine(cfg)

    suffix = "strategy" if strategy else "indicator"
    target = output or Path(
        f"exports/BQR_{cfg.motor}_{cfg.range_mode}_min{cfg.min_bars}_"
        f"pend{cfg.max_pending}{flavor}_{suffix}.pine"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    typer.echo(str(target))


def app():
    typer.run(main)
