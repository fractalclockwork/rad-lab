#!/usr/bin/env python3
"""RX-only Pluto capture at a chosen center (default 146.550 MHz for Baofeng HIL).

No TX. Prefer Soapy plutosdr; requires present-class USB access.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from radboards import load_board  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description="Pluto RX-only spectrum capture")
    p.add_argument("--freq", type=int, default=146_550_000, help="Center Hz")
    p.add_argument("--rate", type=int, default=2_000_000, help="Sample rate Hz")
    p.add_argument("--rx-ms", type=int, default=2000, help="Capture length ms")
    p.add_argument("--gain", type=float, default=30.0, help="RX gain dB")
    p.add_argument(
        "--tag",
        default="2m_wide",
        help="Output name tag under reports/pluto/uv5r/",
    )
    args = p.parse_args(argv)

    board = load_board("pluto")
    sample_rate = int(args.rate)
    center_hz = int(args.freq)
    rx_ms = int(args.rx_ms)
    gain = float(args.gain)
    n = max(4096, int(sample_rate * rx_ms / 1000))

    import SoapySDR  # type: ignore
    from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32  # type: ignore

    driver = board.get("soapy_driver") or "plutosdr"
    devices = SoapySDR.Device.enumerate(dict(driver=driver))
    if not devices:
        print(f"no Pluto via Soapy driver={driver}", file=sys.stderr)
        return 1
    args_dev = dict(devices[0])
    serial = str(args_dev.get("serial", args_dev.get("label", "")))
    dev = SoapySDR.Device(devices[0])
    dev.setSampleRate(SOAPY_SDR_RX, 0, sample_rate)
    dev.setFrequency(SOAPY_SDR_RX, 0, center_hz)
    try:
        dev.setGain(SOAPY_SDR_RX, 0, gain)
    except Exception:
        pass

    stream = dev.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
    dev.activateStream(stream)
    buf = np.zeros(n, dtype=np.complex64)
    got = 0
    t0 = time.monotonic()
    deadline = t0 + rx_ms / 1000.0 + 2.0
    while got < n and time.monotonic() < deadline:
        sr = dev.readStream(stream, [buf[got:]], n - got)
        if sr.ret > 0:
            got += sr.ret
        elif sr.ret < -1:
            break
    dev.deactivateStream(stream)
    dev.closeStream(stream)
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    if got < 1024:
        print(f"only {got} samples", file=sys.stderr)
        return 1

    iq = buf[:got]
    power = float(np.mean(np.abs(iq) ** 2))
    rms = float(np.sqrt(power))
    peak = float(np.max(np.abs(iq)))
    window = np.hanning(got).astype(np.float32)
    spec = np.fft.fftshift(np.fft.fft(iq * window))
    freqs = np.fft.fftshift(np.fft.fftfreq(got, d=1.0 / sample_rate))
    psd_db = 10 * np.log10(np.maximum(np.abs(spec) ** 2, 1e-20))
    peak_idx = int(np.argmax(psd_db))
    peak_hz = float(freqs[peak_idx])
    peak_db = float(psd_db[peak_idx])
    noise_mask = np.abs(freqs) > sample_rate / got * 4
    noise_db = float(np.median(psd_db[noise_mask])) if np.any(noise_mask) else float("nan")
    over_noise = (peak_db - noise_db) if np.isfinite(noise_db) else None

    out = ROOT / "reports" / "pluto" / "uv5r"
    out.mkdir(parents=True, exist_ok=True)
    iq_path = out / f"rx_{args.tag}_{center_hz // 1000}khz.c64"
    iq[: min(got, sample_rate // 10)].tofile(iq_path)

    report = {
        "status": "pass" if got >= n * 0.9 else "partial",
        "at": datetime.now(timezone.utc).isoformat(),
        "mode": "rx_only",
        "board": "pluto",
        "serial": serial,
        "center_hz": center_hz,
        "sample_rate": sample_rate,
        "rx_ms_requested": rx_ms,
        "rx_gain_db": gain,
        "samples_requested": n,
        "samples_captured": int(got),
        "elapsed_ms": round(elapsed_ms, 2),
        "rms": rms,
        "peak_abs": peak,
        "mean_power": power,
        "mean_power_db": float(10 * np.log10(max(power, 1e-20))),
        "spectrum_peak_offset_hz": peak_hz,
        "spectrum_peak_db": peak_db,
        "spectrum_noise_floor_db": noise_db,
        "spectrum_peak_over_noise_db": over_noise,
        "iq_snippet": str(iq_path.relative_to(ROOT)),
        "note": "RX-only; no Pluto TX. Compare keyed vs unkeyed Baofeng captures.",
    }
    report_path = out / f"rx_{args.tag}_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
