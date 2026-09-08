#!/usr/bin/env python3
"""Seal a verified HELD 3000 root after an explicit owner closure decision."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import sys
from typing import Mapping

import stagec_common as common
import verify_v023_c1c2_successor_stagec as verifier


SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1-"
    "administrative-closure-v1"
)
HELD_TOKEN_SHA256 = hashlib.sha256(verifier.HELD.encode("ascii")).hexdigest()


def _authenticate_decision_marker(
    path: Path,
    *,
    bindings_sha256: str,
    plan_sha256: str,
    policy_bindings_sha256: str,
    admission_mapping_sha256: str,
    result_sha256: str,
    checkpoint_sha256: str,
) -> tuple[dict[str, object], str]:
    marker = common.read_json(path, field="owner closure decision marker")
    marker_sha = common.verify_named_sidecar(path)
    validated = common.validate_owner_closure_decision_marker(
        marker,
        bindings_sha256=bindings_sha256,
        plan_sha256=plan_sha256,
        policy_bindings_sha256=policy_bindings_sha256,
        admission_mapping_sha256=admission_mapping_sha256,
        result_3000_sha256=result_sha256,
        held_terminal_token_sha256=HELD_TOKEN_SHA256,
        checkpoint_3000_sha256=checkpoint_sha256,
    )
    return validated, marker_sha


def _refuse_continuation_evidence(root: Path, bindings_path: Path) -> None:
    continuation_root = root / "continuation"
    if continuation_root.exists() or continuation_root.is_symlink():
        raise common.StageCError(
            "reporting root contains a continuation activity marker or registry"
        )
    if any((root / name).exists() for name in (
        "continuation-result.json", "MANIFEST.sha256", "COMPLETE",
        "ADMINISTRATIVE-CLOSURE.json", "ADMINISTRATIVE-CLOSURE.json.sha256",
    )):
        raise common.StageCError("root is already continued, closed, or sealed")
    active_names = {
        "CONTINUATION-ACTIVE", "CONTINUATION-ACTIVE.json",
        "continuation-session.json", "continuation-started.json",
    }
    for path in root.rglob("*"):
        if path.name in active_names or "integrity-stop" in path.name.lower():
            raise common.StageCError("root contains active continuation or STOP evidence")
        if not path.is_file():
            continue
        match = re.search(r"(?:episode|checkpoint|rung|state)-(\d{6})", path.name)
        if match is not None and int(match.group(1)) > 3000:
            raise common.StageCError("root contains an episode/checkpoint beyond 3000")
        if path.suffix == ".json" and path.stat().st_size < 2_000_000:
            payload = common.read_json(path, field=f"root evidence {path.name}")
            for field in ("completed_episode", "end_boundary", "episode_index"):
                value = payload.get(field)
                if type(value) is int and value > 3000:
                    raise common.StageCError("root contains continuation evidence beyond 3000")
    root_token = str(root.resolve()).encode("utf-8")
    bindings_token = str(bindings_path.resolve()).encode("utf-8")
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            command = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if (root_token in command or bindings_token in command) and any(token in command for token in (
            b"run_v023_c1c2_successor_stage_c_chunks.py",
            b"run_v023_c1c2_successor_stage_c.py",
        )):
            raise common.StageCError("an active continuation session targets this root")


def _verify_bound_r2_addendum(
    path: Path, bindings: Mapping[str, object]
) -> str:
    schedule = bindings.get("scheduling_addendum")
    if (
        not isinstance(schedule, Mapping)
        or path.resolve() != Path(str(schedule.get("path", ""))).resolve()
    ):
        raise common.StageCError("closure addendum must be the R2 path bound by execution bindings")
    addendum_sha = common.verify_named_sidecar(path)
    if addendum_sha != schedule.get("sha256"):
        raise common.StageCError("closure addendum must be the R2 digest bound by execution bindings")
    return addendum_sha


def seal(args: argparse.Namespace) -> dict[str, object]:
    root = args.root.resolve()
    if args.output_receipt.resolve(strict=False) != (root / "ADMINISTRATIVE-CLOSURE.json"):
        raise common.StageCError("closure receipt must be ROOT/ADMINISTRATIVE-CLOSURE.json")
    with common.root_lock(root):
        prospective = common.verify_bindings(args.bindings)
        supplement = common.verify_stage_ab_supplement(
            args.admission_supplement, args.bindings, prospective
        )
        common.verify_acceptance_bundle(
            args.acceptance_bundle,
            {**prospective, "bindings_sha256": common.file_sha256(args.bindings)},
        )
        report = verifier.verify_finished(
            root, args.bindings, args.admission_supplement,
            require_tree_seal=False,
        )
        if report.get("completed_episode") != 3000 or report.get("overall_token") != verifier.HELD:
            raise common.StageCError("administrative closure requires a verified HELD 3000 root")
        _refuse_continuation_evidence(root, args.bindings)
        result_path = root / "result.json"
        checkpoint_path = root / "checkpoints/checkpoint-003000.json"
        admission = common.read_json(root / common.FORMAL_ADMISSION_NAME, field="formal admission")
        result_sha = common.file_sha256(result_path)
        checkpoint_sha = common.file_sha256(checkpoint_path)
        policy_sha = common.digest(
            admission.get("policy_bindings_sha256"), field="policy bindings digest"
        )
        mapping_sha = common.digest(
            admission.get("admission_mapping_sha256"), field="admission mapping digest"
        )
        marker, marker_sha = _authenticate_decision_marker(
            args.decision_marker,
            bindings_sha256=common.file_sha256(args.bindings),
            plan_sha256=common.PLAN_SHA256,
            policy_bindings_sha256=policy_sha,
            admission_mapping_sha256=mapping_sha,
            result_sha256=result_sha,
            checkpoint_sha256=checkpoint_sha,
        )
        addendum_sha = _verify_bound_r2_addendum(args.addendum_r2, prospective)
        preserved = {
            path.relative_to(root).as_posix(): common.file_sha256(path)
            for path in root.rglob("*") if path.is_file() and not path.is_symlink()
        }
        closed_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        receipt: dict[str, object] = {
            "schema": SCHEMA,
            "status": "ADMINISTRATIVE_CLOSURE_SEALED",
            "formal": True,
            "decision": marker["decision"],
            "reason": marker["decision"],
            "decision_marker": {
                "path": str(args.decision_marker.resolve()),
                "sha256": marker_sha,
            },
            "addendum_r2": {
                "path": str(args.addendum_r2.resolve()),
                "sha256": addendum_sha,
            },
            "bindings_sha256": common.file_sha256(args.bindings),
            "plan_sha256": common.PLAN_SHA256,
            "policy_bindings_sha256": policy_sha,
            "admission_mapping_sha256": mapping_sha,
            "result_3000_sha256": result_sha,
            "held_terminal_token_sha256": HELD_TOKEN_SHA256,
            "checkpoint_3000_sha256": checkpoint_sha,
            "continuation_performed": False,
            "planned_maximum_episodes": 9000,
            "completed_boundary": 3000,
            "closed_utc": closed_utc,
            "controller_identity": marker["recorded_by"],
        }
        receipt_sha = common.publish_sealed_json(
            args.output_receipt, receipt, field="administrative closure receipt"
        )
        for relative, expected in preserved.items():
            if common.file_sha256(root / relative) != expected:
                raise common.StageCError(f"scientific byte changed during closure: {relative}")
        common.write_tree_seal(root)
        verifier.verify_finished(root, args.bindings, args.admission_supplement)
        return {**receipt, "receipt_sha256": receipt_sha}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--admission-supplement", type=Path, required=True)
    parser.add_argument("--acceptance-bundle", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--decision-marker", type=Path, required=True)
    parser.add_argument("--addendum-r2", type=Path, required=True)
    parser.add_argument("--output-receipt", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = seal(args)
    except Exception as error:
        print(f"STAGEC_ADMINISTRATIVE_CLOSURE_REFUSED: {error}", file=sys.stderr)
        return 2
    print(
        f"STAGEC_ADMINISTRATIVE_CLOSURE_SEALED root={args.root.resolve()} "
        f"receipt_sha256={receipt['receipt_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
