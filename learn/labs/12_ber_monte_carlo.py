#!/usr/bin/env python3
"""Lesson 12 lab: Monte Carlo BER vs Eb/N0 (Module 5 Activity 5.1).

Transmits BPSK over AWGN across Eb/N0 = 0..12 dB (1 dB steps), compares the
simulated BER against the theoretical Q(sqrt(2 Eb/N0)) curve, and reports
Shannon capacity for context.
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
    awgn_ebno,
    ber_psk_theoretical,
    bit_error_rate,
    bpsk_demodulate,
    bpsk_modulate,
    monte_carlo_ber_bpsk,
    report_dir,
    save_time_plot,
    shannon_capacity,
    write_report,
)


def main(argv=None):
    p = argparse.ArgumentParser(description="Monte Carlo BER (learn/12)")
    p.add_argument("--ebno-min", type=float, default=0.0)
    p.add_argument("--ebno-max", type=float, default=12.0)
    p.add_argument("--num-bits", type=int, default=200000)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    ebno_db = np.arange(args.ebno_min, args.ebno_max + 1.0, 1.0)
    ber_sim, ber_theo = monte_carlo_ber_bpsk(ebno_db, num_bits=args.num_bits, seed=args.seed)

    # Reference: one realization at the highest Eb/N0, time domain
    n_show = min(args.num_bits, 400)
    bits = np.random.default_rng(args.seed).integers(0, 2, n_show).astype(np.uint8)
    tx = bpsk_modulate(bits, samples_per_symbol=1)
    rx = awgn_ebno(tx, args.ebno_max, bits_per_symbol=1, seed=args.seed)
    rx_bits = bpsk_demodulate(rx, samples_per_symbol=1)
    t = np.arange(n_show)
    ber_last = bit_error_rate(bits, rx_bits)

    out = report_dir("12_ber_monte_carlo")

    # BER curve figure
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(ebno_db, ber_sim, "o-", label="simulated", markersize=4)
    ax.semilogy(ebno_db, ber_theo, "-", label="theoretical", linewidth=1.5)
    ax.set_xlabel("Eb/N0 (dB)")
    ax.set_ylabel("BER")
    ax.set_title("BPSK BER vs Eb/N0 (AWGN)")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    ber_path = out / "ber_curve.png"
    fig.savefig(ber_path, dpi=120)
    plt.close(fig)

    # Time-domain snapshot figure
    fig2, ax2 = plt.subplots(figsize=(6, 2.5))
    ax2.plot(t[: n_show // 4], tx[: n_show // 4], drawstyle="steps-post", label="tx")
    ax2.plot(t[: n_show // 4], rx[: n_show // 4], alpha=0.6, label="rx (noisy)")
    ax2.set_xlabel("Sample")
    ax2.set_ylabel("Amplitude")
    ax2.set_title(f"BPSK @ {args.ebno_max} dB Eb/N0")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    fig2.tight_layout()
    snap_path = out / "snapshot.png"
    fig2.savefig(snap_path, dpi=120)
    plt.close(fig2)

    capacity = shannon_capacity(1.0e6, 10.0 ** (args.ebno_max / 10.0))
    ok = bool(np.all(ber_sim <= ber_theo * 1.5 + 1.0 / args.num_bits))
    report = {
        "status": "pass" if ok else "fail",
        "ebno_db": ebno_db.tolist(),
        "ber_simulated": ber_sim.tolist(),
        "ber_theoretical": ber_theo.tolist(),
        "num_bits": args.num_bits,
        "ber_last_snapshot": float(ber_last),
        "shannon_capacity_bps": float(capacity),
        "plots": {
            "ber_curve": str(ber_path.relative_to(out.parents[2])),
            "snapshot": str(snap_path.relative_to(out.parents[2])),
        },
    }
    write_report(out, report)
    print(f"status={report['status']}")
    for eb, s, th in zip(ebno_db, ber_sim, ber_theo):
        print(f"  Eb/N0={eb:4.0f} dB  sim={s:.4e}  theory={th:.4e}")
    print(f"  Shannon C(1 MHz, {args.ebno_max} dB)={capacity:,.0f} bps")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
