#!/usr/bin/env python3
"""RX-only capture and spectrum summary (no TX)."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
ROOT = REPO_ROOT

from harness.radboards import load_board  # noqa: E402
from harness.ready import require_rf  # noqa: E402


def main():
    require_rf("hackrf")
    board = load_board("hackrf")
    center_hz = int(board["center_hz"])
    sample_rate = int(board["sample_rate"])
    rx_ms = int(board.get("rx_ms", 400))
    lna = float(board.get("rx_lna_db", 16))
    vga = float(board.get("rx_vga_db", 16))
    n = max(4096, int(sample_rate * rx_ms / 1000))

    from environment.container import require_container  # noqa: E402

    require_container("hardware/labs/03_rx_capture.py")
    import SoapySDR  # type: ignore
    from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32  # type: ignore

    devices = SoapySDR.Device.enumerate(dict(driver="hackrf"))
    if not devices:
        print("no HackRF via Soapy", file=sys.stderr)
        return 1
    args = dict(devices[0])
    serial = str(args.get("serial", ""))
    dev = SoapySDR.Device(devices[0])
    dev.setSampleRate(SOAPY_SDR_RX, 0, sample_rate)
    dev.setFrequency(SOAPY_SDR_RX, 0, center_hz)
    try:
        dev.setGain(SOAPY_SDR_RX, 0, "LNA", lna)
        dev.setGain(SOAPY_SDR_RX, 0, "VGA", vga)
    except Exception:
        dev.setGain(SOAPY_SDR_RX, 0, lna)

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
    hot = float(np.mean(psd_db > (noise_db + 10))) if np.isfinite(noise_db) else float("nan")

    out = ROOT / "reports" / "hackrf" / "rx_test"
    out.mkdir(parents=True, exist_ok=True)
    iq_path = out / "rx_915mhz_2msps.c64"
    iq[: min(got, sample_rate // 10)].tofile(iq_path)

    report = {
        "status": "pass" if got >= n * 0.9 else "partial",
        "at": datetime.now(timezone.utc).isoformat(),
        "mode": "rx_only",
        "serial": serial,
        "center_hz": center_hz,
        "sample_rate": sample_rate,
        "rx_ms_requested": rx_ms,
        "rx_lna_db": lna,
        "rx_vga_db": vga,
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
        "spectrum_peak_over_noise_db": (peak_db - noise_db) if np.isfinite(noise_db) else None,
        "bins_hot_frac": hot,
        "iq_snippet": str(iq_path.relative_to(ROOT)),
        "note": "RX-only noise/spectrum capture; no TX.",
    }
    (out / "rx_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
