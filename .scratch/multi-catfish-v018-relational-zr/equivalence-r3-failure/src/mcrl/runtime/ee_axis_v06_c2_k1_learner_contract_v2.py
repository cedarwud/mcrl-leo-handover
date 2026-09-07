"""Result-blind V0.6 C2-k1 bounded learner contract (v2).

This module is deliberately independent of ``ee_axis_v06_c2_k1_learner_prep``.
It freezes the post-T1 learner choices in one exact JSON-shaped plan and
provides a read-only, fail-closed boundary for the later T1 formal verdict.

The verdict boundary accepts *paths* to an authenticated artifact and its
write-once seal.  It never accepts a caller-supplied disposition string and
it never writes a verdict, a source result, a checkpoint, or a learner
artifact.  The source payload is checked only when this boundary is invoked;
this keeps contract preparation result-blind while T1 remains unopened.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from ..env.action_contract import NUM_ACTIONS
from .ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)


# ---------------------------------------------------------------------------
# Frozen plan constants
# ---------------------------------------------------------------------------

LEARNER_PLAN_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-bounded-learner-plan-v2"
FORMAL_VERDICT_ARTIFACT_SCHEMA = (
    "multi-catfish-mcrl-v06-c2-k1-t1-formal-verdict-v2"
)
FORMAL_VERDICT_SEAL_SCHEMA = (
    "multi-catfish-mcrl-v06-c2-k1-t1-formal-verdict-seal-v2"
)
T1_SOURCE_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-source-v1"
T1_SOURCE_SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-source-seal-v1"
T1_ALGORITHM_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-v1"
T1_SOURCE_RULE = "c2-k1-total-policy-effect-branch-local-v1"

FORMAL_LEARNER_VERDICT = "AUTHORIZE_ONE_BOUNDED_C2_K1_LEARNER_SCREEN"
SOURCE_FALSIFIED_VERDICT = "C2_K1_SOURCE_FALSIFIED_NO_TRAINING"
INVALID_T1_VERDICT = "T1_INVALID_NO_TRAINING"

CLAIM_CEILING = "BOUNDED_Q2_LEARNER_SCREEN_ONLY_NO_TEST_NO_CH5_NO_LONG_TRAINING"
LEARNER_SCOPE = "one-bounded-c2-k1-q2-only"

LINEAGES = ("q13-a", "q13-b", "q13-c")
Q13_INITIALIZATION_SEEDS = (2026092101, 2026092102, 2026092103)
Q2_INITIALIZATION_SEEDS = (2026102101, 2026102102, 2026102103)
Q2_SEEDS_BY_LINEAGE = dict(zip(LINEAGES, Q2_INITIALIZATION_SEEDS, strict=True))
Q2_UPDATE0_PARAMETER_SHA256 = {
    "q13-a": "502a1c13f840d21d94730ec2502eb2a9384294dc26f938c233a28a24b2c441a6",
    "q13-b": "050ac3b794f4db81748b464fd0a4eecd0c228cab5572d839e53bb5b9b673fd4e",
    "q13-c": "da4abd36fe154c240839df89560c504ec95458df221c408f312144bf05cb47d7",
}
T1_PREREG_FILE_SHA256 = (
    "e9fe8e83ba01f99076ce435b2499ae919cabbf55659433549a6a576e7a6c065f"
)
Q2_CLASS = "mcrl.algorithms.ee_axis_v06_c2_k1.EEAxisV06C2K1Trainer"
DESIGN_EVAL_FIELD_COMPONENT = (
    "multi-catfish-mcrl-v06-c2-k1-design-eval-field-v1"
)

STATE_DIM = EE_AXIS_STATE_DIM
ACTION_DIM = NUM_ACTIONS
HIDDEN_WIDTHS = (100, 50, 50)
ACTIVATION = "tanh"

KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
KAPPA_BITS_HEX = KAPPA_BITS.hex()
BETA = float.fromhex("0x1.999999999999ap-4")
BETA_HEX = BETA.hex()

# JSON lists are intentional here: this mapping is embedded verbatim in the
# machine-readable plan and has no tuple/NumPy representation ambiguity.
ADAM_PARAMETERS: dict[str, Any] = {
    "name": "Adam",
    "lr": 0.001,
    "betas": [0.9, 0.999],
    "eps": 1e-8,
    "weight_decay": 0.0,
    "amsgrad": False,
}

WORLD_COUNT = 12
ROWS_PER_LINEAGE = WORLD_COUNT * ACTION_DIM
TOTAL_SOURCE_ROWS = ROWS_PER_LINEAGE * len(LINEAGES)
TRAINING_STEPS = 100
TRAINING_CHECKPOINTS = (0, 100)
DESIGN_EVAL_SEEDS = tuple(range(2026103001, 2026103011))
DESIGN_EVAL_STEPS = 10
DESIGN_EVAL_USERS = 100
DESIGN_EVAL_ARMS = ("FULL", "DROP_C2")
FROZEN_FREEZE_ROOT_RELATIVE = (
    "artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze"
)


class C2K1LearnerContractV2Error(ValueError):
    """The v2 plan or authenticated formal-verdict bundle is inadmissible."""


def canonical_bytes(payload: object) -> bytes:
    """Return the only accepted on-disk JSON encoding for contract files."""

    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise C2K1LearnerContractV2Error(
            "payload is not canonical finite JSON"
        ) from error
    return encoded + b"\n"


def canonical_sha256(payload: object) -> str:
    """Hash the canonical payload, excluding its file-format newline.

    This matches the frozen T1 runner's ``canonical_sha256`` semantics.  File
    SHA-256 values still include the terminal newline written on disk.
    """

    return hashlib.sha256(canonical_bytes(payload)[:-1]).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C2K1LearnerContractV2Error(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise C2K1LearnerContractV2Error(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _exact_bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise C2K1LearnerContractV2Error(f"{field} must be Boolean")
    return value


def _reject_forbidden_keys(value: Mapping[str, Any], *, field: str) -> None:
    forbidden = sorted(set(value) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise C2K1LearnerContractV2Error(
            f"{field} contains forbidden target/outcome fields: {forbidden}"
        )


def _path(value: object, *, field: str) -> Path:
    """Resolve an absolute path while rejecting symlinks and non-files."""

    if not isinstance(value, (str, os.PathLike)):
        raise C2K1LearnerContractV2Error(
            f"{field} must be a filesystem path, not a verdict literal"
        )
    try:
        candidate = Path(value)
    except (TypeError, ValueError, OSError) as error:
        raise C2K1LearnerContractV2Error(f"{field} is not a valid path") from error
    if not candidate.is_absolute():
        raise C2K1LearnerContractV2Error(f"{field} must be an absolute path")
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as error:
        raise C2K1LearnerContractV2Error(f"{field} cannot be resolved") from error
    if candidate.is_symlink() or resolved.is_symlink():
        raise C2K1LearnerContractV2Error(f"{field} must not be a symlink")
    if not resolved.is_file():
        raise C2K1LearnerContractV2Error(f"{field} must name a regular file")
    return resolved


def _file_sha256(path: Path, *, field: str) -> str:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise C2K1LearnerContractV2Error(f"cannot read {field}") from error
    return hashlib.sha256(raw).hexdigest()


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in pairs:
        if key in result:
            raise C2K1LearnerContractV2Error(f"duplicate JSON key: {key}")
        result[key] = item
    return result


def _read_canonical_json(value: object, *, field: str) -> tuple[Path, dict[str, Any], str]:
    path = _path(value, field=field)
    try:
        raw = path.read_bytes()
        parsed = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            object_pairs_hook=_no_duplicate_object,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise C2K1LearnerContractV2Error(f"{field} is not valid canonical JSON") from error
    if not isinstance(parsed, dict) or raw != canonical_bytes(parsed):
        raise C2K1LearnerContractV2Error(f"{field} is not canonical JSON")
    return path, parsed, hashlib.sha256(raw).hexdigest()


_FORBIDDEN_FIELDS = frozenset(
    {
        "target",
        "target_surplus_bits",
        "z2",
        "z2_k1_bits",
        "z2_k1_normalized",
        "outcome",
        "outcomes",
        "metrics",
        "ee",
        "oracle",
        "drop",
        "rates",
        "power",
        "served",
        "partial",
        "result",
    }
)


# ---------------------------------------------------------------------------
# Exact machine-readable learner plan
# ---------------------------------------------------------------------------


def _plan_body() -> dict[str, Any]:
    return {
        "schema": LEARNER_PLAN_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "scope": LEARNER_SCOPE,
        "authorization": {
            "artifact_schema": FORMAL_VERDICT_ARTIFACT_SCHEMA,
            "seal_schema": FORMAL_VERDICT_SEAL_SCHEMA,
            "source_schema": T1_SOURCE_SCHEMA,
            "required_disposition": FORMAL_LEARNER_VERDICT,
            "artifact_path_required": True,
            "seal_path_required": True,
            "artifact_directory": "freeze/formal-verdict",
            "source_path_binding_required": True,
            "caller_literal_accepted": False,
        },
        "lineages": [
            {
                "lineage": lineage,
                "q13_initialization_seed": q13_seed,
                "q2_initialization_seed": q2_seed,
                "q2_update0_parameter_sha256": Q2_UPDATE0_PARAMETER_SHA256[
                    lineage
                ],
            }
            for lineage, q13_seed, q2_seed in zip(
                LINEAGES,
                Q13_INITIALIZATION_SEEDS,
                Q2_INITIALIZATION_SEEDS,
                strict=True,
            )
        ],
        "state": {
            "schema": EE_AXIS_STATE_SCHEMA,
            "schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
            "dimension": STATE_DIM,
            "dtype": "float32",
            "action_dim": ACTION_DIM,
        },
        "q2_architecture": {
            "name": "MaskedMeanMax",
            "class": Q2_CLASS,
            "hidden_widths": list(HIDDEN_WIDTHS),
            "activation": ACTIVATION,
            "construction": (
                "torch.manual_seed(q2_seed); immediately instantiate exactly "
                "one MaskedMeanMaxQNetwork"
            ),
            "resident_legacy_q2_retained_in_authenticated_hybrid_container": True,
            "resident_legacy_q2_excluded_from_training_and_decision_path": True,
            "resident_legacy_q2_evaluated_or_summed": False,
        },
        "optimizer": dict(ADAM_PARAMETERS),
        "target_scale": {
            "kappa_bits": KAPPA_BITS,
            "kappa_bits_hex": KAPPA_BITS_HEX,
        },
        "gauge": {"beta": BETA, "beta_hex": BETA_HEX},
        "loss": {
            "formula": (
                "mean((Q2(s,aC)-Q2(s,aM)-zeta2/kappa)^2)"
                "+beta*mean(Q2(s,aM)^2)"
            ),
            "q2_weight": 1.0,
            "config_loss_weights": [1.0, 1.0, 1.0],
            "reference_action": "frozen_Main_opening_action",
            "retain_reference_equals_reference": True,
            "bellman_bootstrap": False,
            "target_network": False,
            "legacy_reward": False,
            "target_clipping": False,
            "route_weight": False,
            "cross_lineage_target_pooling": False,
        },
        "batch": {
            "worlds": WORLD_COUNT,
            "actions": ACTION_DIM,
            "rows_per_lineage": ROWS_PER_LINEAGE,
            "total_rows": TOTAL_SOURCE_ROWS,
            "mode": "full_batch",
            "order": "prepare_anchor_order_then_action_0_to_27",
            "shuffle": False,
            "replacement": False,
            "sign_filter": False,
        },
        "execution": {
            "freeze_root_relative": FROZEN_FREEZE_ROOT_RELATIVE,
            "single_global_freeze_root": True,
            "train_output_rule": "freeze/train-{lineage}",
            "design_eval_output_rule": "freeze/design-eval",
            "no_alternate_root": True,
        },
        "training": {
            "steps": TRAINING_STEPS,
            "checkpoints": list(TRAINING_CHECKPOINTS),
            "primary_checkpoint": 100,
            "device": "cpu",
            "deterministic": True,
            "torch_deterministic_algorithms": True,
            "torch_num_threads": 1,
            "update0_parameter_digests_sealed_pre_reveal": True,
            "output_path_rule": "freeze/train-{lineage}",
            "attempt_sealed_before_first_optimizer": True,
        },
        "design_eval": {
            "seeds": list(DESIGN_EVAL_SEEDS),
            "seed_count": len(DESIGN_EVAL_SEEDS),
            "label": "DESIGN-EVAL",
            "not_test": True,
            "steps": DESIGN_EVAL_STEPS,
            "users": DESIGN_EVAL_USERS,
            "arms": list(DESIGN_EVAL_ARMS),
            "common_safe_mask": True,
            "matched_keyed_exogenous_random_field": True,
            "keyed_field_component": DESIGN_EVAL_FIELD_COMPONENT,
            "keyed_field_root": [
                "simulator_source_manifest_sha256",
                "main_checkpoint_sha256",
                "simulator_prereg_file_sha256",
                "physical_design_eval_seed",
            ],
            "independent_branch_states": True,
            "route_state_inputs": {
                "Q1": "V0.3 causal 228-D state",
                "Q2": "V0.3 causal 228-D state",
                "Q3": "V0.4 C3 228-D state",
            },
            "resident_legacy_q2_retained_in_authenticated_hybrid_container": True,
            "resident_legacy_q2_evaluated_or_summed": False,
            "output_path_rule": "freeze/design-eval",
            "attempt_sealed_before_first_seed": True,
            "action_rules": {
                "FULL": "argmax_masked(Q1+Q2+Q3)",
                "DROP_C2": "argmax_masked(Q1+Q3)",
            },
            "tie_rule": "lowest_legal_action_index_numpy_argmax",
            "empty_mask_rule": "NO_OP=-1_and_do_not_evaluate_Q2",
            "no_action_tape": True,
            "no_cross_branch_action_import": True,
            "no_repair_or_override": True,
        },
        "gates": {
            "G-L": {
                "all_required": True,
                "formal_verdict": "exact_authenticated_artifact",
                "source_rows": TOTAL_SOURCE_ROWS,
                "rows_per_lineage": ROWS_PER_LINEAGE,
                "optimizer_steps": TRAINING_STEPS,
                "finite_all_steps": True,
                "q1_q3_byte_identical": True,
                "q1_q3_receive_no_gradient": True,
                "checkpoints_exact": list(TRAINING_CHECKPOINTS),
                "reload_primary_checkpoint": 100,
                "no_test_or_partial_source": True,
                "no_outcome_selection": True,
                "no_retry_replacement_or_extra_arm": True,
                "single_global_freeze_root": True,
                "simulator_baseline_and_extensions_authenticated": True,
                "formal_verifier_matches_prepare_code_authority": True,
                "resident_legacy_q2_evaluated_or_summed": False,
                "drop_c2_reproduces_prepare_q13_scores_and_a_D": {
                    "anchors": 12,
                    "lineages": 3,
                    "cells": 36,
                    "exact": True,
                    "before_design_eval": True,
                },
            },
            "G-E": {
                "statistic": "raw_pooled_ratio_of_sums_ee",
                "full_strictly_gt_drop_c2": True,
                "positive_lineage_contrasts_min": 2,
                "positive_world_contrasts_min": 7,
                "physical_world_count": len(DESIGN_EVAL_SEEDS),
                "independent_unit": "physical_world",
                "zero_is_not_positive": True,
            },
            "G-S": {
                "pooled_full_served_fraction_not_below_drop_c2": True,
                "nonnegative_lineage_contrasts_min": 2,
                "service_is_separate_guard": True,
                "no_second_rate_mask": True,
            },
        },
        "q1_q3_frozen": True,
        "q2_only_updates": True,
        "t1_prereg_file_sha256": T1_PREREG_FILE_SHA256,
        "support_limit": {
            "distinct_training_states": 12,
            "training_masks": "complete_28_action_only",
            "deployment_may_use_partial_masks": True,
            "failure_attribution_is_not_identified": True,
        },
        "diagnostics": {
            "q2_surface_median_abs": True,
            "q13_surface_median_abs": True,
            "q2_to_q13_magnitude": True,
            "complete_28_action_support_fraction": True,
            "cannot_rescue_or_veto_gates": True,
        },
        "hyperparameters_bound": True,
        "training_started": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "no_9000ep": True,
        "retry_policy": "single_screen_exhausted_on_valid_failure",
    }


_PLAN_BODY = _plan_body()
_LEARNER_PLAN_V2 = dict(_PLAN_BODY, plan_sha256=canonical_sha256(_PLAN_BODY))
_PLAN_FIELDS = frozenset(_LEARNER_PLAN_V2)


def learner_plan_v2() -> dict[str, Any]:
    """Return a mutable copy of the exact v2 plan with its payload digest."""

    # JSON round-tripping gives callers ordinary lists/dicts while ensuring
    # they cannot mutate the module-level contract object.
    return json.loads(canonical_bytes(_LEARNER_PLAN_V2).decode("ascii"))


def verify_learner_plan_v2(payload: Mapping[str, Any]) -> str:
    """Verify exact fields and digest of the machine-readable learner plan."""

    if not isinstance(payload, Mapping):
        raise C2K1LearnerContractV2Error("learner plan must be a mapping")
    _reject_forbidden_keys(payload, field="learner plan")
    unknown = set(payload) - _PLAN_FIELDS
    missing = _PLAN_FIELDS - set(payload)
    if unknown:
        raise C2K1LearnerContractV2Error(
            f"learner plan contains unknown fields: {sorted(unknown)}"
        )
    if missing:
        raise C2K1LearnerContractV2Error(
            f"learner plan is missing fields: {sorted(missing)}"
        )
    plan_digest = _digest(payload.get("plan_sha256"), field="plan_sha256")
    unsigned = dict(payload)
    unsigned.pop("plan_sha256", None)
    if canonical_sha256(unsigned) != plan_digest:
        raise C2K1LearnerContractV2Error(
            "learner plan digest disagrees with payload"
        )
    if dict(payload) != _LEARNER_PLAN_V2:
        raise C2K1LearnerContractV2Error(
            "learner plan does not match the exact bounded v2 contract"
        )
    return plan_digest


# ---------------------------------------------------------------------------
# Authenticated formal-verdict bundle
# ---------------------------------------------------------------------------


_ARTIFACT_FIELDS = frozenset(
    {
        "schema",
        "status",
        "disposition",
        "source_schema",
        "source_seal_schema",
        "source_path",
        "source_file_sha256",
        "source_payload_sha256",
        "source_seal_path",
        "source_seal_file_sha256",
        "prepare_sha256",
        "t1_prereg_file_sha256",
        "verifier_code_authority_sha256",
        "counts",
        "gates",
        "training",
        "test_split_opened",
        "outcome_selection",
        "q2_consulted",
        "write_once",
        "attempt",
        "retry",
        "replacement",
        "verdict_sha256",
    }
)
_SEAL_FIELDS = frozenset(
    {
        "schema",
        "verdict_sha256",
        "verdict_file_sha256",
        "verdict_path",
        "source_path",
        "source_file_sha256",
        "source_seal_path",
        "source_seal_file_sha256",
        "prepare_sha256",
        "t1_prereg_file_sha256",
        "verifier_code_authority_sha256",
        "write_once",
        "attempt",
        "retry",
        "replacement",
        "training",
        "test_split_opened",
        "outcome_selection",
        "q2_consulted",
    }
)
_SOURCE_SEAL_FIELDS = frozenset(
    {
        "schema",
        "source_sha256",
        "source_file_sha256",
        "prepare_sha256",
        "training",
        "test_split_opened",
        "outcome_selection",
    }
)


def _validate_target_free_flags(payload: Mapping[str, Any], *, field: str) -> None:
    for name in (
        "training",
        "test_split_opened",
        "outcome_selection",
        "q2_consulted",
    ):
        _exact_bool(payload.get(name), field=f"{field}.{name}")
        if payload[name] is not False:
            raise C2K1LearnerContractV2Error(
                f"{field}.{name} must remain false at the T1 learner boundary"
            )


def _validate_write_once(payload: Mapping[str, Any], *, field: str) -> None:
    if payload.get("write_once") is not True:
        raise C2K1LearnerContractV2Error(f"{field} is not write-once")
    if payload.get("attempt") != 1:
        raise C2K1LearnerContractV2Error(f"{field}.attempt must be exactly one")
    if payload.get("retry") is not False:
        raise C2K1LearnerContractV2Error(f"{field}.retry must be false")
    if payload.get("replacement") is not False:
        raise C2K1LearnerContractV2Error(f"{field}.replacement must be false")


def _validate_gate_shape(gates: object, *, field: str) -> dict[str, Any]:
    if not isinstance(gates, Mapping):
        raise C2K1LearnerContractV2Error(f"{field} must be a mapping")
    required = {"G-M", "G-E", "G-S", "launchable"}
    if set(gates) != required:
        raise C2K1LearnerContractV2Error(f"{field} has an unexpected gate schema")
    normalized: dict[str, Any] = {}
    for gate in ("G-M", "G-E", "G-S"):
        value = gates[gate]
        if not isinstance(value, Mapping) or type(value.get("passed")) is not bool:
            raise C2K1LearnerContractV2Error(f"{field}.{gate}.passed is malformed")
        normalized[gate] = dict(value)
    if type(gates["launchable"]) is not bool:
        raise C2K1LearnerContractV2Error(f"{field}.launchable is malformed")
    normalized["launchable"] = gates["launchable"]
    expected_launchable = all(normalized[gate]["passed"] for gate in ("G-M", "G-E", "G-S"))
    if normalized["launchable"] is not expected_launchable:
        raise C2K1LearnerContractV2Error(f"{field}.launchable disagrees with gates")
    return normalized


def _validate_source_payload(
    source: Mapping[str, Any],
    *,
    source_path: Path,
    source_file_sha256: str,
    source_seal: Mapping[str, Any],
    source_seal_path: Path,
    source_seal_file_sha256: str,
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the future T1 source chain without selecting any outcome."""

    _reject_forbidden_keys(source, field="source")
    if source.get("schema") != T1_SOURCE_SCHEMA:
        raise C2K1LearnerContractV2Error("source schema is not the frozen T1 source")
    if source.get("algorithm_schema") != T1_ALGORITHM_SCHEMA:
        raise C2K1LearnerContractV2Error("source algorithm schema is stale")
    if source.get("source_rule") != T1_SOURCE_RULE:
        raise C2K1LearnerContractV2Error("source rule is stale")
    _validate_target_free_flags(source, field="source")
    source_digest = _digest(source.get("source_sha256"), field="source.source_sha256")
    unsigned = dict(source)
    unsigned.pop("source_sha256", None)
    if canonical_sha256(unsigned) != source_digest:
        raise C2K1LearnerContractV2Error("source payload digest is stale")
    counts = source.get("counts")
    if counts != {
        "anchors": WORLD_COUNT,
        "lineages": len(LINEAGES),
        "opening_actions": ACTION_DIM,
        "pairs": TOTAL_SOURCE_ROWS,
        "controls": 36,
    }:
        raise C2K1LearnerContractV2Error("source cardinality is not 1008 pairs and 36 controls")
    gates = _validate_gate_shape(source.get("gates"), field="source.gates")
    if gates["G-M"]["passed"] is not True:
        raise C2K1LearnerContractV2Error("source G-M mechanics gate did not pass")

    if source.get("prepare_sha256") != artifact.get("prepare_sha256"):
        raise C2K1LearnerContractV2Error("source prepare authority drifted")
    if artifact.get("source_file_sha256") != source_file_sha256:
        raise C2K1LearnerContractV2Error("source file digest drifted")
    if artifact.get("source_payload_sha256") != source_digest:
        raise C2K1LearnerContractV2Error("source payload authority drifted")
    if artifact.get("gates") != gates:
        raise C2K1LearnerContractV2Error("formal verdict gates drifted from source")

    if set(source_seal) != _SOURCE_SEAL_FIELDS:
        raise C2K1LearnerContractV2Error("source seal schema is not exact")
    if source_seal.get("schema") != T1_SOURCE_SEAL_SCHEMA:
        raise C2K1LearnerContractV2Error("source seal schema is stale")
    if source_seal.get("source_sha256") != canonical_sha256(source):
        raise C2K1LearnerContractV2Error("source seal payload digest is invalid")
    if source_seal.get("source_file_sha256") != source_file_sha256:
        raise C2K1LearnerContractV2Error("source seal file digest is invalid")
    if source_seal.get("prepare_sha256") != source.get("prepare_sha256"):
        raise C2K1LearnerContractV2Error("source seal prepare authority drifted")
    _validate_target_free_flags(
        {**source_seal, "q2_consulted": False},
        field="source seal",
    )
    if artifact.get("source_seal_file_sha256") != source_seal_file_sha256:
        raise C2K1LearnerContractV2Error("source seal file digest drifted")

    return {
        "source_path": str(source_path),
        "source_seal_path": str(source_seal_path),
        "source_file_sha256": source_file_sha256,
        "source_payload_sha256": source_digest,
        "source_seal_file_sha256": source_seal_file_sha256,
        "prepare_sha256": str(source["prepare_sha256"]),
        "gates": gates,
        "counts": {"pairs": TOTAL_SOURCE_ROWS, "controls": 36},
    }


def verify_authenticated_formal_verdict(
    formal_verdict_artifact_path: str | os.PathLike[str],
    formal_verdict_seal_path: str | os.PathLike[str],
    *,
    expected_source_path: str | os.PathLike[str] | None = None,
    expected_source_seal_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Authenticate one write-once T1 verdict artifact and its source chain.

    ``formal_verdict_artifact_path`` and ``formal_verdict_seal_path`` are the
    only verdict input.  In particular, this function has no ``verdict`` or
    ``disposition`` argument, so a caller cannot smuggle an authorization
    literal around the artifact/seal boundary.
    """

    artifact_path, artifact, artifact_file_sha256 = _read_canonical_json(
        formal_verdict_artifact_path,
        field="formal verdict artifact path",
    )
    seal_path, seal, _seal_file_sha256 = _read_canonical_json(
        formal_verdict_seal_path,
        field="formal verdict seal path",
    )
    _reject_forbidden_keys(artifact, field="formal verdict artifact")
    _reject_forbidden_keys(seal, field="formal verdict seal")
    if set(artifact) != _ARTIFACT_FIELDS:
        raise C2K1LearnerContractV2Error(
            "formal verdict artifact schema is not exact"
        )
    if set(seal) != _SEAL_FIELDS:
        raise C2K1LearnerContractV2Error("formal verdict seal schema is not exact")
    if artifact.get("schema") != FORMAL_VERDICT_ARTIFACT_SCHEMA:
        raise C2K1LearnerContractV2Error("formal verdict artifact schema is stale")
    if seal.get("schema") != FORMAL_VERDICT_SEAL_SCHEMA:
        raise C2K1LearnerContractV2Error("formal verdict seal schema is stale")
    if artifact.get("status") != "VERIFIED":
        raise C2K1LearnerContractV2Error("formal verdict artifact is not VERIFIED")
    if artifact.get("source_schema") != T1_SOURCE_SCHEMA:
        raise C2K1LearnerContractV2Error("formal verdict source schema is stale")
    if artifact.get("source_seal_schema") != T1_SOURCE_SEAL_SCHEMA:
        raise C2K1LearnerContractV2Error("formal verdict source seal schema is stale")
    _validate_target_free_flags(artifact, field="formal verdict artifact")
    _validate_target_free_flags(seal, field="formal verdict seal")
    _validate_write_once(artifact, field="formal verdict artifact")
    _validate_write_once(seal, field="formal verdict seal")

    disposition = artifact.get("disposition")
    if disposition not in {FORMAL_LEARNER_VERDICT, SOURCE_FALSIFIED_VERDICT}:
        raise C2K1LearnerContractV2Error(
            "formal verdict disposition is not a permitted exact T1 verdict"
        )
    _digest(artifact.get("prepare_sha256"), field="formal verdict prepare_sha256")
    t1_prereg_file_sha256 = _digest(
        artifact.get("t1_prereg_file_sha256"),
        field="formal verdict t1_prereg_file_sha256",
    )
    verifier_code_authority_sha256 = _digest(
        artifact.get("verifier_code_authority_sha256"),
        field="formal verdict verifier_code_authority_sha256",
    )
    artifact_digest = _digest(
        artifact.get("verdict_sha256"),
        field="formal verdict artifact.verdict_sha256",
    )
    unsigned_artifact = dict(artifact)
    unsigned_artifact.pop("verdict_sha256", None)
    if canonical_sha256(unsigned_artifact) != artifact_digest:
        raise C2K1LearnerContractV2Error(
            "formal verdict artifact digest is stale"
        )
    if seal.get("verdict_sha256") != artifact_digest:
        raise C2K1LearnerContractV2Error("formal verdict seal digest is invalid")
    if seal.get("verdict_file_sha256") != artifact_file_sha256:
        raise C2K1LearnerContractV2Error("formal verdict seal file digest is invalid")
    if seal.get("verdict_path") != str(artifact_path):
        raise C2K1LearnerContractV2Error("formal verdict seal path drifted")

    source_path, source, source_file_sha256 = _read_canonical_json(
        artifact.get("source_path"),
        field="formal verdict source path",
    )
    source_seal_path, source_seal, source_seal_file_sha256 = _read_canonical_json(
        artifact.get("source_seal_path"),
        field="formal verdict source seal path",
    )
    if artifact.get("source_path") != str(source_path):
        raise C2K1LearnerContractV2Error("formal verdict source path is not canonical")
    if artifact.get("source_seal_path") != str(source_seal_path):
        raise C2K1LearnerContractV2Error("formal verdict source seal path is not canonical")
    if (
        expected_source_path is not None
        and _path(expected_source_path, field="expected source path") != source_path
    ):
        raise C2K1LearnerContractV2Error("expected source path drifted")
    if (
        expected_source_seal_path is not None
        and _path(expected_source_seal_path, field="expected source seal path")
        != source_seal_path
    ):
        raise C2K1LearnerContractV2Error("expected source seal path drifted")
    source_receipt = _validate_source_payload(
        source,
        source_path=source_path,
        source_file_sha256=source_file_sha256,
        source_seal=source_seal,
        source_seal_path=source_seal_path,
        source_seal_file_sha256=source_seal_file_sha256,
        artifact=artifact,
    )
    for field in (
        "source_path",
        "source_file_sha256",
        "source_seal_path",
        "source_seal_file_sha256",
        "prepare_sha256",
        "t1_prereg_file_sha256",
        "verifier_code_authority_sha256",
    ):
        if seal.get(field) != artifact.get(field):
            raise C2K1LearnerContractV2Error(
                f"formal verdict seal {field} drifted"
            )
    if artifact.get("counts") != source_receipt["counts"]:
        raise C2K1LearnerContractV2Error("formal verdict counts drifted from source")

    launchable = source_receipt["gates"]["launchable"]
    if (disposition == FORMAL_LEARNER_VERDICT) != launchable:
        raise C2K1LearnerContractV2Error(
            "formal verdict disposition disagrees with source gates"
        )

    return {
        "schema": FORMAL_VERDICT_ARTIFACT_SCHEMA,
        "status": "VERIFIED",
        "disposition": disposition,
        "verdict_sha256": artifact_digest,
        "verdict_file_sha256": artifact_file_sha256,
        "verdict_path": str(artifact_path),
        "t1_prereg_file_sha256": t1_prereg_file_sha256,
        "verifier_code_authority_sha256": verifier_code_authority_sha256,
        **source_receipt,
        "formal_verdict_seal_path": str(seal_path),
    }


def check_postgate_learner_plan(
    plan: Mapping[str, Any],
    *,
    formal_verdict_artifact_path: str | os.PathLike[str],
    formal_verdict_seal_path: str | os.PathLike[str],
    expected_source_path: str | os.PathLike[str] | None = None,
    expected_source_seal_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Authorize the exact v2 plan only from an authenticated verdict bundle."""

    plan_digest = verify_learner_plan_v2(plan)
    receipt = verify_authenticated_formal_verdict(
        formal_verdict_artifact_path,
        formal_verdict_seal_path,
        expected_source_path=expected_source_path,
        expected_source_seal_path=expected_source_seal_path,
    )
    if receipt["disposition"] != FORMAL_LEARNER_VERDICT:
        raise C2K1LearnerContractV2Error(
            "bounded learner screen requires the exact authenticated authorization verdict"
        )
    if receipt["t1_prereg_file_sha256"] != plan["t1_prereg_file_sha256"]:
        raise C2K1LearnerContractV2Error(
            "formal verdict T1 preregistration authority drifted from learner plan"
        )
    return {
        "schema": LEARNER_PLAN_SCHEMA,
        "plan_sha256": plan_digest,
        "formal_verdict": FORMAL_LEARNER_VERDICT,
        "formal_verdict_sha256": receipt["verdict_sha256"],
        "formal_verdict_artifact_path": receipt["verdict_path"],
        "formal_verdict_seal_path": receipt["formal_verdict_seal_path"],
        "verifier_code_authority_sha256": receipt[
            "verifier_code_authority_sha256"
        ],
        "source_path": receipt["source_path"],
        "accepted": True,
        "training_started": False,
        "hyperparameters_bound": True,
        "test_split_opened": False,
    }


# Explicit aliases make the seam discoverable to launchers without adding a
# second implementation or a caller-string compatibility path.
verify_formal_verdict_artifact = verify_authenticated_formal_verdict
check_postgate_learner_plan_v2 = check_postgate_learner_plan
authorize_bounded_learner_screen = check_postgate_learner_plan


__all__ = [
    "ACTION_DIM",
    "ACTIVATION",
    "ADAM_PARAMETERS",
    "BETA",
    "BETA_HEX",
    "C2K1LearnerContractV2Error",
    "CLAIM_CEILING",
    "DESIGN_EVAL_ARMS",
    "DESIGN_EVAL_FIELD_COMPONENT",
    "DESIGN_EVAL_SEEDS",
    "DESIGN_EVAL_STEPS",
    "DESIGN_EVAL_USERS",
    "FORMAL_LEARNER_VERDICT",
    "FORMAL_VERDICT_ARTIFACT_SCHEMA",
    "FORMAL_VERDICT_SEAL_SCHEMA",
    "FROZEN_FREEZE_ROOT_RELATIVE",
    "HIDDEN_WIDTHS",
    "INVALID_T1_VERDICT",
    "KAPPA_BITS",
    "KAPPA_BITS_HEX",
    "LEARNER_PLAN_SCHEMA",
    "LEARNER_SCOPE",
    "LINEAGES",
    "Q13_INITIALIZATION_SEEDS",
    "Q2_INITIALIZATION_SEEDS",
    "Q2_CLASS",
    "Q2_SEEDS_BY_LINEAGE",
    "Q2_UPDATE0_PARAMETER_SHA256",
    "ROWS_PER_LINEAGE",
    "SOURCE_FALSIFIED_VERDICT",
    "T1_ALGORITHM_SCHEMA",
    "T1_PREREG_FILE_SHA256",
    "T1_SOURCE_RULE",
    "STATE_DIM",
    "T1_SOURCE_SCHEMA",
    "T1_SOURCE_SEAL_SCHEMA",
    "TOTAL_SOURCE_ROWS",
    "TRAINING_CHECKPOINTS",
    "TRAINING_STEPS",
    "authorize_bounded_learner_screen",
    "canonical_bytes",
    "canonical_sha256",
    "check_postgate_learner_plan",
    "check_postgate_learner_plan_v2",
    "learner_plan_v2",
    "verify_authenticated_formal_verdict",
    "verify_formal_verdict_artifact",
    "verify_learner_plan_v2",
]
