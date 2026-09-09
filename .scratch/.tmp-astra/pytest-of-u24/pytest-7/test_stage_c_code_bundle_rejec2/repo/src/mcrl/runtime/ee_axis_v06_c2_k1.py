"""Clean V0.6 C2-k1 source/oracle-headroom contract.

This module is intentionally a small, simulator-independent boundary.  It
contains the parts that must not be reinterpreted by a source runner:

* deterministic fresh TRAIN-world/anchor selection;
* a frozen, branch-local Q1+Q3 continuation policy;
* the one-step temporal surplus target at offset ``k=1``;
* direct DROP and oracle action scores; and
* ratio-of-sums and service-gate bookkeeping for a four-offset trace.

There is no Q2, hold/release compositor, action tape, fallback, sign filter,
or outcome-based row selection here.  A production runner may provide the
physics and frozen-network bytes, but it must use these pure functions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np

from ..env.action_contract import NUM_ACTIONS, NO_OP_ACTION


SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-v1"
SOURCE_RULE = "c2-k1-total-policy-effect-branch-local-v1"
POLICY_RULE = "frozen-q1-plus-q3-own-branch-state-mask-v1"
CLAIM_CEILING = "TRAIN_DESIGN_FALSIFICATION_ONLY_NO_LEARNING_NO_TEST_NO_EE_EFFICACY"
POOL_NAMES = ("early", "mid", "late")
TRAIN_WORLD_POOLS: dict[str, tuple[int, ...]] = {
    "early": tuple(range(2026101001, 2026101011)),
    "mid": tuple(range(2026101011, 2026101021)),
    "late": tuple(range(2026101021, 2026101031)),
}
WORLD_COUNT_PER_POOL = 4
ACTION_COUNT = NUM_ACTIONS
OFFSET_COUNT = 4
K1_OFFSET = 1
K2_K3_OFFSETS = (2, 3)
TRAIN_STEP_WINDOWS: dict[str, tuple[int, int]] = {
    "early": (1, 2), "mid": (3, 4), "late": (5, 6),
}


class C2K1ContractError(ValueError):
    """Input or source contract is invalid and must fail closed."""


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        raise C2K1ContractError(f"{field} must be finite numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise C2K1ContractError(f"{field} must be finite numeric") from exc
    if not math.isfinite(result):
        raise C2K1ContractError(f"{field} must be finite numeric")
    return result


def _array(value: object, *, field: str, shape: tuple[int, ...] | None = None,
           dtype: Any = np.float64) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=dtype)
    except (TypeError, ValueError) as exc:
        raise C2K1ContractError(f"{field} is not a numeric array") from exc
    if shape is not None and result.shape != shape:
        raise C2K1ContractError(f"{field} must have shape {shape}, got {result.shape}")
    if np.issubdtype(result.dtype, np.number) and not np.all(np.isfinite(result)):
        raise C2K1ContractError(f"{field} must be finite")
    return np.array(result, copy=True, order="C")


def canonical_bytes(payload: object) -> bytes:
    try:
        return (json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise C2K1ContractError("payload is not canonical finite JSON") from exc


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_bytes(payload)[:-1]).hexdigest()


def write_once_json(path: Path, payload: object) -> str:
    """Atomically create one canonical JSON file; never overwrite a seal."""
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite sealed file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload)
    fd, name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp",
                                 dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise FileExistsError(f"refusing to overwrite sealed file: {destination}") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def select_train_worlds(eligible_by_pool: Mapping[str, Sequence[int]]) -> tuple[tuple[str, int], ...]:
    """Select the first four eligible worlds from each fixed pool.

    The function takes only pre-treatment eligibility.  It rejects unknown,
    duplicated, or out-of-pool IDs, making post-outcome selection impossible.
    """
    if set(eligible_by_pool) != set(POOL_NAMES):
        raise C2K1ContractError("eligible world pools must be exactly early, mid, late")
    selected: list[tuple[str, int]] = []
    seen: set[int] = set()
    for pool in POOL_NAMES:
        allowed = set(TRAIN_WORLD_POOLS[pool])
        values = list(eligible_by_pool[pool])
        if len(values) != len(set(values)):
            raise C2K1ContractError(f"{pool} eligibility contains duplicate worlds")
        if any(type(value) is not int or value not in allowed for value in values):
            raise C2K1ContractError(f"{pool} contains an ID outside its fixed pool")
        ordered = sorted(values)
        if len(ordered) < WORLD_COUNT_PER_POOL:
            raise C2K1ContractError(f"{pool} has fewer than four eligible worlds")
        for world in ordered[:WORLD_COUNT_PER_POOL]:
            if world in seen:
                raise C2K1ContractError("TRAIN world IDs are not independent")
            seen.add(world)
            selected.append((pool, world))
    return tuple(selected)


@dataclass(frozen=True)
class Anchor:
    pool: str
    world_id: int
    step: int
    focal_user: int

    def __post_init__(self) -> None:
        if self.pool not in POOL_NAMES or self.world_id not in TRAIN_WORLD_POOLS[self.pool]:
            raise C2K1ContractError("anchor world is outside the fixed TRAIN pool")
        if type(self.step) is not int or self.step < 0:
            raise C2K1ContractError("anchor step must be a nonnegative integer")
        if type(self.focal_user) is not int or self.focal_user < 0:
            raise C2K1ContractError("focal user must be a nonnegative integer")


def select_anchor(pool: str, world_id: int, eligible_steps: Sequence[int],
                  eligible_users: Sequence[int]) -> Anchor:
    """Choose the first predecision step and lowest eligible focal user."""
    if pool not in POOL_NAMES or world_id not in TRAIN_WORLD_POOLS[pool]:
        raise C2K1ContractError("world is outside the fixed TRAIN pool")
    steps = sorted(set(eligible_steps))
    users = sorted(set(eligible_users))
    if not steps or any(type(value) is not int or value < 0 for value in steps):
        raise C2K1ContractError("predecision eligible steps are empty or malformed")
    if not users or any(type(value) is not int or value < 0 for value in users):
        raise C2K1ContractError("predecision eligible users are empty or malformed")
    lo, hi = TRAIN_STEP_WINDOWS[pool]
    if any(value < lo or value > hi for value in steps):
        raise C2K1ContractError(f"{pool} eligible steps must be within {lo}..{hi}")
    return Anchor(pool, world_id, steps[0], users[0])


def masked_argmax(q1: object, q3: object, mask: object, *, field: str = "policy") -> int:
    """Safe argmax of frozen Q1+Q3 under the supplied branch-local mask."""
    first = _array(q1, field=f"{field}.q1", shape=(ACTION_COUNT,))
    third = _array(q3, field=f"{field}.q3", shape=(ACTION_COUNT,))
    legal = np.asarray(mask)
    if legal.shape != (ACTION_COUNT,) or legal.dtype != np.bool_:
        raise C2K1ContractError(f"{field}.mask must be Boolean shape ({ACTION_COUNT},)")
    if not bool(np.any(legal)):
        return NO_OP_ACTION
    scores = first + third
    return int(np.argmax(np.where(legal, scores, -np.inf)))


def branch_local_actions(q1: object, q3: object, mask: object, *, field: str) -> int:
    """Alias whose name makes branch-local use explicit at the call site."""
    return masked_argmax(q1, q3, mask, field=field)


def c2_k1_surplus_bits(candidate_rates: object, reference_rates: object,
                       candidate_power_w: object, reference_power_w: object,
                       *, interval_s: float, lambda_bits_per_j: float) -> float:
    """Compute the exact C2 target at offset k=1.

    ``candidate_rates`` and ``reference_rates`` are user-rate vectors at k=1;
    power values are the complete network-power terms at k=1.  All signs are
    retained, including zero and negative surpluses.
    """
    cand = _array(candidate_rates, field="candidate_rates_k1", dtype=np.float64)
    ref = _array(reference_rates, field="reference_rates_k1", dtype=np.float64)
    if cand.ndim != 1 or ref.shape != cand.shape:
        raise C2K1ContractError("k1 rate vectors must be equal-length one-dimensional arrays")
    interval = _finite(interval_s, field="interval_s")
    multiplier = _finite(lambda_bits_per_j, field="lambda_bits_per_j")
    if interval <= 0 or multiplier <= 0:
        raise C2K1ContractError("interval_s and lambda_bits_per_j must be positive")
    delta_power = _finite(candidate_power_w, field="candidate_power_w") - _finite(reference_power_w, field="reference_power_w")
    return float(interval * math.fsum((float(x) for x in cand - ref))
                 - multiplier * interval * delta_power)


def oracle_and_drop_scores(q1: object, q3: object, z2_k1_normalized: object,
                           mask: object) -> tuple[int, int]:
    """Return direct, unweighted oracle and DROP-C2 masked actions.

    The oracle is ``argmax(Q1+Q3+z2/kappa)`` and DROP is
    ``argmax(Q1+Q3)``.  ``z2`` is already normalized by the caller; no Q2
    network or learned weight is accepted by this interface.
    """
    first = _array(q1, field="oracle.q1", shape=(ACTION_COUNT,))
    third = _array(q3, field="oracle.q3", shape=(ACTION_COUNT,))
    target = _array(z2_k1_normalized, field="oracle.z2_k1_normalized", shape=(ACTION_COUNT,))
    legal = np.asarray(mask)
    if legal.shape != (ACTION_COUNT,) or legal.dtype != np.bool_ or not np.any(legal):
        raise C2K1ContractError("oracle mask must be nonempty Boolean shape (28,)")
    base = first + third
    drop = int(np.argmax(np.where(legal, base, -np.inf)))
    oracle = int(np.argmax(np.where(legal, base + target, -np.inf)))
    return oracle, drop


@dataclass(frozen=True)
class OpeningPair:
    """One opening action and both branch-local k1 decisions."""

    action: int
    reference_action: int
    reference_k1_action: int
    candidate_k1_action: int
    z2_k1_bits: float
    z2_k1_normalized: float


def build_opening_pairs(q1_k0: object, q3_k0: object, mask_k0: object,
                        branch_rows: Sequence[Mapping[str, object]], *,
                        reference_action: int,
                        interval_s: float, lambda_bits_per_j: float,
                        kappa_bits: float) -> tuple[OpeningPair, ...]:
    """Build all 28 opening pairs for one frozen lineage.

    ``branch_rows`` must contain one row per action.  Each row supplies the
    branch-local k1 states/masks and k1 rates/powers.  The focal action is
    changed only at k0; k1 is always independently selected from each own
    state/mask.
    """
    if len(branch_rows) != ACTION_COUNT:
        raise C2K1ContractError("T1 requires exactly 28 opening action rows")
    # The gauge is the frozen Main opening selected before source generation.
    # It is an explicit sealed input; deriving it from Q1+Q3 would silently
    # change the reference branch when a hybrid or mask changes.
    if type(reference_action) is not int or not 0 <= reference_action < ACTION_COUNT:
        raise C2K1ContractError("reference_action must be an exact native action")
    legal = np.asarray(mask_k0)
    if legal.shape != (ACTION_COUNT,) or legal.dtype != np.bool_:
        raise C2K1ContractError("opening reference mask must be Boolean shape (28,)")
    if not bool(legal[reference_action]):
        raise C2K1ContractError("explicit reference_action is not legal at the anchor")
    # Validate Q surfaces even though they are not used to infer the gauge.
    _array(q1_k0, field="opening.q1_k0", shape=(ACTION_COUNT,))
    _array(q3_k0, field="opening.q3_k0", shape=(ACTION_COUNT,))
    kappa = _finite(kappa_bits, field="kappa_bits")
    if kappa <= 0:
        raise C2K1ContractError("kappa_bits must be positive")
    pairs: list[OpeningPair] = []
    for action, row in enumerate(branch_rows):
        if not isinstance(row, Mapping):
            raise C2K1ContractError(f"opening row {action} is malformed")
        ref_k1 = branch_local_actions(row["reference_q1_k1"], row["reference_q3_k1"],
                                      row["reference_mask_k1"], field=f"row{action}.reference")
        cand_k1 = branch_local_actions(row["candidate_q1_k1"], row["candidate_q3_k1"],
                                       row["candidate_mask_k1"], field=f"row{action}.candidate")
        z = c2_k1_surplus_bits(row["candidate_rates_k1"], row["reference_rates_k1"],
                               row["candidate_power_k1"], row["reference_power_k1"],
                               interval_s=interval_s, lambda_bits_per_j=lambda_bits_per_j)
        pairs.append(OpeningPair(action, reference_action, ref_k1, cand_k1, z, z / kappa))
    return tuple(pairs)


def four_offset_metrics(rates_bps: object, power_w: object, served: object,
                        *, interval_s: float) -> dict[str, Any]:
    """Compute ratio-of-sums EE and explicit service gates for k=0..3."""
    rates = _array(rates_bps, field="rates_bps", dtype=np.float64)
    power = _array(power_w, field="power_w", dtype=np.float64)
    service = np.asarray(served)
    if rates.ndim not in (2, 3) or rates.shape[0] != OFFSET_COUNT:
        raise C2K1ContractError("rates_bps must have shape (4, users) or (4, cells, users)")
    if power.shape != (OFFSET_COUNT,) or np.any(power <= 0):
        raise C2K1ContractError("power_w must be positive shape (4,)")
    if service.shape != rates.shape or service.dtype != np.bool_:
        raise C2K1ContractError("served must be Boolean and match rates_bps")
    interval = _finite(interval_s, field="interval_s")
    if interval <= 0:
        raise C2K1ContractError("interval_s must be positive")
    # EE numerator is the canonical realised-rate sum.  Service is a
    # separate gate only; it must never remask the physical rate numerator.
    rate_axes = tuple(range(1, rates.ndim))
    bits_by_offset = interval * np.sum(rates, axis=rate_axes)
    energy_by_offset = interval * power
    bits = float(np.sum(bits_by_offset))
    energy = float(np.sum(energy_by_offset))
    service_axes = tuple(range(1, service.ndim))
    gate = bool(np.all(np.any(service, axis=service_axes)))
    cells = int(rates.shape[1]) if rates.ndim == 3 else 1
    users = int(rates.shape[-1])
    served_count = int(np.count_nonzero(service))
    served_fraction = float(served_count / (cells * OFFSET_COUNT * users))
    served_by_offset = np.sum(service, axis=service_axes).astype(int)
    return {"bits_by_offset": bits_by_offset.tolist(), "energy_by_offset": energy_by_offset.tolist(),
            "total_bits": bits, "total_energy_j": energy,
            "ratio_of_sums_ee_bits_per_j": bits / energy,
            "service_gate": {"passed": gate,
                              "served_users_by_offset": served_by_offset.tolist(),
                              "served_fraction": served_fraction,
                              "all_offsets_have_service": gate}}


def selected_continuation_metrics(row: Mapping[str, object], *, policy: str,
                                  interval_s: float) -> dict[str, Any]:
    """Evaluate only a preselected ``oracle`` or ``drop`` continuation.

    The caller supplies the branch-local four-offset trace under the explicit
    ``<policy>_rates_bps``, ``<policy>_power_w``, and ``<policy>_served`` keys.
    No third policy is accepted, and no row is selected from its metric.
    """
    if policy not in {"oracle", "drop"}:
        raise C2K1ContractError("continuation policy must be oracle or drop")
    prefix = f"{policy}_"
    required = (f"{prefix}rates_bps", f"{prefix}power_w", f"{prefix}served")
    missing = [field for field in required if field not in row]
    if missing:
        raise C2K1ContractError(f"continuation row lacks {','.join(missing)}")
    result = four_offset_metrics(row[required[0]], row[required[1]], row[required[2]], interval_s=interval_s)
    result["policy"] = policy
    return result


def policy_hash(q1_bytes: object, q3_bytes: object, mask_bytes: object) -> str:
    """Hash the frozen Q1/Q3/mask byte lineage used by T1."""
    digest = hashlib.sha256()
    for label, value in (("q1", q1_bytes), ("q3", q3_bytes), ("mask", mask_bytes)):
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise C2K1ContractError(f"{label}_bytes must be bytes-like")
        digest.update(label.encode("ascii") + b"\0")
        digest.update(bytes(value))
    return digest.hexdigest()


__all__ = [
    "ACTION_COUNT", "Anchor", "C2K1ContractError", "CLAIM_CEILING", "OpeningPair",
    "POLICY_RULE", "POOL_NAMES", "SCHEMA", "SOURCE_RULE", "TRAIN_WORLD_POOLS",
    "TRAIN_STEP_WINDOWS",
    "build_opening_pairs", "branch_local_actions", "canonical_bytes", "canonical_sha256",
    "c2_k1_surplus_bits", "four_offset_metrics", "masked_argmax", "oracle_and_drop_scores",
    "selected_continuation_metrics",
    "policy_hash", "select_anchor", "select_train_worlds", "write_once_json",
]
