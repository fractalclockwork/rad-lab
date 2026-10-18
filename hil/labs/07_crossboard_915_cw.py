#!/usr/bin/env python3
"""HackRF↔Pluto simplex CW lab at 915 MHz (attenuated cable only).

Two directed legs, both must pass:
  1. HackRF TX → Pluto RX
  2. Pluto TX → HackRF RX

Uses the shared ISM CW tone from boards/*.yaml (100 kHz offset at 915 MHz).
Does not write stage.json. Requires HIL_LOOPBACK=1.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "hil" / "scripts"))
ROOT = REPO_ROOT

from fixture import measure_tone_snr  # noqa: E402
from radboards import load_board  # noqa: E402

LOOPBACK_ENV = "HIL_LOOPBACK"
IMAGE_NAME = "rad-lab-sdr"
PEAK_TOLERANCE_HZ = 5000.0
LEGS = (
    ("hackrf", "pluto", "Wire HackRF TX → attenuator → Pluto RX, then press Enter."),
    ("pluto", "hackrf", "Rewire Pluto TX → attenuator → HackRF RX, then press Enter."),
)


def assert_loopback():
    if os.environ.get(LOOPBACK_ENV) != "1":
        raise SystemExit(
            f"set {LOOPBACK_ENV}=1 before cross-board TX "
            "(attenuator on the cable; no antenna)"
        )


def clamp_tx_gain(board):
    requested = float(board.get("txvga_db", 0))
    ceiling = float(board.get("max_tx_db", requested))
    if requested > ceiling:
        raise SystemExit(
            f"txvga_db {requested} exceeds max_tx_db {ceiling}; refuse TX"
        )
    return requested


def shared_rf(tx_board, rx_board):
    keys = ("center_hz", "sample_rate", "tone_offset_hz")
    for key in keys:
        if float(tx_board[key]) != float(rx_board[key]):
            raise SystemExit(
                f"board RF mismatch on {key}: "
                f"tx={tx_board[key]} rx={rx_board[key]}"
            )
    return {
        "center_hz": int(tx_board["center_hz"]),
        "sample_rate": int(tx_board["sample_rate"]),
        "tone_offset_hz": float(tx_board["tone_offset_hz"]),
        "min_snr_db": max(
            float(tx_board.get("min_snr_db", 10.0)),
            float(rx_board.get("min_snr_db", 10.0)),
        ),
    }


def evaluate_leg(metrics, tone_offset_hz, min_snr_db, tolerance_hz=PEAK_TOLERANCE_HZ):
    """Pure pass/fail from measure_tone_snr metrics (no Soapy)."""
    snr_db = float(metrics["snr_db"])
    peak_hz = float(metrics["peak_hz"])
    snr_ok = snr_db >= float(min_snr_db)
    peak_ok = abs(peak_hz - float(tone_offset_hz)) <= float(tolerance_hz)
    return {
        "pass": bool(snr_ok and peak_ok),
        "snr_ok": bool(snr_ok),
        "peak_ok": bool(peak_ok),
        "snr_db": snr_db,
        "peak_hz": peak_hz,
        "tone_offset_hz": float(tone_offset_hz),
        "min_snr_db": float(min_snr_db),
        "tolerance_hz": float(tolerance_hz),
    }


def prompt_wire(message, stdin=None, no_prompt=False):
    print(message, file=sys.stderr)
    if no_prompt:
        print("Skipping cable prompt.", file=sys.stderr)
        return 0
    stream = sys.stdin if stdin is None else stdin
    if stream.readline() == "":
        print("EOF while waiting for cable confirm", file=sys.stderr)
        return 1
    return 0


def _open_soapy(board):
    import SoapySDR  # type: ignore

    driver = board.get("soapy_driver") or board["id"]
    devices = SoapySDR.Device.enumerate(dict(driver=driver))
    if not devices:
        raise SystemExit(f"no Soapy devices for driver={driver}")
    args = dict(devices[0])
    serial = str(args.get("serial") or args.get("label") or "")
    return SoapySDR.Device(devices[0]), serial, driver


def _set_rx_gain(dev, board):
    from SoapySDR import SOAPY_SDR_RX  # type: ignore

    if board["id"] == "hackrf":
        try:
            dev.setGain(SOAPY_SDR_RX, 0, "LNA", float(board.get("rx_lna_db", 16)))
            dev.setGain(SOAPY_SDR_RX, 0, "VGA", float(board.get("rx_vga_db", 16)))
        except Exception:
            dev.setGain(SOAPY_SDR_RX, 0, float(board.get("rx_lna_db", 16)))
    else:
        try:
            dev.setGain(SOAPY_SDR_RX, 0, float(board.get("rx_lna_db", 30)))
        except Exception:
            pass


def _set_tx_gain(dev, board, gain):
    from SoapySDR import SOAPY_SDR_TX  # type: ignore

    if board["id"] == "hackrf":
        try:
            dev.setGain(SOAPY_SDR_TX, 0, "VGA", gain)
        except Exception:
            dev.setGain(SOAPY_SDR_TX, 0, gain)
    else:
        dev.setGain(SOAPY_SDR_TX, 0, gain)


def run_leg_hardware(tx_id, rx_id):
    """TX on one board, RX on the other; score CW tone. Container entrypoint."""
    import SoapySDR  # type: ignore
    from SoapySDR import SOAPY_SDR_CF32, SOAPY_SDR_RX, SOAPY_SDR_TX  # type: ignore

    assert_loopback()
    tx_board = load_board(tx_id)
    rx_board = load_board(rx_id)
    rf = shared_rf(tx_board, rx_board)
    tx_gain = clamp_tx_gain(tx_board)
    max_tx_ms = int(tx_board.get("max_tx_ms", 200))
    rx_ms = int(rx_board.get("rx_ms", 400))
    sample_rate = float(rf["sample_rate"])
    center_hz = float(rf["center_hz"])
    tone_offset_hz = float(rf["tone_offset_hz"])
    min_snr = float(rf["min_snr_db"])

    tx_dev, tx_serial, tx_driver = _open_soapy(tx_board)
    rx_dev, rx_serial, rx_driver = _open_soapy(rx_board)

    tx_dev.setSampleRate(SOAPY_SDR_TX, 0, sample_rate)
    tx_dev.setFrequency(SOAPY_SDR_TX, 0, center_hz)
    _set_tx_gain(tx_dev, tx_board, tx_gain)

    rx_dev.setSampleRate(SOAPY_SDR_RX, 0, sample_rate)
    rx_dev.setFrequency(SOAPY_SDR_RX, 0, center_hz)
    _set_rx_gain(rx_dev, rx_board)

    n_tx = max(1024, int(sample_rate * max_tx_ms / 1000.0))
    n_rx = max(4096, int(sample_rate * rx_ms / 1000.0))
    t = np.arange(n_tx) / sample_rate
    tx_iq = (0.3 * np.exp(2j * np.pi * tone_offset_hz * t)).astype(np.complex64)
    rx_buf = np.zeros(n_rx, dtype=np.complex64)

    tx_stream = tx_dev.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)
    rx_stream = rx_dev.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
    started = time.monotonic()
    got = 0
    try:
        rx_dev.activateStream(rx_stream)
        tx_dev.activateStream(tx_stream)
        tx_mtu = min(n_tx, 1024 * 8)
        sent = 0
        while sent < n_tx:
            chunk = tx_iq[sent : sent + tx_mtu]
            sr = tx_dev.writeStream(tx_stream, [chunk], int(chunk.size))
            if sr.ret < 0:
                raise SystemExit(f"TX writeStream failed: {sr.ret}")
            if sr.ret == 0:
                if (time.monotonic() - started) * 1000 > max_tx_ms * 2:
                    raise SystemExit("TX timed out")
                continue
            sent += int(sr.ret)
            if (time.monotonic() - started) * 1000 > max_tx_ms * 2:
                break
        deadline = time.monotonic() + (rx_ms / 1000.0) + 1.0
        while got < n_rx and time.monotonic() < deadline:
            sr = rx_dev.readStream(rx_stream, [rx_buf[got:]], n_rx - got)
            if sr.ret > 0:
                got += int(sr.ret)
            elif sr.ret == -1:
                continue
            else:
                break
    finally:
        for close_dev, stream in ((tx_dev, tx_stream), (rx_dev, rx_stream)):
            try:
                close_dev.deactivateStream(stream)
                close_dev.closeStream(stream)
            except Exception:
                pass

    if got < 1024:
        raise SystemExit(f"RX captured only {got} samples")
    metrics = measure_tone_snr(rx_buf[:got], sample_rate, tone_offset_hz)
    verdict = evaluate_leg(metrics, tone_offset_hz, min_snr)
    result = {
        "status": "pass" if verdict["pass"] else "fail",
        "tx_board": tx_id,
        "rx_board": rx_id,
        "tx_driver": tx_driver,
        "rx_driver": rx_driver,
        "tx_serial": tx_serial,
        "rx_serial": rx_serial,
        "center_hz": int(center_hz),
        "sample_rate": int(sample_rate),
        "tone_offset_hz": tone_offset_hz,
        "tx_gain_db": tx_gain,
        "max_tx_ms": max_tx_ms,
        "rx_ms": rx_ms,
        "samples_rx": int(got),
        "elapsed_ms": round((time.monotonic() - started) * 1000.0, 2),
        "metrics": metrics,
        "verdict": verdict,
    }
    print(json.dumps(result))
    return 0 if verdict["pass"] else 1


def _parse_leg_json(stdout: str):
    lines = [ln.strip() for ln in (stdout or "").splitlines() if ln.strip()]
    for line in reversed(lines):
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise SystemExit(f"no leg JSON in docker stdout: {(stdout or '')[-500:]}")


def _docker_run_leg(tx_id, rx_id):
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
        "--run-leg",
        "--tx",
        tx_id,
        "--rx",
        rx_id,
    ]
    completed = subprocess.run(cmd, text=True, capture_output=True)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    if completed.returncode not in (0, 1):
        raise SystemExit(
            f"docker leg {tx_id}->{rx_id} failed ({completed.returncode}): "
            f"{(completed.stderr or completed.stdout or '')[-800:]}"
        )
    result = _parse_leg_json(completed.stdout)
    result["exit_code"] = completed.returncode
    return result


def main(argv=None):
    p = argparse.ArgumentParser(
        description="HackRF↔Pluto 915 MHz CW simplex (attenuated cable only)"
    )
    p.add_argument(
        "--run-leg",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p.add_argument("--tx", choices=("hackrf", "pluto"), default=None)
    p.add_argument("--rx", choices=("hackrf", "pluto"), default=None)
    p.add_argument(
        "--no-prompt",
        action="store_true",
        help="Skip cable-confirm prompts (scripted / tests)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Report directory (default reports/crossboard)",
    )
    args = p.parse_args(argv)

    if args.run_leg:
        if not args.tx or not args.rx:
            raise SystemExit("--run-leg requires --tx and --rx")
        if args.tx == args.rx:
            raise SystemExit("tx and rx boards must differ")
        return run_leg_hardware(args.tx, args.rx)

    assert_loopback()
    hackrf = load_board("hackrf")
    pluto = load_board("pluto")
    rf = shared_rf(hackrf, pluto)

    legs = []
    for tx_id, rx_id, message in LEGS:
        if prompt_wire(message, no_prompt=args.no_prompt) != 0:
            return 1
        print(f"Running leg {tx_id} TX → {rx_id} RX …", file=sys.stderr, flush=True)
        legs.append(_docker_run_leg(tx_id, rx_id))

    both_pass = all(leg.get("status") == "pass" for leg in legs)
    report = {
        "status": "pass" if both_pass else "fail",
        "at": datetime.now(timezone.utc).isoformat(),
        "mode": "crossboard_cw",
        "center_hz": rf["center_hz"],
        "sample_rate": rf["sample_rate"],
        "tone_offset_hz": rf["tone_offset_hz"],
        "min_snr_db": rf["min_snr_db"],
        "legs": legs,
        "note": (
            "Lesson lab; does not write stage.json. "
            "Pass when both HackRF→Pluto and Pluto→HackRF CW legs meet SNR and peak."
        ),
    }
    out_dir = args.out_dir or (ROOT / "reports" / "crossboard")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "915_cw_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if both_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
