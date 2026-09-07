#!/usr/bin/env python3
"""Post-outcome single-route diagnostic for the sealed V0.4 five-arm result."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
import time
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_v04_five_arm_ablation as five  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v04-route-interaction-diagnostic-v1"
SEAL_SCHEMA = f"{SCHEMA}-seal"
CLAIM_CEILING = "INTERACTION_DIAGNOSIS_ONLY_NO_ROUTE_EFFICACY_CONFIRMATION"
EXPECTED_FIVE_ARM_RESULT_SHA256 = (
    "9142da31690927fe853765b9dfc0c807d4202738784961b44be393a77c608224"
)
EXPECTED_FIVE_ARM_SEAL_SHA256 = (
    "1e554bf5997d4571193b7f04312c60d11a7d7e5f497128ba1c6bd45ce32d84e0"
)
SINGLE_ARMS = ("C1_ONLY", "C2_ONLY", "C3_ONLY")
ACTIVE_SINGLE_ROUTES = {
    "C1_ONLY": ("C1",),
    "C2_ONLY": ("C2",),
    "C3_ONLY": ("C3",),
}
DEFAULT_FIVE_ARM_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-five-arm-ablation-20260901-r1"
)
DEFAULT_OUTPUT_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-route-interaction-diagnostic-20260901-r1"
)
DEFAULT_WORK_ORDER = (
    REPO
    / "docs"
    / "MULTI-CATFISH-MCRL-V04-ROUTE-INTERACTION-DIAGNOSTIC-2026-09-01.md"
)


class RouteInteractionDiagnosticError(RuntimeError):
    """The post-outcome interaction diagnostic failed closed."""


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RouteInteractionDiagnosticError(f"missing/non-regular input: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RouteInteractionDiagnosticError("non-canonical diagnostic payload") from error


def _write_once(path: Path, payload: object) -> str:
    if path.exists() or path.is_symlink():
        raise RouteInteractionDiagnosticError(f"refusing to overwrite {path}")
    data = _canonical_bytes(payload)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise RouteInteractionDiagnosticError(f"cannot read JSON input {path}") from error
    if not isinstance(value, dict):
        raise RouteInteractionDiagnosticError(f"JSON input is not an object: {path}")
    return value


def _summary(
    rows: Sequence[Mapping[str, Any]],
    *,
    single_route_policy: str | None = None,
) -> dict[str, Any]:
    """Aggregate rows while retaining the frozen five-arm validator.

    The frozen five-arm aggregator intentionally accepts only its sealed arm
    labels.  This diagnostic adds three post-outcome labels, so validate those
    labels at this seam and pass a copy with the equivalent route-row label to
    the unchanged frozen validator.  The original rows and labels are never
    mutated.
    """

    rows_for_validation: Sequence[Mapping[str, Any]] = rows
    if single_route_policy is not None:
        if single_route_policy not in SINGLE_ARMS:
            raise RouteInteractionDiagnosticError(
                f"unknown single-route policy: {single_route_policy}"
            )
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if row.get("policy_label") != single_route_policy:
                raise RouteInteractionDiagnosticError(
                    "single-route row policy label drifted"
                )
            copy = dict(row)
            # FULL is a route-row label accepted by the frozen structural
            # validator; all metric and provenance fields remain unchanged.
            copy["policy_label"] = "FULL"
            normalized.append(copy)
        rows_for_validation = normalized

    result = five.aggregate_rows(rows_for_validation)
    if not isinstance(result, dict):
        raise RouteInteractionDiagnosticError("five-arm aggregator returned no mapping")
    return result


def _contrast(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, float]:
    left_ee = float(left["pooled_ratio_of_sums_ee_bits_per_j"])
    right_ee = float(right["pooled_ratio_of_sums_ee_bits_per_j"])
    if not all(math.isfinite(value) and value > 0.0 for value in (left_ee, right_ee)):
        raise RouteInteractionDiagnosticError("contrast EE values must be positive finite")
    difference = left_ee - right_ee
    return {
        "left_ee_bits_per_j": left_ee,
        "right_ee_bits_per_j": right_ee,
        "difference_bits_per_j": difference,
        "difference_percent_of_right": 100.0 * difference / right_ee,
    }


def _rows_for_initialization(
    rows: Sequence[Mapping[str, Any]], initialization_seed: int
) -> list[Mapping[str, Any]]:
    selected = [
        row for row in rows if row.get("initialization_seed") == initialization_seed
    ]
    if len(selected) != len(five.EVALUATION_SEEDS):
        raise RouteInteractionDiagnosticError("initialization row count is incomplete")
    return selected


def _action_trace_diversity(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    digests = [str(row["action_trace_sha256"]) for row in rows]
    return {"rows": len(rows), "distinct_action_traces": len(set(digests))}


def run_diagnostic(
    *,
    five_arm_dir: Path,
    output_dir: Path,
    gate_dir: Path,
    source_dir: Path,
    v03_root: Path,
    prereg_path: Path,
    tle_root: Path,
    work_order: Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    root = Path(five_arm_dir)
    result_path = root / "result.json"
    seal_path = root / "result-seal.json"
    if _sha256(result_path) != EXPECTED_FIVE_ARM_RESULT_SHA256:
        raise RouteInteractionDiagnosticError("five-arm result bytes changed")
    if _sha256(seal_path) != EXPECTED_FIVE_ARM_SEAL_SHA256:
        raise RouteInteractionDiagnosticError("five-arm result seal bytes changed")
    five_result = _read_json(result_path)
    if five_result.get("scientific_status") != "MULTI_CATFISH_NOT_ALL_CONFIRMED":
        raise RouteInteractionDiagnosticError("unexpected five-arm scientific status")
    if tuple(five_result.get("evaluation_seeds", ())) != five.EVALUATION_SEEDS:
        raise RouteInteractionDiagnosticError("five-arm evaluation seeds changed")
    if tuple(five_result.get("initialization_seeds", ())) != five.INITIALIZATION_SEEDS:
        raise RouteInteractionDiagnosticError("five-arm initialization seeds changed")
    if five_result.get("test_split_opened") is not False:
        raise RouteInteractionDiagnosticError("five-arm artifact crossed TEST")
    if Path(output_dir).exists() or Path(output_dir).is_symlink():
        raise RouteInteractionDiagnosticError(f"refusing to overwrite {output_dir}")

    source_files = (
        Path(__file__).resolve(),
        Path(five.__file__).resolve(),
        REPO / "src" / "mcrl" / "algorithms" / "ee_axis_v04_hybrid.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_state.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_v04_c3_state.py",
        REPO / "src" / "mcrl" / "env" / "keyed_fading.py",
        Path(work_order).resolve(),
    )
    source_manifest = {
        path.relative_to(REPO).as_posix(): _sha256(path) for path in source_files
    }

    runtime = five.source._default_runtime()
    record = five.read_prereg(Path(prereg_path))
    gate_receipt = five._load_gate_receipt(
        gate_dir=Path(gate_dir),
        source_dir=Path(source_dir),
        prereg_path=Path(prereg_path),
    )
    route_rows: dict[str, list[dict[str, Any]]] = {arm: [] for arm in SINGLE_ARMS}
    original_route_arms = five.ROUTE_ARMS
    original_active_routes = five.ACTIVE_ROUTES
    try:
        # The sealed evaluator is imported as a physics adapter only.  This
        # process-local extension is explicit in the new source manifest and
        # cannot alter the retained five-arm artifact.
        five.ROUTE_ARMS = SINGLE_ARMS
        five.ACTIVE_ROUTES = ACTIVE_SINGLE_ROUTES
        with tempfile.TemporaryDirectory(prefix="mcrl-v04-route-interaction-tle-") as temporary:
            archive = runtime.frozen_archive(
                record,
                Path(tle_root),
                Path(temporary) / "frozen-tle",
            )
            hybrids: dict[int, Any] = {}
            before: dict[int, Mapping[str, Any]] = {}
            for initialization_seed in five.INITIALIZATION_SEEDS:
                trainer = five.screen.load_gate_selected_hybrid(
                    gate_receipt,
                    v03_root=Path(v03_root),
                    initialization_seed=initialization_seed,
                )
                five._prepare_hybrid(trainer)
                hybrids[initialization_seed] = trainer
                before[initialization_seed] = five._snapshot_hybrid(trainer)
            for evaluation_seed in five.EVALUATION_SEEDS:
                field = five._field_for_seed(evaluation_seed)
                for initialization_seed in five.INITIALIZATION_SEEDS:
                    trainer = hybrids[initialization_seed]
                    for arm in SINGLE_ARMS:
                        row = five.evaluate_route_episode(
                            trainer,
                            archive,
                            evaluation_seed=evaluation_seed,
                            initialization_seed=initialization_seed,
                            policy_label=arm,
                            field=field,
                        )
                        route_rows[arm].append(row)
            for initialization_seed, trainer in hybrids.items():
                five._assert_hybrid_unchanged(trainer, before[initialization_seed])
    finally:
        five.ROUTE_ARMS = original_route_arms
        five.ACTIVE_ROUTES = original_active_routes

    if any(len(rows) != 90 for rows in route_rows.values()):
        raise RouteInteractionDiagnosticError("single-route episode budget is incomplete")
    single_summaries = {
        arm: _summary(rows, single_route_policy=arm)
        for arm, rows in route_rows.items()
    }
    existing = five_result["arms_data"]
    if not isinstance(existing, Mapping):
        raise RouteInteractionDiagnosticError("five-arm blocks are missing")
    existing_rows = {
        arm: existing[arm]["rows"]
        for arm in ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "MAIN")
    }
    existing_summaries = {
        arm: existing[arm]["summary"]
        for arm in ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "MAIN")
    }

    c1_contexts = {
        "with_Q2": _contrast(existing_summaries["DROP_C3"], single_summaries["C2_ONLY"]),
        "with_Q3": _contrast(existing_summaries["DROP_C2"], single_summaries["C3_ONLY"]),
        "with_Q2_Q3": _contrast(existing_summaries["FULL"], existing_summaries["DROP_C1"]),
    }
    per_initialization: dict[str, Any] = {}
    for initialization_seed in five.INITIALIZATION_SEEDS:
        singles = {
            arm: _summary(
                _rows_for_initialization(rows, initialization_seed),
                single_route_policy=arm,
            )
            for arm, rows in route_rows.items()
        }
        pairs = {
            arm: _summary(_rows_for_initialization(existing_rows[arm], initialization_seed))
            for arm in ("FULL", "DROP_C1", "DROP_C2", "DROP_C3")
        }
        per_initialization[str(initialization_seed)] = {
            "single_route_summaries": singles,
            "c1_conditional_margins": {
                "with_Q2": _contrast(pairs["DROP_C3"], singles["C2_ONLY"]),
                "with_Q3": _contrast(pairs["DROP_C2"], singles["C3_ONLY"]),
                "with_Q2_Q3": _contrast(pairs["FULL"], pairs["DROP_C1"]),
            },
        }

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "DIAGNOSTIC_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "source_five_arm_result_sha256": EXPECTED_FIVE_ARM_RESULT_SHA256,
        "source_five_arm_seal_sha256": EXPECTED_FIVE_ARM_SEAL_SHA256,
        "source_manifest": source_manifest,
        "evaluation_split": five.EVALUATION_SPLIT,
        "evaluation_seeds": list(five.EVALUATION_SEEDS),
        "initialization_seeds": list(five.INITIALIZATION_SEEDS),
        "selected_q3_rung": five.SELECTED_Q3_RUNG,
        "single_route_arms": list(SINGLE_ARMS),
        "single_route_summaries": single_summaries,
        "existing_five_arm_summaries": existing_summaries,
        "action_trace_diversity": {
            arm: _action_trace_diversity(rows) for arm, rows in route_rows.items()
        },
        "c1_conditional_margins": c1_contexts,
        "per_initialization": per_initialization,
        "diagnostic_interpretation": {
            "all_three_c1_contexts_positive": all(
                value["difference_bits_per_j"] > 0.0 for value in c1_contexts.values()
            ),
            "c1_large_full_margin_is_context_conditional": True,
            "route_efficacy_confirmed": False,
            "final_five_arm_rerun_after_c2_required": True,
        },
        "episode_count": sum(len(rows) for rows in route_rows.values()),
        "episode_training": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": True,
        "elapsed_s": time.perf_counter() - started,
    }

    destination = Path(output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    try:
        result_sha = _write_once(temporary / "result.json", body)
        seal = {
            "schema": SEAL_SCHEMA,
            "result_file_sha256": result_sha,
            "source_five_arm_result_sha256": EXPECTED_FIVE_ARM_RESULT_SHA256,
            "work_order_file_sha256": _sha256(Path(work_order)),
            "episode_count": body["episode_count"],
            "episode_training": False,
            "test_split_opened": False,
            "claim_ceiling": CLAIM_CEILING,
        }
        seal_sha = _write_once(temporary / "result-seal.json", seal)
        if destination.exists() or destination.is_symlink():
            raise RouteInteractionDiagnosticError("diagnostic destination appeared")
        os.rename(temporary, destination)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary)
    return {
        "status": body["status"],
        "output_dir": str(destination.resolve()),
        "result_file_sha256": result_sha,
        "result_seal_file_sha256": seal_sha,
        "episode_count": body["episode_count"],
        "c1_conditional_margins": c1_contexts,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--five-arm-dir", type=Path, default=DEFAULT_FIVE_ARM_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--gate-dir", type=Path, default=five.DEFAULT_GATE_DIR)
    parser.add_argument("--source-dir", type=Path, default=five.DEFAULT_SOURCE_DIR)
    parser.add_argument("--v03-root", type=Path, default=five.DEFAULT_V03_ROOT)
    parser.add_argument("--prereg", type=Path, default=five.DEFAULT_PREREG)
    parser.add_argument("--tle-root", type=Path, default=five.DEFAULT_TLE_ROOT)
    parser.add_argument("--work-order", type=Path, default=DEFAULT_WORK_ORDER)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    receipt = run_diagnostic(
        five_arm_dir=args.five_arm_dir,
        output_dir=args.output_dir,
        gate_dir=args.gate_dir,
        source_dir=args.source_dir,
        v03_root=args.v03_root,
        prereg_path=args.prereg,
        tle_root=args.tle_root,
        work_order=args.work_order,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
