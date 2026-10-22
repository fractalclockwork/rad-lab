# Loopback HWIL

The image stage is the closed loop for agents and humans:

1. Assert an attenuator path with `HUMAN_LOOPBACK=1`.
2. Run the DSP fixture (no RF).
3. Transmit a brief CW at `tone_offset_hz` with gain ≤ `max_tx_db` and duration ≤ `max_tx_ms`:
   - **Pluto (`BOARD=pluto`)**: full-duplex same-board loopback (`Pluto TX → attenuator → Pluto RX`).
   - **HackRF (`BOARD=hackrf`)**: half-duplex two-leg cross-board loopback to/from Pluto (`HackRF TX → attenuator → Pluto RX`, then `Pluto TX → attenuator → HackRF RX`), gated on Pluto `image` pass.
4. Capture RX IQ and require SNR ≥ `min_snr_db` and peak within ±10 kHz.
5. Write `hil.jsonl` and `junit.xml` under `reports/<board>/<timestamp>/` (and `reports/crossboard/915_cw_report.json` for cross-board).

Without hardware, CI uses `RAD_LAB_HWIL_SIM=1` after the same stage gates. Simulated mode still requires the loopback env flag so agents do not skip the operator assertion.

Never automate antenna TX from this repository’s default stages.
