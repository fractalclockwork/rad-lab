# 13 — (7,4) Hamming Code & Coding Gain

Implements a **(7, 4) Hamming** block encoder and syndrome decoder with single-error correction (Module 5 Activity 5.2).

Code rate \\(r = 4/7\\). For a fair comparison at the same information-bit \\(E_b/N_0\\), coded BPSK symbols run at symbol SNR \\(= (E_b/N_0)\\cdot r\\) (i.e. \\(10\\log_{10}(4/7) \\approx -2.4\\) dB). The Hamming code must overcome this rate penalty before showing net coding gain, which appears at lower BER.

## Lab

```bash
.venv/bin/python learn/labs/13_hamming74.py --ebno-min 0 --ebno-max 12 --num-info-bits 200000
```

Writes under `reports/learn/13_hamming74/`:

| Plot | What to notice |
|------|----------------|
| `ber_curve.png` | Uncoded vs coded BER vs information Eb/N0; coded wins at higher Eb/N0 |
| report.json | `coding_gain_db` at BER = \\(10^{-3}\\) |

Pass when coded BER is at or below uncoded at the top of the sweep.

## Curriculum complete

Software-first lessons are done. Conducted RF TX/RX (Pluto loopback BER sweeps, hardware noise floor) remains under [`hil/`](../../hil/README.md).
