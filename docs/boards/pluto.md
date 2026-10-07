# ADALM-PLUTO

Analog Devices ADALM-PLUTO (PlutoSDR). USB VID:PID typically `0456:b673`. SoapySDR driver `plutosdr`.

## Specification

| Item | Value |
| --- | --- |
| Part | ADALM-PLUTO |
| Tuning | ~70 MHz to 6 GHz (firmware dependent) |
| USB | `0456:b673` |
| Probe | Soapy `driver=plutosdr` |
| Gate | Requires HackRF `image` stage `pass` |

## Bring-up

Stages refuse to run until `reports/hackrf/stage.json` shows `image` as `pass`. Loopback rules match HackRF: attenuator cable, `HIL_LOOPBACK=1`, TX gain/time caps in `boards/pluto.yaml`.

```bash
export HIL_LOOPBACK=1
make stage BOARD=pluto STAGE=present
make stage BOARD=pluto STAGE=workflow
make hil BOARD=pluto
```

## Manuals

- [Pluto user guide](https://wiki.analog.com/university/tools/pluto/users), archive id `pluto-user-guide`
- [Hardware notes](https://wiki.analog.com/university/tools/pluto/hacking/hardware), archive id `pluto-hardware`
