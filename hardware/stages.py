#!/usr/bin/env python3
"""HWIL staged bring-up. One target at a time, and only after the previous stage passed."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from harness.radboards import (
    ORDER,
    STAGES,
    load_board,
    primary_image_path,
    read_stages,
    run_report_dir,
    stage_passed,
    write_stage,
)
from hardware.probe import probe_board, probe_soapy
from software.fixture import run_fixture
from hardware.loopback import run_loopback, write_loopback_logs
from human.assent import LOOPBACK_ENV, SIM_ENV, confirm_tx, require_hardware

ROOT_HINT = "Run from the repo root so hardware/boards/ and reports/ resolve."


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


def _refuse(board_id, stage, reason, next_cmd):
    """Write a fail record for a gate/operator refusal, then exit."""
    board = {"id": board_id}
    try:
        board = load_board(board_id)
    except SystemExit:
        pass
    fail_record(board, stage, reason, next=next_cmd)
    raise SystemExit(reason)


def gate(board_id, stage):
    if board_id not in ORDER or stage not in STAGES:
        raise SystemExit(f"unknown target {board_id} {stage}. {ROOT_HINT}")
    if stage != "present" and not stage_passed(board_id, STAGES[STAGES.index(stage) - 1]):
        previous = STAGES[STAGES.index(stage) - 1]
        _refuse(
            board_id,
            stage,
            f"{board_id} {previous} stage has not passed; refusing {stage}",
            f"make stage BOARD={board_id} STAGE={previous}",
        )
    board = load_board(board_id)
    partner_id = board.get("partner_board")
    if stage == "image" and partner_id and not stage_passed(partner_id, "image"):
        _refuse(
            board_id,
            stage,
            f"{partner_id} image stage has not passed; refusing {board_id} {stage}",
            f"{LOOPBACK_ENV}=1 make hwil BOARD={partner_id}",
        )
    env_name = board.get("requires_env") or LOOPBACK_ENV
    if stage == "image" and os.environ.get(env_name) != "1":
        _refuse(
            board_id,
            stage,
            f"set {env_name}=1 before the image stage "
            "(attenuated TX↔RX cable path asserted by the operator)",
            f"{env_name}=1 make hwil BOARD={board_id}",
        )
    return board


def run_present(board):
    result = probe_board(board)
    if not result.ok and not result.usb_matches:
        return fail_record(
            board,
            "present",
            result.detail or "device not found",
            tool=result.tool,
            usb_matches=result.usb_matches,
            next=f"attach {board['id']} and re-run: make stage BOARD={board['id']} STAGE=present",
        )
    if not result.ok and result.usb_matches:
        return fail_record(
            board,
            "present",
            result.detail or "USB seen but probe failed",
            tool=result.tool,
            usb_matches=result.usb_matches,
            raw=result.raw[-1000:],
            next=f"fix USB permissions/driver, then: make stage BOARD={board['id']} STAGE=present",
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
    try:
        require_hardware(board)
    except SystemExit as exc:
        return fail_record(
            board,
            "workflow",
            str(exc),
            next=f"attach {board['id']}, then: make stage BOARD={board['id']} STAGE=workflow",
        )
    present = read_stages(board["id"])["stages"].get("present") or {}
    env_name = board.get("requires_env") or LOOPBACK_ENV
    loopback = {
        "env": env_name,
        "state": "set" if os.environ.get(env_name) == "1" else "not-set",
    }
    limits = {
        "txvga_db": board.get("txvga_db"),
        "max_tx_db": board.get("max_tx_db"),
        "max_tx_ms": board.get("max_tx_ms"),
        "center_hz": board.get("center_hz"),
    }
    driver = board.get("soapy_driver") or board["id"]
    # Device-open evidence comes from a container-side Soapy probe (the dev-host
    # never imports SoapySDR). Fall back to the CLI re-probe if it fails.
    probe = probe_soapy(driver)
    if not probe.ok:
        result = probe_board(board)
        if not result.ok:
            return fail_record(
                board,
                "workflow",
                probe.detail or "soapy probe failed",
                tool="SoapySDRUtil",
                probe=result.detail,
                next=f"fix Soapy/driver, then: make stage BOARD={board['id']} STAGE=workflow",
            )
        return pass_record(
            board,
            "workflow",
            tool=result.tool,
            device=present.get("device") or result.device_name,
            serial=present.get("serial") or result.serial,
            soapy_open="skipped",
            soapy_note=probe.detail,
            loopback=loopback,
            tx_limits=limits,
            image_paths={primary_image_path(board)["id"]: "ready"},
        )
    return pass_record(
        board,
        "workflow",
        tool="SoapySDRUtil",
        device=present.get("device") or probe.device_name or board.get("device_name"),
        serial=present.get("serial") or probe.serial,
        soapy_open="ok",
        loopback=loopback,
        tx_limits=limits,
        image_paths={primary_image_path(board)["id"]: "ready"},
    )


def run_image(board):
    simulate = os.environ.get(SIM_ENV) == "1"
    partner_id = board.get("partner_board")
    # Simulated image skips USB and YES; cable attestation still required (gate).
    if not simulate:
        try:
            require_hardware(board)
            if partner_id:
                require_hardware(load_board(partner_id))
        except SystemExit as exc:
            return fail_record(
                board,
                "image",
                str(exc),
                next=(
                    f"attach {board['id']}"
                    + (f" and {partner_id}" if partner_id else "")
                    + ", or run: "
                    f"{LOOPBACK_ENV}=1 {SIM_ENV}=1 make hwil BOARD={board['id']}"
                ),
            )
    out = run_report_dir(board["id"])
    try:
        fixture = run_fixture(board, out_dir=out)
    except Exception as exc:
        write_loopback_logs(out, [], failures=[f"fixture: {exc}"])
        return fail_record(board, "image", f"fixture failed: {exc}", report_dir=str(out))

    try:
        if not simulate:
            tx_desc = (
                f"attenuated cross-board TX↔RX loopback ({board['id']}↔{partner_id})"
                if partner_id
                else f"attenuated TX→RX loopback on {board['id']}"
            )
            confirm_tx(f"{tx_desc} (conducted cable only; no antenna)")
        records = run_loopback(board, simulate=simulate)
    except SystemExit as exc:
        write_loopback_logs(out, [], failures=[str(exc)])
        return fail_record(
            board,
            "image",
            str(exc),
            report_dir=str(out),
            fixture=fixture,
            next=f"{LOOPBACK_ENV}=1 make hwil BOARD={board['id']}",
        )
    except Exception as exc:
        write_loopback_logs(out, [], failures=[str(exc)])
        return fail_record(
            board,
            "image",
            str(exc),
            report_dir=str(out),
            fixture=fixture,
            next=(
                "check attenuator/cable and gains; see report_dir, then "
                f"{LOOPBACK_ENV}=1 make hwil BOARD={board['id']}"
            ),
        )
    write_loopback_logs(out, records)
    (out / "image_summary.json").write_text(
        json.dumps({"fixture": fixture, "loopback": records}, indent=2) + "\n"
    )
    return pass_record(
        board,
        "image",
        device=read_stages(board["id"])["stages"].get("present", {}).get("device"),
        report_dir=str(out),
        loopback=records,
        fixture=fixture,
        simulated=simulate,
        image_paths={primary_image_path(board)["id"]: "ready"},
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run one HWIL bring-up stage for one board")
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
