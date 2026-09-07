from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).with_name("capacity_watch.py")
SPEC = importlib.util.spec_from_file_location("capacity_watch", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
WATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCH)


def _capacity_record(ordinal: int = 10) -> dict:
    return {
        "timestamp": "2026-08-31T00:00:00Z",
        "ordinal": ordinal,
        "type": "event_msg",
        "payload": {
            "type": "task_complete",
            "error": {"message": WATCH.TARGET_MESSAGE},
        },
    }


def _started_record(ordinal: int = 11) -> dict:
    return {
        "timestamp": "2026-08-31T00:03:00Z",
        "ordinal": ordinal,
        "type": "event_msg",
        "payload": {"type": "task_started"},
    }


def _append(path: Path, *records: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def _run(tmp_path: Path, rollout: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--rollout",
            str(rollout),
            "--state",
            str(tmp_path / "state.json"),
            "--lock",
            str(tmp_path / "watch.lock"),
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_only_structured_terminal_event_matches() -> None:
    assert WATCH._capacity_terminal_event(_capacity_record())
    assert not WATCH._capacity_terminal_event(
        {
            "ordinal": 10,
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": WATCH.TARGET_MESSAGE}],
            },
        }
    )
    assert not WATCH._capacity_terminal_event(
        {
            "ordinal": 10,
            "type": "event_msg",
            "payload": {"type": "task_complete", "last_agent_message": WATCH.TARGET_MESSAGE},
        }
    )


def test_first_run_starts_at_eof_and_capacity_triggers_once(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    _append(rollout, {"ordinal": 1, "type": "event_msg", "payload": {"type": "task_started"}})
    first = _run(tmp_path, rollout)
    assert first.returncode == 0
    assert first.stdout == ""

    _append(rollout, _capacity_record())
    second = _run(tmp_path, rollout)
    assert second.returncode == 0
    assert "queued resume" in second.stdout

    third = _run(tmp_path, rollout)
    assert third.returncode == 0
    assert third.stdout == ""


def test_later_task_started_cancels_pending_resume(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.jsonl"
    _append(rollout, {"ordinal": 1, "type": "event_msg", "payload": {"type": "task_started"}})
    assert _run(tmp_path, rollout).returncode == 0

    _append(rollout, _capacity_record(), _started_record())
    result = _run(tmp_path, rollout)
    assert result.returncode == 0
    assert result.stdout == ""
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["pending"] is None
    assert state["last_triggered"] is None
