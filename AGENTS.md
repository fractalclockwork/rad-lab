# Agentic rules

This repo is structured by **role**. Agents must stand in one role at a time and follow that tree’s `AGENTS.md`.

**Terminology:** **HWIL** = hardware-in-the-loop (physical DUT automation). **Human** / **human-in-the-loop** = operator role (always spelled out). Assent env vars are `HUMAN_*`.

| Role | Tree | May invent? | Notes |
| --- | --- | --- | --- |
| **human** (human-in-the-loop) | [`human/`](human/) | Never assent | Do not set `HUMAN_*` or type YES |
| **hardware** (HWIL) | [`hardware/`](hardware/) | After assent + evidence | RF stages, firmware, RF labs |
| **software** | [`software/`](software/) | Freely | Fixture + DSP; no USB |
| **environment** | [`environment/`](environment/) | Freely for builds | Container/host boundary, archive |
| **lesson** | [`lesson/`](lesson/) | Content only | Unlocked by `reports/*/stage.json` |
| **harness** | [`harness/`](harness/) | Paths + ready gates only | No TX, no prompts |

Evidence under `reports/` is the only unlock token across roles.

Methodology: [`docs/methodology/`](docs/methodology/README.md).
