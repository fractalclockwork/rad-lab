#!/usr/bin/env python3
"""SPI-flash HackRF firmware from the archived release, then verify."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from devices import IMAGE_NAME, docker_image_exists, parse_hackrf_info, run_text
from radboards import ROOT, load_board

FIRMWARE_ENV = "HIL_FIRMWARE"


def now():
    return datetime.now(timezone.utc).isoformat()


def run_dir(board_id):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = ROOT / "reports" / board_id / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_firmware_version(text):
    match = re.search(r"Firmware Version:\s*([^\s(]+)", text)
    return match.group(1) if match else ""


def probe_info():
    code, text = run_text(["hackrf_info"], usb=True)
    serial, board = parse_hackrf_info(text)
    version = parse_firmware_version(text)
    return {
        "ok": code == 0 and "No HackRF boards found" not in text and bool(serial or version),
        "code": code,
        "serial": serial,
        "board": board,
        "firmware": version,
        "raw": text,
        "tool_host": shutil.which("hackrf_info") or f"docker:{IMAGE_NAME}",
    }


def normalize_serial(value):
    return re.sub(r"[^0-9a-fA-F]", "", value or "").lower()


def serials_match(expected, actual):
    a = normalize_serial(expected)
    b = normalize_serial(actual)
    if not a or not b:
        return False
    # Allow short form (trailing unique nibbles) or full 32-hex form.
    return a == b or a.endswith(b) or b.endswith(a)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def firmware_bin_path(board):
    rel = board.get("firmware_bin_path")
    if not rel:
        raise SystemExit("board YAML missing firmware_bin_path")
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(
            f"missing firmware image {path}; run make archive "
            f"(release id {board.get('firmware_release_id')})"
        )
    return path


def run_spiflash(bin_path):
    argv = ["hackrf_spiflash", "-w", str(bin_path)]
    if shutil.which("hackrf_spiflash") is None:
        if not docker_image_exists():
            raise SystemExit(
                f"hackrf_spiflash not on PATH and {IMAGE_NAME} missing; run make image"
            )
        # Mount repo so the binary path is visible at the same absolute path.
        argv = (
            [
                "docker",
                "run",
                "--rm",
                "--privileged",
                "-v",
                "/dev/bus/usb:/dev/bus/usb",
                "-v",
                f"{ROOT}:{ROOT}",
                "-w",
                str(ROOT),
                IMAGE_NAME,
            ]
            + argv
        )
    completed = subprocess.run(argv, text=True, capture_output=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output


def expected_serial(board):
    return os.environ.get("HACKRF_SERIAL") or board.get("expected_serial") or ""


def verify(board, out=None, require_target=True):
    target = board.get("firmware_target") or ""
    probe = probe_info()
    record = {
        "status": "fail",
        "at": now(),
        "target": target,
        "probe": {
            "ok": probe["ok"],
            "serial": probe["serial"],
            "firmware": probe["firmware"],
            "board": probe["board"],
            "tool_host": probe["tool_host"],
        },
    }
    if not probe["ok"]:
        record["reason"] = "HackRF not found"
        if out:
            write_json(out / "firmware.json", record)
        print(probe["raw"][-1000:], file=sys.stderr)
        print(record["reason"], file=sys.stderr)
        return 1, record

    want = expected_serial(board)
    if want and not serials_match(want, probe["serial"]):
        record["reason"] = (
            f"serial mismatch: expected {want}, saw {probe['serial']}"
        )
        if out:
            write_json(out / "firmware.json", record)
        print(record["reason"], file=sys.stderr)
        return 1, record

    if require_target and target and target not in probe["firmware"]:
        record["reason"] = (
            f"firmware {probe['firmware']} does not match target {target}"
        )
        if out:
            write_json(out / "firmware.json", record)
        print(record["reason"], file=sys.stderr)
        return 1, record

    record["status"] = "pass"
    if out:
        write_json(out / "firmware.json", record)
        write_json(ROOT / "reports" / board["id"] / "firmware_stage.json", record)
    print(json.dumps(record, indent=2))
    return 0, record


def flash(board):
    if os.environ.get(FIRMWARE_ENV) != "1":
        raise SystemExit(
            f"set {FIRMWARE_ENV}=1 before flashing "
            "(operator asserts the correct HackRF One is on USB)"
        )
    if not docker_image_exists() and shutil.which("hackrf_spiflash") is None:
        raise SystemExit(f"run make image so {IMAGE_NAME} provides 2026.01.3 tools")

    out = run_dir(board["id"])
    pre = probe_info()
    write_json(
        out / "firmware_pre.json",
        {
            "at": now(),
            "serial": pre["serial"],
            "firmware": pre["firmware"],
            "board": pre["board"],
            "raw": pre["raw"],
            "ok": pre["ok"],
        },
    )
    if not pre["ok"]:
        print(pre["raw"][-1000:], file=sys.stderr)
        raise SystemExit("HackRF not found before flash")

    want = expected_serial(board)
    if want and not serials_match(want, pre["serial"]):
        raise SystemExit(
            f"refusing flash: expected serial {want}, saw {pre['serial']}"
        )

    target = board.get("firmware_target") or ""
    if target and target in (pre["firmware"] or ""):
        print(
            f"DUT already reports firmware {pre['firmware']}; skipping SPI write",
            flush=True,
        )
        return verify(board, out=out, require_target=True)[0]

    bin_path = firmware_bin_path(board)
    print(f"writing {bin_path}", flush=True)
    code, output = run_spiflash(bin_path)
    write_json(
        out / "firmware_flash.json",
        {
            "at": now(),
            "bin": str(bin_path.relative_to(ROOT)),
            "exit_code": code,
            "output": output[-4000:],
        },
    )
    print(output, flush=True)
    if code != 0:
        raise SystemExit(f"hackrf_spiflash failed with exit {code}")

    print(
        "\nSPI write complete. Press RESET on the HackRF (or unplug/replug USB), "
        "then re-run: make firmware BOARD=hackrf  (or --verify-only)\n",
        flush=True,
    )
    # Brief settle; full verify may still see old image until RESET.
    time.sleep(1.0)
    post = probe_info()
    write_json(
        out / "firmware_post_prereset.json",
        {
            "at": now(),
            "serial": post["serial"],
            "firmware": post["firmware"],
            "note": "may still show old firmware until RESET",
            "raw": post["raw"],
        },
    )
    if target and target in (post["firmware"] or ""):
        return verify(board, out=out, require_target=True)[0]

    pending = {
        "status": "pending_reset",
        "at": now(),
        "pre_firmware": pre["firmware"],
        "post_prereset_firmware": post["firmware"],
        "target": target,
        "serial": pre["serial"],
        "report_dir": str(out),
        "next": "RESET the DUT, then: make firmware BOARD=hackrf (verify)",
    }
    write_json(out / "firmware.json", pending)
    write_json(ROOT / "reports" / board["id"] / "firmware_stage.json", pending)
    print(json.dumps(pending, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Flash or verify HackRF firmware")
    parser.add_argument("--board", default="hackrf")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Probe and require firmware_target; do not write SPI",
    )
    args = parser.parse_args(argv)
    if args.board != "hackrf":
        raise SystemExit("firmware flash is only implemented for BOARD=hackrf")
    board = load_board(args.board)
    if args.verify_only:
        out = run_dir(board["id"])
        code, _ = verify(board, out=out, require_target=True)
        return code
    # Default: if already at target, verify; else flash (needs HIL_FIRMWARE=1).
    probe = probe_info()
    target = board.get("firmware_target") or ""
    if (
        probe["ok"]
        and target
        and target in (probe["firmware"] or "")
        and (
            not expected_serial(board)
            or serials_match(expected_serial(board), probe["serial"])
        )
    ):
        out = run_dir(board["id"])
        code, _ = verify(board, out=out, require_target=True)
        return code
    return flash(board)


if __name__ == "__main__":
    raise SystemExit(main())
