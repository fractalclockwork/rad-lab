#!/usr/bin/env python3
"""Lesson 05: 16-QAM constellation under AWGN + symbol/bit error rates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

LABS = Path(__file__).resolve().parent
sys.path.insert(0, str(LABS))

from dsp_common import (  # noqa: E402
    awgn,
    bit_error_rate,
    bits_from_text,
    qam16_constellation,
    qam16_demodulate,
    qam16_modulate,
    report_dir,
    save_constellation_plot,
    save_spectrum_plot,
    spectrum_db,
    write_report,
)


def main(argv=None):
    p = argparse.ArgumentParser(description="16-QAM constellation lab (learn/05)")
    p.add_argument("--text", default="RADLAB-QAM16")
    p.add_argument("--snr-db", type=float, default=18.0)
    p.add_argument("--sps", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    bits = bits_from_text(args.text)
    tx = qam16_modulate(bits, args.sps)
    rx = awgn(tx, args.snr_db, seed=args.seed)
    rx_bits = qam16_demodulate(rx, args.sps)
    ber = bit_error_rate(bits, rx_bits[: bits.size])

    # Symbol error: compare hard decisions on averaged symbols
    n_sym = tx.size // args.sps
    tx_sym = tx.reshape(n_sym, args.sps).mean(axis=1)
    rx_sym = rx.reshape(n_sym, args.sps).mean(axis=1)
    ideal = qam16_constellation()
    tx_idx = np.argmin(np.abs(tx_sym.reshape(-1, 1) - ideal.reshape(1, -1)), axis=1)
    rx_idx = np.argmin(np.abs(rx_sym.reshape(-1, 1) - ideal.reshape(1, -1)), axis=1)
    ser = float(np.mean(tx_idx != rx_idx))

    out = report_dir("05_qam16")
    const_path = out / "constellation.png"
    save_constellation_plot(
        const_path,
        rx_sym,
        f"16-QAM @ {args.snr_db} dB SNR",
        ideal=ideal,
    )
    freqs, psd = spectrum_db(tx, 100_000.0)
    spec_path = out / "spectrum.png"
    save_spectrum_plot(spec_path, freqs, psd, "16-QAM spectrum")

    ok = ber < 1e-3 and ser < 1e-3
    report = {
        "status": "pass" if ok else "fail",
        "text": args.text,
        "snr_db": args.snr_db,
        "ber": ber,
        "ser": ser,
        "plots": {
            "constellation": str(const_path.relative_to(out.parents[2])),
            "spectrum": str(spec_path.relative_to(out.parents[2])),
        },
    }
    write_report(out, report)
    print(f"status={report['status']} ber={ber:.3e} ser={ser:.3e}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
