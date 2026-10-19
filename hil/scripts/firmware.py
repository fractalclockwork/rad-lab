#!/usr/bin/env python3
"""Flash or verify board firmware (HackRF SPI, Pluto USB mass-storage)."""

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

from devices import IMAGE_NAME, docker_image_exists, parse_hackrf_info, require_hardware, run_text
from radboards import ROOT, load_board

FIRMWARE_ENV = "HIL_FIRMWARE"


def now():
    return datetime.now(timezone.utc).isoformat()


def run_dir(board_id):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = ROOT / "reports" / board_id / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def normalize_serial(value):
    return re.sub(r"[^0-9a-fA-F]", "", value or "").lower()


def serials_match(expected, actual):
    a = normalize_serial(expected)
    b = normalize_serial(actual)
    if not a or not b:
        return False
    return a == b or a.endswith(b) or b.endswith(a)


def firmware_versions_match(target, actual):
    """Loose match: 'v0.39' vs '0.39' vs strings containing the target."""
    if not target:
        return True
    if not actual:
        return False
    t = target.strip().lower()
    a = actual.strip().lower()
    if t in a or a in t:
        return True
    t_stripped = t.lstrip("v")
    a_stripped = a.lstrip("v")
    return t_stripped == a_stripped or t_stripped in a_stripped


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


def firmware_dfu_path(board):
    rel = board.get("firmware_dfu_path")
    if not rel:
        return None
    path = ROOT / rel
    return path if path.is_file() else None


# --- HackRF -----------------------------------------------------------------


def parse_firmware_version(text):
    match = re.search(r"Firmware Version:\s*([^\s(]+)", text)
    return match.group(1) if match else ""


def probe_hackrf():
    code, text = run_text(["hackrf_info"], usb=True)
    serial, board = parse_hackrf_info(text)
    version = parse_firmware_version(text)
    return {
        "ok": code == 0 and "No HackRF boards found" not in text and bool(serial or version),
        "code": code,
        "serial": serial,
        "board": board,
        "firmware": version,
        "uri": "",
        "raw": text,
        "tool_host": f"docker:{IMAGE_NAME}",  # SDR toolchain runs only in the container
    }


def expected_serial_hackrf(board):
    return os.environ.get("HACKRF_SERIAL") or board.get("expected_serial") or ""


def run_spiflash(bin_path):
    """SPI-flash HackRF firmware — always inside rad-lab-sdr (never host-side)."""
    if not docker_image_exists():
        raise SystemExit(f"{IMAGE_NAME} image missing; run make image")
    argv = (
        [
            "docker",
            "run",
            "--rm",
            "-e",
            "RAD_LAB_CONTAINER=1",
            "--privileged",
            "-v",
            "/dev/bus/usb:/dev/bus/usb",
            "-v",
            f"{ROOT}:{ROOT}",
            "-w",
            str(ROOT),
            IMAGE_NAME,
        ]
        + ["hackrf_spiflash", "-w", str(bin_path)]
    )
    completed = subprocess.run(argv, text=True, capture_output=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output


# --- Pluto ------------------------------------------------------------------


def parse_iio_contexts(text):
    """Parse `iio_info -s` lines into (uri, description) pairs."""
    contexts = []
    for line in text.splitlines():
        # e.g. "    0: 0456:b673 (Analog Devices PlutoSDR ...), usb:1.2.5"
        match = re.search(r"\(([^)]*)\).*?\b((?:usb|ip|local):[^\s,]+)", line)
        if match:
            contexts.append({"description": match.group(1).strip(), "uri": match.group(2)})
            continue
        match = re.search(r"\b((?:usb|ip|local):[^\s,]+)", line)
        if match and ("pluto" in line.lower() or "0456" in line.lower() or "ad936" in line.lower()):
            contexts.append({"description": line.strip(), "uri": match.group(1)})
    return contexts


def iio_attr_context(uri, attr):
    code, text = run_text(["iio_attr", "-u", uri, "-C", attr], usb=True)
    if code != 0:
        return ""
    # Output forms: "fw_version: v0.39" or just "v0.39"
    text = text.strip()
    if ":" in text:
        return text.split(":", 1)[-1].strip()
    return text.splitlines()[-1].strip() if text else ""


def probe_pluto_soapy():
    """Fallback when `iio_info -s` fails (Avahi / device busy): Soapy probe text."""
    # Do NOT wrap with the host `timeout` binary. run_text() executes
    # SoapySDRUtil inside the rad-lab-sdr container by argv[0] allowlist; a host
    # `timeout` prefix would match as argv[0] and run on the host instead (where
    # SoapySDRUtil is absent). run_text already enforces its own subprocess
    # timeout, so a stuck libiio scan still cannot hang the agent.

    def _soapy(argv):
        try:
            return run_text(argv, usb=True, timeout=30)
        except subprocess.TimeoutExpired:
            return 124, "timeout"

    code, text = _soapy(["SoapySDRUtil", "--probe=driver=plutosdr"])
    if code != 0 or (
        "Opening PlutoSDR" not in text and "driver=PlutoSDR" not in text
    ):
        code2, text2 = _soapy(["SoapySDRUtil", "--probe", "driver=plutosdr"])
        if code2 == 0 or "fw_version" in text2:
            code, text = code2, text2
    fw = ""
    serial = ""
    uri = ""
    match = re.search(r"fw_version\s*=\s*(\S+)", text)
    if match:
        fw = match.group(1)
    match = re.search(r"hw_serial\s*=\s*(\S+)", text)
    if match:
        serial = match.group(1)
    match = re.search(r"uri\s*=\s*(\S+)", text)
    if match:
        uri = match.group(1)
    ok = bool(fw or serial) and "no devices" not in text.lower()
    return {
        "ok": ok,
        "code": code,
        "serial": serial,
        "board": "ADALM-PLUTO",
        "firmware": fw,
        "uri": uri,
        "raw": text,
        "tool_host": f"docker:{IMAGE_NAME}",  # SDR toolchain runs only in the container
    }


def probe_pluto():
    code, text = run_text(["iio_info", "-s"], usb=True)
    contexts = parse_iio_contexts(text)
    pluto = None
    for ctx in contexts:
        desc = (ctx.get("description") or "").lower()
        if "pluto" in desc or "0456" in desc or "ad9361" in desc:
            pluto = ctx
            break
    if pluto is None and contexts:
        # Single USB IIO device is often the Pluto in a lab setting.
        pluto = contexts[0]
    if pluto is None:
        soapy = probe_pluto_soapy()
        if soapy["ok"]:
            soapy["raw"] = text + "\n" + soapy["raw"]
            return soapy
        return {
            "ok": False,
            "code": code,
            "serial": "",
            "board": "",
            "firmware": "",
            "uri": "",
            "raw": text + "\n" + soapy.get("raw", ""),
            "tool_host": f"docker:{IMAGE_NAME}",  # SDR toolchain runs only in the container
        }

    uri = pluto["uri"]
    fw = iio_attr_context(uri, "fw_version")
    serial = iio_attr_context(uri, "hw_serial")
    if not fw:
        # Some builds expose fw_version only in full iio_info dump.
        _, dump = run_text(["iio_info", "-u", uri], usb=True, timeout=60)
        match = re.search(r"fw_version:\s*(\S+)", dump)
        if match:
            fw = match.group(1)
        match = re.search(r"hw_serial:\s*(\S+)", dump)
        if match and not serial:
            serial = match.group(1)
        text = text + "\n" + dump[-2000:]

    if not fw and not serial:
        soapy = probe_pluto_soapy()
        if soapy["ok"]:
            soapy["raw"] = text + "\n" + soapy["raw"]
            return soapy

    return {
        "ok": bool(uri) and (bool(fw) or bool(serial) or code == 0),
        "code": code,
        "serial": serial,
        "board": pluto.get("description") or "ADALM-PLUTO",
        "firmware": fw,
        "uri": uri,
        "raw": text,
        "tool_host": f"docker:{IMAGE_NAME}",  # SDR toolchain runs only in the container
    }


def expected_serial_pluto(board):
    return os.environ.get("PLUTO_SERIAL") or board.get("expected_serial") or ""


def find_pluto_mounts():
    """Return Pluto USB mass-storage mounts (shallow scan under /media, /run/media)."""
    candidates = []
    # Only user media roots — never rglob all of /mnt (huge host trees).
    roots = []
    for base in (Path("/media"), Path("/run/media")):
        if base.is_dir():
            roots.append(base)
            for child in base.iterdir():
                if child.is_dir():
                    roots.append(child)
    for root in roots:
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        name = root.name.lower()
        if "pluto" in name:
            candidates.append(root)
            continue
        names = {p.name.lower() for p in entries}
        if "info.html" in names or "pluto.frm" in names or "license.html" in names:
            candidates.append(root)
            continue
        for path in entries:
            if path.is_dir() and "pluto" in path.name.lower():
                candidates.append(path)
    seen = set()
    out = []
    for path in candidates:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def eject_mount(path: Path):
    """Software-eject Pluto mass-storage so the DUT applies pluto.frm.

    Prefer unmount of the block device. Avoid udisksctl power-off — it can
    drop the whole composite USB device before the update finishes.
    """
    errors = []
    source = ""
    try:
        completed = subprocess.run(
            ["findmnt", "-n", "-o", "SOURCE", str(path)],
            text=True,
            capture_output=True,
        )
        if completed.returncode == 0:
            source = (completed.stdout or "").strip()
    except OSError:
        pass
    subprocess.run(["sync"], check=False)
    if source and shutil.which("udisksctl"):
        completed = subprocess.run(
            ["udisksctl", "unmount", "-b", source],
            text=True,
            capture_output=True,
        )
        errors.append((completed.stdout or "") + (completed.stderr or ""))
    elif shutil.which("umount"):
        completed = subprocess.run(
            ["umount", str(path)], text=True, capture_output=True
        )
        errors.append((completed.stdout or "") + (completed.stderr or ""))
    if shutil.which("eject") and source:
        completed = subprocess.run(
            ["eject", source], text=True, capture_output=True
        )
        errors.append((completed.stdout or "") + (completed.stderr or ""))
    subprocess.run(["sync"], check=False)
    return "\n".join(errors)


def flash_pluto_mass_storage(frm_path: Path):
    mounts = find_pluto_mounts()
    if not mounts:
        raise SystemExit(
            "Pluto USB mass-storage volume not mounted. "
            "Plug the DUT so it appears as PlutoSDR, then re-run with HIL_FIRMWARE=1. "
            "DFU recovery is only for after mass-storage flash failure "
            "(see hil/docs/boards/pluto.md)."
        )
    dest_dir = mounts[0]
    dest = dest_dir / "pluto.frm"
    shutil.copy2(frm_path, dest)
    eject_log = eject_mount(dest_dir)
    return {
        "mount": str(dest_dir),
        "dest": str(dest),
        "eject_log": eject_log[-2000:],
    }


def run_pluto_dfu(dfu_path: Path):
    """DFU recovery only — operator must put Pluto in DFU mode first.

    Always inside rad-lab-sdr (dfu-util is SDR toolchain; never host-side).
    """
    if not docker_image_exists():
        raise SystemExit(f"{IMAGE_NAME} image missing; run make image")
    argv = (
        [
            "docker",
            "run",
            "--rm",
            "-e",
            "RAD_LAB_CONTAINER=1",
            "--privileged",
            "-v",
            "/dev/bus/usb:/dev/bus/usb",
            "-v",
            f"{ROOT}:{ROOT}",
            "-w",
            str(ROOT),
            IMAGE_NAME,
        ]
        + [
            "dfu-util",
            "-d",
            "0456:b673,0456:b674",
            "-a",
            "0",
            "-D",
            str(dfu_path),
        ]
    )
    completed = subprocess.run(argv, text=True, capture_output=True)
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


# --- Shared verify / flash --------------------------------------------------


def probe_board_firmware(board):
    if board["id"] == "hackrf":
        return probe_hackrf()
    if board["id"] == "pluto":
        return probe_pluto()
    raise SystemExit(f"firmware probe not implemented for {board['id']}")


def expected_serial(board):
    if board["id"] == "hackrf":
        return expected_serial_hackrf(board)
    if board["id"] == "pluto":
        return expected_serial_pluto(board)
    return board.get("expected_serial") or ""


def verify(board, out=None, require_target=True):
    target = board.get("firmware_target") or ""
    probe = probe_board_firmware(board)
    record = {
        "status": "fail",
        "at": now(),
        "board_id": board["id"],
        "target": target,
        "probe": {
            "ok": probe["ok"],
            "serial": probe["serial"],
            "firmware": probe["firmware"],
            "board": probe["board"],
            "uri": probe.get("uri") or "",
            "tool_host": probe["tool_host"],
        },
    }
    if not probe["ok"]:
        record["reason"] = f"{board['id']} not found"
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

    if require_target and target and not firmware_versions_match(target, probe["firmware"]):
        record["reason"] = (
            f"firmware {probe['firmware']!r} does not match target {target!r}"
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


def flash_hackrf(board):
    if os.environ.get(FIRMWARE_ENV) != "1":
        raise SystemExit(
            f"set {FIRMWARE_ENV}=1 before flashing "
            "(operator asserts the correct HackRF One is on USB)"
        )
    if not docker_image_exists() and shutil.which("hackrf_spiflash") is None:
        raise SystemExit(f"run make image so {IMAGE_NAME} provides 2026.01.3 tools")

    out = run_dir(board["id"])
    pre = probe_hackrf()
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

    want = expected_serial_hackrf(board)
    if want and not serials_match(want, pre["serial"]):
        raise SystemExit(
            f"refusing flash: expected serial {want}, saw {pre['serial']}"
        )

    target = board.get("firmware_target") or ""
    if target and firmware_versions_match(target, pre["firmware"]):
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
    time.sleep(1.0)
    post = probe_hackrf()
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
    if target and firmware_versions_match(target, post["firmware"]):
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


def flash_pluto(board, use_dfu=False):
    if os.environ.get(FIRMWARE_ENV) != "1":
        raise SystemExit(
            f"set {FIRMWARE_ENV}=1 before flashing "
            "(operator asserts the correct ADALM-PLUTO is on USB)"
        )

    out = run_dir(board["id"])
    pre = probe_pluto()
    write_json(
        out / "firmware_pre.json",
        {
            "at": now(),
            "serial": pre["serial"],
            "firmware": pre["firmware"],
            "uri": pre.get("uri") or "",
            "board": pre["board"],
            "raw": pre["raw"][-4000:],
            "ok": pre["ok"],
        },
    )

    want = expected_serial_pluto(board)
    if pre["ok"] and want and not serials_match(want, pre["serial"]):
        raise SystemExit(
            f"refusing flash: expected serial {want}, saw {pre['serial']}"
        )

    target = board.get("firmware_target") or ""
    if (
        pre["ok"]
        and target
        and firmware_versions_match(target, pre["firmware"])
        and not use_dfu
    ):
        print(
            f"DUT already reports firmware {pre['firmware']}; skipping flash",
            flush=True,
        )
        return verify(board, out=out, require_target=True)[0]

    if use_dfu:
        dfu_path = firmware_dfu_path(board)
        if dfu_path is None:
            raise SystemExit("missing pluto.dfu; run make archive")
        print(f"DFU writing {dfu_path} (operator must have entered DFU mode)", flush=True)
        code, output = run_pluto_dfu(dfu_path)
        write_json(
            out / "firmware_flash.json",
            {
                "at": now(),
                "method": "dfu",
                "bin": str(dfu_path.relative_to(ROOT)),
                "exit_code": code,
                "output": output[-4000:],
            },
        )
        print(output, flush=True)
        if code != 0:
            raise SystemExit(f"dfu-util failed with exit {code}")
    else:
        frm_path = firmware_bin_path(board)
        print(f"copying {frm_path} to Pluto mass-storage", flush=True)
        try:
            flash_meta = flash_pluto_mass_storage(frm_path)
        except SystemExit:
            raise
        write_json(
            out / "firmware_flash.json",
            {
                "at": now(),
                "method": "mass_storage",
                "bin": str(frm_path.relative_to(ROOT)),
                **flash_meta,
            },
        )
        print(json.dumps(flash_meta, indent=2), flush=True)

    print(
        "\nFirmware update started. Wait for the blue LED to stop flashing "
        "(do not unplug). When Pluto remounts, re-run:\n"
        "  make firmware BOARD=pluto\n",
        flush=True,
    )
    time.sleep(2.0)
    post = probe_pluto()
    write_json(
        out / "firmware_post_prereset.json",
        {
            "at": now(),
            "serial": post["serial"],
            "firmware": post["firmware"],
            "uri": post.get("uri") or "",
            "note": "device may still be updating; re-verify after LED settles",
            "raw": post["raw"][-2000:],
        },
    )
    if target and firmware_versions_match(target, post.get("firmware") or ""):
        return verify(board, out=out, require_target=True)[0]

    pending = {
        "status": "pending_reboot",
        "at": now(),
        "pre_firmware": pre.get("firmware"),
        "post_prereset_firmware": post.get("firmware"),
        "target": target,
        "serial": pre.get("serial"),
        "report_dir": str(out),
        "next": "Wait for update LED, then: make firmware BOARD=pluto (verify). "
        "Use DFU only if mass-storage flash failed (hil/docs/boards/pluto.md).",
    }
    write_json(out / "firmware.json", pending)
    write_json(ROOT / "reports" / board["id"] / "firmware_stage.json", pending)
    print(json.dumps(pending, indent=2))
    return 0


def flash(board, use_dfu=False):
    # Firmware write touches hardware — the board must be present on USB first.
    require_hardware(board)
    if board["id"] == "hackrf":
        if use_dfu:
            raise SystemExit("HackRF DFU is manual recovery; see hil/docs/boards/hackrf.md")
        return flash_hackrf(board)
    if board["id"] == "pluto":
        return flash_pluto(board, use_dfu=use_dfu)
    raise SystemExit(f"firmware flash not implemented for {board['id']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Flash or verify SDR board firmware")
    parser.add_argument("--board", default="hackrf")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Probe and require firmware_target; do not write",
    )
    parser.add_argument(
        "--dfu",
        action="store_true",
        help="Pluto only: DFU recovery after mass-storage flash failure",
    )
    args = parser.parse_args(argv)
    if args.board not in {"hackrf", "pluto"}:
        raise SystemExit(f"firmware flash is only implemented for hackrf|pluto")
    board = load_board(args.board)
    if args.verify_only:
        out = run_dir(board["id"])
        code, _ = verify(board, out=out, require_target=True)
        return code
    probe = probe_board_firmware(board)
    target = board.get("firmware_target") or ""
    if (
        not args.dfu
        and probe["ok"]
        and target
        and firmware_versions_match(target, probe["firmware"])
        and (
            not expected_serial(board)
            or serials_match(expected_serial(board), probe["serial"])
        )
    ):
        out = run_dir(board["id"])
        code, _ = verify(board, out=out, require_target=True)
        return code
    return flash(board, use_dfu=args.dfu)


if __name__ == "__main__":
    raise SystemExit(main())
