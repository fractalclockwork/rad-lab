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
