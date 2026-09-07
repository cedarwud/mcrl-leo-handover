"""Pure source-binding plan for the later V0.23 five-arm ablation.

This module is deliberately one layer below an episode runner.  It accepts
already authenticated source attestations and emits an immutable description
of which source is bound to each primary arm.  It does not call a provider,
read a receipt, run a learner, open an episode, or choose scientific values.

The three neutral route inputs correspond to the existing seams:

* C1 uses the cluster-matched neutral source rule;
* C2 uses the equal-budget neutral source rule; and
* C3 uses the matched-placebo neutral source supplied by the sealed provider.

The plan is intentionally fail-closed.  Every route source carries an exact
source digest, a common configuration/world/seed binding, and learner
initialization/update counts.  Only the route source is changed between a
FULL arm and its DROP counterpart; a post-hoc head drop is not admitted as a
primary efficacy ablation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import hashlib
import json
import math
from types import MappingProxyType


SCHEMA = "multi-catfish-mcrl-v023-source-binding-plan-v2"
SCHEMA_VERSION = 2

PRIMARY_ARMS: tuple[str, ...] = (
    "FULL",
    "BASELINE",
    "DROP_C1",
    "DROP_C2",
    "DROP_C3",
)
ROUTES: tuple[str, ...] = ("C1", "C2", "C3")

INFORMED = "INFORMED"
CLUSTER_MATCHED_NEUTRAL = "CLUSTER_MATCHED_NEUTRAL"
EQUAL_BUDGET_NEUTRAL = "EQUAL_BUDGET_NEUTRAL"
MATCHED_PLACEBO_NEUTRAL = "MATCHED_PLACEBO_NEUTRAL"

# Public aliases make the route contract discoverable without introducing a
# second implementation of either neutral selector.
C1_CLUSTER_MATCHED_NEUTRAL = CLUSTER_MATCHED_NEUTRAL
C2_EQUAL_BUDGET_NEUTRAL = EQUAL_BUDGET_NEUTRAL
C3_MATCHED_PLACEBO_NEUTRAL = MATCHED_PLACEBO_NEUTRAL

SOURCE_ABLATION = "SOURCE_ABLATION"
HEAD_DROP = "HEAD_DROP"

C1_CLUSTER_NEUTRAL_SOURCE_RULE = (
    "c1-cluster-profile-matched-randomized-predecision-v2"
)
C2_EQUAL_BUDGET_NEUTRAL_SOURCE_RULE = "c2-equal-budget-uniform-predecision-v1"
C3_MATCHED_PLACEBO_SOURCE_RULE = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"

BASELINE_SOURCE_KIND = "EXPLICIT_AUTHENTICATED_PRE_CATFISH_POLICY"
TRAIN_SPLITS = frozenset({"TRAIN", "TRAIN_DEVELOPMENT"})


class SourceBindingPlanError(ValueError):
    """A source-binding plan cannot be admitted under the frozen contract."""


# Compatibility spelling for callers that use the longer name.
V023SourceBindingPlanError = SourceBindingPlanError


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical mapping keys must be strings")
            result[key] = _jsonable(child)
        return result
    if isinstance(value, (tuple, list)):
        return [_jsonable(child) for child in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON does not admit non-finite floats")
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            _jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise SourceBindingPlanError("value is not canonical finite ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    """Hash a strict canonical JSON value."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _digest(value: object, *, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SourceBindingPlanError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SourceBindingPlanError(f"{field_name} must be a non-empty trimmed string")
    return value


def _positive_int(value: object, *, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise SourceBindingPlanError(f"{field_name} must be a positive exact integer")
    return value


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


def _sequence(value: object, *, field_name: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes, Mapping)):
        raise SourceBindingPlanError(f"{field_name} must be a non-empty sequence")
    try:
        result = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise SourceBindingPlanError(
            f"{field_name} must be a non-empty sequence"
        ) from error
    if not result:
        raise SourceBindingPlanError(f"{field_name} must be non-empty")
    return result


def _train_split(value: object, *, field_name: str) -> str:
    split = _text(value, field_name=field_name)
    upper = split.upper()
    if "TEST" in upper or not upper.startswith("TRAIN"):
        raise SourceBindingPlanError(f"{field_name} must be TRAIN-only")
    return split


def _safe_world_ids(value: object) -> tuple[str | int, ...]:
    raw = _sequence(value, field_name="world_ids")
    result: list[str | int] = []
    for index, world in enumerate(raw):
        if type(world) is int:
            if world < 0:
                raise SourceBindingPlanError(
                    f"world_ids[{index}] must be nonnegative when numeric"
                )
            result.append(world)
            continue
        if not isinstance(world, str) or not world.strip():
            raise SourceBindingPlanError(
                f"world_ids[{index}] must be a non-empty string or integer"
            )
        if "TEST" in world.upper():
            raise SourceBindingPlanError("TEST world identifiers are closed")
        result.append(world)
    if len(set(result)) != len(result):
        raise SourceBindingPlanError("world_ids must be unique")
    return tuple(result)


def _safe_seeds(value: object, *, field_name: str = "training_seeds") -> tuple[int, ...]:
    raw = _sequence(value, field_name=field_name)
    result: list[int] = []
    for index, seed in enumerate(raw):
        if type(seed) is not int or seed < 0:
            raise SourceBindingPlanError(
                f"{field_name}[{index}] must be a nonnegative exact integer"
            )
        result.append(seed)
    if len(set(result)) != len(result):
        raise SourceBindingPlanError(f"{field_name} must be unique")
    return tuple(result)


def _safe_initialization_ids(value: object) -> tuple[str | int, ...]:
    raw = _sequence(value, field_name="learner_initialization_ids")
    result: list[str | int] = []
    for index, item in enumerate(raw):
        if type(item) is int:
            if item < 0:
                raise SourceBindingPlanError(
                    f"learner_initialization_ids[{index}] must be nonnegative"
                )
            result.append(item)
        elif isinstance(item, str) and item.strip():
            result.append(item)
        else:
            raise SourceBindingPlanError(
                "learner_initialization_ids must contain strings or integers"
            )
    if len(set(result)) != len(result):
        raise SourceBindingPlanError("learner_initialization_ids must be unique")
    return tuple(result)


def _expected_collection_sha256(label: str, values: Sequence[object]) -> str:
    return canonical_sha256({label: list(values)})


_FORBIDDEN_KEYS = frozenset(
    {
        "test",
        "test_id",
        "test_ids",
        "test_split",
        "test_split_opened",
        "test_world",
        "test_worlds",
        "episode",
        "episodes",
        "episode_id",
        "episode_count",
        "episode_training",
        "physical_episode",
        "outcome",
        "outcomes",
        "reward",
        "rewards",
        "metric",
        "metrics",
        "alias",
        "aliases",
        "source_alias",
        "source_aliases",
        "same_source",
        "head_drop",
        "drop_mode",
    }
)


def _reject_forbidden_tree(value: object, *, field_name: str) -> None:
    """Reject outcome/TEST/episode metadata crossing the binding boundary."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SourceBindingPlanError(
                    f"{field_name} contains a non-string metadata key"
                )
            normalized = key.strip().lower()
            if normalized in _FORBIDDEN_KEYS:
                raise SourceBindingPlanError(
                    f"{field_name} contains forbidden {key} field"
                )
            _reject_forbidden_tree(child, field_name=f"{field_name}.{key}")
    elif isinstance(value, (tuple, list)):
        for index, child in enumerate(value):
            _reject_forbidden_tree(child, field_name=f"{field_name}[{index}]")


def _normalize_route(route: object) -> str:
    value = _text(route, field_name="route").upper()
    if value not in ROUTES:
        raise SourceBindingPlanError(f"route must be one of {ROUTES}")
    return value


def _normalize_mode(route: str, mode: object) -> str:
    value = _text(mode, field_name="mode")
    upper = value.upper().replace("-", "_")
    # The current selectors expose their source-rule names.  Accept those
    # spellings as an input alias but retain one canonical plan vocabulary.
    if upper == INFORMED or (
        route == "C1" and value == "c1-exp-dull-rollout-lower-frontier-v1"
    ) or (
        route == "C2" and value == "c2-hold-or-max-lagged-sinr-rival-predecision-v1"
    ):
        return INFORMED
    if route == "C1" and (
        upper == CLUSTER_MATCHED_NEUTRAL
        or value == C1_CLUSTER_NEUTRAL_SOURCE_RULE
    ):
        return CLUSTER_MATCHED_NEUTRAL
    if route == "C2" and (
        upper == EQUAL_BUDGET_NEUTRAL
        or value == C2_EQUAL_BUDGET_NEUTRAL_SOURCE_RULE
    ):
        return EQUAL_BUDGET_NEUTRAL
    if route == "C3" and (
        upper in {MATCHED_PLACEBO_NEUTRAL, "MATCHED_PLACEBO", "NEUTRAL_SOURCE"}
    ):
        return MATCHED_PLACEBO_NEUTRAL
    if upper == HEAD_DROP:
        raise SourceBindingPlanError(
            "HEAD_DROP is not admitted as a primary efficacy ablation"
        )
    raise SourceBindingPlanError(f"unsupported {route} source mode: {value}")


def _normalize_ablation_mode(value: object) -> str:
    mode = _text(value, field_name="ablation_mode").upper().replace("-", "_")
    if mode == HEAD_DROP:
        raise SourceBindingPlanError(
            "HEAD_DROP is not admitted as a primary efficacy ablation"
        )
    if mode != SOURCE_ABLATION:
        raise SourceBindingPlanError(
            "primary DROP arms require SOURCE_ABLATION semantics"
        )
    return SOURCE_ABLATION


@dataclass(frozen=True)
class CommonBinding:
    """Exact source-world contract shared by the three route pairs.

    Learner configuration, initialization and update budgets are deliberately
    *not* common across C1/C2/C3.  They are route-specific and are matched only
    between the informed and neutral source of the same route.
    """

    split: str
    world_ids: tuple[str | int, ...]
    training_seeds: tuple[int, ...]
    world_sha256: str
    seed_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "world_ids", tuple(self.world_ids))
        object.__setattr__(self, "training_seeds", tuple(self.training_seeds))

    def verify(self) -> None:
        _train_split(self.split, field_name="split")
        worlds = _safe_world_ids(self.world_ids)
        seeds = _safe_seeds(self.training_seeds)
        _digest(self.world_sha256, field_name="world_sha256")
        _digest(self.seed_sha256, field_name="seed_sha256")
        if self.world_sha256 != _expected_collection_sha256("world_ids", worlds):
            raise SourceBindingPlanError("world_ids do not match world_sha256")
        if self.seed_sha256 != _expected_collection_sha256("training_seeds", seeds):
            raise SourceBindingPlanError("training_seeds do not match seed_sha256")

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "split": self.split,
            "world_ids": list(self.world_ids),
            "training_seeds": list(self.training_seeds),
            "world_sha256": self.world_sha256,
            "seed_sha256": self.seed_sha256,
        }


# Shorter alias for callers that call this context a study binding.
StudyBinding = CommonBinding


@dataclass(frozen=True)
class RouteSourceBinding:
    """One authenticated C1/C2/C3 source attestation."""

    route: str
    mode: str
    source_sha256: str
    row_budget: int
    learner_initialization_ids: tuple[str | int, ...]
    learner_initialization_sha256: str
    learner_config_sha256: str
    learner_update_count: int
    common: CommonBinding
    source_rule: str
    authenticated: bool = True
    source_identity: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
    test_split_opened: bool = False
    episode_training: bool = False

    def __post_init__(self) -> None:
        route = _normalize_route(self.route)
        object.__setattr__(self, "route", route)
        object.__setattr__(self, "mode", _normalize_mode(route, self.mode))
        object.__setattr__(
            self,
            "learner_initialization_ids",
            tuple(self.learner_initialization_ids),
        )
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    @property
    def source_hash(self) -> str:
        """Compatibility alias for the exact route source digest."""

        return self.source_sha256

    @property
    def update_budget(self) -> int:
        return self.learner_update_count

    @property
    def initialization_count(self) -> int:
        return len(self.learner_initialization_ids)

    @property
    def learner_initialization_count(self) -> int:
        """Number of route-local learner initializations."""

        return len(self.learner_initialization_ids)

    @property
    def neutral(self) -> bool:
        return self.mode != INFORMED

    def verify(self) -> None:
        _digest(self.source_sha256, field_name=f"{self.route}.source_sha256")
        _positive_int(self.row_budget, field_name=f"{self.route}.row_budget")
        initializations = _safe_initialization_ids(self.learner_initialization_ids)
        _digest(
            self.learner_initialization_sha256,
            field_name=f"{self.route}.learner_initialization_sha256",
        )
        if self.learner_initialization_sha256 != _expected_collection_sha256(
            "learner_initialization_ids", initializations
        ):
            raise SourceBindingPlanError(
                f"{self.route} learner initialization digest drifted"
            )
        _digest(
            self.learner_config_sha256,
            field_name=f"{self.route}.learner_config_sha256",
        )
        _positive_int(
            self.learner_update_count,
            field_name=f"{self.route}.learner_update_count",
        )
        if not isinstance(self.common, CommonBinding):
            raise SourceBindingPlanError(
                f"{self.route}.common must be CommonBinding"
            )
        self.common.verify()
        _text(self.source_rule, field_name=f"{self.route}.source_rule")
        if self.mode == CLUSTER_MATCHED_NEUTRAL:
            if self.route != "C1" or self.source_rule != C1_CLUSTER_NEUTRAL_SOURCE_RULE:
                raise SourceBindingPlanError(
                    "C1 neutral source must use the cluster-matched source rule"
                )
        elif self.mode == EQUAL_BUDGET_NEUTRAL:
            if self.route != "C2" or self.source_rule != C2_EQUAL_BUDGET_NEUTRAL_SOURCE_RULE:
                raise SourceBindingPlanError(
                    "C2 neutral source must use the equal-budget source rule"
                )
        elif self.mode == MATCHED_PLACEBO_NEUTRAL:
            if self.route != "C3" or self.source_rule != C3_MATCHED_PLACEBO_SOURCE_RULE:
                raise SourceBindingPlanError(
                    "C3 neutral source must use the matched-placebo source rule"
                )
        if self.mode == INFORMED and "NEUTRAL" in self.source_rule.upper():
            raise SourceBindingPlanError(
                f"{self.route} informed source cannot use a neutral source rule"
            )
        if type(self.authenticated) is not bool or not self.authenticated:
            raise SourceBindingPlanError(
                f"{self.route} source must be explicitly authenticated"
            )
        if self.source_identity is not None:
            _text(self.source_identity, field_name=f"{self.route}.source_identity")
        if type(self.test_split_opened) is not bool or self.test_split_opened:
            raise SourceBindingPlanError(f"{self.route} source crossed TEST boundary")
        if type(self.episode_training) is not bool or self.episode_training:
            raise SourceBindingPlanError(
                f"{self.route} source crossed the episode boundary"
            )
        _reject_forbidden_tree(self.metadata, field_name=f"{self.route}.metadata")

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "route": self.route,
            "mode": self.mode,
            "source_rule": self.source_rule,
            "source_sha256": self.source_sha256,
            "row_budget": self.row_budget,
            "learner_initialization_ids": list(self.learner_initialization_ids),
            "learner_initialization_count": self.learner_initialization_count,
            "learner_initialization_sha256": self.learner_initialization_sha256,
            "learner_config_sha256": self.learner_config_sha256,
            "learner_update_count": self.learner_update_count,
            "source_identity": self.source_identity,
            "common": self.common.to_dict(),
        }


@dataclass(frozen=True)
class BaselinePolicyBinding:
    """An explicit authenticated pre-Catfish Main policy artifact.

    The baseline predates the C1/C2/C3 source learners, so it must not claim
    their training worlds, learner initializations, or update budget.  Shared
    physical-evaluation inputs belong to the later evaluator contract rather
    than this source-binding layer.
    """

    policy_id: str
    policy_sha256: str
    authentication_sha256: str
    authenticated: bool = True
    explicit_pre_catfish: bool = True
    source_kind: str = BASELINE_SOURCE_KIND
    source_identity: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
    test_split_opened: bool = False
    episode_training: bool = False

    @property
    def source_sha256(self) -> str:
        """Compatibility alias used by generic artifact-binding consumers."""

        return self.policy_sha256

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def verify(self) -> None:
        _text(self.policy_id, field_name="baseline.policy_id")
        _digest(self.policy_sha256, field_name="baseline.policy_sha256")
        _digest(
            self.authentication_sha256,
            field_name="baseline.authentication_sha256",
        )
        if self.policy_sha256 == self.authentication_sha256:
            raise SourceBindingPlanError(
                "baseline policy and authentication digests must be distinct"
            )
        if type(self.authenticated) is not bool or not self.authenticated:
            raise SourceBindingPlanError(
                "BASELINE requires an explicitly authenticated policy"
            )
        if type(self.explicit_pre_catfish) is not bool or not self.explicit_pre_catfish:
            raise SourceBindingPlanError(
                "BASELINE must be explicitly marked pre-Catfish"
            )
        if self.source_kind != BASELINE_SOURCE_KIND:
            raise SourceBindingPlanError(
                "BASELINE source kind must identify an explicit pre-Catfish policy"
            )
        if self.source_identity is not None:
            _text(self.source_identity, field_name="baseline.source_identity")
        if type(self.test_split_opened) is not bool or self.test_split_opened:
            raise SourceBindingPlanError("BASELINE crossed TEST boundary")
        if type(self.episode_training) is not bool or self.episode_training:
            raise SourceBindingPlanError("BASELINE crossed the episode boundary")
        _reject_forbidden_tree(self.metadata, field_name="baseline.metadata")
        policy_text = self.policy_id.upper().replace(" ", "_")
        if "Q1+Q2" in policy_text or "Q1_Q2" in policy_text:
            raise SourceBindingPlanError(
                "BASELINE cannot be inferred from a Q1+Q2 source"
            )

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "policy_id": self.policy_id,
            "policy_sha256": self.policy_sha256,
            "authentication_sha256": self.authentication_sha256,
            "source_kind": self.source_kind,
            "source_identity": self.source_identity,
        }


@dataclass(frozen=True)
class ArmSourceBinding:
    """The route bindings selected for exactly one primary arm."""

    arm: str
    routes: tuple[RouteSourceBinding, ...] = ()
    baseline: BaselinePolicyBinding | None = None
    ablation_mode: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "arm", _text(self.arm, field_name="arm").upper())
        object.__setattr__(self, "routes", tuple(self.routes))

    @property
    def route_bindings(self) -> tuple[RouteSourceBinding, ...]:
        return self.routes

    def route(self, name: str) -> RouteSourceBinding:
        route = _normalize_route(name)
        for binding in self.routes:
            if binding.route == route:
                return binding
        raise SourceBindingPlanError(f"{self.arm} has no {route} route binding")

    def verify(self, *, common: CommonBinding, plan_ablation_mode: str) -> None:
        if self.arm not in PRIMARY_ARMS:
            raise SourceBindingPlanError(f"unknown primary arm: {self.arm}")
        if self.arm == "BASELINE":
            if self.baseline is None:
                raise SourceBindingPlanError(
                    "BASELINE requires an explicit authenticated policy binding"
                )
            if self.routes:
                raise SourceBindingPlanError("BASELINE must not be inferred from route sources")
            self.baseline.verify()
            if self.ablation_mode is not None:
                raise SourceBindingPlanError("BASELINE cannot carry an ablation mode")
            return
        if self.baseline is not None:
            raise SourceBindingPlanError(f"{self.arm} cannot carry a BASELINE policy")
        if self.ablation_mode != plan_ablation_mode:
            raise SourceBindingPlanError(f"{self.arm} ablation mode drifted")
        if tuple(binding.route for binding in self.routes) != ROUTES:
            raise SourceBindingPlanError(
                f"{self.arm} must bind C1, C2, and C3 exactly once"
            )
        for binding in self.routes:
            if not isinstance(binding, RouteSourceBinding):
                raise SourceBindingPlanError(f"{self.arm} has an invalid route binding")
            binding.verify()
            if binding.common != common:
                raise SourceBindingPlanError(f"{self.arm} {binding.route} common binding drifted")

        expected_modes = {
            "FULL": {
                "C1": INFORMED,
                "C2": INFORMED,
                "C3": INFORMED,
            },
            "DROP_C1": {
                "C1": CLUSTER_MATCHED_NEUTRAL,
                "C2": INFORMED,
                "C3": INFORMED,
            },
            "DROP_C2": {
                "C1": INFORMED,
                "C2": EQUAL_BUDGET_NEUTRAL,
                "C3": INFORMED,
            },
            "DROP_C3": {
                "C1": INFORMED,
                "C2": INFORMED,
                "C3": MATCHED_PLACEBO_NEUTRAL,
            },
        }[self.arm]
        for route, expected in expected_modes.items():
            actual = self.route(route).mode
            if actual != expected:
                raise SourceBindingPlanError(
                    f"{self.arm} {route} requires {expected}, got {actual}"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "routes": [binding.to_dict() for binding in self.routes],
            "baseline": None if self.baseline is None else self.baseline.to_dict(),
            "ablation_mode": self.ablation_mode,
        }


@dataclass(frozen=True)
class FiveArmSourceBindingPlan:
    """Content-addressed plan for FULL/BASELINE/three source ablations."""

    common: CommonBinding
    arm_bindings: tuple[ArmSourceBinding, ...]
    ablation_mode: str
    plan_sha256: str
    schema: str = SCHEMA
    schema_version: int = SCHEMA_VERSION

    @property
    def arms(self) -> tuple[str, ...]:
        return tuple(binding.arm for binding in self.arm_bindings)

    @property
    def route_learner_update_counts(self) -> dict[str, int]:
        """Return the independently frozen update budget for each route."""

        full = self.for_arm("FULL")
        return {route: full.route(route).learner_update_count for route in ROUTES}

    @property
    def route_learner_initialization_ids(
        self,
    ) -> dict[str, tuple[str | int, ...]]:
        """Return the independently frozen initialization panel per route."""

        full = self.for_arm("FULL")
        return {
            route: full.route(route).learner_initialization_ids for route in ROUTES
        }

    def for_arm(self, arm: str) -> ArmSourceBinding:
        normalized = _text(arm, field_name="arm").upper()
        for binding in self.arm_bindings:
            if binding.arm == normalized:
                return binding
        raise SourceBindingPlanError(f"plan has no arm {normalized}")

    def route_source_hashes(self, arm: str) -> dict[str, str]:
        binding = self.for_arm(arm)
        if binding.arm == "BASELINE":
            assert binding.baseline is not None
            return {"BASELINE": binding.baseline.policy_sha256}
        return {route.route: route.source_sha256 for route in binding.routes}

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "ablation_mode": self.ablation_mode,
            "common": self.common.to_dict(),
            "arms": [binding.to_dict() for binding in self.arm_bindings],
        }

    def verify(self) -> str:
        if self.schema != SCHEMA or self.schema_version != SCHEMA_VERSION:
            raise SourceBindingPlanError("source-binding plan schema drifted")
        self.common.verify()
        ablation_mode = _normalize_ablation_mode(self.ablation_mode)
        if tuple(self.arms) != PRIMARY_ARMS:
            raise SourceBindingPlanError(
                "a five-arm plan must contain FULL, BASELINE, DROP_C1, DROP_C2, DROP_C3"
            )
        for binding in self.arm_bindings:
            binding.verify(common=self.common, plan_ablation_mode=ablation_mode)
        _verify_route_pairs(self.arm_bindings)
        _verify_cross_binding_aliases(self.arm_bindings)
        expected = canonical_sha256(self._payload())
        if self.plan_sha256 != expected:
            raise SourceBindingPlanError("source-binding plan digest drifted")
        return expected

    def to_dict(self) -> dict[str, object]:
        self.verify()
        payload = self._payload()
        payload["plan_sha256"] = self.plan_sha256
        return payload


# Concise compatibility aliases.
SourceBindingPlan = FiveArmSourceBindingPlan
FiveArmPlan = FiveArmSourceBindingPlan


def _unique_route_bindings(arms: Sequence[ArmSourceBinding]) -> tuple[RouteSourceBinding, ...]:
    result: list[RouteSourceBinding] = []
    seen: set[tuple[str, str, str]] = set()
    for arm in arms:
        for binding in arm.routes:
            key = (binding.route, binding.mode, binding.source_sha256)
            if key not in seen:
                result.append(binding)
                seen.add(key)
    return tuple(result)


def _verify_route_pairs(arms: Sequence[ArmSourceBinding]) -> None:
    full = next(binding for binding in arms if binding.arm == "FULL")
    drops = {
        binding.arm: binding
        for binding in arms
        if binding.arm in {"DROP_C1", "DROP_C2", "DROP_C3"}
    }
    for route, drop_arm, neutral_mode in (
        ("C1", "DROP_C1", CLUSTER_MATCHED_NEUTRAL),
        ("C2", "DROP_C2", EQUAL_BUDGET_NEUTRAL),
        ("C3", "DROP_C3", MATCHED_PLACEBO_NEUTRAL),
    ):
        informed = full.route(route)
        neutral = drops[drop_arm].route(route)
        if informed.mode != INFORMED or neutral.mode != neutral_mode:
            raise SourceBindingPlanError(f"{route} informed/neutral role drifted")
        if informed.row_budget != neutral.row_budget:
            raise SourceBindingPlanError(
                f"{route} informed and neutral row budgets must be equal"
            )
        if informed.learner_initialization_count != neutral.learner_initialization_count:
            raise SourceBindingPlanError(
                f"{route} informed and neutral initialization counts must be equal"
            )
        if informed.learner_initialization_ids != neutral.learner_initialization_ids:
            raise SourceBindingPlanError(
                f"{route} informed and neutral initialization IDs must be equal"
            )
        if (
            informed.learner_initialization_sha256
            != neutral.learner_initialization_sha256
        ):
            raise SourceBindingPlanError(
                f"{route} informed and neutral initialization digests must be equal"
            )
        if informed.learner_config_sha256 != neutral.learner_config_sha256:
            raise SourceBindingPlanError(
                f"{route} informed and neutral learner configs must be equal"
            )
        if informed.learner_update_count != neutral.learner_update_count:
            raise SourceBindingPlanError(
                f"{route} informed and neutral update budgets must be equal"
            )
        if informed.source_sha256 == neutral.source_sha256:
            raise SourceBindingPlanError(
                f"{route} neutral source aliases its informed source hash"
            )
        if (
            informed.source_identity is not None
            and neutral.source_identity is not None
            and informed.source_identity == neutral.source_identity
        ):
            raise SourceBindingPlanError(
                f"{route} neutral source aliases its informed source identity"
            )


def _verify_cross_binding_aliases(arms: Sequence[ArmSourceBinding]) -> None:
    sources = _unique_route_bindings(arms)
    identities: dict[str, tuple[str, str]] = {}
    hashes: dict[str, tuple[str, str]] = {}
    for source in sources:
        label = f"{source.route}/{source.mode}"
        prior_hash = hashes.get(source.source_sha256)
        if prior_hash is not None and prior_hash != (source.route, source.mode):
            raise SourceBindingPlanError(
                f"source hash aliases distinct route bindings: {prior_hash} and {label}"
            )
        hashes[source.source_sha256] = (source.route, source.mode)
        identity = source.source_identity or source.source_sha256
        prior_identity = identities.get(identity)
        if prior_identity is not None and prior_identity != (source.route, source.mode):
            raise SourceBindingPlanError(
                f"source identity aliases distinct route bindings: {prior_identity} and {label}"
            )
        identities[identity] = (source.route, source.mode)

    baseline = next(binding for binding in arms if binding.arm == "BASELINE").baseline
    assert baseline is not None
    baseline_label = "BASELINE/POLICY"
    prior_hash = hashes.get(baseline.policy_sha256)
    if prior_hash is not None:
        raise SourceBindingPlanError(
            f"BASELINE policy aliases route source {prior_hash}"
        )
    baseline_identity = baseline.source_identity or baseline.policy_sha256
    if baseline_identity in identities:
        raise SourceBindingPlanError(
            f"BASELINE policy aliases route source {identities[baseline_identity]}"
        )
    # Keep the local variable meaningful in tracebacks and make the boundary
    # explicit for reviewers; baseline is otherwise intentionally independent.
    _ = baseline_label


def build_five_arm_source_binding_plan(
    *,
    common: CommonBinding,
    c1_informed: RouteSourceBinding,
    c1_cluster_neutral: RouteSourceBinding,
    c2_informed: RouteSourceBinding,
    c2_equal_budget_neutral: RouteSourceBinding,
    c3_informed: RouteSourceBinding,
    c3_matched_placebo_neutral: RouteSourceBinding,
    baseline: BaselinePolicyBinding,
    ablation_mode: str = SOURCE_ABLATION,
) -> FiveArmSourceBindingPlan:
    """Construct and authenticate the fixed five-arm source plan.

    All values affecting the scientific run are caller inputs.  This function
    only validates their equality and assembles the frozen arm mapping.
    """

    if not isinstance(common, CommonBinding):
        raise SourceBindingPlanError("common must be CommonBinding")
    common.verify()
    selected_ablation_mode = _normalize_ablation_mode(ablation_mode)
    route_inputs = (
        c1_informed,
        c1_cluster_neutral,
        c2_informed,
        c2_equal_budget_neutral,
        c3_informed,
        c3_matched_placebo_neutral,
    )
    for source in route_inputs:
        if not isinstance(source, RouteSourceBinding):
            raise SourceBindingPlanError("all route inputs must be RouteSourceBinding values")
        source.verify()
        if source.common != common:
            raise SourceBindingPlanError(
                f"{source.route} source has world/seed drift"
            )
    if not isinstance(baseline, BaselinePolicyBinding):
        raise SourceBindingPlanError(
            "baseline must be an explicit BaselinePolicyBinding; it cannot be inferred"
        )
    baseline.verify()

    plan_arms = (
        ArmSourceBinding(
            arm="FULL",
            routes=(c1_informed, c2_informed, c3_informed),
            ablation_mode=selected_ablation_mode,
        ),
        ArmSourceBinding(arm="BASELINE", baseline=baseline),
        ArmSourceBinding(
            arm="DROP_C1",
            routes=(c1_cluster_neutral, c2_informed, c3_informed),
            ablation_mode=selected_ablation_mode,
        ),
        ArmSourceBinding(
            arm="DROP_C2",
            routes=(c1_informed, c2_equal_budget_neutral, c3_informed),
            ablation_mode=selected_ablation_mode,
        ),
        ArmSourceBinding(
            arm="DROP_C3",
            routes=(c1_informed, c2_informed, c3_matched_placebo_neutral),
            ablation_mode=selected_ablation_mode,
        ),
    )
    payload = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "ablation_mode": selected_ablation_mode,
        "common": common.to_dict(),
        "arms": [arm.to_dict() for arm in plan_arms],
    }
    plan = FiveArmSourceBindingPlan(
        common=common,
        arm_bindings=plan_arms,
        ablation_mode=selected_ablation_mode,
        plan_sha256=canonical_sha256(payload),
    )
    plan.verify()
    return plan


# Natural aliases for external launch-contract authors.
plan_five_arm_source_bindings = build_five_arm_source_binding_plan
make_five_arm_source_binding_plan = build_five_arm_source_binding_plan


def _source_value(source: object, name: str) -> object:
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _source_has(source: object, name: str) -> bool:
    if isinstance(source, Mapping):
        return name in source
    return hasattr(source, name)


def _source_digest_candidate(source: object) -> str | None:
    for name in (
        "provider_receipt_sha256",
        "selection_digest",
        "source_sha256",
        "source_digest",
        "content_digest",
        "attestation_sha256",
    ):
        if _source_has(source, name):
            value = _source_value(source, name)
            if value is not None:
                return _digest(value, field_name=f"source.{name}")
    return None


def _source_row_budget_candidate(source: object) -> int | None:
    for name in ("source_row_count", "row_count", "budget", "informed_budget"):
        if _source_has(source, name):
            value = _source_value(source, name)
            if value is not None:
                return _positive_int(value, field_name=f"source.{name}")
    return None


def _source_update_budget_candidate(source: object) -> int | None:
    for name in ("update_budget", "learner_update_count", "updates"):
        if _source_has(source, name):
            value = _source_value(source, name)
            if value is not None:
                return _positive_int(value, field_name=f"source.{name}")
    return None


def _authenticate_source_object(source: object) -> None:
    if source is None:
        raise SourceBindingPlanError("an authenticated source object is required")
    if isinstance(source, Mapping):
        _reject_forbidden_tree(source, field_name="source")
    verify = getattr(source, "verify", None)
    if verify is not None:
        if not callable(verify):
            raise SourceBindingPlanError("source.verify must be callable")
        try:
            result = verify()
        except Exception as error:  # pragma: no cover - adapter boundary
            raise SourceBindingPlanError("source authentication failed") from error
        if result is False:
            raise SourceBindingPlanError("source authentication returned false")
    authenticated = _source_value(source, "authenticated")
    if authenticated is not None and (
        type(authenticated) is not bool or not authenticated
    ):
        raise SourceBindingPlanError("source is not explicitly authenticated")


def bind_authenticated_route_source(
    source: object,
    *,
    route: str,
    mode: str,
    common: CommonBinding,
    source_sha256: str | None = None,
    row_budget: int | None = None,
    learner_initialization_ids: Sequence[str | int] | None = None,
    learner_config_sha256: str | None = None,
    learner_update_count: int | None = None,
    source_rule: str | None = None,
    source_identity: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> RouteSourceBinding:
    """Bind an already-authenticated selector/provider result.

    The function never calls a provider.  ``source`` must be a result already
    obtained from the C1/C2/C3 seam; its optional ``verify`` method is called
    only to re-authenticate that immutable result in memory.
    """

    _authenticate_source_object(source)
    normalized_route = _normalize_route(route)
    normalized_mode = _normalize_mode(normalized_route, mode)
    if source_sha256 is None:
        source_sha256 = _source_digest_candidate(source)
    if source_sha256 is None:
        raise SourceBindingPlanError(
            f"{normalized_route} source_sha256 is missing; no implicit hash is allowed"
        )
    if row_budget is None:
        row_budget = _source_row_budget_candidate(source)
    if row_budget is None:
        raise SourceBindingPlanError(f"{normalized_route} source row budget is missing")
    if learner_initialization_ids is None:
        candidate = _source_value(source, "learner_initialization_ids")
        if candidate is not None and not isinstance(candidate, (str, bytes, Mapping)):
            try:
                learner_initialization_ids = tuple(candidate)  # type: ignore[arg-type]
            except TypeError as error:
                raise SourceBindingPlanError(
                    f"{normalized_route} learner initialization IDs are malformed"
                ) from error
    if learner_initialization_ids is None:
        raise SourceBindingPlanError(
            f"{normalized_route} learner initialization IDs are missing"
        )
    normalized_initializations = _safe_initialization_ids(
        learner_initialization_ids
    )
    if learner_config_sha256 is None:
        candidate = _source_value(source, "learner_config_sha256")
        if candidate is not None:
            learner_config_sha256 = candidate  # type: ignore[assignment]
    if learner_config_sha256 is None:
        raise SourceBindingPlanError(
            f"{normalized_route} learner config digest is missing"
        )
    normalized_config = _digest(
        learner_config_sha256,
        field_name=f"{normalized_route}.learner_config_sha256",
    )
    if learner_update_count is None:
        learner_update_count = _source_update_budget_candidate(source)
    if learner_update_count is None:
        raise SourceBindingPlanError(
            f"{normalized_route} learner update count is missing"
        )
    if source_rule is None:
        source_rule = _source_value(source, "source_rule")
    if source_rule is None and normalized_mode == CLUSTER_MATCHED_NEUTRAL:
        source_rule = C1_CLUSTER_NEUTRAL_SOURCE_RULE
    if source_rule is None and normalized_mode == EQUAL_BUDGET_NEUTRAL:
        source_rule = C2_EQUAL_BUDGET_NEUTRAL_SOURCE_RULE
    if source_rule is None and normalized_mode == MATCHED_PLACEBO_NEUTRAL:
        source_rule = C3_MATCHED_PLACEBO_SOURCE_RULE
    if source_rule is None and normalized_mode == INFORMED:
        source_rule = INFORMED
    if source_rule is None:
        raise SourceBindingPlanError(f"{normalized_route} source rule is missing")
    if source_identity is None:
        value = _source_value(source, "source_identity")
        if value is not None:
            source_identity = value
    object_metadata: Mapping[str, object] = metadata or {}
    if isinstance(source, Mapping):
        object_metadata = {**dict(source), **dict(object_metadata)}
    else:
        for name in ("metadata", "provenance"):
            value = _source_value(source, name)
            if isinstance(value, Mapping):
                object_metadata = {**dict(value), **dict(object_metadata)}
    test_split_opened = _source_value(source, "test_split_opened")
    episode_training = _source_value(source, "episode_training")
    if test_split_opened is None:
        test_split_opened = False
    if episode_training is None:
        episode_training = False
    binding = RouteSourceBinding(
        route=normalized_route,
        mode=normalized_mode,
        source_sha256=source_sha256,
        row_budget=row_budget,
        learner_initialization_ids=normalized_initializations,
        learner_initialization_sha256=_expected_collection_sha256(
            "learner_initialization_ids", normalized_initializations
        ),
        learner_config_sha256=normalized_config,
        learner_update_count=learner_update_count,
        common=common,
        source_rule=source_rule,
        authenticated=True,
        source_identity=source_identity,
        metadata=object_metadata,
        test_split_opened=test_split_opened,
        episode_training=episode_training,
    )
    binding.verify()
    return binding


def bind_authenticated_baseline_policy(
    policy: object,
    *,
    policy_id: str | None = None,
    policy_sha256: str | None = None,
    authentication_sha256: str | None = None,
    source_identity: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> BaselinePolicyBinding:
    """Bind an explicit pre-Catfish policy artifact without route inference."""

    if policy is None:
        raise SourceBindingPlanError(
            "BASELINE requires an explicit authenticated policy artifact"
        )
    _authenticate_source_object(policy)
    if isinstance(policy, Mapping):
        _reject_forbidden_tree(policy, field_name="baseline policy")
        if any(
            key in policy
            for key in ("q1", "q2", "q1_source", "q2_source", "routes")
        ):
            raise SourceBindingPlanError(
                "BASELINE cannot be inferred from Q1+Q2 route inputs"
            )
    if policy_id is None:
        value = _source_value(policy, "policy_id")
        if value is None:
            value = _source_value(policy, "artifact_id")
        policy_id = value
    if policy_sha256 is None:
        for name in ("policy_sha256", "artifact_sha256", "source_sha256"):
            value = _source_value(policy, name)
            if value is not None:
                policy_sha256 = value
                break
    if authentication_sha256 is None:
        for name in (
            "authentication_sha256",
            "provider_receipt_sha256",
            "attestation_sha256",
        ):
            value = _source_value(policy, name)
            if value is not None:
                authentication_sha256 = value
                break
    if policy_id is None or policy_sha256 is None or authentication_sha256 is None:
        raise SourceBindingPlanError(
            "BASELINE requires explicit policy, policy hash, and authentication hash"
        )
    if source_identity is None:
        value = _source_value(policy, "source_identity")
        if value is not None:
            source_identity = value
    object_metadata: Mapping[str, object] = metadata or {}
    if isinstance(policy, Mapping):
        object_metadata = {**dict(policy), **dict(object_metadata)}
    explicit = _source_value(policy, "explicit_pre_catfish")
    if explicit is None:
        explicit = True
    authenticated = _source_value(policy, "authenticated")
    if authenticated is None:
        authenticated = True
    test_split_opened = _source_value(policy, "test_split_opened")
    episode_training = _source_value(policy, "episode_training")
    baseline = BaselinePolicyBinding(
        policy_id=policy_id,
        policy_sha256=policy_sha256,
        authentication_sha256=authentication_sha256,
        authenticated=authenticated,
        explicit_pre_catfish=explicit,
        source_kind=BASELINE_SOURCE_KIND,
        source_identity=source_identity,
        metadata=object_metadata,
        test_split_opened=False if test_split_opened is None else test_split_opened,
        episode_training=False if episode_training is None else episode_training,
    )
    baseline.verify()
    return baseline


__all__ = [
    "BASELINE_SOURCE_KIND",
    "C1_CLUSTER_MATCHED_NEUTRAL",
    "C1_CLUSTER_NEUTRAL_SOURCE_RULE",
    "C2_EQUAL_BUDGET_NEUTRAL",
    "C2_EQUAL_BUDGET_NEUTRAL_SOURCE_RULE",
    "C3_MATCHED_PLACEBO_NEUTRAL",
    "C3_MATCHED_PLACEBO_SOURCE_RULE",
    "CLUSTER_MATCHED_NEUTRAL",
    "CommonBinding",
    "EQUAL_BUDGET_NEUTRAL",
    "FiveArmPlan",
    "FiveArmSourceBindingPlan",
    "HEAD_DROP",
    "INFORMED",
    "MATCHED_PLACEBO_NEUTRAL",
    "PRIMARY_ARMS",
    "ROUTES",
    "SOURCE_ABLATION",
    "SCHEMA",
    "SCHEMA_VERSION",
    "SourceBindingPlan",
    "SourceBindingPlanError",
    "StudyBinding",
    "ArmSourceBinding",
    "BaselinePolicyBinding",
    "RouteSourceBinding",
    "V023SourceBindingPlanError",
    "bind_authenticated_baseline_policy",
    "bind_authenticated_route_source",
    "build_five_arm_source_binding_plan",
    "canonical_sha256",
    "make_five_arm_source_binding_plan",
    "plan_five_arm_source_bindings",
]
