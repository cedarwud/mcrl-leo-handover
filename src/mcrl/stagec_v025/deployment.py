"""Deployable two-head selector, set coordinator seam, and S_UNI comparator."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import math
import multiprocessing
import time
from typing import Callable, Literal, Mapping, Protocol, Sequence

from .canonical import StageCContractError, canonical_sha256
from .coalitions import CoalitionContext
from .experiments import CheckpointKnockoutExperiment
from .interfaces import CoordinatorInformation, ArmInformationInterface, authenticate_matched_catalogues
from .learner import ARM_ORDER, Route, ThreeRouteModel, V1ThreeRouteModel
from .state import PhysicalAction


DEPLOYMENT_DEADLINE_S = 10.0
Profile = tuple[int, ...]


@dataclass(frozen=True, slots=True)
class UserActionTable:
    user_id: int
    actions: tuple[PhysicalAction, ...]
    action_mask: tuple[bool, ...]
    q1_states: tuple[tuple[float, ...], ...]
    q2_states: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        size = len(self.actions)
        if size < 1 or len(self.action_mask) != size or len(self.q1_states) != size or len(self.q2_states) != size:
            raise StageCContractError("user action table arrays must have one common nonzero length")
        if not any(
            enabled and action.is_null
            for action, enabled in zip(self.actions, self.action_mask, strict=True)
        ):
            raise StageCContractError("user table must include an explicit legal null action")


@dataclass(frozen=True, slots=True)
class ResolvedProfile:
    profile: Profile
    served_count: int
    bits: float = 0.0
    joules: float = 0.0


@dataclass(frozen=True, slots=True)
class DeploymentDecision:
    profile: Profile
    independent_profile: Profile
    used_fallback: bool
    fallback_reason: str | None
    elapsed_s: float
    jointly_legal: bool
    service_guard_passed: bool


SelectorMode = Literal["S3", "S0", "S_UNI"]


@dataclass(frozen=True, slots=True)
class SelectorDecision:
    mode: SelectorMode
    profile: Profile
    score: float
    used_fallback: bool
    fallback_reason: str | None
    local_optimum_certified: bool | None
    evaluated_profiles: int
    elapsed_s: float = 0.0
    worker_pid: int | None = None
    worker_terminated: bool = False


class CoordinatorHook(Protocol):
    def __call__(
        self,
        *,
        profile: Profile,
        tables: Sequence[UserActionTable],
        model: ThreeRouteModel,
    ) -> float: ...


def learned_c3_score(
    *, profile: Profile, tables: Sequence[UserActionTable], model: ThreeRouteModel
) -> float:
    total = 0.0
    for table, action_index in zip(tables, profile, strict=True):
        total += model.score(
            "C3",
            (*table.q1_states[action_index], *table.q2_states[action_index]),
        )
    return total


def masked_argmax(values: Sequence[float], mask: Sequence[bool]) -> int:
    if len(values) != len(mask) or not values:
        raise StageCContractError("masked argmax shape mismatch")
    legal = [index for index, enabled in enumerate(mask) if enabled]
    if not legal:
        raise StageCContractError("masked argmax has no legal action")
    # Lowest stable action index wins ties. BASE tie preference is applied at
    # profile coordination, where BASE need not be action index zero.
    return max(legal, key=lambda index: (float(values[index]), -index))


def independent_two_head_profile(
    model: ThreeRouteModel, tables: Sequence[UserActionTable]
) -> Profile:
    selected: list[int] = []
    for table in tables:
        scores = [
            model.score("C1", q1) + model.score("C2", q2)
            for q1, q2 in zip(table.q1_states, table.q2_states, strict=True)
        ]
        selected.append(masked_argmax(scores, table.action_mask))
    return tuple(selected)


def construct_reference_proposal(
    *,
    model: ThreeRouteModel,
    tables: Sequence[UserActionTable],
    catalogue: Sequence[Profile],
    jointly_legal: Callable[[Profile], bool],
) -> Profile:
    """Build A3's Q1+Q2 proposal and deterministically repair joint conflicts."""

    independent = independent_two_head_profile(model, tables)
    if jointly_legal(independent):
        return independent
    best: Profile | None = None
    best_score = float("-inf")
    for profile in catalogue:
        if len(profile) != len(tables) or not jointly_legal(profile):
            continue
        score = DeploymentAdapter._profile_q12(model, tables, profile)
        if score > best_score:
            best, best_score = profile, score
    if best is None:
        raise StageCContractError("joint conflict repair found no legal complete profile")
    return best


def deployment_capability_manifest(
    *,
    code_digest: str,
    physics_digest: str,
    catalogue_digest: str,
    telemetry_sources_and_ages: Mapping[str, str] | None = None,
    roster_and_cross_gain_coverage: str = "synthetic_complete_roster_and_beam_specific_cross_gains",
    model_assumptions: Sequence[str] = ("nominal_no_realised_fading",),
    calibration_source: str = "synthetic_fixture_only",
    worker_hardware: str = "sat",
    worker_count: int = 4,
    catalogue_bounds: Mapping[str, int] | None = None,
    solver_limits: Mapping[str, object] | None = None,
    memory_limit_bytes: int = 1_073_741_824,
    missing_data_handling: str = "reject_and_execute_prevalidated_base",
    measured_end_to_end_latency_s: Sequence[float],
) -> dict[str, object]:
    for name, digest in (
        ("code_digest", code_digest),
        ("physics_digest", physics_digest),
        ("catalogue_digest", catalogue_digest),
    ):
        if not isinstance(digest, str) or len(digest) != 64 or any(
            char not in "0123456789abcdef" for char in digest
        ):
            raise StageCContractError(f"{name} must be a lowercase SHA-256")
    if worker_count < 1 or memory_limit_bytes < 1:
        raise StageCContractError("capability worker and memory limits must be positive")
    latency = tuple(float(value) for value in measured_end_to_end_latency_s)
    if not latency or any(not math.isfinite(value) or value < 0.0 for value in latency):
        raise StageCContractError("capability requires nonempty nonnegative latency observations")
    payload: dict[str, object] = {
        "schema": "mcrl-v025-stagec-deployment-capability-v1",
        "code_digest": code_digest,
        "physics_digest": physics_digest,
        "catalogue_digest": catalogue_digest,
        "coordinator_compute_budget_wall_s": DEPLOYMENT_DEADLINE_S,
        "decision_interval_s": 30.08,
        "reserved_interval_use": "sensing_transport_validation_and_atomic_commit",
        "inputs": [
            "all_users_current_geometry",
            "per_user_legal_physical_actions",
            "previous_committed_physical_profile",
            "beam_specific_cross_gains",
            "nominal_forecasts",
            "sealed_calibration",
        ],
        "capabilities": [
            "construct_complete_simultaneous_profiles",
            "resolve_joint_nominal_physics",
            "evaluate_sealed_bounded_catalogue",
            "validate_joint_legality",
            "enforce_no_served_count_decrease_vs_base",
            "atomically_commit_or_base_fallback",
        ],
        "timer_enforcement": "runner_process_deadline_kill_join",
        "base_first": "computed_validated_and_repaired_before_coordinator_timer",
        "deadline_fallback": "execute_prevalidated_a0",
        "telemetry_sources_and_ages": dict(
            telemetry_sources_and_ages
            or {"synthetic_fixture": "age_0_at_declared_decision_time"}
        ),
        "roster_and_cross_gain_coverage": roster_and_cross_gain_coverage,
        "model_assumptions": list(model_assumptions),
        "calibration_source": calibration_source,
        "worker_hardware": worker_hardware,
        "worker_count": worker_count,
        "cache_policy": "cold_per_anchor_no_warm_cache",
        "catalogue_bounds": dict(catalogue_bounds or {"profiles": 64, "coalition_size": 4}),
        "solver_limits": dict(solver_limits or {"wall_s": DEPLOYMENT_DEADLINE_S}),
        "memory_limit_bytes": memory_limit_bytes,
        "missing_data_handling": missing_data_handling,
        "measured_end_to_end_latency_distribution_s": {
            "samples": list(latency),
            "count": len(latency),
            "p50": None if not latency else float(sorted(latency)[len(latency) // 2]),
            "max": None if not latency else max(latency),
        },
    }
    payload["manifest_sha256"] = canonical_sha256(payload)
    return payload


class DeploymentAdapter:
    def __init__(self, *, deadline_s: float = DEPLOYMENT_DEADLINE_S) -> None:
        if deadline_s <= 0.0:
            raise StageCContractError("deployment deadline must be positive")
        self.deadline_s = float(deadline_s)

    def select(
        self,
        *,
        model: ThreeRouteModel,
        tables: Sequence[UserActionTable],
        base_profile: Profile,
        catalogue: Sequence[Profile],
        jointly_legal: Callable[[Profile], bool],
        resolve_profile: Callable[[Profile], ResolvedProfile],
        coordinator: CoordinatorHook = learned_c3_score,
        clock: Callable[[], float] = time.monotonic,
        _started_at: float | None = None,
    ) -> DeploymentDecision:
        started = clock() if _started_at is None else _started_at
        if len(base_profile) != len(tables) or not jointly_legal(base_profile):
            raise StageCContractError("BASE must be a complete jointly legal profile")
        independent = base_profile

        def fallback(reason: str) -> DeploymentDecision:
            return DeploymentDecision(
                base_profile,
                independent,
                True,
                reason,
                max(0.0, clock() - started),
                True,
                True,
            )

        def deadline_expired() -> bool:
            return clock() - started > self.deadline_s

        try:
            independent = independent_two_head_profile(model, tables)
            if deadline_expired():
                return fallback("deadline")
            independent_legal = jointly_legal(independent)
            base_resolution = resolve_profile(base_profile)
            if (
                base_resolution.profile != base_profile
                or base_resolution.served_count < 0
            ):
                return fallback("base_resolution_validation")
            if deadline_expired():
                return fallback("deadline")
            best = base_profile
            best_score = self._profile_q12(model, tables, base_profile) + coordinator(
                profile=base_profile, tables=tables, model=model
            )
            if deadline_expired():
                return fallback("deadline")
            fallback_reason: str | None = (
                None
                if independent_legal
                else "independent_profile_jointly_infeasible"
            )
            # BASE is first and strict improvement is required, so BASE wins ties.
            ordered = [base_profile, *catalogue]
            if independent not in ordered:
                ordered.append(independent)
            seen: set[Profile] = set()
            for profile in ordered:
                if profile in seen:
                    continue
                seen.add(profile)
                if deadline_expired():
                    return fallback("deadline")
                if len(profile) != len(tables) or not jointly_legal(profile):
                    continue
                resolved = resolve_profile(profile)
                if deadline_expired():
                    return fallback("deadline")
                if resolved.profile != profile:
                    return fallback("profile_resolution_validation")
                if resolved.served_count < base_resolution.served_count:
                    continue
                score = self._profile_q12(model, tables, profile) + coordinator(
                    profile=profile, tables=tables, model=model
                )
                if deadline_expired():
                    return fallback("deadline")
                if score > best_score:
                    best, best_score = profile, score
            legal = jointly_legal(best)
            resolved_best = resolve_profile(best)
            if deadline_expired():
                return fallback("deadline")
            guard = (
                resolved_best.profile == best
                and resolved_best.served_count >= base_resolution.served_count
            )
            if not legal or not guard:
                return fallback("post_selection_validation")
            elapsed = max(0.0, clock() - started)
            if elapsed > self.deadline_s:
                return fallback("deadline")
            used_fallback = best == base_profile and fallback_reason is not None
            return DeploymentDecision(
                best,
                independent,
                used_fallback,
                fallback_reason if used_fallback else None,
                elapsed,
                legal,
                guard,
            )
        except Exception as error:
            return fallback(f"validation_failure:{type(error).__name__}")

    def select_runner_timed(
        self,
        *,
        model: ThreeRouteModel,
        tables: Sequence[UserActionTable],
        base_profile: Profile,
        catalogue: Sequence[Profile],
        jointly_legal: Callable[[Profile], bool],
        resolve_profile: Callable[[Profile], ResolvedProfile],
        coordinator: CoordinatorHook = learned_c3_score,
        clock: Callable[[], float] = time.monotonic,
    ) -> DeploymentDecision:
        """F2 runner-enforced wall timer with prevalidated BASE-first fallback."""

        if len(base_profile) != len(tables) or not jointly_legal(base_profile):
            raise StageCContractError("BASE must be jointly legal before coordinator start")
        base_resolution = resolve_profile(base_profile)
        if base_resolution.profile != base_profile or base_resolution.served_count < 0:
            raise StageCContractError("BASE must be validated/repaired before coordinator start")
        started = clock()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stagec-coordinator")
        future = executor.submit(
            self.select,
            model=model,
            tables=tables,
            base_profile=base_profile,
            catalogue=catalogue,
            jointly_legal=jointly_legal,
            resolve_profile=resolve_profile,
            coordinator=coordinator,
            clock=clock,
            _started_at=started,
        )
        try:
            return future.result(timeout=self.deadline_s)
        except FutureTimeoutError:
            future.cancel()
            return DeploymentDecision(
                profile=base_profile,
                independent_profile=base_profile,
                used_fallback=True,
                fallback_reason="runner_deadline_cancel",
                elapsed_s=max(0.0, clock() - started),
                jointly_legal=True,
                service_guard_passed=True,
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def select_with_preparation(
        self,
        *,
        model: ThreeRouteModel,
        prepare: Callable[[], tuple[Sequence[UserActionTable], Sequence[Profile]]],
        base_profile: Profile,
        jointly_legal: Callable[[Profile], bool],
        resolve_profile: Callable[[Profile], ResolvedProfile],
        coordinator: CoordinatorHook = learned_c3_score,
        clock: Callable[[], float] = time.monotonic,
    ) -> DeploymentDecision:
        """Runner-time preparation, catalogue search, and validation as one task."""

        if not jointly_legal(base_profile):
            raise StageCContractError("BASE must be a jointly legal profile")
        base_resolution = resolve_profile(base_profile)
        if base_resolution.profile != base_profile or base_resolution.served_count < 0:
            raise StageCContractError("BASE must be validated/repaired before coordinator start")
        started = clock()

        def run() -> DeploymentDecision:
            tables, catalogue = prepare()
            return self.select(
                model=model,
                tables=tables,
                base_profile=base_profile,
                catalogue=catalogue,
                jointly_legal=jointly_legal,
                resolve_profile=resolve_profile,
                coordinator=coordinator,
                clock=clock,
                _started_at=started,
            )

        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stagec-coordinator")
        future = executor.submit(run)
        try:
            return future.result(timeout=self.deadline_s)
        except FutureTimeoutError:
            future.cancel()
            return DeploymentDecision(
                base_profile,
                base_profile,
                True,
                "runner_deadline_cancel",
                max(0.0, clock() - started),
                True,
                True,
            )
        except Exception as error:
            return DeploymentDecision(
                base_profile,
                base_profile,
                True,
                f"prep_or_validation_failure:{type(error).__name__}",
                max(0.0, clock() - started),
                True,
                True,
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _profile_q12(
        model: ThreeRouteModel, tables: Sequence[UserActionTable], profile: Profile
    ) -> float:
        if len(profile) != len(tables):
            raise StageCContractError("profile is incomplete")
        total = 0.0
        for table, action_index in zip(tables, profile, strict=True):
            if not 0 <= action_index < len(table.actions) or not table.action_mask[action_index]:
                raise StageCContractError("profile contains a locally illegal action")
            total += model.score("C1", table.q1_states[action_index])
            total += model.score("C2", table.q2_states[action_index])
        return total


def select_s_uni(
    *,
    base_profile: Profile,
    tables: Sequence[UserActionTable],
    jointly_legal: Callable[[Profile], bool],
    exact_nominal_score: Callable[[Profile], float],
) -> Profile:
    """Iterated exact-unilateral deployable comparator with stable tie handling."""

    current = base_profile
    while True:
        current_score = exact_nominal_score(current)
        best = current
        best_score = current_score
        for user_index, table in enumerate(tables):
            for action_index, legal in enumerate(table.action_mask):
                if not legal or action_index == current[user_index]:
                    continue
                candidate = (*current[:user_index], action_index, *current[user_index + 1 :])
                if not jointly_legal(candidate):
                    continue
                score = exact_nominal_score(candidate)
                if score > best_score:
                    best, best_score = candidate, score
        if best == current:
            return current
        current = best


class ProfileSelector:
    """One C2 selector class implementing S3, S0, and S_UNI."""

    def __init__(self, mode: SelectorMode) -> None:
        if mode not in {"S3", "S0", "S_UNI"}:
            raise StageCContractError("unknown selector mode")
        self.mode = mode

    @staticmethod
    def repair_reference(
        *,
        model: V1ThreeRouteModel,
        tables: Sequence[UserActionTable],
        catalogue: Sequence[Profile],
        jointly_legal: Callable[[Profile], bool],
    ) -> Profile:
        """A3 production Q1+Q2 proposal with deterministic joint repair."""

        proposal = tuple(
            masked_argmax(
                tuple(
                    model.score("C1", q1) + model.score("C2", q2)
                    for q1, q2 in zip(table.q1_states, table.q2_states, strict=True)
                ),
                table.action_mask,
            )
            for table in tables
        )
        if jointly_legal(proposal):
            return proposal
        legal = tuple(profile for profile in catalogue if jointly_legal(profile))
        if not legal:
            raise StageCContractError("joint conflict repair found no legal catalogue profile")
        best = legal[0]
        best_score = float("-inf")
        for profile in legal:
            score = sum(
                model.score("C1", table.q1_states[index])
                + model.score("C2", table.q2_states[index])
                for table, index in zip(tables, profile, strict=True)
            )
            if score > best_score:
                best, best_score = profile, score
        return best

    @staticmethod
    def _profile_payload(profile: Profile, tables: Sequence[UserActionTable]) -> list[dict[str, object]]:
        if len(profile) != len(tables):
            raise StageCContractError("profile is incomplete")
        return [
            {"user_id": table.user_id, "action": table.actions[index].payload()}
            for table, index in zip(tables, profile, strict=True)
        ]

    @classmethod
    def _authenticate_inputs(
        cls,
        *,
        base_profile: Profile,
        tables: Sequence[UserActionTable],
        catalogue: Sequence[Profile],
        coordinator_information: CoordinatorInformation,
        arm_information_interfaces: Mapping[str, ArmInformationInterface],
        matched_information_sha256: str,
        coalition_context: Mapping[Profile, CoalitionContext] | None,
    ) -> None:
        required_arms = (*ARM_ORDER, "S0", "S_UNI")
        actual = authenticate_matched_catalogues(
            arm_information_interfaces, required_arms=required_arms
        )
        if actual != matched_information_sha256:
            raise StageCContractError("selector A4 equality authenticator drifted")
        if coordinator_information.catalogue_sha256 != next(
            iter(arm_information_interfaces.values())
        ).catalogue_sha256:
            raise StageCContractError("selector catalogue differs from A4 authority")
        if coordinator_information.source_provenance_sha256 != next(
            iter(arm_information_interfaces.values())
        ).source_provenance_sha256:
            raise StageCContractError("selector source provenance differs from A4 authority")
        supplied = {canonical_sha256(cls._profile_payload(profile, tables)) for profile in catalogue}
        authorised = {
            canonical_sha256(profile.payload()) for profile in coordinator_information.catalogue
        }
        if supplied != authorised:
            raise StageCContractError("selector catalogue differs from I_coordinator")
        reference = tuple(
            action for action in coordinator_information.references.proposal_a0
        )
        if [action.payload() for action in reference] != [
            item["action"] for item in cls._profile_payload(base_profile, tables)
        ]:
            raise StageCContractError("selector BASE differs from authenticated a0")
        if coalition_context is None:
            return
        expected_profiles = set(catalogue) | {base_profile}
        if set(coalition_context) != expected_profiles:
            raise StageCContractError("coalition contexts do not cover the catalogue exactly")
        expected_reference = tuple(
            (table.user_id, table.actions[index])
            for table, index in zip(tables, base_profile, strict=True)
        )
        for profile, context in coalition_context.items():
            if context.anchor_id != coordinator_information.anchor_id:
                raise StageCContractError("coalition context anchor is unauthenticated")
            if context.reference_profile != expected_reference:
                raise StageCContractError("coalition context reference profile is unauthenticated")
            changed = {
                table.user_id: (table.actions[base], table.actions[selected])
                for table, base, selected in zip(tables, base_profile, profile, strict=True)
                if selected != base
            }
            members = {member.user_id: member for member in context.members}
            if set(members) != set(changed):
                raise StageCContractError("coalition changed-user set differs from catalogue profile")
            for user, (reference_action, selected_action) in changed.items():
                member = members[user]
                if (
                    member.reference_action != reference_action
                    or member.selected_action != selected_action
                ):
                    raise StageCContractError("coalition physical actions differ from catalogue profile")

    @staticmethod
    def _additive_score(
        model: V1ThreeRouteModel,
        tables: Sequence[UserActionTable],
        profile: Profile,
        reference: Profile,
        *,
        knockout: str | None,
    ) -> float:
        total = 0.0
        for table, selected, baseline in zip(tables, profile, reference, strict=True):
            if knockout != "C1":
                total += model.score("C1", table.q1_states[selected]) - model.score(
                    "C1", table.q1_states[baseline]
                )
            if knockout != "C2":
                total += model.score("C2", table.q2_states[selected]) - model.score(
                    "C2", table.q2_states[baseline]
                )
        return total

    def select(
        self,
        *,
        base_profile: Profile,
        tables: Sequence[UserActionTable],
        catalogue: Sequence[Profile],
        jointly_legal: Callable[[Profile], bool],
        service_guard: Callable[[Profile], bool],
        model: V1ThreeRouteModel | None = None,
        coalition_context: Mapping[Profile, CoalitionContext] | None = None,
        exact_psi: Callable[[Profile], float] | None = None,
        exact_nominal_score: Callable[[Profile], float] | None = None,
        knockout_route: Route | None = None,
        coordinator_information: CoordinatorInformation,
        arm_information_interfaces: Mapping[str, ArmInformationInterface],
        matched_information_sha256: str,
        model_checkpoint_sha256: str | None = None,
        knockout_experiment: CheckpointKnockoutExperiment | None = None,
    ) -> SelectorDecision:
        self._authenticate_inputs(
            base_profile=base_profile,
            tables=tables,
            catalogue=catalogue,
            coordinator_information=coordinator_information,
            arm_information_interfaces=arm_information_interfaces,
            matched_information_sha256=matched_information_sha256,
            coalition_context=coalition_context if self.mode != "S_UNI" else None,
        )
        if self.mode == "S3" and model_checkpoint_sha256 is None:
            raise StageCContractError("S3 requires a deployed checkpoint identity")
        if knockout_route is not None:
            if (
                knockout_experiment is None
                or model_checkpoint_sha256 != knockout_experiment.checkpoint_sha256
                or knockout_route not in knockout_experiment.zeroed_deployed_routes
            ):
                raise StageCContractError("knockout is not bound to the deployed checkpoint")
        if not jointly_legal(base_profile) or not service_guard(base_profile):
            raise StageCContractError("selector requires a prevalidated BASE")
        if self.mode == "S_UNI":
            if exact_nominal_score is None:
                raise StageCContractError("S_UNI requires exact nominal joint physics")
            current = base_profile
            evaluated = 0
            while True:
                best = current
                best_score = exact_nominal_score(current)
                evaluated += 1
                for user_index, table in enumerate(tables):
                    for action_index, legal in enumerate(table.action_mask):
                        if not legal or action_index == current[user_index]:
                            continue
                        candidate = (*current[:user_index], action_index, *current[user_index + 1 :])
                        if not jointly_legal(candidate) or not service_guard(candidate):
                            continue
                        score = exact_nominal_score(candidate)
                        evaluated += 1
                        if score > best_score:
                            best, best_score = candidate, score
                if best == current:
                    return SelectorDecision("S_UNI", current, best_score, False, None, True, evaluated)
                current = best

        if model is None or coalition_context is None:
            raise StageCContractError(f"{self.mode} requires model and coalition contexts")
        if self.mode == "S0" and exact_psi is None:
            raise StageCContractError("S0 requires exact Psi")
        best = base_profile
        best_score = float("-inf")
        evaluated = 0
        for profile in (base_profile, *catalogue):
            if len(profile) != len(tables) or not jointly_legal(profile) or not service_guard(profile):
                continue
            additive = self._additive_score(
                model, tables, profile, base_profile, knockout=knockout_route
            )
            interaction = 0.0
            if knockout_route != "C3":
                interaction = (
                    model.interaction(coalition_context[profile])
                    if self.mode == "S3"
                    else float(exact_psi(profile))
                )
            score = additive + interaction
            evaluated += 1
            if score > best_score:
                best, best_score = profile, score
        if evaluated == 0:
            return SelectorDecision(self.mode, base_profile, 0.0, True, "empty_legal_catalogue", None, 0)
        return SelectorDecision(self.mode, best, best_score, False, None, None, evaluated)

    def select_timed(self, *, deadline_s: float = DEPLOYMENT_DEADLINE_S, **kwargs: object) -> SelectorDecision:
        """F2: validate BASE in the parent, then kill the coordinator on timeout."""

        base_profile = kwargs.get("base_profile")
        jointly_legal = kwargs.get("jointly_legal")
        service_guard = kwargs.get("service_guard")
        if (
            not isinstance(base_profile, tuple)
            or not callable(jointly_legal)
            or not callable(service_guard)
            or not jointly_legal(base_profile)
            or not service_guard(base_profile)
        ):
            raise StageCContractError("timed selector requires prevalidated BASE")
        if deadline_s <= 0.0:
            raise StageCContractError("selector deadline must be positive")
        context = multiprocessing.get_context("fork")
        parent, child = context.Pipe(duplex=False)

        def work() -> None:
            try:
                child.send(("ok", self.select(**kwargs)))
            except BaseException as error:
                child.send(("error", type(error).__name__))
            finally:
                child.close()

        started = time.monotonic()
        process = context.Process(target=work, name="stagec-profile-selector")
        process.start()
        child.close()
        process.join(deadline_s)
        if process.is_alive():
            pid = process.pid
            process.kill()
            process.join()
            parent.close()
            return SelectorDecision(
                self.mode,
                base_profile,
                0.0,
                True,
                "runner_deadline_process_killed",
                None,
                0,
                time.monotonic() - started,
                pid,
                not process.is_alive(),
            )
        elapsed = time.monotonic() - started
        if not parent.poll():
            parent.close()
            return SelectorDecision(
                self.mode, base_profile, 0.0, True, "coordinator_worker_failed", None, 0,
                elapsed, process.pid, False,
            )
        status, payload = parent.recv()
        parent.close()
        if status != "ok" or not isinstance(payload, SelectorDecision):
            return SelectorDecision(
                self.mode, base_profile, 0.0, True,
                f"coordinator_worker_error:{payload}", None, 0, elapsed, process.pid, False,
            )
        return SelectorDecision(
            payload.mode, payload.profile, payload.score, payload.used_fallback,
            payload.fallback_reason, payload.local_optimum_certified,
            payload.evaluated_profiles, elapsed, process.pid, False,
        )


__all__ = [
    "DEPLOYMENT_DEADLINE_S", "DeploymentAdapter", "DeploymentDecision", "Profile",
    "ProfileSelector", "ResolvedProfile", "SelectorDecision", "SelectorMode", "UserActionTable", "deployment_capability_manifest",
    "construct_reference_proposal", "independent_two_head_profile", "learned_c3_score", "masked_argmax", "select_s_uni",
]
