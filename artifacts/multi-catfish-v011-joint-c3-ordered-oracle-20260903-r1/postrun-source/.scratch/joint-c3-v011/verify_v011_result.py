#!/usr/bin/env python3
"""Outcome-independent verifier for a frozen V0.11 result receipt.

The V0.11 runner is the producer of the receipt.  This module intentionally
does not import it (or any of its merge/gate helpers): it repeats the frozen
receipt, provenance, coverage, aggregation, and ordered-selection checks from
the preregistered control plane.  It only consumes a completed ``result.json``
and never opens a simulator, a checkpoint, or a TEST split.

The producer writes canonical JSON without a trailing newline.  The verifier
requires that exact encoding, rejects duplicate/non-finite JSON values, and
fails closed on every mismatch.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any


REPO = Path(__file__).resolve().parents[2]

# Frozen V0.11 wire constants.  They are deliberately repeated here instead
# of importing the producer or project runtime.  The values are the
# pre-outcome PREPARE-RECEIPT authority for this gate.
RESULT_SCHEMA = "multi-catfish-mcrl-v011-joint-c3-ordered-oracle-result-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v011-joint-c3-ordered-oracle-episode-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v011-joint-c3-ordered-oracle-shard-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v011-joint-c3-ordered-oracle-contract-v1"
CLAIM_CEILING = "ONE_TRAIN_WORLD_ORDERED_ORACLE_NO_LEARNER_NO_TEST"

WORLD_SEED = 2026104701
LINEAGES = (2026092101, 2026092102, 2026092103)
ARMS = (
    "DROP_C3",
    "FULL_M1D",
    "FULL_AP",
    "DIAG_O_DROP",
    "DIAG_O_FULL",
)
USERS = 100
STEPS_PER_EPISODE = 10
MAX_SWEEPS = 5
FIELD_COMPONENT = "MCRL_V011_JOINT_C3_ORDERED_ORACLE_V1"
FIELD_EXCLUDES = ("arm", "initialization_seed", "policy_label")

# These are the byte identities sealed in the V0.11 PREPARE-RECEIPT.  The
# result verifier authenticates the current workspace against them; it does
# not take source hashes from the result as a new authority.
EXPECTED_CONTRACT_FILE_SHA256 = (
    "1cd8f529b6c775c9cb344886856211f89e8eef50569598cd91b9f6b324e5c97f"
)
EXPECTED_CONTRACT_SHA256 = (
    "0c6e5f40498f6300b8b77068c3791a7d4267bd0909390b7b087cffad4acab9b0"
)
EXPECTED_RUNNER_FILE_SHA256 = (
    "9ade6e8ade29a688b4e2ecafb2ebfd9a0ba19886a698d839bce5b3d8e95e641f"
)
EXPECTED_RUNTIME_FILE_SHA256 = {
    "src/mcrl/runtime/ee_axis_joint_c3.py": (
        "6ec3fb3ff69edec887f4129ebd9ee140c943006a5927f93fc45dbfc45e26c07c"
    ),
    "src/mcrl/runtime/ee_axis_matched_opening.py": (
        "0ba0649f520cdc290061001d9a4ad971015524e63dbf1cf33c5fc82c7eb547f3"
    ),
    "src/mcrl/runtime/ee_axis_ops3.py": (
        "68251ff750410ff74abfb412df83bafef459831874abfcfbee6e1e04d1adea02"
    ),
    "src/mcrl/runtime/ee_axis_ops3_live.py": (
        "6847069235ce3789c9f2f76bfd1de9f7a4e02402788eed0fabcc0ab57faed35a"
    ),
}
EXPECTED_FIELD_ROOT_DIGEST = (
    "ac9238e2ea6843aa950c33a02c9657466a669b72df89b2fd16fdd454970db7b9"
)
EXPECTED_Q1_CHECKPOINTS = {
    2026092101: {
        "checkpoint_sha256": (
            "f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0"
        ),
        "parameter_sha256": (
            "4eba7ed1d89bcd41f68716ba25c739ce4132d79e722ce4a3313c342e8a0097a0"
        ),
    },
    2026092102: {
        "checkpoint_sha256": (
            "6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba"
        ),
        "parameter_sha256": (
            "e79fa1512eebd3f6fdfad753459bd6819c36e56f07ce8df28b61c557ab2da5e1"
        ),
    },
    2026092103: {
        "checkpoint_sha256": (
            "507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2"
        ),
        "parameter_sha256": (
            "807d31778203cdf3e7848e22d23ef8f450244eb9b8fe4f309dbb478c4cfa3e37"
        ),
    },
}

CONTRACT_PATH = REPO / "docs" / "MULTI-CATFISH-MCRL-V011-JOINT-C3-ORDERED-ORACLE-PREREG-2026-09-03.md"
RUNNER_PATH = REPO / ".scratch" / "joint-c3-v011" / "run_v011_joint_c3_ordered_oracle.py"


class V011ResultVerificationError(ValueError):
    """A persisted V0.11 result receipt failed closed verification."""


def _fail(message: str) -> None:
    raise V011ResultVerificationError(message)


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V011ResultVerificationError(
            "payload is not finite canonical JSON"
        ) from error


def canonical_sha256(value: object) -> str:
    """Return the producer-compatible SHA-256 of canonical JSON ``value``."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        _fail(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    try:
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise V011ResultVerificationError(f"cannot read file: {source}") from error
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    _fail(f"JSON constant {value!r} is not finite")
    return None


def read_canonical_json(path: Path) -> tuple[dict[str, Any], str]:
    """Read one producer-style canonical JSON object and its file digest."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        _fail(f"result JSON is missing or non-regular: {source}")
    try:
        raw = source.read_bytes()
        payload = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except V011ResultVerificationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise V011ResultVerificationError(f"invalid result JSON: {source}") from error
    if not isinstance(payload, dict):
        _fail("result JSON root must be an object")
    if raw != _canonical_bytes(payload):
        _fail("result JSON is not the producer's canonical encoding")
    return payload, _sha256_bytes(raw)


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field} must be a lowercase SHA-256 digest")
    return value


def _exact_int(value: object, *, field: str, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        suffix = f" >= {minimum}" if minimum is not None else ""
        _fail(f"{field} must be an exact integer{suffix}")
    return value


def _finite_number(
    value: object,
    *,
    field: str,
    positive: bool = False,
    nonnegative: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{field} must be a finite number")
    number = float(value)
    if (
        not math.isfinite(number)
        or (positive and number <= 0.0)
        or (nonnegative and number < 0.0)
    ):
        _fail(f"{field} has an invalid finite-number value")
    return number


def _bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        _fail(f"{field} must be Boolean")
    return value


def _mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{field} must be a JSON object")
    return value


def _list(value: object, *, field: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{field} must be a JSON array")
    return value


def _frozen_contract() -> dict[str, Any]:
    """Reproduce the exact V0.11 contract receipt from frozen primitives."""

    return {
        "schema": CONTRACT_SCHEMA,
        "world_seed": WORLD_SEED,
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "arm_heads": {
            "DROP_C3": ["Q1", "O2_OPS3"],
            "FULL_M1D": ["Q1", "O2_OPS3", "O3_M1D"],
            "FULL_AP": ["Q1", "O2_OPS3", "O3_AP_MONE"],
            "DIAG_O_DROP": ["O1_EXACT", "O2_OPS3"],
            "DIAG_O_FULL": ["O1_EXACT", "O2_OPS3", "O3_EXACT"],
        },
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes": len(ARMS) * len(LINEAGES),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "background": "MASKED_ARGMAX_Q1_PLUS_O2",
        "candidate_order": ["AP_MONE", "M1D"],
        "max_complete_gauss_seidel_sweeps": MAX_SWEEPS,
        "gauss_seidel_user_order": list(range(USERS)),
        "ap_permutations": "ONE_KEYED_ORDER_AND_EXACT_REVERSE",
        "summation": "left_to_right_unweighted",
        "selection": "one_common_mask_one_argmax_one_action",
        "field_components": [FIELD_COMPONENT, WORLD_SEED],
        "field_excludes": list(FIELD_EXCLUDES),
        "matched_opening_schema": "multi-catfish-mcrl-c3-matched-opening-surface-v1",
        "joint_c3_schema": "multi-catfish-mcrl-joint-c3-runtime-v1",
        "ops3_live_schema": "multi-catfish-mcrl-v03-c2-ops3-live-anchor-v1.2",
        "lambda_bits_per_j_hex": "0x1.443a8f481639ap+26",
        "kappa_bits_hex": "0x1.2cea89d260f2ap+33",
        "gate": {
            "pooled_full_strictly_above_drop_c3": True,
            "positive_lineages_minimum": 2,
            "pooled_service_noninferior": True,
            "service_noninferior_lineages_minimum": 2,
            "one_user_step_shortfall_fails": True,
            "nonzero_c3_spread": True,
            "nonzero_action_exposure": True,
            "m1d_every_anchor_fixed_point": True,
            "m1d_final_one_pass_exact": True,
            "exact_o_diagnostic_nonbinding": True,
        },
        "selection_table": {
            "A_and_M_or_O": "GO_AP_MONE_LEARNABILITY_PREREG_ONLY",
            "not_A_and_M": "GO_M1D_LEARNABILITY_PREREG_ONLY",
            "A_only": "INCONSISTENT_AP_ONLY_NO_LEARNER_REVIEW",
            "O_only": "C1_ALIGNMENT_BLOCKS_C3_NO_LEARNER",
            "none": "JOINT_C3_STRUCTURAL_REDESIGN_REQUIRED",
        },
    }


def _verify_authority(payload: Mapping[str, Any]) -> None:
    contract = _mapping(payload.get("contract"), field="contract")
    claimed_contract_sha = _digest(
        payload.get("contract_sha256"), field="contract_sha256"
    )
    if canonical_sha256(contract) != claimed_contract_sha:
        _fail("contract_sha256 does not match canonical contract")
    if claimed_contract_sha != EXPECTED_CONTRACT_SHA256:
        _fail("contract receipt is not the frozen V0.11 contract")
    if dict(contract) != _frozen_contract():
        _fail("contract fields differ from the frozen V0.11 contract")

    contract_file_sha = _digest(
        payload.get("contract_file_sha256"), field="contract_file_sha256"
    )
    runner_file_sha = _digest(
        payload.get("runner_file_sha256"), field="runner_file_sha256"
    )
    if contract_file_sha != EXPECTED_CONTRACT_FILE_SHA256:
        _fail("contract_file_sha256 is not the frozen contract hash")
    if runner_file_sha != EXPECTED_RUNNER_FILE_SHA256:
        _fail("runner_file_sha256 is not the frozen runner hash")

    runtime_raw = _mapping(
        payload.get("runtime_file_sha256"), field="runtime_file_sha256"
    )
    if set(runtime_raw) != set(EXPECTED_RUNTIME_FILE_SHA256):
        _fail("runtime_file_sha256 path set differs from the frozen source set")
    for relative, expected in EXPECTED_RUNTIME_FILE_SHA256.items():
        claimed = _digest(runtime_raw.get(relative), field=f"runtime_file_sha256.{relative}")
        if claimed != expected:
            _fail(f"runtime_file_sha256.{relative} is not frozen")

    # Authenticate the source bytes as well as the copied claims.  This keeps
    # a result from being accepted after a producer/runtime edit in the
    # shared checkout.
    if not CONTRACT_PATH.is_file() or file_sha256(CONTRACT_PATH) != EXPECTED_CONTRACT_FILE_SHA256:
        _fail("current contract bytes do not match the frozen source")
    if not RUNNER_PATH.is_file() or file_sha256(RUNNER_PATH) != EXPECTED_RUNNER_FILE_SHA256:
        _fail("current runner bytes do not match the frozen source")
    for relative, expected in EXPECTED_RUNTIME_FILE_SHA256.items():
        current = REPO / relative
        if not current.is_file() or file_sha256(current) != expected:
            _fail(f"current runtime bytes do not match the frozen source: {relative}")

    if payload.get("claim_ceiling") != CLAIM_CEILING:
        _fail("claim ceiling is stale or too broad")
    field_digest = _digest(payload.get("field_root_digest"), field="field_root_digest")
    if field_digest != EXPECTED_FIELD_ROOT_DIGEST:
        _fail("result field root is not the frozen common field")
    if payload.get("field_root_digest") != EXPECTED_FIELD_ROOT_DIGEST:
        _fail("result field root is not the frozen common field")


def _verify_checkpoint(value: object, *, lineage: int, field: str) -> None:
    checkpoint = _mapping(value, field=field)
    expected_keys = {
        "checkpoint_path",
        "checkpoint_sha256",
        "authority_sha256",
        "initialization_seed",
        "rung",
        "head_index",
        "trainer_algorithm",
        "config_sha256",
        "parameter_sha256",
    }
    if set(checkpoint) != expected_keys:
        _fail(f"{field} fields differ from the frozen Q1 receipt")
    expected = EXPECTED_Q1_CHECKPOINTS[lineage]
    if _digest(checkpoint.get("checkpoint_sha256"), field=f"{field}.checkpoint_sha256") != expected["checkpoint_sha256"]:
        _fail(f"{field}.checkpoint_sha256 is not frozen")
    if _digest(checkpoint.get("parameter_sha256"), field=f"{field}.parameter_sha256") != expected["parameter_sha256"]:
        _fail(f"{field}.parameter_sha256 is not frozen")
    _digest(checkpoint.get("authority_sha256"), field=f"{field}.authority_sha256")
    _digest(checkpoint.get("config_sha256"), field=f"{field}.config_sha256")
    _exact_int(checkpoint.get("initialization_seed"), field=f"{field}.initialization_seed")
    if checkpoint.get("initialization_seed") != lineage:
        _fail(f"{field}.initialization_seed does not match row lineage")
    if checkpoint.get("rung") != 10 or checkpoint.get("head_index") != 0:
        _fail(f"{field} is not the frozen Q1 rung-10 head-0 receipt")
    if not isinstance(checkpoint.get("checkpoint_path"), str) or not checkpoint["checkpoint_path"]:
        _fail(f"{field}.checkpoint_path must be a non-empty string")
    if not isinstance(checkpoint.get("trainer_algorithm"), str) or not checkpoint["trainer_algorithm"]:
        _fail(f"{field}.trainer_algorithm must be a non-empty string")


def _verify_surface_hashes(value: object, *, field: str) -> None:
    surfaces = _mapping(value, field=field)
    expected = {"q1", "o2", "o1", "o3", "mask", "q1_reference", "background"}
    if set(surfaces) != expected:
        _fail(f"{field} fields differ from the frozen surface receipt")
    for key in expected:
        _digest(surfaces.get(key), field=f"{field}.{key}")


def _verify_mechanics(value: object, *, field: str) -> None:
    mechanics = _mapping(value, field=field)
    expected = {
        "live_state_unchanged",
        "common_mask",
        "reference_rows_exact_zero",
        "opening_service_gate_equal",
        "background_sha256",
        "passed",
    }
    if set(mechanics) != expected:
        _fail(f"{field} fields differ from the frozen mechanics receipt")
    for key in expected - {"background_sha256"}:
        _bool(mechanics.get(key), field=f"{field}.{key}")
    _digest(mechanics.get("background_sha256"), field=f"{field}.background_sha256")
    expected_passed = all(bool(mechanics[key]) for key in expected - {"passed", "background_sha256"})
    if mechanics["passed"] != expected_passed:
        _fail(f"{field}.passed disagrees with mechanics components")


def _verify_method(value: object, *, arm: str, field: str) -> bool:
    method = _mapping(value, field=field)
    kind = method.get("kind")
    if not isinstance(kind, str):
        _fail(f"{field}.kind must be a string")
    expected_kind = {
        "DROP_C3": "DROP_C3",
        "FULL_M1D": "M1D",
        "FULL_AP": "AP_MONE",
        "DIAG_O_DROP": "EXACT_O1_DROP",
        "DIAG_O_FULL": "EXACT_O1_FULL",
    }[arm]
    if kind != expected_kind:
        _fail(f"{field}.kind does not match arm")

    if arm == "DROP_C3":
        if method.get("status") != "BASE":
            _fail(f"{field}.status is stale")
        return True

    identity = _bool(method.get("identity_passed"), field=f"{field}.identity_passed")
    if arm == "FULL_M1D":
        sweep_count = _exact_int(
            method.get("sweep_count"), field=f"{field}.sweep_count", minimum=1
        )
        if sweep_count > MAX_SWEEPS:
            _fail(f"{field}.sweep_count exceeds the five-sweep cap")
        changed = _list(method.get("changed_per_sweep"), field=f"{field}.changed_per_sweep")
        if len(changed) != sweep_count:
            _fail(f"{field}.changed_per_sweep length disagrees with sweep_count")
        for index, count in enumerate(changed):
            _exact_int(count, field=f"{field}.changed_per_sweep[{index}]", minimum=0)
        for key in ("final_iterate_sha256", "production_sha256"):
            _digest(method.get(key), field=f"{field}.{key}")
        _bool(method.get("cycles_detected"), field=f"{field}.cycles_detected")
        g_delta = method.get("g_bm_minus_g_b0_bits")
        if identity:
            _finite_number(g_delta, field=f"{field}.g_bm_minus_g_b0_bits")
        elif g_delta is not None:
            _finite_number(g_delta, field=f"{field}.g_bm_minus_g_b0_bits")
        if identity:
            _mapping(method.get("q1_vs_exact_o1"), field=f"{field}.q1_vs_exact_o1")
    elif arm == "FULL_AP":
        for key in ("permutation_sha256", "proposal_sha256"):
            _digest(method.get(key), field=f"{field}.{key}")
        for key in ("proposal_flips_from_background", "selected_flips_from_proposal"):
            _exact_int(method.get(key), field=f"{field}.{key}", minimum=0)
        if method.get("status") != "CONSTRUCTED":
            _fail(f"{field}.status is stale")
        for key in ("order_credited_sum_bits", "order_joint_surplus_bits", "order_identity_residual_bits"):
            values = _list(method.get(key), field=f"{field}.{key}")
            if len(values) != 2:
                _fail(f"{field}.{key} must contain both antithetic orders")
            for index, item in enumerate(values):
                _finite_number(item, field=f"{field}.{key}[{index}]")
        for key in (
            "proposal_flips_from_background",
            "executed_flips_from_background",
            "executed_flips_from_proposal",
        ):
            # The first proposal count is checked above; the latter two are
            # appended by the execution receipt below.
            if key in method:
                _exact_int(method[key], field=f"{field}.{key}", minimum=0)
        for key in (
            "executed_antithetic_credited_sum_bits",
            "executed_joint_surplus_bits",
            "executed_joint_minus_credited_bits",
        ):
            _finite_number(method.get(key), field=f"{field}.{key}")
    else:
        # Exact-O diagnostics carry one or two sweep receipts.  Their
        # candidate-specific identity is the convergence/equivalence bit.
        for prefix in ("drop", "full"):
            status_key = f"{prefix}_status"
            if status_key not in method:
                if prefix == "full" and arm == "DIAG_O_DROP":
                    continue
                _fail(f"{field}.{status_key} is missing")
            status = method[status_key]
            if not isinstance(status, str) or not status:
                _fail(f"{field}.{status_key} must be a non-empty string")
            sweep_key = f"{prefix}_sweep_count"
            changed_key = f"{prefix}_changed_per_sweep"
            if sweep_key in method:
                _exact_int(method[sweep_key], field=f"{field}.{sweep_key}", minimum=0)
            if changed_key in method:
                changed = _list(method[changed_key], field=f"{field}.{changed_key}")
                if len(changed) > MAX_SWEEPS:
                    _fail(f"{field}.{changed_key} exceeds the five-sweep cap")
                for index, count in enumerate(changed):
                    _exact_int(count, field=f"{field}.{changed_key}[{index}]", minimum=0)
        if arm == "DIAG_O_FULL" and "full_status" not in method:
            _fail(f"{field}.full_status is missing")
    return identity


def _verify_step(value: object, *, arm: str, lineage: int, index: int) -> tuple[float, float, int, int, int, int]:
    field = f"rows[{arm}/{lineage}].per_step[{index}]"
    step = _mapping(value, field=field)
    expected = {
        "step_index",
        "total_bits",
        "total_energy_j",
        "served_user_steps",
        "hold_rate",
        "active_beam_count",
        "action_exposure",
        "selected_actions",
        "surface_sha256",
        "mechanics",
        "method",
        "joint_opening",
    }
    if set(step) != expected:
        _fail(f"{field} fields differ from the frozen episode receipt")
    if step.get("step_index") != index:
        _fail(f"{field}.step_index is not ordered")
    bits = _finite_number(step.get("total_bits"), field=f"{field}.total_bits", nonnegative=True)
    energy = _finite_number(step.get("total_energy_j"), field=f"{field}.total_energy_j", positive=True)
    served = _exact_int(step.get("served_user_steps"), field=f"{field}.served_user_steps", minimum=0)
    if served > USERS:
        _fail(f"{field}.served_user_steps exceeds user count")
    active = _exact_int(step.get("active_beam_count"), field=f"{field}.active_beam_count", minimum=0)
    exposure = _exact_int(step.get("action_exposure"), field=f"{field}.action_exposure", minimum=0)
    if exposure > USERS:
        _fail(f"{field}.action_exposure exceeds user count")
    hold_rate = step.get("hold_rate")
    if hold_rate is not None and not 0.0 <= _finite_number(hold_rate, field=f"{field}.hold_rate") <= 1.0:
        _fail(f"{field}.hold_rate lies outside [0,1]")
    actions = _list(step.get("selected_actions"), field=f"{field}.selected_actions")
    if len(actions) != USERS:
        _fail(f"{field}.selected_actions must contain 100 native actions")
    for action_index, action in enumerate(actions):
        action_value = _exact_int(action, field=f"{field}.selected_actions[{action_index}]")
        if not 0 <= action_value < 28:
            _fail(f"{field}.selected_actions[{action_index}] is outside native actions")
    _verify_surface_hashes(step.get("surface_sha256"), field=f"{field}.surface_sha256")
    _verify_mechanics(step.get("mechanics"), field=f"{field}.mechanics")
    identity = _verify_method(step.get("method"), arm=arm, field=f"{field}.method")
    opening = _mapping(step.get("joint_opening"), field=f"{field}.joint_opening")
    opening_expected = {"status", "changed_users", "delta_bits", "delta_energy_j", "fixed_lambda_surplus_bits"}
    if set(opening) != opening_expected:
        _fail(f"{field}.joint_opening fields differ from the frozen receipt")
    status = opening.get("status")
    if status not in {"NO_EXPOSURE", "OBSERVED"}:
        _fail(f"{field}.joint_opening.status is invalid")
    changed = _exact_int(opening.get("changed_users"), field=f"{field}.joint_opening.changed_users", minimum=0)
    if changed > USERS:
        _fail(f"{field}.joint_opening.changed_users exceeds user count")
    delta_bits = _finite_number(opening.get("delta_bits"), field=f"{field}.joint_opening.delta_bits")
    delta_energy = _finite_number(opening.get("delta_energy_j"), field=f"{field}.joint_opening.delta_energy_j")
    surplus = _finite_number(opening.get("fixed_lambda_surplus_bits"), field=f"{field}.joint_opening.fixed_lambda_surplus_bits")
    # The exact lambda is frozen in the contract.  Keep this check outcome
    # independent: it only authenticates the arithmetic relationship recorded
    # in the receipt, not whether the outcome is favorable.
    expected_surplus = delta_bits - float.fromhex("0x1.443a8f481639ap+26") * delta_energy
    if surplus != expected_surplus:
        _fail(f"{field}.joint_opening fixed-lambda arithmetic disagrees")
    if status == "NO_EXPOSURE":
        if changed != 0 or delta_bits != 0.0 or delta_energy != 0.0 or surplus != 0.0:
            _fail(f"{field}.joint_opening NO_EXPOSURE payload is nonzero")
    elif changed == 0:
        _fail(f"{field}.joint_opening OBSERVED payload has zero exposure")
    return bits, energy, served, exposure, int(status == "OBSERVED"), int(
        status == "OBSERVED" and surplus < 0.0
    )


def _verify_row(value: object, *, expected_arm: str, expected_lineage: int, world_digest: str | None) -> dict[str, Any]:
    field = f"rows[{expected_arm}/{expected_lineage}]"
    row = _mapping(value, field=field)
    expected = {
        "schema",
        "arm",
        "initialization_seed",
        "world_seed",
        "split",
        "test_split_opened",
        "episode_training",
        "users",
        "steps",
        "initial_world_sha256",
        "field_root_digest",
        "q1_checkpoint",
        "q1_parameter_sha256_before",
        "q1_parameter_sha256_after",
        "total_bits",
        "total_energy_j",
        "ratio_of_sums_ee_bits_per_j",
        "served_user_steps",
        "served_fraction",
        "c3_legal_spread_count",
        "action_exposure",
        "joint_opening_exposed_count",
        "joint_opening_negative_count",
        "method_passed",
        "candidate_specific_identity_passed",
        "mechanics_passed",
        "per_step",
        "elapsed_s",
    }
    if set(row) != expected:
        _fail(f"{field} fields differ from the frozen episode receipt")
    if row.get("schema") != EPISODE_SCHEMA or row.get("arm") != expected_arm:
        _fail(f"{field} schema or arm is stale")
    if row.get("initialization_seed") != expected_lineage:
        _fail(f"{field} lineage is not the expected frozen lineage")
    if row.get("world_seed") != WORLD_SEED or row.get("split") != "TRAIN":
        _fail(f"{field} world/split identity drifted")
    if row.get("test_split_opened") is not False or row.get("episode_training") is not False:
        _fail(f"{field} crossed TEST or training boundary")
    if row.get("users") != USERS or row.get("steps") != STEPS_PER_EPISODE:
        _fail(f"{field} episode dimensions drifted")
    initial_world = _digest(row.get("initial_world_sha256"), field=f"{field}.initial_world_sha256")
    if world_digest is not None and initial_world != world_digest:
        _fail(f"{field}.initial_world_sha256 differs across shards")
    if _digest(row.get("field_root_digest"), field=f"{field}.field_root_digest") != EXPECTED_FIELD_ROOT_DIGEST:
        _fail(f"{field}.field_root_digest is not frozen")
    _verify_checkpoint(row.get("q1_checkpoint"), lineage=expected_lineage, field=f"{field}.q1_checkpoint")
    parameter = EXPECTED_Q1_CHECKPOINTS[expected_lineage]["parameter_sha256"]
    if _digest(row.get("q1_parameter_sha256_before"), field=f"{field}.q1_parameter_sha256_before") != parameter:
        _fail(f"{field}.q1_parameter_sha256_before is not frozen")
    if _digest(row.get("q1_parameter_sha256_after"), field=f"{field}.q1_parameter_sha256_after") != parameter:
        _fail(f"{field}.q1_parameter_sha256_after is not frozen")

    per_step = _list(row.get("per_step"), field=f"{field}.per_step")
    if len(per_step) != STEPS_PER_EPISODE:
        _fail(f"{field}.per_step must contain ten steps")
    totals_bits = 0.0
    totals_energy = 0.0
    served_total = 0
    exposure_total = 0
    exposed_total = 0
    negative_total = 0
    identity_values: list[bool] = []
    mechanics_values: list[bool] = []
    for index, step in enumerate(per_step):
        bits, energy, served, exposure, exposed, negative = _verify_step(
            step, arm=expected_arm, lineage=expected_lineage, index=index
        )
        totals_bits += bits
        totals_energy += energy
        served_total += served
        exposure_total += exposure
        exposed_total += exposed
        negative_total += negative
        step_mapping = _mapping(step, field=f"{field}.per_step[{index}]")
        identity_values.append(
            expected_arm == "DROP_C3"
            or _bool(
                _mapping(step_mapping["method"], field=f"{field}.per_step[{index}].method").get("identity_passed"),
                field=f"{field}.per_step[{index}].method.identity_passed",
            )
        )
        mechanics_values.append(
            _bool(
                _mapping(step_mapping["mechanics"], field=f"{field}.per_step[{index}].mechanics").get("passed"),
                field=f"{field}.per_step[{index}].mechanics.passed",
            )
        )

    total_bits = _finite_number(row.get("total_bits"), field=f"{field}.total_bits", nonnegative=True)
    total_energy = _finite_number(row.get("total_energy_j"), field=f"{field}.total_energy_j", positive=True)
    ratio = _finite_number(row.get("ratio_of_sums_ee_bits_per_j"), field=f"{field}.ratio_of_sums_ee_bits_per_j", nonnegative=True)
    served = _exact_int(row.get("served_user_steps"), field=f"{field}.served_user_steps", minimum=0)
    fraction = _finite_number(row.get("served_fraction"), field=f"{field}.served_fraction", nonnegative=True)
    spread = _exact_int(row.get("c3_legal_spread_count"), field=f"{field}.c3_legal_spread_count", minimum=0)
    exposure = _exact_int(row.get("action_exposure"), field=f"{field}.action_exposure", minimum=0)
    exposed = _exact_int(row.get("joint_opening_exposed_count"), field=f"{field}.joint_opening_exposed_count", minimum=0)
    negative = _exact_int(row.get("joint_opening_negative_count"), field=f"{field}.joint_opening_negative_count", minimum=0)
    if spread > USERS * STEPS_PER_EPISODE:
        _fail(f"{field}.c3_legal_spread_count exceeds the episode census")
    if exposure > USERS * STEPS_PER_EPISODE:
        _fail(f"{field}.action_exposure exceeds the episode census")
    if exposed > STEPS_PER_EPISODE:
        _fail(f"{field}.joint_opening_exposed_count exceeds the episode")
    method_passed = _bool(row.get("method_passed"), field=f"{field}.method_passed")
    candidate_identity = _bool(row.get("candidate_specific_identity_passed"), field=f"{field}.candidate_specific_identity_passed")
    mechanics_passed = _bool(row.get("mechanics_passed"), field=f"{field}.mechanics_passed")
    _finite_number(row.get("elapsed_s"), field=f"{field}.elapsed_s", nonnegative=True)

    if total_bits != totals_bits or total_energy != totals_energy:
        _fail(f"{field} totals do not equal the ordered per-step totals")
    if served != served_total or exposure != exposure_total:
        _fail(f"{field} service/exposure totals do not equal per-step receipts")
    if exposed != exposed_total or negative != negative_total or negative > exposed:
        _fail(f"{field} joint-opening census does not equal per-step receipts")
    if ratio != total_bits / total_energy:
        _fail(f"{field} ratio_of_sums_ee_bits_per_j is not canonical")
    if fraction != served / (USERS * STEPS_PER_EPISODE):
        _fail(f"{field} served_fraction is not canonical")
    expected_identity = all(identity_values)
    if candidate_identity != expected_identity:
        _fail(f"{field}.candidate_specific_identity_passed disagrees with methods")
    expected_mechanics = all(mechanics_values)
    if mechanics_passed != expected_mechanics:
        _fail(f"{field}.mechanics_passed disagrees with per-step mechanics")
    if method_passed != expected_identity:
        _fail(f"{field}.method_passed disagrees with method identities")
    if expected_arm == "DROP_C3" and not candidate_identity:
        _fail(f"{field} DROP_C3 identity must be true")
    return {
        "arm": expected_arm,
        "initialization_seed": expected_lineage,
        "initial_world_sha256": initial_world,
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": ratio,
        "served_user_steps": served,
        "c3_legal_spread_count": spread,
        "action_exposure": exposure,
        "joint_opening_exposed_count": exposed,
        "joint_opening_negative_count": negative,
        "mechanics_passed": mechanics_passed,
        "method_passed": method_passed,
        "candidate_specific_identity_passed": candidate_identity,
    }


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(rows) != len(LINEAGES):
        _fail("each frozen arm must contain exactly three lineage rows")
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    if not math.isfinite(bits) or not math.isfinite(energy) or energy <= 0.0:
        _fail("pooled EE denominator is not positive and finite")
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_fraction": served / (len(rows) * USERS * STEPS_PER_EPISODE),
    }


def _pair_gate(
    *,
    label: str,
    full_arm: str,
    drop_arm: str,
    rows: Sequence[Mapping[str, Any]],
    pooled: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    by_key = {(str(row["arm"]), int(row["initialization_seed"])): row for row in rows}
    full_pool = pooled[full_arm]
    drop_pool = pooled[drop_arm]
    full_ee = float(full_pool["ratio_of_sums_ee_bits_per_j"])
    drop_ee = float(drop_pool["ratio_of_sums_ee_bits_per_j"])
    by_lineage: dict[str, Any] = {}
    positive = 0
    service_noninferior = 0
    for lineage in LINEAGES:
        full = by_key[(full_arm, lineage)]
        drop = by_key[(drop_arm, lineage)]
        delta = float(full["ratio_of_sums_ee_bits_per_j"]) - float(drop["ratio_of_sums_ee_bits_per_j"])
        service_delta = int(full["served_user_steps"]) - int(drop["served_user_steps"])
        positive += int(delta > 0.0)
        service_noninferior += int(service_delta >= 0)
        by_lineage[str(lineage)] = {
            "delta_ee_bits_per_j": delta,
            "relative_delta_ee": delta / float(drop["ratio_of_sums_ee_bits_per_j"]),
            "delta_served_user_steps": service_delta,
        }

    full_rows = [row for row in rows if row["arm"] == full_arm]
    drop_rows = [row for row in rows if row["arm"] == drop_arm]
    mechanics = all(bool(row["mechanics_passed"]) for row in (*full_rows, *drop_rows))
    method = all(bool(row["method_passed"]) for row in (*full_rows, *drop_rows))
    identity = all(bool(row["candidate_specific_identity_passed"]) for row in (*full_rows, *drop_rows))
    spread = sum(int(row["c3_legal_spread_count"]) for row in full_rows)
    exposure = sum(int(row["action_exposure"]) for row in full_rows)
    joint_exposed = sum(int(row["joint_opening_exposed_count"]) for row in full_rows)
    joint_negative = sum(int(row["joint_opening_negative_count"]) for row in full_rows)
    pooled_service = int(full_pool["served_user_steps"]) >= int(drop_pool["served_user_steps"])
    hard_stops: list[str] = []
    if not mechanics:
        hard_stops.append(f"{label} mechanics failed")
    if not method:
        hard_stops.append(f"{label} method-specific gate failed")
    if not identity:
        hard_stops.append(f"{label} candidate-specific identity gate failed")
    if spread <= 0:
        hard_stops.append(f"{label} has zero legal-action C3 spread")
    if exposure <= 0:
        hard_stops.append(f"{label} has zero executed-action exposure")
    if not full_ee > drop_ee:
        hard_stops.append(f"{label} pooled EE is not strictly positive")
    if positive < 2:
        hard_stops.append(f"{label} has fewer than two positive lineages")
    if not pooled_service:
        hard_stops.append(f"{label} pooled service guard failed")
    if service_noninferior < 2:
        hard_stops.append(f"{label} has fewer than two service-safe lineages")
    if joint_exposed <= 0:
        hard_stops.append(f"{label} has no joint-opening exposure")
    elif 2 * joint_negative > joint_exposed:
        hard_stops.append(f"{label} joint-opening direction is negative in a majority")
    return {
        "label": label,
        "full_arm": full_arm,
        "drop_arm": drop_arm,
        "passed": not hard_stops,
        "pooled": {
            "delta_ee_bits_per_j": full_ee - drop_ee,
            "relative_delta_ee": (full_ee - drop_ee) / drop_ee,
            "delta_served_user_steps": int(full_pool["served_user_steps"]) - int(drop_pool["served_user_steps"]),
        },
        "by_lineage": by_lineage,
        "positive_lineages": positive,
        "service_noninferior_lineages": service_noninferior,
        "pooled_service_noninferior": pooled_service,
        "mechanics_passed": mechanics,
        "method_passed": method,
        "candidate_specific_identity_passed": identity,
        "c3_legal_spread_count": spread,
        "action_exposure": exposure,
        "joint_opening_exposed_count": joint_exposed,
        "joint_opening_negative_count": joint_negative,
        "hard_stops": hard_stops,
    }


def ordered_decision(*, passed_ap: bool, passed_m1d: bool, passed_o: bool) -> str:
    """Apply the preregistered AP-before-M1D selection table."""

    if passed_ap and (passed_m1d or passed_o):
        return "GO_AP_MONE_LEARNABILITY_PREREG_ONLY"
    if (not passed_ap) and passed_m1d:
        return "GO_M1D_LEARNABILITY_PREREG_ONLY"
    if passed_ap and (not passed_m1d) and (not passed_o):
        return "INCONSISTENT_AP_ONLY_NO_LEARNER_REVIEW"
    if (not passed_ap) and (not passed_m1d) and passed_o:
        return "C1_ALIGNMENT_BLOCKS_C3_NO_LEARNER"
    return "JOINT_C3_STRUCTURAL_REDESIGN_REQUIRED"


def _verify_summaries_and_gate(
    payload: Mapping[str, Any],
    *,
    rows: Sequence[Mapping[str, Any]],
    pooled: Mapping[str, Mapping[str, Any]],
    gates: Mapping[str, Mapping[str, Any]],
    decision: str,
) -> None:
    expected_summaries = {"pooled_by_arm": pooled, "candidate_gates": gates}
    if payload.get("summaries") != expected_summaries:
        _fail("result summaries disagree with independently recomputed values")
    expected_gate = {
        "decision": decision,
        "pass_ap": bool(gates["AP"]["passed"]),
        "pass_m1d": bool(gates["M1D"]["passed"]),
        "pass_exact_o": bool(gates["O"]["passed"]),
        "ordered_selection_ap_before_m1d": True,
    }
    if payload.get("gate") != expected_gate:
        _fail("result gate disagrees with independently recomputed ordered decision")


def verify_result(path: Path) -> dict[str, Any]:
    """Verify one completed V0.11 ``result.json`` and return a CLI summary."""

    payload, result_file_sha256 = read_canonical_json(Path(path))
    expected_top_level = {
        "schema",
        "claim_ceiling",
        "contract",
        "contract_sha256",
        "contract_file_sha256",
        "runner_file_sha256",
        "runtime_file_sha256",
        "field_root_digest",
        "initial_world_sha256",
        "rows",
        "summaries",
        "gate",
        "result_sha256",
    }
    if set(payload) != expected_top_level:
        _fail("result fields differ from the frozen result schema")
    if payload.get("schema") != RESULT_SCHEMA:
        _fail("result schema is stale")
    supplied_result_sha = _digest(payload.get("result_sha256"), field="result_sha256")
    body = dict(payload)
    del body["result_sha256"]
    if canonical_sha256(body) != supplied_result_sha:
        _fail("result_sha256 does not match canonical result contents")
    _verify_authority(payload)

    top_initial_world = _digest(payload.get("initial_world_sha256"), field="initial_world_sha256")
    raw_rows = _list(payload.get("rows"), field="rows")
    expected_pairs = [(arm, lineage) for arm in ARMS for lineage in LINEAGES]
    if len(raw_rows) != len(expected_pairs):
        _fail("result must contain exactly 15 rows")
    rows: list[dict[str, Any]] = []
    observed_pairs: list[tuple[str, int]] = []
    for index, raw_row in enumerate(raw_rows):
        expected_arm, expected_lineage = expected_pairs[index]
        verified = _verify_row(
            raw_row,
            expected_arm=expected_arm,
            expected_lineage=expected_lineage,
            world_digest=top_initial_world,
        )
        rows.append(verified)
        observed_pairs.append((expected_arm, expected_lineage))
    if observed_pairs != expected_pairs:
        _fail("result arm/lineage coverage is not the exact frozen order")

    by_arm = {arm: [row for row in rows if row["arm"] == arm] for arm in ARMS}
    if any(len(by_arm[arm]) != len(LINEAGES) for arm in ARMS):
        _fail("result arm/lineage coverage is not exactly 5x3")
    pooled = {arm: _pool(by_arm[arm]) for arm in ARMS}
    gates = {
        "AP": _pair_gate(
            label="AP",
            full_arm="FULL_AP",
            drop_arm="DROP_C3",
            rows=rows,
            pooled=pooled,
        ),
        "M1D": _pair_gate(
            label="M1D",
            full_arm="FULL_M1D",
            drop_arm="DROP_C3",
            rows=rows,
            pooled=pooled,
        ),
        "O": _pair_gate(
            label="O",
            full_arm="DIAG_O_FULL",
            drop_arm="DIAG_O_DROP",
            rows=rows,
            pooled=pooled,
        ),
    }
    decision = ordered_decision(
        passed_ap=bool(gates["AP"]["passed"]),
        passed_m1d=bool(gates["M1D"]["passed"]),
        passed_o=bool(gates["O"]["passed"]),
    )
    _verify_summaries_and_gate(
        payload, rows=rows, pooled=pooled, gates=gates, decision=decision
    )
    return {
        "status": "PASS",
        "schema": RESULT_SCHEMA,
        "result_sha256": supplied_result_sha,
        "result_file_sha256": result_file_sha256,
        "rows": len(rows),
        "decision": decision,
        "pass_ap": bool(gates["AP"]["passed"]),
        "pass_m1d": bool(gates["M1D"]["passed"]),
        "pass_exact_o": bool(gates["O"]["passed"]),
    }


# A short alias is useful to callers and keeps the CLI implementation thin.
verify = verify_result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="completed V0.11 result.json")
    args = parser.parse_args(argv)
    try:
        summary = verify_result(args.result)
    except (OSError, V011ResultVerificationError, KeyError, TypeError, ValueError) as error:
        print(f"V011 RESULT VERIFY FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
