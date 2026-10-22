"""Software DSP fixture that must pass before any TX HWIL burst."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

PEAK_TOLERANCE_HZ = 10_000.0


def evaluate_tone(metrics, tone_offset_hz, min_snr_db, tolerance_hz=PEAK_TOLERANCE_HZ):
    snr_db = float(metrics["snr_db"])
    peak_hz = float(metrics["peak_hz"])
    snr_ok = snr_db >= float(min_snr_db)
    peak_ok = abs(peak_hz - float(tone_offset_hz)) <= float(tolerance_hz)
    return {
        "pass": bool(snr_ok and peak_ok),
        "snr_ok": bool(snr_ok),
        "peak_ok": bool(peak_ok),
        "snr_db": snr_db,
        "peak_hz": peak_hz,
        "tone_offset_hz": float(tone_offset_hz),
        "min_snr_db": float(min_snr_db),
        "tolerance_hz": float(tolerance_hz),
    }


def assert_tone(metrics, tone_offset_hz, min_snr_db, tolerance_hz=PEAK_TOLERANCE_HZ):
    verdict = evaluate_tone(metrics, tone_offset_hz, min_snr_db, tolerance_hz)
    if not verdict["snr_ok"]:
        raise AssertionError(
            f"loopback SNR {verdict['snr_db']:.1f} dB below {min_snr_db} dB"
        )
    if not verdict["peak_ok"]:
        raise AssertionError(
            f"loopback peak {verdict['peak_hz']:.1f} Hz more than "
            f"{tolerance_hz} Hz from expected {tone_offset_hz} Hz"
        )
    return verdict


def synthesize_tone(sample_rate, tone_offset_hz, n_samples, snr_db=25.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n_samples) / float(sample_rate)
    tone = np.exp(2j * np.pi * tone_offset_hz * t)
    noise_power = 10 ** (-snr_db / 10.0)
    noise = (
        rng.normal(scale=np.sqrt(noise_power / 2), size=n_samples)
        + 1j * rng.normal(scale=np.sqrt(noise_power / 2), size=n_samples)
    )
    return (tone + noise).astype(np.complex64)


def measure_tone_snr(iq, sample_rate, tone_offset_hz, bin_half_width_hz=None):
    """Return SNR (dB) of a complex baseband tone near tone_offset_hz."""
    iq = np.asarray(iq, dtype=np.complex64)
    n = iq.size
    if n < 64:
        raise ValueError("need at least 64 samples")
    window = np.hanning(n).astype(np.float32)
    spectrum = np.fft.fftshift(np.fft.fft(iq * window))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / sample_rate))
    power = np.abs(spectrum) ** 2
    if bin_half_width_hz is None:
        bin_half_width_hz = max(sample_rate / n * 3, 1000.0)
    tone_mask = np.abs(freqs - tone_offset_hz) <= bin_half_width_hz
    if not np.any(tone_mask):
        raise ValueError("tone bin mask empty")
    # Exclude DC and the tone bins from noise estimate.
    noise_mask = (~tone_mask) & (np.abs(freqs) > sample_rate / n * 2)
    tone_power = float(np.max(power[tone_mask]))
    noise_power = float(np.median(power[noise_mask])) if np.any(noise_mask) else 1e-20
    snr_db = 10.0 * np.log10(tone_power / max(noise_power, 1e-20))
    # Peak search over non-DC bins. Quadrature receivers (e.g. HackRF) inject a
    # DC/LO-leakage spike that is a measurement artifact, not a received signal;
    # including it would pin the global argmax to 0 Hz. This mirrors the DC guard
    # already applied to the noise estimate, so a genuinely absent or mis-tuned
    # tone still yields a peak elsewhere and fails assert_tone_peak.
    dc_free = np.abs(freqs) > sample_rate / n * 2
    # Exclude band edges where LO leakage / DC-offset images can dominate the
    # argmax on weak loopback signals (direct-conversion receivers inject
    # artifacts near +/- Nyquist that are not the tone under test).
    edge_guard_hz = max(sample_rate / n * 10, sample_rate * 0.01)
    edge_free = dc_free & (np.abs(freqs) < sample_rate / 2.0 - edge_guard_hz)
    if np.any(edge_free):
        peak_hz = float(freqs[edge_free][np.argmax(power[edge_free])])
    elif np.any(dc_free):
        peak_hz = float(freqs[dc_free][np.argmax(power[dc_free])])
    else:
        peak_hz = float(freqs[np.argmax(power)])
    return {
        "snr_db": float(snr_db),
        "peak_hz": peak_hz,
        "tone_offset_hz": float(tone_offset_hz),
        "tone_power": float(tone_power),
        "noise_power": float(noise_power),
        "n_samples": int(n),
    }


def run_fixture(board, out_dir=None):
    """Generate a synthetic tone and verify the analyzer meets min_snr_db."""
    sample_rate = int(board["sample_rate"])
    tone_offset_hz = float(board["tone_offset_hz"])
    min_snr = float(board.get("min_snr_db", 10.0))
    n_samples = max(4096, int(sample_rate * 0.05))
    iq = synthesize_tone(sample_rate, tone_offset_hz, n_samples, snr_db=min_snr + 10)
    metrics = measure_tone_snr(iq, sample_rate, tone_offset_hz)
    ok = metrics["snr_db"] >= min_snr
    result = {
        "status": "pass" if ok else "fail",
        "metrics": metrics,
        "min_snr_db": min_snr,
    }
    if out_dir is not None:
        path = Path(out_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / "fixture.json").write_text(json.dumps(result, indent=2) + "\n")
    if not ok:
        raise AssertionError(
            f"fixture SNR {metrics['snr_db']:.1f} dB below min {min_snr} dB"
        )
    return result
