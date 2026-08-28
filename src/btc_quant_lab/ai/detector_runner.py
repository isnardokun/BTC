from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REQUEST = Path("/input/request.json")
VARIANT = Path("/workspace/detector_variant.py")
OUTPUT = Path("/output/result.json")

REQUIRED_SIGNAL_FIELDS = {
    "ts",
    "direction",
    "top",
    "bottom",
    "candidate_ts",
    "confirm_price",
    "bars_to_confirm",
}


def _load_variant():
    spec = importlib.util.spec_from_file_location("detector_variant", VARIANT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load detector_variant.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    detect = getattr(module, "detect", None)
    if not callable(detect):
        raise TypeError("detector_variant.py must define detect(candles, config)")
    return detect


def _validate_output(raw) -> list[dict]:
    if not isinstance(raw, list):
        raise TypeError("detect() must return a list")
    if len(raw) > 100_000:
        raise ValueError("detector returned too many signals")

    validated: list[dict] = []
    previous_ts = -1
    for item in raw:
        if not isinstance(item, dict):
            raise TypeError("every signal must be a dict")
        if not REQUIRED_SIGNAL_FIELDS.issubset(item):
            missing = sorted(REQUIRED_SIGNAL_FIELDS - set(item))
            raise ValueError(f"signal missing fields: {missing}")

        direction = int(item["direction"])
        if direction not in {-1, 1}:
            raise ValueError("direction must be -1 or 1")
        ts = int(item["ts"])
        candidate_ts = int(item["candidate_ts"])
        if ts < previous_ts:
            raise ValueError("signals must be sorted by ts")
        if candidate_ts > ts:
            raise ValueError("candidate_ts cannot be after confirmation ts")

        top = float(item["top"])
        bottom = float(item["bottom"])
        if top < bottom:
            raise ValueError("signal top cannot be below bottom")

        validated.append(
            {
                "ts": ts,
                "direction": direction,
                "top": top,
                "bottom": bottom,
                "candidate_ts": candidate_ts,
                "confirm_price": float(item["confirm_price"]),
                "bars_to_confirm": int(item["bars_to_confirm"]),
            }
        )
        previous_ts = ts
    return validated


def main() -> None:
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    candles = request.get("candles")
    config = request.get("config", {})
    if not isinstance(candles, list):
        raise TypeError("request candles must be a list")
    if not isinstance(config, dict):
        raise TypeError("request config must be a dict")

    detect = _load_variant()
    signals = _validate_output(detect(candles, config))
    OUTPUT.write_text(json.dumps({"signals": signals}), encoding="utf-8")


if __name__ == "__main__":
    main()
