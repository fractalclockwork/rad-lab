# Documentation

Board pages, lessons, the local archive, and the host-driven hardware-in-the-loop pipeline for SDR bring-up.

| Topic | Page |
| --- | --- |
| Boards | [hackrf](boards/hackrf.md), [pluto](boards/pluto.md), [fl2000](boards/fl2000.md), [accessories](boards/accessories.md) |
| Concepts | [Lessons](learn/README.md) |
| Cached manuals | [Archive](../archive/README.md) |
| Stages and container | [Pipeline](pipeline.md) |
| JSON and JUnit records | [Reports](reports.md) |
| Labs | [labs/](../labs/README.md) |
| Agents | [AGENTS.md](../AGENTS.md) |

## Supported hardware

| Board id | Target | Probe | Primary image path |
| --- | --- | --- | --- |
| `hackrf` | HackRF One | `hackrf_info` / Soapy `hackrf` | TX↔RX attenuator loopback |
| `pluto` | ADALM-PLUTO | Soapy `plutosdr` | TX↔RX attenuator loopback (after HackRF image) |

## Quick start

```bash
make archive
make image
make stage BOARD=hackrf STAGE=present
make stage BOARD=hackrf STAGE=workflow
export HIL_LOOPBACK=1
make hil BOARD=hackrf
```

Pluto stages stay closed until `reports/hackrf/stage.json` shows `image` as `pass`.
