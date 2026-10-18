# Loopback HIL

The image stage is the closed loop for agents and humans:

1. Assert an attenuator path with `HIL_LOOPBACK=1`.
2. Run the DSP fixture (no RF).
3. Transmit a brief CW at `tone_offset_hz` with gain ≤ `max_tx_db` and duration ≤ `max_tx_ms`.
4. Capture RX IQ and require SNR ≥ `min_snr_db`.
5. Write `hil.jsonl` and `junit.xml` under `reports/hackrf/<timestamp>/`.

Without hardware, CI uses `RAD_LAB_HIL_SIM=1` after the same stage gates. Simulated mode still requires the loopback env flag so agents do not skip the operator assertion.

Never automate antenna TX from this repository’s default stages.
