#!/usr/bin/env python3
"""Lesson 11 lab: RRC pulse shaping, ISI, eye diagrams (Module 4 Activities 4.1-4.3).

- Rectangular vs RRC pulse shaping: observe ISI (symbol smearing) vs zero-ISI.
- Eye diagrams for roll-off alpha = 0.1, 0.35, 0.75.
- Matched-filter SNR: noisy pulse sequence before vs after RRC matched filter.
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
    awgn,
    bit_error_rate,
    bpsk_modulate,
    matched_filter_snr,
    qpsk_constellation,
    qpsk_modulate,
    report_dir,
    rrc_filter,
    save_eye_diagram,
    save_spectrum_plot,
    spectrum_db,
    write_report,
)

from scipy.signal import lfilter  # noqa: E402


def symbols_from_bits(bits, modulation):
    """Map bits to one complex symbol per symbol period (no repetition)."""
    if modulation == "bpsk":
        sym = bpsk_modulate(bits, samples_per_symbol=1)
    else:
        sym = qpsk_modulate(bits, samples_per_symbol=1)
    return sym.astype(np.complex128).ravel()


def upsample_zero_insert(symbols, sps):
    """Insert (sps-1) zeros between consecutive symbols."""
    up = np.zeros(symbols.size * sps, dtype=np.complex128)
    up[::sps] = symbols
    return up


def demod_symbols(rx_sym, modulation):
    """Nearest-neighbor demod of symbol samples back to bits."""
    if modulation == "bpsk":
        return (rx_sym.real < 0).astype(np.uint8)
    ideal = qpsk_constellation()
    d = np.abs(rx_sym.reshape(-1, 1) - ideal.reshape(1, -1))
    mapped = np.argmin(d, axis=1)
    idx_to_bits = {0: (0, 0), 1: (0, 1), 2: (1, 1), 3: (1, 0)}
    return np.array([b for m in mapped for b in idx_to_bits[int(m)]], dtype=np.uint8)


def main(argv=None):
    p = argparse.ArgumentParser(description="RRC / eye diagram (learn/11)")
    p.add_argument("--modulation", default="qpsk", choices=["bpsk", "qpsk"])
    p.add_argument("--sps", type=int, default=8)
    p.add_argument("--num-syms", type=int, default=512)
    p.add_argument("--snr-db", type=float, default=15.0)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    rng = np.random.default_rng(args.seed)
    n_bits = args.num_syms * (2 if args.modulation == "qpsk" else 1)
    bits = rng.integers(0, 2, n_bits).astype(np.uint8)

    symbols = symbols_from_bits(bits, args.modulation)
    tx_up = upsample_zero_insert(symbols, args.sps)

    out = report_dir("11_rrc_eye")

    # Rectangular (repeated symbols, no shaping) spectrum for comparison
    tx_rect = np.repeat(symbols, args.sps)
    freqs_r, psd_r = spectrum_db(tx_rect, 100_000.0)
    spec_r_path = out / "spectrum_rectangular.png"
    save_spectrum_plot(spec_r_path, freqs_r, psd_r, "Rectangular pulse spectrum")

    # RRC pulse-shaped transmit signal (alpha = 0.35)
    alpha = 0.35
    num_taps = 101
    h = rrc_filter(alpha, args.sps, num_taps=num_taps)
    tx_rrc = lfilter(h, [1.0], tx_up)
    freqs_f, psd_f = spectrum_db(tx_rrc, 100_000.0)
    spec_f_path = out / "spectrum_rrc.png"
    save_spectrum_plot(spec_f_path, freqs_f, psd_f, f"RRC (alpha={alpha}) pulse spectrum")

    # Eye diagrams for alpha = 0.1, 0.35, 0.75
    eye_paths = {}
    for a in [0.1, 0.35, 0.75]:
        h_a = rrc_filter(a, args.sps, num_taps=num_taps)
        shaped = lfilter(h_a, [1.0], tx_up)
        eye_path = out / f"eye_alpha{int(a * 100):02d}.png"
        save_eye_diagram(eye_path, shaped, args.sps, span_symbols=2, title=f"Eye diagram alpha={a}")
        eye_paths[f"alpha_{a}"] = str(eye_path.relative_to(out.parents[2]))

    # Matched-filter SNR: Tx RRC + AWGN + Rx RRC vs Tx RRC + AWGN (no Rx filter)
    rx_noisy = awgn(tx_rrc, args.snr_db, seed=args.seed)
    snr_before, snr_after = matched_filter_snr(tx_rrc, rx_noisy, alpha, args.sps, num_taps=num_taps)

    # Decoded BER: Rx matched filter, sample at compensated symbol centers
    rx_matched = lfilter(h, [1.0], rx_noisy)
    delay = num_taps - 1  # total group delay Tx(50) + Rx(50) = num_taps-1 samples
    sample_idx = delay + np.arange(args.num_syms) * args.sps
    sample_idx = sample_idx[sample_idx < rx_matched.size]
    rx_sym = rx_matched[sample_idx.astype(int)]
    rx_bits = demod_symbols(rx_sym, args.modulation)
    ber = bit_error_rate(bits[: rx_bits.size], rx_bits)

    ok = snr_after >= snr_before and ber < 1e-2
    report = {
        "status": "pass" if ok else "fail",
        "modulation": args.modulation,
        "sps": args.sps,
        "snr_db": args.snr_db,
        "snr_before_db": float(snr_before),
        "snr_after_db": float(snr_after),
        "snr_gain_db": float(snr_after - snr_before),
        "ber": float(ber),
        "plots": {
            "spectrum_rectangular": str(spec_r_path.relative_to(out.parents[2])),
            "spectrum_rrc": str(spec_f_path.relative_to(out.parents[2])),
            **eye_paths,
        },
    }
    write_report(out, report)
    print(f"status={report['status']}")
    print(f"  snr_before={snr_before:.1f} dB snr_after={snr_after:.1f} dB gain={snr_after - snr_before:+.1f} dB")
    print(f"  ber={ber:.4e}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
