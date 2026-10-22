#!/usr/bin/env python3
"""Lesson 03: complex baseband FM modulate / demodulate with plots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from harness.ready import require_lessons  # noqa: E402
from software.dsp.common import (  # noqa: E402
    fm_demodulate,
    fm_modulate,
    report_dir,
    save_iq_trajectory,
    save_spectrum_plot,
    save_time_plot,
    spectrum_db,
    write_report,
)


def main(argv=None):
    require_lessons()
    p = argparse.ArgumentParser(description="FM mod/demod lab (lesson/03)")
    p.add_argument("--rate", type=float, default=200_000.0)
    p.add_argument("--message-hz", type=float, default=1_000.0)
    p.add_argument("--deviation", type=float, default=5_000.0)
    p.add_argument("--ms", type=float, default=20.0)
    args = p.parse_args(argv)

    n = int(args.rate * args.ms / 1000.0)
    t = np.arange(n) / args.rate
    message = np.sin(2 * np.pi * args.message_hz * t).astype(np.float64)
    iq = fm_modulate(message, args.rate, args.deviation)
    freq = fm_demodulate(iq, args.rate)
    # Normalize demod to [-1, 1] for correlation with message
    recovered = freq / max(np.max(np.abs(freq)), 1e-12)

    sl = slice(n // 10, -n // 10)
    corr = float(np.corrcoef(message[sl], recovered[sl])[0, 1])
    ok = corr > 0.9

    out = report_dir("03_fm")
    show = min(n, int(args.rate / args.message_hz * 6))
    time_path = out / "time.png"
    save_time_plot(
        time_path,
        t[:show],
        [message[:show], recovered[:show]],
        ["message", "demod Hz (norm)"],
        "FM modulate / demodulate",
    )
    freqs, psd = spectrum_db(iq, args.rate)
    spec_path = out / "spectrum.png"
    save_spectrum_plot(spec_path, freqs, psd, "FM complex baseband spectrum")
    traj_path = out / "iq_trajectory.png"
    save_iq_trajectory(traj_path, iq, "FM IQ trajectory (constant envelope)")

    report = {
        "status": "pass" if ok else "fail",
        "correlation": corr,
        "deviation_hz": args.deviation,
        "message_hz": args.message_hz,
        "plots": {
            "time": str(time_path.relative_to(out.parents[2])),
            "spectrum": str(spec_path.relative_to(out.parents[2])),
            "iq_trajectory": str(traj_path.relative_to(out.parents[2])),
        },
    }
    write_report(out, report)
    print(f"status={report['status']} correlation={corr:.3f}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
