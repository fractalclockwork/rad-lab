# HWIL bring-up

**Hardware-in-the-loop** automation, gated by **human-in-the-loop** assent. Finish this checklist before [lesson development](../lesson/).

## Roles

- **Human-in-the-loop** — plug in the DUT, attest attenuator cable (`HUMAN_LOOPBACK=1`), attest firmware identity (`HUMAN_FIRMWARE=1`), type `YES` (or `HUMAN_TX_CONFIRM=1`) before TX. See [`human/assent.py`](../human/assent.py).
- **HWIL** — staged probe, fixture, container loopback, SNR/peak, evidence under `reports/<board>/`. Entry points: `make stage`, `make hwil`.

`reports/<board>/stage.json` gates Make stages and unlocks RF labs plus lesson labs once both boards’ `image` stages pass. Baofeng / 2 m / crossboard labs write under `reports/` but do **not** replace `make hwil`.

## Sequence

1. **[Tooling](docs/bringup/tooling.md)** — archive, container image, firmware validate/upgrade, staged `present` → `workflow` → same-board `image` where gated.
2. **RX/TX per DUT** — Baofeng 2 m bootstrap against HackRF and Pluto ([baofeng simplex](docs/bringup/baofeng-simplex.md), [Pluto 2 m](docs/bringup/pluto-2m.md)).
3. **[Cross-board CW](docs/bringup/crossboard-915-cw.md)** — HackRF↔Pluto at 915 MHz.

## Entry points

| Path | Role |
| --- | --- |
| [docs/bringup/](docs/bringup/README.md) | Ordered bring-up guides |
| [docs/boards/](docs/boards/) | Per-device pages |
| [docs/pipeline.md](docs/pipeline.md) | Stages, env vars, container |
| [labs/](labs/README.md) | Bring-up lab scripts |
| [boards/](boards/) | Board YAML |
| [AGENTS.md](AGENTS.md) | Agentic HWIL rules |

```bash
make archive && make image
make stage BOARD=hackrf STAGE=present
make stage BOARD=hackrf STAGE=workflow
HUMAN_LOOPBACK=1 make hwil BOARD=hackrf
```
