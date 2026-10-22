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

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
ROOT = REPO_ROOT
from environment.container import docker_prefix  # noqa: E402
from human.assent import (  # noqa: E402
    CALLSIGN_ENV,
    clamp_tx_gain,
    require_tx,
    resolve_callsign,
    sanitize_callsign,
)
from harness.radboards import load_board  # noqa: E402
from harness.ready import require_rf  # noqa: E402
from software.dsp.common import (  # noqa: E402
    MORSE,
    build_callsign_fm_iq,
    fm_modulate,
    morse_audio,
    to_cs8,
)


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
    board = load_board("hackrf")
    try:
        txvga = clamp_tx_gain(board, args.txvga)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    args.txvga = int(txvga)

    text, iq = build_callsign_fm_iq(
        callsign,
        args.sample_rate,
        args.deviation,
        repeat=args.repeat,
        wpm=args.wpm,
        with_tone=args.with_tone,
    )
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

    require_rf("hackrf")
    require_tx(
        board,
        "HackRF FM Morse ID burst (attenuator cable TX→RX; no antenna)",
        gain=args.txvga,
    )

    cmd = docker_prefix(
        usb=True, mounts=[f"{ROOT}:/work"], workdir="/work"
    ) + [
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
