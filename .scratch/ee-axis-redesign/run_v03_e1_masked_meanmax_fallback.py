#!/usr/bin/env python3
"""Run the single predeclared masked mean/max E1 validation fallback.

The primary action-shared V3 validation is the only input authority.  This
runner is admissible only when that sealed result says
``EVALUATE_MASKED_MEANMAX_ONCE`` (C1/C2 pass, C3 fails, and the independent
instrument gates pass).  It reuses the same frozen TRAIN source, explicit
validation batches, three initialization seeds, update rungs, nulls, common
rung selection, collision census, action-effect ceiling, and C2 anchor
sensitivity gate.  Only the scorer changes to legal-mask featurewise mean/max
context.

This runner never opens TEST, computes EE, selects another fallback, or
rewrites the primary V3 authority.  Its result status is exactly one of
``GO_500EP_SCREEN_ONLY`` or ``STOP_MASKED_MEANMAX_VALIDATION``.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stable = _load_module(
    "e1_action_shared_validation_stable_for_meanmax",
    HERE / "run_v03_e1_action_shared_validation.py",
)
v3 = _load_module(
    "e1_action_shared_validation_v3_for_meanmax",
    HERE / "run_v03_e1_action_shared_validation_v3.py",
)

from mcrl.algorithms import ee_axis_action_shared_meanmax as meanmax  # noqa: E402
from mcrl.algorithms.ee_axis_pairwise import ROUTE_NAMES  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v03-e1-masked-meanmax-fallback-v1"
AUTHORITY_SCHEMA = f"{SCHEMA}-authority"
AUTHORITY_SEAL_SCHEMA = f"{AUTHORITY_SCHEMA}-seal"
CHECKPOINT_SCHEMA = f"{SCHEMA}-checkpoint"
RESULT_SCHEMA = f"{SCHEMA}-result"
RESULT_SEAL_SCHEMA = f"{RESULT_SCHEMA}-seal"
TRIGGER_STATUS = "EVALUATE_MASKED_MEANMAX_ONCE"
GO_STATUS = "GO_500EP_SCREEN_ONLY"
STOP_STATUS = "STOP_MASKED_MEANMAX_VALIDATION"
CLAIM_CEILING = "ONE_SHOT_MASKED_MEANMAX_VALIDATION_NO_TEST_NO_EE"
FALSE_BOUNDARY = {
    "validation_dataset_bytes_opened": False,
    "validation_metrics_computed": False,
    "test_split_opened": False,
    "held_out_ee_evaluated": False,
}
POST_METRIC_BOUNDARY = {
    "validation_dataset_bytes_opened": True,
    "validation_metrics_computed": True,
    "test_split_opened": False,
    "held_out_ee_evaluated": False,
}
CODE_MANIFEST_PATHS = (
    ".scratch/ee-axis-redesign/run_v03_e1_masked_meanmax_fallback.py",
    ".scratch/ee-axis-redesign/run_v03_e1_action_shared_validation.py",
    ".scratch/ee-axis-redesign/run_v03_e1_action_shared_validation_v3.py",
    ".scratch/ee-axis-redesign/run_v03_e1_action_shared_sources.py",
    ".scratch/ee-axis-redesign/verify_v03_e1_action_shared_sources.py",
    ".scratch/ee-axis-redesign/census_v03_e1_action_graph_coverage.py",
    ".scratch/ee-axis-redesign/run_v03_e1_c2_train_action_graph_expansion.py",
    ".scratch/ee-axis-redesign/run_v03_e1_c2_train_action_balanced_expansion.py",
    "src/mcrl/algorithms/ee_axis_action_shared.py",
    "src/mcrl/algorithms/ee_axis_action_shared_meanmax.py",
    "src/mcrl/algorithms/ee_axis_pairwise.py",
    "src/mcrl/runtime/ee_axis_e1_ladder.py",
    "src/mcrl/runtime/ee_axis_e1_c2_schedule.py",
    "src/mcrl/runtime/ee_axis_instrument_validity.py",
    "src/mcrl/runtime/ee_axis_temporal_dataset.py",
    "src/mcrl/runtime/ee_axis_temporal_pairs.py",
    "tests/test_w74_ee_axis_action_shared_meanmax.py",
    "tests/test_w75_masked_meanmax_fallback.py",
    "docs/MULTI-CATFISH-MCRL-V03-E1-MASKED-MEANMAX-FALLBACK-CONTRACT-2026-09-01.md",
    "docs/MULTI-CATFISH-MCRL-V03-E1-ACTION-SHARED-AMENDMENT-2026-09-01.md",
    "docs/DEVIATION-REGISTER.md",
)

FRESH_VALIDATION_LOOK_INDEX = 2
CONTEXT_SELECTION_PROVENANCE = {
    "design_only": True,
    "selection_null": "action-only",
    "selected_variant": "meanmax",
    "selected_reason": "best_C3_skill_in_four_way_design_only_context_screen",
    "fresh_validation_look_index": FRESH_VALIDATION_LOOK_INDEX,
    "fresh_validation_look_plan": [
        {"look_index": 1, "variant": "local_action_shared_v3"},
        {"look_index": 2, "variant": "masked_meanmax_once"},
    ],
    "same_initialization_seeds_as_primary": True,
    "weight_matched_to_primary": False,
    "alpha_control_gate_used": False,
    "sign_only_exploratory_gate_used": False,
    "scorer_input_width": {"primary_local": 12, "fallback_local_meanmax": 28},
    "per_head_parameter_count": {"primary": 8951, "fallback": 10551},
    "per_head_parameter_increase_fraction": 1600 / 8951,
    "four_way_skill_at_design_rung_30": {
        "local": {"C1": 0.2711, "C2": 0.2659, "C3": 0.1298},
        "mean": {"C1": 0.2477, "C2": 0.2681, "C3": 0.1286},
        "meanmax": {"C1": 0.2440, "C2": 0.2669, "C3": 0.1532},
        "deepset": {"C1": 0.2402, "C2": 0.2656, "C3": 0.1395},
    },
}


class MaskedMeanMaxFallbackError(RuntimeError):
    """The one-shot fallback violated its sealed authority."""


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise MaskedMeanMaxFallbackError(
            f"sealed file is missing, non-regular, or a symlink: {path}"
        )
    return stable._sha256_file(path)


def _regular_directory(path: Path, *, label: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise MaskedMeanMaxFallbackError(f"{label} is not a regular directory")
    return path.resolve(strict=True)


def _digest(value: object, *, field: str) -> str:
    try:
        return stable.sources._digest(value, field=field)
    except Exception as error:
        raise MaskedMeanMaxFallbackError(str(error)) from error


def _read_exact(path: Path, expected_sha256: str, *, label: str) -> dict[str, Any]:
    expected = _digest(expected_sha256, field=f"expected_{label}_sha256")
    if _sha256(path) != expected:
        raise MaskedMeanMaxFallbackError(f"{label} bytes changed")
    try:
        payload = stable.sources._read_canonical_json(path)
    except Exception as error:
        raise MaskedMeanMaxFallbackError(f"{label} is not canonical JSON") from error
    if not isinstance(payload, dict):
        raise MaskedMeanMaxFallbackError(f"{label} is not an object")
    return payload


def _code_manifest() -> dict[str, str]:
    return {relative: _sha256(REPO / relative) for relative in CODE_MANIFEST_PATHS}


def _assert_false_boundary(payload: Mapping[str, Any], *, label: str) -> None:
    for field in (
        "validation_dataset_bytes_opened",
        "validation_metrics_computed",
        "test_split_opened",
        "held_out_ee_evaluated",
    ):
        if field in payload and payload.get(field) is not False:
            raise MaskedMeanMaxFallbackError(f"{label} crossed prohibited {field}")
    if "test_dataset_paths_opened" in payload and payload.get("test_dataset_paths_opened") != []:
        raise MaskedMeanMaxFallbackError(f"{label} crossed prohibited test_dataset_paths_opened")


def _authenticate_v3_trigger(
    root: Path,
    *,
    expected_authority_file_sha256: str,
    expected_authority_seal_file_sha256: str,
    expected_result_file_sha256: str,
    expected_result_seal_file_sha256: str,
    expected_preoutcome_authority_sha256: str,
    expected_preoutcome_authority_seal_sha256: str,
) -> dict[str, Any]:
    """Authenticate the exact V3 result which authorizes this one shot."""

    root = _regular_directory(root, label="V3 validation root")
    authority_path = root / "authority.json"
    authority_seal_path = root / "authority-seal.json"
    result_path = root / "result.json"
    result_seal_path = root / "result-seal.json"
    authority = _read_exact(
        authority_path,
        expected_authority_file_sha256,
        label="V3 authority file",
    )
    authority_seal = _read_exact(
        authority_seal_path,
        expected_authority_seal_file_sha256,
        label="V3 authority seal",
    )
    result = _read_exact(
        result_path,
        expected_result_file_sha256,
        label="V3 result file",
    )
    result_seal = _read_exact(
        result_seal_path,
        expected_result_seal_file_sha256,
        label="V3 result seal",
    )
    authority_sha = _digest(
        authority.get("authority_sha256"), field="V3.authority_sha256"
    )
    authority_body = dict(authority)
    authority_body.pop("authority_sha256", None)
    canonical_authority_sha = stable.sources._canonical_sha256(authority_body)
    expected_preoutcome = _digest(
        expected_preoutcome_authority_sha256,
        field="expected_V3_preoutcome_authority_sha256",
    )
    expected_preoutcome_seal = _digest(
        expected_preoutcome_authority_seal_sha256,
        field="expected_V3_preoutcome_authority_seal_sha256",
    )
    if (
        authority_sha != canonical_authority_sha
        or authority.get("schema") != v3.EXECUTION_AUTHORITY_SCHEMA
        or authority.get("status") != "SEALED_BEFORE_ANY_VALIDATION_METRIC"
        or authority.get("claim_ceiling") != v3.CLAIM_CEILING
        or authority.get("preoutcome_authority_sha256") != expected_preoutcome
        or authority.get("preoutcome_authority_seal_sha256") != expected_preoutcome_seal
        or authority_seal.get("schema") != f"{v3.EXECUTION_AUTHORITY_SCHEMA}-seal"
        or authority_seal.get("authority_sha256") != authority_sha
        or authority_seal.get("authority_file_sha256") != expected_authority_file_sha256
        or result.get("schema") != v3.RESULT_SCHEMA
        or result.get("status") != TRIGGER_STATUS
        or result.get("claim_ceiling") != v3.CLAIM_CEILING
        or result.get("authority_sha256") != authority_sha
        or result.get("preoutcome_authority_sha256") != expected_preoutcome
        or result.get("source_partition_expanded") != "TRAIN"
        or result.get("expanded_route") != "C2"
        or result.get("base_validation_batches_unchanged") is not True
        or result.get("test_dataset_paths_opened") != []
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or result_seal.get("schema") != v3.RESULT_SEAL_SCHEMA
        or result_seal.get("authority_sha256") != authority_sha
        or result_seal.get("preoutcome_authority_sha256") != expected_preoutcome
        or result_seal.get("result_file_sha256") != expected_result_file_sha256
    ):
        raise MaskedMeanMaxFallbackError("V3 trigger authority/result closure is invalid")
    gate = result.get("gate")
    route_gate = gate.get("route_gate") if isinstance(gate, dict) else None
    if (
        not isinstance(gate, dict)
        or gate.get("status") != TRIGGER_STATUS
        or not isinstance(route_gate, dict)
        or set(route_gate) != set(ROUTE_NAMES)
        or route_gate.get("C1", {}).get("pass") is not True
        or route_gate.get("C2", {}).get("pass") is not True
        or route_gate.get("C3", {}).get("pass") is not False
        or gate.get("collision_pass") is not True
        or gate.get("action_main_effect_pass") is not True
        or gate.get("c2_anchor_sensitivity_pass") is not True
    ):
        raise MaskedMeanMaxFallbackError("V3 result does not authorize the isolated C3 fallback")
    _assert_false_boundary(authority, label="V3 authority")
    _assert_false_boundary(result, label="V3 result")
    code_manifest = authority.get("code_manifest")
    if not isinstance(code_manifest, dict):
        raise MaskedMeanMaxFallbackError("V3 authority has no code manifest")
    # The V3 result is already sealed against its own implementation.  Do not
    # silently accept a changed V3 validator while consuming its trigger.
    v3_manifest = v3._code_manifest()
    for relative, digest in v3_manifest.items():
        if code_manifest.get(relative) != digest:
            raise MaskedMeanMaxFallbackError(f"V3 code manifest changed: {relative}")
    return {
        "authority": authority,
        "authority_seal": authority_seal,
        "result": result,
        "result_seal": result_seal,
        "authority_file_sha256": expected_authority_file_sha256,
        "authority_seal_file_sha256": expected_authority_seal_file_sha256,
        "result_file_sha256": expected_result_file_sha256,
        "result_seal_file_sha256": expected_result_seal_file_sha256,
        "preoutcome_authority_sha256": expected_preoutcome,
        "preoutcome_authority_seal_sha256": expected_preoutcome_seal,
    }


def _load_dependencies_before_metrics(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    expansion_root: Path,
    preoutcome_authority_path: Path,
    preoutcome_authority_seal_path: Path,
    expected_preoutcome_authority_sha256: str,
    expected_preoutcome_authority_seal_sha256: str,
) -> dict[str, Any]:
    """Authenticate source/expansion metadata without opening validation rows."""

    preoutcome = v3._load_preoutcome_authority(
        preoutcome_authority_path,
        preoutcome_authority_seal_path,
        expected_authority_sha256=expected_preoutcome_authority_sha256,
        expected_seal_sha256=expected_preoutcome_authority_seal_sha256,
    )
    dependencies = v3.collect_preoutcome_dependencies(
        source_root=source_root,
        independent_root=independent_root,
        census_root=census_root,
        expansion_root=expansion_root,
        expected_independent_result_sha256=preoutcome[
            "base_independent_verifier_result_sha256"
        ],
        expected_independent_result_seal_sha256=preoutcome[
            "base_independent_verifier_result_seal_sha256"
        ],
        expected_census_result_sha256=preoutcome["census_result_sha256"],
        expected_census_result_seal_sha256=preoutcome["census_result_seal_sha256"],
        expected_expansion_authority_sha256=preoutcome["expansion_authority_sha256"],
        expected_expansion_authority_seal_sha256=preoutcome[
            "expansion_authority_seal_sha256"
        ],
        expected_expansion_result_sha256=preoutcome["expansion_result_sha256"],
        expected_expansion_result_seal_sha256=preoutcome[
            "expansion_result_seal_sha256"
        ],
    )
    if preoutcome != v3.preoutcome_authority_payload(dependencies):
        raise MaskedMeanMaxFallbackError("preoutcome dependency closure changed")
    return {"preoutcome": preoutcome, "dependencies": dependencies}


def _masked_route_metrics(
    trainer: Any,
    batches: Any,
    route_index: int,
) -> dict[str, Any]:
    """Use the stable null/generalization metric with explicit masks."""

    route = ROUTE_NAMES[route_index]
    train = batches.batch("train", route)
    validation = batches.batch("validation", route)
    q = trainer.q_values(validation.states, validation.action_masks)[route_index]
    report = stable.compute_strong_baseline_pair_generalization(
        train_reference_actions=train.reference_actions,
        train_candidate_actions=train.candidate_actions,
        train_targets=np.asarray(train.target_surplus_bits, dtype=np.float64)
        / trainer.config.kappa_bits,
        heldout_reference_actions=validation.reference_actions,
        heldout_candidate_actions=validation.candidate_actions,
        heldout_targets=np.asarray(validation.target_surplus_bits, dtype=np.float64)
        / trainer.config.kappa_bits,
        heldout_q_surface=q,
        action_dim=trainer.config.action_dim,
    )
    payload = report.as_dict()
    payload["model_to_strongest_null_mae_ratio"] = (
        report.model_mae / report.strongest_state_independent_baseline_mae
    )
    payload["skill_vs_strongest_null"] = report.relative_mae_improvement
    return payload


def _masked_action_main_effect(trainers: Mapping[int, Any], batches: Any) -> dict[str, float]:
    train_states = np.concatenate(
        [batches.batch("train", route).states for route in ROUTE_NAMES], axis=0
    )
    train_masks = np.concatenate(
        [batches.batch("train", route).action_masks for route in ROUTE_NAMES], axis=0
    )
    validation_states = np.concatenate(
        [batches.batch("validation", route).states for route in ROUTE_NAMES], axis=0
    )
    validation_masks = np.concatenate(
        [batches.batch("validation", route).action_masks for route in ROUTE_NAMES], axis=0
    )
    train_indices = stable._unique_state_indices(train_states, train_masks)
    validation_indices = stable._unique_state_indices(validation_states, validation_masks)
    values: dict[str, float] = {}
    for seed, trainer in trainers.items():
        train_scores = trainer.deployment_scores(
            train_states[train_indices], train_masks[train_indices]
        )
        validation_scores = trainer.deployment_scores(
            validation_states[validation_indices], validation_masks[validation_indices]
        )
        values[str(seed)] = stable.compute_action_main_effect(
            validation_scores=train_scores,
            validation_masks=train_masks[train_indices],
            test_scores=validation_scores,
            test_masks=validation_masks[validation_indices],
        ).action_main_effect_fraction
    return values


def _masked_c2_anchor_sensitivity(
    trainers: Mapping[int, Any],
    batches: Any,
    temporal_rows: tuple[Any, ...],
) -> dict[str, Any]:
    """Stable C2 estimands, with explicit validation masks passed to Q."""

    train = batches.batch("train", "C2")
    validation = batches.batch("validation", "C2")
    if len(temporal_rows) != validation.states.shape[0]:
        raise MaskedMeanMaxFallbackError("C2 metadata no longer aligns with its batch")
    first = next(iter(trainers.values()))
    target = np.asarray(validation.target_surplus_bits, dtype=np.float64) / first.config.kappa_bits
    baseline_candidates = stable._baseline_predictions(
        train, validation, first.config.kappa_bits
    )
    groups: dict[tuple[int, int], list[int]] = {}
    for index, row in enumerate(temporal_rows):
        groups.setdefault((int(row.seed), int(row.step_index)), []).append(index)
    group_keys = tuple(sorted(groups))
    group_indices = tuple(groups[key] for key in group_keys)
    if len(group_keys) < 2:
        raise MaskedMeanMaxFallbackError("C2 requires at least two validation world anchors")
    baseline_anchor_errors = {
        name: np.asarray(
            [np.mean(np.abs(prediction - target)[indices]) for indices in group_indices],
            dtype=np.float64,
        )
        for name, prediction in baseline_candidates.items()
    }
    model_anchor_errors: dict[int, np.ndarray] = {}
    for seed, trainer in trainers.items():
        q = trainer.q_values(validation.states, validation.action_masks)[1]
        index = np.arange(target.size)
        prediction = q[index, validation.candidate_actions] - q[
            index, validation.reference_actions
        ]
        errors = np.abs(prediction - target)
        model_anchor_errors[seed] = np.asarray(
            [np.mean(errors[indices]) for indices in group_indices], dtype=np.float64
        )
    all_anchors = np.ones(len(group_keys), dtype=bool)
    balanced = stable._c2_estimand_report(
        baseline_anchor_errors=baseline_anchor_errors,
        model_anchor_errors=model_anchor_errors,
        keep=all_anchors,
    )
    leave_one_out: list[dict[str, Any]] = []
    for omitted, (source_seed, step_index) in enumerate(group_keys):
        keep = np.ones(len(group_keys), dtype=bool)
        keep[omitted] = False
        leave_one_out.append(
            {
                "omitted_world_anchor": {
                    "source_seed": source_seed,
                    "step_index": step_index,
                },
                **stable._c2_estimand_report(
                    baseline_anchor_errors=baseline_anchor_errors,
                    model_anchor_errors=model_anchor_errors,
                    keep=keep,
                ),
            }
        )
    per_initialization = {
        str(seed): {
            "anchor_balanced_skill": balanced["skills_by_initialization"][str(seed)],
            "leave_one_world_anchor_out_skills": [
                row["skills_by_initialization"][str(seed)] for row in leave_one_out
            ],
        }
        for seed in sorted(model_anchor_errors)
    }
    all_estimands_pass = bool(
        balanced["pass"] and all(row["pass"] for row in leave_one_out)
    )
    return {
        "world_anchors": len(group_keys),
        "anchor_balanced": balanced,
        "leave_one_world_anchor_out": leave_one_out,
        "per_initialization": per_initialization,
        "all_estimands_pass_primary_gate": all_estimands_pass,
        "same_positive_direction": all_estimands_pass,
    }


def _state_mask_census(batches: Any) -> dict[str, Any]:
    """Describe the actual TRAIN+validation state/mask surface, without targets."""

    per_route: dict[str, dict[str, int | float]] = {}
    all_states: list[np.ndarray] = []
    all_masks: list[np.ndarray] = []
    for route in ROUTE_NAMES:
        states = np.concatenate(
            [batches.batch(split, route).states for split in ("train", "validation")],
            axis=0,
        )
        masks = np.concatenate(
            [batches.batch(split, route).action_masks for split in ("train", "validation")],
            axis=0,
        )
        all_states.append(states)
        all_masks.append(masks)
        per_route[route] = {
            "rows": int(states.shape[0]),
            "distinct_states": int(
                len({np.asarray(row, dtype="<f4").tobytes() for row in states})
            ),
            "all_legal_mask_fraction": float(np.mean(np.all(masks, axis=1))),
        }
    states = np.concatenate(all_states, axis=0)
    masks = np.concatenate(all_masks, axis=0)
    return {
        "rows": int(states.shape[0]),
        "distinct_states": int(
            len({np.asarray(row, dtype="<f4").tobytes() for row in states})
        ),
        "all_legal_mask_fraction": float(np.mean(np.all(masks, axis=1))),
        "by_route": per_route,
    }


def _save_and_reload(
    *,
    path: Path,
    authority_sha256: str,
    trainer: Any,
    seed: int,
    rung: int,
    metrics: Mapping[str, Any],
    batches: Any,
) -> tuple[str, Any]:
    payload = {
        "schema": CHECKPOINT_SCHEMA,
        "authority_sha256": authority_sha256,
        "initialization_seed": seed,
        "rung": rung,
        "validation_metrics": dict(metrics),
        "trainer": trainer.checkpoint_state(update_count=rung * 3),
        **POST_METRIC_BOUNDARY,
    }
    digest = stable._save_checkpoint(path, payload)
    if _sha256(path) != digest:
        raise MaskedMeanMaxFallbackError("checkpoint digest changed immediately after save")
    reloaded_payload = torch.load(path, map_location="cpu", weights_only=False)
    if (
        reloaded_payload.get("schema") != CHECKPOINT_SCHEMA
        or reloaded_payload.get("authority_sha256") != authority_sha256
        or reloaded_payload.get("initialization_seed") != seed
        or reloaded_payload.get("rung") != rung
        or reloaded_payload.get("validation_metrics") != dict(metrics)
        or reloaded_payload.get("validation_dataset_bytes_opened") is not True
        or reloaded_payload.get("validation_metrics_computed") is not True
        or reloaded_payload.get("test_split_opened") is not False
        or reloaded_payload.get("held_out_ee_evaluated") is not False
    ):
        raise MaskedMeanMaxFallbackError("checkpoint identity changed after save")
    restored = meanmax.EEAxisMaskedMeanMaxTrainer(
        trainer.config, train_seed=seed, device="cpu"
    )
    if restored.load_checkpoint_state(reloaded_payload["trainer"]) != rung * 3:
        raise MaskedMeanMaxFallbackError("checkpoint update count changed after reload")
    for route_index, route in enumerate(ROUTE_NAMES):
        restored_metrics = _masked_route_metrics(restored, batches, route_index)
        if restored_metrics != dict(metrics[route]):
            raise MaskedMeanMaxFallbackError(
                f"checkpoint reload changed {route} metrics at rung {rung}"
            )
    return digest, restored


def _final_status(gate_status: object) -> str:
    """Collapse the stable gate to the two permitted one-shot outcomes."""

    if gate_status == GO_STATUS:
        return GO_STATUS
    if gate_status in {
        TRIGGER_STATUS,
        "STOP_ACTION_SHARED_VALIDATION",
    }:
        return STOP_STATUS
    raise MaskedMeanMaxFallbackError("fallback received an unknown validation gate status")


def run(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    expansion_root: Path,
    v3_root: Path,
    preoutcome_authority_path: Path,
    preoutcome_authority_seal_path: Path,
    output_dir: Path,
    expected_v3_authority_file_sha256: str,
    expected_v3_authority_seal_file_sha256: str,
    expected_v3_result_file_sha256: str,
    expected_v3_result_seal_file_sha256: str,
    expected_preoutcome_authority_sha256: str,
    expected_preoutcome_authority_seal_sha256: str,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to overwrite one-shot mean/max fallback")
    trigger = _authenticate_v3_trigger(
        v3_root,
        expected_authority_file_sha256=expected_v3_authority_file_sha256,
        expected_authority_seal_file_sha256=expected_v3_authority_seal_file_sha256,
        expected_result_file_sha256=expected_v3_result_file_sha256,
        expected_result_seal_file_sha256=expected_v3_result_seal_file_sha256,
        expected_preoutcome_authority_sha256=expected_preoutcome_authority_sha256,
        expected_preoutcome_authority_seal_sha256=expected_preoutcome_authority_seal_sha256,
    )
    preoutcome_bundle = _load_dependencies_before_metrics(
        source_root=source_root,
        independent_root=independent_root,
        census_root=census_root,
        expansion_root=expansion_root,
        preoutcome_authority_path=preoutcome_authority_path,
        preoutcome_authority_seal_path=preoutcome_authority_seal_path,
        expected_preoutcome_authority_sha256=expected_preoutcome_authority_sha256,
        expected_preoutcome_authority_seal_sha256=expected_preoutcome_authority_seal_sha256,
    )
    preoutcome = preoutcome_bundle["preoutcome"]
    dependencies = preoutcome_bundle["dependencies"]
    if (
        trigger["authority"]["preoutcome_authority_sha256"]
        != expected_preoutcome_authority_sha256
        or trigger["result"]["preoutcome_authority_sha256"]
        != expected_preoutcome_authority_sha256
    ):
        raise MaskedMeanMaxFallbackError("V3 and fallback preoutcome authorities disagree")
    prereg = dependencies["prereg"]
    primary_config = stable._config_from_prereg(prereg)
    config = meanmax.config_from_action_shared(primary_config)
    if (
        primary_config.learning_rate != 0.001
        or primary_config.beta != 0.1
        or config.learning_rate != primary_config.learning_rate
        or config.beta != primary_config.beta
        or config.kappa_bits != primary_config.kappa_bits
        or config.hidden_layers != primary_config.hidden_layers
        or config.activation != primary_config.activation
        or config.loss_weights != primary_config.loss_weights
    ):
        raise MaskedMeanMaxFallbackError("fallback changed a frozen scalar learner hyperparameter")
    code_manifest = _code_manifest()
    authority = {
        "schema": AUTHORITY_SCHEMA,
        "status": "SEALED_BEFORE_VALIDATION_DATASET_AND_METRICS",
        "claim_ceiling": CLAIM_CEILING,
        "one_shot": True,
        "fallback_variant": "legal-mask-featurewise-mean-and-maximum-context",
        "trigger_status": TRIGGER_STATUS,
        "context_selection_provenance": CONTEXT_SELECTION_PROVENANCE,
        "v3_input": {
            "authority_file_sha256": expected_v3_authority_file_sha256,
            "authority_seal_file_sha256": expected_v3_authority_seal_file_sha256,
            "result_file_sha256": expected_v3_result_file_sha256,
            "result_seal_file_sha256": expected_v3_result_seal_file_sha256,
        },
        "preoutcome_authority_sha256": expected_preoutcome_authority_sha256,
        "preoutcome_authority_seal_sha256": expected_preoutcome_authority_seal_sha256,
        "source_prereg_sha256": prereg["prereg_sha256"],
        "source_manifest_sha256": prereg["source_manifest_sha256"],
        "source_access_before_validation": dependencies["source_metadata"],
        "formal_expansion_access": {
            "authority_sha256": dependencies["expansion"]["authority_sha256"],
            "authority_seal_sha256": dependencies["expansion"]["authority_seal_sha256"],
            "result_sha256": dependencies["expansion"]["result_sha256"],
            "result_seal_sha256": dependencies["expansion"]["result_seal_sha256"],
            "selected_seed_order": dependencies["expansion"]["selected_seed_order"],
        },
        "primary_config": asdict(primary_config),
        "fallback_config": asdict(config),
        "initialization_seeds": [int(seed) for seed in prereg["initialization_seeds"]],
        "update_rungs": list(stable.UPDATE_RUNGS),
        "validation_gate_contract": stable.VALIDATION_GATE_CONTRACT,
        "code_manifest": code_manifest,
        **FALSE_BOUNDARY,
    }
    output_dir.mkdir(parents=True)
    authority_file_sha256 = stable.sources._write_once_json(
        output_dir / "authority.json", authority
    )
    authority_seal_file_sha256 = stable.sources._write_once_json(
        output_dir / "authority-seal.json",
        {
            "schema": AUTHORITY_SEAL_SCHEMA,
            "authority_sha256": authority_file_sha256,
            "authority_file_sha256": authority_file_sha256,
            "preoutcome_authority_sha256": expected_preoutcome_authority_sha256,
        },
    )
    # Only after both fallback authority files are durable may validation
    # dataset bytes be opened.
    base_batches, validation_temporal_rows, source_access = stable._load_batches(
        source_root=source_root,
        prereg=prereg,
        config=primary_config,
        expected_source_receipt_sha256=dependencies["source_metadata"][
            "source_receipt_file_sha256"
        ],
        independent_verification=dependencies["independent"],
    )
    expansion_rows, expansion_access = v3._load_expansion_rows(
        expansion_root,
        dependencies["expansion"],
        prereg=prereg,
    )
    batches, augmentation = v3._append_train_c2_only(
        base_batches, expansion_rows, config=primary_config
    )
    if dependencies["source_metadata"]["validation_datasets"] != preoutcome[
        "base_source"
    ]["validation_datasets"]:
        raise MaskedMeanMaxFallbackError("base validation dataset digests changed")
    started = time.perf_counter()
    checkpoints = output_dir / "checkpoints"
    checkpoints.mkdir()
    receipts: dict[int, dict[int, dict[str, dict[str, Any]]]] = {}
    checkpoint_digests: dict[str, str] = {}
    checkpoint_reload: dict[str, dict[str, Any]] = {}
    for raw_seed in prereg["initialization_seeds"]:
        seed = int(raw_seed)
        trainer = meanmax.EEAxisMaskedMeanMaxTrainer(config, train_seed=seed, device="cpu")
        completed = 0
        seed_receipts: dict[int, dict[str, dict[str, Any]]] = {}
        for rung in stable.UPDATE_RUNGS:
            for _update in range(completed, rung):
                for route in ROUTE_NAMES:
                    trainer.update_route(route, batches.batch("train", route))
            completed = rung
            seed_receipts[rung] = {
                route: _masked_route_metrics(trainer, batches, route_index)
                for route_index, route in enumerate(ROUTE_NAMES)
            }
            checkpoint_name = f"init-{seed}-rung-{rung:06d}.pt"
            digest, _restored = _save_and_reload(
                path=checkpoints / checkpoint_name,
                authority_sha256=authority_file_sha256,
                trainer=trainer,
                seed=seed,
                rung=rung,
                metrics=seed_receipts[rung],
                batches=batches,
            )
            checkpoint_digests[checkpoint_name] = digest
            checkpoint_reload[checkpoint_name] = {
                "file_sha256": digest,
                "save_reload_validated": True,
                "update_count": rung * 3,
            }
        receipts[seed] = seed_receipts
    initialization_seeds = tuple(int(seed) for seed in prereg["initialization_seeds"])
    if len(initialization_seeds) != 3:
        raise MaskedMeanMaxFallbackError("fallback requires exactly three initializations")
    selected_rung, mean_ratios = stable.select_common_rung(
        receipts, initialization_seeds=initialization_seeds
    )
    selected_trainers: dict[int, Any] = {}
    for seed in initialization_seeds:
        checkpoint_name = f"init-{seed}-rung-{selected_rung:06d}.pt"
        checkpoint_path = checkpoints / checkpoint_name
        expected_checkpoint_sha256 = checkpoint_digests.get(checkpoint_name)
        if expected_checkpoint_sha256 is None or _sha256(checkpoint_path) != expected_checkpoint_sha256:
            raise MaskedMeanMaxFallbackError("selected checkpoint digest changed")
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        if (
            checkpoint.get("schema") != CHECKPOINT_SCHEMA
            or checkpoint.get("authority_sha256") != authority_file_sha256
            or checkpoint.get("initialization_seed") != seed
            or checkpoint.get("rung") != selected_rung
            or checkpoint.get("validation_metrics")
            != receipts[seed][selected_rung]
            or checkpoint.get("validation_dataset_bytes_opened") is not True
            or checkpoint.get("validation_metrics_computed") is not True
            or checkpoint.get("test_split_opened") is not False
            or checkpoint.get("held_out_ee_evaluated") is not False
        ):
            raise MaskedMeanMaxFallbackError("selected checkpoint identity changed")
        restored = meanmax.EEAxisMaskedMeanMaxTrainer(config, train_seed=seed, device="cpu")
        if restored.load_checkpoint_state(checkpoint["trainer"]) != selected_rung * 3:
            raise MaskedMeanMaxFallbackError("selected checkpoint reload update count changed")
        selected_trainers[seed] = restored
    action_effects = _masked_action_main_effect(selected_trainers, batches)
    collisions = stable._collision_census(
        batches,
        kappa_bits=config.kappa_bits,
        policy_digest=str(prereg["checkpoint_sha256"]),
    )
    c2_sensitivity = _masked_c2_anchor_sensitivity(
        selected_trainers, batches, validation_temporal_rows
    )
    state_mask_census = _state_mask_census(batches)
    gate = stable._gate(
        selected_rung=selected_rung,
        receipts=receipts,
        action_main_effects=action_effects,
        collisions=collisions,
        c2_sensitivity=c2_sensitivity,
    )
    status = _final_status(gate["status"])
    result = {
        "schema": RESULT_SCHEMA,
        "status": status,
        "claim_ceiling": CLAIM_CEILING,
        "authority_sha256": authority_file_sha256,
        "authority_seal_file_sha256": authority_seal_file_sha256,
        "trigger_status": TRIGGER_STATUS,
        "fallback_exhausted": True,
        "no_second_fallback_authorized": True,
        "selected_common_rung": selected_rung,
        "mean_model_to_strongest_null_ratio_by_rung": {
            str(rung): value for rung, value in mean_ratios.items()
        },
        "validation_receipts": {
            str(seed): {str(rung): values for rung, values in rows.items()}
            for seed, rows in receipts.items()
        },
        "deployment_action_main_effect_by_initialization": action_effects,
        "observability_collisions": collisions,
        "c2_anchor_sensitivity": c2_sensitivity,
        "state_mask_census": state_mask_census,
        "context_selection_provenance": CONTEXT_SELECTION_PROVENANCE,
        "gate": gate,
        "checkpoint_file_sha256s": checkpoint_digests,
        "checkpoint_save_reload": checkpoint_reload,
        "source_partition_expanded": "TRAIN",
        "expanded_route": "C2",
        "base_validation_batches_unchanged": True,
        "augmentation": augmentation,
        "expansion_access": expansion_access,
        "source_access": source_access,
        "elapsed_s": time.perf_counter() - started,
        "test_dataset_paths_opened": [],
        **POST_METRIC_BOUNDARY,
    }
    if _code_manifest() != code_manifest:
        raise MaskedMeanMaxFallbackError("fallback code changed during execution")
    result_file_sha256 = stable.sources._write_once_json(
        output_dir / "result.json", result
    )
    result_seal_file_sha256 = stable.sources._write_once_json(
        output_dir / "result-seal.json",
        {
            "schema": RESULT_SEAL_SCHEMA,
            "authority_sha256": authority_file_sha256,
            "authority_seal_file_sha256": authority_seal_file_sha256,
            "result_file_sha256": result_file_sha256,
        },
    )
    stable.sources._write_once_json(
        output_dir / "status.json",
        {
            "schema": SCHEMA,
            "status": "complete",
            "result_status": status,
            "authority_sha256": authority_file_sha256,
            "result_file_sha256": result_file_sha256,
            "result_seal_file_sha256": result_seal_file_sha256,
            "elapsed_s": time.perf_counter() - started,
            **POST_METRIC_BOUNDARY,
        },
    )
    return {
        **result,
        "result_file_sha256": result_file_sha256,
        "result_seal_file_sha256": result_seal_file_sha256,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--independent-root", type=Path, required=True)
    parser.add_argument("--census-root", type=Path, required=True)
    parser.add_argument("--expansion-root", type=Path, required=True)
    parser.add_argument("--v3-root", type=Path, required=True)
    parser.add_argument("--preoutcome-authority", type=Path, required=True)
    parser.add_argument("--preoutcome-authority-seal", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-v3-authority-file-sha256", required=True)
    parser.add_argument("--expected-v3-authority-seal-file-sha256", required=True)
    parser.add_argument("--expected-v3-result-file-sha256", required=True)
    parser.add_argument("--expected-v3-result-seal-file-sha256", required=True)
    parser.add_argument("--expected-preoutcome-authority-sha256", required=True)
    parser.add_argument("--expected-preoutcome-authority-seal-sha256", required=True)
    args = parser.parse_args(argv)
    payload = run(
        source_root=args.source_root,
        independent_root=args.independent_root,
        census_root=args.census_root,
        expansion_root=args.expansion_root,
        v3_root=args.v3_root,
        preoutcome_authority_path=args.preoutcome_authority,
        preoutcome_authority_seal_path=args.preoutcome_authority_seal,
        output_dir=args.output_dir,
        expected_v3_authority_file_sha256=args.expected_v3_authority_file_sha256,
        expected_v3_authority_seal_file_sha256=args.expected_v3_authority_seal_file_sha256,
        expected_v3_result_file_sha256=args.expected_v3_result_file_sha256,
        expected_v3_result_seal_file_sha256=args.expected_v3_result_seal_file_sha256,
        expected_preoutcome_authority_sha256=args.expected_preoutcome_authority_sha256,
        expected_preoutcome_authority_seal_sha256=args.expected_preoutcome_authority_seal_sha256,
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
