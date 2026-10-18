#!/usr/bin/env python3
"""Lesson 10 lab: M-FSK modulate / non-coherent demodulate (Module 3 Activity 3.2).

4-FSK with orthogonal tones and an envelope-detector filter-bank demodulator
(unknown carrier phase). Reports bit error rate and plots the FSK spectrum.
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
    bit_error_rate,
    fsk_demodulate_noncoherent,
    fsk_modulate,
    report_dir,
    save_spectrum_plot,
    spectrum_db,
    write_report,
)


def main(argv=None):
    p = argparse.ArgumentParser(description="M-FSK non-coherent (learn/10)")
    p.add_argument("--tones", type=float, nargs="+", default=[10e3, 22.5e3, 35e3, 47.5e3])
    p.add_argument("--rate", type=float, default=200_000.0)
    p.add_argument("--ebno-db", type=float, default=10.0)
    p.add_argument("--sps", type=int, default=16)
    p.add_argument("--num-syms", type=int, default=200)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    m = len(args.tones)
    bits_per_symbol = int(np.log2(m))
    assert 2 ** bits_per_symbol == m, "number of tones must be a power of two"

    rng = np.random.default_rng(args.seed)
    bits = rng.integers(0, 2, args.num_syms * bits_per_symbol).astype(np.uint8)

    tx = fsk_modulate(bits, args.rate, args.tones, samples_per_symbol=args.sps)
    rx = awgn_ebno(tx, args.ebno_db, bits_per_symbol=bits_per_symbol, seed=args.seed)
    rx_bits = fsk_demodulate_noncoherent(rx, args.rate, args.tones, samples_per_symbol=args.sps)
    ber = bit_error_rate(bits, rx_bits[: bits.size])

    out = report_dir("10_mfsk")
    freqs, psd = spectrum_db(tx, args.rate)
    spec_path = out / "spectrum.png"
    save_spectrum_plot(spec_path, freqs, psd, f"{m}-FSK spectrum (tones {[int(f) for f in args.tones]} Hz)")

    ok = ber < 1e-2
    report = {
        "status": "pass" if ok else "fail",
        "m": m,
        "ebno_db": args.ebno_db,
        "sps": args.sps,
        "num_syms": args.num_syms,
        "ber": float(ber),
        "plots": {"spectrum": str(spec_path.relative_to(out.parents[2]))},
    }
    write_report(out, report)
    print(f"status={report['status']} ber={ber:.4e}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
