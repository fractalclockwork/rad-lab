# 12 — Monte Carlo BER vs \\(E_b/N_0\\)

Transmits BPSK over AWGN across \\(E_b/N_0 = 0\\dots12\\) dB (1 dB steps) and compares simulated BER against the theoretical curve:

\\[
P_b = Q\\left(\\sqrt{\\frac{2E_b}{N_0}}\\right) = \\frac{1}{2}\\operatorname{erfc}\\left(\\sqrt{\\frac{E_b}{N_0}}\\right)
\\]

(Module 5 Activity 5.1.) Also reports Shannon capacity \\(C = B\\log_2(1+\\mathrm{SNR})\\) for context.

## Lab

```bash
.venv/bin/python lesson/labs/12_ber_monte_carlo.py --ebno-min 0 --ebno-max 12 --num-bits 200000
```

Writes under `reports/lesson/12_ber_monte_carlo/`:

| Plot | What to notice |
|------|----------------|
| `ber_curve.png` | Simulated markers on the theoretical BER curve |
| `snapshot.png` | One noisy BPSK trace at top Eb/N0 |

Pass when simulated BER tracks theory within tolerance.

## Next

[13 — (7,4) Hamming Coding Gain](13-hamming74.md)
