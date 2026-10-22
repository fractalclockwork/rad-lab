import importlib.util
from io import StringIO
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "crossboard_915_cw",
    Path(__file__).resolve().parents[1] / "labs" / "07_crossboard_915_cw.py",
)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def test_refuses_without_loopback(monkeypatch):
    monkeypatch.delenv("HUMAN_LOOPBACK", raising=False)
    with pytest.raises(SystemExit, match="HUMAN_LOOPBACK"):
        lab.assert_loopback()


def test_allows_loopback(monkeypatch):
    monkeypatch.setenv("HUMAN_LOOPBACK", "1")
    lab.assert_loopback()


def test_clamp_tx_gain_respects_ceiling():
    assert lab.clamp_tx_gain({"txvga_db": 0, "max_tx_db": 4}) == 0.0
    assert lab.clamp_tx_gain({"txvga_db": -10, "max_tx_db": -5}) == -10.0
    with pytest.raises(SystemExit, match="max_tx_db"):
        lab.clamp_tx_gain({"txvga_db": -4, "max_tx_db": -5})


def test_evaluate_leg_snr_and_peak():
    ok = lab.evaluate_leg(
        {"snr_db": 25.0, "peak_hz": 100_000.0},
        tone_offset_hz=100_000.0,
        min_snr_db=10.0,
    )
    assert ok["pass"] is True
    assert ok["snr_ok"] is True
    assert ok["peak_ok"] is True

    low = lab.evaluate_leg(
        {"snr_db": 5.0, "peak_hz": 100_000.0},
        tone_offset_hz=100_000.0,
        min_snr_db=10.0,
    )
    assert low["pass"] is False
    assert low["snr_ok"] is False

    off = lab.evaluate_leg(
        {"snr_db": 40.0, "peak_hz": 0.0},
        tone_offset_hz=100_000.0,
        min_snr_db=10.0,
    )
    assert off["pass"] is False
    assert off["peak_ok"] is False


def test_evaluate_leg_peak_tolerance_boundary():
    edge = lab.evaluate_leg(
        {"snr_db": 12.0, "peak_hz": 105_000.0},
        tone_offset_hz=100_000.0,
        min_snr_db=10.0,
        tolerance_hz=5000.0,
    )
    assert edge["pass"] is True
    beyond = lab.evaluate_leg(
        {"snr_db": 12.0, "peak_hz": 105_000.1},
        tone_offset_hz=100_000.0,
        min_snr_db=10.0,
        tolerance_hz=5000.0,
    )
    assert beyond["pass"] is False


def test_prompt_waits_for_enter(capsys):
    assert lab.prompt_wire("confirm cable", stdin=StringIO("\n")) == 0
    assert "confirm cable" in capsys.readouterr().err


def test_prompt_eof_fails(capsys):
    assert lab.prompt_wire("confirm cable", stdin=StringIO("")) == 1
    assert "EOF while waiting for cable confirm" in capsys.readouterr().err


def test_no_prompt_skips_wait(capsys):
    assert lab.prompt_wire("confirm cable", stdin=StringIO(""), no_prompt=True) == 0
    err = capsys.readouterr().err
    assert "Skipping cable prompt." in err


def test_main_refuses_without_loopback(monkeypatch):
    monkeypatch.delenv("HUMAN_LOOPBACK", raising=False)
    with pytest.raises(SystemExit, match="HUMAN_LOOPBACK"):
        lab.main(["--no-prompt"])


def test_crossboard_loopback_via_loopback_module(tmp_path, monkeypatch):
    from harness import radboards
    from hardware import loopback

    hackrf = radboards.load_board("hackrf")
    fake_report = {
        "status": "pass",
        "min_snr_db": 7.0,
        "legs": [
            {
                "status": "pass",
                "tx_board": "hackrf",
                "rx_board": "pluto",
                "tx_serial": "h1",
                "rx_serial": "p1",
                "tone_offset_hz": 100000.0,
                "tx_gain_db": 0.0,
                "elapsed_ms": 50.0,
                "metrics": {"snr_db": 22.0, "peak_hz": 100000.0},
                "verdict": {"pass": True, "snr_ok": True, "peak_ok": True},
            },
            {
                "status": "pass",
                "tx_board": "pluto",
                "rx_board": "hackrf",
                "tx_serial": "p1",
                "rx_serial": "h1",
                "tone_offset_hz": 100000.0,
                "tx_gain_db": -30.0,
                "elapsed_ms": 50.0,
                "metrics": {"snr_db": 24.0, "peak_hz": 100000.0},
                "verdict": {"pass": True, "snr_ok": True, "peak_ok": True},
            },
        ],
    }
    monkeypatch.setattr(
        loopback,
        "_crossboard_loopback",
        lambda board, no_prompt=None: [
            loopback.loopback_record(
                sent=f"CW_TONE_TX_{leg['tx_board'].upper()}_RX_{leg['rx_board'].upper()}",
                expected="peak~100000.0Hz snr>=7.0dB",
                actual=f"peak={leg['metrics']['peak_hz']:.1f}Hz snr={leg['metrics']['snr_db']:.1f}dB",
                snr_db=leg["metrics"]["snr_db"],
                host_monotonic_ns=1,
                mode="hardware",
                tx_board=leg["tx_board"],
                rx_board=leg["rx_board"],
                metrics=leg["metrics"],
                verdict=leg["verdict"],
            )
            for leg in fake_report["legs"]
        ],
    )
    records = loopback.run_loopback(hackrf, simulate=False)
    assert len(records) == 2
    assert records[0]["sent"] == "CW_TONE_TX_HACKRF_RX_PLUTO"
    assert records[1]["sent"] == "CW_TONE_TX_PLUTO_RX_HACKRF"


def test_shared_rf_mismatch():
    tx = {"center_hz": 915e6, "sample_rate": 2e6, "tone_offset_hz": 1e5, "min_snr_db": 10}
    rx = {**tx, "center_hz": 916e6}
    with pytest.raises(SystemExit, match="RF mismatch"):
        lab.shared_rf(tx, rx)
