#!/usr/bin/env python3
"""Instrumented FULL2/selected-C3-S adapter for the confirmatory ladder.

The coordinator path is assembled from the frozen matrix hook implementation.
This file adds confirmatory recording and cached eta rescoring; it does not
reproduce individual variant levers.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import math
from pathlib import Path
import resource
import sys
import time
from typing import Any, Mapping

import numpy as np


HERE = Path(__file__).resolve().parent  # Provenance: confirmatory package location.
REPO = HERE.parents[1]  # Provenance: workspace package layout.
SCREEN_DIR = REPO / ".scratch" / "multi-catfish-v023-c3s-screen"  # Provenance: sealed v1 coordinator source.
VARIANT_DIR = REPO / ".scratch" / "multi-catfish-v023-c3s-variants"  # Provenance: sealed matrix hooks.
STAGEC_PHYSICAL_DIR = REPO / ".scratch" / "multi-catfish-v023-c1c2-successor-physical-evaluation"  # Provenance: FULL2 loader.
PHYSICAL_DIR = REPO / ".scratch" / "multi-catfish-v023-physical"  # Provenance: v1 nominal evaluator.
SOURCE_RUNNER_DIR = REPO / ".scratch" / "multi-catfish-v023-two-route-source-training-runner"  # Provenance: FULL2 producer imports.
for _path in (SCREEN_DIR, VARIANT_DIR, STAGEC_PHYSICAL_DIR, PHYSICAL_DIR, SOURCE_RUNNER_DIR, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# Direct imports deliberately avoid sys.modules aliases (task constraint).
import c3s_policy  # noqa: E402
import variant_policy  # noqa: E402
import v023_c1c2_successor_physical_runner as _stagec_physical  # noqa: E402
import v023_physical_episode_runner as _nominal_physical  # noqa: E402


ARMS = ("FULL2", "FULL2+C3-S")  # Provenance: astra C exact two-arm estimand.
COORDINATOR_CONFIGURATIONS = (*variant_policy.VARIANT_ARMS, "FULL")  # Provenance: sealed matrix plus v1 full catalog.
USERS = 100  # Provenance: astra C exact estimand.
STEPS = 30  # Provenance: astra A0/C canonical horizon amendment.
INTERVAL_SECONDS = 30.08  # Provenance: sealed screen contract section 4.
ETA_MULTIPLIERS = (Fraction(4, 5), Fraction(1), Fraction(6, 5))  # Provenance: astra C eta sensitivity.
ETA_SENSITIVITY_DECISIONS = 100 * STEPS  # Provenance: first 100-world rung at T=30.


class C3SFull2AdapterError(RuntimeError):
    """A frozen-policy, snapshot, or episode integrity check failed."""


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise C3SFull2AdapterError(f"required regular file is absent or symlinked: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_full2_export(path: str | Path, expected_sha256: str) -> Any:
    """Authenticate and load the producer's attempt-3 epoch-100 FULL2 export."""

    return _stagec_physical.load_learned_two_route_checkpoint(
        path, arm="FULL2", expected_sha256=expected_sha256, training_provenance=None,
    )


def _array_digest(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(array.shape).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _nominal_payload(value: Mapping[str, object]) -> dict[str, object]:
    metric = c3s_policy._metric(value, label="confirmatory nominal")
    return {
        "total_bits_hex": float(metric["total_bits"]).hex(),
        "total_energy_j_hex": float(metric["total_energy_j"]).hex(),
        "served": int(metric["served"]),
        "opportunities": int(metric["opportunities"]),
    }


def _physical_actions(snapshot: Any, actions: np.ndarray) -> list[list[int] | None]:
    keys = np.asarray(snapshot.slot_physical_keys)
    values: list[list[int] | None] = []
    for user, action in enumerate(actions.tolist()):
        values.append(None if action < 0 else [int(keys[user, action, 0]), int(keys[user, action, 1])])
    return values


class C3SFull2PolicyAdapter:
    """Stage-C-shaped fixed policy using the complete matrix configuration hooks."""

    def __init__(
        self, *, frozen_full2: Any, coordinator_enabled: bool,
        configuration: str = "LITE",
        decision_offset: int = 0,
        eta_config: str | Path = SCREEN_DIR / "c3s_config.json",
        nominal_physical: Any = _nominal_physical,
    ) -> None:
        if type(coordinator_enabled) is not bool:
            raise C3SFull2AdapterError("coordinator_enabled must be Boolean")
        if configuration not in COORDINATOR_CONFIGURATIONS:
            raise C3SFull2AdapterError("configuration is not a frozen matrix/v1 coordinator id")
        if getattr(frozen_full2, "arm", None) != "FULL2":
            raise C3SFull2AdapterError("adapter requires the authenticated FULL2 export")
        verify = getattr(frozen_full2, "verify", None)
        if not callable(verify):
            raise C3SFull2AdapterError("FULL2 export lacks its verifier")
        verify()
        self.frozen_full2 = frozen_full2
        self.coordinator_enabled = coordinator_enabled
        self.configuration = configuration
        self.arm = ARMS[1] if coordinator_enabled else ARMS[0]
        self.eta_config = Path(eta_config)
        self.eta_ref = c3s_policy.load_eta_ref(self.eta_config)
        self.physical = nominal_physical
        if type(decision_offset) is not int or decision_offset < 0:
            raise C3SFull2AdapterError("decision_offset must be a nonnegative integer")
        self.decision_offset = decision_offset
        variant_arm = "LITE" if configuration == "FULL" else configuration
        self._variant = variant_policy.VariantPolicyAdapter(
            physical=nominal_physical, frozen=frozen_full2, arm=variant_arm,
            eta_ref=self.eta_ref, constants_path=VARIANT_DIR / "variants_config.json",
        )
        self._variant.catalog = "full" if configuration == "FULL" else "lite"
        self.decision_records: list[dict[str, object]] = []
        self._pending_sensitivity: tuple[tuple[dict[str, object], ...], Any, str, Any, dict[str, object]] | None = None

    def verify(self) -> None:
        self.frozen_full2.verify()
        if self.eta_ref != c3s_policy.load_eta_ref(self.eta_config):
            raise C3SFull2AdapterError("eta_ref drifted")
        if self.configuration not in COORDINATOR_CONFIGURATIONS:
            raise C3SFull2AdapterError("coordinator configuration drifted")
        variant_policy.load_constants(VARIANT_DIR / "variants_config.json")

    def start_episode(self) -> None:
        """Reset the variant's within-episode state for one fresh world."""

        if self._pending_sensitivity is not None:
            raise C3SFull2AdapterError("previous decision's non-decisional diagnostic is incomplete")
        self._variant.blocked_through.clear()
        self._variant.decision_index = 0

    def binding(self) -> dict[str, object]:
        self.verify()
        source = self.frozen_full2.binding()
        return {
            "arm": self.arm,
            "policy_family": "C1C2_SUCCESSOR_FULL2_WITH_OPTIONAL_FROZEN_C3S_CONFIGURATION",
            "full2_export_path": source["checkpoint_path"],
            "full2_export_sha256": source["checkpoint_sha256"],
            "q1_parameter_sha256": source["q1_parameter_sha256"],
            "q2_parameter_sha256": source["q2_parameter_sha256"],
            "update_count": source["update_count"], "routes": source["routes"],
            "coordinator_enabled": self.coordinator_enabled,
            "configuration": self.configuration,
            "eta_ref": c3s_policy.fraction_payload(self.eta_ref),
            "coordinator_code": {"path": str((SCREEN_DIR / "c3s_policy.py").resolve()), "sha256": file_sha256(SCREEN_DIR / "c3s_policy.py")},
            "variant_hooks": {"path": str((VARIANT_DIR / "variant_policy.py").resolve()), "sha256": file_sha256(VARIANT_DIR / "variant_policy.py")},
            "variant_config": {"path": str((VARIANT_DIR / "variants_config.json").resolve()), "sha256": file_sha256(VARIANT_DIR / "variants_config.json")},
            "proposal_rule": "FLOAT32_UNWEIGHTED_MASKED_Q1_PLUS_Q2_LOWEST_SLOT_TIE_NOOP_ON_EMPTY",
            "fixed_policy": True,
        }

    def _catalog(self, snapshot: Any, evaluator: Any, context: Any, phases: dict[str, float]) -> tuple[dict[str, object], ...]:
        if not self.coordinator_enabled:
            return variant_policy._base_only_catalog(snapshot, evaluator, phases)
        cadence_off = self.configuration == "V-C" and context.step_index % self._variant.cadence_steps != self._variant.cadence_residue
        base_catalog = (
            variant_policy._base_only_catalog(snapshot, evaluator, phases)
            if cadence_off else c3s_policy.build_s0_catalog(snapshot=snapshot, evaluator=evaluator, timing_out=phases)
        )
        return base_catalog if self.configuration == "FULL" else self._variant.hooks.catalog_builder(base_catalog, snapshot, self._variant)

    def _select(self, catalog: tuple[dict[str, object], ...], context: Any) -> tuple[Mapping[str, object], Mapping[str, object]]:
        if self.configuration == "FULL":
            return c3s_policy.select_candidate(catalog, eta_ref=self._variant.eta_ref), catalog[0]
        selected, base, _scores = variant_policy.select_with_hooks(catalog, context=context, adapter=self._variant)
        return selected, base

    def _sensitivity(self, catalog: tuple[dict[str, object], ...], context: Any, primary_profile_id: str) -> list[dict[str, object]]:
        if self.decision_offset + len(self.decision_records) > ETA_SENSITIVITY_DECISIONS or not self.coordinator_enabled:
            return []
        original_eta = self._variant.eta_ref
        original_blocks = dict(self._variant.blocked_through)
        rows: list[dict[str, object]] = []
        try:
            for multiplier in ETA_MULTIPLIERS:
                self._variant.eta_ref = original_eta * multiplier
                self._variant.blocked_through = dict(original_blocks)
                selected, _base = self._select(catalog, context)
                score = (
                    c3s_policy.nominal_score(selected["nominal"], self._variant.eta_ref)  # type: ignore[arg-type]
                    if self.configuration == "FULL"
                    else self._variant.hooks.objective(selected, context, self._variant)
                )
                rows.append({
                    "eta_multiplier": c3s_policy.fraction_payload(multiplier),
                    "eta_ref": c3s_policy.fraction_payload(self._variant.eta_ref),
                    "selected_profile_id": str(selected["profile_id"]),
                    "choice_agrees_with_primary": str(selected["profile_id"]) == primary_profile_id,
                    "nominal": _nominal_payload(selected["nominal"]),  # type: ignore[arg-type]
                    "score": c3s_policy.fraction_payload(score),
                })
        finally:
            self._variant.eta_ref = original_eta
            self._variant.blocked_through = original_blocks
        return rows

    def complete_nondecisional_diagnostics(self) -> None:
        """Run cached eta rescoring outside the full decision-wall timer."""

        pending = self._pending_sensitivity
        if pending is None:
            return
        catalog, context, profile_id, diagnostic_hooks, record = pending
        self._pending_sensitivity = None
        original_hooks = self._variant.hooks
        started = time.perf_counter()
        try:
            self._variant.hooks = diagnostic_hooks
            record["eta_sensitivity"] = self._sensitivity(catalog, context, profile_id)
        finally:
            self._variant.hooks = original_hooks
        phases = record["phase_wall_seconds_hex"]
        assert isinstance(phases, dict)
        phases["eta_sensitivity_rescoring"] = (time.perf_counter() - started).hex()

    def select_actions(self, step_environment: Any, observation: Any, rng: np.random.Generator) -> np.ndarray:
        """Select once and retain complete frozen-hook decision diagnostics."""

        self.verify()
        if self._pending_sensitivity is not None:
            raise C3SFull2AdapterError("non-decisional diagnostic must complete before the next decision")
        if not isinstance(rng, np.random.Generator):
            raise C3SFull2AdapterError("policy RNG must be a NumPy Generator")
        before = c3s_policy._live_neutrality_fingerprint(step_environment, rng)
        started = time.perf_counter()
        snapshot, evaluator = c3s_policy._snapshot_inputs(self._variant, step_environment, observation)
        context = (
            self._variant._context(step_environment, observation, snapshot)
            if self.coordinator_enabled
            else variant_policy.DecisionContext(step_index=int(observation.step_index))
        )
        phases: dict[str, float] = {"q_inference": float(snapshot.q_inference_seconds)}
        catalog_started = time.perf_counter()
        catalog = self._catalog(snapshot, evaluator, context, phases)
        phases["catalog_total"] = time.perf_counter() - catalog_started
        unique = int(phases.pop("unique_nominal_evaluations"))
        selection_started = time.perf_counter()
        original_hooks = self._variant.hooks
        if self.coordinator_enabled and self.configuration == "V-L2":
            # Cache the one projected BASE interval once per candidate. Both
            # primary selection and 4/5,1,6/5 repricing use these same metrics.
            future_by_profile = {
                str(row["profile_id"]): variant_policy._future_base_metric(row, context, self._variant)
                for row in catalog
            }

            def cached_lookahead(row: Mapping[str, object], _context: Any, variant: Any) -> Fraction:
                future = future_by_profile[str(row["profile_id"])]
                if future is None:
                    return c3s_policy.nominal_score(row["nominal"], variant.eta_ref)  # type: ignore[arg-type]
                return variant_policy.lookahead_objective(row["nominal"], future, eta_ref=variant.eta_ref)  # type: ignore[arg-type]

            self._variant.hooks = replace(original_hooks, objective=cached_lookahead)
        try:
            if self.coordinator_enabled:
                selected, base = self._select(catalog, context)
                phases["primary_selection"] = time.perf_counter() - selection_started
                sensitivity: list[dict[str, object]] = []
                diagnostic_hooks = self._variant.hooks
            else:
                base = catalog[0]
                selected, sensitivity = base, []
                phases["primary_selection"] = time.perf_counter() - selection_started
                diagnostic_hooks = self._variant.hooks
        finally:
            self._variant.hooks = original_hooks
        if c3s_policy._live_neutrality_fingerprint(step_environment, rng) != before:
            raise C3SFull2AdapterError("coordinator changed live environment/RNG/tracking state")
        actions = np.asarray(selected["actions"], dtype=np.int64)
        proposal = np.asarray(base["actions"], dtype=np.int64)
        counts = {kind: sum(row["kind"] == kind for row in catalog) for kind in ("base", "unilateral", "joint")}
        cadence_active = not (
            self.coordinator_enabled and self.configuration == "V-C"
            and context.step_index % self._variant.cadence_steps != self._variant.cadence_residue
        )
        record = {
            "decision_index": len(self.decision_records), "step_index": int(context.step_index),
            "arm": self.arm, "coordinator_configuration": self.configuration,
            "pre_decision_state_sha256": before,
            "full2_proposal": proposal.tolist(), "full2_proposal_sha256": _array_digest(proposal),
            "full2_proposal_physical_associations": _physical_actions(snapshot, proposal),
            "committed_profile_id": str(selected["profile_id"]),
            "committed_actions": actions.tolist(), "committed_actions_sha256": _array_digest(actions),
            "committed_physical_associations": _physical_actions(snapshot, actions),
            "selected_nominal": _nominal_payload(selected["nominal"]),  # type: ignore[arg-type]
            "full2_proposal_nominal": _nominal_payload(base["nominal"]),  # type: ignore[arg-type]
            "catalog_size": len(catalog), "unique_nominal_evaluations": unique,
            "profile_counts": counts, "coordinator_active_step": cadence_active,
            "full_decision_wall_seconds_hex": (0.0).hex(),
            "phase_wall_seconds_hex": {name: float(value).hex() for name, value in phases.items()},
            "eta_sensitivity": sensitivity,
            "policy_state_after": {"decision_index": self._variant.decision_index + 1, "blocked_through": {str(key): value for key, value in sorted(self._variant.blocked_through.items())}},
            "process_lifetime_peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        }
        self.decision_records.append(record)
        self._variant.decision_index += 1
        record["full_decision_wall_seconds_hex"] = (time.perf_counter() - started).hex()
        if self.coordinator_enabled and self.decision_offset + len(self.decision_records) <= ETA_SENSITIVITY_DECISIONS:
            self._pending_sensitivity = (catalog, context, str(selected["profile_id"]), diagnostic_hooks, record)
        return actions.copy()


@dataclass(frozen=True)
class EpisodeExecution:
    arm: str
    total_bits: float
    total_energy_j: float
    served_user_steps: int
    service_opportunities: int
    action_trace_sha256: str
    initial_state_sha256: str
    decision_records: tuple[Mapping[str, object], ...]


class FixedPolicyEpisodeAdapter:
    """Run one canonical 30-decision episode and enrich archived decisions."""

    def __init__(self, policy: C3SFull2PolicyAdapter, *, users: int = USERS, steps: int = STEPS) -> None:
        if users != USERS or steps != STEPS:
            raise C3SFull2AdapterError("confirmatory episodes require 100 users and 30 steps")
        policy.verify()
        self.policy, self.users, self.steps = policy, users, steps

    def run_episode(self, environment: Any, *, environment_rng: np.random.Generator, mobility_rng: np.random.Generator) -> EpisodeExecution:
        if not isinstance(environment_rng, np.random.Generator) or not isinstance(mobility_rng, np.random.Generator):
            raise C3SFull2AdapterError("episode RNGs must be NumPy Generators")
        self.policy.start_episode()
        states, masks, observation = environment.reset(environment_rng, mobility_rng)
        del states
        from mcrl.runtime.ee_axis_state import encode_ee_axis_state

        step_environment = getattr(environment, "environment", environment)
        native = encode_ee_axis_state(step_environment, observation)
        native.verify()
        initial_state = hashlib.sha256((_array_digest(native.state_matrix) + _array_digest(native.action_masks)).encode("ascii")).hexdigest()
        trace = hashlib.sha256()
        bits: list[float] = []
        energy: list[float] = []
        served = 0
        first_record = len(self.policy.decision_records)
        for step_index in range(self.steps):
            actions = np.asarray(self.policy.select_actions(step_environment, observation, environment_rng))
            mask_values = np.stack([np.asarray(mask.mask, dtype=np.bool_) for mask in masks])
            if actions.shape != (self.users,) or actions.dtype.kind not in "iu":
                raise C3SFull2AdapterError("policy did not return a complete integer action vector")
            rows = np.arange(self.users)
            empty = ~np.any(mask_values, axis=1)
            slot_actions = actions >= 0
            invalid_slot = slot_actions & (
                (actions >= mask_values.shape[1])
                | ~mask_values[rows, np.clip(actions, 0, mask_values.shape[1] - 1)]
            )
            if np.any(actions < -1) or np.any((actions == -1) != empty) or np.any(invalid_slot):
                raise C3SFull2AdapterError("policy returned an illegal action")
            trace.update(actions.astype(np.int64, copy=False).tobytes(order="C"))
            result = environment.step(actions, environment_rng)
            outcome = environment.last_outcome
            rate = np.asarray(outcome.link_rate_bps, dtype=np.float64)
            power = float(outcome.system_power_w)
            interval = float(step_environment.driver.config.ephemeris.time_step_s)
            step_bits, step_energy = interval * float(np.sum(rate, dtype=np.float64)), interval * power
            if not math.isfinite(step_bits) or step_bits < 0 or not math.isfinite(step_energy) or step_energy <= 0:
                raise C3SFull2AdapterError("committed endpoint is non-finite or outside its domain")
            bits.append(step_bits); energy.append(step_energy)
            resolution = getattr(outcome, "resolution", None)
            served_mask = np.asarray(getattr(resolution, "served", rate > 0), dtype=np.bool_)
            realised_served = int(np.count_nonzero(served_mask)); served += realised_served
            serving_satellite = np.asarray(getattr(resolution, "serving_satellite", np.full(self.users, -1)), dtype=np.int64)
            serving_cell = np.asarray(getattr(resolution, "serving_cell", np.full(self.users, -1)), dtype=np.int64)
            realised_associations = [
                None if not served_mask[user] else [int(serving_satellite[user]), int(serving_cell[user])]
                for user in range(self.users)
            ]
            self.policy.decision_records[first_record + step_index]["realised"] = {
                "total_bits_hex": step_bits.hex(), "total_energy_j_hex": step_energy.hex(),
                "served": realised_served, "opportunities": self.users,
                "physical_associations": realised_associations,
                "handover_classes": [str(getattr(value, "value", value)) for value in getattr(outcome, "handovers", ())],
            }
            self.policy.complete_nondecisional_diagnostics()
            done = bool(getattr(outcome, "done", getattr(result, "done", False)))
            if done != (step_index == self.steps - 1):
                raise C3SFull2AdapterError("environment termination differs from 30 committed steps")
            masks, observation = list(result.action_masks), outcome.observation
        self.policy.verify()
        self.policy.complete_nondecisional_diagnostics()
        records = tuple(self.policy.decision_records[first_record:])
        if len(records) != STEPS:
            raise C3SFull2AdapterError("episode decision-record coverage is not 30")
        return EpisodeExecution(
            arm=self.policy.arm, total_bits=math.fsum(bits), total_energy_j=math.fsum(energy),
            served_user_steps=served, service_opportunities=self.users * self.steps,
            action_trace_sha256=trace.hexdigest(), initial_state_sha256=initial_state,
            decision_records=records,
        )


__all__ = [
    "ARMS", "COORDINATOR_CONFIGURATIONS", "STEPS", "USERS", "C3SFull2AdapterError",
    "C3SFull2PolicyAdapter", "EpisodeExecution", "FixedPolicyEpisodeAdapter", "load_full2_export",
]
