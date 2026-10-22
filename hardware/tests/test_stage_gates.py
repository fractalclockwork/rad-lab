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


def test_allow_present_on_both_boards_independently(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    pluto = stage.gate("pluto", "present")
    hackrf = stage.gate("hackrf", "present")
    assert pluto["id"] == "pluto"
    assert hackrf["id"] == "hackrf"


def test_refuse_hackrf_image_until_pluto_image(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    radboards.write_stage("hackrf", "present", {"status": "pass", "stage": "present"})
    radboards.write_stage("hackrf", "workflow", {"status": "pass", "stage": "workflow"})
    monkeypatch.setenv("HUMAN_LOOPBACK", "1")
    with pytest.raises(SystemExit, match="pluto image stage has not passed"):
        stage.gate("hackrf", "image")


def test_image_requires_loopback_env(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    radboards.write_stage("pluto", "present", {"status": "pass", "stage": "present"})
    radboards.write_stage("pluto", "workflow", {"status": "pass", "stage": "workflow"})
    monkeypatch.delenv("HUMAN_LOOPBACK", raising=False)
    with pytest.raises(SystemExit, match="HUMAN_LOOPBACK"):
        stage.gate("pluto", "image")


def test_image_gate_ok_with_loopback(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    radboards.write_stage("pluto", "present", {"status": "pass", "stage": "present"})
    radboards.write_stage("pluto", "workflow", {"status": "pass", "stage": "workflow"})
    monkeypatch.setenv("HUMAN_LOOPBACK", "1")
    board = stage.gate("pluto", "image")
    assert board["id"] == "pluto"


def test_hackrf_image_allowed_after_pluto_image(tmp_path, monkeypatch):
    _patch_roots(monkeypatch, tmp_path)
    radboards.write_stage("pluto", "image", {"status": "pass", "stage": "image"})
    radboards.write_stage("hackrf", "present", {"status": "pass", "stage": "present"})
    radboards.write_stage("hackrf", "workflow", {"status": "pass", "stage": "workflow"})
    monkeypatch.setenv("HUMAN_LOOPBACK", "1")
    board = stage.gate("hackrf", "image")
    assert board["id"] == "hackrf"
