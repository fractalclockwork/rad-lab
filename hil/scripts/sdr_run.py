# Standalone SDR entrypoint for the dev-host / students. Everything runs inside
# the rad-lab-sdr container (repo mounted at /work); the dev-host never executes
# SDR software. The container holds the reproducible SoapySDR / HackRF / libiio /
# Python DSP toolchain.
#
# Usage:
#   python3 hil/scripts/sdr_run.py --usb hackrf_info
#   python3 hil/scripts/sdr_run.py "hackrf_info"                # shlex-split
#   python3 hil/scripts/sdr_run.py --usb "python3 hil/labs/03_rx_capture.py"
#   python3 hil/scripts/sdr_run.py --usb hil/labs/07_crossboard_915_cw.py
#   python3 hil/scripts/sdr_run.py lsusb                        # host-side, informational
#
# `--usb` adds privileged /dev/bus/usb passthrough (needed for any hardware
# access). Environment:
#   HIL_LOOPBACK=1    (required for any image/loopback step; asserts the
#                       attenuated SMA TX->RX cable is in place)
#   HACKRF_SERIAL     (optional)
#   PLUTO_SERIAL      (optional)
#   RAD_LAB_HIL_SIM=1 (software-only image stage)

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE_NAME = "rad-lab-sdr"

# Imported from the sibling module so the presence / TX-confirm logic lives in
# one place (devices.py) and is shared with stage.py / firmware.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from devices import confirm_tx, hardware_present  # noqa: E402

# Commands that actually drive the RF front-end (TX). Anything else run with
# --usb (e.g. hackrf_info, SoapySDRUtil --probe) is presence-gated only.
TX_COMMANDS = ("hackrf_transfer",)


def _is_tx_lab(cmd: list[str]) -> bool:
    """True when argv targets a lab/script that transmits RF."""
    for token in cmd:
        if token.endswith(".py"):
            name = Path(token).name.lower()
            if "tx" in name or "crossboard" in name:
                return True
    return False


def _is_tx_command(cmd: list[str]) -> bool:
    return cmd[0] in TX_COMMANDS or _is_tx_lab(cmd)


def sdr_command(argv: list[str], *, usb: bool = False) -> list[str]:
    """Build the container command for an SDR binary or lab script.

    Everything runs inside rad-lab-sdr with the repo mounted at /work; the
    dev-host never executes SDR software. `usb=True` adds privileged
    /dev/bus/usb passthrough (needed for hackrf_*, iio_*, dfu-util).
    """
    prefix = ["docker", "run", "--rm", "-e", "RAD_LAB_CONTAINER=1"]
    if usb:
        prefix += ["--privileged", "-v", "/dev/bus/usb:/dev/bus/usb"]
    prefix += ["-v", f"{ROOT}:/work", "-w", "/work", IMAGE_NAME]
    return prefix + list(argv)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    if argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    # Accept and strip a --usb flag anywhere; it enables /dev/bus/usb passthrough.
    usb = "--usb" in argv
    cmd = [a for a in argv if a != "--usb"]
    if not cmd:
        print(__doc__)
        return 0
    if cmd[0] == "lsusb":
        # Informational USB enumeration stays on the host (no RF touched).
        completed = subprocess.run(cmd)
        return completed.returncode
    if len(cmd) == 1 and " " in cmd[0]:
        # A single quoted command string: shlex-split it into argv tokens.
        cmd = shlex.split(cmd[0])

    # --- hardware preflight -------------------------------------------------
    # With --usb the operator is asking to reach physical SDR hardware. Refuse
    # to launch the container unless the board is actually on the USB bus.
    if usb:
        hackrf = hardware_present({"id": "hackrf", "usb_vendor": "1d50", "usb_product": "6089"})
        pluto = hardware_present({"id": "pluto", "usb_vendor": "0456", "usb_product": "b673"})
        if not hackrf and not pluto:
            print(
                "refusing --usb: no HackRF (1d50:6089) or Pluto (0456:b673) "
                "found on USB. Run `make stage BOARD=<board> STAGE=present` "
                "to check, or omit --usb for host-side/informational commands.",
                file=sys.stderr,
            )
            return 1
        # Anything that keys the transmitter needs explicit operator assent.
        if _is_tx_command(cmd):
            confirm_tx(
                "SDR TX via " + " ".join(cmd)
                + " (attach an antenna for radiated TX, or an attenuator for "
                "a conducted path)"
            )

    docker_cmd = sdr_command(cmd, usb=usb)
    print("$", " ".join(shlex.quote(c) for c in docker_cmd))
    completed = subprocess.run(docker_cmd)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
