#!/usr/bin/env python3
"""Lesson 08 lab: AWGN calibrated to Eb/N0 (Module 2 Activity 2.1).

Adds complex AWGN to QPSK symbols at several Eb/N0 values and verifies the
measured noise power follows SNR = (Eb/N0) * eta_s. Plots constellations.
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
    awgn_ebno,
    qpsk_constellation,
    qpsk_modulate,
    report_dir,
    save_constellation_plot,
    save_spectrum_plot,
    spectrum_db,
    write_report,
)


def main(argv=None):
    p = argparse.ArgumentParser(description="AWGN vs Eb/N0 (learn/08)")
    p.add_argument("--ebno-db", type=float, nargs="+", default=[0, 6, 12, 18])
    p.add_argument("--sps", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    bits = np.random.default_rng(args.seed).integers(0, 2, 512).astype(np.uint8)
    tx = qpsk_modulate(bits, args.sps)
    ideal = qpsk_constellation()

    out = report_dir("08_awgn_ebno")
    results = {}

    for ebno_db in args.ebno_db:
        rx = awgn_ebno(tx, ebno_db, bits_per_symbol=2, seed=args.seed + int(ebno_db))
        # Measure SNR on raw IQ samples: SNR = (Eb/N0) * eta_s, eta_s = 2 for QPSK
        signal_power = float(np.mean(np.abs(tx) ** 2))
        noise_power = float(np.mean(np.abs(rx - tx) ** 2))
        snr_db = 10 * np.log10(signal_power / max(noise_power, 1e-20))
        expected_snr_db = ebno_db + 10 * np.log10(2.0)  # eta_s = 2 for QPSK
        results[float(ebno_db)] = {
            "snr_db": float(snr_db),
            "expected_snr_db": float(expected_snr_db),
            "snr_error_db": float(snr_db - expected_snr_db),
        }
        n_sym = tx.size // args.sps
        rx_sym = rx[: n_sym * args.sps].reshape(n_sym, args.sps).mean(axis=1)
        c_path = out / f"constellation_ebno{int(ebno_db)}.png"
        save_constellation_plot(
            c_path,
            rx_sym,
            f"QPSK @ {ebno_db} dB Eb/N0 (meas SNR {snr_db:.1f} dB)",
            ideal=ideal,
        )

    freqs, psd = spectrum_db(tx, 100_000.0)
    spec_path = out / "spectrum.png"
    save_spectrum_plot(spec_path, freqs, psd, "QPSK spectrum")

    ok = all(
        abs(r["snr_error_db"]) < 2.0 for r in results.values()
    )  # within 2 dB of theory
    report = {
        "status": "pass" if ok else "fail",
        "sps": args.sps,
        "results": results,
        "plots": {
            "spectrum": str(spec_path.relative_to(out.parents[2])),
            **{
                f"constellation_ebno{int(k)}": str(
                    (out / f"constellation_ebno{int(k)}.png").relative_to(out.parents[2])
                )
                for k in results
            },
        },
    }
    write_report(out, report)
    print(f"status={report['status']}")
    for ebno_db, r in results.items():
        print(
            f"  Eb/N0={ebno_db:5.1f} dB  meas SNR={r['snr_db']:6.1f} dB "
            f"expected={r['expected_snr_db']:6.1f} dB err={r['snr_error_db']:+.1f} dB"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
