#!/usr/bin/env python3
"""Run the TRAIN-only V0.25 v1.2 matrix probe.

``--dry-run`` and ``--rehearsal`` execute the real V0.25 radiation, ACM,
energy, target, set-decoder, and receipt path on a tiny deterministic provider.
The provider is converted to primitive snapshots; no environment or Satrec is
ever deep-copied.  A server launcher may replace only ``WORLD_PROVIDER_FACTORY``.
"""

from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import itertools
import importlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import time
import uuid
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from mcrl.errors import MCRLContractError  # noqa: E402
from mcrl.physics_v025.acm import ACM_MODES, rate_model, select_mode  # noqa: E402
from mcrl.physics_v025.architectures import RadiationConfig  # noqa: E402
from mcrl.physics_v025.adapter import (  # noqa: E402
    CellScore,
    build_shared_tape,
    discontinuities_from_event_ledger,
    score_setting,
)
from mcrl.physics_v025.batch import evaluate_ar_tdm_catalogue  # noqa: E402
from mcrl.physics_v025.calibration import (  # noqa: E402
    CalibrationObservation,
    CalibrationValues,
    NominalConfiguration,
    freeze_setting_calibration,
    nominal_greedy_reference,
    assert_calibration_world_separation,
)
from mcrl.physics_v025.constants_v025 import (  # noqa: E402
    BEAM_RF_CAP_W,
    DECISION_INTERVAL_S,
    SINR_MIN_DB,
    constant_manifest,
)
from mcrl.physics_v025.energy import (  # noqa: E402
    PRIMARY_IDLE_POWER_W,
    SENSITIVITY_IDLE_POWER_W,
    schedule_energy,
)
from mcrl.physics_v025.integration import InterruptionEvent  # noqa: E402
from mcrl.physics_v025.matrix import (  # noqa: E402
    ALL_SEALED_RUN_SETTINGS,
    LAUNCH_RUN_ORDER,
    MATRIX_SETTINGS,
    PRIMARY_RUN_SETTING,
    REGIME_RUN_SETTINGS,
    PhysicsSetting,
    SealedRunSetting,
    run_setting_for,
    shared_computation_plan,
)
from mcrl.physics_v025.parity import (  # noqa: E402
    DecisionProfile,
    common_action_bootstrap,
    declared_c3_oracle,
    demand_cap_profiles,
    production_c3,
    reoptimize_joint_by_regime,
    reward_endpoint_identity,
    trace_declared_target_decoder_parity,
)
from mcrl.physics_v025.state_v025 import SCHEMA_SHA256, schema_manifest  # noqa: E402
from mcrl.physics_v025.tapes import (  # noqa: E402
    CALIBRATION_WORLD_DOMAINS,
    PROBE_WORLD_DOMAINS,
    REFERENCE_CARRIERS,
    ExogenousWorldTape,
    PrimitiveWorldProvider,
    ProviderProtocolOutputs,
    TinySyntheticProvider,
    build_world_tape,
    canonical_bytes,
    corrected_boundary_rekey_rate,
    digest_payload,
    seed_from_domain,
)
from mcrl.physics_v025.targets import (  # noqa: E402
    NetworkOutcome,
    OffsetProjection,
    c1_difference_surplus,
    c2_persistence_forecast,
    c3_lcsrs_interaction,
    classify_physical_transition,
    network_objective,
    phi_qos,
    set_score_decomposition,
)


SCHEMA = "multi-catfish-mcrl-v025-matrix-probe-v1.5-stage4b"
UNIT_SCHEMA = f"{SCHEMA}-unit-receipt"
MERGE_SCHEMA = f"{SCHEMA}-merge-receipt"
DEFAULT_OUTPUT = REPO / "artifacts/v025-physics-successor/matrix-probe"
ATTEMPT_REGISTRY = HERE / "ATTEMPT-REGISTRY-2026-09.jsonl"
REFERENCE_SECONDS = 302.0
REFERENCE_WORKERS = 4
REFERENCE_EVALUATIONS = 3_840
ORCHESTRATION_RESERVE = 1.30
OVERNIGHT_CORE_HOURS = 160.0

ALL_NEUTRAL_CONTROL = "ALL_NEUTRAL_CONTROL"
ARMS = (
    "E1_U1",
    "E1_J1",
    "UNION_CATALOGUE_OPTIMUM",
    "S0_DEPLOYABLE",
    "FULL",
    "DROP_C1",
    "DROP_C2",
    "DROP_C3",
    "UNI",
    "S_UNI",
    ALL_NEUTRAL_CONTROL,
    "NULL",
    "RANDOM_FEASIBLE",
    "NOMINAL_GREEDY",
)
MARGINALS = {
    "C1": ("FULL", "DROP_C1"),
    "C2": ("FULL", "DROP_C2"),
    "C3": ("FULL", "DROP_C3"),
}
TOP_PROPOSALS = 2
COMPLETE_CATALOGUE_LIMIT = 4_096
PAIRWISE_TOP_K_USERS = 10
CATALOGUE_CAP = 3_200
DECISION_DEADLINE_S = 10.0
DECLARED_WORKERS = 1
SET_LEVEL_ARMS = ("S0_DEPLOYABLE", "FULL", "DROP_C1", "DROP_C2", "DROP_C3", "UNI", "S_UNI")
SUCCESSOR_DEVELOPMENT_ROLES = frozenset(
    {"PROBE", "CALIBRATION", "REHEARSAL", "KAT", "SYNTHETIC_REAL"}
)


def apply_deadline_fallback(
    selections: Mapping[str, Configuration],
    *,
    base: Configuration,
    missed: bool,
) -> dict[str, Configuration]:
    """Commit BASE for every deployable set arm after one whole-path miss."""

    result = dict(selections)
    if missed:
        for arm in SET_LEVEL_ARMS:
            result[arm] = base
    return result


def catalogue_definition() -> dict[str, object]:
    definition = {
        "version": "mcrl-v025-bounded-catalogue-v2",
        "complete_cartesian_limit": COMPLETE_CATALOGUE_LIMIT,
        "unilateral": "every live legal move for every user",
        "s0": "top-two nominal proposals plus frozen beam evacuations",
        "pairwise": {
            "top_k_users_by_nominal_unilateral_surplus": PAIRWISE_TOP_K_USERS,
            "top_legal_options_per_user": TOP_PROPOSALS,
        },
        "evacuation": "every user on each active beam to best live legal alternative",
        "zero_legal_user": "explicit null action; excluded from Cartesian factor",
        "cap": CATALOGUE_CAP,
    }
    return {**definition, "sha256": digest_payload(definition)}

# Server injection seam. The object is read sequentially and detached by
# build_world_tape; it is never cloned or retained in a receipt.
WORLD_PROVIDER_FACTORY: Callable[[], PrimitiveWorldProvider] = TinySyntheticProvider


class ProbeError(RuntimeError):
    pass


def _source_digest_for_factory(factory: Callable[[], object]) -> str:
    module = sys.modules.get(factory.__module__)
    path = None if module is None else getattr(module, "__file__", None)
    if path is None or not Path(path).is_file():
        return digest_payload({"module": factory.__module__, "name": factory.__qualname__})
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _code_authority_digest() -> str:
    digest = hashlib.sha256()
    for path in (Path(__file__), *sorted((REPO / "src/mcrl/physics_v025").glob("*.py"))):
        digest.update(path.relative_to(REPO).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def append_attempt(
    *,
    status: str,
    attempt_id: str,
    experiment: str,
    panel: str,
    cell: str,
    unit: str,
    authority: Mapping[str, object],
) -> str:
    """Append one fsynced hash-chained attempt record."""

    if status not in {"STARTED", "DONE", "ABANDONED"}:
        raise ProbeError("attempt status is invalid")
    import fcntl

    ATTEMPT_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with ATTEMPT_REGISTRY.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        lines = [line for line in handle.read().splitlines() if line]
        previous = None
        if lines:
            previous = json.loads(lines[-1])["record_sha256"]
        record = {
            "schema": f"{SCHEMA}-attempt-v1",
            "status": status,
            "attempt_id": attempt_id,
            "experiment": experiment,
            "panel": panel,
            "cell": cell,
            "unit": unit,
            "authority": dict(authority),
            "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "previous_record_sha256": previous,
        }
        record["record_sha256"] = digest_payload(record)
        handle.seek(0, os.SEEK_END)
        handle.write(canonical_bytes(record) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return str(record["record_sha256"])


def _attempt_records() -> list[dict[str, object]]:
    if not ATTEMPT_REGISTRY.is_file():
        return []
    records = [json.loads(line) for line in ATTEMPT_REGISTRY.read_text(encoding="ascii").splitlines() if line]
    previous = None
    for record in records:
        declared = record.get("record_sha256")
        unsigned = dict(record)
        unsigned.pop("record_sha256", None)
        if unsigned.get("previous_record_sha256") != previous or declared != digest_payload(unsigned):
            raise ProbeError("attempt registry hash chain is invalid")
        previous = declared
    return records


@dataclass(frozen=True)
class Configuration:
    configuration_id: str
    assignments: tuple[tuple[int, tuple[int, int] | None], ...]
    changed_users: int
    kind: str

    @property
    def mapping(self) -> dict[int, tuple[int, int] | None]:
        return dict(self.assignments)


@dataclass(frozen=True)
class EvaluatedProfile:
    config: Configuration
    score: CellScore
    energy_components: Mapping[str, float]
    lit_beam_seconds: float
    lit_satellite_seconds: float
    acm_mode_counts: Mapping[str, int]
    se_plateau_user_steps: int
    user_step_observations: int
    rf_cap_hits: int
    rf_transmission_observations: int
    treatment_t_same_instant_comparison: Mapping[str, object] | None

    @property
    def bits(self) -> float:
        return math.fsum(self.score.bits.values())

    @property
    def joules(self) -> float:
        return self.score.joules

    def outcome(self, *, phi: Fraction = Fraction()) -> NetworkOutcome:
        opportunities = max(1, len(self.score.bits)) * DECISION_INTERVAL_S
        decoding = math.fsum(self.score.decoding_time_s.values()) / opportunities
        useful = math.fsum(self.score.useful_time_s.values()) / opportunities
        return NetworkOutcome.build(
            bits=sum((Fraction(str(value)) for value in self.score.bits.values()), Fraction()),
            joules=self.joules,
            phi=phi,
            decoding_availability=min(1.0, max(0.0, decoding)),
            useful_availability=min(1.0, max(0.0, useful)),
            per_user_bits=self.score.bits,
        )


@dataclass
class EvaluationCounter:
    boundary_evaluations: int = 0


def _setting(label: str) -> PhysicsSetting:
    matches = [setting for setting in MATRIX_SETTINGS if setting.label == label]
    if len(matches) != 1:
        raise ProbeError(f"cell must be one of the {len(MATRIX_SETTINGS)} declared labels: {label!r}")
    return matches[0]


def _provider_for_run(run_setting: SealedRunSetting) -> PrimitiveWorldProvider:
    if run_setting.user_count == 100:
        return WORLD_PROVIDER_FACTORY()
    try:
        return WORLD_PROVIDER_FACTORY(user_count=run_setting.user_count)  # type: ignore[call-arg]
    except TypeError as error:
        raise ProbeError("R2 requires a provider factory with a user_count parameter") from error


def _world_domain(index: int, *, calibration: bool = False) -> str:
    domains = CALIBRATION_WORLD_DOMAINS if calibration else PROBE_WORLD_DOMAINS
    if index < 1 or index > len(domains):
        raise ProbeError("world index is outside the declared domain inventory")
    return domains[index - 1]


def _base_configuration(tape: ExogenousWorldTape, step_index: int, carrier: str) -> Configuration:
    action = next(
        row for row in tape.carriers if row.step_index == step_index and row.carrier == carrier
    )
    return Configuration(f"BASE:{carrier}", action.assignments, 0, "reference")


def _candidate_shortlist(boundary) -> set[tuple[int, tuple[int, int]]]:
    """Coarse provider shortlist, before successor visibility/D2 masks."""

    return {
        (row.user_id, row.identity)
        for row in boundary.candidates
        if row.coarse_shortlisted
    }


def _rekeyed_users(tape: ExogenousWorldTape, step_index: int) -> tuple[int, ...]:
    step = tape.steps[step_index]
    return () if step.arrays is not None else step.boundaries[0].cell_rekeyed_users


def _legal_options(
    tape: ExogenousWorldTape, step_index: int
) -> tuple[dict[int, tuple[tuple[int, int], ...]], dict[str, int]]:
    """Return decision-instant legal options without materialising array rows."""

    step = tape.steps[step_index]
    users = tuple(sorted(user.user_id for user in tape.user_layout))
    if step.arrays is not None:
        arrays = step.arrays
        live = arrays.visible[0] & arrays.d2_eligible[0] & arrays.cell_reachable[0]
        options: dict[int, list[tuple[float, tuple[int, int]]]] = {user: [] for user in users}
        for row in np.flatnonzero(live).tolist():
            user = int(arrays.users[int(arrays.row_user_column[row])])
            identity = tuple(int(value) for value in arrays.identities[row])
            options[user].append((float(arrays.slants_km[0, row]), identity))
        resolved = {
            user: tuple(identity for _slant, identity in sorted(set(rows)))
            for user, rows in options.items()
        }
        legal_count = int(np.count_nonzero(live))
        return resolved, {
            "coarse_shortlist_count": int(len(arrays.identities)),
            "full_successor_legal_count": legal_count,
            "candidate_shortlist_miss_count": 0,
        }
    first = step.boundaries[0]
    shortlist = _candidate_shortlist(first)
    full_legal = {(row.user_id, row.identity) for row in first.candidates if row.legal}
    misses = full_legal - shortlist
    resolved = {
        user: tuple(
            row.identity
            for row in sorted(
                (
                    row
                    for row in first.candidates
                    if row.user_id == user
                    and row.legal
                    and (row.user_id, row.identity) in shortlist
                ),
                key=lambda row: (row.slant_km, row.identity),
            )
        )
        for user in users
    }
    return resolved, {
        "coarse_shortlist_count": len(shortlist),
        "full_successor_legal_count": len(full_legal),
        "candidate_shortlist_miss_count": len(misses),
    }


def _configuration(
    base: Configuration,
    mapping: Mapping[int, tuple[int, int] | None],
    *,
    kind: str,
) -> Configuration:
    assignments = tuple(sorted(mapping.items()))
    base_map = base.mapping
    changed = sum(base_map[user] != identity for user, identity in assignments)
    encoded = ";".join(
        f"{user}:NULL" if identity is None else f"{user}:{identity[0]}:{identity[1]}"
        for user, identity in assignments
    )
    return Configuration(f"CFG:{encoded}", assignments, changed, kind)


def _catalogue_with_census(
    tape: ExogenousWorldTape,
    step_index: int,
    base: Configuration,
) -> tuple[tuple[Configuration, ...], dict[str, int]]:
    users = tuple(sorted(user.user_id for user in tape.user_layout))
    options, census = _legal_options(tape, step_index)
    factors = tuple(options[user] if options[user] else (None,) for user in users)
    product_size = math.prod(len(factor) for factor in factors)
    rows: list[Configuration] = [base]
    base_map = base.mapping
    if product_size <= COMPLETE_CATALOGUE_LIMIT:
        for product in itertools.product(*factors):
            mapping = dict(zip(users, product, strict=True))
            if mapping == base_map:
                continue
            rows.append(_configuration(base, mapping, kind="complete-cartesian"))
        mode = "complete-cartesian"
    else:
        # (i) every legal unilateral move; an option-less user keeps the
        # explicit null action and never collapses the other users' catalogue.
        unilaterals: dict[int, list[Configuration]] = {user: [] for user in users}
        for user in users:
            for identity in options[user]:
                if identity == base_map[user]:
                    continue
                mapping = dict(base_map)
                mapping[user] = identity
                row = _configuration(base, mapping, kind="unilateral")
                rows.append(row)
                unilaterals[user].append(row)

        # Nominal unilateral surplus ordering is deterministic here and can
        # be replaced by the exact nominal evaluator before sealing.  Legal
        # options arrive in increasing slant order, so the rank is the sealed
        # causal proxy and never uses realised fading.
        ranked_users = sorted(
            users,
            key=lambda user: (-len(unilaterals[user]), user),
        )[:PAIRWISE_TOP_K_USERS]

        # (ii) S0 top-two proposals assembled as complete deployable profiles.
        for proposal_rank in range(TOP_PROPOSALS):
            mapping = dict(base_map)
            for user in users:
                if len(unilaterals[user]) > proposal_rank:
                    mapping[user] = unilaterals[user][proposal_rank].mapping[user]
            if mapping != base_map:
                rows.append(_configuration(base, mapping, kind="s0-top-two"))

        # (iii) pairwise moves among top K, over each user's top two options.
        for first, second in itertools.combinations(ranked_users, 2):
            for first_row in unilaterals[first][:TOP_PROPOSALS]:
                for second_row in unilaterals[second][:TOP_PROPOSALS]:
                    mapping = dict(base_map)
                    mapping[first] = first_row.mapping[first]
                    mapping[second] = second_row.mapping[second]
                    rows.append(_configuration(base, mapping, kind="pairwise-top10-top2"))

        # (iv) one evacuation set per active beam, every incumbent user moved
        # to its best live legal alternative (or explicit null if none).
        for beam in sorted({identity for identity in base_map.values() if identity is not None}):
            mapping = dict(base_map)
            affected = [user for user in users if base_map[user] == beam]
            for user in affected:
                mapping[user] = next(
                    (identity for identity in options[user] if identity != beam),
                    None,
                )
            if mapping != base_map:
                rows.append(_configuration(base, mapping, kind="beam-evacuation"))
        mode = "bounded-union-v2"

    unique = {row.assignments: row for row in rows}
    ordered = (base,) + tuple(
        sorted(
            (row for assignments, row in unique.items() if assignments != base.assignments),
            key=lambda row: row.configuration_id,
        )
    )
    if mode != "complete-cartesian" and len(ordered) > CATALOGUE_CAP:
        raise ProbeError(f"bounded catalogue exceeded sealed cap {CATALOGUE_CAP}")
    return ordered, {
        **census,
        "complete_cartesian_size": product_size,
        "catalogue_mode": mode,
        "null_action_users": sum(not options[user] for user in users),
        "bounded_catalogue_count": len(ordered),
    }


def _catalogue(tape: ExogenousWorldTape, step_index: int, base: Configuration) -> tuple[Configuration, ...]:
    return _catalogue_with_census(tape, step_index, base)[0]


def _energy_fields(
    shared,
    setting: PhysicsSetting,
    *,
    circuit_power_per_active_chain_w: float = 0.338,
) -> tuple[dict[str, float], float, float]:
    idle = SENSITIVITY_IDLE_POWER_W if setting.standby == "f" else PRIMARY_IDLE_POWER_W
    boundary = []
    for item in shared.integrated:
        receipt = schedule_energy(
            shared.inventory,
            ((slot.fraction, dict(slot.beam_rf_w)) for slot in item.radiation.slots),
            duration_s=1.0,
            idle_power_w=idle,
            circuit_power_per_active_chain_w=circuit_power_per_active_chain_w,
        )
        beams = {beam for slot in item.radiation.slots for beam, rf in slot.beam_rf_w if rf > 0.0}
        satellites = {beam[0] for beam in beams}
        boundary.append((receipt, float(len(beams)), float(len(satellites))))
    fields = ("pa_j", "circuit_j", "standby_j", "baseband_j", "bus_j")
    if setting.integration == "T":
        receipt, beams, satellites = boundary[0]
        return (
            {name: getattr(receipt, name) * DECISION_INTERVAL_S for name in fields},
            beams * DECISION_INTERVAL_S,
            satellites * DECISION_INTERVAL_S,
        )
    components = {name: 0.0 for name in fields}
    beam_seconds = satellite_seconds = 0.0
    for left, right in zip(boundary, boundary[1:]):
        for name in fields:
            components[name] += 0.5 * (getattr(left[0], name) + getattr(right[0], name)) * 0.640
        beam_seconds += 0.5 * (left[1] + right[1]) * 0.640
        satellite_seconds += 0.5 * (left[2] + right[2]) * 0.640
    return components, beam_seconds, satellite_seconds


def _physical_events(
    before: Configuration,
    after: Configuration,
    *,
    cell_rekeyed_users: Iterable[int] = (),
):
    """Build the one authoritative ledger from physical assignment identities."""

    before_map = before.mapping
    rekeyed = frozenset(cell_rekeyed_users)
    return tuple(
        classify_physical_transition(
            user_id=user,
            before=before_map[user],
            after=identity,
            cell_rekey=user in rekeyed,
            was_previously_served=before_map[user] is not None,
        )
        for user, identity in after.assignments
    )


def _interruption_events(
    before: Configuration,
    after: Configuration,
    decision_time_s: float,
    *,
    cell_rekeyed_users: Iterable[int] = (),
) -> tuple[InterruptionEvent, ...]:
    """Translate that ledger to H/SH useful-time removals at the decision instant."""

    mapping = {
        "beam_change": "same_satellite_beam_change",
        "satellite_change": "satellite_change",
        "cell_rekey": "same_satellite_beam_change",
        "initial_entry": "initial_entry",
        "reentry": "reentry",
    }
    return tuple(
        InterruptionEvent(event.user_id, decision_time_s, mapping[event.kind])
        for event in _physical_events(
            before, after, cell_rekeyed_users=cell_rekeyed_users
        )
        if event.kind in mapping
    )


class StepEvaluator:
    """Architecture/configuration cache; treatment cells only rescore it."""

    def __init__(
        self,
        tape: ExogenousWorldTape,
        setting: PhysicsSetting,
        step_index: int,
        *,
        transition_from: Configuration,
        cell_rekeyed_users: Iterable[int] = (),
        field: str = "realised",
        counter: EvaluationCounter | None = None,
        run_setting: SealedRunSetting | None = None,
    ) -> None:
        self.tape = tape
        self.setting = setting
        self.step_index = step_index
        self.transition_from = transition_from
        self.cell_rekeyed_users = tuple(cell_rekeyed_users)
        self.field = field
        self.counter = counter
        self.run_setting = run_setting_for(setting.label) if run_setting is None else run_setting
        self._shared: dict[str, object] = {}
        self._evaluated: dict[str, EvaluatedProfile] = {}
        self._invalid: set[str] = set()
        self.physical_evaluations = 0

    def evaluate_many(self, configs: Sequence[Configuration]) -> None:
        """Populate the cache through the dense real-world ``a-r0`` path."""

        missing = [row for row in configs if row.configuration_id not in self._evaluated]
        step = self.tape.steps[self.step_index]
        if not missing or step.arrays is None or self.setting.label != "a-r0":
            for config in missing:
                self.evaluate(config)
            return
        arrays = step.arrays
        row_of = arrays._row_index()
        users = tuple(int(value) for value in arrays.users)
        selected = np.full((len(missing), len(users)), -1, dtype=np.int64)
        for config_index, config in enumerate(missing):
            mapping = config.mapping
            for user_column, user in enumerate(users):
                identity = mapping[user]
                if identity is not None:
                    selected[config_index, user_column] = row_of[(user, identity)]
        result = evaluate_ar_tdm_catalogue(
            arrays,
            selected,
            field=self.field,
            rate_target_bps=self.run_setting.rate_target_bps,
            circuit_power_per_active_chain_w=self.run_setting.circuit_power_per_active_chain_w,
        )
        mode_names = ("NO_MODE",) + tuple(row.name for row in ACM_MODES)
        for index, config in enumerate(missing):
            if not bool(result.valid[index]):
                self._invalid.add(config.configuration_id)
                continue
            per_user_bits = {
                user: float(result.bits[index, column])
                for column, user in enumerate(users)
            }
            decoding = {
                user: float(result.decoding_time_s[index, column])
                for column, user in enumerate(users)
            }
            served = {user: decoding[user] > 0.0 for user in users}
            feasible = {
                user: bool(result.feasible[index, column])
                for column, user in enumerate(users)
            }
            attained = {
                user: bool(result.attained[index, column])
                for column, user in enumerate(users)
            }
            score = CellScore(
                self.setting,
                per_user_bits,
                float(result.joules[index]),
                decoding,
                dict(decoding),
                served,
                attained,
                feasible,
                None,
                self.run_setting.rate_target_bps,
                True,
                float(result.residual_w[index]),
            )
            components = {
                "pa_j": float(result.pa_j[index]),
                "circuit_j": float(result.circuit_j[index]),
                "standby_j": 0.0,
                "baseband_j": float(result.baseband_j[index]),
                "bus_j": 0.0,
            }
            counts = {
                name: int(result.mode_counts[index, column])
                for column, name in enumerate(mode_names)
                if result.mode_counts[index, column]
            }
            profile = EvaluatedProfile(
                config,
                score,
                components,
                (
                    0.0
                    if self.run_setting.circuit_power_per_active_chain_w == 0.0
                    else components["circuit_j"] / self.run_setting.circuit_power_per_active_chain_w
                ),
                components["baseband_j"] / 0.200,
                counts,
                int(result.plateau_users[index]),
                len(users),
                int(result.cap_hits[index]),
                int(result.transmissions[index]),
                None,
            )
            self._evaluated[config.configuration_id] = profile
        evaluations = len(missing) * 48
        self.physical_evaluations += evaluations
        if self.counter is not None:
            self.counter.boundary_evaluations += evaluations

    def evaluate(self, config: Configuration) -> EvaluatedProfile:
        if config.configuration_id in self._evaluated:
            return self._evaluated[config.configuration_id]
        geometry = self.tape.geometry_for(step_index=self.step_index, assignments=config.mapping)
        shared = build_shared_tape(
            self.setting.architecture,
            geometry,
            self.tape.inventory,
            field=self.field,  # type: ignore[arg-type]
            roster=tuple(user.user_id for user in self.tape.user_layout),
            config=RadiationConfig(rate_target_bps=self.run_setting.rate_target_bps),
            circuit_power_per_active_chain_w=self.run_setting.circuit_power_per_active_chain_w,
        )
        event_ledger = _interruption_events(
            self.transition_from,
            config,
            shared.integrated[0].time_s,
            cell_rekeyed_users=self.cell_rekeyed_users,
        )
        score = score_setting(
            shared,
            self.setting,
            discontinuities=discontinuities_from_event_ledger(
                shared, event_ledger
            ),
            interruptions=event_ledger,
        )
        if not score.valid:
            raise ProbeError(f"invalid power certificate for {config.configuration_id}")
        components, beam_seconds, satellite_seconds = _energy_fields(
            shared,
            self.setting,
            circuit_power_per_active_chain_w=self.run_setting.circuit_power_per_active_chain_w,
        )
        if not math.isclose(math.fsum(components.values()), score.joules, rel_tol=1e-10, abs_tol=1e-8):
            raise ProbeError("energy-component reconstruction disagrees with cell score")
        mode_counts: dict[str, int] = {}
        cap_hits = transmissions = 0
        top_mode = max(ACM_MODES, key=lambda row: row.efficiency_bit_per_symbol)
        user_on_plateau: dict[int, bool] = {}
        for boundary in shared.integrated:
            for slot in boundary.radiation.slots:
                for tx in slot.transmissions:
                    mode = select_mode(tx.sinr)
                    name = "NO_MODE" if mode is None else mode.name
                    mode_counts[name] = mode_counts.get(name, 0) + 1
                    user_on_plateau[tx.user_id] = user_on_plateau.get(tx.user_id, True) and mode == top_mode
                    transmissions += 1
                    cap_hits += int(math.isclose(tx.rf_power_w, BEAM_RF_CAP_W, rel_tol=0.0, abs_tol=1e-9))
        t_comparison = None
        if self.setting.integration == "T":
            integral_setting = next(
                row
                for row in MATRIX_SETTINGS
                if row.architecture == self.setting.architecture and row.treatment == "0"
            )
            integral_score = score_setting(
                shared,
                integral_setting,
                discontinuities=discontinuities_from_event_ledger(
                    shared, event_ledger
                ),
                interruptions=event_ledger,
            )
            t_comparison = {
                "snapshot_convention": "left-endpoint decision-time zero-order hold",
                "same_instant_integral": {
                    "bits": math.fsum(integral_score.bits.values()),
                    "joules": integral_score.joules,
                },
                "left_snapshot": {"bits": math.fsum(score.bits.values()), "joules": score.joules},
            }
        result = EvaluatedProfile(
            config,
            score,
            components,
            beam_seconds,
            satellite_seconds,
            mode_counts,
            sum(user_on_plateau.values()),
            len(user_on_plateau),
            cap_hits,
            transmissions,
            t_comparison,
        )
        self._shared[config.configuration_id] = shared
        self._evaluated[config.configuration_id] = result
        self.physical_evaluations += len(shared.integrated)
        if self.counter is not None:
            self.counter.boundary_evaluations += len(shared.integrated)
        return result

    def required_power(self, config: Configuration) -> tuple[float, float]:
        self.evaluate(config)
        shared = self._shared[config.configuration_id]
        powers = [
            tx.rf_power_w
            for boundary in shared.integrated  # type: ignore[attr-defined]
            for slot in boundary.radiation.slots
            for tx in slot.transmissions
        ]
        return (max(powers, default=0.0), BEAM_RF_CAP_W)


def _nominal_configuration(config: Configuration, profile: EvaluatedProfile) -> NominalConfiguration:
    return NominalConfiguration(
        config.configuration_id,
        config.assignments,
        profile.bits,
        profile.joules,
        sum(profile.score.served_phy.values()),
    )


def _calibrate(
    setting: PhysicsSetting,
    run_setting: SealedRunSetting | None = None,
) -> CalibrationValues:
    run_setting = run_setting_for(setting.label) if run_setting is None else run_setting
    observations = []
    for index, domain in enumerate(CALIBRATION_WORLD_DOMAINS, start=1):
        tape = build_world_tape(
            domain=domain,
            provider=_provider_for_run(run_setting),
            steps=1,
            start_time_s=0.0,
        )
        base = _base_configuration(tape, 0, "nearest-eligible")
        catalog = _catalogue(tape, 0, base)
        nominal_evaluator = StepEvaluator(
            tape,
            setting,
            0,
            transition_from=base,
            cell_rekeyed_users=_rekeyed_users(tape, 0),
            field="nominal",
            run_setting=run_setting,
        )
        nominal_profiles = {
            config.configuration_id: nominal_evaluator.evaluate(config) for config in catalog
        }
        chosen_nominal = nominal_greedy_reference(
            _nominal_configuration(config, nominal_profiles[config.configuration_id])
            for config in catalog
        )
        chosen = next(config for config in catalog if config.configuration_id == chosen_nominal.configuration_id)
        evaluated = StepEvaluator(
            tape,
            setting,
            0,
            transition_from=base,
            cell_rekeyed_users=_rekeyed_users(tape, 0),
            run_setting=run_setting,
        ).evaluate(chosen)
        observations.append(
            CalibrationObservation.build(
                world_domain=domain,
                bits=evaluated.bits,
                joules=evaluated.joules,
                users=len(tape.user_layout),
                time_s=DECISION_INTERVAL_S,
                selected_configuration_id=chosen.configuration_id,
            )
        )
    frozen = freeze_setting_calibration(setting=setting, observations=observations)
    return replace(
        frozen,
        setting_label=run_setting.run_id,
        setting_digest=run_setting.digest,
    )


def _objective(profile: EvaluatedProfile, calibration: CalibrationValues) -> Fraction:
    return network_objective(
        profile.outcome(),
        lambda_bits_per_j=calibration.lambda_bits_per_j,
        eta_ref=calibration.eta_ref,
        kappa_bits_per_user_s=calibration.kappa_bits_per_user_s,
    )


def _best(
    rows: Iterable[EvaluatedProfile], calibration: CalibrationValues
) -> EvaluatedProfile:
    return min(rows, key=lambda row: (-_objective(row, calibration), row.config.configuration_id))


def _phi_for(
    base: Configuration,
    candidate: Configuration,
    *,
    cell_rekeyed_users: Iterable[int] = (),
) -> Fraction:
    return phi_qos(
        _physical_events(
            base, candidate, cell_rekeyed_users=cell_rekeyed_users
        )
    )


def _forecast_rows(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    anchor_step: int,
    config: Configuration,
    carrier: str,
    counter: EvaluationCounter,
    focal_user: int,
    run_setting: SealedRunSetting | None = None,
) -> tuple[OffsetProjection, ...]:
    rows = []
    for offset in range(1, 4):
        projected_step = anchor_step + offset
        base = _base_configuration(tape, projected_step, carrier)
        # Persist physical identities; Geometry is rebuilt at the projected boundary.
        persisted = Configuration(config.configuration_id, config.assignments, config.changed_users, config.kind)
        evaluator = StepEvaluator(
            tape,
            setting,
            projected_step,
            transition_from=base,
            cell_rekeyed_users=_rekeyed_users(tape, projected_step),
            field="nominal",
            counter=counter,
            run_setting=run_setting,
        )
        try:
            result = evaluator.evaluate(persisted)
            valid = True
        except (MCRLContractError, ProbeError):
            result = None
            valid = False
        required, cap = 0.0, BEAM_RF_CAP_W
        margins = []
        ses = []
        if valid and result is not None:
            required, cap = evaluator.required_power(result.config)
            shared = evaluator._shared[result.config.configuration_id]
            model = rate_model(setting.rate)
            for boundary in shared.integrated:  # type: ignore[attr-defined]
                for slot in boundary.radiation.slots:
                    for tx in slot.transmissions:
                        margins.append(10.0 * math.log10(tx.sinr) - SINR_MIN_DB)
                        ses.append(model.rate_bps(tx.sinr, tx.bandwidth_hz) / tx.bandwidth_hz)
            survives = bool(result.score.served_phy.get(focal_user, False))
            outcome = result.outcome()
        else:
            survives = False
            outcome = NetworkOutcome.build(
                bits=0,
                joules=0,
                phi=0,
                decoding_availability=0,
                useful_availability=0,
            )
        rows.append(
            OffsetProjection(
                offset,
                valid,
                survives,
                outcome,
                True,
                required if setting.architecture in {"a-r", "a′-r"} else None,
                cap if setting.architecture in {"a-r", "a′-r"} else None,
                min(margins, default=-math.inf) if margins else -100.0,
                math.fsum(ses) / len(ses) if ses else 0.0,
            )
        )
    return tuple(rows)


def _factor_scores(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    carrier: str,
    base: Configuration,
    incumbent: Configuration,
    catalog: Sequence[Configuration],
    evaluated: Mapping[str, EvaluatedProfile],
    calibration: CalibrationValues,
    counter: EvaluationCounter,
) -> tuple[
    dict[str, dict[tuple[int, tuple[int, int] | None], Fraction]],
    Fraction,
    int,
]:
    base_profile = evaluated[base.configuration_id]
    result = {name: {} for name in ("C1", "C2", "C3")}
    for config in catalog:
        if config.changed_users != 1:
            continue
        user = next(
            user for user, identity in config.assignments if dict(base.assignments)[user] != identity
        )
        identity = dict(config.assignments)[user]
        c1 = c1_difference_surplus(
            evaluated[config.configuration_id].outcome(
                phi=_phi_for(
                    incumbent,
                    config,
                    cell_rekeyed_users=_rekeyed_users(tape, step_index),
                )
            ),
            base_profile.outcome(
                phi=_phi_for(
                    incumbent,
                    base,
                    cell_rekeyed_users=_rekeyed_users(tape, step_index),
                )
            ),
            lambda_bits_per_j=calibration.lambda_bits_per_j,
            eta_ref=calibration.eta_ref,
            kappa_bits_per_user_s=calibration.kappa_bits_per_user_s,
        )
        result["C1"][(user, identity)] = c1.normalized_total
        candidate_forecast = _forecast_rows(
            tape=tape,
            setting=setting,
            anchor_step=step_index,
            config=config,
            carrier=carrier,
            counter=counter,
            focal_user=user,
        )
        default_forecast = _forecast_rows(
            tape=tape,
            setting=setting,
            anchor_step=step_index,
            config=base,
            carrier=carrier,
            counter=counter,
            focal_user=user,
        )
        c2 = c2_persistence_forecast(
            candidate_forecast,
            default_forecast,
            lambda_bits_per_j=calibration.lambda_bits_per_j,
            eta_ref=calibration.eta_ref,
            kappa_bits_per_user_s=calibration.kappa_bits_per_user_s,
        )
        result["C2"][(user, identity)] = c2.normalized_total
    users = tuple(user for user, _ in base.assignments)
    interaction_sum = Fraction()
    interaction_count = 0
    for user0, user1 in itertools.combinations(users, 2):
        uni0 = [row for row in catalog if row.changed_users == 1 and dict(row.assignments)[user0] != dict(base.assignments)[user0]]
        uni1 = [row for row in catalog if row.changed_users == 1 and dict(row.assignments)[user1] != dict(base.assignments)[user1]]
        for first in uni0:
            for second in uni1:
                merged_map = dict(base.assignments)
                merged_map[user0] = dict(first.assignments)[user0]
                merged_map[user1] = dict(second.assignments)[user1]
                joint = next((row for row in catalog if row.mapping == merged_map), None)
                if joint is None:
                    continue
                interaction = c3_lcsrs_interaction(
                    coalition_users=(user0, user1),
                    f00=base_profile.outcome(),
                    f10=evaluated[first.configuration_id].outcome(),
                    f01=evaluated[second.configuration_id].outcome(),
                    f11=evaluated[joint.configuration_id].outcome(),
                    lambda_bits_per_j=calibration.lambda_bits_per_j,
                    eta_ref=calibration.eta_ref,
                    kappa_bits_per_user_s=calibration.kappa_bits_per_user_s,
                )
                interaction_sum += interaction.psi
                interaction_count += 1
                for user, z3 in interaction.z3_by_user:
                    identity = merged_map[user]
                    old = result["C3"].get((user, identity))
                    normalized = z3 / calibration.kappa_bits_per_user_s
                    if old is None or normalized > old:
                        result["C3"][(user, identity)] = normalized
    return result, interaction_sum, interaction_count


def _configuration_factor_scores(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    carrier: str,
    base: Configuration,
    incumbent: Configuration,
    catalog: Sequence[Configuration],
    evaluator: StepEvaluator,
    calibration: CalibrationValues,
    counter: EvaluationCounter,
    c2_horizon_offsets: int = 3,
    run_setting: SealedRunSetting | None = None,
) -> tuple[dict[str, dict[str, object]], Fraction, int]:
    """Score every complete configuration by the sealed v1.5 decomposition."""

    base_profile = evaluator.evaluate(base)
    base_map = base.mapping
    singleton_c2: dict[tuple[int, tuple[int, int] | None], Fraction] = {}
    default_forecasts: dict[int, tuple[OffsetProjection, ...]] = {}
    result: dict[str, dict[str, object]] = {}
    interaction_sum = Fraction()
    interaction_count = 0
    for config in catalog:
        selected_map = config.mapping
        changed = tuple(
            user for user in sorted(base_map) if selected_map[user] != base_map[user]
        )
        outcomes: dict[frozenset[int], NetworkOutcome] = {}
        for size in range(len(changed) + 1):
            for subset_tuple in itertools.combinations(changed, size):
                subset = frozenset(subset_tuple)
                mapping = dict(base_map)
                for user in subset:
                    mapping[user] = selected_map[user]
                subset_config = _configuration(base, mapping, kind="v15-powerset")
                outcomes[subset] = evaluator.evaluate(subset_config).outcome()
        candidate_phi = _phi_for(
            incumbent,
            config,
            cell_rekeyed_users=_rekeyed_users(tape, step_index),
        )
        base_phi = _phi_for(
            incumbent,
            base,
            cell_rekeyed_users=_rekeyed_users(tape, step_index),
        )
        decomposition = set_score_decomposition(
            coalition_users=changed,
            outcomes_by_subset=outcomes,
            lambda_bits_per_j=calibration.lambda_bits_per_j,
            eta_ref=calibration.eta_ref,
            kappa_bits_per_user_s=calibration.kappa_bits_per_user_s,
            phi_difference=candidate_phi - base_phi,
        )
        c2 = Fraction()
        for user in changed:
            key = (user, selected_map[user])
            if key not in singleton_c2:
                singleton_map = dict(base_map)
                singleton_map[user] = selected_map[user]
                singleton_config = _configuration(base, singleton_map, kind="v15-singleton")
                if user not in default_forecasts:
                    default_forecasts[user] = _forecast_rows(
                        tape=tape,
                        setting=setting,
                        anchor_step=step_index,
                        config=base,
                        carrier=carrier,
                        counter=counter,
                        focal_user=user,
                        run_setting=run_setting,
                    )
                projection = c2_persistence_forecast(
                    _forecast_rows(
                        tape=tape,
                        setting=setting,
                        anchor_step=step_index,
                        config=singleton_config,
                        carrier=carrier,
                        counter=counter,
                        focal_user=user,
                        run_setting=run_setting,
                    ),
                    default_forecasts[user],
                    lambda_bits_per_j=calibration.lambda_bits_per_j,
                    eta_ref=calibration.eta_ref,
                    kappa_bits_per_user_s=calibration.kappa_bits_per_user_s,
                    horizon_offsets=c2_horizon_offsets,
                )
                singleton_c2[key] = projection.normalized_total
            c2 += singleton_c2[key]
        result[config.configuration_id] = {
            "C1": decomposition.factor_c1,
            "C2": c2,
            "C3": decomposition.c3,
            "d_by_user": decomposition.d_by_user,
            "psi_A": decomposition.interaction_bits,
            "shapley_interaction_by_user": decomposition.shapley_interaction_by_user,
            "joint_change_bits": decomposition.joint_change_bits,
            "c1_physical_core": decomposition.c1,
            "phi_difference": decomposition.phi_difference,
        }
        if changed:
            interaction_sum += decomposition.interaction_bits
        if len(changed) > 1:
            interaction_count += 1
    return result, interaction_sum, interaction_count


def _set_score_select(
    *,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[str, object]],
    include: Sequence[str],
) -> Configuration:
    """Select one atomic configuration from the exact declared factor sum."""

    scored = [
        (
            sum((Fraction(factors[row.configuration_id][name]) for name in include), Fraction()),
            row.configuration_id,
            row,
        )
        for row in catalog
    ]
    return min(scored, key=lambda row: (-row[0], row[1]))[2]


def _independent_proposal(
    *,
    base: Configuration,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[tuple[int, tuple[int, int] | None], Fraction]],
    include: Sequence[str],
) -> Configuration:
    assignments = dict(base.assignments)
    for user in sorted(assignments):
        candidates = []
        for config in catalog:
            if config.changed_users != 1:
                continue
            identity = dict(config.assignments)[user]
            if identity == assignments[user]:
                continue
            score = sum((factors[name].get((user, identity), Fraction()) for name in include), Fraction())
            candidates.append((score, identity))
        if candidates:
            score, identity = min(candidates, key=lambda row: (-row[0], row[1]))
            if score > 0:
                assignments[user] = identity
    return next(
        (row for row in catalog if row.mapping == assignments),
        base,
    )


def _set_select(
    *,
    catalog: Sequence[Configuration],
    evaluated: Mapping[str, EvaluatedProfile],
    factors: Mapping[str, Mapping[tuple[int, tuple[int, int] | None], Fraction]],
    include: Sequence[str],
    base: Configuration,
    calibration: CalibrationValues,
) -> Configuration:
    del evaluated, calibration
    base_map = dict(base.assignments)
    scored = []
    for config in catalog:
        bonus = Fraction()
        for user, identity in config.assignments:
            if identity == base_map[user]:
                continue
            bonus += sum((factors[name].get((user, identity), Fraction()) for name in include), Fraction())
        # Factor arms compare only the declared target sum.  Exact F is
        # reserved for the U1/J1/union ceiling arms and S_UNI comparator.
        scored.append((bonus, config.configuration_id, config))
    return min(scored, key=lambda row: (-row[0], row[1]))[2]


def _unilateral_factor_select(
    *,
    base: Configuration,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[tuple[int, tuple[int, int] | None], Fraction]],
) -> Configuration:
    candidates = [base] + [row for row in catalog if row.changed_users == 1]
    return _set_select(
        catalog=candidates,
        evaluated={},
        factors=factors,
        include=("C1", "C2", "C3"),
        base=base,
        calibration=None,  # type: ignore[arg-type]
    )


def _s_uni_select(
    *,
    base: Configuration,
    tape: ExogenousWorldTape,
    step_index: int,
    evaluator: StepEvaluator,
    calibration: CalibrationValues,
    deadline_at: float,
) -> tuple[Configuration, int, float, bool]:
    """Information-matched exact single-user best response to convergence."""

    started = time.perf_counter()
    options, _census = _legal_options(tape, step_index)
    current = base
    iterations = 0
    while True:
        if time.perf_counter() >= deadline_at:
            return base, iterations, time.perf_counter() - started, True
        current_profile = evaluator.evaluate(current)
        best = current
        best_value = _objective(current_profile, calibration)
        for user in sorted(options):
            for identity in options[user]:
                if identity == current.mapping[user]:
                    continue
                mapping = current.mapping
                mapping[user] = identity
                candidate = _configuration(base, mapping, kind="s-uni-iterate")
                profile = evaluator.evaluate(candidate)
                if sum(profile.score.served_phy.values()) < sum(
                    evaluator.evaluate(base).score.served_phy.values()
                ):
                    continue
                value = _objective(profile, calibration)
                if value > best_value or (
                    value == best_value and candidate.configuration_id < best.configuration_id
                ):
                    best, best_value = candidate, value
            if time.perf_counter() >= deadline_at:
                return base, iterations, time.perf_counter() - started, True
        if best.assignments == current.assignments:
            return current, iterations, time.perf_counter() - started, False
        current = best
        iterations += 1


def _s0_select(
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    base: Configuration,
    catalog: Sequence[Configuration],
    counter: EvaluationCounter,
    run_setting: SealedRunSetting | None = None,
) -> tuple[Configuration, tuple[str, ...], Configuration]:
    nominal_evaluator = StepEvaluator(
        tape,
        setting,
        step_index,
        transition_from=base,
        cell_rekeyed_users=_rekeyed_users(tape, step_index),
        field="nominal",
        counter=counter,
        run_setting=run_setting,
    )
    nominal_profiles = {
        row.configuration_id: nominal_evaluator.evaluate(row) for row in catalog
    }
    unilateral = [row for row in catalog if row.changed_users == 1]
    top_ids = []
    for user, _ in base.assignments:
        proposals = [row for row in unilateral if dict(row.assignments)[user] != dict(base.assignments)[user]]
        ranked = sorted(
            proposals,
            key=lambda row: (
                -_nominal_configuration(row, nominal_profiles[row.configuration_id]).nominal_bits,
                row.configuration_id,
            ),
        )[:TOP_PROPOSALS]
        top_ids.extend(row.configuration_id for row in ranked)
    allowed = [base] + [row for row in unilateral if row.configuration_id in top_ids]
    # Frozen evacuations: include multi-user configurations assembled solely
    # from the top-two per-user proposal identities.
    allowed.extend(
        row
        for row in catalog
        if row.changed_users > 1
        and all(
            any(dict(proposal.assignments)[user] == identity for proposal in unilateral if proposal.configuration_id in top_ids)
            for user, identity in row.assignments
            if identity != dict(base.assignments)[user]
        )
    )
    nominal = nominal_greedy_reference(
        _nominal_configuration(row, nominal_profiles[row.configuration_id]) for row in allowed
    )
    nominal_all = nominal_greedy_reference(
        _nominal_configuration(row, nominal_profiles[row.configuration_id]) for row in catalog
    )
    return (
        next(row for row in allowed if row.configuration_id == nominal.configuration_id),
        tuple(sorted(set(top_ids))),
        next(row for row in catalog if row.configuration_id == nominal_all.configuration_id),
    )


def _rate_tail(bits: Mapping[int, float]) -> dict[str, float]:
    rates = np.asarray([value / DECISION_INTERVAL_S for value in bits.values()], dtype=np.float64)
    if rates.size == 0:
        return {"p05_bps": 0.0, "p50_bps": 0.0, "p95_bps": 0.0}
    return {
        "p05_bps": float(np.quantile(rates, 0.05)),
        "p50_bps": float(np.quantile(rates, 0.50)),
        "p95_bps": float(np.quantile(rates, 0.95)),
    }


def _arm_row(
    *,
    arm: str,
    profile: EvaluatedProfile,
    base: Configuration,
    cell_rekeyed_users: Iterable[int],
    elapsed_s: float,
) -> dict[str, object]:
    users = max(1, len(base.assignments))
    opportunity = users * DECISION_INTERVAL_S
    events = _physical_events(
        base, profile.config, cell_rekeyed_users=cell_rekeyed_users
    )
    phi = phi_qos(events)
    handover_count = sum(
        event.kind in {"beam_change", "satellite_change", "cell_rekey"} for event in events
    )
    complete = sum(
        math.isclose(
            float(profile.score.decoding_time_s.get(user, 0.0)),
            DECISION_INTERVAL_S,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        )
        for user, _identity in base.assignments
    )
    partial = sum(
        float(profile.score.decoding_time_s.get(user, 0.0)) > 0.0
        for user, _identity in base.assignments
    )
    useful_user_seconds = math.fsum(profile.score.useful_time_s.values())
    return {
        "arm": arm,
        "configuration_id": profile.config.configuration_id,
        "bits": profile.bits,
        "joules": profile.joules,
        "pooled_ee_bits_per_j": None if profile.joules == 0 else profile.bits / profile.joules,
        "energy": dict(profile.energy_components),
        "lit_beam_seconds": profile.lit_beam_seconds,
        "lit_satellite_seconds": profile.lit_satellite_seconds,
        "decoding_availability": math.fsum(profile.score.decoding_time_s.values()) / opportunity,
        "useful_availability": math.fsum(profile.score.useful_time_s.values()) / opportunity,
        "partial_service_availability": partial / users,
        "complete_service_availability": complete / users,
        "complete_service_user_steps": complete,
        "full_roster_user_steps": users,
        "qos_additive": {
            "availability_served": useful_user_seconds,
            "availability_opportunities": opportunity,
            "handover_events": handover_count,
            "handover_opportunities": users,
            "phi_cost_numerator": -float(phi),
            "phi_cost_denominator": users,
        },
        "phi_signalling_qos_preference": float(phi),
        "phi_priced_handover_cost_per_user_step": -float(phi) / users,
        "handover_rate_per_user_decision": handover_count / users,
        "rate_tail": _rate_tail(profile.score.bits),
        "served_PHY": profile.score.served_phy,
        "rate_target_attained": profile.score.rate_target_attained,
        "rate_target_feasible": profile.score.rate_target_feasible,
        "rate_target_attainment_by_boundary": profile.score.rate_target_attainment_by_boundary,
        "treatment_t_same_instant_comparison": profile.treatment_t_same_instant_comparison,
        "changed_users": profile.config.changed_users,
        "handovers": {
            kind: sum(event.kind == kind for event in events)
            for kind in ("beam_change", "satellite_change", "cell_rekey", "initial_entry", "reentry", "exit")
        },
        "prior_current_identities": [
            {
                "user_id": user,
                "prior": None if base.mapping[user] is None else list(base.mapping[user]),
                "current": (
                    None
                    if profile.config.mapping[user] is None
                    else list(profile.config.mapping[user])
                ),
                "event_type": next(event.kind for event in events if event.user_id == user),
            }
            for user, _identity in base.assignments
        ],
        "decision_time_s": elapsed_s,
    }


def _anchor_qos_metrics(
    profile: EvaluatedProfile,
    incumbent: Configuration,
    *,
    cell_rekeyed_users: Iterable[int],
) -> dict[str, float]:
    users = max(1, len(incumbent.assignments))
    events = _physical_events(
        incumbent,
        profile.config,
        cell_rekeyed_users=cell_rekeyed_users,
    )
    return {
        "availability": math.fsum(profile.score.useful_time_s.values())
        / (users * DECISION_INTERVAL_S),
        "handover_rate": sum(
            event.kind in {"beam_change", "satellite_change", "cell_rekey"}
            for event in events
        )
        / users,
        "phi_cost": max(0.0, -float(phi_qos(events))) / users,
    }


def _anchor_qos_noninferior(
    candidate: EvaluatedProfile,
    comparators: Sequence[EvaluatedProfile],
    incumbent: Configuration,
    *,
    cell_rekeyed_users: Iterable[int],
) -> tuple[bool, dict[str, object]]:
    candidate_qos = _anchor_qos_metrics(
        candidate,
        incumbent,
        cell_rekeyed_users=cell_rekeyed_users,
    )

    def relative(numerator: float, denominator: float) -> float | None:
        if denominator > 0.0:
            return numerator / denominator - 1.0
        return 0.0 if numerator == 0.0 else None

    rows = {}
    passed = True
    for comparator in comparators:
        comparator_qos = _anchor_qos_metrics(
            comparator,
            incumbent,
            cell_rekeyed_users=cell_rekeyed_users,
        )
        certificate = {
            "availability_delta": candidate_qos["availability"]
            - comparator_qos["availability"],
            "handover_rate_relative_change": relative(
                candidate_qos["handover_rate"], comparator_qos["handover_rate"]
            ),
            "phi_cost_relative_change": relative(
                candidate_qos["phi_cost"], comparator_qos["phi_cost"]
            ),
        }
        handover_relative = certificate["handover_rate_relative_change"]
        phi_relative = certificate["phi_cost_relative_change"]
        certificate["pass"] = (
            certificate["availability_delta"] > -0.005
            and handover_relative is not None
            and handover_relative < 0.05
            and phi_relative is not None
            and phi_relative < 0.05
        )
        passed &= bool(certificate["pass"])
        rows[comparator.config.configuration_id] = certificate
    return passed, {"candidate": candidate_qos, "comparators": rows}


def _canonical_step_rows(
    steps: Sequence[Mapping[str, object]],
    *,
    provider_sha256: str,
    code_sha256: str,
) -> list[dict[str, object]]:
    rows = []
    for step in steps:
        for arm in step["arms"]:  # type: ignore[index]
            rows.append(
                {
                    "schema": f"{SCHEMA}-canonical-step-row",
                    "anchor_index": int(step["anchor_index"]),
                    "step_index": int(step["step_index"]),
                    "carrier": str(step["carrier"]),
                    "arm": str(arm["arm"]),
                    "bits_hex": float(arm["bits"]).hex(),
                    "joules_hex": float(arm["joules"]).hex(),
                    "energy_hex": {
                        name: float(value).hex()
                        for name, value in arm["energy"].items()  # type: ignore[union-attr]
                    },
                    "opportunity_user_seconds_hex": (
                        int(arm["full_roster_user_steps"]) * DECISION_INTERVAL_S
                    ).hex(),
                    "served_partial_user_steps": int(
                        round(
                            float(arm["partial_service_availability"])
                            * int(arm["full_roster_user_steps"])
                        )
                    ),
                    "served_complete_user_steps": int(arm["complete_service_user_steps"]),
                    "full_roster_user_steps": int(arm["full_roster_user_steps"]),
                    "prior_current_identities": arm["prior_current_identities"],
                    "phi_numerator_hex": float(arm["phi_signalling_qos_preference"]).hex(),
                    "phi_denominator": int(arm["full_roster_user_steps"]),
                    "handover_events": int(arm["qos_additive"]["handover_events"]),
                    "handover_opportunities": int(
                        arm["qos_additive"]["handover_opportunities"]
                    ),
                    "provider_sha256": provider_sha256,
                    "code_sha256": code_sha256,
                }
            )
    return rows


def _verify_reaggregation(
    rows: Sequence[Mapping[str, object]], summary: Mapping[str, object]
) -> None:
    for arm_name in ARMS:
        selected = [row for row in rows if row["arm"] == arm_name]
        expected = summary["arms"][arm_name]  # type: ignore[index]
        bits = math.fsum(float.fromhex(str(row["bits_hex"])) for row in selected)
        joules = math.fsum(float.fromhex(str(row["joules_hex"])) for row in selected)
        if not math.isclose(bits, float(expected["bits"]), rel_tol=0.0, abs_tol=1e-8) or not math.isclose(
            joules, float(expected["joules"]), rel_tol=0.0, abs_tol=1e-10
        ):
            raise ProbeError("canonical rows disagree with receipt summary")


def _usable_energy_range_step(
    *,
    selected: EvaluatedProfile,
    base: Configuration,
    base_profile: EvaluatedProfile,
    evaluated: Mapping[str, EvaluatedProfile],
) -> dict[str, object]:
    """Reporting-only successor range diagnostic; it applies no gate."""

    base_map = dict(base.assignments)
    by_beam: dict[str, float] = {}
    for beam in sorted({identity for identity in base_map.values() if identity is not None}):
        alternatives = [
            row
            for row in evaluated.values()
            if all(row.score.served_phy.values())
            and any(
                base_map[user] == beam and identity != beam
                for user, identity in row.config.assignments
            )
        ]
        best_change = max(
            (base_profile.joules - row.joules for row in alternatives),
            default=0.0,
        )
        by_beam[f"{beam[0]}:{beam[1]}"] = float(best_change)
    return {
        "selected_acm_mode_counts": dict(sorted(selected.acm_mode_counts.items())),
        "se_plateau_user_steps": selected.se_plateau_user_steps,
        "user_step_observations": selected.user_step_observations,
        "rf_cap_hits": selected.rf_cap_hits,
        "rf_transmission_observations": selected.rf_transmission_observations,
        "se_plateau_user_step_share": (
            0.0
            if selected.user_step_observations == 0
            else selected.se_plateau_user_steps / selected.user_step_observations
        ),
        "rf_cap_transmission_share": (
            0.0
            if selected.rf_transmission_observations == 0
            else selected.rf_cap_hits / selected.rf_transmission_observations
        ),
        "best_feasible_reassignment_dc_energy_change_j_by_beam": by_beam,
        "thresholds_applied": False,
    }


def execute_step(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    carrier: str,
    calibration: CalibrationValues,
    counter: EvaluationCounter,
    incumbent: Configuration | None = None,
    c2_horizon_offsets: int = 3,
    run_setting: SealedRunSetting | None = None,
) -> dict[str, object]:
    decision_started = time.perf_counter()
    deadline_at = decision_started + DECISION_DEADLINE_S
    counter_start = counter.boundary_evaluations
    base = _base_configuration(tape, step_index, carrier)
    incumbent = base if incumbent is None else incumbent
    catalog, catalogue_census = _catalogue_with_census(tape, step_index, base)
    evaluator = StepEvaluator(
        tape,
        setting,
        step_index,
        transition_from=incumbent,
        cell_rekeyed_users=_rekeyed_users(tape, step_index),
        counter=counter,
        run_setting=run_setting,
    )
    evaluator.evaluate_many(catalog)
    evaluator.evaluate_many(catalog)
    catalog = tuple(
        row for row in catalog if row.configuration_id not in evaluator._invalid
    )
    if base.configuration_id not in evaluator._evaluated:
        raise ProbeError("BASE has an invalid power certificate")
    evaluated = {row.configuration_id: evaluator.evaluate(row) for row in catalog}
    base_profile = evaluated[base.configuration_id]
    unilateral = [evaluated[row.configuration_id] for row in catalog if row.changed_users == 1]
    joint = [evaluated[row.configuration_id] for row in catalog if row.changed_users > 1]
    u1 = _best((base_profile, *unilateral), calibration)
    j1 = _best((base_profile, *joint), calibration)
    union = _best(evaluated.values(), calibration)
    s0, top2, nominal_control = _s0_select(
        tape, setting, step_index, base, catalog, counter, run_setting
    )
    factors, interaction_sum, interaction_count = _configuration_factor_scores(
        tape=tape,
        setting=setting,
        step_index=step_index,
        carrier=carrier,
        base=base,
        incumbent=incumbent,
        catalog=catalog,
        evaluator=evaluator,
        calibration=calibration,
        counter=counter,
        c2_horizon_offsets=c2_horizon_offsets,
        run_setting=run_setting,
    )
    s_uni, s_uni_iterations, s_uni_wall_s, s_uni_missed = _s_uni_select(
        base=base,
        tape=tape,
        step_index=step_index,
        evaluator=evaluator,
        calibration=calibration,
        deadline_at=deadline_at,
    )
    selections = {
        "E1_U1": u1.config,
        "E1_J1": j1.config,
        "UNION_CATALOGUE_OPTIMUM": union.config,
        "S0_DEPLOYABLE": s0,
        "FULL": _set_score_select(catalog=catalog, factors=factors, include=("C1", "C2", "C3")),
        "DROP_C1": _set_score_select(catalog=catalog, factors=factors, include=("C2", "C3")),
        "DROP_C2": _set_score_select(catalog=catalog, factors=factors, include=("C1", "C3")),
        "DROP_C3": _set_score_select(catalog=catalog, factors=factors, include=("C1", "C2")),
        "UNI": _set_score_select(
            catalog=(base, *tuple(row for row in catalog if row.changed_users == 1)),
            factors=factors,
            include=("C1", "C2", "C3"),
        ),
        "S_UNI": s_uni,
        ALL_NEUTRAL_CONTROL: base,
        # NULL traverses the coordinator but commits BASE byte-for-byte.
        "NULL": base,
        "RANDOM_FEASIBLE": catalog[int(tape.seed + step_index) % len(catalog)],
        "NOMINAL_GREEDY": nominal_control,
    }
    deadline_missed = s_uni_missed or time.perf_counter() > deadline_at
    selections = apply_deadline_fallback(
        selections, base=base, missed=deadline_missed
    )
    range_diagnostic = _usable_energy_range_step(
        selected=evaluated[selections["FULL"].configuration_id],
        base=base,
        base_profile=base_profile,
        evaluated=evaluated,
    )
    selected_full_factors = factors[selections["FULL"].configuration_id]
    solver_residual_w_max = max(
        row.score.certificate_residual_w for row in evaluated.values()
    )
    # An update residual is not, without a contraction proof, an upper bound
    # on fixed-point error or on threshold-sensitive F.  Only an exactly fixed
    # floating-point update certifies zero here; all other cases fail closed
    # until the solver exports independently proved F bounds.
    certified_numerical_error_bits = (
        0.0 if solver_residual_w_max == 0.0 else None
    )
    j1_objective_margin_bits = float(_objective(j1, calibration) - _objective(u1, calibration))
    j1_matched_qos, j1_qos_certificate = _anchor_qos_noninferior(
        j1,
        (base_profile, u1),
        incumbent,
        cell_rekeyed_users=_rekeyed_users(tape, step_index),
    )
    genuine_multi_user_witness = (
        j1.config.changed_users > 1
        and j1_matched_qos
        and certified_numerical_error_bits is not None
        and j1_objective_margin_bits > certified_numerical_error_bits
    )
    arm_rows = []
    for arm in ARMS:
        started = time.perf_counter()
        profile = evaluator.evaluate(selections[arm])
        arm_rows.append(
            _arm_row(
                arm=arm,
                profile=profile,
                base=incumbent,
                cell_rekeyed_users=_rekeyed_users(tape, step_index),
                elapsed_s=time.perf_counter() - started,
            )
        )
        arm_rows[-1]["computation_deadline_s"] = DECISION_DEADLINE_S
        arm_rows[-1]["declared_worker_count"] = DECLARED_WORKERS
        arm_rows[-1]["deadline_missed"] = (
            deadline_missed
            if arm in SET_LEVEL_ARMS
            else False
        )
        if arm == "S_UNI":
            arm_rows[-1]["iteration_count"] = s_uni_iterations
            arm_rows[-1]["decoder_wall_s"] = s_uni_wall_s
    return {
        "step_index": step_index,
        "carrier": carrier,
        "rekey_eligible_user_boundaries": (
            len(base.assignments)
            if step_index > 0 and tape.steps[step_index].refresh_phase == 0
            else 0
        ),
        "arms": arm_rows,
        "e1_certificate": {
            "candidate_census_complete": True,
            **catalogue_census,
            "candidate_count": len(catalog),
            "unilateral_count": len(unilateral),
            "joint_count": len(joint),
            "u1_configuration": u1.config.configuration_id,
            "j1_configuration": j1.config.configuration_id,
            "union_configuration": union.config.configuration_id,
            "genuine_multi_user_witness": genuine_multi_user_witness,
            "j1_beyond_base_and_u_all": genuine_multi_user_witness,
            "j1_objective_margin_bits": j1_objective_margin_bits,
            "certified_numerical_error_bits": certified_numerical_error_bits,
            "certified_numerical_error_status": (
                "EXACT_FIXED_POINT"
                if certified_numerical_error_bits is not None
                else "UNAVAILABLE_FAIL_CLOSED"
            ),
            "matched_qos_noninferior": j1_matched_qos,
            "matched_qos_certificate": j1_qos_certificate,
            "u_all_configuration": u1.config.configuration_id,
            "solver_residual_w_max": solver_residual_w_max,
        },
        "s0_certificate": {
            "nominal_information_only": True,
            "top_two_proposal_ids": list(top2),
            "evacuation_decoder": "frozen-complete-top2-combinations-v1",
        },
        "non_additive_interaction_bits": float(selected_full_factors["psi_A"]),
        "non_additive_interaction_count": int(
            selections["FULL"].changed_users > 1
        ),
        "catalogue_interaction_sum_bits": float(interaction_sum),
        "catalogue_interaction_configuration_count": interaction_count,
        "factor_arm_formulas": {
            "FULL": "C1+C2+C3",
            "DROP_C1": "C2+C3",
            "DROP_C2": "C1+C3",
            "DROP_C3": "C1+C2",
        },
        "selected_full_set_score": {
            name: (
                float(value)
                if isinstance(value, Fraction)
                else [[user, float(credit)] for user, credit in value]
            )
            for name, value in selected_full_factors.items()
        },
        "coordinator": {
            "deadline_s": DECISION_DEADLINE_S,
            "declared_worker_count": DECLARED_WORKERS,
            "whole_path_wall_s": time.perf_counter() - decision_started,
            "deadline_missed": deadline_missed,
            "fallback": "BASE" if deadline_missed else None,
            "s_uni_iterations": s_uni_iterations,
            "s_uni_wall_s": s_uni_wall_s,
        },
        "successor_usable_energy_range": range_diagnostic,
        "physical_boundary_evaluations": counter.boundary_evaluations - counter_start,
    }


def _summarize_energy_range(steps: Sequence[Mapping[str, object]]) -> dict[str, object]:
    rows = [step["successor_usable_energy_range"] for step in steps]
    mode_counts: dict[str, int] = {}
    by_beam: dict[str, float] = {}
    for row in rows:
        for name, count in row["selected_acm_mode_counts"].items():  # type: ignore[union-attr]
            mode_counts[str(name)] = mode_counts.get(str(name), 0) + int(count)
        for beam, value in row["best_feasible_reassignment_dc_energy_change_j_by_beam"].items():  # type: ignore[union-attr]
            by_beam[str(beam)] = max(by_beam.get(str(beam), -math.inf), float(value))
    plateau = sum(int(row["se_plateau_user_steps"]) for row in rows)
    users = sum(int(row["user_step_observations"]) for row in rows)
    cap_hits = sum(int(row["rf_cap_hits"]) for row in rows)
    rf = sum(int(row["rf_transmission_observations"]) for row in rows)
    return {
        "selected_acm_mode_counts": dict(sorted(mode_counts.items())),
        "se_plateau_user_step_share": 0.0 if users == 0 else plateau / users,
        "rf_cap_transmission_share": 0.0 if rf == 0 else cap_hits / rf,
        "best_feasible_reassignment_dc_energy_change_j_by_beam": dict(sorted(by_beam.items())),
        "thresholds_applied": False,
    }


def _summarize_steps(steps: Sequence[Mapping[str, object]], calibration: CalibrationValues) -> dict[str, object]:
    by_arm: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        rows = [row for step in steps for row in step["arms"] if row["arm"] == arm]  # type: ignore[index]
        bits = math.fsum(float(row["bits"]) for row in rows)
        joules = math.fsum(float(row["joules"]) for row in rows)
        availability_served = math.fsum(
            float(row["qos_additive"]["availability_served"]) for row in rows  # type: ignore[index]
        )
        availability_opportunities = math.fsum(
            float(row["qos_additive"]["availability_opportunities"]) for row in rows  # type: ignore[index]
        )
        handover_events = math.fsum(
            float(row["qos_additive"]["handover_events"]) for row in rows  # type: ignore[index]
        )
        handover_opportunities = math.fsum(
            float(row["qos_additive"]["handover_opportunities"]) for row in rows  # type: ignore[index]
        )
        phi_cost_numerator = math.fsum(
            float(row["qos_additive"]["phi_cost_numerator"]) for row in rows  # type: ignore[index]
        )
        phi_cost_denominator = math.fsum(
            float(row["qos_additive"]["phi_cost_denominator"]) for row in rows  # type: ignore[index]
        )
        by_arm[arm] = {
            "bits": bits,
            "joules": joules,
            "pooled_ee_bits_per_j": None if joules == 0 else bits / joules,
            "pa_j": math.fsum(float(row["energy"]["pa_j"]) for row in rows),  # type: ignore[index]
            "standby_j": math.fsum(float(row["energy"]["standby_j"]) for row in rows),  # type: ignore[index]
            "circuit_j": math.fsum(float(row["energy"]["circuit_j"]) for row in rows),  # type: ignore[index]
            "baseband_j": math.fsum(float(row["energy"]["baseband_j"]) for row in rows),  # type: ignore[index]
            "availability": availability_served / availability_opportunities,
            "decoding_availability": math.fsum(float(row["decoding_availability"]) for row in rows) / len(rows),
            "partial_service_availability": math.fsum(float(row["partial_service_availability"]) for row in rows) / len(rows),
            "useful_availability": math.fsum(float(row["useful_availability"]) for row in rows) / len(rows),
            "phi_signalling_qos_preference": math.fsum(
                float(row["phi_signalling_qos_preference"]) for row in rows
            ),
            "phi_priced_handover_cost_per_user_step": phi_cost_numerator / phi_cost_denominator,
            "qos_additive": {
                "availability_served": availability_served,
                "availability_opportunities": availability_opportunities,
                "handover_events": handover_events,
                "handover_opportunities": handover_opportunities,
                "phi_cost_numerator": phi_cost_numerator,
                "phi_cost_denominator": phi_cost_denominator,
            },
            "handovers": {
                kind: sum(int(row["handovers"][kind]) for row in rows)  # type: ignore[index]
                for kind in ("beam_change", "satellite_change", "cell_rekey", "initial_entry", "reentry", "exit")
            },
            "corrected_boundary_conditional_rekey": {
                "rekeys": sum(int(row["handovers"]["cell_rekey"]) for row in rows),  # type: ignore[index]
                "eligible_user_boundaries": sum(
                    int(step["rekey_eligible_user_boundaries"]) for step in steps
                ),
                "rate": corrected_boundary_rekey_rate(
                    rekeys=sum(int(row["handovers"]["cell_rekey"]) for row in rows),  # type: ignore[index]
                    eligible_boundaries=sum(
                        int(step["rekey_eligible_user_boundaries"]) for step in steps
                    ),
                ),
                "numerator_source": "physical event ledger",
            },
            "handover_rate_per_user_decision": handover_events / handover_opportunities,
            "changed_users": sum(int(row["changed_users"]) for row in rows),
            "decision_time_tail_s": {
                "p50": float(np.quantile([row["decision_time_s"] for row in rows], 0.5)),
                "p95": float(np.quantile([row["decision_time_s"] for row in rows], 0.95)),
                "max": max(float(row["decision_time_s"]) for row in rows),
            },
            "rate_tail": {
                key: float(np.quantile([row["rate_tail"][key] for row in rows], 0.5))  # type: ignore[index]
                for key in ("p05_bps", "p50_bps", "p95_bps")
            },
        }
    marginals = {}
    failed = []
    for name, (full_name, drop_name) in MARGINALS.items():
        full, drop = by_arm[full_name], by_arm[drop_name]
        full_ee, drop_ee = full["pooled_ee_bits_per_j"], drop["pooled_ee_bits_per_j"]
        delta_bits = float(full["bits"]) - float(drop["bits"])
        delta_joules = float(full["joules"]) - float(drop["joules"])
        delta_ee = None if full_ee is None or drop_ee is None else float(full_ee) - float(drop_ee)
        row = {
            "full": full_name,
            "drop": drop_name,
            "delta_bits": delta_bits,
            "delta_joules": delta_joules,
            "delta_ee_bits_per_j": delta_ee,
            "surplus_at_calibration_price_bits": delta_bits - float(calibration.eta_ref) * delta_joules,
            "failed": delta_ee is None or delta_ee <= 0.0,
        }
        if row["failed"]:
            failed.append(name)
        marginals[name] = row
    return {
        "arms": by_arm,
        "marginals": marginals,
        "which_marginal_failed": failed,
        "non_additive_interaction_bits": math.fsum(float(step["non_additive_interaction_bits"]) for step in steps),
        "outage_runs": _outage_runs(steps),
        "handover_totals": {
            kind: sum(
                int(row["handovers"][kind])  # type: ignore[index]
                for step in steps
                for row in step["arms"]  # type: ignore[index]
            )
            for kind in ("beam_change", "satellite_change", "cell_rekey", "initial_entry", "reentry", "exit")
        },
        "corrected_boundary_conditional_rekey_by_arm": {
            arm: by_arm[arm]["corrected_boundary_conditional_rekey"] for arm in ARMS
        },
    }


def pooled_ratio_cluster_bootstrap(
    clusters: Sequence[Mapping[str, float]],
    *,
    draws: int = 10_000,
    seed: int = 0x0252026,
) -> dict[str, object]:
    """One-way paired-date bootstrap of pooled EE and additive QoS counts."""

    if type(draws) is not int or draws < 1 or len(clusters) < 2:
        raise ProbeError("cluster bootstrap needs at least two clusters and one draw")
    fields = (
        "full_bits",
        "full_joules",
        "comparator_bits",
        "comparator_joules",
        "full_availability_served",
        "full_availability_opportunities",
        "comparator_availability_served",
        "comparator_availability_opportunities",
        "full_phi_numerator",
        "full_phi_denominator",
        "comparator_phi_numerator",
        "comparator_phi_denominator",
        "full_handover_events",
        "full_handover_opportunities",
        "comparator_handover_events",
        "comparator_handover_opportunities",
    )
    def value(row: Mapping[str, float], field: str) -> float:
        if field in row:
            return float(row[field])
        legacy = {
            "full_availability_served": float(row.get("full_qos", 0.0)),
            "full_availability_opportunities": 1.0,
            "comparator_availability_served": float(row.get("comparator_qos", 0.0)),
            "comparator_availability_opportunities": 1.0,
            "full_phi_numerator": float(row.get("full_phi_cost_per_user_step", max(0.0, -float(row.get("full_phi", 0.0))))),
            "full_phi_denominator": 1.0,
            "comparator_phi_numerator": float(row.get("comparator_phi_cost_per_user_step", max(0.0, -float(row.get("comparator_phi", 0.0))))),
            "comparator_phi_denominator": 1.0,
            "full_handover_events": float(row.get("full_handover_rate", 0.0)),
            "full_handover_opportunities": 1.0,
            "comparator_handover_events": float(row.get("comparator_handover_rate", 0.0)),
            "comparator_handover_opportunities": 1.0,
        }
        if field in legacy:
            return legacy[field]
        raise ProbeError(f"bootstrap row lacks {field}")

    values = np.asarray(
        [[value(row, field) for field in fields] for row in clusters],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ProbeError("bootstrap inputs must be finite and physical")
    denominator_columns = (1, 3, 5, 7, 9, 11, 13, 15)
    if np.any(values[:, denominator_columns] <= 0.0):
        raise ProbeError("bootstrap additive denominators must be positive")

    rng = np.random.default_rng(seed)
    sampled_rows = []
    attempts = 0
    while len(sampled_rows) < draws and attempts < draws * 20:
        attempts += 1
        indices = rng.integers(0, len(values), size=len(values))
        totals = values[indices].sum(axis=0)
        # A zero-bit cluster is valid input.  Degenerate all-zero resamples
        # are discarded/redrawn so the primary ratio interval stays defined.
        if totals[0] <= 0.0 or totals[2] <= 0.0:
            continue
        sampled_rows.append(totals)
    if len(sampled_rows) != draws:
        raise ProbeError("bootstrap could not form enough positive pooled-bit draws")
    sampled = np.asarray(sampled_rows, dtype=np.float64)
    full_ee = sampled[:, 0] / sampled[:, 1]
    comparator_ee = sampled[:, 2] / sampled[:, 3]
    contrast = full_ee / comparator_ee - 1.0
    qos_delta = sampled[:, 4] / sampled[:, 5] - sampled[:, 6] / sampled[:, 7]
    def relative_change(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
        result = np.full(numerator.shape, np.inf, dtype=np.float64)
        positive = denominator > 0.0
        result[positive] = numerator[positive] / denominator[positive] - 1.0
        result[(denominator == 0.0) & (numerator == 0.0)] = 0.0
        return result

    full_phi_rate = sampled[:, 8] / sampled[:, 9]
    comparator_phi_rate = sampled[:, 10] / sampled[:, 11]
    phi_relative = relative_change(full_phi_rate, comparator_phi_rate)
    full_handover_rate = sampled[:, 12] / sampled[:, 13]
    comparator_handover_rate = sampled[:, 14] / sampled[:, 15]
    handover_relative = relative_change(full_handover_rate, comparator_handover_rate)

    totals = values.sum(axis=0)
    if totals[0] <= 0.0 or totals[2] <= 0.0:
        raise ProbeError("observed pooled bits must be positive for an EE contrast")
    observed = (totals[0] / totals[1]) / (totals[2] / totals[3]) - 1.0
    observed_qos = totals[4] / totals[5] - totals[6] / totals[7]
    observed_phi = float(relative_change(totals[8:9] / totals[9:10], totals[10:11] / totals[11:12])[0])
    observed_handovers = float(relative_change(totals[12:13] / totals[13:14], totals[14:15] / totals[15:16])[0])
    ee_lower = float(np.quantile(contrast, 0.025))
    ee_upper = float(np.quantile(contrast, 0.975))
    qos_lower = float(np.quantile(qos_delta, 0.025))
    phi_upper = float(np.quantile(phi_relative, 0.975))
    handover_upper = float(np.quantile(handover_relative, 0.975))
    return {
        "schema": f"{SCHEMA}-pooled-ratio-cluster-bootstrap",
        "clusters": len(values),
        "draws": draws,
        "seed": seed,
        "estimator": "paired resample; recompute pooled ratios from additive date-cluster totals within every draw",
        "interval_convention": "central 95% percentile interval [q0.025,q0.975]",
        "contrast_relative": observed,
        "contrast_lower_95_relative": ee_lower,
        "contrast_upper_95_relative": ee_upper,
        "contrast_percentage_points": 100.0 * observed,
        "contrast_lower_95_percentage_points": 100.0 * ee_lower,
        "contrast_upper_95_percentage_points": 100.0 * ee_upper,
        "prespecified_margin_relative": 0.005,
        "ee_margin_pass": ee_lower > 0.005,
        "qos_availability_delta": observed_qos,
        "qos_availability_lower_95": qos_lower,
        "phi_priced_handover_cost_relative_change": observed_phi,
        "phi_priced_handover_cost_relative_upper_95": phi_upper,
        "handover_rate_relative_change": observed_handovers,
        "handover_rate_relative_upper_95": handover_upper,
        "availability_margin_fraction": -0.005,
        "relative_cost_margin": 0.05,
        "qos_noninferior": qos_lower > -0.005 and phi_upper < 0.05 and handover_upper < 0.05,
        "additive_fields_pooled_inside_each_draw": list(fields[4:]),
        "zero_bit_cluster_disposition": "valid for primary; discard/redraw only an all-zero pooled-bit resample",
        "supplementary_paired_world_log_ee": (
            {
                "status": "UNDEFINED_ZERO_BIT_CLUSTER",
                "not_a_substitute_for_pooled_ratio_interval": True,
            }
            if np.any(values[:, 0] == 0.0) or np.any(values[:, 2] == 0.0)
            else {
                "status": "DEFINED",
                **(lambda paired, sampled_log: {
                    "mean_log_ratio": float(paired.mean()),
                    "lower_95_percentage_points": float(100.0 * np.expm1(np.quantile(sampled_log, 0.025))),
                    "upper_95_percentage_points": float(100.0 * np.expm1(np.quantile(sampled_log, 0.975))),
                })(
                    np.log((values[:, 0] / values[:, 1]) / (values[:, 2] / values[:, 3])),
                    np.log((values[:, 0] / values[:, 1]) / (values[:, 2] / values[:, 3]))[
                        np.random.default_rng(seed ^ 0x11AACC).integers(
                            0, len(values), size=(draws, len(values))
                        )
                    ].mean(axis=1),
                ),
                "not_a_substitute_for_pooled_ratio_interval": True,
            }
        ),
    }


def _positive_paired_ratio_values(blocks: Sequence[Mapping[str, object]]) -> np.ndarray:
    """Validate the four positive fields shared by log-based estimators."""

    values = np.asarray(
        [
            [
                float(row["full_bits"]),
                float(row["full_joules"]),
                float(row["comparator_bits"]),
                float(row["comparator_joules"]),
            ]
            for row in blocks
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ProbeError("paired log-contrast bits and energy must be finite and positive")
    return values


def delta_method_log_contrast(
    blocks: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Reporting-only paired-block delta interval for the pooled log contrast."""

    if len(blocks) < 2:
        raise ProbeError("delta-method interval needs at least two paired blocks")
    raw = np.asarray(
        [
            [
                float(row["full_bits"]),
                float(row["full_joules"]),
                float(row["comparator_bits"]),
                float(row["comparator_joules"]),
            ]
            for row in blocks
        ],
        dtype=np.float64,
    )
    if np.any(raw[:, (0, 2)] == 0.0):
        return {
            "schema": f"{SCHEMA}-paired-block-delta-log-contrast",
            "status": "UNDEFINED_ZERO_BIT_CLUSTER",
            "reporting_only": True,
        }
    values = _positive_paired_ratio_values(blocks)
    means = values.mean(axis=0)
    log_contrast = math.log(means[0] / means[1]) - math.log(means[2] / means[3])
    psi = (
        values[:, 0] / means[0]
        - values[:, 1] / means[1]
        - values[:, 2] / means[2]
        + values[:, 3] / means[3]
    )
    standard_error = float(np.std(psi, ddof=1) / math.sqrt(len(values)))
    low_log = log_contrast - 1.959963984540054 * standard_error
    high_log = log_contrast + 1.959963984540054 * standard_error
    return {
        "schema": f"{SCHEMA}-paired-block-delta-log-contrast",
        "status": "DEFINED",
        "blocks": len(values),
        "formula": "psi=(BF/mu_BF-EF/mu_EF)-(BD/mu_BD-ED/mu_ED)",
        "mean_log_ratio": log_contrast,
        "standard_error_log_ratio": standard_error,
        "contrast_percentage_points": 100.0 * math.expm1(log_contrast),
        "lower_95_percentage_points": 100.0 * math.expm1(low_log),
        "upper_95_percentage_points": 100.0 * math.expm1(high_log),
        "reporting_only": True,
    }


def two_way_pigeonhole_bootstrap(
    blocks: Sequence[Mapping[str, object]],
    *,
    draws: int = 10_000,
    seed: int = 0x0252026,
) -> dict[str, object]:
    """Two-way date x learner-seed bootstrap with arm-paired weights.

    Every draw applies the same product weight to FULL and its comparator,
    pools all additive numerators/denominators, and recomputes every ratio.
    """

    if type(draws) is not int or draws < 1 or len(blocks) < 2:
        raise ProbeError("pigeonhole bootstrap needs at least two blocks and one draw")
    dates = sorted({str(row["tle_date"]) for row in blocks})
    seeds = sorted({int(row["learner_seed"]) for row in blocks})
    if not dates or not seeds:
        raise ProbeError("pigeonhole bootstrap needs both clustering dimensions")
    date_index = {value: index for index, value in enumerate(dates)}
    seed_index = {value: index for index, value in enumerate(seeds)}
    core = np.asarray(
        [
            [
                float(row["full_bits"]),
                float(row["full_joules"]),
                float(row["comparator_bits"]),
                float(row["comparator_joules"]),
            ]
            for row in blocks
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(core)) or np.any(core < 0.0) or np.any(core[:, (1, 3)] <= 0.0):
        raise ProbeError("pigeonhole core inputs must be finite with positive energy")

    def get(row: Mapping[str, object], name: str, fallback: str, default: float) -> float:
        return float(row[name]) if name in row else float(row.get(fallback, default))

    qos = np.asarray(
        [
            [
                get(row, "full_availability_served", "full_qos", 0.0),
                get(row, "full_availability_opportunities", "_missing", 1.0),
                get(row, "comparator_availability_served", "comparator_qos", 0.0),
                get(row, "comparator_availability_opportunities", "_missing", 1.0),
                get(row, "full_phi_numerator", "full_phi_cost_per_user_step", max(0.0, -float(row.get("full_phi", 0.0)))),
                get(row, "full_phi_denominator", "_missing", 1.0),
                get(row, "comparator_phi_numerator", "comparator_phi_cost_per_user_step", max(0.0, -float(row.get("comparator_phi", 0.0)))),
                get(row, "comparator_phi_denominator", "_missing", 1.0),
                get(row, "full_handover_events", "full_handover_rate", 0.0),
                get(row, "full_handover_opportunities", "_missing", 1.0),
                get(row, "comparator_handover_events", "comparator_handover_rate", 0.0),
                get(row, "comparator_handover_opportunities", "_missing", 1.0),
            ]
            for row in blocks
        ],
        dtype=np.float64,
    )
    values = np.concatenate((core, qos), axis=1)
    if not np.all(np.isfinite(qos)) or np.any(qos < 0.0) or np.any(qos[:, (1, 3, 5, 7, 9, 11)] <= 0.0):
        raise ProbeError("pigeonhole QoS counts must be finite additive quantities")
    row_dates = np.asarray([date_index[str(row["tle_date"])] for row in blocks])
    row_seeds = np.asarray([seed_index[int(row["learner_seed"])] for row in blocks])
    rng = np.random.default_rng(seed)
    sampled_rows = []
    attempts = 0
    while len(sampled_rows) < draws and attempts < draws * 20:
        attempts += 1
        date_weights = rng.multinomial(len(dates), np.full(len(dates), 1.0 / len(dates)))
        seed_weights = rng.multinomial(len(seeds), np.full(len(seeds), 1.0 / len(seeds)))
        weights = date_weights[row_dates] * seed_weights[row_seeds]
        totals = (values * weights[:, None]).sum(axis=0)
        if totals[0] <= 0.0 or totals[2] <= 0.0:
            continue
        sampled_rows.append(totals)
    if len(sampled_rows) != draws:
        raise ProbeError("pigeonhole bootstrap could not form enough nonempty resamples")
    sampled = np.asarray(sampled_rows, dtype=np.float64)
    interval = (sampled[:, 0] / sampled[:, 1]) / (sampled[:, 2] / sampled[:, 3]) - 1.0
    availability = sampled[:, 4] / sampled[:, 5] - sampled[:, 6] / sampled[:, 7]

    def relative(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
        result = np.full(numerator.shape, np.inf)
        positive = denominator > 0.0
        result[positive] = numerator[positive] / denominator[positive] - 1.0
        result[(numerator == 0.0) & (denominator == 0.0)] = 0.0
        return result

    phi = relative(sampled[:, 8] / sampled[:, 9], sampled[:, 10] / sampled[:, 11])
    handover = relative(sampled[:, 12] / sampled[:, 13], sampled[:, 14] / sampled[:, 15])
    totals = values.sum(axis=0)
    observed = (totals[0] / totals[1]) / (totals[2] / totals[3]) - 1.0
    availability_lower = float(np.quantile(availability, 0.025))
    phi_upper = float(np.quantile(phi, 0.975))
    handover_upper = float(np.quantile(handover, 0.975))
    lower = float(np.quantile(interval, 0.025))
    upper = float(np.quantile(interval, 0.975))
    return {
        "schema": f"{SCHEMA}-two-way-pigeonhole-bootstrap",
        "tle_dates": len(dates),
        "learner_seeds": len(seeds),
        "draws": draws,
        "seed": seed,
        "estimator": "two-way pigeonhole date x learner seed; arms paired; additive ratios recomputed per draw",
        "interval_convention": "central 95% percentile interval [q0.025,q0.975]",
        "contrast_relative": observed,
        "contrast_lower_95_relative": lower,
        "contrast_upper_95_relative": upper,
        "contrast_percentage_points": 100.0 * observed,
        "lower_95_percentage_points": 100.0 * lower,
        "upper_95_percentage_points": 100.0 * upper,
        "prespecified_margin_relative": 0.005,
        "ee_margin_pass": lower > 0.005,
        "qos_availability_lower_95": availability_lower,
        "phi_priced_handover_cost_relative_upper_95": phi_upper,
        "handover_rate_relative_upper_95": handover_upper,
        "qos_noninferior": availability_lower > -0.005 and phi_upper < 0.05 and handover_upper < 0.05,
        "zero_bit_cluster_disposition": "valid for primary; discard/redraw only an all-zero pooled-bit resample",
        "eligible_as_primary_for_learner_experiments": True,
    }


def uncertainty_estimate(
    blocks: Sequence[Mapping[str, object]],
    *,
    learner_experiment: bool,
    draws: int = 10_000,
    seed: int = 0x0252026,
) -> dict[str, object]:
    """Dispatch the v1.5 primary estimator by experiment type."""

    if learner_experiment:
        primary = two_way_pigeonhole_bootstrap(blocks, draws=draws, seed=seed)
    else:
        # A date is the resampling unit.  If callers supply multiple rows for
        # one date, pool every additive field before entering the bootstrap.
        # This also makes accidental learner-seed pseudoreplication impossible
        # in the learner-free physics path.
        grouped: dict[str, list[Mapping[str, object]]] = {}
        for index, row in enumerate(blocks):
            grouped.setdefault(str(row.get("tle_date", index)), []).append(row)
        date_clusters: list[dict[str, float]] = []
        identifiers = {"tle_date", "learner_seed"}
        for rows in grouped.values():
            fields = set().union(*(set(row) for row in rows)) - identifiers
            date_clusters.append(
                {
                    field: math.fsum(float(row[field]) for row in rows if field in row)
                    for field in fields
                }
            )
        primary = pooled_ratio_cluster_bootstrap(
            date_clusters, draws=draws, seed=seed
        )
    return {
        "primary": primary,
        "primary_estimator": "two-way-pigeonhole" if learner_experiment else "one-way-date-bootstrap",
        "supplementary_delta_method": delta_method_log_contrast(blocks),
    }


def _outage_runs(steps: Sequence[Mapping[str, object]]) -> dict[str, int]:
    result = {}
    for arm in ARMS:
        longest = current = 0
        for step in steps:
            row = next(row for row in step["arms"] if row["arm"] == arm)  # type: ignore[index]
            outage = not all(bool(value) for value in row["served_PHY"].values()) if row["served_PHY"] else True  # type: ignore[union-attr]
            current = current + 1 if outage else 0
            longest = max(longest, current)
        result[arm] = longest
    return result


def run_unit(
    *,
    setting: PhysicsSetting,
    world_index: int,
    executed_steps: int = 30,
    anchor_stride: int = 1,
    smoke_not_matrix: bool = False,
    attempt_id: str | None = None,
    calibration: CalibrationValues | None = None,
    expected_world_digest: str | None = None,
    expected_world_manifest: Mapping[str, object] | None = None,
    run_setting: SealedRunSetting | None = None,
) -> dict[str, object]:
    if (
        type(executed_steps) is not int
        or not 1 <= executed_steps <= 30
        or type(anchor_stride) is not int
        or anchor_stride < 1
    ):
        raise ProbeError("executed_steps must be 1..30 and anchor stride positive")
    domain = _world_domain(world_index)
    run_setting = run_setting_for(setting.label) if run_setting is None else run_setting
    if run_setting.base_cell != setting.label:
        raise ProbeError("run setting does not bind the requested physical cell")
    tape = build_world_tape(
        domain=domain,
        provider=_provider_for_run(run_setting),
        steps=executed_steps + 3,
        start_time_s=0.0,
    )
    if expected_world_digest is not None and tape.digest != expected_world_digest:
        raise ProbeError("rebuilt world tape disagrees with the pre-outcome sealed manifest")
    if expected_world_manifest is not None and tape.manifest() != dict(expected_world_manifest):
        raise ProbeError("rebuilt provider protocol outputs disagree with the sealed manifest")
    calibration = _calibrate(setting, run_setting) if calibration is None else calibration
    if calibration.setting_digest != run_setting.digest:
        raise ProbeError("frozen calibration does not belong to the requested cell")
    started = time.perf_counter()
    counter = EvaluationCounter()
    steps = []
    anchor_index = 0
    for step in range(0, executed_steps, anchor_stride):
        for carrier in REFERENCE_CARRIERS:
            incumbent = _base_configuration(
                tape,
                max(0, step - 1),
                carrier,
            )
            row = execute_step(
                tape=tape,
                setting=setting,
                step_index=step,
                carrier=carrier,
                calibration=calibration,
                counter=counter,
                incumbent=incumbent,
                c2_horizon_offsets=run_setting.c2_horizon_offsets,
                run_setting=run_setting,
            )
            row["anchor_index"] = anchor_index
            row["forecast_offsets"] = [1, 2, 3]
            steps.append(row)
            anchor_index += 1
    elapsed = time.perf_counter() - started
    provider_sha256 = tape.protocol.provider_source_digest
    code_sha256 = _code_authority_digest()
    summary = _summarize_steps(steps, calibration)
    canonical_rows = _canonical_step_rows(
        steps,
        provider_sha256=provider_sha256,
        code_sha256=code_sha256,
    )
    _verify_reaggregation(canonical_rows, summary)
    receipt = {
        "schema": UNIT_SCHEMA,
        "status": "SMOKE_NOT_MATRIX" if smoke_not_matrix else "COMPLETE",
        "SMOKE_NOT_MATRIX": smoke_not_matrix,
        "attempt_id": attempt_id,
        "split": tape.split,
        "test_split_opened": False,
        "training": False,
        "cell": run_setting.run_id,
        "base_cell": setting.label,
        "cell_sha256": run_setting.digest,
        "claim_classification": run_setting.claim_classification,
        "regime": run_setting.regime,
        "regime_wording": (
            "primary a-r0"
            if run_setting.claim_classification == "PRIMARY"
            else f"in regime {run_setting.regime}"
        ),
        "sealed_run_setting": run_setting.payload(),
        "world_index": world_index,
        "world_domain": domain,
        "world_seed": tape.seed,
        "learner_seed": 0,
        "cluster": {
            "tle_date": tape.tle_date,
            "world_seed": tape.seed,
            "learner_seed": 0,
            "oracle_world": world_index,
        },
        "world_manifest": tape.manifest(),
        "world_manifest_sha256": tape.digest,
        "calibration": calibration.payload(),
        "calibration_sha256": calibration.digest,
        "provider_source_sha256": provider_sha256,
        "code_authority_sha256": code_sha256,
        "anchor_stride": anchor_stride,
        "canonical_steps_rolled": 30,
        "prepared_steps": len(tape.steps),
        "prepared_step_contract": "30 executed + 3 forecast offsets",
        "c2_horizon_offsets_used": list(range(1, run_setting.c2_horizon_offsets + 1)),
        "anchor_count": len(steps),
        "catalogue_definition": catalogue_definition(),
        "catalogue_definition_sha256": catalogue_definition()["sha256"],
        "arms": list(ARMS),
        "steps": steps,
        "canonical_step_rows": canonical_rows,
        "canonical_step_rows_sha256": digest_payload(canonical_rows),
        "candidate_shortlist_miss_count": sum(
            int(step["e1_certificate"]["candidate_shortlist_miss_count"]) for step in steps
        ),
        "successor_usable_energy_range": _summarize_energy_range(steps),
        "failure_analysis": summary,
        "elapsed_seconds": elapsed,
    }
    receipt["receipt_sha256"] = digest_payload(receipt)
    return receipt


def synthetic_shortlist_miss_counts() -> dict[int, int]:
    """KAT helper: census all four synthetic probe worlds before outcomes."""

    counts: dict[int, int] = {}
    for world_index, domain in enumerate(PROBE_WORLD_DOMAINS, start=1):
        tape = build_world_tape(
            domain=domain,
            provider=TinySyntheticProvider(),
            steps=1,
            start_time_s=0.0,
        )
        base = _base_configuration(tape, 0, "nearest-eligible")
        _rows, census = _catalogue_with_census(tape, 0, base)
        counts[world_index] = census["candidate_shortlist_miss_count"]
    return counts


def _dry_run_parity_receipt() -> dict[str, object]:
    profiles = tuple(
        DecisionProfile.build(label, bits=(5, 5), energy_j=energy, served=(True, True))
        for label, energy in zip(("00", "10", "01", "11"), (10, 10, 10, 8), strict=True)
    )
    trace = trace_declared_target_decoder_parity(
        *profiles,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=2,
    )
    declared_formula = declared_c3_oracle(
        *profiles,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=2,
    )
    production_formula = production_c3(
        *profiles,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=2,
    )
    base = Configuration("00", ((0, None), (1, None)), 0, "parity")
    catalog = (
        base,
        Configuration("10", ((0, (1, 0)), (1, None)), 1, "parity"),
        Configuration("01", ((0, None), (1, (2, 0))), 1, "parity"),
        Configuration("11", ((0, (1, 0)), (1, (2, 0))), 2, "parity"),
    )

    class _ParityObjective:
        def __init__(self, profile: DecisionProfile) -> None:
            self.profile = profile

        def outcome(self) -> NetworkOutcome:
            return NetworkOutcome.build(
                bits=self.profile.total_bits,
                joules=self.profile.energy_j,
                phi=0,
                decoding_availability=1,
                useful_availability=1,
                per_user_bits=dict(enumerate(self.profile.bits)),
            )

    calibration = CalibrationValues(
        "fixture",
        "fixture",
        Fraction(1),
        Fraction(1),
        Fraction(1, 2),
        Fraction(1),
        Fraction(1),
        1,
        2,
        Fraction(1, 2),
        CALIBRATION_WORLD_DOMAINS,
        ("fixture-1", "fixture-2"),
    )
    evaluated = {
        config.configuration_id: _ParityObjective(profile)
        for config, profile in zip(catalog, profiles, strict=True)
    }
    v15_decomposition = set_score_decomposition(
        coalition_users=(0, 1),
        outcomes_by_subset={
            frozenset(): evaluated["00"].outcome(),
            frozenset((0,)): evaluated["10"].outcome(),
            frozenset((1,)): evaluated["01"].outcome(),
            frozenset((0, 1)): evaluated["11"].outcome(),
        },
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=2,
    )
    if v15_decomposition.c1 + v15_decomposition.c3 != (
        v15_decomposition.joint_change_bits / 2
    ):
        raise ProbeError("v1.5 C1+C3 set-score identity failed")
    decoder_cross: dict[str, dict[str, object]] = {}
    for formula_name, formula in (
        ("declared", declared_formula),
        ("production", production_formula),
    ):
        decoder_factors = {
            "C1": {},
            "C2": {},
            "C3": {
                (0, (1, 0)): formula.lcsrs_shares[0] / 2,
                (1, (2, 0)): formula.lcsrs_shares[1] / 2,
            },
        }
        additive = _independent_proposal(
            base=base, catalog=catalog, factors=decoder_factors, include=("C3",)
        )
        atomic = _set_select(
            catalog=catalog,
            evaluated=evaluated,  # type: ignore[arg-type]
            factors=decoder_factors,
            include=("C3",),
            base=base,
            calibration=calibration,
        )
        decoder_cross[formula_name] = {}
        for decoder_name, selected in (("additive", additive), ("atomic", atomic)):
            endpoint = profiles[("00", "10", "01", "11").index(selected.configuration_id)]
            decoder_cross[formula_name][decoder_name] = {
                "executed_action": selected.configuration_id,
                "bits": [float(value) for value in endpoint.bits],
                "joules": float(endpoint.energy_j),
                "served": list(endpoint.served),
            }
    additive = decoder_cross["production"]["additive"]
    atomic = decoder_cross["production"]["atomic"]
    if additive["executed_action"] != trace.additive_execution.action:
        raise ProbeError("production additive decoder disagrees with declared fixture")
    if atomic["executed_action"] != trace.atomic_execution.action:
        raise ProbeError("production atomic set decoder disagrees with declared fixture")
    core = reward_endpoint_identity(
        step_bits=(10, 20, 5),
        step_energy_j=(1, 3, 2),
        lambda_bits_per_j=2,
        eta_ref=2,
        kappa_bits_per_user_s=1,
    )
    capped = demand_cap_profiles(
        profiles,
        demand_cap_bits=100,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=2,
    )
    reoptimized = reoptimize_joint_by_regime(
        {"fixture": profiles},
        lambda_by_regime={"fixture": 1},
        eta_ref_by_regime={"fixture": 1},
        kappa_bits_per_user_s_by_regime={"fixture": 2},
    )
    bootstrap = common_action_bootstrap(
        ((10, 0), (0, 9)),
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=1,
    )
    payload = {
        "declared_psi": 2,
        "v15_set_score_identity": {
            "d_by_user": [
                [user, float(value)] for user, value in v15_decomposition.d_by_user
            ],
            "psi_A": float(v15_decomposition.interaction_bits),
            "shapley_interaction_by_user": [
                [user, float(value)]
                for user, value in v15_decomposition.shapley_interaction_by_user
            ],
            "C1_plus_C3": float(v15_decomposition.c1 + v15_decomposition.c3),
            "F_joint_minus_F_base_over_kappa": float(
                v15_decomposition.joint_change_bits / 2
            ),
            "exact": True,
        },
        "production_formula_matches_declared": trace.production_formula_matches_declared,
        "additive_executed_action": additive["executed_action"],
        "atomic_executed_action": atomic["executed_action"],
        "executed_endpoint_energy_j": atomic["joules"],
        "formula_decoder_cross": decoder_cross,
        "production_decoder_paths": ["_independent_proposal", "_set_select"],
        "reward_endpoint_identity_core": float(core),
        "nonbinding_demand_cap_invariant": capped == profiles,
        "per_regime_joint_reoptimization": reoptimized,
        "common_action_bootstrap": {
            "action_index": bootstrap.action_index,
            "selected_heads": [float(value) for value in bootstrap.selected_heads],
            "scalarized_value": float(bootstrap.scalarized_value),
            "unattainable_headwise_mix_rejected": bootstrap.selected_heads != (10, 9),
        },
        "raw_states_traced": sorted(trace.raw_state_endpoints),
        "t3_energy_used": False,
    }
    payload["kat_receipt_sha256"] = digest_payload(payload)
    return payload


def estimate(*, q: float | None) -> dict[str, object]:
    plan = dict(shared_computation_plan(q=q))
    reference = float(plan["reference_core_hours"])
    projected = None if q is None else reference * q * ORCHESTRATION_RESERVE
    plan.update(
        {
            "schema": f"{SCHEMA}-estimate",
            "worlds": list(PROBE_WORLD_DOMAINS),
            # Retain the sealed v1.2 matrix accounting fields.  The additive
            # contingency settings are reported separately and do not rewrite
            # the 31-cell reference estimate.
            "cells": [setting.label for setting in MATRIX_SETTINGS],
            "units": len(PROBE_WORLD_DOMAINS) * len(MATRIX_SETTINGS),
            "all_sealed_run_settings": [
                setting.run_id for setting in ALL_SEALED_RUN_SETTINGS
            ],
            "all_sealed_run_units": (
                len(PROBE_WORLD_DOMAINS) * len(ALL_SEALED_RUN_SETTINGS)
            ),
            "matrix_cells": [setting.label for setting in MATRIX_SETTINGS],
            "matrix_cells_count": len(MATRIX_SETTINGS),
            "sealed_sensitivities_enumerated_after_matrix": [
                setting.run_id for setting in ALL_SEALED_RUN_SETTINGS[len(MATRIX_SETTINGS):]
            ],
            "launch_order": [setting.run_id for setting in LAUNCH_RUN_ORDER],
            "arms": list(ARMS),
            "architecture_tape_once_treatments_rescore": True,
            "orchestration_rescore_reserve": ORCHESTRATION_RESERVE,
            "projected_core_hours_with_reserve": projected,
            "overnight_ceiling_core_hours": OVERNIGHT_CORE_HOURS,
            "within_overnight_ceiling": None if projected is None else projected <= OVERNIGHT_CORE_HOURS,
            "no_catalogue_or_world_truncation": True,
        }
    )
    return plan


def rehearsal() -> dict[str, object]:
    setting = _setting("a-r0")
    calibration = _calibrate(setting)
    started = time.perf_counter()
    receipt = run_unit(
        setting=setting,
        world_index=1,
        executed_steps=1,
        calibration=calibration,
    )
    elapsed = time.perf_counter() - started
    evaluations = sum(int(step["physical_boundary_evaluations"]) for step in receipt["steps"])
    reference_core_seconds_per_evaluation = REFERENCE_SECONDS * REFERENCE_WORKERS / REFERENCE_EVALUATIONS
    q = (elapsed / max(1, evaluations)) / reference_core_seconds_per_evaluation
    projection = estimate(q=q)
    return {
        "schema": f"{SCHEMA}-rehearsal",
        "cell": "a-r0",
        "world": 1,
        "anchors": 3,
        "arms": list(ARMS),
        "elapsed_seconds": elapsed,
        "physical_boundary_evaluations": evaluations,
        "reference": {
            "seconds": REFERENCE_SECONDS,
            "workers": REFERENCE_WORKERS,
            "evaluations": REFERENCE_EVALUATIONS,
        },
        "q": q,
        "projected_matrix_core_hours": projection["projected_core_hours_with_reserve"],
        "within_160_core_hours": projection["within_overnight_ceiling"],
        "where_time_goes_if_over_ceiling": None
        if projection["within_overnight_ceiling"]
        else {
            "geometry_channel_power_catalogue": "architecture tape construction and complete candidate census",
            "forecast": "three projected offsets with background powers recomputed",
            "rescoring": "12 arms and exact-factor per-cell selection",
            "action": "optimize shared primitive computation; do not truncate cells/worlds/catalogue",
        },
        "development_rehearsal_not_claim_panel": True,
        "unit_receipt_sha256": receipt["receipt_sha256"],
    }


def build_calibration_manifest() -> dict[str, object]:
    """Compute every disjoint-world cell calibration before any probe unit."""

    values = [
        _calibrate(_setting(run.base_cell), run) for run in ALL_SEALED_RUN_SETTINGS
    ]
    world_manifests = []
    calibration_tapes = []
    provider_profiles = (PRIMARY_RUN_SETTING, run_setting_for("R2"))
    for profile in provider_profiles:
        for world_index, domain in enumerate(CALIBRATION_WORLD_DOMAINS, start=1):
            tape = build_world_tape(
                domain=domain,
                provider=_provider_for_run(profile),
                steps=1,
                start_time_s=0.0,
            )
            calibration_tapes.append(tape)
            world_manifests.append(
                {
                    "world_index": world_index,
                    "world_profile": "R2" if profile.run_id == "R2" else "DEFAULT",
                    "domain": domain,
                    "manifest": tape.manifest(),
                    "world_manifest_sha256": tape.digest,
                }
            )
    probe_tapes = [
        build_world_tape(
            domain=domain,
            provider=_provider_for_run(profile),
            steps=1,
            start_time_s=0.0,
        )
        for profile in provider_profiles
        for domain in PROBE_WORLD_DOMAINS
    ]
    assert_calibration_world_separation(
        calibration_tapes=calibration_tapes, probe_tapes=probe_tapes
    )
    payload = {
        "schema": f"{SCHEMA}-calibration-manifest",
        "status": "FROZEN_CALIBRATION",
        "worlds": list(CALIBRATION_WORLD_DOMAINS),
        "world_manifests": world_manifests,
        "cells": [value.payload() for value in values],
        "cell_order": [setting.run_id for setting in ALL_SEALED_RUN_SETTINGS],
        "test_split_opened": False,
        "probe_outcomes_opened": False,
        "frozen_once": True,
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def build_probe_world_manifest(*, executed_steps: int = 30) -> dict[str, object]:
    """Materialize/digest the four common tapes before opening any arm outcome."""

    worlds = []
    probe_tapes = []
    provider_profiles = (PRIMARY_RUN_SETTING, run_setting_for("R2"))
    for profile in provider_profiles:
        for index, domain in enumerate(PROBE_WORLD_DOMAINS, start=1):
            tape = build_world_tape(
                domain=domain,
                provider=_provider_for_run(profile),
                steps=executed_steps + 3,
                start_time_s=0.0,
            )
            probe_tapes.append(tape)
            worlds.append(
                {
                    "world_index": index,
                    "world_profile": "R2" if profile.run_id == "R2" else "DEFAULT",
                    "domain": domain,
                    "world_seed": tape.seed,
                    "manifest": tape.manifest(),
                    "world_manifest_sha256": tape.digest,
                }
            )
    calibration_tapes = [
        build_world_tape(
            domain=domain,
            provider=WORLD_PROVIDER_FACTORY(),
            steps=1,
            start_time_s=0.0,
        )
        for domain in CALIBRATION_WORLD_DOMAINS
    ]
    assert_calibration_world_separation(
        calibration_tapes=calibration_tapes, probe_tapes=probe_tapes
    )
    payload = {
        "schema": f"{SCHEMA}-world-manifest",
        "status": "FROZEN_WORLD_MANIFEST",
        "executed_steps": executed_steps,
        "forecast_offsets": 3,
        "worlds": worlds,
        "test_split_opened": False,
        "probe_outcomes_opened": False,
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def world_allocation_identity(
    tape: ExogenousWorldTape,
    *,
    role: str,
    learner_seed: int,
) -> dict[str, object]:
    """Return the full audit-A allocation identity for one world."""

    manifest = tape.manifest()
    return {
        "role": role,
        "world_domain": tape.domain,
        "split": tape.split,
        "start_utc": manifest["start_utc"],
        "tle_date": tape.tle_date,
        "tle_files": manifest["tle_files"],
        "split_rule_sha256": manifest["split_rule_sha256"],
        "provider_source_sha256": manifest["provider_source_sha256"],
        "layout_sha256": manifest["layout_sha256"],
        "mobility_stream_identity": manifest["stream_identities"]["mobility"],  # type: ignore[index]
        "fading_stream_identity": manifest["stream_identities"]["fading"],  # type: ignore[index]
        "world_seed": tape.seed,
        "learner_seed": learner_seed,
        "world_manifest_sha256": tape.digest,
    }


def assert_role_wise_date_disjointness(
    identities: Sequence[Mapping[str, object]],
) -> None:
    """Fail closed when one successor date is reserved for multiple roles."""

    roles_by_date: dict[str, set[str]] = {}
    for row in identities:
        role, date = str(row.get("role", "")), str(row.get("tle_date", ""))
        if not role or not date:
            raise ProbeError("allocation identity lacks role or TLE date")
        roles_by_date.setdefault(date, set()).add(role)
    collisions = {date: sorted(roles) for date, roles in roles_by_date.items() if len(roles) > 1}
    if collisions:
        raise ProbeError(f"successor role-wise date collision: {collisions}")


def build_allocation_manifest(
    identities: Sequence[Mapping[str, object]],
    *,
    legacy_development_overlap_dates: Sequence[str] = (),
) -> dict[str, object]:
    """Seal role allocations and the non-causal TLE benchmark convention."""

    rows = [dict(row) for row in identities]
    assert_role_wise_date_disjointness(rows)
    required = {
        "role", "world_domain", "split", "start_utc", "tle_date", "tle_files",
        "split_rule_sha256", "provider_source_sha256", "layout_sha256",
        "mobility_stream_identity", "fading_stream_identity", "world_seed",
        "learner_seed", "world_manifest_sha256",
    }
    if any(set(row) != required for row in rows):
        raise ProbeError("allocation manifest world identity is incomplete or noncanonical")
    if any(row["split"] != "TRAIN" for row in rows):
        raise ProbeError("allocation manifest may contain TRAIN worlds only")
    roles = {str(row["role"]) for row in rows}
    required_roles = SUCCESSOR_DEVELOPMENT_ROLES | {"CLAIM_PANEL"}
    if not required_roles <= roles:
        raise ProbeError(
            "allocation manifest must enumerate CLAIM_PANEL and every successor-development role"
        )
    payload = {
        "schema": f"{SCHEMA}-allocation-manifest",
        "status": "FROZEN_ALLOCATION",
        "worlds": rows,
        "role_wise_date_disjoint": True,
        "claim_panel_date_fresh_from_successor_development": True,
        "legacy_development_overlap_dates": sorted(set(legacy_development_overlap_dates)),
        "tle_selection_convention": {
            "rule": "per NORAD choose nearest epoch from date-1/date/date+1 at episode start",
            "maximum_absolute_age_hours": 24,
            "future_epochs_allowed": True,
            "causality": "NON_CAUSAL_ACCURACY_FIRST_BENCHMARK",
            "verify_source": True,
        },
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def load_calibration(
    path: Path,
    setting: PhysicsSetting,
    run_setting: SealedRunSetting | None = None,
) -> CalibrationValues:
    target = Path(path)
    sidecar = _sidecar(target)
    if not target.is_file() or not sidecar.is_file():
        raise ProbeError("frozen calibration manifest and sidecar are required")
    encoded = target.read_bytes()
    digest = hashlib.sha256(encoded).hexdigest()
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise ProbeError("calibration sidecar disagrees")
    if stat.S_IMODE(target.stat().st_mode) != 0o444:
        raise ProbeError("calibration manifest is not immutable mode 0444")
    payload = json.loads(encoded)
    if payload.get("schema") != f"{SCHEMA}-calibration-manifest" or payload.get("status") != "FROZEN_CALIBRATION":
        raise ProbeError("calibration manifest schema/status disagrees")
    _verify_self_digest(payload, label="calibration manifest")
    run_setting = run_setting_for(setting.label) if run_setting is None else run_setting
    rows = [row for row in payload.get("cells", []) if row.get("setting_sha256") == run_setting.digest]
    if len(rows) != 1:
        raise ProbeError("calibration manifest lacks exactly one requested setting")
    return CalibrationValues.from_payload(rows[0])


def _verify_world_protocol_manifest(manifest: Mapping[str, object]) -> None:
    protocol = manifest.get("provider_protocol")
    if not isinstance(protocol, dict):
        raise ProbeError("world manifest lacks mandatory provider protocol outputs")
    for field in ("split", "start_utc", "tle_files", "split_rule_sha256", "provider_source_sha256"):
        if protocol.get(field) != manifest.get(field):
            raise ProbeError(f"world manifest provider protocol disagrees on {field}")
    if manifest.get("split") != "TRAIN":
        raise ProbeError("world manifest is not TRAIN")
    if not isinstance(manifest.get("tle_files"), list) or not manifest["tle_files"]:
        raise ProbeError("world manifest has no opened TLE bindings")
    for name, digest in manifest["tle_files"]:  # type: ignore[assignment]
        if not name or not isinstance(digest, str) or len(digest) != 64:
            raise ProbeError("world manifest has malformed TLE filename/hash output")
    for field in ("split_rule_sha256", "provider_source_sha256"):
        value = manifest.get(field)
        if not isinstance(value, str) or len(value) != 64:
            raise ProbeError(f"world manifest has malformed {field}")
    try:
        ProviderProtocolOutputs(
            split=str(protocol["split"]),
            start_utc=str(protocol["start_utc"]),
            tle_files=tuple((str(name), str(digest)) for name, digest in protocol["tle_files"]),
            split_rule_digest=str(protocol["split_rule_sha256"]),
            provider_source_digest=str(protocol["provider_source_sha256"]),
        )
    except (KeyError, TypeError, ValueError, MCRLContractError) as error:
        raise ProbeError("world manifest provider protocol is not executable/valid") from error


def load_world_binding(
    path: Path,
    world_index: int,
    run_setting: SealedRunSetting = PRIMARY_RUN_SETTING,
) -> tuple[str, dict[str, object]]:
    target = Path(path)
    sidecar = _sidecar(target)
    if not target.is_file() or not sidecar.is_file():
        raise ProbeError("frozen world manifest and sidecar are required")
    encoded = target.read_bytes()
    digest = hashlib.sha256(encoded).hexdigest()
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise ProbeError("world-manifest sidecar disagrees")
    if stat.S_IMODE(target.stat().st_mode) != 0o444:
        raise ProbeError("world manifest is not immutable mode 0444")
    payload = json.loads(encoded)
    if payload.get("schema") != f"{SCHEMA}-world-manifest" or payload.get("status") != "FROZEN_WORLD_MANIFEST":
        raise ProbeError("world manifest schema/status disagrees")
    _verify_self_digest(payload, label="world manifest")
    profile = "R2" if run_setting.run_id == "R2" else "DEFAULT"
    rows = [
        row
        for row in payload.get("worlds", [])
        if row.get("world_index") == world_index
        and row.get("world_profile", "DEFAULT") == profile
    ]
    if len(rows) != 1 or rows[0].get("domain") != _world_domain(world_index):
        raise ProbeError("world manifest lacks exactly one requested domain")
    manifest = rows[0].get("manifest")
    if not isinstance(manifest, dict):
        raise ProbeError("world manifest row lacks embedded tape manifest")
    _verify_world_protocol_manifest(manifest)
    if rows[0].get("world_manifest_sha256") != digest_payload(manifest):
        raise ProbeError("world manifest row digest does not bind its protocol outputs")
    return str(rows[0]["world_manifest_sha256"]), manifest


def load_world_digest(path: Path, world_index: int) -> str:
    """Compatibility wrapper around the stronger pre-unit protocol verifier."""

    return load_world_binding(path, world_index)[0]


def install_provider(specification: str) -> None:
    """Install ``module:factory`` for formal server world acquisition."""

    global WORLD_PROVIDER_FACTORY
    try:
        module_name, attribute = specification.split(":", 1)
        factory = getattr(importlib.import_module(module_name), attribute)
        provider = factory()
    except Exception as error:
        raise ProbeError("--provider must name an importable module:factory") from error
    for name in (
        "inventory", "cluster_identity", "protocol_outputs", "user_layout", "boundary"
    ):
        if not callable(getattr(provider, name, None)):
            raise ProbeError(f"provider lacks callable {name}")
    WORLD_PROVIDER_FACTORY = factory


def _sidecar(path: Path) -> Path:
    return Path(str(path) + ".sha256")


def _verify_self_digest(payload: Mapping[str, object], *, label: str) -> None:
    unsigned = dict(payload)
    declared = unsigned.pop("receipt_sha256", None)
    if not isinstance(declared, str) or declared != digest_payload(unsigned):
        raise ProbeError(f"{label} embedded receipt digest disagrees")


def write_immutable(path: Path, payload: Mapping[str, object]) -> str:
    target = Path(path)
    sidecar = _sidecar(target)
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise ProbeError(f"refusing to overwrite immutable receipt: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    digest = hashlib.sha256(encoded).hexdigest()
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    sidecar.chmod(0o444)
    return digest


def _unit_path(output: Path, setting: PhysicsSetting, world: int) -> Path:
    safe = setting.label.replace("′", "prime").replace("γ", "gamma")
    return output / "units" / safe / f"world-{world}.json"


def _run_unit_path(output: Path, run_setting: SealedRunSetting, world: int) -> Path:
    safe = run_setting.run_id.replace("′", "prime").replace("γ", "gamma")
    return output / "units" / safe / f"world-{world}.json"


def _nonadditivity_fraction(receipts: Sequence[Mapping[str, object]]) -> float | None:
    """Interaction share of the matched FULL-vs-BASE F change, without clipping."""

    interaction = joint = 0.0
    for receipt in receipts:
        summary = receipt["failure_analysis"]  # type: ignore[index]
        interaction += float(summary["non_additive_interaction_bits"])
        full = summary["arms"]["FULL"]  # type: ignore[index]
        base = summary["arms"][ALL_NEUTRAL_CONTROL]  # type: ignore[index]
        eta_ratio = receipt["calibration"]["eta_ref"]  # type: ignore[index]
        eta = float(eta_ratio[0]) / float(eta_ratio[1])
        joint += (float(full["bits"]) - float(base["bits"])) - eta * (
            float(full["joules"]) - float(base["joules"])
        )
    return None if joint == 0.0 else interaction / joint


def _merged_uncertainty(receipts: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Build v1.2 uncertainty and claim gates from complete unit receipts."""

    by_cell: dict[str, list[Mapping[str, object]]] = {}
    for receipt in receipts:
        by_cell.setdefault(str(receipt["cell"]), []).append(receipt)
    results: dict[str, object] = {}
    for run_setting in ALL_SEALED_RUN_SETTINGS:
        rows = sorted(by_cell[run_setting.run_id], key=lambda row: int(row["world_index"]))
        cluster_ids = [
            (
                str(row["world_manifest"]["cluster"]["tle_date"]),  # type: ignore[index]
                int(row.get("learner_seed", 0)),
            )
            for row in rows
        ]
        contrasts: dict[str, object] = {}
        for name, comparator in (
            *((name, drop) for name, (_full, drop) in MARGINALS.items()),
            ("LEVEL_A_S_UNI", "S_UNI"),
            ("ALL_NEUTRAL", ALL_NEUTRAL_CONTROL),
        ):
            grouped: dict[tuple[str, int], list[dict[str, float]]] = {}
            for row in rows:
                arms = row["failure_analysis"]["arms"]  # type: ignore[index]
                full = arms["FULL"]
                other = arms[comparator]
                grouped.setdefault(
                    (
                        str(row["world_manifest"]["cluster"]["tle_date"]),  # type: ignore[index]
                        int(row.get("learner_seed", 0)),
                    ),
                    [],
                ).append(
                    {
                        "tle_date": row["world_manifest"]["cluster"]["tle_date"],
                        "learner_seed": row["learner_seed"],
                        "full_bits": full["bits"],
                        "full_joules": full["joules"],
                        "comparator_bits": other["bits"],
                        "comparator_joules": other["joules"],
                        "full_availability_served": full["qos_additive"]["availability_served"],
                        "full_availability_opportunities": full["qos_additive"]["availability_opportunities"],
                        "comparator_availability_served": other["qos_additive"]["availability_served"],
                        "comparator_availability_opportunities": other["qos_additive"]["availability_opportunities"],
                        "full_phi_numerator": full["qos_additive"]["phi_cost_numerator"],
                        "full_phi_denominator": full["qos_additive"]["phi_cost_denominator"],
                        "comparator_phi_numerator": other["qos_additive"]["phi_cost_numerator"],
                        "comparator_phi_denominator": other["qos_additive"]["phi_cost_denominator"],
                        "full_handover_events": full["qos_additive"]["handover_events"],
                        "full_handover_opportunities": full["qos_additive"]["handover_opportunities"],
                        "comparator_handover_events": other["qos_additive"]["handover_events"],
                        "comparator_handover_opportunities": other["qos_additive"]["handover_opportunities"],
                    }
                )
            clusters = []
            for (tle_date, learner_seed), members in sorted(grouped.items()):
                clusters.append(
                    {
                        "tle_date": tle_date,
                        "learner_seed": learner_seed,
                        "full_bits": math.fsum(row["full_bits"] for row in members),
                        "full_joules": math.fsum(row["full_joules"] for row in members),
                        "comparator_bits": math.fsum(row["comparator_bits"] for row in members),
                        "comparator_joules": math.fsum(row["comparator_joules"] for row in members),
                        **{
                            field: math.fsum(row[field] for row in members)
                            for field in (
                                "full_availability_served",
                                "full_availability_opportunities",
                                "comparator_availability_served",
                                "comparator_availability_opportunities",
                                "full_phi_numerator",
                                "full_phi_denominator",
                                "comparator_phi_numerator",
                                "comparator_phi_denominator",
                                "full_handover_events",
                                "full_handover_opportunities",
                                "comparator_handover_events",
                                "comparator_handover_opportunities",
                            )
                        },
                    }
                )
            bootstrap_seed = seed_from_domain(f"V025_PROBE/bootstrap/{run_setting.run_id}/{name}")
            estimate_row = uncertainty_estimate(
                clusters,
                learner_experiment=False,
                seed=bootstrap_seed,
            )
            estimate_row["supplementary_two_way_pigeonhole"] = two_way_pigeonhole_bootstrap(
                clusters,
                seed=bootstrap_seed ^ 0x5A5A5A5A,
            )
            contrasts[name] = estimate_row["primary"] | {
                "supplementary_delta_method": estimate_row["supplementary_delta_method"],
                "supplementary_two_way_pigeonhole": estimate_row["supplementary_two_way_pigeonhole"],
            }
        marginal_rows = [contrasts[name] for name in MARGINALS]
        results[run_setting.run_id] = {
            "cluster_ids_tle_date_x_learner_seed": [[date, seed] for date, seed in sorted(set(cluster_ids))],
            "learner_seed_by_world": {
                str(row["world_index"]): row["learner_seed"]
                for row in rows
            },
            "contrasts": contrasts,
            "intersection_union_success": all(
                row["ee_margin_pass"] and row["qos_noninferior"] for row in marginal_rows  # type: ignore[index]
            ),
            "claim_scope": "FULL-minus-DROP with other two components enabled",
            "claim_classification": (
                run_setting.claim_classification
            ),
            "level_b": {
                "contrast": "FULL_vs_DROP_C3",
                "certificate": contrasts["C3"],
                "nonadditivity_fraction": _nonadditivity_fraction(rows),
            },
            "level_a": {
                "contrast": "FULL_vs_S_UNI",
                "certificate": contrasts["LEVEL_A_S_UNI"],
                "nonadditivity_fraction": _nonadditivity_fraction(rows),
            },
            "main_effects_claimed": False,
        }
    return {
        "primary_estimator": "one-way paired bootstrap over TLE dates for learner-free physics matrix",
        "learner_experiment_primary_estimator": "two-way pigeonhole bootstrap over TLE dates x learner seeds",
        "cluster_unit": "TLE date; worlds pool within a cell",
        "per_cell": results,
        "primary_a_r0_intersection_union_success": results["a-r0"]["intersection_union_success"],  # type: ignore[index]
        "all_neutral_support_only": True,
    }


def training_admission(
    *,
    primary_setting: str,
    certificates: Mapping[str, object],
    regime_certificates: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Execute the sealed PHYSICS-GO conjunction on a-r0 and nothing else."""

    if primary_setting != "a-r0":
        raise ProbeError("training admission must read a-r0 only")
    specifications = (
        ("physics_integrity", "physics/integrity PASS", lambda value: value is True),
        ("u1_complete_certified", "complete U1 census with certified optimum", lambda value: value is True),
        ("j1_beyond_base_and_u_all", "J1 beyond BASE and U_all by more than numerical error under matched QoS", lambda value: value is True),
        ("s0_relative_gain", "deployable S0 relative pooled-EE gain >= 1%", lambda value: float(value) >= 0.01),
        ("usable_energy_opportunity", "usable-energy opportunity exceeds certified numerical error where claimed", lambda value: value is True),
        ("retained_factor_marginals", "every retained FULL-minus-DROP marginal is positive under QoS", lambda value: value is True),
    )
    def evaluate(setting_id: str, values: Mapping[str, object]) -> tuple[dict[str, object], bool]:
        rows: dict[str, object] = {}
        for key, rule, predicate in specifications:
            if key not in values:
                raise ProbeError(f"{setting_id} admission certificate missing {key}")
            value = values[key]
            rows[key] = {"value": value, "rule": rule, "pass": bool(predicate(value))}
        return rows, all(bool(row["pass"]) for row in rows.values())  # type: ignore[union-attr]

    rows, passed = evaluate("a-r0", certificates)
    sensitivities = {}
    for regime, regime_values in sorted((regime_certificates or {}).items()):
        regime_rows, regime_passed = evaluate(regime, regime_values)
        sensitivities[regime] = {
            "label": f"in regime {regime}",
            "decision": "ADMIT_IN_REGIME" if regime_passed else "NOT_ADMITTED_IN_REGIME",
            "certificates": regime_rows,
            "reported_separately": True,
            "changes_primary_admission": False,
        }
    return {
        "decision": "ADMIT" if passed else "NOT_ADMITTED",
        "source_setting": "a-r0",
        "certificates": rows,
        "u1_need_not_exceed_base_for_c3": True,
        "training_setting_if_admitted": "a-r0",
        "regime_sensitivity_certificates": sensitivities,
    }


def _pooled_relative_ee(
    receipts: Sequence[Mapping[str, object]], first: str, second: str
) -> float:
    def totals(arm: str) -> tuple[float, float]:
        return (
            math.fsum(float(row["failure_analysis"]["arms"][arm]["bits"]) for row in receipts),  # type: ignore[index]
            math.fsum(float(row["failure_analysis"]["arms"][arm]["joules"]) for row in receipts),  # type: ignore[index]
        )
    first_bits, first_joules = totals(first)
    second_bits, second_joules = totals(second)
    if min(first_joules, second_joules, second_bits) <= 0.0:
        return -math.inf
    return (first_bits / first_joules) / (second_bits / second_joules) - 1.0


def _setting_admission_certificates(
    receipts: Sequence[Mapping[str, object]],
    uncertainty: Mapping[str, object],
    run_id: str,
) -> dict[str, object]:
    setting_receipts = [row for row in receipts if row["cell"] == run_id]
    if not setting_receipts:
        raise ProbeError(f"{run_id} receipts are required for admission reporting")
    setting_uncertainty = uncertainty["per_cell"][run_id]  # type: ignore[index]
    factors = [setting_uncertainty["contrasts"][name] for name in MARGINALS]  # type: ignore[index]
    numerical_error = 1.0e-9
    return {
        "physics_integrity": all(row.get("status") == "COMPLETE" for row in setting_receipts),
        "u1_complete_certified": all(
            step["e1_certificate"]["candidate_census_complete"]
            for row in setting_receipts
            for step in row["steps"]  # type: ignore[index]
        ),
        "j1_beyond_base_and_u_all": all(
            step["e1_certificate"]["genuine_multi_user_witness"]
            for row in setting_receipts
            for step in row["steps"]  # type: ignore[index]
        ),
        "s0_relative_gain": _pooled_relative_ee(
            setting_receipts, "S0_DEPLOYABLE", ALL_NEUTRAL_CONTROL
        ),
        "usable_energy_opportunity": any(
            abs(float(value)) > numerical_error
            for row in setting_receipts
            for value in row["successor_usable_energy_range"]["best_feasible_reassignment_dc_energy_change_j_by_beam"].values()  # type: ignore[index]
        ),
        "retained_factor_marginals": all(
            bool(row["ee_margin_pass"] and row["qos_noninferior"]) for row in factors
        ),
    }


def report_schema() -> dict[str, object]:
    """Return the executable, TRAIN-only v1.5 claim classification."""

    return {
        "only_primary_setting": "a-r0",
        "primary_claim": "conditional conjunction",
        "all_other_settings": "EXPLORATORY_SENSITIVITY",
        "panel": "TRAIN_ONLY",
    }


def merge(output: Path) -> dict[str, object]:
    registry = _attempt_records()
    by_attempt: dict[str, list[dict[str, object]]] = {}
    for record in registry:
        by_attempt.setdefault(str(record["attempt_id"]), []).append(record)
    bindings = []
    receipts = []
    for run_setting in ALL_SEALED_RUN_SETTINGS:
        setting = _setting(run_setting.base_cell)
        for world in range(1, 5):
            path = _run_unit_path(output, run_setting, world)
            sidecar = _sidecar(path)
            if not path.is_file() or not sidecar.is_file():
                raise ProbeError(f"merge waiting for {run_setting.run_id}:{world}")
            encoded = path.read_bytes()
            digest = hashlib.sha256(encoded).hexdigest()
            if sidecar.read_text(encoding="ascii").split() != [digest, path.name]:
                raise ProbeError(f"unit digest sidecar mismatch: {path}")
            if stat.S_IMODE(path.stat().st_mode) != 0o444:
                raise ProbeError(f"unit is not immutable mode 0444: {path}")
            receipt = json.loads(encoded)
            if receipt.get("cell_sha256") != run_setting.digest or receipt.get("world_index") != world:
                raise ProbeError(f"unit identity mismatch: {path}")
            if receipt.get("claim_classification") != run_setting.claim_classification:
                raise ProbeError(f"unit claim classification mismatch: {path}")
            if receipt.get("schema") != UNIT_SCHEMA or receipt.get("status") != "COMPLETE":
                raise ProbeError(f"unit schema/status mismatch: {path}")
            attempt_id = receipt.get("attempt_id")
            attempt_rows = by_attempt.get(str(attempt_id), [])
            statuses = [row.get("status") for row in attempt_rows]
            if statuses != ["STARTED", "DONE"]:
                raise ProbeError(f"unit lacks one clean STARTED/DONE attempt: {path}")
            if any(row.get("status") == "ABANDONED" for row in attempt_rows):
                raise ProbeError(f"unit has an unadjudicated abandoned attempt: {path}")
            _verify_self_digest(receipt, label=f"unit {run_setting.run_id}:{world}")
            if receipt.get("world_manifest_sha256") != digest_payload(receipt["world_manifest"]):
                raise ProbeError(f"embedded world-manifest digest mismatch: {path}")
            if receipt.get("calibration_sha256") != digest_payload(receipt["calibration"]):
                raise ProbeError(f"embedded calibration digest mismatch: {path}")
            if receipt.get("canonical_step_rows_sha256") != digest_payload(
                receipt.get("canonical_step_rows")
            ):
                raise ProbeError(f"canonical step-row digest mismatch: {path}")
            _verify_reaggregation(
                receipt["canonical_step_rows"],  # type: ignore[arg-type]
                receipt["failure_analysis"],  # type: ignore[arg-type]
            )
            receipts.append(receipt)
            bindings.append({"cell": run_setting.run_id, "world": world, "path": str(path), "sha256": digest})
    for world in range(1, 5):
        default_digests = {
            row["world_manifest_sha256"]
            for row in receipts
            if row["world_index"] == world and row["cell"] != "R2"
        }
        r2_digests = {
            row["world_manifest_sha256"]
            for row in receipts
            if row["world_index"] == world and row["cell"] == "R2"
        }
        if len(default_digests) != 1 or len(r2_digests) != 1:
            raise ProbeError(f"world {world} is not common within each provider regime")
    for run_setting in ALL_SEALED_RUN_SETTINGS:
        digests = {row["calibration_sha256"] for row in receipts if row["cell"] == run_setting.run_id}
        if len(digests) != 1:
            raise ProbeError(f"calibration drift across worlds for {run_setting.run_id}")
    strides = {int(row.get("anchor_stride", 0)) for row in receipts}
    if len(strides) != 1 or next(iter(strides)) < 1:
        raise ProbeError("merge refuses missing or mixed anchor strides")
    catalogue_digests = {row.get("catalogue_definition_sha256") for row in receipts}
    if catalogue_digests != {catalogue_definition()["sha256"]}:
        raise ProbeError("catalogue definition drift across units")
    uncertainty = _merged_uncertainty(receipts)
    admission = training_admission(
        primary_setting="a-r0",
        certificates=_setting_admission_certificates(receipts, uncertainty, "a-r0"),
        regime_certificates={
            run.regime: _setting_admission_certificates(
                receipts, uncertainty, run.run_id
            )
            for run in (
                *REGIME_RUN_SETTINGS,
                run_setting_for("a′-r0"),
                run_setting_for("a-γ0"),
            )
        },
    )
    payload = {
        "schema": MERGE_SCHEMA,
        "status": "COMPLETE",
        "units": bindings,
        "unit_count": len(bindings),
        "cell_order": [setting.run_id for setting in ALL_SEALED_RUN_SETTINGS],
        "worlds": list(PROBE_WORLD_DOMAINS),
        "all_cells_reported": True,
        "anchor_stride": next(iter(strides)),
        "catalogue_definition_sha256": catalogue_definition()["sha256"],
        "test_split_opened": False,
        "training": False,
        "uncertainty": uncertainty,
        "training_admission": admission,
        "report_schema": report_schema(),
        "summary_sha256": digest_payload([receipt["failure_analysis"] for receipt in receipts]),
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--unit", metavar="CELL:WORLD")
    modes.add_argument("--merge", action="store_true")
    modes.add_argument("--estimate", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--rehearsal", action="store_true")
    modes.add_argument("--calibrate", action="store_true")
    modes.add_argument("--manifest", action="store_true")
    modes.add_argument("--allocation", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--provider", help="formal server primitive provider as module:factory")
    parser.add_argument("--calibration", type=Path, help="immutable calibration manifest for --unit")
    parser.add_argument("--world-manifest", type=Path, help="immutable pre-outcome world manifest for --unit")
    parser.add_argument(
        "--allocation-input",
        type=Path,
        help="JSON allocation identities consumed by --allocation",
    )
    parser.add_argument("--q", type=float)
    parser.add_argument("--anchor-stride", type=int, default=1)
    parser.add_argument("--executed-steps", type=int, default=30)
    parser.add_argument("--smoke-not-matrix", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.provider:
        install_provider(args.provider)
    if args.estimate:
        print(json.dumps(estimate(q=args.q), indent=2, sort_keys=True))
        return 0
    if args.dry_run:
        receipt = run_unit(setting=_setting("a-r0"), world_index=1, executed_steps=1)
        parity = _dry_run_parity_receipt()
        result = {
            "schema": f"{SCHEMA}-dry-run",
            "status": "PASS",
            "one_real_step_every_arm": [row["arm"] for row in receipt["steps"][0]["arms"]],
            "arms_expected": list(ARMS),
            "no_environment_clone": True,
            "world_manifest_sha256": receipt["world_manifest_sha256"],
            "calibration_sha256": receipt["calibration_sha256"],
            "unit_receipt_sha256": receipt["receipt_sha256"],
            "declared_target_decoder_parity": parity,
            "kat_receipt_sha256": parity["kat_receipt_sha256"],
            "reward_endpoint_identity_checked": True,
            "candidate_shortlist_miss_counts": synthetic_shortlist_miss_counts(),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.rehearsal:
        payload = rehearsal()
        path = args.output / "rehearsal.json"
        digest = write_immutable(path, payload)
        print(json.dumps({"status": "COMPLETE", "path": str(path), "file_sha256": digest, **payload}, indent=2, sort_keys=True))
        return 0
    if args.calibrate:
        if not args.provider:
            raise SystemExit("--calibrate requires the formal server --provider module:factory")
        payload = build_calibration_manifest()
        path = args.output / "calibration-manifest.json"
        digest = write_immutable(path, payload)
        print(json.dumps({"status": "FROZEN_CALIBRATION", "path": str(path), "file_sha256": digest}, indent=2, sort_keys=True))
        return 0
    if args.manifest:
        if not args.provider:
            raise SystemExit("--manifest requires the formal server --provider module:factory")
        payload = build_probe_world_manifest()
        path = args.output / "world-manifest.json"
        digest = write_immutable(path, payload)
        print(json.dumps({"status": "FROZEN_WORLD_MANIFEST", "path": str(path), "file_sha256": digest}, indent=2, sort_keys=True))
        return 0
    if args.allocation:
        if args.allocation_input is None:
            raise SystemExit("--allocation requires --allocation-input")
        try:
            source = json.loads(args.allocation_input.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"invalid --allocation-input: {error}") from error
        if not isinstance(source, (list, dict)):
            raise SystemExit("--allocation-input must be a list or JSON object")
        identities = source if isinstance(source, list) else source.get("worlds")
        if not isinstance(identities, list):
            raise SystemExit("--allocation-input must be a list or contain a worlds list")
        overlap = [] if isinstance(source, list) else source.get(
            "legacy_development_overlap_dates", []
        )
        if not isinstance(overlap, list) or not all(
            isinstance(value, str) for value in overlap
        ):
            raise SystemExit("legacy_development_overlap_dates must be a list of strings")
        payload = build_allocation_manifest(
            identities,
            legacy_development_overlap_dates=overlap,
        )
        path = args.output / "allocation-manifest.json"
        digest = write_immutable(path, payload)
        print(json.dumps({"status": "FROZEN_ALLOCATION", "path": str(path), "file_sha256": digest}, indent=2, sort_keys=True))
        return 0
    if args.unit:
        if not args.provider or args.calibration is None or args.world_manifest is None:
            raise SystemExit(
                "formal --unit requires --provider module:factory, --calibration manifest, "
                "and --world-manifest"
            )
        try:
            cell, world_text = args.unit.rsplit(":", 1)
            run_setting = run_setting_for(cell)
            setting = _setting(run_setting.base_cell)
            world = int(world_text)
        except (ValueError, ProbeError) as error:
            raise SystemExit(f"invalid --unit CELL:WORLD: {error}") from error
        frozen_calibration = load_calibration(args.calibration, setting, run_setting)
        world_digest, expected_world_manifest = load_world_binding(
            args.world_manifest, world, run_setting
        )
        attempt_id = str(uuid.uuid4())
        authority = {
            "code_sha256": _code_authority_digest(),
            "provider_sha256": expected_world_manifest["provider_source_sha256"],
            "world_sha256": world_digest,
            "calibration_sha256": frozen_calibration.digest,
        }
        append_attempt(
            status="STARTED",
            attempt_id=attempt_id,
            experiment="V025_PHYSICS_SUCCESSOR",
            panel="SMOKE" if args.smoke_not_matrix else "PROBE_R2",
            cell=run_setting.run_id,
            unit=str(world),
            authority=authority,
        )
        try:
            receipt = run_unit(
                setting=setting,
                world_index=world,
                executed_steps=args.executed_steps,
                anchor_stride=args.anchor_stride,
                smoke_not_matrix=args.smoke_not_matrix,
                attempt_id=attempt_id,
                calibration=frozen_calibration,
                expected_world_digest=world_digest,
                expected_world_manifest=expected_world_manifest,
                run_setting=run_setting,
            )
            path = (
                args.output / "smoke" / "a-r0-world-1.json"
                if args.smoke_not_matrix
                else _run_unit_path(args.output, run_setting, world)
            )
            digest = write_immutable(path, receipt)
        except Exception:
            append_attempt(
                status="ABANDONED",
                attempt_id=attempt_id,
                experiment="V025_PHYSICS_SUCCESSOR",
                panel="SMOKE" if args.smoke_not_matrix else "PROBE_R2",
                cell=run_setting.run_id,
                unit=str(world),
                authority=authority,
            )
            raise
        append_attempt(
            status="DONE",
            attempt_id=attempt_id,
            experiment="V025_PHYSICS_SUCCESSOR",
            panel="SMOKE" if args.smoke_not_matrix else "PROBE_R2",
            cell=run_setting.run_id,
            unit=str(world),
            authority={**authority, "receipt_file_sha256": digest},
        )
        print(json.dumps({"status": "COMPLETE", "path": str(path), "file_sha256": digest}, indent=2, sort_keys=True))
        return 0
    payload = merge(args.output)
    path = args.output / "merged-receipt.json"
    digest = write_immutable(path, payload)
    print(json.dumps({"status": "COMPLETE", "path": str(path), "file_sha256": digest}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
