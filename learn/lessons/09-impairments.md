# 09 — Constellation Impairment Diagnosis

Applies, separately and combined, to a clean QPSK constellation:

| Impairment | Visual signature |
|------------|------------------|
| CFO | constellation rotates at rate \\(\\Delta f\\) |
| Phase noise | arc-smearing / blur around each point |
| AWGN | radial spreading (isotropic cloud) |

This matches Module 2 Activity 2.3 and the channel model \\(y[n] = x[n]e^{j(2\\pi\\Delta f n T_s + \\phi_0)} + w[n]\\). Synthetic IQ only; no hardware required.

## Lab

```bash
.venv/bin/python learn/labs/09_constellation_impairments.py --cfo-hz 25000 --phase-noise-rad 0.15 --snr-db 15
```

Writes under `reports/learn/09_impairments/`: one constellation PNG per case (`clean`, `cfo`, `phase_noise`, `awgn`, `combined`).

Pass when CFO, phase noise, and AWGN each raise the RMS error vs the clean case.

## Next

[10 — M-FSK Non-Coherent](10-mfsk.md)
