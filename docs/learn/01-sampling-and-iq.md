# Sampling and IQ

A complex baseband sample is \(I + jQ\). At sample rate \(f_s\), a tone at offset \(f_0\) is:

\[
x[n] = A \exp\!\left(j 2\pi \frac{f_0}{f_s} n\right)
\]

For the HackRF bring-up fixture, \(f_s = 2\,\mathrm{Msps}\) and \(f_0 = 100\,\mathrm{kHz}\). One period of the tone spans \(f_s / f_0 = 20\) samples.

The HIL analyzer takes an FFT of a Hann-windowed capture, measures power in bins near \(f_0\), and compares it to the median power of the remaining bins. Pass when that ratio (in dB) meets `min_snr_db`.

See archive id `hackrf-one-docs-index` for vendor sampling limits. Do not treat this lesson as a substitute for the HackRF operating manual.
