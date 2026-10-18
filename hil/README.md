# HIL bring-up

Workflow A for rad-lab. Finish this checklist before [lesson development](../learn/).

## Sequence

1. **[Tooling](docs/bringup/tooling.md)** — archive, container image, firmware validate/upgrade, staged `present` → `workflow` → same-board `image` where gated.
2. **RX/TX per DUT** — Baofeng 2 m bootstrap against HackRF and Pluto ([baofeng simplex](docs/bringup/baofeng-simplex.md), [Pluto 2 m](docs/bringup/pluto-2m.md)).
3. **[Cross-board CW](docs/bringup/crossboard-915-cw.md)** — HackRF↔Pluto at 915 MHz.

`reports/<board>/stage.json` gates Make stages. Baofeng / 2 m / crossboard labs write under `reports/` but do **not** replace `make hil`.

## Entry points

| Path | Role |
| --- | --- |
| [docs/bringup/](docs/bringup/README.md) | Ordered bring-up guides |
| [docs/boards/](docs/boards/) | Per-device pages |
| [docs/pipeline.md](docs/pipeline.md) | Stages, env vars, container |
| [labs/](labs/README.md) | Bring-up lab scripts |
| [boards/](boards/) | Board YAML |
| [AGENTS.md](AGENTS.md) | Agentic HIL rules |

```bash
make archive && make image
make stage BOARD=hackrf STAGE=present
make stage BOARD=hackrf STAGE=workflow
HIL_LOOPBACK=1 make hil BOARD=hackrf
```
