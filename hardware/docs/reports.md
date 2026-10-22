# Reports

Runs write under `reports/`. That directory is gitignored. Nothing here starts a metrics server. The JSON and JUnit files are the records a later scraper or agent would read.

## Stage record

`reports/<board>/stage.json` is one document updated in place. Each key under `stages` is `present`, `workflow`, or `image`.

```json
{
  "board": "hackrf",
  "stages": {
    "present": {
      "status": "pass",
      "stage": "present",
      "at": "2026-10-06T00:00:00+00:00",
      "device": "HackRF One",
      "serial": "0000000000000000",
      "tool": "hackrf_info"
    }
  }
}
```

`status` is `pass` or `fail`. A failure adds `reason` and often `next` (the recovery command). The image stage, when it passes, also stores `loopback` and `report_dir`.

## One image-stage directory

`reports/<board>/<YYYYMMDDTHHMMSSZ>/` is created after the USB check on the image stage.

| File | Written by | Contents |
| --- | --- | --- |
| `fixture.json` | `fixture.py` | Synthetic tone SNR check |
| `hil.jsonl` | `loopback.py` | One JSON object per exchange (filename kept for scrapers) |
| `junit.xml` | `loopback.py` | One `testcase` per exchange, or a `failure` |
| `image_summary.json` | `stage.py` | Fixture + loopback bundle |

### `hil.jsonl` fields

```json
{
  "sent": "CW_TONE",
  "expected": "peak~100000.0Hz snr>=7.0dB",
  "actual": "peak=100097.7Hz snr=28.4dB",
  "snr_db": 28.4,
  "host_monotonic_ns": 123456789,
  "mode": "hardware"
}
```

`mode` is `hardware` or `simulated`.
