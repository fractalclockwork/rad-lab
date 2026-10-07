# HackRF bring-up

Order of evidence:

1. **present** — USB `1d50:6089` and `hackrf_info` (or Soapy probe) see the board.
2. **workflow** — the host can open the device; TX limits from YAML are recorded; `HIL_LOOPBACK` state is noted.
3. **image** — software fixture passes, then a short TX↔RX loopback tone must clear `min_snr_db`.

Commands:

```bash
make stage BOARD=hackrf STAGE=present
make stage BOARD=hackrf STAGE=workflow
export HIL_LOOPBACK=1
make hil BOARD=hackrf
```

Wiring is on the [HackRF board page](../boards/hackrf.md). Archive ids: `hackrf-one-docs-index`, `hackrf-hardware-overview`.
