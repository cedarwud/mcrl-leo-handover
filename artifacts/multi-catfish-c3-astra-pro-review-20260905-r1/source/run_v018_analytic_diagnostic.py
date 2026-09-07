#!/usr/bin/env python3
"""V0.18 matched three-arm analytic C3 diagnostic.

This runner is deliberately a *gate*, not a trainer.  It reuses the frozen
Q1 head and the learned OPS-3 Q2 checkpoints from V0.15, and evaluates three
paired arms on fresh TRAIN worlds:

``BASE``
    one native masked argmax of ``Q1 + Q2``;
``EXACT_ZR``
    the same argmax with the existing exact zero-marginal C3 surface;
``NOMINAL_ZR``
    the same argmax with the parameter-free relational nominal C3 surface.

Every arm gets one environment and one common keyed-fading field per world.
The exact surface is measured in BASE and NOMINAL only for the predecision
compatibility proof; it is never added to those arms' action scores.  There
is no learner update, episode training, TEST split, coordinator, or override.

The executable contract remains intentionally frozen outside this file.  The
runner refuses to execute while the V0.18 draft contract is still marked
``DRAFT``.  ``plan`` is safe before freezing and prints the proposed panel.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np


REPO = Path(__file__).resolve().parents[2]
V015_RUNNER_PATH = (
    REPO / ".scratch" / "multi-catfish-v015-c3-learned-context"
    / "run_v015_c3_learned_context_oracle.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "mcrl_v015_helpers_for_v018_analytic_diagnostic", V015_RUNNER_PATH
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot import V0.15 helper runner: {V015_RUNNER_PATH}")
_V015 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _V015
_SPEC.loader.exec_module(_V015)

for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.env.link_budget import (  # noqa: E402
    BEAM_POWER_MAX_W,
    SEGMENT_START_POWER_W,
    recurrence_power_w,
)
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import opening_service_feasibility_surface  # noqa: E402
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_relational_zr_c3 import (  # noqa: E402
    RELATIONAL_ZR_C3_SCHEMA,
    encode_relational_zr_c3_state,
    nominal_relational_zr_surface,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v018_gate import (  # noqa: E402
    V018_ARMS,
    adjudicate_v018_analytic_gate,
)
from mcrl.runtime.ee_axis_zero_marginal_c3_live import (  # noqa: E402
    measure_zero_marginal_c3,
)


V018_ARMS = tuple(V018_ARMS)
ARMS = V018_ARMS
WORLD_SEEDS = (2026120401, 2026120402, 2026120403, 2026120404)
LINEAGES = tuple(_V015.LINEAGES)
USERS = int(_V015.USERS)
STEPS_PER_EPISODE = int(_V015.STEPS_PER_EPISODE)
# Keep the V0.15 keyed-field namespace so the only changed factor in this
# diagnostic is the C3 arm.  Fresh V0.18 world seeds still make these fields
# distinct from the previously opened V0.15 worlds.
FIELD_COMPONENT = _V015.FIELD_COMPONENT

RESULT_SCHEMA = "multi-catfish-mcrl-v018-analytic-diagnostic-result-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v018-analytic-diagnostic-shard-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v018-analytic-diagnostic-episode-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v018-analytic-diagnostic-contract-v1"
RESULT_SEAL_SCHEMA = "multi-catfish-mcrl-v018-analytic-diagnostic-result-seal-v1"
PROVENANCE_SCHEMA = "multi-catfish-mcrl-v018-analytic-r2-provenance-v1"
R2_EXECUTION_ATTEMPT = "r2"
R1_ABORT_STATUS = "Status: `ABORTED_PERFORMANCE_NO_RESULT`"
R4_PASS_DECISION = "PASS_R2_CACHE_EQUIVALENCE"
R4_CODE_MANIFEST_SHA256 = (
    "0fd88169d63ce02b87534d4f3c0a81559e17df444a2c2c8f556aac3d901382c1"
)

V018_CONTRACT_PATH = (
    REPO / ".scratch" / "multi-catfish-v018-relational-zr" / "contracts"
    / "MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md"
)
V018_CONTRACT_SHA256 = (
    "ad752fa124edd0ee92007c4f791a50cec4884eb2fc0d65c24e6de83332a80451"
)
V03_ROOT = _V015.V03_ROOT
V014_GATE_ROOT = _V015.V014_GATE_ROOT
DEFAULT_PREREG = _V015.DEFAULT_PREREG
DEFAULT_TLE_ROOT = _V015.DEFAULT_TLE_ROOT
DEFAULT_OUTPUT_ROOT = (
    REPO / ".scratch" / "multi-catfish-v018-relational-zr" / "run"
)


class V018OracleError(RuntimeError):
    """The V0.18 source, physics, pairing, or receipt boundary failed."""


def _canonical_default(value: object) -> bool | int | float:
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("non-finite NumPy scalar")
        return result
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=_canonical_default,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V018OracleError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V018OracleError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_text(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise V018OracleError(f"{field} must be a lowercase SHA-256")
    if any(character not in "0123456789abcdef" for character in value):
        raise V018OracleError(f"{field} must be a lowercase SHA-256")
    return value


def _relative_provenance_path(path: Path, field: str) -> str:
    source = Path(path)
    if source.is_absolute() or any(part == ".." for part in source.parts):
        raise V018OracleError(f"{field} must be a repository-relative path")
    value = source.as_posix()
    if not value or value == ".":
        raise V018OracleError(f"{field} must name a regular file")
    return value


def _bind_provenance_file(
    path: Path,
    expected_sha256: object,
    field: str,
) -> dict[str, str]:
    relative = _relative_provenance_path(path, f"{field}.path")
    expected = _sha256_text(expected_sha256, f"{field}.sha256")
    source = Path(relative)
    actual = file_sha256(source)
    if actual != expected:
        raise V018OracleError(
            f"{field} digest mismatch: expected {expected}, got {actual}"
        )
    return {"path": relative, "sha256": expected}


def _read_provenance_json(path: Path, field: str) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(
            source.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant: {value}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise V018OracleError(f"invalid {field} JSON: {source}") from error
    if not isinstance(payload, dict):
        raise V018OracleError(f"{field} JSON is not an object: {source}")
    return payload


def build_r2_provenance(
    *,
    performance_addendum: Path,
    performance_addendum_sha256: str,
    r2_code_manifest: Path,
    r2_code_manifest_sha256: str,
    r1_abort_receipt: Path,
    r1_abort_receipt_sha256: str,
    r4_result: Path,
    r4_result_sha256: str,
    r4_receipt: Path,
    r4_receipt_sha256: str,
    r4_artifact_manifest: Path,
    r4_artifact_manifest_sha256: str,
    r4_code_manifest: Path,
    r4_code_manifest_sha256: str,
    r4_independent_validation: Path,
    r4_independent_validation_sha256: str,
) -> dict[str, Any]:
    """Authenticate the immutable R2 execution provenance closure.

    This function is intentionally separate from the scientific runner.  It
    only checks already-persisted bytes and frozen PASS receipts; it does not
    open a simulator, an action, a teacher, or a learner.
    """

    addendum = _bind_provenance_file(
        performance_addendum, performance_addendum_sha256, "performance_addendum"
    )
    r2_manifest = _bind_provenance_file(
        r2_code_manifest, r2_code_manifest_sha256, "r2_code_manifest"
    )
    r1_abort = _bind_provenance_file(
        r1_abort_receipt, r1_abort_receipt_sha256, "r1_abort_receipt"
    )
    abort_text = Path(r1_abort["path"]).read_text(encoding="utf-8")
    if R1_ABORT_STATUS not in abort_text:
        raise V018OracleError("R1 abort receipt does not attest ABORTED_PERFORMANCE_NO_RESULT")

    r4_result_binding = _bind_provenance_file(
        r4_result, r4_result_sha256, "r4_result"
    )
    r4_receipt_binding = _bind_provenance_file(
        r4_receipt, r4_receipt_sha256, "r4_receipt"
    )
    r4_manifest_binding = _bind_provenance_file(
        r4_artifact_manifest,
        r4_artifact_manifest_sha256,
        "r4_artifact_manifest",
    )
    r4_code_binding = _bind_provenance_file(
        r4_code_manifest, r4_code_manifest_sha256, "r4_code_manifest"
    )
    if r4_code_binding["sha256"] != R4_CODE_MANIFEST_SHA256:
        raise V018OracleError("R4 provenance does not use the frozen R4 code manifest")
    if r4_code_binding["sha256"] == r2_manifest["sha256"]:
        raise V018OracleError("R2 and R4 code manifests must be distinct receipts")
    r4_validation_binding = _bind_provenance_file(
        r4_independent_validation,
        r4_independent_validation_sha256,
        "r4_independent_validation",
    )

    result_payload = _read_provenance_json(Path(r4_result_binding["path"]), "R4 result")
    if result_payload.get("decision") != R4_PASS_DECISION:
        raise V018OracleError("R4 result is not the frozen PASS decision")
    if result_payload.get("passed") is not True:
        raise V018OracleError("R4 result does not attest passed=true")
    if result_payload.get("execution_attempt") != "r4":
        raise V018OracleError("R4 result execution attempt is not r4")
    for field in ("action_executed", "episode_training", "learner_update", "exact_teacher_opened"):
        if result_payload.get(field) is not False:
            raise V018OracleError(f"R4 result does not attest {field}=false")
    result_embedded_sha = result_payload.get("result_sha256")
    if result_embedded_sha is not None:
        _sha256_text(result_embedded_sha, "R4 result.result_sha256")

    receipt_payload = _read_provenance_json(
        Path(r4_receipt_binding["path"]), "R4 receipt"
    )
    if receipt_payload.get("decision") != R4_PASS_DECISION:
        raise V018OracleError("R4 receipt is not the frozen PASS decision")
    if receipt_payload.get("schema") != "multi-catfish-mcrl-v018-r4-equivalence-receipt-v1":
        raise V018OracleError("R4 receipt schema is not the frozen equivalence schema")
    for field in ("action_executed", "episode_training", "learner_update", "test_split_opened"):
        if receipt_payload.get(field) is not False:
            raise V018OracleError(f"R4 receipt does not attest {field}=false")
    receipt_manifest_sha = receipt_payload.get("code_manifest_sha256")
    if receipt_manifest_sha != R4_CODE_MANIFEST_SHA256:
        raise V018OracleError("R4 receipt code-manifest digest is not the frozen R4 digest")

    validation_payload = _read_provenance_json(
        Path(r4_validation_binding["path"]), "R4 independent validation"
    )
    if validation_payload.get("decision") != R4_PASS_DECISION:
        raise V018OracleError("R4 independent validation is not the frozen PASS decision")
    if validation_payload.get("verified") is not True or validation_payload.get("passed") is not True:
        raise V018OracleError("R4 independent validation does not attest verified pass")
    if validation_payload.get("code_manifest_sha256") != R4_CODE_MANIFEST_SHA256:
        raise V018OracleError("R4 independent validation code-manifest digest mismatch")

    provenance = {
        "schema": PROVENANCE_SCHEMA,
        "execution_attempt": R2_EXECUTION_ATTEMPT,
        "performance_addendum": addendum,
        "r2_code_manifest": r2_manifest,
        "r1_abort_receipt": r1_abort,
        "r4_pass": {
            "decision": R4_PASS_DECISION,
            "result": r4_result_binding,
            "receipt": r4_receipt_binding,
            "artifact_manifest": r4_manifest_binding,
            "code_manifest": r4_code_binding,
            "independent_validation": r4_validation_binding,
        },
    }
    provenance["provenance_sha256"] = canonical_sha256(provenance)
    return provenance


def validate_r2_provenance(provenance: Mapping[str, Any]) -> None:
    """Validate the self-digest and immutable shape of a stored R2 receipt."""

    if not isinstance(provenance, Mapping):
        raise V018OracleError("R2 provenance is not an object")
    if provenance.get("schema") != PROVENANCE_SCHEMA:
        raise V018OracleError("R2 provenance schema mismatch")
    if provenance.get("execution_attempt") != R2_EXECUTION_ATTEMPT:
        raise V018OracleError("R2 provenance execution attempt mismatch")
    supplied = provenance.get("provenance_sha256")
    _sha256_text(supplied, "provenance_sha256")
    body = dict(provenance)
    body.pop("provenance_sha256", None)
    if supplied != canonical_sha256(body):
        raise V018OracleError("R2 provenance self-digest mismatch")
    for key in (
        "performance_addendum",
        "r2_code_manifest",
        "r1_abort_receipt",
    ):
        binding = provenance.get(key)
        if not isinstance(binding, Mapping):
            raise V018OracleError(f"R2 provenance is missing {key}")
        _relative_provenance_path(Path(str(binding.get("path", ""))), f"{key}.path")
        _sha256_text(binding.get("sha256"), f"{key}.sha256")
    r4 = provenance.get("r4_pass")
    if not isinstance(r4, Mapping) or r4.get("decision") != R4_PASS_DECISION:
        raise V018OracleError("R2 provenance is missing the frozen R4 PASS")
    for key in (
        "result",
        "receipt",
        "artifact_manifest",
        "code_manifest",
        "independent_validation",
    ):
        binding = r4.get(key)
        if not isinstance(binding, Mapping):
            raise V018OracleError(f"R2 provenance is missing R4 {key}")
        _relative_provenance_path(Path(str(binding.get("path", ""))), f"r4.{key}.path")
        _sha256_text(binding.get("sha256"), f"r4.{key}.sha256")


def array_sha256(*values: object) -> str:
    digest = hashlib.sha256()
    for value in values:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V018OracleError(f"missing JSON receipt: {source}")
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V018OracleError(f"invalid JSON receipt: {source}") from error
    if not isinstance(payload, dict):
        raise V018OracleError(f"JSON receipt is not an object: {source}")
    return payload


def validate_v018_contract(path: Path = V018_CONTRACT_PATH) -> None:
    """Require a frozen pre-outcome V0.18 contract before simulator access."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V018OracleError(f"missing V0.18 contract: {source}")
    if file_sha256(source) != V018_CONTRACT_SHA256:
        raise V018OracleError("V0.18 contract hash differs from the frozen prereg")
    text = source.read_text(encoding="utf-8")
    if "Status: `FROZEN_BEFORE_OUTCOME`" not in text:
        raise V018OracleError(
            "V0.18 contract is not frozen before outcome access; refusing to run"
        )
    for phrase in (
        "BASE",
        "EXACT_ZR",
        "NOMINAL_ZR",
        "four newly frozen TRAIN worlds",
        "TEST remains unopened",
        "STOP_V018_MECHANICS",
        "STOP_ZR_IN_LEARNED_Q2_CONTEXT",
        "STOP_RELATIONAL_OBSERVABILITY",
    ):
        if phrase not in text:
            raise V018OracleError(f"V0.18 contract is missing required binding: {phrase}")


def contract_receipt(
    *,
    worlds: Sequence[int] = WORLD_SEEDS,
    lineages: Sequence[int] = LINEAGES,
    contract_path: Path = V018_CONTRACT_PATH,
) -> dict[str, Any]:
    worlds_tuple = tuple(int(value) for value in worlds)
    lineages_tuple = tuple(int(value) for value in lineages)
    if not worlds_tuple or len(set(worlds_tuple)) != len(worlds_tuple):
        raise V018OracleError("contract world list must be nonempty and unique")
    if any(value not in WORLD_SEEDS for value in worlds_tuple):
        raise V018OracleError("contract world is outside the frozen V0.18 worlds")
    if not lineages_tuple or len(set(lineages_tuple)) != len(lineages_tuple):
        raise V018OracleError("contract lineage list must be nonempty and unique")
    if any(value not in LINEAGES for value in lineages_tuple):
        raise V018OracleError("contract lineage is outside frozen Q1/Q2 lineages")
    return {
        "schema": CONTRACT_SCHEMA,
        "world_seeds": list(worlds_tuple),
        "lineages": list(lineages_tuple),
        "arms": list(ARMS),
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes": len(worlds_tuple) * len(lineages_tuple) * len(ARMS),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "q1_policy": "frozen_v03_head_0_rung_10",
        "q2_policy": "frozen_v014_head_q2_rung_3000",
        "background_policy": "Q1_PLUS_LEARNED_Q2",
        "exact_policy": "Q1_PLUS_LEARNED_Q2_PLUS_EXACT_ZR",
        "nominal_policy": "Q1_PLUS_LEARNED_Q2_PLUS_NOMINAL_ZR",
        "nominal_surface": "RELATIONAL_ZR_UNIT_FADING_ZERO_SHADOW_DIAGNOSTIC_ONLY",
        "exact_surface_role_in_base_and_nominal": "COMPATIBILITY_PROOF_ONLY",
        "selection": "one_common_mask_one_masked_argmax_one_action_vector",
        "field_component": FIELD_COMPONENT,
        "field_excludes": ["arm", "lineage", "policy", "action", "target", "outcome"],
        "checkpoint_rung": {"q1": 10, "q2": 3000},
        "q2_init_by_lineage": {
            str(key): value for key, value in _V015.Q2_INIT_BY_LINEAGE.items()
        },
        "q2_checkpoint_sha256": {
            str(key): value for key, value in _V015.Q2_CHECKPOINT_SHA256.items()
        },
        "contexts": [12, 1, 2],
        "service_noninferiority_margin": 0.001,
        "contract_file": str(Path(contract_path).resolve()),
        "claim_ceiling": "TRAIN_ANALYTIC_DIAGNOSTIC_NO_LEARNER_NO_TEST_NO_EFFICACY_CLAIM",
    }


def field_for_world(world_seed: int) -> KeyedFadingField:
    if isinstance(world_seed, bool) or not isinstance(world_seed, (int, np.integer)):
        raise V018OracleError("world seed must be an integer")
    return KeyedFadingField.from_components(FIELD_COMPONENT, int(world_seed))


def _current_required_power_and_opening(
    *,
    current_gain_linear: object,
    segment_start_gain_linear: object,
    action_masks: object,
    pmax_w: float = BEAM_POWER_MAX_W,
    p0_w: float = SEGMENT_START_POWER_W,
) -> tuple[np.ndarray, np.ndarray]:
    """Build the exact current (h=0) recurrence and service surfaces."""

    current = np.asarray(current_gain_linear, dtype=np.float64)
    starts = np.asarray(segment_start_gain_linear, dtype=np.float64)
    legal = np.asarray(action_masks)
    if (
        current.ndim != 2
        or starts.shape != current.shape
        or legal.dtype != np.bool_
        or legal.shape != current.shape
        or current.shape[1] != NUM_ACTIONS
        or not np.all(np.isfinite(current))
        or not np.all(np.isfinite(starts))
        or np.any(current < 0.0)
        or np.any(starts < 0.0)
    ):
        raise V018OracleError("current gain/start gain/mask matrix is malformed")
    if not math.isfinite(float(pmax_w)) or float(pmax_w) <= 0.0:
        raise V018OracleError("pmax_w must be finite and positive")
    if not math.isfinite(float(p0_w)) or not 0.0 < float(p0_w) <= float(pmax_w):
        raise V018OracleError("p0_w must be positive and no greater than pmax_w")
    required = np.zeros_like(current, dtype=np.float64)
    positive = legal & (current > 0.0) & (starts > 0.0)
    if bool(np.any(positive)):
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            try:
                required[positive] = recurrence_power_w(
                    starts[positive], current[positive], p0_w=float(p0_w)
                )
            except (FloatingPointError, ValueError, RuntimeError) as error:
                raise V018OracleError("current recurrence power is not finite") from error
    if not np.all(np.isfinite(required)):
        raise V018OracleError("current recurrence power is non-finite")
    opening = np.stack(
        [
            opening_service_feasibility_surface(
                legal_mask=legal[uid],
                segment_start_gain_linear=starts[uid],
                current_gain_linear=current[uid],
                p0_w=float(p0_w),
                pmax_w=float(pmax_w),
            )
            for uid in range(current.shape[0])
        ],
        axis=0,
    ).astype(np.bool_, copy=False)
    if opening.shape != legal.shape or np.any(opening & ~legal):
        raise V018OracleError("current opening surface is not a legal subset")
    return required, opening


def _masked_argmax(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    legal = np.asarray(masks)
    if values.ndim != 2 or values.shape[1] != NUM_ACTIONS:
        raise V018OracleError("score surface must have shape (U,28)")
    if legal.dtype != np.bool_ or legal.shape != values.shape:
        raise V018OracleError("score mask is not a native Boolean surface")
    if not np.all(np.isfinite(values)) or not np.all(np.any(legal, axis=1)):
        raise V018OracleError("score surface is non-finite or has an empty row")
    return np.argmax(np.where(legal, values, -np.inf), axis=1).astype(np.int64)


def compose_arm_scores(
    q1: object,
    q2: object,
    exact_q3: object,
    nominal_q3: object,
    masks: object,
    arm: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Compose one arm score and action vector without touching the physics.

    This small pure seam makes the arm boundary auditable: NOMINAL_ZR reads
    only ``nominal_q3`` while EXACT_ZR reads only ``exact_q3``.  Both use the
    same detached Q1+Q2 background and the same native mask.
    """

    if arm not in ARMS:
        raise V018OracleError(f"unknown V0.18 arm: {arm}")
    arrays = tuple(np.asarray(value, dtype=np.float64) for value in (q1, q2, exact_q3, nominal_q3))
    legal = np.asarray(masks)
    if any(value.ndim != 2 or value.shape[1] != NUM_ACTIONS for value in arrays):
        raise V018OracleError("Q surfaces must be two-dimensional (U,28)")
    if any(value.shape != arrays[0].shape for value in arrays):
        raise V018OracleError("Q surfaces do not share one shape")
    if legal.dtype != np.bool_ or legal.shape != arrays[0].shape:
        raise V018OracleError("native mask does not match Q surfaces")
    if any(not np.all(np.isfinite(value)) for value in arrays):
        raise V018OracleError("Q surfaces contain non-finite values")
    base = arrays[0] + arrays[1]
    if arm == "BASE":
        q3 = np.zeros_like(base)
    elif arm == "EXACT_ZR":
        q3 = arrays[2]
    else:
        q3 = arrays[3]
    score = base + q3
    selected = _masked_argmax(score, legal)
    return score, selected


def _q1_values(network: Any, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
    return _V015._q1_values(network, states, masks)


def _q2_values(network: Any, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
    return _V015._q2_values(network, states, masks)


def _live_digest(environment: Any, rng: np.random.Generator) -> str:
    return _V015._live_digest(environment, rng)


def _initial_world_sha(environment: Any, observation: Any) -> str:
    return _V015._initial_world_sha(environment, observation)


def _joint_support_receipt(
    step_env: Any,
    rng: np.random.Generator,
    reference: np.ndarray,
    selected: np.ndarray,
    interval_s: float,
) -> dict[str, Any]:
    return _V015._joint_support_receipt(
        step_env, rng, reference, selected, interval_s
    )


def _exact_zr_surface(measurements: Any, interval_s: float) -> tuple[np.ndarray, dict[str, Any]]:
    return _V015._build_c3_surfaces(measurements, interval_s)


def _source_context_metrics(
    *,
    context: int,
    base_surface: np.ndarray,
    exact_q3: np.ndarray,
    nominal_q3: np.ndarray,
    masks: np.ndarray,
    compatible: np.ndarray,
) -> dict[str, Any]:
    """Compute source-only nominal-vs-exact decision diagnostics."""

    base_action = _masked_argmax(base_surface, masks)
    teacher_action = _masked_argmax(base_surface + exact_q3, masks)
    nominal_action = _masked_argmax(base_surface + nominal_q3, masks)
    same_teacher = nominal_action == teacher_action
    same_base = base_action == teacher_action
    pivotal = teacher_action != base_action
    stable = ~pivotal
    changed = nominal_action != base_action
    positive_supported = np.zeros_like(changed, dtype=np.bool_)
    rows = np.flatnonzero(changed)
    if rows.size:
        positive_supported[rows] = (
            (exact_q3[rows, nominal_action[rows]] > 0.0)
            & compatible[rows, nominal_action[rows]]
        )

    counts = {
        "agreement_count": int(np.count_nonzero(same_teacher)),
        "base_agreement_count": int(np.count_nonzero(same_base)),
        "pivotal_agreement_count": int(np.count_nonzero(same_teacher[pivotal])),
        "pivotal_count": int(np.count_nonzero(pivotal)),
        "stable_preservation_count": int(
            np.count_nonzero((nominal_action == base_action)[stable])
        ),
        "stable_count": int(np.count_nonzero(stable)),
        "nominal_change_count": int(np.count_nonzero(changed)),
        "positive_supported_change_count": int(
            np.count_nonzero(positive_supported[changed])
        ),
        "row_count": int(masks.shape[0]),
    }
    return _context_report_from_counts(
        context=int(context),
        counts=counts,
        teacher_action_sha256=array_sha256(teacher_action),
        base_action_sha256=array_sha256(base_action),
        nominal_action_sha256=array_sha256(nominal_action),
    )


def _context_report_from_counts(
    *,
    context: int,
    counts: Mapping[str, int],
    teacher_action_sha256: str | None = None,
    base_action_sha256: str | None = None,
    nominal_action_sha256: str | None = None,
    report_count: int = 1,
) -> dict[str, Any]:
    """Convert additive source counts to the registered ratio diagnostics."""

    rows = int(counts.get("row_count", 0))
    agreement_count = int(counts.get("agreement_count", 0))
    base_agreement_count = int(counts.get("base_agreement_count", 0))
    pivotal_count = int(counts.get("pivotal_count", 0))
    pivotal_agreement_count = int(counts.get("pivotal_agreement_count", 0))
    stable_count = int(counts.get("stable_count", 0))
    stable_preservation_count = int(counts.get("stable_preservation_count", 0))
    nominal_change_count = int(counts.get("nominal_change_count", 0))
    positive_supported_change_count = int(
        counts.get("positive_supported_change_count", 0)
    )
    agreement = agreement_count / rows if rows else 0.0
    base_agreement = base_agreement_count / rows if rows else 0.0
    pivotal_agreement = (
        pivotal_agreement_count / pivotal_count if pivotal_count else 0.0
    )
    stable_preservation = (
        stable_preservation_count / stable_count if stable_count else 0.0
    )
    change_support = (
        positive_supported_change_count / nominal_change_count
        if nominal_change_count
        else 0.0
    )
    return {
        "context": int(context),
        "rows": rows,
        "report_count": int(report_count),
        **{name: int(value) for name, value in counts.items()},
        "base_teacher_agreement": base_agreement,
        "nominal_teacher_agreement": agreement,
        "pivotal_rows": pivotal_count,
        "pivotal_agreement": pivotal_agreement,
        "stable_rows": stable_count,
        "stable_preservation": stable_preservation,
        "nominal_change_rate": nominal_change_count / rows if rows else 0.0,
        "nominal_change_positive_compatible_fraction": change_support,
        "teacher_action_sha256": teacher_action_sha256,
        "base_action_sha256": base_action_sha256,
        "nominal_action_sha256": nominal_action_sha256,
        "passed": bool(
            (agreement > base_agreement if int(context) == 12 else agreement >= base_agreement)
            and (int(context) != 12 or pivotal_agreement >= 0.50)
            and (int(context) != 12 or stable_preservation >= 0.95)
            and (int(context) != 12 or nominal_change_count > 0)
            and (int(context) != 12 or change_support >= 0.80)
        ),
    }


def _aggregate_context_reports(
    reports: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Pool additive source counts without letting the last report win."""

    if not reports:
        raise V018OracleError("cannot aggregate an empty source context")
    keys = (
        "row_count",
        "agreement_count",
        "base_agreement_count",
        "pivotal_agreement_count",
        "pivotal_count",
        "stable_preservation_count",
        "stable_count",
        "nominal_change_count",
        "positive_supported_change_count",
    )
    counts = {name: sum(int(report.get(name, 0)) for report in reports) for name in keys}
    context_values = {int(report["context"]) for report in reports}
    if len(context_values) != 1:
        raise V018OracleError("source reports mix reference contexts")
    return _context_report_from_counts(
        context=next(iter(context_values)),
        counts=counts,
        report_count=len(reports),
    )


def _source_context_summary(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not reports:
        return {"contexts": {}, "passed": False}
    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for report in reports:
        grouped.setdefault(int(report["context"]), []).append(report)
    by_context = {
        str(context): _aggregate_context_reports(values)
        for context, values in grouped.items()
    }
    required = {"12", "1", "2"}
    return {
        "contexts": by_context,
        "passed": required.issubset(by_context)
        and all(bool(by_context[key].get("passed")) for key in required),
    }


def _source_diagnostics_panel_summary(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Pool BASE source counts by lineage and over the complete panel."""

    base_rows = [
        row
        for row in rows
        if str(row.get("arm")) == "BASE"
        and isinstance(row.get("source_diagnostics"), Mapping)
        and bool(row.get("source_diagnostics", {}).get("contexts"))
    ]
    if not base_rows:
        return {"pooled": {"contexts": {}, "passed": False}, "by_lineage": {}, "passed": False}

    def _pool_source(source_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        grouped: dict[int, list[Mapping[str, Any]]] = {}
        for source_row in source_rows:
            contexts = source_row.get("source_diagnostics", {}).get("contexts", {})
            if not isinstance(contexts, Mapping):
                continue
            for raw_context, record in contexts.items():
                if isinstance(record, Mapping):
                    grouped.setdefault(int(raw_context), []).append(record)
        contexts = {
            str(context): _aggregate_context_reports(records)
            for context, records in grouped.items()
        }
        required = {"12", "1", "2"}
        return {
            "contexts": contexts,
            "passed": required.issubset(contexts)
            and all(bool(contexts[key].get("passed")) for key in required),
        }

    pooled = _pool_source(base_rows)
    by_lineage: dict[str, Any] = {}
    for lineage in sorted({int(row["lineage"]) for row in base_rows}):
        by_lineage[str(lineage)] = _pool_source(
            [row for row in base_rows if int(row["lineage"]) == lineage]
        )
    return {
        "pooled": pooled,
        "by_lineage": by_lineage,
        "passed": bool(pooled["passed"])
        and bool(by_lineage)
        and all(bool(report["passed"]) for report in by_lineage.values()),
    }


def evaluate_episode(
    *,
    q1: Any,
    q1_receipt: Mapping[str, Any],
    q2: Any,
    q2_receipt: Mapping[str, Any],
    archive: Any,
    world_seed: int,
    field: KeyedFadingField,
    lineage: int,
    arm: str,
) -> dict[str, Any]:
    """Evaluate one ten-step BASE/EXACT_ZR/NOMINAL_ZR trajectory."""

    if arm not in ARMS:
        raise V018OracleError(f"unknown V0.18 arm: {arm}")
    if int(lineage) not in LINEAGES:
        raise V018OracleError("lineage is outside the frozen Q1/Q2 set")

    environment = _V015._V013.screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = _V015._V013.screen._evaluation_rngs(
        int(world_seed)
    )
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    step_env = environment.environment
    interval_s = float(step_env.driver.config.ephemeris.time_step_s)
    initial_world = _initial_world_sha(environment, observation)
    q1_before = _V015._q_parameter_sha256(q1)
    q2_before = _V015._q_parameter_sha256(q2)
    started = time.perf_counter()

    total_bits = 0.0
    total_energy = 0.0
    served_steps = 0
    action_exposure = 0
    exact_positive_targets = 0
    exact_supported_positive_targets = 0
    exact_compatible_actions = 0
    c3_spread = 0
    mechanics_passed = True
    compatibility_proof_passed = True
    joint_support_passed = True
    per_step: list[dict[str, Any]] = []
    source_reports: list[dict[str, Any]] = []

    with __import__("torch").no_grad():
        for step_index in range(STEPS_PER_EPISODE):
            native = encode_ee_axis_state(step_env, observation)
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            q1_values = _q1_values(q1, native.state_matrix, masks)
            q1_reference = _V015.select_actions(
                q1_values,
                np.zeros_like(q1_values),
                np.zeros_like(q1_values),
                masks,
                include_c3=False,
            )

            # OPS-3 is used only as the frozen learned-Q2 state carrier.
            anchor = snapshot_ops3_anchor(step_env, observation)
            projection = project_ops3_anchor(anchor)
            ops3_surfaces = build_ops3_live_surfaces(anchor, projection, q1_reference)
            q2_state = _V015.encode_ee_axis_v014_q2_states(ops3_surfaces)
            q2_state.verify()
            if not np.array_equal(q2_state.action_masks, masks):
                raise V018OracleError("Q2 carrier mask differs from native mask")
            learned_q2 = _q2_values(q2, q2_state.state_matrix, q2_state.action_masks)
            base_surface = q1_values + learned_q2
            background = _masked_argmax(base_surface, masks)

            required_power, opening = _current_required_power_and_opening(
                current_gain_linear=anchor.current_gain_linear,
                segment_start_gain_linear=anchor.segment_start_gain_linear,
                action_masks=masks,
            )
            premeasurement_digest = _live_digest(environment, env_rng)

            # Encode the relational input before any exact ActionEvaluation.
            relational_state = encode_relational_zr_c3_state(
                step_env,
                observation,
                reference_actions=background,
                required_power_surface=required_power,
                opening_feasibility_surface=opening,
                pmax_w=BEAM_POWER_MAX_W,
            )
            relational_state.verify()
            if relational_state.schema != RELATIONAL_ZR_C3_SCHEMA:
                raise V018OracleError("relational C3 schema is stale")

            # The exact teacher is opened once for the compatibility proof at
            # every arm anchor.  BASE and NOMINAL never use this surface in
            # their action score.
            measurements = measure_zero_marginal_c3(
                step_env,
                observation=observation,
                reference_actions=background,
                rng=env_rng,
                include_insertion=False,
                interval_s=interval_s,
            )
            exact_q3, exact_method = _exact_zr_surface(measurements, interval_s)
            exact_compatible = np.asarray(measurements.compatible, dtype=np.bool_)
            reconstructed_compatible = np.asarray(
                relational_state.positive_credit_compatible, dtype=np.bool_
            )
            step_compatibility = bool(np.array_equal(exact_compatible, reconstructed_compatible))
            compatibility_proof_passed = compatibility_proof_passed and step_compatibility

            nominal_delta, nominal_q3 = nominal_relational_zr_surface(
                step_env,
                observation,
                reference_actions=background,
                required_power_surface=required_power,
                opening_feasibility_surface=opening,
                interval_s=interval_s,
                kappa_bits=OPS3_KAPPA_BITS,
                pmax_w=BEAM_POWER_MAX_W,
            )
            nominal_delta = np.asarray(nominal_delta, dtype=np.float64)
            nominal_q3 = np.asarray(nominal_q3, dtype=np.float64)
            if nominal_q3.shape != base_surface.shape or not np.all(np.isfinite(nominal_q3)):
                raise V018OracleError("nominal ZR surface is malformed")
            if not step_compatibility:
                raise V018OracleError(
                    "V0.18 compatibility proof disagrees with exact live support"
                )

            if arm == "BASE":
                score, selected = compose_arm_scores(
                    q1_values, learned_q2, exact_q3, nominal_q3, masks, "BASE"
                )
            elif arm == "EXACT_ZR":
                score, selected = compose_arm_scores(
                    q1_values, learned_q2, exact_q3, nominal_q3, masks, "EXACT_ZR"
                )
            else:
                # Deliberately pass the exact surface as a separate argument;
                # compose_arm_scores selects only nominal_q3 in this branch.
                score, selected = compose_arm_scores(
                    q1_values, learned_q2, exact_q3, nominal_q3, masks, "NOMINAL_ZR"
                )

            postmeasurement_digest = _live_digest(environment, env_rng)
            if premeasurement_digest != postmeasurement_digest:
                raise V018OracleError("counterfactual source changed live state or RNG")

            changed = np.flatnonzero(selected != background)
            changed_compatible = bool(
                all(bool(exact_compatible[int(uid), int(selected[int(uid)])]) for uid in changed)
            )
            changed_exact_positive = bool(
                all(float(exact_q3[int(uid), int(selected[int(uid)])]) > 0.0 for uid in changed)
            )
            if arm == "EXACT_ZR" and changed.size and (
                not changed_compatible or not changed_exact_positive
            ):
                raise V018OracleError("EXACT_ZR changed action lacks positive compatible ZR credit")

            base_evaluation = step_env.evaluate_actions(background, env_rng)
            opening_equal = all(
                bool(ops3_surfaces[uid].opening_service_feasible[int(background[uid])])
                == bool(base_evaluation.resolution.served[uid])
                for uid in range(USERS)
            )
            joint_support = _joint_support_receipt(
                step_env, env_rng, background, selected, interval_s
            )
            post_checks_digest = _live_digest(environment, env_rng)
            step_mechanics = {
                "live_state_and_rng_unchanged": (
                    premeasurement_digest == postmeasurement_digest == post_checks_digest
                ),
                "common_native_mask": np.array_equal(relational_state.action_mask, masks),
                "relational_state_verified": True,
                "relational_state_schema": relational_state.schema == RELATIONAL_ZR_C3_SCHEMA,
                "exact_measurement_mask_equal": np.array_equal(measurements.legal_mask, masks),
                "compatibility_reconstruction_exact": step_compatibility,
                "opening_service_gate_equal": opening_equal,
                "q1_surface_finite": bool(np.all(np.isfinite(q1_values))),
                "learned_q2_surface_finite": bool(np.all(np.isfinite(learned_q2))),
                "nominal_surface_finite": bool(np.all(np.isfinite(nominal_q3))),
                "native_action_vector": selected.shape == (USERS,),
                "joint_support_diagnostic_passed": bool(joint_support["passed"]),
                "joint_support_required_passed": (
                    bool(joint_support["passed"]) if arm == "EXACT_ZR" else True
                ),
                "background_sha256": array_sha256(background),
            }
            step_mechanics["passed"] = bool(
                all(
                    value
                    for key, value in step_mechanics.items()
                    if key
                    not in {
                        "background_sha256",
                        "joint_support_diagnostic_passed",
                        "passed",
                    }
                )
            )
            if not step_mechanics["passed"]:
                raise V018OracleError("V0.18 per-step mechanics failed")

            # Source diagnostics are generated once on the BASE trajectory;
            # h=12/1/2 are detached reference contexts and do not feed the
            # executed action.  No duplicate trajectory is needed for them.
            if arm == "BASE":
                context_reports: list[dict[str, Any]] = []
                context_bases = {
                    12: base_surface,
                    1: q1_values,
                    2: learned_q2,
                }
                context_references = {
                    code: _masked_argmax(surface, masks)
                    for code, surface in context_bases.items()
                }
                # Reuse h=12's already opened exact measurement and relational
                # state; h=1/h=2 each get their own detached proof measurement.
                for context in (12, 1, 2):
                    reference = context_references[context]
                    if context == 12:
                        context_exact = exact_q3
                        context_nominal = nominal_q3
                        context_compatible = exact_compatible
                    else:
                        context_pre_digest = _live_digest(environment, env_rng)
                        context_state = encode_relational_zr_c3_state(
                            step_env,
                            observation,
                            reference_actions=reference,
                            required_power_surface=required_power,
                            opening_feasibility_surface=opening,
                            pmax_w=BEAM_POWER_MAX_W,
                        )
                        context_measurement = measure_zero_marginal_c3(
                            step_env,
                            observation=observation,
                            reference_actions=reference,
                            rng=env_rng,
                            include_insertion=False,
                            interval_s=interval_s,
                        )
                        context_exact, _context_method = _exact_zr_surface(
                            context_measurement, interval_s
                        )
                        _context_delta, context_nominal = nominal_relational_zr_surface(
                            step_env,
                            observation,
                            reference_actions=reference,
                            required_power_surface=required_power,
                            opening_feasibility_surface=opening,
                            interval_s=interval_s,
                            kappa_bits=OPS3_KAPPA_BITS,
                            pmax_w=BEAM_POWER_MAX_W,
                        )
                        context_compatible = np.asarray(
                            context_measurement.compatible, dtype=np.bool_
                        )
                        context_post_digest = _live_digest(environment, env_rng)
                        if context_pre_digest != context_post_digest:
                            raise V018OracleError(
                                f"context {context} measurement changed live state or RNG"
                            )
                        if not np.array_equal(
                            context_state.positive_credit_compatible, context_compatible
                        ):
                            raise V018OracleError(
                                f"context {context} compatibility reconstruction failed"
                            )
                    context_report = _source_context_metrics(
                        context=context,
                        base_surface=np.asarray(context_bases[context], dtype=np.float64),
                        exact_q3=np.asarray(context_exact, dtype=np.float64),
                        nominal_q3=np.asarray(context_nominal, dtype=np.float64),
                        masks=masks,
                        compatible=context_compatible,
                    )
                    context_reports.append(context_report)
                source_reports.extend(context_reports)

            result = environment.step(selected, env_rng)
            outcome = environment.last_outcome
            rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
            power = float(outcome.system_power_w)
            if (
                rates.shape != (USERS,)
                or not np.all(np.isfinite(rates))
                or np.any(rates < 0.0)
                or not math.isfinite(power)
                or power <= 0.0
            ):
                raise V018OracleError("canonical EE inputs are malformed")
            bits = interval_s * math.fsum(float(value) for value in rates)
            energy = interval_s * power
            total_bits += bits
            total_energy += energy
            served_steps += int(outcome.resolution.served_count)
            flips = int(changed.size)
            legal_spread = int(
                sum(
                    np.ptp(exact_q3[uid, np.flatnonzero(masks[uid])]) > 0.0
                    for uid in range(masks.shape[0])
                )
            )
            action_exposure += flips
            c3_spread += legal_spread
            exact_positive_targets += int(exact_method["positive_target_count"])
            exact_supported_positive_targets += int(
                exact_method["supported_positive_target_count"]
            )
            exact_compatible_actions += int(exact_method["compatibility_component_counts"]["all"])
            mechanics_passed = mechanics_passed and bool(step_mechanics["passed"])
            compatibility_proof_passed = compatibility_proof_passed and step_compatibility
            joint_support_passed = joint_support_passed and bool(joint_support["passed"])
            per_step.append(
                {
                    "step_index": step_index,
                    "total_bits": float(bits),
                    "total_energy_j": float(energy),
                    "served_user_steps": int(outcome.resolution.served_count),
                    "action_exposure": flips,
                    "changed_actions_compatible": changed_compatible,
                    "changed_actions_positive_exact_zr": changed_exact_positive,
                    "exact_compatible_action_count": int(
                        exact_method["compatibility_component_counts"]["all"]
                    ),
                    "exact_positive_target_count": int(exact_method["positive_target_count"]),
                    "nominal_positive_action_count": int(
                        np.count_nonzero(nominal_q3 > 0.0)
                    ),
                    "c3_legal_spread_count": legal_spread,
                    "selected_actions": [int(value) for value in selected.tolist()],
                    "reference_actions": [int(value) for value in background.tolist()],
                    "surface_sha256": {
                        "q1": array_sha256(q1_values),
                        "q2_learned": array_sha256(learned_q2),
                        "q2_state": q2_state.state_sha256,
                        "q3_exact": array_sha256(exact_q3),
                        "q3_nominal": array_sha256(nominal_q3),
                        "nominal_delta_bits": array_sha256(nominal_delta),
                        "relational_state": relational_state.state_sha256,
                        "relational_compatible": array_sha256(reconstructed_compatible),
                        "mask": array_sha256(masks),
                        "background": array_sha256(background),
                        "selected": array_sha256(selected),
                    },
                    "premeasurement_live_sha256": premeasurement_digest,
                    "postmeasurement_live_sha256": postmeasurement_digest,
                    "post_checks_live_sha256": post_checks_digest,
                    "mechanics": step_mechanics,
                    "exact_method": exact_method,
                    "joint_support": joint_support,
                }
            )
            if result.done:
                if step_index != STEPS_PER_EPISODE - 1:
                    raise V018OracleError("episode terminated before ten steps")
                break
            observation = outcome.observation

    if _V015._q_parameter_sha256(q1) != q1_before:
        raise V018OracleError("frozen Q1 changed during diagnostic episode")
    if _V015._q_parameter_sha256(q2) != q2_before:
        raise V018OracleError("frozen learned Q2 changed during diagnostic episode")
    source_summary = _source_context_summary(source_reports)
    return {
        "schema": EPISODE_SCHEMA,
        "arm": arm,
        "lineage": int(lineage),
        "initialization_seed": int(lineage),
        "world_seed": int(world_seed),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "users": USERS,
        "steps": STEPS_PER_EPISODE,
        "served_opportunities": USERS * STEPS_PER_EPISODE,
        "initial_world_sha256": initial_world,
        "field_root_digest": field.root_digest,
        "q1_checkpoint_sha256": q1_receipt["checkpoint_sha256"],
        "q2_checkpoint_sha256": q2_receipt["checkpoint_sha256"],
        "q1_checkpoint": dict(q1_receipt),
        "q2_checkpoint": dict(q2_receipt),
        "q1_parameter_sha256_before": q1_before,
        "q1_parameter_sha256_after": _V015._q_parameter_sha256(q1),
        "q2_parameter_sha256_before": q2_before,
        "q2_parameter_sha256_after": _V015._q_parameter_sha256(q2),
        "total_bits": float(total_bits),
        "total_energy_j": float(total_energy),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / total_energy),
        "served_user_steps": served_steps,
        "served_fraction": served_steps / float(USERS * STEPS_PER_EPISODE),
        "c3_legal_spread_count": c3_spread,
        "exact_positive_target_count": exact_positive_targets,
        "exact_supported_positive_target_count": exact_supported_positive_targets,
        "exact_compatible_action_count": exact_compatible_actions,
        "action_exposure": action_exposure,
        "mechanics_passed": mechanics_passed,
        "compatibility_proof_passed": compatibility_proof_passed,
        "joint_support_passed": joint_support_passed,
        "source_diagnostics": source_summary,
        # BASE is the sole source-diagnostics arm.  Merge pools its additive
        # reports by lineage and over the panel before calling the pure gate.
        "source_diagnostics_passed": bool(source_summary["passed"])
        if arm == "BASE"
        else None,
        "per_step": per_step,
        "elapsed_s": time.perf_counter() - started,
    }


def _resolve_source_pass(rows: Sequence[Mapping[str, Any]]) -> bool:
    return bool(_source_diagnostics_panel_summary(rows)["passed"])


def run_shard(
    *,
    world_seed: int,
    arm: str,
    lineage: int,
    output_dir: Path,
    q2_root: Path = V014_GATE_ROOT,
    v03_root: Path = V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path = DEFAULT_TLE_ROOT,
    contract_path: Path = V018_CONTRACT_PATH,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one (world, arm, lineage) shard; no files are overwritten."""

    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V018OracleError(f"refusing to overwrite shard output: {output}")
    if (
        int(world_seed) not in WORLD_SEEDS
        or int(lineage) not in LINEAGES
        or arm not in ARMS
    ):
        raise V018OracleError("world, lineage, or arm is outside V0.18 declaration")
    validate_r2_provenance(provenance)
    validate_v018_contract(contract_path)
    _V015.validate_v015_contract()
    q2_gate_receipt = _V015.validate_v014_gate_receipts(q2_root)
    q1, q1_receipt = _V015.load_frozen_q1(v03_root, lineage)
    q2, q2_receipt = _V015.load_frozen_q2(
        q2_root, lineage=lineage, gate_receipt=q2_gate_receipt
    )
    record = _V015._V013.read_prereg(prereg_path)
    field = field_for_world(int(world_seed))
    with tempfile.TemporaryDirectory(prefix="mcrl-v018-relational-zr-tle-") as temporary:
        archive = _V015._V013.screen._frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        row = evaluate_episode(
            q1=q1,
            q1_receipt=q1_receipt,
            q2=q2,
            q2_receipt=q2_receipt,
            archive=archive,
            world_seed=int(world_seed),
            field=field,
            lineage=int(lineage),
            arm=arm,
        )
    contract = contract_receipt(
        worlds=(int(world_seed),),
        lineages=(int(lineage),),
        contract_path=contract_path,
    )
    payload = {
        "schema": SHARD_SCHEMA,
        "execution_attempt": R2_EXECUTION_ATTEMPT,
        "shard_id": f"{int(world_seed)}-{arm}-{int(lineage)}",
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "contract_file_sha256": file_sha256(Path(contract_path).resolve()),
        "prereg_file_sha256": file_sha256(Path(prereg_path)),
        "q1_checkpoint_sha256": q1_receipt["checkpoint_sha256"],
        "q2_checkpoint_sha256": q2_receipt["checkpoint_sha256"],
        "q2_gate_receipt": dict(q2_gate_receipt),
        "provenance": dict(provenance),
        "provenance_sha256": provenance["provenance_sha256"],
        "performance_addendum_sha256": provenance["performance_addendum"]["sha256"],
        "r2_code_manifest_sha256": provenance["r2_code_manifest"]["sha256"],
        "r1_abort_receipt_sha256": provenance["r1_abort_receipt"]["sha256"],
        "r4_pass_provenance": dict(provenance["r4_pass"]),
        "row": row,
    }
    payload["row_sha256"] = canonical_sha256(row)
    output.mkdir(parents=True, exist_ok=False)
    (output / "shard.json").write_bytes(_canonical_bytes(payload))
    print(
        f"{world_seed}/{arm}/{lineage}: "
        f"EE={row['ratio_of_sums_ee_bits_per_j']:.9g} elapsed={row['elapsed_s']:.1f}s"
    )
    return payload


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise V018OracleError("cannot pool empty rows")
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    opportunities = sum(int(row["served_opportunities"]) for row in rows)
    if not all(math.isfinite(value) and value > 0.0 for value in (bits, energy)):
        raise V018OracleError("pooled canonical EE totals are not positive finite")
    if served < 0 or opportunities <= 0 or served > opportunities:
        raise V018OracleError("pooled service counts are malformed")
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_opportunities": opportunities,
        "served_fraction": served / opportunities,
    }


def _validate_panel_identity(
    rows: Sequence[Mapping[str, Any]],
    *,
    worlds: Sequence[int],
    lineages: Sequence[int],
) -> dict[tuple[int, str, int], Mapping[str, Any]]:
    indexed: dict[tuple[int, str, int], Mapping[str, Any]] = {}
    for row in rows:
        world = int(row["world_seed"])
        lineage = int(row.get("lineage", row.get("initialization_seed")))
        arm = str(row["arm"])
        key = (world, arm, lineage)
        if key in indexed or arm not in ARMS:
            raise V018OracleError("duplicate or unknown V0.18 panel identity")
        indexed[key] = row
    expected = {
        (int(world), arm, int(lineage))
        for world in worlds
        for arm in ARMS
        for lineage in lineages
    }
    if set(indexed) != expected:
        raise V018OracleError("panel is not a complete rectangular V0.18 closure")
    for world in worlds:
        matched = [
            indexed[(int(world), arm, int(lineage))]
            for arm in ARMS
            for lineage in lineages
        ]
        if len({str(row["initial_world_sha256"]) for row in matched}) != 1:
            raise V018OracleError("matched arms do not share one initial world")
        if len({str(row["field_root_digest"]) for row in matched}) != 1:
            raise V018OracleError("matched arms do not share one keyed field")
    for lineage in lineages:
        matched = [
            indexed[(int(world), arm, int(lineage))]
            for world in worlds
            for arm in ARMS
        ]
        for name in ("q1_checkpoint_sha256", "q2_checkpoint_sha256"):
            if len({str(row[name]) for row in matched}) != 1:
                raise V018OracleError(f"matched rows do not share one {name}")
    return indexed


def merge_shards(
    shard_files: Sequence[Path],
    output_dir: Path,
    *,
    worlds: Sequence[int],
    lineages: Sequence[int],
    q2_root: Path = V014_GATE_ROOT,
    v03_root: Path = V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
    contract_path: Path = V018_CONTRACT_PATH,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge a complete 3-arm panel and invoke the pure V0.18 gate."""

    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V018OracleError(f"refusing to overwrite merge output: {output}")
    validate_r2_provenance(provenance)
    validate_v018_contract(contract_path)
    _V015.validate_v015_contract()
    _V015.validate_v014_gate_receipts(q2_root)
    # The merge contract does not reopen simulator data, but authenticating
    # the frozen prereg and source roots keeps a hand-assembled shard panel
    # from being mistaken for this declared experiment.
    _ = _V015._V013.read_prereg(prereg_path)
    if not Path(v03_root).is_dir():
        raise V018OracleError(f"missing frozen Q1 root: {v03_root}")
    payloads = [_read_json(Path(path)) for path in shard_files]
    rows: list[dict[str, Any]] = []
    for payload in payloads:
        if payload.get("schema") != SHARD_SCHEMA:
            raise V018OracleError("a shard schema is stale")
        row = payload.get("row")
        if not isinstance(row, Mapping):
            raise V018OracleError("shard row is missing")
        if payload.get("row_sha256") != canonical_sha256(row):
            raise V018OracleError("shard row digest failed")
        if payload.get("q1_checkpoint_sha256") != row.get("q1_checkpoint_sha256"):
            raise V018OracleError("shard Q1 receipt mismatch")
        if payload.get("q2_checkpoint_sha256") != row.get("q2_checkpoint_sha256"):
            raise V018OracleError("shard Q2 receipt mismatch")
        if payload.get("execution_attempt") != R2_EXECUTION_ATTEMPT:
            raise V018OracleError("shard execution attempt mismatch")
        if payload.get("provenance_sha256") != provenance["provenance_sha256"]:
            raise V018OracleError("shard provenance digest mismatch")
        if payload.get("provenance") != dict(provenance):
            raise V018OracleError("shard provenance differs from requested R2 closure")
        if payload.get("r2_code_manifest_sha256") != provenance["r2_code_manifest"]["sha256"]:
            raise V018OracleError("shard R2 code-manifest digest mismatch")
        if payload.get("performance_addendum_sha256") != provenance["performance_addendum"]["sha256"]:
            raise V018OracleError("shard performance-addendum digest mismatch")
        if payload.get("r1_abort_receipt_sha256") != provenance["r1_abort_receipt"]["sha256"]:
            raise V018OracleError("shard R1 abort-receipt digest mismatch")
        rows.append(dict(row))
    indexed = _validate_panel_identity(rows, worlds=worlds, lineages=lineages)
    pooled = {
        arm: _pool(
            [
                indexed[(int(world), arm, int(lineage))]
                for world in worlds
                for lineage in lineages
            ]
        )
        for arm in ARMS
    }
    compatibility = all(bool(row.get("compatibility_proof_passed")) for row in rows)
    source_panel = _source_diagnostics_panel_summary(rows)
    source_passed = bool(source_panel["passed"])
    gate = adjudicate_v018_analytic_gate(
        rows,
        worlds=tuple(int(value) for value in worlds),
        lineages=tuple(int(value) for value in lineages),
        compatibility_proof_passed=compatibility,
        source_diagnostics_passed=source_passed,
    )
    contract = contract_receipt(
        worlds=worlds, lineages=lineages, contract_path=contract_path
    )
    result = {
        "schema": RESULT_SCHEMA,
        "execution_attempt": R2_EXECUTION_ATTEMPT,
        "claim_ceiling": "TRAIN_ANALYTIC_DIAGNOSTIC_NO_LEARNER_NO_TEST_NO_EFFICACY_CLAIM",
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "provenance": dict(provenance),
        "provenance_sha256": provenance["provenance_sha256"],
        "performance_addendum_sha256": provenance["performance_addendum"]["sha256"],
        "r2_code_manifest_sha256": provenance["r2_code_manifest"]["sha256"],
        "r1_abort_receipt_sha256": provenance["r1_abort_receipt"]["sha256"],
        "r4_pass_provenance": dict(provenance["r4_pass"]),
        "world_seeds": [int(value) for value in worlds],
        "lineages": [int(value) for value in lineages],
        "field_component": FIELD_COMPONENT,
        "rows": sorted(
            rows,
            key=lambda row: (
                int(row["world_seed"]),
                ARMS.index(str(row["arm"])),
                int(row.get("lineage", row.get("initialization_seed"))),
            ),
        ),
        "summaries": {
            "pooled_by_arm": pooled,
            "source_diagnostics": source_panel,
            "gate": gate,
        },
        "gate": gate,
    }
    result["result_sha256"] = canonical_sha256(result)
    output.mkdir(parents=True, exist_ok=False)
    result_file = output / "result.json"
    result_file.write_bytes(_canonical_bytes(result))
    result_digest = file_sha256(result_file)
    seal = {
        "schema": RESULT_SEAL_SCHEMA,
        "result_file_sha256": result_digest,
        "result_sha256": result["result_sha256"],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "provenance_sha256": provenance["provenance_sha256"],
        "r2_code_manifest_sha256": provenance["r2_code_manifest"]["sha256"],
        "performance_addendum_sha256": provenance["performance_addendum"]["sha256"],
        "r1_abort_receipt_sha256": provenance["r1_abort_receipt"]["sha256"],
        "r4_pass_result_sha256": provenance["r4_pass"]["result"]["sha256"],
    }
    (output / "result-seal.json").write_bytes(_canonical_bytes(seal))
    print(
        f"decision={gate['decision']} "
        f"base={pooled['BASE']['ratio_of_sums_ee_bits_per_j']:.9g} "
        f"exact={pooled['EXACT_ZR']['ratio_of_sums_ee_bits_per_j']:.9g} "
        f"nominal={pooled['NOMINAL_ZR']['ratio_of_sums_ee_bits_per_j']:.9g}"
    )
    return result


def _ints(values: Sequence[int] | None, default: Sequence[int]) -> tuple[int, ...]:
    result = tuple(int(value) for value in (values or default))
    if not result or len(set(result)) != len(result):
        raise V018OracleError("CLI values must be distinct and nonempty")
    return result


def _add_r2_provenance_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the mandatory immutable R2 provenance bindings to a CLI command."""

    parser.add_argument("--performance-addendum", type=Path, required=True)
    parser.add_argument("--performance-addendum-sha256", required=True)
    parser.add_argument("--r2-code-manifest", type=Path, required=True)
    parser.add_argument("--r2-code-manifest-sha256", required=True)
    parser.add_argument("--r1-abort-receipt", type=Path, required=True)
    parser.add_argument("--r1-abort-receipt-sha256", required=True)
    parser.add_argument("--r4-result", type=Path, required=True)
    parser.add_argument("--r4-result-sha256", required=True)
    parser.add_argument("--r4-receipt", type=Path, required=True)
    parser.add_argument("--r4-receipt-sha256", required=True)
    parser.add_argument("--r4-artifact-manifest", type=Path, required=True)
    parser.add_argument("--r4-artifact-manifest-sha256", required=True)
    parser.add_argument("--r4-code-manifest", type=Path, required=True)
    parser.add_argument("--r4-code-manifest-sha256", required=True)
    parser.add_argument("--r4-independent-validation", type=Path, required=True)
    parser.add_argument("--r4-independent-validation-sha256", required=True)


def _r2_provenance_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return build_r2_provenance(
        performance_addendum=args.performance_addendum,
        performance_addendum_sha256=args.performance_addendum_sha256,
        r2_code_manifest=args.r2_code_manifest,
        r2_code_manifest_sha256=args.r2_code_manifest_sha256,
        r1_abort_receipt=args.r1_abort_receipt,
        r1_abort_receipt_sha256=args.r1_abort_receipt_sha256,
        r4_result=args.r4_result,
        r4_result_sha256=args.r4_result_sha256,
        r4_receipt=args.r4_receipt,
        r4_receipt_sha256=args.r4_receipt_sha256,
        r4_artifact_manifest=args.r4_artifact_manifest,
        r4_artifact_manifest_sha256=args.r4_artifact_manifest_sha256,
        r4_code_manifest=args.r4_code_manifest,
        r4_code_manifest_sha256=args.r4_code_manifest_sha256,
        r4_independent_validation=args.r4_independent_validation,
        r4_independent_validation_sha256=args.r4_independent_validation_sha256,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--json", action="store_true")
    shard = sub.add_parser("shard")
    shard.add_argument("--world", type=int, required=True)
    shard.add_argument("--lineage", type=int, choices=LINEAGES, required=True)
    shard.add_argument("--arm", choices=ARMS, required=True)
    shard.add_argument("--output", type=Path, required=True)
    shard.add_argument("--q2-root", type=Path, default=V014_GATE_ROOT)
    shard.add_argument("--v03-root", type=Path, default=V03_ROOT)
    shard.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    shard.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    shard.add_argument("--contract", type=Path, default=V018_CONTRACT_PATH)
    _add_r2_provenance_arguments(shard)
    merge = sub.add_parser("merge")
    merge.add_argument("--shards", type=Path, nargs="+", required=True)
    merge.add_argument("--output", type=Path, required=True)
    merge.add_argument("--world", type=int, action="append", default=None)
    merge.add_argument("--lineage", type=int, action="append", choices=LINEAGES, default=None)
    merge.add_argument("--contract", type=Path, default=V018_CONTRACT_PATH)
    _add_r2_provenance_arguments(merge)
    args = parser.parse_args(argv)
    if args.command == "plan":
        payload = contract_receipt()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else canonical_sha256(payload))
        return 0
    if args.command == "shard":
        provenance = _r2_provenance_from_args(args)
        run_shard(
            world_seed=args.world,
            arm=args.arm,
            lineage=args.lineage,
            output_dir=args.output,
            q2_root=args.q2_root,
            v03_root=args.v03_root,
            prereg_path=args.prereg,
            tle_root=args.tle_root,
            contract_path=args.contract,
            provenance=provenance,
        )
        return 0
    worlds = _ints(args.world, WORLD_SEEDS)
    lineages = _ints(args.lineage, LINEAGES)
    provenance = _r2_provenance_from_args(args)
    merge_shards(
        args.shards,
        args.output,
        worlds=worlds,
        lineages=lineages,
        contract_path=args.contract,
        provenance=provenance,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
