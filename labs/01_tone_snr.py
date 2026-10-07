#!/usr/bin/env python3
"""Lab 01: measure SNR of a synthetic complex tone (no hardware)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from radboards import load_board  # noqa: E402
from fixture import run_fixture  # noqa: E402


def main():
    board = load_board("hackrf")
    result = run_fixture(board)
    print(f"status={result['status']} snr_db={result['metrics']['snr_db']:.2f}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
