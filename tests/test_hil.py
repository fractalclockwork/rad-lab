import hil
import radboards


def test_simulated_loopback_records_snr():
    board = radboards.load_board("hackrf")
    records = hil.run_loopback_hil(board, simulate=True)
    assert records[0]["sent"] == "CW_TONE"
    assert records[0]["mode"] == "simulated"
    assert records[0]["snr_db"] >= board["min_snr_db"]
    assert records[0]["host_monotonic_ns"] > 0


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
