#!/usr/bin/env python3
"""TX FM Morse callsign via ADALM-PLUTO (conducted path only).

Callsign is never hardcoded. Set it with --callsign or RAD_LAB_CALLSIGN.

Actual TX requires HUMAN_LOOPBACK=1 (operator asserts Pluto TX into an
attenuator and a 50 ohm load, or into another RX through that pad).
No antenna. National calling channels are refused.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
ROOT = REPO_ROOT
from environment.container import docker_prefix, require_container  # noqa: E402
from human.assent import (  # noqa: E402
    CALLSIGN_ENV,
    LOOPBACK_ENV,
    TX_CONFIRM_ENV,
    clamp_tx_gain,
    require_loopback,
    require_tx,
    resolve_callsign,
)
from harness.radboards import load_board  # noqa: E402
from harness.ready import require_rf  # noqa: E402
from software.dsp.common import build_callsign_fm_iq  # noqa: E402

CALLING_HZ = {146_520_000, 446_000_000}
DEFAULT_FREQ = 146_550_000
DEFAULT_DEVIATION = 5000.0
DEFAULT_RATE = 2_000_000


# Tests and callers still use these names.
def assert_loopback():
    require_loopback("Pluto TX (attenuator on the TX SMA; no antenna)")


def assert_frequency(freq: int):
    if int(freq) in CALLING_HZ:
        raise SystemExit(
            f"refusing calling channel {int(freq)} Hz "
            "(146.520 and 446.000 are not lab frequencies)"
        )


def assert_tx_gain(requested: float, ceiling: float) -> float:
    return clamp_tx_gain({"max_tx_db": ceiling, "txvga_db": requested}, requested)


def build_iq(callsign: str, sample_rate: int, deviation_hz: float, repeat: int, wpm: int, with_tone: bool):
    return build_callsign_fm_iq(
        callsign,
        sample_rate,
        deviation_hz,
        repeat=repeat,
        wpm=wpm,
        with_tone=with_tone,
    )


def stream_file(path: Path, freq: int, sample_rate: int, gain_db: float):
    """Transmit one CF32 file on Pluto TX. Used inside rad-lab-sdr."""
    require_container("hardware/labs/06_pluto_tx_callsign_fm.py")
    import SoapySDR  # type: ignore
    from SoapySDR import SOAPY_SDR_CF32, SOAPY_SDR_TX  # type: ignore

    assert_frequency(freq)
    board = load_board("pluto")
    gain_db = require_tx(
        board,
        "Pluto FM TX (conducted path only: attenuator or 50 Ω load; no antenna)",
        gain=gain_db,
    )

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
    cmd = docker_prefix(
        usb=True,
        mounts=[f"{ROOT}:/work"],
        workdir="/work",
        env={LOOPBACK_ENV: "1", TX_CONFIRM_ENV: "1"},
    ) + [
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

    callsign = resolve_callsign(args.callsign)
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

    require_rf("pluto")
    require_tx(
        board,
        "Pluto FM Morse ID burst "
        "(conducted path only: attenuator or 50 Ω load; no antenna)",
        gain=gain,
    )
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
