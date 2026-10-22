# Human-in-the-loop

Operator assent before hardware automation keys RF or flashes firmware.

| Flag | Meaning |
| --- | --- |
| `HUMAN_LOOPBACK=1` | Attenuator cable TX→RX is connected (no antenna) |
| `HUMAN_TX_CONFIRM=1` | Scripted YES for TX |
| `HUMAN_FIRMWARE=1` | Correct DUT identity confirmed before flash |
| `RAD_LAB_CALLSIGN` | Station callsign for on-air ID labs |

API: [`assent.py`](assent.py) — `require_hardware`, `require_loopback`, `require_firmware`, `confirm_tx`, `require_tx`, `clamp_tx_gain`, `resolve_callsign`, `sanitize_callsign`.
