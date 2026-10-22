#!/usr/bin/env python3
"""Lesson 09 lab: constellation impairment diagnosis (Module 2 Activity 2.3).

Transmits clean QPSK then applies, separately and combined:
  CFO   -> constellation rotation
  phase noise -> arc-smearing / blur
  AWGN  -> radial spreading
Plots the resulting constellations so each impairment's visual signature is clear.
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
    apply_cfo,
    apply_phase_noise,
    awgn_ebno,
    qpsk_constellation,
    qpsk_modulate,
    report_dir,
    save_constellation_plot,
    write_report,
)


def main(argv=None):
    require_lessons()
    p = argparse.ArgumentParser(description="Constellation impairments (lesson/09)")
    p.add_argument("--snr-db", type=float, default=15.0)
    p.add_argument("--cfo-hz", type=float, default=25_000.0)
    p.add_argument("--phase-noise-rad", type=float, default=0.15)
    p.add_argument("--sps", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    bits = np.random.default_rng(args.seed).integers(0, 2, 256).astype(np.uint8)
    tx = qpsk_modulate(bits, args.sps)
    ideal = qpsk_constellation()
    n_sym = tx.size // args.sps
    tx_sym = tx[: n_sym * args.sps].reshape(n_sym, args.sps).mean(axis=1)

    out = report_dir("09_impairments")

    def syms_from(iq):
        return iq[: n_sym * args.sps].reshape(n_sym, args.sps).mean(axis=1)

    cases = {
        "clean": tx_sym,
        "cfo": syms_from(apply_cfo(tx, 100_000.0, args.cfo_hz)),
        "phase_noise": syms_from(
            apply_phase_noise(tx, 100_000.0, args.phase_noise_rad, seed=args.seed)
        ),
        "awgn": syms_from(awgn_ebno(tx, args.snr_db, bits_per_symbol=2, seed=args.seed)),
        "combined": syms_from(
            awgn_ebno(
                apply_phase_noise(
                    apply_cfo(tx, 100_000.0, args.cfo_hz),
                    100_000.0,
                    args.phase_noise_rad,
                    seed=args.seed,
                ),
                args.snr_db,
                bits_per_symbol=2,
                seed=args.seed + 1,
            )
        ),
    }

    results = {}
    for label, syms in cases.items():
        path = out / f"{label}.png"
        save_constellation_plot(
            path,
            syms,
            f"QPSK — {label.replace('_', ' ').title()}",
            ideal=ideal,
        )
        # Impairment signature: RMS distance from nearest ideal point
        d = np.abs(syms.reshape(-1, 1) - ideal.reshape(1, -1))
        nearest = np.argmin(d, axis=1)
        rms_err = float(np.sqrt(np.mean(np.abs(syms - ideal[nearest]) ** 2)))
        results[label] = {"rms_err": rms_err}
        results[label]["path"] = str(path.relative_to(out.parents[2]))

    ok = (
        results["cfo"]["rms_err"] > results["clean"]["rms_err"]
        and results["phase_noise"]["rms_err"] > results["clean"]["rms_err"]
        and results["awgn"]["rms_err"] > results["clean"]["rms_err"]
    )
    report = {
        "status": "pass" if ok else "fail",
        "snr_db": args.snr_db,
        "cfo_hz": args.cfo_hz,
        "phase_noise_rad": args.phase_noise_rad,
        "results": {k: {"rms_err": v["rms_err"]} for k, v in results.items()},
        "plots": {k: v["path"] for k, v in results.items()},
    }
    write_report(out, report)
    print(f"status={report['status']}")
    for label, v in results.items():
        print(f"  {label:12s} rms_err={v['rms_err']:.4f}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
