#!/usr/bin/env python3
"""V0.22 two-user coalition-residual current-slot mechanics probe.

This runner is deliberately rejection-oriented.  It scans only predeclared
TRAIN worlds for the first topology-qualified two-user source beam, opens the
four fixed profiles 00/10/01/11, checks the named-coalition identity, and then
performs the literal row-wise Q1+Q2+Q3 composition once.  It owns no learner,
does not open TEST, and cannot authorize episode training.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_coalition_residual_c3 import (  # noqa: E402
    COALITION_RESIDUAL_C3_SCHEMA,
    build_coalition_residual_surface,
)


V020_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "run_v020_repriced_c3_gate.py"
)
CONTRACT = HERE / "COALITION-RESIDUAL-MECHANICS-PROBE-CONTRACT-2026-09-05.md"
CONTRACT_SHA256 = "af32646dc6995c776e8bf341f20d4a7984fd67c498fcca60fa67e1d50b9b66f9"
FORMULA = REPO / "src" / "mcrl" / "runtime" / "ee_axis_coalition_residual_c3.py"
FORMULA_SHA256 = "70ebb7d9fec48397c2c3935ca64a579874483987020e903fa04c312a4b2f80c6"
PREREG_SHA256 = "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
PREFLIGHT = HERE / "preflight_v022_coalition_residual.py"
PREFLIGHT_MANIFEST = HERE / "PREFLIGHT-MANIFEST.json"
PREFLIGHT_MANIFEST_DIGEST = HERE / "PREFLIGHT-MANIFEST.sha256"

WORLDS = (2026121701, 2026121702, 2026121703, 2026121704)
LINEAGE = 2026092101
FIELD_COMPONENT = "MCRL_V022_C3_COALITION_RESIDUAL_V1"
LAMBDA_BITS_PER_J = float.fromhex("0x1.c3c0a7b6b86d3p+26")
KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
STEPS_PER_EPISODE = 10
SCHEMA = "multi-catfish-mcrl-v022-c3-coalition-residual-mechanics-probe-v1"
CLAIM_CEILING = (
    "TRAIN_TOPOLOGY_SELECTED_CURRENT_SLOT_MECHANICS_NO_LEARNER_NO_EPISODE_TRAINING_NO_TEST"
)


class V022CoalitionProbeError(RuntimeError):
    """The frozen V0.22 mechanics-probe boundary was violated."""


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V022CoalitionProbeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _validate_external_preflight(
    *, manifest: Path, manifest_digest: Path, prereg: Path
) -> dict[str, Any]:
    """Validate the external manifest before loading any inherited runner.

    The preflight module intentionally does not import this runner.  Keeping
    this check outside the runner makes the runner hash non-circular: the
    manifest pins this file, while its companion file pins the manifest.
    """

    preflight = _load_module("mcrl_v022_external_preflight", PREFLIGHT)
    try:
        receipt = preflight.validate_manifest(
            Path(manifest),
            manifest_digest_path=Path(manifest_digest),
            repo=REPO,
            prereg_path=Path(prereg),
        )
    except Exception as error:
        raise V022CoalitionProbeError(f"external preflight failed: {error}") from error
    if not isinstance(receipt, dict) or receipt.get("status") != "PASS":
        raise V022CoalitionProbeError("external preflight did not return PASS")
    return receipt


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise V022CoalitionProbeError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_default(value: object) -> bool | int | float:
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("non-finite scalar")
        return result
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=_canonical_default,
    ).encode("ascii")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _masked_argmax(values: np.ndarray, legal: np.ndarray) -> np.ndarray:
    scores = np.asarray(values, dtype=np.float64)
    masks = np.asarray(legal)
    if scores.shape != masks.shape or masks.dtype != np.bool_:
        raise V022CoalitionProbeError("score and native mask shapes differ")
    if not np.all(np.isfinite(scores)) or not np.all(np.any(masks, axis=1)):
        raise V022CoalitionProbeError("score surface is not finite and selectable")
    return np.argmax(np.where(masks, scores, -np.inf), axis=1).astype(np.int64)


def _physical_key(table: object, action: int) -> tuple[int, int]:
    return (
        int(np.asarray(getattr(table, "norad_ids"))[action]),
        int(np.asarray(getattr(table, "cell_ids"))[action]),
    )


def _topology_input_receipt(
    observation: object,
    *,
    reference_actions: np.ndarray,
    legal_mask: np.ndarray,
    opening_feasible: np.ndarray,
    base_surface: np.ndarray,
) -> dict[str, object]:
    """Persist every outcome-blind input needed to recompute topology choice."""

    tables = tuple(getattr(getattr(observation, "candidates"), "slot_tables"))
    users = len(tables)
    if (
        reference_actions.shape != (users,)
        or legal_mask.shape != (users, NUM_ACTIONS)
        or opening_feasible.shape != legal_mask.shape
        or base_surface.shape != legal_mask.shape
    ):
        raise V022CoalitionProbeError("topology receipt inputs disagree")
    candidate_keys = [
        [
            [int(getattr(table, "norad_ids")[action]), int(getattr(table, "cell_ids")[action])]
            for action in range(NUM_ACTIONS)
        ]
        for table in tables
    ]
    return {
        "reference_actions": [int(value) for value in reference_actions.tolist()],
        "legal_mask": legal_mask.tolist(),
        "opening_feasible": opening_feasible.tolist(),
        "base_surface": base_surface.tolist(),
        "candidate_physical_keys": candidate_keys,
        "base_surface_sha256": hashlib.sha256(
            np.ascontiguousarray(base_surface, dtype=np.float64).tobytes()
        ).hexdigest(),
    }


def _topology_proposal(
    observation: object,
    *,
    reference_actions: np.ndarray,
    legal_mask: np.ndarray,
    opening_feasible: np.ndarray,
    base_surface: np.ndarray,
) -> dict[str, object] | None:
    """Return the first Section-3 proposal without evaluating a candidate arm."""

    tables = tuple(getattr(getattr(observation, "candidates"), "slot_tables"))
    users = len(tables)
    if (
        reference_actions.shape != (users,)
        or legal_mask.shape != (users, NUM_ACTIONS)
        or opening_feasible.shape != legal_mask.shape
        or base_surface.shape != legal_mask.shape
    ):
        raise V022CoalitionProbeError("topology inputs disagree")

    reference_keys: list[tuple[int, int] | None] = [None] * users
    occupants: dict[tuple[int, int], list[int]] = {}
    for uid, raw_action in enumerate(reference_actions.tolist()):
        action = int(raw_action)
        if not bool(legal_mask[uid, action]):
            raise V022CoalitionProbeError("reference action is outside native mask")
        if not bool(opening_feasible[uid, action]):
            continue
        key = _physical_key(tables[uid], action)
        reference_keys[uid] = key
        occupants.setdefault(key, []).append(uid)

    for source in sorted(key for key, members in occupants.items() if len(members) == 2):
        members = tuple(sorted(int(uid) for uid in occupants[source]))
        outside_keys = {
            key
            for key, users_on_key in occupants.items()
            if key != source and any(int(uid) not in members for uid in users_on_key)
        }
        if not outside_keys:
            continue
        proposed_actions: list[int] = []
        proposed_keys: list[tuple[int, int]] = []
        complete = True
        for uid in members:
            choices: list[int] = []
            for raw_action in np.flatnonzero(
                legal_mask[uid] & opening_feasible[uid]
            ).tolist():
                action = int(raw_action)
                key = _physical_key(tables[uid], action)
                if key != source and key in outside_keys:
                    choices.append(action)
            if not choices:
                complete = False
                break
            best_value = max(float(base_surface[uid, action]) for action in choices)
            selected = min(
                action
                for action in choices
                if float(base_surface[uid, action]) == best_value
            )
            proposed_actions.append(selected)
            proposed_keys.append(_physical_key(tables[uid], selected))
        if complete:
            return {
                "source_key": [int(source[0]), int(source[1])],
                "coalition_user_ids": [int(value) for value in members],
                "proposed_actions": proposed_actions,
                "proposed_keys": [
                    [int(key[0]), int(key[1])] for key in proposed_keys
                ],
                "reference_occupancy": {
                    f"{key[0]}:{key[1]}": [int(uid) for uid in sorted(values)]
                    for key, values in sorted(occupants.items())
                },
            }
    return None


def _q12_anchor(
    *,
    v018: Any,
    q1: Any,
    q2: Any,
    step_env: Any,
    observation: Any,
) -> dict[str, object]:
    native = v018.encode_ee_axis_state(step_env, observation)
    native.verify()
    masks = np.asarray(native.action_masks, dtype=np.bool_)
    with torch.no_grad():
        q1_values = v018._q1_values(q1, native.state_matrix, masks)
        q1_reference = v018._V015.select_actions(
            q1_values,
            np.zeros_like(q1_values),
            np.zeros_like(q1_values),
            masks,
            include_c3=False,
        )
        anchor = v018.snapshot_ops3_anchor(step_env, observation)
        projection = v018.project_ops3_anchor(anchor)
        ops3 = v018.build_ops3_live_surfaces(anchor, projection, q1_reference)
        q2_state = v018._V015.encode_ee_axis_v014_q2_states(ops3)
        q2_state.verify()
        learned_q2 = v018._q2_values(
            q2, q2_state.state_matrix, q2_state.action_masks
        )
    if not np.array_equal(q2_state.action_masks, masks):
        raise V022CoalitionProbeError("Q2 carrier mask differs from native mask")
    base_surface = np.asarray(q1_values + learned_q2, dtype=np.float64)
    background = _masked_argmax(base_surface, masks)
    required_power, opening = v018._current_required_power_and_opening(
        current_gain_linear=anchor.current_gain_linear,
        segment_start_gain_linear=anchor.segment_start_gain_linear,
        action_masks=masks,
    )
    return {
        "native": native,
        "masks": masks,
        "q1": np.asarray(q1_values, dtype=np.float64),
        "q2": np.asarray(learned_q2, dtype=np.float64),
        "base": base_surface,
        "background": background,
        "required_power": np.asarray(required_power, dtype=np.float64),
        "opening": np.asarray(opening, dtype=np.bool_),
        "q2_state_sha256": q2_state.state_sha256,
    }


def _evaluation_record(
    evaluation: object,
    *,
    actions: np.ndarray,
    interval_s: float,
) -> dict[str, object]:
    rates = np.asarray(getattr(evaluation, "link_rate_bps"), dtype=np.float64)
    per_user_bits = interval_s * rates
    energy = interval_s * float(getattr(evaluation, "system_power_w"))
    served = np.asarray(getattr(getattr(evaluation, "resolution"), "served"), dtype=np.bool_)
    radiating = getattr(evaluation, "radiating")
    norads = np.asarray(getattr(radiating, "norad_ids"), dtype=np.int64)
    cells = np.asarray(getattr(radiating, "cell_ids"), dtype=np.int64)
    powers = np.asarray(getattr(radiating, "power_w"), dtype=np.float64)
    if (
        rates.ndim != 1
        or per_user_bits.shape != served.shape
        or not np.all(np.isfinite(per_user_bits))
        or np.any(per_user_bits < 0.0)
        or not math.isfinite(energy)
        or energy <= 0.0
        or norads.shape != cells.shape
        or powers.shape != norads.shape
    ):
        raise V022CoalitionProbeError("physical profile is malformed")
    beam_keys = [
        [int(norad), int(cell)]
        for norad, cell in zip(norads.tolist(), cells.tolist(), strict=True)
    ]
    total_bits = math.fsum(float(value) for value in per_user_bits.tolist())
    return {
        "actions": [int(value) for value in actions.tolist()],
        "per_user_bits": [float(value) for value in per_user_bits.tolist()],
        "total_bits": float(total_bits),
        "energy_j": float(energy),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / energy),
        "served": [bool(value) for value in served.tolist()],
        "served_users": int(np.count_nonzero(served)),
        "active_beam_keys": beam_keys,
        "active_satellites": sorted({int(value) for value in norads.tolist()}),
        "beam_power_w": [float(value) for value in powers.tolist()],
        "action_sha256": hashlib.sha256(
            np.ascontiguousarray(actions, dtype=np.int64).tobytes()
        ).hexdigest(),
    }


def _formula_record(result: object) -> dict[str, object]:
    fields = (
        "own_bits",
        "nonfocal_bits",
        "d_bits",
        "joint_delta_bits",
        "joint_delta_energy_j",
        "joint_surplus_bits",
        "interaction_bits",
        "interaction_energy_j",
        "interaction_surplus_bits",
        "equal_share_bits",
        "z3_bits",
        "combined_bits",
        "identity_residual_bits",
    )
    record: dict[str, object] = {"schema": str(getattr(result, "schema"))}
    for field in fields:
        value = getattr(result, field)
        record[field] = (
            [float(item) for item in np.asarray(value).tolist()]
            if isinstance(value, np.ndarray)
            else float(value)
        )
    record["q3_sha256"] = hashlib.sha256(
        np.ascontiguousarray(getattr(result, "q3_values"), dtype=np.float64).tobytes()
    ).hexdigest()
    return record


def _adoption(
    selected: np.ndarray,
    reference: np.ndarray,
    members: np.ndarray,
    proposed: np.ndarray,
) -> str:
    adopted = [
        int(selected[int(uid)]) == int(action)
        for uid, action in zip(members.tolist(), proposed.tolist(), strict=True)
    ]
    nonmembers = np.ones(reference.size, dtype=np.bool_)
    nonmembers[members] = False
    if not np.array_equal(selected[nonmembers], reference[nonmembers]):
        return "OTHER_PROFILE"
    if adopted == [True, True]:
        return "11"
    if adopted == [True, False]:
        return "10"
    if adopted == [False, True]:
        return "01"
    if np.array_equal(selected, reference):
        return "00"
    return "OTHER_PROFILE"


def _rng_digest(state: object) -> str:
    """Hash the opaque NumPy RNG state without serializing it into JSON."""

    return hashlib.sha256(repr(state).encode("utf-8")).hexdigest()


def _validate_inherited_sources(v018: Any) -> dict[str, object]:
    """Execute the frozen validators used by the inherited V0.20 stack."""

    try:
        v018.validate_v018_contract()
        v018._V015.validate_v015_contract()
        v014_receipt = v018._V015.validate_v014_gate_receipts(
            v018.V014_GATE_ROOT
        )
        v018._V015._V013.assert_contract_frozen(
            v018._V015._V013.CONTRACT_PATH
        )
    except Exception as error:
        raise V022CoalitionProbeError(
            f"inherited source validator failed: {error}"
        ) from error
    if not isinstance(v014_receipt, Mapping):
        raise V022CoalitionProbeError("V0.14 validator returned no receipt")
    return {
        "v018_contract_sha256": v018.V018_CONTRACT_SHA256,
        "v018_contract_validator": "PASS",
        "v015_contract_sha256": v018._V015.V015_CONTRACT_SHA256,
        "v015_contract_validator": "PASS",
        "v014_gate_receipt": dict(v014_receipt),
        "v014_gate_validator": "PASS",
        "v013_contract_sha256": v018._V015._V013.file_sha256(
            v018._V015._V013.CONTRACT_PATH
        ),
        "v013_contract_validator": "PASS",
    }


def _assert_complete_no_case_scan(scan: list[dict[str, object]]) -> None:
    """Fail closed unless every declared world has all ten anchor receipts."""

    expected = len(WORLDS) * STEPS_PER_EPISODE
    if len(scan) != expected:
        raise V022CoalitionProbeError(
            f"NO_QUALIFIED_PAIR_CASE requires {expected} anchors, got {len(scan)}"
        )
    by_world: dict[int, list[int]] = {int(world): [] for world in WORLDS}
    for row in scan:
        if not isinstance(row, Mapping):
            raise V022CoalitionProbeError("scan receipt row is malformed")
        world = int(row.get("world", -1))
        step = int(row.get("step", -1))
        if world not in by_world:
            raise V022CoalitionProbeError("scan receipt contains an undeclared world")
        by_world[world].append(step)
    for world, steps in by_world.items():
        if sorted(steps) != list(range(STEPS_PER_EPISODE)):
            raise V022CoalitionProbeError(
                f"scan for world {world} is not the complete 0..{STEPS_PER_EPISODE - 1} panel"
            )


def run(
    *,
    output: Path,
    tle_root: Path,
    prereg: Path,
    manifest: Path = PREFLIGHT_MANIFEST,
    manifest_digest: Path = PREFLIGHT_MANIFEST_DIGEST,
) -> dict[str, object]:
    if output.exists() or output.is_symlink():
        raise V022CoalitionProbeError(f"refusing to overwrite {output}")
    preflight_receipt = _validate_external_preflight(
        manifest=Path(manifest),
        manifest_digest=Path(manifest_digest),
        prereg=Path(prereg),
    )
    if _sha256(CONTRACT) != CONTRACT_SHA256:
        raise V022CoalitionProbeError("mechanics contract bytes changed")
    if _sha256(FORMULA) != FORMULA_SHA256:
        raise V022CoalitionProbeError("coalition formula bytes changed")
    if _sha256(prereg) != PREREG_SHA256:
        raise V022CoalitionProbeError("preregistration bytes changed")

    v020 = _load_module("mcrl_v020_for_v022_coalition", V020_PATH)
    v020_receipt = v020._validate_global_inputs()
    v018 = v020._load_module("mcrl_v018_for_v022_coalition", v020.V018_PATH)
    inherited_receipt = _validate_inherited_sources(v018)
    if (
        int(v018.STEPS_PER_EPISODE) != STEPS_PER_EPISODE
        or int(v018.USERS) != 100
        or int(v018._V015.STEPS_PER_EPISODE) != STEPS_PER_EPISODE
        or int(v018._V015.USERS) != 100
        or int(v018._V015._V013.STEPS_PER_EPISODE) != STEPS_PER_EPISODE
        or int(v018._V015._V013.USERS) != 100
    ):
        raise V022CoalitionProbeError("inherited episode or user configuration drifted")
    q1, q1_receipt, q2, q2_receipt = v020.load_repriced_heads(LINEAGE)
    record = v018._V015._V013.read_prereg(prereg)
    q1_before = v018._V015._q_parameter_sha256(q1)
    q2_before = v018._V015._q_parameter_sha256(q2)
    started = time.perf_counter()
    scan: list[dict[str, object]] = []
    world_receipts: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="mcrl-v022-coalition-tle-") as temporary:
        archive = v018._V015._V013.screen._frozen_archive(
            record, tle_root, Path(temporary) / "frozen-tle"
        )
        ephemeris_validation = v018._V015._V013.screen.assert_ephemeris_matches_record(
            record, archive=archive
        )
        if not isinstance(ephemeris_validation, Mapping):
            raise V022CoalitionProbeError("TLE validator returned no receipt")
        ephemeris_receipt = {
            "status": "PASS",
            "file_set_sha256": str(ephemeris_validation["file_set_sha256"]),
            "archive": dict(ephemeris_validation["archive"]),
            "split": dict(ephemeris_validation["split"]),
            "sampling": dict(ephemeris_validation["sampling"]),
            "receipt_sha256": _canonical_sha256(dict(ephemeris_validation)),
        }
        for world in WORLDS:
            environment = v018._V015._V013.screen._make_environment(
                archive, users=v018.USERS
            )
            field = KeyedFadingField.from_components(FIELD_COMPONENT, world)
            environment.environment._fading_field = field
            env_rng, mobility_rng, _action_rng, _control_rng = (
                v018._V015._V013.screen._evaluation_rngs(world)
            )
            _states, _masks, observation = environment.reset(env_rng, mobility_rng)
            step_env = environment.environment
            interval_s = float(step_env.driver.config.ephemeris.time_step_s)
            world_live_before = v018._live_digest(environment, env_rng)
            world_rng_before = copy.deepcopy(env_rng.bit_generator.state)

            for step_index in range(STEPS_PER_EPISODE):
                if int(observation.step_index) != step_index:
                    raise V022CoalitionProbeError("anchor step index drifted")
                anchor_data = _q12_anchor(
                    v018=v018,
                    q1=q1,
                    q2=q2,
                    step_env=step_env,
                    observation=observation,
                )
                proposal = None
                if step_index > 0:
                    proposal = _topology_proposal(
                        observation,
                        reference_actions=anchor_data["background"],
                        legal_mask=anchor_data["masks"],
                        opening_feasible=anchor_data["opening"],
                        base_surface=anchor_data["base"],
                    )
                topology_inputs = _topology_input_receipt(
                    observation,
                    reference_actions=np.asarray(anchor_data["background"], dtype=np.int64),
                    legal_mask=np.asarray(anchor_data["masks"], dtype=np.bool_),
                    opening_feasible=np.asarray(anchor_data["opening"], dtype=np.bool_),
                    base_surface=np.asarray(anchor_data["base"], dtype=np.float64),
                )
                scan_row = {
                    "world": int(world),
                    "step": int(step_index),
                    "qualified": proposal is not None,
                    "reference_sha256": hashlib.sha256(
                        np.ascontiguousarray(
                            anchor_data["background"], dtype=np.int64
                        ).tobytes()
                    ).hexdigest(),
                    "topology_inputs": topology_inputs,
                    "proposal": dict(proposal) if proposal is not None else None,
                }
                scan.append(scan_row)
                if proposal is not None:
                    payload = _evaluate_selected_anchor(
                        v018=v018,
                        environment=environment,
                        env_rng=env_rng,
                        observation=observation,
                        world=world,
                        step_index=step_index,
                        interval_s=interval_s,
                        anchor_data=anchor_data,
                        proposal=proposal,
                        scan=scan,
                        q1=q1,
                        q2=q2,
                        q1_before=q1_before,
                        q2_before=q2_before,
                        q1_receipt=q1_receipt,
                        q2_receipt=q2_receipt,
                        field=field,
                        started=started,
                        v020_receipt=v020_receipt,
                        preflight_receipt=preflight_receipt,
                        inherited_receipt=inherited_receipt,
                        ephemeris_receipt=ephemeris_receipt,
                        topology_inputs=topology_inputs,
                    )
                    output.mkdir(parents=True, exist_ok=False)
                    (output / "result.json").write_bytes(_canonical_bytes(payload))
                    return payload

                outcome = environment.step(anchor_data["background"], env_rng)
                if outcome.done and step_index != STEPS_PER_EPISODE - 1:
                    raise V022CoalitionProbeError(
                        "episode terminated before the complete ten-anchor scan"
                    )
                if not outcome.done and step_index == STEPS_PER_EPISODE - 1:
                    raise V022CoalitionProbeError(
                        "episode did not terminate at the declared ten-anchor boundary"
                    )
                observation = environment.last_outcome.observation
            world_live_after = v018._live_digest(environment, env_rng)
            world_rng_after = copy.deepcopy(env_rng.bit_generator.state)
            world_receipts.append(
                {
                    "world": int(world),
                    "field_root_digest": field.root_digest,
                    "anchors_scanned": STEPS_PER_EPISODE,
                    "counterfactual_evaluations": 0,
                    "counterfactual_state_rng_nonmutation": "NOT_APPLICABLE_NO_QUALIFIED_PAIR",
                    "live_digest_before": world_live_before,
                    "live_digest_after": world_live_after,
                    "rng_digest_before": _rng_digest(world_rng_before),
                    "rng_digest_after": _rng_digest(world_rng_after),
                    "declared_rollout_state_transition_observed": bool(
                        world_live_before != world_live_after
                    ),
                    "counterfactual_nonmutation_receipt": {
                        "evaluated": False,
                        "passed": True,
                        "reason": "NO_QUALIFIED_PAIR",
                    },
                    "q1_parameter_sha256": q1_before,
                    "q2_parameter_sha256": q2_before,
                }
            )

    _assert_complete_no_case_scan(scan)
    q1_after = v018._V015._q_parameter_sha256(q1)
    q2_after = v018._V015._q_parameter_sha256(q2)
    networks_unchanged = bool(q1_after == q1_before and q2_after == q2_before)
    payload = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "formula_sha256": FORMULA_SHA256,
        "runner_sha256": _sha256(Path(__file__)),
        "preflight": preflight_receipt,
        "inherited_validators": inherited_receipt,
        "ephemeris_validation": ephemeris_receipt,
        "split": "TRAIN_DEVELOPMENT",
        "worlds": list(WORLDS),
        "lineage": LINEAGE,
        "v020_validation_status": str(v020_receipt.get("status")),
        "scan": scan,
        "world_receipts": world_receipts,
        "nonmutation_receipt": {
            "scope": "NO_QUALIFIED_PAIR_CASE_SCAN_ONLY",
            "counterfactual_evaluations": 0,
            "q1_parameter_sha256_before": q1_before,
            "q1_parameter_sha256_after": q1_after,
            "q2_parameter_sha256_before": q2_before,
            "q2_parameter_sha256_after": q2_after,
            "q1_q2_unchanged": networks_unchanged,
        },
        "decision": "NO_QUALIFIED_PAIR_CASE",
        "elapsed_s": time.perf_counter() - started,
        "test_split_opened": False,
        "learner_update": False,
        "episode_training": False,
    }
    if not networks_unchanged:
        raise V022CoalitionProbeError("Q1/Q2 parameters changed during no-case scan")
    payload["result_sha256"] = _canonical_sha256(payload)
    output.mkdir(parents=True, exist_ok=False)
    (output / "result.json").write_bytes(_canonical_bytes(payload))
    return payload


def _evaluate_selected_anchor(
    *,
    v018: Any,
    environment: Any,
    env_rng: np.random.Generator,
    observation: Any,
    world: int,
    step_index: int,
    interval_s: float,
    anchor_data: Mapping[str, object],
    proposal: Mapping[str, object],
    scan: list[dict[str, object]],
    q1: Any,
    q2: Any,
    q1_before: str,
    q2_before: str,
    q1_receipt: Mapping[str, object],
    q2_receipt: Mapping[str, object],
    field: KeyedFadingField,
    started: float,
    v020_receipt: Mapping[str, object],
    preflight_receipt: Mapping[str, object],
    inherited_receipt: Mapping[str, object],
    ephemeris_receipt: Mapping[str, object],
    topology_inputs: Mapping[str, object],
) -> dict[str, object]:
    step_env = environment.environment
    reference = np.asarray(anchor_data["background"], dtype=np.int64)
    masks = np.asarray(anchor_data["masks"], dtype=np.bool_)
    base_surface = np.asarray(anchor_data["base"], dtype=np.float64)
    members = np.asarray(proposal["coalition_user_ids"], dtype=np.int64)
    proposed = np.asarray(proposal["proposed_actions"], dtype=np.int64)
    if members.shape != (2,) or proposed.shape != (2,):
        raise V022CoalitionProbeError("the frozen probe requires exactly two members")

    profiles: dict[str, np.ndarray] = {"00": np.array(reference, copy=True)}
    profiles["10"] = np.array(reference, copy=True)
    profiles["10"][members[0]] = proposed[0]
    profiles["01"] = np.array(reference, copy=True)
    profiles["01"][members[1]] = proposed[1]
    profiles["11"] = np.array(reference, copy=True)
    profiles["11"][members] = proposed

    expected_proposal = _topology_proposal(
        observation,
        reference_actions=reference,
        legal_mask=masks,
        opening_feasible=np.asarray(anchor_data["opening"], dtype=np.bool_),
        base_surface=base_surface,
    )
    topology_recomputed = bool(expected_proposal == dict(proposal))
    topology_receipt = {
        "selected_preoutcome": topology_recomputed,
        "proposal_sha256": _canonical_sha256(dict(proposal)),
        "recomputed_proposal_sha256": (
            _canonical_sha256(expected_proposal) if expected_proposal is not None else None
        ),
        "inputs_sha256": _canonical_sha256(dict(topology_inputs)),
        "outcome_fields_read": False,
    }
    live_before = v018._live_digest(environment, env_rng)
    rng_before = copy.deepcopy(env_rng.bit_generator.state)
    evaluations = {
        code: step_env.evaluate_actions(actions, env_rng)
        for code, actions in profiles.items()
    }
    live_after_profiles = v018._live_digest(environment, env_rng)
    rng_after_profiles = copy.deepcopy(env_rng.bit_generator.state)
    records = {
        code: _evaluation_record(
            evaluations[code], actions=profiles[code], interval_s=interval_s
        )
        for code in ("00", "10", "01", "11")
    }

    formula = build_coalition_residual_surface(
        B0_v=np.asarray(records["00"]["per_user_bits"], dtype=np.float64),
        E0=float(records["00"]["energy_j"]),
        Bu=np.stack(
            [
                np.asarray(records["10"]["per_user_bits"], dtype=np.float64),
                np.asarray(records["01"]["per_user_bits"], dtype=np.float64),
            ]
        ),
        Eu=np.asarray(
            [records["10"]["energy_j"], records["01"]["energy_j"]],
            dtype=np.float64,
        ),
        BC=np.asarray(records["11"]["per_user_bits"], dtype=np.float64),
        EC=float(records["11"]["energy_j"]),
        coalition_user_ids=members,
        proposed_actions=proposed,
        lambda_bits_per_j=LAMBDA_BITS_PER_J,
        kappa_bits=KAPPA_BITS,
        reference_actions=reference,
        legal_mask=masks,
        action_count=NUM_ACTIONS,
    )
    if formula.schema != COALITION_RESIDUAL_C3_SCHEMA:
        raise V022CoalitionProbeError("coalition formula schema drifted")
    formula_residual = float(formula.verify())
    formula_scale = max(
        1.0,
        abs(float(formula.joint_surplus_bits)),
        abs(float(np.sum(formula.combined_bits))),
    )
    formula_tolerance = max(1.0e-12, 1024.0 * np.finfo(np.float64).eps * formula_scale)
    formula_identity_verified = bool(
        math.isfinite(formula_residual) and abs(formula_residual) <= formula_tolerance
    )

    composed = _masked_argmax(base_surface + formula.q3_values, masks)
    composed_evaluation = step_env.evaluate_actions(composed, env_rng)
    composed_record = _evaluation_record(
        composed_evaluation, actions=composed, interval_s=interval_s
    )
    live_after = v018._live_digest(environment, env_rng)
    rng_after = copy.deepcopy(env_rng.bit_generator.state)

    source = tuple(int(value) for value in proposal["source_key"])
    beam_sets = {
        code: {tuple(int(value) for value in key) for key in row["active_beam_keys"]}
        for code, row in records.items()
    }
    source_public_good = bool(
        source in beam_sets["00"]
        and source in beam_sets["10"]
        and source in beam_sets["01"]
        and source not in beam_sets["11"]
    )
    no_new_beam = not bool(beam_sets["11"] - beam_sets["00"])
    exactly_one_beam_removed = bool(
        beam_sets["00"] - beam_sets["11"] == {source}
        and len(beam_sets["11"]) == len(beam_sets["00"]) - 1
    )
    pair_served_all = all(
        all(bool(records[code]["served"][int(uid)]) for uid in members.tolist())
        for code in ("00", "10", "01", "11")
    )
    service_guard = int(records["11"]["served_users"]) >= int(
        records["00"]["served_users"]
    )
    joint_ee_positive = float(records["11"]["ratio_of_sums_ee_bits_per_j"]) > float(
        records["00"]["ratio_of_sums_ee_bits_per_j"]
    )
    ratio_identity_value = (
        float(records["11"]["total_bits"])
        - float(records["00"]["total_bits"])
        - float(records["00"]["ratio_of_sums_ee_bits_per_j"])
        * (float(records["11"]["energy_j"]) - float(records["00"]["energy_j"]))
    )
    ratio_sign_agrees = bool((ratio_identity_value > 0.0) == joint_ee_positive)
    support = np.zeros_like(formula.q3_values, dtype=np.bool_)
    support[members, proposed] = True
    expected_support_values = np.zeros_like(formula.q3_values, dtype=np.float64)
    expected_support_values[members, proposed] = (
        np.asarray(formula.z3_bits, dtype=np.float64) / KAPPA_BITS
    )
    sparse_zero = bool(
        np.array_equal(
            np.asarray(formula.q3_values, dtype=np.float64)[~support],
            expected_support_values[~support],
        )
        and np.array_equal(
            np.asarray(formula.q3_values, dtype=np.float64)[support],
            expected_support_values[support],
        )
        and np.all(formula.q3_values[~masks] == 0.0)
        and np.all(formula.q3_values[np.arange(reference.size), reference] == 0.0)
    )
    state_rng_unchanged = bool(
        live_before == live_after_profiles == live_after
        and rng_before == rng_after_profiles == rng_after
    )
    q1_after = v018._V015._q_parameter_sha256(q1)
    q2_after = v018._V015._q_parameter_sha256(q2)
    networks_unchanged = bool(q1_after == q1_before and q2_after == q2_before)
    nonmutation_receipt = {
        "live_digest_before": live_before,
        "live_digest_after_profiles": live_after_profiles,
        "live_digest_after_composed": live_after,
        "rng_digest_before": _rng_digest(rng_before),
        "rng_digest_after_profiles": _rng_digest(rng_after_profiles),
        "rng_digest_after_composed": _rng_digest(rng_after),
        "q1_parameter_sha256_before": q1_before,
        "q1_parameter_sha256_after": q1_after,
        "q2_parameter_sha256_before": q2_before,
        "q2_parameter_sha256_after": q2_after,
        "live_state_unchanged": live_before == live_after_profiles == live_after,
        "rng_unchanged": rng_before == rng_after_profiles == rng_after,
        "q1_q2_unchanged": networks_unchanged,
    }
    def manifest_binding_matches(role: str, path: Path, digest: str) -> bool:
        return bool(
            any(
                entry.get("role") == role
                and entry.get("path") == str(path.relative_to(REPO))
                and entry.get("sha256") == digest
                for entry in preflight_receipt.get("bindings", [])
                if isinstance(entry, Mapping)
            )
        )

    contract_authenticated = bool(
        preflight_receipt.get("status") == "PASS"
        and bool(preflight_receipt.get("manifest_file_sha256"))
        and str(preflight_receipt["configuration"].get("lineage")) == str(LINEAGE)
        and manifest_binding_matches("contract", CONTRACT, CONTRACT_SHA256)
    )
    formula_authenticated = manifest_binding_matches(
        "formula", FORMULA, FORMULA_SHA256
    )
    prereg_authenticated = manifest_binding_matches(
        "preregistration", REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json", PREREG_SHA256
    )
    checkpoint_authenticated = manifest_binding_matches(
        "selected_q1_q2_checkpoint", Path(q1_receipt["checkpoint_path"]), str(q1_receipt["checkpoint_sha256"])
    )
    tle_authenticated = bool(
        ephemeris_receipt.get("status") == "PASS"
        and ephemeris_receipt.get("file_set_sha256")
        == preflight_receipt["configuration"].get("tle_file_set_sha256")
    )
    mechanics = {
        "contract_authenticated": contract_authenticated,
        "formula_authenticated": formula_authenticated,
        "prereg_authenticated": prereg_authenticated,
        "checkpoint_authenticated": checkpoint_authenticated,
        "tle_runtime_validated": tle_authenticated,
        "inherited_validators_passed": all(
            value == "PASS"
            for key, value in inherited_receipt.items()
            if key.endswith("_validator")
        ),
        "topology_selected_preoutcome": topology_recomputed,
        "source_beam_public_good_signature": source_public_good,
        "joint_opens_no_new_beam": no_new_beam,
        "joint_removes_exactly_source_beam": exactly_one_beam_removed,
        "pair_served_all_profiles": pair_served_all,
        "joint_service_noninferior": service_guard,
        "formula_identity_verified": formula_identity_verified,
        "ratio_sign_identity_agrees": ratio_sign_agrees,
        "live_state_and_rng_unchanged": state_rng_unchanged,
        "q1_q2_unchanged": networks_unchanged,
        "sparse_q3_exact_zero_fill": sparse_zero,
    }
    mechanics["passed"] = bool(all(mechanics.values()))
    adoption = _adoption(composed, reference, members, proposed)

    if mechanics["passed"] and joint_ee_positive and adoption == "11":
        decision = "GO_LC_SRS_OBSERVABILITY_GATE"
    elif mechanics["passed"] and joint_ee_positive:
        decision = "REDESIGN_COALITION_INTERFACE"
    else:
        decision = "STOP_THIS_COALITION_PROPOSAL"

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "formula_sha256": FORMULA_SHA256,
        "runner_sha256": _sha256(Path(__file__)),
        "preflight": dict(preflight_receipt),
        "inherited_validators": dict(inherited_receipt),
        "ephemeris_validation": dict(ephemeris_receipt),
        "prereg_sha256": PREREG_SHA256,
        "split": "TRAIN_DEVELOPMENT",
        "worlds": list(WORLDS),
        "selected_world": int(world),
        "selected_step": int(step_index),
        "lineage": LINEAGE,
        "field_root_digest": field.root_digest,
        "lambda_bits_per_j": LAMBDA_BITS_PER_J,
        "lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
        "kappa_bits": KAPPA_BITS,
        "kappa_bits_hex": KAPPA_BITS.hex(),
        "q1_receipt": dict(q1_receipt),
        "q2_receipt": dict(q2_receipt),
        "q2_state_sha256": str(anchor_data["q2_state_sha256"]),
        "v020_validation_status": str(v020_receipt.get("status")),
        "scan": scan,
        "proposal": dict(proposal),
        "topology_inputs": dict(topology_inputs),
        "topology_receipt": topology_receipt,
        "profiles": records,
        "formula": _formula_record(formula),
        "composition": {
            "adoption_profile": adoption,
            "selected_actions": [int(value) for value in composed.tolist()],
            "record": composed_record,
        },
        "mechanics": mechanics,
        "formula_verification": {
            "residual_bits": formula_residual,
            "tolerance_bits": formula_tolerance,
            "passed": formula_identity_verified,
        },
        "nonmutation_receipt": nonmutation_receipt,
        "joint_ee_positive": joint_ee_positive,
        "ratio_reference_identity_bits": float(ratio_identity_value),
        "decision": decision,
        "elapsed_s": time.perf_counter() - started,
        "test_split_opened": False,
        "learner_update": False,
        "episode_training": False,
    }
    payload["result_sha256"] = _canonical_sha256(payload)
    print(
        f"{decision}: world={world} step={step_index} adoption={adoption} "
        f"EE00={float(records['00']['ratio_of_sums_ee_bits_per_j']):.9g} "
        f"EE11={float(records['11']['ratio_of_sums_ee_bits_per_j']):.9g}",
        flush=True,
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=PREFLIGHT_MANIFEST)
    parser.add_argument(
        "--manifest-digest", type=Path, default=PREFLIGHT_MANIFEST_DIGEST
    )
    args = parser.parse_args()
    run(
        output=args.output,
        tle_root=args.tle_root,
        prereg=args.prereg,
        manifest=args.manifest,
        manifest_digest=args.manifest_digest,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
