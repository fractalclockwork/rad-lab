# HackRF One

Wideband half-duplex SDR transceiver from Great Scott Gadgets. USB VID:PID `1d50:6089`. SoapySDR driver `hackrf`.

Bring-up: [hackrf stages](../bringup/hackrf.md), [loopback](../bringup/loopback.md), [baofeng simplex](../bringup/baofeng-simplex.md), [crossboard 915 CW](../bringup/crossboard-915-cw.md). Concepts after HIL: [sampling and IQ](../../../learn/lessons/01-sampling-and-iq.md).

## Specification

| Item | Value |
| --- | --- |
| Part | HackRF One |
| Tuning | ~1 MHz to 6 GHz |
| Sample rate | up to 20 Msps (bring-up uses 2 Msps) |
| USB | `1d50:6089` |
| Probe | `hackrf_info`, Soapy `driver=hackrf` |
| Firmware target | **2026.01.3** (`hackrf_one_usb.bin`) |
| Lab DUT serial | `…a06063c823864f5f` |
| TX safety | Attenuated SMA cable TX→RX only; `HIL_LOOPBACK=1` |

## Firmware flash (SPI)

Host tools in `rad-lab-sdr` are built from the same release as the firmware image. CPLD `hackrf_cpldjtag` is **not** required when the DUT is already on firmware ≥ 2021.03.1.

```bash
make archive          # fetches hackrf-2026.01.3 into archive/cache/sdk/
make image            # rebuilds rad-lab-sdr with 2026.01.3 tools
export HIL_FIRMWARE=1 # operator asserts the correct HackRF is on USB
make firmware BOARD=hackrf
# Press RESET (or unplug/replug), then:
make firmware BOARD=hackrf
# or: .venv/bin/python hil/scripts/firmware.py --board hackrf --verify-only
```

| Item | Value |
| --- | --- |
| Release archive id | `hackrf-2026.01.3` |
| SPI image | `archive/cache/sdk/hackrf-2026.01.3/firmware-bin/hackrf_one_usb.bin` |
| Arming env | `HIL_FIRMWARE=1` |
| Reports | `reports/hackrf/<timestamp>/firmware_*.json` |

### DFU recovery (only if SPI flash fails)

1. Hold **DFU** while pressing **RESET**, then release DFU. `lsusb` should show NXP `1fc9:000c`.
2. Load RAM image:  
   `dfu-util --device 1fc9:000c --alt 0 --download archive/cache/sdk/hackrf-2026.01.3/firmware-bin/hackrf_one_usb.dfu`
3. Run the SPI write path above (`hackrf_spiflash -w …/hackrf_one_usb.bin`).
4. RESET and verify `Firmware Version: 2026.01.3`.

Official reference: [Updating Firmware](https://hackrf.readthedocs.io/en/latest/updating_firmware.html).

## Bring-up defaults

From `hil/boards/hackrf.yaml`:

| Parameter | Value | Note |
| --- | --- | --- |
| `firmware_target` | 2026.01.3 | SPI flash goal |
| `center_hz` | 915e6 | Cable loopback only |
| `tone_offset_hz` | 100e3 | Baseband offset for CW |
| `txvga_db` | 0 | Clamped by `max_tx_db` |
| `max_tx_db` | 4 | Hard ceiling |
| `max_tx_ms` | 200 | Burst limit |
| `min_snr_db` | 10 | Pass threshold |

## Attenuator wiring

1. Connect HackRF **TX** to an attenuator (recommend ≥30 dB for first runs).
2. Connect the attenuator output to HackRF **RX**.
3. Confirm no antenna is attached.
4. Export `HIL_LOOPBACK=1`.
5. Run `present` → `workflow` → `make hil BOARD=hackrf`.

## SDK and manuals

- [HackRF documentation](https://hackrf.readthedocs.io/), archive ids `hackrf-one-docs-index`, `hackrf-hardware-overview`
- Vendor site: [greatscottgadgets.com/hackrf](https://greatscottgadgets.com/hackrf/)

## Stages

This board is the first target. Pluto stays closed until HackRF `image` passes. Stage list: [pipeline](../pipeline.md).

```bash
make stage BOARD=hackrf STAGE=present
make stage BOARD=hackrf STAGE=workflow
export HIL_LOOPBACK=1
make hil BOARD=hackrf
```
