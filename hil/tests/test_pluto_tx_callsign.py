import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "pluto_tx_callsign",
    Path(__file__).resolve().parents[1] / "labs" / "06_pluto_tx_callsign_fm.py",
)
pluto_tx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pluto_tx)


def test_refuses_calling_channels():
    with pytest.raises(SystemExit, match="calling channel"):
        pluto_tx.assert_frequency(146_520_000)
    with pytest.raises(SystemExit, match="calling channel"):
        pluto_tx.assert_frequency(446_000_000)


def test_allows_simplex_2m():
    pluto_tx.assert_frequency(146_550_000)


def test_gain_respects_board_ceiling():
    assert pluto_tx.assert_tx_gain(-10, -5) == -10
    assert pluto_tx.assert_tx_gain(-5, -5) == -5
    with pytest.raises(SystemExit, match="max_tx_db"):
        pluto_tx.assert_tx_gain(-4, -5)


def test_tx_requires_loopback(monkeypatch):
    monkeypatch.delenv("HIL_LOOPBACK", raising=False)
    with pytest.raises(SystemExit, match="HIL_LOOPBACK"):
        pluto_tx.assert_loopback()


def test_dry_run_writes_iq_without_tx(tmp_path, monkeypatch):
    monkeypatch.delenv("HIL_LOOPBACK", raising=False)
    monkeypatch.delenv("RAD_LAB_CALLSIGN", raising=False)
    code = pluto_tx.main(
        [
            "--callsign",
            "K0TEST",
            "--dry-run",
            "--repeat",
            "1",
            "--wpm",
            "30",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert code == 0
    iq = list(tmp_path.glob("tx_callsign_K0TEST_*.cf32"))
    reports = list(tmp_path.glob("*_report.json"))
    assert len(iq) == 1 and iq[0].stat().st_size > 0
    assert len(reports) == 1
    text = reports[0].read_text()
    assert '"status": "dry_run"' in text
    assert "146550000" in text
