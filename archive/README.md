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
| `sdk` | Large proprietary toolchains if added later |
| `binary` | Captured IQ fixtures kept beside a run report |

## Docker image

After `make image` succeeds, `make archive-image` runs `docker save` of `rad-lab-sdr` into `archive/cache/images/`. Restoring is `docker load`, not another silent install.
