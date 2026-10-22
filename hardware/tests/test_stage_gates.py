from pathlib import Path

import pytest
from harness import radboards
from hardware import stages as stage

ROOT = Path(__file__).resolve().parents[1]


def _patch_roots(monkeypatch, tmp_path):
    monkeypatch.setattr(radboards, "ROOT", tmp_path)
    monkeypatch.setattr(
        radboards, "board_path", lambda board_id: ROOT / "boards" / f"{board_id}.yaml"
    )


def test_gate_unknown_board():
    with pytest.raises(SystemExit, match="unknown target"):
        stage.gate("nope", "present")


def test_refuse_workflow_without_present(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="present stage has not passed"):
        stage.gate("hackrf", "workflow")
    record = radboards.read_stages("hackrf")["stages"].get("workflow") or {}
    assert record.get("status") == "fail"


def test_refuse_pluto_until_hackrf_image(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="hackrf image stage has not passed"):
        stage.gate("pluto", "present")


def test_image_requires_loopback_env(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    radboards.write_stage("hackrf", "present", {"status": "pass", "stage": "present"})
    radboards.write_stage("hackrf", "workflow", {"status": "pass", "stage": "workflow"})
    monkeypatch.delenv("HUMAN_LOOPBACK", raising=False)
    with pytest.raises(SystemExit, match="HUMAN_LOOPBACK"):
        stage.gate("hackrf", "image")


def test_image_gate_ok_with_loopback(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    radboards.write_stage("hackrf", "present", {"status": "pass", "stage": "present"})
    radboards.write_stage("hackrf", "workflow", {"status": "pass", "stage": "workflow"})
    monkeypatch.setenv("HUMAN_LOOPBACK", "1")
    board = stage.gate("hackrf", "image")
    assert board["id"] == "hackrf"


def test_pluto_allowed_after_hackrf_image(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    radboards.write_stage("hackrf", "image", {"status": "pass", "stage": "image"})
    board = stage.gate("pluto", "present")
    assert board["id"] == "pluto"
