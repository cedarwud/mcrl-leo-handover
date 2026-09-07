#!/usr/bin/env python3
"""Resume one Codex thread after an exact terminal model-capacity failure.

The watcher is intentionally quiet on ordinary runs.  It tails only new JSONL
records, ignores quoted/user/tool text, and reacts only to a terminal event_msg
whose structured error message matches the configured capacity sentence.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


TARGET_MESSAGE = "Selected model is at capacity. Please try a different model."
THREAD_ID = "01a02ee2-3a25-7c03-aa70-5ad81bdfb765"
WORKSPACE = Path("/home/u24/papers/mcrl-leo-handover")
ROLLOUT = Path(
    "/home/u24/.codex/sessions/2026/08/23/"
    "rollout-2026-08-23T21-49-33-01a02ee2-3a25-7c03-aa70-5ad81bdfb765.jsonl"
)
STATE = WORKSPACE / ".scratch/conversation-watch/state.json"
LOCK = WORKSPACE / ".scratch/conversation-watch/capacity_watch.lock"
CODEX = Path("/home/u24/.local/bin/codex")
RESUME_MESSAGE = (
    "請繼續。前一回合因 Selected model is at capacity 中止；"
    "請從最近已驗證狀態接續既定工作。"
)


def _read_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_state(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _capacity_terminal_event(record: dict[str, Any]) -> bool:
    if record.get("type") != "event_msg":
        return False
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return False

    # Capacity failures observed in Codex rollouts terminate a task and carry a
    # structured error.  Accept a few error-shaped event kinds, but never scan
    # arbitrary serialized text (which would match user quotes or tool inputs).
    event_type = payload.get("type")
    if event_type not in {
        "task_complete",
        "task_aborted",
        "task_failed",
        "turn_aborted",
        "turn_failed",
        "stream_error",
        "response_error",
        "error",
    }:
        return False
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
    elif isinstance(error, str):
        message = error
    else:
        message = payload.get("message")
    return isinstance(message, str) and message.strip() == TARGET_MESSAGE


def _task_started(record: dict[str, Any]) -> bool:
    return (
        record.get("type") == "event_msg"
        and isinstance(record.get("payload"), dict)
        and record["payload"].get("type") == "task_started"
    )


def _ordinal(record: dict[str, Any]) -> int:
    value = record.get("ordinal", -1)
    return value if isinstance(value, int) else -1


def _tail_records(path: Path, offset: int) -> tuple[list[dict[str, Any]], int]:
    size = path.stat().st_size
    if offset < 0 or offset > size:
        offset = 0
    records: list[dict[str, Any]] = []
    with path.open("rb") as handle:
        handle.seek(offset)
        while True:
            line_start = handle.tell()
            line = handle.readline()
            if not line:
                return records, handle.tell()
            if not line.endswith(b"\n"):
                # Do not consume a JSON record that is still being written.
                return records, line_start
            try:
                record = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(record, dict):
                records.append(record)


def _event_key(record: dict[str, Any]) -> str:
    material = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _queue_resume(codex: Path, dry_run: bool) -> subprocess.CompletedProcess[str]:
    command = [
        str(codex),
        "queue",
        "--thread",
        THREAD_ID,
        "--message",
        RESUME_MESSAGE,
        "-C",
        str(WORKSPACE),
    ]
    if dry_run:
        return subprocess.CompletedProcess(command, 0, stdout="dry-run", stderr="")
    return subprocess.run(
        command,
        cwd=WORKSPACE,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollout", type=Path, default=ROLLOUT)
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--lock", type=Path, default=LOCK)
    parser.add_argument("--codex", type=Path, default=CODEX)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    args.lock.parent.mkdir(parents=True, exist_ok=True)
    with args.lock.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        if not args.rollout.is_file():
            print(f"capacity-watch: rollout missing: {args.rollout}", file=sys.stderr)
            return 2

        state = _read_state(args.state)
        if "offset" not in state:
            # First run starts at EOF so historical failures and quoted text can
            # never cause an unsolicited resume.
            state = {
                "offset": args.rollout.stat().st_size,
                "pending": None,
                "last_triggered": None,
            }
            _write_state(args.state, state)
            return 0

        records, new_offset = _tail_records(args.rollout, int(state.get("offset", 0)))
        pending = state.get("pending") if isinstance(state.get("pending"), dict) else None

        for record in records:
            if _capacity_terminal_event(record):
                pending = {
                    "key": _event_key(record),
                    "ordinal": _ordinal(record),
                    "timestamp": record.get("timestamp"),
                    "attempts": 0,
                }
            elif pending is not None and _task_started(record):
                # A later task proves that this conversation already resumed.
                if _ordinal(record) > int(pending.get("ordinal", -1)):
                    pending = None

        state["offset"] = new_offset
        state["pending"] = pending

        if pending is None or pending.get("key") == state.get("last_triggered"):
            _write_state(args.state, state)
            return 0

        try:
            result = _queue_resume(args.codex, args.dry_run)
        except (OSError, subprocess.SubprocessError) as exc:
            pending["attempts"] = int(pending.get("attempts", 0)) + 1
            pending["last_error"] = str(exc)
            _write_state(args.state, state)
            print(f"capacity-watch: resume failed: {exc}", file=sys.stderr)
            return 3

        if result.returncode != 0:
            pending["attempts"] = int(pending.get("attempts", 0)) + 1
            pending["last_error"] = (result.stderr or result.stdout).strip()[-2000:]
            _write_state(args.state, state)
            print(
                f"capacity-watch: resume command exited {result.returncode}: "
                f"{pending['last_error']}",
                file=sys.stderr,
            )
            return result.returncode

        state["last_triggered"] = pending["key"]
        state["pending"] = None
        _write_state(args.state, state)
        print(
            "capacity-watch: queued resume for terminal capacity event "
            f"ordinal={pending.get('ordinal')}"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
