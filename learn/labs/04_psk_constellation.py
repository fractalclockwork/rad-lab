#!/usr/bin/env python3
"""Lesson 04: BPSK and QPSK constellations + BER vs SNR."""

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
    bpsk_demodulate,
    bpsk_modulate,
    qpsk_constellation,
    qpsk_demodulate,
    qpsk_modulate,
    report_dir,
    save_constellation_plot,
    save_spectrum_plot,
    spectrum_db,
    text_from_bits,
    write_report,
)


def main(argv=None):
    p = argparse.ArgumentParser(description="PSK constellation lab (learn/04)")
    p.add_argument("--text", default="RADLAB")
    p.add_argument("--snr-db", type=float, default=12.0)
    p.add_argument("--sps", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    bits = bits_from_text(args.text)
    out = report_dir("04_psk")

    # BPSK
    bpsk_tx = bpsk_modulate(bits, args.sps)
    bpsk_rx = awgn(bpsk_tx, args.snr_db, seed=args.seed)
    bpsk_bits = bpsk_demodulate(bpsk_rx, args.sps)
    bpsk_ber = bit_error_rate(bits, bpsk_bits[: bits.size])
    bpsk_syms = bpsk_rx.reshape(-1, args.sps).mean(axis=1)
    bpsk_path = out / "bpsk_constellation.png"
    save_constellation_plot(
        bpsk_path, bpsk_syms, f"BPSK @ {args.snr_db} dB SNR", ideal=np.array([1, -1])
    )

    # QPSK
    qpsk_tx = qpsk_modulate(bits, args.sps)
    qpsk_rx = awgn(qpsk_tx, args.snr_db, seed=args.seed + 1)
    qpsk_bits = qpsk_demodulate(qpsk_rx, args.sps)
    qpsk_ber = bit_error_rate(bits, qpsk_bits[: bits.size])
    qpsk_syms = qpsk_rx.reshape(-1, args.sps).mean(axis=1)
    qpsk_path = out / "qpsk_constellation.png"
    save_constellation_plot(
        qpsk_path,
        qpsk_syms,
        f"QPSK @ {args.snr_db} dB SNR",
        ideal=qpsk_constellation(),
    )

    sample_rate = 100_000.0
    freqs, psd = spectrum_db(qpsk_tx, sample_rate)
    spec_path = out / "qpsk_spectrum.png"
    save_spectrum_plot(spec_path, freqs, psd, "QPSK pulse spectrum")

    recovered = text_from_bits(qpsk_bits[: bits.size])
    ok = bpsk_ber < 1e-3 and qpsk_ber < 1e-3 and recovered.startswith(args.text[:3])

    report = {
        "status": "pass" if ok else "fail",
        "text": args.text,
        "snr_db": args.snr_db,
        "bpsk_ber": bpsk_ber,
        "qpsk_ber": qpsk_ber,
        "recovered_prefix": recovered[: len(args.text)],
        "plots": {
            "bpsk_constellation": str(bpsk_path.relative_to(out.parents[2])),
            "qpsk_constellation": str(qpsk_path.relative_to(out.parents[2])),
            "qpsk_spectrum": str(spec_path.relative_to(out.parents[2])),
        },
    }
    write_report(out, report)
    print(
        f"status={report['status']} bpsk_ber={bpsk_ber:.3e} qpsk_ber={qpsk_ber:.3e}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
