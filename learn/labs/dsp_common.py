"""Shared DSP helpers for learn/ labs (synthetic IQ only; no Soapy TX)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "reports" / "learn"


def report_dir(tag: str) -> Path:
    path = REPORTS / tag
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_report(directory: Path, payload: dict) -> Path:
    path = directory / "report.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def awgn(iq: np.ndarray, snr_db: float, seed: int = 0) -> np.ndarray:
    """Add complex AWGN so E[|signal|^2] / E[|noise|^2] ≈ 10^(snr_db/10)."""
    iq = np.asarray(iq, dtype=np.complex128)
    signal_power = float(np.mean(np.abs(iq) ** 2))
    if signal_power <= 0:
        signal_power = 1.0
    noise_power = signal_power / (10 ** (float(snr_db) / 10.0))
    rng = np.random.default_rng(seed)
    noise = (
        rng.normal(scale=np.sqrt(noise_power / 2), size=iq.size)
        + 1j * rng.normal(scale=np.sqrt(noise_power / 2), size=iq.size)
    )
    return (iq + noise).astype(np.complex64)


def spectrum_db(iq: np.ndarray, sample_rate: float):
    iq = np.asarray(iq, dtype=np.complex128)
    n = iq.size
    window = np.hanning(n)
    spec = np.fft.fftshift(np.fft.fft(iq * window))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / float(sample_rate)))
    psd = 10 * np.log10(np.maximum(np.abs(spec) ** 2, 1e-20))
    return freqs, psd


def save_time_plot(path: Path, t, series, labels, title: str):
    fig, ax = plt.subplots(figsize=(8, 3.5))
    for y, label in zip(series, labels):
        ax.plot(t, y, label=label, linewidth=1.0)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title(title)
    if len(labels) > 1:
        ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def save_spectrum_plot(path: Path, freqs, psd_db, title: str):
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(freqs / 1e3, psd_db, linewidth=0.8)
    ax.set_xlabel("Frequency (kHz)")
    ax.set_ylabel("Power (dB)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def save_constellation_plot(path: Path, iq, title: str, ideal=None):
    fig, ax = plt.subplots(figsize=(5, 5))
    pts = np.asarray(iq).ravel()
    ax.scatter(pts.real, pts.imag, s=8, alpha=0.35, label="symbols")
    if ideal is not None:
        ideal = np.asarray(ideal).ravel()
        ax.scatter(ideal.real, ideal.imag, s=40, marker="x", label="ideal")
        ax.legend(loc="upper right")
    ax.set_xlabel("I")
    ax.set_ylabel("Q")
    ax.set_title(title)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def save_iq_trajectory(path: Path, iq, title: str, max_points: int = 4000):
    iq = np.asarray(iq).ravel()
    if iq.size > max_points:
        idx = np.linspace(0, iq.size - 1, max_points).astype(int)
        iq = iq[idx]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(iq.real, iq.imag, linewidth=0.6, alpha=0.8)
    ax.set_xlabel("I")
    ax.set_ylabel("Q")
    ax.set_title(title)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


# --- Analog ---


def am_modulate(message: np.ndarray, carrier_hz: float, sample_rate: float, depth: float = 0.7):
    message = np.asarray(message, dtype=np.float64)
    message = message / max(np.max(np.abs(message)), 1e-12)
    t = np.arange(message.size) / float(sample_rate)
    rf = (1.0 + float(depth) * message) * np.cos(2 * np.pi * carrier_hz * t)
    return t, rf.astype(np.float64)


def am_demodulate_envelope(rf: np.ndarray):
    """Rectify + moving-average envelope detector."""
    rf = np.asarray(rf, dtype=np.float64)
    mag = np.abs(rf)
    kernel = max(8, mag.size // 200)
    kernel += kernel % 2 == 0
    env = np.convolve(mag, np.ones(kernel) / kernel, mode="same")
    env = env - np.mean(env)
    peak = np.max(np.abs(env))
    if peak > 0:
        env = env / peak
    return env


def fm_modulate(message: np.ndarray, sample_rate: float, deviation_hz: float) -> np.ndarray:
    """Complex baseband FM from real message in [-1, 1]."""
    message = np.clip(np.asarray(message, dtype=np.float64), -1.0, 1.0)
    phase = np.cumsum(2 * np.pi * float(deviation_hz) * message / float(sample_rate))
    return (np.exp(1j * phase) * 0.7).astype(np.complex64)


def fm_demodulate(iq: np.ndarray, sample_rate: float) -> np.ndarray:
    """Instantaneous frequency from phase difference of complex baseband."""
    iq = np.asarray(iq, dtype=np.complex128)
    phase = np.unwrap(np.angle(iq))
    dphase = np.diff(phase, prepend=phase[0])
    return (dphase * float(sample_rate) / (2 * np.pi)).astype(np.float64)


# --- Digital ---


def bits_from_text(text: str) -> np.ndarray:
    data = text.encode("ascii")
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    return bits.astype(np.uint8)


def text_from_bits(bits: np.ndarray) -> str:
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    pad = (-bits.size) % 8
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    data = np.packbits(bits)
    return bytes(data).decode("ascii", errors="replace")


def bpsk_modulate(bits: np.ndarray, samples_per_symbol: int = 8) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    symbols = (1 - 2 * bits.astype(np.float64)).astype(np.complex128)  # 0→+1, 1→-1
    return np.repeat(symbols, samples_per_symbol).astype(np.complex64)


def bpsk_demodulate(iq: np.ndarray, samples_per_symbol: int = 8) -> np.ndarray:
    iq = np.asarray(iq, dtype=np.complex128)
    n_sym = iq.size // samples_per_symbol
    shaped = iq[: n_sym * samples_per_symbol].reshape(n_sym, samples_per_symbol).mean(axis=1)
    return (shaped.real < 0).astype(np.uint8)


def qpsk_constellation():
    # Gray: 00→(+1+1j), 01→(-1+1j), 11→(-1-1j), 10→(+1-1j), normalized
    points = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j], dtype=np.complex128)
    return points / np.sqrt(2)


def qpsk_modulate(bits: np.ndarray, samples_per_symbol: int = 8) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    if bits.size % 2:
        bits = np.concatenate([bits, np.zeros(1, dtype=np.uint8)])
    dibits = bits.reshape(-1, 2)
    idx = (dibits[:, 0] << 1) | dibits[:, 1]
    # Map Gray dibits 00,01,11,10 → constellation indices 0,1,2,3
    gray_to_idx = {0: 0, 1: 1, 3: 2, 2: 3}
    mapped = np.array([gray_to_idx[int(v)] for v in idx], dtype=int)
    points = qpsk_constellation()
    symbols = points[mapped]
    return np.repeat(symbols, samples_per_symbol).astype(np.complex64)


def qpsk_demodulate(iq: np.ndarray, samples_per_symbol: int = 8) -> np.ndarray:
    iq = np.asarray(iq, dtype=np.complex128)
    n_sym = iq.size // samples_per_symbol
    shaped = iq[: n_sym * samples_per_symbol].reshape(n_sym, samples_per_symbol).mean(axis=1)
    points = qpsk_constellation()
    # nearest neighbor
    d = np.abs(shaped.reshape(-1, 1) - points.reshape(1, -1))
    mapped = np.argmin(d, axis=1)
    idx_to_gray = {0: (0, 0), 1: (0, 1), 2: (1, 1), 3: (1, 0)}
    bits = []
    for m in mapped:
        bits.extend(idx_to_gray[int(m)])
    return np.asarray(bits, dtype=np.uint8)


_QAM16_GRAY = ((0, 0), (0, 1), (1, 1), (1, 0))
_QAM16_LEVELS = np.array([-3.0, -1.0, 1.0, 3.0])


def qam16_constellation():
    """16 points: for each Q Gray level, then each I Gray level (row-major)."""
    pts = []
    for q in _QAM16_LEVELS:
        for i in _QAM16_LEVELS:
            pts.append(i + 1j * q)
    pts = np.asarray(pts, dtype=np.complex128)
    return pts / np.sqrt(np.mean(np.abs(pts) ** 2))


def _gray_pair_to_level_index(b0: int, b1: int) -> int:
    key = (int(b0), int(b1))
    return _QAM16_GRAY.index(key)


def qam16_modulate(bits: np.ndarray, samples_per_symbol: int = 8) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    pad = (-bits.size) % 4
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    nibbles = bits.reshape(-1, 4)
    i_idx = np.array([_gray_pair_to_level_index(r[0], r[1]) for r in nibbles])
    q_idx = np.array([_gray_pair_to_level_index(r[2], r[3]) for r in nibbles])
    symbols = _QAM16_LEVELS[i_idx] + 1j * _QAM16_LEVELS[q_idx]
    symbols = symbols / np.sqrt(np.mean(np.abs(symbols) ** 2))
    return np.repeat(symbols.astype(np.complex128), samples_per_symbol).astype(np.complex64)


def qam16_demodulate(iq: np.ndarray, samples_per_symbol: int = 8) -> np.ndarray:
    iq = np.asarray(iq, dtype=np.complex128)
    n_sym = iq.size // samples_per_symbol
    shaped = iq[: n_sym * samples_per_symbol].reshape(n_sym, samples_per_symbol).mean(axis=1)
    points = qam16_constellation()
    d = np.abs(shaped.reshape(-1, 1) - points.reshape(1, -1))
    mapped = np.argmin(d, axis=1)
    bits = []
    for m in mapped:
        q_idx = int(m) // 4
        i_idx = int(m) % 4
        bits.extend(_QAM16_GRAY[i_idx])
        bits.extend(_QAM16_GRAY[q_idx])
    return np.asarray(bits, dtype=np.uint8)


def bit_error_rate(tx_bits: np.ndarray, rx_bits: np.ndarray) -> float:
    tx = np.asarray(tx_bits).ravel()
    rx = np.asarray(rx_bits).ravel()
    n = min(tx.size, rx.size)
    if n == 0:
        return 1.0
    return float(np.mean(tx[:n] != rx[:n]))


def symbol_error_rate(tx_symbols: np.ndarray, rx_symbols: np.ndarray) -> float:
    tx = np.asarray(tx_symbols).ravel()
    rx = np.asarray(rx_symbols).ravel()
    n = min(tx.size, rx.size)
    if n == 0:
        return 1.0
    return float(np.mean(tx[:n] != rx[:n]))


# --- Module 1: complex baseband & windowing ---


def analytic_signal_hilbert(real_signal: np.ndarray) -> np.ndarray:
    """Form the analytic signal x_a[n] = x[n] + j*H{x[n]} via Hilbert transform.

    Returns a complex baseband signal containing only positive frequencies.
    Matches Module 1 Activity 1.1 scaffolding (scipy.signal.hilbert).
    """
    from scipy.signal import hilbert

    real_signal = np.asarray(real_signal, dtype=np.float64)
    analytic = hilbert(real_signal)
    return analytic.astype(np.complex64)


def generate_complex_baseband(
    freq_offset: float, sample_rate: float, num_samples: int
) -> tuple[np.ndarray, np.ndarray]:
    """Generate complex baseband IQ samples for a given frequency offset.

    Builds a real passband cosine, then forms the analytic signal via the
    Hilbert transform. Matches Module 1 code scaffolding in the spec.
    Returns (complex_baseband, time_vector).
    """
    t = np.arange(num_samples) / float(sample_rate)
    real_signal = np.cos(2 * np.pi * float(freq_offset) * t)
    analytic_signal = analytic_signal_hilbert(real_signal)
    return analytic_signal, t


def window_spectrum(
    iq: np.ndarray, sample_rate: float, window: str = "hann"
) -> tuple[np.ndarray, np.ndarray]:
    """Windowed FFT magnitude (dB) for rectangular, hann, and blackman windows.

    Module 1 Activity 1.2: compare spectral leakage / mainlobe width across
    window choices. Returns (freqs_hz, psd_db).
    """
    iq = np.asarray(iq, dtype=np.complex128)
    n = iq.size
    if window == "rectangular":
        w = np.ones(n)
    elif window == "hann":
        w = np.hanning(n)
    elif window == "blackman":
        w = np.blackman(n)
    else:
        raise ValueError(f"unknown window: {window!r}")
    spec = np.fft.fftshift(np.fft.fft(iq * w))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / float(sample_rate)))
    psd = 10 * np.log10(np.maximum(np.abs(spec) ** 2, 1e-20))
    return freqs, psd


# --- Module 1 Activity 1.3: digital up/down conversion ---


def duc(iq: np.ndarray, sample_rate: float, freq_offset: float) -> np.ndarray:
    """Digital upconversion: shift complex baseband to an offset carrier.

    y[n] = x[n] * exp(j 2 pi f_offset n / f_s). Returns complex passband.
    """
    iq = np.asarray(iq, dtype=np.complex128)
    n = np.arange(iq.size)
    lo = np.exp(2j * np.pi * float(freq_offset) * n / float(sample_rate))
    return (iq * lo).astype(np.complex64)


def ddc(rf: np.ndarray, sample_rate: float, freq_offset: float) -> np.ndarray:
    """Digital downconversion: mix an offset carrier back to complex baseband.

    y[n] = x[n] * exp(-j 2 pi f_offset n / f_s). Returns complex baseband.
    """
    rf = np.asarray(rf, dtype=np.complex128)
    n = np.arange(rf.size)
    lo = np.exp(-2j * np.pi * float(freq_offset) * n / float(sample_rate))
    return (rf * lo).astype(np.complex64)


# --- Module 2: AWGN calibrated to Eb/N0 ---


def awgn_ebno(
    iq: np.ndarray,
    ebno_db: float,
    bits_per_symbol: int = 1,
    seed: int = 0,
) -> np.ndarray:
    """Add complex AWGN calibrated to Eb/N0 rather than signal SNR.

    For unit-energy symbols with spectral efficiency bits_per_symbol:
        Es/N0 = (Eb/N0) * bits_per_symbol,  noise_power = P_signal / (Es/N0)
    noise variance per dimension = noise_power / 2.
    Matches Module 2 Activity 2.1 (SNR = (Eb/N0) * eta_s).
    """
    iq = np.asarray(iq, dtype=np.complex128)
    ebno_linear = 10.0 ** (float(ebno_db) / 10.0)
    bps = max(int(bits_per_symbol), 1)
    signal_power = float(np.mean(np.abs(iq) ** 2))
    if signal_power <= 0:
        signal_power = 1.0
    es_over_n0 = ebno_linear * bps
    noise_power = signal_power / es_over_n0
    rng = np.random.default_rng(seed)
    noise = (
        rng.normal(scale=np.sqrt(noise_power / 2), size=iq.size)
        + 1j * rng.normal(scale=np.sqrt(noise_power / 2), size=iq.size)
    )
    return (iq + noise).astype(np.complex64)


def apply_cfo(iq: np.ndarray, sample_rate: float, cfo_hz: float) -> np.ndarray:
    """Apply carrier frequency offset: y[n] = x[n] * exp(j 2 pi dfo n / f_s).

    Rotates the constellation at rate cfo_hz. Module 2 Activity 2.3.
    """
    iq = np.asarray(iq, dtype=np.complex128)
    n = np.arange(iq.size)
    rot = np.exp(2j * np.pi * float(cfo_hz) * n / float(sample_rate))
    return (iq * rot).astype(np.complex64)


def apply_phase_noise(
    iq: np.ndarray, sample_rate: float, phase_std_rad: float, seed: int = 0
) -> np.ndarray:
    """Apply additive Gaussian phase noise to each sample.

    y[n] = x[n] * exp(j theta[n]), theta[n] ~ N(0, phase_std_rad^2).
    Blurs the constellation along arcs. Module 2 Activity 2.3.
    """
    iq = np.asarray(iq, dtype=np.complex128)
    rng = np.random.default_rng(seed)
    theta = rng.normal(0.0, float(phase_std_rad), size=iq.size)
    return (iq * np.exp(1j * theta)).astype(np.complex64)


# --- Module 3: M-PSK (incl. 8PSK) and M-FSK ---


def _binary_to_gray(b: np.ndarray) -> np.ndarray:
    return b ^ (b >> 1)


def _gray_to_binary(gray_values: np.ndarray) -> np.ndarray:
    """Inverse of binary-to-Gray: recover b from g = b ^ (b >> 1)."""
    gray_values = np.asarray(gray_values, dtype=np.int64)
    b = gray_values.copy()
    shift = gray_values >> 1
    while np.any(shift):
        b = b ^ shift
        shift = shift >> 1
    return b


def mpsk_constellation(m_order: int) -> np.ndarray:
    """Ideal M-PSK constellation on the unit circle.

    s_m = exp(j 2 pi m / M), m in 0..M-1 (uniform phase points).
    Point at phase index m carries Gray label gray(m) = m ^ (m >> 1), so
    adjacent phases differ by exactly one bit. Matches Module 3 Activity 3.1.
    """
    m_order = int(m_order)
    phases = 2 * np.pi * np.arange(m_order) / m_order
    return np.exp(1j * phases)


def map_bits_to_mpsk(bits: np.ndarray, m_order: int) -> np.ndarray:
    """Map a binary array to M-PSK complex symbols using Gray coding.

    Groups bits into log2(M) symbols (binary index b). Each bit pattern b is
    placed at phase index inverse_gray(b), so that adjacent phase positions
    carry Gray-adjacent bit patterns. Matches Module 3 Activity 3.1.
    """
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    bits_per_symbol = int(np.log2(m_order))
    assert 2 ** bits_per_symbol == m_order, "m_order must be a power of two"
    remainder = len(bits) % bits_per_symbol
    if remainder != 0:
        bits = np.pad(bits, (0, bits_per_symbol - remainder))
    bit_groups = bits.reshape(-1, bits_per_symbol)
    symbol_indices = np.array(
        [int("".join(map(str, g)), 2) for g in bit_groups], dtype=int
    )
    # Place bit pattern b at phase index inverse_gray(b) so adjacent phases
    # are Gray-adjacent (differ by exactly one bit).
    phase_indices = _gray_to_binary(symbol_indices).astype(int)
    points = mpsk_constellation(m_order)
    return points[phase_indices].astype(np.complex64)


def demod_mpsk(iq: np.ndarray, m_order: int) -> np.ndarray:
    """Nearest-neighbor M-PSK demodulation returning the original bit array.

    Finds the nearest phase index i; the received bits are the Gray label
    gray(i) = i ^ (i >> 1) of that phase position.
    """
    iq = np.asarray(iq, dtype=np.complex128).ravel()
    points = mpsk_constellation(m_order)
    bits_per_symbol = int(np.log2(m_order))
    d = np.abs(iq.reshape(-1, 1) - points.reshape(1, -1))
    phase_indices = np.argmin(d, axis=1)
    gray_labels = _binary_to_gray(phase_indices)
    bits = []
    for g in gray_labels:
        bits.extend([(int(g) >> k) & 1 for k in range(bits_per_symbol - 1, -1, -1)])
    return np.asarray(bits, dtype=np.uint8)


def fsk_modulate(
    bits: np.ndarray,
    sample_rate: float,
    tone_hz: list[float],
    samples_per_symbol: int = 8,
) -> np.ndarray:
    """M-FSK modulator: one tone per symbol from an orthogonal tone set.

    Each symbol emits a single complex exponential at its assigned tone.
    Module 3 Activity 3.2.
    """
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    m = len(tone_hz)
    bits_per_symbol = int(np.log2(m))
    assert 2 ** bits_per_symbol == m, "number of tones must be a power of two"
    remainder = len(bits) % bits_per_symbol
    if remainder != 0:
        bits = np.pad(bits, (0, bits_per_symbol - remainder))
    bit_groups = bits.reshape(-1, bits_per_symbol)
    symbol_indices = np.array(
        [int("".join(map(str, g)), 2) for g in bit_groups], dtype=int
    )
    t = np.arange(samples_per_symbol) / float(sample_rate)
    chunks = []
    for idx in symbol_indices:
        tone = float(tone_hz[int(idx)])
        chunks.append(np.exp(2j * np.pi * tone * t))
    return np.concatenate(chunks).astype(np.complex64)


def fsk_demodulate_noncoherent(
    iq: np.ndarray,
    sample_rate: float,
    tone_hz: list[float],
    samples_per_symbol: int = 8,
) -> np.ndarray:
    """Non-coherent M-FSK demod via envelope-detector filter bank.

    Correlates each symbol interval with each tone and picks the largest
    magnitude (unknown carrier phase). Returns Gray-coded bit array.
    Module 3 Activity 3.2.
    """
    iq = np.asarray(iq, dtype=np.complex128).ravel()
    m = len(tone_hz)
    bits_per_symbol = int(np.log2(m))
    n_sym = iq.size // samples_per_symbol
    shaped = iq[: n_sym * samples_per_symbol].reshape(n_sym, samples_per_symbol)
    t = np.arange(samples_per_symbol) / float(sample_rate)
    refs = [np.exp(2j * np.pi * float(f) * t) for f in tone_hz]
    energies = np.stack([np.abs(shaped @ np.conj(ref)) ** 2 for ref in refs], axis=1)
    symbol_indices = np.argmax(energies, axis=1)
    bits = []
    for idx in symbol_indices:
        bits.extend([(int(idx) >> k) & 1 for k in range(bits_per_symbol - 1, -1, -1)])
    return np.asarray(bits, dtype=np.uint8)


# --- Module 4: pulse shaping, ISI, eye diagrams ---


def rrc_filter(alpha: float, sps: int, num_taps: int) -> np.ndarray:
    """Root-Raised Cosine FIR impulse response (normalized to unit energy).

    alpha: roll-off in [0, 1], sps: samples per symbol, num_taps: filter length
    (made odd if even). Matches Module 4 (H_tx = H_rx = sqrt(H_RC)).
    """
    alpha = float(alpha)
    sps = int(sps)
    num_taps = int(num_taps)
    if num_taps % 2 == 0:
        num_taps += 1
    t = (np.arange(num_taps) - (num_taps - 1) / 2) / float(sps)
    h = np.zeros(num_taps, dtype=np.float64)
    four_alpha_t = 4.0 * alpha * t
    for i, ti in enumerate(t):
        if abs(ti) < 1e-12:
            h[i] = 1.0 - alpha + 4.0 * alpha / np.pi
        elif abs(abs(four_alpha_t[i]) - 1.0) < 1e-9:
            h[i] = (
                alpha
                / np.sqrt(2.0)
                * (
                    (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * alpha))
                    + (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * alpha))
                )
            )
        else:
            num = np.sin((1.0 - alpha) * np.pi * ti) + four_alpha_t[i] * np.cos(
                (1.0 + alpha) * np.pi * ti
            )
            den = np.pi * ti * (1.0 - four_alpha_t[i] ** 2)
            h[i] = num / den
    h = h / np.sqrt(np.sum(h ** 2))  # unit energy
    return h


def rc_response(alpha: float, sps: int, num_taps: int) -> np.ndarray:
    """Raised Cosine impulse response = RRC * RRC (cascade of TX + RX filters)."""
    h = rrc_filter(alpha, sps, num_taps)
    return np.convolve(h, h)


def apply_rrc(
    iq: np.ndarray, alpha: float, sps: int, num_taps: int = 101
) -> np.ndarray:
    """Apply RRC pulse shaping (or matched filtering) to complex baseband."""
    from scipy.signal import lfilter

    iq = np.asarray(iq, dtype=np.complex128)
    h = rrc_filter(alpha, sps, num_taps)
    return lfilter(h, [1.0], iq).astype(np.complex64)


def eye_diagram(
    iq: np.ndarray, sps: int, span_symbols: int = 2
) -> tuple[np.ndarray, np.ndarray]:
    """Slice baseband into overlapping span_symbols segments for an eye diagram.

    Returns (time_axis_in_symbols, segments) with segments shape
    (n_segments, span_symbols*sps). Module 4 Activity 4.2.
    """
    iq = np.asarray(iq, dtype=np.complex128).ravel()
    samples_per_window = span_symbols * sps
    n_sym = iq.size // sps
    n_seg = n_sym - span_symbols + 1
    if n_seg < 1:
        return np.array([]), np.array([]).reshape(0, samples_per_window)
    segs = np.array(
        [iq[k * sps : k * sps + samples_per_window] for k in range(n_seg)]
    )
    t = np.arange(samples_per_window) / float(sps)
    return t, segs


def save_eye_diagram(
    path,
    iq,
    sps: int,
    span_symbols: int = 2,
    title: str = "Eye diagram",
    real_only: bool = True,
):
    """Render an eye diagram (I and optionally Q overlaid) from baseband IQ."""
    from pathlib import Path

    t, segs = eye_diagram(iq, sps, span_symbols)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    if segs.size:
        series = segs.real if real_only else np.stack([segs.real, segs.imag])
        labels = ["I"] if real_only else ["I", "Q"]
        for y, label in zip(series, labels):
            ax.plot(t, y, linewidth=0.6, alpha=0.4, label=label)
    ax.set_xlabel("Time (symbols)")
    ax.set_ylabel("Amplitude")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p = Path(path)
    fig.savefig(p, dpi=120)
    plt.close(fig)
    return p


def matched_filter_snr(
    tx_symbols: np.ndarray,
    rx_noisy: np.ndarray,
    alpha: float,
    sps: int,
    num_taps: int = 101,
) -> tuple[float, float]:
    """Output SNR before vs after RRC matched filtering (Module 4 Activity 4.3).

    Returns (snr_before_db, snr_after_db). Filtering both TX and RX with the
    same RRC demonstrates the matched filter maximizing output SNR.
    """
    from scipy.signal import lfilter

    tx = np.asarray(tx_symbols, dtype=np.complex128).ravel()
    rx = np.asarray(rx_noisy, dtype=np.complex128).ravel()
    n = min(tx.size, rx.size)
    tx, rx = tx[:n], rx[:n]
    noise_before = rx - tx
    snr_before = 10 * np.log10(
        np.mean(np.abs(tx) ** 2) / max(np.mean(np.abs(noise_before) ** 2), 1e-20)
    )
    h = rrc_filter(alpha, sps, num_taps)
    tx_f = lfilter(h, [1.0], tx)
    rx_f = lfilter(h, [1.0], rx)
    n_f = min(tx_f.size, rx_f.size)
    noise_after = rx_f[:n_f] - tx_f[:n_f]
    snr_after = 10 * np.log10(
        np.mean(np.abs(tx_f[:n_f]) ** 2)
        / max(np.mean(np.abs(noise_after) ** 2), 1e-20)
    )
    return float(snr_before), float(snr_after)


# --- Module 5: channel coding & BER performance ---


def hamming74_encode(data_bits: np.ndarray) -> np.ndarray:
    """(7, 4) Hamming systematic encoder.

    Input: bit array length multiple of 4. Output: 7-bit codewords laid out as
    [p1, p2, d1, p3, d2, d3, d4] (parity positions 1,2,4; data positions 3,5,6,7).
    Module 5 Activity 5.2.
    """
    data_bits = np.asarray(data_bits, dtype=np.uint8).ravel()
    pad = (-data_bits.size) % 4
    if pad:
        data_bits = np.pad(data_bits, (0, pad))
    n_blocks = data_bits.size // 4
    blocks = data_bits.reshape(n_blocks, 4)
    d1, d2, d3, d4 = blocks[:, 0], blocks[:, 1], blocks[:, 2], blocks[:, 3]
    p1 = d1 ^ d2 ^ d4  # parity over positions 1,3,5,7
    p2 = d1 ^ d3 ^ d4  # parity over positions 2,3,6,7
    p3 = d2 ^ d3 ^ d4  # parity over positions 4,5,6,7
    codewords = np.stack([p1, p2, d1, p3, d2, d3, d4], axis=1)
    return codewords.ravel().astype(np.uint8)


def hamming74_decode(encoded: np.ndarray) -> np.ndarray:
    """(7, 4) Hamming syndrome decoder with single-error correction.

    Syndrome = s1 + 2*s2 + 4*s3 gives the 1-indexed error position (0 = none).
    Recovers the 4 data bits per codeword.
    """
    encoded = np.asarray(encoded, dtype=np.uint8).ravel()
    n_blocks = encoded.size // 7
    blocks = encoded.reshape(n_blocks, 7)
    r = blocks
    s1 = r[:, 0] ^ r[:, 2] ^ r[:, 4] ^ r[:, 6]
    s2 = r[:, 1] ^ r[:, 2] ^ r[:, 5] ^ r[:, 6]
    s3 = r[:, 3] ^ r[:, 4] ^ r[:, 5] ^ r[:, 6]
    syndrome = s1 + 2 * s2 + 4 * s3  # 1-indexed error position; 0 = clean
    corrected = blocks.copy()
    rows = np.arange(n_blocks)
    nonzero = syndrome != 0
    corrected[rows[nonzero], syndrome[nonzero] - 1] ^= 1
    data = corrected[:, [2, 4, 5, 6]]  # data positions 3,5,6,7 (1-indexed)
    return data.ravel().astype(np.uint8)


def ber_psk_theoretical(ebno_db) -> np.ndarray:
    """Theoretical BPSK BER in AWGN: Q(sqrt(2 Eb/N0)) = 0.5*erfc(sqrt(Eb/N0)).

    Module 5 Activity 5.1.
    """
    from scipy.special import erfc

    ebno = np.atleast_1d(np.asarray(ebno_db, dtype=np.float64))
    ebno_linear = 10.0 ** (ebno / 10.0)
    return 0.5 * erfc(np.sqrt(ebno_linear))


def monte_carlo_ber_bpsk(ebno_db_range, num_bits: int = 1000000, seed: int = 0):
    """Monte Carlo BPSK BER over AWGN vs theoretical curves.

    Transmits num_bits BPSK symbols across ebno_db_range (dB). Matches
    Module 5 Activity 5.1 (0 dB to 12 dB in 1 dB steps).
    Returns (ber_simulated, ber_theoretical).
    """
    from scipy.special import erfc

    ebno_db_range = np.atleast_1d(np.asarray(ebno_db_range, dtype=np.float64))
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, num_bits).astype(np.uint8)
    symbols = 2 * bits.astype(np.float64) - 1.0  # 0 -> -1, 1 -> +1
    ber_sim = []
    ber_theo = []
    for ebno_db in ebno_db_range:
        ebno_linear = 10.0 ** (ebno_db / 10.0)
        sigma = np.sqrt(1.0 / (2.0 * ebno_linear))
        noise = rng.normal(0, sigma, num_bits)
        received = symbols + noise
        decisions = (received > 0).astype(np.uint8)
        ber_sim.append(float(np.mean(bits != decisions)))
        ber_theo.append(float(0.5 * erfc(np.sqrt(ebno_linear))))
    return np.array(ber_sim), np.array(ber_theo)


def shannon_capacity(B: float, snr_linear: float) -> float:
    """Shannon-Hartley channel capacity: C = B log2(1 + SNR). Module 5."""
    return float(B * np.log2(1.0 + float(snr_linear)))
