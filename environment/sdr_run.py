# Standalone SDR entrypoint. Everything runs inside rad-lab-sdr.
#
# Usage:
#   python3 -m environment.sdr_run --usb hackrf_info
#   make sdr SRC="python3 hardware/labs/03_rx_capture.py"
#
# Environment:
#   HUMAN_LOOPBACK=1    (required for TX)
#   HUMAN_TX_CONFIRM=1  (scripted YES)
#   RAD_LAB_HWIL_SIM=1  (software-only image stage)

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from environment.container import docker_prefix  # noqa: E402
from hardware.probe import hardware_present  # noqa: E402
from human.assent import confirm_tx, require_loopback  # noqa: E402
from harness.radboards import load_board  # noqa: E402

TX_COMMANDS = frozenset({"hackrf_transfer"})
TX_LABS = frozenset(
    {
        "04_tx_callsign_fm.py",
        "06_pluto_tx_callsign_fm.py",
        "07_crossboard_915_cw.py",
    }
)


def _is_tx_command(cmd: list[str]) -> bool:
    if cmd and cmd[0] in TX_COMMANDS:
        return True
    for token in cmd:
        if token.endswith(".py") and Path(token).name in TX_LABS:
            return True
    return False


def sdr_command(argv: list[str], *, usb: bool = False) -> list[str]:
    return docker_prefix(
        usb=usb, mounts=[f"{ROOT}:/work"], workdir="/work"
    ) + list(argv)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    usb = "--usb" in argv
    cmd = [a for a in argv if a != "--usb"]
    if not cmd:
        print(__doc__)
        return 0
    if cmd[0] == "lsusb":
        return subprocess.run(cmd).returncode
    if len(cmd) == 1 and " " in cmd[0]:
        cmd = shlex.split(cmd[0])

    if usb:
        present = False
        for board_id in ("hackrf", "pluto"):
            try:
                board = load_board(board_id)
            except SystemExit:
                continue
            if hardware_present(board):
                present = True
                break
        if not present:
            print(
                "refusing --usb: no HackRF or Pluto found on USB. "
                "Run `make stage BOARD=<board> STAGE=present` to check.",
                file=sys.stderr,
            )
            return 1
        if _is_tx_command(cmd):
            require_loopback("SDR TX via " + " ".join(cmd))
            confirm_tx(
                "SDR TX via "
                + " ".join(cmd)
                + " (attenuator cable TX→RX; no antenna)"
            )

    docker_cmd = sdr_command(cmd, usb=usb)
    print("$", " ".join(shlex.quote(c) for c in docker_cmd))
    return subprocess.run(docker_cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
