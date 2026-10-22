# HackRF↔Pluto 915 MHz CW simplex

After each board’s own RX/TX path is trusted (HackRF loopback HWIL, Pluto 2 m RX/TX), run a **directed** CW exchange between them on the shared ISM cable-loopback center. This does **not** write `stage.json` and does not replace same-board `HUMAN_LOOPBACK=1 make hwil`.

## Safety

- **915 MHz cable only.** Use an attenuator (≥30 dB for first runs). No antenna on either board.
- Set `HUMAN_LOOPBACK=1` before the lab. The script refuses TX without it.
- Gains stay at board YAML defaults and under each board’s `max_tx_db` (HackRF ≤ 4 dB, Pluto ≤ −5 dB).
- Modulation is a short complex **CW tone** at 100 kHz baseband offset (RF ≈ 915.1 MHz), the same vector as [`hardware/loopback.py`](../../loopback.py).

## Wiring (two legs)

Simplex: one transmitter at a time. Rewire between legs.

1. **HackRF TX → pad → Pluto RX.** Confirm both USB devices are present.
2. Run the lab; at the first prompt, press Enter.
3. **Rewire: Pluto TX → pad → HackRF RX.** Press Enter at the second prompt.

## Command

```bash
HUMAN_LOOPBACK=1 .venv/bin/python hardware/labs/07_crossboard_915_cw.py
```

The host process prompts and writes the report. Each RF leg runs inside `rad-lab-sdr` with USB mounted (SoapySDR).

`--no-prompt` skips the Enter waits for scripted reruns when the cable is already correct for the next leg.

## Pass criterion

Both legs must pass:

| Check | Requirement |
| --- | --- |
| SNR | `snr_db` ≥ `min_snr_db` (7.0 dB from board YAML) |
| Peak | Spectrum peak within ±10 kHz of `tone_offset_hz` (100 kHz) |

One report: `reports/crossboard/915_cw_report.json` with per-leg metrics and serials.

## Next

Same-board Pluto image stage (915 MHz TX↔RX on the Pluto alone), when HackRF `image` is already `pass`:

```bash
HUMAN_LOOPBACK=1 make hwil BOARD=pluto
```
