#!/usr/bin/env python3
"""Run the fresh action-shared train/validation E1 screen without test or EE."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
import sys

for path in (REPO, REPO / "src", HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

source_spec = importlib.util.spec_from_file_location(
    "e1_action_shared_sources",
    HERE / "run_v03_e1_action_shared_sources.py",
)
if source_spec is None or source_spec.loader is None:
    raise RuntimeError("cannot load action-shared source authority")
sources_v2 = importlib.util.module_from_spec(source_spec)
source_spec.loader.exec_module(sources_v2)
sources_v2._install_protocol()
sources = sources_v2.source

from mcrl.algorithms.ee_axis_action_shared import (  # noqa: E402
    ACTION_SHARED_ALGORITHM,
    EEAxisActionSharedConfig,
    EEAxisActionSharedTrainer,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch, ROUTE_NAMES  # noqa: E402
from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.runtime.ee_axis_e1_ladder import (  # noqa: E402
    E1LadderBatches,
    pair_batch_digest,
)
from mcrl.runtime.ee_axis_instrument_validity import (  # noqa: E402
    compute_action_main_effect,
    compute_observability_collisions,
    compute_strong_baseline_pair_generalization,
)
from mcrl.runtime.ee_axis_opening_dataset import read_opening_dataset  # noqa: E402
from mcrl.runtime.ee_axis_opening_pairs import build_opening_route_batch  # noqa: E402
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM  # noqa: E402
from mcrl.runtime.ee_axis_temporal_dataset import read_temporal_dataset  # noqa: E402
from mcrl.runtime.ee_axis_temporal_pairs import build_temporal_route_batch  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v03-e1-action-shared-validation-v1"
AUTHORITY_SCHEMA = f"{SCHEMA}-authority"
RESULT_SCHEMA = f"{SCHEMA}-result"
RESULT_SEAL_SCHEMA = f"{SCHEMA}-result-seal"
VALIDATION_PREOUTCOME_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-action-shared-validation-preoutcome-authority-v1"
)
CLAIM_CEILING = "GO_500EP_SCREEN_ONLY_NO_TEST_NO_EE"
UPDATE_RUNGS = (3, 10, 30, 100, 300)
ACTION_MAIN_EFFECT_CEILING = 0.80
VALIDATION_GATE_CONTRACT = {
    "common_rung_selection": (
        "minimum-mean-model-to-strongest-null-ratio-across-routes-and-initializations"
    ),
    "route_gate": {
        "mean_skill_strictly_positive": True,
        "positive_initializations_minimum": 2,
    },
    "c2_estimand_gate": {
        "estimands": ["anchor_balanced", "each_leave_one_world_anchor_out"],
        "strongest_null_selection": (
            "minimum-estimand-specific-mae-over-action_only-zero-train_median"
        ),
        "mean_skill_strictly_positive": True,
        "positive_initializations_minimum": 2,
        "all_estimands_must_pass": True,
    },
    "action_main_effect_ceiling": ACTION_MAIN_EFFECT_CEILING,
    "zero_persistent_conflicting_collisions": True,
}


class ActionSharedValidationError(RuntimeError):
    """The amended validation authority or its execution failed closed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_once_json(path: Path, payload: object) -> str:
    return sources._write_once_json(path, payload)


def _read_hash_bound_json(path: Path) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in pairs:
            if key in payload:
                raise ActionSharedValidationError(
                    f"duplicate JSON key in hash-bound authority: {key}"
                )
            payload[key] = value
        return payload

    try:
        payload = json.loads(
            path.read_text(encoding="ascii"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ActionSharedValidationError(
            f"cannot parse hash-bound authority: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ActionSharedValidationError("hash-bound authority is not an object")
    return payload


def _load_validation_preoutcome_authority(
    path: Path,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    expected = sources._digest(
        expected_sha256,
        field="expected_validation_preoutcome_authority_sha256",
    )
    if path.is_symlink() or _sha256_file(path) != expected:
        raise ActionSharedValidationError("validation pre-outcome authority changed")
    authority = _read_hash_bound_json(path)
    if (
        authority.get("schema") != VALIDATION_PREOUTCOME_SCHEMA
        or authority.get("status")
        != "SEALED_AFTER_COLLECTION_BEFORE_ANY_OUTCOME_INSPECTION"
        or authority.get("test_outcomes_authorized") is not False
        or authority.get("held_out_ee_authorized") is not False
        or authority.get("validation_gate_contract") != VALIDATION_GATE_CONTRACT
    ):
        raise ActionSharedValidationError("validation pre-outcome contract changed")
    code_manifest = authority.get("code_manifest")
    if not isinstance(code_manifest, dict):
        raise ActionSharedValidationError("validation pre-outcome code manifest is absent")
    required_paths = (
        ".scratch/ee-axis-redesign/run_v03_e1_action_shared_validation.py",
        ".scratch/ee-axis-redesign/verify_v03_e1_action_shared_sources.py",
        "docs/MULTI-CATFISH-MCRL-V03-E1-ACTION-SHARED-AMENDMENT-2026-09-01.md",
        "src/mcrl/algorithms/ee_axis_action_shared.py",
        "src/mcrl/runtime/ee_axis_instrument_validity.py",
    )
    if set(code_manifest) != set(required_paths):
        raise ActionSharedValidationError("validation pre-outcome code closure changed")
    for relative in required_paths:
        candidate = REPO / relative
        if candidate.is_symlink() or _sha256_file(candidate) != code_manifest[relative]:
            raise ActionSharedValidationError(
                f"validation pre-outcome code changed: {relative}"
            )
    return authority


def _load_independent_source_verification(
    root: Path,
    *,
    expected_source_receipt_sha256: str,
    expected_result_sha256: str,
    expected_result_seal_sha256: str,
    expected_validation_preoutcome_authority_sha256: str,
) -> dict[str, Any]:
    result_path = root / "result.json"
    seal_path = root / "result-seal.json"
    expected_result = sources._digest(
        expected_result_sha256,
        field="expected_independent_source_verification_result_sha256",
    )
    expected_seal = sources._digest(
        expected_result_seal_sha256,
        field="expected_independent_source_verification_result_seal_sha256",
    )
    if (
        result_path.is_symlink()
        or seal_path.is_symlink()
        or _sha256_file(result_path) != expected_result
        or _sha256_file(seal_path) != expected_seal
    ):
        raise ActionSharedValidationError(
            "independent source verification differs from captured digests"
        )
    result = sources._read_canonical_json(result_path)
    seal = sources._read_canonical_json(seal_path)
    if (
        result.get("status") != "PASS_INDEPENDENT_4_3_0_NO_TEST"
        or result.get("test_outcomes_generated") is not False
        or result.get("test_dataset_documents_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or result.get("source_receipt_file_sha256")
        != expected_source_receipt_sha256
        or result.get("validation_preoutcome_authority_file_sha256")
        != expected_validation_preoutcome_authority_sha256
        or seal.get("result_file_sha256") != expected_result
        or seal.get("preoutcome_authority_file_sha256")
        != result.get("preoutcome_authority_file_sha256")
        or seal.get("validation_preoutcome_authority_file_sha256")
        != expected_validation_preoutcome_authority_sha256
    ):
        raise ActionSharedValidationError(
            "independent 4/3/0 no-test source verification is absent or invalid"
        )
    return {
        **result,
        "result_file_sha256": expected_result,
        "result_seal_file_sha256": expected_seal,
    }


def _load_source_authority(
    source_root: Path,
    *,
    independent_verification_root: Path,
    expected_source_receipt_sha256: str,
    expected_independent_result_sha256: str,
    expected_independent_result_seal_sha256: str,
    validation_preoutcome_authority: Mapping[str, Any],
    validation_preoutcome_authority_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Authenticate immutable source bytes without recomputing old code closure.

    The independent verifier already replayed the manifest-sensitive source
    checks in the immutable generation snapshot. Validation may therefore run
    with the safety-fixed checkpoint loader while binding that verifier's
    result instead of pretending the post-source code bytes are identical.
    """

    manifest = sources._read_canonical_json(source_root / "source-manifest.json")
    prereg = sources._read_canonical_json(source_root / "prereg.json")
    manifest_body = dict(manifest)
    manifest_digest = manifest_body.pop("source_manifest_sha256", None)
    prereg_body = dict(prereg)
    prereg_digest = prereg_body.pop("prereg_sha256", None)
    if (
        manifest_digest != sources._canonical_sha256(manifest_body)
        or prereg_digest != sources._canonical_sha256(prereg_body)
        or prereg.get("source_manifest_sha256") != manifest_digest
    ):
        raise ActionSharedValidationError("source manifest or prereg digest changed")
    expected_split = {
        str(seed): split_name
        for seed, split_name in sorted(sources_v2.SOURCE_SEED_SPLIT.items())
    }
    if prereg.get("source_seed_split") != expected_split:
        raise ActionSharedValidationError("source prereg is not the sealed 4/3/0 split")
    independent = _load_independent_source_verification(
        independent_verification_root,
        expected_source_receipt_sha256=expected_source_receipt_sha256,
        expected_result_sha256=expected_independent_result_sha256,
        expected_result_seal_sha256=expected_independent_result_seal_sha256,
        expected_validation_preoutcome_authority_sha256=(
            validation_preoutcome_authority_sha256
        ),
    )
    if (
        independent.get("preoutcome_authority_file_sha256")
        != validation_preoutcome_authority.get(
            "source_preoutcome_authority_file_sha256"
        )
    ):
        raise ActionSharedValidationError("independent source authority is not pre-C2 sealed")
    return manifest, prereg, independent


def _config_from_prereg(prereg: Mapping[str, Any]) -> EEAxisActionSharedConfig:
    learner = prereg.get("learner")
    if not isinstance(learner, dict):
        raise ActionSharedValidationError("source prereg lacks learner contract")
    if (
        learner.get("algorithm") != ACTION_SHARED_ALGORITHM
        or learner.get("scorer") != "local-action-shared-8-plus-4"
    ):
        raise ActionSharedValidationError("source prereg is not local action-shared")
    try:
        config = EEAxisActionSharedConfig(
            state_dim=EE_AXIS_STATE_DIM,
            action_dim=NUM_ACTIONS,
            hidden_layers=tuple(int(value) for value in learner["hidden_layers"]),
            activation=str(learner["activation"]),
            learning_rate=float.fromhex(learner["learning_rate_hex"]),
            kappa_bits=float.fromhex(learner["kappa_bits_hex"]),
            beta=float.fromhex(learner["beta_hex"]),
            loss_weights=tuple(
                float.fromhex(value) for value in learner["loss_weights_hex"]
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ActionSharedValidationError("source learner contract is malformed") from error
    if config.beta != 0.1 or config.learning_rate != 0.001:
        raise ActionSharedValidationError("beta or learning rate differs from amendment")
    return config


def _canonical_dataset_path(*, root: Path, raw: object, expected: str) -> Path:
    if type(raw) is not str or raw != expected:
        raise ActionSharedValidationError("dataset path changed")
    path = root / raw
    if path.is_symlink() or not path.is_file():
        raise ActionSharedValidationError("dataset is missing, non-regular, or a symlink")
    if path.resolve(strict=True).parent != root.resolve(strict=True):
        raise ActionSharedValidationError("dataset path escapes source-data")
    return path


def _unique_state_indices(states: np.ndarray, masks: np.ndarray) -> np.ndarray:
    seen: set[tuple[bytes, bytes]] = set()
    indices: list[int] = []
    for index, (state, mask) in enumerate(
        zip(states, masks, strict=True)
    ):
        key = (
            np.asarray(state, dtype="<f4").tobytes(),
            np.asarray(mask, dtype=np.bool_).tobytes(),
        )
        if key not in seen:
            seen.add(key)
            indices.append(index)
    return np.asarray(indices, dtype=np.int64)


def _load_batches(
    *,
    source_root: Path,
    prereg: Mapping[str, Any],
    config: EEAxisActionSharedConfig,
    expected_source_receipt_sha256: str,
    independent_verification: Mapping[str, Any],
) -> tuple[E1LadderBatches, tuple[Any, ...], dict[str, Any]]:
    data_root = source_root / "source-data"
    if source_root.is_symlink() or data_root.is_symlink() or not data_root.is_dir():
        raise ActionSharedValidationError("source root is not a regular publication")
    receipt_path = data_root / "receipt.json"
    expected_receipt = sources._digest(
        expected_source_receipt_sha256,
        field="expected_source_receipt_sha256",
    )
    if _sha256_file(receipt_path) != expected_receipt:
        raise ActionSharedValidationError("source receipt differs from captured digest")
    receipt = sources._read_canonical_json(receipt_path)
    index_path = data_root / "ladder-index.json"
    index = sources._read_canonical_json(index_path)
    if (
        index.get("schema") != sources.LADDER_INDEX_SCHEMA
        or index.get("test_split_opened") is not False
        or _sha256_file(index_path) != receipt.get("ladder_index_file_sha256")
        or receipt.get("status") != "PASS"
        or receipt.get("held_out_ee_evaluated") is not False
        or independent_verification.get("source_receipt_file_sha256")
        != expected_receipt
    ):
        raise ActionSharedValidationError("ladder index schema or test boundary changed")
    expected_split = {
        str(seed): split_name
        for seed, split_name in sorted(sources_v2.SOURCE_SEED_SPLIT.items())
    }
    if index.get("seed_split") != expected_split or "test" in expected_split.values():
        raise ActionSharedValidationError("ladder index is not the sealed 4/3/0 split")
    supplement_path = source_root / "action-shared-supplement-receipt.json"
    supplement_seal = sources._read_canonical_json(
        source_root / "action-shared-supplement-receipt-seal.json"
    )
    supplement = sources._read_canonical_json(supplement_path)
    if (
        supplement.get("status") != "PASS"
        or supplement.get("test_outcomes_generated") is not False
        or supplement.get("test_split_opened") is not False
        or supplement_seal.get("receipt_file_sha256") != _sha256_file(supplement_path)
        or independent_verification.get("supplement_receipt_file_sha256")
        != _sha256_file(supplement_path)
    ):
        raise ActionSharedValidationError("source supplement did not pass its no-test gate")

    opening: dict[str, dict[str, list[Any]]] = {
        "train": {"C1": [], "C3": []},
        "validation": {"C1": [], "C3": []},
    }
    temporal: dict[str, list[Any]] = {"train": [], "validation": []}
    opened: list[str] = []
    rows = index.get("datasets")
    if not isinstance(rows, dict) or set(rows) != set(expected_split):
        raise ActionSharedValidationError("ladder dataset index is incomplete")
    for seed_text, split_name in expected_split.items():
        entry = rows[seed_text]
        if not isinstance(entry, dict):
            raise ActionSharedValidationError("dataset index row is malformed")
        seed = int(seed_text)
        opening_path = _canonical_dataset_path(
            root=data_root,
            raw=entry.get("opening_path"),
            expected=f"opening-{seed}.json",
        )
        temporal_path = _canonical_dataset_path(
            root=data_root,
            raw=entry.get("temporal_path"),
            expected=f"temporal-{seed}.json",
        )
        opening_dataset = read_opening_dataset(opening_path)
        temporal_dataset = read_temporal_dataset(temporal_path)
        if (
            opening_dataset.verify() != entry["opening_dataset_sha256"]
            or temporal_dataset.verify() != entry["temporal_dataset_sha256"]
            or entry["opening_dataset_sha256"]
            != receipt["opening_dataset_sha256s"][seed_text]
            or entry["temporal_dataset_sha256"]
            != receipt["temporal_dataset_sha256s"][seed_text]
            or _sha256_file(opening_path)
            != receipt["opening_dataset_file_sha256s"][seed_text]
            or _sha256_file(temporal_path)
            != receipt["temporal_dataset_file_sha256s"][seed_text]
        ):
            raise ActionSharedValidationError("dataset digest changed")
        if (
            opening_dataset.source_manifest_sha256 != prereg["source_manifest_sha256"]
            or temporal_dataset.source_manifest_sha256 != prereg["source_manifest_sha256"]
            or opening_dataset.checkpoint_sha256 != prereg["checkpoint_sha256"]
            or temporal_dataset.checkpoint_sha256 != prereg["checkpoint_sha256"]
        ):
            raise ActionSharedValidationError("dataset lineage changed")
        opening[split_name]["C1"].extend(opening_dataset.c1_pairs)
        opening[split_name]["C3"].extend(opening_dataset.c3_pairs)
        temporal[split_name].extend(temporal_dataset.rows)
        opened.extend((opening_path.name, temporal_path.name))

    batches = E1LadderBatches(
        train=(
            build_opening_route_batch(opening["train"]["C1"]).pair_batch,
            build_temporal_route_batch(temporal["train"]).pair_batch,
            build_opening_route_batch(opening["train"]["C3"]).pair_batch,
        ),
        validation=(
            build_opening_route_batch(opening["validation"]["C1"]).pair_batch,
            build_temporal_route_batch(temporal["validation"]).pair_batch,
            build_opening_route_batch(opening["validation"]["C3"]).pair_batch,
        ),
    )
    for split_name in ("train", "validation"):
        for route in ROUTE_NAMES:
            batches.batch(split_name, route).validate(
                state_dim=config.state_dim,
                action_dim=config.action_dim,
            )
    return batches, tuple(temporal["validation"]), {
        "source_receipt_file_sha256": expected_receipt,
        "supplement_receipt_file_sha256": _sha256_file(supplement_path),
        "independent_source_verification_result_sha256": independent_verification[
            "result_file_sha256"
        ],
        "opened_dataset_paths": opened,
        "test_dataset_paths_opened": [],
        "test_split_opened": False,
    }


def _route_metrics(
    trainer: EEAxisActionSharedTrainer,
    batches: E1LadderBatches,
    route_index: int,
) -> dict[str, float | str | int | None]:
    route = ROUTE_NAMES[route_index]
    train = batches.batch("train", route)
    validation = batches.batch("validation", route)
    q = trainer.q_values(validation.states)[route_index]
    report = compute_strong_baseline_pair_generalization(
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


def select_common_rung(
    receipts: Mapping[int, Mapping[int, Mapping[str, Mapping[str, Any]]]],
    *,
    initialization_seeds: tuple[int, int, int],
) -> tuple[int, dict[int, float]]:
    if set(receipts) != set(initialization_seeds):
        raise ActionSharedValidationError("rung receipts lack an initialization")
    means: dict[int, float] = {}
    for rung in UPDATE_RUNGS:
        values: list[float] = []
        for seed in initialization_seeds:
            if set(receipts[seed]) != set(UPDATE_RUNGS):
                raise ActionSharedValidationError("rung receipts are incomplete")
            if set(receipts[seed][rung]) != set(ROUTE_NAMES):
                raise ActionSharedValidationError("route receipts are incomplete")
            for route in ROUTE_NAMES:
                value = receipts[seed][rung][route].get(
                    "model_to_strongest_null_mae_ratio"
                )
                if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    raise ActionSharedValidationError("rung ratio is non-finite")
                values.append(float(value))
        means[rung] = float(np.mean(values))
    return min(UPDATE_RUNGS, key=lambda rung: (means[rung], rung)), means


def _action_main_effect(
    trainers: Mapping[int, EEAxisActionSharedTrainer],
    batches: E1LadderBatches,
) -> dict[str, float]:
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
        [
            batches.batch("validation", route).action_masks
            for route in ROUTE_NAMES
        ],
        axis=0,
    )
    train_indices = _unique_state_indices(train_states, train_masks)
    validation_indices = _unique_state_indices(validation_states, validation_masks)
    values: dict[str, float] = {}
    for seed, trainer in trainers.items():
        train_scores = trainer.deployment_scores(train_states[train_indices])
        validation_scores = trainer.deployment_scores(
            validation_states[validation_indices]
        )
        values[str(seed)] = compute_action_main_effect(
            validation_scores=train_scores,
            validation_masks=train_masks[train_indices],
            test_scores=validation_scores,
            test_masks=validation_masks[validation_indices],
        ).action_main_effect_fraction
    return values


def _collision_census(
    batches: E1LadderBatches,
    *,
    kappa_bits: float,
    policy_digest: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for route in ROUTE_NAMES:
        combined = [batches.batch(split_name, route) for split_name in ("train", "validation")]
        states = np.concatenate([batch.states for batch in combined], axis=0)
        masks = np.concatenate([batch.action_masks for batch in combined], axis=0)
        references = np.concatenate([batch.reference_actions for batch in combined])
        candidates = np.concatenate([batch.candidate_actions for batch in combined])
        targets = np.concatenate([batch.target_surplus_bits for batch in combined]) / kappa_bits
        report = compute_observability_collisions(
            routes=[route] * states.shape[0],
            policy_digests=[policy_digest] * states.shape[0],
            states=states,
            masks=masks,
            reference_actions=references,
            candidate_actions=candidates,
            targets=targets,
        )
        result[route] = report.as_dict()
    return result


def _baseline_predictions(train: EEAxisPairBatch, validation: EEAxisPairBatch, kappa: float) -> dict[str, np.ndarray]:
    train_r = np.asarray(train.reference_actions, dtype=np.int64)
    train_c = np.asarray(train.candidate_actions, dtype=np.int64)
    train_y = np.asarray(train.target_surplus_bits, dtype=np.float64) / kappa
    design = np.zeros((train_y.size, NUM_ACTIONS), dtype=np.float64)
    index = np.arange(train_y.size)
    design[index, train_c] = 1.0
    design[index, train_r] = -1.0
    coefficients = np.linalg.lstsq(design, train_y, rcond=None)[0]
    val_r = np.asarray(validation.reference_actions, dtype=np.int64)
    val_c = np.asarray(validation.candidate_actions, dtype=np.int64)
    return {
        "action_only": coefficients[val_c] - coefficients[val_r],
        "zero": np.zeros(val_r.size, dtype=np.float64),
        "train_median": np.full(val_r.size, np.median(train_y), dtype=np.float64),
    }


def _c2_estimand_report(
    *,
    baseline_anchor_errors: Mapping[str, np.ndarray],
    model_anchor_errors: Mapping[int, np.ndarray],
    keep: np.ndarray,
) -> dict[str, Any]:
    baseline_maes = {
        name: float(np.mean(errors[keep]))
        for name, errors in baseline_anchor_errors.items()
    }
    baseline_name = min(
        baseline_maes,
        key=lambda name: (baseline_maes[name], name),
    )
    denominator = baseline_maes[baseline_name]
    if denominator <= 0.0:
        raise ActionSharedValidationError(
            "C2 estimand-specific strongest baseline has no positive error"
        )
    skills = {
        str(seed): 1.0 - float(np.mean(errors[keep]) / denominator)
        for seed, errors in sorted(model_anchor_errors.items())
    }
    values = list(skills.values())
    positive = sum(value > 0.0 for value in values)
    mean_skill = float(np.mean(values))
    return {
        "strongest_baseline_name": baseline_name,
        "strongest_baseline_mae": denominator,
        "baseline_maes": baseline_maes,
        "skills_by_initialization": skills,
        "mean_skill": mean_skill,
        "positive_initializations": positive,
        "pass": bool(mean_skill > 0.0 and positive >= 2),
    }


def _c2_anchor_sensitivity(
    trainers: Mapping[int, EEAxisActionSharedTrainer],
    batches: E1LadderBatches,
    temporal_rows: tuple[Any, ...],
) -> dict[str, Any]:
    train = batches.batch("train", "C2")
    validation = batches.batch("validation", "C2")
    if len(temporal_rows) != validation.states.shape[0]:
        raise ActionSharedValidationError("C2 metadata no longer aligns with its batch")
    target = np.asarray(validation.target_surplus_bits, dtype=np.float64) / next(
        iter(trainers.values())
    ).config.kappa_bits
    baseline_candidates = _baseline_predictions(
        train,
        validation,
        next(iter(trainers.values())).config.kappa_bits,
    )
    groups: dict[tuple[int, int], list[int]] = {}
    for index, row in enumerate(temporal_rows):
        groups.setdefault((int(row.seed), int(row.step_index)), []).append(index)
    group_keys = tuple(sorted(groups))
    group_indices = tuple(groups[key] for key in group_keys)
    if len(group_keys) < 2:
        raise ActionSharedValidationError("C2 requires at least two validation world anchors")
    baseline_anchor_errors = {
        name: np.asarray(
            [
                np.mean(np.abs(prediction - target)[indices])
                for indices in group_indices
            ],
            dtype=np.float64,
        )
        for name, prediction in baseline_candidates.items()
    }
    model_anchor_errors: dict[int, np.ndarray] = {}
    for seed, trainer in trainers.items():
        q = trainer.q_values(validation.states)[1]
        index = np.arange(target.size)
        model_prediction = (
            q[index, validation.candidate_actions]
            - q[index, validation.reference_actions]
        )
        model_error = np.abs(model_prediction - target)
        model_anchor_errors[seed] = np.asarray(
            [np.mean(model_error[indices]) for indices in group_indices],
            dtype=np.float64,
        )

    all_anchors = np.ones(len(group_keys), dtype=bool)
    balanced = _c2_estimand_report(
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
                **_c2_estimand_report(
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


def _gate(
    *,
    selected_rung: int,
    receipts: Mapping[int, Mapping[int, Mapping[str, Mapping[str, Any]]]],
    action_main_effects: Mapping[str, float],
    collisions: Mapping[str, Mapping[str, Any]],
    c2_sensitivity: Mapping[str, Any],
) -> dict[str, Any]:
    route_gate: dict[str, Any] = {}
    for route in ROUTE_NAMES:
        skills = [
            float(receipts[seed][selected_rung][route]["skill_vs_strongest_null"])
            for seed in sorted(receipts)
        ]
        route_gate[route] = {
            "skills": skills,
            "mean_skill": float(np.mean(skills)),
            "positive_initializations": sum(skill > 0.0 for skill in skills),
            "pass": bool(np.mean(skills) > 0.0 and sum(skill > 0.0 for skill in skills) >= 2),
        }
    collision_pass = all(
        int(report["conflicting_sign_groups"]) == 0 for report in collisions.values()
    )
    action_effect_pass = all(
        math.isfinite(float(value)) and float(value) <= ACTION_MAIN_EFFECT_CEILING
        for value in action_main_effects.values()
    )
    local_pass = (
        all(report["pass"] for report in route_gate.values())
        and collision_pass
        and action_effect_pass
        and bool(c2_sensitivity["same_positive_direction"])
    )
    if local_pass:
        status = "GO_500EP_SCREEN_ONLY"
    elif (
        route_gate["C1"]["pass"]
        and route_gate["C2"]["pass"]
        and not route_gate["C3"]["pass"]
        and collision_pass
        and action_effect_pass
        and bool(c2_sensitivity["same_positive_direction"])
    ):
        status = "EVALUATE_MASKED_MEANMAX_ONCE"
    else:
        status = "STOP_ACTION_SHARED_VALIDATION"
    return {
        "status": status,
        "route_gate": route_gate,
        "collision_pass": collision_pass,
        "action_main_effect_pass": action_effect_pass,
        "c2_anchor_sensitivity_pass": bool(c2_sensitivity["same_positive_direction"]),
    }


def _save_checkpoint(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or path.is_symlink():
        raise ActionSharedValidationError("refusing to overwrite a checkpoint")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        torch.save(dict(payload), temporary)
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return _sha256_file(path)


def run(
    *,
    source_root: Path,
    independent_verification_root: Path,
    validation_preoutcome_authority_path: Path,
    output_dir: Path,
    expected_source_receipt_sha256: str,
    expected_independent_result_sha256: str,
    expected_independent_result_seal_sha256: str,
    expected_validation_preoutcome_authority_sha256: str,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to overwrite action-shared validation")
    validation_preoutcome_authority = _load_validation_preoutcome_authority(
        validation_preoutcome_authority_path,
        expected_sha256=expected_validation_preoutcome_authority_sha256,
    )
    _manifest, prereg, independent_verification = _load_source_authority(
        source_root,
        independent_verification_root=independent_verification_root,
        expected_source_receipt_sha256=expected_source_receipt_sha256,
        expected_independent_result_sha256=expected_independent_result_sha256,
        expected_independent_result_seal_sha256=(
            expected_independent_result_seal_sha256
        ),
        validation_preoutcome_authority=validation_preoutcome_authority,
        validation_preoutcome_authority_sha256=(
            expected_validation_preoutcome_authority_sha256
        ),
    )
    config = _config_from_prereg(prereg)
    batches, temporal_rows, access = _load_batches(
        source_root=source_root,
        prereg=prereg,
        config=config,
        expected_source_receipt_sha256=expected_source_receipt_sha256,
        independent_verification=independent_verification,
    )
    output_dir.mkdir(parents=True)
    checkpoints = output_dir / "checkpoints"
    checkpoints.mkdir()
    source_files = (
        Path(__file__),
        REPO / "src/mcrl/algorithms/ee_axis_action_shared.py",
        REPO / "src/mcrl/runtime/ee_axis_instrument_validity.py",
    )
    code_manifest = {
        str(path.relative_to(REPO)): _sha256_file(path) for path in source_files
    }
    batch_digests = {
        split_name: {
            route: pair_batch_digest(batches.batch(split_name, route))
            for route in ROUTE_NAMES
        }
        for split_name in ("train", "validation")
    }
    authority = {
        "schema": AUTHORITY_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "source_prereg_sha256": prereg["prereg_sha256"],
        "source_manifest_sha256": prereg["source_manifest_sha256"],
        "validation_preoutcome_authority_file_sha256": (
            expected_validation_preoutcome_authority_sha256
        ),
        "independent_source_verification_result_sha256": (
            expected_independent_result_sha256
        ),
        "independent_source_verification_result_seal_sha256": (
            expected_independent_result_seal_sha256
        ),
        "source_access": access,
        "config": asdict(config),
        "initialization_seeds": prereg["initialization_seeds"],
        "update_rungs": list(UPDATE_RUNGS),
        "validation_gate_contract": VALIDATION_GATE_CONTRACT,
        "code_manifest": code_manifest,
        "batch_digests": batch_digests,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    authority["authority_sha256"] = sources._canonical_sha256(authority)
    _write_once_json(output_dir / "authority.json", authority)

    started = time.perf_counter()
    receipts: dict[int, dict[int, dict[str, dict[str, Any]]]] = {}
    checkpoint_digests: dict[str, str] = {}
    for raw_seed in prereg["initialization_seeds"]:
        seed = int(raw_seed)
        trainer = EEAxisActionSharedTrainer(config, train_seed=seed, device="cpu")
        completed = 0
        seed_receipts: dict[int, dict[str, dict[str, Any]]] = {}
        for rung in UPDATE_RUNGS:
            for _update in range(completed, rung):
                for route in ROUTE_NAMES:
                    trainer.update_route(route, batches.batch("train", route))
            completed = rung
            seed_receipts[rung] = {
                route: _route_metrics(trainer, batches, route_index)
                for route_index, route in enumerate(ROUTE_NAMES)
            }
            checkpoint_name = f"init-{seed}-rung-{rung:06d}.pt"
            checkpoint_digests[checkpoint_name] = _save_checkpoint(
                checkpoints / checkpoint_name,
                {
                    "schema": f"{SCHEMA}-checkpoint",
                    "authority_sha256": authority["authority_sha256"],
                    "initialization_seed": seed,
                    "rung": rung,
                    "validation_metrics": seed_receipts[rung],
                    "trainer": trainer.checkpoint_state(update_count=rung * 3),
                    "test_split_opened": False,
                    "held_out_ee_evaluated": False,
                },
            )
        receipts[seed] = seed_receipts

    initialization_seeds = tuple(int(seed) for seed in prereg["initialization_seeds"])
    if len(initialization_seeds) != 3:
        raise ActionSharedValidationError("validation requires three initializations")
    selected_rung, mean_ratios = select_common_rung(
        receipts,
        initialization_seeds=initialization_seeds,  # type: ignore[arg-type]
    )
    trainers: dict[int, EEAxisActionSharedTrainer] = {}
    for seed in initialization_seeds:
        checkpoint_name = f"init-{seed}-rung-{selected_rung:06d}.pt"
        checkpoint_path = checkpoints / checkpoint_name
        if _sha256_file(checkpoint_path) != checkpoint_digests[checkpoint_name]:
            raise ActionSharedValidationError("selected checkpoint digest changed")
        checkpoint = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=False,
        )
        if (
            checkpoint.get("authority_sha256") != authority["authority_sha256"]
            or checkpoint.get("initialization_seed") != seed
            or checkpoint.get("rung") != selected_rung
            or checkpoint.get("schema") != f"{SCHEMA}-checkpoint"
            or checkpoint.get("validation_metrics")
            != receipts[seed][selected_rung]
            or checkpoint.get("test_split_opened") is not False
            or checkpoint.get("held_out_ee_evaluated") is not False
        ):
            raise ActionSharedValidationError("selected checkpoint identity changed")
        trainer = EEAxisActionSharedTrainer(config, train_seed=seed, device="cpu")
        if trainer.load_checkpoint_state(checkpoint["trainer"]) != selected_rung * 3:
            raise ActionSharedValidationError("selected checkpoint update count changed")
        trainers[seed] = trainer
    action_effects = _action_main_effect(trainers, batches)
    collisions = _collision_census(
        batches,
        kappa_bits=config.kappa_bits,
        policy_digest=str(prereg["checkpoint_sha256"]),
    )
    c2_sensitivity = _c2_anchor_sensitivity(trainers, batches, temporal_rows)
    gate = _gate(
        selected_rung=selected_rung,
        receipts=receipts,
        action_main_effects=action_effects,
        collisions=collisions,
        c2_sensitivity=c2_sensitivity,
    )
    result = {
        "schema": RESULT_SCHEMA,
        "status": gate["status"],
        "claim_ceiling": CLAIM_CEILING,
        "authority_sha256": authority["authority_sha256"],
        "selected_common_rung": selected_rung,
        "mean_model_to_strongest_null_ratio_by_rung": {
            str(rung): value for rung, value in mean_ratios.items()
        },
        "validation_receipts": {
            str(seed): {
                str(rung): values for rung, values in seed_rows.items()
            }
            for seed, seed_rows in receipts.items()
        },
        "deployment_action_main_effect_by_initialization": action_effects,
        "observability_collisions": collisions,
        "c2_anchor_sensitivity": c2_sensitivity,
        "gate": gate,
        "checkpoint_file_sha256s": checkpoint_digests,
        "selected_checkpoint_files": {
            str(seed): f"checkpoints/init-{seed}-rung-{selected_rung:06d}.pt"
            for seed in initialization_seeds
        },
        "elapsed_s": time.perf_counter() - started,
        "test_dataset_paths_opened": [],
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    result_file_sha256 = _write_once_json(output_dir / "result.json", result)
    seal = {
        "schema": RESULT_SEAL_SCHEMA,
        "authority_sha256": authority["authority_sha256"],
        "result_file_sha256": result_file_sha256,
    }
    seal_file_sha256 = _write_once_json(output_dir / "result-seal.json", seal)
    return {
        **result,
        "result_file_sha256": result_file_sha256,
        "result_seal_file_sha256": seal_file_sha256,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--independent-source-verification-root", type=Path, required=True)
    parser.add_argument("--validation-preoutcome-authority", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-source-receipt-sha256", required=True)
    parser.add_argument("--expected-independent-result-sha256", required=True)
    parser.add_argument("--expected-independent-result-seal-sha256", required=True)
    parser.add_argument(
        "--expected-validation-preoutcome-authority-sha256", required=True
    )
    args = parser.parse_args(argv)
    result = run(
        source_root=args.source_root,
        independent_verification_root=args.independent_source_verification_root,
        validation_preoutcome_authority_path=args.validation_preoutcome_authority,
        output_dir=args.output_dir,
        expected_source_receipt_sha256=args.expected_source_receipt_sha256,
        expected_independent_result_sha256=args.expected_independent_result_sha256,
        expected_independent_result_seal_sha256=(
            args.expected_independent_result_seal_sha256
        ),
        expected_validation_preoutcome_authority_sha256=(
            args.expected_validation_preoutcome_authority_sha256
        ),
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
