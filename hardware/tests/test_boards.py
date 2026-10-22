from harness import radboards


def test_load_hackrf():
    board = radboards.load_board("hackrf")
    assert board["id"] == "hackrf"
    assert board["usb_vendor"] == "1d50"
    assert board["requires_env"] == "HUMAN_LOOPBACK"
    assert board["txvga_db"] <= board["max_tx_db"]


def test_order_pluto_first():
    assert radboards.ORDER[0] == "pluto"
    assert "hackrf" in radboards.ORDER
    assert radboards.load_board("pluto")["loopback_mode"] == "same_board"
    assert radboards.load_board("hackrf")["loopback_mode"] == "crossboard"
    assert radboards.load_board("hackrf")["partner_board"] == "pluto"


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
