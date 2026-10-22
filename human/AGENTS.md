# Human-in-the-loop

Assent only. Agents must **not** invent cable attestation, DUT identity, or TX confirmation.

## Allowed
- Read [`assent.py`](assent.py) and this file.
- Ask the operator to set `HUMAN_LOOPBACK`, `HUMAN_TX_CONFIRM`, `HUMAN_FIRMWARE`, or type `YES`.

## Forbidden
- Exporting `HUMAN_LOOPBACK=1`, `HUMAN_TX_CONFIRM=1`, or `HUMAN_FIRMWARE=1` without real operator assent.
- Typing `YES` on behalf of the operator.
- Importing hardware TX modules from this tree.
