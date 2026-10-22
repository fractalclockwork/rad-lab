# Pluto 2 m RX (Baofeng known TX)

After Pluto `present` (and preferably firmware **v0.39**), use the UV-5R+PLUS as a known FM transmitter on **146.550 MHz** while the Pluto only receives. This does **not** write `stage.json` and does not replace the 915 MHz attenuated loopback `image` stage.

Safety rules match [Baofeng simplex HWIL](baofeng-simplex.md): conducted/pad preferred, no antenna TX from the Pluto, stay off 146.520 calling.

## Setup

1. Pluto on USB; `make stage BOARD=pluto STAGE=present` has passed.
2. Baofeng on **146.550**, WN = **WIDE**, **low** TX power, pad or very short path toward the Pluto RX SMA (not an open antenna for bench work if you can avoid it).
3. From the repo root, with the Baofeng still unkeyed:

```bash
.venv/bin/python hardware/labs/05_pluto_rx_capture.py --freq 146550000
```

The script tunes the Pluto and discards a short warmup. It tells you to leave the transmitter unkeyed, measures that floor, then prints:

```text
Receiver ready on 146.550 MHz. Key the transmitter and hold PTT, then press Enter.
```

Key the Baofeng and hold PTT through the capture (default 2 s), then press Enter.

One report lands in `reports/pluto/uv5r/rx_2m_wide_report.json`, with short unkeyed and keyed `.c64` snippets beside it.

## Pass criterion

Pass means `status` is `pass` and the process exits 0. That requires both captures to complete and `carrier_detected` to be true.

`carrier_rise_db` is keyed in-band power minus the unkeyed floor. In-band power is the mean power inside ±15 kHz (`--window-hz`). The default pass line is 10 dB (`--min-carrier-db`). A conducted pad is often well above that. A DC spur that is already in the unkeyed floor does not pass on its own, because the check is the rise, not the absolute peak.

Record the report path and `carrier_rise_db` in the lab notebook / commit message when bring-up is documented.

## Next

Conducted Pluto TX on the same 146.550 MHz channel, after this RX lab: [`hardware/labs/06_pluto_tx_callsign_fm.py`](../../labs/06_pluto_tx_callsign_fm.py). Pluto **TX** SMA into an attenuator and a 50 Ω load (or into HackRF RX through the pad). No antenna. Set `HUMAN_LOOPBACK=1` and pass `--callsign` or `RAD_LAB_CALLSIGN`.

Then the directed HackRF↔Pluto CW exchange on 915 MHz: [cross-board 915 CW](crossboard-915-cw.md). Same-board Pluto cable loopback remains a later stage and does not replace either lab: `HUMAN_LOOPBACK=1 make hwil BOARD=pluto`.
