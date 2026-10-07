# HackRF One

Wideband half-duplex SDR transceiver from Great Scott Gadgets. USB VID:PID `1d50:6089`. SoapySDR driver `hackrf`.

Lessons: [sampling and IQ](../learn/01-sampling-and-iq.md), [HackRF bring-up](../learn/02-hackrf-bring-up.md), [loopback HIL](../learn/03-loopback-hil.md).

## Specification

| Item | Value |
| --- | --- |
| Part | HackRF One |
| Tuning | ~1 MHz to 6 GHz |
| Sample rate | up to 20 Msps (bring-up uses 2 Msps) |
| USB | `1d50:6089` |
| Probe | `hackrf_info`, Soapy `driver=hackrf` |
| TX safety | Attenuated SMA cable TX→RX only; `HIL_LOOPBACK=1` |

## Bring-up defaults

From `boards/hackrf.yaml`:

| Parameter | Value | Note |
| --- | --- | --- |
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
