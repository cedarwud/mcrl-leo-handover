#!/usr/bin/env python3
"""Run and seal the mandatory one-world Stage-B plumbing gate."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys
from typing import Any, Mapping

import stagec_common as common


PASS = "PASS_PLUMBING_INTEGRITY"


def _module(path: Path) -> Any:
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    result = importlib.import_module(path.stem)
    if Path(result.__file__).resolve() != path.resolve():
        raise common.StageCError(f"module origin drifted: {path}")
    return result


def _args_from_bindings(bindings: Mapping[str, object], output: Path) -> argparse.Namespace:
    stage_a = bindings["stage_a"]
    baseline = bindings["baseline"]
    physical = bindings["physical_inputs"]
    if not all(isinstance(item, Mapping) for item in (stage_a, baseline, physical)):
        raise common.StageCError("Stage-B bindings are malformed")
    exports = stage_a["exports"]
    if not isinstance(exports, list):
        raise common.StageCError("Stage-A export bindings are malformed")
    return argparse.Namespace(
        tle_root=Path(str(physical["tle_root"])),
        output=output,
        learned_checkpoint=[Path(str(stage_a["root"])) / str(entry["path"]) for entry in exports],
        learned_sha256=[str(entry["sha256"]) for entry in exports],
        baseline_checkpoint=Path(str(baseline["checkpoint_path"])),
        baseline_status=Path(str(baseline["status_path"])),
        baseline_status_sha256=str(baseline["status_sha256"]),
    )


def run(bindings_path: Path, output: Path) -> dict[str, object]:
    bindings = common.verify_bindings(bindings_path)
    code_sha, _entries = common.verify_code_manifest()
    if bindings.get("code", {}).get("external_manifest_sha256") != code_sha:
        raise common.StageCError("Stage-B code closure drifted")
    physical = bindings.get("physical_inputs")
    if not isinstance(physical, Mapping):
        raise common.StageCError("Stage-B physical input bindings are malformed")
    tle_rows, tle_sha = common.tree_manifest(Path(str(physical.get("tle_root"))))
    if tle_rows != physical.get("tle_manifest") or tle_sha != physical.get("tle_manifest_sha256"):
        raise common.StageCError("Stage-B frozen TLE tree drifted")
    if str(output.resolve(strict=False)) != bindings.get("stage_b_output_root"):
        raise common.StageCError("Stage-B output root differs from the frozen binding")
    if output.exists() or output.is_symlink():
        raise common.StageCError("Stage-B output root must be absent")
    diagnostic = _module(common.PHYSICAL / "v023_c1c2_successor_plumbing_diagnostic.py")
    result = diagnostic.run_diagnostic(_args_from_bindings(bindings, output))
    if result.get("status") != PASS or result.get("arms") != list(common.ARMS):
        raise common.StageCError("Stage-B diagnostic did not pass exact four-arm coverage")
    receipt = output / "plumbing-receipt.json"
    gate = {
        "schema": "multi-catfish-mcrl-v023-c1c2-successor-stage-b-gate-v1",
        "status": PASS,
        "formal": True,
        "bindings_sha256": common.file_sha256(bindings_path, field="execution bindings"),
        "plumbing_receipt_sha256": common.file_sha256(receipt, field="plumbing receipt"),
        "arms": list(common.ARMS),
        "world_id": "train-v023-c1c2-successor-plumbing-001",
        "completed_steps_per_arm": 10,
    }
    common.write_once(output / "stage-b-gate.json", gate)
    common.write_digest_sidecar(output / "stage-b-gate.json")
    return gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        run(args.bindings, args.output)
    except Exception as error:
        print(f"STOP_PLUMBING_INTEGRITY: {error}", file=sys.stderr)
        return 2
    print(f"{PASS} gate={args.output / 'stage-b-gate.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
