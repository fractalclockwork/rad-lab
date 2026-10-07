# Labs

Hands-on exercises for the containerized SDR environment. Run after HackRF `present` at minimum; RF-transmitting labs require a passed workflow stage and `HIL_LOOPBACK=1`.

| Lab | Path | Hardware |
| --- | --- | --- |
| Tone SNR fixture | [01_tone_snr.py](01_tone_snr.py) | None |
| Soapy probe | [02_soapy_probe.py](02_soapy_probe.py) | HackRF preferred |

```bash
# inside venv or container, from repo root
python3 labs/01_tone_snr.py
python3 labs/02_soapy_probe.py
```
