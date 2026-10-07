# Archive

Git tracks `archive/manifest.yaml`. The files themselves live in `archive/cache/` and are gitignored. That split keeps large manuals and optional Docker image tarballs on this machine without bloating the repository. Lessons cite cached files by archive id. They do not copy the manuals.

`make archive` runs `scripts/archive.py`.

- A row with a public URL is downloaded when the cache copy is missing or its sha256 does not match.
- A row marked `manual: true` is skipped until you copy the file to `path`.
- `optional: true` means a failed download is reported and does not fail the whole archive run.
- Size and retrieve date are written to `archive/cache/status.json`.

## Kinds

| Kind | What goes here |
| --- | --- |
| `doc` | Reference manuals, hardware pages, datasheets |
| `image` | Board photos, and `docker save` of `rad-lab-sdr` |
| `sdk` | HackRF release tarballs (e.g. `hackrf-2026.01.3`), extracted under `archive/cache/sdk/` |
| `binary` | Captured IQ fixtures kept beside a run report |

## Extract

Rows with `extract: true` unpack after a successful fetch. `extract_dir` is the expected unpacked tree; `extract_marker` is a file that must exist afterward (for HackRF, `firmware-bin/hackrf_one_usb.bin`).

## Docker image

`make image` requires the HackRF SDK tarball in cache (via `make archive`) so the container can build matching `libhackrf` / `hackrf-tools`. After `make image` succeeds, `make archive-image` runs `docker save` of `rad-lab-sdr` into `archive/cache/images/`. Restoring is `docker load`, not another silent install.
