"""Stage-record gates for RF labs and lessons."""

from __future__ import annotations

from harness.radboards import ORDER, stage_passed


def _next_command(board_id: str, stage: str) -> str:
    if stage == "image":
        return f"HUMAN_LOOPBACK=1 make hwil BOARD={board_id}"
    return f"make stage BOARD={board_id} STAGE={stage}"


def require_rf(board_id: str) -> None:
    if stage_passed(board_id, "image"):
        return
    for stage in ("present", "workflow", "image"):
        if not stage_passed(board_id, stage):
            raise SystemExit(
                f"{board_id} {stage} stage has not passed; "
                f"refusing RF lab. Next: {_next_command(board_id, stage)}"
            )
    raise SystemExit(
        f"{board_id} image stage has not passed; "
        f"refusing RF lab. Next: {_next_command(board_id, 'image')}"
    )


def require_lessons() -> None:
    for board_id in ORDER:
        if stage_passed(board_id, "image"):
            continue
        for stage in ("present", "workflow", "image"):
            if not stage_passed(board_id, stage):
                raise SystemExit(
                    f"{board_id} {stage} stage has not passed; "
                    f"refusing lesson lab. Finish hardware bring-up first. "
                    f"Next: {_next_command(board_id, stage)}"
                )
        raise SystemExit(
            f"{board_id} image stage has not passed; "
            f"refusing lesson lab. Next: {_next_command(board_id, 'image')}"
        )
