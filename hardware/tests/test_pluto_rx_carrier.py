import importlib.util
from io import StringIO
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "pluto_rx_capture",
    Path(__file__).resolve().parents[1] / "labs" / "05_pluto_rx_capture.py",
)
rx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rx)

SAMPLE_RATE = 2_000_000
N = 8192
WINDOW_HZ = 15_000
MIN_DB = 10.0


def _noise(seed):
    rng = np.random.default_rng(seed)
    i = rng.normal(size=N)
    q = rng.normal(size=N)
    return ((i + 1j * q) / np.sqrt(2)).astype(np.complex64)


def _tone(freq_hz, amplitude):
    t = np.arange(N) / SAMPLE_RATE
    return (amplitude * np.exp(1j * 2 * np.pi * freq_hz * t)).astype(np.complex64)


def _rise(unkeyed, keyed):
    return rx.carrier_rise_db(
        rx.inband_power_db(unkeyed, SAMPLE_RATE, WINDOW_HZ),
        rx.inband_power_db(keyed, SAMPLE_RATE, WINDOW_HZ),
    )


def test_noise_only_is_not_a_carrier():
    rise = _rise(_noise(1), _noise(2))
    assert abs(rise) < 6
    assert rx.carrier_detected(rise, MIN_DB) is False


def test_inband_tone_is_a_carrier():
    floor = _noise(3)
    keyed = floor + _tone(20 * SAMPLE_RATE / N, 8.0)
    rise = _rise(floor, keyed)
    assert rise >= MIN_DB
    assert rx.carrier_detected(rise, MIN_DB) is True


def test_out_of_band_tone_is_not_a_carrier():
    floor = _noise(4)
    keyed = floor + _tone(400 * SAMPLE_RATE / N, 8.0)
    rise = _rise(floor, keyed)
    assert rise < MIN_DB
    assert rx.carrier_detected(rise, MIN_DB) is False


def test_dc_spur_in_both_captures_is_not_a_rise():
    spur = _tone(0.0, 4.0)
    rise = _rise(_noise(5) + spur, _noise(6) + spur)
    assert rise < MIN_DB
    assert rx.carrier_detected(rise, MIN_DB) is False


def test_carrier_threshold_boundary():
    assert rx.carrier_detected(10.0, 10.0) is True
    assert rx.carrier_detected(9.99, 10.0) is False
    assert rx.carrier_detected(None, 10.0) is False


def test_prompt_waits_for_enter(capsys):
    assert rx.prompt_to_key(146_550_000, stdin=StringIO("\n")) == 0
    err = capsys.readouterr().err
    assert "Receiver ready on 146.550 MHz. Key the transmitter and hold PTT, then press Enter." in err


def test_prompt_eof_fails(capsys):
    assert rx.prompt_to_key(146_550_000, stdin=StringIO("")) == 1
    assert "EOF while waiting for key-up" in capsys.readouterr().err
