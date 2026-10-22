# 01 — Sampling and IQ

A complex baseband sample is \(I + jQ\). At sample rate \(f_s\), a tone at offset \(f_0\) is:

\[
x[n] = A \exp\!\left(j 2\pi \frac{f_0}{f_s} n\right)
\]

The HackRF HWIL fixture uses \(f_s = 2\,\mathrm{Msps}\) and \(f_0 = 100\,\mathrm{kHz}\) (`hardware/boards/hackrf.yaml`). One period of the tone spans \(f_s / f_0 = 20\) samples.

## Lab

Software-only (no SDR TX). From the repo root:

```bash
.venv/bin/python lesson/labs/01_iq_tone_plots.py
```

Writes under `reports/lesson/01_iq_tone/`:

| Plot | What to notice |
| --- | --- |
| `time.png` | I and Q are a quadrature pair (90° apart) |
| `spectrum.png` | Peak near +100 kHz (not DC) |

Pass when the spectrum peak is within a few bins of `tone_hz`.

## Next

[02 — Analog AM](02-am-mod-demod.md)
