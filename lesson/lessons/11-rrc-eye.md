# 11 — RRC Pulse Shaping, Eye Diagrams & Matched Filter

Symbols are upsampled by zero-insertion then filtered with a **Root-Raised Cosine** (RRC) pulse. TX and RX each use RRC, so the cascade is Raised Cosine (zero ISI at symbol centers, Module 4).

| Activity | What to notice |
|----------|----------------|
| 4.1 Pulse shaping | RRC spectrum suppresses out-of-band sidelobes vs rectangular |
| 4.2 Eye diagram | For \\(\\alpha=0.1,0.35,0.75\\): smaller \\(\\alpha\\) = narrower bandwidth but tighter timing tolerance |
| 4.3 Matched filter | SNR after Rx RRC exceeds SNR before by \\(\\approx 10\\log_{10}\\text{sps}\\) dB (processing gain) |

## Lab

```bash
.venv/bin/python lesson/labs/11_rrc_eye_diagram.py --modulation qpsk --sps 8 --snr-db 15
```

Writes under `reports/lesson/11_rrc_eye/`:

| Plot | What to notice |
|------|----------------|
| `spectrum_rectangular.png` | Rectangular spectrum (high sidelobes) |
| `spectrum_rrc.png` | RRC spectrum (suppressed sidelobes) |
| `eye_alphaNN.png` | Eye opening vs roll-off |
| report.json | `snr_gain_db` (matched-filter processing gain) |

Pass when SNR after filtering is >= SNR before and BER < \\(10^{-2}\\).

## Next

[12 — Monte Carlo BER vs \\(E_b/N_0\\)](12-ber-monte-carlo.md)
