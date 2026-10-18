#!/usr/bin/env python3
"""Lesson 13 lab: (7,4) Hamming code & coding gain (Module 5 Activity 5.2).

Compares uncoded BPSK vs (7,4) Hamming-coded BPSK over AWGN as a function of
information-bit Eb/N0. The code rate is 4/7, so coded symbols run at
Eb/N0 * 4/7 symbol SNR. Reports the coding gain at BER = 1e-3.
Synthetic IQ only; plots use matplotlib (Agg).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

LABS = Path(__file__).resolve().parent
sys.path.insert(0, str(LABS))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from dsp_common import (  # noqa: E402
    awgn,
    awgn_ebno,
    ber_psk_theoretical,
    bit_error_rate,
    bpsk_demodulate,
    bpsk_modulate,
    hamming74_decode,
    hamming74_encode,
    report_dir,
    save_spectrum_plot,
    spectrum_db,
    write_report,
)

CODE_RATE = 4.0 / 7.0  # (7,4) Hamming


def interp_ebno_at_ber(ebno_db, ber, target=1e-3):
    """Eb/N0 at which the BER curve crosses target (linear interp in log-BER)."""
    ber = np.asarray(ber)
    ebno_db = np.asarray(ebno_db)
    if ber.size < 2:
        return float("nan")
    # find crossing
    above = ber >= target
    if not np.any(above):
        return float(ebno_db[-1])
    if not np.any(~above):
        return float(ebno_db[0])
    # last index above target, first below
    idx = np.where(above)[0][-1]
    if idx + 1 >= ebno_db.size:
        return float(ebno_db[idx])
    x0, x1 = ebno_db[idx], ebno_db[idx + 1]
    y0, y1 = np.log10(max(ber[idx], 1e-12)), np.log10(max(ber[idx + 1], 1e-12))
    yt = np.log10(target)
    if y1 == y0:
        return float(x0)
    return float(x0 + (x1 - x0) * (yt - y0) / (y1 - y0))


def main(argv=None):
    p = argparse.ArgumentParser(description="Hamming (7,4) coding gain (learn/13)")
    p.add_argument("--ebno-min", type=float, default=0.0)
    p.add_argument("--ebno-max", type=float, default=12.0)
    p.add_argument("--num-info-bits", type=int, default=200000)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    ebno_db = np.arange(args.ebno_min, args.ebno_max + 1.0, 1.0)
    rate = CODE_RATE
    coded_snr_db = ebno_db + 10 * np.log10(rate)  # symbol SNR for coded bits

    rng = np.random.default_rng(args.seed)
    ber_uncoded = []
    ber_coded = []

    for eb, snr in zip(ebno_db, coded_snr_db):
        info_bits = rng.integers(0, 2, args.num_info_bits).astype(np.uint8)

        # --- uncoded ---
        tx_u = bpsk_modulate(info_bits, samples_per_symbol=1)
        rx_u = awgn_ebno(tx_u, eb, bits_per_symbol=1, seed=int(eb) + 1000)
        rx_u_bits = bpsk_demodulate(rx_u, samples_per_symbol=1)
        ber_uncoded.append(bit_error_rate(info_bits, rx_u_bits[: info_bits.size]))

        # --- coded ---
        coded_bits = hamming74_encode(info_bits)
        tx_c = bpsk_modulate(coded_bits, samples_per_symbol=1)
        rx_c = awgn(tx_c, snr, seed=int(eb) + 2000)
        rx_c_bits = bpsk_demodulate(rx_c, samples_per_symbol=1)
        dec_bits = hamming74_decode(rx_c_bits)
        ber_coded.append(bit_error_rate(info_bits[: dec_bits.size], dec_bits))

    ber_uncoded = np.array(ber_uncoded)
    ber_coded = np.array(ber_coded)

    ebno_uncoded_1e3 = interp_ebno_at_ber(ebno_db, ber_uncoded, 1e-3)
    ebno_coded_1e3 = interp_ebno_at_ber(ebno_db, ber_coded, 1e-3)
    coding_gain = ebno_uncoded_1e3 - ebno_coded_1e3 if np.isfinite(ebno_coded_1e3) else float("nan")

    out = report_dir("13_hamming74")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(ebno_db, ber_uncoded, "o-", label="uncoded BPSK", markersize=4)
    ax.semilogy(ebno_db, ber_coded, "s-", label="(7,4) Hamming", markersize=4)
    ax.set_xlabel("Information Eb/N0 (dB)")
    ax.set_ylabel("BER")
    ax.set_title("Uncoded vs (7,4) Hamming-coded BPSK")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    curve_path = out / "ber_curve.png"
    fig.savefig(curve_path, dpi=120)
    plt.close(fig)

    ok = ber_coded[-1] <= ber_uncoded[-1]  # coded should help at high Eb/N0
    report = {
        "status": "pass" if ok else "fail",
        "code_rate": rate,
        "ebno_db": ebno_db.tolist(),
        "ber_uncoded": ber_uncoded.tolist(),
        "ber_coded": ber_coded.tolist(),
        "ebno_uncoded_at_1e3": ebno_uncoded_1e3,
        "ebno_coded_at_1e3": ebno_coded_1e3,
        "coding_gain_db": coding_gain,
        "num_info_bits": args.num_info_bits,
        "plots": {"ber_curve": str(curve_path.relative_to(out.parents[2]))},
    }
    write_report(out, report)
    print(f"status={report['status']}")
    for eb, b_u, b_c in zip(ebno_db, ber_uncoded, ber_coded):
        print(f"  Eb/N0={eb:4.0f} dB  uncoded={b_u:.4e}  coded={b_c:.4e}")
    print(f"  Eb/N0 @ BER=1e-3: uncoded={ebno_uncoded_1e3:.2f} dB, coded={ebno_coded_1e3:.2f} dB")
    print(f"  coding gain = {coding_gain:.2f} dB")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
