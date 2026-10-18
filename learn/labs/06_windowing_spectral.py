#!/usr/bin/env python3
"""Lesson 06 lab: windowed spectral analysis (Module 1 Activity 1.2).

Compares rectangular, Hann, and Blackman windows on a complex tone:
spectral leakage, mainlobe width, and peak location.
Synthetic IQ only; plots use matplotlib (Agg).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

LABS = Path(__file__).resolve().parent
sys.path.insert(0, str(LABS))

from dsp_common import (  # noqa: E402
    generate_complex_baseband,
    report_dir,
    save_spectrum_plot,
    window_spectrum,
    write_report,
)


def main(argv=None):
    p = argparse.ArgumentParser(description="Windowed spectral analysis (learn/06)")
    p.add_argument("--rate", type=float, default=2_000_000.0)
    p.add_argument("--tone-hz", type=float, default=100_000.0)
    p.add_argument("--ms", type=float, default=5.0)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    n = max(4096, int(args.rate * args.ms / 1000.0))
    iq, t = generate_complex_baseband(args.tone_hz, args.rate, n)

    windows = ["rectangular", "hann", "blackman"]
    results = {}
    fig_axes = []

    # Overlay all three windowed spectra on one figure for direct comparison
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 3.5))
    for w in windows:
        freqs, psd = window_spectrum(iq, args.rate, window=w)
        peak_hz = float(freqs[np.argmax(psd)])
        # sidelobe level: max PSD outside the mainlobe bin
        peak_bin = int(np.argmax(psd))
        mask = np.ones(psd.size, dtype=bool)
        mask[max(0, peak_bin - 2) : peak_bin + 3] = False
        sidelobe_db = float(np.max(psd[mask])) if np.any(mask) else -np.inf
        results[w] = {
            "peak_hz": peak_hz,
            "peak_bin": peak_bin,
            "sidelobe_db": sidelobe_db,
            "peak_within_bins": bool(abs(peak_hz - args.tone_hz) < args.rate / n * 4),
        }
        ax.plot(freqs / 1e3, psd, linewidth=0.8, label=w)
    ax.set_xlabel("Frequency (kHz)")
    ax.set_ylabel("Power (dB)")
    ax.set_title(f"Windowed spectra, tone @ {args.tone_hz / 1e3:.0f} kHz")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out = report_dir("06_windowing")
    spec_path = out / "spectra.png"
    fig.savefig(spec_path, dpi=120)
    plt.close(fig)

    ok = all(r["peak_within_bins"] for r in results.values())
    report = {
        "status": "pass" if ok else "fail",
        "sample_rate": args.rate,
        "tone_hz": args.tone_hz,
        "windows": results,
        "plots": {"spectra": str(spec_path.relative_to(out.parents[2]))},
    }
    write_report(out, report)
    print(f"status={report['status']}")
    for w, r in results.items():
        print(
            f"  {w:11s} peak={r['peak_hz']:.1f} Hz "
            f"sidelobe={r['sidelobe_db']:.1f} dB "
            f"peak_ok={r['peak_within_bins']}"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
