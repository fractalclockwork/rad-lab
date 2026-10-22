# 02 — Analog AM

Double-sideband AM with carrier:

\[
s(t) = \bigl(1 + m\,a(t)\bigr)\cos(2\pi f_c t),\quad |a(t)|\le 1,\ 0 < m \le 1
\]

Demodulation here uses a simple **envelope detector** (rectify + moving average), not a coherent mixer.

## Lab

```bash
.venv/bin/python lesson/labs/02_am_mod_demod.py
```

| Plot | What to notice |
| --- | --- |
| `time.png` | Message, RF, and recovered envelope |
| `spectrum.png` | Carrier at \(f_c\) with sidebands at \(\pm f_m\) |
| `iq_baseband.png` | Baseband IQ after mixing the RF down |

Pass when the recovered envelope correlates with the message above ~0.85.

## Next

[03 — Analog FM](03-fm-mod-demod.md)
