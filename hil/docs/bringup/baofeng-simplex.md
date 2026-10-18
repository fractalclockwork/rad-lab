# Baofeng UV-5R+PLUS simplex HIL

The UV-5R+PLUS is an FM handheld, not a `make stage` target. This bring-up step uses it as a known transmitter on two US amateur simplex channels. The HackRF only receives. Nothing in this procedure is written into `stage.json`, and it does not replace the 915 MHz cable loopback in [loopback HIL](loopback.md).

The radio transmits analog FM only. The two supported channel modes are wide FM and narrow FM. AM, SSB, and digital voice are outside this set, so the HIL pair is one wide test and one narrow test.

## Bench rules

- Take the antenna off the Baofeng and off the HackRF. Terminate the Baofeng with a 50 Ω load through the attenuator chain below.
- Set the Baofeng to low power. High power is about 4–5 W and is not used here.
- HackRF commands in this lesson are receive-only. Do not pass a transmit file, and leave the HackRF RF amp off.
- These frequencies follow the US (ITU Region 2) amateur band plan. They are inside the UV-5R+PLUS US transmit ranges (144–148 MHz and 420–450 MHz). If a signal from this bench can be heard on another receiver without a cable, stop and fix the load before any further key-up.
- Radiated use is a separate, licensed contact: Technician or higher in the US, callsign identification, and a local band-plan check. Do not move this procedure onto an antenna, and do not park test traffic on the national calling channels 146.520 or 446.000 MHz.
- HackRF TX ID bursts use [`hil/labs/04_tx_callsign_fm.py`](../../labs/04_tx_callsign_fm.py). Pluto uses [`hil/labs/06_pluto_tx_callsign_fm.py`](../../labs/06_pluto_tx_callsign_fm.py) on 146.550 MHz and refuses TX unless `HIL_LOOPBACK=1`. Pass `--callsign YOURCALL` or export `RAD_LAB_CALLSIGN`; the repo does not ship a personal callsign default.

## Tests

Both tests are simplex: no repeater shift, no CTCSS, no DCS.

| Test | Band | Frequency | Segment | Mode | Spacing | Peak deviation |
| --- | --- | --- | --- | --- | --- | --- |
| `2m-wide` | 2 m | 146.550 MHz | 146.40–146.58 MHz FM simplex | Wide FM, 16K0F3E | 25 kHz | ±5 kHz |
| `70cm-narrow` | 70 cm | 446.500 MHz | 445–447 MHz shared FM simplex | Narrow FM, 11K0F3E | 12.5 kHz | ±2.5 kHz |

146.550 MHz sits in the 2 m simplex segment and is not the 146.520 MHz calling channel. 446.500 MHz sits in the 70 cm simplex segment and is not the 446.000 MHz calling channel. Confirm both are still simplex where you operate before any radiated use.

## Baofeng setup

Use VFO mode on the A display. Turn dual watch off so the radio cannot key the other VFO.

| Menu name | Setting | Why |
| --- | --- | --- |
| TXP | LOW | About 1 W (+30 dBm) into the pad |
| WN | WIDE on 146.550, NARR on 446.500 | Selects the test mode |
| SFT | OFF | Simplex |
| OFFSET | 0 | No repeater split |
| T-CTCS / R-CTCS | OFF | Carrier test, no tone squelch |
| T-DCS / R-DCS | OFF | Same |

Enter 146.550, set WN to WIDE, and run the 2 m capture below. Then enter 446.500, set WN to NARR, and run the 70 cm capture. Menu numbers on the UV-5R series are usually TXP = 2, WN = 5, SFT = 25, OFFSET = 26; trust the menu name if a firmware build renumbers them.

## Wiring

Low power is +30 dBm. Keep the HackRF RX port at or below about −20 dBm, which takes at least 50 dB of attenuation. Put a power-rated pad first.

1. Baofeng antenna jack (SMA) to a 30 dB attenuator rated for at least 2 W (5 W is better).
2. That pad to a second 20 dB or 30 dB attenuator.
3. The second pad to HackRF **RX** only.
4. No antenna anywhere in the chain. The HackRF input is the 50 Ω termination.

A 30 dB + 20 dB chain leaves about −20 dBm at the HackRF from 1 W. Add another 10 dB if the spectrum is clipping.

## HackRF receive

Run these from the repo root after the HackRF `present` stage. Each capture is two seconds at 2 Msps, which is wide enough for either FM mode. LNA and VGA stay at 0 because the conducted carrier is strong.

```bash
mkdir -p reports/hackrf/uv5r

# 2m-wide: 146.550 MHz, Baofeng WN = WIDE, keyed on low power
hackrf_transfer -r reports/hackrf/uv5r/2m_wide.cs8 \
  -f 146550000 -s 2000000 -n 4000000 -l 0 -g 0

# 70cm-narrow: 446.500 MHz, Baofeng WN = NARR, keyed on low power
hackrf_transfer -r reports/hackrf/uv5r/70cm_narrow.cs8 \
  -f 446500000 -s 2000000 -n 4000000 -l 0 -g 0
```

Also take one capture on each frequency with the Baofeng unkeyed. Those files are the noise floor for the same tune.

## Pass criteria

| Check | Unkeyed | Keyed, no voice | Keyed, speaking |
| --- | --- | --- | --- |
| Carrier at the tuned frequency | Absent | Present, within a few kilohertz of center | Present |
| `2m-wide` occupied bandwidth | Noise | Narrow carrier | On the order of ±5 kHz |
| `70cm-narrow` occupied bandwidth | Noise | Narrow carrier | On the order of ±2.5 kHz, clearly tighter than the wide capture |

The UV-5R+PLUS frequency stability is specified at ±2.5 ppm, about ±370 Hz at 146.550 MHz and about ±1.1 kHz at 446.500 MHz. A carrier inside that window is consistent with the radio. A carrier only on the unkeyed capture, or a HackRF that was run with a transmit option, fails the test.

Sample rate is 2 Msps, so a ±5 kHz deviation sits in a few bins next to DC after an FFT of the complex `cs8` capture (interleaved signed 8-bit I/Q). Compare the speaking captures to each other: the 446.500 MHz narrow recording must be the narrower of the two.
