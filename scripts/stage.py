#!/usr/bin/env python3
"""Staged bring-up. One target at a time, and only after the previous stage passed."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from radboards import (
    ORDER,
    STAGES,
    load_board,
    primary_image_path,
    read_stages,
    stage_passed,
    write_stage,
)
from devices import probe_board, open_soapy_device
from fixture import run_fixture
from hil import run_loopback_hil, write_hil_logs

ROOT = Path(__file__).resolve().parents[1]
ROOT_HINT = "Run from the repo root so boards/ and reports/ resolve."


def now():
    return datetime.now(timezone.utc).isoformat()


def fail_record(board, stage, reason, **extra):
    record = {"status": "fail", "stage": stage, "reason": reason, "at": now()}
    record.update(extra)
    write_stage(board["id"], stage, record)
    print(reason, file=sys.stderr)
    return 1


def pass_record(board, stage, **extra):
    record = {"status": "pass", "stage": stage, "at": now()}
    record.update(extra)
    write_stage(board["id"], stage, record)
    print(json.dumps(record, indent=2))
    return 0


def gate(board_id, stage):
    if board_id not in ORDER or stage not in STAGES:
        raise SystemExit(f"unknown target {board_id} {stage}. {ROOT_HINT}")
    if stage != "present" and not stage_passed(board_id, STAGES[STAGES.index(stage) - 1]):
        previous = STAGES[STAGES.index(stage) - 1]
        raise SystemExit(
            f"{board_id} {previous} stage has not passed; refusing {stage}"
        )
    if board_id != "hackrf" and not stage_passed("hackrf", "image"):
        raise SystemExit(
            f"hackrf image stage has not passed; refusing {board_id} {stage}"
        )
    board = load_board(board_id)
    env_name = board.get("requires_env")
    if stage == "image" and env_name and os.environ.get(env_name) != "1":
        raise SystemExit(
            f"set {env_name}=1 before the image stage "
            "(attenuated TX↔RX cable path asserted by the operator)"
        )
    return board


def run_dir(board_id):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = ROOT / "reports" / board_id / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_present(board):
    result = probe_board(board)
    if not result.ok and not result.usb_matches:
        return fail_record(
            board,
            "present",
            result.detail or "device not found",
            tool=result.tool,
            usb_matches=result.usb_matches,
        )
    if not result.ok and result.usb_matches:
        return fail_record(
            board,
            "present",
            result.detail or "USB seen but probe failed",
            tool=result.tool,
            usb_matches=result.usb_matches,
            raw=result.raw[-1000:],
        )
    return pass_record(
        board,
        "present",
        tool=result.tool,
        device=result.device_name or board.get("device_name"),
        serial=result.serial,
        usb_matches=result.usb_matches,
        image_paths={primary_image_path(board)["id"]: "not-run"},
    )


def run_workflow(board):
    present = read_stages(board["id"])["stages"].get("present") or {}
    env_name = board.get("requires_env")
    loopback = {
        "env": env_name,
        "state": "set" if env_name and os.environ.get(env_name) == "1" else "not-set",
    }
    limits = {
        "txvga_db": board.get("txvga_db"),
        "max_tx_db": board.get("max_tx_db"),
        "max_tx_ms": board.get("max_tx_ms"),
        "center_hz": board.get("center_hz"),
    }
    driver = board.get("soapy_driver") or board["id"]
    device, error = open_soapy_device(driver)
    if error:
        # Host may only have CLI tools; re-probe is enough for workflow if present passed.
        result = probe_board(board)
        if not result.ok:
            return fail_record(
                board,
                "workflow",
                error,
                tool="SoapySDR",
                probe=result.detail,
            )
        return pass_record(
            board,
            "workflow",
            tool=result.tool,
            device=present.get("device") or result.device_name,
            serial=present.get("serial") or result.serial,
            soapy_open="skipped",
            soapy_note=error,
            loopback=loopback,
            tx_limits=limits,
            image_paths={primary_image_path(board)["id"]: "ready"},
        )
    # Soft close — Soapy devices do not always expose close().
    try:
        del device
    except Exception:
        pass
    return pass_record(
        board,
        "workflow",
        tool="SoapySDR",
        device=present.get("device") or board.get("device_name"),
        serial=present.get("serial"),
        soapy_open="ok",
        loopback=loopback,
        tx_limits=limits,
        image_paths={primary_image_path(board)["id"]: "ready"},
    )


def run_image(board):
    out = run_dir(board["id"])
    try:
        fixture = run_fixture(board, out_dir=out)
    except Exception as exc:
        write_hil_logs(out, [], failures=[f"fixture: {exc}"])
        return fail_record(board, "image", f"fixture failed: {exc}", report_dir=str(out))

    simulate = os.environ.get("RAD_LAB_HIL_SIM") == "1"
    try:
        records = run_loopback_hil(board, simulate=simulate)
    except Exception as exc:
        write_hil_logs(out, [], failures=[str(exc)])
        return fail_record(
            board,
            "image",
            str(exc),
            report_dir=str(out),
            fixture=fixture,
        )
    write_hil_logs(out, records)
    (out / "image_summary.json").write_text(
        json.dumps({"fixture": fixture, "hil": records}, indent=2) + "\n"
    )
    return pass_record(
        board,
        "image",
        device=read_stages(board["id"])["stages"].get("present", {}).get("device"),
        report_dir=str(out),
        hil=records,
        fixture=fixture,
        simulated=simulate,
        image_paths={primary_image_path(board)["id"]: "ready"},
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run one bring-up stage for one board")
    parser.add_argument("--board", required=True)
    parser.add_argument("--stage", required=True, choices=STAGES)
    args = parser.parse_args(argv)
    board = gate(args.board, args.stage)
    if args.stage == "present":
        return run_present(board)
    if args.stage == "workflow":
        return run_workflow(board)
    return run_image(board)


if __name__ == "__main__":
    raise SystemExit(main())
