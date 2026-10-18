import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "dsp_common",
    Path(__file__).resolve().parents[1] / "labs" / "dsp_common.py",
)
dsp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsp)


def test_am_roundtrip_correlation():
    rate = 100_000.0
    n = 4000
    t = np.arange(n) / rate
    message = np.sin(2 * np.pi * 500 * t)
    _, rf = dsp.am_modulate(message, carrier_hz=10_000, sample_rate=rate, depth=0.8)
    recovered = dsp.am_demodulate_envelope(rf)
    sl = slice(n // 10, -n // 10)
    corr = np.corrcoef(message[sl], recovered[sl])[0, 1]
    assert corr > 0.85


def test_fm_roundtrip_correlation():
    rate = 100_000.0
    n = 4000
    t = np.arange(n) / rate
    message = np.sin(2 * np.pi * 500 * t)
    iq = dsp.fm_modulate(message, rate, deviation_hz=3_000)
    freq = dsp.fm_demodulate(iq, rate)
    recovered = freq / np.max(np.abs(freq))
    sl = slice(n // 10, -n // 10)
    corr = np.corrcoef(message[sl], recovered[sl])[0, 1]
    assert corr > 0.9


def test_bpsk_zero_ber_high_snr():
    bits = dsp.bits_from_text("TEST")
    tx = dsp.bpsk_modulate(bits, samples_per_symbol=8)
    rx = dsp.awgn(tx, snr_db=20, seed=1)
    decoded = dsp.bpsk_demodulate(rx, samples_per_symbol=8)
    assert dsp.bit_error_rate(bits, decoded[: bits.size]) == 0.0


def test_qpsk_zero_ber_high_snr():
    bits = dsp.bits_from_text("TEST")
    tx = dsp.qpsk_modulate(bits, samples_per_symbol=8)
    rx = dsp.awgn(tx, snr_db=20, seed=2)
    decoded = dsp.qpsk_demodulate(rx, samples_per_symbol=8)
    assert dsp.bit_error_rate(bits, decoded[: bits.size]) == 0.0


def test_qam16_zero_ber_high_snr():
    bits = dsp.bits_from_text("QAM16")
    tx = dsp.qam16_modulate(bits, samples_per_symbol=8)
    rx = dsp.awgn(tx, snr_db=25, seed=3)
    decoded = dsp.qam16_demodulate(rx, samples_per_symbol=8)
    assert dsp.bit_error_rate(bits, decoded[: bits.size]) == 0.0


def test_qam16_constellation_has_16_points():
    assert dsp.qam16_constellation().size == 16


def test_text_bits_roundtrip():
    text = "RADLAB"
    bits = dsp.bits_from_text(text)
    assert dsp.text_from_bits(bits).startswith(text)
