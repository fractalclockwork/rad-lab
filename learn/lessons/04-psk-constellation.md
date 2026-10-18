# 04 — Digital PSK

**BPSK** maps bits to \(\{+1,-1\}\). **QPSK** maps Gray dibits onto four phase points on the unit circle (normalized).

AWGN clouds the constellation; hard decisions pick the nearest ideal point. Bit error rate (BER) falls quickly as SNR rises.

## Lab

```bash
.venv/bin/python learn/labs/04_psk_constellation.py
# optional:
.venv/bin/python learn/labs/04_psk_constellation.py --snr-db 8 --text HELLO
```

| Plot | What to notice |
| --- | --- |
| `bpsk_constellation.png` | Two clusters on the I axis |
| `qpsk_constellation.png` | Four Gray-labeled clouds |
| `qpsk_spectrum.png` | Pulse-shaped (rectangular) spectrum |

Default SNR is 12 dB. Pass when BPSK and QPSK BER are both below \(10^{-3}\).

## Next

[05 — Digital 16-QAM](05-qam-constellation.md)
