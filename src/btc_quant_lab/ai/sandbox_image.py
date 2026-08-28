from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_DETECTOR_IMAGE = "docker.io/library/python:3.12-slim"
SANDBOX_STATE_DIR = Path(".sandbox")
SANDBOX_IMAGE_ID_FILE = SANDBOX_STATE_DIR / "detector_image_id.txt"
SANDBOX_IMAGE_NAME_FILE = SANDBOX_STATE_DIR / "detector_image_name.txt"


def configured_detector_image() -> str:
    """Return the immutable local image ID prepared for detector execution when available."""
    if SANDBOX_IMAGE_ID_FILE.is_file():
        image_id = SANDBOX_IMAGE_ID_FILE.read_text(encoding="utf-8").strip()
        if image_id:
            return image_id
    return os.environ.get("BQR_DETECTOR_SANDBOX_IMAGE", DEFAULT_DETECTOR_IMAGE).strip()


def local_podman_image_id(image: str) -> str | None:
    """Resolve a local image reference without pulling or contacting a registry."""
    podman = shutil.which("podman")
    if not podman:
        return None
    try:
        completed = subprocess.run(
            [podman, "image", "inspect", image, "--format", "{{.Id}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return None
    if completed.returncode != 0:
        return None
    image_id = completed.stdout.strip()
    return image_id or None


def runtime_default_matches_pinned() -> bool:
    """Ensure legacy/default-tag calls resolve to the same image pinned by setup.

    The deep detector loop currently has a few trusted host-side call sites that still
    invoke `process_sandbox.run_detector_fork()` without an explicit image argument.
    This preflight prevents those calls from silently using a moved tag.
    """
    if not SANDBOX_IMAGE_ID_FILE.is_file():
        return False
    pinned = SANDBOX_IMAGE_ID_FILE.read_text(encoding="utf-8").strip()
    if not pinned:
        return False
    return local_podman_image_id(DEFAULT_DETECTOR_IMAGE) == pinned


def detector_image_metadata() -> dict:
    configured = configured_detector_image()
    image_name = None
    image_id = None
    if SANDBOX_IMAGE_NAME_FILE.is_file():
        image_name = SANDBOX_IMAGE_NAME_FILE.read_text(encoding="utf-8").strip() or None
    if SANDBOX_IMAGE_ID_FILE.is_file():
        image_id = SANDBOX_IMAGE_ID_FILE.read_text(encoding="utf-8").strip() or None
    default_runtime_id = local_podman_image_id(DEFAULT_DETECTOR_IMAGE)
    return {
        "configured_image": configured,
        "image_name": image_name,
        "image_id": image_id,
        "pinned_by_setup": image_id is not None,
        "default_runtime_image_id": default_runtime_id,
        "default_runtime_matches_pinned": bool(image_id and default_runtime_id == image_id),
    }
