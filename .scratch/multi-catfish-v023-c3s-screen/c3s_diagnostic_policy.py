#!/usr/bin/env python3
"""Placebo and hostile-baseline policies for the C3-S diagnostic panel."""

from __future__ import annotations

import copy
from dataclasses import replace
from fractions import Fraction
import hashlib
import time
from typing import Any, Mapping, Sequence

import numpy as np

import c3s_policy


RANDOM_DOMAIN_PREFIX = "C3S_DIAG/random/"  # Task specification, 2026-09-08.
SHUFFLE_DOMAIN_PREFIX = "C3S_DIAG/shuffle/"  # Task specification, 2026-09-08.
RENEW_DOMAIN_PREFIX = "C3S_DIAG/renew/"  # Task specification, 2026-09-08.
SEED_MASK = (1 << 63) - 1  # Repository SHA-256 world-seed rule.
FORCED_RENEW_AGE = 4  # Frozen simulator dwell N; task declaration, 2026-09-08.
RANDOM_RENEW_K = 3  # LITE moves about one configuration/decision; K=3 brackets it.


class DiagnosticPolicyError(RuntimeError):
    """A diagnostic selector violated its declared information or catalog rule."""


def derive_seed(domain: str) -> int:
    """Apply the repository's domain-separated SHA-256 seed rule."""

    try:
        encoded = domain.encode("ascii")
    except (AttributeError, UnicodeEncodeError) as error:
        raise DiagnosticPolicyError("randomisation domain must be ASCII") from error
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big") & SEED_MASK


def _eligible(catalog: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    if not catalog or catalog[0].get("profile_id") != "BASE":
        raise DiagnosticPolicyError("diagnostic catalog must begin with BASE")
    nominal = catalog[0].get("nominal")
    if not isinstance(nominal, Mapping):
        raise DiagnosticPolicyError("BASE nominal metric is absent")
    try:
        threshold = int(nominal["served"])
    except (KeyError, TypeError, ValueError) as error:
        raise DiagnosticPolicyError("BASE nominal service is malformed") from error
    rows: list[Mapping[str, object]] = []
    for row in catalog:
        metric = row.get("nominal")
        if not isinstance(metric, Mapping):
            raise DiagnosticPolicyError("candidate nominal metric is absent")
        if int(metric.get("served", -1)) >= threshold:
            rows.append(row)
    if not rows:
        raise DiagnosticPolicyError("nominal service guard has no feasible candidate")
    return rows


def restricted_catalog(
    catalog: Sequence[Mapping[str, object]], *, keep: str,
) -> tuple[Mapping[str, object], ...]:
    """Retain BASE plus exactly one declared LITE candidate family."""

    if keep not in {"unilateral", "joint"}:
        raise DiagnosticPolicyError("catalog restriction must be unilateral or joint")
    rows = tuple(row for row in catalog if row.get("kind") in {"base", keep})
    if not rows or rows[0].get("profile_id") != "BASE":
        raise DiagnosticPolicyError("restricted catalog lost BASE")
    if any(row.get("kind") not in {"base", keep} for row in rows):
        raise DiagnosticPolicyError("restricted catalog leaked another family")
    return rows


def random_feasible_candidate(
    catalog: Sequence[Mapping[str, object]], *, domain: str,
) -> Mapping[str, object]:
    """Choose uniformly from the nominal-service-feasible LITE rows."""

    rows = _eligible(catalog)
    generator = np.random.default_rng(derive_seed(domain))
    return rows[int(generator.integers(0, len(rows)))]


def shuffled_score_candidate(
    catalog: Sequence[Mapping[str, object]], *, eta_ref: Fraction, domain: str,
) -> Mapping[str, object]:
    """Permute the LITE nominal score vector, then guarded argmax it."""

    rows = list(catalog)
    if not rows:
        raise DiagnosticPolicyError("cannot shuffle an empty catalog")
    scores = [c3s_policy.nominal_score(row["nominal"], eta_ref) for row in rows]  # type: ignore[arg-type]
    permutation = np.random.default_rng(derive_seed(domain)).permutation(len(rows))
    assigned = {id(row): scores[int(permutation[index])] for index, row in enumerate(rows)}
    eligible = _eligible(rows)
    best = max(assigned[id(row)] for row in eligible)
    tied = [row for row in eligible if assigned[id(row)] == best]
    return min(tied, key=c3s_policy._tie_key)


def learned_decision(
    snapshot: c3s_policy.DecisionSnapshot,
    evaluator: c3s_policy.NominalSnapshotEvaluator,
    *, arm: str, world: int, lineage: int, step: int,
) -> c3s_policy.DecisionResult:
    """Run one learned-proposal diagnostic through the detached C3-S path."""

    phases: dict[str, float] = {"q_inference": snapshot.q_inference_seconds}
    started = time.perf_counter()
    catalog = c3s_policy.build_s0_catalog(
        snapshot=snapshot, evaluator=evaluator, timing_out=phases,
    )
    phases["catalog_total"] = time.perf_counter() - started
    unique = int(phases.pop("unique_nominal_evaluations"))
    selecting = time.perf_counter()
    if arm == "NULL":
        # Exercise catalog, exact score, and guard, then deliberately execute BASE.
        c3s_policy.select_candidate(catalog, eta_ref=snapshot.eta_ref)
        selected = catalog[0]
    elif arm == "RANDOM_FEASIBLE":
        selected = random_feasible_candidate(
            catalog,
            domain=f"{RANDOM_DOMAIN_PREFIX}{world}/{lineage}/{step}",
        )
    elif arm == "SHUFFLED_SCORE":
        selected = shuffled_score_candidate(
            catalog, eta_ref=snapshot.eta_ref,
            domain=f"{SHUFFLE_DOMAIN_PREFIX}{world}/{lineage}/{step}",
        )
    elif arm == "LITE_UNILATERAL_ONLY":
        selected = c3s_policy.select_candidate(
            restricted_catalog(catalog, keep="unilateral"), eta_ref=snapshot.eta_ref,
        )
        catalog = restricted_catalog(catalog, keep="unilateral")
    elif arm == "LITE_EVACUATION_ONLY":
        selected = c3s_policy.select_candidate(
            restricted_catalog(catalog, keep="joint"), eta_ref=snapshot.eta_ref,
        )
        catalog = restricted_catalog(catalog, keep="joint")
    else:
        raise DiagnosticPolicyError(f"unsupported learned diagnostic arm: {arm}")
    phases["selection"] = time.perf_counter() - selecting
    counts = {
        kind: sum(row.get("kind") == kind for row in catalog)
        for kind in ("base", "unilateral", "joint")
    }
    return c3s_policy.DecisionResult(
        actions=np.asarray(selected["actions"], dtype=np.int64),
        base_actions=np.asarray(snapshot.base_actions, dtype=np.int64),
        profile_id=str(selected["profile_id"]), catalog_size=len(catalog),
        counts=counts, nominal=dict(selected["nominal"]),
        phase_wall_seconds=phases, unique_nominal_evaluations=unique,
    )


def nominal_local_snr_actions(step_env: Any, observation: Any) -> np.ndarray:
    """Q-free local policy using unit-fading/zero-shadow current-slot SINR."""

    from mcrl.env.action_contract import NUM_BEAM_SLOTS

    before = c3s_policy._structural_sha256(step_env)
    candidates = observation.candidates
    tables = tuple(candidates.slot_tables)
    users = len(tables)
    norads = np.stack([np.asarray(table.norad_ids) for table in tables])
    cells = np.stack([np.asarray(table.cell_ids) for table in tables])
    theta = np.zeros((users, norads.shape[1]), dtype=np.float64)
    for slot in range(candidates.off_axis_deg.shape[1]):
        block = slice(slot * NUM_BEAM_SLOTS, (slot + 1) * NUM_BEAM_SLOTS)
        angles = np.asarray(candidates.off_axis_deg[:, slot, :], dtype=np.float64)
        theta[:, block] = np.where(np.isnan(angles), 0.0, angles)
    context = copy.copy(step_env)
    context.physics = replace(step_env.physics, fading_enabled=False)
    quality = type(step_env)._candidate_sinr(
        context, candidates, theta, norads, cells,
        np.random.default_rng(derive_seed("C3S_DIAG/nominal/no-rng-consumed")),
    )
    actions = np.full(users, c3s_policy.f1.NO_OP_ACTION, dtype=np.int64)
    for user, table in enumerate(tables):
        legal = np.flatnonzero(np.asarray(table.mask, dtype=np.bool_))
        if legal.size:
            if not np.all(np.isfinite(quality[user, legal])):
                raise DiagnosticPolicyError("nominal SNR is non-finite on a legal slot")
            actions[user] = min(
                (int(action) for action in legal.tolist()),
                key=lambda action: (-float(quality[user, action]), action),
            )
    if c3s_policy._structural_sha256(step_env) != before:
        raise DiagnosticPolicyError("Q-free nominal SNR selector mutated live state")
    return actions


def current_association_actions(step_env: Any, observation: Any) -> np.ndarray:
    """Project incumbents to legal slots, canonically repairing absent incumbents."""

    tables = tuple(observation.candidates.slot_tables)
    associations = tuple(getattr(step_env, "_previous_association", ()))
    if len(associations) != len(tables):
        raise DiagnosticPolicyError("committed association/user count differs")
    actions = np.full(len(tables), c3s_policy.f1.NO_OP_ACTION, dtype=np.int64)
    for user, (association, table) in enumerate(zip(associations, tables, strict=True)):
        legal = [int(value) for value in np.flatnonzero(table.mask).tolist()]
        if not legal:
            continue
        incumbent = None
        if association is not None:
            incumbent = (int(association.norad_id), int(association.cell_id))
        matches = [
            action for action in legal
            if (int(table.norad_ids[action]), int(table.cell_ids[action])) == incumbent
        ]
        actions[user] = min(matches) if matches else min(legal)
    return actions


def segment_ages_before_decision(step_env: Any, users: int) -> np.ndarray:
    """Return committed association ages, including the step-zero warm ages."""

    segments = tuple(getattr(step_env, "_segments", ()))
    if len(segments) != users:
        raise DiagnosticPolicyError("segment/user count differs")
    ages = np.asarray([
        0 if segment is None else int(getattr(segment, "age_steps", -1))
        for segment in segments
    ], dtype=np.int64)
    if np.any(ages < 0):
        raise DiagnosticPolicyError("association segment age is negative")
    pending = getattr(step_env, "_pending_segment_age", None)
    if int(getattr(step_env, "_step_index", -1)) == 0 and pending is not None:
        opening = np.asarray(pending, dtype=np.int64)
        if opening.shape != (users,) or np.any(opening < 0):
            raise DiagnosticPolicyError("opening segment ages are malformed")
        ages = np.where(ages == 0, opening, ages)
    return ages


def _physical_key(table: Any, action: int) -> tuple[int, int] | None:
    if action == c3s_policy.f1.NO_OP_ACTION:
        return None
    return (int(table.norad_ids[action]), int(table.cell_ids[action]))


class ChurnSelector:
    """Unscored random-renew and BASE-forced-renew diagnostic policies."""

    def __init__(
        self, *, arm: str, world: int, lineage: int,
        base_proposer: Any,
    ) -> None:
        if arm not in {"RANDOM_RENEW", "RANDOM_RENEW_K", "BASE_FORCED_RENEW_4"}:
            raise DiagnosticPolicyError("unknown churn diagnostic arm")
        self.arm = arm
        self.world = int(world)
        self.lineage = int(lineage)
        self.base_proposer = base_proposer
        self.decision_records: list[dict[str, object]] = []
        self.q_head_accesses = 2

    def select_actions(
        self, step_env: Any, observation: Any, _rng: np.random.Generator,
    ) -> np.ndarray:
        started = time.perf_counter()
        base = np.asarray(self.base_proposer(step_env, observation), dtype=np.int64)
        if base.ndim != 1 or base.size < 1:
            raise DiagnosticPolicyError("BASE proposal is malformed")
        users = base.shape[0]
        masks = np.asarray(observation.masks, dtype=np.bool_)
        if masks.shape != (users, c3s_policy.f1.NUM_ACTIONS):
            raise DiagnosticPolicyError("churn mask is malformed")
        rows = np.arange(users)
        eligible = np.any(masks, axis=1)
        if np.any(~masks[rows[eligible], base[eligible]]):
            raise DiagnosticPolicyError("BASE proposal is illegal")
        actions = base.copy()
        renewal_users: list[int] = []
        edited_users: list[int] = []

        if self.arm == "BASE_FORCED_RENEW_4":
            ages = segment_ages_before_decision(step_env, users)
            renewal_users = [
                int(uid) for uid in np.flatnonzero(eligible & (ages >= FORCED_RENEW_AGE))
            ]
            configuration = "BASE_FORCED_RENEW_4"
        else:
            tables = tuple(observation.candidates.slot_tables)
            previous = tuple(getattr(step_env, "_previous_association", ()))
            if len(tables) != users or len(previous) != users:
                raise DiagnosticPolicyError("churn association/candidate count differs")
            alternatives: dict[int, np.ndarray] = {}
            for uid in range(users):
                legal = np.flatnonzero(masks[uid])
                base_key = _physical_key(tables[uid], int(base[uid]))
                incumbent = previous[uid]
                incumbent_key = None if incumbent is None else (
                    int(incumbent.norad_id), int(incumbent.cell_id)
                )
                options = np.asarray([
                    int(action) for action in legal.tolist()
                    if _physical_key(tables[uid], int(action)) != base_key
                    or (
                        incumbent_key is not None
                        and _physical_key(tables[uid], int(action)) == incumbent_key
                    )
                ], dtype=np.int64)
                if options.size == 0:
                    continue
                if incumbent is not None and not any(
                    _physical_key(tables[uid], int(action))
                    == incumbent_key
                    for action in legal.tolist()
                ):
                    continue
                alternatives[uid] = options
            count = 1 if self.arm == "RANDOM_RENEW" else RANDOM_RENEW_K
            if len(alternatives) < count:
                raise DiagnosticPolicyError(
                    f"{self.arm} needs {count} users with a legal non-BASE edit"
                )
            generator = np.random.default_rng(derive_seed(
                f"{RENEW_DOMAIN_PREFIX}{self.world}/{self.lineage}/"
                f"{len(self.decision_records)}"
            ))
            ordered = np.asarray(sorted(alternatives), dtype=np.int64)
            edited_users = [
                int(value)
                for value in generator.choice(
                    ordered, size=count, replace=False,
                ).tolist()
            ]
            for uid in edited_users:
                options = alternatives[uid]
                actions[uid] = int(options[int(generator.integers(0, len(options)))])
                incumbent = previous[uid]
                if incumbent is not None and _physical_key(tables[uid], int(actions[uid])) == (
                    int(incumbent.norad_id), int(incumbent.cell_id)
                ):
                    renewal_users.append(uid)
            configuration = (
                "RANDOM_UNILATERAL_RENEW_K1"
                if count == 1 else "RANDOM_UNILATERAL_RENEW_K3"
            )

        changed = 0
        if edited_users:
            tables = tuple(observation.candidates.slot_tables)
            changed = sum(
                _physical_key(tables[uid], int(actions[uid]))
                != _physical_key(tables[uid], int(base[uid]))
                for uid in edited_users
            )
        expected = 0 if self.arm == "BASE_FORCED_RENEW_4" else (
            1 if self.arm == "RANDOM_RENEW" else RANDOM_RENEW_K
        )
        if len(edited_users) != expected:
            raise DiagnosticPolicyError(
                f"{self.arm} edited {len(edited_users)} users; expected {expected}"
            )
        self.decision_records.append({
            "decision_index": len(self.decision_records), "arm": self.arm,
            "q_head_accesses": 2, "selected_profile_id": configuration,
            "executed_configuration_type": configuration,
            "users_changed_vs_base": changed,
            "edited_users": edited_users,
            "explicit_renewal_users": renewal_users,
            "catalog_size": 0, "unique_nominal_evaluations": 0,
            "selected_nominal": None,
            "wall_seconds_hex": (time.perf_counter() - started).hex(),
            "information_rule": "BASE_PROPOSAL_PLUS_UNSCORED_LEGAL_CHURN",
        })
        return actions


def _detached_snapshot(
    step_env: Any, observation: Any, *, reference: np.ndarray,
    ranking: np.ndarray | None = None,
) -> tuple[c3s_policy.DecisionSnapshot, c3s_policy.NominalSnapshotEvaluator]:
    """Build the existing capability-free nominal evaluator without Q inference."""

    from mcrl.env.action_contract import SlotTable

    original = observation.candidates
    tables = tuple(
        SlotTable(
            norad_ids=c3s_policy._readonly(table.norad_ids, dtype=np.int64),
            cell_ids=c3s_policy._readonly(table.cell_ids, dtype=np.int64),
            mask=c3s_policy._readonly(table.mask, dtype=np.bool_),
        )
        for table in tuple(original.slot_tables)
    )
    candidates = c3s_policy.FrozenCandidates(
        slot_tables=tables,
        off_axis_deg=c3s_policy._readonly(original.off_axis_deg, dtype=np.float64),
        elevation_deg=c3s_policy._readonly(original.elevation_deg, dtype=np.float64),
        window_satellite_ecef_km=c3s_policy._readonly(
            original.window_satellite_ecef_km, dtype=np.float64
        ),
        window_norad_ids=c3s_policy._readonly(original.window_norad_ids, dtype=np.int64),
    )
    users = len(tables)
    masks = np.stack([table.mask for table in tables])
    keys = np.stack([np.stack((table.norad_ids, table.cell_ids), axis=1) for table in tables])
    pending = getattr(step_env, "_pending_segment_age", None)
    history: list[tuple[int, tuple[tuple[int, np.ndarray], ...]]] = []
    if int(getattr(step_env, "_step_index", -1)) == 0 and pending is not None:
        for age in sorted(set(int(value) for value in np.asarray(pending).tolist())):
            if age > 0:
                positions = step_env.driver.satellite_ecef_at(-age)
                history.append((-age, tuple(
                    (int(norad), c3s_policy._readonly(position, dtype=np.float64))
                    for norad, position in sorted(positions.items())
                )))
    physics = c3s_policy.NominalPhysicsSnapshot(
        candidates=candidates, grid=c3s_policy._copy_grid(step_env.driver.grid),
        user_ecef_km=c3s_policy._readonly(step_env.driver.user_ecef_km(), dtype=np.float64),
        historical_satellite_ecef=tuple(history),
        physics=replace(step_env.physics, fading_enabled=False),
        segments=tuple(copy.deepcopy(getattr(step_env, "_segments", ()))),
        previous_association=tuple(copy.deepcopy(getattr(step_env, "_previous_association", ()))),
        pending_segment_age=None if pending is None else c3s_policy._readonly(pending, dtype=np.int64),
        step_index=int(getattr(step_env, "_step_index", -1)),
    )
    surface = np.zeros((users, c3s_policy.f1.NUM_ACTIONS), dtype=np.float32)
    if ranking is not None:
        surface = np.asarray(ranking, dtype=np.float32)
    snapshot = c3s_policy.DecisionSnapshot(
        native_state_matrix=c3s_policy._readonly(np.zeros((users, 1)), dtype=np.float32),
        legal_masks=c3s_policy._readonly(masks, dtype=np.bool_),
        slot_physical_keys=c3s_policy._readonly(keys, dtype=np.int64),
        q12_proposal=c3s_policy._readonly(surface, dtype=np.float32),
        base_actions=c3s_policy._readonly(reference, dtype=np.int64), candidates=candidates,
        committed_association=physics.previous_association,
        committed_segments=physics.segments,
        committed_radiating=copy.deepcopy(getattr(step_env, "_previous_radiating", None)),
        tracking_state=(copy.deepcopy(original.d2), copy.deepcopy(original.dwell)),
        interval_s=float(step_env.driver.config.ephemeris.time_step_s),
        catalog="full", eta_ref=c3s_policy.load_eta_ref(), q_inference_seconds=0.0,
    )
    evaluator = c3s_policy.NominalSnapshotEvaluator(
        physics,
        physics_override=getattr(step_env, "diagnostic_physics_override", None),
    )
    c3s_policy._freeze_nested_arrays((snapshot, evaluator))
    snapshot.verify()
    evaluator.verify()
    return snapshot, evaluator


def heuristic_lite_catalog(
    snapshot: c3s_policy.DecisionSnapshot,
    evaluator: c3s_policy.NominalSnapshotEvaluator,
    *, timing_out: dict[str, float] | None = None,
) -> tuple[Mapping[str, object], ...]:
    """Top-2-per-user catalog where the alternative is ranked by nominal F."""

    full = c3s_policy.build_s0_catalog(
        snapshot=snapshot, evaluator=evaluator, timing_out=timing_out,
    )
    base = full[0]
    by_user: dict[int, list[Mapping[str, object]]] = {}
    joints: list[Mapping[str, object]] = []
    for row in full[1:]:
        if row.get("kind") == "unilateral":
            user = int(str(row["profile_id"]).split(":")[1])
            by_user.setdefault(user, []).append(row)
        elif row.get("kind") == "joint":
            joints.append(row)
    chosen: list[Mapping[str, object]] = []
    for user in sorted(by_user):
        options = by_user[user]
        best_score = max(c3s_policy.nominal_score(row["nominal"], snapshot.eta_ref) for row in options)  # type: ignore[arg-type]
        chosen.append(min(
            (row for row in options if c3s_policy.nominal_score(row["nominal"], snapshot.eta_ref) == best_score),  # type: ignore[arg-type]
            key=c3s_policy._tie_key,
        ))
    return (base, *chosen, *joints)


class QFreeSelector:
    """State-neutral HEUR, HEUR+C3-S-lite, and nominal-MPC selector."""

    def __init__(self, *, arm: str) -> None:
        if arm not in {"HEUR", "HEUR_C3S_LITE", "NOMINAL_MPC"}:
            raise DiagnosticPolicyError("unknown Q-free arm")
        self.arm = arm
        self.decision_records: list[dict[str, object]] = []
        self.q_head_accesses = 0

    def select_actions(self, step_env: Any, observation: Any, _rng: np.random.Generator) -> np.ndarray:
        before = c3s_policy._structural_sha256(step_env)
        started = time.perf_counter()
        if self.arm in {"HEUR", "HEUR_C3S_LITE"}:
            reference = nominal_local_snr_actions(step_env, observation)
        else:
            reference = current_association_actions(step_env, observation)
        profile_id = "BASE"
        nominal: Mapping[str, object] | None = None
        counts = {"base": 1, "unilateral": 0, "joint": 0}
        catalog_size = 1
        unique = 0
        if self.arm != "HEUR":
            snapshot, evaluator = _detached_snapshot(
                step_env, observation, reference=reference,
            )
            timing: dict[str, float] = {}
            catalog = (
                heuristic_lite_catalog(snapshot, evaluator, timing_out=timing)
                if self.arm == "HEUR_C3S_LITE"
                else c3s_policy.build_s0_catalog(
                    snapshot=snapshot, evaluator=evaluator, timing_out=timing,
                )
            )
            selected = c3s_policy.select_candidate(catalog, eta_ref=snapshot.eta_ref)
            actions = np.asarray(selected["actions"], dtype=np.int64)
            profile_id = str(selected["profile_id"])
            nominal = selected["nominal"]  # type: ignore[assignment]
            catalog_size = len(catalog)
            counts = {
                kind: sum(row.get("kind") == kind for row in catalog)
                for kind in ("base", "unilateral", "joint")
            }
            unique = int(timing["unique_nominal_evaluations"])
        else:
            actions = reference
        if c3s_policy._structural_sha256(step_env) != before:
            raise DiagnosticPolicyError("Q-free selector mutated live state")
        self.decision_records.append({
            "decision_index": len(self.decision_records), "arm": self.arm,
            "q_head_accesses": 0, "selected_profile_id": profile_id,
            "action_changed": not np.array_equal(actions, reference),
            "catalog_size": catalog_size, "unique_nominal_evaluations": unique,
            "profile_counts": counts, "selected_nominal": None if nominal is None else {
                "total_bits_hex": float(nominal["total_bits"]).hex(),
                "total_energy_j_hex": float(nominal["total_energy_j"]).hex(),
                "served": int(nominal["served"]),
                "opportunities": int(nominal["opportunities"]),
            },
            "wall_seconds_hex": (time.perf_counter() - started).hex(),
            "information_rule": "NO_Q_HEADS_NO_LEARNED_PROPOSALS",
            "reference_role": (
                "NOMINAL_LOCAL_SNR_HEURISTIC"
                if self.arm in {"HEUR", "HEUR_C3S_LITE"}
                else "CURRENT_ASSOCIATION_WITH_CANONICAL_MASK_COMPLETION"
            ),
        })
        return actions.astype(np.int64, copy=True)


__all__ = [
    "ChurnSelector", "DiagnosticPolicyError", "FORCED_RENEW_AGE", "QFreeSelector",
    "RANDOM_RENEW_K", "derive_seed", "heuristic_lite_catalog",
    "learned_decision", "nominal_local_snr_actions", "random_feasible_candidate",
    "restricted_catalog", "segment_ages_before_decision", "shuffled_score_candidate",
]
