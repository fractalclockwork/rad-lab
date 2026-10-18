# 03 — Analog FM

Complex baseband FM (same construction as the HIL callsign TX helper, without RF):

\[
x[n] = A\exp\!\Big(j\sum_k 2\pi\,\Delta f\,a[k]/f_s\Big)
\]

Demodulation takes the unwrapped phase difference (instantaneous frequency).

## Lab

```bash
.venv/bin/python learn/labs/03_fm_mod_demod.py
```

| Plot | What to notice |
| --- | --- |
| `time.png` | Message vs normalized demod frequency |
| `spectrum.png` | Bessel sidebands for large deviation |
| `iq_trajectory.png` | Constant-envelope circle in the IQ plane |

Pass when demod↔message correlation is above ~0.9.

## Next

[04 — Digital PSK](04-psk-constellation.md)
