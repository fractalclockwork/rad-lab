#!/usr/bin/env python3
"""Generate FM IQ of a Morse callsign for HackRF TX (short ID burst).

Callsign is never hardcoded. Set it with --callsign or RAD_LAB_CALLSIGN.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CALLSIGN_ENV = "RAD_LAB_CALLSIGN"

MORSE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    " ": " ",
    "/": "-..-.",
}


def sanitize_callsign(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9/]", "", value.strip().upper())
    if not cleaned or not re.search(r"[A-Z]", cleaned) or not re.search(r"[0-9]", cleaned):
        raise SystemExit(
            f"invalid callsign {value!r}: use letters and a digit "
            f"(set --callsign or {CALLSIGN_ENV})"
        )
    return cleaned


def resolve_callsign(cli_value: str | None) -> str:
    raw = (cli_value or "").strip() or os.environ.get(CALLSIGN_ENV, "").strip()
    if not raw:
        raise SystemExit(
            f"callsign required: pass --callsign YOURCALL or export {CALLSIGN_ENV}=YOURCALL"
        )
    return sanitize_callsign(raw)


def morse_audio(text: str, sample_rate: int, wpm: int = 18) -> np.ndarray:
    """Baseband audio (real) for Morse; unit = dit duration."""
    unit = 1.2 / wpm  # seconds per dit
    tone_hz = 700.0
    pieces = []
    for ch in text.upper():
        code = MORSE.get(ch)
        if code is None:
            continue
        if code == " ":
            pieces.append(np.zeros(int(sample_rate * unit * 7), dtype=np.float32))
            continue
        for sym in code:
            dur = unit if sym == "." else unit * 3
            n = int(sample_rate * dur)
            t = np.arange(n, dtype=np.float32) / sample_rate
            pieces.append(0.8 * np.sin(2 * np.pi * tone_hz * t).astype(np.float32))
            pieces.append(np.zeros(int(sample_rate * unit), dtype=np.float32))
        pieces.append(np.zeros(int(sample_rate * unit * 2), dtype=np.float32))
    pad = np.zeros(int(sample_rate * 0.3), dtype=np.float32)
    return np.concatenate([pad, *pieces, pad]) if pieces else pad


def fm_modulate(audio: np.ndarray, sample_rate: int, deviation_hz: float) -> np.ndarray:
    """Complex baseband FM from real audio in [-1, 1]."""
    audio = np.clip(audio.astype(np.float64), -1.0, 1.0)
    phase = np.cumsum(2 * np.pi * deviation_hz * audio / sample_rate)
    return (np.exp(1j * phase) * 0.7).astype(np.complex64)


def to_cs8(iq: np.ndarray) -> np.ndarray:
    i = np.clip(np.round(iq.real * 127.0), -127, 127).astype(np.int8)
    q = np.clip(np.round(iq.imag * 127.0), -127, 127).astype(np.int8)
    out = np.empty(i.size * 2, dtype=np.int8)
    out[0::2] = i
    out[1::2] = q
    return out


def main():
    p = argparse.ArgumentParser(
        description="TX Morse callsign on FM via HackRF",
        epilog=f"Callsign: --callsign YOURCALL or export {CALLSIGN_ENV}=YOURCALL",
    )
    p.add_argument(
        "--callsign",
        default=None,
        help=f"Station callsign (or set {CALLSIGN_ENV}; no default)",
    )
    p.add_argument("--freq", type=int, default=446_500_000)
    p.add_argument("--sample-rate", type=int, default=2_000_000)
    p.add_argument(
        "--deviation",
        type=float,
        default=2500.0,
        help="peak FM deviation Hz (2500 narrow / 5000 wide)",
    )
    p.add_argument("--txvga", type=int, default=0, help="HackRF TX VGA 0-47; default 0")
    p.add_argument("--amp", type=int, default=0, choices=(0, 1), help="RF amp; leave 0")
    p.add_argument("--wpm", type=int, default=18)
    p.add_argument("--dry-run", action="store_true", help="Write IQ only; do not TX")
    p.add_argument("--repeat", type=int, default=2, help="How many times to send the callsign")
    p.add_argument(
        "--with-tone",
        action="store_true",
        help="Prefix/suffix a 1 kHz tone for easier squelch checks",
    )
    args = p.parse_args()

    callsign = resolve_callsign(args.callsign)

    if args.txvga > 20:
        print("refusing txvga > 20 for lab ID bursts; lower --txvga", file=sys.stderr)
        return 1

    text = " ".join([callsign] * max(1, args.repeat))
    audio_sr = 48_000
    audio = morse_audio(text, audio_sr, wpm=args.wpm)
    if args.with_tone:
        t = np.arange(int(audio_sr * 2.0), dtype=np.float32) / audio_sr
        tone = 0.7 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        audio = np.concatenate([tone, audio, tone[: audio_sr // 2]])

    n_rf = int(len(audio) * args.sample_rate / audio_sr)
    x_old = np.linspace(0, 1, num=len(audio), endpoint=False)
    x_new = np.linspace(0, 1, num=n_rf, endpoint=False)
    audio_rf = np.interp(x_new, x_old, audio).astype(np.float32)
    iq = fm_modulate(audio_rf, args.sample_rate, args.deviation)
    cs8 = to_cs8(iq)

    out_dir = ROOT / "reports" / "hackrf" / "uv5r"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Z0-9]", "", callsign)
    tag = f"{args.freq // 1000}khz_dev{int(args.deviation)}"
    iq_path = out_dir / f"tx_callsign_{safe}_{tag}.cs8"
    report_path = out_dir / f"tx_callsign_{safe}_{tag}_report.json"
    cs8.tofile(iq_path)
    dur_s = len(iq) / args.sample_rate

    meta = {
        "at": datetime.now(timezone.utc).isoformat(),
        "callsign": callsign,
        "text": text,
        "freq_hz": args.freq,
        "mode": "FM Morse ID",
        "deviation_hz": args.deviation,
        "sample_rate": args.sample_rate,
        "txvga": args.txvga,
        "amp": args.amp,
        "duration_s": round(dur_s, 3),
        "samples": int(len(iq)),
        "file": str(iq_path.relative_to(ROOT)),
        "with_tone": args.with_tone,
        "dry_run": args.dry_run,
    }
    print(json.dumps(meta, indent=2), flush=True)

    if args.dry_run:
        report_path.write_text(json.dumps({**meta, "status": "dry_run"}, indent=2) + "\n")
        return 0

    cmd = [
        "docker",
        "run",
        "--rm",
        "--privileged",
        "-v",
        "/dev/bus/usb:/dev/bus/usb",
        "-v",
        f"{ROOT}:/work",
        "-w",
        "/work",
        "rad-lab-sdr",
        "hackrf_transfer",
        "-t",
        str(iq_path.relative_to(ROOT)),
        "-f",
        str(args.freq),
        "-s",
        str(args.sample_rate),
        "-x",
        str(args.txvga),
        "-a",
        str(args.amp),
    ]
    print(
        f"TX {callsign} on {args.freq/1e6:.3f} MHz for ~{dur_s:.1f}s "
        f"(txvga={args.txvga}, amp={args.amp}, deviation={args.deviation} Hz).",
        flush=True,
    )
    completed = subprocess.run(cmd, text=True)
    meta["status"] = "pass" if completed.returncode == 0 else "fail"
    meta["exit_code"] = completed.returncode
    report_path.write_text(json.dumps(meta, indent=2) + "\n")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
