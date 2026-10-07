# Agentic HIL rules for rad-lab

This repository uses a **host-gated, staged** bring-up. Agents must treat `reports/<board>/stage.json` as the source of truth for hardware progress.

## Allowed actions

1. Read board YAML under `boards/` and docs under `docs/`.
2. Run software checks: `make check`, `make sim BOARD=hackrf`, labs that do not TX.
3. Run `make stage BOARD=hackrf STAGE=present|workflow` when USB hardware may be attached.
4. Run `make hil` / `STAGE=image` **only** when `HIL_LOOPBACK=1` is set and the operator has confirmed an attenuator cable from TX to RX.
5. Use `RAD_LAB_HIL_SIM=1` for image-stage dry runs in CI or when no RF hardware is present (still requires `HIL_LOOPBACK=1`).
6. Run `make firmware BOARD=hackrf` **only** when `HIL_FIRMWARE=1` is set and the operator has confirmed the correct HackRF One is on USB.

## Forbidden

- Setting `HIL_LOOPBACK=1` without an attenuator/cable path (do not invent operator assent).
- Setting `HIL_FIRMWARE=1` without operator confirmation of the DUT identity.
- Entering DFU or running `dfu-util` unless `hackrf_spiflash` has already failed.
- Raising `txvga_db` above `max_tx_db` in board YAML for a “stronger” signal.
- Antenna TX, outdoor TX, or amplifier-enabled TX from default stages.
- Skipping stage order (`present` → `workflow` → `image`) or running Pluto before HackRF `image` passes.
- Ignoring `status: fail` reasons in `stage.json`; fix the cause and re-run the same stage.

## How to repair from HIL failures

1. Open `reports/<board>/stage.json` and the `report_dir` from the failed image stage.
2. Read `fixture.json`, `hil.jsonl`, and `junit.xml`.
3. Common causes: missing USB permissions, no attenuator (low SNR), wrong driver, gain too low/high, `HIL_LOOPBACK` unset.
4. Re-run only the failed stage after the fix.

## Make cheatsheet

```bash
make check
make archive && make image
HIL_FIRMWARE=1 make firmware BOARD=hackrf                # SPI flash; then RESET
make firmware BOARD=hackrf                               # verify 2026.01.3
make stage BOARD=hackrf STAGE=present
make stage BOARD=hackrf STAGE=workflow
HIL_LOOPBACK=1 RAD_LAB_HIL_SIM=1 make hil BOARD=hackrf   # no RF
HIL_LOOPBACK=1 make hil BOARD=hackrf                     # real loopback
```

## Container

`make image` builds `rad-lab-sdr` with HackRF host tools from release **2026.01.3**. Prefer those tools for firmware work. Mount USB with `--privileged -v /dev/bus/usb:/dev/bus/usb` when probing or flashing from the container.
