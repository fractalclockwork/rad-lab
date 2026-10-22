#!/usr/bin/env python3
"""Lab 02: probe the first Soapy HackRF (or report how to attach one)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
ROOT = REPO_ROOT

from harness.radboards import load_board  # noqa: E402
from hardware.probe import probe_board  # noqa: E402
from harness.ready import require_rf  # noqa: E402


def main():
    require_rf("hackrf")
    board = load_board("hackrf")
    result = probe_board(board)
    print(f"ok={result.ok} tool={result.tool} serial={result.serial or '-'}")
    print(result.detail)
    if result.usb_matches:
        print("usb:")
        for line in result.usb_matches:
            print(" ", line)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
