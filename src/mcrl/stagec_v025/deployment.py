"""Deployable two-head selector, set coordinator seam, and S_UNI comparator."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, Mapping, Protocol, Sequence

from .canonical import StageCContractError, canonical_sha256
from .learner import ThreeRouteModel
from .state import PhysicalAction


DEPLOYMENT_DEADLINE_S = 30.08
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


def deployment_capability_manifest(
    *, code_digest: str, physics_digest: str, catalogue_digest: str
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
    payload: dict[str, object] = {
        "schema": "mcrl-v025-stagec-deployment-capability-v1-draft",
        "code_digest": code_digest,
        "physics_digest": physics_digest,
        "catalogue_digest": catalogue_digest,
        "deadline_s": DEPLOYMENT_DEADLINE_S,
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
        "timer_scope": "proposal+forecasts+catalogue+selection+validation+fallback",
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
        """Start the deadline before host forecast/table/catalogue preparation."""

        started = clock()
        if not jointly_legal(base_profile):
            raise StageCContractError("BASE must be a jointly legal profile")
        try:
            tables, catalogue = prepare()
        except Exception as error:
            return DeploymentDecision(
                base_profile,
                base_profile,
                True,
                f"prep_failure:{type(error).__name__}",
                max(0.0, clock() - started),
                True,
                True,
            )
        if clock() - started > self.deadline_s:
            return DeploymentDecision(
                base_profile,
                base_profile,
                True,
                "deadline",
                max(0.0, clock() - started),
                True,
                True,
            )
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


__all__ = [
    "DEPLOYMENT_DEADLINE_S", "DeploymentAdapter", "DeploymentDecision", "Profile",
    "ResolvedProfile", "UserActionTable", "deployment_capability_manifest",
    "independent_two_head_profile", "learned_c3_score", "masked_argmax", "select_s_uni",
]
