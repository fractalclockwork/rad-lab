import hil
import radboards


def test_simulated_loopback_records_snr():
    board = radboards.load_board("hackrf")
    records = hil.run_loopback_hil(board, simulate=True)
    assert records[0]["sent"] == "CW_TONE"
    assert records[0]["mode"] == "simulated"
    assert records[0]["snr_db"] >= board["min_snr_db"]
    assert records[0]["host_monotonic_ns"] > 0


def test_container_loopback_runs_in_container(monkeypatch):
    """Non-simulated loopback must orchestrate a rad-lab-sdr container, not
    import SoapySDR on the dev-host."""
    import json as _json
    import subprocess as _subprocess

    board = radboards.load_board("hackrf")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        payload = _json.dumps(
            {"status": "pass", "records": [{"sent": "CW_TONE", "mode": "hardware"}]}
        )
        return _subprocess.CompletedProcess(cmd, 0, stdout=payload, stderr="")

    monkeypatch.setattr(hil.subprocess, "run", fake_run)
    records = hil.run_loopback_hil(dict(board), simulate=False)
    cmd = captured["cmd"]
    assert cmd[0] == "docker" and cmd[1] == "run"
    assert "RAD_LAB_CONTAINER=1" in cmd
    assert "--privileged" in cmd
    assert hil.devices.IMAGE_NAME in cmd
    entry = cmd[cmd.index(hil.devices.IMAGE_NAME) + 1 :]
    assert entry[0] == "python3"
    assert entry[1].endswith("_container_loopback.py")
    # board dict is passed as JSON for the container-side entrypoint
    board_json = entry[entry.index("--board") + 1]
    assert _json.loads(board_json)["id"] == "hackrf"
    assert records == [{"sent": "CW_TONE", "mode": "hardware"}]


def test_container_loopback_failure_raises(monkeypatch):
    import subprocess as _subprocess

    board = radboards.load_board("hackrf")

    def fake_run(cmd, **kwargs):
        return _subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    monkeypatch.setattr(hil.subprocess, "run", fake_run)
    try:
        hil.run_loopback_hil(dict(board), simulate=False)
    except RuntimeError as exc:
        assert "container loopback failed" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_hil_logs_include_junit(tmp_path):
    records = [
        hil.hil_record("CW_TONE", "snr>=10", "snr=20", 20.0, 123, mode="simulated")
    ]
    hil.write_hil_logs(tmp_path, records)
    assert (tmp_path / "hil.jsonl").read_text().startswith('{"sent": "CW_TONE"')
    xml = (tmp_path / "junit.xml").read_text()
    assert "snr" in xml
    assert 'failures="0"' in xml
    assert "testcase" in xml
    hil.write_hil_logs(tmp_path, [], failures=["no tone"])
    failed = (tmp_path / "junit.xml").read_text()
    assert 'failures="1"' in failed
    assert "no tone" in failed


def test_tone_peak_must_match_offset():
    hil.assert_tone_peak({"snr_db": 30.0, "peak_hz": 100000.0}, 100000.0)
    hil.assert_tone_peak({"snr_db": 12.0, "peak_hz": 0.0}, 100000.0)
    try:
        hil.assert_tone_peak({"snr_db": 0.0, "peak_hz": 100000.0}, 100000.0)
    except AssertionError as exc:
        assert "no detectable tone" in str(exc)
    else:
        raise AssertionError("expected zero-SNR failure")


def test_tx_gain_clamp():
    board = radboards.load_board("hackrf")
    ok = dict(board)
    ok["txvga_db"] = 0
    assert hil._clamp_tx_gain(ok) == 0
    bad = dict(board)
    bad["txvga_db"] = 40
    bad["max_tx_db"] = 4
    try:
        hil._clamp_tx_gain(bad)
    except ValueError as exc:
        assert "max_tx_db" in str(exc)
    else:
        raise AssertionError("expected clamp failure")
