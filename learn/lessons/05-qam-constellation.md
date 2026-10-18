# 05 — Digital 16-QAM

Sixteen amplitude/phase points on a square grid (Gray-labeled I and Q). Same AWGN model as the PSK lab; symbol error rate (SER) and BER both reported.

16-QAM needs more SNR than QPSK for the same BER because points are closer together.

## Lab

```bash
.venv/bin/python learn/labs/05_qam_constellation.py
# try a noisier channel:
.venv/bin/python learn/labs/05_qam_constellation.py --snr-db 12
```

| Plot | What to notice |
| --- | --- |
| `constellation.png` | 4×4 grid with noise clouds; ideal marks as × |
| `spectrum.png` | Rectangular pulse spectrum |

Default SNR is 18 dB. Pass when BER and SER are both below \(10^{-3}\).

## Curriculum complete

Return to [lessons index](README.md). Conducted RF TX/RX remains under [`hil/`](../../hil/README.md), not these software labs.
