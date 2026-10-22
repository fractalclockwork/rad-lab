# Hardware-in-the-loop (HWIL)

DUT model, staged bring-up, firmware, and RF labs. Call **human** assent before any TX or flash. Use **environment** for container SDR binaries. May call **software** fixture before image TX.

## Allowed
- `make stage`, `make hwil`, `make firmware` when USB presence and assent rules are satisfied.
- `RAD_LAB_HWIL_SIM=1` with `HUMAN_LOOPBACK=1` for simulated image (skips USB and YES).
- RF labs under `labs/` after that board’s `image` stage passes (`harness.ready.require_rf`).

## Forbidden
- TX or flash without human assent.
- Running Pluto stages before HackRF `image` is pass.
- Raising `txvga_db` above `max_tx_db`.
- Antenna TX from default stages.
