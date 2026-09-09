#!/usr/bin/env python3
"""Build or verify the frozen V0.23 C1/C2 successor 9000-world plan."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-world-plan-v1"
SPLIT = "TRAIN"
ARMS = ("FULL2", "DROP_C1", "DROP_C2", "BASELINE")
EPISODES = 9000
FIRST_WORLD_SEED = 2026090601
FIELD_COMPONENT = "MCRL_V020_REPRICED_C3_GATE_V1"


class WorldPlanError(ValueError):
    """The frozen physical-evaluation plan is malformed or has drifted."""


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise WorldPlanError("canonical mappings require string keys")
            result[key] = _jsonable(child)
        return result
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise WorldPlanError("canonical JSON requires finite floats")
        return value
    raise WorldPlanError(f"unsupported canonical value: {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            _jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise WorldPlanError("plan is not canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def keyed_field_root_digest(component: str, seed: int) -> str:
    """Use the repository carrier when available; retain an inert fallback.

    The fallback is exactly the carrier's public root formula and keeps the
    plan builder importable on a staging host before the simulator package is
    imported.  The runner re-verifies every root with ``KeyedFadingField``.
    """

    try:
        from mcrl.env.keyed_fading import KeyedFadingField
    except ImportError:
        payload = json.dumps(
            ["keyed-branch-independent-v1", component, int(seed)],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        root_key = hashlib.sha256(payload).hexdigest()
        return hashlib.sha256(root_key.encode("utf-8")).hexdigest()
    return KeyedFadingField.from_components(component, int(seed)).root_digest


def build_world_plan() -> dict[str, object]:
    """Return the one prospectively declared 9000-world plan."""

    worlds = [
        {
            "episode_index": index,
            "world_id": f"world-{index:06d}",
            "world_seed": 2026090600 + index,
            "field_root_digest": keyed_field_root_digest(
                FIELD_COMPONENT, 2026090600 + index
            ),
        }
        for index in range(1, EPISODES + 1)
    ]
    body: dict[str, object] = {
        "schema": SCHEMA,
        "split": SPLIT,
        "episode_budget": EPISODES,
        "arms": list(ARMS),
        "field_component": FIELD_COMPONENT,
        "world_rule": {
            "index_base": 1,
            "world_id_format": "world-{k:06d}",
            "world_seed_formula": "2026090600 + k",
        },
        "worlds": worlds,
        "q3_evaluated": False,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    body["plan_sha256"] = canonical_sha256(body)
    return body


def verify_world_plan(value: Mapping[str, object]) -> str:
    """Verify exact equality with the declared generated plan."""

    if not isinstance(value, Mapping):
        raise WorldPlanError("world plan must be a mapping")
    supplied = value.get("plan_sha256")
    if not isinstance(supplied, str) or len(supplied) != 64:
        raise WorldPlanError("plan_sha256 must be a SHA-256")
    body = dict(value)
    body.pop("plan_sha256", None)
    if canonical_sha256(body) != supplied:
        raise WorldPlanError("plan digest disagrees with plan contents")
    expected = build_world_plan()
    if dict(value) != expected:
        raise WorldPlanError("plan differs from the declared 9000-world plan")
    return supplied


def read_world_plan(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise WorldPlanError(f"world plan is missing or symlinked: {source}")
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WorldPlanError(f"world plan is not ASCII JSON: {source}") from error
    if not isinstance(payload, dict):
        raise WorldPlanError("world plan root must be an object")
    verify_world_plan(payload)
    return payload


def _write_once(path: Path, value: object) -> None:
    if path.exists() or path.is_symlink():
        raise WorldPlanError(f"refusing to overwrite world plan: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_bytes(value))
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, path)
        except FileExistsError as error:
            raise WorldPlanError(f"world plan was published concurrently: {path}") from error
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path, help="write the declared plan once")
    group.add_argument("--check", type=Path, help="verify an existing plan")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.check is not None:
            payload = read_world_plan(args.check)
            print(f"WORLD_PLAN_OK plan_sha256={payload['plan_sha256']}")
        else:
            payload = build_world_plan()
            _write_once(args.output, payload)
            print(f"WORLD_PLAN_WRITTEN path={args.output} plan_sha256={payload['plan_sha256']}")
    except WorldPlanError as error:
        print(f"WORLD_PLAN_ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARMS",
    "EPISODES",
    "FIELD_COMPONENT",
    "SCHEMA",
    "SPLIT",
    "WorldPlanError",
    "build_world_plan",
    "canonical_bytes",
    "canonical_sha256",
    "keyed_field_root_digest",
    "read_world_plan",
    "verify_world_plan",
]
