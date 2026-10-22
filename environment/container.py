"""Host vs container boundary for the rad-lab-sdr toolchain.

Environment builds argv and runs docker. It never keys RF by itself;
human assent and hardware stages decide when TX is allowed.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

IMAGE_NAME = "rad-lab-sdr"

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
        return False
    return name in SDR_BINARIES


def docker_image_exists():
    completed = subprocess.run(
        ["docker", "image", "inspect", IMAGE_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def docker_prefix(usb=False, mounts=(), workdir=None, env=()):
    prefix = ["docker", "run", "--rm", "-e", "RAD_LAB_CONTAINER=1"]
    if isinstance(env, dict):
        for k, v in env.items():
            prefix.extend(["-e", f"{k}={v}"])
    else:
        for item in env:
            prefix.extend(["-e", str(item)])
    if usb:
        prefix.extend(["--privileged", "-v", "/dev/bus/usb:/dev/bus/usb"])
    for mount in mounts:
        prefix.extend(["-v", mount])
    if workdir:
        prefix.extend(["-w", workdir])
    prefix.append(IMAGE_NAME)
    return prefix


def run_text(argv, timeout=30, usb=False):
    """Run SDR tooling ONLY inside rad-lab-sdr; lsusb stays host-side."""
    argv = list(argv)
    if is_sdr_binary(argv[0]):
        argv = docker_prefix(usb=usb) + argv
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


def in_container():
    if os.environ.get("RAD_LAB_CONTAINER") == "1":
        return True
    return Path("/.dockerenv").exists() or Path("/.containerenv").exists()


def require_container(tool):
    if in_container():
        return
    raise SystemExit(
        f"{tool} must run inside the rad-lab-sdr container, never on the dev-host. "
        'Use: make sdr SRC="python3 hardware/labs/<lab>.py" '
        "or: python3 -m environment.sdr_run <binary|script>"
    )
