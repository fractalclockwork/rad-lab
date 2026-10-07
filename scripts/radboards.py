"""Load board manifests and stage records."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ORDER = ("hackrf", "pluto")
STAGES = ("present", "workflow", "image")
# Cataloged accessories are documented but not accepted by make stage.
ACCESSORIES = ("amp", "splitter", "analyzer", "usb-vga-dac")


def board_path(board_id):
    path = ROOT / "boards" / f"{board_id}.yaml"
    if not path.is_file():
        raise SystemExit(f"unknown board {board_id}")
    return path


def load_board(board_id):
    data = yaml.safe_load(board_path(board_id).read_text())
    data["id"] = board_id
    return data


def stage_path(board_id):
    return ROOT / "reports" / board_id / "stage.json"


def read_stages(board_id):
    path = stage_path(board_id)
    if not path.is_file():
        return {"board": board_id, "stages": {}}
    return json.loads(path.read_text())


def write_stage(board_id, stage, record):
    document = read_stages(board_id)
    document["board"] = board_id
    document.setdefault("stages", {})[stage] = record
    path = stage_path(board_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n")
    return document


def stage_passed(board_id, stage):
    record = read_stages(board_id)["stages"].get(stage) or {}
    return record.get("status") == "pass"


def primary_image_path(board):
    for path in board.get("image_paths") or []:
        if path.get("primary"):
            return path
    raise SystemExit(f"{board['id']} has no primary image path")
