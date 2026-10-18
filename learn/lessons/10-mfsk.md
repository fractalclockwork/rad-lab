# 10 — M-FSK Modulate / Non-Coherent Demodulate

**M-FSK** assigns one orthogonal tone per \\(\\log_2 M\\)-bit symbol. Because the receiver may not know the carrier phase, demodulation uses an **envelope-detector filter bank**: correlate each symbol interval with every tone reference and pick the largest magnitude (Module 3 Activity 3.2).

Tone spacing \\(1/T_{\\text{sym}}\\) keeps the tones orthogonal over a symbol interval.

## Lab

```bash
.venv/bin/python learn/labs/10_mfsk.py --tones 10000 22500 35000 47500 --ebno-db 10
```

Writes under `reports/learn/10_mfsk/`:

| Plot | What to notice |
|------|----------------|
| `spectrum.png` | Distinct tone peaks at each FSK frequency |

Pass when BER is below \\(10^{-2}\\).

## Next

[11 — RRC Pulse Shaping & Eye Diagrams](11-rrc-eye.md)
