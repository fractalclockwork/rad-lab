# Tutorial labs

Software-first DSP labs for [`learn/lessons/`](../lessons/). No Soapy TX; plots use matplotlib (`Agg`).

| Lab | Script | Lesson |
| --- | --- | --- |
| IQ tone plots | [01_iq_tone_plots.py](01_iq_tone_plots.py) | [01](../lessons/01-sampling-and-iq.md) |
| AM mod/demod | [02_am_mod_demod.py](02_am_mod_demod.py) | [02](../lessons/02-am-mod-demod.md) |
| FM mod/demod | [03_fm_mod_demod.py](03_fm_mod_demod.py) | [03](../lessons/03-fm-mod-demod.md) |
| PSK constellations | [04_psk_constellation.py](04_psk_constellation.py) | [04](../lessons/04-psk-constellation.md) |
| 16-QAM constellation | [05_qam_constellation.py](05_qam_constellation.py) | [05](../lessons/05-qam-constellation.md) |

Shared helpers: [`dsp_common.py`](dsp_common.py).

```bash
# from repo root, after pip install -r requirements.txt
.venv/bin/python learn/labs/01_iq_tone_plots.py
.venv/bin/python learn/labs/02_am_mod_demod.py
.venv/bin/python learn/labs/03_fm_mod_demod.py
.venv/bin/python learn/labs/04_psk_constellation.py
.venv/bin/python learn/labs/05_qam_constellation.py
```

Bring-up / RF labs remain under [`hil/labs/`](../../hil/labs/).
