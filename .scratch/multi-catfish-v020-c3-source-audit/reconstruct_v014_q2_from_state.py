#!/usr/bin/env python3
"""Audit whether compact V0.14 Q2 states retain the OPS3 target mechanics.

This diagnostic is deliberately source-only.  It consumes an existing compact
TRAIN shard and reconstructs the uncentered OPS3 ``z2`` surface from the 448
feature-major state, the legal mask, and ``step_indices``.  It never opens the
simulator, propagates a TLE, trains a learner, or modifies an artifact.

The V0.14 state contract is:

* static features 0--3 are background load/user-count, background RF power /
  ``p_max``, active-beam, and active-satellite indicators;
* each offset contributes valid, persistence, required-power/p_max, and
  ``log1p(SINR)``;
* the static load divisor is the frozen V0.14 population (100 users here);
* an existing-beam marginal uses canonical supply power at the max of old and
  required RF power; a new beam adds its supply, circuit, and (if needed)
  satellite baseband terms.

The state stores float32 features, so this is an information-preservation
audit rather than a claim of bit-identical replay.  A new lambda can be
evaluated from the recovered rate and power components without new physics:

    z2(lambda') = mean_h[chi_h * interval * (rate_h - lambda' * dP_h)
                         - (1 - chi_h) * kappa].
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcrl.env.link_budget import (  # noqa: E402
    BASEBAND_POWER_PER_SATELLITE_W,
    BEAM_BANDWIDTH_HZ,
    BEAM_POWER_MAX_W,
    CIRCUIT_POWER_PER_BEAM_W,
    PA_MAX_EFFICIENCY,
    PA_SATURATION_POWER_W,
    pa_efficiency,
    supply_power_w,
)
from mcrl.runtime.ee_axis_ops3 import (  # noqa: E402
    OPS3_HORIZON,
    OPS3_INTERVAL_S,
    OPS3_KAPPA_BITS,
    OPS3_LAMBDA_BITS_PER_J,
)


ACTION_COUNT = 28
STATE_FEATURE_DIM = 16
DEFAULT_USER_COUNT = 100
DEFAULT_TOTAL_STEPS = 10
DEFAULT_SOURCE = (
    REPO
    / "artifacts"
    / "multi-catfish-v014-learnability-20260903-r1"
    / "server-run"
    / "source-panel"
    / "shards"
    / "2026108001-2026092101"
    / "source.npz"
)
DEFAULT_OUTPUT_DIR = REPO / ".scratch" / "multi-catfish-v020-c3-source-audit"
DEFAULT_JSON = DEFAULT_OUTPUT_DIR / "q2-reconstruction-audit.json"
DEFAULT_REPRICED = DEFAULT_OUTPUT_DIR / "q2-repriced-target-lambda-half.npy"


class ReconstructionError(ValueError):
    """The compact source state is malformed or not the frozen V0.14 shape."""


@dataclass(frozen=True)
class ReconstructedQ2:
    """Recovered old/new-lambda surfaces and additive components."""

    old_target_bits: np.ndarray
    repriced_target_bits: np.ndarray
    rate_component_bits: np.ndarray
    power_component_j: np.ndarray
    outage_component_bits: np.ndarray
    horizon: np.ndarray
    marginal_power_w: np.ndarray
    rate_bps: np.ndarray


def _finite_float(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ReconstructionError(f"{field} must be finite") from error
    if not math.isfinite(result):
        raise ReconstructionError(f"{field} must be finite")
    return result


def _stats(values: np.ndarray) -> dict[str, float | int | None]:
    flat = np.asarray(values, dtype=np.float64).ravel()
    if flat.size == 0:
        return {"count": 0, "max": None, "median": None, "p95": None}
    if not np.all(np.isfinite(flat)):
        raise ReconstructionError("diagnostic statistics received non-finite values")
    return {
        "count": int(flat.size),
        "max": float(np.max(flat)),
        "median": float(np.median(flat)),
        "p95": float(np.percentile(flat, 95.0)),
    }


def _binary_feature(values: np.ndarray, *, field: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(array)) or not np.all((array == 0.0) | (array == 1.0)):
        raise ReconstructionError(f"{field} must contain only binary values")
    return array.astype(np.bool_)


def _load_source(path: Path) -> dict[str, np.ndarray]:
    if path.is_symlink() or not path.is_file():
        raise ReconstructionError(f"source must be a regular file: {path}")
    with np.load(path, allow_pickle=False) as loaded:
        expected = {
            "q2_states",
            "q2_masks",
            "q2_target_bits",
            "step_indices",
            "kappa_bits",
        }
        missing = expected.difference(loaded.files)
        if missing:
            raise ReconstructionError(f"source is missing arrays: {sorted(missing)}")
        return {name: np.array(loaded[name], copy=True) for name in loaded.files}


def _load_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ReconstructionError(f"metadata is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReconstructionError(f"metadata is not valid JSON: {path}") from error
    if not isinstance(payload, dict):
        raise ReconstructionError("metadata root must be an object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_inputs(
    arrays: dict[str, np.ndarray],
    *,
    user_count: int,
    total_steps: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    states = np.asarray(arrays["q2_states"])
    masks = np.asarray(arrays["q2_masks"])
    targets = np.asarray(arrays["q2_target_bits"], dtype=np.float64)
    steps = np.asarray(arrays["step_indices"])
    kappa_array = np.asarray(arrays["kappa_bits"], dtype=np.float64)
    if states.ndim != 2 or states.shape[1] != STATE_FEATURE_DIM * ACTION_COUNT:
        raise ReconstructionError(
            f"q2_states must have shape (N,{STATE_FEATURE_DIM * ACTION_COUNT})"
        )
    rows = int(states.shape[0])
    if masks.shape != (rows, ACTION_COUNT) or masks.dtype != np.bool_:
        raise ReconstructionError("q2_masks must be Boolean shape (N,28)")
    if targets.shape != (rows, ACTION_COUNT) or not np.all(np.isfinite(targets)):
        raise ReconstructionError("q2_target_bits must be finite shape (N,28)")
    if steps.shape != (rows,) or not np.issubdtype(steps.dtype, np.integer):
        raise ReconstructionError("step_indices must be integer shape (N,)")
    if np.any(steps < 0) or np.any(steps >= total_steps):
        raise ReconstructionError("step_indices are outside the frozen episode")
    if kappa_array.shape != (1,):
        raise ReconstructionError("kappa_bits must have shape (1,)")
    kappa = _finite_float(kappa_array[0], field="kappa_bits")
    if kappa <= 0.0:
        raise ReconstructionError("kappa_bits must be positive")
    if type(user_count) is not int or user_count < 1:
        raise ReconstructionError("user_count must be a positive integer")
    if type(total_steps) is not int or total_steps < 1:
        raise ReconstructionError("total_steps must be a positive integer")
    if not np.all(np.isfinite(states)):
        raise ReconstructionError("q2_states must be finite")
    if np.any(targets[~masks] != 0.0):
        raise ReconstructionError("q2_target_bits must be zero outside q2_masks")
    return states.astype(np.float64), masks, targets, steps.astype(np.int64), kappa


def reconstruct_q2_targets(
    states: object,
    masks: object,
    step_indices: object,
    *,
    kappa_bits: float,
    lambda_bits_per_j: float,
    user_count: int = DEFAULT_USER_COUNT,
    total_steps: int = DEFAULT_TOTAL_STEPS,
    lambda_new_bits_per_j: float | None = None,
) -> ReconstructedQ2:
    """Decode Q2 ``z2`` and optionally reprice it at ``lambda_new``.

    This function only uses compact features.  In particular, it does not
    accept candidate identities, geometry, SINR, or simulator state.  The
    physical identities have been reduced by the V0.14 static beam/satellite
    indicators, while the signal term is retained as ``log1p(SINR)``.
    """

    raw_states = np.asarray(states)
    if raw_states.ndim < 1:
        raise ReconstructionError("q2_states must be a two-dimensional array")
    arrays = {
        "q2_states": np.asarray(states),
        "q2_masks": np.asarray(masks),
        "q2_target_bits": np.zeros((raw_states.shape[0], ACTION_COUNT)),
        "step_indices": np.asarray(step_indices),
        "kappa_bits": np.asarray([kappa_bits], dtype=np.float64),
    }
    state, legal, _ignored_target, steps, kappa = _validate_inputs(
        arrays,
        user_count=user_count,
        total_steps=total_steps,
    )
    lambda_old = _finite_float(lambda_bits_per_j, field="lambda_bits_per_j")
    if lambda_old <= 0.0:
        raise ReconstructionError("lambda_bits_per_j must be positive")
    lambda_new = lambda_old if lambda_new_bits_per_j is None else _finite_float(
        lambda_new_bits_per_j,
        field="lambda_new_bits_per_j",
    )
    if lambda_new <= 0.0:
        raise ReconstructionError("lambda_new_bits_per_j must be positive")

    features = state.reshape(-1, STATE_FEATURE_DIM, ACTION_COUNT)
    background_load = features[:, 0, :] * float(user_count)
    background_power = features[:, 1, :] * float(BEAM_POWER_MAX_W)
    beam_active = _binary_feature(features[:, 2, :], field="beam_active")
    satellite_active = _binary_feature(features[:, 3, :], field="satellite_active")
    if np.any(beam_active & ~satellite_active):
        raise ReconstructionError("an active beam cannot belong to an inactive satellite")
    if np.any(background_load < 0.0) or np.any(background_power < 0.0):
        raise ReconstructionError("background load/power must be non-negative")
    if np.any((~beam_active) & ((background_load != 0.0) | (background_power != 0.0))):
        raise ReconstructionError("inactive beams must have zero background load and power")

    horizons = np.minimum(
        OPS3_HORIZON,
        np.maximum(0, total_steps - 1 - steps),
    ).astype(np.int64)
    rate_component = np.zeros((state.shape[0], ACTION_COUNT), dtype=np.float64)
    power_component = np.zeros((state.shape[0], ACTION_COUNT), dtype=np.float64)
    outage_component = np.zeros((state.shape[0], ACTION_COUNT), dtype=np.float64)
    marginal_power = np.zeros((OPS3_HORIZON, state.shape[0], ACTION_COUNT), dtype=np.float64)
    rate_bps = np.zeros_like(marginal_power)

    for offset in range(OPS3_HORIZON):
        block = 4 + 4 * offset
        valid = _binary_feature(features[:, block, :], field=f"h{offset + 1}_valid")
        persistence = _binary_feature(
            features[:, block + 1, :], field=f"h{offset + 1}_persistence"
        )
        required_ratio = features[:, block + 2, :]
        log1p_sinr = features[:, block + 3, :]
        if np.any(required_ratio < 0.0) or np.any(log1p_sinr < 0.0):
            raise ReconstructionError(f"h{offset + 1} rate/power features must be non-negative")
        expected_valid = legal & (offset < horizons[:, None])
        if not np.array_equal(valid, expected_valid):
            raise ReconstructionError(
                f"h{offset + 1}_valid does not match legal mask and step-index horizon"
            )
        if np.any(persistence & ~valid):
            raise ReconstructionError(f"h{offset + 1}_persistence is true outside valid rows")
        if np.any((log1p_sinr != 0.0) & ~persistence):
            raise ReconstructionError(f"h{offset + 1}_log1p_sinr is nonzero after service loss")
        if np.any((required_ratio != 0.0) & ~valid):
            raise ReconstructionError(f"h{offset + 1}_required_power_ratio is nonzero outside horizon")

        required_power = required_ratio * float(BEAM_POWER_MAX_W)
        old_supply = supply_power_w(
            background_power,
            pa_efficiency(background_power),
        )
        max_beam_power = np.maximum(background_power, required_power)
        existing_delta = supply_power_w(
            max_beam_power,
            pa_efficiency(max_beam_power),
        ) - old_supply
        new_delta = (
            supply_power_w(required_power, pa_efficiency(required_power))
            + float(CIRCUIT_POWER_PER_BEAM_W)
            + np.where(
                satellite_active,
                0.0,
                float(BASEBAND_POWER_PER_SATELLITE_W),
            )
        )
        candidate_delta = np.where(
            beam_active,
            existing_delta,
            np.where(required_power > 0.0, new_delta, 0.0),
        )
        candidate_delta = np.where(legal, candidate_delta, 0.0)
        if not np.all(np.isfinite(candidate_delta)):
            raise ReconstructionError(f"h{offset + 1} marginal power is non-finite")

        load = 1.0 + background_load
        rate = (
            float(BEAM_BANDWIDTH_HZ)
            * log1p_sinr
            / (load * math.log(2.0))
        )
        rate = np.where(legal, rate, 0.0)
        if not np.all(np.isfinite(rate)):
            raise ReconstructionError(f"h{offset + 1} reconstructed rate is non-finite")

        chi = persistence.astype(np.float64)
        in_horizon = offset < horizons[:, None]
        rate_terms = np.where(
            in_horizon,
            chi * float(OPS3_INTERVAL_S) * rate,
            0.0,
        )
        power_terms = np.where(
            in_horizon,
            chi * float(OPS3_INTERVAL_S) * candidate_delta,
            0.0,
        )
        outage_terms = np.where(
            in_horizon,
            (1.0 - chi) * kappa,
            0.0,
        )
        rate_component += rate_terms
        power_component += power_terms
        outage_component += outage_terms
        marginal_power[offset] = candidate_delta
        rate_bps[offset] = rate

    divisor = np.maximum(horizons, 1).astype(np.float64)
    old_target = (rate_component - lambda_old * power_component - outage_component) / divisor[:, None]
    repriced_target = (
        rate_component - lambda_new * power_component - outage_component
    ) / divisor[:, None]
    old_target = np.where(legal, old_target, 0.0)
    repriced_target = np.where(legal, repriced_target, 0.0)
    if not np.all(np.isfinite(old_target)) or not np.all(np.isfinite(repriced_target)):
        raise ReconstructionError("reconstructed target surface is non-finite")
    return ReconstructedQ2(
        old_target_bits=old_target,
        repriced_target_bits=repriced_target,
        rate_component_bits=rate_component,
        power_component_j=power_component,
        outage_component_bits=outage_component,
        horizon=horizons,
        marginal_power_w=marginal_power,
        rate_bps=rate_bps,
    )


def _audit(
    *,
    source_path: Path,
    metadata_path: Path,
    output_json: Path,
    repriced_output: Path,
    user_count: int,
    total_steps: int,
    lambda_new: float,
) -> dict[str, Any]:
    arrays = _load_source(source_path)
    metadata = _load_metadata(metadata_path)
    states, masks, target, steps, kappa = _validate_inputs(
        arrays,
        user_count=user_count,
        total_steps=total_steps,
    )
    try:
        old_lambda = float.fromhex(
            str(metadata.get("ops3_lambda_bits_per_j_hex", ""))
        )
    except ValueError as error:
        raise ReconstructionError("source old lambda metadata is malformed") from error
    if float(old_lambda).hex() != float(OPS3_LAMBDA_BITS_PER_J).hex():
        raise ReconstructionError("source old lambda is not the current frozen OPS3 lambda")
    if float(kappa).hex() != float(OPS3_KAPPA_BITS).hex():
        raise ReconstructionError("source kappa is not the current frozen OPS3 kappa")

    reconstructed = reconstruct_q2_targets(
        states,
        masks,
        steps,
        kappa_bits=kappa,
        lambda_bits_per_j=old_lambda,
        user_count=user_count,
        total_steps=total_steps,
        lambda_new_bits_per_j=lambda_new,
    )
    error = reconstructed.old_target_bits - target
    legal_error = error[masks]
    legal_target = target[masks]
    absolute = np.abs(legal_error)
    nonzero = np.abs(legal_target) > 0.0
    relative = np.divide(
        absolute,
        np.abs(legal_target),
        out=np.full_like(absolute, np.nan),
        where=nonzero,
    )
    target_scale = float(np.max(np.abs(legal_target))) if legal_target.size else 1.0
    scale_relative = absolute / target_scale if target_scale else absolute
    affine = reconstructed.old_target_bits - (
        lambda_new - old_lambda
    ) * reconstructed.power_component_j / np.maximum(
        reconstructed.horizon, 1
    )[:, None]
    affine_error = np.abs(affine - reconstructed.repriced_target_bits)[masks]
    source_sha = _sha256(source_path)
    metadata_npz_sha = metadata.get("npz_sha256")
    source_sha_receipt = source_path.with_name("source.sha256")
    source_receipt: dict[str, str] = {}
    if source_sha_receipt.is_file():
        for line in source_sha_receipt.read_text(encoding="ascii").splitlines():
            if "=" in line:
                name, value = line.split("=", 1)
                source_receipt[name] = value
    payload: dict[str, Any] = {
        "schema": "multi-catfish-mcrl-v020-c3-q2-state-reconstruction-audit-v1",
        "source": str(source_path),
        "source_sha256": source_sha,
        "metadata_npz_sha256": metadata_npz_sha,
        "source_receipt_matches": bool(source_sha == metadata_npz_sha),
        "source_receipt": source_receipt,
        "source_metadata": {
            "schema": metadata.get("schema"),
            "split": metadata.get("split"),
            "test_split_opened": metadata.get("test_split_opened"),
            "row_count": metadata.get("row_count"),
            "q2_state_dim": metadata.get("q2_state_dim"),
            "q2_target_semantics": metadata.get("q2_target_semantics"),
        },
        "frozen_assumptions": {
            "user_count": user_count,
            "total_steps": total_steps,
            "action_count": ACTION_COUNT,
            "horizon_rule": "min(3, total_steps - 1 - step_index)",
            "interval_s": float(OPS3_INTERVAL_S),
            "beam_bandwidth_hz": float(BEAM_BANDWIDTH_HZ),
            "beam_power_max_w": float(BEAM_POWER_MAX_W),
            "pa_max_efficiency": float(PA_MAX_EFFICIENCY),
            "pa_saturation_power_w": float(PA_SATURATION_POWER_W),
            "old_lambda_bits_per_j": old_lambda,
            "old_lambda_bits_per_j_hex": float(old_lambda).hex(),
            "kappa_bits": kappa,
        },
        "rows": int(states.shape[0]),
        "legal_entries": int(np.count_nonzero(masks)),
        "zero_target_legal_entries": int(np.count_nonzero(~nonzero)),
        "horizon_counts": {
            str(value): int(np.count_nonzero(reconstructed.horizon == value))
            for value in range(OPS3_HORIZON + 1)
        },
        "error_metrics_on_legal_entries": {
            "absolute_bits": _stats(absolute),
            "relative_to_nonzero_target": _stats(relative[nonzero]),
            "relative_to_max_abs_target_scale": _stats(scale_relative),
        },
        "repricing": {
            "new_lambda_bits_per_j": float(lambda_new),
            "new_lambda_bits_per_j_hex": float(lambda_new).hex(),
            "target_bits_min": float(np.min(reconstructed.repriced_target_bits[masks])),
            "target_bits_max": float(np.max(reconstructed.repriced_target_bits[masks])),
            "target_bits_median": float(np.median(reconstructed.repriced_target_bits[masks])),
            "affine_reconstruction_absolute_bits": _stats(affine_error),
            "formula": "z2(lambda') = z2(lambda) - (lambda' - lambda) * mean_h[chi_h * interval * dP_h]",
            "physics_rerun": False,
        },
        "interpretation": {
            "state_sufficient_under_contract": bool(
                np.max(absolute) <= 2_000.0
                and np.max(scale_relative) < 1.0e-6
            ),
            "float32_precision_ceiling_observed": float(np.max(absolute)),
            "scientific_boundary": (
                "Linear lambda repricing is supported under the frozen V0.14 "
                "100-user/10-step OPS3 contract. The state is not bit-exact "
                "because its 16 features are float32, and repricing does not "
                "recompute geometry or a changed policy/physics model."
            ),
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    repriced_output.parent.mkdir(parents=True, exist_ok=True)
    np.save(repriced_output, reconstructed.repriced_target_bits)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--repriced-output", type=Path, default=DEFAULT_REPRICED)
    parser.add_argument(
        "--lambda-new",
        type=float,
        default=None,
        help="new lambda in bits/J (default: one half of the frozen old lambda)",
    )
    parser.add_argument("--user-count", type=int, default=DEFAULT_USER_COUNT)
    parser.add_argument("--total-steps", type=int, default=DEFAULT_TOTAL_STEPS)
    args = parser.parse_args(argv)
    metadata = args.metadata or args.source.with_name("metadata.json")
    lambda_new = (
        float(OPS3_LAMBDA_BITS_PER_J) / 2.0
        if args.lambda_new is None
        else float(args.lambda_new)
    )
    payload = _audit(
        source_path=args.source,
        metadata_path=metadata,
        output_json=args.output_json,
        repriced_output=args.repriced_output,
        user_count=args.user_count,
        total_steps=args.total_steps,
        lambda_new=lambda_new,
    )
    metrics = payload["error_metrics_on_legal_entries"]
    print(
        json.dumps(
            {
                "source": str(args.source),
                "legal_entries": payload["legal_entries"],
                "absolute_bits": metrics["absolute_bits"],
                "relative_to_nonzero_target": metrics["relative_to_nonzero_target"],
                "relative_to_max_abs_target_scale": metrics[
                    "relative_to_max_abs_target_scale"
                ],
                "repriced_output": str(args.repriced_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
