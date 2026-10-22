# 07 — Digital Up/Down Conversion (DUC/DDC)

Complex baseband \\(x[n] = I[n] + jQ[n]\\) is shifted to an offset carrier by **digital upconversion**:

\\[
y[n] = x[n] e^{j 2\\pi f_{\\text{offset}} n / f_s}
\\]

and returned to baseband by **digital downconversion**:

\\[
z[n] = y[n] e^{-j 2\\pi f_{\\text{offset}} n / f_s} \\approx x[n].
\\]

This is the software equivalent of an IQ modulator/demodulator front end (Module 1 Activity 1.3).

## Lab

```bash
.venv/bin/python lesson/labs/07_duc_ddc_iq.py
```

Writes under `reports/lesson/07_duc_ddc/`:

| Plot | What to notice |
|------|----------------|
| `time.png` | Baseband I/Q vs roundtrip I/Q (overlap) |
| `spectrum_baseband.png` | Tone at `tone_hz` |
| `spectrum_upconverted.png` | Tone moved to `offset_hz + tone_hz` |

Pass when the DUC/DDC roundtrip error is below \\(10^{-3}\\).

## Next

[08 — AWGN vs Eb/N0](08-awgn-ebno.md)
