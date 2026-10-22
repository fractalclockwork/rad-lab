from hardware import loopback
from harness import radboards


def test_simulated_loopback_records_snr():
    pluto = radboards.load_board("pluto")
    records = loopback.run_loopback(pluto, simulate=True)
    assert len(records) == 1
    assert records[0]["sent"] == "CW_TONE"
    assert records[0]["mode"] == "simulated"
    assert records[0]["snr_db"] >= pluto["min_snr_db"]
    assert records[0]["verdict"]["pass"] is True

    hackrf = radboards.load_board("hackrf")
    cb_records = loopback.run_loopback(hackrf, simulate=True)
    assert len(cb_records) == 2
    assert cb_records[0]["sent"] == "CW_TONE_TX_HACKRF_RX_PLUTO"
    assert cb_records[1]["sent"] == "CW_TONE_TX_PLUTO_RX_HACKRF"
    assert all(r["mode"] == "simulated" and r["verdict"]["pass"] is True for r in cb_records)


def test_container_loopback_runs_in_container(monkeypatch):
    import json as _json
    import subprocess as _subprocess

    board = radboards.load_board("pluto")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        payload = _json.dumps(
            {"status": "pass", "records": [{"sent": "CW_TONE", "mode": "hardware"}]}
        )
        return _subprocess.CompletedProcess(cmd, 0, stdout=payload, stderr="")

    monkeypatch.setattr(loopback.subprocess, "run", fake_run)
    records = loopback.run_loopback(dict(board), simulate=False)
    cmd = captured["cmd"]
    assert cmd[0] == "docker"
    assert "RAD_LAB_CONTAINER=1" in cmd
    assert loopback.devices.IMAGE_NAME in cmd
    entry = cmd[cmd.index(loopback.devices.IMAGE_NAME) + 1 :]
    assert entry[0] == "python3"
    assert entry[1].endswith("_container_loopback.py")
    assert "/work/hardware/" in entry[1]
    assert records == [{"sent": "CW_TONE", "mode": "hardware"}]


def test_tone_peak_must_match_offset():
    loopback.assert_tone_peak({"snr_db": 30.0, "peak_hz": 100000.0}, 100000.0)
    try:
        loopback.assert_tone_peak({"snr_db": 12.0, "peak_hz": 0.0}, 100000.0)
    except AssertionError:
        pass
    else:
        raise AssertionError("expected peak offset failure")


def test_tx_gain_clamp():
    board = radboards.load_board("hackrf")
    ok = dict(board)
    ok["txvga_db"] = 0
    assert loopback._clamp_tx_gain(ok) == 0
    bad = dict(board)
    bad["txvga_db"] = 40
    bad["max_tx_db"] = 4
    try:
        loopback._clamp_tx_gain(bad)
    except SystemExit as exc:
        assert "max_tx_db" in str(exc)
    else:
        raise AssertionError("expected clamp failure")
