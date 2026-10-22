#!/usr/bin/env python3
"""Lesson 07 lab: digital up/down conversion (Module 1 Activity 1.3).

DUC shifts complex baseband to an offset carrier; DDC mixes it back.
Verifies the roundtrip and plots baseband vs upconverted spectra.
Synthetic IQ only; plots use matplotlib (Agg).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from harness.ready import require_lessons  # noqa: E402
from software.dsp.common import (  # noqa: E402
    ddc,
    duc,
    generate_complex_baseband,
    report_dir,
    save_spectrum_plot,
    save_time_plot,
    spectrum_db,
    write_report,
)


def main(argv=None):
    require_lessons()
    p = argparse.ArgumentParser(description="DUC/DDC roundtrip (lesson/07)")
    p.add_argument("--rate", type=float, default=2_000_000.0)
    p.add_argument("--tone-hz", type=float, default=100_000.0)
    p.add_argument("--offset-hz", type=float, default=250_000.0)
    p.add_argument("--ms", type=float, default=5.0)
    args = p.parse_args(argv)

    n = max(4096, int(args.rate * args.ms / 1000.0))
    iq, t = generate_complex_baseband(args.tone_hz, args.rate, n)

    # Digital upconversion then downconversion
    up = duc(iq, args.rate, args.offset_hz)
    back = ddc(up, args.rate, args.offset_hz)

    roundtrip_err = float(np.max(np.abs(iq - back)))
    ok = roundtrip_err < 1e-3

    out = report_dir("07_duc_ddc")
    show = min(n, int(args.rate / args.tone_hz * 8))
    time_path = out / "time.png"
    save_time_plot(
        time_path,
        t[:show],
        [iq.real[:show], iq.imag[:show], back.real[:show], back.imag[:show]],
        ["baseband I", "baseband Q", "roundtrip I", "roundtrip Q"],
        f"Baseband vs DUC/DDC roundtrip (offset {args.offset_hz/1e3:.0f} kHz)",
    )

    freqs, psd_base = spectrum_db(iq, args.rate)
    base_path = out / "spectrum_baseband.png"
    save_spectrum_plot(
        base_path, freqs, psd_base, f"Baseband tone @ {args.tone_hz/1e3:.0f} kHz"
    )

    freqs_u, psd_up = spectrum_db(up, args.rate)
    up_path = out / "spectrum_upconverted.png"
    save_spectrum_plot(
        up_path,
        freqs_u,
        psd_up,
        f"Upconverted @ {args.offset_hz/1e3:.0f} kHz + {args.tone_hz/1e3:.0f} kHz",
    )

    report = {
        "status": "pass" if ok else "fail",
        "sample_rate": args.rate,
        "tone_hz": args.tone_hz,
        "offset_hz": args.offset_hz,
        "roundtrip_max_err": roundtrip_err,
        "plots": {
            "time": str(time_path.relative_to(out.parents[2])),
            "spectrum_baseband": str(base_path.relative_to(out.parents[2])),
            "spectrum_upconverted": str(up_path.relative_to(out.parents[2])),
        },
    }
    write_report(out, report)
    print(f"status={report['status']} roundtrip_max_err={roundtrip_err:.2e}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
