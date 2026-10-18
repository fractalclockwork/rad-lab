from pathlib import Path

import radboards


def test_load_hackrf():
    board = radboards.load_board("hackrf")
    assert board["id"] == "hackrf"
    assert board["usb_vendor"] == "1d50"
    assert board["requires_env"] == "HIL_LOOPBACK"
    assert board["txvga_db"] <= board["max_tx_db"]


def test_order_hackrf_first():
    assert radboards.ORDER[0] == "hackrf"
    assert "pluto" in radboards.ORDER


def test_primary_image_path():
    board = radboards.load_board("hackrf")
    path = radboards.primary_image_path(board)
    assert path["id"] == "tx-rx-loopback"


def test_stage_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(radboards, "ROOT", tmp_path)
    radboards.write_stage("hackrf", "present", {"status": "pass", "stage": "present"})
    assert radboards.stage_passed("hackrf", "present")
    assert not radboards.stage_passed("hackrf", "image")
    assert (tmp_path / "reports" / "hackrf" / "stage.json").is_file()
