#!/usr/bin/env python3
"""Lesson 01 lab: complex tone time + spectrum plots (synthetic IQ)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from harness.ready import require_lessons  # noqa: E402
from software.dsp.common import (  # noqa: E402
    report_dir,
    save_spectrum_plot,
    save_time_plot,
    spectrum_db,
    write_report,
)


def synthesize_tone(sample_rate: float, tone_hz: float, n: int) -> np.ndarray:
    t = np.arange(n) / float(sample_rate)
    return (0.7 * np.exp(2j * np.pi * tone_hz * t)).astype(np.complex64)


def main(argv=None):
    require_lessons()
    p = argparse.ArgumentParser(description="Plot synthetic complex tone (lesson/01)")
    p.add_argument("--rate", type=float, default=2_000_000.0)
    p.add_argument("--tone-hz", type=float, default=100_000.0)
    p.add_argument("--ms", type=float, default=5.0)
    args = p.parse_args(argv)

    n = max(4096, int(args.rate * args.ms / 1000.0))
    iq = synthesize_tone(args.rate, args.tone_hz, n)
    t = np.arange(n) / args.rate
    out = report_dir("01_iq_tone")
    # Show a short slice so the tone period is visible
    show = min(n, int(args.rate / args.tone_hz * 8))
    time_path = out / "time.png"
    save_time_plot(
        time_path,
        t[:show],
        [iq.real[:show], iq.imag[:show]],
        ["I", "Q"],
        f"Complex tone @ {args.tone_hz/1e3:.0f} kHz",
    )
    freqs, psd = spectrum_db(iq, args.rate)
    spec_path = out / "spectrum.png"
    save_spectrum_plot(spec_path, freqs, psd, "Tone spectrum")
    peak_hz = float(freqs[np.argmax(psd)])
    ok = abs(peak_hz - args.tone_hz) < args.rate / n * 4
    report = {
        "status": "pass" if ok else "fail",
        "sample_rate": args.rate,
        "tone_hz": args.tone_hz,
        "peak_hz": peak_hz,
        "plots": {
            "time": str(time_path.relative_to(out.parents[2])),
            "spectrum": str(spec_path.relative_to(out.parents[2])),
        },
    }
    write_report(out, report)
    print(f"status={report['status']} peak_hz={peak_hz:.1f}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
