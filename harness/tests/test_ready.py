from pathlib import Path

import pytest
from harness import radboards, ready

ROOT = Path(__file__).resolve().parents[2] / "hardware"


def _patch_roots(monkeypatch, tmp_path):
    monkeypatch.setattr(radboards, "ROOT", tmp_path)
    monkeypatch.setattr(
        radboards, "board_path", lambda board_id: ROOT / "boards" / f"{board_id}.yaml"
    )


def test_require_rf_refuses_without_image(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="present stage has not passed"):
        ready.require_rf("hackrf")


def test_require_rf_ok_after_image(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    radboards.write_stage("hackrf", "image", {"status": "pass", "stage": "image"})
    ready.require_rf("hackrf")


def test_require_lessons_needs_both_boards(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    radboards.write_stage("hackrf", "image", {"status": "pass", "stage": "image"})
    with pytest.raises(SystemExit, match="pluto"):
        ready.require_lessons()
    radboards.write_stage("pluto", "image", {"status": "pass", "stage": "image"})
    ready.require_lessons()
