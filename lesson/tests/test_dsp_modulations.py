import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "dsp_common",
    Path(__file__).resolve().parents[2] / "software" / "dsp" / "common.py",
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


# --- Module 1: windowing & DUC/DDC ---

def test_window_spectrum_all_windows():
    n = 8192
    t = np.arange(n) / 2e6
    iq = np.exp(2j * np.pi * 100e3 * t)
    for window in ["rectangular", "hann", "blackman"]:
        freqs, psd = dsp.window_spectrum(iq, 2e6, window=window)
        assert freqs.size == n and psd.size == n
        peak_hz = float(freqs[np.argmax(psd)])
        assert abs(peak_hz - 100e3) < 2e6 / n * 4


def test_duc_ddc_roundtrip():
    n = 4096
    t = np.arange(n) / 2e6
    iq = np.exp(2j * np.pi * 100e3 * t)
    up = dsp.duc(iq, 2e6, 250e3)
    back = dsp.ddc(up, 2e6, 250e3)
    assert np.allclose(iq, back, atol=1e-3)


# --- Module 2: Eb/N0 AWGN & impairments ---

def test_awgn_ebno_snr_scaling():
    # QPSK: measured SNR should equal Eb/N0 + 10*log10(2)
    bits = np.random.default_rng(0).integers(0, 2, 4096).astype(np.uint8)
    tx = dsp.qpsk_modulate(bits, samples_per_symbol=1)
    for ebno_db in [0.0, 6.0, 12.0]:
        rx = dsp.awgn_ebno(tx, ebno_db, bits_per_symbol=2, seed=1)
        snr_db = 10 * np.log10(np.mean(np.abs(tx) ** 2) / np.mean(np.abs(rx - tx) ** 2))
        assert abs(snr_db - (ebno_db + 10 * np.log10(2.0))) < 0.5


def test_cfo_applies_per_sample_rotation():
    fs = 1e6
    cfo = 250e3
    iq = np.ones(4, dtype=np.complex128)
    rot = dsp.apply_cfo(iq, fs, cfo)
    expected = np.exp(2j * np.pi * cfo * np.arange(4) / fs)
    assert np.allclose(rot, expected, atol=1e-6)


def test_phase_noise_preserves_magnitude():
    iq = np.ones(1000, dtype=np.complex64)
    pn = dsp.apply_phase_noise(iq, 1e6, 0.1, seed=0)
    assert np.allclose(np.abs(pn), 1.0, atol=1e-6)


# --- Module 3: 8PSK & M-FSK ---

def test_mpsk_constellation_size():
    assert dsp.mpsk_constellation(8).size == 8
    assert dsp.mpsk_constellation(4).size == 4


def test_8psk_gray_roundtrip():
    bits = np.array([0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1], dtype=np.uint8)
    syms = dsp.map_bits_to_mpsk(bits, 8)
    dec = dsp.demod_mpsk(syms, 8)
    assert np.array_equal(dec, bits)

    # adjacent phase indices carry Gray-adjacent labels
    pts = dsp.mpsk_constellation(8)
    labels = []
    for i in range(8):
        g = i ^ (i >> 1)
        labels.append(tuple((g >> k) & 1 for k in range(2, -1, -1)))
    for a, b in zip(labels, labels[1:] + [labels[0]]):
        assert sum(x != y for x, y in zip(a, b)) == 1


def test_4fsk_roundtrip():
    tones = [10e3, 20e3, 30e3, 40e3]
    spacing = 200e3 / 16
    tones = [10e3 + k * spacing for k in range(4)]
    bits = np.array([0, 0, 0, 1, 1, 1, 1, 0], dtype=np.uint8)
    mod = dsp.fsk_modulate(bits, 200e3, tones, samples_per_symbol=16)
    dem = dsp.fsk_demodulate_noncoherent(mod, 200e3, tones, samples_per_symbol=16)
    assert np.array_equal(dem, bits)


# --- Module 4: RRC & matched filter ---

def test_rrc_filter_odd_length_unit_energy():
    h = dsp.rrc_filter(0.35, 8, 101)
    assert h.size == 101
    assert np.allclose(np.sum(h ** 2), 1.0, atol=1e-6)


def test_matched_filter_raises_snr():
    rng = np.random.default_rng(0)
    sig = (2 * rng.integers(0, 2, 400) - 1).astype(np.complex64)
    noisy = sig + (rng.normal(0, 0.1, 400) + 1j * rng.normal(0, 0.1, 400)).astype(np.complex64)
    sb, sa = dsp.matched_filter_snr(sig, noisy, 0.35, 8, num_taps=101)
    assert sa >= sb - 1e-6


# --- Module 5: Hamming, BER, Shannon ---

def test_hamming74_sec():
    data = np.array([1, 0, 1, 1], dtype=np.uint8)
    enc = dsp.hamming74_encode(data)
    assert enc.size == 7
    assert np.array_equal(dsp.hamming74_decode(enc), data)
    # single-error correction
    for pos in range(7):
        corrupted = enc.copy()
        corrupted[pos] ^= 1
        assert np.array_equal(dsp.hamming74_decode(corrupted), data)


def test_monotonic_ber_curve():
    ebno = np.arange(0, 13, 1)
    sim, theo = dsp.monte_carlo_ber_bpsk(ebno, num_bits=100000, seed=3)
    assert sim.size == 13 and theo.size == 13
    assert sim[-1] < sim[0]
    # simulated close to theory at mid SNR
    assert abs(sim[6] - theo[6]) < 5e-4  # at 6 dB


def test_ber_theoretical_matches_erfc():
    from scipy.special import erfc
    ebno = np.array([0.0, 3.0, 6.0])
    theo = dsp.ber_psk_theoretical(ebno)
    expected = 0.5 * erfc(np.sqrt(10 ** (ebno / 10.0)))
    assert np.allclose(theo, expected)


def test_shannon_capacity_positive():
    c = dsp.shannon_capacity(1e6, 10.0)
    assert c > 0
    assert np.isclose(c, 1e6 * np.log2(11.0))

