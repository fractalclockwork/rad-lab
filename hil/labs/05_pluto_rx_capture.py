#!/usr/bin/env python3
"""RX-only Pluto capture at a chosen center (default 146.550 MHz for Baofeng HIL).

No TX. Arms the receiver, records an unkeyed floor, prompts to key, then
passes only when in-band power rises by the carrier threshold.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "hil" / "scripts"))
ROOT = REPO_ROOT

from radboards import load_board  # noqa: E402


def inband_power_db(iq, sample_rate, window_hz):
    """Mean power of the FFT bins inside ±window_hz, in dB."""
    samples = np.asarray(iq)
    n = int(samples.size)
    if n < 2 or sample_rate <= 0 or window_hz < 0:
        return float("nan")
    window = np.hanning(n).astype(np.float32)
    spec = np.fft.fftshift(np.fft.fft(samples * window))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / float(sample_rate)))
    mask = np.abs(freqs) <= float(window_hz)
    if not np.any(mask):
        return float("nan")
    power = float(np.mean(np.abs(spec[mask]) ** 2))
    return float(10 * np.log10(max(power, 1e-20)))


def carrier_rise_db(unkeyed_db, keyed_db):
    if not (np.isfinite(unkeyed_db) and np.isfinite(keyed_db)):
        return None
    return float(keyed_db - unkeyed_db)


def carrier_detected(rise_db, min_carrier_db):
    return rise_db is not None and float(rise_db) >= float(min_carrier_db)


def format_mhz(center_hz):
    return f"{float(center_hz) / 1e6:.3f}"


def announce_unkeyed(center_hz):
    print(
        f"Leave the transmitter unkeyed. Measuring the noise floor at {format_mhz(center_hz)} MHz.",
        file=sys.stderr,
    )


def prompt_to_key(center_hz, stdin=None):
    """Ask the operator to key. Return 0 after Enter, 1 on EOF."""
    print(
        f"Receiver ready on {format_mhz(center_hz)} MHz. "
        "Key the transmitter and hold PTT, then press Enter.",
        file=sys.stderr,
    )
    stream = sys.stdin if stdin is None else stdin
    if stream.readline() == "":
        print("EOF while waiting for key-up", file=sys.stderr)
        return 1
    return 0


def analyze_capture(iq, sample_rate, window_hz):
    got = int(iq.size)
    power = float(np.mean(np.abs(iq) ** 2)) if got else 0.0
    rms = float(np.sqrt(power))
    peak = float(np.max(np.abs(iq))) if got else 0.0
    inband_db = inband_power_db(iq, sample_rate, window_hz)
    peak_hz = None
    peak_db = None
    noise_db = None
    over_noise = None
    if got >= 2:
        window = np.hanning(got).astype(np.float32)
        spec = np.fft.fftshift(np.fft.fft(iq * window))
        freqs = np.fft.fftshift(np.fft.fftfreq(got, d=1.0 / float(sample_rate)))
        psd_db = 10 * np.log10(np.maximum(np.abs(spec) ** 2, 1e-20))
        peak_idx = int(np.argmax(psd_db))
        peak_hz = float(freqs[peak_idx])
        peak_db = float(psd_db[peak_idx])
        noise_mask = np.abs(freqs) > sample_rate / got * 4
        if np.any(noise_mask):
            noise_db = float(np.median(psd_db[noise_mask]))
            over_noise = peak_db - noise_db
    return {
        "samples_captured": got,
        "rms": rms,
        "peak_abs": peak,
        "mean_power": power,
        "mean_power_db": float(10 * np.log10(max(power, 1e-20))),
        "inband_power_db": None if not np.isfinite(inband_db) else inband_db,
        "spectrum_peak_offset_hz": peak_hz,
        "spectrum_peak_db": peak_db,
        "spectrum_noise_floor_db": noise_db,
        "spectrum_peak_over_noise_db": over_noise,
    }


def capture_iq(dev, stream, n, rx_ms):
    buf = np.zeros(n, dtype=np.complex64)
    got = 0
    t0 = time.monotonic()
    deadline = t0 + rx_ms / 1000.0 + 2.0
    while got < n and time.monotonic() < deadline:
        sr = dev.readStream(stream, [buf[got:]], n - got)
        if sr.ret > 0:
            got += int(sr.ret)
        elif sr.ret < -1:
            break
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    return buf[:got], elapsed_ms


def capture_complete(got, n):
    return got >= n * 0.9 and got >= 1024


def write_snippet(path, iq, sample_rate):
    n = min(int(iq.size), max(1, int(sample_rate) // 10))
    iq[:n].tofile(path)


def main(argv=None):
    p = argparse.ArgumentParser(description="Pluto RX-only 2 m simplex carrier check")
    p.add_argument("--freq", type=int, default=146_550_000, help="Center Hz")
    p.add_argument("--rate", type=int, default=2_000_000, help="Sample rate Hz")
    p.add_argument("--rx-ms", type=int, default=2000, help="Capture length ms")
    p.add_argument("--gain", type=float, default=30.0, help="RX gain dB")
    p.add_argument(
        "--window-hz",
        type=float,
        default=15_000,
        help="In-band half-width Hz around DC",
    )
    p.add_argument(
        "--min-carrier-db",
        type=float,
        default=10.0,
        help="Minimum keyed in-band rise over the unkeyed floor",
    )
    p.add_argument(
        "--tag",
        default="2m_wide",
        help="Output name tag under reports/pluto/uv5r/",
    )
    p.add_argument(
        "--no-prompt",
        action="store_true",
        help="Skip the key-up prompt and capture the keyed interval immediately",
    )
    args = p.parse_args(argv)

    board = load_board("pluto")
    sample_rate = int(args.rate)
    center_hz = int(args.freq)
    rx_ms = int(args.rx_ms)
    gain = float(args.gain)
    window_hz = float(args.window_hz)
    min_carrier_db = float(args.min_carrier_db)
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
    try:
        warmup_n = max(1024, int(sample_rate * 0.1))
        capture_iq(dev, stream, warmup_n, 100)
        announce_unkeyed(center_hz)
        unkeyed, unkeyed_ms = capture_iq(dev, stream, n, rx_ms)
        if not capture_complete(unkeyed.size, n):
            print(f"unkeyed capture only {unkeyed.size} samples", file=sys.stderr)
            return 1
        if args.no_prompt:
            print(
                "Skipping key-up prompt; capturing the keyed interval now.",
                file=sys.stderr,
            )
        elif prompt_to_key(center_hz) != 0:
            return 1
        keyed, keyed_ms = capture_iq(dev, stream, n, rx_ms)
    finally:
        dev.deactivateStream(stream)
        dev.closeStream(stream)

    unkeyed_stats = analyze_capture(unkeyed, sample_rate, window_hz)
    keyed_stats = analyze_capture(keyed, sample_rate, window_hz)
    unkeyed_stats["elapsed_ms"] = round(unkeyed_ms, 2)
    keyed_stats["elapsed_ms"] = round(keyed_ms, 2)
    rise = carrier_rise_db(
        unkeyed_stats["inband_power_db"]
        if unkeyed_stats["inband_power_db"] is not None
        else float("nan"),
        keyed_stats["inband_power_db"]
        if keyed_stats["inband_power_db"] is not None
        else float("nan"),
    )
    detected = carrier_detected(rise, min_carrier_db)
    both_complete = capture_complete(unkeyed.size, n) and capture_complete(keyed.size, n)
    status = "pass" if both_complete and detected else "fail"

    out = ROOT / "reports" / "pluto" / "uv5r"
    out.mkdir(parents=True, exist_ok=True)
    khz = center_hz // 1000
    unkeyed_iq = out / f"rx_{args.tag}_unkeyed_{khz}khz.c64"
    keyed_iq = out / f"rx_{args.tag}_keyed_{khz}khz.c64"
    write_snippet(unkeyed_iq, unkeyed, sample_rate)
    write_snippet(keyed_iq, keyed, sample_rate)
    unkeyed_stats["iq_snippet"] = str(unkeyed_iq.relative_to(ROOT))
    keyed_stats["iq_snippet"] = str(keyed_iq.relative_to(ROOT))

    report = {
        "status": status,
        "at": datetime.now(timezone.utc).isoformat(),
        "mode": "rx_only",
        "board": "pluto",
        "serial": serial,
        "center_hz": center_hz,
        "sample_rate": sample_rate,
        "rx_ms_requested": rx_ms,
        "rx_gain_db": gain,
        "samples_requested": n,
        "carrier_window_hz": window_hz,
        "min_carrier_db": min_carrier_db,
        "carrier_rise_db": rise,
        "carrier_detected": detected,
        "unkeyed": unkeyed_stats,
        "keyed": keyed_stats,
        "note": (
            "RX-only; no Pluto TX. Pass when keyed in-band power rises "
            "by min_carrier_db over the unkeyed floor."
        ),
    }
    report_path = out / f"rx_{args.tag}_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not both_complete:
        print(f"keyed capture only {keyed.size} samples", file=sys.stderr)
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
