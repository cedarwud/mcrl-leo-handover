#!/usr/bin/env python3
"""C-A exact action-set Shapley oracle fast screen.

``--estimate`` is read-only and intentionally works while the controller
contract is still unsealed.  ``--dry-run`` and every acquisition/merge path
fail closed until the controller contract, preflight, and separate launch
authority are immutable and mutually authenticated.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
from dataclasses import dataclass
import fcntl
from fractions import Fraction
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-existence-e1"
F1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f1"
F2_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f2"
for _path in (HERE, E1_DIR, F1_DIR, F2_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v023_c3_existence_e1 as e1  # noqa: E402
from run_v023_c3_existence_e1 import (  # noqa: E402
    pin_single_thread_runtime as _e1_pin_single_thread_runtime,
)
import run_v023_c3_contingency_f1 as f1  # noqa: E402
import run_v023_c3_contingency_f2 as f2  # noqa: E402
from mcrl.env.action_contract import NO_OP_ACTION  # noqa: E402
from mcrl.env.antenna import RX_GAIN_MAX_DBI  # noqa: E402
from mcrl.env.interference import (  # noqa: E402
    beam_field_at_users,
    build_radiating_beams,
    co_channel_interference,
    received_power_terms,
)
from mcrl.env.link_budget import (  # noqa: E402
    BEAM_POWER_MAX_W,
    SEGMENT_START_POWER_W,
    beam_power_w,
    classify_link_power_feasibility,
    pa_efficiency,
    recurrence_power_w,
    shannon_rate_bps,
    supply_power_w,
    system_power_w,
)
from mcrl.env.ephemeris import SatelliteSet, step_times  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import (  # noqa: E402
    OPS3_HORIZON,
    OPS3_INTERVAL_S,
    opening_service_feasibility_surface,
)
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    OPS3AnchorSnapshot,
    OPS3ProjectionReceipt,
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_opening_source import (  # noqa: E402
    OpeningSourceProvenance,
    produce_opening_comparison,
)


SCHEMA = "multi-catfish-mcrl-v023-c3-candidate-ca-v1"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-manifest"
LAUNCH_AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"
UNIT_TAPE_SCHEMA = f"{SCHEMA}-unit-oracle-tape"
UNIT_RECEIPT_SCHEMA = f"{SCHEMA}-unit-receipt"
TERMINAL_RECEIPT_SCHEMA = f"{SCHEMA}-terminal-receipt"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C3_CANDIDATE_CA_FAST_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST"
)

LAMBDA_BITS_PER_J = 118424222.8550065
KAPPA_BITS = 10097071012.757404
INTERVAL_S = 47 * 0.640
SERVICE_MARGIN = Fraction(1, 1000)
WORLDS = e1.WORLDS
LINEAGES = e1.LINEAGES
STEP_INDICES = (0, 1)
USERS = 100
NUM_ACTIONS = f1.NUM_ACTIONS
ALL_UNITS: tuple["UnitKey", ...]
E1_OUTPUT_ROOT = Path("/home/sat/mcrl-v023-c3-existence-e1-20260908-r1")
E1_TERMINAL = E1_OUTPUT_ROOT / e1.DEFAULT_TERMINAL_RECEIPT_NAME
CONTRACT_PATH = (
    E1_DIR / "candidates" / "V023-C3-CANDIDATE-A-CONTRACT-2026-09-08.md"
)
CONTROLLER_REVIEW_PATH = E1_DIR / "candidates" / "CONTROLLER-REVIEW-CANDIDATES-2026-09-08.md"
CANONICAL_TLE_ROOT = e1.CANONICAL_TLE_ROOT
CANONICAL_INTERPRETER = e1.CANONICAL_INTERPRETER
DEFAULT_PREFLIGHT = HERE / "CA-PREFLIGHT-MANIFEST.json"
DEFAULT_UNIT_TAPE = "ca-oracle-tape.json"
DEFAULT_UNIT_RECEIPT = "receipt.json"
DEFAULT_TERMINAL_RECEIPT = "terminal-receipt.json"
DEFAULT_BUDGET_LEDGER = "budget-ledger.json"
DEFAULT_BUDGET_WORKER_SECONDS = 57_600.0
DEFAULT_RESERVATION_WORKER_SECONDS = DEFAULT_BUDGET_WORKER_SECONDS / 12.0
F1_SECONDS_PER_UNIT_TWO_STEPS = Fraction(383, 1)
F1_PROFILES_PER_UNIT_TWO_STEPS = Fraction(2700, 1)
_RX_GAIN_MAX_LINEAR = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)


class CAError(RuntimeError):
    """An authority, replay, physics, or immutable receipt failed closed."""


class CAIncomplete(CAError):
    """Acquisition stopped without truncating a declared calculation."""

    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


class CAMergeWaiting(CAIncomplete):
    def __init__(self, missing: int) -> None:
        self.missing = missing
        super().__init__("MISSING_UNITS", f"{missing} units missing")


def pin_single_thread_runtime() -> None:
    """Use the E1 pin, as required by the inter-op/runtime contract."""

    try:
        _e1_pin_single_thread_runtime()
    except e1.E1Error as error:
        raise CAError(str(error)) from error


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as error:
        raise CAError("payload is not canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str) or len(value) != 64 or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CAError(f"{field} must be lowercase SHA-256")
    return value


def _load_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise CAError(f"{field} is missing or symlinked")
    try:
        value = json.loads(target.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CAError(f"{field} is not valid JSON") from error
    if not isinstance(value, dict):
        raise CAError(f"{field} must be a JSON object")
    return value


def write_once(path: Path, payload: Mapping[str, object]) -> str:
    """Publish canonical JSON as 0444 and authenticate a reopened readback."""

    target = Path(path)
    if target.exists() or target.is_symlink():
        raise CAError(f"refusing to overwrite write-once artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(dict(payload)) + b"\n"
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    observed = target.read_bytes()
    digest = hashlib.sha256(observed).hexdigest()
    if (
        observed != encoded or target.stat().st_mode & 0o777 != 0o444
        or _load_json(target, field=f"published {target.name}") != dict(payload)
    ):
        raise CAError(f"published artifact failed immutable readback: {target}")
    return digest


def _write_sidecar(path: Path, digest: str) -> Path:
    target = Path(path)
    sidecar = Path(f"{target}.sha256")
    if sidecar.exists() or sidecar.is_symlink():
        raise CAError(f"refusing to overwrite digest sidecar: {sidecar}")
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    sidecar.chmod(0o444)
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise CAError("digest sidecar failed readback")
    return sidecar


def _validate_sidecar(path: Path, *, label: str) -> str:
    target = Path(path)
    sidecar = Path(f"{target}.sha256")
    if (
        target.is_symlink() or not target.is_file() or target.stat().st_mode & 0o222
        or sidecar.is_symlink() or not sidecar.is_file()
        or sidecar.stat().st_mode & 0o222
    ):
        raise CAError(f"{label} is not sealed read-only with matching .sha256 sidecar")
    digest = file_sha256(target)
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise CAError(f"{label} is not sealed read-only with matching .sha256 sidecar")
    return digest


def sealed_contract_binding(path: Path = CONTRACT_PATH) -> dict[str, str]:
    target = Path(path)
    digest = _validate_sidecar(target, label="C-A contract")
    text = target.read_text(encoding="utf-8")
    if (
        "UNSEALED" in text or "NO_LAUNCH" in text
        or "<<BIND_AT_FREEZE:" in text
        or "ASTRA_CANDIDATE_A=DRAFTED" in text
    ):
        raise CAError("C-A contract is not sealed: draft markers remain")
    return {"path": str(target.resolve()), "sha256": digest}


@dataclass(frozen=True, order=True)
class UnitKey:
    world: int
    lineage: int

    @classmethod
    def parse(cls, value: str) -> "UnitKey":
        try:
            world, lineage = value.split(":", 1)
            result = cls(int(world), int(lineage))
        except (AttributeError, TypeError, ValueError) as error:
            raise CAError("unit must be WORLD:LINEAGE") from error
        result.verify()
        return result

    def verify(self) -> None:
        if type(self.world) is not int or self.world not in WORLDS:
            raise CAError("unit world is outside the exact E1 panel")
        if type(self.lineage) is not int or self.lineage not in LINEAGES:
            raise CAError("unit lineage is outside the authenticated rung-003000 panel")

    @property
    def slug(self) -> str:
        self.verify()
        return f"{self.world}-{self.lineage}"

    def as_dict(self) -> dict[str, int]:
        self.verify()
        return {"world": self.world, "lineage": self.lineage}


ALL_UNITS = tuple(UnitKey(world, lineage) for world in WORLDS for lineage in LINEAGES)


def validate_step_indices(values: Sequence[int]) -> tuple[int, int]:
    result = tuple(values)
    if result != STEP_INDICES:
        raise CAError("C-A permits exactly steps 0 and 1")
    return STEP_INDICES


@dataclass(frozen=True)
class Proposal:
    origin: tuple[int, int]
    destination: tuple[int, int]
    members: tuple[int, ...]
    proposed_actions: tuple[int, ...]

    @property
    def profile_id(self) -> str:
        return (
            f"C:{self.origin[0]}:{self.origin[1]}"
            f"->{self.destination[0]}:{self.destination[1]}"
        )

    def payload(self) -> dict[str, object]:
        return {
            "proposal_id": self.profile_id,
            "origin_physical_key": list(self.origin),
            "destination_physical_key": list(self.destination),
            "members": list(self.members),
            "proposed_actions": list(self.proposed_actions),
            "member_count": len(self.members),
            "subset_profile_count": 1 << len(self.members),
        }


def _physical_key(value: object) -> tuple[int, int] | None:
    if value is None:
        return None
    if (
        not isinstance(value, (list, tuple)) or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise CAError("action physical key is malformed")
    return int(value[0]), int(value[1])


def build_proposal_catalog(
    base_actions: object,
    masks: object,
    action_physical_keys: Sequence[Sequence[object]],
    *,
    realised_keys: Sequence[tuple[int, int] | None] | None = None,
) -> tuple[Proposal, ...]:
    """Build the exact action-occupancy or realised-occupancy catalogue."""

    actions = np.asarray(base_actions)
    legal = np.asarray(masks)
    if actions.shape != (USERS,) or actions.dtype.kind not in "iu":
        raise CAError("BASE action vector is malformed")
    if legal.shape != (USERS, NUM_ACTIONS) or legal.dtype != np.bool_:
        raise CAError("catalogue legality surface is malformed")
    if len(action_physical_keys) != USERS:
        raise CAError("catalogue physical-key table has the wrong user count")
    if realised_keys is not None and len(realised_keys) != USERS:
        raise CAError("realised occupancy has the wrong user count")

    origins: dict[tuple[int, int], list[int]] = {}
    for user, raw_action in enumerate(actions.tolist()):
        action = int(raw_action)
        if action == NO_OP_ACTION:
            if bool(np.any(legal[user])):
                raise CAError("NOOP is legal only for an all-false mask")
            key = None
        else:
            if not 0 <= action < NUM_ACTIONS or not bool(legal[user, action]):
                raise CAError("BASE action is illegal")
            row = action_physical_keys[user]
            if len(row) != NUM_ACTIONS:
                raise CAError("physical-key row has the wrong action count")
            key = _physical_key(row[action])
            if key is None:
                raise CAError("legal BASE action lacks a physical key")
        occupancy_key = key if realised_keys is None else realised_keys[user]
        if occupancy_key is not None:
            occupancy_key = _physical_key(occupancy_key)
            assert occupancy_key is not None
            origins.setdefault(occupancy_key, []).append(user)

    proposals: list[Proposal] = []
    for origin in sorted(origins):
        members = tuple(origins[origin])
        maps: list[dict[tuple[int, int], int]] = []
        for user in members:
            mapping: dict[tuple[int, int], int] = {}
            row = action_physical_keys[user]
            for raw_action in np.flatnonzero(legal[user]).tolist():
                action = int(raw_action)
                key = _physical_key(row[action])
                if key is None:
                    continue
                if key in mapping:
                    raise CAError("duplicate legal physical alias in catalogue")
                mapping[key] = action
            maps.append(mapping)
        common = set(maps[0])
        for mapping in maps[1:]:
            common.intersection_update(mapping)
        common.discard(origin)
        for destination in sorted(common):
            proposals.append(
                Proposal(
                    origin=origin,
                    destination=destination,
                    members=members,
                    proposed_actions=tuple(mapping[destination] for mapping in maps),
                )
            )
    return tuple(proposals)


def catalogue_signature(catalogue: Sequence[Proposal]) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (row.origin, row.destination, row.members, row.proposed_actions)
        for row in catalogue
    )


def require_profile_count_within_cap(
    *, member_count: int, profile_count_cap: int
) -> int:
    if type(member_count) is not int or member_count < 0:
        raise CAError("proposal member count is malformed")
    if type(profile_count_cap) is not int or profile_count_cap < 1:
        raise CAError("profile-count cap must be a positive exact integer")
    count = 1 << member_count
    if count > profile_count_cap:
        raise CAIncomplete(
            "PROFILE_COUNT_EXCEEDED",
            f"PROFILE_COUNT_EXCEEDED: proposal needs {count} profiles, cap is {profile_count_cap}",
        )
    return count


def _fraction_from_number(value: int | float | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CAError("characteristic value is not numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise CAError("characteristic value is non-finite")
    return Fraction.from_float(converted)


def exact_shapley(
    characteristic: Mapping[frozenset[int], int | float | Fraction],
    members: Sequence[int],
) -> dict[int, Fraction]:
    """Enumerate the exact Shapley sum with rational combinatorial weights."""

    ordered = tuple(int(value) for value in members)
    if len(set(ordered)) != len(ordered) or tuple(sorted(ordered)) != ordered:
        raise CAError("Shapley members must be unique and sorted")
    m = len(ordered)
    expected = {
        frozenset(ordered[index] for index in range(m) if mask & (1 << index))
        for mask in range(1 << m)
    }
    if set(characteristic) != expected:
        raise CAError("characteristic function is not complete")
    values = {key: _fraction_from_number(value) for key, value in characteristic.items()}
    factorial = math.factorial
    result: dict[int, Fraction] = {}
    for member in ordered:
        total = Fraction(0)
        others = tuple(value for value in ordered if value != member)
        for mask in range(1 << len(others)):
            subset = frozenset(
                others[index] for index in range(len(others)) if mask & (1 << index)
            )
            weight = Fraction(
                factorial(len(subset)) * factorial(m - len(subset) - 1),
                factorial(m),
            )
            total += weight * (values[subset | {member}] - values[subset])
        result[member] = total
    if sum(result.values(), Fraction(0)) != values[frozenset(ordered)] - values[frozenset()]:
        raise CAError("exact Shapley allocation failed efficiency conservation")
    return result


def subtract_overlap(
    shapley: Mapping[int, Fraction], overlap: Mapping[int, int | float | Fraction]
) -> dict[int, Fraction]:
    if set(shapley) != set(overlap):
        raise CAError("overlap does not cover exactly the Shapley members")
    return {
        member: value - _fraction_from_number(overlap[member])
        for member, value in shapley.items()
    }


def _fraction_payload(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _fraction_from_payload(value: object, *, field: str) -> Fraction:
    if not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}:
        raise CAError(f"{field} exact rational is malformed")
    try:
        result = Fraction(int(str(value["numerator"])), int(str(value["denominator"])))
    except (ValueError, ZeroDivisionError) as error:
        raise CAError(f"{field} exact rational is malformed") from error
    if _fraction_payload(result) != dict(value):
        raise CAError(f"{field} exact rational is not canonical")
    return result


def _encode_float_surface(value: object, *, dtype: np.dtype[Any]) -> list[list[str]]:
    array = np.asarray(value, dtype=dtype)
    if array.shape != (USERS, NUM_ACTIONS) or not np.all(np.isfinite(array)):
        raise CAError("numeric surface is malformed")
    return [[float(item).hex() for item in row] for row in array.tolist()]


def _decode_float_surface(value: object, *, dtype: np.dtype[Any], field: str) -> np.ndarray:
    if not isinstance(value, list) or len(value) != USERS:
        raise CAError(f"{field} surface is malformed")
    try:
        decoded = np.asarray(
            [[float.fromhex(str(item)) for item in row] for row in value], dtype=dtype
        )
    except (TypeError, ValueError) as error:
        raise CAError(f"{field} surface is malformed") from error
    if decoded.shape != (USERS, NUM_ACTIONS) or not np.all(np.isfinite(decoded)):
        raise CAError(f"{field} surface is malformed")
    if _encode_float_surface(decoded, dtype=dtype) != value:
        raise CAError(f"{field} surface is not canonical")
    return decoded


def select_deployed_actions(
    q12_float32: object,
    masks: object,
    z_bits: object,
    kappa_bits: float = KAPPA_BITS,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply float64(float32(Q1+Q2)) + z/kappa and lowest-index ties."""

    q12 = np.asarray(q12_float32)
    legal = np.asarray(masks)
    z = np.asarray(z_bits)
    if q12.ndim != 2 or q12.dtype != np.dtype(np.float32):
        raise CAError("Q1+Q2 must be a two-dimensional exact float32 surface")
    if legal.dtype != np.bool_ or legal.shape != q12.shape:
        raise CAError("composition legality mask is malformed")
    if z.shape != q12.shape or not np.issubdtype(z.dtype, np.floating):
        raise CAError("composition z surface is malformed")
    if (
        not np.all(np.isfinite(q12)) or not np.all(np.isfinite(z))
        or not math.isfinite(float(kappa_bits)) or float(kappa_bits) <= 0.0
    ):
        raise CAError("composition contains non-finite values or invalid kappa")
    composed = q12.astype(np.float64) + z.astype(np.float64) / float(kappa_bits)
    selected = np.full(q12.shape[0], NO_OP_ACTION, dtype=np.int64)
    eligible = np.any(legal, axis=1)
    selected[eligible] = np.argmax(
        np.where(legal[eligible], composed[eligible], -np.inf), axis=1
    )
    return selected, composed


@dataclass(frozen=True)
class PooledRow:
    bits: float
    energy_j: float
    served: int
    opportunities: int


def pool_exact(rows: Sequence[PooledRow]) -> dict[str, object]:
    if not rows:
        raise CAError("pool requires at least one anchor")
    total_bits = Fraction(0)
    total_energy = Fraction(0)
    served = 0
    opportunities = 0
    for row in rows:
        if (
            not math.isfinite(row.bits) or row.bits < 0.0
            or not math.isfinite(row.energy_j) or row.energy_j <= 0.0
            or type(row.served) is not int or type(row.opportunities) is not int
            or not 0 <= row.served <= row.opportunities
        ):
            raise CAError("pooled physical row is malformed")
        total_bits += Fraction.from_float(row.bits)
        total_energy += Fraction.from_float(row.energy_j)
        served += row.served
        opportunities += row.opportunities
    if opportunities <= 0:
        raise CAError("pooled opportunity denominator is empty")
    return {
        "total_bits_exact": total_bits,
        "total_energy_j_exact": total_energy,
        "eta_exact": total_bits / total_energy,
        "served": served,
        "opportunities": opportunities,
        "service_fraction_exact": Fraction(served, opportunities),
    }


def _pool_payload(pooled: Mapping[str, object]) -> dict[str, object]:
    return {
        "total_bits_exact": _fraction_payload(pooled["total_bits_exact"]),
        "total_energy_j_exact": _fraction_payload(pooled["total_energy_j_exact"]),
        "eta_exact": _fraction_payload(pooled["eta_exact"]),
        "eta_hex": float(pooled["eta_exact"]).hex(),
        "served": pooled["served"],
        "opportunities": pooled["opportunities"],
        "service_fraction_exact": _fraction_payload(pooled["service_fraction_exact"]),
        "service_fraction_hex": float(pooled["service_fraction_exact"]).hex(),
    }


def screen_decision(
    *,
    base_rows: Sequence[PooledRow],
    candidate_rows: Sequence[PooledRow],
    catalogue_agreement: bool,
    higher_order_exposure: bool,
    legal_physical_change: bool,
) -> dict[str, object]:
    base = pool_exact(base_rows)
    candidate = pool_exact(candidate_rows)
    if base["opportunities"] != candidate["opportunities"]:
        raise CAError("BASE and C-A opportunity denominators disagree")
    reasons: list[str] = []
    if candidate["eta_exact"] <= base["eta_exact"]:
        reasons.append("EE_NOT_IMPROVED")
    if candidate["service_fraction_exact"] < base["service_fraction_exact"] - SERVICE_MARGIN:
        reasons.append("SERVICE_FAILED")
    if not legal_physical_change:
        reasons.append("NO_ACTION_CHANGE")
    if not higher_order_exposure:
        reasons.append("NO_HIGHER_ORDER_EXPOSURE")
    if not catalogue_agreement:
        reasons.append("INTERFACE_CATALOG_MISMATCH")
    return {
        "decision": (
            "C_A_FAST_SCREEN_SUPPORT" if not reasons
            else "C_A_FAST_SCREEN_NO_SUPPORT"
        ),
        "reasons": reasons,
        "eta_A": _pool_payload(candidate),
        "eta_BASE": _pool_payload(base),
    }


def _immutable_file(path: Path, *, label: str) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o222:
        raise CAError(f"{label} is missing, symlinked, or writable")


def authenticate_e1_terminal(root: Path = E1_OUTPUT_ROOT) -> tuple[dict[str, Any], str]:
    """Authenticate the eligible E1 terminal and all listed immutable unit files."""

    output = Path(root)
    terminal_path = output / e1.DEFAULT_TERMINAL_RECEIPT_NAME
    _immutable_file(terminal_path, label="E1 terminal receipt")
    terminal = _load_json(terminal_path, field="E1 terminal receipt")
    if (
        terminal.get("schema") != e1.TERMINAL_RECEIPT_SCHEMA
        or terminal.get("status") != "COMPLETE"
        or terminal.get("integrity") is not True
        or not isinstance(terminal.get("outcome"), Mapping)
        or terminal["outcome"].get("joint") != "E1_JOINT_HEADROOM"
        or terminal.get("test_split_opened") is not False
        or terminal.get("episode_training") is not False
        or terminal.get("learner_update") is not False
        or terminal.get("efficacy_claim") is not False
    ):
        raise CAError("E1 terminal does not admit the C-A joint family")
    if terminal.get("lineage_authorities") != f2.lineage_authority_bindings():
        raise CAError("E1 terminal lineage authorities drifted")
    listed = terminal.get("unit_receipts")
    if not isinstance(listed, list) or len(listed) != len(ALL_UNITS):
        raise CAError("E1 terminal does not list exactly twelve units")
    return terminal, file_sha256(terminal_path)


def _e1_unit_paths(root: Path, key: UnitKey) -> tuple[Path, Path, Path]:
    directory = Path(root) / "units" / key.slug
    return (
        directory / e1.DEFAULT_TAPE_NAME,
        directory / e1.DEFAULT_TAPE_MANIFEST_NAME,
        directory / e1.DEFAULT_UNIT_RECEIPT_NAME,
    )


def load_authenticated_e1_tape(
    root: Path, key: UnitKey, terminal: Mapping[str, object]
) -> dict[str, Any]:
    tape_path, manifest_path, receipt_path = _e1_unit_paths(root, key)
    for path, label in (
        (tape_path, "E1 tape"), (manifest_path, "E1 tape manifest"),
        (receipt_path, "E1 unit receipt"),
    ):
        _immutable_file(path, label=f"{label} {key.slug}")
    listing = {
        (int(row["unit"]["world"]), int(row["unit"]["lineage"])): row
        for row in terminal["unit_receipts"]
        if isinstance(row, Mapping) and isinstance(row.get("unit"), Mapping)
    }
    listed = listing.get((key.world, key.lineage))
    if listed is None or listed.get("sha256") != file_sha256(receipt_path):
        raise CAError(f"E1 terminal/unit receipt mismatch for {key.slug}")
    receipt = _load_json(receipt_path, field=f"E1 unit receipt {key.slug}")
    manifest = _load_json(manifest_path, field=f"E1 tape manifest {key.slug}")
    tape_sha = file_sha256(tape_path)
    if (
        receipt.get("status") != "COMPLETE" or receipt.get("integrity") is not True
        or receipt.get("tape_sha256") != tape_sha
        or not isinstance(manifest.get("tape"), Mapping)
        or manifest["tape"].get("sha256") != tape_sha
        or manifest["tape"].get("bytes") != tape_path.stat().st_size
        or manifest["tape"].get("mode") != "0444"
    ):
        raise CAError(f"E1 immutable unit bundle failed authentication for {key.slug}")
    tape = _load_json(tape_path, field=f"E1 tape {key.slug}")
    if (
        tape.get("schema") != e1.UNIT_TAPE_SCHEMA
        or tape.get("status") != "COMPLETE_IMMUTABLE_TAPE"
        or tape.get("unit", {}).get("world") != key.world
        or tape.get("unit", {}).get("lineage") != key.lineage
        or receipt.get("preflight_manifest_sha256")
        != terminal.get("preflight_manifest_sha256")
        or tape.get("preflight_manifest_sha256")
        != terminal.get("preflight_manifest_sha256")
    ):
        raise CAError(f"E1 tape identity/provenance drifted for {key.slug}")
    steps = tape.get("steps")
    if not isinstance(steps, list) or [row.get("step_index") for row in steps] != list(range(10)):
        raise CAError("E1 tape does not contain canonical steps 0..9")
    return tape


def _realised_keys_from_profile(profile: f1.PhysicalProfile) -> tuple[tuple[int, int] | None, ...]:
    return tuple(
        (int(profile.serving_satellite[user]), int(profile.serving_cell[user]))
        if bool(profile.served[user]) else None
        for user in range(profile.users)
    )


def estimate_from_e1(root: Path = E1_OUTPUT_ROOT) -> dict[str, object]:
    terminal, terminal_sha = authenticate_e1_terminal(root)
    anchors: list[dict[str, object]] = []
    proposal_total = member_total = subset_total = 0
    maximum_members = 0
    mismatch_anchors = 0
    for key in ALL_UNITS:
        tape = load_authenticated_e1_tape(root, key, terminal)
        for step in tape["steps"][:2]:
            masks = np.asarray(step["action_masks"], dtype=np.bool_)
            actions = np.asarray(step["reference_actions"], dtype=np.int64)
            keys = step["action_physical_keys"]
            base = f1.profile_from_payload(step["reference_profile"])
            action_catalogue = build_proposal_catalog(actions, masks, keys)
            realised_catalogue = build_proposal_catalog(
                actions, masks, keys, realised_keys=_realised_keys_from_profile(base)
            )
            proposals = len(action_catalogue)
            members = sum(len(row.members) for row in action_catalogue)
            subsets = sum(1 << len(row.members) for row in action_catalogue)
            max_members = max((len(row.members) for row in action_catalogue), default=0)
            agreement = catalogue_signature(action_catalogue) == catalogue_signature(realised_catalogue)
            anchors.append({
                "anchor": f"{key.world}:{key.lineage}:{step['step_index']}",
                "proposals": proposals,
                "proposal_member_rows": members,
                "subset_profiles": subsets,
                "ops3_offset_profile_evaluations": subsets * 3,
                "max_members": max_members,
                "catalogue_agreement": agreement,
            })
            proposal_total += proposals
            member_total += members
            subset_total += subsets
            maximum_members = max(maximum_members, max_members)
            mismatch_anchors += int(not agreement)
    ops3_evaluations = subset_total * 3
    current_evaluations = subset_total
    c1_overlap_evaluations = member_total * 2
    total_evaluations = (
        current_evaluations + ops3_evaluations + c1_overlap_evaluations
    )
    seconds_per_profile = F1_SECONDS_PER_UNIT_TWO_STEPS / F1_PROFILES_PER_UNIT_TWO_STEPS
    worker_seconds = total_evaluations * seconds_per_profile
    return {
        "schema": f"{SCHEMA}-estimate",
        "e1_terminal": {"path": str((Path(root) / e1.DEFAULT_TERMINAL_RECEIPT_NAME).resolve()), "sha256": terminal_sha},
        "cost_basis": {
            "seconds_per_world_lineage_two_steps": 383,
            "profiles_per_world_lineage_two_steps": 2700,
            "seconds_per_profile_exact": _fraction_payload(seconds_per_profile),
        },
        "anchors": anchors,
        "totals": {
            "anchors": len(anchors),
            "proposals": proposal_total,
            "proposal_member_rows": member_total,
            "subset_profiles": subset_total,
            "current_profile_evaluations": current_evaluations,
            "c1_overlap_profile_evaluations": c1_overlap_evaluations,
            "ops3_offset_profile_evaluations": ops3_evaluations,
            "complete_profile_evaluations": total_evaluations,
            "maximum_members": maximum_members,
            "largest_per_proposal_profile_count": 1 << maximum_members,
            "catalogue_mismatch_anchors": mismatch_anchors,
            "projected_worker_seconds_exact": _fraction_payload(worker_seconds),
            "projected_worker_hours": float(worker_seconds / 3600),
        },
    }


def _source_sha256(callable_value: Callable[..., object]) -> str:
    return hashlib.sha256(inspect.getsource(callable_value).encode("utf-8")).hexdigest()


def panel_bindings(profile_count_cap: int) -> dict[str, object]:
    if type(profile_count_cap) is not int or profile_count_cap < 1:
        raise CAError("profile-count cap must be a positive exact integer")
    return {
        "worlds": list(WORLDS),
        "lineages": list(LINEAGES),
        "steps": list(STEP_INDICES),
        "unit_count": len(ALL_UNITS),
        "users": USERS,
        "split": f1.SPLIT,
        "field_component": f1.FIELD_COMPONENT,
        "base_rule": "MASKED_ARGMAX_FLOAT32_Q1_PLUS_Q2",
        "catalogue_rule": "DETACHED_BASE_ACTION_KEY_OCCUPANCY_ALL_COMMON_LEGAL_DESTINATIONS",
        "interface_comparator": "E1_REALISED_SERVED_OCCUPANCY_CATALOGUE_EXACT_MEMBERSHIP",
        "coalition_rule": "EVERY_SUBSET_COMPLETE_JOINT_PROFILE_NO_SAMPLING",
        "allocation": "EXACT_SHAPLEY_MINUS_DECLARED_C1_C2_OVERLAP",
        "deployment": "MASKED_ARGMAX_FLOAT64_OF_FLOAT32_Q12_PLUS_Z_OVER_KAPPA_LOWEST_INDEX_TIES",
        "profile_count_cap": profile_count_cap,
        "budget_worker_seconds_hex": DEFAULT_BUDGET_WORKER_SECONDS.hex(),
        "lambda_bits_per_j_hex": LAMBDA_BITS_PER_J.hex(),
        "kappa_bits_hex": KAPPA_BITS.hex(),
        "interval_s_hex": INTERVAL_S.hex(),
        "ops3_horizon": OPS3_HORIZON,
        "service_margin": _fraction_payload(SERVICE_MARGIN),
        "base_advancement": "COMMIT_ONLY_BASE_BETWEEN_ANCHORS",
    }


def formula_digests() -> dict[str, str]:
    return {
        "proposal_catalogue_source_sha256": _source_sha256(build_proposal_catalog),
        "exact_shapley_source_sha256": _source_sha256(exact_shapley),
        "overlap_source_sha256": _source_sha256(subtract_overlap),
        "composition_source_sha256": _source_sha256(select_deployed_actions),
        "pooling_source_sha256": _source_sha256(pool_exact),
        "decision_source_sha256": _source_sha256(screen_decision),
    }


def _repo_relative(path: Path) -> str:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(REPO.resolve()):
        raise CAError(f"code binding escapes checkout: {path}")
    return resolved.relative_to(REPO.resolve()).as_posix()


def validate_output_root(path: Path) -> Path:
    """Reject every protected input tree and every non-owned repo directory."""

    target = Path(path)
    if not target.is_absolute() or target.is_symlink():
        raise CAError("output root must be an absolute non-symlink path")
    resolved = target.resolve()
    owned = HERE.resolve()
    if not resolved.is_relative_to(owned):
        raise CAError("output root must stay inside the owned C-A directory")
    return resolved


def expected_code_bindings() -> list[dict[str, str]]:
    paths = [
        ("ca_runner", HERE / "run_v023_c3_candidate_ca.py"),
        ("ca_preflight_builder", HERE / "build_ca_preflight_manifest.py"),
        ("ca_launch_authority_builder", HERE / "build_ca_launch_authority.py"),
        ("ca_tests", HERE / "test_candidate_ca.py"),
        ("ca_readme", HERE / "README.md"),
        ("e1_joint_catalog_import", E1_DIR / "run_v023_c3_existence_e1.py"),
        ("f1_tape_anchor_import", F1_DIR / "run_v023_c3_contingency_f1.py"),
        ("f2_lineage_authority_import", F2_DIR / "run_v023_c3_contingency_f2.py"),
        ("ops3_live_projection", REPO / "src/mcrl/runtime/ee_axis_ops3_live.py"),
        ("ops3_formula", REPO / "src/mcrl/runtime/ee_axis_ops3.py"),
        ("c1_opening_source", REPO / "src/mcrl/runtime/ee_axis_opening_source.py"),
        ("evaluation_neutrality", REPO / "src/mcrl/runtime/ee_axis_v04_c3_opening_source.py"),
        ("joint_action_evaluator", REPO / "src/mcrl/env/step.py"),
        ("canonical_power", REPO / "src/mcrl/env/link_budget.py"),
        ("canonical_interference", REPO / "src/mcrl/env/interference.py"),
    ]
    return [
        {"role": role, "path": _repo_relative(path), "sha256": file_sha256(path)}
        for role, path in paths
    ]


def static_bindings(profile_count_cap: int) -> dict[str, object]:
    contract = sealed_contract_binding()
    terminal, terminal_sha = authenticate_e1_terminal(E1_OUTPUT_ROOT)
    if tuple(WORLDS) != tuple(e1.WORLDS) or tuple(LINEAGES) != tuple(f2.LINEAGES):
        raise CAError("E1/F2 panel imports drifted")
    validate_step_indices(STEP_INDICES)
    if USERS != f1.USERS or INTERVAL_S != OPS3_INTERVAL_S:
        raise CAError("user count or native interval drifted")
    if LAMBDA_BITS_PER_J != f1.LAMBDA_BITS_PER_J or KAPPA_BITS != f1.KAPPA_BITS:
        raise CAError("declared lambda/kappa disagree with the authenticated F1 source")
    try:
        frozen = e1.prereg_tle_bindings()
    except e1.E1Error as error:
        raise CAError(str(error)) from error
    return {
        "bindings": panel_bindings(profile_count_cap),
        "contract": contract,
        "controller_review": {
            "path": str(CONTROLLER_REVIEW_PATH.resolve()),
            "sha256": file_sha256(CONTROLLER_REVIEW_PATH),
        },
        "e1_terminal_receipt": {
            "path": str(E1_TERMINAL.resolve()),
            "sha256": terminal_sha,
            "status": terminal["status"],
            "eligible_joint_outcome": terminal["outcome"]["joint"],
        },
        "lineage_authorities": f2.lineage_authority_bindings(),
        "preregistration": frozen["preregistration"],
        "tle_archive": frozen["tle_archive"],
        "formula_digests": formula_digests(),
        "process_environment": e1.process_bindings(),
    }


def validate_preflight_manifest(path: Path, *, profile_count_cap: int) -> tuple[dict[str, Any], str]:
    target = Path(path)
    payload = _load_json(target, field="C-A preflight manifest")
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": CLAIM_CEILING,
        **static_bindings(profile_count_cap),
        "code_files": expected_code_bindings(),
    }
    if payload != expected:
        raise CAError("C-A preflight manifest disagrees with current exact bindings/code")
    digest = _validate_sidecar(target, label="C-A preflight manifest")
    return payload, digest


def validate_launch_authority(
    path: Path,
    *,
    preflight_path: Path,
    preflight_sha256: str,
    profile_count_cap: int,
    output_root: Path | None = None,
    tle_root: Path | None = None,
    launch_arguments: Sequence[str] | None = None,
) -> dict[str, Any]:
    target = Path(path)
    payload = _load_json(target, field="C-A launch authority")
    _validate_sidecar(target, label="C-A launch authority")
    frozen = static_bindings(profile_count_cap)
    expected_keys = {
        "schema", "status", "claim_ceiling", "preflight_manifest", "contract",
        "controller_review", "e1_terminal_receipt", "bindings", "checkout_root", "output_root",
        "tle_root", "preregistration", "tle_archive", "lineage_authorities",
        "formula_digests", "launch_arguments", "test_split_opened",
        "episode_training", "learner_update", "efficacy_claim",
    }
    if set(payload) != expected_keys:
        raise CAError("C-A launch authority keys drifted")
    bound_output = payload.get("output_root")
    if not isinstance(bound_output, str) or not Path(bound_output).is_absolute():
        raise CAError("launch authority output root must be absolute")
    validate_output_root(Path(bound_output))
    expected = {
        "schema": LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": CLAIM_CEILING,
        "preflight_manifest": {"path": str(Path(preflight_path).resolve()), "sha256": preflight_sha256},
        "contract": frozen["contract"],
        "controller_review": frozen["controller_review"],
        "e1_terminal_receipt": frozen["e1_terminal_receipt"],
        "bindings": frozen["bindings"],
        "checkout_root": str(REPO.resolve()),
        "output_root": str(Path(bound_output).resolve()),
        "tle_root": str(CANONICAL_TLE_ROOT),
        "preregistration": frozen["preregistration"],
        "tle_archive": frozen["tle_archive"],
        "lineage_authorities": frozen["lineage_authorities"],
        "formula_digests": frozen["formula_digests"],
        "launch_arguments": list(payload.get("launch_arguments", [])),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    if payload != expected:
        raise CAError("C-A launch authority does not bind the exact sealed inputs")
    if output_root is not None and (
        str(validate_output_root(Path(output_root))) != expected["output_root"]
    ):
        raise CAError("runtime output root differs from launch authority")
    if tle_root is not None and (Path(tle_root) != CANONICAL_TLE_ROOT or Path(tle_root).is_symlink()):
        raise CAError("runtime TLE root differs from canonical frozen TLE root")
    if launch_arguments is not None and list(launch_arguments) != expected["launch_arguments"]:
        raise CAError("runtime argv differs from launch authority")
    return payload


@dataclass(frozen=True)
class AnchorCapture:
    native: Any
    q12: np.ndarray
    base_actions: np.ndarray
    q1_reference: np.ndarray
    masks: np.ndarray
    ops3_anchor: OPS3AnchorSnapshot
    ops3_projection: OPS3ProjectionReceipt
    ops3_surfaces: tuple[Any, ...]


def _capture_anchor(physical: Any, frozen: Any, step_env: Any, observation: Any) -> AnchorCapture:
    """Capture Q1/Q2 plus the one detached OPS-3 projection used by C-A."""

    from mcrl.runtime.ee_axis_state import encode_ee_axis_state
    from mcrl.runtime.ee_axis_v014_q2_state import encode_ee_axis_v014_q2_states

    native = encode_ee_axis_state(step_env, observation)
    native.verify()
    masks = np.asarray(native.action_masks, dtype=np.bool_)
    eligible = np.any(masks, axis=1)
    q1 = f1._network_surface_allow_empty(
        physical, frozen.q1, native.state_matrix, masks, field="Q1"
    )
    q1_reference = e1._masked_first_argmax(q1, masks)
    anchor = snapshot_ops3_anchor(step_env, observation)
    projection = project_ops3_anchor(anchor)
    surfaces = build_ops3_live_surfaces(anchor, projection, q1_reference)
    q2 = np.zeros(masks.shape, dtype=np.float64)
    if np.any(eligible):
        q2_state = encode_ee_axis_v014_q2_states(
            tuple(surface for user, surface in enumerate(surfaces) if bool(eligible[user]))
        )
        q2_state.verify()
        if not np.array_equal(q2_state.action_masks, masks[eligible]):
            raise CAError("Q2 carrier mask differs from the native mask")
        q2[eligible] = physical._surface(
            frozen.q2, q2_state.state_matrix, q2_state.action_masks, field="Q2"
        )
    q12 = np.asarray(
        np.asarray(q1, dtype=np.float32) + np.asarray(q2, dtype=np.float32),
        dtype=np.float32,
    )
    base = e1._base_argmax(q12, masks)
    return AnchorCapture(
        native=native,
        q12=q12,
        base_actions=base,
        q1_reference=np.asarray(q1_reference, dtype=np.int64),
        masks=masks,
        ops3_anchor=anchor,
        ops3_projection=projection,
        ops3_surfaces=tuple(surfaces),
    )


def repriced_y2_targets(
    surfaces: Sequence[Any],
    masks: np.ndarray,
    q1_reference: np.ndarray,
) -> np.ndarray:
    """Rebuild the unchanged repriced OPS-3 normalized C2 target."""

    if len(surfaces) != USERS or masks.shape != (USERS, NUM_ACTIONS):
        raise CAError("OPS-3 target carrier shape drifted")
    targets = np.zeros((USERS, NUM_ACTIONS), dtype=np.float64)
    for user, surface in enumerate(surfaces):
        horizon = int(surface.horizon)
        if horizon < 0 or horizon > OPS3_HORIZON:
            raise CAError("OPS-3 surface horizon drifted")
        legal = np.asarray(surface.legal_mask, dtype=np.bool_)
        if not np.array_equal(legal, masks[user]):
            raise CAError("OPS-3 target mask drifted")
        reference = int(q1_reference[user])
        if horizon == 0 or reference == NO_OP_ACTION:
            continue
        chi = np.asarray(surface.persistence, dtype=np.float64)[:horizon]
        rate = np.asarray(surface.rate_bps, dtype=np.float64)[:horizon]
        power = np.asarray(surface.marginal_power_w, dtype=np.float64)[:horizon]
        terms = (
            chi * INTERVAL_S * (rate - LAMBDA_BITS_PER_J * power)
            - (1.0 - chi) * KAPPA_BITS
        )
        raw = np.mean(terms, axis=0, dtype=np.float64)
        normalized = (raw - raw[reference]) / KAPPA_BITS
        targets[user] = np.where(legal, normalized, 0.0)
        if targets[user, reference] != 0.0:
            raise CAError("authenticated repriced C2 reference is not exact zero")
    if not np.all(np.isfinite(targets)):
        raise CAError("repriced C2 target contains non-finite values")
    return targets


def _ops3_surface_payloads(surfaces: Sequence[Any]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for surface in surfaces:
        horizon = int(surface.horizon)
        legal = np.asarray(surface.legal_mask, dtype=np.bool_)
        persistence = np.asarray(surface.persistence, dtype=np.bool_)[:horizon]
        rate = np.asarray(surface.rate_bps, dtype=np.float64)[:horizon]
        power = np.asarray(surface.marginal_power_w, dtype=np.float64)[:horizon]
        if legal.shape != (NUM_ACTIONS,) or any(
            array.shape != (horizon, NUM_ACTIONS)
            for array in (persistence, rate, power)
        ):
            raise CAError("OPS-3 C2 source carrier is malformed")
        rows.append({
            "horizon": horizon,
            "legal_mask": legal.tolist(),
            "persistence": persistence.tolist(),
            "rate_bps_hex": [[float(value).hex() for value in row] for row in rate.tolist()],
            "marginal_power_w_hex": [[float(value).hex() for value in row] for row in power.tolist()],
        })
    if len(rows) != USERS:
        raise CAError("OPS-3 C2 source carrier has wrong user count")
    return rows


def _ops3_surfaces_from_payload(value: object) -> tuple[Any, ...]:
    if not isinstance(value, list) or len(value) != USERS:
        raise CAError("OPS-3 C2 source carrier is malformed")
    surfaces = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != {
            "horizon", "legal_mask", "persistence", "rate_bps_hex",
            "marginal_power_w_hex",
        }:
            raise CAError("OPS-3 C2 source carrier row is malformed")
        horizon = row["horizon"]
        if type(horizon) is not int or horizon != OPS3_HORIZON:
            raise CAError("OPS-3 C2 source horizon drifted")
        try:
            legal = np.asarray(row["legal_mask"], dtype=np.bool_)
            persistence = np.asarray(row["persistence"], dtype=np.bool_)
            rate = np.asarray(
                [[float.fromhex(str(item)) for item in values] for values in row["rate_bps_hex"]],
                dtype=np.float64,
            )
            power = np.asarray(
                [[float.fromhex(str(item)) for item in values] for values in row["marginal_power_w_hex"]],
                dtype=np.float64,
            )
        except (TypeError, ValueError) as error:
            raise CAError("OPS-3 C2 source carrier values are malformed") from error
        if (
            legal.shape != (NUM_ACTIONS,)
            or persistence.shape != (horizon, NUM_ACTIONS)
            or rate.shape != (horizon, NUM_ACTIONS)
            or power.shape != (horizon, NUM_ACTIONS)
            or not np.all(np.isfinite(rate)) or not np.all(np.isfinite(power))
        ):
            raise CAError("OPS-3 C2 source carrier values are malformed")
        surfaces.append(SimpleNamespace(
            horizon=horizon, legal_mask=legal, persistence=persistence,
            rate_bps=rate, marginal_power_w=power,
        ))
    if _ops3_surface_payloads(surfaces) != value:
        raise CAError("OPS-3 C2 source carrier is not canonical")
    return tuple(surfaces)


def _projected_satellite_positions(
    anchor: OPS3AnchorSnapshot, projection: OPS3ProjectionReceipt
) -> tuple[dict[int, np.ndarray], ...]:
    if projection.horizon == 0:
        return ()
    satellites = SatelliteSet(anchor._satellite_records)
    if not np.array_equal(satellites.norad_ids, anchor.tracked_norad_ids):
        raise CAError("projected satellite identity universe drifted")
    first = projection.offset_times_utc[0]
    jd, fr = step_times(first, projection.horizon, time_step_s=anchor.decision_step_s)
    positions = satellites.propagate_ecef(jd, fr, require_all_healthy=False)
    expected = (anchor.tracked_norad_ids.size, projection.horizon, 3)
    if positions.shape != expected or not np.all(np.isfinite(positions)):
        raise CAError("projected satellite positions are malformed")
    result = []
    for offset in range(projection.horizon):
        result.append({
            int(norad): np.asarray(positions[index, offset], dtype=np.float64)
            for index, norad in enumerate(anchor.tracked_norad_ids.tolist())
        })
    return tuple(result)


def _validate_complete_actions(
    actions: object, anchor: OPS3AnchorSnapshot
) -> np.ndarray:
    raw = np.asarray(actions)
    if raw.shape != (anchor.num_users,) or raw.dtype.kind not in "iu":
        raise CAError("complete joint profile action vector is malformed")
    result = np.asarray(raw, dtype=np.int64)
    for user, action in enumerate(result.tolist()):
        if bool(np.any(anchor.legal_mask[user])):
            if not 0 <= action < NUM_ACTIONS or not bool(anchor.legal_mask[user, action]):
                raise CAError("complete joint profile contains an illegal action")
        elif action != NO_OP_ACTION:
            raise CAError("all-false mask requires NOOP")
    return result


def evaluate_projected_profile(
    *,
    anchor: OPS3AnchorSnapshot,
    projection: OPS3ProjectionReceipt,
    satellite_positions: Sequence[Mapping[int, np.ndarray]],
    actions: object,
) -> dict[str, object]:
    """Evaluate one complete joint vector at all OPS-3 future offsets."""

    selected = _validate_complete_actions(actions, anchor)
    if projection.horizon != anchor.horizon or len(satellite_positions) != projection.horizon:
        raise CAError("joint projection horizon disagrees with OPS-3")
    active = np.zeros(anchor.num_users, dtype=np.bool_)
    opening_start = np.zeros(anchor.num_users, dtype=np.float64)
    opening_current = np.zeros(anchor.num_users, dtype=np.float64)
    for user, action in enumerate(selected.tolist()):
        if action != NO_OP_ACTION:
            opening_start[user] = float(anchor.segment_start_gain_linear[user, action])
            opening_current[user] = float(anchor.current_gain_linear[user, action])
            opening = opening_service_feasibility_surface(
                legal_mask=anchor.legal_mask[user],
                segment_start_gain_linear=anchor.segment_start_gain_linear[user],
                current_gain_linear=anchor.current_gain_linear[user],
                p0_w=SEGMENT_START_POWER_W,
                pmax_w=BEAM_POWER_MAX_W,
            )
            active[user] = bool(opening[action])

    offset_rows: list[dict[str, object]] = []
    persistence_offsets: list[dict[str, object]] = []
    a_terms: list[float] = []
    energy: list[float] = []
    for h in range(projection.horizon):
        required = np.zeros(anchor.num_users, dtype=np.float64)
        chosen_gain = np.zeros(anchor.num_users, dtype=np.float64)
        selected_d2 = np.zeros(anchor.num_users, dtype=np.bool_)
        selected_visible = np.zeros(anchor.num_users, dtype=np.bool_)
        norads = np.full(anchor.num_users, -1, dtype=np.int64)
        cells = np.full(anchor.num_users, -1, dtype=np.int64)
        for user, action in enumerate(selected.tolist()):
            if action == NO_OP_ACTION:
                active[user] = False
                continue
            offset = projection.offsets_by_user[user][h]
            gain = float(offset.projected_gain_linear[action])
            chosen_gain[user] = gain
            selected_d2[user] = bool(offset.d2_eligible[action])
            selected_visible[user] = bool(offset.cell_visible[action])
            norads[user] = int(anchor.candidate_norad_ids[user, action])
            cells[user] = int(anchor.candidate_cell_ids[user, action])
            if gain > 0.0:
                required[user] = float(recurrence_power_w(
                    anchor.segment_start_gain_linear[user, action], gain,
                    p0_w=SEGMENT_START_POWER_W,
                ))
            feasible = not bool(classify_link_power_feasibility(
                np.asarray([required[user]], dtype=np.float64),
                max_power_w=BEAM_POWER_MAX_W,
            )[0])
            active[user] &= (
                bool(offset.d2_eligible[action])
                and bool(offset.cell_visible[action])
                and gain > 0.0 and feasible
            )
        served = np.asarray(active, dtype=np.bool_)
        beam_keys = sorted({
            (int(norads[user]), int(cells[user]))
            for user in np.flatnonzero(served).tolist()
        })
        beam_index_by_key = {key: index for index, key in enumerate(beam_keys)}
        beam_index = np.asarray([
            beam_index_by_key[(int(norads[user]), int(cells[user]))]
            if bool(served[user]) else -1
            for user in range(anchor.num_users)
        ], dtype=np.int64)
        beam_power = beam_power_w(required, served, beam_index, len(beam_keys))
        positions = dict(satellite_positions[h])
        radiating = build_radiating_beams(
            beam_norad_ids=np.asarray([key[0] for key in beam_keys], dtype=np.int64),
            beam_cell_ids=np.asarray([key[1] for key in beam_keys], dtype=np.int64),
            beam_power_w=beam_power,
            satellite_ecef_by_norad=positions,
            grid=anchor._grid,
        )
        field = beam_field_at_users(
            user_ecef_km=anchor.user_ecef_km, radiating=radiating
        )
        fallback = anchor.user_ecef_km
        boresight = np.stack([
            positions[int(norads[user])] if bool(served[user]) else fallback[user]
            for user in range(anchor.num_users)
        ])
        terms = received_power_terms(
            field, radiating,
            user_ecef_km=anchor.user_ecef_km,
            boresight_satellite_ecef_km=boresight,
            boresight_norad_ids=np.where(served, norads, -1),
        )
        colors = np.where(served, anchor._grid.colors[np.maximum(cells, 0)], -1)
        interference = co_channel_interference(
            terms, radiating,
            wanted_norad_ids=np.where(served, norads, -1),
            wanted_cell_ids=np.where(served, cells, -1),
            wanted_colors=colors,
        )
        wanted = np.zeros(anchor.num_users, dtype=np.float64)
        for user in np.flatnonzero(served).tolist():
            column = int(beam_index[user])
            wanted[user] = (
                required[user] * chosen_gain[user]
                * field.path_gain[user, column]
                * field.fading_gain[user, column]
                * _RX_GAIN_MAX_LINEAR
            )
        sinr = np.where(
            served,
            wanted / (interference.total_w + anchor.noise_power_w),
            0.0,
        )
        loads = np.asarray([
            sum(1 for index in beam_index.tolist() if index == beam_index[user])
            if bool(served[user]) else 0
            for user in range(anchor.num_users)
        ], dtype=np.float64)
        rates = np.where(
            served,
            shannon_rate_bps(sinr, beam_load=loads, bandwidth_hz=anchor.beam_bandwidth_hz),
            0.0,
        )
        supply = supply_power_w(beam_power, pa_efficiency(beam_power))
        _, satellite_beam_counts = np.unique(
            np.asarray([key[0] for key in beam_keys], dtype=np.int64),
            return_counts=True,
        )
        power_w = system_power_w(supply, satellite_beam_counts.astype(np.float64))
        total_bits = INTERVAL_S * math.fsum(float(value) for value in rates)
        total_energy = INTERVAL_S * power_w
        lost = anchor.num_users - int(np.count_nonzero(served))
        a_value = total_bits - KAPPA_BITS * lost
        a_terms.append(a_value)
        energy.append(total_energy)
        offset_rows.append({
            "h": h + 1,
            "total_bits_hex": total_bits.hex(),
            "total_energy_j_hex": total_energy.hex(),
            "system_power_w_hex": power_w.hex(),
            "served": int(np.count_nonzero(served)),
            "service_loss": lost,
            "chi": served.tolist(),
            "chi_sha256": hashlib.sha256(np.ascontiguousarray(served).tobytes()).hexdigest(),
        })
        persistence_offsets.append({
            "h": h + 1,
            "projected_gain_linear_hex": [float(value).hex() for value in chosen_gain.tolist()],
            "d2_eligible": selected_d2.tolist(),
            "cell_visible": selected_visible.tolist(),
        })
    if projection.horizon == 0:
        a_value = 0.0
        energy_value = 0.0
    else:
        a_value = math.fsum(a_terms) / projection.horizon
        energy_value = math.fsum(energy) / projection.horizon
    return {
        "horizon": projection.horizon,
        "persistence_source": {
            "opening_segment_start_gain_linear_hex": [
                float(value).hex() for value in opening_start.tolist()
            ],
            "opening_current_gain_linear_hex": [
                float(value).hex() for value in opening_current.tolist()
            ],
            "offsets": persistence_offsets,
        },
        "A_bits_hex": a_value.hex(),
        "E_j_hex": energy_value.hex(),
        "offsets": offset_rows,
    }


def _current_profile_receipt(evaluation: Any) -> tuple[dict[str, object], f1.PhysicalProfile]:
    profile, link_power = f1.profile_from_evaluation(evaluation, interval_s=INTERVAL_S)
    payload = f1.profile_to_payload(profile, link_power_w=link_power)
    metrics = e1._profile_metrics(profile)
    return {
        "physical_profile_sha256": canonical_sha256(payload),
        "physical_profile": payload,
        "metrics": metrics,
        "f0_conservation": e1._conservation(profile),
    }, profile


def _proposal_from_e1_row(row: Mapping[str, object]) -> Proposal:
    origin = _physical_key(row.get("origin_physical_key"))
    destination = _physical_key(row.get("destination_physical_key"))
    if origin is None or destination is None:
        raise CAError("E1 realised catalogue row lacks physical identities")
    members = tuple(int(value) for value in row.get("origin_users", []))
    joint = np.asarray(row.get("candidate_joint_actions"), dtype=np.int64)
    if joint.shape != (USERS,):
        raise CAError("E1 realised catalogue joint action vector is malformed")
    return Proposal(
        origin=origin,
        destination=destination,
        members=members,
        proposed_actions=tuple(int(joint[user]) for user in members),
    )


def _proposal_from_payload(row: Mapping[str, object]) -> Proposal:
    origin = _physical_key(row.get("origin_physical_key"))
    destination = _physical_key(row.get("destination_physical_key"))
    try:
        members = tuple(int(value) for value in row.get("members", []))
        proposed = tuple(int(value) for value in row.get("proposed_actions", []))
    except (TypeError, ValueError) as error:
        raise CAError("proposal payload members/actions are malformed") from error
    if origin is None or destination is None or len(members) != len(proposed):
        raise CAError("proposal payload is malformed")
    proposal = Proposal(origin, destination, members, proposed)
    if dict(row) != proposal.payload():
        raise CAError("proposal payload is not canonical")
    return proposal


def _e1_realised_catalogue_receipt(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    result = []
    for row in rows:
        proposal = _proposal_from_e1_row(row)
        result.append({
            **proposal.payload(),
            "profile_id": row["profile_id"],
            "physical_profile_sha256": row["physical_profile_sha256"],
            "alias_of_profile_id": row["alias_of_profile_id"],
            "metrics": row["metrics"],
            "f0_conservation": row["f0_conservation"],
        })
    return result


def _subset_actions(base: np.ndarray, proposal: Proposal, mask: int) -> np.ndarray:
    actions = np.array(base, dtype=np.int64, copy=True)
    for index, (user, action) in enumerate(
        zip(proposal.members, proposal.proposed_actions, strict=True)
    ):
        if mask & (1 << index):
            actions[user] = action
    return actions


def _evaluate_proposal(
    *,
    proposal: Proposal,
    base_actions: np.ndarray,
    base_evaluation: Any,
    step_env: Any,
    rng: np.random.Generator,
    capture: AnchorCapture,
    satellite_positions: Sequence[Mapping[int, np.ndarray]],
    y2_targets: np.ndarray,
    profile_count_cap: int,
    observation: Any,
    native_state: Any,
    common_random_field: KeyedFadingField,
    opening_provenance: OpeningSourceProvenance,
) -> tuple[dict[str, object], dict[int, Fraction]]:
    count = require_profile_count_within_cap(
        member_count=len(proposal.members), profile_count_cap=profile_count_cap
    )
    subset_receipts: list[dict[str, object]] = []
    current_evaluations: dict[int, Any] = {}
    projected_values: dict[int, tuple[float, float]] = {}
    for mask in range(count):
        actions = _subset_actions(base_actions, proposal, mask)
        evaluation = e1._evaluate_actions_neutral(step_env, actions, rng)
        current_evaluations[mask] = evaluation
        current_receipt, _profile = _current_profile_receipt(evaluation)
        projected = evaluate_projected_profile(
            anchor=capture.ops3_anchor,
            projection=capture.ops3_projection,
            satellite_positions=satellite_positions,
            actions=actions,
        )
        a_value = float.fromhex(str(projected["A_bits_hex"]))
        energy_value = float.fromhex(str(projected["E_j_hex"]))
        projected_values[mask] = (a_value, energy_value)
        subset_receipts.append({
            "subset_mask": mask,
            "members": [
                proposal.members[index]
                for index in range(len(proposal.members)) if mask & (1 << index)
            ],
            "action_vector_sha256": hashlib.sha256(
                np.ascontiguousarray(actions, dtype=np.dtype("<i8")).tobytes()
            ).hexdigest(),
            "current_interval": current_receipt,
            "projection": projected,
        })
    a_empty, e_empty = projected_values[0]
    characteristic: dict[frozenset[int], float] = {}
    for mask, receipt in enumerate(subset_receipts):
        a_value, energy_value = projected_values[mask]
        value = (a_value - a_empty) - LAMBDA_BITS_PER_J * (energy_value - e_empty)
        receipt["V_bits_hex"] = value.hex()
        subset = frozenset(
            proposal.members[index]
            for index in range(len(proposal.members)) if mask & (1 << index)
        )
        characteristic[subset] = value
    shapley = exact_shapley(characteristic, proposal.members)
    overlap: dict[int, float] = {}
    overlap_receipts: dict[str, object] = {}
    base_energy = float(base_evaluation.system_power_w) * INTERVAL_S
    for index, (user, proposed_action) in enumerate(
        zip(proposal.members, proposal.proposed_actions, strict=True)
    ):
        singleton_actions = _subset_actions(base_actions, proposal, 1 << index)
        opening = produce_opening_comparison(
            step_env,
            observation=observation,
            state_observation=native_state,
            reference_actions=base_actions,
            candidate_actions=singleton_actions,
            focal_user=user,
            common_random_field=common_random_field,
            provenance=opening_provenance,
            rng=rng,
            lambda_bits_per_j=LAMBDA_BITS_PER_J,
            interval_s=INTERVAL_S,
        )
        raw = opening.raw_pair
        singleton = current_evaluations[1 << index]
        if (
            not np.array_equal(raw.reference_rates_bps, base_evaluation.link_rate_bps)
            or not np.array_equal(raw.candidate_rates_bps, singleton.link_rate_bps)
            or raw.reference_system_power_w != float(base_evaluation.system_power_w)
            or raw.candidate_system_power_w != float(singleton.system_power_w)
        ):
            raise CAError("C1 opening source disagrees with the matched subset evaluation")
        bits_delta = INTERVAL_S * (
            float(raw.candidate_rates_bps[user])
            - float(raw.reference_rates_bps[user])
        )
        energy_delta = raw.candidate_system_power_w * INTERVAL_S - base_energy
        y2_delta = (
            float(y2_targets[user, proposed_action])
            - float(y2_targets[user, int(base_actions[user])])
        )
        overlap[user] = bits_delta - LAMBDA_BITS_PER_J * energy_delta + KAPPA_BITS * y2_delta
        overlap_receipts[str(user)] = {
            "c1_opening_comparison_sha256": raw.comparison_sha256,
            "current_delivered_bits_delta_hex": bits_delta.hex(),
            "current_total_network_energy_delta_j_hex": energy_delta.hex(),
            "repriced_normalized_c2_delta_hex": y2_delta.hex(),
            "d12_bits_hex": overlap[user].hex(),
        }
    z = subtract_overlap(shapley, overlap)
    full_receipt = subset_receipts[-1]
    payload = {
        **proposal.payload(),
        "subset_receipts": subset_receipts,
        "full_adoption_receipt_sha256": canonical_sha256(full_receipt),
        "shapley_exact": {str(user): _fraction_payload(value) for user, value in shapley.items()},
        "overlap_d12_bits_hex": {str(user): overlap[user].hex() for user in proposal.members},
        "overlap_receipts": overlap_receipts,
        "z_exact": {str(user): _fraction_payload(value) for user, value in z.items()},
        "allocation_conservation": {
            "sum_phi_exact": _fraction_payload(sum(shapley.values(), Fraction(0))),
            "grand_minus_empty_exact": _fraction_payload(
                _fraction_from_number(characteristic[frozenset(proposal.members)])
                - _fraction_from_number(characteristic[frozenset()])
            ),
            "verified": True,
        },
    }
    return payload, z


def _decode_e1_q12(step: Mapping[str, object]) -> np.ndarray:
    try:
        return e1._decode_q12_surface(step["q1_q2_float32"])
    except e1.E1Error as error:
        raise CAError(str(error)) from error


def _profile_row_from_receipt(receipt: Mapping[str, object]) -> PooledRow:
    payload = receipt.get("physical_profile")
    if not isinstance(payload, Mapping):
        raise CAError("physical receipt lacks its serialized profile")
    if receipt.get("physical_profile_sha256") != canonical_sha256(payload):
        raise CAError("physical receipt profile digest drifted")
    try:
        profile = f1.profile_from_payload(payload)
    except CAIncomplete:
        raise
    except Exception as error:
        raise CAError("serialized physical profile is malformed") from error
    metrics = receipt["metrics"]
    if not isinstance(metrics, Mapping):
        raise CAError("physical receipt metrics are malformed")
    if metrics != e1._profile_metrics(profile):
        raise CAError("physical receipt metrics are not derived from its profile")
    if receipt.get("f0_conservation") != e1._conservation(profile):
        raise CAError("physical receipt conservation is not derived from its profile")
    if int(metrics.get("opportunities", -1)) != USERS:
        raise CAError("physical receipt does not contain exactly 100 opportunities")
    return PooledRow(
        bits=float.fromhex(str(metrics["total_bits"])),
        energy_j=float.fromhex(str(metrics["total_energy_j"])),
        served=int(metrics["served"]),
        opportunities=int(metrics["opportunities"]),
    )


def generate_unit_tape(
    *, key: UnitKey, profile_count_cap: int, preflight_sha256: str,
    preflight_path: Path, launch_authority_sha256: str,
    launch_authority_path: Path, e1_root: Path = E1_OUTPUT_ROOT
) -> dict[str, object]:
    """Reacquire one fresh world×lineage tape and commit BASE only."""

    key.verify()
    terminal, terminal_sha = authenticate_e1_terminal(e1_root)
    donor_tape = load_authenticated_e1_tape(e1_root, key, terminal)
    physical, server = f1._runtime_modules()
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    record = read_prereg(f1.PREREG_PATH)
    if record.digest != f1.PREREG_RECORD_DIGEST:
        raise CAError("TRAIN PREREG semantic digest changed")
    frozen = f2._load_frozen_heads(key.lineage)
    q1_before = physical._parameter_sha256(frozen.q1)
    q2_before = physical._parameter_sha256(frozen.q2)
    field = KeyedFadingField.from_components(f1.FIELD_COMPONENT, key.world)
    with tempfile.TemporaryDirectory(prefix=f"mcrl-v023-ca-{key.slug}-tle-") as temporary:
        archive = server._freeze_archive(
            record, CANONICAL_TLE_ROOT, Path(temporary) / "frozen", physical
        )
        environment = server._make_environment(archive)
        step_env = environment.environment
        if getattr(step_env, "_started", False):
            raise CAError("environment started before keyed field binding")
        step_env._fading_field = field
        rngs = tuple(_evaluation_rngs(key.world))
        if len(rngs) < 2:
            raise CAError("canonical RNG factory lacks environment/mobility streams")
        _states, _masks, observation = environment.reset(rngs[0], rngs[1])
        step_receipts: list[dict[str, object]] = []
        for step_index in STEP_INDICES:
            if int(observation.step_index) != step_index:
                raise CAError("fresh replay reached the wrong C-A step")
            donor_step = donor_tape["steps"][step_index]
            capture = _capture_anchor(physical, frozen, step_env, observation)
            base_actions = capture.base_actions
            key_table = f1.action_physical_keys(observation)
            if (
                not np.array_equal(capture.q12, _decode_e1_q12(donor_step))
                or not np.array_equal(capture.masks, np.asarray(donor_step["action_masks"], dtype=np.bool_))
                or base_actions.tolist() != donor_step["reference_actions"]
                or key_table != donor_step["action_physical_keys"]
                or capture.native.state_sha256 != donor_step["state_sha256"]
            ):
                raise CAError("fresh anchor disagrees with the authenticated E1 tape")
            base_evaluation = e1._evaluate_actions_neutral(step_env, base_actions, rngs[0])
            base_receipt, base_profile = _current_profile_receipt(base_evaluation)
            base_payload = f1.profile_to_payload(
                base_profile, link_power_w=np.asarray(base_evaluation.link_power_w, dtype=np.float64)
            )
            if base_payload != donor_step["reference_profile"]:
                raise CAError("fresh BASE profile disagrees with the authenticated E1 tape")

            action_catalogue = build_proposal_catalog(base_actions, capture.masks, key_table)
            realised_rows = e1.build_joint_witness_catalog(e1.JointWitnessAnchor(
                observation=observation,
                reference_actions=base_actions,
                reference_profile=base_profile,
                reference_link_power_w=np.asarray(base_evaluation.link_power_w, dtype=np.float64),
                step_env=step_env,
                rng=rngs[0],
                interval_s=INTERVAL_S,
            ))
            serialized_replay = [e1._serialize_profile_row(row) for row in realised_rows]
            if serialized_replay != donor_step["joint_witness_catalog"]:
                raise CAError("fresh E1 realised catalogue replay disagrees with its tape")
            realised_catalogue = tuple(_proposal_from_e1_row(row) for row in realised_rows)
            agreement = catalogue_signature(action_catalogue) == catalogue_signature(realised_catalogue)
            satellite_positions = _projected_satellite_positions(
                capture.ops3_anchor, capture.ops3_projection
            )
            y2_targets = repriced_y2_targets(
                capture.ops3_surfaces, capture.masks, capture.q1_reference
            )
            y2_source_carrier = _ops3_surface_payloads(capture.ops3_surfaces)
            checkpoint_sha = str(
                f2.lineage_authority_bindings()[LINEAGES.index(key.lineage)]
                ["checkpoint"]["sha256"]
            )
            opening_provenance = OpeningSourceProvenance(
                source_policy_version=1,
                anchor_sha256=capture.native.state_sha256,
                source_manifest_sha256=preflight_sha256,
                checkpoint_sha256=checkpoint_sha,
                common_random_field_sha256=field.root_digest,
                c1_source_rule="C_A_DECLARED_CURRENT_INTERVAL_C1_OVERLAP",
                c3_source_rule="C_A_EXACT_ACTION_SET_SHAPLEY_ORACLE",
                admitted_route="C1",
            )
            opening_provenance.verify()
            z_surface = np.zeros((USERS, NUM_ACTIONS), dtype=np.float64)
            assignment: dict[tuple[int, int], str] = {}
            proposal_receipts: list[dict[str, object]] = []
            full_adoption_receipts: list[dict[str, object]] = []
            first_full_profile: dict[str, str] = {
                str(base_receipt["physical_profile_sha256"]): "BASE"
            }
            for proposal in action_catalogue:
                proposal_receipt, proposal_z = _evaluate_proposal(
                    proposal=proposal,
                    base_actions=base_actions,
                    base_evaluation=base_evaluation,
                    step_env=step_env,
                    rng=rngs[0],
                    capture=capture,
                    satellite_positions=satellite_positions,
                    y2_targets=y2_targets,
                    profile_count_cap=profile_count_cap,
                    observation=observation,
                    native_state=capture.native,
                    common_random_field=field,
                    opening_provenance=opening_provenance,
                )
                full_profile_sha = str(
                    proposal_receipt["subset_receipts"][-1]["current_interval"]
                    ["physical_profile_sha256"]
                )
                proposal_receipt["alias_of_proposal_id"] = first_full_profile.get(
                    full_profile_sha
                )
                first_full_profile.setdefault(full_profile_sha, proposal.profile_id)
                proposal_receipts.append(proposal_receipt)
                full_adoption_receipts.append({
                    "proposal_id": proposal.profile_id,
                    "receipt_sha256": proposal_receipt["full_adoption_receipt_sha256"],
                })
                for user, action in zip(
                    proposal.members, proposal.proposed_actions, strict=True
                ):
                    cell = (user, action)
                    if cell in assignment:
                        raise CAError("a member action row belongs to multiple proposals")
                    assignment[cell] = proposal.profile_id
                    z_surface[user, action] = float(proposal_z[user])

            deployed, composed_surface = select_deployed_actions(
                capture.q12, capture.masks, z_surface
            )
            deployed_evaluation = e1._evaluate_actions_neutral(step_env, deployed, rngs[0])
            deployed_receipt, _deployed_profile = _current_profile_receipt(deployed_evaluation)
            physical_change_users = []
            for user, (left, right) in enumerate(
                zip(base_actions.tolist(), deployed.tolist(), strict=True)
            ):
                left_key = None if left == NO_OP_ACTION else _physical_key(key_table[user][left])
                right_key = None if right == NO_OP_ACTION else _physical_key(key_table[user][right])
                if left_key != right_key:
                    physical_change_users.append(user)
            partial_adoption_receipts: list[dict[str, object]] = []
            deployed_full_adoption: list[dict[str, object]] = []
            for proposal, receipt in zip(action_catalogue, proposal_receipts, strict=True):
                adopted = tuple(
                    user for user, action in zip(
                        proposal.members, proposal.proposed_actions, strict=True
                    ) if int(deployed[user]) == action
                )
                if not adopted:
                    continue
                mask = sum(
                    1 << index for index, user in enumerate(proposal.members)
                    if user in adopted
                )
                row = {
                    "proposal_id": proposal.profile_id,
                    "adopted_members": list(adopted),
                    "member_count": len(proposal.members),
                    "subset_mask": mask,
                    "subset_receipt_sha256": canonical_sha256(receipt["subset_receipts"][mask]),
                }
                if len(adopted) == len(proposal.members):
                    deployed_full_adoption.append(row)
                else:
                    partial_adoption_receipts.append(row)
            step_receipts.append({
                "step_index": step_index,
                "state_sha256": capture.native.state_sha256,
                "ops3": {
                    "anchor_sha256": capture.ops3_anchor.anchor_sha256,
                    "tracker_seed_sha256": capture.ops3_anchor.tracker_seed_sha256,
                    "projection_sha256": capture.ops3_projection.projection_sha256,
                    "horizon": capture.ops3_projection.horizon,
                    "q1_reference_actions": capture.q1_reference.tolist(),
                    "repriced_y2_source_carrier": y2_source_carrier,
                    "repriced_y2_source_carrier_sha256": canonical_sha256(y2_source_carrier),
                    "repriced_y2_targets_float64": _encode_float_surface(
                        y2_targets, dtype=np.dtype(np.float64)
                    ),
                    "repriced_y2_target_sha256": hashlib.sha256(
                        np.ascontiguousarray(y2_targets, dtype=np.dtype("<f8")).tobytes()
                    ).hexdigest(),
                },
                "base_actions": base_actions.tolist(),
                "deployed_actions": deployed.tolist(),
                "q1_q2_float32": _encode_float_surface(
                    capture.q12, dtype=np.dtype(np.float32)
                ),
                "action_masks": capture.masks.tolist(),
                "action_physical_keys": key_table,
                "z_bits_float64": _encode_float_surface(
                    z_surface, dtype=np.dtype(np.float64)
                ),
                "q12_float32_sha256": hashlib.sha256(
                    np.ascontiguousarray(capture.q12, dtype=np.dtype("<f4")).tobytes()
                ).hexdigest(),
                "z_bits_float64_sha256": hashlib.sha256(
                    np.ascontiguousarray(z_surface, dtype=np.dtype("<f8")).tobytes()
                ).hexdigest(),
                "composed_float64_sha256": hashlib.sha256(
                    np.ascontiguousarray(composed_surface, dtype=np.dtype("<f8")).tobytes()
                ).hexdigest(),
                "action_occupancy_catalogue": [row.payload() for row in action_catalogue],
                "realised_occupancy_catalogue": _e1_realised_catalogue_receipt(realised_rows),
                "catalogue_agreement": agreement,
                "higher_order_exposure": any(len(row.members) >= 3 for row in action_catalogue),
                "proposal_receipts": proposal_receipts,
                "full_adoption_receipts": full_adoption_receipts,
                "deployed_full_adoption_receipts": deployed_full_adoption,
                "partial_adoption_receipts": partial_adoption_receipts,
                "base_physical": base_receipt,
                "deployed_physical_once": deployed_receipt,
                "physical_change_users": physical_change_users,
            })
            if step_index == STEP_INDICES[0]:
                committed = environment.step(base_actions, rngs[0])
                committed_receipt, _ = _current_profile_receipt(committed)
                if committed_receipt != base_receipt:
                    raise CAError("committed BASE disagrees with evaluated BASE")
                if bool(committed.done):
                    raise CAError("fresh episode terminated before step 1")
                observation = committed.observation
    if (
        physical._parameter_sha256(frozen.q1) != q1_before
        or physical._parameter_sha256(frozen.q2) != q2_before
    ):
        raise CAError("frozen Q1/Q2 parameters changed during C-A inference")
    return {
        "schema": UNIT_TAPE_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "bindings": panel_bindings(profile_count_cap),
        "e1_terminal_receipt_sha256": terminal_sha,
        "preflight_manifest": {
            "path": str(Path(preflight_path).resolve()),
            "sha256": _digest(preflight_sha256, field="preflight manifest sha256"),
        },
        "launch_authority": {
            "path": str(Path(launch_authority_path).resolve()),
            "sha256": _digest(launch_authority_sha256, field="launch authority sha256"),
        },
        "lineage_authority": f2.lineage_authority_bindings()[LINEAGES.index(key.lineage)],
        "q1_parameter_sha256": q1_before,
        "q2_parameter_sha256": q2_before,
        "steps": step_receipts,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def verify_unit_tape(
    tape: Mapping[str, object], *, key: UnitKey, profile_count_cap: int
) -> dict[str, int]:
    key.verify()
    if (
        tape.get("schema") != UNIT_TAPE_SCHEMA
        or tape.get("status") != "COMPLETE_IMMUTABLE_TAPE"
        or tape.get("claim_ceiling") != CLAIM_CEILING
        or tape.get("unit") != key.as_dict()
        or tape.get("bindings") != panel_bindings(profile_count_cap)
        or tape.get("lineage_authority")
        != f2.lineage_authority_bindings()[LINEAGES.index(key.lineage)]
        or any(tape.get(field) is not False for field in (
            "test_split_opened", "episode_training", "learner_update", "efficacy_claim"
        ))
    ):
        raise CAError("C-A unit tape binding/status drifted")
    _digest(tape.get("e1_terminal_receipt_sha256"), field="E1 terminal sha256")
    for field in ("preflight_manifest", "launch_authority"):
        binding = tape.get(field)
        if (
            not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}
            or not isinstance(binding.get("path"), str) or not Path(binding["path"]).is_absolute()
        ):
            raise CAError(f"unit {field} binding is malformed")
        _digest(binding.get("sha256"), field=f"{field} sha256")
    _digest(tape.get("q1_parameter_sha256"), field="Q1 parameter sha256")
    _digest(tape.get("q2_parameter_sha256"), field="Q2 parameter sha256")
    steps = tape.get("steps")
    if (
        not isinstance(steps, list) or len(steps) != 2
        or [row.get("step_index") for row in steps if isinstance(row, Mapping)]
        != list(STEP_INDICES)
    ):
        raise CAError("C-A tape must contain exactly steps 0 and 1")
    proposals = subsets = partial = changes = 0
    for step in steps:
        if not isinstance(step, Mapping):
            raise CAError("C-A step receipt is malformed")
        action_catalogue = step.get("action_occupancy_catalogue")
        realised_catalogue = step.get("realised_occupancy_catalogue")
        proposal_receipts = step.get("proposal_receipts")
        if not all(isinstance(value, list) for value in (
            action_catalogue, realised_catalogue, proposal_receipts,
            step.get("full_adoption_receipts"),
            step.get("deployed_full_adoption_receipts"),
            step.get("partial_adoption_receipts"),
            step.get("physical_change_users"),
        )):
            raise CAError("C-A catalogue/adoption receipt is malformed")
        if len(action_catalogue) != len(proposal_receipts):
            raise CAError("proposal catalogue and receipt coverage disagree")
        ops3_receipt = step.get("ops3")
        if not isinstance(ops3_receipt, Mapping):
            raise CAError("OPS-3 anchor receipt is malformed")
        for field in (
            "anchor_sha256", "tracker_seed_sha256", "projection_sha256",
            "repriced_y2_source_carrier_sha256", "repriced_y2_target_sha256",
        ):
            _digest(ops3_receipt.get(field), field=f"OPS-3 {field}")
        if ops3_receipt.get("horizon") != OPS3_HORIZON:
            raise CAError("OPS-3 horizon is not H_p=min(3,T-1-t)=3 for steps 0/1")
        try:
            base_actions = np.asarray(step["base_actions"], dtype=np.int64)
            masks = np.asarray(step["action_masks"], dtype=np.bool_)
            key_table = step["action_physical_keys"]
        except (KeyError, TypeError, ValueError) as error:
            raise CAError("C-A action interface receipt is malformed") from error
        if base_actions.shape != (USERS,) or masks.shape != (USERS, NUM_ACTIONS):
            raise CAError("C-A action interface receipt has the wrong shape")
        base_physical = step.get("base_physical")
        if not isinstance(base_physical, Mapping):
            raise CAError("BASE physical receipt is malformed")
        _profile_row_from_receipt(base_physical)
        base_profile = f1.profile_from_payload(base_physical["physical_profile"])
        y2_targets = _decode_float_surface(
            ops3_receipt.get("repriced_y2_targets_float64"),
            dtype=np.dtype(np.float64), field="repriced Y2 target",
        )
        if hashlib.sha256(np.ascontiguousarray(y2_targets, dtype=np.dtype("<f8")).tobytes()).hexdigest() != ops3_receipt.get("repriced_y2_target_sha256"):
            raise CAError("repriced Y2 target digest drifted")
        q1_reference = np.asarray(ops3_receipt.get("q1_reference_actions"), dtype=np.int64)
        if q1_reference.shape != (USERS,):
            raise CAError("OPS-3 Q1 reference action vector is malformed")
        for user, action in enumerate(q1_reference.tolist()):
            if action == NO_OP_ACTION:
                if bool(np.any(masks[user])):
                    raise CAError("OPS-3 Q1 reference uses NOOP for an eligible user")
            elif not 0 <= action < NUM_ACTIONS or not bool(masks[user, action]) or y2_targets[user, action] != 0.0:
                raise CAError("repriced Y2 target does not use its authenticated Q1 reference")
        y2_source_carrier = ops3_receipt.get("repriced_y2_source_carrier")
        if canonical_sha256(y2_source_carrier) != ops3_receipt.get("repriced_y2_source_carrier_sha256"):
            raise CAError("repriced Y2 source carrier digest drifted")
        source_surfaces = _ops3_surfaces_from_payload(y2_source_carrier)
        if not np.array_equal(
            repriced_y2_targets(source_surfaces, masks, q1_reference), y2_targets
        ):
            raise CAError("repriced Y2 target is not derived from its OPS-3 source carrier")
        rebuilt = build_proposal_catalog(base_actions, masks, key_table)
        rebuilt_realised = build_proposal_catalog(
            base_actions, masks, key_table,
            realised_keys=_realised_keys_from_profile(base_profile),
        )
        parsed_action = tuple(
            _proposal_from_payload(row) if isinstance(row, Mapping) else None
            for row in action_catalogue
        )
        if any(row is None for row in parsed_action) or catalogue_signature(rebuilt) != catalogue_signature(parsed_action):
            raise CAError("action catalogue does not derive from its recorded BASE interface")
        parsed_realised: list[Proposal] = []
        for row in realised_catalogue:
            if not isinstance(row, Mapping):
                raise CAError("realised catalogue row is malformed")
            proposal_fields = {
                name: row.get(name) for name in (
                    "proposal_id", "origin_physical_key", "destination_physical_key",
                    "members", "proposed_actions", "member_count", "subset_profile_count",
                )
            }
            parsed_realised.append(_proposal_from_payload(proposal_fields))
            for digest_field in ("physical_profile_sha256",):
                _digest(row.get(digest_field), field=f"realised {digest_field}")
            if not isinstance(row.get("metrics"), Mapping):
                raise CAError("realised catalogue metrics are malformed")
        if catalogue_signature(rebuilt_realised) != catalogue_signature(parsed_realised):
            raise CAError("realised catalogue does not derive from retained BASE occupancy")
        agreement = catalogue_signature(parsed_action) == catalogue_signature(parsed_realised)
        if step.get("catalogue_agreement") is not agreement:
            raise CAError("catalogue agreement flag is not derived from recorded catalogues")
        higher_order = any(len(row.members) >= 3 for row in parsed_action)
        if step.get("higher_order_exposure") is not higher_order:
            raise CAError("higher-order exposure flag is not derived from the catalogue")

        q12 = _decode_float_surface(
            step.get("q1_q2_float32"), dtype=np.dtype(np.float32), field="Q1+Q2"
        )
        z_surface = _decode_float_surface(
            step.get("z_bits_float64"), dtype=np.dtype(np.float64), field="z"
        )
        if hashlib.sha256(np.ascontiguousarray(q12, dtype=np.dtype("<f4")).tobytes()).hexdigest() != step.get("q12_float32_sha256"):
            raise CAError("Q1+Q2 surface digest drifted")
        if not np.array_equal(base_actions, e1._base_argmax(q12, masks)):
            raise CAError("recorded BASE is not masked argmax(float32(Q1+Q2))")
        if hashlib.sha256(np.ascontiguousarray(z_surface, dtype=np.dtype("<f8")).tobytes()).hexdigest() != step.get("z_bits_float64_sha256"):
            raise CAError("z surface digest drifted")
        recomputed_z = np.zeros((USERS, NUM_ACTIONS), dtype=np.float64)
        assignment: set[tuple[int, int]] = set()
        expected_full: list[dict[str, object]] = []
        base_for_alias = step.get("base_physical")
        if not isinstance(base_for_alias, Mapping):
            raise CAError("BASE physical receipt is malformed")
        first_full_profile: dict[str, str] = {
            str(base_for_alias.get("physical_profile_sha256")): "BASE"
        }
        for proposal, receipt in zip(parsed_action, proposal_receipts, strict=True):
            if not isinstance(receipt, Mapping):
                raise CAError("proposal row is malformed")
            if any(receipt.get(name) != value for name, value in proposal.payload().items()):
                raise CAError("proposal receipt identity disagrees with its catalogue row")
            m = len(proposal.members)
            count = require_profile_count_within_cap(
                member_count=m, profile_count_cap=profile_count_cap
            )
            rows = receipt.get("subset_receipts")
            if not isinstance(rows, list) or len(rows) != count:
                raise CAError("proposal subset profile coverage is incomplete")
            if [row.get("subset_mask") for row in rows if isinstance(row, Mapping)] != list(range(count)):
                raise CAError("proposal subset masks are truncated or reordered")
            characteristic: dict[frozenset[int], float] = {}
            empty_a = empty_e = None
            for mask, subset_row in enumerate(rows):
                if not isinstance(subset_row, Mapping):
                    raise CAError("proposal subset row is malformed")
                actions = _subset_actions(base_actions, proposal, mask)
                action_sha = hashlib.sha256(
                    np.ascontiguousarray(actions, dtype=np.dtype("<i8")).tobytes()
                ).hexdigest()
                expected_members = [
                    proposal.members[index] for index in range(m) if mask & (1 << index)
                ]
                if subset_row.get("action_vector_sha256") != action_sha or subset_row.get("members") != expected_members:
                    raise CAError("proposal subset action identity drifted")
                current = subset_row.get("current_interval")
                projection = subset_row.get("projection")
                if not isinstance(current, Mapping) or not isinstance(projection, Mapping):
                    raise CAError("proposal subset physical receipt is malformed")
                _digest(current.get("physical_profile_sha256"), field="subset physical profile")
                _profile_row_from_receipt(current)
                try:
                    a_value = float.fromhex(str(projection["A_bits_hex"]))
                    e_value = float.fromhex(str(projection["E_j_hex"]))
                except (KeyError, ValueError) as error:
                    raise CAError("proposal projection value is malformed") from error
                if not math.isfinite(a_value) or not math.isfinite(e_value):
                    raise CAError("proposal projection value is non-finite")
                horizon = projection.get("horizon")
                offsets = projection.get("offsets")
                if horizon != ops3_receipt["horizon"] or not isinstance(offsets, list) or len(offsets) != horizon:
                    raise CAError("proposal projection horizon/offset coverage is malformed")
                persistence_source = projection.get("persistence_source")
                if not isinstance(persistence_source, Mapping) or set(persistence_source) != {
                    "opening_segment_start_gain_linear_hex",
                    "opening_current_gain_linear_hex", "offsets",
                }:
                    raise CAError("projection persistence source is malformed")
                try:
                    opening_start = np.asarray([
                        float.fromhex(str(value)) for value in
                        persistence_source["opening_segment_start_gain_linear_hex"]
                    ], dtype=np.float64)
                    opening_current = np.asarray([
                        float.fromhex(str(value)) for value in
                        persistence_source["opening_current_gain_linear_hex"]
                    ], dtype=np.float64)
                except (TypeError, ValueError) as error:
                    raise CAError("projection opening source is malformed") from error
                source_offsets = persistence_source["offsets"]
                if (
                    opening_start.shape != (USERS,) or opening_current.shape != (USERS,)
                    or not np.all(np.isfinite(opening_start))
                    or not np.all(np.isfinite(opening_current))
                    or np.any(opening_start < 0.0) or np.any(opening_current < 0.0)
                    or not isinstance(source_offsets, list) or len(source_offsets) != horizon
                ):
                    raise CAError("projection persistence source values are malformed")
                active = np.zeros(USERS, dtype=np.bool_)
                for user, action in enumerate(actions.tolist()):
                    if action == NO_OP_ACTION:
                        if opening_start[user] != 0.0 or opening_current[user] != 0.0:
                            raise CAError("NOOP projection opening source is nonzero")
                        continue
                    if opening_start[user] > 0.0 and opening_current[user] > 0.0:
                        required = float(recurrence_power_w(
                            opening_start[user], opening_current[user],
                            p0_w=SEGMENT_START_POWER_W,
                        ))
                        active[user] = not bool(classify_link_power_feasibility(
                            np.asarray([required], dtype=np.float64),
                            max_power_w=BEAM_POWER_MAX_W,
                        )[0])
                a_terms: list[float] = []
                energy_terms: list[float] = []
                for offset_index, offset in enumerate(offsets, start=1):
                    if not isinstance(offset, Mapping) or offset.get("h") != offset_index:
                        raise CAError("proposal projection offset ordering is malformed")
                    try:
                        offset_bits = float.fromhex(str(offset["total_bits_hex"]))
                        offset_energy = float.fromhex(str(offset["total_energy_j_hex"]))
                        offset_power = float.fromhex(str(offset["system_power_w_hex"]))
                        served = int(offset["served"])
                        lost = int(offset["service_loss"])
                    except (KeyError, TypeError, ValueError) as error:
                        raise CAError("proposal projection offset is malformed") from error
                    if (
                        not math.isfinite(offset_bits) or offset_bits < 0.0
                        or not math.isfinite(offset_energy) or offset_energy < 0.0
                        or not math.isfinite(offset_power) or offset_power < 0.0
                        or offset_energy != INTERVAL_S * offset_power
                        or served + lost != USERS or not 0 <= served <= USERS
                    ):
                        raise CAError("proposal projection offset metrics are invalid")
                    source_row = source_offsets[offset_index - 1]
                    if not isinstance(source_row, Mapping) or set(source_row) != {
                        "h", "projected_gain_linear_hex", "d2_eligible", "cell_visible",
                    } or source_row.get("h") != offset_index:
                        raise CAError("projection persistence offset source is malformed")
                    try:
                        projected_gain = np.asarray([
                            float.fromhex(str(value)) for value in source_row["projected_gain_linear_hex"]
                        ], dtype=np.float64)
                        d2 = np.asarray(source_row["d2_eligible"], dtype=np.bool_)
                        visible = np.asarray(source_row["cell_visible"], dtype=np.bool_)
                    except (TypeError, ValueError) as error:
                        raise CAError("projection persistence offset source is malformed") from error
                    if (
                        projected_gain.shape != (USERS,) or d2.shape != (USERS,)
                        or visible.shape != (USERS,)
                        or not np.all(np.isfinite(projected_gain)) or np.any(projected_gain < 0.0)
                    ):
                        raise CAError("projection persistence offset source is malformed")
                    for user, action in enumerate(actions.tolist()):
                        if action == NO_OP_ACTION:
                            active[user] = False
                            continue
                        gain = float(projected_gain[user])
                        feasible = False
                        if gain > 0.0:
                            required = float(recurrence_power_w(
                                opening_start[user], gain, p0_w=SEGMENT_START_POWER_W
                            ))
                            feasible = not bool(classify_link_power_feasibility(
                                np.asarray([required], dtype=np.float64),
                                max_power_w=BEAM_POWER_MAX_W,
                            )[0])
                        active[user] &= bool(d2[user]) and bool(visible[user]) and gain > 0.0 and feasible
                    chi = np.asarray(offset.get("chi"), dtype=np.bool_)
                    if (
                        chi.shape != (USERS,)
                        or int(np.count_nonzero(chi)) != served
                        or not np.array_equal(chi, active)
                        or hashlib.sha256(np.ascontiguousarray(chi).tobytes()).hexdigest()
                        != offset.get("chi_sha256")
                    ):
                        raise CAError("projection persistence indicator drifted")
                    a_terms.append(offset_bits - KAPPA_BITS * lost)
                    energy_terms.append(offset_energy)
                expected_a = 0.0 if horizon == 0 else math.fsum(a_terms) / horizon
                expected_e = 0.0 if horizon == 0 else math.fsum(energy_terms) / horizon
                if a_value != expected_a or e_value != expected_e:
                    raise CAError("proposal projection A/E are not derived from offsets")
                if mask == 0:
                    empty_a, empty_e = a_value, e_value
                assert empty_a is not None and empty_e is not None
                value = (a_value - empty_a) - LAMBDA_BITS_PER_J * (e_value - empty_e)
                if subset_row.get("V_bits_hex") != value.hex():
                    raise CAError("proposal characteristic value is not derived from A/E")
                characteristic[frozenset(expected_members)] = value
            shapley = exact_shapley(characteristic, proposal.members)
            recorded_shapley = receipt.get("shapley_exact")
            recorded_overlap = receipt.get("overlap_d12_bits_hex")
            overlap_receipts = receipt.get("overlap_receipts")
            recorded_z = receipt.get("z_exact")
            if not all(isinstance(value, Mapping) for value in (
                recorded_shapley, recorded_overlap, overlap_receipts, recorded_z
            )):
                raise CAError("proposal allocation receipt is malformed")
            if set(recorded_shapley) != {str(user) for user in proposal.members}:
                raise CAError("recorded Shapley allocation has wrong membership")
            for user in proposal.members:
                if _fraction_from_payload(recorded_shapley[str(user)], field="Shapley") != shapley[user]:
                    raise CAError("recorded Shapley allocation drifted")
            try:
                overlap = {
                    user: float.fromhex(str(recorded_overlap[str(user)]))
                    for user in proposal.members
                }
            except (KeyError, ValueError) as error:
                raise CAError("proposal overlap allocation is malformed") from error
            calculated_z = subtract_overlap(shapley, overlap)
            empty_profile = f1.profile_from_payload(
                rows[0]["current_interval"]["physical_profile"]
            )
            for member_index, (user, action) in enumerate(
                zip(proposal.members, proposal.proposed_actions, strict=True)
            ):
                overlap_row = overlap_receipts.get(str(user))
                if not isinstance(overlap_row, Mapping) or overlap_row.get("d12_bits_hex") != overlap[user].hex():
                    raise CAError("proposal C1/C2 overlap receipt drifted")
                _digest(overlap_row.get("c1_opening_comparison_sha256"), field="C1 opening comparison")
                try:
                    bits_delta = float.fromhex(str(overlap_row["current_delivered_bits_delta_hex"]))
                    energy_delta = float.fromhex(str(overlap_row["current_total_network_energy_delta_j_hex"]))
                    y2_delta = float.fromhex(str(overlap_row["repriced_normalized_c2_delta_hex"]))
                except (KeyError, ValueError) as error:
                    raise CAError("proposal overlap components are malformed") from error
                expected_overlap = (
                    bits_delta - LAMBDA_BITS_PER_J * energy_delta
                    + KAPPA_BITS * y2_delta
                )
                singleton_profile = f1.profile_from_payload(
                    rows[1 << member_index]["current_interval"]["physical_profile"]
                )
                expected_bits_delta = INTERVAL_S * (
                    float(singleton_profile.link_rate_bps[user])
                    - float(empty_profile.link_rate_bps[user])
                )
                expected_energy_delta = (
                    float(singleton_profile.system_power_w) * INTERVAL_S
                    - float(empty_profile.system_power_w) * INTERVAL_S
                )
                expected_y2_delta = (
                    float(y2_targets[user, action])
                    - float(y2_targets[user, int(base_actions[user])])
                )
                if (
                    not all(math.isfinite(value) for value in (bits_delta, energy_delta, y2_delta, expected_overlap))
                    or bits_delta != expected_bits_delta
                    or energy_delta != expected_energy_delta
                    or y2_delta != expected_y2_delta
                    or expected_overlap != overlap[user]
                ):
                    raise CAError("proposal d12 is not derived from its B/E/C2 components")
                if _fraction_from_payload(recorded_z.get(str(user)), field="z") != calculated_z[user]:
                    raise CAError("proposal z allocation drifted")
                cell = (user, action)
                if cell in assignment:
                    raise CAError("proposal z cells overlap")
                assignment.add(cell)
                recomputed_z[cell] = float(calculated_z[user])
            allocation = receipt.get("allocation_conservation")
            grand_delta = (
                _fraction_from_number(characteristic[frozenset(proposal.members)])
                - _fraction_from_number(characteristic[frozenset()])
            )
            if allocation != {
                "sum_phi_exact": _fraction_payload(sum(shapley.values(), Fraction(0))),
                "grand_minus_empty_exact": _fraction_payload(grand_delta),
                "verified": True,
            }:
                raise CAError("proposal Shapley conservation receipt drifted")
            full_sha = canonical_sha256(rows[-1])
            if receipt.get("full_adoption_receipt_sha256") != full_sha:
                raise CAError("proposal full-adoption receipt digest drifted")
            expected_full.append({"proposal_id": proposal.profile_id, "receipt_sha256": full_sha})
            full_profile_sha = str(rows[-1]["current_interval"]["physical_profile_sha256"])
            if receipt.get("alias_of_proposal_id") != first_full_profile.get(full_profile_sha):
                raise CAError("proposal physical alias receipt drifted")
            first_full_profile.setdefault(full_profile_sha, proposal.profile_id)
            subsets += count
        if not np.array_equal(recomputed_z, z_surface):
            raise CAError("recorded z surface is not derived from proposal allocations")
        if step.get("full_adoption_receipts") != expected_full:
            raise CAError("full-adoption receipt index drifted")
        deployed, composed = select_deployed_actions(q12, masks, z_surface)
        if deployed.tolist() != step.get("deployed_actions"):
            raise CAError("deployed decision is not the masked composed argmax")
        if hashlib.sha256(np.ascontiguousarray(composed, dtype=np.dtype("<f8")).tobytes()).hexdigest() != step.get("composed_float64_sha256"):
            raise CAError("composed decision surface digest drifted")
        base = step.get("base_physical")
        deployed = step.get("deployed_physical_once")
        if not isinstance(base, Mapping) or not isinstance(deployed, Mapping):
            raise CAError("BASE/deployed physical receipt is missing")
        _profile_row_from_receipt(base)
        _profile_row_from_receipt(deployed)
        expected_changes: list[int] = []
        deployed_actions = step["deployed_actions"]
        for user, (left, right) in enumerate(zip(base_actions.tolist(), deployed_actions, strict=True)):
            left_key = None if left == NO_OP_ACTION else _physical_key(key_table[user][left])
            right_key = None if right == NO_OP_ACTION else _physical_key(key_table[user][right])
            if left_key != right_key:
                expected_changes.append(user)
        if step.get("physical_change_users") != expected_changes:
            raise CAError("physical-change receipt is not derived from deployed actions")
        expected_partial: list[dict[str, object]] = []
        expected_deployed_full: list[dict[str, object]] = []
        for proposal, receipt in zip(parsed_action, proposal_receipts, strict=True):
            adopted = tuple(
                user for user, action in zip(proposal.members, proposal.proposed_actions, strict=True)
                if int(deployed_actions[user]) == action
            )
            if not adopted:
                continue
            mask = sum(1 << index for index, user in enumerate(proposal.members) if user in adopted)
            row = {
                "proposal_id": proposal.profile_id,
                "adopted_members": list(adopted),
                "member_count": len(proposal.members),
                "subset_mask": mask,
                "subset_receipt_sha256": canonical_sha256(receipt["subset_receipts"][mask]),
            }
            (expected_deployed_full if len(adopted) == len(proposal.members) else expected_partial).append(row)
        if step.get("partial_adoption_receipts") != expected_partial or step.get("deployed_full_adoption_receipts") != expected_deployed_full:
            raise CAError("deployed adoption receipts drifted")
        proposals += len(action_catalogue)
        partial += len(expected_partial)
        changes += len(expected_changes)
    return {
        "anchors": 2,
        "proposals": proposals,
        "subset_profiles": subsets,
        "partial_adoptions": partial,
        "physical_changes": changes,
    }


def _unit_dir(output: Path, key: UnitKey) -> Path:
    return Path(output) / "units" / key.slug


def _unit_receipt(
    tape: Mapping[str, object], *, key: UnitKey, profile_count_cap: int, tape_sha256: str
) -> dict[str, object]:
    counts = verify_unit_tape(tape, key=key, profile_count_cap=profile_count_cap)
    return {
        "schema": UNIT_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "outcome": "C_A_UNIT_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "bindings": panel_bindings(profile_count_cap),
        "lineage_authority": tape["lineage_authority"],
        "e1_terminal_receipt_sha256": tape["e1_terminal_receipt_sha256"],
        "preflight_manifest": tape["preflight_manifest"],
        "launch_authority": tape["launch_authority"],
        "tape_sha256": tape_sha256,
        "counts": counts,
        "integrity": True,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def write_unit_bundle(
    output: Path, *, key: UnitKey, tape: Mapping[str, object], profile_count_cap: int
) -> tuple[Path, Path, Path]:
    verify_unit_tape(tape, key=key, profile_count_cap=profile_count_cap)
    root = Path(output)
    final = _unit_dir(root, key)
    if final.exists() or final.is_symlink():
        raise CAError(f"refusing to overwrite write-once unit directory: {final}")
    units = root / "units"
    units.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".stage-{key.slug}-", dir=units))
    try:
        tape_path = stage / DEFAULT_UNIT_TAPE
        manifest_path = stage / "ca-oracle-tape.manifest.json"
        receipt_path = stage / DEFAULT_UNIT_RECEIPT
        tape_sha = write_once(tape_path, tape)
        manifest = {
            "schema": f"{UNIT_TAPE_SCHEMA}-manifest",
            "status": "COMPLETE_IMMUTABLE_TAPE",
            "unit": key.as_dict(),
            "claim_ceiling": CLAIM_CEILING,
            "tape": {
                "path": DEFAULT_UNIT_TAPE,
                "sha256": tape_sha,
                "bytes": tape_path.stat().st_size,
                "mode": "0444",
            },
        }
        write_once(manifest_path, manifest)
        receipt = _unit_receipt(
            tape, key=key, profile_count_cap=profile_count_cap, tape_sha256=tape_sha
        )
        write_once(receipt_path, receipt)
        os.rename(stage, final)
    finally:
        if stage.exists():
            for child in stage.iterdir():
                child.chmod(0o600)
                child.unlink()
            stage.rmdir()
    return (
        final / DEFAULT_UNIT_TAPE,
        final / "ca-oracle-tape.manifest.json",
        final / DEFAULT_UNIT_RECEIPT,
    )


def authenticate_unit_bundle(
    output: Path, *, key: UnitKey, profile_count_cap: int, e1_terminal_sha256: str,
    preflight_path: Path, preflight_sha256: str,
    expected_launch_authority: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    directory = _unit_dir(output, key)
    tape_path = directory / DEFAULT_UNIT_TAPE
    manifest_path = directory / "ca-oracle-tape.manifest.json"
    receipt_path = directory / DEFAULT_UNIT_RECEIPT
    for path, label in (
        (tape_path, "C-A unit tape"), (manifest_path, "C-A unit manifest"),
        (receipt_path, "C-A unit receipt"),
    ):
        _immutable_file(path, label=f"{label} {key.slug}")
    tape = _load_json(tape_path, field=f"C-A unit tape {key.slug}")
    manifest = _load_json(manifest_path, field=f"C-A unit manifest {key.slug}")
    receipt = _load_json(receipt_path, field=f"C-A unit receipt {key.slug}")
    tape_sha = file_sha256(tape_path)
    expected_manifest = {
        "schema": f"{UNIT_TAPE_SCHEMA}-manifest",
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "unit": key.as_dict(),
        "claim_ceiling": CLAIM_CEILING,
        "tape": {
            "path": DEFAULT_UNIT_TAPE, "sha256": tape_sha,
            "bytes": tape_path.stat().st_size, "mode": "0444",
        },
    }
    if manifest != expected_manifest:
        raise CAError(f"C-A unit manifest drifted for {key.slug}")
    expected_receipt = _unit_receipt(
        tape, key=key, profile_count_cap=profile_count_cap, tape_sha256=tape_sha
    )
    if receipt != expected_receipt or tape.get("e1_terminal_receipt_sha256") != e1_terminal_sha256:
        raise CAError(f"C-A unit receipt/provenance drifted for {key.slug}")
    expected_preflight = {
        "path": str(Path(preflight_path).resolve()), "sha256": preflight_sha256
    }
    if tape.get("preflight_manifest") != expected_preflight:
        raise CAError(f"C-A unit preflight binding drifted for {key.slug}")
    launch = tape.get("launch_authority")
    if not isinstance(launch, Mapping):
        raise CAError(f"C-A unit launch binding is malformed for {key.slug}")
    launch_path = Path(str(launch["path"]))
    if file_sha256(launch_path) != launch.get("sha256"):
        raise CAError(f"C-A unit launch authority bytes drifted for {key.slug}")
    authority = validate_launch_authority(
        launch_path, preflight_path=preflight_path,
        preflight_sha256=preflight_sha256, profile_count_cap=profile_count_cap,
        output_root=Path(output),
    )
    parsed = _parser().parse_args(authority["launch_arguments"])
    if parsed.unit != f"{key.world}:{key.lineage}" or parsed.merge:
        raise CAError(f"C-A unit launch authority names the wrong unit for {key.slug}")
    if expected_launch_authority is not None and dict(launch) != dict(expected_launch_authority):
        raise CAError(f"existing C-A unit belongs to another launch authority for {key.slug}")
    return receipt, file_sha256(receipt_path), tape


@dataclass(frozen=True)
class BudgetReservation:
    token: str
    reserved_worker_seconds: float


def _empty_budget() -> dict[str, object]:
    return {
        "schema": f"{SCHEMA}-worker-budget-ledger",
        "cap_worker_seconds_hex": DEFAULT_BUDGET_WORKER_SECONDS.hex(),
        "charged_worker_seconds_hex": 0.0.hex(),
        "unit_charge_count": 0,
        "unit_charged_worker_seconds_hex": 0.0.hex(),
        "reservations": [],
    }


def _validate_budget(payload: Mapping[str, object]) -> None:
    if (
        set(payload) != set(_empty_budget())
        or payload.get("schema") != _empty_budget()["schema"]
        or payload.get("cap_worker_seconds_hex") != DEFAULT_BUDGET_WORKER_SECONDS.hex()
        or not isinstance(payload.get("reservations"), list)
    ):
        raise CAError("worker budget ledger binding drifted")
    try:
        charged = float.fromhex(str(payload["charged_worker_seconds_hex"]))
        unit_charged = float.fromhex(str(payload["unit_charged_worker_seconds_hex"]))
    except (TypeError, ValueError) as error:
        raise CAError("worker budget ledger usage is malformed") from error
    count = payload["unit_charge_count"]
    if (
        not math.isfinite(charged) or charged < 0.0
        or not math.isfinite(unit_charged) or unit_charged < 0.0
        or unit_charged > charged
        or type(count) is not int or count < 0
    ):
        raise CAError("worker budget ledger usage is malformed")
    seen: set[str] = set()
    total = 0.0
    for row in payload["reservations"]:
        if not isinstance(row, Mapping) or set(row) != {
            "token", "scope", "worker_seconds_hex"
        }:
            raise CAError("worker budget reservation is malformed")
        token = row.get("token")
        scope = row.get("scope")
        try:
            amount = float.fromhex(str(row.get("worker_seconds_hex")))
        except (TypeError, ValueError) as error:
            raise CAError("worker budget reservation is malformed") from error
        if (
            not isinstance(token, str) or not token or token in seen
            or not isinstance(scope, str)
            or not (scope == "merge" or scope.startswith("unit:"))
            or not math.isfinite(amount) or amount <= 0.0
        ):
            raise CAError("worker budget reservation is malformed")
        seen.add(token)
        total += amount
    if not math.isfinite(total) or total > DEFAULT_BUDGET_WORKER_SECONDS:
        raise CAError("worker budget reservations exceed the 16-hour pool")


def _budget_update(output: Path, update: Callable[[dict[str, Any]], object]) -> object:
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    path = root / DEFAULT_BUDGET_LEDGER
    if path.is_symlink():
        raise CAError("budget ledger must not be a symlink")
    with path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        raw = handle.read()
        payload = _empty_budget() if not raw else json.loads(raw.decode("ascii"))
        _validate_budget(payload)
        result = update(payload)
        _validate_budget(payload)
        encoded = canonical_bytes(payload) + b"\n"
        handle.seek(0)
        handle.truncate()
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
        handle.seek(0)
        if handle.read() != encoded:
            raise CAError("worker budget ledger failed readback")
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return result


def _reserve_budget(output: Path, *, scope: str) -> BudgetReservation:
    token = hashlib.sha256(
        f"{scope}:{os.getpid()}:{time.monotonic_ns()}".encode("ascii")
    ).hexdigest()

    def update(payload: dict[str, Any]) -> BudgetReservation:
        charged = float.fromhex(payload["charged_worker_seconds_hex"])
        reserved = math.fsum(
            float.fromhex(row["worker_seconds_hex"])
            for row in payload["reservations"]
        )
        count = int(payload["unit_charge_count"])
        unit_charged = float.fromhex(payload["unit_charged_worker_seconds_hex"])
        amount = max(
            DEFAULT_RESERVATION_WORKER_SECONDS,
            unit_charged / count if count else DEFAULT_RESERVATION_WORKER_SECONDS,
        )
        if charged + reserved + amount > DEFAULT_BUDGET_WORKER_SECONDS:
            raise CAIncomplete("BUDGET_EXHAUSTED", "declared 16 worker-hour budget cannot reserve another operation")
        payload["reservations"].append({
            "token": token, "scope": scope, "worker_seconds_hex": amount.hex()
        })
        return BudgetReservation(token, amount)

    return _budget_update(output, update)  # type: ignore[return-value]


def _finish_budget(
    output: Path, *, reservation: BudgetReservation, elapsed: float
) -> float:
    if not math.isfinite(elapsed) or elapsed < 0.0:
        raise CAError("budget elapsed time is malformed")

    def update(payload: dict[str, Any]) -> float:
        matches = [row for row in payload["reservations"] if row["token"] == reservation.token]
        if len(matches) != 1:
            raise CAError("budget reservation is missing or duplicated")
        payload["reservations"] = [
            row for row in payload["reservations"] if row["token"] != reservation.token
        ]
        charged = float.fromhex(payload["charged_worker_seconds_hex"])
        charged += elapsed
        payload["charged_worker_seconds_hex"] = charged.hex()
        if str(matches[0].get("scope", "")).startswith("unit:"):
            payload["unit_charge_count"] += 1
            unit_charged = float.fromhex(payload["unit_charged_worker_seconds_hex"])
            payload["unit_charged_worker_seconds_hex"] = (unit_charged + elapsed).hex()
        return charged

    return _budget_update(output, update)  # type: ignore[return-value]


def _status_receipt(
    *, status: str, scope: str, profile_count_cap: int, error: BaseException,
    preflight_path: Path, preflight_sha256: str,
    launch_authority_path: Path, launch_authority_sha256: str,
) -> dict[str, object]:
    reason = error.reason if isinstance(error, CAIncomplete) else "INTEGRITY_FAILURE"
    return {
        "schema": f"{SCHEMA}-status-receipt",
        "status": status,
        "outcome": status,
        "scope": scope,
        "reason": reason,
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
        "claim_ceiling": CLAIM_CEILING,
        "bindings": panel_bindings(profile_count_cap),
        "preflight_manifest": {
            "path": str(Path(preflight_path).resolve()), "sha256": preflight_sha256,
        },
        "launch_authority": {
            "path": str(Path(launch_authority_path).resolve()),
            "sha256": launch_authority_sha256,
        },
        "integrity": status != "INVALID_RUN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def _publish_status_once(
    output: Path, *, status: str, scope: str, profile_count_cap: int, error: BaseException,
    preflight_path: Path, preflight_sha256: str,
    launch_authority_path: Path, launch_authority_sha256: str,
) -> Path:
    root = Path(output)
    name = f"{status}-{scope.replace(':', '-')}.json"
    path = root / name
    payload = _status_receipt(
        status=status, scope=scope, profile_count_cap=profile_count_cap, error=error,
        preflight_path=preflight_path, preflight_sha256=preflight_sha256,
        launch_authority_path=launch_authority_path,
        launch_authority_sha256=launch_authority_sha256,
    )
    if path.exists() or path.is_symlink():
        _immutable_file(path, label=f"existing {status} receipt")
        if _load_json(path, field=f"existing {status} receipt") != payload:
            raise CAError(f"existing {status} receipt binding/content drifted")
        return path
    write_once(path, payload)
    return path


def execute_unit(
    *, key: UnitKey, output: Path, profile_count_cap: int,
    preflight_path: Path, preflight_sha256: str,
    launch_authority_path: Path, launch_authority_sha256: str,
) -> tuple[Path, bool, bool]:
    root = Path(output)
    validate_output_root(root)
    terminal, terminal_sha = authenticate_e1_terminal(E1_OUTPUT_ROOT)
    del terminal
    existing = _unit_dir(root, key) / DEFAULT_UNIT_RECEIPT
    existed_at_start = existing.exists() or existing.is_symlink()
    try:
        reservation = _reserve_budget(root, scope=f"unit:{key.slug}")
    except CAIncomplete as error:
        return _publish_status_once(
            root, status="INCOMPLETE", scope=f"unit:{key.slug}",
            profile_count_cap=profile_count_cap, error=error,
            preflight_path=preflight_path, preflight_sha256=preflight_sha256,
            launch_authority_path=launch_authority_path,
            launch_authority_sha256=launch_authority_sha256,
        ), False, False
    started = time.monotonic()
    old_handler: Any = None
    timer = False
    try:
        if hasattr(signal, "setitimer"):
            old_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(
                signal.SIGALRM,
                lambda _signum, _frame: (_ for _ in ()).throw(
                    CAIncomplete("BUDGET_EXHAUSTED", "unit worker-time reservation exhausted")
                ),
            )
            signal.setitimer(signal.ITIMER_REAL, reservation.reserved_worker_seconds)
            timer = True
        if existed_at_start:
            authenticate_unit_bundle(
                root, key=key, profile_count_cap=profile_count_cap,
                e1_terminal_sha256=terminal_sha,
                preflight_path=preflight_path, preflight_sha256=preflight_sha256,
                expected_launch_authority={
                    "path": str(Path(launch_authority_path).resolve()),
                    "sha256": launch_authority_sha256,
                },
            )
            return existing, True, True
        tape = generate_unit_tape(
            key=key, profile_count_cap=profile_count_cap,
            preflight_sha256=preflight_sha256,
            preflight_path=preflight_path,
            launch_authority_sha256=launch_authority_sha256,
            launch_authority_path=launch_authority_path,
        )
        _tape, _manifest, receipt = write_unit_bundle(
            root, key=key, tape=tape, profile_count_cap=profile_count_cap
        )
        authenticate_unit_bundle(
            root, key=key, profile_count_cap=profile_count_cap,
            e1_terminal_sha256=terminal_sha,
            preflight_path=preflight_path, preflight_sha256=preflight_sha256,
            expected_launch_authority={
                "path": str(Path(launch_authority_path).resolve()),
                "sha256": launch_authority_sha256,
            },
        )
        return receipt, False, True
    except (CAIncomplete, KeyboardInterrupt) as error:
        incomplete = error if isinstance(error, CAIncomplete) else CAIncomplete("INTERRUPTED", str(error))
        return _publish_status_once(
            root, status="INCOMPLETE", scope=f"unit:{key.slug}",
            profile_count_cap=profile_count_cap, error=incomplete,
            preflight_path=preflight_path, preflight_sha256=preflight_sha256,
            launch_authority_path=launch_authority_path,
            launch_authority_sha256=launch_authority_sha256,
        ), False, False
    except Exception as error:
        return _publish_status_once(
            root, status="INVALID_RUN", scope=f"unit:{key.slug}",
            profile_count_cap=profile_count_cap, error=error,
            preflight_path=preflight_path, preflight_sha256=preflight_sha256,
            launch_authority_path=launch_authority_path,
            launch_authority_sha256=launch_authority_sha256,
        ), False, False
    finally:
        if timer:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, old_handler)
        _finish_budget(
            root, reservation=reservation, elapsed=time.monotonic() - started
        )


def build_terminal_receipt(
    *, tapes: Sequence[Mapping[str, object]], unit_receipts: Sequence[tuple[UnitKey, str]],
    profile_count_cap: int, e1_terminal_sha256: str,
    preflight_path: Path, preflight_sha256: str,
    launch_authority_path: Path, launch_authority_sha256: str,
) -> dict[str, object]:
    if len(tapes) != len(ALL_UNITS) or tuple(key for key, _ in unit_receipts) != ALL_UNITS:
        raise CAError("terminal merge requires all twelve units in canonical order")
    base_rows: list[PooledRow] = []
    candidate_rows: list[PooledRow] = []
    catalogue_agreement = True
    higher_order = False
    physical_change = False
    partial_rows = 0
    anchors_with_partial = 0
    partial_anchor_losses: list[dict[str, object]] = []
    for tape in tapes:
        if tape.get("preflight_manifest") != {
            "path": str(Path(preflight_path).resolve()), "sha256": preflight_sha256
        }:
            raise CAError("unit tape preflight binding disagrees at merge")
        unit = tape["unit"]
        for step in tape["steps"]:
            base = _profile_row_from_receipt(step["base_physical"])
            candidate = _profile_row_from_receipt(step["deployed_physical_once"])
            base_rows.append(base)
            candidate_rows.append(candidate)
            catalogue_agreement &= bool(step["catalogue_agreement"])
            higher_order |= bool(step["higher_order_exposure"])
            physical_change |= bool(step["physical_change_users"])
            partial = step["partial_adoption_receipts"]
            partial_rows += len(partial)
            if partial:
                anchors_with_partial += 1
                surplus_delta = (
                    candidate.bits - base.bits
                    - LAMBDA_BITS_PER_J * (candidate.energy_j - base.energy_j)
                )
                service_delta = candidate.served - base.served
                if surplus_delta < 0.0 or service_delta < 0:
                    partial_anchor_losses.append({
                        "anchor": f"{unit['world']}:{unit['lineage']}:{step['step_index']}",
                        "partial_proposals": len(partial),
                        "repriced_surplus_delta_bits_hex": surplus_delta.hex(),
                        "served_delta": service_delta,
                    })
    if (
        len(base_rows) != 24 or len(candidate_rows) != 24
        or sum(row.opportunities for row in base_rows) != 2400
        or sum(row.opportunities for row in candidate_rows) != 2400
    ):
        raise CAError("terminal pooling requires exactly 24 anchors and 2,400 opportunities")
    outcome = screen_decision(
        base_rows=base_rows,
        candidate_rows=candidate_rows,
        catalogue_agreement=catalogue_agreement,
        higher_order_exposure=higher_order,
        legal_physical_change=physical_change,
    )
    return {
        "schema": TERMINAL_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "outcome": outcome["decision"],
        "reasons": outcome["reasons"],
        "claim_ceiling": CLAIM_CEILING,
        "bindings": panel_bindings(profile_count_cap),
        "e1_terminal_receipt_sha256": e1_terminal_sha256,
        "preflight_manifest": {
            "path": str(Path(preflight_path).resolve()), "sha256": preflight_sha256,
        },
        "merge_launch_authority": {
            "path": str(Path(launch_authority_path).resolve()),
            "sha256": launch_authority_sha256,
        },
        "lineage_authorities": f2.lineage_authority_bindings(),
        "formula_digests": formula_digests(),
        "unit_receipts": [
            {"unit": key.as_dict(), "path": f"units/{key.slug}/{DEFAULT_UNIT_RECEIPT}", "sha256": digest}
            for key, digest in unit_receipts
        ],
        "pooled": {"A": outcome["eta_A"], "BASE": outcome["eta_BASE"]},
        "requirements": {
            "complete_valid_receipts": True,
            "catalogue_interface_agreement": catalogue_agreement,
            "higher_order_exposure": higher_order,
            "legal_physical_action_change": physical_change,
        },
        "partial_adoption_report": {
            "partial_proposal_receipts": partial_rows,
            "anchors_with_partial_adoption": anchors_with_partial,
            "losses": partial_anchor_losses,
            "threshold_applied": False,
        },
        "integrity": True,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def authenticate_existing_terminal(
    path: Path, *, output: Path, profile_count_cap: int,
    e1_terminal_sha256: str, preflight_path: Path, preflight_sha256: str,
    launch_authority_path: Path, launch_authority_sha256: str,
) -> bool:
    """Authenticate a write-once terminal before treating a rerun as complete."""

    _immutable_file(path, label="existing C-A terminal receipt")
    terminal = _load_json(path, field="existing C-A terminal receipt")
    status = terminal.get("status")
    common = {
        "schema": TERMINAL_RECEIPT_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "bindings": panel_bindings(profile_count_cap),
        "e1_terminal_receipt_sha256": e1_terminal_sha256,
        "preflight_manifest": {
            "path": str(Path(preflight_path).resolve()), "sha256": preflight_sha256,
        },
        "merge_launch_authority": {
            "path": str(Path(launch_authority_path).resolve()),
            "sha256": launch_authority_sha256,
        },
    }
    for field, expected in common.items():
        if terminal.get(field) != expected:
            raise CAError(f"existing C-A terminal {field} binding drifted")
    if file_sha256(Path(launch_authority_path)) != launch_authority_sha256:
        raise CAError("existing C-A terminal merge authority bytes drifted")
    validate_launch_authority(
        Path(launch_authority_path), preflight_path=preflight_path,
        preflight_sha256=preflight_sha256, profile_count_cap=profile_count_cap,
        output_root=output,
    )
    if status == "COMPLETE":
        receipts: list[tuple[UnitKey, str]] = []
        tapes: list[Mapping[str, object]] = []
        for key in ALL_UNITS:
            _receipt, digest, tape = authenticate_unit_bundle(
                output, key=key, profile_count_cap=profile_count_cap,
                e1_terminal_sha256=e1_terminal_sha256,
                preflight_path=preflight_path, preflight_sha256=preflight_sha256,
            )
            receipts.append((key, digest))
            tapes.append(tape)
        expected = build_terminal_receipt(
            tapes=tapes, unit_receipts=receipts,
            profile_count_cap=profile_count_cap,
            e1_terminal_sha256=e1_terminal_sha256,
            preflight_path=preflight_path, preflight_sha256=preflight_sha256,
            launch_authority_path=launch_authority_path,
            launch_authority_sha256=launch_authority_sha256,
        )
        if terminal != expected:
            raise CAError("existing C-A COMPLETE terminal is not reproducible from its units")
        return True
    if status == "INVALID_RUN":
        required = {
            *common, "status", "outcome", "integrity", "error_type", "error_sha256",
            "test_split_opened", "episode_training", "learner_update", "efficacy_claim",
        }
        if (
            set(terminal) != required
            or terminal.get("outcome") != "INVALID_RUN"
            or terminal.get("integrity") is not False
            or not isinstance(terminal.get("error_type"), str)
            or any(terminal.get(field) is not False for field in (
                "test_split_opened", "episode_training", "learner_update", "efficacy_claim"
            ))
        ):
            raise CAError("existing C-A INVALID_RUN terminal is malformed")
        _digest(terminal.get("error_sha256"), field="terminal error sha256")
        return False
    raise CAError("existing C-A terminal has an unauthenticated status")


def execute_merge(
    *, output: Path, profile_count_cap: int,
    preflight_path: Path, preflight_sha256: str,
    launch_authority_path: Path, launch_authority_sha256: str,
) -> tuple[Path, bool, bool]:
    root = Path(output)
    validate_output_root(root)
    terminal_path = root / DEFAULT_TERMINAL_RECEIPT
    e1_terminal, e1_terminal_sha = authenticate_e1_terminal(E1_OUTPUT_ROOT)
    del e1_terminal
    existed_at_start = terminal_path.exists() or terminal_path.is_symlink()
    missing = 0 if existed_at_start else sum(
        not (_unit_dir(root, key) / DEFAULT_UNIT_RECEIPT).is_file() for key in ALL_UNITS
    )
    if missing:
        raise CAMergeWaiting(missing)
    try:
        reservation = _reserve_budget(root, scope="merge")
    except CAIncomplete as error:
        return _publish_status_once(
            root, status="INCOMPLETE", scope="merge",
            profile_count_cap=profile_count_cap, error=error,
            preflight_path=preflight_path, preflight_sha256=preflight_sha256,
            launch_authority_path=launch_authority_path,
            launch_authority_sha256=launch_authority_sha256,
        ), False, False
    started = time.monotonic()
    old_handler: Any = None
    timer = False
    try:
        if hasattr(signal, "setitimer"):
            old_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(
                signal.SIGALRM,
                lambda _signum, _frame: (_ for _ in ()).throw(
                    CAIncomplete("BUDGET_EXHAUSTED", "merge worker-time reservation exhausted")
                ),
            )
            signal.setitimer(signal.ITIMER_REAL, reservation.reserved_worker_seconds)
            timer = True
        if existed_at_start:
            valid = authenticate_existing_terminal(
                terminal_path, output=root, profile_count_cap=profile_count_cap,
                e1_terminal_sha256=e1_terminal_sha,
                preflight_path=preflight_path, preflight_sha256=preflight_sha256,
                launch_authority_path=launch_authority_path,
                launch_authority_sha256=launch_authority_sha256,
            )
            return terminal_path, True, valid
        receipts: list[tuple[UnitKey, str]] = []
        tapes: list[Mapping[str, object]] = []
        for key in ALL_UNITS:
            _receipt, digest, tape = authenticate_unit_bundle(
                root, key=key, profile_count_cap=profile_count_cap,
                e1_terminal_sha256=e1_terminal_sha,
                preflight_path=preflight_path, preflight_sha256=preflight_sha256,
            )
            receipts.append((key, digest))
            tapes.append(tape)
        payload = build_terminal_receipt(
            tapes=tapes, unit_receipts=receipts,
            profile_count_cap=profile_count_cap,
            e1_terminal_sha256=e1_terminal_sha,
            preflight_path=preflight_path,
            preflight_sha256=preflight_sha256,
            launch_authority_path=launch_authority_path,
            launch_authority_sha256=launch_authority_sha256,
        )
        write_once(terminal_path, payload)
        return terminal_path, False, True
    except (CAIncomplete, KeyboardInterrupt) as error:
        incomplete = error if isinstance(error, CAIncomplete) else CAIncomplete("INTERRUPTED", str(error))
        return _publish_status_once(
            root, status="INCOMPLETE", scope="merge",
            profile_count_cap=profile_count_cap, error=incomplete,
            preflight_path=preflight_path, preflight_sha256=preflight_sha256,
            launch_authority_path=launch_authority_path,
            launch_authority_sha256=launch_authority_sha256,
        ), False, False
    except Exception as error:
        if existed_at_start:
            return _publish_status_once(
                root, status="INVALID_RUN", scope="merge-existing-terminal",
                profile_count_cap=profile_count_cap, error=error,
                preflight_path=preflight_path, preflight_sha256=preflight_sha256,
                launch_authority_path=launch_authority_path,
                launch_authority_sha256=launch_authority_sha256,
            ), False, False
        payload = {
            "schema": TERMINAL_RECEIPT_SCHEMA,
            "status": "INVALID_RUN",
            "outcome": "INVALID_RUN",
            "claim_ceiling": CLAIM_CEILING,
            "bindings": panel_bindings(profile_count_cap),
            "e1_terminal_receipt_sha256": e1_terminal_sha,
            "preflight_manifest": {
                "path": str(Path(preflight_path).resolve()), "sha256": preflight_sha256,
            },
            "merge_launch_authority": {
                "path": str(Path(launch_authority_path).resolve()),
                "sha256": launch_authority_sha256,
            },
            "integrity": False,
            "error_type": type(error).__name__,
            "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
            "efficacy_claim": False,
        }
        write_once(terminal_path, payload)
        return terminal_path, False, False
    finally:
        if timer:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, old_handler)
        _finish_budget(
            root, reservation=reservation, elapsed=time.monotonic() - started
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--estimate", action="store_true", help="read E1 tapes and estimate exact enumeration cost")
    mode.add_argument("--unit", help="run one exact WORLD:LINEAGE shard")
    mode.add_argument("--merge", action="store_true", help="authenticate and merge all twelve shards")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--profile-count-cap", type=int)
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--tle-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--e1-output", type=Path, default=E1_OUTPUT_ROOT)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    if args.estimate:
        return {"mode": "estimate", "estimate": estimate_from_e1(Path(args.e1_output))}
    # This ordering is deliberate: dry-run reports the true controller gate.
    sealed_contract_binding()
    if args.profile_count_cap is None or args.profile_count_cap < 1:
        raise CAError("sealed execution requires --profile-count-cap from the controller estimate decision")
    _manifest, preflight_sha = validate_preflight_manifest(
        Path(args.preflight_manifest), profile_count_cap=args.profile_count_cap
    )
    if args.dry_run:
        return {"mode": "dry-run", "preflight": str(Path(args.preflight_manifest))}
    if (
        args.launch_authority is None or args.output is None
    ):
        raise CAError("execution requires --launch-authority and absolute --output")
    validate_output_root(Path(args.output))
    if Path(args.e1_output).resolve() != E1_OUTPUT_ROOT.resolve():
        raise CAError("formal execution requires the authority-bound canonical E1 output root")
    validate_launch_authority(
        Path(args.launch_authority),
        preflight_path=Path(args.preflight_manifest), preflight_sha256=preflight_sha,
        profile_count_cap=args.profile_count_cap, output_root=Path(args.output),
        tle_root=Path(args.tle_root) if args.tle_root is not None else None,
        launch_arguments=getattr(args, "raw_launch_arguments", None),
    )
    authority_sha = file_sha256(Path(args.launch_authority))
    if args.unit is not None:
        if args.tle_root is None:
            raise CAError("--unit requires --tle-root")
        path, skipped, valid = execute_unit(
            key=UnitKey.parse(args.unit), output=Path(args.output),
            profile_count_cap=args.profile_count_cap,
            preflight_path=Path(args.preflight_manifest),
            preflight_sha256=preflight_sha,
            launch_authority_path=Path(args.launch_authority),
            launch_authority_sha256=authority_sha,
        )
        return {"mode": "unit", "receipt": str(path), "skipped": skipped, "valid": valid}
    if not args.merge:
        raise CAError("execution requires exactly one of --unit or --merge")
    path, skipped, valid = execute_merge(
        output=Path(args.output), profile_count_cap=args.profile_count_cap,
        preflight_path=Path(args.preflight_manifest),
        preflight_sha256=preflight_sha,
        launch_authority_path=Path(args.launch_authority),
        launch_authority_sha256=authority_sha,
    )
    return {"mode": "merge", "receipt": str(path), "skipped": skipped, "valid": valid}


def _print_estimate(payload: Mapping[str, object]) -> None:
    totals = payload["totals"]
    print(
        "CA_ESTIMATE_TOTAL "
        f"anchors={totals['anchors']} proposals={totals['proposals']} "
        f"member_rows={totals['proposal_member_rows']} subset_profiles={totals['subset_profiles']} "
        f"current_profile_evaluations={totals['current_profile_evaluations']} "
        f"c1_overlap_profile_evaluations={totals['c1_overlap_profile_evaluations']} "
        f"ops3_offset_profile_evaluations={totals['ops3_offset_profile_evaluations']} "
        f"complete_profile_evaluations={totals['complete_profile_evaluations']} "
        f"max_members={totals['maximum_members']} "
        f"largest_per_proposal={totals['largest_per_proposal_profile_count']} "
        f"catalogue_mismatch_anchors={totals['catalogue_mismatch_anchors']} "
        f"projected_worker_hours={totals['projected_worker_hours']:.6f}"
    )
    print(
        "CA_ESTIMATE_BASIS seconds_per_world_lineage_two_steps=383 "
        "profiles_per_world_lineage_two_steps=2700 "
        "includes_current_plus_c1_overlap_plus_three_ops3_offsets=true"
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        pin_single_thread_runtime()
    except CAError as error:
        print(f"CA_ERROR: {error}", file=sys.stderr)
        return 2
    raw = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(raw)
    args.raw_launch_arguments = raw
    old_sigterm = signal.getsignal(signal.SIGTERM)

    def interrupt(_signum: int, _frame: object) -> None:
        raise CAIncomplete("INTERRUPTED", "execution interrupted by SIGTERM")

    signal.signal(signal.SIGTERM, interrupt)
    try:
        result = run(args)
    except CAMergeWaiting as error:
        print(f"CA_MERGE_WAITING missing={error.missing}")
        return 3
    except Exception as error:
        print(f"CA_ERROR: {error}", file=sys.stderr)
        return 2
    finally:
        signal.signal(signal.SIGTERM, old_sigterm)
    if result["mode"] == "estimate":
        _print_estimate(result["estimate"])
        return 0
    if result["mode"] == "dry-run":
        print(f"CA_DRY_RUN_PASS preflight={result['preflight']}")
        return 0
    payload = _load_json(Path(result["receipt"]), field="published C-A receipt")
    if payload.get("status") == "INCOMPLETE":
        print(f"CA_{str(result['mode']).upper()}_INCOMPLETE receipt={result['receipt']}")
        return 3
    state = "SKIPPED_COMPLETE" if result["skipped"] else "WRITTEN"
    print(f"CA_{str(result['mode']).upper()}_{state} receipt={result['receipt']}")
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
