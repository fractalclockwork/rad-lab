# Lesson development

Start here only after the [HIL bring-up checklist](../hil/README.md) is complete (tooling, per-DUT RX/TX, crossboard CW).

This tree is a **software-first DSP curriculum**: modulation, demodulation, spectra, and constellations on synthetic IQ. Prefer attenuated cable paths and follow [`hil/AGENTS.md`](../hil/AGENTS.md) if you later add conducted RF labs.

## Curriculum

| # | Lesson | Lab |
| --- | --- | --- |
| 01 | [Sampling and IQ](lessons/01-sampling-and-iq.md) | [`labs/01_iq_tone_plots.py`](labs/01_iq_tone_plots.py) |
| 02 | [Analog AM](lessons/02-am-mod-demod.md) | [`labs/02_am_mod_demod.py`](labs/02_am_mod_demod.py) |
| 03 | [Analog FM](lessons/03-fm-mod-demod.md) | [`labs/03_fm_mod_demod.py`](labs/03_fm_mod_demod.py) |
| 04 | [Digital PSK](lessons/04-psk-constellation.md) | [`labs/04_psk_constellation.py`](labs/04_psk_constellation.py) |
| 05 | [Digital 16-QAM](lessons/05-qam-constellation.md) | [`labs/05_qam_constellation.py`](labs/05_qam_constellation.py) |

Full index: [lessons/README.md](lessons/README.md). Outputs: `reports/learn/`.

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python learn/labs/01_iq_tone_plots.py
```
