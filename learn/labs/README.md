# Tutorial labs

Software-first DSP labs for [`learn/lessons/`](../lessons/). No Soapy TX; plots use matplotlib (`Agg`).

| Lab | Script | Lesson |
| --- | --- | --- |
| IQ tone plots | [01_iq_tone_plots.py](01_iq_tone_plots.py) | [01](../lessons/01-sampling-and-iq.md) |
| AM mod/demod | [02_am_mod_demod.py](02_am_mod_demod.py) | [02](../lessons/02-am-mod-demod.md) |
| FM mod/demod | [03_fm_mod_demod.py](03_fm_mod_demod.py) | [03](../lessons/03-fm-mod-demod.md) |
| PSK constellations | [04_psk_constellation.py](04_psk_constellation.py) | [04](../lessons/04-psk-constellation.md) |
| 16-QAM constellation | [05_qam_constellation.py](05_qam_constellation.py) | [05](../lessons/05-qam-constellation.md) |
| Windowing & spectra | [06_windowing_spectral.py](06_windowing_spectral.py) | [06](../lessons/06-windowing-spectral.md) |
| DUC / DDC roundtrip | [07_duc_ddc_iq.py](07_duc_ddc_iq.py) | [07](../lessons/07-duc-ddc.md) |
| AWGN vs Eb/N0 | [08_awgn_ebno.py](08_awgn_ebno.py) | [08](../lessons/08-awgn-ebno.md) |
| Constellation impairments | [09_constellation_impairments.py](09_constellation_impairments.py) | [09](../lessons/09-impairments.md) |
| M-FSK non-coherent | [10_mfsk.py](10_mfsk.py) | [10](../lessons/10-mfsk.md) |
| RRC / eye diagram | [11_rrc_eye_diagram.py](11_rrc_eye_diagram.py) | [11](../lessons/11-rrc-eye.md) |
| Monte Carlo BER | [12_ber_monte_carlo.py](12_ber_monte_carlo.py) | [12](../lessons/12-ber-monte-carlo.md) |
| Hamming (7,4) coding | [13_hamming74.py](13_hamming74.py) | [13](../lessons/13-hamming74.md) |

Shared helpers: [`dsp_common.py`](dsp_common.py).

```bash
# from repo root, after pip install -r requirements.txt
.venv/bin/python learn/labs/01_iq_tone_plots.py
.venv/bin/python learn/labs/02_am_mod_demod.py
.venv/bin/python learn/labs/03_fm_mod_demod.py
.venv/bin/python learn/labs/04_psk_constellation.py
.venv/bin/python learn/labs/05_qam_constellation.py
.venv/bin/python learn/labs/06_windowing_spectral.py
.venv/bin/python learn/labs/07_duc_ddc_iq.py
.venv/bin/python learn/labs/08_awgn_ebno.py
.venv/bin/python learn/labs/09_constellation_impairments.py
.venv/bin/python learn/labs/10_mfsk.py
.venv/bin/python learn/labs/11_rrc_eye_diagram.py
.venv/bin/python learn/labs/12_ber_monte_carlo.py
.venv/bin/python learn/labs/13_hamming74.py
```

Bring-up / RF labs remain under [`hil/labs/`](../../hil/labs/).
