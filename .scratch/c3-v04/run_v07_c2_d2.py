#!/usr/bin/env python3
"""V0.7 C2 D2 development calibration, source preparation, sharding, and merge.

``calibrate`` is the only command allowed while the D2 preregistration is a
draft.  Once the preregistration is frozen, ``prepare`` records the complete
outcome-blind native-mask selection receipt, ``shard`` records one frozen Q13
lineage, and ``adjudicate`` strictly merges exactly three shards into the
pure-data D2 adjudicator.  No command in this runner trains Q2, opens TEST, or
launches an EE evaluation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.runtime.ee_axis_v07_c2_dataset import (  # noqa: E402
    V07C2Dataset,
    canonical_json_bytes,
)
from mcrl.runtime.ee_axis_v07_c2_d2 import (  # noqa: E402
    D2ActionRecord,
    D2AdjudicationResult,
    D2_INVALID_NO_INFERENCE,
    D2_LINEAGES,
    D2_LINEAGE_PAIRS,
    D2Metrics,
    D2MechanicsReceipt,
    D2PhysicalAnchor,
    D2Q13SurfaceReceipt,
    D2SelectionReceipt,
    D2LineageDecisionCapture,
    D2_PASS_AUTHORIZE_D3_IMPLEMENTATION,
    D2_SEEDS,
    D2_EXPECTED_ANCHORS,
    D2_DEFAULT_KAPPA_BITS,
    D2_INTERVAL_S,
    D2_IQR_METHOD,
    D2_LAMBDA_BITS_PER_J,
    adjudicate_d2,
)
from mcrl.runtime.ee_axis_v07_c2_focal_next import (  # noqa: E402
    FocalNextSurplus,
    focal_next_surplus_target,
)
from mcrl.runtime.ee_axis_v07_c2_state import (  # noqa: E402
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)


CALIBRATION_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-development-calibration-v1"
PREPARE_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-prepare-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-lineage-shard-v1"
CALIBRATION_SEED = 2026104099
SEALED_CALIBRATION_RELATIVE = Path(
    "artifacts/multi-catfish-v07-c2-development-calibration-20260902-r1/calibration.json"
)
SEALED_CALIBRATION_FILE_SHA256 = (
    "a061429c4326934cd33596ae6c89dfc54f8cd043ebe56544340c5a3fa3aa62b5"
)
SEALED_CALIBRATION_PAYLOAD_SHA256 = (
    "6fc168578c97bd6e6f09013fd7b4167e2b2b34189bb549f23b48ae8025706693"
)
FORMAL_ATTEMPT_ID = "multi-catfish-v07-c2-d2-formal-20260902-r1"
FORMAL_ATTEMPT_RELATIVE = Path("artifacts") / FORMAL_ATTEMPT_ID
D2_WINDOWS = {"early": (1, 2), "late": (5, 6)}
LINEAGES = ("q13-a", "q13-b", "q13-c")
KAPPA_BITS = D2_DEFAULT_KAPPA_BITS
LAMBDA_BITS_PER_J = D2_LAMBDA_BITS_PER_J
INTERVAL_S = D2_INTERVAL_S
# Filled only after the complete runner/tests/review freeze.  ``prepare`` and
# ``shard`` fail closed while this remains unset; development calibration is
# intentionally independent of the future evidence preregistration.
EXPECTED_D2_PREREG_SHA256 = ""
ADJUDICATION_SCHEMA = "multi-catfish-mcrl-v07-c2-d2-adjudication-run-v1"
CAPTURE_RECEIPT_SCHEMA = "multi-catfish-mcrl-v07-c2-decision-capture-v1"
BRANCH_RECEIPT_SCHEMA = "multi-catfish-mcrl-v07-c2-branch-receipt-v1"


class V07D2RunnerError(RuntimeError):
    """The development calibration must stop without producing evidence."""


def _formula_constants() -> dict[str, str]:
    return {
        "lambda_bits_per_j": LAMBDA_BITS_PER_J.hex(),
        "interval_s": INTERVAL_S.hex(),
        "kappa_bits": KAPPA_BITS.hex(),
        "iqr_method": D2_IQR_METHOD,
    }


def _capture_formula_constants() -> dict[str, str]:
    return {
        "lambda_bits_per_j": LAMBDA_BITS_PER_J.hex(),
        "interval_s": INTERVAL_S.hex(),
        "kappa_bits": KAPPA_BITS.hex(),
    }


@dataclass(frozen=True)
class CarrierAnchorSelection:
    """Outcome-blind carrier scan result plus every inspected window step."""

    target_step: int
    focal_user: int
    carrier_history: tuple[np.ndarray, ...]
    eligible_users_by_step: tuple[tuple[int, tuple[int, ...]], ...]

    def __iter__(self):
        """Keep the original three-value unpacking API source-compatible."""

        yield self.target_step
        yield self.focal_user
        yield self.carrier_history


def _array_sha256(value: object, *, dtype: np.dtype[Any]) -> str:
    """Digest dtype, shape, and C-order bytes for receipt-bound arrays."""

    array = np.ascontiguousarray(np.asarray(value, dtype=dtype))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii"))
    digest.update(b"\0")
    digest.update(array.tobytes())
    return digest.hexdigest()


def _is_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_digest(value: object, *, field: str) -> str:
    if not _is_digest(value):
        raise V07D2RunnerError(f"{field} is not a lower-case SHA-256 digest")
    return str(value)


def _decode_hex_float(value: object, *, field: str) -> float:
    if not isinstance(value, str):
        raise V07D2RunnerError(f"{field} is not a hexadecimal float")
    try:
        result = float.fromhex(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise V07D2RunnerError(f"{field} is not a hexadecimal float") from error
    if not np.isfinite(result) or result.hex() != value:
        raise V07D2RunnerError(f"{field} is not a canonical finite hexadecimal float")
    return result


def _decode_hex_vector(value: object, *, field: str, length: int) -> np.ndarray:
    if not isinstance(value, list) or len(value) != length:
        raise V07D2RunnerError(f"{field} has the wrong vector length")
    result = np.asarray(
        [_decode_hex_float(item, field=f"{field}[{index}]") for index, item in enumerate(value)],
        dtype=np.float64,
    )
    result.setflags(write=False)
    return result


def _decode_action_vector(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value:
        raise V07D2RunnerError(f"{field} must be a nonempty action vector")
    if any(type(action) is not int for action in value):
        raise V07D2RunnerError(f"{field} must contain exact integer actions")
    result = np.asarray(value, dtype=np.int64)
    if np.any(result < -1) or np.any(result >= 28):
        raise V07D2RunnerError(f"{field} contains an out-of-space action")
    result.setflags(write=False)
    return result


def _decode_bool_matrix(value: object, *, field: str) -> np.ndarray:
    if not isinstance(value, list) or not value:
        raise V07D2RunnerError(f"{field} must be a nonempty mask matrix")
    if any(not isinstance(row, list) or len(row) != 28 for row in value):
        raise V07D2RunnerError(f"{field} must have native 28-action rows")
    if any(type(item) is not bool for row in value for item in row):
        raise V07D2RunnerError(f"{field} must contain boolean mask entries")
    result = np.asarray(value, dtype=np.bool_)
    result.setflags(write=False)
    return result


def _selection_receipt_payload(
    *,
    window: str,
    eligible_users_by_step: tuple[tuple[int, tuple[int, ...]], ...],
) -> dict[str, object]:
    receipt = D2SelectionReceipt(
        window=window,
        eligible_users_by_step=eligible_users_by_step,
    )
    return receipt.to_payload()


def _prepare_anchor_digest_payload(raw: Mapping[str, object]) -> dict[str, object]:
    """Return the exact raw payload covered by ``anchor_sha256``."""

    expected = {
        "source_seed",
        "window",
        "target_step",
        "focal_user",
        "focal_mask",
        "all_user_masks",
        "all_user_masks_sha256",
        "anchor_state",
        "anchor_state_sha256",
        "carrier_history",
        "carrier_history_sha256",
        "crn_sha256",
        "selection_receipt",
    }
    return {key: raw[key] for key in expected}


def _validate_prepare_anchor(raw: object) -> dict[str, object]:
    """Validate and normalize one target-free anchor in a prepare payload."""

    if not isinstance(raw, dict):
        raise V07D2RunnerError("D2 prepare anchor is malformed")
    required = {
        "source_seed",
        "window",
        "target_step",
        "focal_user",
        "focal_mask",
        "all_user_masks",
        "all_user_masks_sha256",
        "anchor_state",
        "anchor_state_sha256",
        "carrier_history",
        "carrier_history_sha256",
        "crn_sha256",
        "selection_receipt",
        "anchor_digest_payload",
        "anchor_sha256",
    }
    if set(raw) != required:
        raise V07D2RunnerError("D2 prepare anchor schema drifted")
    seed = raw["source_seed"]
    target_step = raw["target_step"]
    focal_user = raw["focal_user"]
    if type(seed) is not int or seed not in D2_SEEDS:
        raise V07D2RunnerError("D2 prepare anchor seed is outside the frozen block")
    if type(target_step) is not int or target_step < 0:
        raise V07D2RunnerError("D2 prepare target step is malformed")
    if type(focal_user) is not int or focal_user < 0:
        raise V07D2RunnerError("D2 prepare focal user is malformed")
    window = raw["window"]
    if window not in D2_WINDOWS:
        raise V07D2RunnerError("D2 prepare anchor window is malformed")
    mask_raw = raw["focal_mask"]
    if not isinstance(mask_raw, list) or len(mask_raw) != 28 or any(type(item) is not bool for item in mask_raw):
        raise V07D2RunnerError("D2 prepare focal mask is not a native boolean mask")
    mask = np.asarray(mask_raw, dtype=np.bool_)
    if int(np.count_nonzero(mask)) < 3:
        raise V07D2RunnerError("D2 prepare focal mask has fewer than three legal actions")
    all_masks = _decode_bool_matrix(raw["all_user_masks"], field="all_user_masks")
    if focal_user >= all_masks.shape[0] or not np.array_equal(all_masks[focal_user], mask):
        raise V07D2RunnerError("D2 prepare focal mask disagrees with the full mask matrix")
    all_masks_digest = _require_digest(
        raw["all_user_masks_sha256"], field="all_user_masks_sha256"
    )
    if _array_sha256(all_masks, dtype=np.dtype(np.bool_)) != all_masks_digest:
        raise V07D2RunnerError("D2 prepare full mask matrix digest drifted")
    selection_raw = raw["selection_receipt"]
    if not isinstance(selection_raw, dict):
        raise V07D2RunnerError("D2 prepare selection receipt is malformed")
    if set(selection_raw) != {
        "schema",
        "window",
        "eligible_users_by_step",
        "selection_rule",
        "outcome_blind",
    }:
        raise V07D2RunnerError("D2 prepare selection receipt schema drifted")
    entries_raw = selection_raw["eligible_users_by_step"]
    if not isinstance(entries_raw, list):
        raise V07D2RunnerError("D2 prepare eligible-step receipt is malformed")
    entries: list[tuple[int, tuple[int, ...]]] = []
    for entry in entries_raw:
        if not isinstance(entry, list) or len(entry) != 2:
            raise V07D2RunnerError("D2 prepare eligible-step entry is malformed")
        step, users_raw = entry
        if type(step) is not int or not isinstance(users_raw, list):
            raise V07D2RunnerError("D2 prepare eligible-step entry is malformed")
        if any(type(user) is not int or user < 0 for user in users_raw):
            raise V07D2RunnerError("D2 prepare eligible user ID is malformed")
        entries.append((step, tuple(users_raw)))
    selection = D2SelectionReceipt(
        schema=selection_raw["schema"],
        window=selection_raw["window"],
        eligible_users_by_step=tuple(entries),
        selection_rule=selection_raw["selection_rule"],
        outcome_blind=selection_raw["outcome_blind"],
    )
    selection.verify(anchor_step=target_step, focal_user=focal_user)
    if selection.to_payload() != selection_raw:
        raise V07D2RunnerError("D2 prepare selection receipt is not canonical")
    state_raw = raw["anchor_state"]
    if not isinstance(state_raw, list):
        raise V07D2RunnerError("D2 prepare anchor state is malformed")
    state = np.asarray(
        [_decode_hex_float(item, field=f"anchor_state[{index}]") for index, item in enumerate(state_raw)],
        dtype=np.float32,
    )
    if state.shape != (228,):
        raise V07D2RunnerError("D2 prepare anchor state has the wrong dimension")
    state_digest = _require_digest(raw["anchor_state_sha256"], field="anchor_state_sha256")
    if _array_sha256(state, dtype=np.dtype(np.float32)) != state_digest:
        raise V07D2RunnerError("D2 prepare anchor state digest drifted")
    carrier_raw = raw["carrier_history"]
    if not isinstance(carrier_raw, list) or not carrier_raw:
        raise V07D2RunnerError("D2 prepare carrier history is malformed")
    carrier: list[list[int]] = []
    for index, actions in enumerate(carrier_raw):
        if not isinstance(actions, list) or not actions or any(type(action) is not int for action in actions):
            raise V07D2RunnerError(f"D2 prepare carrier action {index} is malformed")
        if any(action < -1 or action >= 28 for action in actions):
            raise V07D2RunnerError("D2 prepare carrier action is outside the native space")
        carrier.append(list(actions))
    carrier_digest = _require_digest(raw["carrier_history_sha256"], field="carrier_history_sha256")
    if hashlib.sha256(canonical_json_bytes(carrier)).hexdigest() != carrier_digest:
        raise V07D2RunnerError("D2 prepare carrier history digest drifted")
    crn_digest = _require_digest(raw["crn_sha256"], field="crn_sha256")
    digest_payload = raw["anchor_digest_payload"]
    if not isinstance(digest_payload, dict):
        raise V07D2RunnerError("D2 prepare anchor digest payload is malformed")
    expected_payload = _prepare_anchor_digest_payload(raw)
    if digest_payload != expected_payload:
        raise V07D2RunnerError("D2 prepare anchor digest payload drifted")
    anchor_digest = _require_digest(raw["anchor_sha256"], field="anchor_sha256")
    if hashlib.sha256(canonical_json_bytes(expected_payload)).hexdigest() != anchor_digest:
        raise V07D2RunnerError("D2 prepare anchor digest drifted")
    normalized = dict(raw)
    normalized["focal_mask"] = [bool(item) for item in mask.tolist()]
    normalized["all_user_masks"] = [
        [bool(item) for item in row.tolist()] for row in all_masks
    ]
    normalized["anchor_state"] = [float(item).hex() for item in state.tolist()]
    normalized["carrier_history"] = carrier
    return normalized


def _load(path: Path, *, prefix: str) -> Any:
    source = Path(path)
    name = prefix + hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise V07D2RunnerError(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _canonical_write_once(path: Path, payload: object) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload) + b"\n"
    try:
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
    except FileExistsError as error:
        raise V07D2RunnerError(f"refusing to overwrite evidence output: {target}") from error
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            target.unlink()
        except OSError:
            pass
        raise


def _file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V07D2RunnerError(f"missing regular authority file: {source}")
    return hashlib.sha256(source.read_bytes()).hexdigest()


def _canonical_read(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V07D2RunnerError(f"missing regular JSON: {source}")
    raw = source.read_bytes()
    try:
        value = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise V07D2RunnerError(f"invalid canonical JSON: {source}") from error
    if not isinstance(value, dict) or raw != canonical_json_bytes(value) + b"\n":
        raise V07D2RunnerError(f"JSON is not canonical: {source}")
    return value


def _formal_output_path(stage: str, *, lineage: str | None = None) -> Path:
    root = REPO / FORMAL_ATTEMPT_RELATIVE
    if stage == "prepare" and lineage is None:
        return root / "prepare.json"
    if stage == "shard" and lineage in LINEAGES:
        return root / f"shard-{lineage}.json"
    if stage == "adjudicate" and lineage is None:
        return root / "adjudication.json"
    raise V07D2RunnerError("formal D2 stage identity is malformed")


def _claim_formal_stage(
    *,
    stage: str,
    output: Path,
    prereg_sha256: str,
    lineage: str | None = None,
) -> str:
    """Atomically seal a formal stage before it can inspect target outcomes."""

    expected_output = _formal_output_path(stage, lineage=lineage).resolve()
    if Path(output).resolve() != expected_output:
        raise V07D2RunnerError(
            f"formal {stage} output must be the fixed attempt path {expected_output}"
        )
    marker = expected_output.with_suffix(".started.json")
    body = {
        "schema": "multi-catfish-mcrl-v07-c2-d2-attempt-marker-v1",
        "attempt_id": FORMAL_ATTEMPT_ID,
        "stage": stage,
        "lineage": lineage,
        "prereg_sha256": _require_digest(prereg_sha256, field="prereg_sha256"),
        "output_relative": expected_output.relative_to(REPO.resolve()).as_posix(),
        "retry_index": 0,
        "replacement_used": False,
    }
    marker_sha256 = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    _canonical_write_once(marker, body | {"marker_sha256": marker_sha256})
    return marker_sha256


def _verify_formal_stage_marker(
    *,
    stage: str,
    marker_sha256: object,
    prereg_sha256: str,
    lineage: str | None = None,
) -> None:
    output = _formal_output_path(stage, lineage=lineage)
    marker = output.with_suffix(".started.json")
    payload = _canonical_read(marker)
    body = dict(payload)
    supplied = body.pop("marker_sha256", None)
    if supplied != marker_sha256 or supplied != hashlib.sha256(
        canonical_json_bytes(body)
    ).hexdigest():
        raise V07D2RunnerError(f"formal {stage} attempt marker digest drifted")
    if body != {
        "schema": "multi-catfish-mcrl-v07-c2-d2-attempt-marker-v1",
        "attempt_id": FORMAL_ATTEMPT_ID,
        "stage": stage,
        "lineage": lineage,
        "prereg_sha256": prereg_sha256,
        "output_relative": output.resolve().relative_to(REPO.resolve()).as_posix(),
        "retry_index": 0,
        "replacement_used": False,
    }:
        raise V07D2RunnerError(f"formal {stage} attempt marker boundary drifted")


def _read_sealed_calibration(path: Path) -> dict[str, Any]:
    source = Path(path).resolve()
    expected = (REPO / SEALED_CALIBRATION_RELATIVE).resolve()
    if source != expected:
        raise V07D2RunnerError("prepare must consume the one sealed calibration path")
    if _file_sha256(source) != SEALED_CALIBRATION_FILE_SHA256:
        raise V07D2RunnerError("sealed calibration file digest drifted")
    payload = _canonical_read(source)
    body = dict(payload)
    supplied = body.pop("payload_sha256", None)
    if (
        supplied != SEALED_CALIBRATION_PAYLOAD_SHA256
        or hashlib.sha256(canonical_json_bytes(body)).hexdigest() != supplied
    ):
        raise V07D2RunnerError("sealed calibration payload digest drifted")
    if (
        payload.get("schema") != CALIBRATION_SCHEMA
        or payload.get("claim_ceiling")
        != "DEVELOPMENT_PLUMBING_AND_WALL_TIME_ONLY"
        or payload.get("source_seed") != CALIBRATION_SEED
        or payload.get("lineage") != "q13-a"
        or payload.get("test_split_opened") is not False
        or payload.get("training") is not False
        or payload.get("d2_authorized") is not False
    ):
        raise V07D2RunnerError("sealed calibration boundary is malformed")
    return payload


def _require_frozen_d2_prereg(path: Path) -> str:
    if len(EXPECTED_D2_PREREG_SHA256) != 64:
        raise V07D2RunnerError("D2 preregistration has not been frozen")
    observed = _file_sha256(path)
    if observed != EXPECTED_D2_PREREG_SHA256:
        raise V07D2RunnerError("D2 preregistration digest drifted")
    text = Path(path).read_text(encoding="utf-8")
    if "Status: `PREOUTCOME_FROZEN" not in text:
        raise V07D2RunnerError("D2 preregistration status is not frozen")
    return observed


def _modules() -> tuple[Any, Any, Any, str]:
    live_v06 = _load(HERE / "v06_c2_k1_live_adapter.py", prefix="v06_auth_for_v07_")
    runner_v06 = _load(HERE / "run_v06_c2_k1_t1.py", prefix="v06_runner_for_v07_")
    live_v07 = _load(HERE / "v07_c2_focal_next_live_adapter.py", prefix="v07_live_")
    support = runner_v06._support_census_loader()
    simulator_manifest = support._production_source_manifest(
        support._production_modules()
    )
    simulator_manifest_sha256 = simulator_manifest.get("source_manifest_sha256")
    if not isinstance(simulator_manifest_sha256, str) or len(simulator_manifest_sha256) != 64:
        raise V07D2RunnerError("simulator source manifest is malformed")
    return live_v06, runner_v06, live_v07, simulator_manifest_sha256


def _code_authority() -> dict[str, str]:
    paths = (
        HERE / "run_v07_c2_d2.py",
        HERE / "v07_c2_focal_next_live_adapter.py",
        HERE / "run_v06_c2_k1_t1.py",
        HERE / "v06_c2_k1_live_adapter.py",
        HERE / "run_v04_c2_support_complete_census.py",
        REPO / "src/mcrl/runtime/ee_axis_v07_c2_focal_next.py",
        REPO / "src/mcrl/runtime/ee_axis_v07_c2_dataset.py",
        REPO / "src/mcrl/runtime/ee_axis_v07_c2_d2.py",
        REPO / "src/mcrl/runtime/ee_axis_v07_c2_policy.py",
        REPO / "src/mcrl/runtime/ee_axis_v07_c2_state.py",
        REPO / "src/mcrl/runtime/ee_axis_v06_c2_k1_q13.py",
        REPO / "src/mcrl/runtime/ee_axis_state.py",
        REPO / "src/mcrl/runtime/ee_axis_v04_c3_state.py",
        REPO / "src/mcrl/env/action_contract.py",
        REPO / "src/mcrl/env/keyed_fading.py",
        REPO / "src/mcrl/env/step.py",
    )
    return {str(path.relative_to(REPO)): _file_sha256(path) for path in paths}


def _scan_carrier_anchor(
    runtime: Any,
    *,
    source_seed: int,
    field: Any,
    eligible_steps: tuple[int, ...] = (1, 2),
) -> CarrierAnchorSelection:
    """Select the first mask-only anchor and retain every window scan step."""

    if (
        not isinstance(eligible_steps, tuple)
        or not eligible_steps
        or any(type(step) is not int or step < 0 for step in eligible_steps)
        or tuple(sorted(set(eligible_steps))) != eligible_steps
    ):
        raise V07D2RunnerError("eligible_steps must be a sorted nonempty step tuple")

    wrapped = runtime.make_environment(runtime.archive, users=int(runtime.users))
    runtime.bind_field(wrapped, field)
    env_rng, mobility_rng, *_ = runtime.evaluation_rngs(int(source_seed))
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    history: list[np.ndarray] = []
    eligible_users_by_step: list[tuple[int, tuple[int, ...]]] = []
    selected_step: int | None = None
    selected_focal: int | None = None
    selected_history: tuple[np.ndarray, ...] | None = None
    while int(observation.step_index) <= max(eligible_steps):
        actions = np.asarray(
            runtime.main_actions(
                runtime.trainer,
                wrapped,
                states,
                masks,
                observation,
                env_rng,
            ),
            dtype=np.int64,
        )
        if actions.shape != (int(runtime.users),):
            raise V07D2RunnerError("Main carrier returned a malformed action vector")
        history.append(actions.copy())
        step = int(observation.step_index)
        if step in eligible_steps:
            native = np.asarray(observation.masks)
            if native.ndim != 2 or native.shape[0] != int(runtime.users) or native.shape[1] != 28 or native.dtype != np.bool_:
                raise V07D2RunnerError("carrier returned a malformed native mask matrix")
            users = tuple(int(user) for user in np.flatnonzero(np.count_nonzero(native, axis=1) >= 3))
            eligible_users_by_step.append((step, users))
            if users and selected_step is None:
                selected_step = step
                selected_focal = users[0]
                selected_history = tuple(np.array(item, dtype=np.int64, copy=True) for item in history)
                # The selected anchor action is deliberately left unexecuted.
                # Later window steps are irrelevant once the first eligible
                # predecision has been found, so the selection receipt stops
                # at this step instead of contaminating the carrier history.
                break
        if step >= max(eligible_steps):
            break
        result = wrapped.step(actions, env_rng)
        if bool(result.done):
            break
        states = list(result.user_states)
        masks = list(result.action_masks)
        observation = wrapped.last_outcome.observation
    if selected_step is None or selected_focal is None or selected_history is None:
        if tuple(step for step, _ in eligible_users_by_step) != eligible_steps:
            raise V07D2RunnerError(
                "carrier ended before the complete eligible window was scanned"
            )
        window_label = "early" if eligible_steps == (1, 2) else "late" if eligible_steps == (5, 6) else "requested"
        raise V07D2RunnerError(f"development seed has no {window_label} native mask with >=3 actions")
    selected_index = eligible_steps.index(selected_step)
    if tuple(step for step, _ in eligible_users_by_step) != eligible_steps[: selected_index + 1]:
        raise V07D2RunnerError("carrier selection receipt did not stop at the anchor")
    return CarrierAnchorSelection(
        target_step=selected_step,
        focal_user=selected_focal,
        carrier_history=selected_history,
        eligible_users_by_step=tuple(eligible_users_by_step),
    )


def _calibrate(args: argparse.Namespace) -> dict[str, object]:
    if Path(args.output).resolve() != (REPO / SEALED_CALIBRATION_RELATIVE).resolve():
        raise V07D2RunnerError("development calibration has one fixed output path")
    if args.lineage != "q13-a":
        raise V07D2RunnerError("development calibration has one frozen q13-a lineage")
    if (REPO / SEALED_CALIBRATION_RELATIVE).exists():
        raise V07D2RunnerError("development calibration is already sealed; retry forbidden")
    if args.source_seed != CALIBRATION_SEED or args.source_seed in D2_SEEDS:
        raise V07D2RunnerError("calibration seed is not the frozen development seed")
    live_v06, runner_v06, live_v07, simulator_manifest_sha256 = _modules()

    started = time.monotonic()
    with live_v06.authenticated_runtime(
        tle_root=args.tle_root,
        prereg_path=args.prereg,
        main_dir=args.main_dir,
        gate_dir=args.gate_dir,
        source_dir=args.q13_source_dir,
        v03_root=args.v03_root,
    ) as runtime:
        field = runner_v06._physical_world_field(
            checkpoint_sha256=runtime.checkpoint_sha256,
            source_manifest_sha256=simulator_manifest_sha256,
            simulator_prereg_file_sha256=runtime.prereg_file_sha256,
            source_seed=args.source_seed,
        )
        target_step, focal_user, carrier = _scan_carrier_anchor(
            runtime,
            source_seed=args.source_seed,
            field=field,
        )
        hybrid = runtime.hybrids[args.lineage]
        bound, decision, _state = live_v07.bind_behavior_action_at_anchor(
            runtime,
            runtime.archive,
            hybrid,
            None,
            source_seed=args.source_seed,
            field=field,
            carrier_history=carrier,
            target_step=target_step,
            interval_s=INTERVAL_S,
            kappa_bits=KAPPA_BITS,
        )
        if np.count_nonzero(decision.masks[focal_user]) < 3:
            raise V07D2RunnerError("lineage behavior changed the native anchor mask")
        capture = live_v07.capture_one_decision(
            runtime,
            runtime.archive,
            hybrid,
            None,
            lineage=args.lineage,
            refresh_round="bootstrap",
            world_id=args.source_seed,
            source_seed=args.source_seed,
            target_step=target_step,
            focal_user=focal_user,
            history=bound,
            field=field,
            interval_s=INTERVAL_S,
            kappa_bits=KAPPA_BITS,
            lambda_bits_per_j=LAMBDA_BITS_PER_J,
        )
        capture.verify()
        elapsed = time.monotonic() - started
        payload: dict[str, object] = {
            "schema": CALIBRATION_SCHEMA,
            "claim_ceiling": "DEVELOPMENT_PLUMBING_AND_WALL_TIME_ONLY",
            "source_seed": args.source_seed,
            "lineage": args.lineage,
            "target_step": target_step,
            "focal_user": focal_user,
            "legal_action_count": capture.coverage.mask_count,
            "row_count": len(capture.rows),
            "elapsed_wall_seconds": elapsed,
            "estimated_d2_seconds_linear_60_cells": elapsed * 60.0,
            "capture_receipt": dict(capture.receipt),
            "dataset": __import__(
                "mcrl.runtime.ee_axis_v07_c2_dataset",
                fromlist=["V07C2Dataset"],
            ).V07C2Dataset.from_records(
                rows=capture.rows, coverage=(capture.coverage,)
            ).to_document(),
            "checkpoint_sha256": runtime.checkpoint_sha256,
            "simulator_source_manifest_sha256": simulator_manifest_sha256,
            "q13_gate_source_manifest_sha256": runtime.q13_gate_source_manifest_sha256,
            "crn_sha256": field.root_digest,
            "test_split_opened": False,
            "training": False,
            "d2_authorized": False,
        }
    body = dict(payload)
    payload["payload_sha256"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    _canonical_write_once(args.output, payload)
    return payload


def _prepare(args: argparse.Namespace) -> dict[str, object]:
    prereg_sha256 = _require_frozen_d2_prereg(args.d2_prereg)
    calibration = _read_sealed_calibration(args.calibration)
    attempt_marker_sha256 = _claim_formal_stage(
        stage="prepare",
        output=args.output,
        prereg_sha256=prereg_sha256,
    )
    live_v06, runner_v06, live_v07, simulator_manifest_sha256 = _modules()
    anchors: list[dict[str, object]] = []
    with live_v06.authenticated_runtime(
        tle_root=args.tle_root,
        prereg_path=args.prereg,
        main_dir=args.main_dir,
        gate_dir=args.gate_dir,
        source_dir=args.q13_source_dir,
        v03_root=args.v03_root,
    ) as runtime:
        for source_seed in D2_SEEDS:
            for window, eligible_steps in D2_WINDOWS.items():
                field = runner_v06._physical_world_field(
                    checkpoint_sha256=runtime.checkpoint_sha256,
                    source_manifest_sha256=simulator_manifest_sha256,
                    simulator_prereg_file_sha256=runtime.prereg_file_sha256,
                    source_seed=source_seed,
                )
                scan = _scan_carrier_anchor(
                    runtime,
                    source_seed=source_seed,
                    field=field,
                    eligible_steps=eligible_steps,
                )
                target_step = scan.target_step
                focal_user = scan.focal_user
                carrier = scan.carrier_history
                wrapped, _rng, observation = live_v07._replay_to_anchor(
                    runtime,
                    runtime.archive,
                    source_seed=source_seed,
                    field=field,
                    history=carrier,
                    target_step=target_step,
                )
                focal_mask = np.asarray(observation.masks[focal_user], dtype=np.bool_)
                all_user_masks = np.asarray(observation.masks, dtype=np.bool_)
                if (
                    all_user_masks.ndim != 2
                    or all_user_masks.shape[1] != 28
                    or focal_user >= all_user_masks.shape[0]
                    or not np.array_equal(all_user_masks[focal_user], focal_mask)
                ):
                    raise V07D2RunnerError("prepared full native mask matrix is malformed")
                if int(np.count_nonzero(focal_mask)) < 3:
                    raise V07D2RunnerError("prepared focal mask lost eligibility")
                environment = live_v07._environment(wrapped)
                state_encoding = live_v07.encode_ee_axis_v07_c2_state(
                    environment, observation
                )
                state_matrix = np.asarray(state_encoding.state_matrix, dtype=np.float32)
                if state_matrix.ndim != 2 or focal_user >= state_matrix.shape[0]:
                    raise V07D2RunnerError("prepared anchor state matrix is malformed")
                anchor_state = np.array(state_matrix[focal_user], dtype=np.float32, copy=True)
                if anchor_state.shape != (228,) or not np.all(np.isfinite(anchor_state)):
                    raise V07D2RunnerError("prepared focal anchor state is malformed")
                carrier_payload = [
                    [int(action) for action in actions.tolist()] for actions in carrier
                ]
                carrier_history_sha256 = hashlib.sha256(
                    canonical_json_bytes(carrier_payload)
                ).hexdigest()
                anchor_state_payload = [float(value).hex() for value in anchor_state.tolist()]
                anchor_state_sha256 = _array_sha256(
                    anchor_state, dtype=np.dtype(np.float32)
                )
                selection_receipt = _selection_receipt_payload(
                    window=window,
                    eligible_users_by_step=scan.eligible_users_by_step,
                )
                anchor_digest_payload = {
                    "source_seed": source_seed,
                    "window": window,
                    "target_step": target_step,
                    "focal_user": focal_user,
                    "focal_mask": [bool(value) for value in focal_mask.tolist()],
                    "all_user_masks": [
                        [bool(value) for value in row.tolist()]
                        for row in all_user_masks
                    ],
                    "all_user_masks_sha256": _array_sha256(
                        all_user_masks, dtype=np.dtype(np.bool_)
                    ),
                    "anchor_state": anchor_state_payload,
                    "anchor_state_sha256": anchor_state_sha256,
                    "carrier_history": carrier_payload,
                    "carrier_history_sha256": carrier_history_sha256,
                    "crn_sha256": field.root_digest,
                    "selection_receipt": selection_receipt,
                }
                anchors.append(
                    {
                        **anchor_digest_payload,
                        "anchor_digest_payload": anchor_digest_payload,
                        "anchor_sha256": hashlib.sha256(
                            canonical_json_bytes(anchor_digest_payload)
                        ).hexdigest(),
                    }
                )
        if len(anchors) != 20:
            raise V07D2RunnerError("D2 prepare must contain exactly 20 anchors")
        body: dict[str, object] = {
            "schema": PREPARE_SCHEMA,
            "claim_ceiling": "TARGET_FREE_D2_PREPARE_ONLY",
            "attempt_id": FORMAL_ATTEMPT_ID,
            "attempt_marker_sha256": attempt_marker_sha256,
            "d2_prereg_file_sha256": prereg_sha256,
            "calibration_file_sha256": SEALED_CALIBRATION_FILE_SHA256,
            "calibration_payload_sha256": calibration["payload_sha256"],
            "formula_constants": _formula_constants(),
            "q2_state_schema": V07_C2_Q2_STATE_SCHEMA,
            "q2_state_schema_sha256": V07_C2_Q2_STATE_SCHEMA_SHA256,
            "source_seeds": list(D2_SEEDS),
            "windows": {key: list(value) for key, value in D2_WINDOWS.items()},
            "anchors": anchors,
            "checkpoint_sha256": runtime.checkpoint_sha256,
            "simulator_prereg_file_sha256": runtime.prereg_file_sha256,
            "simulator_source_manifest_sha256": simulator_manifest_sha256,
            "q13_gate_source_manifest_sha256": runtime.q13_gate_source_manifest_sha256,
            "hybrid_sha256_by_lineage": dict(runtime.hybrid_hashes),
            "code_authority": _code_authority(),
            "counterfactual_outcomes_evaluated": False,
            "test_split_opened": False,
            "training": False,
        }
    payload = body | {"prepare_sha256": hashlib.sha256(canonical_json_bytes(body)).hexdigest()}
    _canonical_write_once(args.output, payload)
    return payload


def _read_prepare(path: Path, *, d2_prereg: Path) -> dict[str, Any]:
    prereg_sha256 = _require_frozen_d2_prereg(d2_prereg)
    payload = _canonical_read(path)
    body = dict(payload)
    supplied = body.pop("prepare_sha256", None)
    if payload.get("schema") != PREPARE_SCHEMA or supplied != hashlib.sha256(
        canonical_json_bytes(body)
    ).hexdigest():
        raise V07D2RunnerError("D2 prepare digest/schema drifted")
    if payload.get("d2_prereg_file_sha256") != prereg_sha256:
        raise V07D2RunnerError("D2 prepare is bound to another preregistration")
    required = {
        "schema",
        "claim_ceiling",
        "attempt_id",
        "attempt_marker_sha256",
        "d2_prereg_file_sha256",
        "calibration_file_sha256",
        "calibration_payload_sha256",
        "formula_constants",
        "q2_state_schema",
        "q2_state_schema_sha256",
        "source_seeds",
        "windows",
        "anchors",
        "checkpoint_sha256",
        "simulator_prereg_file_sha256",
        "simulator_source_manifest_sha256",
        "q13_gate_source_manifest_sha256",
        "hybrid_sha256_by_lineage",
        "code_authority",
        "counterfactual_outcomes_evaluated",
        "test_split_opened",
        "training",
        "prepare_sha256",
    }
    if set(payload) != required:
        raise V07D2RunnerError("D2 prepare schema drifted")
    if payload.get("claim_ceiling") != "TARGET_FREE_D2_PREPARE_ONLY":
        raise V07D2RunnerError("D2 prepare claim ceiling drifted")
    if payload.get("attempt_id") != FORMAL_ATTEMPT_ID:
        raise V07D2RunnerError("D2 prepare attempt identity drifted")
    _verify_formal_stage_marker(
        stage="prepare",
        marker_sha256=payload.get("attempt_marker_sha256"),
        prereg_sha256=prereg_sha256,
    )
    if (
        payload.get("calibration_file_sha256") != SEALED_CALIBRATION_FILE_SHA256
        or payload.get("calibration_payload_sha256")
        != SEALED_CALIBRATION_PAYLOAD_SHA256
    ):
        raise V07D2RunnerError("D2 prepare is not bound to the sealed calibration")
    if payload.get("formula_constants") != _formula_constants():
        raise V07D2RunnerError("D2 prepare formula constants drifted")
    if (
        payload.get("q2_state_schema") != V07_C2_Q2_STATE_SCHEMA
        or payload.get("q2_state_schema_sha256")
        != V07_C2_Q2_STATE_SCHEMA_SHA256
    ):
        raise V07D2RunnerError("D2 prepare Q2 state schema drifted")
    if payload.get("code_authority") != _code_authority():
        raise V07D2RunnerError("D2 prepare code authority drifted")
    for field in (
        "checkpoint_sha256",
        "simulator_prereg_file_sha256",
        "simulator_source_manifest_sha256",
        "q13_gate_source_manifest_sha256",
    ):
        _require_digest(payload[field], field=field)
    hybrid_hashes = payload.get("hybrid_sha256_by_lineage")
    if not isinstance(hybrid_hashes, dict) or set(hybrid_hashes) != set(LINEAGES):
        raise V07D2RunnerError("D2 prepare lineage checkpoint receipt drifted")
    for lineage in LINEAGES:
        _require_digest(hybrid_hashes[lineage], field=f"hybrid_sha256_by_lineage.{lineage}")
    anchors = payload.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != D2_EXPECTED_ANCHORS:
        raise V07D2RunnerError("D2 prepare does not contain 20 anchors")
    if payload.get("source_seeds") != list(D2_SEEDS):
        raise V07D2RunnerError("D2 prepare seed schedule drifted")
    if payload.get("windows") != {key: list(value) for key, value in D2_WINDOWS.items()}:
        raise V07D2RunnerError("D2 prepare window schedule drifted")
    if payload.get("counterfactual_outcomes_evaluated") is not False:
        raise V07D2RunnerError("D2 prepare evaluated a counterfactual outcome")
    if payload.get("test_split_opened") is not False or payload.get("training") is not False:
        raise V07D2RunnerError("D2 prepare crossed a forbidden evidence boundary")
    normalized = [_validate_prepare_anchor(raw) for raw in anchors]
    keys = {
        (raw["source_seed"], raw["target_step"], raw["focal_user"])
        for raw in normalized
    }
    if len(keys) != D2_EXPECTED_ANCHORS:
        raise V07D2RunnerError("D2 prepare contains duplicate physical anchors")
    if {raw["source_seed"] for raw in normalized} != set(D2_SEEDS):
        raise V07D2RunnerError("D2 prepare does not cover the frozen seed block")
    for seed in D2_SEEDS:
        seed_rows = [raw for raw in normalized if raw["source_seed"] == seed]
        if len(seed_rows) != 2 or {raw["window"] for raw in seed_rows} != {"early", "late"}:
            raise V07D2RunnerError("D2 prepare does not contain one early and one late anchor per seed")
    expected_order = tuple(
        sorted(
            normalized,
            key=lambda raw: (raw["source_seed"], 0 if raw["window"] == "early" else 1),
        )
    )
    if tuple(normalized) != expected_order:
        raise V07D2RunnerError("D2 prepare anchors are not deterministically ordered")
    payload["anchors"] = normalized
    return payload


def _strict_bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise V07D2RunnerError(f"{field} must be boolean")
    return value


def _targets_equal(left: FocalNextSurplus, right: FocalNextSurplus) -> bool:
    fields = (
        "z2_focal_next_surplus_bits",
        "focal_next_rate_delta_bits",
        "focal_next_marginal_energy_delta_j",
        "candidate_focal_rate_bps",
        "reference_focal_rate_bps",
        "candidate_focal_marginal_power_w",
        "reference_focal_marginal_power_w",
        "candidate_full_power_w",
        "candidate_without_focal_power_w",
        "reference_full_power_w",
        "reference_without_focal_power_w",
        "lambda_bits_per_j",
        "interval_s",
        "schema",
    )
    return all(getattr(left, field) == getattr(right, field) for field in fields)


def _measurement_receipt(value: object, *, field: str) -> dict[str, object]:
    """Validate one live successor measurement and recompute its array digests."""

    required = {
        "terminal_absorbing_zero",
        "focal_rate_bps",
        "full_power_w",
        "without_focal_power_w",
        "successor_actions",
        "successor_masks",
        "successor_actions_sha256",
        "successor_masks_sha256",
        "successor_policy_sha256",
        "focal_already_noop",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise V07D2RunnerError(f"{field} measurement schema drifted")
    terminal = _strict_bool(value["terminal_absorbing_zero"], field=f"{field}.terminal_absorbing_zero")
    focal_rate = _decode_hex_float(value["focal_rate_bps"], field=f"{field}.focal_rate_bps")
    full_power = _decode_hex_float(value["full_power_w"], field=f"{field}.full_power_w")
    without_power = _decode_hex_float(
        value["without_focal_power_w"], field=f"{field}.without_focal_power_w"
    )
    if any(value < 0.0 for value in (focal_rate, full_power, without_power)):
        raise V07D2RunnerError(f"{field} contains a negative physical quantity")
    actions = _decode_action_vector(value["successor_actions"], field=f"{field}.successor_actions")
    masks = _decode_bool_matrix(value["successor_masks"], field=f"{field}.successor_masks")
    if masks.shape != (actions.size, 28):
        raise V07D2RunnerError(f"{field} successor actions/masks have different shapes")
    for user, action in enumerate(actions.tolist()):
        if bool(np.any(masks[user])):
            if action == -1 or not bool(masks[user, int(action)]):
                raise V07D2RunnerError(f"{field} successor action is illegal under its native mask")
        elif action != -1:
            raise V07D2RunnerError(f"{field} empty successor mask lacks the no-op")
    action_digest = _require_digest(
        value["successor_actions_sha256"], field=f"{field}.successor_actions_sha256"
    )
    mask_digest = _require_digest(
        value["successor_masks_sha256"], field=f"{field}.successor_masks_sha256"
    )
    if _array_sha256(actions, dtype=np.dtype(np.int64)) != action_digest:
        raise V07D2RunnerError(f"{field} successor action digest drifted")
    if _array_sha256(masks, dtype=np.dtype(np.bool_)) != mask_digest:
        raise V07D2RunnerError(f"{field} successor mask digest drifted")
    policy_digest = _require_digest(
        value["successor_policy_sha256"], field=f"{field}.successor_policy_sha256"
    )
    focal_already_noop = _strict_bool(
        value["focal_already_noop"], field=f"{field}.focal_already_noop"
    )
    return {
        "terminal_absorbing_zero": terminal,
        "focal_rate_bps": focal_rate,
        "full_power_w": full_power,
        "without_focal_power_w": without_power,
        "successor_actions": actions,
        "successor_masks": masks,
        "successor_actions_sha256": action_digest,
        "successor_masks_sha256": mask_digest,
        "successor_policy_sha256": policy_digest,
        "focal_already_noop": focal_already_noop,
    }


def _validate_live_capture(
    *,
    cell: dict[str, object],
    prepared_anchor: dict[str, object],
    dataset: V07C2Dataset,
) -> dict[str, object]:
    """Validate the live capture receipt, raw branch arrays, and row hashes."""

    receipt_value = cell.get("capture_receipt")
    if not isinstance(receipt_value, dict):
        raise V07D2RunnerError("D2 cell capture receipt is malformed")
    receipt = dict(receipt_value)
    supplied = receipt.pop("receipt_sha256", None)
    if not _is_digest(supplied) or supplied != hashlib.sha256(canonical_json_bytes(receipt)).hexdigest():
        raise V07D2RunnerError("D2 capture receipt digest drifted")
    expected_receipt = {
        "schema",
        "lineage",
        "refresh_round",
        "world_id",
        "source_seed",
        "target_step",
        "focal_user",
        "formula_constants",
        "q2_state_schema",
        "q2_state_schema_sha256",
        "crn_sha256",
        "anchor_policy_sha256",
        "anchor_reference_actions",
        "anchor_state_sha256",
        "anchor_reference_actions_sha256",
        "native_legal_actions",
        "empty_mask",
        "q1_focal_surface_hex",
        "q3_focal_surface_hex",
        "q1_focal_surface_array_sha256",
        "q3_focal_surface_array_sha256",
        "q1_network_sha256",
        "q3_network_sha256",
        "frozen_network_receipt_complete",
        "frozen_network_bytes_unchanged",
        "selected_q3_rung",
        "branch_receipt_schema",
        "branch_rows",
        "dataset_sha256",
        "resident_legacy_q2_evaluated",
        "target_or_ee_selected",
        "branch_local_successor_decisions",
        "full_evaluation_noncommitting",
        "without_focal_evaluation_noncommitting",
        "focal_removal_only",
        "selection_outcome_blind",
        "retry_count",
        "replacement_used",
        "test_record_used",
    }
    if set(receipt) != expected_receipt:
        raise V07D2RunnerError("D2 capture receipt schema drifted")
    if receipt["schema"] != CAPTURE_RECEIPT_SCHEMA:
        raise V07D2RunnerError("D2 capture receipt has the wrong schema")
    if receipt["formula_constants"] != _capture_formula_constants():
        raise V07D2RunnerError("D2 capture formula constants drifted")
    if (
        receipt["q2_state_schema"] != V07_C2_Q2_STATE_SCHEMA
        or receipt["q2_state_schema_sha256"]
        != V07_C2_Q2_STATE_SCHEMA_SHA256
        or dataset.state_schema != V07_C2_Q2_STATE_SCHEMA
        or dataset.state_schema_sha256 != V07_C2_Q2_STATE_SCHEMA_SHA256
    ):
        raise V07D2RunnerError("D2 capture Q2 state schema drifted")
    for field, expected in (
        ("lineage", cell["lineage"]),
        ("world_id", cell["source_seed"]),
        ("source_seed", cell["source_seed"]),
        ("target_step", cell["target_step"]),
        ("focal_user", cell["focal_user"]),
        ("crn_sha256", prepared_anchor["crn_sha256"]),
        ("anchor_state_sha256", prepared_anchor["anchor_state_sha256"]),
    ):
        if receipt[field] != expected:
            raise V07D2RunnerError(f"D2 capture receipt {field} drifted")
    _require_digest(receipt["anchor_policy_sha256"], field="anchor_policy_sha256")
    if receipt["refresh_round"] != "bootstrap":
        raise V07D2RunnerError("D2 capture used a non-bootstrap refresh round")
    if receipt["empty_mask"] is not False or receipt["resident_legacy_q2_evaluated"] is not False or receipt["target_or_ee_selected"] is not False:
        raise V07D2RunnerError("D2 capture crossed an outcome or legacy-Q2 boundary")
    for field in (
        "branch_local_successor_decisions",
        "full_evaluation_noncommitting",
        "without_focal_evaluation_noncommitting",
        "focal_removal_only",
        "selection_outcome_blind",
    ):
        if receipt[field] is not True:
            raise V07D2RunnerError(f"D2 capture {field} receipt failed")
    if receipt["retry_count"] != 0 or receipt["replacement_used"] is not False or receipt["test_record_used"] is not False:
        raise V07D2RunnerError("D2 capture contains a retry, replacement, or TEST record")
    if (
        receipt["frozen_network_receipt_complete"] is not True
        or receipt["frozen_network_bytes_unchanged"] is not True
        or receipt["selected_q3_rung"] != 100
    ):
        raise V07D2RunnerError("D2 capture lacks the frozen Q1/Q3 network receipt")
    q1_network = _require_digest(receipt["q1_network_sha256"], field="q1_network_sha256")
    q3_network = _require_digest(receipt["q3_network_sha256"], field="q3_network_sha256")
    crn_digest = _require_digest(receipt["crn_sha256"], field="crn_sha256")
    reference_actions = _decode_action_vector(
        receipt["anchor_reference_actions"], field="anchor_reference_actions"
    )
    if _array_sha256(reference_actions, dtype=np.dtype(np.int64)) != receipt["anchor_reference_actions_sha256"]:
        raise V07D2RunnerError("D2 anchor reference action digest drifted")
    all_user_masks = _decode_bool_matrix(
        prepared_anchor["all_user_masks"], field="prepared all_user_masks"
    )
    if reference_actions.shape != (all_user_masks.shape[0],):
        raise V07D2RunnerError("D2 reference vector and full mask user counts differ")
    for user, action in enumerate(reference_actions.tolist()):
        if bool(np.any(all_user_masks[user])):
            if action < 0 or not bool(all_user_masks[user, action]):
                raise V07D2RunnerError(
                    "D2 reference opening contains a non-focal illegal action"
                )
        elif action != -1:
            raise V07D2RunnerError(
                "D2 reference opening must use no-op for an empty native mask"
            )
    mask = np.asarray(prepared_anchor["focal_mask"], dtype=np.bool_)
    coverage = dataset.coverage
    if len(coverage) != 1:
        raise V07D2RunnerError("D2 cell dataset must contain one native coverage record")
    coverage_item = coverage[0]
    if (
        coverage_item.lineage != cell["lineage"]
        or coverage_item.refresh_round != "bootstrap"
        or coverage_item.world_id != cell["source_seed"]
        or coverage_item.step_index != cell["target_step"]
        or coverage_item.focal_user != cell["focal_user"]
        or not np.array_equal(coverage_item.action_mask, mask)
        or coverage_item.mask_count < 3
    ):
        raise V07D2RunnerError("D2 dataset coverage drifted from the prepared native mask")
    if not dataset.rows:
        raise V07D2RunnerError("D2 cell cannot have an empty action dataset")
    if receipt["native_legal_actions"] != list(coverage_item.legal_actions):
        raise V07D2RunnerError("D2 capture legal-action receipt drifted")
    if receipt["dataset_sha256"] != dataset.corpus_sha256:
        raise V07D2RunnerError("D2 capture dataset digest drifted")
    q1 = _decode_hex_vector(receipt["q1_focal_surface_hex"], field="q1_focal_surface", length=28)
    q3 = _decode_hex_vector(receipt["q3_focal_surface_hex"], field="q3_focal_surface", length=28)
    if _array_sha256(q1, dtype=np.dtype(np.float64)) != receipt["q1_focal_surface_array_sha256"]:
        raise V07D2RunnerError("D2 Q1 focal surface digest drifted")
    if _array_sha256(q3, dtype=np.dtype(np.float64)) != receipt["q3_focal_surface_array_sha256"]:
        raise V07D2RunnerError("D2 Q3 focal surface digest drifted")
    branch_rows_value = receipt["branch_rows"]
    if not isinstance(branch_rows_value, list) or len(branch_rows_value) != len(dataset.rows):
        raise V07D2RunnerError("D2 capture branch-row count drifted")
    branches: dict[int, dict[str, object]] = {}
    row_by_action = {row.candidate_action: row for row in dataset.rows}
    invariant_reference_receipt: object | None = None
    for branch_index, raw_branch in enumerate(branch_rows_value):
        if not isinstance(raw_branch, dict):
            raise V07D2RunnerError("D2 branch receipt is malformed")
        required_branch = {
            "schema",
            "candidate_action",
            "opening_actions",
            "opening_actions_sha256",
            "opening_focal_difference_count",
            "candidate",
            "reference",
            "target_row_sha256",
        }
        if set(raw_branch) != required_branch or raw_branch["schema"] != BRANCH_RECEIPT_SCHEMA:
            raise V07D2RunnerError("D2 branch receipt schema drifted")
        candidate_action = raw_branch["candidate_action"]
        if type(candidate_action) is not int or candidate_action not in row_by_action or candidate_action in branches:
            raise V07D2RunnerError("D2 branch candidate action is duplicated or unexpected")
        opening = _decode_action_vector(
            raw_branch["opening_actions"], field=f"branch[{branch_index}].opening_actions"
        )
        opening_digest = _require_digest(
            raw_branch["opening_actions_sha256"], field="opening_actions_sha256"
        )
        if _array_sha256(opening, dtype=np.dtype(np.int64)) != opening_digest:
            raise V07D2RunnerError("D2 opening action digest drifted")
        if opening.shape != reference_actions.shape:
            raise V07D2RunnerError("D2 opening vectors have different user counts")
        row = row_by_action[candidate_action]
        if opening[cell["focal_user"]] != row.candidate_action or reference_actions[cell["focal_user"]] != row.reference_action:
            raise V07D2RunnerError("D2 opening vector does not match its dataset row")
        changed = np.flatnonzero(opening != reference_actions)
        expected_changed = () if candidate_action == row.reference_action else (int(cell["focal_user"]),)
        if tuple(int(value) for value in changed) != expected_changed:
            raise V07D2RunnerError("D2 opening vector changes a non-focal user")
        expected_difference_count = 0 if candidate_action == row.reference_action else 1
        if raw_branch["opening_focal_difference_count"] != expected_difference_count:
            raise V07D2RunnerError("D2 opening focal-difference receipt drifted")
        raw_reference_receipt = raw_branch["reference"]
        if invariant_reference_receipt is None:
            invariant_reference_receipt = raw_reference_receipt
        elif raw_reference_receipt != invariant_reference_receipt:
            raise V07D2RunnerError(
                "D2 reference successor receipt drifted across candidate rows"
            )
        candidate_measurement = _measurement_receipt(
            raw_branch["candidate"], field=f"branch[{branch_index}].candidate"
        )
        reference_measurement = _measurement_receipt(
            raw_branch["reference"], field=f"branch[{branch_index}].reference"
        )
        if candidate_measurement["terminal_absorbing_zero"] is not False or reference_measurement["terminal_absorbing_zero"] is not False:
            raise V07D2RunnerError("D2 successor is terminal/absorbing")
        if candidate_action == row.reference_action:
            for field in (
                "terminal_absorbing_zero",
                "focal_rate_bps",
                "full_power_w",
                "without_focal_power_w",
                "successor_actions_sha256",
                "successor_masks_sha256",
                "successor_policy_sha256",
                "focal_already_noop",
            ):
                if candidate_measurement[field] != reference_measurement[field]:
                    raise V07D2RunnerError("D2 equal-action branch receipts differ")
            if not np.array_equal(
                candidate_measurement["successor_actions"],
                reference_measurement["successor_actions"],
            ) or not np.array_equal(
                candidate_measurement["successor_masks"],
                reference_measurement["successor_masks"],
            ):
                raise V07D2RunnerError("D2 equal-action branch receipts differ")
        expected_target = focal_next_surplus_target(
            lambda_bits_per_j=row.target.lambda_bits_per_j,
            interval_s=row.target.interval_s,
            candidate_focal_rate_bps=candidate_measurement["focal_rate_bps"],
            reference_focal_rate_bps=reference_measurement["focal_rate_bps"],
            candidate_full_power_w=candidate_measurement["full_power_w"],
            candidate_without_focal_power_w=candidate_measurement["without_focal_power_w"],
            reference_full_power_w=reference_measurement["full_power_w"],
            reference_without_focal_power_w=reference_measurement["without_focal_power_w"],
        )
        if not _targets_equal(row.target, expected_target):
            raise V07D2RunnerError("D2 branch raw terms do not reconstruct the dataset target")
        if raw_branch["target_row_sha256"] != row.row_sha256:
            raise V07D2RunnerError("D2 branch target-row hash drifted")
        branches[candidate_action] = {
            "candidate_action": candidate_action,
            "opening_reference_actions": reference_actions,
            "opening_candidate_actions": opening,
            "candidate": candidate_measurement,
            "reference": reference_measurement,
            "target": row.target,
        }
    if tuple(branches) != coverage_item.legal_actions:
        raise V07D2RunnerError("D2 branch rows do not cover the native legal mask exactly once")
    reference_actions_by_row = {row.reference_action for row in dataset.rows}
    if len(reference_actions_by_row) != 1:
        raise V07D2RunnerError("D2 reference action drifted within a lineage cell")
    return {
        "receipt": receipt,
        "q1": q1,
        "q3": q3,
        "q1_network_sha256": q1_network,
        "q3_network_sha256": q3_network,
        "policy_sha256": _require_digest(receipt["anchor_policy_sha256"], field="anchor_policy_sha256"),
        "crn_sha256": crn_digest,
        "reference_actions": reference_actions,
        "branches": branches,
    }


def _decode_d2_cell(
    *,
    cell: object,
    prepared_anchor: dict[str, object],
    lineage: str,
) -> D2LineageDecisionCapture:
    if not isinstance(cell, dict):
        raise V07D2RunnerError("D2 shard cell is malformed")
    required = {
        "schema",
        "source_seed",
        "window",
        "target_step",
        "focal_user",
        "lineage",
        "anchor_sha256",
        "anchor_state_sha256",
        "carrier_history_sha256",
        "crn_sha256",
        "focal_mask",
        "all_user_masks_sha256",
        "anchor_policy_sha256",
        "anchor_reference_actions",
        "anchor_reference_actions_sha256",
        "q1_focal_surface_hex",
        "q3_focal_surface_hex",
        "q1_focal_surface_array_sha256",
        "q3_focal_surface_array_sha256",
        "q1_network_sha256",
        "q3_network_sha256",
        "frozen_network_receipt_complete",
        "frozen_network_bytes_unchanged",
        "selected_q3_rung",
        "branch_rows",
        "capture_receipt",
        "dataset",
    }
    if set(cell) != required:
        raise V07D2RunnerError("D2 shard cell schema drifted")
    for field, expected in (
        ("source_seed", prepared_anchor["source_seed"]),
        ("window", prepared_anchor["window"]),
        ("target_step", prepared_anchor["target_step"]),
        ("focal_user", prepared_anchor["focal_user"]),
        ("anchor_sha256", prepared_anchor["anchor_sha256"]),
        ("anchor_state_sha256", prepared_anchor["anchor_state_sha256"]),
        ("carrier_history_sha256", prepared_anchor["carrier_history_sha256"]),
        ("crn_sha256", prepared_anchor["crn_sha256"]),
        ("focal_mask", prepared_anchor["focal_mask"]),
        ("all_user_masks_sha256", prepared_anchor["all_user_masks_sha256"]),
    ):
        if cell[field] != expected:
            raise V07D2RunnerError(f"D2 shard cell {field} drifted from prepare")
    if cell["schema"] != "multi-catfish-mcrl-v07-c2-d2-lineage-cell-v1" or cell["lineage"] != lineage:
        raise V07D2RunnerError("D2 shard cell lineage/schema drifted")
    dataset_raw = cell["dataset"]
    if not isinstance(dataset_raw, Mapping):
        raise V07D2RunnerError("D2 shard dataset is malformed")
    try:
        dataset = V07C2Dataset.from_document(dataset_raw)
    except Exception as error:
        raise V07D2RunnerError("D2 shard dataset failed canonical verification") from error
    live = _validate_live_capture(cell=cell, prepared_anchor=prepared_anchor, dataset=dataset)
    for field in (
        "anchor_policy_sha256",
        "anchor_reference_actions",
        "anchor_reference_actions_sha256",
        "q1_focal_surface_hex",
        "q3_focal_surface_hex",
        "q1_focal_surface_array_sha256",
        "q3_focal_surface_array_sha256",
        "q1_network_sha256",
        "q3_network_sha256",
        "frozen_network_receipt_complete",
        "frozen_network_bytes_unchanged",
        "selected_q3_rung",
        "branch_rows",
    ):
        if cell[field] != live["receipt"].get(field):
            raise V07D2RunnerError(f"D2 shard cell {field} disagrees with live receipt")
    for row in dataset.rows:
        if _array_sha256(row.state, dtype=np.dtype(np.float32)) != prepared_anchor["anchor_state_sha256"]:
            raise V07D2RunnerError("D2 dataset state digest drifted from prepare")
        if row.target.lambda_bits_per_j != LAMBDA_BITS_PER_J or row.target.interval_s != INTERVAL_S:
            raise V07D2RunnerError("D2 target formula constants drifted")
    selection_raw = prepared_anchor["selection_receipt"]
    if not isinstance(selection_raw, dict):
        raise V07D2RunnerError("D2 prepared selection receipt is malformed")
    entries = tuple(
        (int(step), tuple(int(user) for user in users))
        for step, users in selection_raw["eligible_users_by_step"]
    )
    selection = D2SelectionReceipt(
        schema=selection_raw["schema"],
        window=selection_raw["window"],
        eligible_users_by_step=entries,
        selection_rule=selection_raw["selection_rule"],
        outcome_blind=selection_raw["outcome_blind"],
    )
    anchor = D2PhysicalAnchor(
        seed=prepared_anchor["source_seed"],
        step_index=prepared_anchor["target_step"],
        focal_user=prepared_anchor["focal_user"],
        window=prepared_anchor["window"],
        native_action_mask=np.asarray(prepared_anchor["focal_mask"], dtype=np.bool_),
        selection=selection,
        anchor_sha256=prepared_anchor["anchor_sha256"],
        state_sha256=prepared_anchor["anchor_state_sha256"],
        carrier_sha256=prepared_anchor["carrier_history_sha256"],
    )
    q13 = D2Q13SurfaceReceipt(
        q1_surface=live["q1"],
        q3_surface=live["q3"],
        q1_checkpoint_sha256=live["q1_network_sha256"],
        q3_checkpoint_sha256=live["q3_network_sha256"],
        policy_sha256=live["policy_sha256"],
        selected_q3_rung=live["receipt"]["selected_q3_rung"],
        bootstrap_q2_zero=True,
        resident_legacy_q2_evaluated=False,
    )
    rows: list[D2ActionRecord] = []
    flags = live["receipt"]
    for row in dataset.rows:
        branch = live["branches"][row.candidate_action]
        candidate_measurement = branch["candidate"]
        reference_measurement = branch["reference"]
        mechanics = D2MechanicsReceipt(
            opening_reference_actions=branch["opening_reference_actions"],
            opening_candidate_actions=branch["opening_candidate_actions"],
            successor_reference_action_sha256=reference_measurement["successor_actions_sha256"],
            successor_candidate_action_sha256=candidate_measurement["successor_actions_sha256"],
            crn_sha256=live["crn_sha256"],
            policy_sha256=live["policy_sha256"],
            reference_branch_local=flags["branch_local_successor_decisions"],
            candidate_branch_local=flags["branch_local_successor_decisions"],
            full_evaluation_noncommitting=flags["full_evaluation_noncommitting"],
            without_focal_evaluation_noncommitting=flags["without_focal_evaluation_noncommitting"],
            focal_removal_only=flags["focal_removal_only"],
            selection_outcome_blind=flags["selection_outcome_blind"],
            retry_count=flags["retry_count"],
            replacement_used=flags["replacement_used"],
            test_record_used=flags["test_record_used"],
            successor_present=True,
            terminal_absorbing_zero=False,
        )
        rows.append(
            D2ActionRecord(
                candidate_action=row.candidate_action,
                reference_action=row.reference_action,
                target=row.target,
                mechanics=mechanics,
            )
        )
    capture = D2LineageDecisionCapture(
        anchor=anchor,
        lineage=lineage,
        q13=q13,
        rows=tuple(rows),
    )
    try:
        capture.verify()
    except Exception as error:
        raise V07D2RunnerError("decoded D2 capture failed typed adjudicator validation") from error
    return capture


def _decode_d2_shards(
    *,
    prepare: dict[str, object],
    shards: Sequence[dict[str, object]],
) -> tuple[D2LineageDecisionCapture, ...]:
    """Strictly merge one prepare payload and exactly one shard per lineage."""

    if len(shards) != 3:
        raise V07D2RunnerError("D2 adjudication requires exactly three lineage shards")
    prepare_body = dict(prepare)
    prepare_sha256 = prepare_body.pop("prepare_sha256", None)
    if (
        not _is_digest(prepare_sha256)
        or hashlib.sha256(canonical_json_bytes(prepare_body)).hexdigest() != prepare_sha256
    ):
        raise V07D2RunnerError("D2 prepare digest is malformed")
    if prepare.get("schema") != PREPARE_SCHEMA or prepare.get("claim_ceiling") != "TARGET_FREE_D2_PREPARE_ONLY":
        raise V07D2RunnerError("D2 prepare claim/schema drifted")
    if prepare.get("attempt_id") != FORMAL_ATTEMPT_ID:
        raise V07D2RunnerError("D2 prepare attempt identity drifted")
    _require_digest(
        prepare.get("attempt_marker_sha256"),
        field="prepare.attempt_marker_sha256",
    )
    _require_digest(
        prepare.get("d2_prereg_file_sha256"),
        field="prepare.d2_prereg_file_sha256",
    )
    if prepare.get("formula_constants") != _formula_constants():
        raise V07D2RunnerError("D2 prepare formula constants drifted")
    if (
        prepare.get("q2_state_schema") != V07_C2_Q2_STATE_SCHEMA
        or prepare.get("q2_state_schema_sha256")
        != V07_C2_Q2_STATE_SCHEMA_SHA256
    ):
        raise V07D2RunnerError("D2 prepare Q2 state schema drifted")
    if (
        prepare.get("calibration_file_sha256") != SEALED_CALIBRATION_FILE_SHA256
        or prepare.get("calibration_payload_sha256")
        != SEALED_CALIBRATION_PAYLOAD_SHA256
    ):
        raise V07D2RunnerError("D2 prepare calibration receipt drifted")
    if prepare.get("source_seeds") != list(D2_SEEDS) or prepare.get("windows") != {
        key: list(value) for key, value in D2_WINDOWS.items()
    }:
        raise V07D2RunnerError("D2 prepare schedule drifted")
    if (
        prepare.get("counterfactual_outcomes_evaluated") is not False
        or prepare.get("test_split_opened") is not False
        or prepare.get("training") is not False
    ):
        raise V07D2RunnerError("D2 prepare crossed a forbidden evidence boundary")
    if not isinstance(prepare.get("checkpoint_sha256"), str):
        raise V07D2RunnerError("D2 prepare checkpoint receipt is malformed")
    _require_digest(prepare["checkpoint_sha256"], field="prepare.checkpoint_sha256")
    hybrid_hashes = prepare.get("hybrid_sha256_by_lineage")
    if not isinstance(hybrid_hashes, dict) or set(hybrid_hashes) != set(LINEAGES):
        raise V07D2RunnerError("D2 prepare lineage checkpoint receipt is malformed")
    for lineage in LINEAGES:
        _require_digest(hybrid_hashes[lineage], field=f"prepare.hybrid_sha256_by_lineage.{lineage}")
    raw_anchors = prepare.get("anchors")
    if not isinstance(raw_anchors, list) or len(raw_anchors) != D2_EXPECTED_ANCHORS:
        raise V07D2RunnerError("D2 prepare does not contain exactly 20 anchors")
    normalized_anchors = [_validate_prepare_anchor(raw) for raw in raw_anchors]
    if tuple(normalized_anchors) != tuple(raw_anchors):
        raise V07D2RunnerError("D2 prepare anchor payload is not canonical")
    prepared_by_key = {
        (raw["source_seed"], raw["target_step"], raw["focal_user"]): raw
        for raw in normalized_anchors
    }
    if len(prepared_by_key) != D2_EXPECTED_ANCHORS:
        raise V07D2RunnerError("D2 prepare contains duplicate physical anchors")
    seen_lineages: set[str] = set()
    captures: list[D2LineageDecisionCapture] = []
    for shard in shards:
        if not isinstance(shard, dict):
            raise V07D2RunnerError("D2 shard is malformed")
        body = dict(shard)
        supplied = body.pop("shard_sha256", None)
        if not _is_digest(supplied) or supplied != hashlib.sha256(canonical_json_bytes(body)).hexdigest():
            raise V07D2RunnerError("D2 shard digest drifted")
        required = {
            "schema",
            "claim_ceiling",
            "attempt_id",
            "attempt_marker_sha256",
            "lineage",
                "prepare_sha256",
                "formula_constants",
                "q2_state_schema",
                "q2_state_schema_sha256",
                "cells",
            "checkpoint_sha256",
            "lineage_hybrid_sha256",
            "test_split_opened",
            "training",
        }
        if set(body) != required or body["schema"] != SHARD_SCHEMA:
            raise V07D2RunnerError("D2 shard schema drifted")
        if body["claim_ceiling"] != "D2_FORMULA_SOURCE_ONLY_NO_LEARNING_NO_EE_EFFICACY":
            raise V07D2RunnerError("D2 shard claim ceiling drifted")
        if body["attempt_id"] != FORMAL_ATTEMPT_ID:
            raise V07D2RunnerError("D2 shard attempt identity drifted")
        _require_digest(body["attempt_marker_sha256"], field="shard.attempt_marker_sha256")
        if body["formula_constants"] != _formula_constants():
            raise V07D2RunnerError("D2 shard formula constants drifted")
        if (
            body["q2_state_schema"] != V07_C2_Q2_STATE_SCHEMA
            or body["q2_state_schema_sha256"]
            != V07_C2_Q2_STATE_SCHEMA_SHA256
        ):
            raise V07D2RunnerError("D2 shard Q2 state schema drifted")
        lineage = body["lineage"]
        if lineage not in LINEAGES or lineage in seen_lineages:
            raise V07D2RunnerError("D2 shards have a missing or duplicate lineage")
        seen_lineages.add(lineage)
        if body["prepare_sha256"] != prepare_sha256:
            raise V07D2RunnerError("D2 shard is bound to another prepare payload")
        if body["checkpoint_sha256"] != prepare["checkpoint_sha256"]:
            raise V07D2RunnerError("D2 shard Main checkpoint drifted")
        if body["lineage_hybrid_sha256"] != prepare["hybrid_sha256_by_lineage"].get(lineage):
            raise V07D2RunnerError("D2 shard lineage checkpoint drifted")
        _require_digest(body["checkpoint_sha256"], field="shard.checkpoint_sha256")
        _require_digest(body["lineage_hybrid_sha256"], field="shard.lineage_hybrid_sha256")
        if body["test_split_opened"] is not False or body["training"] is not False:
            raise V07D2RunnerError("D2 shard crossed a forbidden evidence boundary")
        cells = body["cells"]
        if not isinstance(cells, list) or len(cells) != D2_EXPECTED_ANCHORS:
            raise V07D2RunnerError("D2 shard must contain exactly 20 cells")
        shard_keys: set[tuple[int, int, int]] = set()
        shard_order: list[tuple[int, int, int]] = []
        for cell in cells:
            if not isinstance(cell, dict):
                raise V07D2RunnerError("D2 shard cell is malformed")
            key = (cell.get("source_seed"), cell.get("target_step"), cell.get("focal_user"))
            if key in shard_keys or key not in prepared_by_key:
                raise V07D2RunnerError("D2 shard has a duplicate or unknown physical anchor")
            shard_keys.add(key)
            shard_order.append(key)
            captures.append(
                _decode_d2_cell(
                    cell=cell,
                    prepared_anchor=prepared_by_key[key],
                    lineage=lineage,
                )
            )
        if shard_keys != set(prepared_by_key):
            raise V07D2RunnerError("D2 shard does not cover exactly the prepared anchors")
        if tuple(shard_order) != tuple(prepared_by_key):
            raise V07D2RunnerError("D2 shard cells are not deterministically ordered")
    if seen_lineages != set(LINEAGES) or len(captures) != 60:
        raise V07D2RunnerError("D2 merge does not contain exactly 60 lineage cells")
    return tuple(sorted(captures, key=lambda item: (item.anchor.seed, item.anchor.step_index, item.anchor.focal_user, LINEAGES.index(item.lineage))))


def _read_shard(path: Path) -> dict[str, Any]:
    return _canonical_read(path)


def _adjudication_document(
    *,
    prepare: dict[str, object],
    shards: Sequence[dict[str, object]],
    attempt_marker_sha256: str,
) -> dict[str, object]:
    """Build a write-once canonical D2 result, including invalid merges."""

    shard_digests: dict[str, str] = {}
    try:
        captures = _decode_d2_shards(prepare=prepare, shards=shards)
        result = adjudicate_d2(captures)
        shard_digests = {
            str(shard["lineage"]): str(shard["shard_sha256"])
            for shard in shards
        }
    except Exception:
        result = D2AdjudicationResult(
            verdict=D2_INVALID_NO_INFERENCE,
            metrics=D2Metrics(),
            reasons=("D2 shard merge validation failed",),
        )
    body: dict[str, object] = {
        "schema": ADJUDICATION_SCHEMA,
        "claim_ceiling": "D2_FORMULA_SOURCE_ONLY_NO_LEARNING_NO_EE_EFFICACY",
        "attempt_id": FORMAL_ATTEMPT_ID,
        "attempt_marker_sha256": _require_digest(
            attempt_marker_sha256,
            field="adjudication.attempt_marker_sha256",
        ),
        "prepare_sha256": prepare.get("prepare_sha256"),
        "formula_constants": _formula_constants(),
        "q2_state_schema": V07_C2_Q2_STATE_SCHEMA,
        "q2_state_schema_sha256": V07_C2_Q2_STATE_SCHEMA_SHA256,
        "shard_sha256_by_lineage": {
            lineage: shard_digests[lineage]
            for lineage in LINEAGES
            if lineage in shard_digests
        },
        "result": result.to_document(),
        "test_split_opened": False,
        "training": False,
        # A D2 PASS authorizes D3 implementation only; this runner never
        # authorizes an episode or TEST launch.
        "d2_authorized": False,
    }
    return body | {"adjudication_sha256": hashlib.sha256(canonical_json_bytes(body)).hexdigest()}


def _adjudicate(args: argparse.Namespace) -> dict[str, object]:
    if len(args.shard) != 3:
        raise V07D2RunnerError("adjudicate requires exactly three --shard paths")
    prepare = _read_prepare(args.prepare, d2_prereg=args.d2_prereg)
    expected_paths = {
        lineage: _formal_output_path("shard", lineage=lineage).resolve()
        for lineage in LINEAGES
    }
    supplied_paths = tuple(Path(path).resolve() for path in args.shard)
    if len(set(supplied_paths)) != len(LINEAGES) or set(supplied_paths) != set(
        expected_paths.values()
    ):
        raise V07D2RunnerError(
            "adjudicate must consume exactly the three fixed formal shard paths"
        )
    if any(path.is_symlink() or not path.is_file() for path in supplied_paths):
        raise V07D2RunnerError("a fixed formal D2 shard is missing or not regular")
    attempt_marker_sha256 = _claim_formal_stage(
        stage="adjudicate",
        output=args.output,
        prereg_sha256=prepare["d2_prereg_file_sha256"],
    )
    shard_payloads: list[dict[str, Any]] = []
    for lineage in LINEAGES:
        shard = _read_shard(expected_paths[lineage])
        if shard.get("lineage") != lineage:
            raise V07D2RunnerError("formal D2 shard path/lineage identity drifted")
        _verify_formal_stage_marker(
            stage="shard",
            lineage=lineage,
            marker_sha256=shard.get("attempt_marker_sha256"),
            prereg_sha256=prepare["d2_prereg_file_sha256"],
        )
        shard_payloads.append(shard)
    shards = tuple(shard_payloads)
    payload = _adjudication_document(
        prepare=prepare,
        shards=shards,
        attempt_marker_sha256=attempt_marker_sha256,
    )
    _canonical_write_once(args.output, payload)
    return payload


def _shard(args: argparse.Namespace) -> dict[str, object]:
    prepared = _read_prepare(args.prepare, d2_prereg=args.d2_prereg)
    attempt_marker_sha256 = _claim_formal_stage(
        stage="shard",
        lineage=args.lineage,
        output=args.output,
        prereg_sha256=prepared["d2_prereg_file_sha256"],
    )
    live_v06, runner_v06, live_v07, simulator_manifest_sha256 = _modules()
    cells: list[dict[str, object]] = []
    with live_v06.authenticated_runtime(
        tle_root=args.tle_root,
        prereg_path=args.prereg,
        main_dir=args.main_dir,
        gate_dir=args.gate_dir,
        source_dir=args.q13_source_dir,
        v03_root=args.v03_root,
    ) as runtime:
        if (
            prepared.get("checkpoint_sha256") != runtime.checkpoint_sha256
            or prepared.get("simulator_source_manifest_sha256")
            != simulator_manifest_sha256
            or prepared.get("q13_gate_source_manifest_sha256")
            != runtime.q13_gate_source_manifest_sha256
            or prepared.get("hybrid_sha256_by_lineage") != runtime.hybrid_hashes
        ):
            raise V07D2RunnerError("D2 runtime authority differs from prepare")
        hybrid = runtime.hybrids[args.lineage]
        for raw in prepared["anchors"]:
            if not isinstance(raw, dict):
                raise V07D2RunnerError("D2 prepare anchor is malformed")
            source_seed = int(raw["source_seed"])
            target_step = int(raw["target_step"])
            focal_user = int(raw["focal_user"])
            carrier = tuple(
                np.asarray(actions, dtype=np.int64)
                for actions in raw["carrier_history"]
            )
            if hashlib.sha256(
                canonical_json_bytes(raw["carrier_history"])
            ).hexdigest() != raw["carrier_history_sha256"]:
                raise V07D2RunnerError("D2 carrier history digest drifted")
            field = runner_v06._physical_world_field(
                checkpoint_sha256=runtime.checkpoint_sha256,
                source_manifest_sha256=simulator_manifest_sha256,
                simulator_prereg_file_sha256=runtime.prereg_file_sha256,
                source_seed=source_seed,
            )
            if field.root_digest != raw["crn_sha256"]:
                raise V07D2RunnerError("D2 keyed field differs from prepare")
            bound, decision, _state = live_v07.bind_behavior_action_at_anchor(
                runtime,
                runtime.archive,
                hybrid,
                None,
                source_seed=source_seed,
                field=field,
                carrier_history=carrier,
                target_step=target_step,
                interval_s=INTERVAL_S,
                kappa_bits=KAPPA_BITS,
            )
            if decision.masks[focal_user].tolist() != raw["focal_mask"]:
                raise V07D2RunnerError("D2 native focal mask drifted from prepare")
            if not np.array_equal(
                np.asarray(decision.masks, dtype=np.bool_),
                np.asarray(raw["all_user_masks"], dtype=np.bool_),
            ):
                raise V07D2RunnerError("D2 full native mask matrix drifted from prepare")
            capture = live_v07.capture_one_decision(
                runtime,
                runtime.archive,
                hybrid,
                None,
                lineage=args.lineage,
                refresh_round="bootstrap",
                world_id=source_seed,
                source_seed=source_seed,
                target_step=target_step,
                focal_user=focal_user,
                history=bound,
                field=field,
                interval_s=INTERVAL_S,
                kappa_bits=KAPPA_BITS,
                lambda_bits_per_j=LAMBDA_BITS_PER_J,
            )
            capture.verify()
            dataset_module = __import__(
                "mcrl.runtime.ee_axis_v07_c2_dataset",
                fromlist=["V07C2Dataset"],
            )
            dataset = dataset_module.V07C2Dataset.from_records(
                rows=capture.rows, coverage=(capture.coverage,)
            )
            receipt = dict(capture.receipt)
            cell = {
                "schema": "multi-catfish-mcrl-v07-c2-d2-lineage-cell-v1",
                "source_seed": source_seed,
                "window": raw["window"],
                "target_step": target_step,
                "focal_user": focal_user,
                "lineage": args.lineage,
                "anchor_sha256": raw["anchor_sha256"],
                "anchor_state_sha256": raw["anchor_state_sha256"],
                "carrier_history_sha256": raw["carrier_history_sha256"],
                "crn_sha256": raw["crn_sha256"],
                "focal_mask": list(raw["focal_mask"]),
                "all_user_masks_sha256": raw["all_user_masks_sha256"],
                "anchor_policy_sha256": receipt["anchor_policy_sha256"],
                "anchor_reference_actions": list(receipt["anchor_reference_actions"]),
                "anchor_reference_actions_sha256": receipt["anchor_reference_actions_sha256"],
                "q1_focal_surface_hex": list(receipt["q1_focal_surface_hex"]),
                "q3_focal_surface_hex": list(receipt["q3_focal_surface_hex"]),
                "q1_focal_surface_array_sha256": receipt["q1_focal_surface_array_sha256"],
                "q3_focal_surface_array_sha256": receipt["q3_focal_surface_array_sha256"],
                "q1_network_sha256": receipt["q1_network_sha256"],
                "q3_network_sha256": receipt["q3_network_sha256"],
                "frozen_network_receipt_complete": receipt["frozen_network_receipt_complete"],
                "frozen_network_bytes_unchanged": receipt["frozen_network_bytes_unchanged"],
                "selected_q3_rung": receipt["selected_q3_rung"],
                "branch_rows": list(receipt["branch_rows"]),
                "capture_receipt": receipt,
                "dataset": dataset.to_document(),
            }
            _validate_live_capture(
                cell=cell,
                prepared_anchor=raw,
                dataset=dataset,
            )
            cells.append(cell)
        if len(cells) != 20:
            raise V07D2RunnerError("D2 shard must contain exactly 20 cells")
        body = {
            "schema": SHARD_SCHEMA,
            "claim_ceiling": "D2_FORMULA_SOURCE_ONLY_NO_LEARNING_NO_EE_EFFICACY",
            "attempt_id": FORMAL_ATTEMPT_ID,
            "attempt_marker_sha256": attempt_marker_sha256,
            "lineage": args.lineage,
            "prepare_sha256": prepared["prepare_sha256"],
            "formula_constants": _formula_constants(),
            "q2_state_schema": V07_C2_Q2_STATE_SCHEMA,
            "q2_state_schema_sha256": V07_C2_Q2_STATE_SCHEMA_SHA256,
            "cells": cells,
            "checkpoint_sha256": runtime.checkpoint_sha256,
            "lineage_hybrid_sha256": runtime.hybrid_hashes[args.lineage],
            "test_split_opened": False,
            "training": False,
        }
    payload = body | {"shard_sha256": hashlib.sha256(canonical_json_bytes(body)).hexdigest()}
    _canonical_write_once(args.output, payload)
    return payload


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    calibrate = sub.add_parser("calibrate")
    calibrate.add_argument("--tle-root", type=Path, required=True)
    calibrate.add_argument("--prereg", type=Path, required=True)
    calibrate.add_argument("--main-dir", type=Path, required=True)
    calibrate.add_argument("--gate-dir", type=Path, required=True)
    calibrate.add_argument("--q13-source-dir", type=Path, required=True)
    calibrate.add_argument("--v03-root", type=Path, required=True)
    calibrate.add_argument("--lineage", choices=LINEAGES, default="q13-a")
    calibrate.add_argument("--source-seed", type=int, default=CALIBRATION_SEED)
    calibrate.add_argument("--output", type=Path, required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--tle-root", type=Path, required=True)
    prepare.add_argument("--prereg", type=Path, required=True)
    prepare.add_argument("--d2-prereg", type=Path, required=True)
    prepare.add_argument("--calibration", type=Path, required=True)
    prepare.add_argument("--main-dir", type=Path, required=True)
    prepare.add_argument("--gate-dir", type=Path, required=True)
    prepare.add_argument("--q13-source-dir", type=Path, required=True)
    prepare.add_argument("--v03-root", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    shard = sub.add_parser("shard")
    shard.add_argument("--prepare", type=Path, required=True)
    shard.add_argument("--d2-prereg", type=Path, required=True)
    shard.add_argument("--tle-root", type=Path, required=True)
    shard.add_argument("--prereg", type=Path, required=True)
    shard.add_argument("--main-dir", type=Path, required=True)
    shard.add_argument("--gate-dir", type=Path, required=True)
    shard.add_argument("--q13-source-dir", type=Path, required=True)
    shard.add_argument("--v03-root", type=Path, required=True)
    shard.add_argument("--lineage", choices=LINEAGES, required=True)
    shard.add_argument("--output", type=Path, required=True)
    adjudicate = sub.add_parser("adjudicate")
    adjudicate.add_argument("--prepare", type=Path, required=True)
    adjudicate.add_argument("--d2-prereg", type=Path, required=True)
    adjudicate.add_argument("--shard", type=Path, action="append", required=True)
    adjudicate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "calibrate":
            result = _calibrate(args)
            print(
                json.dumps(
                    {
                        "status": "CALIBRATION_COMPLETE",
                        "rows": result["row_count"],
                        "elapsed_wall_seconds": result["elapsed_wall_seconds"],
                        "output": str(args.output),
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "prepare":
            result = _prepare(args)
            print(
                json.dumps(
                    {
                        "status": "D2_PREPARED",
                        "anchors": len(result["anchors"]),
                        "prepare_sha256": result["prepare_sha256"],
                        "output": str(args.output),
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "shard":
            result = _shard(args)
            print(
                json.dumps(
                    {
                        "status": "D2_SHARD_COMPLETE",
                        "lineage": result["lineage"],
                        "cells": len(result["cells"]),
                        "shard_sha256": result["shard_sha256"],
                        "output": str(args.output),
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "adjudicate":
            result = _adjudicate(args)
            adjudication = result["result"]
            print(
                json.dumps(
                    {
                        "status": "D2_ADJUDICATION_COMPLETE",
                        "verdict": adjudication["verdict"],
                        "adjudication_sha256": result["adjudication_sha256"],
                        "output": str(args.output),
                    },
                    sort_keys=True,
                )
            )
            return 0
    except (OSError, RuntimeError, ValueError, TypeError, ImportError, AttributeError) as error:
        print(f"FAIL_CLOSED: {error}", file=sys.stderr)
        return 2
    raise V07D2RunnerError("unhandled command")


if __name__ == "__main__":
    raise SystemExit(_main())
