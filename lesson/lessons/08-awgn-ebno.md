# 08 — AWGN vs \\(E_b/N_0\\)

Adds complex AWGN to QPSK symbols calibrated to \\(E_b/N_0\\) rather than raw SNR. Per the spec:

\\[
\\mathrm{SNR} = \\left(\\frac{E_b}{N_0}\\right)\\eta_s, \\qquad \\eta_s = \\log_2 M
\\]

so for QPSK (\\(\\eta_s=2\\)), measured SNR should be \\(E_b/N_0 + 3\\) dB. Verifies the noise-power scaling and plots constellations at each point (Module 2 Activity 2.1).

## Lab

```bash
.venv/bin/python lesson/labs/08_awgn_ebno.py --ebno-db 0 6 12 18
```

Writes under `reports/lesson/08_awgn_ebno/`:

| Plot | What to notice |
|------|----------------|
| `constellation_ebno<N>.png` | QPSK cloud tightens as Eb/N0 rises |
| `spectrum.png` | QPSK transmit spectrum |

Pass when measured SNR is within 2 dB of \\(E_b/N_0 + 3\\) dB.

## Next

[09 — Constellation Impairments](09-impairments.md)
