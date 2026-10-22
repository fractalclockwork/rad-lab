# Bring-up labs

Hands-on scripts for HWIL bring-up. Run from the **repo root**. Lab `01` is software-only. Labs `02`–`07` require that board’s `image` stage to have passed (`ready.require_rf`). RF-transmitting labs also require `HUMAN_LOOPBACK=1` and TX confirmation.

| Lab | Path | Hardware |
| --- | --- | --- |
| Tone SNR fixture | [01_tone_snr.py](01_tone_snr.py) | None (no stage gate) |
| Soapy probe | [02_soapy_probe.py](02_soapy_probe.py) | HackRF preferred |
| RX capture | [03_rx_capture.py](03_rx_capture.py) | HackRF |
| TX callsign FM | [04_tx_callsign_fm.py](04_tx_callsign_fm.py) | HackRF (+ licensed op); dry-run skips RF gate |
| Pluto 2 m RX | [05_pluto_rx_capture.py](05_pluto_rx_capture.py) | Pluto (+ Baofeng known TX). Prompts for key-up and passes on carrier detection. |
| Pluto 2 m TX callsign FM | [06_pluto_tx_callsign_fm.py](06_pluto_tx_callsign_fm.py) | Pluto (+ attenuator, licensed op) |
| Cross-board 915 CW | [07_crossboard_915_cw.py](07_crossboard_915_cw.py) | HackRF + Pluto (+ attenuator). `HUMAN_LOOPBACK=1`; both directed legs must pass. |

## Callsign

On-air ID labs do **not** hardcode a station callsign. Set yours explicitly:

```bash
export RAD_LAB_CALLSIGN=YOURCALL
# or:
python3 hardware/labs/04_tx_callsign_fm.py --callsign YOURCALL --freq 446500000 --deviation 2500 --txvga 0
# Pluto 2 m wide FM, conducted TX only (refuses without HUMAN_LOOPBACK=1):
HUMAN_LOOPBACK=1 python3 hardware/labs/06_pluto_tx_callsign_fm.py --callsign YOURCALL
# HackRF↔Pluto 915 MHz CW simplex (attenuated cable; two rewire prompts):
HUMAN_LOOPBACK=1 python3 hardware/labs/07_crossboard_915_cw.py
```

Optional local file: copy [`local.env.example`](../../local.env.example) to `local.env` (gitignored) and `set -a; source local.env; set +a`.

```bash
# inside venv or container, from repo root
python3 hardware/labs/01_tone_snr.py
python3 hardware/labs/02_soapy_probe.py
```
