# Pluto 2 m RX (Baofeng known TX)

After Pluto `present` (and preferably firmware **v0.39**), use the UV-5R+PLUS as a known FM transmitter on **146.550 MHz** while the Pluto only receives. This does **not** write `stage.json` and does not replace the 915 MHz attenuated loopback `image` stage.

Safety rules match [Baofeng simplex HIL](04-baofeng-simplex-hil.md): conducted/pad preferred, no antenna TX from the Pluto, stay off 146.520 calling.

## Setup

1. Pluto on USB; `make stage BOARD=pluto STAGE=present` has passed.
2. Baofeng on **146.550**, WN = **WIDE**, **low** TX power, pad or very short path toward the Pluto RX SMA (not an open antenna for bench work if you can avoid it).
3. From the repo root:

```bash
# Unkeyed noise floor
.venv/bin/python labs/05_pluto_rx_capture.py --freq 146550000 --tag 2m_unkeyed

# Key the Baofeng, then:
.venv/bin/python labs/05_pluto_rx_capture.py --freq 146550000 --tag 2m_keyed
```

Reports land in `reports/pluto/uv5r/rx_*_report.json` plus a short `.c64` IQ snippet.

## Pass criterion

- Unkeyed: no strong carrier near DC offset (noise-like spectrum).
- Keyed: clear peak; `spectrum_peak_over_noise_db` well above the unkeyed capture (tens of dB typical with a pad).

Record the two report paths and peak-over-noise numbers in the lab notebook / commit message when bring-up is documented.

## Next

Attenuated Pluto TX↔RX loopback: `HIL_LOOPBACK=1 make hil BOARD=pluto` (915 MHz CW per `boards/pluto.yaml`).
