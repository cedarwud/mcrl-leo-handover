#!/usr/bin/env python3
"""Seal and generate fresh C1/C2/C3 source data for E1.

``prepare`` seals the source manifest, preregistration, and every C2
pre-outcome candidate schedule without running a detached forecast.  A later
``generate`` invocation verifies those exact bytes before it creates opening
or temporal counterfactual outcomes.  No Q function is updated here and no EE
endpoint is evaluated.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_V03 = REPO / ".scratch" / "c2-v03"
for path in (HERE, C2_V03, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_c2_v03_deterministic_plumbing_probe as c2_probe  # noqa: E402
import run_c2_v03_real_backend_smoke as c2_backend_smoke  # noqa: E402
import run_c2_v03_real_temporal_pair_smoke as c2_pair_smoke  # noqa: E402
import run_v03_phase1_informed_corpus as phase1  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_e1_c2_schedule import (  # noqa: E402
    E1C2PreOutcomeSchedule,
    E1C2ScheduleCluster,
    e1_c2_world_anchor_sha256,
    load_e1_c2_schedule,
    seal_e1_c2_schedule,
)
from mcrl.runtime.ee_axis_e1_split import (  # noqa: E402
    E1PairIndexRow,
    verify_e1_partition,
    verify_e1_seed_split,
    verify_full_sibling_groups,
)
from mcrl.runtime.ee_axis_opening_dataset import (  # noqa: E402
    EEAxisOpeningDataset,
    read_opening_dataset,
    write_opening_dataset,
)
from mcrl.runtime.ee_axis_temporal_dataset import (  # noqa: E402
    EEAxisTemporalDataset,
    read_temporal_dataset,
    write_temporal_dataset,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
)


SOURCE_MANIFEST_SCHEMA = "multi-catfish-mcrl-v03-e1-source-manifest-v1"
PREREG_SCHEMA = "multi-catfish-mcrl-v03-e1-source-prereg-v1"
PREPARE_RECEIPT_SCHEMA = "multi-catfish-mcrl-v03-e1-source-prepare-receipt-v1"
SOURCE_RECEIPT_SCHEMA = "multi-catfish-mcrl-v03-e1-fresh-source-receipt-v1"
LADDER_INDEX_SCHEMA = "multi-catfish-mcrl-v03-e1-ladder-source-index-v1"
TEST_INDEX_SCHEMA = "multi-catfish-mcrl-v03-e1-test-source-index-v1"
CLAIM_CEILING = "FRESH_SOURCE_AND_INSTRUMENT_DATA_ONLY_NOT_EE_EFFICACY"

SOURCE_SEED_SPLIT = {
    2026091001: "train",
    2026091002: "train",
    2026091003: "train",
    2026091004: "validation",
    2026091005: "test",
    2026091006: "test",
}
INITIALIZATION_SEEDS = (2026091101, 2026091102, 2026091103)
BURNED_SOURCE_SEEDS = tuple(
    [*range(2026082401, 2026082414)]
    + [2026082801]
    + list(range(2026083101, 2026083106))
    + [2026083111, 2026090101, 2026090102, 2026090103, 2026090104, 2026090105]
    + [2026090201, 2026090202]
)
OPENING_ANCHORS_PER_SEED = 5
OPENING_FOCAL_USERS_PER_ANCHOR = 2
OPENING_SOURCE_STEPS_PER_SEED = 10
OPENING_MINIMUM_CLUSTERS_PER_SEED = 10
OPENING_MINIMUM_INFERENCE_ANCHORS_PER_SEED = 5
C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED = 12
C2_MINIMUM_SCHEDULED_CLUSTERS_PER_SEED = 10
C2_MINIMUM_COMPLETE_CLUSTERS_PER_SEED = 10
C2_MINIMUM_SCHEDULED_ANCHORS_PER_SEED = 3
C2_MINIMUM_COMPLETE_ANCHORS_PER_SEED = 3
C2_MAX_FOCAL_USERS_PER_ANCHOR = 5
MINIMUM_INFERENCE_ANCHORS = {
    "C1": {"train": 15, "validation": 5, "test": 10},
    "C2": {"train": 9, "validation": 3, "test": 6},
    "C3": {"train": 15, "validation": 5, "test": 10},
}
USERS = 100
BASE_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
BASE_CHECKPOINT_DIR = REPO / "artifacts" / "training-2026-08-25-rerun01" / "main"
CALIBRATION_RECEIPT = (
    REPO
    / "artifacts"
    / "multi-catfish-v03-three-route-real-smoke-20260831"
    / "receipt.json"
)
E1_LEARNING_RATE = 0.001
E1_HIDDEN_LAYERS = (100, 50, 50)
E1_ACTIVATION = "tanh"


class E1FreshSourceError(RuntimeError):
    """Fresh E1 source authority or materialization failed closed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise E1FreshSourceError("payload is not finite canonical JSON") from error


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _opaque_regular_file_sha256(path: Path) -> str:
    """Hash sealed bytes without parsing them or following a symlink."""

    if path.is_symlink() or not path.is_file():
        raise E1FreshSourceError(f"sealed opaque file is missing or non-regular: {path}")
    return _file_sha256(path)


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise E1FreshSourceError(f"{field} must be lowercase SHA-256")
    return value


def _write_once_json(path: Path, payload: object) -> str:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite sealed E1 file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(payload) + b"\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return hashlib.sha256(encoded).hexdigest()


def _write_runtime_status(path: Path, payload: object) -> None:
    """Atomically replace non-authoritative progress telemetry."""

    if path.is_symlink():
        raise E1FreshSourceError("runtime status path may not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(payload) + b"\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _read_canonical_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise E1FreshSourceError(f"sealed E1 file is missing or not regular: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise E1FreshSourceError(f"sealed E1 file is invalid JSON: {path}") from error
    if not isinstance(payload, dict):
        raise E1FreshSourceError(f"sealed E1 file is not an object: {path}")
    if raw != _canonical_bytes(payload) + b"\n":
        raise E1FreshSourceError(f"sealed E1 file is not canonical: {path}")
    return payload


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO.resolve()))
    except ValueError as error:
        raise E1FreshSourceError(f"source path lies outside repository: {path}") from error


def _source_paths() -> tuple[Path, ...]:
    paths: list[Path] = list(_default_code_paths())
    paths.extend(sorted(C2_V03.glob("*.py")))
    paths.extend(sorted((REPO / ".scratch" / "catfish-oracle-gate").glob("*.py")))
    paths.extend(
        [
            Path(c2_probe.__file__),
            Path(c2_backend_smoke.__file__),
            Path(c2_pair_smoke.__file__),
            Path(phase1.__file__),
            Path(phase1.opening_smoke.__file__),
            REPO / ".scratch" / "ee-axis-redesign" / "run_c3_unilateral_oracle_pilot.py",
            REPO / "scripts" / "run_head_pivotality_probe.py",
            Path(__file__),
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_e1_c2_schedule.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_e1_split.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_c1_selector.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_source_selectors.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_opening_runner.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_opening_source.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_opening_dataset.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_capture.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_pairs.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_dataset.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_state.py",
        ]
    )
    unique = tuple(sorted({path.resolve() for path in paths}, key=lambda item: str(item)))
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise E1FreshSourceError(f"source manifest has missing paths: {missing}")
    return unique


def _build_source_manifest() -> dict[str, Any]:
    files = [
        {"path": _relative(path), "sha256": _file_sha256(path)}
        for path in _source_paths()
    ]
    body = {"schema": SOURCE_MANIFEST_SCHEMA, "files": files}
    return {**body, "source_manifest_sha256": _canonical_sha256(body)}


def _validate_source_manifest(payload: Mapping[str, Any]) -> str:
    current = _build_source_manifest()
    if dict(payload) != current:
        raise E1FreshSourceError("current source closure differs from sealed E1 manifest")
    return _digest(payload.get("source_manifest_sha256"), field="source_manifest_sha256")


def _policy_sha256() -> str:
    return _canonical_sha256(
        {
            "c2_policy_version": c2_pair_smoke.core.CANDIDATE_VERSION,
            "source_rules": ["incumbent-hold", "max-lagged-candidate-sinr-rival"],
            "compositor_version": c2_pair_smoke.backend.POLICY_COMPOSITOR_VERSION,
            "forecast_schema": c2_pair_smoke.backend.FORECAST_SCHEMA,
            "fading_mode": c2_pair_smoke.KEYED_FADING,
        }
    )


def _build_preregistration(
    *,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    environment_source_sha256: str,
    reward_source_sha256: str,
    learner_contract: Mapping[str, Any],
) -> dict[str, Any]:
    verify_e1_seed_split(SOURCE_SEED_SPLIT, burned_seeds=BURNED_SOURCE_SEEDS)
    body = {
        "schema": PREREG_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "endpoint": "NO_EE_ENDPOINT_IN_E1_SOURCE_OR_LADDER",
        "source_manifest_sha256": source_manifest_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "c2_policy_sha256": _policy_sha256(),
        "learner": dict(learner_contract),
        "source_seed_split": {
            str(seed): split for seed, split in sorted(SOURCE_SEED_SPLIT.items())
        },
        "burned_source_seeds": list(BURNED_SOURCE_SEEDS),
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "update_rungs_per_head": [10, 100, 1_000, 10_000],
        "opening_source_geometry": {
            "anchors_per_seed": OPENING_ANCHORS_PER_SEED,
            "focal_users_per_anchor": OPENING_FOCAL_USERS_PER_ANCHOR,
            "source_steps_per_seed": OPENING_SOURCE_STEPS_PER_SEED,
            "minimum_intervention_clusters_per_seed": OPENING_MINIMUM_CLUSTERS_PER_SEED,
            "minimum_inference_anchors_per_seed": OPENING_MINIMUM_INFERENCE_ANCHORS_PER_SEED,
            "full_legal_alternative_siblings": True,
        },
        "c2_source_geometry": {
            "minimum_scheduled_clusters_per_seed": C2_MINIMUM_SCHEDULED_CLUSTERS_PER_SEED,
            "maximum_scheduled_clusters_per_seed": C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED,
            "minimum_complete_clusters_per_seed": C2_MINIMUM_COMPLETE_CLUSTERS_PER_SEED,
            "maximum_focal_users_per_anchor": C2_MAX_FOCAL_USERS_PER_ANCHOR,
            "minimum_scheduled_anchors_per_seed": C2_MINIMUM_SCHEDULED_ANCHORS_PER_SEED,
            "minimum_complete_anchors_per_seed": C2_MINIMUM_COMPLETE_ANCHORS_PER_SEED,
            "retain_all_censors": True,
        },
        "minimum_clusters": {"train": 30, "validation": 10, "test": 20},
        "inference_units": {
            "C1": "source-seed-plus-anchor",
            "C2_primary": "source-seed-plus-anchor-plus-focal-user-conditional-on-anchor",
            "C2_sensitivity": "leave-one-anchor-out-and-anchor-balanced",
            "C3": "source-seed-plus-anchor",
        },
        "minimum_inference_anchors": MINIMUM_INFERENCE_ANCHORS,
        "test_opening_rule": "validation-selects-one-common-rung-then-test-opens-once",
    }
    return {**body, "prereg_sha256": _canonical_sha256(body)}


def _learner_contract(*, checkpoint_sha256: str) -> dict[str, Any]:
    try:
        payload = json.loads(CALIBRATION_RECEIPT.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise E1FreshSourceError("cannot read frozen E1 calibration receipt") from error
    if not isinstance(payload, dict) or payload.get("checkpoint_sha256") != checkpoint_sha256:
        raise E1FreshSourceError("frozen calibration and E1 checkpoint disagree")
    try:
        kappa_bits = float(payload["kappa_bits"])
        lambda_bits_per_j = float(payload["lambda_bits_per_j"])
        beta = float(payload["beta"])
        loss_weights = [float(value) for value in payload["loss_weights"]]
    except (KeyError, TypeError, ValueError) as error:
        raise E1FreshSourceError("frozen calibration receipt is malformed") from error
    numeric = [kappa_bits, lambda_bits_per_j, beta, *loss_weights]
    if (
        not all(math.isfinite(value) for value in numeric)
        or kappa_bits <= 0.0
        or lambda_bits_per_j <= 0.0
        or beta < 0.0
        or len(loss_weights) != 3
        or any(value <= 0.0 for value in loss_weights)
    ):
        raise E1FreshSourceError("frozen learner calibration is non-finite or invalid")
    return {
        "algorithm": "multi-catfish-mcrl-ee-axis-v03-pairwise",
        "learning_rate_hex": E1_LEARNING_RATE.hex(),
        "hidden_layers": list(E1_HIDDEN_LAYERS),
        "activation": E1_ACTIVATION,
        "kappa_bits_hex": kappa_bits.hex(),
        "lambda_bits_per_j_hex": lambda_bits_per_j.hex(),
        "beta_hex": beta.hex(),
        "loss_weights_hex": [value.hex() for value in loss_weights],
        "calibration_receipt_path": _relative(CALIBRATION_RECEIPT),
        "calibration_receipt_file_sha256": _file_sha256(CALIBRATION_RECEIPT),
    }


def _schedule_rng(prereg_sha256: str, *, seed: int, step: int) -> np.random.Generator:
    material = f"multi-catfish-v03-e1-c2-schedule-v1:{prereg_sha256}:{seed}:{step}".encode("ascii")
    value = int.from_bytes(hashlib.sha256(material).digest()[:16], "big")
    return np.random.Generator(np.random.PCG64(value))


def _candidate_action(prepared: Any) -> int:
    focal_user = int(prepared.anchor.focal_user)
    matches = [
        int(binding.action)
        for binding in prepared.anchor.action_bindings_by_user[focal_user]
        if tuple(binding.physical_key) == tuple(prepared.candidate_key)
    ]
    if len(matches) != 1:
        raise E1FreshSourceError("prepared C2 candidate lacks one opening action binding")
    return matches[0]


def _cluster_field_sha256(prepared: Any) -> str:
    anchor = prepared.anchor
    return KeyedFadingField.from_components(
        c2_pair_smoke.backend.FORECAST_SCHEMA,
        anchor.checkpoint_sha256,
        anchor.anchor_sha256,
        anchor.focal_user,
        anchor.evaluation_seed,
    ).root_digest


def _anchor_schedule_sha256_from_cluster(cluster: Any) -> str:
    return _canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v03-e1-c2-anchor-schedule-v1",
            "source_seed": int(cluster.source_seed),
            "anchor_sha256": str(cluster.anchor_sha256),
            "world_anchor_sha256": str(cluster.world_anchor_sha256),
            "anchor_step": int(cluster.anchor_step),
            "focal_user": int(cluster.focal_user),
            "reference_action": int(cluster.reference_action),
            "candidate_action": int(cluster.candidate_action),
            "reference_physical_key": [
                int(value) for value in cluster.reference_physical_key
            ],
            "candidate_physical_key": [
                int(value) for value in cluster.candidate_physical_key
            ],
            "candidate_source_rule": str(cluster.candidate_source_rule),
        }
    )


def _discover_c2_schedule(
    *,
    trainer: Any,
    archive: Any,
    seed: int,
    prereg_sha256: str,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    environment_source_sha256: str,
    reward_source_sha256: str,
) -> tuple[E1C2PreOutcomeSchedule, dict[str, Any]]:
    wrapped = loader._make_environment(archive, users=USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    clusters: list[E1C2ScheduleCluster] = []
    rejected: list[dict[str, Any]] = []
    steps_per_episode = int(wrapped.environment.driver.config.steps_per_episode)
    while int(observation.step_index) <= c2_backend_smoke.MAX_ANCHOR_STEP:
        main_actions, main_physical = c2_backend_smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        step = int(observation.step_index)
        departures = c2_pair_smoke._departure_users(wrapped, main_physical)
        remaining = steps_per_episode - step
        if departures and remaining >= c2_pair_smoke.core.HOLD_STEPS + 1:
            rng = _schedule_rng(prereg_sha256, seed=seed, step=step)
            ordered = rng.permutation(np.asarray(departures, dtype=np.int64)).tolist()
            for raw_focal in ordered[:C2_MAX_FOCAL_USERS_PER_ANCHOR]:
                focal_user = int(raw_focal)
                try:
                    service = c2_pair_smoke.backend.C2TemporalForkTrainerBackend(
                        wrapped=wrapped,
                        states=states,
                        masks=masks,
                        observation=observation,
                        env_rng=env_rng,
                        trainer=trainer,
                        checkpoint_sha256=checkpoint_sha256,
                        environment_source_sha256=environment_source_sha256,
                        reward_source_sha256=reward_source_sha256,
                        evaluation_seed=seed,
                        focal_user=focal_user,
                        forecast_fading_mode=c2_pair_smoke.KEYED_FADING,
                    )
                    prepared = service.prepare_hold_or_max_lagged_gain_rival(
                        focal_user=focal_user
                    )
                    reference_key = prepared.anchor.main_physical_actions[focal_user]
                    if reference_key is None:
                        raise E1FreshSourceError("scheduled C2 reference lacks physical identity")
                    candidate_action = _candidate_action(prepared)
                    world_anchor_sha256 = e1_c2_world_anchor_sha256(
                        source_seed=seed, anchor_step=step
                    )
                    schedule_body = {
                        "schema": "multi-catfish-mcrl-v03-e1-c2-anchor-schedule-v1",
                        "source_seed": seed,
                        "anchor_sha256": prepared.anchor.anchor_sha256,
                        "world_anchor_sha256": world_anchor_sha256,
                        "anchor_step": step,
                        "focal_user": focal_user,
                        "reference_action": int(prepared.anchor.main_actions[focal_user]),
                        "candidate_action": candidate_action,
                        "reference_physical_key": [int(value) for value in reference_key],
                        "candidate_physical_key": [int(value) for value in prepared.candidate_key],
                        "candidate_source_rule": str(prepared.source_rule),
                    }
                    clusters.append(
                        E1C2ScheduleCluster(
                            source_seed=seed,
                            anchor_sha256=str(prepared.anchor.anchor_sha256),
                            world_anchor_sha256=world_anchor_sha256,
                            anchor_schedule_sha256=_canonical_sha256(schedule_body),
                            anchor_step=step,
                            focal_user=focal_user,
                            reference_action=int(prepared.anchor.main_actions[focal_user]),
                            candidate_action=candidate_action,
                            reference_physical_key=tuple(int(value) for value in reference_key),
                            candidate_physical_key=tuple(int(value) for value in prepared.candidate_key),
                            candidate_source_rule=str(prepared.source_rule),
                            policy_sha256=_policy_sha256(),
                            source_manifest_sha256=source_manifest_sha256,
                            checkpoint_sha256=checkpoint_sha256,
                            common_random_field_sha256=_cluster_field_sha256(prepared),
                        )
                    )
                except c2_pair_smoke.backend.C2ForecastSupportRejection as error:
                    rejected.append(
                        {
                            "step_index": step,
                            "focal_user": focal_user,
                            "reason": str(error.reason),
                            "forecast_offset": int(error.forecast_offset),
                        }
                    )
                if len(clusters) >= C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED:
                    break
        if len(clusters) >= C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED:
            break
        result = wrapped.step(main_actions, env_rng)
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation
    scheduled_anchors = {cluster.world_anchor_sha256 for cluster in clusters}
    if (
        len(clusters) < C2_MINIMUM_SCHEDULED_CLUSTERS_PER_SEED
        or len(scheduled_anchors) < C2_MINIMUM_SCHEDULED_ANCHORS_PER_SEED
    ):
        raise E1FreshSourceError(
            f"INSUFFICIENT_COVERAGE: C2 seed {seed} scheduled "
            f"{len(clusters)} clusters across {len(scheduled_anchors)} anchors; "
            f"requires at least {C2_MINIMUM_SCHEDULED_CLUSTERS_PER_SEED} "
            f"clusters across {C2_MINIMUM_SCHEDULED_ANCHORS_PER_SEED} anchors"
        )
    clusters.sort(key=lambda row: (row.anchor_step, row.focal_user, row.cluster_sha256))
    schedule = E1C2PreOutcomeSchedule(
        source_seed=seed,
        clusters=tuple(clusters),
        policy_sha256=_policy_sha256(),
        source_manifest_sha256=source_manifest_sha256,
        checkpoint_sha256=checkpoint_sha256,
    )
    return schedule, {
        "source_seed": seed,
        "clusters": len(clusters),
        "anchors": len(scheduled_anchors),
        "preoutcome_rejections": rejected,
        "forecast_outcomes_read": False,
    }


def prepare(
    *,
    output_dir: Path,
    tle_root: Path,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite E1 authority: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    source_manifest = _build_source_manifest()
    source_manifest_sha256 = _validate_source_manifest(source_manifest)
    base_record = read_prereg(BASE_PREREG)
    with tempfile.TemporaryDirectory(prefix="mcrl-e1-prepare-") as temporary:
        archive = c2_probe._frozen_archive(
            base_record, tle_root, Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = loader._verify_and_load_trainer(
            base_record,
            archive,
            run_dir=BASE_CHECKPOINT_DIR,
            users=USERS,
        )
        checkpoint_sha256 = _digest(
            checkpoint["checkpoint_sha256"], field="checkpoint_sha256"
        )
        environment_source_sha256 = _code_sha256(_default_code_paths())
        reward_source_sha256 = _file_sha256(REPO / "src" / "mcrl" / "env" / "step.py")
        prereg = _build_preregistration(
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            environment_source_sha256=environment_source_sha256,
            reward_source_sha256=reward_source_sha256,
            learner_contract=_learner_contract(
                checkpoint_sha256=checkpoint_sha256
            ),
        )
        prereg_sha256 = _digest(prereg["prereg_sha256"], field="prereg_sha256")
        network_before = c2_backend_smoke._network_snapshot(trainer)
        replay_before = len(trainer.replay)
        schedules: dict[int, E1C2PreOutcomeSchedule] = {}
        discovery_receipts: list[dict[str, Any]] = []
        for seed in sorted(SOURCE_SEED_SPLIT):
            schedule, receipt = _discover_c2_schedule(
                trainer=trainer,
                archive=archive,
                seed=seed,
                prereg_sha256=prereg_sha256,
                source_manifest_sha256=source_manifest_sha256,
                checkpoint_sha256=checkpoint_sha256,
                environment_source_sha256=environment_source_sha256,
                reward_source_sha256=reward_source_sha256,
            )
            schedules[seed] = schedule
            discovery_receipts.append(receipt)
            print(
                json.dumps(
                    {
                        "phase": "prepare-c2-schedule",
                        "source_seed": seed,
                        "completed": len(schedules),
                        "total": len(SOURCE_SEED_SPLIT),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        if not c2_backend_smoke._networks_equal(trainer, network_before):
            raise E1FreshSourceError("C2 schedule discovery mutated Main networks")
        if len(trainer.replay) != replay_before:
            raise E1FreshSourceError("C2 schedule discovery wrote Main replay")

    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}.", dir=output_dir.parent
    ) as temporary:
        staging = Path(temporary) / "publish"
        staging.mkdir()
        source_manifest_file_sha256 = _write_once_json(
            staging / "source-manifest.json", source_manifest
        )
        prereg_file_sha256 = _write_once_json(staging / "prereg.json", prereg)
        schedule_seals: dict[str, str] = {}
        for seed, schedule in schedules.items():
            schedule_seals[str(seed)] = seal_e1_c2_schedule(
                staging / "schedules" / f"c2-{seed}.json",
                schedule,
                source_seed=seed,
                policy_sha256=_policy_sha256(),
                source_manifest_sha256=source_manifest_sha256,
                checkpoint_sha256=checkpoint_sha256,
            )
        schedule_seals_file_sha256 = _write_once_json(
            staging / "schedule-seals.json", schedule_seals
        )
        receipt = {
            "schema": PREPARE_RECEIPT_SCHEMA,
            "status": "SEALED_PREOUTCOME",
            "claim_ceiling": CLAIM_CEILING,
            "source_manifest_sha256": source_manifest_sha256,
            "source_manifest_file_sha256": source_manifest_file_sha256,
            "prereg_sha256": prereg_sha256,
            "prereg_file_sha256": prereg_file_sha256,
            "schedule_seals_file_sha256": schedule_seals_file_sha256,
            "schedule_file_sha256s": schedule_seals,
            "discovery_receipts": discovery_receipts,
            "checkpoint_sha256": checkpoint_sha256,
            "main_networks_bitwise_unchanged": True,
            "main_replay_unchanged": True,
            "forecast_outcomes_read": False,
            "elapsed_s": time.perf_counter() - started,
        }
        prepare_receipt_file_sha256 = _write_once_json(
            staging / "prepare-receipt.json", receipt
        )
        _write_once_json(
            staging / "prepare-receipt-seal.json",
            {
                "schema": "multi-catfish-mcrl-v03-e1-prepare-receipt-seal-v1",
                "prepare_receipt_file_sha256": prepare_receipt_file_sha256,
            },
        )
        shutil.move(str(staging), str(output_dir))
    return receipt


def _load_authority(output_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    prepare_receipt_path = output_dir / "prepare-receipt.json"
    prepare_receipt = _read_canonical_json(prepare_receipt_path)
    prepare_seal = _read_canonical_json(output_dir / "prepare-receipt-seal.json")
    if (
        prepare_receipt.get("schema") != PREPARE_RECEIPT_SCHEMA
        or prepare_receipt.get("status") != "SEALED_PREOUTCOME"
        or prepare_seal.get("schema")
        != "multi-catfish-mcrl-v03-e1-prepare-receipt-seal-v1"
        or prepare_seal.get("prepare_receipt_file_sha256")
        != _file_sha256(prepare_receipt_path)
    ):
        raise E1FreshSourceError("E1 prepare receipt or its seal is invalid")
    manifest = _read_canonical_json(output_dir / "source-manifest.json")
    source_manifest_sha256 = _validate_source_manifest(manifest)
    prereg = _read_canonical_json(output_dir / "prereg.json")
    if prereg.get("schema") != PREREG_SCHEMA:
        raise E1FreshSourceError("E1 prereg schema is stale")
    prereg_body = dict(prereg)
    supplied_prereg_sha256 = prereg_body.pop("prereg_sha256", None)
    if supplied_prereg_sha256 != _canonical_sha256(prereg_body):
        raise E1FreshSourceError("E1 prereg digest disagrees")
    if prereg.get("source_manifest_sha256") != source_manifest_sha256:
        raise E1FreshSourceError("E1 prereg and source manifest disagree")
    checkpoint_sha256 = _digest(
        prereg.get("checkpoint_sha256"), field="checkpoint_sha256"
    )
    if prereg.get("learner") != _learner_contract(
        checkpoint_sha256=checkpoint_sha256
    ):
        raise E1FreshSourceError("current frozen learner calibration differs from E1 prereg")
    sealed_split = {int(seed): split for seed, split in prereg["source_seed_split"].items()}
    if sealed_split != SOURCE_SEED_SPLIT:
        raise E1FreshSourceError("E1 source seed split changed")
    seals = _read_canonical_json(output_dir / "schedule-seals.json")
    if set(seals) != {str(seed) for seed in SOURCE_SEED_SPLIT} or any(
        not isinstance(value, str) for value in seals.values()
    ):
        raise E1FreshSourceError("E1 schedule seals are malformed")
    expected_file_hashes = {
        "source_manifest_file_sha256": _file_sha256(output_dir / "source-manifest.json"),
        "prereg_file_sha256": _file_sha256(output_dir / "prereg.json"),
        "schedule_seals_file_sha256": _file_sha256(output_dir / "schedule-seals.json"),
    }
    if any(
        prepare_receipt.get(field) != value
        for field, value in expected_file_hashes.items()
    ):
        raise E1FreshSourceError("E1 prepare receipt file hashes changed")
    if prepare_receipt.get("schedule_file_sha256s") != seals:
        raise E1FreshSourceError("E1 prepare receipt and schedule seals disagree")
    for seed, expected_sha256 in seals.items():
        schedule_path = output_dir / "schedules" / f"c2-{seed}.json"
        if _file_sha256(schedule_path) != expected_sha256:
            raise E1FreshSourceError(f"sealed C2 schedule file changed for seed {seed}")
    return manifest, prereg, {str(key): str(value) for key, value in seals.items()}


def _verify_cluster_against_prepared(cluster: Any, prepared: Any) -> None:
    if cluster.anchor_schedule_sha256 != _anchor_schedule_sha256_from_cluster(cluster):
        raise E1FreshSourceError(
            "sealed C2 anchor_schedule_sha256 disagrees with its pre-outcome fields"
        )
    focal_user = int(cluster.focal_user)
    anchor = prepared.anchor
    reference_key = anchor.main_physical_actions[focal_user]
    observed = {
        "anchor_sha256": str(anchor.anchor_sha256),
        "reference_action": int(anchor.main_actions[focal_user]),
        "candidate_action": _candidate_action(prepared),
        "reference_physical_key": None if reference_key is None else tuple(reference_key),
        "candidate_physical_key": tuple(prepared.candidate_key),
        "candidate_source_rule": str(prepared.source_rule),
        "common_random_field_sha256": _cluster_field_sha256(prepared),
    }
    expected = {
        "anchor_sha256": cluster.anchor_sha256,
        "reference_action": cluster.reference_action,
        "candidate_action": cluster.candidate_action,
        "reference_physical_key": cluster.reference_physical_key,
        "candidate_physical_key": cluster.candidate_physical_key,
        "candidate_source_rule": cluster.candidate_source_rule,
        "common_random_field_sha256": cluster.common_random_field_sha256,
    }
    if observed != expected:
        raise E1FreshSourceError(
            f"replayed C2 pre-outcome cluster changed: expected={expected}, observed={observed}"
        )


def _generate_c2_for_seed(
    *,
    trainer: Any,
    archive: Any,
    schedule: E1C2PreOutcomeSchedule,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    environment_source_sha256: str,
    reward_source_sha256: str,
    lambda_bits_per_j: float,
    interval_s: float,
) -> tuple[EEAxisTemporalDataset, dict[str, Any]]:
    seed = int(schedule.source_seed)
    wrapped = loader._make_environment(archive, users=USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    by_step: dict[int, list[Any]] = defaultdict(list)
    for cluster in schedule.clusters:
        by_step[int(cluster.anchor_step)].append(cluster)
    completed_steps: set[int] = set()
    complete_pairs: list[Any] = []
    complete_world_anchors: set[str] = set()
    rows: list[dict[str, Any]] = []
    maximum_step = max(by_step)
    while int(observation.step_index) <= maximum_step:
        main_actions, _main_physical = c2_backend_smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        step = int(observation.step_index)
        for cluster in by_step.get(step, []):
            started = time.perf_counter()
            base = {
                "source_seed": seed,
                "anchor_step": step,
                "anchor_sha256": cluster.anchor_sha256,
                "focal_user": int(cluster.focal_user),
                "cluster_sha256": cluster.cluster_sha256,
            }
            try:
                service = c2_pair_smoke.backend.C2TemporalForkTrainerBackend(
                    wrapped=wrapped,
                    states=states,
                    masks=masks,
                    observation=observation,
                    env_rng=env_rng,
                    trainer=trainer,
                    checkpoint_sha256=checkpoint_sha256,
                    environment_source_sha256=environment_source_sha256,
                    reward_source_sha256=reward_source_sha256,
                    evaluation_seed=seed,
                    focal_user=int(cluster.focal_user),
                    forecast_fading_mode=c2_pair_smoke.KEYED_FADING,
                )
                prepared = service.prepare_hold_or_max_lagged_gain_rival(
                    focal_user=int(cluster.focal_user)
                )
                _verify_cluster_against_prepared(cluster, prepared)
                materialized = c2_pair_smoke.capture_and_materialize_q2_pair(
                    prepared,
                    anchor_schedule_sha256=cluster.anchor_schedule_sha256,
                    source_manifest_sha256=source_manifest_sha256,
                    lambda_bits_per_j=lambda_bits_per_j,
                    interval_s=interval_s,
                )
                pair = materialized.pair
                if (
                    pair.anchor_sha256 != cluster.anchor_sha256
                    or pair.reference_action != cluster.reference_action
                    or pair.candidate_action != cluster.candidate_action
                    or pair.common_random_field_sha256
                    != cluster.common_random_field_sha256
                ):
                    raise E1FreshSourceError("materialized C2 pair disagrees with sealed cluster")
                complete_pairs.append(pair)
                complete_world_anchors.add(cluster.world_anchor_sha256)
                rows.append(
                    {
                        **base,
                        "outcome": "COMPLETE_PAIR",
                        "comparison_sha256": pair.comparison_sha256,
                        "target_surplus_bits": float(pair.zeta2_temporal_surplus_bits),
                        "release_offset": int(pair.release_offset),
                        "release_reason": str(pair.release_reason),
                        "elapsed_s": time.perf_counter() - started,
                    }
                )
            except c2_pair_smoke.backend.C2ForecastSupportRejection as error:
                if int(error.forecast_offset) != 0:
                    raise E1FreshSourceError(
                        "reactive C2 produced a downstream support rejection instead of "
                        "the sealed monotone release"
                    ) from error
                rows.append(
                    {
                        **base,
                        "outcome": "RIGHT_CENSORED_OPENING_SUPPORT",
                        "reason": str(error.reason),
                        "forecast_offset": int(error.forecast_offset),
                        "elapsed_s": time.perf_counter() - started,
                    }
                )
        if step in by_step:
            completed_steps.add(step)
        if completed_steps == set(by_step):
            break
        result = wrapped.step(main_actions, env_rng)
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation
    if completed_steps != set(by_step):
        raise E1FreshSourceError(f"C2 seed {seed} did not replay every sealed anchor")
    if len(complete_pairs) < C2_MINIMUM_COMPLETE_CLUSTERS_PER_SEED:
        raise E1FreshSourceError(
            f"INSUFFICIENT_COVERAGE: C2 seed {seed} has {len(complete_pairs)} complete clusters"
        )
    if len(complete_world_anchors) < C2_MINIMUM_COMPLETE_ANCHORS_PER_SEED:
        raise E1FreshSourceError(
            f"INSUFFICIENT_COVERAGE: C2 seed {seed} has complete pairs on "
            f"{len(complete_world_anchors)} anchors; requires "
            f"{C2_MINIMUM_COMPLETE_ANCHORS_PER_SEED}"
        )
    dataset = EEAxisTemporalDataset.from_pairs(complete_pairs)
    return dataset, {
        "source_seed": seed,
        "scheduled_clusters": len(schedule.clusters),
        "scheduled_anchors": len(
            {row.world_anchor_sha256 for row in schedule.clusters}
        ),
        "complete_clusters": len(complete_pairs),
        "complete_anchors": len(complete_world_anchors),
        "censored_clusters": len(schedule.clusters) - len(complete_pairs),
        "rows": rows,
    }


def _index_opening(dataset: EEAxisOpeningDataset, *, source_seed: int) -> list[E1PairIndexRow]:
    rows: list[E1PairIndexRow] = []
    for route, pairs in (("C1", dataset.c1_pairs), ("C3", dataset.c3_pairs)):
        rows.extend(
            E1PairIndexRow(
                route=route,
                source_seed=source_seed,
                anchor_sha256=pair.anchor_sha256,
                inference_anchor_sha256=pair.anchor_sha256,
                focal_user=pair.focal_user,
                reference_action=pair.reference_action,
                candidate_action=pair.candidate_action,
                action_mask=tuple(bool(value) for value in pair.action_mask.tolist()),
            )
            for pair in pairs
        )
    return rows


def _index_temporal(dataset: EEAxisTemporalDataset) -> list[E1PairIndexRow]:
    return [
        E1PairIndexRow(
            route="C2",
            source_seed=pair.seed,
            anchor_sha256=pair.anchor_sha256,
            inference_anchor_sha256=e1_c2_world_anchor_sha256(
                source_seed=pair.seed, anchor_step=pair.step_index
            ),
            focal_user=pair.focal_user,
            reference_action=pair.reference_action,
            candidate_action=pair.candidate_action,
            action_mask=tuple(bool(value) for value in pair.action_mask.tolist()),
        )
        for pair in dataset.rows
    ]


def _verify_opening_seed_coverage(
    dataset: EEAxisOpeningDataset, *, source_seed: int
) -> dict[str, dict[str, int]]:
    """Fail immediately if one opening seed cannot support E1 inference."""

    rows = _index_opening(dataset, source_seed=source_seed)
    result: dict[str, dict[str, int]] = {}
    for route in ("C1", "C3"):
        selected = [row for row in rows if row.route == route]
        verify_full_sibling_groups(selected, route=route)
        clusters = {row.cluster_key for row in selected}
        anchors = {row.inference_cluster_key for row in selected}
        if (
            len(clusters) < OPENING_MINIMUM_CLUSTERS_PER_SEED
            or len(anchors) < OPENING_MINIMUM_INFERENCE_ANCHORS_PER_SEED
        ):
            raise E1FreshSourceError(
                f"INSUFFICIENT_COVERAGE: {route} seed {source_seed} has "
                f"{len(clusters)} intervention clusters across {len(anchors)} "
                f"inference anchors"
            )
        result[route] = {
            "intervention_clusters": len(clusters),
            "inference_anchors": len(anchors),
            "rows": len(selected),
        }
    return result


def _source_index_payloads(
    *,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    opening_sha256s: Mapping[str, str],
    temporal_sha256s: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Construct the only two allowed source-data indexes.

    Paths are deliberately canonical basenames.  Consumers must compare the
    raw strings, not merely ``Path.name``, before opening a dataset.
    """

    expected_keys = {str(seed) for seed in SOURCE_SEED_SPLIT}
    if set(opening_sha256s) != expected_keys or set(temporal_sha256s) != expected_keys:
        raise E1FreshSourceError("source dataset digest maps are incomplete")
    for seed in expected_keys:
        _digest(opening_sha256s[seed], field=f"opening_dataset_sha256s[{seed}]")
        _digest(temporal_sha256s[seed], field=f"temporal_dataset_sha256s[{seed}]")

    def payload_for(*, split_name: str, schema: str) -> dict[str, Any]:
        seeds = [
            seed
            for seed, observed_split in sorted(SOURCE_SEED_SPLIT.items())
            if observed_split == split_name
            or (split_name == "ladder" and observed_split in {"train", "validation"})
        ]
        payload: dict[str, Any] = {
            "schema": schema,
            "source_manifest_sha256": source_manifest_sha256,
            "checkpoint_sha256": checkpoint_sha256,
            "seed_split": {
                str(seed): SOURCE_SEED_SPLIT[seed] for seed in seeds
            },
            "datasets": {
                str(seed): {
                    "opening_path": f"opening-{seed}.json",
                    "opening_dataset_sha256": opening_sha256s[str(seed)],
                    "temporal_path": f"temporal-{seed}.json",
                    "temporal_dataset_sha256": temporal_sha256s[str(seed)],
                }
                for seed in seeds
            },
            "held_out_ee_evaluated": False,
        }
        if split_name == "ladder":
            payload.update(
                {
                    "test_split_present": True,
                    "test_split_opened": False,
                }
            )
        else:
            payload["may_open_only_after_selected_common_rung"] = True
        return payload

    return (
        payload_for(split_name="ladder", schema=LADDER_INDEX_SCHEMA),
        payload_for(split_name="test", schema=TEST_INDEX_SCHEMA),
    )


def _validate_source_receipt(
    receipt: Mapping[str, Any], *, prereg: Mapping[str, Any]
) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    expected_fields = {
        "schema",
        "status",
        "claim_ceiling",
        "training",
        "held_out_ee_evaluated",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "opening_dataset_sha256s",
        "temporal_dataset_sha256s",
        "opening_dataset_file_sha256s",
        "temporal_dataset_file_sha256s",
        "ladder_index_file_sha256",
        "test_index_file_sha256",
        "ladder_generation_details_file_sha256",
        "test_generation_details_file_sha256",
        "coverage_by_seed",
        "split_receipt",
        "elapsed_s",
    }
    if set(receipt) != expected_fields:
        raise E1FreshSourceError("E1 public source receipt schema is unexpected")
    if receipt.get("schema") != SOURCE_RECEIPT_SCHEMA or receipt.get("status") != "PASS":
        raise E1FreshSourceError("E1 source receipt is absent or not PASS")
    if (
        receipt.get("claim_ceiling") != CLAIM_CEILING
        or receipt.get("training") is not False
        or receipt.get("held_out_ee_evaluated") is not False
        or receipt.get("source_manifest_sha256") != prereg.get("source_manifest_sha256")
        or receipt.get("checkpoint_sha256") != prereg.get("checkpoint_sha256")
    ):
        raise E1FreshSourceError("E1 source receipt authority changed")
    expected_keys = {str(seed) for seed in SOURCE_SEED_SPLIT}
    opening = receipt.get("opening_dataset_sha256s")
    temporal = receipt.get("temporal_dataset_sha256s")
    opening_files = receipt.get("opening_dataset_file_sha256s")
    temporal_files = receipt.get("temporal_dataset_file_sha256s")
    if (
        not isinstance(opening, dict)
        or not isinstance(temporal, dict)
        or not isinstance(opening_files, dict)
        or not isinstance(temporal_files, dict)
        or set(opening) != expected_keys
        or set(temporal) != expected_keys
        or set(opening_files) != expected_keys
        or set(temporal_files) != expected_keys
    ):
        raise E1FreshSourceError("E1 source receipt dataset maps are incomplete")
    opening_digests = {
        seed: _digest(value, field=f"opening_dataset_sha256s[{seed}]")
        for seed, value in opening.items()
    }
    temporal_digests = {
        seed: _digest(value, field=f"temporal_dataset_sha256s[{seed}]")
        for seed, value in temporal.items()
    }
    opening_file_digests = {
        seed: _digest(value, field=f"opening_dataset_file_sha256s[{seed}]")
        for seed, value in opening_files.items()
    }
    temporal_file_digests = {
        seed: _digest(value, field=f"temporal_dataset_file_sha256s[{seed}]")
        for seed, value in temporal_files.items()
    }
    _digest(receipt.get("ladder_index_file_sha256"), field="ladder_index_file_sha256")
    _digest(receipt.get("test_index_file_sha256"), field="test_index_file_sha256")
    _digest(
        receipt.get("ladder_generation_details_file_sha256"),
        field="ladder_generation_details_file_sha256",
    )
    _digest(
        receipt.get("test_generation_details_file_sha256"),
        field="test_generation_details_file_sha256",
    )
    coverage = receipt.get("coverage_by_seed")
    coverage_fields = {
        "source_seed",
        "split",
        "c1_rows",
        "c3_rows",
        "c2_scheduled_clusters",
        "c2_scheduled_anchors",
        "c2_complete_clusters",
        "c2_complete_anchors",
        "c2_censored_clusters",
    }
    if (
        not isinstance(coverage, list)
        or len(coverage) != len(SOURCE_SEED_SPLIT)
        or any(not isinstance(row, dict) for row in coverage)
        or any(set(row) != coverage_fields for row in coverage)
        or {row.get("source_seed") for row in coverage} != set(SOURCE_SEED_SPLIT)
        or any(
            row.get("split") != SOURCE_SEED_SPLIT[row["source_seed"]]
            for row in coverage
        )
        or any(
            type(row[field]) is not int or row[field] < 0
            for row in coverage
            for field in coverage_fields - {"source_seed", "split"}
        )
        or any(
            row["c2_complete_clusters"] + row["c2_censored_clusters"]
            != row["c2_scheduled_clusters"]
            for row in coverage
        )
    ):
        raise E1FreshSourceError("E1 source receipt coverage is incomplete")
    elapsed_s = receipt.get("elapsed_s")
    if (
        isinstance(elapsed_s, bool)
        or not isinstance(elapsed_s, (int, float))
        or not math.isfinite(float(elapsed_s))
        or float(elapsed_s) < 0.0
    ):
        raise E1FreshSourceError("E1 source receipt elapsed time is invalid")
    return (
        opening_digests,
        temporal_digests,
        opening_file_digests,
        temporal_file_digests,
    )


def _validate_published_index(
    *,
    data_root: Path,
    prereg: Mapping[str, Any],
    receipt: Mapping[str, Any],
    kind: str,
) -> dict[str, Any]:
    """Authenticate one index against the source receipt and canonical layout."""

    opening, temporal, _opening_files, _temporal_files = _validate_source_receipt(
        receipt, prereg=prereg
    )
    ladder, test = _source_index_payloads(
        source_manifest_sha256=str(prereg["source_manifest_sha256"]),
        checkpoint_sha256=str(prereg["checkpoint_sha256"]),
        opening_sha256s=opening,
        temporal_sha256s=temporal,
    )
    if kind == "ladder":
        filename = "ladder-index.json"
        digest_field = "ladder_index_file_sha256"
        expected = ladder
    elif kind == "test":
        filename = "test-index.json"
        digest_field = "test_index_file_sha256"
        expected = test
    else:
        raise E1FreshSourceError(f"unknown E1 source index kind: {kind}")
    path = data_root / filename
    observed = _read_canonical_json(path)
    if _file_sha256(path) != receipt[digest_field]:
        raise E1FreshSourceError(f"published {kind} index file digest changed")
    if observed != expected:
        raise E1FreshSourceError(f"published {kind} index content changed")
    return observed


def generate(
    *,
    output_dir: Path,
    tle_root: Path,
) -> dict[str, Any]:
    if (output_dir / "source-data").exists() or (output_dir / "source-data").is_symlink():
        raise FileExistsError("refusing to overwrite generated E1 source data")
    _manifest, prereg, schedule_seals = _load_authority(output_dir)
    source_manifest_sha256 = _digest(
        prereg["source_manifest_sha256"], field="source_manifest_sha256"
    )
    checkpoint_sha256 = _digest(prereg["checkpoint_sha256"], field="checkpoint_sha256")
    environment_source_sha256 = _digest(
        prereg["environment_source_sha256"], field="environment_source_sha256"
    )
    reward_source_sha256 = _digest(
        prereg["reward_source_sha256"], field="reward_source_sha256"
    )
    started = time.perf_counter()
    runtime_status = output_dir / "runtime-status.json"
    _write_runtime_status(
        runtime_status,
        {
            "schema": "multi-catfish-mcrl-v03-e1-source-runtime-status-v1",
            "status": "running",
            "stage": "opening",
            "opening_seeds_completed": 0,
            "c2_seeds_completed": 0,
            "elapsed_s": 0.0,
        },
    )
    opening_datasets: dict[int, EEAxisOpeningDataset] = {}
    opening_receipts: list[dict[str, Any]] = []
    for seed in sorted(SOURCE_SEED_SPLIT):
        dataset, receipt = phase1._opening_corpus(
            tle_root=tle_root,
            source_manifest_sha256=source_manifest_sha256,
            c3_anchors=OPENING_ANCHORS_PER_SEED,
            source_seed=seed,
            c1_anchors=OPENING_ANCHORS_PER_SEED,
            c1_focal_users_per_anchor=OPENING_FOCAL_USERS_PER_ANCHOR,
            c3_focal_users_per_anchor=OPENING_FOCAL_USERS_PER_ANCHOR,
            max_source_steps=OPENING_SOURCE_STEPS_PER_SEED,
        )
        if dataset.checkpoint_sha256 != checkpoint_sha256:
            raise E1FreshSourceError("opening dataset changed frozen Main checkpoint")
        seed_coverage = _verify_opening_seed_coverage(dataset, source_seed=seed)
        receipt = {**receipt, "e1_coverage": seed_coverage}
        opening_datasets[seed] = dataset
        opening_receipts.append(receipt)
        _write_runtime_status(
            runtime_status,
            {
                "schema": "multi-catfish-mcrl-v03-e1-source-runtime-status-v1",
                "status": "running",
                "stage": "opening",
                "last_source_seed": seed,
                "opening_seeds_completed": len(opening_datasets),
                "c2_seeds_completed": 0,
                "elapsed_s": time.perf_counter() - started,
            },
        )

    base_record = read_prereg(BASE_PREREG)
    temporal_datasets: dict[int, EEAxisTemporalDataset] = {}
    temporal_receipts: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mcrl-e1-generate-c2-") as temporary:
        archive = c2_probe._frozen_archive(
            base_record, tle_root, Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = loader._verify_and_load_trainer(
            base_record,
            archive,
            run_dir=BASE_CHECKPOINT_DIR,
            users=USERS,
        )
        if checkpoint["checkpoint_sha256"] != checkpoint_sha256:
            raise E1FreshSourceError("loaded Main checkpoint changed after E1 seal")
        network_before = c2_backend_smoke._network_snapshot(trainer)
        replay_before = len(trainer.replay)
        calibration_environment = loader._make_environment(archive, users=USERS)
        calibration = c2_pair_smoke.gate_runner._freeze_lambda(
            trainer,
            calibration_environment,
            seed=c2_pair_smoke.DEFAULT_CALIBRATION_SEED,
        )
        multiplier = float(calibration["lambda_bits_per_j"])
        interval_s = float(calibration["interval_s"])
        if not math.isclose(multiplier, phase1.opening_smoke.LAMBDA_BITS_PER_J, rel_tol=0.0, abs_tol=1e-9):
            raise E1FreshSourceError("opening and C2 lambda0 disagree")
        for seed in sorted(SOURCE_SEED_SPLIT):
            schedule = load_e1_c2_schedule(
                output_dir / "schedules" / f"c2-{seed}.json",
                expected_file_sha256=schedule_seals[str(seed)],
                source_seed=seed,
                policy_sha256=_policy_sha256(),
                source_manifest_sha256=source_manifest_sha256,
                checkpoint_sha256=checkpoint_sha256,
            )
            dataset, receipt = _generate_c2_for_seed(
                trainer=trainer,
                archive=archive,
                schedule=schedule,
                source_manifest_sha256=source_manifest_sha256,
                checkpoint_sha256=checkpoint_sha256,
                environment_source_sha256=environment_source_sha256,
                reward_source_sha256=reward_source_sha256,
                lambda_bits_per_j=multiplier,
                interval_s=interval_s,
            )
            temporal_datasets[seed] = dataset
            temporal_receipts.append(receipt)
            _write_runtime_status(
                runtime_status,
                {
                    "schema": "multi-catfish-mcrl-v03-e1-source-runtime-status-v1",
                    "status": "running",
                    "stage": "c2",
                    "last_source_seed": seed,
                    "opening_seeds_completed": len(opening_datasets),
                    "c2_seeds_completed": len(temporal_datasets),
                    "elapsed_s": time.perf_counter() - started,
                },
            )
        if not c2_backend_smoke._networks_equal(trainer, network_before):
            raise E1FreshSourceError("E1 C2 generation mutated Main networks")
        if len(trainer.replay) != replay_before:
            raise E1FreshSourceError("E1 C2 generation wrote Main replay")

    index_rows: list[E1PairIndexRow] = []
    for seed in sorted(SOURCE_SEED_SPLIT):
        index_rows.extend(_index_opening(opening_datasets[seed], source_seed=seed))
        index_rows.extend(_index_temporal(temporal_datasets[seed]))
    split_receipt = verify_e1_partition(
        index_rows,
        seed_split=SOURCE_SEED_SPLIT,
        burned_seeds=BURNED_SOURCE_SEEDS,
        minimum_inference_anchors=MINIMUM_INFERENCE_ANCHORS,
    )

    with tempfile.TemporaryDirectory(
        prefix=".e1-source-data.", dir=output_dir
    ) as temporary:
        staging = Path(temporary) / "publish"
        staging.mkdir()
        opening_sha: dict[str, str] = {}
        temporal_sha: dict[str, str] = {}
        opening_file_sha: dict[str, str] = {}
        temporal_file_sha: dict[str, str] = {}
        for seed in sorted(SOURCE_SEED_SPLIT):
            opening_path = staging / f"opening-{seed}.json"
            temporal_path = staging / f"temporal-{seed}.json"
            write_opening_dataset(opening_path, opening_datasets[seed])
            write_temporal_dataset(temporal_path, temporal_datasets[seed])
            opening_sha[str(seed)] = opening_datasets[seed].verify()
            temporal_sha[str(seed)] = temporal_datasets[seed].verify()
            opening_file_sha[str(seed)] = _file_sha256(opening_path)
            temporal_file_sha[str(seed)] = _file_sha256(temporal_path)
        opening_receipt_by_seed = {
            int(row["source_seed"]): row for row in opening_receipts
        }
        temporal_receipt_by_seed = {
            int(row["source_seed"]): row for row in temporal_receipts
        }
        if (
            set(opening_receipt_by_seed) != set(SOURCE_SEED_SPLIT)
            or set(temporal_receipt_by_seed) != set(SOURCE_SEED_SPLIT)
        ):
            raise E1FreshSourceError("source-generation receipts are incomplete")
        ladder_seeds = [
            seed
            for seed, split_name in sorted(SOURCE_SEED_SPLIT.items())
            if split_name in {"train", "validation"}
        ]
        test_seeds = [
            seed
            for seed, split_name in sorted(SOURCE_SEED_SPLIT.items())
            if split_name == "test"
        ]
        ladder_details_file_sha256 = _write_once_json(
            staging / "ladder-generation-details.json",
            {
                "schema": "multi-catfish-mcrl-v03-e1-ladder-generation-details-v1",
                "source_manifest_sha256": source_manifest_sha256,
                "checkpoint_sha256": checkpoint_sha256,
                "source_seeds": ladder_seeds,
                "opening_receipts": [
                    opening_receipt_by_seed[seed] for seed in ladder_seeds
                ],
                "temporal_receipts": [
                    temporal_receipt_by_seed[seed] for seed in ladder_seeds
                ],
            },
        )
        test_details_file_sha256 = _write_once_json(
            staging / "test-generation-details.json",
            {
                "schema": "multi-catfish-mcrl-v03-e1-test-generation-details-v1",
                "source_manifest_sha256": source_manifest_sha256,
                "checkpoint_sha256": checkpoint_sha256,
                "source_seeds": test_seeds,
                "opening_receipts": [
                    opening_receipt_by_seed[seed] for seed in test_seeds
                ],
                "temporal_receipts": [
                    temporal_receipt_by_seed[seed] for seed in test_seeds
                ],
            },
        )
        ladder_index, test_index = _source_index_payloads(
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            opening_sha256s=opening_sha,
            temporal_sha256s=temporal_sha,
        )
        ladder_index_file_sha256 = _write_once_json(
            staging / "ladder-index.json", ladder_index
        )
        test_index_file_sha256 = _write_once_json(
            staging / "test-index.json", test_index
        )
        receipt = {
            "schema": SOURCE_RECEIPT_SCHEMA,
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "training": False,
            "held_out_ee_evaluated": False,
            "source_manifest_sha256": source_manifest_sha256,
            "checkpoint_sha256": checkpoint_sha256,
            "opening_dataset_sha256s": opening_sha,
            "temporal_dataset_sha256s": temporal_sha,
            "opening_dataset_file_sha256s": opening_file_sha,
            "temporal_dataset_file_sha256s": temporal_file_sha,
            "ladder_index_file_sha256": ladder_index_file_sha256,
            "test_index_file_sha256": test_index_file_sha256,
            "ladder_generation_details_file_sha256": ladder_details_file_sha256,
            "test_generation_details_file_sha256": test_details_file_sha256,
            "coverage_by_seed": [
                {
                    "source_seed": seed,
                    "split": SOURCE_SEED_SPLIT[seed],
                    "c1_rows": int(opening_receipt_by_seed[seed]["c1_rows"]),
                    "c3_rows": int(opening_receipt_by_seed[seed]["c3_rows"]),
                    "c2_scheduled_clusters": int(
                        temporal_receipt_by_seed[seed]["scheduled_clusters"]
                    ),
                    "c2_scheduled_anchors": int(
                        temporal_receipt_by_seed[seed]["scheduled_anchors"]
                    ),
                    "c2_complete_clusters": int(
                        temporal_receipt_by_seed[seed]["complete_clusters"]
                    ),
                    "c2_complete_anchors": int(
                        temporal_receipt_by_seed[seed]["complete_anchors"]
                    ),
                    "c2_censored_clusters": int(
                        temporal_receipt_by_seed[seed]["censored_clusters"]
                    ),
                }
                for seed in sorted(SOURCE_SEED_SPLIT)
            ],
            "split_receipt": split_receipt.as_dict(),
            "elapsed_s": time.perf_counter() - started,
        }
        receipt_file_sha256 = _write_once_json(staging / "receipt.json", receipt)
        shutil.move(str(staging), str(output_dir / "source-data"))
    _write_runtime_status(
        runtime_status,
        {
            "schema": "multi-catfish-mcrl-v03-e1-source-runtime-status-v1",
            "status": "complete",
            "stage": "source-data-published",
            "opening_seeds_completed": len(opening_datasets),
            "c2_seeds_completed": len(temporal_datasets),
            "elapsed_s": time.perf_counter() - started,
        },
    )
    return {
        "schema": "multi-catfish-mcrl-v03-e1-source-publication-summary-v1",
        "status": "PASS_SOURCE_DATA_PUBLISHED",
        "claim_ceiling": CLAIM_CEILING,
        "source_manifest_sha256": source_manifest_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "source_receipt_file_sha256": receipt_file_sha256,
        "coverage_by_seed": receipt["coverage_by_seed"],
        "test_outcomes_returned": False,
        "test_split_opened_for_selection": False,
        "held_out_ee_evaluated": False,
    }


def verify_published(output_dir: Path) -> dict[str, Any]:
    _manifest, prereg, schedule_seals = _load_authority(output_dir)
    data_root = output_dir / "source-data"
    if data_root.is_symlink() or not data_root.is_dir():
        raise E1FreshSourceError("published source-data must be a regular directory")
    receipt = _read_canonical_json(data_root / "receipt.json")
    (
        opening_digests,
        temporal_digests,
        opening_file_digests,
        temporal_file_digests,
    ) = _validate_source_receipt(receipt, prereg=prereg)
    _validate_published_index(
        data_root=data_root, prereg=prereg, receipt=receipt, kind="ladder"
    )
    _validate_published_index(
        data_root=data_root, prereg=prereg, receipt=receipt, kind="test"
    )
    for filename, digest_field in (
        ("ladder-generation-details.json", "ladder_generation_details_file_sha256"),
        ("test-generation-details.json", "test_generation_details_file_sha256"),
    ):
        if _opaque_regular_file_sha256(data_root / filename) != receipt[digest_field]:
            raise E1FreshSourceError(f"published {filename} bytes changed")

    rows: list[E1PairIndexRow] = []
    ladder_seeds = {
        seed
        for seed, split_name in SOURCE_SEED_SPLIT.items()
        if split_name in {"train", "validation"}
    }
    for seed in sorted(SOURCE_SEED_SPLIT):
        load_e1_c2_schedule(
            output_dir / "schedules" / f"c2-{seed}.json",
            expected_file_sha256=schedule_seals[str(seed)],
            source_seed=seed,
            policy_sha256=_policy_sha256(),
            source_manifest_sha256=prereg["source_manifest_sha256"],
            checkpoint_sha256=prereg["checkpoint_sha256"],
        )
        opening_path = data_root / f"opening-{seed}.json"
        temporal_path = data_root / f"temporal-{seed}.json"
        if _opaque_regular_file_sha256(opening_path) != opening_file_digests[str(seed)]:
            raise E1FreshSourceError("published opening dataset file bytes changed")
        if _opaque_regular_file_sha256(temporal_path) != temporal_file_digests[str(seed)]:
            raise E1FreshSourceError("published temporal dataset file bytes changed")
        if seed not in ladder_seeds:
            # Test outcomes stay unopened until validation selects one common
            # rung.  Their exact sealed bytes are checked opaquely above.
            continue
        opening = read_opening_dataset(opening_path)
        temporal = read_temporal_dataset(temporal_path)
        if opening.verify() != opening_digests[str(seed)]:
            raise E1FreshSourceError("published opening dataset digest changed")
        if temporal.verify() != temporal_digests[str(seed)]:
            raise E1FreshSourceError("published temporal dataset digest changed")
        rows.extend(_index_opening(opening, source_seed=seed))
        rows.extend(_index_temporal(temporal))
    if not rows:
        raise E1FreshSourceError("published ladder split has no rows")
    for row in rows:
        row.verify()
        if row.source_seed not in ladder_seeds:
            raise E1FreshSourceError("pre-ladder verification opened a test row")
    anchor_owner: dict[str, str] = {}
    for row in rows:
        split_name = SOURCE_SEED_SPLIT[row.source_seed]
        previous = anchor_owner.setdefault(row.inference_anchor_sha256, split_name)
        if previous != split_name:
            raise E1FreshSourceError("one anchor appears across train/validation")
    verify_full_sibling_groups(rows, route="C1")
    verify_full_sibling_groups(rows, route="C3")

    split_receipt = receipt.get("split_receipt")
    if not isinstance(split_receipt, dict) or not isinstance(
        split_receipt.get("coverage"), list
    ):
        raise E1FreshSourceError("published split receipt is malformed")
    expected_coverage = {
        item.get("route"): item
        for item in split_receipt["coverage"]
        if isinstance(item, dict)
    }
    if set(expected_coverage) != {"C1", "C2", "C3"}:
        raise E1FreshSourceError("published split receipt routes are incomplete")
    for route in ("C1", "C2", "C3"):
        route_rows = [row for row in rows if row.route == route]
        for split_name, minimum in (("train", 30), ("validation", 10)):
            selected = [
                row
                for row in route_rows
                if SOURCE_SEED_SPLIT[row.source_seed] == split_name
            ]
            clusters = {row.cluster_key for row in selected}
            inference_anchors = {row.inference_cluster_key for row in selected}
            if len(clusters) < minimum:
                raise E1FreshSourceError(
                    f"published {route} {split_name} coverage is insufficient"
                )
            if (
                expected_coverage[route].get(f"{split_name}_clusters")
                != len(clusters)
                or expected_coverage[route].get(f"{split_name}_rows")
                != len(selected)
            ):
                raise E1FreshSourceError(
                    f"published {route} {split_name} coverage changed"
                )
            if (
                len(inference_anchors)
                < MINIMUM_INFERENCE_ANCHORS[route][split_name]
                or expected_coverage[route].get(
                    f"{split_name}_inference_anchors"
                )
                != len(inference_anchors)
            ):
                raise E1FreshSourceError(
                    f"published {route} {split_name} inference-anchor coverage changed"
                )
    return {
        "status": "PASS",
        "source_manifest_sha256": prereg["source_manifest_sha256"],
        "prereg_sha256": prereg["prereg_sha256"],
        "split_receipt": split_receipt,
        "test_dataset_bytes_hashed_opaquely": True,
        "test_dataset_documents_deserialized": False,
        "test_outcomes_returned": False,
        "held_out_ee_evaluated": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "generate", "verify"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO / "artifacts" / "multi-catfish-v03-e1-instrument-validity-20260901",
    )
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    args = parser.parse_args(argv)
    if args.phase == "prepare":
        payload = prepare(output_dir=args.output_dir, tle_root=args.tle_root)
    elif args.phase == "generate":
        payload = generate(output_dir=args.output_dir, tle_root=args.tle_root)
    elif args.phase == "verify":
        payload = verify_published(args.output_dir)
    else:
        payload = verify_published(args.output_dir)
    print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
