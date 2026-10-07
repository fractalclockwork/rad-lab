# ADALM-PLUTO

Analog Devices ADALM-PLUTO (PlutoSDR). USB VID:PID typically `0456:b673`. SoapySDR driver `plutosdr`. IIO probe via `iio_info` / `iio_attr`.

Lessons: [Baofeng simplex HIL](../learn/04-baofeng-simplex-hil.md) (known TX), [Pluto 2 m RX](../learn/05-pluto-2m-rx.md).

## Specification

| Item | Value |
| --- | --- |
| Part | ADALM-PLUTO |
| Tuning | ~70 MHz to 6 GHz (firmware dependent) |
| USB | `0456:b673` |
| Probe | IIO (`iio_info -s`) then Soapy `driver=plutosdr` |
| Firmware target | **v0.39** (`pluto.frm` from ADI `plutosdr-fw`) |
| Lab DUT serial | `1044734c96050013eaff200049464f471d` |
| Gate | Requires HackRF `image` stage `pass` |
| TX safety | Attenuated SMA cable TX→RX only; `HIL_LOOPBACK=1` |

### Bring-up status (handoff)

Tooling for Pluto firmware / stages / 2 m RX lab is in-tree. On the last host the DUT still reported **v0.38** after a mass-storage copy; prefer **USB + external power**, copy `pluto.frm`, **software-eject only** (do not `udisksctl power-off`), wait for the blue LED, then `make firmware BOARD=pluto`. Resume: firmware verify → `present` → `workflow` → [2 m RX](../learn/05-pluto-2m-rx.md) → `HIL_LOOPBACK=1 make hil BOARD=pluto`.

## Firmware flash (USB mass-storage)

Host tools: `libiio-utils` / `dfu-util` in `rad-lab-sdr`. Preferred update: copy `pluto.frm` to the PlutoSDR volume and **software-eject** (ADI procedure). Do not unplug while the blue LED flashes.

```bash
make archive          # fetches plutosdr-fw-v0.39.zip → pluto.frm
make image            # rebuilds rad-lab-sdr (IIO + SoapyPlutoSDR)
# Record only (safe):
make firmware BOARD=pluto
# Operator asserts the correct Pluto is on USB:
export HIL_FIRMWARE=1
make firmware BOARD=pluto
# Wait for LED / remount, then verify:
make firmware BOARD=pluto
# or: .venv/bin/python scripts/firmware.py --board pluto --verify-only
```

| Item | Value |
| --- | --- |
| Release archive id | `plutosdr-fw-v0.39` |
| Mass-storage image | `archive/cache/sdk/plutosdr-fw-v0.39/pluto.frm` |
| DFU image | `archive/cache/sdk/plutosdr-fw-v0.39/pluto.dfu` |
| Arming env | `HIL_FIRMWARE=1` |
| Optional serial | `PLUTO_SERIAL` or `expected_serial` in YAML |
| Reports | `reports/pluto/<timestamp>/firmware_*.json` |

### DFU recovery (only if mass-storage flash fails)

1. Put Pluto into DFU mode (ADI: hold button while plugging USB — see vendor firmware guide).
2. `HIL_FIRMWARE=1 .venv/bin/python scripts/firmware.py --board pluto --dfu`
3. Wait for reboot; `make firmware BOARD=pluto` to verify `v0.39`.

Official reference: [Updating the Firmware](https://analogdevicesinc.github.io/documentation/solutions/platforms/pluto/get-started/firmware.html).

## Bring-up defaults

From `boards/pluto.yaml`:

| Parameter | Value | Note |
| --- | --- | --- |
| `firmware_target` | v0.39 | Mass-storage / DFU goal |
| `center_hz` | 915e6 | Cable loopback only |
| `tone_offset_hz` | 100e3 | Baseband offset for CW |
| `txvga_db` | -10 | Clamped by `max_tx_db` |
| `max_tx_db` | -5 | Hard ceiling |
| `max_tx_ms` | 200 | Burst limit |
| `min_snr_db` | 10 | Pass threshold |

## Stages

Stages refuse to run until `reports/hackrf/stage.json` shows `image` as `pass`. Loopback rules match HackRF: attenuator cable, `HIL_LOOPBACK=1`.

```bash
make stage BOARD=pluto STAGE=present
make stage BOARD=pluto STAGE=workflow
# 2 m RX lab (Baofeng known TX) — see docs/learn/05-pluto-2m-rx.md
export HIL_LOOPBACK=1
make hil BOARD=pluto
```

## Attenuator wiring (image stage)

1. Connect Pluto **TX** to an attenuator (≥30 dB recommended for first runs).
2. Connect the attenuator output to Pluto **RX**.
3. Confirm no antenna is attached.
4. Export `HIL_LOOPBACK=1`.
5. Run `present` → `workflow` → `make hil BOARD=pluto`.

## Manuals

- [Pluto user guide](https://wiki.analog.com/university/tools/pluto/users), archive id `pluto-user-guide`
- [Hardware notes](https://wiki.analog.com/university/tools/pluto/hacking/hardware), archive id `pluto-hardware`
- Firmware release: [plutosdr-fw v0.39](https://github.com/analogdevicesinc/plutosdr-fw/releases/tag/v0.39)
