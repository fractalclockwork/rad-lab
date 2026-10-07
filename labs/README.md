# Labs

Hands-on exercises for the containerized SDR environment. Run after HackRF `present` at minimum; RF-transmitting labs require a passed workflow stage and `HIL_LOOPBACK=1`.

| Lab | Path | Hardware |
| --- | --- | --- |
| Tone SNR fixture | [01_tone_snr.py](01_tone_snr.py) | None |
| Soapy probe | [02_soapy_probe.py](02_soapy_probe.py) | HackRF preferred |
| RX capture | [03_rx_capture.py](03_rx_capture.py) | HackRF |
| TX callsign FM | [04_tx_callsign_fm.py](04_tx_callsign_fm.py) | HackRF (+ licensed op) |
| Pluto 2 m RX | [05_pluto_rx_capture.py](05_pluto_rx_capture.py) | Pluto (+ Baofeng known TX) |

## Callsign

On-air ID labs do **not** hardcode a station callsign. Set yours explicitly:

```bash
export RAD_LAB_CALLSIGN=YOURCALL
# or:
python3 labs/04_tx_callsign_fm.py --callsign YOURCALL --freq 446500000 --deviation 2500 --txvga 0
```

Optional local file: copy [`local.env.example`](../local.env.example) to `local.env` (gitignored) and `set -a; source local.env; set +a`.

```bash
# inside venv or container, from repo root
python3 labs/01_tone_snr.py
python3 labs/02_soapy_probe.py
```
