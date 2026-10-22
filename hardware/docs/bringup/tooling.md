# Tooling

First bring-up step: reproducible host tools, firmware, and staged probes. Run from the **repo root**.

## Archive and container

```bash
make archive          # manuals + SDK artifacts → archive/cache/
make image            # builds rad-lab-sdr (HackRF 2026.01.3, SoapyPlutoSDR, libiio)
make check            # pytest + software fixture
```

Details: [pipeline](../pipeline.md), [archive](../../../archive/README.md).

## Firmware

Operator must confirm the correct DUT on USB before write.

```bash
export HUMAN_FIRMWARE=1
make firmware BOARD=hackrf   # SPI; RESET; re-run to verify 2026.01.3
make firmware BOARD=pluto    # after HackRF image pass; mass-storage pluto.frm → v0.39
```

Board pages: [HackRF firmware](../boards/hackrf.md), [Pluto firmware](../boards/pluto.md).

## Staged present → workflow → image

```bash
make stage BOARD=hackrf STAGE=present
make stage BOARD=hackrf STAGE=workflow
export HUMAN_LOOPBACK=1
make hwil BOARD=hackrf
```

Pluto stages stay closed until `reports/hackrf/stage.json` shows `image` as `pass`. Same-board image rules: [loopback](loopback.md).

Software-only image dry run (still needs the env flag):

```bash
HUMAN_LOOPBACK=1 RAD_LAB_HWIL_SIM=1 make hwil BOARD=hackrf
```

## Next

Per-DUT RX/TX on 2 m: [baofeng-simplex](baofeng-simplex.md), then [pluto-2m](pluto-2m.md).
