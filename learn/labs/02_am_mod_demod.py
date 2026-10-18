#!/usr/bin/env python3
"""Lesson 02: DSB-AM modulate / envelope demodulate with plots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

LABS = Path(__file__).resolve().parent
sys.path.insert(0, str(LABS))

from dsp_common import (  # noqa: E402
    am_demodulate_envelope,
    am_modulate,
    report_dir,
    save_spectrum_plot,
    save_time_plot,
    spectrum_db,
    write_report,
)


def main(argv=None):
    p = argparse.ArgumentParser(description="AM mod/demod lab (learn/02)")
    p.add_argument("--rate", type=float, default=200_000.0)
    p.add_argument("--carrier-hz", type=float, default=20_000.0)
    p.add_argument("--message-hz", type=float, default=1_000.0)
    p.add_argument("--depth", type=float, default=0.7)
    p.add_argument("--ms", type=float, default=20.0)
    args = p.parse_args(argv)

    n = int(args.rate * args.ms / 1000.0)
    t = np.arange(n) / args.rate
    message = np.sin(2 * np.pi * args.message_hz * t)
    t, rf = am_modulate(message, args.carrier_hz, args.rate, depth=args.depth)
    recovered = am_demodulate_envelope(rf)

    # Correlation of recovered vs message (skip edge transients)
    sl = slice(n // 10, -n // 10)
    corr = float(np.corrcoef(message[sl], recovered[sl])[0, 1])
    ok = corr > 0.85

    out = report_dir("02_am")
    show = min(n, int(args.rate / args.message_hz * 6))
    time_path = out / "time.png"
    save_time_plot(
        time_path,
        t[:show],
        [message[:show], rf[:show] / np.max(np.abs(rf)), recovered[:show]],
        ["message", "RF (scaled)", "envelope"],
        "AM modulate / demodulate",
    )
    # Treat real RF as analytic for spectrum view
    freqs, psd = spectrum_db(rf.astype(np.complex128), args.rate)
    spec_path = out / "spectrum.png"
    save_spectrum_plot(spec_path, freqs, psd, "AM RF spectrum")
    # IQ after baseband shift of RF (for constellation-style I/Q plot)
    lo = np.exp(-2j * np.pi * args.carrier_hz * t)
    baseband = (rf * lo).astype(np.complex128)
    # crude LPF via moving average
    k = max(8, int(args.rate / args.carrier_hz))
    baseband = np.convolve(baseband, np.ones(k) / k, mode="same")
    iq_path = out / "iq_baseband.png"
    from dsp_common import save_iq_trajectory

    save_iq_trajectory(iq_path, baseband[:: max(1, n // 4000)], "AM baseband IQ path")

    report = {
        "status": "pass" if ok else "fail",
        "correlation": corr,
        "carrier_hz": args.carrier_hz,
        "message_hz": args.message_hz,
        "depth": args.depth,
        "plots": {
            "time": str(time_path.relative_to(out.parents[2])),
            "spectrum": str(spec_path.relative_to(out.parents[2])),
            "iq": str(iq_path.relative_to(out.parents[2])),
        },
    }
    write_report(out, report)
    print(f"status={report['status']} correlation={corr:.3f}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
