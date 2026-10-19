# Agentic HIL rules for rad-lab

This tree is **Workflow A — HIL bring-up**. Agents must treat `reports/<board>/stage.json` as the source of truth for staged hardware progress. Tutorial work belongs under [`learn/`](../learn/) only after this checklist is green.

## Allowed actions

1. Read board YAML under `hil/boards/` and docs under `hil/docs/`.
2. Run software checks: `make check`, `make sim BOARD=hackrf`, bring-up labs under `hil/labs/` that do not TX.
3. Run `make stage BOARD=hackrf STAGE=present|workflow` **only** when the board is visible on host USB (`lsusb` shows its VID:PID). `STAGE=present` is the diagnostic for "is it plugged in?" and needs no confirmation.
4. Run `make hil` / `STAGE=image` **only** when `HIL_LOOPBACK=1` is set and the operator has confirmed an attenuator cable from TX to RX, **and** the board is on USB. Non-simulated image stages additionally require interactive `YES` confirmation (or `HIL_TX_CONFIRM=1`) because they key the transmitter.
5. Use `RAD_LAB_HIL_SIM=1` for image-stage dry runs in CI or when no RF hardware is present (still requires `HIL_LOOPBACK=1`; hardware presence is not required for sim).
6. Run `make firmware BOARD=hackrf` **only** when `HIL_FIRMWARE=1` is set and the operator has confirmed the correct HackRF One is on USB.
7. Run `make firmware BOARD=pluto` **only** when `HIL_FIRMWARE=1` is set and the operator has confirmed the correct ADALM-PLUTO is on USB (mass-storage `pluto.frm`; DFU only after that fails).
8. Run bring-up labs under `hil/labs/` (2 m RX/TX, crossboard CW) with the same loopback / pad rules documented in `hil/docs/bringup/`. Any lab that keys the transmitter requires interactive `YES` confirmation or `HIL_TX_CONFIRM=1` **in addition** to `HIL_LOOPBACK=1`.

## Forbidden
- Running any hardware stage (`workflow`, `image`, `firmware`, `sdr_run --usb …`) when the board's VID:PID is absent from host `lsusb`. The dev-host refuses before touching docker.
- Keying any transmitter (loopback, crossboard, callsign FM, `hackrf_transfer`) without operator confirmation: type `YES` at the interactive prompt, or export `HIL_TX_CONFIRM=1` for scripted/CI runs. `--no-prompt` skips cable-rewire prompts only, never TX confirmation.
- Setting `HIL_LOOPBACK=1` without an attenuator/cable path (do not invent operator assent).
- Setting `HIL_FIRMWARE=1` without operator confirmation of the DUT identity.
- Entering DFU or running `dfu-util` unless `hackrf_spiflash` (HackRF) or Pluto mass-storage flash has already failed.
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
HIL_LOOPBACK=1 RAD_LAB_HIL_SIM=1 make hil BOARD=hackrf   # no RF (sim)
HIL_TX_CONFIRM=1 HIL_LOOPBACK=1 make hil BOARD=hackrf    # real loopback, scripted
HIL_LOOPBACK=1 make hil BOARD=hackrf                     # real loopback, interactive YES
# Pluto (after HackRF image pass):
make firmware BOARD=pluto                                # record / verify v0.39
HIL_FIRMWARE=1 make firmware BOARD=pluto                 # mass-storage pluto.frm
make stage BOARD=pluto STAGE=present
make stage BOARD=pluto STAGE=workflow
HIL_LOOPBACK=1 make hil BOARD=pluto                      # attenuated TX↔RX
```

## Container

`make image` builds `rad-lab-sdr` with HackRF host tools from release **2026.01.3**, libiio utils, and SoapyPlutoSDR. Prefer those tools for firmware work. Mount USB with `--privileged -v /dev/bus/usb:/dev/bus/usb` when probing or flashing from the container.
