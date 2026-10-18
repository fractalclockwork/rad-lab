# 06 — Windowing & Spectral Analysis

A tone at offset \\(f_0\\) sampled at \\(f_s\\) has a line spectrum, but observing it over a finite window convolves the true spectrum with the window's Fourier transform — producing **spectral leakage** and widening the mainlobe.

| Window | Mainlobe | Peak sidelobe | Best for |
|--------|----------|---------------|----------|
| Rectangular | narrowest | high (~-13 dB) | max frequency resolution |
| Hann | wider | low (~-31 dB) | general purpose |
| Blackman | widest | very low (~-58 dB) | dynamic range |

## Lab

```bash
.venv/bin/python learn/labs/06_windowing_spectral.py
```

Writes under `reports/learn/06_windowing/`:

| Plot | What to notice |
|------|----------------|
| `spectra.png` | All three windows overlaid; Hann/Blackman suppress sidelobes at the cost of mainlobe width |

Pass when the tone peak is within a few FFT bins of `tone_hz` for all windows.

## Next

[07 — Digital Up/Down Conversion](07-duc-ddc.md)
