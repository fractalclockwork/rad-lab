"""USB / Soapy / hackrf_info probing helpers for present and workflow stages."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field


HACKRF_USB = ("1d50", "6089")
PLUTO_USB = ("0456", "b673")


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


def docker_prefix(usb=False):
    prefix = ["docker", "run", "--rm"]
    if usb:
        prefix.extend(["--privileged", "-v", "/dev/bus/usb:/dev/bus/usb"])
    prefix.append(IMAGE_NAME)
    return prefix


def run_text(argv, timeout=30, usb=False):
    """Run argv on the host, or inside rad-lab-sdr when the binary is missing."""
    if shutil.which(argv[0]) is None:
        if docker_image_exists():
            argv = docker_prefix(usb=usb) + list(argv)
        else:
            return (
                127,
                f"{argv[0]} not on PATH and {IMAGE_NAME} image is not built "
                "(run make image)",
            )
    completed = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
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
    match = re.search(r"serial\s*[:=]\s*([^\s,]+)", text, re.IGNORECASE)
    if match:
        serial = match.group(1)
    return ProbeResult(
        ok=True,
        tool="SoapySDRUtil",
        device_name=driver,
        serial=serial,
        detail="soapy probe ok",
        raw=text,
    )


def probe_board(board):
    """Prefer hackrf_info for HackRF; fall back to Soapy; always record lsusb."""
    vendor = str(board.get("usb_vendor", "")).lower()
    product = str(board.get("usb_product", "")).lower()
    matches = usb_matches(vendor, product) if vendor and product else []
    board_id = board["id"]
    if board_id == "hackrf":
        result = probe_hackrf_info()
        if not result.ok:
            result = probe_soapy(board.get("soapy_driver") or "hackrf")
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


def open_soapy_device(driver):
    """Return (device, None) or (None, error). Soft dependency on SoapySDR Python."""
    try:
        import SoapySDR  # type: ignore
    except ImportError as exc:
        return None, f"SoapySDR Python bindings unavailable: {exc}"
    try:
        devices = SoapySDR.Device.enumerate(dict(driver=driver))
        if not devices:
            return None, f"no Soapy devices for driver={driver}"
        return SoapySDR.Device(devices[0]), None
    except Exception as exc:  # noqa: BLE001 — surface to stage record
        return None, str(exc)
