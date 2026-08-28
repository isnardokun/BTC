from pathlib import Path

from btc_quant_lab.ai import sandbox_image


def test_configured_image_prefers_pinned_id(tmp_path: Path, monkeypatch):
    id_file = tmp_path / "detector_image_id.txt"
    name_file = tmp_path / "detector_image_name.txt"
    id_file.write_text("sha256:abc123\n", encoding="utf-8")
    name_file.write_text("example/python:3.12\n", encoding="utf-8")

    monkeypatch.setattr(sandbox_image, "SANDBOX_IMAGE_ID_FILE", id_file)
    monkeypatch.setattr(sandbox_image, "SANDBOX_IMAGE_NAME_FILE", name_file)
    monkeypatch.setenv("BQR_DETECTOR_SANDBOX_IMAGE", "other/image:latest")

    assert sandbox_image.configured_detector_image() == "sha256:abc123"
    metadata = sandbox_image.detector_image_metadata()
    assert metadata["image_name"] == "example/python:3.12"
    assert metadata["image_id"] == "sha256:abc123"
    assert metadata["pinned_by_setup"] is True


def test_configured_image_uses_explicit_environment_before_setup(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        sandbox_image,
        "SANDBOX_IMAGE_ID_FILE",
        tmp_path / "missing-id.txt",
    )
    monkeypatch.setattr(
        sandbox_image,
        "SANDBOX_IMAGE_NAME_FILE",
        tmp_path / "missing-name.txt",
    )
    monkeypatch.setenv("BQR_DETECTOR_SANDBOX_IMAGE", "example/pinned:local")

    assert sandbox_image.configured_detector_image() == "example/pinned:local"
