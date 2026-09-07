#!/usr/bin/env python3
"""Run the sealed, evaluation-only C2 persistence Stage-0 gate.

The formal runner requires a closure manifest and a later seed-reveal manifest.
It never updates a learner, optimizer, replay buffer, runtime reward, or Main.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import statistics
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DESIGN_DIR = REPO / ".scratch" / "catfish-design-data"
ORACLE_DIR = REPO / ".scratch" / "catfish-oracle-gate"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(DESIGN_DIR))
sys.path.insert(0, str(ORACLE_DIR))

import run_c3_disjoint_median_shadow as provenance  # noqa: E402
import scripts.run_head_pivotality_probe as checkpoint_loader  # noqa: E402
from mcrl.env.action_contract import (  # noqa: E402
    NO_OP_ACTION,
    Association,
    HandoverClass,
)
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.runtime.head_pivotality import (  # noqa: E402
    masked_greedy_actions,
    physical_action_keys,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)


SPEC = DESIGN_DIR / "C2-PERSISTENCE-OPTION-STAGE0-SPEC-2026-08-27.md"
C3_SPEC = DESIGN_DIR / "C3-PERSISTENT-POWER-STAGE0-SPEC-2026-08-27.md"
METHOD = REPO / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md"
DEFAULT_INPUT = REPO / "artifacts" / "training-2026-08-25-rerun01"
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
EXPECTED_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
EXPECTED_PREREG_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)
EXPECTED_METHOD_SHA256 = (
    "25318fcea4acca6c8692c454751b3af35e7d4151195d200821077c208672e63f"
)
EXPECTED_ANALYSIS_CODE_SHA256 = (
    "4cfc7e3043453994fc0686c3bbfa14d9a95156aeabc578b26decb2f210603a2e"
)

USERS = 100
STEPS = 10
ANCHOR_STEPS = frozenset(range(6))
FOCAL_USERS_PER_STEP = 5
HOLD_STEPS = 3
RELEASE_OFFSET = 3
DECISION_INTERVAL_S = 30.08
SERVICE_TOLERANCE = 0.005
EE_IDENTITY_RELATIVE_TOLERANCE = 1e-9
FORECAST_NAMESPACE = "SMC-ER-C2-PRE-v1"
# Forecasting uses two domain-separated streams.  They are deliberately
# distinct from the realised evaluation streams and from one another: a
# forecast must not silently turn the mobility stream into a fading stream.
FORECAST_ENV_NAMESPACE = "SMC-ER-C2-FORECAST-ENV-v2"
FORECAST_MOBILITY_NAMESPACE = "SMC-ER-C2-FORECAST-MOBILITY-v2"
RANDOM_NAMESPACE = "SMC-ER-C2-RANDOM-v1"
SEED_SCHEMA = "smc-er-stage0-seeds-v1"
CLOSURE_SCHEMA = "smc-er-stage0-closure-v1"
OUTPUT_SCHEMA = "smc-er-c2-stage0-result-v1"
EXPECTED_C2_SPEC_SHA256 = (
    "fbf9599a3f390944925aecc9f56c7769b9577804b654a1b3701f6951aef13e17"
)
EXPECTED_C3_SPEC_SHA256 = (
    "188b66428c040b6055fa3dcdb20d54f1e81e6e2aa66adc62a6a090f025a91175"
)

PhysicalKey = tuple[int, int]


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dt.datetime):
        return value.isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    ).encode("utf-8")


def _value_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _derived_seed_int(
    namespace: str, *, evaluation_seed: int, step_index: int, focal_user: int
) -> int:
    payload = [
        namespace,
        EXPECTED_CHECKPOINT_SHA256,
        int(evaluation_seed),
        int(step_index),
        int(focal_user),
    ]
    digest = hashlib.sha256(_canonical_bytes(payload)).digest()
    return int.from_bytes(digest[:16], "big")


def _derived_rng(
    namespace: str, *, evaluation_seed: int, step_index: int, focal_user: int
) -> np.random.Generator:
    sequence = np.random.SeedSequence(
        _derived_seed_int(
            namespace,
            evaluation_seed=evaluation_seed,
            step_index=step_index,
            focal_user=focal_user,
        )
    )
    return np.random.Generator(np.random.PCG64(sequence))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _required_closure_files() -> set[str]:
    paths = {
        SPEC,
        C3_SPEC,
        METHOD,
        DEFAULT_PREREG,
        DEFAULT_INPUT / "main" / "final-checkpoint.pt",
        ORACLE_DIR / "run_c3_disjoint_median_shadow.py",
        REPO / "scripts" / "run_head_pivotality_probe.py",
        *_default_code_paths(),
        *HERE.glob("*.py"),
    }
    return {str(target.resolve().relative_to(REPO)) for target in paths}


def _dependency_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {"python": platform.python_version()}
    for name in ("numpy", "torch", "sgp4"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _frozen_tle_hashes(prereg_path: Path) -> dict[str, str]:
    prereg = _read_json(prereg_path)
    rows = prereg["sections"]["ephemeris"]["frozen_files"]
    return {str(row["file"]): str(row["sha256"]) for row in rows}


def _valid_sha256(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _verify_closure(
    path: Path,
    *,
    prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path = Path(TLE_ROOT_DEFAULT).expanduser(),
) -> tuple[dict[str, Any], str]:
    manifest = _read_json(path)
    if manifest.get("schema") != CLOSURE_SCHEMA:
        raise RuntimeError("invalid Stage-0 closure-manifest schema")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise RuntimeError("closure manifest has no file hashes")
    for relative, expected in files.items():
        target = REPO / str(relative)
        if not target.is_file() or _sha256(target) != str(expected):
            raise RuntimeError(f"closure file drift: {relative}")
    required = _required_closure_files()
    if not required.issubset(files):
        missing = sorted(required - set(files))
        raise RuntimeError("closure manifest misses required files: " + ", ".join(missing))
    if manifest.get("analysis_code_sha256") != EXPECTED_ANALYSIS_CODE_SHA256:
        raise RuntimeError("closure analysis-source digest mismatch")
    if manifest.get("dependency_versions") != _dependency_versions():
        raise RuntimeError("closure dependency-version mismatch")

    expected_tles = _frozen_tle_hashes(prereg_path)
    if manifest.get("tle_files") != expected_tles:
        raise RuntimeError("closure TLE inventory does not match frozen preregistration")
    for relative, expected in expected_tles.items():
        target = tle_root / relative
        if not target.is_file() or _sha256(target) != expected:
            raise RuntimeError(f"closure TLE drift: {relative}")

    tests = manifest.get("test_receipts")
    if not isinstance(tests, list) or len(tests) < 2:
        raise RuntimeError("closure requires detailed C2 and C3 test receipts")
    commands = []
    for receipt in tests:
        if not isinstance(receipt, dict):
            raise RuntimeError("closure test receipt is malformed")
        if receipt.get("exit_code") != 0 or not _valid_sha256(
            receipt.get("stdout_sha256")
        ):
            raise RuntimeError("closure test receipt is not a sealed pass")
        command = str(receipt.get("command", ""))
        if not command:
            raise RuntimeError("closure test receipt omits its exact command")
        commands.append(command)
    for required_test in ("test_c2_stage0.py", "test_run_c3_stage0.py"):
        if not any(required_test in command for command in commands):
            raise RuntimeError(f"closure omits explicit {required_test} execution")
    return manifest, _sha256(path)


def _read_formal_seeds(path: Path, *, closure_sha256: str) -> tuple[int, ...]:
    manifest = _read_json(path)
    if manifest.get("schema") != SEED_SCHEMA:
        raise RuntimeError("invalid Stage-0 seed-manifest schema")
    if manifest.get("closure_manifest_sha256") != closure_sha256:
        raise RuntimeError("seed manifest does not bind the closure manifest")
    seeds = tuple(int(seed) for seed in manifest.get("c2_seeds", ()))
    if len(seeds) != 5 or len(set(seeds)) != 5:
        raise RuntimeError("formal C2 campaign requires five unique seeds")
    c3_seeds = tuple(int(seed) for seed in manifest.get("c3_seeds", ()))
    if len(c3_seeds) != 5 or len(set(c3_seeds)) != 5:
        raise RuntimeError("formal C3 campaign requires five unique seeds")
    if set(seeds) & set(c3_seeds):
        raise RuntimeError("formal C2 and C3 seeds must be mutually disjoint")
    if not manifest.get("repository_disjointness_checked_before_reveal"):
        raise RuntimeError("seed manifest lacks pre-reveal disjointness attestation")
    if not _valid_sha256(manifest.get("disjointness_search_receipt_sha256")):
        raise RuntimeError("seed manifest lacks a sealed disjointness-search receipt")
    return seeds


def _main_actions(
    trainer: Any, states: Sequence[Any], wrapped_masks: Sequence[Any]
) -> np.ndarray:
    encoded = trainer.encode_states(list(states))
    masks = np.stack([row.mask for row in wrapped_masks])
    q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
    return masked_greedy_actions(q1, masks)


def _key_for_action(table: Any, action: int) -> PhysicalKey | None:
    if int(action) == NO_OP_ACTION:
        return None
    association = table.association(int(action))
    return int(association.norad_id), int(association.cell_id)


def _action_for_key(table: Any, key: PhysicalKey | None) -> int | None:
    if key is None:
        return NO_OP_ACTION if table.num_valid == 0 else None
    valid = np.flatnonzero(table.mask)
    matches = [
        int(action)
        for action in valid.tolist()
        if int(table.norad_ids[action]) == key[0]
        and int(table.cell_ids[action]) == key[1]
    ]
    if len(matches) > 1:
        raise RuntimeError(f"duplicate physical key {key} in one slot table")
    return matches[0] if matches else None


def _unique_valid_keys(table: Any) -> tuple[PhysicalKey, ...]:
    keys = {
        (int(table.norad_ids[action]), int(table.cell_ids[action]))
        for action in np.flatnonzero(table.mask).tolist()
    }
    return tuple(sorted(keys))


def _active_keys(outcome: Any) -> tuple[PhysicalKey, ...]:
    return tuple(sorted(tuple(map(int, key)) for key in outcome.resolution.active_beams))


def _anchor_fingerprint(
    wrapped: Any, env_rng: np.random.Generator, observation: Any
) -> tuple[dict[str, Any], str]:
    receipt = {
        "epoch": wrapped.epoch.isoformat(),
        "step_index": int(observation.step_index),
        "wrapped": provenance._wrapped_mutable_state_receipt(wrapped),
        "environment_rng_sha256": provenance._rng_sha(env_rng),
        "candidate_table_sha256": provenance._candidate_table_sha(observation),
        "observation_state_sha256": _value_sha256(observation.state_matrix),
        "observation_mask_sha256": _value_sha256(observation.masks),
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
    }
    return receipt, _value_sha256(receipt)


def _anchor_fingerprint_matches(
    anchor: Mapping[str, Any],
    *,
    expected_fingerprint: Mapping[str, Any] | None,
    expected_fingerprint_sha256: str | None,
) -> bool:
    """Require exact replay equality with the original anchor receipt.

    The digest is useful for a compact receipt, but it is not the only guard:
    callers must provide and match the complete mutable/physical/RNG receipt
    as well.  Supplying only one half of the pair is treated as a failed
    contract rather than silently degrading to a digest-only check.
    """

    if expected_fingerprint is None and expected_fingerprint_sha256 is None:
        return True
    if expected_fingerprint is None or expected_fingerprint_sha256 is None:
        return False
    return bool(
        anchor.get("fingerprint") == dict(expected_fingerprint)
        and anchor.get("fingerprint_sha256") == expected_fingerprint_sha256
    )


def _reconstruct_anchor(
    archive: Any, *, seed: int, prefix_actions: Sequence[np.ndarray]
) -> dict[str, Any]:
    wrapped = checkpoint_loader._make_environment(archive, users=USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    for expected_step, frozen_actions in enumerate(prefix_actions):
        if int(observation.step_index) != expected_step:
            raise RuntimeError("prefix replay step-index drift")
        result = wrapped.step(np.asarray(frozen_actions, dtype=np.int32), env_rng)
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation
    receipt, digest = _anchor_fingerprint(wrapped, env_rng, observation)
    return {
        "wrapped": wrapped,
        "env_rng": env_rng,
        "states": states,
        "masks": masks,
        "observation": observation,
        "fingerprint": receipt,
        "fingerprint_sha256": digest,
    }


def _anchor_replay_matches(
    anchor: Mapping[str, Any],
    *,
    expected_fingerprint: Mapping[str, Any] | None,
    expected_fingerprint_sha256: str | None,
) -> bool:
    """Compare a replay against the complete original anchor receipt."""

    return _anchor_fingerprint_matches(
        anchor,
        expected_fingerprint=expected_fingerprint,
        expected_fingerprint_sha256=expected_fingerprint_sha256,
    )


def _focal_schedule(seed: int) -> dict[int, tuple[int, ...]]:
    rng = np.random.default_rng(int(seed) + 220003)
    return {
        step: tuple(
            int(uid)
            for uid in rng.permutation(USERS)[:FOCAL_USERS_PER_STEP].tolist()
        )
        for step in sorted(ANCHOR_STEPS)
    }


def _current_safe_keys(
    anchor: dict[str, Any], trainer: Any, *, focal_user: int
) -> tuple[PhysicalKey, ...]:
    wrapped = anchor["wrapped"]
    observation = anchor["observation"]
    actions = _main_actions(trainer, anchor["states"], anchor["masks"])
    table = observation.candidates.slot_tables[focal_user]
    original_physics = wrapped.environment.physics
    safe: list[PhysicalKey] = []
    wrapped.environment.physics = replace(original_physics, fading_enabled=False)
    try:
        for key in _unique_valid_keys(table):
            action = _action_for_key(table, key)
            if action is None:
                continue
            candidate = actions.copy()
            candidate[focal_user] = action
            evaluation = wrapped.environment.evaluate_actions(
                candidate, np.random.default_rng(0)
            )
            if bool(evaluation.resolution.served[focal_user]):
                safe.append(key)
    finally:
        wrapped.environment.physics = original_physics
    return tuple(sorted(safe))


def _reference_incumbent_qualification(
    anchor: dict[str, Any],
    trainer: Any,
    *,
    focal_user: int,
    incumbent_key: PhysicalKey,
) -> tuple[bool, str | None, PhysicalKey | None]:
    """Prove that frozen Main continues and serves the incumbent at the anchor."""

    wrapped = anchor["wrapped"]
    observation = anchor["observation"]
    actions = _main_actions(trainer, anchor["states"], anchor["masks"])
    table = observation.candidates.slot_tables[focal_user]
    reference_key = _key_for_action(table, int(actions[focal_user]))
    if reference_key != incumbent_key:
        return False, "main_reference_not_continuing_incumbent", reference_key

    original_physics = wrapped.environment.physics
    wrapped.environment.physics = replace(original_physics, fading_enabled=False)
    try:
        evaluation = wrapped.environment.evaluate_actions(
            actions, np.random.default_rng(0)
        )
    finally:
        wrapped.environment.physics = original_physics
    if not bool(evaluation.resolution.served[focal_user]):
        return False, "main_reference_incumbent_not_served", reference_key
    return True, None, reference_key


def _prepare_forecast_anchor(
    archive: Any,
    *,
    seed: int,
    prefix_actions: Sequence[np.ndarray],
    step_index: int,
    focal_user: int,
) -> tuple[dict[str, Any], np.random.Generator, dict[str, Any]]:
    anchor = _reconstruct_anchor(archive, seed=seed, prefix_actions=prefix_actions)
    forecast_env_rng = _derived_rng(
        FORECAST_ENV_NAMESPACE,
        evaluation_seed=seed,
        step_index=step_index,
        focal_user=focal_user,
    )
    forecast_mobility_rng = _derived_rng(
        FORECAST_MOBILITY_NAMESPACE,
        evaluation_seed=seed,
        step_index=step_index,
        focal_user=focal_user,
    )
    environment = anchor["wrapped"].environment
    actual_environment_sha = provenance._rng_sha(anchor["env_rng"])
    actual_mobility_sha = provenance._rng_sha(environment._mobility_rng)
    forecast_env_sha = provenance._rng_sha(forecast_env_rng)
    forecast_mobility_sha = provenance._rng_sha(forecast_mobility_rng)
    independence = {
        "forecast_environment_is_not_actual_object": (
            forecast_env_rng is not anchor["env_rng"]
        ),
        "forecast_mobility_is_not_actual_object": (
            forecast_mobility_rng is not environment._mobility_rng
        ),
        "forecast_stream_objects_are_separate": (
            forecast_env_rng is not forecast_mobility_rng
        ),
        "actual_environment_mobility_objects_are_separate": (
            anchor["env_rng"] is not environment._mobility_rng
        ),
        "forecast_stream_states_are_domain_separated": (
            forecast_env_sha != forecast_mobility_sha
        ),
        "forecast_environment_state_differs_from_actual": (
            forecast_env_sha != actual_environment_sha
        ),
        "forecast_mobility_state_differs_from_actual": (
            forecast_mobility_sha != actual_mobility_sha
        ),
        # Keep the old keys as aliases in receipts so historical diagnostic
        # readers remain able to distinguish a forecast from realised
        # mobility.  The new checks above are the enforced contract.
        "forecast_is_not_actual_object": (
            forecast_mobility_rng is not environment._mobility_rng
        ),
        "forecast_state_differs_from_actual": (
            forecast_mobility_sha != actual_mobility_sha
        ),
        "forecast_rng_sha256": forecast_env_sha,
        "forecast_environment_rng_sha256": forecast_env_sha,
        "forecast_mobility_rng_sha256": forecast_mobility_sha,
        "actual_environment_rng_sha256": actual_environment_sha,
        "actual_mobility_rng_sha256": actual_mobility_sha,
        "fading_disabled": bool(not environment.physics.fading_enabled),
    }
    environment.physics = replace(environment.physics, fading_enabled=False)
    independence["fading_disabled"] = bool(not environment.physics.fading_enabled)
    required = (
        "forecast_environment_is_not_actual_object",
        "forecast_mobility_is_not_actual_object",
        "forecast_stream_objects_are_separate",
        "actual_environment_mobility_objects_are_separate",
        "forecast_stream_states_are_domain_separated",
        "forecast_environment_state_differs_from_actual",
        "forecast_mobility_state_differs_from_actual",
        "fading_disabled",
    )
    if not all(bool(independence[name]) for name in required):
        raise RuntimeError("forecast RNG lineage or fading-independence contract failed")
    environment._mobility_rng = forecast_mobility_rng
    return anchor, forecast_env_rng, independence


def _reference_nonfocal_script(
    archive: Any,
    trainer: Any,
    *,
    seed: int,
    prefix_actions: Sequence[np.ndarray],
    step_index: int,
    focal_user: int,
    focal_option_key: PhysicalKey | None = None,
    expected_anchor_fingerprint: Mapping[str, Any] | None = None,
    expected_anchor_fingerprint_sha256: str | None = None,
) -> tuple[list[tuple[PhysicalKey | None, ...]], dict[str, Any]]:
    anchor, env_rng, independence = _prepare_forecast_anchor(
        archive,
        seed=seed,
        prefix_actions=prefix_actions,
        step_index=step_index,
        focal_user=focal_user,
    )
    wrapped = anchor["wrapped"]
    states = anchor["states"]
    masks = anchor["masks"]
    observation = anchor["observation"]
    script: list[tuple[PhysicalKey | None, ...]] = []
    option_open = focal_option_key is not None
    terminations: list[dict[str, Any]] = []
    anchor_fingerprint_match = _anchor_fingerprint_matches(
        anchor,
        expected_fingerprint=expected_anchor_fingerprint,
        expected_fingerprint_sha256=expected_anchor_fingerprint_sha256,
    )
    independence["anchor_fingerprint_match"] = anchor_fingerprint_match
    independence["anchor_fingerprint_sha256"] = anchor.get("fingerprint_sha256")
    if expected_anchor_fingerprint_sha256 is not None:
        independence["expected_anchor_fingerprint_sha256"] = (
            expected_anchor_fingerprint_sha256
        )
    if not anchor_fingerprint_match:
        # A forecast generated from a replay-drifted anchor is not a valid
        # counterfactual.  Return a sealed empty script so the caller cannot
        # accidentally score it as an ordinary short forecast.
        independence["script_sha256"] = _value_sha256(script)
        independence["script_role"] = (
            "focal-option-branch" if focal_option_key is not None else "main-reference"
        )
        independence["option_terminations"] = terminations
        return script, independence
    for offset in range(RELEASE_OFFSET + 1):
        actions = _main_actions(trainer, states, masks)
        termination_reason: str | None = None
        if offset >= HOLD_STEPS and option_open:
            option_open = False
            termination_reason = "option_horizon_expired"
            terminations.append({"offset": offset, "reason": termination_reason})
        if option_open and focal_option_key is not None and offset < HOLD_STEPS:
            mapped = _action_for_key(
                observation.candidates.slot_tables[focal_user], focal_option_key
            )
            if mapped is None:
                option_open = False
                termination_reason = "physical_id_expired"
                terminations.append({"offset": offset, "reason": termination_reason})
            else:
                actions[focal_user] = mapped
        script.append(
            physical_action_keys(actions, observation.candidates.slot_tables)
        )
        result = wrapped.step(actions, env_rng)
        outcome = wrapped.last_outcome
        if option_open and offset < HOLD_STEPS and not bool(
            outcome.resolution.served[focal_user]
        ):
            option_open = False
            termination_reason = "focal_service_failure"
            terminations.append({"offset": offset, "reason": termination_reason})
        if bool(result.done) and option_open:
            option_open = False
            termination_reason = "episode_end"
            terminations.append({"offset": offset, "reason": termination_reason})
        states, masks = result.user_states, result.action_masks
        observation = wrapped.last_outcome.observation
        if bool(result.done):
            break
    independence["option_terminations"] = terminations
    independence["script_sha256"] = _value_sha256(script)
    independence["script_role"] = (
        "focal-option-branch" if focal_option_key is not None else "main-reference"
    )
    return script, independence


def _forecast_candidate(
    archive: Any,
    trainer: Any,
    *,
    seed: int,
    prefix_actions: Sequence[np.ndarray],
    step_index: int,
    focal_user: int,
    candidate_key: PhysicalKey,
    nonfocal_script: Sequence[tuple[PhysicalKey | None, ...]],
    nonfocal_script_match: bool = True,
    nonfocal_script_receipt: Mapping[str, Any] | None = None,
    expected_anchor_fingerprint: Mapping[str, Any] | None = None,
    expected_anchor_fingerprint_sha256: str | None = None,
) -> dict[str, Any]:
    anchor, env_rng, independence = _prepare_forecast_anchor(
        archive,
        seed=seed,
        prefix_actions=prefix_actions,
        step_index=step_index,
        focal_user=focal_user,
    )
    wrapped = anchor["wrapped"]
    states = anchor["states"]
    masks = anchor["masks"]
    observation = anchor["observation"]
    anchor_fingerprint_match = _anchor_fingerprint_matches(
        anchor,
        expected_fingerprint=expected_anchor_fingerprint,
        expected_fingerprint_sha256=expected_anchor_fingerprint_sha256,
    )
    independence["anchor_fingerprint_match"] = anchor_fingerprint_match
    independence["anchor_fingerprint_sha256"] = anchor.get("fingerprint_sha256")
    if expected_anchor_fingerprint_sha256 is not None:
        independence["expected_anchor_fingerprint_sha256"] = (
            expected_anchor_fingerprint_sha256
        )
    r2_values: list[float] = []
    margins: list[float] = []
    terminations: list[dict[str, Any]] = []
    option_open = True
    failure: str | None = None
    intervals: list[dict[str, Any]] = []

    if not anchor_fingerprint_match:
        return {
            "candidate_key": list(candidate_key),
            "eligible": False,
            "failure": "forecast_anchor_fingerprint_mismatch",
            "s2_pre": None,
            "worst_link_margin_w": None,
            "terminations": [],
            "intervals": [],
            "forecast_rng_independence": independence,
            "nonfocal_script_receipt": (
                None
                if nonfocal_script_receipt is None
                else dict(nonfocal_script_receipt)
            ),
        }

    # The forecast is a causal counterfactual only while its non-focal Main
    # script agrees with the no-option reference.  Do not silently use a
    # shared script generated for another candidate: focal-induced changes in
    # the other users' actions are a confound and invalidate this candidate.
    if not nonfocal_script_match:
        return {
            "candidate_key": list(candidate_key),
            "eligible": False,
            "failure": "nonfocal_forecast_physical_action_divergence",
            "s2_pre": None,
            "worst_link_margin_w": None,
            "terminations": [],
            "intervals": [],
            "forecast_rng_independence": independence,
            "nonfocal_script_receipt": (
                None
                if nonfocal_script_receipt is None
                else dict(nonfocal_script_receipt)
            ),
        }
    if len(nonfocal_script) < RELEASE_OFFSET + 1:
        return {
            "candidate_key": list(candidate_key),
            "eligible": False,
            "failure": "nonfocal_forecast_script_ended_before_horizon",
            "s2_pre": None,
            "worst_link_margin_w": None,
            "terminations": [],
            "intervals": [],
            "forecast_rng_independence": independence,
            "nonfocal_script_receipt": (
                None
                if nonfocal_script_receipt is None
                else dict(nonfocal_script_receipt)
            ),
        }

    for offset in range(RELEASE_OFFSET + 1):
        actions = _main_actions(trainer, states, masks)
        tables = observation.candidates.slot_tables
        option_open_before = bool(option_open)
        used_option = False
        for uid, key in enumerate(nonfocal_script[offset]):
            if uid == focal_user:
                continue
            mapped = _action_for_key(tables[uid], key)
            if mapped is None:
                failure = f"nonfocal_script_unmappable_offset_{offset}_user_{uid}"
                break
            actions[uid] = mapped
        if failure is not None:
            break

        termination_reason: str | None = None
        if offset >= HOLD_STEPS and option_open:
            option_open = False
            termination_reason = "option_horizon_expired"
            terminations.append({"offset": offset, "reason": termination_reason})

        if offset < HOLD_STEPS and option_open:
            mapped = _action_for_key(tables[focal_user], candidate_key)
            if mapped is None:
                option_open = False
                termination_reason = "physical_id_expired"
                terminations.append({"offset": offset, "reason": termination_reason})
            else:
                actions[focal_user] = mapped
                used_option = True

        outcome_result = wrapped.step(actions, env_rng)
        outcome = wrapped.last_outcome
        served = bool(outcome.resolution.served[focal_user])
        if option_open and offset < HOLD_STEPS and not served:
            option_open = False
            termination_reason = "focal_service_failure"
            terminations.append({"offset": offset, "reason": termination_reason})
            # Retain the terminating transition.  The actual branch closes
            # the option after observing this outage and lets scalarized Main
            # choose on the next interval; a recoverable Main fallback is not
            # itself a forecast invalidity.  Only structural failures (for
            # example non-focal divergence or an episode ending before the
            # fixed four-interval horizon) invalidate the candidate.
        r2 = float(outcome.reward_matrix[focal_user, 1])
        r2_values.append(r2)
        if served:
            margins.append(
                float(
                    wrapped.environment.physics.beam_power_max_w
                    - outcome.link_power_w[focal_user]
                )
            )
        intervals.append(
            {
                "offset": offset,
                "r2_focal": r2,
                "served_focal": served,
                "focal_action_key": _key_for_action(
                    tables[focal_user], int(actions[focal_user])
                ),
                "controller": (
                    "persistence-option" if used_option else "scalarized-main"
                ),
                "option_open_before": option_open_before,
                "option_open_after_step": bool(option_open),
                "termination_reason": termination_reason,
            }
        )
        states, masks = outcome_result.user_states, outcome_result.action_masks
        observation = outcome.observation
        if bool(outcome_result.done) and option_open:
            option_open = False
            terminations.append({"offset": offset, "reason": "episode_end"})
            intervals[-1]["option_open_after_step"] = False
            intervals[-1]["termination_reason"] = "episode_end"
        if bool(outcome_result.done):
            if len(r2_values) < RELEASE_OFFSET + 1:
                failure = "episode_end_before_forecast_horizon"
            break
        if failure is not None:
            break

    if failure is None and len(r2_values) == RELEASE_OFFSET + 1 and not margins:
        failure = "forecast_no_served_interval_for_link_margin"

    return {
        "candidate_key": list(candidate_key),
        "eligible": failure is None and len(r2_values) == RELEASE_OFFSET + 1,
        "failure": failure,
        "s2_pre": float(sum(r2_values)),
        "worst_link_margin_w": float(min(margins)) if margins else None,
        "terminations": terminations,
        "intervals": intervals,
        "forecast_rng_independence": independence,
        "nonfocal_script_receipt": (
            None
            if nonfocal_script_receipt is None
            else dict(nonfocal_script_receipt)
        ),
    }


def _select_pre(rows: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    eligible: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("eligible"):
            continue
        try:
            margin = float(row["worst_link_margin_w"])
        except (TypeError, ValueError, KeyError):
            # A candidate with no served interval has no deterministic link
            # margin and must never reach the ranking key as ``None``.
            continue
        if not math.isfinite(margin):
            continue
        eligible.append(row)
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda row: (
            -float(row["s2_pre"]),
            -float(row["worst_link_margin_w"]),
            tuple(int(value) for value in row["candidate_key"]),
        ),
    )


def _outcome_row(
    outcome: Any,
    actions: np.ndarray,
    observation: Any,
    *,
    rng_before: dict[str, str],
    rng_after: dict[str, str],
    option_receipt: dict[str, Any],
    preview_parity_passed: bool,
) -> dict[str, Any]:
    keys = physical_action_keys(actions, observation.candidates.slot_tables)
    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
    throughput_bps = float(rates.sum())
    system_power_w = float(outcome.system_power_w)
    canonical_ee = float(outcome.energy.system_ee_bits_per_j)
    expected_ee = throughput_bps / system_power_w if system_power_w > 0.0 else math.nan
    identity_residual = canonical_ee - expected_ee
    identity_scale = max(1.0, abs(canonical_ee), abs(expected_ee))
    identity_relative_residual = abs(identity_residual) / identity_scale
    identity_passed = bool(
        system_power_w > 0.0
        and math.isfinite(canonical_ee)
        and math.isfinite(expected_ee)
        and identity_relative_residual <= EE_IDENTITY_RELATIVE_TOLERANCE
    )
    return {
        "step_index": int(outcome.step_index),
        "r2": outcome.reward_matrix[:, 1].astype(float).tolist(),
        "served": np.asarray(outcome.resolution.served, dtype=bool).tolist(),
        "served_count": int(outcome.resolution.served_count),
        "handover": [handover.value for handover in outcome.handovers],
        "physical_keys": [None if key is None else list(key) for key in keys],
        "action_mask_sha256": _value_sha256(observation.masks),
        "actions": np.asarray(actions, dtype=np.int32).tolist(),
        "throughput_bps": throughput_bps,
        "system_power_w": system_power_w,
        "canonical_ee_bits_per_j": canonical_ee,
        "expected_ee_bits_per_j": expected_ee,
        "ee_identity_residual": identity_residual,
        "ee_identity_relative_residual": identity_relative_residual,
        "ee_identity_passed": identity_passed,
        "active_beams": [list(key) for key in _active_keys(outcome)],
        "rng_before": rng_before,
        "rng_after": rng_after,
        "preview_parity_passed": bool(preview_parity_passed),
        "option": option_receipt,
    }


def _window_metrics(rows: Sequence[dict[str, Any]], *, focal_user: int) -> dict[str, Any]:
    if not rows:
        raise RuntimeError("cannot aggregate an empty branch window")
    bits = DECISION_INTERVAL_S * sum(float(row["throughput_bps"]) for row in rows)
    energy = DECISION_INTERVAL_S * sum(float(row["system_power_w"]) for row in rows)
    if energy <= 0.0:
        raise RuntimeError("branch window has non-positive payload energy")
    associations = [
        None
        if row["physical_keys"][focal_user] is None
        else tuple(int(value) for value in row["physical_keys"][focal_user])
        for row in rows
    ]
    reversals = sum(
        associations[index] is not None
        and associations[index - 2] is not None
        and associations[index] == associations[index - 2]
        and associations[index] != associations[index - 1]
        for index in range(2, len(associations))
    )
    focal_handovers = [str(row["handover"][focal_user]) for row in rows]
    system_handovers = [
        str(handover)
        for row in rows
        for handover in row["handover"]
    ]
    system_reversals = 0
    for uid in range(USERS):
        user_associations = [
            None
            if row["physical_keys"][uid] is None
            else tuple(int(value) for value in row["physical_keys"][uid])
            for row in rows
        ]
        system_reversals += sum(
            user_associations[index] is not None
            and user_associations[index - 2] is not None
            and user_associations[index] == user_associations[index - 2]
            and user_associations[index] != user_associations[index - 1]
            for index in range(2, len(user_associations))
        )
    return {
        "intervals": len(rows),
        "focal_r2": float(sum(float(row["r2"][focal_user]) for row in rows)),
        "system_r2": float(sum(sum(map(float, row["r2"])) for row in rows)),
        "focal_phi1": focal_handovers.count(HandoverClass.INTRA_SATELLITE.value),
        "focal_phi2": focal_handovers.count(HandoverClass.INTER_SATELLITE.value),
        "focal_reversals": int(reversals),
        "system_phi1": system_handovers.count(HandoverClass.INTRA_SATELLITE.value),
        "system_phi2": system_handovers.count(HandoverClass.INTER_SATELLITE.value),
        "system_reversals": int(system_reversals),
        "focal_served_all": all(bool(row["served"][focal_user]) for row in rows),
        "served_fraction": float(
            sum(int(row["served_count"]) for row in rows) / (USERS * len(rows))
        ),
        "useful_bits": float(bits),
        "payload_energy_j": float(energy),
        "mean_system_power_w": float(
            statistics.fmean(float(row["system_power_w"]) for row in rows)
        ),
        "system_ee_bits_per_j": float(bits / energy),
        "all_ee_identity_passed": all(
            bool(row["ee_identity_passed"]) for row in rows
        ),
    }


def _branch_rng_contract(branches: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Check common-random-number lineage without sharing mutable generators.

    Every realised counterfactual starts from equal environment and mobility
    states, but each branch owns a distinct generator object.  Environment
    fading is disabled for this Stage-0 gate, so an accidental fading draw
    cannot be hidden behind a mobility draw or alter later branches.
    """

    names = sorted(branches)
    env_rngs = [branches[name]["env_rng"] for name in names]
    environments = [branches[name]["wrapped"].environment for name in names]
    mobility_rngs = [environment._mobility_rng for environment in environments]
    age_rngs = [environment._age_rng for environment in environments]
    env_hashes = [provenance._rng_sha(rng) for rng in env_rngs]
    mobility_hashes = [provenance._rng_sha(rng) for rng in mobility_rngs]
    age_hashes = [provenance._rng_sha(rng) for rng in age_rngs]
    fading_flags = [bool(environment.physics.fading_enabled) for environment in environments]

    def _all_distinct(values: Sequence[Any]) -> bool:
        return len({id(value) for value in values}) == len(values)

    checks = {
        "environment_rng_objects_distinct": _all_distinct(env_rngs),
        "mobility_rng_objects_distinct": _all_distinct(mobility_rngs),
        "age_rng_objects_distinct_or_all_none": (
            all(value is None for value in age_rngs) or _all_distinct(age_rngs)
        ),
        "environment_mobility_objects_distinct": all(
            env_rng is not mobility_rng
            for env_rng, mobility_rng in zip(env_rngs, mobility_rngs, strict=True)
        ),
        "environment_age_objects_distinct_or_none": all(
            age_rng is None or age_rng is not env_rng
            for env_rng, age_rng in zip(env_rngs, age_rngs, strict=True)
        ),
        "environment_rng_lineage_equal": len(set(env_hashes)) == 1,
        "mobility_rng_lineage_equal": len(set(mobility_hashes)) == 1,
        "age_rng_lineage_equal": len(set(age_hashes)) == 1,
        "environment_mobility_streams_domain_separated": all(
            env_hash != mobility_hash
            for env_hash, mobility_hash in zip(
                env_hashes, mobility_hashes, strict=True
            )
        ),
        "fading_disabled_in_every_branch": not any(fading_flags),
    }
    return {
        "branches": names,
        "initial_rng_sha256": {
            "environment": dict(zip(names, env_hashes, strict=True)),
            "mobility": dict(zip(names, mobility_hashes, strict=True)),
            "age": dict(zip(names, age_hashes, strict=True)),
        },
        "fading_enabled_by_branch": dict(zip(names, fading_flags, strict=True)),
        "checks": checks,
        "passed": all(bool(value) for value in checks.values()),
    }


def _run_actual_branches(
    archive: Any,
    trainer: Any,
    *,
    seed: int,
    prefix_actions: Sequence[np.ndarray],
    focal_user: int,
    choices: dict[str, PhysicalKey],
    expected_anchor_fingerprint: Mapping[str, Any] | None = None,
    expected_anchor_fingerprint_sha256: str | None = None,
) -> dict[str, Any]:
    branches = {
        name: _reconstruct_anchor(archive, seed=seed, prefix_actions=prefix_actions)
        for name in choices
    }
    fingerprint_shas = {row["fingerprint_sha256"] for row in branches.values()}
    failures: list[str] = []
    anchor_replay_matches = {
        name: _anchor_replay_matches(
            branch,
            expected_fingerprint=expected_anchor_fingerprint,
            expected_fingerprint_sha256=expected_anchor_fingerprint_sha256,
        )
        for name, branch in branches.items()
    }
    if not all(anchor_replay_matches.values()):
        failures.extend(
            f"anchor_replay_fingerprint_mismatch_{name}"
            for name, passed in sorted(anchor_replay_matches.items())
            if not passed
        )
        names = sorted(branches)
        return {
            "anchor_fingerprint_sha256": (
                expected_anchor_fingerprint_sha256
                if expected_anchor_fingerprint_sha256 is not None
                else next(iter(fingerprint_shas), None)
            ),
            "anchor_fingerprint": (
                None
                if expected_anchor_fingerprint is None
                else dict(expected_anchor_fingerprint)
            ),
            "branch_fingerprint_sha256": {
                name: branches[name]["fingerprint_sha256"] for name in names
            },
            "branch_fingerprints": {
                name: branches[name]["fingerprint"] for name in names
            },
            "engineering_failures": sorted(set(failures)),
            "anchor_replay_fingerprint_match": anchor_replay_matches,
            "expected_anchor_fingerprint_sha256": (
                expected_anchor_fingerprint_sha256
            ),
            "rng_contract": {"passed": False, "checks": {}},
            "rng_lineage": [],
            "nonfocal_equality": [],
            "option_terminations": {name: [] for name in names},
            "metrics": {},
            "intervals": {},
        }
    if len(fingerprint_shas) != 1:
        failures.append("anchor_fingerprint_mismatch")
    for branch in branches.values():
        environment = branch["wrapped"].environment
        environment.physics = replace(environment.physics, fading_enabled=False)

    option_open = {name: True for name in branches}
    option_terminations: dict[str, list[dict[str, Any]]] = {
        name: [] for name in branches
    }
    rng_contract = _branch_rng_contract(branches)
    if not bool(rng_contract["passed"]):
        failures.extend(
            f"rng_contract_{name}"
            for name, passed in rng_contract["checks"].items()
            if not passed
        )
    rows = {name: [] for name in branches}
    nonfocal_equality_receipts: list[dict[str, Any]] = []
    rng_lineage_receipts: list[dict[str, Any]] = []
    offset = 0
    while True:
        action_rows: dict[str, np.ndarray] = {}
        key_rows: dict[str, tuple[PhysicalKey | None, ...]] = {}
        option_receipts: dict[str, dict[str, Any]] = {}
        rng_before_by_branch: dict[str, dict[str, str | None]] = {}
        rng_after_by_branch: dict[str, dict[str, str | None]] = {}
        done_flags: list[bool] = []
        for name, branch in branches.items():
            actions = _main_actions(trainer, branch["states"], branch["masks"])
            observation = branch["observation"]
            tables = observation.candidates.slot_tables
            open_before = bool(option_open[name])
            mapped_action: int | None = None
            termination_reason: str | None = None
            if offset >= HOLD_STEPS and option_open[name]:
                option_open[name] = False
                termination_reason = "option_horizon_expired"
                option_terminations[name].append(
                    {"offset": offset, "reason": termination_reason}
                )
            if offset < HOLD_STEPS and option_open[name]:
                mapped = _action_for_key(tables[focal_user], choices[name])
                if mapped is None:
                    option_open[name] = False
                    termination_reason = "physical_id_expired"
                    option_terminations[name].append(
                        {"offset": offset, "reason": termination_reason}
                    )
                else:
                    actions[focal_user] = mapped
                    mapped_action = int(mapped)
            action_rows[name] = actions
            key_rows[name] = physical_action_keys(actions, tables)
            option_receipts[name] = {
                "target_physical_key": list(choices[name]),
                "open_before": open_before,
                "open_after_mapping": bool(option_open[name]),
                "mapped_action": mapped_action,
                "termination_reason": termination_reason,
                "released_to_main": bool(offset >= HOLD_STEPS or not option_open[name]),
                "executed_focal_physical_key": (
                    None
                    if key_rows[name][focal_user] is None
                    else list(key_rows[name][focal_user])
                ),
            }

        names = sorted(branches)
        reference_nonfocal = tuple(
            key for uid, key in enumerate(key_rows[names[0]]) if uid != focal_user
        )
        branch_nonfocal = {
            names[0]: [None if key is None else list(key) for key in reference_nonfocal]
        }
        equal_nonfocal = True
        for name in names[1:]:
            other = tuple(
                key for uid, key in enumerate(key_rows[name]) if uid != focal_user
            )
            branch_nonfocal[name] = [
                None if key is None else list(key) for key in other
            ]
            if other != reference_nonfocal:
                equal_nonfocal = False
                failures.append(f"nonfocal_physical_action_divergence_offset_{offset}")
        nonfocal_equality_receipts.append(
            {
                "offset": offset,
                "equal": equal_nonfocal,
                "physical_action_sha256_by_branch": {
                    name: _value_sha256(value)
                    for name, value in branch_nonfocal.items()
                },
                "physical_actions_by_branch": branch_nonfocal,
            }
        )

        for name, branch in branches.items():
            pre_observation = branch["observation"]
            rng_before = {
                "environment_rng_sha256": provenance._rng_sha(branch["env_rng"]),
                "mobility_rng_sha256": provenance._rng_sha(
                    branch["wrapped"].environment._mobility_rng
                ),
            }
            rng_before_by_branch[name] = rng_before
            preview = branch["wrapped"].environment.evaluate_actions(
                action_rows[name], branch["env_rng"]
            )
            result = branch["wrapped"].step(action_rows[name], branch["env_rng"])
            outcome = branch["wrapped"].last_outcome
            preview_parity_passed = True
            try:
                provenance.base.v1._assert_full_preview_parity(preview, outcome)
            except RuntimeError as exc:
                preview_parity_passed = False
                failures.append(f"preview_parity_{name}_offset_{offset}:{exc}")
            rng_after = {
                "environment_rng_sha256": provenance._rng_sha(branch["env_rng"]),
                "mobility_rng_sha256": provenance._rng_sha(
                    branch["wrapped"].environment._mobility_rng
                ),
            }
            rng_after_by_branch[name] = rng_after
            outcome_receipt = _outcome_row(
                outcome,
                action_rows[name],
                pre_observation,
                rng_before=rng_before,
                rng_after=rng_after,
                option_receipt=option_receipts[name],
                preview_parity_passed=preview_parity_passed,
            )
            if not outcome_receipt["ee_identity_passed"]:
                failures.append(f"ee_identity_{name}_offset_{offset}")
            rows[name].append(outcome_receipt)
            served = bool(outcome.resolution.served[focal_user])
            if option_open[name] and offset < HOLD_STEPS and not served:
                option_open[name] = False
                option_terminations[name].append(
                    {"offset": offset, "reason": "focal_service_failure"}
                )
                option_receipts[name]["termination_reason"] = (
                    "focal_service_failure"
                )
                option_receipts[name]["termination_reason_after_step"] = (
                    "focal_service_failure"
                )
            if bool(result.done) and option_open[name]:
                option_open[name] = False
                option_terminations[name].append(
                    {"offset": offset, "reason": "episode_end"}
                )
                option_receipts[name]["termination_reason"] = "episode_end"
                option_receipts[name]["termination_reason_after_step"] = (
                    "episode_end"
                )
            option_receipts[name]["open_after_step"] = bool(option_open[name])
            branch["states"] = result.user_states
            branch["masks"] = result.action_masks
            branch["observation"] = outcome.observation
            done_flags.append(bool(result.done))

        env_before_values = {
            value.get("environment_rng_sha256")
            for value in rng_before_by_branch.values()
        }
        mobility_before_values = {
            value.get("mobility_rng_sha256")
            for value in rng_before_by_branch.values()
        }
        env_after_values = {
            value.get("environment_rng_sha256")
            for value in rng_after_by_branch.values()
        }
        mobility_after_values = {
            value.get("mobility_rng_sha256")
            for value in rng_after_by_branch.values()
        }
        lineage_equal = bool(
            len(env_before_values) == 1
            and len(mobility_before_values) == 1
            and len(env_after_values) == 1
            and len(mobility_after_values) == 1
        )
        if not lineage_equal:
            failures.append(f"cross_branch_rng_lineage_divergence_offset_{offset}")
        rng_lineage_receipts.append(
            {
                "offset": offset,
                "before_by_branch": rng_before_by_branch,
                "after_by_branch": rng_after_by_branch,
                "common_random_numbers_equal": lineage_equal,
            }
        )

        if len(set(done_flags)) != 1:
            failures.append(f"branch_done_divergence_offset_{offset}")
            break
        if done_flags[0]:
            break
        offset += 1

    metrics = {}
    for name, branch_rows in rows.items():
        if len(branch_rows) < RELEASE_OFFSET + 1:
            failures.append(f"branch_too_short_for_release_{name}")
            continue
        metrics[name] = {
            "option": _window_metrics(branch_rows[:HOLD_STEPS], focal_user=focal_user),
            "post_release": _window_metrics(
                branch_rows[: RELEASE_OFFSET + 1], focal_user=focal_user
            ),
            "full": _window_metrics(branch_rows, focal_user=focal_user),
        }
    return {
        "anchor_fingerprint_sha256": next(iter(fingerprint_shas), None),
        "anchor_fingerprint": branches[sorted(branches)[0]]["fingerprint"],
        "branch_fingerprint_sha256": {
            name: row["fingerprint_sha256"] for name, row in branches.items()
        },
        "branch_fingerprints": {
            name: row["fingerprint"] for name, row in branches.items()
        },
        "anchor_replay_fingerprint_match": anchor_replay_matches,
        "expected_anchor_fingerprint_sha256": (
            expected_anchor_fingerprint_sha256
        ),
        "engineering_failures": sorted(set(failures)),
        "rng_contract": rng_contract,
        "rng_lineage": rng_lineage_receipts,
        "nonfocal_equality": nonfocal_equality_receipts,
        "option_terminations": option_terminations,
        "metrics": metrics,
        "intervals": rows,
    }


def _nonfocal_script_signature(
    script: Sequence[Sequence[PhysicalKey | None]], *, focal_user: int
) -> tuple[tuple[PhysicalKey | None, ...], ...]:
    """Canonicalise a Main script after removing the intervention user."""

    return tuple(
        tuple(key for uid, key in enumerate(row) if uid != focal_user)
        for row in script
    )


def _anchor_row(
    archive: Any,
    trainer: Any,
    *,
    seed: int,
    step_index: int,
    focal_user: int,
    prefix_actions: Sequence[np.ndarray],
) -> dict[str, Any]:
    anchor = _reconstruct_anchor(archive, seed=seed, prefix_actions=prefix_actions)
    ledger = anchor["wrapped"].environment._ledgers[focal_user]
    incumbent = ledger.previous
    base = {
        "evaluation_seed": int(seed),
        "step_index": int(step_index),
        "focal_user": int(focal_user),
        "anchor_fingerprint": anchor["fingerprint"],
        "anchor_fingerprint_sha256": anchor["fingerprint_sha256"],
    }
    if not isinstance(incumbent, Association):
        return base | {"status": "ineligible", "reason": "no_served_incumbent"}
    incumbent_key = (int(incumbent.norad_id), int(incumbent.cell_id))
    qualifies, qualification_reason, reference_key = (
        _reference_incumbent_qualification(
            anchor,
            trainer,
            focal_user=focal_user,
            incumbent_key=incumbent_key,
        )
    )
    if not qualifies:
        return base | {
            "status": "ineligible",
            "reason": qualification_reason,
            "incumbent_key": list(incumbent_key),
            "main_reference_key": (
                None if reference_key is None else list(reference_key)
            ),
        }
    safe_keys = _current_safe_keys(anchor, trainer, focal_user=focal_user)
    if incumbent_key not in safe_keys:
        return base | {
            "status": "ineligible",
            "reason": "incumbent_not_current_safe",
            "incumbent_key": list(incumbent_key),
            "safe_keys": [list(key) for key in safe_keys],
        }
    if len(safe_keys) < 2:
        return base | {
            "status": "ineligible",
            "reason": "fewer_than_two_current_safe_ids",
            "incumbent_key": list(incumbent_key),
            "safe_keys": [list(key) for key in safe_keys],
        }

    reference_nonfocal_script, reference_independence = _reference_nonfocal_script(
        archive,
        trainer,
        seed=seed,
        prefix_actions=prefix_actions,
        step_index=step_index,
        focal_user=focal_user,
        expected_anchor_fingerprint=anchor["fingerprint"],
        expected_anchor_fingerprint_sha256=anchor["fingerprint_sha256"],
    )
    if not reference_independence.get("anchor_fingerprint_match", True):
        return base | {
            "status": "ineligible",
            "reason": "forecast_anchor_fingerprint_mismatch",
            "forecast_rng_independence": reference_independence,
        }
    reference_signature = _nonfocal_script_signature(
        reference_nonfocal_script, focal_user=focal_user
    )
    reference_script_sha = _value_sha256(reference_signature)
    forecasts: list[dict[str, Any]] = []
    for key in safe_keys:
        # Generate a fresh, branch-local script for this candidate.  Reusing
        # one script for all candidates makes the forecast depend on another
        # candidate's counterfactual trajectory and can hide focal-induced
        # non-focal divergence.
        candidate_nonfocal_script, candidate_independence = (
            _reference_nonfocal_script(
                archive,
                trainer,
                seed=seed,
                prefix_actions=prefix_actions,
                step_index=step_index,
                focal_user=focal_user,
                focal_option_key=key,
                expected_anchor_fingerprint=anchor["fingerprint"],
                expected_anchor_fingerprint_sha256=anchor["fingerprint_sha256"],
            )
        )
        candidate_signature = _nonfocal_script_signature(
            candidate_nonfocal_script, focal_user=focal_user
        )
        candidate_script_sha = _value_sha256(candidate_signature)
        script_match = candidate_signature == reference_signature
        script_receipt = {
            "reference_script_sha256": reference_script_sha,
            "candidate_script_sha256": candidate_script_sha,
            "matched_reference_nonfocal_actions": bool(script_match),
            "reference_script_length": len(reference_signature),
            "candidate_script_length": len(candidate_signature),
            "reference_forecast_rng": reference_independence,
            "candidate_forecast_rng": candidate_independence,
        }
        forecast = _forecast_candidate(
            archive,
            trainer,
            seed=seed,
            prefix_actions=prefix_actions,
            step_index=step_index,
            focal_user=focal_user,
            candidate_key=key,
            nonfocal_script=candidate_nonfocal_script,
            nonfocal_script_match=script_match,
            nonfocal_script_receipt=script_receipt,
            expected_anchor_fingerprint=anchor["fingerprint"],
            expected_anchor_fingerprint_sha256=anchor["fingerprint_sha256"],
        )
        forecast["nonfocal_script_receipt"] = script_receipt
        forecasts.append(forecast)
    selected = _select_pre(forecasts)
    if selected is None:
        return base | {
            "status": "ineligible",
            "reason": "no_forecast_valid_candidate",
            "incumbent_key": list(incumbent_key),
            "safe_keys": [list(key) for key in safe_keys],
            "forecast_rows": forecasts,
            "forecast_rng_independence": reference_independence,
            "reference_nonfocal_script_sha256": reference_script_sha,
        }

    random_rng = _derived_rng(
        RANDOM_NAMESPACE,
        evaluation_seed=seed,
        step_index=step_index,
        focal_user=focal_user,
    )
    random_key = safe_keys[int(random_rng.integers(0, len(safe_keys)))]
    selected_key = tuple(int(value) for value in selected["candidate_key"])
    actual = _run_actual_branches(
        archive,
        trainer,
        seed=seed,
        prefix_actions=prefix_actions,
        focal_user=focal_user,
        choices={
            "C2-PRE": selected_key,
            "C2-RANDOM": random_key,
            "C2-STAY": incumbent_key,
        },
        expected_anchor_fingerprint=anchor["fingerprint"],
        expected_anchor_fingerprint_sha256=anchor["fingerprint_sha256"],
    )
    return base | {
        "status": "evaluated",
        "incumbent_key": list(incumbent_key),
        "main_reference_key": list(reference_key),
        "safe_keys": [list(key) for key in safe_keys],
        "selected_pre_key": list(selected_key),
        "selected_random_key": list(random_key),
        "forecast_rows": forecasts,
        "forecast_rng_independence": reference_independence,
        "reference_nonfocal_script_sha256": reference_script_sha,
        "actual": actual,
    }


def _run_seed(archive: Any, trainer: Any, *, seed: int) -> dict[str, Any]:
    wrapped = checkpoint_loader._make_environment(archive, users=USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    schedule = _focal_schedule(seed)
    prefix_actions: list[np.ndarray] = []
    anchors: list[dict[str, Any]] = []

    while True:
        step_index = int(observation.step_index)
        actions = _main_actions(trainer, states, masks)
        if step_index in ANCHOR_STEPS:
            for focal_user in schedule[step_index]:
                anchors.append(
                    _anchor_row(
                        archive,
                        trainer,
                        seed=seed,
                        step_index=step_index,
                        focal_user=focal_user,
                        prefix_actions=prefix_actions,
                    )
                )
        prefix_actions.append(actions.copy())
        result = wrapped.step(actions, env_rng)
        if result.done:
            break
        states, masks = result.user_states, result.action_masks
        observation = wrapped.last_outcome.observation
    return {
        "evaluation_seed": int(seed),
        "focal_schedule": {str(k): list(v) for k, v in schedule.items()},
        "anchors": anchors,
    }


def _mean(values: Iterable[float]) -> float:
    rows = [float(value) for value in values]
    return float(statistics.fmean(rows)) if rows else math.nan


def _aggregate(rollouts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    all_rows = [row for rollout in rollouts for row in rollout["anchors"]]
    evaluated = [row for row in all_rows if row["status"] == "evaluated"]
    engineering_failures = [
        {
            "seed": row["evaluation_seed"],
            "step": row["step_index"],
            "user": row["focal_user"],
            "failure": failure,
        }
        for row in evaluated
        for failure in row["actual"]["engineering_failures"]
    ]
    by_control: dict[str, Any] = {}
    for control in ("C2-RANDOM", "C2-STAY"):
        seed_rows: dict[int, dict[str, float]] = {}
        pooled_full: list[float] = []
        pooled_release: list[float] = []
        pooled_ee: list[float] = []
        pooled_service: list[float] = []
        for rollout in rollouts:
            deltas_full: list[float] = []
            deltas_release: list[float] = []
            deltas_ee: list[float] = []
            deltas_service: list[float] = []
            for row in rollout["anchors"]:
                if row["status"] != "evaluated":
                    continue
                metrics = row["actual"]["metrics"]
                if "C2-PRE" not in metrics or control not in metrics:
                    continue
                pre = metrics["C2-PRE"]
                ctl = metrics[control]
                deltas_full.append(pre["full"]["focal_r2"] - ctl["full"]["focal_r2"])
                deltas_release.append(
                    pre["post_release"]["focal_r2"]
                    - ctl["post_release"]["focal_r2"]
                )
                deltas_ee.append(
                    pre["full"]["system_ee_bits_per_j"]
                    - ctl["full"]["system_ee_bits_per_j"]
                )
                deltas_service.append(
                    pre["full"]["served_fraction"] - ctl["full"]["served_fraction"]
                )
            seed = int(rollout["evaluation_seed"])
            seed_rows[seed] = {
                "support": len(deltas_full),
                "mean_delta_r2_full": _mean(deltas_full),
                "mean_delta_r2_post_release": _mean(deltas_release),
                "mean_delta_ee_bits_per_j": _mean(deltas_ee),
                "mean_delta_served_fraction": _mean(deltas_service),
            }
            pooled_full.extend(deltas_full)
            pooled_release.extend(deltas_release)
            pooled_ee.extend(deltas_ee)
            pooled_service.extend(deltas_service)
        full_seed_means = [
            row["mean_delta_r2_full"]
            for row in seed_rows.values()
            if row["support"] > 0
        ]
        release_seed_means = [
            row["mean_delta_r2_post_release"]
            for row in seed_rows.values()
            if row["support"] > 0
        ]
        by_control[control] = {
            "by_seed": {str(seed): row for seed, row in seed_rows.items()},
            "pooled_mean_delta_r2_full": _mean(pooled_full),
            "pooled_mean_delta_r2_post_release": _mean(pooled_release),
            "pooled_mean_delta_ee_bits_per_j": _mean(pooled_ee),
            "pooled_mean_delta_served_fraction": _mean(pooled_service),
            "positive_seed_means_full": sum(value > 0.0 for value in full_seed_means),
            "positive_seed_means_post_release": sum(
                value > 0.0 for value in release_seed_means
            ),
        }

    support_by_seed = {
        int(rollout["evaluation_seed"]): sum(
            row["status"] == "evaluated" for row in rollout["anchors"]
        )
        for rollout in rollouts
    }
    focal_service_regressions: list[dict[str, Any]] = []
    for row in evaluated:
        actual_rows = row["actual"].get("intervals", {})
        pre_rows = actual_rows.get("C2-PRE", ())
        for control in ("C2-RANDOM", "C2-STAY"):
            control_rows = actual_rows.get(control, ())
            if len(pre_rows) != len(control_rows):
                focal_service_regressions.append(
                    {
                        "seed": row["evaluation_seed"],
                        "step": row["step_index"],
                        "user": row["focal_user"],
                        "control": control,
                        "offset": None,
                        "reason": "branch_length_mismatch",
                    }
                )
                continue
            for offset, (pre_interval, control_interval) in enumerate(
                zip(pre_rows, control_rows, strict=True)
            ):
                uid = int(row["focal_user"])
                if bool(control_interval["served"][uid]) and not bool(
                    pre_interval["served"][uid]
                ):
                    focal_service_regressions.append(
                        {
                            "seed": row["evaluation_seed"],
                            "step": row["step_index"],
                            "user": uid,
                            "control": control,
                            "offset": offset,
                            "reason": "served_to_unserved",
                        }
                    )
    support_pass = bool(
        len(evaluated) >= 20
        and len(support_by_seed) == 5
        and all(value >= 1 for value in support_by_seed.values())
    )
    direction_pass = all(
        values["pooled_mean_delta_r2_full"] > 0.0
        and values["pooled_mean_delta_r2_post_release"] > 0.0
        and values["positive_seed_means_full"] >= 4
        and values["positive_seed_means_post_release"] >= 4
        for values in by_control.values()
    )
    service_pass = bool(
        not focal_service_regressions
        and all(
            values["pooled_mean_delta_served_fraction"] >= -SERVICE_TOLERANCE
            for values in by_control.values()
        )
    )
    if engineering_failures:
        decision = "C2_STAGE0_CERTIFICATE_FAILURE"
    elif support_pass and direction_pass and service_pass:
        decision = "C2_STAGE0_PASS_TO_FIXTURES_ONLY"
    else:
        decision = "C2_STAGE0_FAIL_DROP_ROLE"
    return {
        "sampled_anchors": len(all_rows),
        "evaluated_anchors": len(evaluated),
        "support_by_seed": {str(k): v for k, v in support_by_seed.items()},
        "engineering_failures": engineering_failures,
        "focal_service_regressions": focal_service_regressions,
        "controls": by_control,
        "support_pass": support_pass,
        "direction_pass": direction_pass,
        "service_pass": service_pass,
        "decision": decision,
    }


def _runtime_receipt() -> dict[str, Any]:
    packages = {}
    for name in ("numpy", "torch", "sgp4"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser())
    parser.add_argument("--closure-manifest", type=Path, required=True)
    parser.add_argument("--seed-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    if _sha256(SPEC) != EXPECTED_C2_SPEC_SHA256:
        raise RuntimeError("C2 Stage-0 specification changed")
    if _sha256(C3_SPEC) != EXPECTED_C3_SPEC_SHA256:
        raise RuntimeError("companion C3 Stage-0 specification changed")
    if _sha256(METHOD) != EXPECTED_METHOD_SHA256:
        raise RuntimeError("SMC-ER method contract changed")
    if _sha256(args.prereg) != EXPECTED_PREREG_SHA256:
        raise RuntimeError("frozen preregistration changed")
    if _code_sha256(_default_code_paths()) != EXPECTED_ANALYSIS_CODE_SHA256:
        raise RuntimeError("reviewed analysis source changed")
    closure, closure_sha = _verify_closure(
        args.closure_manifest,
        prereg_path=args.prereg,
        tle_root=args.tle_root,
    )
    seeds = _read_formal_seeds(args.seed_manifest, closure_sha256=closure_sha)
    record = read_prereg(args.prereg)

    with tempfile.TemporaryDirectory(prefix="mcrl-c2-stage0-") as temp:
        archive = checkpoint_loader._frozen_archive(
            record, args.tle_root, Path(temp) / "frozen-tle"
        )
        trainer, checkpoint = checkpoint_loader._verify_and_load_trainer(
            record, archive, run_dir=args.input_dir / "main", users=USERS
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("corrected Main checkpoint changed")
        rollouts = [_run_seed(archive, trainer, seed=seed) for seed in seeds]

    output = {
        "schema": OUTPUT_SCHEMA,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "claim_boundary": (
            "legacy-geometry, fading-off, non-training Stage-0 paired evidence "
            "only; no Q2 learnability, Main transfer, actual-fading, carrier, "
            "training, effectiveness, joint-benefit, or novelty claim"
        ),
        "inputs": {
            "method_sha256": _sha256(METHOD),
            "spec_sha256": _sha256(SPEC),
            "runner_sha256": _sha256(Path(__file__).resolve()),
            "closure_manifest_sha256": closure_sha,
            "seed_manifest_sha256": _sha256(args.seed_manifest),
            "checkpoint_sha256": checkpoint["checkpoint_sha256"],
            "prereg_sha256": _sha256(args.prereg),
            "analysis_code_sha256": _code_sha256(_default_code_paths()),
            "closure_schema": closure["schema"],
        },
        "runtime": _runtime_receipt(),
        "seeds": list(seeds),
        "rollouts": rollouts,
        "aggregate": _aggregate(rollouts),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staged = args.output.with_name(args.output.name + ".tmp")
    if staged.exists():
        raise FileExistsError(f"refusing to overwrite staged output: {staged}")
    staged.write_text(
        json.dumps(output, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )
    os.replace(staged, args.output)
    print(json.dumps({"output": str(args.output), "decision": output["aggregate"]["decision"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
