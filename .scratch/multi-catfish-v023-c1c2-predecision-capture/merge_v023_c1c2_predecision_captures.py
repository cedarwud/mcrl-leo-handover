#!/usr/bin/env python3
"""Merge the eight write-once V0.23 TRAIN capture files into one panel."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Sequence


HERE = Path(__file__).resolve().parent
BRIDGE_PATH = HERE / "v023_c1c2_predecision_capture.py"


class PanelMergeError(RuntimeError):
    """The explicit panel-merge boundary failed closed."""


def _load_bridge() -> ModuleType:
    if BRIDGE_PATH.is_symlink() or not BRIDGE_PATH.is_file():
        raise PanelMergeError("capture bridge is missing or symlinked")
    name = "mcrl_v023_c1c2_panel_merge_bridge"
    spec = importlib.util.spec_from_file_location(name, BRIDGE_PATH)
    if spec is None or spec.loader is None:
        raise PanelMergeError("cannot load capture bridge")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise PanelMergeError("capture bridge import failed") from error
    return module


def _read_capture(path: Path) -> dict[str, object]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise PanelMergeError(f"capture is missing or symlinked: {target}")
    try:
        payload = json.loads(target.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PanelMergeError(f"capture is not canonical ASCII JSON: {target}") from error
    if not isinstance(payload, dict):
        raise PanelMergeError(f"capture root is not an object: {target}")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, action="append", required=True)
    parser.add_argument("--c1-neutral-seed", type=int, required=True)
    parser.add_argument("--c2-neutral-seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def merge(args: argparse.Namespace) -> Path:
    paths = tuple(Path(path) for path in args.capture)
    if len(paths) != 8 or len({path.resolve(strict=False) for path in paths}) != 8:
        raise PanelMergeError("exactly eight distinct --capture paths are required")
    output = Path(args.output)
    if not output.is_absolute():
        raise PanelMergeError("--output must be an absolute path")
    if output.exists() or output.is_symlink():
        raise PanelMergeError(f"refusing to overwrite panel capture: {output}")
    bridge = _load_bridge()
    payload = bridge.merge_world_captures(
        (_read_capture(path) for path in paths),
        c1_neutral_seed=int(args.c1_neutral_seed),
        c2_neutral_seed=int(args.c2_neutral_seed),
    )
    bridge.write_capture(payload, output)
    return output


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        output = merge(args)
    except Exception as error:
        print(f"PREDECISION_PANEL_MERGE_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"PREDECISION_PANEL_MERGE_PASS: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
