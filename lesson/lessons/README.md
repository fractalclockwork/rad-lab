# Lessons

Tutorials after [HWIL bring-up](../../hardware/README.md). All modulation labs are **software-only** (synthetic IQ + plots). Worked tone numbers still match `hardware/boards/hackrf.yaml` (2 Msps, 100 kHz offset).

1. [Sampling and IQ](01-sampling-and-iq.md) — [`lesson/labs/01_iq_tone_plots.py`](../labs/01_iq_tone_plots.py)
2. [Analog AM](02-am-mod-demod.md) — [`lesson/labs/02_am_mod_demod.py`](../labs/02_am_mod_demod.py)
3. [Analog FM](03-fm-mod-demod.md) — [`lesson/labs/03_fm_mod_demod.py`](../labs/03_fm_mod_demod.py)
4. [Digital PSK](04-psk-constellation.md) — [`lesson/labs/04_psk_constellation.py`](../labs/04_psk_constellation.py)
5. [Digital 16-QAM](05-qam-constellation.md) — [`lesson/labs/05_qam_constellation.py`](../labs/05_qam_constellation.py)
6. [Windowing & Spectral Analysis](06-windowing-spectral.md) — [`lesson/labs/06_windowing_spectral.py`](../labs/06_windowing_spectral.py)
7. [Digital Up/Down Conversion](07-duc-ddc.md) — [`lesson/labs/07_duc_ddc_iq.py`](../labs/07_duc_ddc_iq.py)
8. [AWGN vs Eb/N0](08-awgn-ebno.md) — [`lesson/labs/08_awgn_ebno.py`](../labs/08_awgn_ebno.py)
9. [Constellation Impairments](09-impairments.md) — [`lesson/labs/09_constellation_impairments.py`](../labs/09_constellation_impairments.py)
10. [M-FSK Non-Coherent](10-mfsk.md) — [`lesson/labs/10_mfsk.py`](../labs/10_mfsk.py)
11. [RRC Pulse Shaping & Eye Diagrams](11-rrc-eye.md) — [`lesson/labs/11_rrc_eye_diagram.py`](../labs/11_rrc_eye_diagram.py)
12. [Monte Carlo BER vs Eb/N0](12-ber-monte-carlo.md) — [`lesson/labs/12_ber_monte_carlo.py`](../labs/12_ber_monte_carlo.py)
13. [(7,4) Hamming Coding Gain](13-hamming74.md) — [`lesson/labs/13_hamming74.py`](../labs/13_hamming74.py)

Plots and JSON reports land in `reports/lesson/<lab_tag>/`.
