"""USB / Soapy / IIO probing for present and workflow stages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from environment.container import run_text, usb_matches


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
    vendor = str(board.get("usb_vendor", "")).lower()
    product = str(board.get("usb_product", "")).lower()
    matches = usb_matches(vendor, product) if vendor and product else []
    board_id = board["id"]
    if board_id == "hackrf":
        result = probe_hackrf_info()
        if not result.ok:
            result = probe_soapy(board.get("soapy_driver") or "hackrf")
    elif board_id == "pluto":
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


def hardware_present(board):
    vendor = str(board.get("usb_vendor", "")).lower()
    product = str(board.get("usb_product", "")).lower()
    if not vendor or not product:
        return False
    return bool(usb_matches(vendor, product))
