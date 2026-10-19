"""USB / Soapy / hackrf_info probing helpers for present and workflow stages."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


HACKRF_USB = ("1d50", "6089")
PLUTO_USB = ("0456", "b673")

# SDR toolchain binaries that MUST run inside the rad-lab-sdr image so the
# dev-host never directly exercises RF hardware. Anything disallowed here is a
# host-side utility (e.g. lsusb) or a container build/manifest step.
SDR_BINARIES = {
    "hackrf_info",
    "hackrf_spiflash",
    "hackrf_transfer",
    "SoapySDRUtil",
    "iio_info",
    "iio_attr",
    "dfu-util",
}


def is_sdr_binary(name):
    if name in ("lsusb",):
        return False  # informational USB enumeration only; host-side, no RF touched
    return name in SDR_BINARIES


@dataclass
class ProbeResult:
    ok: bool
    tool: str
    device_name: str = ""
    serial: str = ""
    detail: str = ""
    usb_matches: list = field(default_factory=list)
    raw: str = ""


IMAGE_NAME = "rad-lab-sdr"


def docker_image_exists():
    completed = subprocess.run(
        ["docker", "image", "inspect", IMAGE_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def docker_prefix(usb=False, mounts=(), workdir=None):
    prefix = ["docker", "run", "--rm", "-e", "RAD_LAB_CONTAINER=1"]
    if usb:
        prefix.extend(["--privileged", "-v", "/dev/bus/usb:/dev/bus/usb"])
    for mount in mounts:
        prefix.extend(["-v", mount])
    if workdir:
        prefix.extend(["-w", workdir])
    prefix.append(IMAGE_NAME)
    return prefix


def run_text(argv, timeout=30, usb=False):
    """Run SDR tooling ONLY inside the rad-lab-sdr container.

    Returns ``(returncode, combined_output)``. SDR runtime (hackrf_info/
    hackrf_spiflash/hackrf_transfer/SoapySDRUtil/iio_info/iio_attr/dfu-util) is
    never executed on the dev-host. The dev-host remains the control plane for
    orchestration plus informational, non-RF utilities: `lsusb` (kernel USB
    enumeration only) and report-file writing.
    """
    argv = list(argv)
    if is_sdr_binary(argv[0]):
        # Unconditionally containerized: the dev-host never executes SDR
        # toolchain binaries, even when they exist on the host PATH.
        argv = docker_prefix(usb=usb) + argv
    # Host-side utility (e.g. lsusb): informational, no RF.
    completed = subprocess.run(argv, text=True, capture_output=True, timeout=timeout)
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def lsusb_text():
    code, text = run_text(["lsusb"])
    if code != 0:
        return ""
    return text


def usb_matches(vendor, product, text=None):
    text = text if text is not None else lsusb_text()
    needle = f"{vendor}:{product}".lower()
    return [line for line in text.splitlines() if needle in line.lower()]


def parse_hackrf_info(text):
    serial = ""
    board = ""
    for line in text.splitlines():
        if "Serial number" in line or "Serial Number" in line:
            serial = line.split(":", 1)[-1].strip()
        if "Board ID Number" in line or "Firmware Version" in line:
            board = board or line.strip()
        if "Found HackRF" in line:
            board = line.strip()
    return serial, board


def probe_hackrf_info():
    code, text = run_text(["hackrf_info"], usb=True)
    if code != 0:
        return ProbeResult(ok=False, tool="hackrf_info", detail=text[-500:], raw=text)
    if "No HackRF boards found" in text or "hackrf_open() failed" in text:
        return ProbeResult(ok=False, tool="hackrf_info", detail="no HackRF found", raw=text)
    serial, board = parse_hackrf_info(text)
    return ProbeResult(
        ok=True,
        tool="hackrf_info",
        device_name=board or "HackRF One",
        serial=serial,
        detail="hackrf_info ok",
        raw=text,
    )


def _soapy_missing(text):
    lowered = text.lower()
    return (
        "no devices found" in lowered
        or "probe failed" in lowered
        or "no hackrf device" in lowered
        or "error probing device" in lowered
        or "no pluto" in lowered
    )


def probe_soapy(driver="hackrf"):
    code, text = run_text(["SoapySDRUtil", f"--probe=driver={driver}"], usb=True)
    if code != 0:
        # Older util uses different flag forms.
        code, text = run_text(
            ["SoapySDRUtil", "--probe", f"driver={driver}"], usb=True
        )
    if _soapy_missing(text):
        return ProbeResult(ok=False, tool="SoapySDRUtil", detail="no device", raw=text)
    if code != 0:
        return ProbeResult(ok=False, tool="SoapySDRUtil", detail=text[-500:], raw=text)
    serial = ""
    match = re.search(r"hw_serial\s*[:=]\s*([^\s,]+)", text, re.IGNORECASE)
    if match:
        serial = match.group(1)
    else:
        match = re.search(r"(?<![_\w])serial\s*[:=]\s*([^\s,]+)", text, re.IGNORECASE)
        if match:
            serial = match.group(1)
    name = driver
    fw_match = re.search(r"fw_version\s*[:=]\s*([^\s,]+)", text, re.IGNORECASE)
    if fw_match:
        name = f"{driver} {fw_match.group(1)}"
    return ProbeResult(
        ok=True,
        tool="SoapySDRUtil",
        device_name=name,
        serial=serial,
        detail="soapy probe ok",
        raw=text,
    )


def probe_iio_pluto():
    """Probe ADALM-PLUTO via libiio (`iio_info -s` + context attrs)."""
    code, text = run_text(["iio_info", "-s"], usb=True)
    uri = ""
    for line in text.splitlines():
        match = re.search(r"\b((?:usb|ip|local):[^\s,]+)", line)
        if match and (
            "pluto" in line.lower()
            or "0456" in line.lower()
            or "ad936" in line.lower()
            or "analog devices" in line.lower()
        ):
            uri = match.group(1)
            break
    if not uri and code == 0:
        match = re.search(r"\b((?:usb|ip|local):[^\s,]+)", text)
        if match:
            uri = match.group(1)
    if not uri:
        return ProbeResult(ok=False, tool="iio_info", detail="no Pluto IIO context", raw=text)

    fw = ""
    serial = ""
    code_a, fw_text = run_text(["iio_attr", "-u", uri, "-C", "fw_version"], usb=True)
    if code_a == 0 and fw_text.strip():
        fw = fw_text.strip().split(":")[-1].strip()
    code_s, ser_text = run_text(["iio_attr", "-u", uri, "-C", "hw_serial"], usb=True)
    if code_s == 0 and ser_text.strip():
        serial = ser_text.strip().split(":")[-1].strip()
    return ProbeResult(
        ok=True,
        tool="iio_info",
        device_name=f"ADALM-PLUTO {fw}".strip(),
        serial=serial,
        detail=f"uri={uri} fw={fw or '?'}",
        raw=text + "\n" + fw_text + "\n" + ser_text,
    )


def probe_board(board):
    """Prefer hackrf_info for HackRF; IIO then Soapy for Pluto; always record lsusb."""
    vendor = str(board.get("usb_vendor", "")).lower()
    product = str(board.get("usb_product", "")).lower()
    matches = usb_matches(vendor, product) if vendor and product else []
    board_id = board["id"]
    if board_id == "hackrf":
        result = probe_hackrf_info()
        if not result.ok:
            result = probe_soapy(board.get("soapy_driver") or "hackrf")
    elif board_id == "pluto":
        # Soapy first: more reliable than iio_info -s when Avahi/scan is busy.
        result = probe_soapy(board.get("soapy_driver") or "plutosdr")
        if not result.ok:
            result = probe_iio_pluto()
    else:
        result = probe_soapy(board.get("soapy_driver") or board_id)
    result.usb_matches = matches
    if not result.ok and not matches:
        result.detail = result.detail or "device not present on USB"
    elif not result.ok and matches:
        result.detail = (
            result.detail
            or "USB match present but tool probe failed (permissions or driver)"
        )
    return result


def in_container():
    """True when running inside rad-lab-sdr (env marker or Docker/Podman sentinel)."""
    if os.environ.get("RAD_LAB_CONTAINER") == "1":
        return True
    return Path("/.dockerenv").exists() or Path("/.containerenv").exists()


def require_container(tool):
    """Refuse host-side SDR software execution; all SDR runs go through rad-lab-sdr."""
    if in_container():
        return
    raise SystemExit(
        f"{tool} must run inside the rad-lab-sdr container, never on the dev-host. "
        'Use: make sdr SRC="python3 hil/labs/<lab>.py" '
        "or: python3 hil/scripts/sdr_run.py <binary|script>"
    )


def hardware_present(board):
    """True when the board's VID:PID shows up on the host USB bus (lsusb only)."""
    vendor = str(board.get("usb_vendor", "")).lower()
    product = str(board.get("usb_product", "")).lower()
    if not vendor or not product:
        return False
    return bool(usb_matches(vendor, product))


def require_hardware(board):
    """Refuse to proceed when the board is not visible on USB.

    Host-side lsusb only — no docker, no RF touched. Print the VID:PID we looked
    for, what lsusb actually saw, and the software-only escape hatch so the
    operator can recover without guessing.
    """
    vendor = str(board.get("usb_vendor", "")).lower()
    product = str(board.get("usb_product", "")).lower()
    board_id = board.get("id", board)
    seen = lsusb_text()
    matches = usb_matches(vendor, product, seen) if vendor and product else []
    if matches:
        return
    lines = [
        f"{board_id}: device not present on USB (looking for {vendor}:{product})",
        "    refused to proceed — no SDR hardware detected.",
    ]
    if seen.strip():
        lines.append("    lsusb output:")
        for line in seen.strip().splitlines():
            lines.append(f"        {line}")
    else:
        lines.append("    lsusb returned nothing (or is unavailable).")
    lines.extend(
        [
            "    Software-only escape hatch:",
            "        RAD_LAB_HIL_SIM=1 HIL_LOOPBACK=1 make hil BOARD=" + str(board_id),
            "        make sim BOARD=" + str(board_id),
        ]
    )
    raise SystemExit("\n".join(lines))


TX_CONFIRM_ENV = "HIL_TX_CONFIRM"


def confirm_tx(reason):
    """Require explicit operator confirmation before any TX.

    Order of precedence:
      1. HIL_TX_CONFIRM=1   — scripted/CI escape hatch; documents human assent.
      2. TTY present        — interactive YES prompt.
      3. Otherwise          — refuse. Fail closed so agents/CI cannot invent assent.
    """
    if os.environ.get(TX_CONFIRM_ENV) == "1":
        return
    if sys.stdin.isatty():
        prompt = (
            f"TX about to start: {reason}\n"
            "Confirm an attenuator or antenna is connected (TX will radiate or drive "
            "a conducted cable). Type YES to proceed: "
        )
        try:
            answer = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nTX aborted.", file=sys.stderr)
            raise SystemExit(1)
        if answer.strip() != "YES":
            print("TX aborted (confirmation not 'YES').", file=sys.stderr)
            raise SystemExit(1)
        return
    raise SystemExit(
        f"refusing TX ({reason}): no TTY and {TX_CONFIRM_ENV} not set. "
        f"Set {TX_CONFIRM_ENV}=1 (scripted) or run interactively to confirm TX."
    )
