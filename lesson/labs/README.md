# Lesson labs

Software-first DSP labs for [`lesson/lessons/`](../lessons/). No Soapy TX; plots use matplotlib (`Agg`). Unlocked by `harness.ready.require_lessons()` after both boards’ HWIL `image` stages pass.

```bash
.venv/bin/python lesson/labs/01_iq_tone_plots.py
.venv/bin/python lesson/labs/02_am_mod_demod.py
.venv/bin/python lesson/labs/03_fm_mod_demod.py
.venv/bin/python lesson/labs/04_psk_constellation.py
.venv/bin/python lesson/labs/05_qam_constellation.py
.venv/bin/python lesson/labs/06_windowing_spectral.py
.venv/bin/python lesson/labs/07_duc_ddc_iq.py
.venv/bin/python lesson/labs/08_awgn_ebno.py
.venv/bin/python lesson/labs/09_constellation_impairments.py
.venv/bin/python lesson/labs/10_mfsk.py
.venv/bin/python lesson/labs/11_rrc_eye_diagram.py
.venv/bin/python lesson/labs/12_ber_monte_carlo.py
.venv/bin/python lesson/labs/13_hamming74.py
```

Or: `make lesson LAB=01`
