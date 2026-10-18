# Supporting hardware (catalog)

These parts are listed for the lab but are **not** accepted by `make stage` until a probe and stage contract exist.

| Item | Role | Stage id |
| --- | --- | --- |
| Chip frequency generators | Reference / LO | — |
| Amplifiers | Gain stages | — |
| Circulators / splitters / mixers | RF plumbing | — |
| Spectrum analyzer | Observation | — |
| Network analyzer | S-parameters | — |
| USB-VGA DAC (FL2000) | Baseband / HF DAC via osmo-fl2k | — |
| Baofeng UV-5R+PLUS | Dual-band VHF/UHF FM handheld | — |

**FL2000** (`1d5c:2000`): TX-only 8-bit VGA DAC. Most useful as a **baseband** source (**DC–~50 MHz** on green). FM broadcast and VHF images are outside the usable range here; external mixer/LO would be needed to heterodyne later. Specs: [fl2000.md](fl2000.md).

The UV-5R+PLUS conducted check is [baofeng simplex bring-up](../bringup/baofeng-simplex.md): 146.550 MHz wide FM and 446.500 MHz narrow FM, HackRF receive only. The same radio is the known 2 m partner for the Pluto: RX and TX on 146.550 MHz both passed (see [ADALM-PLUTO](pluto.md) and [pluto-2m](../bringup/pluto-2m.md)). Document other part numbers here as devices are brought up with HIL. Prefer attenuated cable paths before any antenna work.
