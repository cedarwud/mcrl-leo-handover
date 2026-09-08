#!/usr/bin/env python3
"""Deployable S0 set-level coordinator used by the C3S closed-loop screen."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, fields, is_dataclass, replace
from fractions import Fraction
import json
import math
from pathlib import Path
import resource
import sys
import time
from types import SimpleNamespace
from typing import Any, Callable, Literal, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-existence-e1"
F1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f1"
F2_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f2"
S0_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-probe-s0"
for _path in (E1_DIR, F1_DIR, F2_DIR, S0_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_probe_s0 as s0  # noqa: E402
import run_v023_c3_existence_e1 as e1  # noqa: E402
import run_v023_c3_contingency_f1 as f1  # noqa: E402


CONFIG_PATH = HERE / "c3s_config.json"
CONFIG_SCHEMA = "multi-catfish-mcrl-v023-c3s-policy-config-v1"
NOMINAL_CONVENTION = "OPS3_UNIT_RICIAN_GAIN_ZERO_DB_SHADOW_CURRENT_ANCHOR_ONLY"
Catalog = Literal["full", "lite"]


class C3SPolicyError(RuntimeError):
    """A policy input, donor rule, or evaluation-neutrality check failed."""


def _readonly(value: object, *, dtype: np.dtype | type | None = None) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _structural_sha256(value: object) -> str:
    """Hash values recursively, including mutable arrays and RNG internals."""

    import hashlib

    digest = hashlib.sha256()
    active: dict[int, int] = {}
    retained: list[object] = []

    def visit(item: object) -> None:
        if item is None or isinstance(item, (bool, int, str, bytes)):
            digest.update(type(item).__name__.encode("ascii"))
            digest.update(repr(item).encode("utf-8"))
            return
        if isinstance(item, float):
            digest.update(b"float")
            digest.update(item.hex().encode("ascii"))
            return
        if isinstance(item, np.generic):
            visit(item.item())
            return
        if isinstance(item, np.ndarray):
            array = np.ascontiguousarray(item)
            digest.update(b"ndarray")
            digest.update(array.dtype.str.encode("ascii"))
            digest.update(repr(array.shape).encode("ascii"))
            digest.update(b"1" if item.flags.writeable else b"0")
            digest.update(array.tobytes(order="C"))
            return
        if isinstance(item, np.random.Generator):
            digest.update(b"numpy.random.Generator")
            visit(item.bit_generator.state)
            # ``Generator.spawn`` advances only the SeedSequence child census;
            # the BitGenerator state itself is unchanged.  Bind both so even
            # unused child-stream allocation is forbidden during selection.
            seed_sequence = getattr(item.bit_generator, "seed_seq", None)
            if seed_sequence is not None:
                visit(seed_sequence.state)
            return
        identity = id(item)
        if identity in active:
            digest.update(f"ref:{active[identity]}".encode("ascii"))
            return
        active[identity] = len(active)
        retained.append(item)
        digest.update(f"{type(item).__module__}.{type(item).__qualname__}".encode("utf-8"))
        if isinstance(item, Mapping):
            for key in sorted(item, key=lambda candidate: repr(candidate)):
                visit(key)
                visit(item[key])
        elif isinstance(item, (tuple, list)):
            for child in item:
                visit(child)
        elif isinstance(item, (set, frozenset)):
            for child_digest in sorted(_structural_sha256(child) for child in item):
                digest.update(child_digest.encode("ascii"))
        elif is_dataclass(item):
            for definition in fields(item):
                digest.update(definition.name.encode("utf-8"))
                visit(getattr(item, definition.name))
        elif hasattr(item, "__dict__"):
            visit(vars(item))
        elif hasattr(type(item), "__slots__"):
            slots = type(item).__slots__
            for name in ((slots,) if isinstance(slots, str) else tuple(slots)):
                if hasattr(item, name):
                    digest.update(str(name).encode("utf-8"))
                    visit(getattr(item, name))
        else:
            digest.update(repr(item).encode("utf-8"))

    visit(value)
    return digest.hexdigest()


def _assert_no_prohibited_capabilities(value: object) -> None:
    """Reject any environment, RNG, or keyed-field object reachable by selection."""

    seen: set[int] = set()

    def visit(item: object) -> None:
        if item is None or isinstance(item, (bool, int, float, str, bytes, np.generic, np.ndarray)):
            return
        identity = id(item)
        if identity in seen:
            return
        seen.add(identity)
        qualified = f"{type(item).__module__}.{type(item).__qualname__}"
        if (
            isinstance(item, np.random.Generator)
            or qualified.endswith(".StepEnvironment")
            or qualified.endswith(".TrainerEnvironment")
            or qualified.endswith(".KeyedFadingField")
        ):
            raise C3SPolicyError(f"prohibited coordinator capability is reachable: {qualified}")
        if isinstance(item, Mapping):
            children = tuple(item.items())
        elif isinstance(item, (tuple, list, set, frozenset)):
            children = tuple(enumerate(item))
        elif is_dataclass(item):
            children = tuple((definition.name, getattr(item, definition.name)) for definition in fields(item))
        elif hasattr(item, "__dict__"):
            children = tuple(vars(item).items())
        elif hasattr(type(item), "__slots__"):
            slots = type(item).__slots__
            names = (slots,) if isinstance(slots, str) else tuple(slots)
            children = tuple((name, getattr(item, name)) for name in names if hasattr(item, name))
        else:
            children = ()
        for _name, child in children:
            visit(child)

    visit(value)


def _live_neutrality_fingerprint(step_env: Any, rng: np.random.Generator) -> str:
    """Bind all live state, including RNG SeedSequence spawning counters."""

    return _structural_sha256((step_env, rng))


def fraction_payload(value: Fraction) -> dict[str, str]:
    return {
        "numerator": str(value.numerator),
        "denominator": str(value.denominator),
        "float_hex": float(value).hex(),
    }


def load_eta_ref(path: Path = CONFIG_PATH) -> Fraction:
    """Load the injected constant; this path never derives it from screen outcomes."""

    try:
        payload = json.loads(Path(path).read_text(encoding="ascii"))
        raw = payload["eta_ref"]
        value = Fraction(int(raw["numerator"]), int(raw["denominator"]))
        encoded = float.fromhex(raw["float_hex"])
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError,
            ValueError, ZeroDivisionError) as error:
        raise C3SPolicyError("eta_ref config is missing or malformed") from error
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema", "eta_ref", "source"}
        or payload.get("schema") != CONFIG_SCHEMA
        or not isinstance(raw, dict)
        or set(raw) != {"numerator", "denominator", "float_hex"}
        or value <= 0
        or not math.isfinite(encoded)
        or encoded.hex() != float(value).hex()
        or value != Fraction.from_float(encoded)
    ):
        raise C3SPolicyError("eta_ref config does not bind one positive exact constant")
    return value


def _metric(value: Mapping[str, object], *, label: str) -> dict[str, object]:
    try:
        bits = float(value["total_bits"])
        energy = float(value["total_energy_j"])
        served = value["served"]
        opportunities = value["opportunities"]
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise C3SPolicyError(f"{label} metric is malformed") from error
    if (
        not math.isfinite(bits) or bits < 0.0
        or not math.isfinite(energy) or energy <= 0.0
        or type(served) is not int or type(opportunities) is not int
        or opportunities <= 0 or not 0 <= served <= opportunities
    ):
        raise C3SPolicyError(f"{label} metric is outside its domain")
    return {
        "total_bits": bits,
        "total_energy_j": energy,
        "served": served,
        "opportunities": opportunities,
    }


def nominal_score(metric: Mapping[str, object], eta_ref: Fraction) -> Fraction:
    parsed = _metric(metric, label="nominal")
    return (
        Fraction.from_float(float(parsed["total_bits"]))
        - eta_ref * Fraction.from_float(float(parsed["total_energy_j"]))
    )


def _tie_key(row: Mapping[str, object]) -> tuple[int, ...]:
    profile_id = str(row.get("profile_id", ""))
    if profile_id == "BASE":
        return (0,)
    explicit = row.get("tie_key")
    if isinstance(explicit, tuple) and explicit and all(type(value) is int for value in explicit):
        return explicit
    try:
        if profile_id.startswith("U:"):
            _prefix, user, action = profile_id.split(":")
            return (1, int(user), int(action))
        if profile_id.startswith("J:"):
            origin, destination = profile_id[2:].split("->")
            origin_satellite, origin_cell = origin.split(":")
            destination_satellite, destination_cell = destination.split(":")
            return (
                2, int(origin_satellite), int(origin_cell),
                int(destination_satellite), int(destination_cell),
            )
    except (TypeError, ValueError):
        pass
    raise C3SPolicyError(f"{profile_id} lacks the fixed S0 tuple tie key")


def select_candidate(
    candidates: Sequence[Mapping[str, object]], *, eta_ref: Fraction,
) -> Mapping[str, object]:
    """Apply S0 exactly: service guard, exact score, BASE-first lexical ties."""

    if not candidates:
        raise C3SPolicyError("candidate catalog is empty")
    base_rows = [row for row in candidates if row.get("profile_id") == "BASE"]
    if len(base_rows) != 1 or candidates[0].get("profile_id") != "BASE":
        raise C3SPolicyError("catalog must contain BASE exactly once and first")
    base_nominal = base_rows[0].get("nominal")
    if not isinstance(base_nominal, Mapping):
        raise C3SPolicyError("BASE nominal metric is absent")
    base_metric = _metric(base_nominal, label="BASE nominal")
    threshold = int(base_metric["served"])
    seen: set[str] = set()
    eligible: list[tuple[Fraction, tuple[int, ...], Mapping[str, object]]] = []
    for row in candidates:
        profile_id = row.get("profile_id")
        nominal = row.get("nominal")
        actions = np.asarray(row.get("actions"))
        if not isinstance(profile_id, str) or not profile_id or profile_id in seen:
            raise C3SPolicyError("catalog profile IDs are malformed or duplicated")
        seen.add(profile_id)
        if not isinstance(nominal, Mapping):
            raise C3SPolicyError(f"{profile_id} nominal metric is absent")
        parsed = _metric(nominal, label=f"{profile_id} nominal")
        if parsed["opportunities"] != base_metric["opportunities"]:
            raise C3SPolicyError("candidate opportunity count differs from BASE")
        if actions.ndim != 1 or actions.dtype.kind not in "iu":
            raise C3SPolicyError(f"{profile_id} action vector is malformed")
        if int(parsed["served"]) >= threshold:
            eligible.append((nominal_score(parsed, eta_ref), _tie_key(row), row))
    if not eligible:
        raise C3SPolicyError("nominal service guard has no feasible candidate")
    best = max(row[0] for row in eligible)
    return min((row for row in eligible if row[0] == best), key=lambda row: row[1])[2]


def _metric_from_e1_payload(payload: object, *, label: str) -> dict[str, object]:
    try:
        return s0.metric_from_tape(payload, label=label)
    except s0.ProbeError as error:
        raise C3SPolicyError(str(error)) from error


def _evacuation_skeletons(
    observation: Any, reference: np.ndarray, base_profile: Any,
) -> tuple[dict[str, object], ...]:
    """Action-only projection of E1 ``build_joint_witness_catalog``."""

    origins: dict[tuple[int, int], list[int]] = {}
    for user in range(base_profile.users):
        if bool(base_profile.served[user]):
            origin = (
                int(base_profile.serving_satellite[user]),
                int(base_profile.serving_cell[user]),
            )
            origins.setdefault(origin, []).append(user)
    rows: list[dict[str, object]] = []
    for origin in sorted(origins):
        users = tuple(origins[origin])
        legal_maps = tuple(e1._legal_key_actions(observation, user) for user in users)
        common = set(legal_maps[0])
        for mapping in legal_maps[1:]:
            common.intersection_update(mapping)
        common.discard(origin)
        for destination in sorted(common):
            actions = np.asarray(reference, dtype=np.int64).copy()
            for user, mapping in zip(users, legal_maps, strict=True):
                actions[user] = mapping[destination]
            rows.append({
                "profile_id": (
                    f"J:{origin[0]}:{origin[1]}"
                    f"->{destination[0]}:{destination[1]}"
                ),
                "kind": "joint", "actions": actions,
                "tie_key": (2, *origin, *destination),
            })
    return tuple(rows)


def _lite_unilateral_skeletons(
    observation: Any, reference: np.ndarray, q12: np.ndarray,
) -> tuple[dict[str, object], ...]:
    """Keep each user's first Q12-ranked physical alternative to BASE."""

    values = np.asarray(q12)
    tables = tuple(observation.candidates.slot_tables)
    if (
        values.dtype != np.dtype(np.float32)
        or values.shape != (len(tables), f1.NUM_ACTIONS)
        or not np.all(np.isfinite(values))
    ):
        raise C3SPolicyError("lite catalog requires one finite float32 Q1+Q2 surface")
    try:
        # Besides producing all physically distinct choices, this donor rejects
        # ambiguous legal physical keys using the inherited E1/F1 rule.
        full_rows = f1.enumerate_unilateral_candidates(observation, reference)
    except Exception as error:
        raise C3SPolicyError("lite unilateral legality validation failed") from error
    by_user_action = {
        (int(row["focal_user"]), int(row["candidate_action"])): row
        for row in full_rows
    }
    rows: list[dict[str, object]] = []
    for user, table in enumerate(tables):
        mask = np.asarray(table.mask)
        legal = [int(action) for action in np.flatnonzero(mask).tolist()]
        base_action = int(reference[user])
        if not legal:
            if base_action != f1.NO_OP_ACTION:
                raise C3SPolicyError("empty-mask lite user does not have BASE NOOP")
            continue
        ranked = sorted(legal, key=lambda action: (-float(values[user, action]), action))
        if ranked[0] != base_action:
            raise C3SPolicyError("lite Q1+Q2 ranking does not reproduce BASE")
        # Starting after BASE naturally skips all BASE-equivalent slots because
        # the inherited full rows contain only physically different choices.
        for action in ranked[1:]:
            skeleton = by_user_action.get((user, action))
            if skeleton is None:
                continue
            rows.append(skeleton)
            break
    return tuple(rows)


@dataclass(frozen=True)
class FrozenCandidates:
    """Only current geometry, physical keys and legal masks needed by S0."""

    slot_tables: tuple[Any, ...]
    off_axis_deg: np.ndarray
    elevation_deg: np.ndarray
    window_satellite_ecef_km: np.ndarray
    window_norad_ids: np.ndarray


@dataclass(frozen=True)
class NominalPhysicsSnapshot:
    """Detached current-slot native-physics inputs; never a live environment."""

    candidates: FrozenCandidates
    grid: Any
    user_ecef_km: np.ndarray
    historical_satellite_ecef: tuple[tuple[int, tuple[tuple[int, np.ndarray], ...]], ...]
    physics: Any
    segments: tuple[Any, ...]
    previous_association: tuple[Any, ...]
    pending_segment_age: np.ndarray | None
    step_index: int

    def verify(self) -> str:
        """Authenticate every detached geometry/physics input used by evaluation."""

        arrays: list[np.ndarray] = []
        seen: set[int] = set()

        def collect(value: object) -> None:
            if isinstance(value, np.ndarray):
                arrays.append(value)
                return
            if value is None or isinstance(value, (bool, int, float, str, bytes, np.generic)):
                return
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            if isinstance(value, Mapping):
                children = tuple(value.items())
            elif isinstance(value, (tuple, list, set, frozenset)):
                children = tuple(enumerate(value))
            elif is_dataclass(value):
                children = tuple(
                    (definition.name, getattr(value, definition.name))
                    for definition in fields(value)
                )
            elif hasattr(value, "__dict__"):
                children = tuple(vars(value).items())
            else:
                children = ()
            for _name, child in children:
                collect(child)

        collect(self)
        users = len(self.candidates.slot_tables)
        if (
            users < 1
            or self.user_ecef_km.shape != (users, 3)
            or self.candidates.off_axis_deg.shape[0] != users
            or self.candidates.elevation_deg.shape[0] != users
            or self.candidates.window_satellite_ecef_km.shape[0] != users
            or self.candidates.window_norad_ids.shape[0] != users
            or self.pending_segment_age is not None
            and self.pending_segment_age.shape != (users,)
            or any(array.flags.writeable for array in arrays)
            or any(
                np.issubdtype(array.dtype, np.number) and not np.all(np.isfinite(array))
                for array in arrays
            )
        ):
            raise C3SPolicyError("detached nominal geometry/physics is malformed or mutable")
        _assert_no_prohibited_capabilities(self)
        return _structural_sha256(self)


class _DetachedDriver:
    def __init__(self, snapshot: NominalPhysicsSnapshot) -> None:
        self.grid = snapshot.grid
        self._users = snapshot.user_ecef_km
        self._historical = {
            int(offset): {int(norad): position for norad, position in positions}
            for offset, positions in snapshot.historical_satellite_ecef
        }

    def user_ecef_km(self) -> np.ndarray:
        return self._users

    def satellite_ecef_at(self, offset_steps: int) -> dict[int, np.ndarray]:
        try:
            return self._historical[int(offset_steps)]
        except KeyError as error:
            raise C3SPolicyError("nominal evaluator requested unsnapshotted geometry") from error


class _DetachedNominalContext:
    """Minimal receiver for the native current-slot physics equations."""

    def __init__(self, snapshot: NominalPhysicsSnapshot) -> None:
        self.num_users = len(snapshot.candidates.slot_tables)
        self.driver = _DetachedDriver(snapshot)
        self.physics = snapshot.physics
        self._segments = list(copy.deepcopy(snapshot.segments))
        self._previous_association = list(copy.deepcopy(snapshot.previous_association))
        self._pending_segment_age = (
            None if snapshot.pending_segment_age is None
            else np.array(snapshot.pending_segment_age, dtype=np.int64, copy=True)
        )
        self._step_index = snapshot.step_index

    def _draw_fading(
        self, satellite_ecef: Mapping[int, np.ndarray], _unused: object,
        _elevation_by_norad: Mapping[int, np.ndarray] | None = None, *, event: str = "direct",
    ) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray]]:
        del event
        order = sorted(satellite_ecef)
        return (
            {int(norad): np.ones(self.num_users, dtype=np.float64) for norad in order},
            {int(norad): np.zeros(self.num_users, dtype=np.float64) for norad in order},
        )

    def _warm_start_gain(self, uid: int, association: Any, historical: Any) -> float | None:
        from mcrl.env.step import StepEnvironment

        return StepEnvironment._warm_start_gain(self, uid, association, historical)


@dataclass(frozen=True)
class NominalSnapshotEvaluator:
    """Pure nominal evaluator constructed only from a detached snapshot."""

    snapshot: NominalPhysicsSnapshot
    physics_override: object | None = None

    def verify(self) -> str:
        return self.snapshot.verify()

    def evaluate(self, actions: np.ndarray) -> Any:
        from mcrl.env.action_contract import assert_selected_actions_valid
        from mcrl.env.step import StepEnvironment

        context = _DetachedNominalContext(self.snapshot)
        selected = assert_selected_actions_valid(actions, self.snapshot.candidates.slot_tables)
        resolver = (
            StepEnvironment._resolve_physics
            if self.physics_override is None
            else getattr(self.physics_override, "resolve_physics")
        )
        physics = resolver(context, self.snapshot.candidates, selected, None)
        return SimpleNamespace(
            resolution=physics["resolution"], radiating=physics["radiating"],
            link_power_w=physics["link_power_w"], link_rate_bps=physics["rate"],
            fixed_power_w=physics["fixed_power_w"], system_power_w=physics["system_power_w"],
        )


@dataclass(frozen=True)
class DecisionSnapshot:
    """The complete and capability-free §2 coordinator input."""

    native_state_matrix: np.ndarray
    legal_masks: np.ndarray
    slot_physical_keys: np.ndarray
    q12_proposal: np.ndarray
    base_actions: np.ndarray
    candidates: FrozenCandidates
    committed_association: tuple[Any, ...]
    committed_segments: tuple[Any, ...]
    committed_radiating: Any
    tracking_state: tuple[Any, Any]
    interval_s: float
    catalog: Catalog
    eta_ref: Fraction
    q_inference_seconds: float

    def verify(self) -> str:
        arrays = (
            self.native_state_matrix, self.legal_masks, self.slot_physical_keys,
            self.q12_proposal, self.base_actions,
        )
        users = self.legal_masks.shape[0]
        if (
            self.native_state_matrix.ndim != 2
            or self.legal_masks.dtype != np.bool_
            or self.legal_masks.shape != (users, f1.NUM_ACTIONS)
            or self.slot_physical_keys.shape != (users, f1.NUM_ACTIONS, 2)
            or self.q12_proposal.dtype != np.float32
            or self.q12_proposal.shape != self.legal_masks.shape
            or self.base_actions.shape != (users,)
            or any(array.flags.writeable for array in arrays)
            or not np.all(np.isfinite(self.native_state_matrix))
            or not np.all(np.isfinite(self.q12_proposal))
            or not math.isfinite(self.interval_s) or self.interval_s <= 0
            or not math.isfinite(self.q_inference_seconds) or self.q_inference_seconds < 0
        ):
            raise C3SPolicyError("pre-decision coordinator snapshot is malformed or mutable")
        _assert_no_prohibited_capabilities(self)
        return _structural_sha256(self)


def _copy_grid(grid: Any) -> Any:
    copied = copy.deepcopy(grid)
    for definition in fields(copied):
        value = getattr(copied, definition.name)
        if isinstance(value, np.ndarray):
            value.setflags(write=False)
    return copied


def _freeze_nested_arrays(value: object) -> None:
    """Make every copied ndarray in a capability-free snapshot read-only."""

    seen: set[int] = set()

    def visit(item: object) -> None:
        if isinstance(item, np.ndarray):
            item.setflags(write=False)
            return
        if item is None or isinstance(item, (bool, int, float, str, bytes, np.generic)):
            return
        identity = id(item)
        if identity in seen:
            return
        seen.add(identity)
        if isinstance(item, Mapping):
            children = tuple(item.items())
        elif isinstance(item, (tuple, list, set, frozenset)):
            children = tuple(enumerate(item))
        elif is_dataclass(item):
            children = tuple(
                (definition.name, getattr(item, definition.name))
                for definition in fields(item)
            )
        elif hasattr(item, "__dict__"):
            children = tuple(vars(item).items())
        else:
            children = ()
        for _name, child in children:
            visit(child)

    visit(value)


def _snapshot_inputs(
    adapter: "C3SPolicyAdapter", step_env: Any, observation: Any,
) -> tuple[DecisionSnapshot, NominalSnapshotEvaluator]:
    from mcrl.env.action_contract import SlotTable

    q_started = time.perf_counter()
    native, q12, base = e1._q12_surface_base_only(
        adapter.physical, adapter.frozen, step_env, observation
    )
    q_seconds = time.perf_counter() - q_started
    native.verify()
    original = observation.candidates
    tables = tuple(
        SlotTable(
            norad_ids=_readonly(table.norad_ids, dtype=np.int64),
            cell_ids=_readonly(table.cell_ids, dtype=np.int64),
            mask=_readonly(table.mask, dtype=np.bool_),
        )
        for table in tuple(original.slot_tables)
    )
    candidates = FrozenCandidates(
        slot_tables=tables,
        off_axis_deg=_readonly(original.off_axis_deg, dtype=np.float64),
        elevation_deg=_readonly(original.elevation_deg, dtype=np.float64),
        window_satellite_ecef_km=_readonly(
            original.window_satellite_ecef_km, dtype=np.float64
        ),
        window_norad_ids=_readonly(original.window_norad_ids, dtype=np.int64),
    )
    keys = _readonly(
        np.stack(
            [np.stack((table.norad_ids, table.cell_ids), axis=1) for table in tables],
            axis=0,
        ),
        dtype=np.int64,
    )
    pending = getattr(step_env, "_pending_segment_age", None)
    history: list[tuple[int, tuple[tuple[int, np.ndarray], ...]]] = []
    if int(getattr(step_env, "_step_index", -1)) == 0 and pending is not None:
        for age in sorted(set(int(value) for value in np.asarray(pending).tolist())):
            if age <= 0:
                continue
            positions = step_env.driver.satellite_ecef_at(-age)
            history.append((
                -age,
                tuple(
                    (int(norad), _readonly(position, dtype=np.float64))
                    for norad, position in sorted(positions.items())
                ),
            ))
    nominal_physics = NominalPhysicsSnapshot(
        candidates=candidates,
        grid=_copy_grid(step_env.driver.grid),
        user_ecef_km=_readonly(step_env.driver.user_ecef_km(), dtype=np.float64),
        historical_satellite_ecef=tuple(history),
        physics=replace(step_env.physics, fading_enabled=False),
        segments=tuple(copy.deepcopy(getattr(step_env, "_segments", ()))),
        previous_association=tuple(copy.deepcopy(getattr(step_env, "_previous_association", ()))),
        pending_segment_age=(None if pending is None else _readonly(pending, dtype=np.int64)),
        step_index=int(getattr(step_env, "_step_index", -1)),
    )
    snapshot = DecisionSnapshot(
        native_state_matrix=_readonly(native.state_matrix, dtype=np.float32),
        legal_masks=_readonly(native.action_masks, dtype=np.bool_),
        slot_physical_keys=keys,
        q12_proposal=_readonly(q12, dtype=np.float32),
        base_actions=_readonly(base, dtype=np.int64),
        candidates=candidates,
        committed_association=nominal_physics.previous_association,
        committed_segments=nominal_physics.segments,
        committed_radiating=copy.deepcopy(getattr(step_env, "_previous_radiating", None)),
        tracking_state=(copy.deepcopy(original.d2), copy.deepcopy(original.dwell)),
        interval_s=float(step_env.driver.config.ephemeris.time_step_s),
        catalog=adapter.catalog,
        eta_ref=adapter.eta_ref,
        q_inference_seconds=q_seconds,
    )
    evaluator = NominalSnapshotEvaluator(
        nominal_physics,
        physics_override=getattr(step_env, "diagnostic_physics_override", None),
    )
    _freeze_nested_arrays((snapshot, evaluator))
    snapshot.verify()
    evaluator.verify()
    return snapshot, evaluator


def build_s0_catalog(
    *, snapshot: DecisionSnapshot, evaluator: NominalSnapshotEvaluator,
    timing_out: dict[str, float] | None = None,
) -> tuple[dict[str, object], ...]:
    """Build the declared full or Q12-pruned-lite catalog in fixed order."""

    snapshot.verify()
    _assert_no_prohibited_capabilities(evaluator)
    reference = np.asarray(snapshot.base_actions)
    if reference.dtype.kind not in "iu" or reference.ndim != 1:
        raise C3SPolicyError("BASE action vector is malformed")
    if snapshot.catalog not in ("full", "lite"):
        raise C3SPolicyError("catalog must be 'full' or 'lite'")
    try:
        evaluation_started = time.perf_counter()
        # Origin membership comes from BASE's nominal/native service result.
        base_evaluation = evaluator.evaluate(reference)
        base_profile, base_link_power = f1.profile_from_evaluation(
            base_evaluation, interval_s=snapshot.interval_s
        )
        del base_link_power
        base_nominal = _metric_from_e1_payload(
            e1._profile_metrics(base_profile), label="BASE nominal evaluation"
        )
        base_evaluation_seconds = time.perf_counter() - evaluation_started
        enumeration_started = time.perf_counter()
        # F1 and E1 retain ownership of physical-key legality and ordering.
        observation = SimpleNamespace(candidates=snapshot.candidates)
        unilateral = (
            f1.enumerate_unilateral_candidates(observation, reference)
            if snapshot.catalog == "full"
            else _lite_unilateral_skeletons(
                observation, reference, snapshot.q12_proposal
            )
        )
        rows: list[dict[str, object]] = [{
            "profile_id": "BASE", "kind": "base", "tie_key": (0,),
            "actions": reference.astype(np.int64, copy=True), "nominal": base_nominal,
        }]
        for skeleton in unilateral:
            actions = np.asarray(skeleton["candidate_joint_actions"], dtype=np.int64)
            rows.append({
                "profile_id": f"U:{skeleton['focal_user']}:{skeleton['candidate_action']}",
                "kind": "unilateral", "actions": actions.copy(),
                "tie_key": (1, int(skeleton["focal_user"]), int(skeleton["candidate_action"])),
            })
        rows.extend(_evacuation_skeletons(observation, reference, base_profile))
        enumeration_seconds = time.perf_counter() - enumeration_started

        # One exhaustive S0 pass.  Physical aliases retain their catalog rows
        # but share the first nominal result by complete action-vector key.
        nominal_started = time.perf_counter()
        cache = {tuple(int(value) for value in reference.tolist()): base_nominal}
        for row in rows[1:]:
            actions = np.asarray(row["actions"], dtype=np.int64)
            key = tuple(int(value) for value in actions.tolist())
            if key not in cache:
                evaluation = evaluator.evaluate(actions)
                profile, _link_power = f1.profile_from_evaluation(
                    evaluation, interval_s=snapshot.interval_s
                )
                cache[key] = _metric_from_e1_payload(
                    e1._profile_metrics(profile), label=f"{row['profile_id']} nominal evaluation"
                )
            row["nominal"] = cache[key]
        nominal_seconds = time.perf_counter() - nominal_started
        if timing_out is not None:
            timing_out.update({
                "base_nominal_evaluation": base_evaluation_seconds,
                "enumeration": enumeration_seconds,
                "remaining_nominal_evaluations": nominal_seconds,
                "nominal_evaluation": base_evaluation_seconds + nominal_seconds,
                "unique_nominal_evaluations": float(len(cache)),
            })
    except C3SPolicyError:
        raise
    except Exception as error:
        raise C3SPolicyError("S0/E1 candidate catalog construction failed") from error
    return tuple(rows)


@dataclass(frozen=True)
class DecisionResult:
    actions: np.ndarray
    base_actions: np.ndarray
    profile_id: str
    catalog_size: int
    counts: Mapping[str, int]
    nominal: Mapping[str, object] = field(default_factory=dict)
    phase_wall_seconds: Mapping[str, float] = field(default_factory=dict)
    unique_nominal_evaluations: int = 0


DecisionFunction = Callable[[DecisionSnapshot, NominalSnapshotEvaluator], DecisionResult]


class C3SPolicyAdapter:
    """A state-neutral policy adapter around authenticated Q1/Q2 and S0."""

    def __init__(
        self, *, physical: Any, frozen: Any, eta_ref: Fraction | None = None,
        eta_config: Path = CONFIG_PATH, catalog: Catalog = "full",
        decision_function: DecisionFunction | None = None,
    ) -> None:
        self.physical = physical
        self.frozen = frozen
        self.eta_ref = load_eta_ref(eta_config) if eta_ref is None else Fraction(eta_ref)
        if self.eta_ref <= 0:
            raise C3SPolicyError("eta_ref must be positive")
        if catalog not in ("full", "lite"):
            raise C3SPolicyError("catalog must be 'full' or 'lite'")
        self.catalog: Catalog = catalog
        self._decision_function = decision_function or _real_decision
        self.decision_records: list[dict[str, object]] = []

    def select_actions(
        self, step_env: Any, observation: Any, rng: np.random.Generator,
    ) -> np.ndarray:
        if not isinstance(rng, np.random.Generator):
            raise C3SPolicyError("policy RNG must be numpy.random.Generator")
        try:
            before = _live_neutrality_fingerprint(step_env, rng)
        except Exception as error:
            raise C3SPolicyError("cannot snapshot the pre-decision environment") from error
        started = time.perf_counter()
        result: DecisionResult | None = None
        decision_error: BaseException | None = None
        try:
            snapshot, evaluator = _snapshot_inputs(self, step_env, observation)
            snapshot_digest = snapshot.verify()
            evaluator_digest = evaluator.verify()
            _assert_no_prohibited_capabilities((snapshot, evaluator))
            result = self._decision_function(snapshot, evaluator)
            if snapshot.verify() != snapshot_digest:
                raise C3SPolicyError("coordinator mutated its frozen input snapshot")
            if evaluator.verify() != evaluator_digest:
                raise C3SPolicyError(
                    "coordinator mutated its authenticated nominal geometry/physics"
                )
        except BaseException as error:
            decision_error = error
        elapsed = time.perf_counter() - started
        try:
            after = _live_neutrality_fingerprint(step_env, rng)
        except Exception as error:
            raise C3SPolicyError("cannot authenticate the post-decision environment") from error
        if after != before:
            raise C3SPolicyError(
                "snapshot construction or coordinator changed environment/RNG/field/tracking state"
            )
        if decision_error is not None:
            raise decision_error
        assert result is not None
        actions = np.asarray(result.actions)
        base = np.asarray(result.base_actions)
        if actions.dtype.kind not in "iu" or actions.ndim != 1 or actions.shape != base.shape:
            raise C3SPolicyError("selected complete action vector is malformed")
        changed_users = 0
        for uid, (action, base_action) in enumerate(zip(actions, base, strict=True)):
            selected_key = (
                (-1, -1) if int(action) == f1.NO_OP_ACTION
                else tuple(int(value) for value in snapshot.slot_physical_keys[uid, int(action)])
            )
            base_key = (
                (-1, -1) if int(base_action) == f1.NO_OP_ACTION
                else tuple(int(value) for value in snapshot.slot_physical_keys[uid, int(base_action)])
            )
            changed_users += selected_key != base_key
        self.decision_records.append({
            "decision_index": len(self.decision_records),
            "catalog": self.catalog,
            "wall_seconds_hex": elapsed.hex(),
            "catalog_size": result.catalog_size,
            "unique_nominal_evaluations": result.unique_nominal_evaluations,
            "profile_counts": dict(result.counts),
            "selected_profile_id": result.profile_id,
            "selected_nominal": {
                "total_bits_hex": float(result.nominal["total_bits"]).hex(),
                "total_energy_j_hex": float(result.nominal["total_energy_j"]).hex(),
                "served": int(result.nominal["served"]),
                "opportunities": int(result.nominal["opportunities"]),
            } if result.nominal else None,
            "action_changed": not np.array_equal(actions, base),
            "users_changed_vs_base": int(changed_users),
            "explicit_renewal_users": [],
            "executed_configuration_type": (
                "BASE" if result.profile_id == "BASE"
                else "UNILATERAL" if result.profile_id.startswith("U:")
                else "EVACUATION" if result.profile_id.startswith("J:")
                else "DECLARED_PROFILE"
            ),
            "nominal_convention": NOMINAL_CONVENTION,
            "phase_wall_seconds_hex": {
                name: float(value).hex() for name, value in result.phase_wall_seconds.items()
            },
            "process_lifetime_peak_rss_kib": int(
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            ),
            "rss_measurement_scope": (
                "PROCESS_LIFETIME_HIGH_WATER_MARK_NOT_ISOLATED_PER_ARM;"
                "FULL_EXECUTES_BEFORE_LITE"
            ),
        })
        return actions.astype(np.int64, copy=True)


def _real_decision(
    snapshot: DecisionSnapshot, evaluator: NominalSnapshotEvaluator,
) -> DecisionResult:
    phases: dict[str, float] = {"q_inference": snapshot.q_inference_seconds}
    catalog_started = time.perf_counter()
    catalog = build_s0_catalog(
        snapshot=snapshot, evaluator=evaluator, timing_out=phases,
    )
    phases["catalog_total"] = time.perf_counter() - catalog_started
    unique_nominal_evaluations = int(phases.pop("unique_nominal_evaluations"))
    selection_started = time.perf_counter()
    selected = select_candidate(catalog, eta_ref=snapshot.eta_ref)
    phases["selection"] = time.perf_counter() - selection_started
    counts = {
        kind: sum(row["kind"] == kind for row in catalog)
        for kind in ("base", "unilateral", "joint")
    }
    return DecisionResult(
        actions=np.asarray(selected["actions"], dtype=np.int64),
        base_actions=np.asarray(snapshot.base_actions, dtype=np.int64),
        profile_id=str(selected["profile_id"]),
        catalog_size=len(catalog),
        counts=counts,
        nominal=dict(selected["nominal"]),
        phase_wall_seconds=phases,
        unique_nominal_evaluations=unique_nominal_evaluations,
    )


__all__ = [
    "C3SPolicyAdapter", "C3SPolicyError", "DecisionResult", "build_s0_catalog",
    "fraction_payload", "load_eta_ref", "nominal_score", "select_candidate",
]
