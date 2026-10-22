"""Human-in-the-loop assent before hardware automation runs.

Agents must not invent YES, cable attestation, or DUT identity.
Only a person may set HUMAN_* flags or type YES at the prompt.
"""

from __future__ import annotations

import os
import re
import sys

from environment import container as env
from software.fixture import PEAK_TOLERANCE_HZ, assert_tone, evaluate_tone

LOOPBACK_ENV = "HUMAN_LOOPBACK"
TX_CONFIRM_ENV = "HUMAN_TX_CONFIRM"
FIRMWARE_ENV = "HUMAN_FIRMWARE"
SIM_ENV = "RAD_LAB_HWIL_SIM"
CALLSIGN_ENV = "RAD_LAB_CALLSIGN"


def sanitize_callsign(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9/]", "", value.strip().upper())
    if not cleaned or not re.search(r"[A-Z]", cleaned) or not re.search(r"[0-9]", cleaned):
        raise SystemExit(
            f"invalid callsign {value!r}: use letters and a digit "
            f"(set --callsign or {CALLSIGN_ENV})"
        )
    return cleaned


def resolve_callsign(cli_value: str | None) -> str:
    raw = (cli_value or "").strip() or os.environ.get(CALLSIGN_ENV, "").strip()
    if not raw:
        raise SystemExit(
            f"callsign required: pass --callsign YOURCALL or export {CALLSIGN_ENV}=YOURCALL"
        )
    return sanitize_callsign(raw)


def require_loopback(reason: str = "attenuated TX→RX cable; no antenna") -> None:
    if os.environ.get(LOOPBACK_ENV) != "1":
        raise SystemExit(
            f"set {LOOPBACK_ENV}=1 before TX ({reason}). "
            "Operator asserts the attenuator cable path is connected."
        )


def require_firmware(board) -> None:
    if os.environ.get(FIRMWARE_ENV) != "1":
        board_id = board.get("id", board) if isinstance(board, dict) else board
        raise SystemExit(
            f"set {FIRMWARE_ENV}=1 before firmware write for {board_id}. "
            "Operator asserts the correct DUT is on USB."
        )


def clamp_tx_gain(board, requested=None):
    if requested is None:
        requested = float(board.get("txvga_db", 0))
    else:
        requested = float(requested)
    ceiling = float(board.get("max_tx_db", requested))
    if requested > ceiling:
        raise SystemExit(
            f"txvga_db {requested} exceeds max_tx_db {ceiling}; refuse TX"
        )
    return requested


def confirm_tx(reason: str) -> None:
    """Require explicit operator confirmation before any TX."""
    if os.environ.get(TX_CONFIRM_ENV) == "1":
        return
    if sys.stdin.isatty():
        prompt = (
            f"TX about to start: {reason}\n"
            "Confirm an attenuator cable from TX to RX (no antenna). "
            f"Type YES to proceed, or set {TX_CONFIRM_ENV}=1 for a scripted run: "
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


def require_hardware(board, lsusb: str | None = None) -> None:
    """Refuse when the board's VID:PID is absent from host USB (lsusb only)."""
    vendor = str(board.get("usb_vendor", "")).lower()
    product = str(board.get("usb_product", "")).lower()
    board_id = board.get("id", board)
    seen = lsusb if lsusb is not None else env.lsusb_text()
    matches = env.usb_matches(vendor, product, seen) if vendor and product else []
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
            "    Software-only options:",
            f"        make sim BOARD={board_id}",
            f"        {LOOPBACK_ENV}=1 {SIM_ENV}=1 make hwil BOARD={board_id}",
        ]
    )
    raise SystemExit("\n".join(lines))


def require_tx(board, reason: str, gain=None, *, skip_confirm: bool = False):
    require_loopback(reason)
    gain_db = clamp_tx_gain(board, gain)
    if not skip_confirm:
        confirm_tx(reason)
    return gain_db


__all__ = [
    "CALLSIGN_ENV",
    "FIRMWARE_ENV",
    "LOOPBACK_ENV",
    "PEAK_TOLERANCE_HZ",
    "SIM_ENV",
    "TX_CONFIRM_ENV",
    "assert_tone",
    "clamp_tx_gain",
    "confirm_tx",
    "evaluate_tone",
    "require_firmware",
    "require_hardware",
    "require_loopback",
    "require_tx",
    "resolve_callsign",
    "sanitize_callsign",
]

