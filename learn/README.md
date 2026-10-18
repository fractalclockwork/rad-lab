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
| 06 | [Windowing & Spectral Analysis](lessons/06-windowing-spectral.md) | [`labs/06_windowing_spectral.py`](labs/06_windowing_spectral.py) |
| 07 | [Digital Up/Down Conversion](lessons/07-duc-ddc.md) | [`labs/07_duc_ddc_iq.py`](labs/07_duc_ddc_iq.py) |
| 08 | [AWGN vs Eb/N0](lessons/08-awgn-ebno.md) | [`labs/08_awgn_ebno.py`](labs/08_awgn_ebno.py) |
| 09 | [Constellation Impairments](lessons/09-impairments.md) | [`labs/09_constellation_impairments.py`](labs/09_constellation_impairments.py) |
| 10 | [M-FSK Non-Coherent](lessons/10-mfsk.md) | [`labs/10_mfsk.py`](labs/10_mfsk.py) |
| 11 | [RRC Pulse Shaping & Eye Diagrams](lessons/11-rrc-eye.md) | [`labs/11_rrc_eye_diagram.py`](labs/11_rrc_eye_diagram.py) |
| 12 | [Monte Carlo BER vs Eb/N0](lessons/12-ber-monte-carlo.md) | [`labs/12_ber_monte_carlo.py`](labs/12_ber_monte_carlo.py) |
| 13 | [(7,4) Hamming Coding Gain](lessons/13-hamming74.md) | [`labs/13_hamming74.py`](labs/13_hamming74.py) |

Full index: [lessons/README.md](lessons/README.md). Outputs: `reports/learn/`.

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python learn/labs/01_iq_tone_plots.py
```
