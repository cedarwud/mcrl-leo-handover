#!/usr/bin/env python3
"""V0.9 integrated exact-OPS3/PNFE oracle gate.

This runner is the executable boundary for the single ``REDESIGN_C3_FIRST``
gate.  It uses one frozen Q1 action-value surface, the exact OPS-3 v1.1 live
projection, and the PNFE live C3 surface.  The four policies are deliberately
small and explicit::

    FULL    = Q1 + O2_EXACT + O3_PNFE
    DROP_C2 = Q1 + O3_PNFE
    DROP_C3 = Q1 + O2_EXACT
    DROP_C1 = O2_EXACT + O3_PNFE

Every decision uses one native Boolean mask, one left-to-right unweighted
sum, one masked argmax, and one executed action.  The script has no learner or
TEST path.  ``plan`` is read-only; ``run`` is the only command that opens the
declared TRAIN world and it is intentionally explicit because it is a heavy
no-training oracle rollout.

The centering action is obtained from the frozen Q1 greedy surface.  This is an
action-only gauge: subtracting one fixed action row from every legal row does
not change an argmax.  Keeping the gauge provider inside this runner avoids
loading or querying any legacy multi-head policy while the V0.9 gate is limited
to the Q1 frozen head.  The receipt records this convention explicitly.

The two mandatory diagnostics are fail-closed.  The h=0 diagnostic compares
the PNFE opening shadow with an independent current-slot ``evaluate_actions``
counterfactual while non-focal actions stay fixed.  The simultaneous diagnostic
measures the cross-term for two users that prefer the same physical beam.  A
missing diagnostic cannot produce ``PASS_ORACLE_GATE``.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
import copy
import datetime as dt
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np
import torch


REPO = Path(__file__).resolve().parents[2]
SCRATCH = REPO / ".scratch" / "c3-v04"
for _path in (SCRATCH, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v04_c3_500_update_screen as screen  # noqa: E402
import run_v04_c3_learnability_gate as gate  # noqa: E402
from mcrl.algorithms.ee_axis_v04_hybrid import (  # noqa: E402
    extract_frozen_meanmax_head,
)
from mcrl.env.action_contract import NO_OP_ACTION, NUM_ACTIONS  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_pnfe_live import (  # noqa: E402
    build_pnfe_live_surfaces,
    snapshot_pnfe_anchor,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402


HERE = Path(__file__).resolve().parent

RESULT_SCHEMA = "multi-catfish-mcrl-v09-integrated-oracle-result-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v09-integrated-oracle-episode-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v09-integrated-oracle-shard-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v09-integrated-oracle-contract-v1"

WORLD_SEED = 2026104501
LINEAGES = (2026092101, 2026092102, 2026092103)
USERS = 100
STEPS_PER_EPISODE = 10
EPISODES_PER_ARM = len(LINEAGES)
EVALUATION_SPLIT = "TRAIN"
TEST_SPLIT_OPENED = False
EPISODE_TRAINING = False

ARMS = ("FULL", "DROP_C2", "DROP_C3", "DROP_C1")
ARM_HEADS: dict[str, tuple[str, ...]] = {
    "FULL": ("Q1", "O2_EXACT", "O3_PNFE"),
    "DROP_C2": ("Q1", "O3_PNFE"),
    "DROP_C3": ("Q1", "O2_EXACT"),
    "DROP_C1": ("O2_EXACT", "O3_PNFE"),
}
FIELD_COMPONENT = "MCRL_V09_INTEGRATED_ORACLE_V1"
FIELD_EXCLUDED_COMPONENTS = ("initialization_seed", "arm", "policy_label")
REFERENCE_CONVENTION = "Q1_FROZEN_GREEDY_ACTION_ONLY_GAUGE"
DIAGNOSTIC_STEPS = (1, 4, 7)
# A single local reversal is a diagnostic observation, not a gate failure.  A
# strict majority of evaluable, predeclared same-beam samples is the frozen
# systematic-reversal hard stop.
CROSS_REVERSAL_BLOCK_FRACTION = 0.5

# This is the exact source/runner contract.  It is recorded, never inferred
# from an observed result, and no CLI option can replace these values.
CONTRACT_PATH = REPO / "docs" / "MULTI-CATFISH-MCRL-V09-INTEGRATED-ORACLE-PREREG-2026-09-02.md"
RUNTIME_PATHS = (
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3_live.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_pnfe.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_pnfe_live.py",
)


class RunnerContractError(RuntimeError):
    """A V0.9 formula, receipt, world, or gate condition failed closed."""


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
        raise RunnerContractError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise RunnerContractError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(*values: object) -> str:
    digest = hashlib.sha256()
    for value in values:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def field_for_world(world_seed: int = WORLD_SEED) -> KeyedFadingField:
    if int(world_seed) != WORLD_SEED:
        raise RunnerContractError(
            f"V0.9 is frozen to world seed {WORLD_SEED}, got {world_seed}"
        )
    # Arm and lineage are deliberately absent.  The same root is used by all
    # four fresh environments and all three frozen lineages.
    return KeyedFadingField.from_components(FIELD_COMPONENT, WORLD_SEED)


def common_field_receipt(world_seed: int = WORLD_SEED) -> dict[str, Any]:
    field = field_for_world(world_seed)
    return {
        "components": [FIELD_COMPONENT, WORLD_SEED],
        "excluded_components": list(FIELD_EXCLUDED_COMPONENTS),
        "receipt": field.receipt(),
        "root_digest": field.root_digest,
    }


def contract_receipt() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "world_seed": WORLD_SEED,
        "lineages": list(LINEAGES),
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes_per_arm": EPISODES_PER_ARM,
        "arms": list(ARMS),
        "arm_heads": {arm: list(heads) for arm, heads in ARM_HEADS.items()},
        "summation": "left_to_right_unweighted",
        "mask": "one_common_boolean_native_mask",
        "selection": "one_masked_argmax_one_executed_action",
        "evaluation_split": EVALUATION_SPLIT,
        "test_split_opened": TEST_SPLIT_OPENED,
        "episode_training": EPISODE_TRAINING,
        "reference_convention": REFERENCE_CONVENTION,
        "field_component": FIELD_COMPONENT,
        "field_excluded_components": list(FIELD_EXCLUDED_COMPONENTS),
        "diagnostics": [
            "h0_true_matched_nonfocal_ordering",
            "simultaneous_cross_term",
        ],
        "diagnostic_steps": list(DIAGNOSTIC_STEPS),
        "h0_diagnostic_sampling": {
            "users": "first_up_to_four_user_ids_with_at_least_four_legal_actions",
            "actions": "selected_arm_action_plus_three_smallest_other_legal_actions",
            "minimum_merged_exposure": "one_comparable_sample",
            "role": "mandatory_to_record_nonbinding",
        },
        "cross_term_background_actions": "SELECTED_ARM_ACTIONS",
        "cross_term_sampling": {
            "candidate_action": "highest_O3_PNFE_other_than_selected__smallest_native_index_tie",
            "group": "lexicographically_first_physical_beam_with_exactly_two_or_three_users",
            "minimum_merged_exposure": "one_evaluable_sample",
        },
        "cross_term_systematic_reversal": {
            "rule": "strict_majority_of_evaluable_scheduled_samples",
            "block_fraction": CROSS_REVERSAL_BLOCK_FRACTION,
        },
        "gate": {
            "pooled_full_strictly_exceeds_each_drop": True,
            "positive_lineage_contrasts_minimum": 2,
            "pooled_service_full_not_lower": True,
            "service_noninferior_lineages_minimum": 2,
            "one_user_step_shortfall_fails": True,
        },
    }


def select_actions(
    surfaces: Mapping[str, np.ndarray],
    legal_mask: np.ndarray,
    arm: str,
) -> np.ndarray:
    """Apply one common mask and one left-to-right unweighted argmax."""

    if arm not in ARM_HEADS:
        raise RunnerContractError(f"unknown arm {arm!r}")
    legal = np.asarray(legal_mask)
    if legal.dtype != np.bool_ or legal.ndim != 2:
        raise RunnerContractError("common legal mask must be Boolean and two-dimensional")
    expected = ARM_HEADS[arm]
    if set(surfaces) != {"Q1", "O2_EXACT", "O3_PNFE"}:
        raise RunnerContractError("surface map must contain exactly Q1, O2_EXACT, O3_PNFE")
    arrays = {
        name: np.asarray(surfaces[name], dtype=np.float64) for name in surfaces
    }
    shape = arrays["Q1"].shape
    if len(shape) != 2 or shape[1] != NUM_ACTIONS:
        raise RunnerContractError("surfaces must have shape (users, native actions)")
    if legal.shape != shape:
        raise RunnerContractError("common legal mask does not match surfaces")
    if any(value.shape != shape or not np.all(np.isfinite(value)) for value in arrays.values()):
        raise RunnerContractError("surface arrays are nonfinite or misaligned")
    if not np.all(np.any(legal, axis=1)):
        raise RunnerContractError("every user must have one legal native action")

    # Keeping this loop explicit makes the declared route ordering auditable.
    scores = np.array(arrays[expected[0]], dtype=np.float64, copy=True)
    for head in expected[1:]:
        scores = scores + arrays[head]
    if not np.all(np.isfinite(scores)):
        raise RunnerContractError("summed surface is nonfinite")
    return np.argmax(np.where(legal, scores, -np.inf), axis=1).astype(
        np.int64, copy=False
    )


def _score_surface(
    surfaces: Mapping[str, np.ndarray], legal_mask: np.ndarray, arm: str
) -> np.ndarray:
    expected = ARM_HEADS[arm]
    scores = np.array(surfaces[expected[0]], dtype=np.float64, copy=True)
    for head in expected[1:]:
        scores = scores + np.asarray(surfaces[head], dtype=np.float64)
    return np.where(np.asarray(legal_mask, dtype=np.bool_), scores, -np.inf)


def _action_margins(
    scores: np.ndarray, legal_mask: np.ndarray, actions: np.ndarray
) -> list[float | None]:
    result: list[float | None] = []
    for uid, row in enumerate(np.asarray(scores, dtype=np.float64)):
        legal = np.flatnonzero(np.asarray(legal_mask[uid], dtype=np.bool_))
        if legal.size < 2:
            result.append(None)
            continue
        chosen = int(actions[uid])
        values = np.sort(row[legal])[::-1]
        if chosen < 0 or not np.isfinite(row[chosen]):
            result.append(None)
            continue
        result.append(float(row[chosen] - values[1]))
    return result


def _q1_values(network: Any, state_matrix: np.ndarray, legal_mask: np.ndarray) -> np.ndarray:
    states = np.asarray(state_matrix, dtype=np.float32)
    masks = np.asarray(legal_mask)
    if states.ndim != 2 or states.shape[1] != 228:
        raise RunnerContractError("frozen Q1 state width must be 228")
    if masks.dtype != np.bool_ or masks.shape != (states.shape[0], NUM_ACTIONS):
        raise RunnerContractError("frozen Q1 mask shape is not native")
    if not np.all(np.any(masks, axis=1)):
        raise RunnerContractError("frozen Q1 requires one legal action per user")
    with torch.no_grad():
        values = network(
            torch.tensor(states, dtype=torch.float32),
            torch.tensor(masks, dtype=torch.bool),
        ).detach().cpu().numpy()
    result = np.asarray(values, dtype=np.float64)
    if result.shape != masks.shape or not np.all(np.isfinite(result)):
        raise RunnerContractError("frozen Q1 surface is malformed")
    return result


def _q1_parameter_sha256(network: Any) -> str:
    digest = hashlib.sha256()
    for name, value in network.state_dict().items():
        tensor = value.detach().cpu()
        digest.update(str(name).encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def load_frozen_q1(v03_root: Path, lineage: int) -> tuple[Any, dict[str, Any]]:
    """Load exactly head 0 without constructing or querying another head."""

    seed = int(lineage)
    if seed not in LINEAGES:
        raise RunnerContractError(f"lineage {seed} is outside the frozen V0.9 set")
    v03_config, _ = gate._config_pair()
    spec = gate._spec_for_seed(Path(v03_root), seed)
    network, lineage_receipt = extract_frozen_meanmax_head(
        spec, v03_config, head_index=0, device="cpu"
    )
    network.eval()
    network.requires_grad_(False)
    if any(parameter.requires_grad for parameter in network.parameters()):
        raise RunnerContractError("frozen Q1 still has trainable parameters")
    receipt = lineage_receipt.as_dict()
    receipt["parameter_sha256"] = _q1_parameter_sha256(network)
    return network, receipt


def _live_digest(environment: Any, rng: Any) -> str:
    """Digest the detached boundary to detect projection-side mutation."""

    step_env = environment.environment if hasattr(environment, "environment") else environment
    digest = hashlib.sha256()
    for name, value in (
        ("step_index", getattr(step_env, "_step_index", None)),
        ("driver_step_index", getattr(step_env.driver, "step_index", None)),
        ("previous_link_power", getattr(step_env, "_previous_link_power_w", None)),
        ("previous_rates", getattr(step_env, "_previous_served_rate_bps", None)),
        ("pending_segment_age", getattr(step_env, "_pending_segment_age", None)),
        ("user_ecef", step_env.driver.user_ecef_km()),
    ):
        digest.update(name.encode("ascii"))
        if isinstance(value, np.ndarray):
            digest.update(array_sha256(value).encode("ascii"))
        else:
            digest.update(repr(value).encode("utf-8"))
    associations = []
    for association in tuple(getattr(step_env, "_previous_association", ())):
        associations.append(
            None
            if association is None
            else (int(association.norad_id), int(association.cell_id))
        )
    digest.update(repr(associations).encode("ascii"))
    segments = []
    for segment in tuple(getattr(step_env, "_segments", ())):
        segments.append(
            None
            if segment is None
            else (
                int(segment.norad_id),
                int(segment.cell_id),
                float(segment.start_transmit_gain).hex(),
                int(segment.age_steps),
            )
        )
    digest.update(repr(segments).encode("ascii"))
    radiating = getattr(step_env, "_previous_radiating", None)
    if radiating is not None:
        for name in ("norad_ids", "cell_ids", "power_w"):
            digest.update(name.encode("ascii"))
            digest.update(array_sha256(getattr(radiating, name)).encode("ascii"))
    digest.update(repr(copy.deepcopy(rng.bit_generator.state)).encode("utf-8"))
    tracker = getattr(step_env.driver, "_tracker", None)
    if tracker is not None:
        digest.update(repr(copy.deepcopy(tracker.__dict__)).encode("utf-8"))
    return digest.hexdigest()


def _validate_physics(outcome: Any) -> tuple[np.ndarray, float]:
    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
    power = float(outcome.system_power_w)
    if (
        rates.shape != (USERS,)
        or not np.all(np.isfinite(rates))
        or np.any(rates < 0.0)
        or not math.isfinite(power)
        or power < 0.0
        or (power == 0.0 and float(np.sum(rates)) > 0.0)
    ):
        raise RunnerContractError("malformed physical EE inputs")
    return rates, power


def _initial_world_sha(environment: Any, observation: Any) -> str:
    return canonical_sha256(
        {
            "epoch": str(environment.epoch.isoformat()),
            "state_sha256": array_sha256(observation.state_matrix),
            "mask_sha256": array_sha256(observation.masks),
            "candidate_norads_sha256": array_sha256(
                np.stack([table.norad_ids for table in observation.candidates.slot_tables])
            ),
            "candidate_cells_sha256": array_sha256(
                np.stack([table.cell_ids for table in observation.candidates.slot_tables])
            ),
        }
    )


def _surface_receipt(
    *,
    q1: np.ndarray,
    o2: np.ndarray,
    o3: np.ndarray,
    mask: np.ndarray,
    references: np.ndarray,
    anchor: Any,
    projection: Any,
    pnfe: Any,
) -> dict[str, Any]:
    return {
        "anchor_sha256": str(anchor.anchor_sha256),
        "projection_sha256": str(projection.projection_sha256),
        "pnfe_anchor_sha256": str(pnfe.pnfe_anchor_sha256),
        "pnfe_receipt_sha256": str(pnfe.receipt_sha256),
        "mask_sha256": array_sha256(mask),
        "reference_actions_sha256": array_sha256(references),
        "q1_surface_sha256": array_sha256(q1),
        "o2_surface_sha256": array_sha256(o2),
        "o3_surface_sha256": array_sha256(o3),
        "projection_surface_sha256": array_sha256(q1, o2, o3, mask, references),
    }


def _assert_mechanics(
    *,
    mask: np.ndarray,
    references: np.ndarray,
    anchor: Any,
    projection: Any,
    exact_surfaces: Sequence[Any],
    external_surfaces: Sequence[Any],
    pnfe_anchor: Any,
    external_receipt: Any,
    live_before: str,
    live_after: str,
) -> dict[str, Any]:
    legal = np.asarray(mask)
    if legal.dtype != np.bool_ or legal.shape != (USERS, NUM_ACTIONS):
        raise RunnerContractError("native mask is malformed")
    refs = np.asarray(references)
    if refs.dtype == np.bool_ or refs.shape != (USERS,):
        raise RunnerContractError("reference vector is malformed")
    if projection.anchor_sha256 != anchor.anchor_sha256:
        raise RunnerContractError("projection/anchor hash mismatch")
    if projection.horizon != anchor.horizon:
        raise RunnerContractError("projection/anchor horizon mismatch")
    if external_receipt.ops3_anchor_sha256 != anchor.anchor_sha256:
        raise RunnerContractError("PNFE/anchor hash mismatch")
    if external_receipt.ops3_projection_sha256 != projection.projection_sha256:
        raise RunnerContractError("PNFE/projection hash mismatch")
    if external_receipt.pnfe_anchor_sha256 != pnfe_anchor.snapshot_sha256:
        raise RunnerContractError("PNFE anchor receipt/snapshot hash mismatch")
    if live_before != live_after:
        raise RunnerContractError("live environment mutated during detached projection")

    exact_reference_zero = True
    external_reference_zero = True
    shared_masks = True
    shared_references = True
    shared_horizons = True
    shared_opening_gate = True
    for uid, (exact, external) in enumerate(
        zip(exact_surfaces, external_surfaces, strict=True)
    ):
        if not np.array_equal(exact.legal_mask, legal[uid]):
            shared_masks = False
        if not np.array_equal(external.legal_mask, legal[uid]):
            shared_masks = False
        if exact.reference_action != int(refs[uid]) or external.reference_action != int(refs[uid]):
            shared_references = False
        if exact.horizon != projection.horizon or external.horizon != projection.horizon:
            shared_horizons = False
        if exact.q2_values[int(refs[uid])] != 0.0:
            exact_reference_zero = False
        if external.q3_values[int(refs[uid])] != 0.0:
            external_reference_zero = False
        if not np.array_equal(
            np.asarray(exact.opening_service_feasible, dtype=np.bool_),
            np.asarray(external.focal_active[0], dtype=np.bool_),
        ):
            shared_opening_gate = False
    checks = {
        "reference_rows_exact_zero": exact_reference_zero and external_reference_zero,
        "exact_reference_rows_zero": exact_reference_zero,
        "external_reference_rows_zero": external_reference_zero,
        "common_mask": shared_masks,
        "common_reference": shared_references,
        "common_horizon": shared_horizons,
        "opening_service_gate_equal": shared_opening_gate,
        "live_state_unchanged": live_before == live_after,
        "passed": all(
            (
                exact_reference_zero,
                external_reference_zero,
                shared_masks,
                shared_references,
                shared_horizons,
                shared_opening_gate,
                live_before == live_after,
            )
        ),
    }
    if not checks["passed"]:
        raise RunnerContractError(f"mechanics assertions failed: {checks}")
    return checks


def _rankdata(values: Sequence[float]) -> np.ndarray:
    """Return average ranks without requiring scipy in the runner."""

    array = np.asarray(values, dtype=np.float64)
    order = np.argsort(array, kind="stable")
    ranks = np.empty(array.size, dtype=np.float64)
    index = 0
    while index < order.size:
        end = index + 1
        while end < order.size and array[order[end]] == array[order[index]]:
            end += 1
        ranks[order[index:end]] = (index + 1 + end) / 2.0
        index = end
    return ranks


def _spearman(shadow: Sequence[float], truth: Sequence[float]) -> float | None:
    if len(shadow) != len(truth) or len(shadow) < 2:
        return None
    left = _rankdata(shadow)
    right = _rankdata(truth)
    left_centered = left - float(np.mean(left))
    right_centered = right - float(np.mean(right))
    denominator = float(
        np.linalg.norm(left_centered) * np.linalg.norm(right_centered)
    )
    if denominator == 0.0:
        return 1.0 if np.array_equal(left, right) else 0.0
    return float(np.dot(left_centered, right_centered) / denominator)


def _h0_true_matched_nonfocal_ordering(
    *,
    environment: Any,
    env_rng: Any,
    selected_actions: np.ndarray,
    shadow_surfaces: Sequence[Any],
    interval_s: float,
    step_index: int,
) -> dict[str, Any]:
    """Compare PNFE h=0 ordering to fixed-action focal-removal physics.

    This is deliberately bounded and predeclared: only t={1,4,7}, the first
    four users (by id) with at least four legal actions, and the selected
    action plus the three smallest legal alternatives are inspected.  The
    selected arm's non-focal actions remain fixed in every branch.
    """

    if step_index not in DIAGNOSTIC_STEPS:
        return {
            "status": "NOT_SCHEDULED",
            "step_index": int(step_index),
            "reason": f"predeclared h0 diagnostic steps are t={DIAGNOSTIC_STEPS}",
        }
    step_env = environment.environment
    selected = np.asarray(selected_actions, dtype=np.int64)
    eligible: list[int] = []
    action_sets: dict[int, list[int]] = {}
    for uid, surface in enumerate(shadow_surfaces):
        legal = np.flatnonzero(np.asarray(surface.legal_mask, dtype=np.bool_))
        if legal.size < 4:
            continue
        reference = int(surface.reference_action)
        if reference not in legal:
            raise RunnerContractError("selected arm action is not legal at h0")
        alternatives = [int(action) for action in legal.tolist() if int(action) != reference]
        action_sets[uid] = [reference, *alternatives[:3]]
        eligible.append(uid)
        if len(eligible) == 4:
            break
    if not eligible:
        return {
            "status": "MISSING",
            "step_index": int(step_index),
            "reason": "fewer than four legal-action h0 users",
            "eligible_users": [],
        }
    shadow_digest = hashlib.sha256()
    truth_digest = hashlib.sha256()
    focal_samples = 0
    pairwise_compared = 0
    pairwise_agreed = 0
    spearman_values: list[float] = []
    top_action_agreed = 0
    for uid in eligible:
        surface = shadow_surfaces[uid]
        actions = action_sets[uid]
        shadow = np.asarray(surface.externality_bits[0], dtype=np.float64)[actions]
        truth_values: list[float] = []
        for action in actions:
            branch = np.array(selected, dtype=np.int64, copy=True)
            branch[uid] = int(action)
            plus = step_env.evaluate_actions(branch, env_rng)
            minus = step_env.evaluate_actions_without_user(
                branch, env_rng, focal_user=uid
            )
            plus_rates = np.asarray(plus.link_rate_bps, dtype=np.float64)
            minus_rates = np.asarray(minus.link_rate_bps, dtype=np.float64)
            victims = np.arange(USERS) != uid
            truth_values.append(
                float(interval_s)
                * float(math.fsum(float(value) for value in (plus_rates[victims] - minus_rates[victims])))
            )
        truth = np.asarray(truth_values, dtype=np.float64)
        rho = _spearman(shadow, truth)
        if rho is not None:
            spearman_values.append(float(rho))
        for left, right in itertools.combinations(range(len(actions)), 2):
            shadow_delta = float(shadow[right] - shadow[left])
            truth_delta = float(truth[right] - truth[left])
            if shadow_delta == 0.0 or truth_delta == 0.0:
                continue
            pairwise_compared += 1
            pairwise_agreed += int((shadow_delta > 0.0) == (truth_delta > 0.0))
        top_action_agreed += int(int(actions[int(np.argmax(shadow))]) == int(actions[int(np.argmax(truth))]))
        focal_samples += 1
        shadow_digest.update(np.ascontiguousarray(shadow).tobytes(order="C"))
        truth_digest.update(np.ascontiguousarray(truth).tobytes(order="C"))
    if focal_samples == 0:
        return {
            "status": "MISSING",
            "step_index": int(step_index),
            "reason": "no bounded h0 focal samples were exposed",
            "eligible_users": eligible,
        }
    pairwise_agreement = (
        pairwise_agreed / pairwise_compared if pairwise_compared else None
    )
    return {
        "status": "OBSERVED" if pairwise_compared or spearman_values else "MISSING",
        "step_index": int(step_index),
        "eligible_users": eligible,
        "action_sets": {str(uid): actions for uid, actions in action_sets.items()},
        "focal_samples": focal_samples,
        "compared_pairs": pairwise_compared,
        "agreed_pairs": pairwise_agreed,
        "pairwise_agreement": pairwise_agreement,
        "mean_spearman": float(np.mean(spearman_values)) if spearman_values else None,
        "top_action_agreement": top_action_agreed / focal_samples,
        "shadow_delta_sha256": shadow_digest.hexdigest(),
        "true_delta_sha256": truth_digest.hexdigest(),
    }


def _nonfocal_bits(rates: np.ndarray, excluded: Sequence[int], interval_s: float) -> float:
    victims = np.ones(USERS, dtype=np.bool_)
    victims[list(int(value) for value in excluded)] = False
    return float(interval_s) * float(math.fsum(float(value) for value in rates[victims]))


def _evaluate_with_removed_users(
    *,
    environment: Any,
    actions: np.ndarray,
    removed_users: Sequence[int],
    env_rng: Any,
) -> tuple[Any, dict[str, Any]]:
    """Use the private evaluator only for a declared multi-removal branch.

    The public action contract correctly rejects ``NO_OP_ACTION`` whenever a
    legal action exists.  A simultaneous diagnostic needs a physical
    group-removal branch, so it calls the existing detached private evaluator
    with a receipt that proves state and RNG neutrality.  This helper never
    commits a transition and is not a deployment path.
    """

    step_env = environment.environment if hasattr(environment, "environment") else environment
    selected = np.asarray(actions, dtype=np.int64).copy()
    removed = sorted({int(uid) for uid in removed_users})
    if any(uid < 0 or uid >= USERS for uid in removed):
        raise RunnerContractError("multi-removal diagnostic user is out of range")
    selected[removed] = NO_OP_ACTION
    before = _live_digest(step_env, env_rng)
    if not hasattr(step_env, "_evaluate_selected_actions"):
        raise RunnerContractError("private multi-removal evaluator is unavailable")
    decision = getattr(step_env, "_candidates", None)
    if decision is None:
        raise RunnerContractError("private multi-removal evaluator has no live anchor")
    evaluation = step_env._evaluate_selected_actions(decision, selected, env_rng)
    after = _live_digest(step_env, env_rng)
    neutral = before == after
    receipt = {
        "evaluator": "StepEnvironment._evaluate_selected_actions",
        "deployment_path": False,
        "removed_users": removed,
        "state_unchanged": neutral,
        "rng_unchanged": neutral,
        "before_digest": before,
        "after_digest": after,
    }
    if not neutral:
        raise RunnerContractError(
            "private multi-removal diagnostic mutated live state or RNG"
        )
    return evaluation, receipt


def _simultaneous_cross_term(
    *,
    environment: Any,
    env_rng: Any,
    selected_actions: np.ndarray,
    external_surfaces: Sequence[Any],
    anchor: Any,
    interval_s: float,
    step_index: int,
) -> dict[str, Any]:
    """Measure one predeclared same-beam joint-vs-unilateral cross-term.

    The other-user background is the current arm's selected action vector.
    This keeps the diagnostic tied to the action actually being compared in
    that arm and records no cross-arm action.
    """

    if step_index not in DIAGNOSTIC_STEPS:
        return {
            "status": "NOT_SCHEDULED",
            "step_index": int(step_index),
            "reason": f"predeclared cross-term diagnostic steps are t={DIAGNOSTIC_STEPS}",
        }

    preferred: dict[int, int] = {}
    for uid, surface in enumerate(external_surfaces):
        legal = np.asarray(surface.legal_mask, dtype=np.bool_)
        values = np.asarray(surface.q3_values, dtype=np.float64)
        candidates = sorted(
            (
                int(action)
                for action in np.flatnonzero(legal).tolist()
                if int(action) != int(selected_actions[uid])
            ),
            key=lambda action: (-float(values[action]), int(action)),
        )
        if candidates:
            preferred[uid] = candidates[0]
    by_pair: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for uid, action in preferred.items():
        norad = int(anchor.candidate_norad_ids[uid, action])
        cell = int(anchor.candidate_cell_ids[uid, action])
        if norad < 0 or cell < 0:
            continue
        pair = (
            norad,
            cell,
        )
        by_pair[pair].append((uid, action))
    # The preregistered sample is the lexicographically first physical beam
    # group having exactly two or three preferred users.  Larger groups are
    # not silently truncated into a different estimand.
    groups = [
        (pair, items)
        for pair, items in by_pair.items()
        if len(items) in (2, 3)
    ]
    if not groups:
        return {
            "status": "MISSING",
            "step_index": int(step_index),
            "reason": "no exposed same-physical-beam pair",
            "candidate_pair_count": 0,
        }
    _pair, group = sorted(groups, key=lambda item: item[0])[0]
    pair_users = tuple(sorted(group))
    base = np.asarray(selected_actions, dtype=np.int64).copy()
    group_ids = [int(uid) for uid, _action in pair_users]
    base[group_ids] = NO_OP_ACTION
    baseline_eval, baseline_receipt = _evaluate_with_removed_users(
        environment=environment,
        actions=selected_actions,
        removed_users=group_ids,
        env_rng=env_rng,
    )
    baseline_rates = np.asarray(baseline_eval.link_rate_bps, dtype=np.float64)
    unilateral: list[float] = []
    unilateral_receipts: list[dict[str, Any]] = []
    for uid, action in pair_users:
        branch = np.array(base, copy=True)
        branch[uid] = int(action)
        outcome, receipt = _evaluate_with_removed_users(
            environment=environment,
            actions=branch,
            removed_users=[other_uid for other_uid in group_ids if other_uid != uid],
            env_rng=env_rng,
        )
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        unilateral.append(
            _nonfocal_bits(rates - baseline_rates, group_ids, interval_s)
        )
        unilateral_receipts.append(receipt)
    joint = np.array(base, copy=True)
    for uid, action in pair_users:
        joint[uid] = int(action)
    joint_eval, joint_receipt = _evaluate_with_removed_users(
        environment=environment,
        actions=joint,
        removed_users=[],
        env_rng=env_rng,
    )
    joint_rates = np.asarray(joint_eval.link_rate_bps, dtype=np.float64)
    joint_delta = _nonfocal_bits(
        joint_rates - baseline_rates,
        group_ids,
        interval_s,
    )
    additive = float(math.fsum(unilateral))
    reversal = bool(
        joint_delta != 0.0
        and additive != 0.0
        and ((joint_delta > 0.0) != (additive > 0.0))
    )
    return {
        # A local reversal is retained as evidence.  The binding aggregate
        # rule is applied after all scheduled samples are collected.
        "status": "OBSERVED",
        "step_index": int(step_index),
        "background_action_source": "SELECTED_ARM_ACTIONS",
        "candidate_pair_count": len(groups),
        "physical_beam": [int(value) for value in _pair],
        "users": group_ids,
        "actions": [int(action) for _uid, action in pair_users],
        "joint_delta_nonfocal_bits": joint_delta,
        "sum_unilateral_delta_nonfocal_bits": additive,
        "cross_term_nonfocal_bits": float(joint_delta - additive),
        "direction_reversal": reversal,
        "multi_removal_receipts": {
            "baseline": baseline_receipt,
            "unilateral": unilateral_receipts,
            "joint": joint_receipt,
        },
    }


def _action_trace_sha256(arm: str, lineage: int, actions: Sequence[Sequence[int]]) -> str:
    return canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v09-integrated-oracle-action-trace-v1",
            "arm": arm,
            "initialization_seed": int(lineage),
            "world_seed": WORLD_SEED,
            "actions": [[int(value) for value in row] for row in actions],
        }
    )


def evaluate_episode(
    *,
    q1: Any,
    q1_receipt: Mapping[str, Any],
    archive: Any,
    field: KeyedFadingField,
    lineage: int,
    arm: str,
    run_diagnostics: bool = True,
) -> dict[str, Any]:
    """Evaluate one fresh environment for one lineage/arm."""

    if arm not in ARMS:
        raise RunnerContractError(f"unknown arm {arm!r}")
    expected_field = field_for_world(WORLD_SEED)
    if field.root_digest != expected_field.root_digest:
        raise RunnerContractError("episode field is not the common keyed world field")
    environment = screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen._evaluation_rngs(WORLD_SEED)
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    if not math.isfinite(interval_s) or interval_s <= 0.0:
        raise RunnerContractError("native decision interval is not finite/positive")
    initial_world_sha = _initial_world_sha(environment, observation)
    q1_before = _q1_parameter_sha256(q1)
    started = time.perf_counter()
    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    steps = 0
    action_trace: list[list[int]] = []
    per_step: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    flip_counts = {name: 0 for name in ARMS}
    margins: dict[str, list[float | None]] = {name: [] for name in ARMS}
    c3_spread_count = 0
    mechanics_rows: list[dict[str, Any]] = []

    with torch.no_grad():
        while True:
            native = encode_ee_axis_state(environment.environment, observation)
            mask = np.asarray(native.action_masks, dtype=np.bool_)
            q1_surface = _q1_values(q1, native.state_matrix, mask)
            # The frozen Q1 greedy action is a fixed, action-only gauge.  It is
            # never executed as a second policy or used to alter an arm.
            references = select_actions(
                {"Q1": q1_surface, "O2_EXACT": np.zeros_like(q1_surface), "O3_PNFE": np.zeros_like(q1_surface)},
                mask,
                "FULL",
            )
            live_before = _live_digest(environment, env_rng)
            anchor = snapshot_ops3_anchor(environment.environment, observation)
            projection = project_ops3_anchor(anchor)
            exact_surfaces = build_ops3_live_surfaces(anchor, projection, references)
            pnfe_anchor = snapshot_pnfe_anchor(environment.environment, observation, anchor)
            external_receipt = build_pnfe_live_surfaces(
                pnfe_anchor,
                anchor,
                projection,
                exact_surfaces,
                references,
            )
            external_surfaces = external_receipt.surfaces
            live_after = _live_digest(environment, env_rng)
            mechanics = _assert_mechanics(
                mask=mask,
                references=references,
                anchor=anchor,
                projection=projection,
                exact_surfaces=exact_surfaces,
                external_surfaces=external_surfaces,
                pnfe_anchor=pnfe_anchor,
                external_receipt=external_receipt,
                live_before=live_before,
                live_after=live_after,
            )
            mechanics_rows.append(mechanics)

            o2 = np.stack([np.asarray(surface.q2_values, dtype=np.float64) for surface in exact_surfaces])
            o3 = np.stack([np.asarray(surface.q3_values, dtype=np.float64) for surface in external_surfaces])
            surfaces = {"Q1": q1_surface, "O2_EXACT": o2, "O3_PNFE": o3}
            arm_actions = {
                name: select_actions(surfaces, mask, name) for name in ARMS
            }
            for name in ARMS:
                margins[name].extend(
                    _action_margins(_score_surface(surfaces, mask, name), mask, arm_actions[name])
                )
                if name != "DROP_C3":
                    flip_counts[name] += int(
                        np.count_nonzero(arm_actions[name] != arm_actions["DROP_C3"])
                    )
            c3_spread_count += sum(
                int(np.ptp(surface.q3_values[np.asarray(surface.legal_mask)]) > 0.0)
                for surface in external_surfaces
            )
            actions = np.asarray(arm_actions[arm], dtype=np.int64)
            if run_diagnostics:
                diagnostic_before = _live_digest(environment, env_rng)
                h0 = _h0_true_matched_nonfocal_ordering(
                    environment=environment,
                    env_rng=env_rng,
                    selected_actions=actions,
                    shadow_surfaces=external_surfaces,
                    interval_s=interval_s,
                    step_index=steps,
                )
                cross = _simultaneous_cross_term(
                    environment=environment,
                    env_rng=env_rng,
                    selected_actions=actions,
                    external_surfaces=external_surfaces,
                    anchor=anchor,
                    interval_s=interval_s,
                    step_index=steps,
                )
                diagnostic_after = _live_digest(environment, env_rng)
                if diagnostic_before != diagnostic_after:
                    raise RunnerContractError(
                        "diagnostic evaluator mutated the live environment or RNG"
                    )
            else:
                h0 = {"status": "MISSING", "reason": "diagnostics disabled"}
                cross = {"status": "MISSING", "reason": "diagnostics disabled"}
            diagnostics.append(
                {
                    "step_index": int(steps),
                    "h0_true_matched_nonfocal_ordering": h0,
                    "simultaneous_cross_term": cross,
                }
            )

            action_trace.append([int(value) for value in actions.tolist()])
            receipt = _surface_receipt(
                q1=q1_surface,
                o2=o2,
                o3=o3,
                mask=mask,
                references=references,
                anchor=anchor,
                projection=projection,
                pnfe=external_receipt,
            )
            result = environment.step(actions, env_rng)
            outcome = environment.last_outcome
            rates, power = _validate_physics(outcome)
            step_bits = float(math.fsum(float(value) for value in rates)) * interval_s
            total_bits += step_bits
            total_energy += power * interval_s
            served = int(outcome.resolution.served_count)
            served_user_steps += served
            per_step.append(
                {
                    "step_index": int(steps),
                    "total_bits": step_bits,
                    "total_energy_j": float(power * interval_s),
                    "served_user_steps": served,
                    "actions": [int(value) for value in actions.tolist()],
                    "receipt": receipt,
                    "action_flip_counts": {
                        name: int(
                            np.count_nonzero(arm_actions[name] != arm_actions["DROP_C3"])
                        )
                        for name in ARMS
                        if name != "DROP_C3"
                    },
                }
            )
            steps += 1
            if result.done:
                break
            observation = outcome.observation

    q1_after = _q1_parameter_sha256(q1)
    if q1_before != q1_after:
        raise RunnerContractError("frozen Q1 parameters changed during episode")
    if steps != STEPS_PER_EPISODE:
        raise RunnerContractError(
            f"episode length drifted: expected {STEPS_PER_EPISODE}, got {steps}"
        )
    decisions = steps * USERS
    return {
        "schema": EPISODE_SCHEMA,
        "arm": arm,
        "initialization_seed": int(lineage),
        "world_seed": WORLD_SEED,
        "evaluation_split": EVALUATION_SPLIT,
        "test_split_opened": TEST_SPLIT_OPENED,
        "episode_training": EPISODE_TRAINING,
        "users": USERS,
        "steps": steps,
        "decision_count": decisions,
        "initial_world_sha256": initial_world_sha,
        "fading_field_sha256": field.root_digest,
        "fading_field_components": [FIELD_COMPONENT, WORLD_SEED],
        "reference_convention": REFERENCE_CONVENTION,
        "q1_checkpoint": dict(q1_receipt),
        "q1_parameter_sha256_before": q1_before,
        "q1_parameter_sha256_after": q1_after,
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy,
        "served_user_steps": served_user_steps,
        "served_fraction": served_user_steps / decisions,
        "action_trace": action_trace,
        "action_trace_sha256": _action_trace_sha256(arm, lineage, action_trace),
        "per_step": per_step,
        "action_flip_counts": flip_counts,
        "action_margins": margins,
        "c3_legal_spread_count": int(c3_spread_count),
        "full_vs_drop_c3_action_flips": int(flip_counts["FULL"]),
        "diagnostics": diagnostics,
        "mechanics": {
            "rows": mechanics_rows,
            "passed": bool(all(row["passed"] for row in mechanics_rows)),
            "no_learner_update": True,
            "no_test_split": TEST_SPLIT_OPENED is False,
            "no_future_policy_query": True,
            "old_heads_queried": False,
        },
        "elapsed_s": time.perf_counter() - started,
    }


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "episodes": 0,
            "total_bits": 0.0,
            "total_energy_j": 0.0,
            "ratio_of_sums_ee_bits_per_j": None,
            "served_user_steps": 0,
            "decision_count": 0,
            "served_fraction": None,
        }
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    decisions = sum(int(row["decision_count"]) for row in rows)
    return {
        "episodes": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy if energy > 0.0 else None,
        "served_user_steps": served,
        "decision_count": decisions,
        "served_fraction": served / decisions if decisions else None,
    }


def _contrast(
    pooled: Mapping[str, Mapping[str, Any]], drop: str
) -> dict[str, Any]:
    full = pooled["FULL"]
    other = pooled[drop]
    full_ee = float(full["ratio_of_sums_ee_bits_per_j"])
    drop_ee = float(other["ratio_of_sums_ee_bits_per_j"])
    return {
        "full_arm": "FULL",
        "drop_arm": drop,
        "delta_ee_bits_per_j": full_ee - drop_ee,
        "relative_delta_ee": (full_ee - drop_ee) / drop_ee,
        "full_served_user_steps": int(full["served_user_steps"]),
        "drop_served_user_steps": int(other["served_user_steps"]),
        "delta_served_user_steps": int(full["served_user_steps"] - other["served_user_steps"]),
    }


def build_summaries(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_arm: dict[str, list[Mapping[str, Any]]] = {arm: [] for arm in ARMS}
    for row in rows:
        arm = str(row.get("arm"))
        if arm not in by_arm:
            raise RunnerContractError(f"row contains unknown arm {arm!r}")
        by_arm[arm].append(row)
    pooled = {arm: _pool(by_arm[arm]) for arm in ARMS}
    by_lineage: dict[str, dict[str, dict[str, Any]]] = {}
    for arm in ARMS:
        by_lineage[arm] = {}
        for lineage in LINEAGES:
            by_lineage[arm][str(lineage)] = _pool(
                [row for row in by_arm[arm] if int(row["initialization_seed"]) == lineage]
            )
    contrasts = {drop: _contrast(pooled, drop) for drop in ("DROP_C1", "DROP_C2", "DROP_C3")}
    lineage_contrasts: dict[str, dict[str, dict[str, Any]]] = {}
    for lineage in LINEAGES:
        lineage_contrasts[str(lineage)] = {}
        for drop in ("DROP_C1", "DROP_C2", "DROP_C3"):
            left = by_lineage["FULL"][str(lineage)]
            right = by_lineage[drop][str(lineage)]
            lhs = left.get("ratio_of_sums_ee_bits_per_j")
            rhs = right.get("ratio_of_sums_ee_bits_per_j")
            lineage_contrasts[str(lineage)][drop] = {
                "delta_ee_bits_per_j": None if lhs is None or rhs is None else float(lhs - rhs),
                "full_served_user_steps": int(left.get("served_user_steps", 0)),
                "drop_served_user_steps": int(right.get("served_user_steps", 0)),
            }
    return {
        "arms": list(ARMS),
        "pooled_by_arm": pooled,
        "pooled_by_arm_and_initialization": by_lineage,
        "contrasts_pooled": contrasts,
        "contrasts_by_initialization": lineage_contrasts,
    }


def _diagnostic_statuses(rows: Sequence[Mapping[str, Any]]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    h0_comparable = 0
    cross_evaluable = 0
    for row in rows:
        blocks = row.get("diagnostics")
        if not isinstance(blocks, Sequence) or isinstance(blocks, (str, bytes)) or not blocks:
            missing.append(f"{row.get('arm')}/{row.get('initialization_seed')}: required diagnostic missing")
            continue
        for step in blocks:
            if not isinstance(step, Mapping):
                missing.append("required diagnostic row is malformed")
                continue
            for key in ("h0_true_matched_nonfocal_ordering", "simultaneous_cross_term"):
                value = step.get(key)
                status = value.get("status") if isinstance(value, Mapping) else None
                if status == "NOT_SCHEDULED":
                    continue
                if status == "MISSING":
                    continue
                if status not in {"OBSERVED", "PASS", "PASS_WITH_TIES"}:
                    missing.append(f"{key} status={status!r}")
                    continue
                if key == "h0_true_matched_nonfocal_ordering":
                    h0_comparable += int(int(value.get("compared_pairs", 0)) > 0)
                else:
                    cross_evaluable += int("direction_reversal" in value)
    if h0_comparable == 0:
        missing.append("required h0 diagnostic has no comparable sample")
    if cross_evaluable == 0:
        missing.append("required cross-term diagnostic has no evaluable sample")
    return not missing, missing


def _cross_term_reversal_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Apply the preregistered aggregate, rather than a one-sample veto."""

    evaluable = 0
    reversals = 0
    for row in rows:
        diagnostics = row.get("diagnostics")
        if not isinstance(diagnostics, Sequence) or isinstance(diagnostics, (str, bytes)):
            continue
        for block in diagnostics:
            if not isinstance(block, Mapping):
                continue
            sample = block.get("simultaneous_cross_term")
            if not isinstance(sample, Mapping) or sample.get("status") == "NOT_SCHEDULED":
                continue
            if sample.get("status") not in {"OBSERVED", "PASS", "PASS_WITH_TIES"}:
                continue
            if "direction_reversal" not in sample:
                continue
            evaluable += 1
            reversals += int(bool(sample["direction_reversal"]))
    fraction = reversals / evaluable if evaluable else None
    return {
        "evaluable_samples": evaluable,
        "reversal_samples": reversals,
        "reversal_fraction": fraction,
        "block_fraction": CROSS_REVERSAL_BLOCK_FRACTION,
        "systematic_reversal": bool(
            evaluable > 0
            and fraction is not None
            and fraction > CROSS_REVERSAL_BLOCK_FRACTION
        ),
    }


def adjudicate_gate(rows_by_arm: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    """Apply the frozen pooled/per-lineage EE and service gate."""

    if set(rows_by_arm) != set(ARMS):
        raise RunnerContractError("gate rows must contain exactly the four declared arms")
    rows = [row for arm in ARMS for row in rows_by_arm[arm]]
    summaries = build_summaries(rows)
    pooled = summaries["pooled_by_arm"]
    pooled_margins: dict[str, bool] = {}
    for drop in ("DROP_C1", "DROP_C2", "DROP_C3"):
        lhs = pooled["FULL"].get("ratio_of_sums_ee_bits_per_j")
        rhs = pooled[drop].get("ratio_of_sums_ee_bits_per_j")
        pooled_margins[drop] = bool(lhs is not None and rhs is not None and lhs > rhs)
    lineage_positive: dict[str, int] = {}
    lineage_service_noninferior: dict[str, int] = {}
    for drop in ("DROP_C1", "DROP_C2", "DROP_C3"):
        positive = 0
        service = 0
        for lineage in LINEAGES:
            entry = summaries["contrasts_by_initialization"][str(lineage)][drop]
            positive += int(entry["delta_ee_bits_per_j"] is not None and entry["delta_ee_bits_per_j"] > 0.0)
            service += int(entry["full_served_user_steps"] >= entry["drop_served_user_steps"])
        lineage_positive[drop] = positive
        lineage_service_noninferior[drop] = service
    diagnostics_complete, diagnostic_stops = _diagnostic_statuses(rows)
    cross_reversal = _cross_term_reversal_summary(rows)
    mechanics_passed = all(
        bool((row.get("mechanics") or {}).get("passed")) for row in rows
    )
    pooled_service_guard = all(
        pooled["FULL"]["served_user_steps"] >= pooled[drop]["served_user_steps"]
        for drop in ("DROP_C1", "DROP_C2", "DROP_C3")
    )
    spread_exposed = sum(int(row.get("c3_legal_spread_count", 0)) for row in rows) > 0
    action_exposed = sum(int(row.get("full_vs_drop_c3_action_flips", 0)) for row in rows) > 0

    hard_stops = list(diagnostic_stops)
    if not mechanics_passed:
        hard_stops.append("mechanics assertion failure")
    if not diagnostics_complete:
        hard_stops.append("required diagnostic missing or failed")
    if not pooled_service_guard:
        hard_stops.append("pooled service guard failed: one user-step shortfall is fatal")
    if not spread_exposed:
        hard_stops.append("O3_PNFE has zero legal-action spread")
    if not action_exposed:
        hard_stops.append("FULL and DROP_C3 have no action exposure")
    if cross_reversal["systematic_reversal"]:
        hard_stops.append(
            "simultaneous C3 cross-term reversal is systematic by the frozen majority rule"
        )
    for drop in ("DROP_C1", "DROP_C2", "DROP_C3"):
        if not pooled_margins[drop]:
            hard_stops.append(f"pooled FULL vs {drop} EE margin is not strictly positive")
        if lineage_positive[drop] < 2:
            hard_stops.append(f"{drop} has fewer than 2/3 positive lineage contrasts")
        if lineage_service_noninferior[drop] < 2:
            hard_stops.append(f"{drop} has fewer than 2/3 service-noninferior lineages")

    passed = not hard_stops
    return {
        "decision": "PASS_ORACLE_GATE" if passed else "FAIL_ORACLE_GATE",
        "pooled_margins": pooled_margins,
        "positive_lineage_contrasts": lineage_positive,
        "service_noninferior_lineages": lineage_service_noninferior,
        "pooled_service_guard": pooled_service_guard,
        "diagnostics_complete": diagnostics_complete,
        "mechanics_passed": mechanics_passed,
        "c3_spread_exposed": spread_exposed,
        "c3_action_exposed": action_exposed,
        "cross_term_reversal": cross_reversal,
        "hard_stops": hard_stops,
        "summaries": summaries,
    }


def _validate_shard_row(
    row: Mapping[str, Any],
    *,
    arm: str,
    lineage: int,
    expected_field: str,
) -> None:
    """Validate a shard without opening a simulator or recomputing physics."""

    if row.get("schema") != EPISODE_SCHEMA:
        raise RunnerContractError("shard row has a stale episode schema")
    if row.get("arm") != arm or int(row.get("initialization_seed", -1)) != lineage:
        raise RunnerContractError("shard row identity disagrees with its envelope")
    if int(row.get("world_seed", -1)) != WORLD_SEED:
        raise RunnerContractError("shard row world seed is not the frozen world")
    if row.get("evaluation_split") != EVALUATION_SPLIT:
        raise RunnerContractError("shard row is not a TRAIN evaluation")
    if bool(row.get("test_split_opened")) or bool(row.get("episode_training")):
        raise RunnerContractError("shard row opened TEST or trained an episode")
    mechanics = row.get("mechanics")
    if not isinstance(mechanics, Mapping):
        raise RunnerContractError("shard row has no mechanics receipt")
    if bool(mechanics.get("old_heads_queried")):
        raise RunnerContractError("shard row queried a legacy head")
    if not bool(mechanics.get("no_future_policy_query")):
        raise RunnerContractError("shard row queried a future policy")
    if not bool(mechanics.get("no_learner_update")):
        raise RunnerContractError("shard row performed a learner update")
    if not bool(mechanics.get("passed")):
        raise RunnerContractError("shard row did not pass mechanics assertions")
    if row.get("fading_field_sha256") != expected_field:
        raise RunnerContractError("shard rows do not share one keyed field root")
    if row.get("fading_field_components") != [FIELD_COMPONENT, WORLD_SEED]:
        raise RunnerContractError("shard row has noncanonical field components")
    if int(row.get("steps", -1)) != STEPS_PER_EPISODE:
        raise RunnerContractError("shard row episode length is not frozen")
    if int(row.get("decision_count", -1)) != USERS * STEPS_PER_EPISODE:
        raise RunnerContractError("shard row decision count is not frozen")
    bits = float(row.get("total_bits", float("nan")))
    energy = float(row.get("total_energy_j", float("nan")))
    if not math.isfinite(bits) or not math.isfinite(energy) or energy <= 0.0:
        raise RunnerContractError("shard row has nonfinite bits or energy")
    trace = row.get("action_trace")
    if not isinstance(trace, list) or len(trace) != STEPS_PER_EPISODE:
        raise RunnerContractError("shard row action trace is incomplete")
    if row.get("action_trace_sha256") != _action_trace_sha256(arm, lineage, trace):
        raise RunnerContractError("shard action trace checksum mismatch")
    q1_before = row.get("q1_parameter_sha256_before")
    q1_after = row.get("q1_parameter_sha256_after")
    if not isinstance(q1_before, str) or q1_before != q1_after:
        raise RunnerContractError("frozen Q1 changed in a shard")
    diagnostics = row.get("diagnostics")
    if not isinstance(diagnostics, list) or len(diagnostics) != STEPS_PER_EPISODE:
        raise RunnerContractError("shard row diagnostics are incomplete")


def _read_shard(path: Path, *, expected_contract: Mapping[str, Any]) -> dict[str, Any]:
    source = Path(path)
    if source.name != "shard.json" or source.is_symlink() or not source.is_file():
        raise RunnerContractError(f"expected a regular shard.json: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerContractError(f"cannot read shard {source}") from error
    if not isinstance(payload, dict) or payload.get("schema") != SHARD_SCHEMA:
        raise RunnerContractError(f"shard {source} has a stale schema")
    contract = payload.get("contract")
    if not isinstance(contract, Mapping):
        raise RunnerContractError(f"shard {source} has no contract receipt")
    if payload.get("contract_sha256") != canonical_sha256(contract):
        raise RunnerContractError(f"shard {source} contract checksum mismatch")
    if dict(contract) != dict(expected_contract):
        raise RunnerContractError(f"shard {source} contract differs from the frozen plan")
    if payload.get("contract_file_sha256") != file_sha256(CONTRACT_PATH):
        raise RunnerContractError(f"shard {source} contract file hash mismatch")
    if payload.get("runner_file_sha256") != file_sha256(Path(__file__).resolve()):
        raise RunnerContractError(f"shard {source} runner file hash mismatch")
    expected_runtime = {
        str(runtime_path.relative_to(REPO)): file_sha256(runtime_path)
        for runtime_path in RUNTIME_PATHS
    }
    if payload.get("runtime_file_sha256") != expected_runtime:
        raise RunnerContractError(f"shard {source} runtime file hashes mismatch")
    row = payload.get("row")
    if not isinstance(row, Mapping):
        raise RunnerContractError(f"shard {source} has no episode row")
    arm = str(payload.get("arm", ""))
    lineage = int(payload.get("initialization_seed", -1))
    if arm not in ARMS or lineage not in LINEAGES:
        raise RunnerContractError(f"shard {source} has an unknown arm/lineage")
    if payload.get("row_sha256") != canonical_sha256(row):
        raise RunnerContractError(f"shard {source} row checksum mismatch")
    _validate_shard_row(
        row,
        arm=arm,
        lineage=lineage,
        expected_field=field_for_world(WORLD_SEED).root_digest,
    )
    return {
        "path": source,
        "payload": payload,
        "row": dict(row),
        "arm": arm,
        "initialization_seed": lineage,
    }


def _shard_result_envelope(
    *,
    rows: Sequence[Mapping[str, Any]],
    shards: Sequence[Mapping[str, Any]],
    decision: Mapping[str, Any],
    started_utc: str,
    source_mode: str,
) -> dict[str, Any]:
    by_arm = {arm: [row for row in rows if row["arm"] == arm] for arm in ARMS}
    world_hashes = {str(row["initial_world_sha256"]) for row in rows}
    field_hashes = {str(row["fading_field_sha256"]) for row in rows}
    if len(world_hashes) != 1:
        raise RunnerContractError("shards do not reproduce one initial TRAIN world")
    if field_hashes != {field_for_world(WORLD_SEED).root_digest}:
        raise RunnerContractError("shards do not share the frozen keyed field")
    contract = contract_receipt()
    return {
        "schema": RESULT_SCHEMA,
        "status": decision["decision"],
        "claim_ceiling": "ONE_UNOPENED_TRAIN_WORLD_ORACLE_DIRECTION_ONLY_NO_LEARNER_NO_TEST",
        "source_mode": source_mode,
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
        "contract_file": str(CONTRACT_PATH),
        "contract_file_sha256": file_sha256(CONTRACT_PATH),
        "runner_file": str(Path(__file__).resolve()),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "runtime_file_sha256": {
            str(path.relative_to(REPO)): file_sha256(path) for path in RUNTIME_PATHS
        },
        "started_utc": started_utc,
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "world_seed": WORLD_SEED,
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "episode_count": len(rows),
        "evaluation_split": EVALUATION_SPLIT,
        "test_split_opened": TEST_SPLIT_OPENED,
        "episode_training": EPISODE_TRAINING,
        "old_heads_queried": False,
        "future_policy_queried": False,
        "learner_update_count": 0,
        "common_field": common_field_receipt(WORLD_SEED),
        "initial_world_sha256": next(iter(world_hashes)),
        "gate": {key: value for key, value in decision.items() if key != "summaries"},
        "summaries": decision["summaries"],
        "shards": [
            {
                "path": str(item["path"]),
                "sha256": file_sha256(Path(item["path"])),
                "row_sha256": item["payload"]["row_sha256"],
                "arm": item["arm"],
                "initialization_seed": item["initialization_seed"],
            }
            for item in shards
        ],
        "rows": list(rows),
        "arm_row_counts": {arm: len(by_arm[arm]) for arm in ARMS},
    }


def merge_shards(*, shard_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Deterministically merge 12 independent shard receipts and adjudicate."""

    root = Path(shard_dir)
    if root.is_symlink() or not root.is_dir():
        raise RunnerContractError(f"expected a shard directory: {root}")
    paths = sorted(path for path in root.rglob("shard.json") if path.is_file())
    expected = len(ARMS) * len(LINEAGES)
    if len(paths) != expected:
        raise RunnerContractError(f"expected {expected} shards, found {len(paths)}")
    contract = contract_receipt()
    records = [_read_shard(path, expected_contract=contract) for path in paths]
    seen: set[tuple[str, int]] = set()
    for record in records:
        identity = (record["arm"], record["initialization_seed"])
        if identity in seen:
            raise RunnerContractError(f"duplicate shard identity: {identity}")
        seen.add(identity)
    expected_ids = {(arm, lineage) for arm in ARMS for lineage in LINEAGES}
    if seen != expected_ids:
        raise RunnerContractError("shard set is incomplete or contains an unknown identity")
    q1_hashes: dict[int, set[str]] = defaultdict(set)
    for record in records:
        row = record["row"]
        q1_hashes[int(record["initialization_seed"])].add(
            str(row["q1_parameter_sha256_before"])
        )
    if any(len(values) != 1 for values in q1_hashes.values()):
        raise RunnerContractError("same lineage shards do not share one frozen Q1 checkpoint")
    ordered = sorted(
        records,
        key=lambda item: (ARMS.index(item["arm"]), LINEAGES.index(item["initialization_seed"])),
    )
    rows = [item["row"] for item in ordered]
    by_arm = {arm: [row for row in rows if row["arm"] == arm] for arm in ARMS}
    decision = adjudicate_gate(by_arm)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    result = _shard_result_envelope(
        rows=rows,
        shards=ordered,
        decision=decision,
        started_utc=started,
        source_mode="INDEPENDENT_EPISODE_SHARDS_MERGE",
    )
    output = Path(output_dir)
    if output.exists():
        raise RunnerContractError(f"refusing to overwrite output directory: {output}")
    output.mkdir(parents=True, exist_ok=False)
    result_path = output / "result.json"
    result_path.write_bytes(_canonical_bytes(result))
    print(f"wrote {result_path}")
    print(f"decision={decision['decision']} hard_stops={len(decision['hard_stops'])}")
    return result


def run_arm_shard(
    *,
    output_dir: Path,
    arm: str,
    lineage: int,
    tle_root: Path = screen.DEFAULT_TLE_ROOT,
    prereg_path: Path = screen.DEFAULT_PREREG,
    v03_root: Path = screen.DEFAULT_V03_ROOT,
    run_diagnostics: bool = True,
) -> dict[str, Any]:
    """Run one explicit arm/lineage and write an isolated ``shard.json``."""

    if arm not in ARMS:
        raise RunnerContractError(f"unknown arm {arm!r}")
    lineage = int(lineage)
    if lineage not in LINEAGES:
        raise RunnerContractError(f"lineage {lineage} is outside the frozen V0.9 set")
    output = Path(output_dir)
    if output.exists():
        raise RunnerContractError(f"refusing to overwrite output directory: {output}")
    record = read_prereg(Path(prereg_path))
    q1, q1_receipt = load_frozen_q1(Path(v03_root), lineage)
    field = field_for_world(WORLD_SEED)
    with tempfile.TemporaryDirectory(prefix="mcrl-v09-integrated-oracle-tle-") as temporary:
        archive = screen._frozen_archive(record, Path(tle_root), Path(temporary) / "frozen-tle")
        row = evaluate_episode(
            q1=q1,
            q1_receipt=q1_receipt,
            archive=archive,
            field=field,
            lineage=lineage,
            arm=arm,
            run_diagnostics=run_diagnostics,
        )
    contract = contract_receipt()
    payload = {
        "schema": SHARD_SCHEMA,
        "shard_id": f"{arm}-{lineage}",
        "arm": arm,
        "initialization_seed": lineage,
        "world_seed": WORLD_SEED,
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
        "contract_file_sha256": file_sha256(CONTRACT_PATH),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "runtime_file_sha256": {
            str(path.relative_to(REPO)): file_sha256(path) for path in RUNTIME_PATHS
        },
        "field_root_digest": field.root_digest,
        "row_sha256": canonical_sha256(row),
        "row": row,
        "diagnostics_enabled": bool(run_diagnostics),
    }
    output.mkdir(parents=True, exist_ok=False)
    path = output / "shard.json"
    path.write_bytes(_canonical_bytes(payload))
    print(f"wrote {path}")
    print(f"{arm}/{lineage} EE={row['ratio_of_sums_ee_bits_per_j']:.6g}")
    return payload


def run_gate(
    *,
    output_dir: Path,
    tle_root: Path = screen.DEFAULT_TLE_ROOT,
    prereg_path: Path = screen.DEFAULT_PREREG,
    v03_root: Path = screen.DEFAULT_V03_ROOT,
    run_diagnostics: bool = True,
) -> dict[str, Any]:
    """Open exactly the declared 12-episode TRAIN oracle gate."""

    if not run_diagnostics:
        # This switch exists only for an explicit mechanics-only dry launch;
        # its rows are marked missing and can never pass adjudication.
        diagnostic_note = "disabled_by_cli__gate_cannot_pass"
    else:
        diagnostic_note = "enabled"
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    output = Path(output_dir)
    if output.exists():
        raise RunnerContractError(f"refusing to overwrite output directory: {output}")
    output.mkdir(parents=True, exist_ok=False)

    record = read_prereg(Path(prereg_path))
    q1_by_lineage: dict[int, tuple[Any, dict[str, Any]]] = {
        int(lineage): load_frozen_q1(Path(v03_root), int(lineage))
        for lineage in LINEAGES
    }
    field = field_for_world(WORLD_SEED)
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mcrl-v09-integrated-oracle-tle-") as temporary:
        archive = screen._frozen_archive(record, Path(tle_root), Path(temporary) / "frozen-tle")
        for arm in ARMS:
            for lineage in LINEAGES:
                q1, q1_receipt = q1_by_lineage[int(lineage)]
                row = evaluate_episode(
                    q1=q1,
                    q1_receipt=q1_receipt,
                    archive=archive,
                    field=field,
                    lineage=int(lineage),
                    arm=arm,
                    run_diagnostics=run_diagnostics,
                )
                rows.append(row)
                print(
                    f"[{arm}/{lineage}] EE={row['ratio_of_sums_ee_bits_per_j']:.6g} "
                    f"served={row['served_fraction']:.4f} "
                    f"{row['elapsed_s']:.2f}s"
                )

    by_arm = {arm: [row for row in rows if row["arm"] == arm] for arm in ARMS}
    world_hashes = {str(row["initial_world_sha256"]) for row in rows}
    field_hashes = {str(row["fading_field_sha256"]) for row in rows}
    if len(world_hashes) != 1:
        raise RunnerContractError("fresh arms did not reproduce one initial TRAIN world")
    if field_hashes != {field.root_digest}:
        raise RunnerContractError("fresh arms did not share one keyed field root")
    decision = adjudicate_gate(by_arm)
    result = {
        "schema": RESULT_SCHEMA,
        "status": decision["decision"],
        "claim_ceiling": (
            "ONE_UNOPENED_TRAIN_WORLD_ORACLE_DIRECTION_ONLY_NO_LEARNER_NO_TEST"
        ),
        "contract": contract_receipt(),
        "contract_sha256": canonical_sha256(contract_receipt()),
        "contract_file": str(CONTRACT_PATH),
        "contract_file_sha256": file_sha256(CONTRACT_PATH),
        "runner_file": str(Path(__file__).resolve()),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "runtime_file_sha256": {
            str(path.relative_to(REPO)): file_sha256(path) for path in RUNTIME_PATHS
        },
        "started_utc": started,
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "world_seed": WORLD_SEED,
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "episode_count": len(rows),
        "evaluation_split": EVALUATION_SPLIT,
        "test_split_opened": TEST_SPLIT_OPENED,
        "episode_training": EPISODE_TRAINING,
        "old_heads_queried": False,
        "future_policy_queried": False,
        "learner_update_count": 0,
        "diagnostic_mode": diagnostic_note,
        "common_field": common_field_receipt(WORLD_SEED),
        "initial_world_sha256": next(iter(world_hashes)),
        "gate": {
            key: value
            for key, value in decision.items()
            if key != "summaries"
        },
        "summaries": decision["summaries"],
        "rows": rows,
    }
    result_path = output / "result.json"
    result_path.write_bytes(_canonical_bytes(result))
    print(f"wrote {result_path}")
    print(f"decision={decision['decision']} hard_stops={len(decision['hard_stops'])}")
    return result


def _print_plan() -> int:
    payload = contract_receipt()
    payload["contract_sha256"] = canonical_sha256(payload)
    payload["common_field"] = common_field_receipt(WORLD_SEED)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="print the frozen contract without opening a world")
    run = sub.add_parser("run", help="run the explicit 12-episode TRAIN oracle gate")
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--tle-root", type=Path, default=screen.DEFAULT_TLE_ROOT)
    run.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
    run.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
    run.add_argument(
        "--disable-diagnostics",
        action="store_true",
        help="mechanics-only dry launch; receipts are marked missing and cannot pass",
    )
    run_arm = sub.add_parser(
        "run-arm",
        help="run one independent arm/lineage shard (safe for process parallelism)",
    )
    run_arm.add_argument("--arm", choices=ARMS, required=True)
    run_arm.add_argument("--lineage", type=int, choices=LINEAGES, required=True)
    run_arm.add_argument("--output-dir", type=Path, required=True)
    run_arm.add_argument("--tle-root", type=Path, default=screen.DEFAULT_TLE_ROOT)
    run_arm.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
    run_arm.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
    run_arm.add_argument(
        "--disable-diagnostics",
        action="store_true",
        help="mechanics-only dry launch; merge remains fail-closed",
    )
    merge = sub.add_parser(
        "merge",
        help="verify a complete shard directory, merge deterministically, and adjudicate",
    )
    merge.add_argument("--shard-dir", type=Path, required=True)
    merge.add_argument("--output-dir", type=Path, required=True)
    adjudicate = sub.add_parser(
        "adjudicate",
        help="alias for deterministic shard merge and gate adjudication",
    )
    adjudicate.add_argument("--shard-dir", type=Path, required=True)
    adjudicate.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "plan":
        return _print_plan()
    if args.command == "run-arm":
        run_arm_shard(
            output_dir=Path(args.output_dir),
            arm=str(args.arm),
            lineage=int(args.lineage),
            tle_root=Path(args.tle_root),
            prereg_path=Path(args.prereg),
            v03_root=Path(args.v03_root),
            run_diagnostics=not bool(args.disable_diagnostics),
        )
        return 0
    if args.command in {"merge", "adjudicate"}:
        merge_shards(
            shard_dir=Path(args.shard_dir),
            output_dir=Path(args.output_dir),
        )
        return 0
    run_gate(
        output_dir=Path(args.output_dir),
        tle_root=Path(args.tle_root),
        prereg_path=Path(args.prereg),
        v03_root=Path(args.v03_root),
        run_diagnostics=not bool(args.disable_diagnostics),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
