#!/usr/bin/env python3
"""TX FM Morse callsign via ADALM-PLUTO (conducted path only).

Reuses Morse and FM helpers from labs/04_tx_callsign_fm.py.
Callsign is never hardcoded. Set it with --callsign or RAD_LAB_CALLSIGN.

Actual TX requires HIL_LOOPBACK=1 (operator asserts Pluto TX into an
attenuator and a 50 ohm load, or into another RX through that pad).
No antenna. National calling channels are refused.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "hil" / "scripts"))
ROOT = REPO_ROOT

from radboards import load_board  # noqa: E402

CALLSIGN_ENV = "RAD_LAB_CALLSIGN"
LOOPBACK_ENV = "HIL_LOOPBACK"
IMAGE_NAME = "rad-lab-sdr"
CALLING_HZ = {146_520_000, 446_000_000}
DEFAULT_FREQ = 146_550_000
DEFAULT_DEVIATION = 5000.0
DEFAULT_RATE = 2_000_000


def _hackrf_tx():
    path = Path(__file__).resolve().parent / "04_tx_callsign_fm.py"
    spec = importlib.util.spec_from_file_location("tx_callsign_fm", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def assert_loopback():
    if os.environ.get(LOOPBACK_ENV) != "1":
        raise SystemExit(
            f"set {LOOPBACK_ENV}=1 before Pluto TX "
            "(attenuator on the TX SMA; no antenna)"
        )


def assert_frequency(freq: int):
    if int(freq) in CALLING_HZ:
        raise SystemExit(
            f"refusing calling channel {int(freq)} Hz "
            "(146.520 and 446.000 are not lab frequencies)"
        )


def assert_tx_gain(requested: float, ceiling: float) -> float:
    requested = float(requested)
    ceiling = float(ceiling)
    if requested > ceiling:
        raise SystemExit(
            f"refusing TX gain {requested} dB above max_tx_db {ceiling} dB"
        )
    return requested


def build_iq(callsign: str, sample_rate: int, deviation_hz: float, repeat: int, wpm: int, with_tone: bool):
    tx = _hackrf_tx()
    text = " ".join([callsign] * max(1, repeat))
    audio_sr = 48_000
    audio = tx.morse_audio(text, audio_sr, wpm=wpm)
    if with_tone:
        t = np.arange(int(audio_sr * 2.0), dtype=np.float32) / audio_sr
        tone = 0.7 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        audio = np.concatenate([tone, audio, tone[: audio_sr // 2]])
    n_rf = int(len(audio) * sample_rate / audio_sr)
    x_old = np.linspace(0, 1, num=len(audio), endpoint=False)
    x_new = np.linspace(0, 1, num=n_rf, endpoint=False)
    audio_rf = np.interp(x_new, x_old, audio).astype(np.float32)
    iq = tx.fm_modulate(audio_rf, sample_rate, deviation_hz)
    return text, iq


def stream_file(path: Path, freq: int, sample_rate: int, gain_db: float):
    """Transmit one CF32 file on Pluto TX. Used inside rad-lab-sdr."""
    import SoapySDR  # type: ignore
    from SoapySDR import SOAPY_SDR_CF32, SOAPY_SDR_TX  # type: ignore

    assert_loopback()
    assert_frequency(freq)
    board = load_board("pluto")
    gain_db = assert_tx_gain(gain_db, float(board["max_tx_db"]))

    iq = np.fromfile(path, dtype=np.complex64)
    if iq.size < 1024:
        raise SystemExit(f"IQ file too short: {iq.size} samples")

    devices = SoapySDR.Device.enumerate(dict(driver="plutosdr"))
    if not devices:
        raise SystemExit("no Pluto via Soapy driver=plutosdr")
    args = dict(devices[0])
    serial = str(args.get("serial") or "")
    want = re.sub(r"[^0-9a-f]", "", str(board.get("expected_serial") or "").lower())
    seen = re.sub(r"[^0-9a-f]", "", serial.lower())
    if want and seen and want not in seen and seen not in want:
        raise SystemExit(f"refusing TX: expected serial {want}, saw {serial}")

    dev = SoapySDR.Device(devices[0])
    dev.setSampleRate(SOAPY_SDR_TX, 0, sample_rate)
    dev.setFrequency(SOAPY_SDR_TX, 0, freq)
    try:
        dev.setBandwidth(SOAPY_SDR_TX, 0, float(sample_rate))
    except Exception:
        pass
    dev.setGain(SOAPY_SDR_TX, 0, gain_db)

    tx_stream = dev.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)
    started = time.monotonic()
    duration_s = iq.size / float(sample_rate)
    try:
        dev.activateStream(tx_stream)
        mtu = min(int(iq.size), 1024 * 8)
        sent = 0
        while sent < iq.size:
            chunk = iq[sent : sent + mtu]
            sr = dev.writeStream(tx_stream, [chunk], int(chunk.size))
            if sr.ret < 0:
                raise SystemExit(f"TX writeStream failed: {sr.ret}")
            if sr.ret == 0:
                if time.monotonic() - started > duration_s * 2 + 2:
                    raise SystemExit("TX timed out")
                continue
            sent += sr.ret
    finally:
        try:
            dev.deactivateStream(tx_stream)
            dev.closeStream(tx_stream)
        except Exception:
            pass
    print(json.dumps({"status": "pass", "serial": serial, "samples": int(iq.size), "gain_db": gain_db}))
    return 0


def _docker_stream(iq_path: Path, freq: int, sample_rate: int, gain_db: float):
    rel = iq_path.relative_to(ROOT)
    script = Path(__file__).resolve().relative_to(ROOT)
    cmd = [
        "docker",
        "run",
        "--rm",
        "--privileged",
        "-e",
        f"{LOOPBACK_ENV}=1",
        "-v",
        "/dev/bus/usb:/dev/bus/usb",
        "-v",
        f"{ROOT}:/work",
        "-w",
        "/work",
        IMAGE_NAME,
        "python3",
        str(script),
        "--stream-file",
        str(rel),
        "--freq",
        str(freq),
        "--sample-rate",
        str(sample_rate),
        "--gain",
        str(gain_db),
    ]
    return subprocess.run(cmd, text=True)


def main(argv=None):
    board = load_board("pluto")
    ceiling = float(board["max_tx_db"])
    default_gain = float(board["txvga_db"])

    p = argparse.ArgumentParser(
        description="TX Morse callsign on FM via Pluto (conducted path only)",
        epilog=f"Callsign: --callsign YOURCALL or export {CALLSIGN_ENV}=YOURCALL",
    )
    p.add_argument("--callsign", default=None, help=f"Station callsign (or set {CALLSIGN_ENV}; no default)")
    p.add_argument("--freq", type=int, default=DEFAULT_FREQ)
    p.add_argument("--sample-rate", type=int, default=DEFAULT_RATE)
    p.add_argument("--deviation", type=float, default=DEFAULT_DEVIATION, help="peak FM deviation Hz")
    p.add_argument("--gain", type=float, default=default_gain, help="Pluto TX hardware gain dB")
    p.add_argument("--wpm", type=int, default=18)
    p.add_argument("--dry-run", action="store_true", help="Write IQ only; do not TX")
    p.add_argument("--repeat", type=int, default=2)
    p.add_argument("--with-tone", action="store_true")
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--stream-file", type=Path, default=None, help=argparse.SUPPRESS)
    args = p.parse_args(argv)

    assert_frequency(args.freq)
    gain = assert_tx_gain(args.gain, ceiling)

    if args.stream_file:
        path = args.stream_file
        if not path.is_absolute():
            path = ROOT / path
        return stream_file(path, args.freq, args.sample_rate, gain)

    tx = _hackrf_tx()
    callsign = tx.resolve_callsign(args.callsign)
    text, iq = build_iq(
        callsign,
        args.sample_rate,
        args.deviation,
        args.repeat,
        args.wpm,
        args.with_tone,
    )

    out_dir = args.out_dir or (ROOT / "reports" / "pluto" / "uv5r")
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Z0-9]", "", callsign)
    tag = f"{args.freq // 1000}khz_dev{int(args.deviation)}"
    iq_path = out_dir / f"tx_callsign_{safe}_{tag}.cf32"
    report_path = out_dir / f"tx_callsign_{safe}_{tag}_report.json"
    iq.tofile(iq_path)
    dur_s = len(iq) / args.sample_rate

    meta = {
        "at": datetime.now(timezone.utc).isoformat(),
        "board": "pluto",
        "callsign": callsign,
        "text": text,
        "freq_hz": args.freq,
        "mode": "FM Morse ID",
        "deviation_hz": args.deviation,
        "sample_rate": args.sample_rate,
        "gain_db": gain,
        "max_tx_db": ceiling,
        "duration_s": round(dur_s, 3),
        "samples": int(len(iq)),
        "file": str(iq_path),
        "with_tone": args.with_tone,
        "dry_run": args.dry_run,
    }
    print(json.dumps(meta, indent=2), flush=True)

    if args.dry_run:
        report_path.write_text(json.dumps({**meta, "status": "dry_run"}, indent=2) + "\n")
        return 0

    assert_loopback()
    print(
        f"TX {callsign} on {args.freq / 1e6:.3f} MHz for ~{dur_s:.1f}s "
        f"(gain={gain} dB, deviation={args.deviation} Hz).",
        flush=True,
    )
    completed = _docker_stream(iq_path, args.freq, args.sample_rate, gain)
    meta["status"] = "pass" if completed.returncode == 0 else "fail"
    meta["exit_code"] = completed.returncode
    report_path.write_text(json.dumps(meta, indent=2) + "\n")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
