#!/usr/bin/env python3
"""Execution-ready V0.23 LC-SRS physical/source adapter.

The staged gate runner owns shard identity and the final JSON receipt.  This
module owns the physical source boundary for one declared TRAIN world.  It
deliberately keeps simulator imports lazy: importing the module is safe for
unit tests, while :class:`V023RuntimeSourceAdapter` opens the authenticated
TLE/checkpoint and simulator only after preflight has passed.

The source worker performs the following frozen sequence:

* restore the audited V0.20 Q1/Q2 background and follow it through one ten
  step TRAIN episode;
* at every noninitial anchor (t=1..9), capture Interface A and enumerate the
  complete outcome-blind V0.23 topology;
* for every enumerated pair, evaluate all 32 matched 00/10/01/11 physical
  profile draws using one keyed field per (family, world, anchor, draw);
* bind the exact V0.23 teacher/pipeline objects; and
* persist a complete canonical JSON index plus an ``allow_pickle=False`` NPZ
  sidecar containing the numeric arrays needed by a fit worker.

No learner update, TEST split, or episode-policy training is performed here.
The public ``generate_source_shard`` method is compatible with the staged
runner's adapter protocol and returns a payload which
``run_source_stage`` seals atomically.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (  # noqa: E402
    LCSRSAnchorRecord,
    LCSRSPairTargets,
)
from mcrl.runtime.ee_axis_coalition_residual_c3 import (  # noqa: E402
    COALITION_RESIDUAL_C3_SCHEMA_VERSION,
)
from mcrl.runtime.ee_axis_lcsrs_c3_encoder import (  # noqa: E402
    LCSRSC3PredecisionCapture,
    capture_lcsrs_c3_predecision,
)
from mcrl.runtime.ee_axis_lcsrs_c3_pipeline import (  # noqa: E402
    LCSRSC3BoundAnchor,
    bind_lcsrs_c3_anchor,
)
from mcrl.runtime.ee_axis_lcsrs_c3_teacher import (  # noqa: E402
    LCSRSFourProfileDraw,
    LCSRSTwoUserTeacher,
    build_lcsrs_topology_teacher,
    lcsrs_action_sha256,
)
from mcrl.runtime.ee_axis_lcsrs_c3_placebo import (  # noqa: E402
    build_lcsrs_matched_placebo,
    placebo_stratum,
)
from mcrl.runtime.ee_axis_lcsrs_c3_gate_metrics import (  # noqa: E402
    comparison_tolerance,
    strict_direction,
)
from mcrl.runtime.ee_axis_ops3 import (  # noqa: E402
    OPS3_HORIZON,
    OPS3_INTERVAL_S,
    OPS3_KAPPA_BITS,
    OPS3_LAMBDA_BITS_PER_J,
    OPS3_SCHEMA,
)
from mcrl.runtime.ee_axis_v014_q2_state import (  # noqa: E402
    V014_Q2_STATE_DIM,
    V014_Q2_STATE_SCHEMA,
    V014_Q2_STATE_SCHEMA_SHA256,
)
from mcrl.runtime.ee_axis_lcsrs_c3_topology import (  # noqa: E402
    LCSRSC3AnchorTopologyReceipt,
    LCSRSC3ClosurePair,
    LCSRSC3NoCloseControl,
)
from mcrl.algorithms.ee_axis_lcsrs_three_route import DetachedQ12Snapshot  # noqa: E402


SOURCE_ARTIFACT_SCHEMA = (
    "multi-catfish-mcrl-v023-lcsrs-source-artifact-v1"
)
SOURCE_ARTIFACT_VERSION = 1
PROFILE_ORDER = ("00", "10", "01", "11")
WORLD_PHASES = tuple(range(1, 10))
DRAW_COUNT = 32
STEPS_PER_EPISODE = 10
USERS = 100
ACTIONS = 28
FIELD_COMPONENT = "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
PLACEBO_KEY = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
PLACEBO_KEY_SHA256 = "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"
EXECUTION_ADDENDUM_PATH = (
    REPO / "docs" / "MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
)
EXECUTION_ADDENDUM_SHA256 = "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070"
Q12_ROOT = REPO / ".scratch" / "multi-catfish-v020-c3-source-audit"
Q12_REPRICING_CONTRACT_PATH = (
    Q12_ROOT / "Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md"
)
Q12_REPRICING_CONTRACT_SHA256 = (
    "34732dd3f65ffebf760313c2ffd235e0ecbd406ba6065dbce5635778550ef4a9"
)
Q12_EXECUTION_CONTRACT_PATH = (
    Q12_ROOT / "Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md"
)
Q12_EXECUTION_CONTRACT_SHA256 = (
    "ea36414aac87b3ef5ba48dbe753e73ff21a0e164d54cdb3edbb899b509edd48c"
)
Q12_FIT_RUNNER_PATH = Q12_ROOT / "run_v020_repriced_q1_q2.py"
Q12_FIT_RUNNER_SHA256 = (
    "f55b882149ce49505c694423520a6a807d6a90babcbce340cb5ba449adea1814"
)
Q12_AUTHORITY_FILE_SHA256 = (
    "a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e"
)
Q12_AUTHORITY_BODY_SHA256 = (
    "50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48"
)
OPS3_FORMULA_PATH = REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3.py"
OPS3_FORMULA_SHA256 = "68251ff750410ff74abfb412df83bafef459831874abfcfbee6e1e04d1adea02"
OPS3_LIVE_PATH = REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3_live.py"
OPS3_LIVE_SHA256 = "6847069235ce3789c9f2f76bfd1de9f7a4e02402788eed0fabcc0ab57faed35a"
Q2_STATE_PATH = REPO / "src" / "mcrl" / "runtime" / "ee_axis_v014_q2_state.py"
Q2_STATE_FILE_SHA256 = "412ce464975e369e44cbb1825e02f1ce36b2ce84882bf110a63b351d63de07f7"
LAMBDA_BITS_PER_J = float.fromhex("0x1.c3c0a7b6b86d3p+26")
KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)


class V023SourceAdapterError(RuntimeError):
    """The physical source boundary failed closed."""


def _step_result_observation(environment: Any, result: Any) -> Any:
    """Get the successor observation from the wrapper's full step outcome.

    ``TrainerEnvironment.step`` intentionally returns the compact
    ``StepResult`` consumed by the learner.  The complete physical
    ``StepOutcome`` (including its observation) is published separately as
    ``last_outcome``.  Keep the direct ``result.observation`` fallback for
    callers that still provide a native ``StepOutcome`` at this seam.
    """

    full_outcome = getattr(environment, "last_outcome", None)
    observation = getattr(full_outcome, "observation", None)
    if observation is None:
        observation = getattr(result, "observation", None)
    if observation is None:
        raise V023SourceAdapterError(
            "step result omitted observation and environment has no full last_outcome"
        )
    return observation


def _load_module(name: str, path: Path) -> Any:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023SourceAdapterError(f"required runner is missing: {source}")
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise V023SourceAdapterError(f"cannot import required runner: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    """Canonical ASCII JSON used for every embedded receipt hash."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=_canonical_default,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023SourceAdapterError("value is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023SourceAdapterError(f"expected regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json_object(path: Path, *, field: str) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023SourceAdapterError(f"{field} is missing or is a symlink")
    try:
        value = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023SourceAdapterError(f"{field} is not readable ASCII JSON") from error
    if not isinstance(value, dict):
        raise V023SourceAdapterError(f"{field} root is not an object")
    return value


def _authenticate_q12_authority(
    *,
    lineage: int,
    q1_receipt: Mapping[str, Any],
    q2_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate the repriced Q1/Q2 lineage behind every C3 anchor.

    The V0.20 convenience loader authenticates the combined checkpoint bytes,
    but the V0.23 context gate also needs the upstream target formula,
    multiplier, horizon, source files, and checkpoint-to-authority link.  Keep
    that proof explicit so an old OPS-3 runtime default cannot be mistaken for
    the repriced Q2 teacher.
    """

    if lineage != 2026092101:
        raise V023SourceAdapterError("Q1/Q2 authority lineage drifted")
    for path, expected, field in (
        (
            Q12_REPRICING_CONTRACT_PATH,
            Q12_REPRICING_CONTRACT_SHA256,
            "Q1/Q2 repricing contract",
        ),
        (
            Q12_EXECUTION_CONTRACT_PATH,
            Q12_EXECUTION_CONTRACT_SHA256,
            "Q1/Q2 execution contract",
        ),
        (Q12_FIT_RUNNER_PATH, Q12_FIT_RUNNER_SHA256, "Q1/Q2 fit runner"),
        (OPS3_FORMULA_PATH, OPS3_FORMULA_SHA256, "OPS-3 formula runtime"),
        (OPS3_LIVE_PATH, OPS3_LIVE_SHA256, "OPS-3 live projection runtime"),
        (Q2_STATE_PATH, Q2_STATE_FILE_SHA256, "target-free Q2 state runtime"),
    ):
        if file_sha256(path) != expected:
            raise V023SourceAdapterError(f"{field} bytes changed")

    authority_path = (
        Q12_ROOT
        / "repriced-q1-q2-fit"
        / f"lineage-{lineage}"
        / "authority.json"
    )
    if file_sha256(authority_path) != Q12_AUTHORITY_FILE_SHA256:
        raise V023SourceAdapterError("Q1/Q2 authority file bytes changed")
    authority = _load_json_object(authority_path, field="Q1/Q2 authority")
    authority_seal = authority.get("authority_sha256")
    if authority_seal != Q12_AUTHORITY_BODY_SHA256:
        raise V023SourceAdapterError("Q1/Q2 authority body seal drifted")
    unsigned = dict(authority)
    unsigned.pop("authority_sha256", None)
    if canonical_sha256(unsigned) != authority_seal:
        raise V023SourceAdapterError("Q1/Q2 authority body does not authenticate")
    if (
        authority.get("schema")
        != "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-authority"
        or authority.get("claim_ceiling")
        != "SOURCE_ONLY_NO_SIMULATOR_NO_TEST_NO_EPISODE_EE"
        or authority.get("contract_sha256") != Q12_EXECUTION_CONTRACT_SHA256
        or authority.get("repricing_contract_sha256")
        != Q12_REPRICING_CONTRACT_SHA256
        or authority.get("lambda_bits_per_j_hex") != LAMBDA_BITS_PER_J.hex()
        or authority.get("lambda_bits_per_j") != LAMBDA_BITS_PER_J
        or authority.get("lineage") != lineage
        or authority.get("q1_updates") != 10
        or authority.get("q2_initialization") != 2026108101
        or authority.get("q2_rungs") != [3, 10, 30, 100, 300, 1000, 3000]
        or authority.get("test_split_opened") is not False
        or authority.get("simulator_run") is not False
        or authority.get("episode_training") is not False
    ):
        raise V023SourceAdapterError("Q1/Q2 authority semantics drifted")
    if _jsonable(q1_receipt.get("config")) != _jsonable(authority.get("q1_config")):
        raise V023SourceAdapterError("Q1 checkpoint config disagrees with authority")
    if _jsonable(q2_receipt.get("config")) != _jsonable(authority.get("q2_config")):
        raise V023SourceAdapterError("Q2 checkpoint config disagrees with authority")
    if (
        q1_receipt.get("update_count") != 10
        or q2_receipt.get("update_count") != 3000
        or q1_receipt.get("train_seed") != lineage
        or q2_receipt.get("train_seed") != 2026108101
        or q1_receipt.get("checkpoint_path") != q2_receipt.get("checkpoint_path")
        or q1_receipt.get("checkpoint_sha256") != q2_receipt.get("checkpoint_sha256")
    ):
        raise V023SourceAdapterError("Q1/Q2 checkpoint receipts disagree with authority")

    checkpoint_path = Path(str(q1_receipt.get("checkpoint_path"))).resolve()
    checkpoint_sha = _digest(
        q1_receipt.get("checkpoint_sha256"), field="Q1/Q2 checkpoint SHA-256"
    )
    if file_sha256(checkpoint_path) != checkpoint_sha:
        raise V023SourceAdapterError("Q1/Q2 combined checkpoint bytes changed")
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    except Exception as error:
        raise V023SourceAdapterError("Q1/Q2 combined checkpoint cannot be reopened") from error
    if not isinstance(checkpoint, Mapping) or (
        checkpoint.get("schema")
        != "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-checkpoint"
        or checkpoint.get("authority_sha256") != authority_seal
        or checkpoint.get("lineage") != lineage
        or checkpoint.get("q2_initialization") != 2026108101
        or checkpoint.get("q1_update_count") != 10
        or checkpoint.get("q2_update_count") != 3000
        or checkpoint.get("q1_head_index") != 0
    ):
        raise V023SourceAdapterError("Q1/Q2 checkpoint is not bound to its authority")

    code_hashes = authority.get("code_file_sha256s")
    target_hashes = authority.get("q2_repriced_target_file_sha256s")
    if not isinstance(code_hashes, Mapping) or not isinstance(target_hashes, Mapping):
        raise V023SourceAdapterError("Q1/Q2 authority file maps are malformed")
    if len(target_hashes) != 7:
        raise V023SourceAdapterError("Q2 repriced target panel is incomplete")
    for label, entries in (("code", code_hashes), ("target", target_hashes)):
        for relative, expected in entries.items():
            if not isinstance(relative, str):
                raise V023SourceAdapterError(f"Q1/Q2 {label} path is malformed")
            digest = _digest(expected, field=f"Q1/Q2 {label} SHA-256")
            candidate = (REPO / relative).resolve()
            if not candidate.is_relative_to(REPO.resolve()):
                raise V023SourceAdapterError(f"Q1/Q2 {label} path escapes repository")
            if file_sha256(candidate) != digest:
                raise V023SourceAdapterError(f"Q1/Q2 {label} bytes changed: {relative}")
    runner_relative = Q12_FIT_RUNNER_PATH.relative_to(REPO).as_posix()
    if code_hashes.get(runner_relative) != Q12_FIT_RUNNER_SHA256:
        raise V023SourceAdapterError("Q1/Q2 fit runner is absent from its authority")

    return {
        "schema": "multi-catfish-mcrl-v023-q12-authority-binding-v1",
        "authority_path": authority_path.relative_to(REPO).as_posix(),
        "authority_file_sha256": Q12_AUTHORITY_FILE_SHA256,
        "authority_body_sha256": Q12_AUTHORITY_BODY_SHA256,
        "execution_contract_path": Q12_EXECUTION_CONTRACT_PATH.relative_to(REPO).as_posix(),
        "execution_contract_sha256": Q12_EXECUTION_CONTRACT_SHA256,
        "repricing_contract_path": Q12_REPRICING_CONTRACT_PATH.relative_to(REPO).as_posix(),
        "repricing_contract_sha256": Q12_REPRICING_CONTRACT_SHA256,
        "fit_runner_path": runner_relative,
        "fit_runner_sha256": Q12_FIT_RUNNER_SHA256,
        "ops3_formula_path": OPS3_FORMULA_PATH.relative_to(REPO).as_posix(),
        "ops3_formula_sha256": OPS3_FORMULA_SHA256,
        "ops3_live_path": OPS3_LIVE_PATH.relative_to(REPO).as_posix(),
        "ops3_live_sha256": OPS3_LIVE_SHA256,
        "q2_state_path": Q2_STATE_PATH.relative_to(REPO).as_posix(),
        "q2_state_file_sha256": Q2_STATE_FILE_SHA256,
        "checkpoint_path": checkpoint_path.relative_to(REPO.resolve()).as_posix(),
        "checkpoint_sha256": checkpoint_sha,
        "q2_target_file_count": len(target_hashes),
        "q2_target_files_sha256": canonical_sha256(dict(target_hashes)),
        "source_sha256": _digest(
            authority.get("source_sha256"), field="Q1/Q2 source SHA-256"
        ),
        "lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
        "ops3_runtime_default_lambda_hex": OPS3_LAMBDA_BITS_PER_J.hex(),
        "ops3_runtime_default_used_for_diagnostic_target": False,
        "ops3_horizon": OPS3_HORIZON,
        "ops3_interval_s_hex": float(OPS3_INTERVAL_S).hex(),
        "q2_state_schema": V014_Q2_STATE_SCHEMA,
        "q2_state_schema_sha256": V014_Q2_STATE_SCHEMA_SHA256,
        "q2_state_dim": V014_Q2_STATE_DIM,
        "target_free_inference": True,
    }


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023SourceAdapterError(f"{field} is not a lowercase SHA-256")
    return value


def _array_digest(value: object, *, domain: str = "source-array-v1") -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _array_metadata(arrays: Mapping[str, np.ndarray]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name in sorted(arrays):
        array = np.ascontiguousarray(np.asarray(arrays[name]))
        result[name] = {
            "dtype": array.dtype.str,
            "shape": list(array.shape),
            "sha256": _array_digest(array),
        }
    return result


def _jsonable(value: object) -> object:
    """Convert runtime records to finite JSON without losing integer IDs."""

    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (bool, int, str)) or value is None:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise V023SourceAdapterError("non-finite float in source receipt")
        return value
    raise TypeError(f"unsupported source receipt value: {type(value).__name__}")


def _rng_digest(state: object) -> str:
    return hashlib.sha256(repr(state).encode("utf-8")).hexdigest()


def _rng_state_unchanged(before: object, after: object) -> bool:
    """Compare copied NumPy generator states without ndarray truth errors."""

    return _rng_digest(before) == _rng_digest(after)


def _masked_argmax(values: object, mask: object) -> np.ndarray:
    scores = np.asarray(values, dtype=np.float64)
    legal = np.asarray(mask)
    if scores.ndim != 2 or scores.shape[1] != ACTIONS:
        raise V023SourceAdapterError("Q surface must have shape (U,28)")
    if legal.dtype != np.bool_ or legal.shape != scores.shape:
        raise V023SourceAdapterError("native mask disagrees with Q surface")
    if not np.all(np.isfinite(scores)) or not np.all(np.any(legal, axis=1)):
        raise V023SourceAdapterError("Q surface is non-finite or unselectable")
    return np.argmax(np.where(legal, scores, -np.inf), axis=1).astype(np.int64)


def _action_digest(actions: object) -> str:
    values = np.asarray(actions, dtype=np.int64)
    if values.ndim != 1:
        raise V023SourceAdapterError("action vector must be one-dimensional")
    # Keep the source receipt byte-for-byte aligned with the binding teacher
    # class.  In particular, its grammar includes the vector length; a local
    # hash that omits that length would be rejected by LCSRSFourProfileDraw.
    try:
        return lcsrs_action_sha256(values)
    except Exception as error:
        raise V023SourceAdapterError("action vector cannot be hashed") from error


def _profile_actions(
    reference: np.ndarray,
    users: np.ndarray,
    proposed: np.ndarray,
) -> dict[str, np.ndarray]:
    if users.shape != (2,) or proposed.shape != (2,):
        raise V023SourceAdapterError("a physical teacher must name two users")
    result = {code: np.array(reference, dtype=np.int64, copy=True) for code in PROFILE_ORDER}
    result["10"][int(users[0])] = int(proposed[0])
    result["01"][int(users[1])] = int(proposed[1])
    result["11"][users] = proposed
    return result


def _ratio_sign_receipt(
    *,
    reference_bits: float,
    reference_energy_j: float,
    joint_bits: float,
    joint_energy_j: float,
) -> dict[str, float | int | bool]:
    """Apply the contract's operand-scaled ratio sign comparison exactly."""

    b0 = float(reference_bits)
    e0 = float(reference_energy_j)
    b1 = float(joint_bits)
    e1 = float(joint_energy_j)
    if (
        not all(math.isfinite(value) for value in (b0, e0, b1, e1))
        or b0 < 0.0
        or b1 < 0.0
        or e0 <= 0.0
        or e1 <= 0.0
    ):
        raise V023SourceAdapterError("ratio-sign inputs are outside their physical domain")
    left_product = b1 * e0
    right_product = b0 * e1
    cross_product = left_product - right_product
    cross_tolerance = comparison_tolerance(left_product, right_product)
    cross_sign = strict_direction(left_product, right_product)
    delta_bits = b1 - b0
    priced_energy_delta = (b0 / e0) * (e1 - e0)
    local_price_surplus = delta_bits - priced_energy_delta
    # ``cross_product = e0 * local_price_surplus``.  Transform the robust
    # cross-product tolerance through that exact positive scale so a numerical
    # tie cannot become a spurious local-price win after cancellation.
    local_tolerance = cross_tolerance / e0
    local_sign = (
        1
        if local_price_surplus > local_tolerance
        else -1
        if local_price_surplus < -local_tolerance
        else 0
    )
    return {
        "ratio_cross_product": float(cross_product),
        "ratio_sign": int(cross_sign),
        "ratio_tolerance": float(cross_tolerance),
        "ratio_identity_value_bits": float(local_price_surplus),
        "ratio_local_tolerance": float(local_tolerance),
        # A mismatch is a per-draw physical-mechanics failure.  The source
        # receipt must retain that finite draw so the frozen >=90% denominator
        # can be evaluated; it is not an integrity/mutation failure.
        "ratio_sign_identity_pass": bool(cross_sign == local_sign),
    }


def _closure_mechanics_failure_codes(
    records: Mapping[str, Mapping[str, Any]],
    *,
    source: tuple[int, int],
    destinations: set[tuple[int, int]],
    members: np.ndarray,
    ratio_sign_identity_pass: bool,
) -> list[str]:
    """Return deterministic, countable closure/service failures for one draw.

    These checks are deliberately separate from integrity guards.  A finite
    physical profile that loses the source beam, opens a new beam, or drops
    service is still a complete observed row and must remain in the source
    denominator.  Mutation, non-finite data, malformed actions, and formula
    identity failures are handled by their existing fail-closed paths.
    """

    active_sets = {
        code: {
            tuple(int(value) for value in key)
            for key in records[code]["active_beam_keys"]
        }
        for code in PROFILE_ORDER
    }
    failures: list[str] = []
    if any(source not in active_sets[code] for code in ("00", "10", "01")):
        failures.append("SOURCE_NOT_RETAINED_00_10_01")
    if source in active_sets["11"]:
        failures.append("SOURCE_NOT_REMOVED_11")
    if not destinations.issubset(active_sets["00"]):
        failures.append("DESIGNATED_DESTINATION_ABSENT_00")
    if not destinations.issubset(active_sets["11"]):
        failures.append("DESIGNATED_DESTINATION_LOST_11")
    if not active_sets["11"].issubset(active_sets["00"]):
        failures.append("NEW_BEAM_OPENED_11")
    if active_sets["11"] != active_sets["00"] - {source}:
        failures.append("NOT_EXACT_SOURCE_ONLY_REMOVAL_11")
    if any(
        not all(bool(records[code]["served"][int(user)]) for code in PROFILE_ORDER)
        for user in members.tolist()
    ):
        failures.append("MEMBER_UNSERVED")
    if int(records["11"]["served_users"]) < int(records["00"]["served_users"]):
        failures.append("SERVE_COUNT_DECREASED_11")
    if not ratio_sign_identity_pass:
        failures.append("RATIO_SIGN_IDENTITY")
    return failures


def _evaluation_record(
    evaluation: object,
    *,
    actions: np.ndarray,
    interval_s: float,
) -> dict[str, Any]:
    rates = np.asarray(getattr(evaluation, "link_rate_bps"), dtype=np.float64)
    served = np.asarray(
        getattr(getattr(evaluation, "resolution"), "served"), dtype=np.bool_
    )
    per_user_bits = interval_s * rates
    energy = interval_s * float(getattr(evaluation, "system_power_w"))
    radiating = getattr(evaluation, "radiating")
    norads = np.asarray(getattr(radiating, "norad_ids"), dtype=np.int64)
    cells = np.asarray(getattr(radiating, "cell_ids"), dtype=np.int64)
    powers = np.asarray(getattr(radiating, "power_w"), dtype=np.float64)
    link_power = np.asarray(getattr(evaluation, "link_power_w"), dtype=np.float64)
    sinr = np.asarray(getattr(evaluation, "link_sinr"), dtype=np.float64)
    if (
        rates.ndim != 1
        or per_user_bits.shape != served.shape
        or link_power.shape != rates.shape
        or sinr.shape != rates.shape
        or not np.all(np.isfinite(per_user_bits))
        or np.any(per_user_bits < 0.0)
        or not math.isfinite(energy)
        or energy <= 0.0
        or norads.ndim != 1
        or cells.shape != norads.shape
        or powers.shape != norads.shape
        or not np.all(np.isfinite(link_power))
        or not np.all(np.isfinite(sinr))
    ):
        raise V023SourceAdapterError("physical profile is malformed")
    beam_keys = [[int(n), int(c)] for n, c in zip(norads.tolist(), cells.tolist(), strict=True)]
    total_bits = math.fsum(float(value) for value in per_user_bits.tolist())
    active_satellites = sorted({int(value) for value in norads.tolist()})
    fixed_power = float(getattr(evaluation, "fixed_power_w"))
    system_power = float(getattr(evaluation, "system_power_w"))
    if not math.isfinite(fixed_power) or not math.isfinite(system_power):
        raise V023SourceAdapterError("profile energy components are non-finite")
    return {
        "actions": [int(value) for value in actions.tolist()],
        "action_sha256": _action_digest(actions),
        "per_user_bits": [float(value) for value in per_user_bits.tolist()],
        "link_rate_bps": [float(value) for value in rates.tolist()],
        "link_power_w": [float(value) for value in link_power.tolist()],
        "link_sinr": [float(value) for value in sinr.tolist()],
        "served": [bool(value) for value in served.tolist()],
        "served_users": int(np.count_nonzero(served)),
        "total_bits": float(total_bits),
        "system_power_w": system_power,
        "fixed_power_w": fixed_power,
        "interval_s": float(interval_s),
        "energy_j": float(energy),
        "g_bits": float(total_bits - LAMBDA_BITS_PER_J * energy),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / energy),
        "active_beam_keys": beam_keys,
        "active_satellites": active_satellites,
        "beam_power_w": [float(value) for value in powers.tolist()],
    }


def _formula_record(result: object) -> dict[str, Any]:
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
    result_dict: dict[str, Any] = {
        "schema": str(getattr(result, "schema")),
        "schema_version": int(COALITION_RESIDUAL_C3_SCHEMA_VERSION),
    }
    for name in fields:
        value = getattr(result, name)
        result_dict[name] = _jsonable(value)
    result_dict["q3_sha256"] = _array_digest(
        np.asarray(getattr(result, "q3_values"), dtype=np.float64),
        domain="v023-q3-surface",
    )
    return result_dict


def _model_digest(q1: object, q2: object, q1_receipt: Mapping[str, Any], q2_receipt: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(b"v023-detached-q12-model-v1")
    for name, network, receipt in (("q1", q1, q1_receipt), ("q2", q2, q2_receipt)):
        digest.update(name.encode("ascii"))
        digest.update(canonical_bytes(dict(receipt)))
        state_dict = getattr(network, "state_dict", None)
        if not callable(state_dict):
            raise V023SourceAdapterError(f"{name} network has no state_dict")
        for key, tensor in sorted(state_dict().items()):
            array = np.asarray(tensor.detach().cpu().numpy())
            digest.update(key.encode("utf-8"))
            digest.update(_array_digest(array, domain="v023-q-parameter").encode("ascii"))
    return digest.hexdigest()


def _live_digest(v018: Any, environment: Any, rng: np.random.Generator) -> str:
    return str(v018._live_digest(environment, rng))


def _repriced_ops3_context(
    *,
    surfaces: Sequence[Any],
    q2_state: Any,
    masks: np.ndarray,
    opening: np.ndarray,
    q1_reference: np.ndarray,
    anchor_horizon: int,
) -> dict[str, Any]:
    """Recompute the frozen-lambda OPS-3 target from raw projected terms.

    ``build_ops3_live_surfaces`` currently uses the historical OPS-3 default
    multiplier.  Its 16 deployable features are multiplier-independent, so
    they remain the correct learned-Q2 input.  The diagnostic teacher is
    deliberately recomputed here at the repriced V0.20 multiplier and never
    copied from that historical ``surface.q2_values`` field.
    """

    rows = tuple(surfaces)
    if len(rows) != masks.shape[0]:
        raise V023SourceAdapterError("OPS-3 surface/user count drifted")
    if (
        float(OPS3_KAPPA_BITS) != KAPPA_BITS
        or OPS3_HORIZON != 3
        or float(OPS3_INTERVAL_S) <= 0.0
    ):
        raise V023SourceAdapterError("OPS-3 frozen constants drifted")
    states = np.asarray(q2_state.state_matrix, dtype=np.float32)
    if states.shape != (masks.shape[0], V014_Q2_STATE_DIM):
        raise V023SourceAdapterError("target-free Q2 state shape drifted")

    features: list[np.ndarray] = []
    persistence: list[np.ndarray] = []
    rates: list[np.ndarray] = []
    powers: list[np.ndarray] = []
    required: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    for user, surface in enumerate(rows):
        if (
            getattr(surface, "schema", None) != OPS3_SCHEMA
            or int(surface.horizon) != int(anchor_horizon)
            or int(surface.reference_action) != int(q1_reference[user])
            or not np.array_equal(np.asarray(surface.legal_mask), masks[user])
            or not np.array_equal(
                np.asarray(surface.opening_service_feasible), opening[user]
            )
        ):
            raise V023SourceAdapterError("OPS-3 surface identity/mask/timing drifted")
        feature = np.asarray(surface.features, dtype=np.float64)
        chi = np.asarray(surface.persistence, dtype=np.float64)
        rate = np.asarray(surface.rate_bps, dtype=np.float64)
        power = np.asarray(surface.marginal_power_w, dtype=np.float64)
        required_power = np.asarray(surface.required_power_w, dtype=np.float64)
        expected_matrix = feature.astype(np.float32).T.reshape(-1)
        if not np.array_equal(states[user], expected_matrix):
            raise V023SourceAdapterError("target-free Q2 state is not the OPS-3 feature surface")
        if (
            feature.shape != (ACTIONS, 16)
            or chi.shape != (OPS3_HORIZON, ACTIONS)
            or rate.shape != chi.shape
            or power.shape != chi.shape
            or required_power.shape != chi.shape
            or not np.all(np.isfinite(feature))
            or not np.all(np.isfinite(chi))
            or not np.all(np.isfinite(rate))
            or not np.all(np.isfinite(power))
            or not np.all(np.isfinite(required_power))
        ):
            raise V023SourceAdapterError("OPS-3 diagnostic arrays are malformed")
        if np.any((chi != 0.0) & (chi != 1.0)) or np.any(np.diff(chi, axis=0) > 0.0):
            raise V023SourceAdapterError("OPS-3 persistence is not absorbing")
        horizon = int(anchor_horizon)
        if horizon < OPS3_HORIZON and (
            np.any(chi[horizon:] != 0.0)
            or np.any(rate[horizon:] != 0.0)
            or np.any(power[horizon:] != 0.0)
            or np.any(required_power[horizon:] != 0.0)
        ):
            raise V023SourceAdapterError("OPS-3 values leaked beyond the valid horizon")
        if horizon == 0:
            if np.any(feature != 0.0):
                raise V023SourceAdapterError("terminal OPS-3 feature surface is not zero")
            normalized = np.zeros((ACTIONS,), dtype=np.float64)
        else:
            terms = (
                chi[:horizon]
                * float(OPS3_INTERVAL_S)
                * (rate[:horizon] - LAMBDA_BITS_PER_J * power[:horizon])
                - (1.0 - chi[:horizon]) * KAPPA_BITS
            )
            z2 = np.mean(terms, axis=0, dtype=np.float64)
            reference = int(q1_reference[user])
            normalized = (z2 - z2[reference]) / KAPPA_BITS
            normalized = np.where(masks[user], normalized, 0.0)
            if normalized[reference] != 0.0:
                raise V023SourceAdapterError("repriced OPS-3 reference is not exact zero")
        if not np.all(np.isfinite(normalized)):
            raise V023SourceAdapterError("repriced OPS-3 target is non-finite")
        features.append(feature)
        persistence.append(chi)
        rates.append(rate)
        powers.append(power)
        required.append(required_power)
        targets.append(normalized)
    return {
        "state_matrix": np.asarray(states, dtype=np.float32),
        "features": np.stack(features),
        "persistence": np.stack(persistence),
        "rate_bps": np.stack(rates),
        "marginal_power_w": np.stack(powers),
        "required_power_w": np.stack(required),
        "target_values": np.stack(targets),
        "horizon": int(anchor_horizon),
    }


def _native_q12_anchor(
    *,
    v018: Any,
    q1: Any,
    q2: Any,
    step_env: Any,
    observation: Any,
    model_digest: str,
) -> dict[str, Any]:
    """Capture authenticated native state and detached Q1+Q2 once."""

    native = v018._V015._V013.encode_ee_axis_state(step_env, observation)
    native.verify()
    provenance = getattr(observation, "observation_provenance", None)
    if provenance is None:
        raise V023SourceAdapterError("native observation has no provenance")
    provenance.verify()
    if provenance.content_digest == "":
        raise V023SourceAdapterError("native observation provenance is unsealed")
    masks = np.asarray(native.action_masks, dtype=np.bool_)
    with torch.no_grad():
        q1_values = np.asarray(
            v018._q1_values(q1, native.state_matrix, masks), dtype=np.float64
        )
        q1_reference = v018._V015.select_actions(
            q1_values,
            np.zeros_like(q1_values),
            np.zeros_like(q1_values),
            masks,
            include_c3=False,
        )
        anchor = v018.snapshot_ops3_anchor(step_env, observation)
        projection = v018.project_ops3_anchor(anchor)
        ops3_surfaces = v018.build_ops3_live_surfaces(anchor, projection, q1_reference)
        q2_state = v018._V015.encode_ee_axis_v014_q2_states(ops3_surfaces)
        q2_state.verify()
        q2_values = np.asarray(
            v018._q2_values(q2, q2_state.state_matrix, q2_state.action_masks),
            dtype=np.float64,
        )
    if not np.array_equal(q2_state.action_masks, masks):
        raise V023SourceAdapterError("Q2 carrier mask differs from native mask")
    if q1_values.shape != masks.shape or q2_values.shape != masks.shape:
        raise V023SourceAdapterError("Q1/Q2 source surfaces disagree with mask")
    # V0.23 freezes Q1/Q2 at float32 model output precision.  References are
    # selected from the exact float32 sum represented by DetachedQ12Snapshot.
    snapshot = DetachedQ12Snapshot(
        q1=np.asarray(q1_values, dtype=np.float32),
        q2=np.asarray(q2_values, dtype=np.float32),
        source_state_digest=native.state_sha256,
        native_observation_event_digest=provenance.content_digest,
        model_digest=model_digest,
    )
    q12 = np.asarray(snapshot.q12, dtype=np.float64)
    background = _masked_argmax(q12, masks)
    required_power, opening = v018._current_required_power_and_opening(
        current_gain_linear=anchor.current_gain_linear,
        segment_start_gain_linear=anchor.segment_start_gain_linear,
        action_masks=masks,
    )
    q2_context = _repriced_ops3_context(
        surfaces=ops3_surfaces,
        q2_state=q2_state,
        masks=masks,
        opening=np.asarray(opening, dtype=np.bool_),
        q1_reference=np.asarray(q1_reference, dtype=np.int64),
        anchor_horizon=int(anchor.horizon),
    )
    return {
        "native": native,
        "snapshot": snapshot,
        "masks": masks,
        "q1": np.asarray(snapshot.q1, dtype=np.float32),
        "q2": np.asarray(snapshot.q2, dtype=np.float32),
        "q12": np.asarray(snapshot.q12, dtype=np.float32),
        "q1_reference": np.asarray(q1_reference, dtype=np.int64),
        "background": background,
        "opening": np.asarray(opening, dtype=np.bool_),
        "required_power": np.asarray(required_power, dtype=np.float64),
        "q2_state_sha256": str(q2_state.state_sha256),
        "q2_context": q2_context,
        "ops3_anchor_sha256": str(anchor.anchor_sha256),
        "ops3_tracker_seed_sha256": str(anchor.tracker_seed_sha256),
        "ops3_projection_sha256": str(projection.projection_sha256),
        "ops3_future_d2_indices": [int(value) for value in projection.future_d2_indices],
        "ops3_sample_times_utc": [value.isoformat() for value in projection.sample_times_utc],
        "ops3_offset_times_utc": [value.isoformat() for value in projection.offset_times_utc],
    }


def _profile_digest_map(records: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    return {
        code: str(records[code]["action_sha256"])
        for code in PROFILE_ORDER
    }


def _control_record(control: LCSRSC3NoCloseControl) -> dict[str, Any]:
    return {
        "control_id": control.control_id,
        "world": int(control.world_id),
        "phase": int(control.phase),
        "anchor_id": control.anchor_id,
        "source_key": [int(control.source_key[0]), int(control.source_key[1])],
        "member_users": [int(value) for value in control.member_users],
        "third_user": int(control.third_user),
        "designated_actions": [
            None if value is None else int(value)
            for value in control.designated_actions
        ],
        "destination_keys": [
            None if key is None else [int(key[0]), int(key[1])]
            for key in control.destination_keys
        ],
        "eligible_actions_by_member": [
            [int(value) for value in row]
            for row in control.eligible_actions_by_member
        ],
        "detached_q12_sha256": control.detached_q12_digest,
        "content_digest": control.content_digest,
        "eligible": bool(control.eligible),
    }


def _transition_class(
    physical_keys: np.ndarray, *, user: int, reference: int, candidate: int
) -> str:
    reference_key = tuple(int(value) for value in physical_keys[user, reference])
    candidate_key = tuple(int(value) for value in physical_keys[user, candidate])
    if reference_key == candidate_key:
        return "SAME_PHYSICAL_LINK"
    if reference_key[0] == candidate_key[0]:
        return "INTRA_SATELLITE_BEAM_MOVE"
    return "INTER_SATELLITE_MOVE"


def _pair_record(pair: LCSRSC3ClosurePair) -> dict[str, Any]:
    return {
        "pair_id": pair.pair_id,
        "source_key": [int(pair.source_key[0]), int(pair.source_key[1])],
        "member_users": [int(value) for value in pair.member_users],
        "designated_actions": [int(value) for value in pair.designated_actions],
        "destination_keys": [
            [int(key[0]), int(key[1])] for key in pair.destination_keys
        ],
        "eligible_actions_by_member": [
            [int(value) for value in row]
            for row in pair.eligible_actions_by_member
        ],
        "detached_q12_sha256": pair.detached_q12_digest,
        "content_digest": pair.content_digest,
    }


def _topology_record(topology: LCSRSC3AnchorTopologyReceipt) -> dict[str, Any]:
    return _jsonable(topology.to_receipt())  # type: ignore[return-value]


def _derive_exclusions(topology: LCSRSC3AnchorTopologyReceipt) -> dict[str, Any]:
    """Report all topology classes without selecting on an outcome."""

    capture = topology.capture
    refs = np.asarray(capture.reference_actions, dtype=np.int64)
    opening = np.asarray(capture.opening_feasibility, dtype=np.bool_)
    keys = np.asarray(capture.physical_keys, dtype=np.int64)
    by_source: dict[tuple[int, int], list[int]] = {}
    for user, action in enumerate(refs.tolist()):
        key = (int(keys[user, action, 0]), int(keys[user, action, 1]))
        by_source.setdefault(key, []).append(user)
    exact_two = [users for users in by_source.values() if len(users) == 2]
    exact_two_opening = sum(
        int(all(bool(opening[user, refs[user]]) for user in users))
        for users in exact_two
    )
    pairs = len(topology.pairs)
    return {
        "reference_source_count": len(by_source),
        "exact_two_source_count": len(exact_two),
        "exact_two_both_opening_count": exact_two_opening,
        "closure_pair_count": pairs,
        "exact_two_missing_destination_count": exact_two_opening - pairs,
        "occupancy_three_control_count": topology.no_close_count,
        "supported_cell_count": 2 * pairs,
        "class_counts": topology.class_counts,
        "retained_for_fitting": topology.retained_for_fitting,
        "retention_status": topology.retention_status,
        "outcome_filter_applied": False,
    }


def _teacher_record(teacher: LCSRSTwoUserTeacher) -> dict[str, Any]:
    draws: list[dict[str, Any]] = []
    for draw, result in zip(teacher.draws, teacher.formula_results, strict=True):
        draws.append(
            {
                "draw_index": int(draw.draw_index),
                "profile_actions": _jsonable(draw.profile_actions),
                "profile_bits": _jsonable(draw.profile_bits),
                "profile_energy_j": _jsonable(draw.profile_energy_j),
                "common_field_sha256_by_profile": list(draw.common_field_sha256_by_profile),
                "action_sha256_by_profile": list(draw.action_sha256_by_profile),
                "formula": _formula_record(result),
            }
        )
    targets = np.asarray(teacher.pair_targets.normalized_targets_by_draw, dtype=np.float64)
    return {
        "pair_id": teacher.pair_id,
        "member_users": _jsonable(teacher.member_users),
        "proposed_actions": _jsonable(teacher.proposed_actions),
        "pair_targets_by_draw": _jsonable(targets),
        "pair_target_mean": _jsonable(np.mean(targets, axis=0, dtype=np.float64)),
        "content_digest": teacher.content_digest,
        "draws": draws,
    }


def _composition_record(
    *,
    bound: LCSRSC3BoundAnchor,
    snapshot: DetachedQ12Snapshot,
    mask: np.ndarray,
) -> dict[str, Any]:
    target = np.asarray(bound.surface.normalized_targets, dtype=np.float64)
    q12 = np.asarray(snapshot.q12, dtype=np.float64)
    selected = _masked_argmax(q12 + target, mask)
    reference = np.asarray(snapshot.q12, dtype=np.float64)
    return {
        "oracle_surface_sha256": _array_digest(target, domain="v023-oracle-q3-surface"),
        "selected_actions": _jsonable(selected),
        "reference_actions": _jsonable(
            _masked_argmax(reference, mask)
        ),
        "changed_user_count": int(np.count_nonzero(selected != _masked_argmax(reference, mask))),
        "target_nonzero_count": int(np.count_nonzero(target)),
        "adoption_profile": "ORACLE_ONE_PASS_FULL_SURFACE",
        "post_selection_physics_evaluated": False,
    }


def _build_sidecar_arrays(
    *,
    captures: Sequence[LCSRSC3PredecisionCapture],
    q2_contexts: Sequence[Mapping[str, Any]],
    anchor_records: Sequence[LCSRSC3BoundAnchor | None],
    pair_teachers: Sequence[tuple[int, LCSRSTwoUserTeacher]],
    profile_rows: Sequence[Mapping[str, Any]],
    controls: Sequence[Mapping[str, Any]] = (),
) -> dict[str, np.ndarray]:
    """Pack complete fixed-width source inputs into one NPZ sidecar.

    The fit worker only needs the retained anchor/pair rows, but the source
    boundary also keeps every enumerated anchor and every raw no-close control
    here.  Keeping those diagnostic rows in the same immutable sidecar makes
    the no-closure invariant independently recomputable without reopening the
    simulator.  Variable-length physical sets are padded with ``-1`` and have
    explicit count arrays.
    """

    if not captures:
        raise V023SourceAdapterError("world has no V0.23 anchors")
    if len(anchor_records) != len(captures) or len(q2_contexts) != len(captures):
        raise V023SourceAdapterError("anchor record/Q2-context/capture counts disagree")
    users = int(captures[0].view.action_context.shape[0])
    if any(int(capture.view.action_context.shape[0]) != users for capture in captures):
        raise V023SourceAdapterError("world anchor user counts disagree")
    phases = np.asarray([capture.topology.phase for capture in captures], dtype=np.int64)
    retained = np.asarray([record is not None for record in anchor_records], dtype=np.bool_)
    status = np.asarray([1 if value else 0 for value in retained.tolist()], dtype=np.uint8)
    anchor_digest = np.asarray(
        [capture.content_digest.encode("ascii") for capture in captures], dtype="S64"
    )
    view_digest = np.asarray(
        [capture.view.content_digest.encode("ascii") for capture in captures], dtype="S64"
    )
    topology_digest = np.asarray(
        [capture.topology.content_digest.encode("ascii") for capture in captures], dtype="S64"
    )
    arrays: dict[str, np.ndarray] = {
        "anchor_phase": phases,
        "anchor_status": status,
        "anchor_retained": retained,
        "anchor_content_digest": anchor_digest,
        "anchor_view_content_digest": view_digest,
        "anchor_topology_content_digest": topology_digest,
        "action_context": np.stack([capture.view.action_context for capture in captures]).astype(np.float32),
        "tokens": np.stack([capture.view.tokens for capture in captures]).astype(np.float32),
        "token_mask": np.stack([capture.view.token_mask for capture in captures]).astype(np.bool_),
        "action_mask": np.stack([capture.view.action_mask for capture in captures]).astype(np.bool_),
        "reference_actions": np.stack([capture.view.reference_actions for capture in captures]).astype(np.int64),
        "opening_feasibility": np.stack([
            np.asarray(capture.topology.capture.opening_feasibility, dtype=np.bool_)
            for capture in captures
        ]),
        "physical_keys": np.stack([
            np.asarray(capture.topology.capture.physical_keys, dtype=np.int64)
            for capture in captures
        ]),
        "q1_values": np.stack([
            np.asarray(capture.topology.capture.q12_snapshot.q1, dtype=np.float64)
            for capture in captures
        ]),
        "q2_values": np.stack([
            np.asarray(capture.topology.capture.q12_snapshot.q2, dtype=np.float64)
            for capture in captures
        ]),
        "q12_values": np.stack([
            np.asarray(capture.topology.capture.q12_snapshot.q12, dtype=np.float64)
            for capture in captures
        ]),
        "q2_state_matrix": np.stack([
            np.asarray(context["state_matrix"], dtype=np.float32)
            for context in q2_contexts
        ]),
        "q2_feature_surface": np.stack([
            np.asarray(context["features"], dtype=np.float64)
            for context in q2_contexts
        ]),
        "q2_teacher_values": np.stack([
            np.asarray(context["target_values"], dtype=np.float64)
            for context in q2_contexts
        ]),
        "q2_persistence": np.stack([
            np.asarray(context["persistence"], dtype=np.float64)
            for context in q2_contexts
        ]),
        "q2_rate_bps": np.stack([
            np.asarray(context["rate_bps"], dtype=np.float64)
            for context in q2_contexts
        ]),
        "q2_marginal_power_w": np.stack([
            np.asarray(context["marginal_power_w"], dtype=np.float64)
            for context in q2_contexts
        ]),
        "q2_required_power_w": np.stack([
            np.asarray(context["required_power_w"], dtype=np.float64)
            for context in q2_contexts
        ]),
        "q2_horizon": np.asarray(
            [int(context["horizon"]) for context in q2_contexts], dtype=np.int64
        ),
    }

    pair_count = len(pair_teachers)
    if pair_count:
        pair_anchor_index = np.asarray([int(anchor) for anchor, _ in pair_teachers], dtype=np.int64)
        pair_retained = np.asarray(
            [anchor_records[int(anchor)] is not None for anchor, _ in pair_teachers],
            dtype=np.bool_,
        )
        pair_ids = np.asarray(
            [teacher.pair_id.encode("utf-8") for _, teacher in pair_teachers], dtype="S256"
        )
        pair_users = np.stack([
            np.asarray(teacher.pair_targets.user_ids, dtype=np.int64)
            for _, teacher in pair_teachers
        ])
        pair_actions = np.stack([
            np.asarray(teacher.pair_targets.action_ids, dtype=np.int64)
            for _, teacher in pair_teachers
        ])
        pair_draw = np.stack([
            np.asarray(teacher.pair_targets.normalized_targets_by_draw, dtype=np.float64)
            for _, teacher in pair_teachers
        ])
        arrays.update({
            "pair_anchor_index": pair_anchor_index,
            "pair_retained": pair_retained,
            "pair_id": pair_ids,
            "pair_user_ids": pair_users,
            "pair_action_ids": pair_actions,
            "pair_target_by_draw": pair_draw,
            "pair_target_mean": np.mean(pair_draw, axis=1, dtype=np.float64),
            "pair_class": np.full((pair_count, 2), 3, dtype=np.uint8),
        })
    else:
        arrays.update({
            "pair_anchor_index": np.zeros((0,), dtype=np.int64),
            "pair_retained": np.zeros((0,), dtype=np.bool_),
            "pair_id": np.zeros((0,), dtype="S256"),
            "pair_user_ids": np.zeros((0, 2), dtype=np.int64),
            "pair_action_ids": np.zeros((0, 2), dtype=np.int64),
            "pair_target_by_draw": np.zeros((0, DRAW_COUNT, 2), dtype=np.float64),
            "pair_target_mean": np.zeros((0, 2), dtype=np.float64),
            "pair_class": np.zeros((0, 2), dtype=np.uint8),
        })

    rows = list(profile_rows)
    row_count = len(rows)
    max_beams = max(
        [
            len(profile.get("active_beam_keys", []))
            for row in rows
            for profile in row.get("profiles", {}).values()
            if isinstance(profile, Mapping)
        ]
        or [0]
    )
    max_sats = max(
        [
            len(profile.get("active_satellites", []))
            for row in rows
            for profile in row.get("profiles", {}).values()
            if isinstance(profile, Mapping)
        ]
        or [0]
    )
    profile_actions = np.zeros((row_count, 4, users), dtype=np.int64)
    profile_bits = np.zeros((row_count, 4, users), dtype=np.float64)
    profile_rates = np.zeros((row_count, 4, users), dtype=np.float64)
    profile_link_power = np.zeros((row_count, 4, users), dtype=np.float64)
    profile_link_sinr = np.zeros((row_count, 4, users), dtype=np.float64)
    profile_energy = np.zeros((row_count, 4), dtype=np.float64)
    profile_g = np.zeros((row_count, 4), dtype=np.float64)
    profile_system_power = np.zeros((row_count, 4), dtype=np.float64)
    profile_fixed_power = np.zeros((row_count, 4), dtype=np.float64)
    profile_served = np.zeros((row_count, 4, users), dtype=np.bool_)
    active_keys = np.full((row_count, 4, max_beams, 2), -1, dtype=np.int64)
    beam_counts = np.zeros((row_count, 4), dtype=np.int64)
    active_sats = np.full((row_count, 4, max_sats), -1, dtype=np.int64)
    sat_counts = np.zeros((row_count, 4), dtype=np.int64)
    beam_power = np.zeros((row_count, 4, max_beams), dtype=np.float64)
    z3 = np.zeros((row_count, 2), dtype=np.float64)
    z3n = np.zeros((row_count, 2), dtype=np.float64)
    residual = np.zeros(row_count, dtype=np.float64)
    ratio_identity = np.zeros(row_count, dtype=np.float64)
    ratio_cross = np.zeros(row_count, dtype=np.float64)
    ratio_sign = np.zeros(row_count, dtype=np.int8)
    ratio_tolerance = np.zeros(row_count, dtype=np.float64)
    ratio_local_tolerance = np.zeros(row_count, dtype=np.float64)
    joint_ee = np.zeros(row_count, dtype=np.float64)
    mutation = np.zeros((row_count, 5), dtype=np.bool_)
    fields = np.empty((row_count,), dtype="S64")
    action_digests = np.empty((row_count, 4), dtype="S64")
    pair_indices = np.zeros(row_count, dtype=np.int64)
    draw_indices = np.zeros(row_count, dtype=np.int64)
    formula_own = np.zeros((row_count, 2), dtype=np.float64)
    formula_nonfocal = np.zeros((row_count, 2), dtype=np.float64)
    formula_d = np.zeros((row_count, 2), dtype=np.float64)
    formula_joint_delta = np.zeros(row_count, dtype=np.float64)
    formula_joint_delta_energy = np.zeros(row_count, dtype=np.float64)
    formula_joint_surplus = np.zeros(row_count, dtype=np.float64)
    formula_interaction = np.zeros(row_count, dtype=np.float64)
    formula_interaction_energy = np.zeros(row_count, dtype=np.float64)
    formula_interaction_surplus = np.zeros(row_count, dtype=np.float64)
    # ``equal_share_bits`` is the scalar per-member allocation used by the
    # coalition residual formula.  Keep it scalar in the sidecar rather than
    # silently duplicating it across the two action columns; the member-wise
    # vectors remain in ``formula_own_bits``/``formula_nonfocal_bits``.
    formula_equal_share = np.zeros((row_count,), dtype=np.float64)
    row_ids = np.empty((row_count,), dtype="S256")
    for row_index, row in enumerate(rows):
        pair_indices[row_index] = int(row["pair_index"])
        draw_indices[row_index] = int(row["draw_index"])
        row_ids[row_index] = str(row.get("pair_id", f"pair-{pair_indices[row_index]}")).encode("utf-8")
        records = row["profiles"]
        for profile_index, code in enumerate(PROFILE_ORDER):
            profile = records[code]
            actions = np.asarray(profile["actions"], dtype=np.int64)
            profile_actions[row_index, profile_index] = actions
            profile_bits[row_index, profile_index] = np.asarray(profile["per_user_bits"], dtype=np.float64)
            profile_rates[row_index, profile_index] = np.asarray(profile["link_rate_bps"], dtype=np.float64)
            profile_link_power[row_index, profile_index] = np.asarray(profile["link_power_w"], dtype=np.float64)
            profile_link_sinr[row_index, profile_index] = np.asarray(profile["link_sinr"], dtype=np.float64)
            profile_energy[row_index, profile_index] = float(profile["energy_j"])
            profile_g[row_index, profile_index] = float(profile["g_bits"])
            profile_system_power[row_index, profile_index] = float(profile["system_power_w"])
            profile_fixed_power[row_index, profile_index] = float(profile["fixed_power_w"])
            profile_served[row_index, profile_index] = np.asarray(profile["served"], dtype=np.bool_)
            keys = np.asarray(profile["active_beam_keys"], dtype=np.int64)
            count = int(keys.shape[0])
            beam_counts[row_index, profile_index] = count
            if count:
                active_keys[row_index, profile_index, :count] = keys
                beam_power[row_index, profile_index, :count] = np.asarray(profile["beam_power_w"], dtype=np.float64)
            sats = np.asarray(profile["active_satellites"], dtype=np.int64)
            sat_count = int(sats.shape[0])
            sat_counts[row_index, profile_index] = sat_count
            if sat_count:
                active_sats[row_index, profile_index, :sat_count] = sats
            action_digests[row_index, profile_index] = str(profile["action_sha256"]).encode("ascii")
        formula = row["formula"]
        z3[row_index] = np.asarray(formula["z3_bits"], dtype=np.float64)
        z3n[row_index] = z3[row_index] / KAPPA_BITS
        residual[row_index] = float(formula["identity_residual_bits"])
        ratio_identity[row_index] = float(row["ratio_identity_value_bits"])
        ratio_cross[row_index] = float(row["ratio_cross_product"])
        ratio_sign[row_index] = int(row["ratio_sign"])
        ratio_tolerance[row_index] = float(row["ratio_tolerance"])
        ratio_local_tolerance[row_index] = float(row["ratio_local_tolerance"])
        joint_ee[row_index] = float(row["joint_ee_bits_per_j"])
        mutation[row_index] = np.asarray(row["nonmutation_flags"], dtype=np.bool_)
        fields[row_index] = str(row["common_field_sha256"]).encode("ascii")
        formula_own[row_index] = np.asarray(formula["own_bits"], dtype=np.float64)
        formula_nonfocal[row_index] = np.asarray(formula["nonfocal_bits"], dtype=np.float64)
        formula_d[row_index] = np.asarray(formula["d_bits"], dtype=np.float64)
        formula_joint_delta[row_index] = float(formula["joint_delta_bits"])
        formula_joint_delta_energy[row_index] = float(formula["joint_delta_energy_j"])
        formula_joint_surplus[row_index] = float(formula["joint_surplus_bits"])
        formula_interaction[row_index] = float(formula["interaction_bits"])
        formula_interaction_energy[row_index] = float(formula["interaction_energy_j"])
        formula_interaction_surplus[row_index] = float(formula["interaction_surplus_bits"])
        formula_equal_share[row_index] = float(formula["equal_share_bits"])
    arrays.update({
        "draw_pair_index": pair_indices,
        "draw_index": draw_indices,
        "draw_pair_id": row_ids,
        "profile_actions": profile_actions,
        "profile_bits": profile_bits,
        "profile_link_rate_bps": profile_rates,
        "profile_link_power_w": profile_link_power,
        "profile_link_sinr": profile_link_sinr,
        "profile_energy_j": profile_energy,
        "profile_g_bits": profile_g,
        "profile_system_power_w": profile_system_power,
        "profile_fixed_power_w": profile_fixed_power,
        "profile_served": profile_served,
        "profile_active_beam_keys": active_keys,
        "profile_active_beam_counts": beam_counts,
        "profile_active_satellites": active_sats,
        "profile_active_satellite_counts": sat_counts,
        "profile_beam_power_w": beam_power,
        "z3_bits_by_draw": z3,
        "z3_normalized_by_draw": z3n,
        "formula_identity_residual_bits": residual,
        "ratio_identity_value_bits": ratio_identity,
        "ratio_cross_product": ratio_cross,
        "ratio_sign": ratio_sign,
        "ratio_tolerance": ratio_tolerance,
        "ratio_local_tolerance": ratio_local_tolerance,
        "joint_ee_bits_per_j": joint_ee,
        "nonmutation_flags": mutation,
        "common_field_digest": fields,
        "action_digest": action_digests,
        "formula_own_bits": formula_own,
        "formula_nonfocal_bits": formula_nonfocal,
        "formula_d_bits": formula_d,
        "formula_joint_delta_bits": formula_joint_delta,
        "formula_joint_delta_energy_j": formula_joint_delta_energy,
        "formula_joint_surplus_bits": formula_joint_surplus,
        "formula_interaction_bits": formula_interaction,
        "formula_interaction_energy_j": formula_interaction_energy,
        "formula_interaction_surplus_bits": formula_interaction_surplus,
        "formula_equal_share_bits": formula_equal_share,
    })

    # Raw no-close controls are diagnostic-only and are intentionally kept
    # outside the pair teacher rows.  Ineligible controls have a deterministic
    # zero-filled row for each of the 32 draw indices and an explicit evaluated
    # flag, so missing physical controls cannot be mistaken for omitted data.
    control_list = list(controls)
    control_count = len(control_list)
    control_row_count = control_count * DRAW_COUNT
    control_max_beams = max(
        [
            len(profile.get("active_beam_keys", []))
            for control in control_list
            for draw in control.get("profile_draws", [])
            for profile in draw.get("profiles", {}).values()
            if isinstance(profile, Mapping)
        ]
        or [0]
    )
    control_max_sats = max(
        [
            len(profile.get("active_satellites", []))
            for control in control_list
            for draw in control.get("profile_draws", [])
            for profile in draw.get("profiles", {}).values()
            if isinstance(profile, Mapping)
        ]
        or [0]
    )
    control_ids = np.empty((control_count,), dtype="S256")
    control_phase = np.zeros(control_count, dtype=np.int64)
    control_source = np.full((control_count, 2), -1, dtype=np.int64)
    control_members = np.full((control_count, 3), -1, dtype=np.int64)
    control_eligible = np.zeros(control_count, dtype=np.bool_)
    control_evaluated = np.zeros(control_row_count, dtype=np.bool_)
    control_index = np.repeat(np.arange(control_count, dtype=np.int64), DRAW_COUNT)
    control_draw = np.tile(np.arange(DRAW_COUNT, dtype=np.int64), control_count)
    control_actions = np.zeros((control_row_count, 4, users), dtype=np.int64)
    control_bits = np.zeros((control_row_count, 4, users), dtype=np.float64)
    control_rates = np.zeros((control_row_count, 4, users), dtype=np.float64)
    control_link_power = np.zeros((control_row_count, 4, users), dtype=np.float64)
    control_link_sinr = np.zeros((control_row_count, 4, users), dtype=np.float64)
    control_energy = np.zeros((control_row_count, 4), dtype=np.float64)
    control_g = np.zeros((control_row_count, 4), dtype=np.float64)
    control_system_power = np.zeros((control_row_count, 4), dtype=np.float64)
    control_fixed_power = np.zeros((control_row_count, 4), dtype=np.float64)
    control_served = np.zeros((control_row_count, 4, users), dtype=np.bool_)
    control_active_keys = np.full((control_row_count, 4, control_max_beams, 2), -1, dtype=np.int64)
    control_beam_counts = np.zeros((control_row_count, 4), dtype=np.int64)
    control_active_sats = np.full((control_row_count, 4, control_max_sats), -1, dtype=np.int64)
    control_sat_counts = np.zeros((control_row_count, 4), dtype=np.int64)
    control_beam_power = np.zeros((control_row_count, 4, control_max_beams), dtype=np.float64)
    control_source_present = np.zeros((control_row_count, 4), dtype=np.bool_)
    control_mutation = np.zeros((control_row_count, 2), dtype=np.bool_)
    control_fields = np.zeros((control_row_count,), dtype="S64")
    control_action_digests = np.zeros((control_row_count, 4), dtype="S64")
    for control_index_value, control in enumerate(control_list):
        control_ids[control_index_value] = str(control["control_id"]).encode("utf-8")
        control_phase[control_index_value] = int(control.get("phase", -1))
        control_source[control_index_value] = np.asarray(control["source_key"], dtype=np.int64)
        member_values = [*control.get("member_users", []), int(control.get("third_user", -1))]
        control_members[control_index_value] = np.asarray(member_values, dtype=np.int64)
        control_eligible[control_index_value] = bool(control.get("eligible", False))
        draws = list(control.get("profile_draws", []))
        if control_eligible[control_index_value] and len(draws) != DRAW_COUNT:
            raise V023SourceAdapterError("eligible no-close control lacks all 32 draws")
        for draw_value in draws:
            draw_value_index = int(draw_value["draw_index"])
            if not 0 <= draw_value_index < DRAW_COUNT:
                raise V023SourceAdapterError("no-close draw index is outside 0..31")
            row_value_index = control_index_value * DRAW_COUNT + draw_value_index
            control_evaluated[row_value_index] = True
            control_fields[row_value_index] = str(draw_value["common_field_sha256"]).encode("ascii")
            nonmutation = draw_value.get("nonmutation", {})
            control_mutation[row_value_index] = np.asarray(
                [bool(nonmutation.get("live_state_unchanged", False)), bool(nonmutation.get("rng_unchanged", False))],
                dtype=np.bool_,
            )
            source_present = draw_value.get("source_present_by_profile", {})
            for profile_index, code in enumerate(PROFILE_ORDER):
                profile = draw_value["profiles"][code]
                control_actions[row_value_index, profile_index] = np.asarray(profile["actions"], dtype=np.int64)
                control_bits[row_value_index, profile_index] = np.asarray(profile["per_user_bits"], dtype=np.float64)
                control_rates[row_value_index, profile_index] = np.asarray(profile["link_rate_bps"], dtype=np.float64)
                control_link_power[row_value_index, profile_index] = np.asarray(profile["link_power_w"], dtype=np.float64)
                control_link_sinr[row_value_index, profile_index] = np.asarray(profile["link_sinr"], dtype=np.float64)
                control_energy[row_value_index, profile_index] = float(profile["energy_j"])
                control_g[row_value_index, profile_index] = float(profile["g_bits"])
                control_system_power[row_value_index, profile_index] = float(profile["system_power_w"])
                control_fixed_power[row_value_index, profile_index] = float(profile["fixed_power_w"])
                control_served[row_value_index, profile_index] = np.asarray(profile["served"], dtype=np.bool_)
                keys = np.asarray(profile["active_beam_keys"], dtype=np.int64)
                count = int(keys.shape[0])
                control_beam_counts[row_value_index, profile_index] = count
                if count:
                    control_active_keys[row_value_index, profile_index, :count] = keys
                    control_beam_power[row_value_index, profile_index, :count] = np.asarray(profile["beam_power_w"], dtype=np.float64)
                satellites = np.asarray(profile["active_satellites"], dtype=np.int64)
                satellite_count = int(satellites.shape[0])
                control_sat_counts[row_value_index, profile_index] = satellite_count
                if satellite_count:
                    control_active_sats[row_value_index, profile_index, :satellite_count] = satellites
                control_source_present[row_value_index, profile_index] = bool(source_present.get(code, False))
                control_action_digests[row_value_index, profile_index] = str(profile["action_sha256"]).encode("ascii")
    arrays.update({
        "control_id": control_ids,
        "control_phase": control_phase,
        "control_source_key": control_source,
        "control_member_users": control_members,
        "control_eligible": control_eligible,
        "control_index": control_index,
        "control_draw_index": control_draw,
        "control_evaluated": control_evaluated,
        "control_profile_actions": control_actions,
        "control_profile_bits": control_bits,
        "control_profile_link_rate_bps": control_rates,
        "control_profile_link_power_w": control_link_power,
        "control_profile_link_sinr": control_link_sinr,
        "control_profile_energy_j": control_energy,
        "control_profile_g_bits": control_g,
        "control_profile_system_power_w": control_system_power,
        "control_profile_fixed_power_w": control_fixed_power,
        "control_profile_served": control_served,
        "control_profile_active_beam_keys": control_active_keys,
        "control_profile_active_beam_counts": control_beam_counts,
        "control_profile_active_satellites": control_active_sats,
        "control_profile_active_satellite_counts": control_sat_counts,
        "control_profile_beam_power_w": control_beam_power,
        "control_source_present": control_source_present,
        "control_nonmutation_flags": control_mutation,
        "control_common_field_digest": control_fields,
        "control_action_digest": control_action_digests,
    })
    for name, array in arrays.items():
        if np.asarray(array).dtype == object:
            raise V023SourceAdapterError(f"sidecar array {name} may not be object dtype")
    return arrays


def _placebo_strata_receipt(
    *,
    anchor_records: Sequence[LCSRSC3BoundAnchor | None],
) -> dict[str, Any]:
    """Build the exact canonical placebo mapping for this one world.

    Eligibility is deliberately delegated to ``build_lcsrs_matched_placebo``
    rather than reimplementing its phase/occupancy/activity/base-gap bins.
    The returned mapping is a receipt only; it never mutates the true surface.
    """

    records = tuple(
        bound.record
        for bound in anchor_records
        if bound is not None
    )
    if any(not isinstance(record, LCSRSAnchorRecord) for record in records):
        raise V023SourceAdapterError("retained source anchor is not an LCSRSAnchorRecord")
    if not records:
        return {
            "schema": f"{SOURCE_ARTIFACT_SCHEMA}-placebo-strata-v1",
            "strata": [],
            "mappings": [],
            "supported_count": 0,
            "placebo_eligible_count": 0,
            "coverage": 0.0,
            "within_world_only": True,
            "placebo_key": PLACEBO_KEY,
            "placebo_key_sha256": PLACEBO_KEY_SHA256,
            "outcome_filter_applied": False,
        }
    try:
        placebo = build_lcsrs_matched_placebo(records, placebo_key=PLACEBO_KEY)
    except Exception as error:
        raise V023SourceAdapterError("canonical matched-placebo construction failed") from error
    if placebo.placebo_key_sha256 != PLACEBO_KEY_SHA256:
        raise V023SourceAdapterError("canonical placebo key digest drifted")
    groups: dict[tuple[int, int, int, int, int, int], list[dict[str, Any]]] = {}
    for record_index, record in enumerate(records):
        for user, action in record.surface.cells_for_class(3).tolist():
            stratum = placebo_stratum(record, int(user), int(action))
            groups.setdefault(stratum.key(), []).append({
                "anchor_index": int(record_index),
                "world": int(record.world_id),
                "anchor_id": record.anchor_id,
                "user": int(user),
                "action": int(action),
            })
    return {
        "schema": f"{SOURCE_ARTIFACT_SCHEMA}-placebo-strata-v1",
        "strata": [
            {
                "stratum": list(key),
                "rows": sorted(rows, key=lambda item: (item["world"], item["anchor_id"], item["user"], item["action"])),
                "count": len(rows),
                "placebo_eligible": len(rows) >= 2,
            }
            for key, rows in sorted(groups.items())
        ],
        "mappings": [
            {
                "stratum": list(mapping.stratum.key()),
                "source_anchor": int(mapping.source_anchor),
                "source_user": int(mapping.source_user),
                "source_action": int(mapping.source_action),
                "destination_anchor": int(mapping.destination_anchor),
                "destination_user": int(mapping.destination_user),
                "destination_action": int(mapping.destination_action),
                "shift": int(mapping.shift),
            }
            for mapping in placebo.mappings
        ],
        "supported_count": int(placebo.total_supported_rows),
        "placebo_eligible_count": int(placebo.eligible_supported_rows),
        "coverage": float(placebo.coverage),
        "within_world_only": True,
        "placebo_key": PLACEBO_KEY,
        "placebo_key_sha256": PLACEBO_KEY_SHA256,
        "content_digest": placebo.content_digest,
        "outcome_filter_applied": False,
    }


def _write_once_bytes(path: Path, payload: bytes) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise V023SourceAdapterError(f"refusing to overwrite source artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _write_npz_once(path: Path, arrays: Mapping[str, np.ndarray]) -> str:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise V023SourceAdapterError(f"refusing to overwrite source sidecar: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    os.close(fd)
    try:
        with open(temporary, "wb") as handle:
            np.savez_compressed(handle, **{name: np.asarray(value) for name, value in arrays.items()})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return file_sha256(target)


@dataclass(frozen=True)
class V023SourceAdapterConfig:
    """Authenticated paths and immutable V0.23 source settings."""

    tle_root: Path
    prereg: Path
    manifest: Path = HERE / "PREFLIGHT-MANIFEST.json"
    manifest_digest: Path = HERE / "PREFLIGHT-MANIFEST.sha256"
    execution_addendum: Path = EXECUTION_ADDENDUM_PATH
    placebo_key: str = PLACEBO_KEY
    placebo_key_sha256: str = PLACEBO_KEY_SHA256
    lineage: int = 2026092101
    source_family: str = FIELD_COMPONENT

    def __post_init__(self) -> None:
        if self.lineage != 2026092101:
            raise V023SourceAdapterError("V0.23 source lineage is frozen")
        if self.source_family != FIELD_COMPONENT:
            raise V023SourceAdapterError("V0.23 field family is frozen")
        if Path(self.execution_addendum).resolve() != EXECUTION_ADDENDUM_PATH.resolve():
            raise V023SourceAdapterError("V0.23 execution addendum path is frozen")
        if self.placebo_key != PLACEBO_KEY or self.placebo_key_sha256 != PLACEBO_KEY_SHA256:
            raise V023SourceAdapterError("V0.23 matched-placebo key is frozen")


class V023RuntimeSourceAdapter:
    """Generate one complete V0.23 physical/source shard.

    The constructor is cheap and does not open a simulator.  All expensive or
    privileged work happens inside ``generate_source_shard`` after external
    preflight and inherited-source validation succeed.
    """

    def __init__(self, config: V023SourceAdapterConfig):
        self.config = config

    def _authenticate(self, *, expected_manifest_sha256: str | None = None) -> tuple[Any, Any, Any, Any, dict[str, Any], str]:
        if file_sha256(self.config.execution_addendum) != EXECUTION_ADDENDUM_SHA256:
            raise V023SourceAdapterError("execution parameter addendum bytes changed")
        preflight_path = HERE / "preflight_v023_lcsrs_observability.py"
        preflight = _load_module("mcrl_v023_source_preflight", preflight_path)
        receipt = preflight.validate_manifest(
            self.config.manifest,
            manifest_digest_path=self.config.manifest_digest,
            repo=REPO,
            prereg_path=self.config.prereg,
        )
        manifest_sha = str(receipt["manifest_file_sha256"])
        if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
            raise V023SourceAdapterError(
                "runtime preflight manifest hash disagrees with shard spec"
            )
        if receipt.get("status") != "PASS":
            raise V023SourceAdapterError("V0.23 preflight did not pass")
        bindings = {
            str(item["role"]): item
            for item in receipt.get("bindings", [])
            if isinstance(item, Mapping) and "role" in item
        }
        for role, expected_path, expected_sha in (
            (
                "execution_parameter_addendum",
                EXECUTION_ADDENDUM_PATH.relative_to(REPO).as_posix(),
                EXECUTION_ADDENDUM_SHA256,
            ),
            (
                "runtime_source_adapter",
                Path(__file__).resolve().relative_to(REPO).as_posix(),
                file_sha256(Path(__file__).resolve()),
            ),
            (
                "source_artifact_schema",
                (HERE / "SOURCE-ARTIFACT-SCHEMA.md").relative_to(REPO).as_posix(),
                file_sha256(HERE / "SOURCE-ARTIFACT-SCHEMA.md"),
            ),
        ):
            binding = bindings.get(role)
            if not isinstance(binding, Mapping):
                raise V023SourceAdapterError(f"preflight manifest lacks {role} binding")
            if binding.get("path") != expected_path or binding.get("sha256") != expected_sha:
                raise V023SourceAdapterError(f"preflight {role} binding disagrees")
        v020_path = REPO / ".scratch" / "multi-catfish-v020-c3-source-audit" / "run_v020_repriced_c3_gate.py"
        v020 = _load_module("mcrl_v020_source_adapter", v020_path)
        v020_receipt = v020._validate_global_inputs()
        v018 = v020._load_module("mcrl_v018_source_adapter", v020.V018_PATH)
        try:
            v018.validate_v018_contract()
            v018._V015.validate_v015_contract()
            v014_receipt = v018._V015.validate_v014_gate_receipts(v018.V014_GATE_ROOT)
            v018._V015._V013.assert_contract_frozen(v018._V015._V013.CONTRACT_PATH)
        except Exception as error:
            raise V023SourceAdapterError(f"inherited V0.20/V0.18 validators failed: {error}") from error
        if not isinstance(v014_receipt, Mapping):
            raise V023SourceAdapterError("V0.14 validator returned no receipt")
        q1, q1_receipt, q2, q2_receipt = v020.load_repriced_heads(self.config.lineage)
        q12_authority = _authenticate_q12_authority(
            lineage=self.config.lineage,
            q1_receipt=q1_receipt,
            q2_receipt=q2_receipt,
        )
        inherited = {
            "v020_global": _jsonable(v020_receipt),
            "v018_contract_sha256": str(v018.V018_CONTRACT_SHA256),
            "v015_contract_sha256": str(v018._V015.V015_CONTRACT_SHA256),
            "v014_gate_receipt": _jsonable(v014_receipt),
            "v013_contract_sha256": str(v018._V015._V013.file_sha256(v018._V015._V013.CONTRACT_PATH)),
            "status": "PASS",
        }
        return v020, v018, q1, q2, {
            "preflight": receipt,
            "inherited": inherited,
            "q1_receipt": q1_receipt,
            "q2_receipt": q2_receipt,
            "q12_authority": q12_authority,
        }, manifest_sha

    def _make_draw_field(self, world: int, anchor_id: str, draw_index: int) -> KeyedFadingField:
        # Pair/profile are intentionally absent from the root key.  The
        # environment's own event/step/NORAD addressing supplies the final
        # physical-link axis inside this immutable field.
        return KeyedFadingField.from_components(
            self.config.source_family,
            int(world),
            str(anchor_id),
            int(draw_index),
        )

    def _evaluate_pair(
        self,
        *,
        v018: Any,
        environment: Any,
        env_rng: np.random.Generator,
        step_env: Any,
        observation: Any,
        world: int,
        anchor_id: str,
        pair_index: int,
        pair: LCSRSC3ClosurePair,
        anchor_data: Mapping[str, Any],
        interval_s: float,
        q1_network: Any,
        q2_network: Any,
        q1_before: str,
        q2_before: str,
    ) -> tuple[LCSRSTwoUserTeacher, list[dict[str, Any]], dict[str, Any]]:
        reference = np.asarray(anchor_data["background"], dtype=np.int64)
        mask = np.asarray(anchor_data["masks"], dtype=np.bool_)
        members = np.asarray(pair.member_users, dtype=np.int64)
        proposed = np.asarray(pair.designated_actions, dtype=np.int64)
        profiles = _profile_actions(reference, members, proposed)
        draws: list[LCSRSFourProfileDraw] = []
        profile_rows: list[dict[str, Any]] = []
        c1_rows: list[dict[str, Any]] = []
        c2_rows: list[dict[str, Any]] = []
        mechanics_by_draw: list[dict[str, Any]] = []
        for draw_index in range(DRAW_COUNT):
            draw_field = self._make_draw_field(world, anchor_id, draw_index)
            live_before = _live_digest(v018, environment, env_rng)
            rng_before = copy.deepcopy(env_rng.bit_generator.state)
            original_field = getattr(step_env, "_fading_field", None)
            try:
                step_env._fading_field = draw_field
                evaluations = {
                    code: step_env.evaluate_actions(profiles[code], env_rng)
                    for code in PROFILE_ORDER
                }
            finally:
                step_env._fading_field = original_field
            live_after = _live_digest(v018, environment, env_rng)
            rng_after = copy.deepcopy(env_rng.bit_generator.state)
            q1_draw_after = str(v018._V015._q_parameter_sha256(q1_network))
            q2_draw_after = str(v018._V015._q_parameter_sha256(q2_network))
            network_unchanged = q1_draw_after == q1_before and q2_draw_after == q2_before
            field_restored = getattr(step_env, "_fading_field", None) is original_field
            live_unchanged = live_before == live_after
            rng_unchanged = _rng_state_unchanged(rng_before, rng_after)
            if not live_unchanged or not rng_unchanged or not network_unchanged or not field_restored:
                raise V023SourceAdapterError(
                    f"profile evaluation mutated frozen inputs for pair {pair.pair_id} draw {draw_index}"
                )
            records = {
                code: _evaluation_record(
                    evaluations[code], actions=profiles[code], interval_s=interval_s
                )
                for code in PROFILE_ORDER
            }
            source = tuple(int(value) for value in pair.source_key)
            active_sets = {
                code: {
                    tuple(int(value) for value in key)
                    for key in records[code]["active_beam_keys"]
                }
                for code in PROFILE_ORDER
            }
            destinations = {
                tuple(int(value) for value in key) for key in pair.destination_keys
            }
            b00 = float(records["00"]["total_bits"])
            b11 = float(records["11"]["total_bits"])
            e00 = float(records["00"]["energy_j"])
            e11 = float(records["11"]["energy_j"])
            ratio_receipt = _ratio_sign_receipt(
                reference_bits=b00,
                reference_energy_j=e00,
                joint_bits=b11,
                joint_energy_j=e11,
            )
            mechanics_failures = _closure_mechanics_failure_codes(
                records,
                source=source,
                destinations=destinations,
                members=members,
                ratio_sign_identity_pass=bool(
                    ratio_receipt["ratio_sign_identity_pass"]
                ),
            )
            mechanics_receipt = {
                "passed": not mechanics_failures,
                "failure_codes": mechanics_failures,
                "ordinary_failure": bool(mechanics_failures),
            }
            mechanics_by_draw.append(mechanics_receipt)
            field_digest = draw_field.root_digest
            draw_receipt = LCSRSFourProfileDraw(
                draw_index=draw_index,
                profile_actions=np.stack([profiles[code] for code in PROFILE_ORDER]),
                profile_bits=np.stack([
                    np.asarray(records[code]["per_user_bits"], dtype=np.float64)
                    for code in PROFILE_ORDER
                ]),
                profile_energy_j=np.asarray([
                    records[code]["energy_j"] for code in PROFILE_ORDER
                ], dtype=np.float64),
                common_field_sha256_by_profile=(field_digest,) * 4,
                action_sha256_by_profile=tuple(
                    records[code]["action_sha256"] for code in PROFILE_ORDER
                ),
            )
            draws.append(draw_receipt)
            formula = None
            profile_rows.append({
                "pair_index": pair_index,
                "pair_id": pair.pair_id,
                "draw_index": draw_index,
                "profiles": records,
                "common_field_sha256": field_digest,
                "action_sha256_by_profile": _profile_digest_map(records),
                "nonmutation_flags": [
                    bool(live_unchanged),
                    bool(rng_unchanged),
                    bool(network_unchanged),
                    bool(field_restored),
                    True,
                ],
                "formula": {},
                "ratio_identity_value_bits": float(
                    ratio_receipt["ratio_identity_value_bits"]
                ),
                "ratio_cross_product": float(ratio_receipt["ratio_cross_product"]),
                "ratio_sign": int(ratio_receipt["ratio_sign"]),
                "ratio_tolerance": float(ratio_receipt["ratio_tolerance"]),
                "ratio_local_tolerance": float(
                    ratio_receipt["ratio_local_tolerance"]
                ),
                "ratio_sign_identity_pass": bool(
                    ratio_receipt["ratio_sign_identity_pass"]
                ),
                "mechanics": mechanics_receipt,
                "joint_ee_bits_per_j": 0.0,
            })
            c1_rows.append({
                "draw_index": draw_index,
                "own_bits": [None, None],
                "q1_delta": [
                    float(anchor_data["q1"][int(members[0]), int(proposed[0])] - anchor_data["q1"][int(members[0]), int(reference[int(members[0])])]),
                    float(anchor_data["q1"][int(members[1]), int(proposed[1])] - anchor_data["q1"][int(members[1]), int(reference[int(members[1])])]),
                ],
            })
            if draw_index == 0:
                physical_keys = np.asarray(
                    anchor_data["capture"].topology.capture.physical_keys,
                    dtype=np.int64,
                )
                c2_rows.append({
                    "row_granularity": "ONE_PER_RETAINED_PAIR_MEMBER_NOT_PER_DRAW",
                    "user_ids": [int(value) for value in members],
                    "candidate_actions": [int(value) for value in proposed],
                    "reference_actions": [
                        int(reference[int(members[0])]),
                        int(reference[int(members[1])]),
                    ],
                    "q2_delta": [
                        float(anchor_data["q2"][int(members[0]), int(proposed[0])] - anchor_data["q2"][int(members[0]), int(reference[int(members[0])])]),
                        float(anchor_data["q2"][int(members[1]), int(proposed[1])] - anchor_data["q2"][int(members[1]), int(reference[int(members[1])])]),
                    ],
                    "ops3_target_delta": [
                        float(anchor_data["q2_context"]["target_values"][int(members[0]), int(proposed[0])] - anchor_data["q2_context"]["target_values"][int(members[0]), int(reference[int(members[0])])]),
                        float(anchor_data["q2_context"]["target_values"][int(members[1]), int(proposed[1])] - anchor_data["q2_context"]["target_values"][int(members[1]), int(reference[int(members[1])])]),
                    ],
                    "transition_class": [
                        _transition_class(
                            physical_keys,
                            user=int(members[0]),
                            reference=int(reference[int(members[0])]),
                            candidate=int(proposed[0]),
                        ),
                        _transition_class(
                            physical_keys,
                            user=int(members[1]),
                            reference=int(reference[int(members[1])]),
                            candidate=int(proposed[1]),
                        ),
                    ],
                })

        teacher = build_lcsrs_topology_teacher(
            topology=anchor_data["capture"].topology,
            pair=pair,
            draws=draws,
            lambda_bits_per_j=LAMBDA_BITS_PER_J,
            kappa_bits=KAPPA_BITS,
        )
        for index, (draw, row) in enumerate(zip(draws, profile_rows, strict=True)):
            result = teacher.formula_results[index]
            records = row["profiles"]
            row["formula"] = _formula_record(result)
            # C1 is an independent calibration diagnostic; preserve the
            # actual formula ell_i rather than an all-zero placeholder.
            c1_rows[index]["own_bits"] = _jsonable(result.own_bits)
            c1_rows[index]["own_normalized"] = _jsonable(
                np.asarray(result.own_bits, dtype=np.float64) / KAPPA_BITS
            )
            row["joint_ee_bits_per_j"] = float(
                records["11"]["ratio_of_sums_ee_bits_per_j"]
            )
            if abs(float(result.identity_residual_bits)) > 1.0e-12 * (
                1.0
                + abs(float(result.joint_surplus_bits))
                + float(np.sum(np.abs(result.combined_bits)))
            ):
                raise V023SourceAdapterError(
                    f"formula identity failed for pair {pair.pair_id} draw {index}"
                )
            row["nonmutation_flags"] = [
                bool(row["nonmutation_flags"][0]),
                bool(row["nonmutation_flags"][1]),
                True,
                True,
                True,
            ]
        q1_after = str(v018._V015._q_parameter_sha256(q1_network))
        q2_after = str(v018._V015._q_parameter_sha256(q2_network))
        if q1_after != q1_before or q2_after != q2_before:
            raise V023SourceAdapterError("Q1/Q2 parameters changed during profile evaluation")
        composition = {
            "pair_id": pair.pair_id,
            "teacher_target_mean": _jsonable(teacher.pair_targets.mean_targets),
            "target_nonzero": True,
        }
        diagnostics = {
            "c1": {
                "kind": "C1_L_VERSUS_Q1_DIAGNOSTIC",
                "rows": c1_rows,
                "nontrivial_count": int(
                    sum(
                        abs(float(value)) >= 0.02
                        for row in c1_rows
                        for value in row["own_normalized"]
                    )
                ),
                "target_filter_applied": False,
            },
            "c2": {
                "kind": "C2_REPRICED_OPS3_CONTEXT_DIAGNOSTIC",
                "rows": c2_rows,
                "exposure_count": 2,
                "nontrivial_count": int(
                    sum(
                        abs(float(value)) >= 0.02
                        for row in c2_rows
                        for value in row["q2_delta"]
                    )
                ),
                "target_filter_applied": False,
                "target_free_inference": True,
                "diagnostic_lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
                "runtime_default_lambda_used_for_target": False,
            },
            "mechanics": {
                "draw_count": DRAW_COUNT,
                "failed_draw_count": int(
                    sum(not bool(item["passed"]) for item in mechanics_by_draw)
                ),
                "failure_codes_by_draw": [
                    list(item["failure_codes"]) for item in mechanics_by_draw
                ],
                "ordinary_failures_retained": True,
            },
            "q1_q2_parameter_sha256_before": {
                "q1": q1_before,
                "q2": q2_before,
            },
            "q1_q2_parameter_sha256_after": {
                "q1": q1_after,
                "q2": q2_after,
            },
            "composition": composition,
        }
        return teacher, profile_rows, diagnostics

    def _evaluate_control(
        self,
        *,
        v018: Any,
        environment: Any,
        env_rng: np.random.Generator,
        step_env: Any,
        world: int,
        anchor_id: str,
        control: LCSRSC3NoCloseControl,
        reference: np.ndarray,
        interval_s: float,
    ) -> dict[str, Any]:
        """Evaluate eligible no-close controls; retain in diagnostics only."""

        result: dict[str, Any] = _control_record(control)
        result["profile_draws"] = []
        if not control.eligible:
            result["evaluation_status"] = "NOT_ELIGIBLE_MISSING_DESTINATION"
            return result
        members = np.asarray(control.member_users, dtype=np.int64)
        proposed = np.asarray(control.designated_actions, dtype=np.int64)
        profiles = _profile_actions(reference, members, proposed)
        for draw_index in range(DRAW_COUNT):
            field = self._make_draw_field(int(world), anchor_id, draw_index)
            original_field = getattr(step_env, "_fading_field", None)
            before = _live_digest(v018, environment, env_rng)
            rng_before = copy.deepcopy(env_rng.bit_generator.state)
            try:
                step_env._fading_field = field
                evaluations = {
                    code: step_env.evaluate_actions(profiles[code], env_rng)
                    for code in PROFILE_ORDER
                }
            finally:
                step_env._fading_field = original_field
            after = _live_digest(v018, environment, env_rng)
            rng_after = copy.deepcopy(env_rng.bit_generator.state)
            field_restored = getattr(step_env, "_fading_field", None) is original_field
            live_unchanged = before == after
            rng_unchanged = _rng_state_unchanged(rng_before, rng_after)
            if not live_unchanged or not rng_unchanged or not field_restored:
                raise V023SourceAdapterError(
                    f"no-close control {control.control_id} mutated frozen inputs"
                )
            records = {
                code: _evaluation_record(
                    evaluations[code], actions=profiles[code], interval_s=interval_s
                )
                for code in PROFILE_ORDER
            }
            source = tuple(control.source_key)
            source_present = {
                code: source in {
                    tuple(key) for key in records[code]["active_beam_keys"]
                }
                for code in PROFILE_ORDER
            }
            # A no-close control is deliberately a negative topology control:
            # the third reference user remains on the source, so the source
            # must remain active even in its joint 11 profile.
            if not all(source_present.values()):
                raise V023SourceAdapterError(
                    f"no-close control {control.control_id} violated source-persistence invariant"
                )
            result["profile_draws"].append({
                "draw_index": draw_index,
                "profiles": records,
                "common_field_sha256": field.root_digest,
                "source_present_by_profile": source_present,
                "nonmutation": {
                    "live_state_unchanged": bool(live_unchanged),
                    "rng_unchanged": bool(rng_unchanged),
                },
            })
        result["evaluation_status"] = "PASS_NO_CLOSE_DIAGNOSTIC"
        return result

    def generate_source_shard(self, spec: Any) -> Mapping[str, Any]:
        """Generate and persist one world source artifact.

        ``spec`` is intentionally duck-typed to avoid importing the staged
        runner at module import time.  It must expose ``world``, ``output``
        and optionally ``preflight_manifest_sha256``.
        """

        world = int(getattr(spec, "world"))
        if world not in tuple(range(2026121705, 2026121713)):
            raise V023SourceAdapterError("world is outside frozen V0.23 panel")
        output = Path(getattr(spec, "output")).resolve()
        if output.exists() or output.is_symlink():
            raise V023SourceAdapterError(f"refusing to overwrite source receipt: {output}")
        sidecar_target = output.with_name(output.stem + ".arrays.npz")
        if sidecar_target.exists() or sidecar_target.is_symlink() or sidecar_target.with_name(sidecar_target.name + ".sha256").exists():
            raise V023SourceAdapterError(f"refusing to overwrite source sidecar: {sidecar_target}")
        expected_manifest_sha256 = getattr(spec, "preflight_manifest_sha256", None)
        v020, v018, q1, q2, auth, manifest_sha = self._authenticate(
            expected_manifest_sha256=expected_manifest_sha256
        )
        preflight_receipt = auth["preflight"]
        inherited = auth["inherited"]
        q1_receipt = auth["q1_receipt"]
        q2_receipt = auth["q2_receipt"]
        q12_authority = auth["q12_authority"]
        try:
            q1_before = str(v018._V015._q_parameter_sha256(q1))
            q2_before = str(v018._V015._q_parameter_sha256(q2))
        except Exception as error:
            raise V023SourceAdapterError("cannot authenticate frozen Q1/Q2 parameter digests") from error
        _digest(q1_before, field="q1_parameter_sha256")
        _digest(q2_before, field="q2_parameter_sha256")
        model_digest = _model_digest(q1, q2, q1_receipt, q2_receipt)
        record = v018._V015._V013.read_prereg(self.config.prereg)
        started = __import__("time").perf_counter()
        world_field = KeyedFadingField.from_components(self.config.source_family, world)
        captures: list[LCSRSC3PredecisionCapture] = []
        q2_contexts: list[Mapping[str, Any]] = []
        bound_records: list[LCSRSC3BoundAnchor | None] = []
        all_pair_teachers: list[tuple[int, LCSRSTwoUserTeacher]] = []
        all_profile_rows: list[dict[str, Any]] = []
        anchor_entries: list[dict[str, Any]] = []
        world_controls: list[dict[str, Any]] = []
        world_live_before = ""
        world_live_after = ""
        world_rng_before = ""
        world_rng_after = ""
        ephemeris_receipt: dict[str, Any]

        with tempfile.TemporaryDirectory(prefix="mcrl-v023-source-tle-") as temporary:
            archive = v018._V015._V013.screen._frozen_archive(
                record, self.config.tle_root, Path(temporary) / "frozen-tle"
            )
            ephemeris_validation = v018._V015._V013.screen.assert_ephemeris_matches_record(
                record, archive=archive
            )
            if not isinstance(ephemeris_validation, Mapping):
                raise V023SourceAdapterError("runtime ephemeris validator returned no receipt")
            ephemeris_receipt = _jsonable(dict(ephemeris_validation))  # type: ignore[assignment]
            environment = v018._V015._V013.screen._make_environment(
                archive, users=v018.USERS
            )
            step_env = environment.environment
            step_env._fading_field = world_field
            env_rng, mobility_rng, _action_rng, _control_rng = (
                v018._V015._V013.screen._evaluation_rngs(world)
            )
            _states, _masks, observation = environment.reset(env_rng, mobility_rng)
            world_live_before = _live_digest(v018, environment, env_rng)
            world_rng_before = _rng_digest(copy.deepcopy(env_rng.bit_generator.state))
            interval_s = float(step_env.driver.config.ephemeris.time_step_s)
            for step_index in range(STEPS_PER_EPISODE):
                if int(observation.step_index) != step_index:
                    raise V023SourceAdapterError("native episode step index drifted")
                anchor_data = _native_q12_anchor(
                    v018=v018,
                    q1=q1,
                    q2=q2,
                    step_env=step_env,
                    observation=observation,
                    model_digest=model_digest,
                )
                background = np.asarray(anchor_data["background"], dtype=np.int64)
                # Initial t=0 is a trajectory anchor only.  C3 source rows are
                # strictly the nine noninitial anchors t=1..9.
                if step_index > 0:
                    anchor_id = f"w{world}:t{step_index}"
                    capture = capture_lcsrs_c3_predecision(
                        step_env,
                        observation,
                        world_id=world,
                        anchor_id=anchor_id,
                        detached_q12=anchor_data["snapshot"],
                        reference_actions=background,
                        opening_feasibility_surface=anchor_data["opening"],
                    )
                    topology = capture.topology
                    captures.append(capture)
                    q2_contexts.append(anchor_data["q2_context"])
                    teachers_for_anchor: list[LCSRSTwoUserTeacher] = []
                    profile_rows_for_anchor: list[dict[str, Any]] = []
                    anchor_diag: dict[str, Any] = {
                        "c1": [],
                        "c2": [],
                        "nonmutation": [],
                    }
                    for pair in topology.pairs:
                        pair_index = len(all_pair_teachers)
                        teacher, profile_rows, diagnostics = self._evaluate_pair(
                            v018=v018,
                            environment=environment,
                            env_rng=env_rng,
                            step_env=step_env,
                            observation=observation,
                            world=world,
                            anchor_id=anchor_id,
                            pair_index=pair_index,
                            pair=pair,
                            anchor_data={**anchor_data, "capture": capture},
                            interval_s=interval_s,
                            q1_network=q1,
                            q2_network=q2,
                            q1_before=q1_before,
                            q2_before=q2_before,
                        )
                        teachers_for_anchor.append(teacher)
                        all_pair_teachers.append((len(captures) - 1, teacher))
                        profile_rows_for_anchor.extend(profile_rows)
                        all_profile_rows.extend(profile_rows)
                        anchor_diag["c1"].append(diagnostics["c1"])
                        anchor_diag["c2"].append(diagnostics["c2"])
                        anchor_diag["nonmutation"].extend(
                            [row["nonmutation_flags"] for row in profile_rows]
                        )
                    bound: LCSRSC3BoundAnchor | None = None
                    if topology.retained_for_fitting:
                        bound = bind_lcsrs_c3_anchor(capture, teachers_for_anchor)
                    bound_records.append(bound)
                    controls = [
                        self._evaluate_control(
                            v018=v018,
                            environment=environment,
                            env_rng=env_rng,
                            step_env=step_env,
                            world=world,
                            anchor_id=anchor_id,
                            control=control,
                            reference=background,
                            interval_s=interval_s,
                        )
                        for control in topology.no_close_controls
                    ]
                    world_controls.extend(controls)
                    topology_json = _topology_record(topology)
                    enumeration = {
                        "schema": f"{SOURCE_ARTIFACT_SCHEMA}-enumeration-v1",
                        "world": world,
                        "phase": step_index,
                        "anchor_id": anchor_id,
                        "pairs": [_pair_record(pair) for pair in topology.pairs],
                        "no_close_controls": [_control_record(control) for control in topology.no_close_controls],
                        "exclusions": _derive_exclusions(topology),
                        "outcome_filter_applied": False,
                    }
                    teachers_json = {
                        "schema": f"{SOURCE_ARTIFACT_SCHEMA}-teacher-v1",
                        "pairs": [_teacher_record(teacher) for teacher in teachers_for_anchor],
                    }
                    surface_json = {
                        "schema": f"{SOURCE_ARTIFACT_SCHEMA}-surface-v1",
                        "retained_for_fitting": topology.retained_for_fitting,
                        "record": None if bound is None else {
                            "world_id": bound.record.world_id,
                            "phase": bound.record.phase,
                            "anchor_id": bound.record.anchor_id,
                            "content_digest": bound.record.content_digest,
                            "surface_digest": bound.surface.content_digest,
                            "class_counts": topology.class_counts,
                        },
                    }
                    anchor_entries.append({
                        "anchor_id": anchor_id,
                        "phase": step_index,
                        "predecision_sha256": capture.content_digest,
                        "native_observation_provenance": _jsonable(capture.native_observation_provenance.__dict__),
                        "state_schema": capture.state_schema,
                        "state_schema_sha256": capture.state_schema_sha256,
                        "state_sha256": capture.state_sha256,
                        "q12_snapshot_sha256": capture.topology.capture.q12_snapshot.content_digest,
                        "q12_model_sha256": capture.topology.capture.q12_snapshot.model_digest,
                        "q12_source_state_sha256": capture.topology.capture.q12_snapshot.source_state_digest,
                        "q12_event_sha256": capture.topology.capture.q12_snapshot.native_observation_event_digest,
                        "reference_actions_sha256": _array_digest(background, domain="v023-reference-actions"),
                        "q2_context": {
                            "schema": "multi-catfish-mcrl-v023-q2-context-v1",
                            "q2_state_schema": V014_Q2_STATE_SCHEMA,
                            "q2_state_schema_sha256": V014_Q2_STATE_SCHEMA_SHA256,
                            "q2_state_sha256": anchor_data["q2_state_sha256"],
                            "ops3_anchor_sha256": anchor_data["ops3_anchor_sha256"],
                            "ops3_tracker_seed_sha256": anchor_data["ops3_tracker_seed_sha256"],
                            "ops3_projection_sha256": anchor_data["ops3_projection_sha256"],
                            "horizon": int(anchor_data["q2_context"]["horizon"]),
                            "future_d2_indices": anchor_data["ops3_future_d2_indices"],
                            "sample_times_utc": anchor_data["ops3_sample_times_utc"],
                            "offset_times_utc": anchor_data["ops3_offset_times_utc"],
                            "q1_reference_actions_sha256": _array_digest(
                                anchor_data["q1_reference"],
                                domain="v023-q1-reference-actions",
                            ),
                            "q12_reference_actions_sha256": _array_digest(
                                background, domain="v023-reference-actions"
                            ),
                            "q1_to_q12_argmax_change_count": int(
                                np.count_nonzero(
                                    np.asarray(anchor_data["q1_reference"], dtype=np.int64)
                                    != background
                                )
                            ),
                            "served_user_count": int(np.count_nonzero(background >= 0)),
                            "target_values_sha256": _array_digest(
                                anchor_data["q2_context"]["target_values"],
                                domain="v023-repriced-ops3-target-values",
                            ),
                            "feature_surface_sha256": _array_digest(
                                anchor_data["q2_context"]["features"],
                                domain="v023-ops3-feature-surface",
                            ),
                            "persistence_sha256": _array_digest(
                                anchor_data["q2_context"]["persistence"],
                                domain="v023-ops3-persistence",
                            ),
                            "target_free_inference": True,
                            "absorbing_persistence_checked": True,
                            "terminal_zero_checked": True,
                            "opening_mask_checked": True,
                            "frozen_background_formula_checked": True,
                            "diagnostic_lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
                            "ops3_runtime_default_lambda_hex": OPS3_LAMBDA_BITS_PER_J.hex(),
                            "runtime_default_lambda_used_for_target": False,
                        },
                        "topology": topology_json,
                        "enumeration": enumeration,
                        "teachers": teachers_json,
                        "surface": surface_json,
                        "enumeration_sha256": canonical_sha256(enumeration),
                        "topology_sha256": canonical_sha256(topology_json),
                        "teacher_sha256": canonical_sha256(teachers_json),
                        "surface_sha256": canonical_sha256(surface_json),
                        "topology_status": topology.retention_status,
                        "retained_for_fitting": topology.retained_for_fitting,
                        "retention_status": topology.retention_status,
                        "class_counts": topology.class_counts,
                        "pair_count": topology.pair_count,
                        "no_close_count": topology.no_close_count,
                        "profile_count": topology.pair_count * DRAW_COUNT * 4,
                        "draw_count": DRAW_COUNT,
                        "nonmutation_receipt": {
                            "profile_rows": len(profile_rows_for_anchor),
                            "all_rows_unchanged": all(bool(row[0]) for row in anchor_diag["nonmutation"]),
                            "all_rng_unchanged": all(bool(row[1]) for row in anchor_diag["nonmutation"]),
                            "all_networks_unchanged": all(bool(row[2]) for row in anchor_diag["nonmutation"]),
                        },
                        "c1_diagnostic": anchor_diag["c1"],
                        "c2_diagnostic": anchor_diag["c2"],
                        "composition": None if bound is None else _composition_record(
                            bound=bound,
                            snapshot=anchor_data["snapshot"],
                            mask=np.asarray(anchor_data["masks"], dtype=np.bool_),
                        ),
                    })
                outcome = environment.step(background, env_rng)
                if outcome.done and step_index != STEPS_PER_EPISODE - 1:
                    raise V023SourceAdapterError("episode terminated before ten anchors")
                if not outcome.done and step_index == STEPS_PER_EPISODE - 1:
                    raise V023SourceAdapterError("episode did not terminate at ten anchors")
                if not outcome.done:
                    observation = _step_result_observation(environment, outcome)
            world_live_after = _live_digest(v018, environment, env_rng)
            world_rng_after = _rng_digest(copy.deepcopy(env_rng.bit_generator.state))

        arrays = _build_sidecar_arrays(
            captures=captures,
            q2_contexts=q2_contexts,
            anchor_records=bound_records,
            pair_teachers=all_pair_teachers,
            profile_rows=all_profile_rows,
            controls=world_controls,
        )
        sidecar = output.with_name(output.stem + ".arrays.npz")
        sidecar_digest = _write_npz_once(sidecar, arrays)
        _write_once_bytes(
            sidecar.with_name(sidecar.name + ".sha256"),
            f"{sidecar_digest}  {sidecar.name}\n".encode("ascii"),
        )
        relative_sidecar = sidecar.name
        array_metadata = _array_metadata(arrays)
        array_body = {
            "schema": f"{SOURCE_ARTIFACT_SCHEMA}-arrays-v1",
            "npz_relative_path": relative_sidecar,
            "npz_sha256": sidecar_digest,
            "npz_sha256_file": sidecar.name + ".sha256",
            "array_metadata": array_metadata,
            "allow_pickle": False,
            "array_count": len(arrays),
            "profile_order": list(PROFILE_ORDER),
            "draw_count": DRAW_COUNT,
            "profile_active_beam_max": int(arrays["profile_active_beam_keys"].shape[2]),
            "profile_active_satellite_max": int(arrays["profile_active_satellites"].shape[2]),
            "control_active_beam_max": int(arrays["control_profile_active_beam_keys"].shape[2]),
            "control_active_satellite_max": int(arrays["control_profile_active_satellites"].shape[2]),
            "padding": {"physical_keys": -1, "satellite_ids": -1, "powers": 0.0},
        }
        enumeration_all = {
            "schema": f"{SOURCE_ARTIFACT_SCHEMA}-enumeration-v1",
            "world": world,
            "anchors": [entry["enumeration"] for entry in anchor_entries],
            "outcome_filter_applied": False,
        }
        topology_all = {
            "schema": f"{SOURCE_ARTIFACT_SCHEMA}-topology-v1",
            "world": world,
            "anchors": [entry["topology"] for entry in anchor_entries],
        }
        teachers_all = {
            "schema": f"{SOURCE_ARTIFACT_SCHEMA}-teacher-v1",
            "world": world,
            "anchors": [entry["teachers"] for entry in anchor_entries],
        }
        surfaces_all = {
            "schema": f"{SOURCE_ARTIFACT_SCHEMA}-surface-v1",
            "world": world,
            "anchors": [entry["surface"] for entry in anchor_entries],
        }
        placebo_strata = _placebo_strata_receipt(
            anchor_records=bound_records,
        )
        enumerated_pair_count = sum(int(entry["pair_count"]) for entry in anchor_entries)
        fitting_pair_count = sum(
            len(bound.teachers) for bound in bound_records if bound is not None
        )
        fitting_supported_count = sum(
            int(np.count_nonzero(bound.surface.row_class == 3))
            for bound in bound_records
            if bound is not None
        )
        target_values = np.concatenate(
            [
                np.asarray(teacher.pair_targets.normalized_targets_by_draw, dtype=np.float64).reshape(-1)
                for _, teacher in all_pair_teachers
            ]
        ) if all_pair_teachers else np.zeros((0,), dtype=np.float64)
        q1_after = str(v018._V015._q_parameter_sha256(q1))
        q2_after = str(v018._V015._q_parameter_sha256(q2))
        if q1_after != q1_before or q2_after != q2_before:
            raise V023SourceAdapterError("Q1/Q2 parameters changed during source rollout")
        payload: dict[str, Any] = {
            "schema": "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-shard",
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "contract_sha256": "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a",
            "preflight_manifest_sha256": manifest_sha,
            "split": "TRAIN_DEVELOPMENT",
            "world": world,
            "world_receipt": {
                "world": world,
                "field_component": self.config.source_family,
                "field_root_digest": world_field.root_digest,
                "phase_count": len(anchor_entries),
                "anchor_ids": [entry["anchor_id"] for entry in anchor_entries],
                "q1_parameter_sha256": q1_before,
                "q2_parameter_sha256": q2_before,
                "q1_parameter_sha256_after": q1_after,
                "q2_parameter_sha256_after": q2_after,
                "environment_initial_digest": world_live_before,
                "environment_final_digest": world_live_after,
                "rng_initial_digest": world_rng_before,
                "rng_final_digest": world_rng_after,
                "source_rollout_state_transition_observed": bool(world_live_before != world_live_after),
                "test_split_opened": False,
                "learner_update": False,
                "episode_training": False,
            },
            "ephemeris_validation": ephemeris_receipt,
            "q12_background": {
                "lineage": self.config.lineage,
                "checkpoint_path": q1_receipt["checkpoint_path"],
                "checkpoint_sha256": q1_receipt["checkpoint_sha256"],
                "q1_checkpoint_path": q1_receipt["checkpoint_path"],
                "q1_checkpoint_sha256": q1_receipt["checkpoint_sha256"],
                "q2_checkpoint_path": q2_receipt["checkpoint_path"],
                "q2_checkpoint_sha256": q2_receipt["checkpoint_sha256"],
                "q1_receipt": _jsonable(q1_receipt),
                "q2_receipt": _jsonable(q2_receipt),
                "q12_authority": _jsonable(q12_authority),
                "q1_parameter_sha256": q1_before,
                "q2_parameter_sha256": q2_before,
                "q12_model_sha256": model_digest,
                "lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
                "kappa_bits_hex": KAPPA_BITS.hex(),
                "q12_unit": "authenticated-normalized-q1-plus-q2-float32",
                "state_schema": "native-ee-axis-state-v1",
            },
            "field_manifest": {
                "family": self.config.source_family,
                "key_axes": ["family", "world", "anchor", "draw", "event", "step_index", "norad_id"],
                "root_excludes": ["pair", "profile"],
                "profile_order": list(PROFILE_ORDER),
                "world_rollout_root_digest": world_field.root_digest,
                "draw_root_rule": "KeyedFadingField.from_components(family, world, anchor_id, draw_index)",
            },
            "anchors": anchor_entries,
            "enumeration": enumeration_all,
            "topology": topology_all,
            "teacher": teachers_all,
            "surface": surfaces_all,
            "controls": {
                "no_close": world_controls,
                "declared_count": len(world_controls),
                "evaluated_count": sum(
                    1 for control in world_controls if control.get("evaluation_status") == "PASS_NO_CLOSE_DIAGNOSTIC"
                ),
                "raw_profile_draws_serialized": True,
                "source_persistence_invariant_checked": True,
                "negative_rows_retained": True,
                "masked_and_unsupported_zero_receipts": True,
            },
            "placebo_strata": placebo_strata,
            "diagnostics": {
                "c1": "serialized_per_pair_per_draw_in_anchor_entries",
                "c2": "serialized_per_pair_per_draw_in_anchor_entries",
                "formula_identity": "serialized_per_draw_in_teacher_and_npz",
                "all_pairs_enumerated": True,
                "outcome_filter_applied": False,
                "first_qualified_pair_selection": False,
                "target_value_counts": {
                    "total": int(target_values.size),
                    "negative": int(np.count_nonzero(target_values < 0.0)),
                    "zero": int(np.count_nonzero(target_values == 0.0)),
                    "positive": int(np.count_nonzero(target_values > 0.0)),
                },
                "inherited_validators": inherited,
            },
            "arrays": array_body,
            "source_artifact_schema": SOURCE_ARTIFACT_SCHEMA,
            "source_artifact_version": SOURCE_ARTIFACT_VERSION,
            "enumeration_sha256": canonical_sha256(enumeration_all),
            "topology_sha256": canonical_sha256(topology_all),
            "teacher_sha256": canonical_sha256(teachers_all),
            "surface_sha256": canonical_sha256(surfaces_all),
            "record_count": int(sum(1 for item in bound_records if item is not None)),
            "pair_count": int(enumerated_pair_count),
            "enumerated_pair_count": int(enumerated_pair_count),
            "fitting_pair_count": int(fitting_pair_count),
            "supported_count": int(fitting_supported_count),
            "fitting_supported_count": int(fitting_supported_count),
            "placebo_eligible_count": int(placebo_strata["placebo_eligible_count"]),
            "execution_addendum_path": str(EXECUTION_ADDENDUM_PATH),
            "execution_addendum_sha256": EXECUTION_ADDENDUM_SHA256,
            "placebo_key": PLACEBO_KEY,
            "placebo_key_sha256": PLACEBO_KEY_SHA256,
            "c1_c2_parameter_unchanged": bool(q1_before == q1_after and q2_before == q2_after),
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
            "elapsed_s": float(__import__("time").perf_counter() - started),
        }
        # The runner adds the receipt seal.  Returning one here would violate
        # its writer-owned-seal boundary.
        return _jsonable(payload)  # type: ignore[return-value]


# Discoverable aliases used by the staged launcher and integration tests.
V023PhysicalSourceAdapter = V023RuntimeSourceAdapter
SourceAdapter = V023RuntimeSourceAdapter


__all__ = [
    "SOURCE_ARTIFACT_SCHEMA",
    "SOURCE_ARTIFACT_VERSION",
    "V023SourceAdapterError",
    "V023SourceAdapterConfig",
    "V023RuntimeSourceAdapter",
    "V023PhysicalSourceAdapter",
    "SourceAdapter",
    "canonical_bytes",
    "canonical_sha256",
]
