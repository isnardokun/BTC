from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DETECTOR_IMAGE = "docker.io/library/python:3.12-slim"
SANDBOX_STATE_DIR = Path(".sandbox")
SANDBOX_IMAGE_ID_FILE = SANDBOX_STATE_DIR / "detector_image_id.txt"
SANDBOX_IMAGE_NAME_FILE = SANDBOX_STATE_DIR / "detector_image_name.txt"


def configured_detector_image() -> str:
    """Return the immutable local image ID prepared for detector execution when available.

    The explicit setup script writes the Podman image ID after pulling the trusted image.
    Using that ID makes later AI runs independent of tag movement. Before setup, this
    function falls back to an explicitly exported image name or the project default.
    """
    if SANDBOX_IMAGE_ID_FILE.is_file():
        image_id = SANDBOX_IMAGE_ID_FILE.read_text(encoding="utf-8").strip()
        if image_id:
            return image_id
    return os.environ.get("BQR_DETECTOR_SANDBOX_IMAGE", DEFAULT_DETECTOR_IMAGE).strip()


def detector_image_metadata() -> dict:
    configured = configured_detector_image()
    image_name = None
    image_id = None
    if SANDBOX_IMAGE_NAME_FILE.is_file():
        image_name = SANDBOX_IMAGE_NAME_FILE.read_text(encoding="utf-8").strip() or None
    if SANDBOX_IMAGE_ID_FILE.is_file():
        image_id = SANDBOX_IMAGE_ID_FILE.read_text(encoding="utf-8").strip() or None
    return {
        "configured_image": configured,
        "image_name": image_name,
        "image_id": image_id,
        "pinned_by_setup": image_id is not None,
    }
