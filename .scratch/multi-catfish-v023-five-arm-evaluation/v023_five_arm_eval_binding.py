"""Fail-closed bindings for the future V0.23 five-arm physical evaluation.

This module deliberately stops one layer before simulator execution.  It
binds five *already frozen* policy artifacts to the exact source-ablation
plan and to a common TRAIN-development world grid.  It cannot train a
learner, select a checkpoint from outcomes, open TEST, or reinterpret a
post-hoc head drop as a Catfish ablation.

The important distinction is explicit:

* ``BASELINE`` is the authenticated pre-Catfish MODQN policy;
* ``FULL`` and ``DROP_C1``/``DROP_C2``/``DROP_C3`` are separately trained
  policy bundles whose source bindings come from the five-arm source plan;
* the DROP arms retain three learned routes.  Their named route was trained
  from the declared neutral source; no route is removed at inference time.

The later physical runner can consume :class:`FiveArmEvaluationBinding`
without inventing any policy or science value while the C3 Gate is running.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any


SCHEMA = "multi-catfish-mcrl-v023-five-arm-evaluation-binding-v1"
SOURCE_PLAN_SCHEMA = "multi-catfish-mcrl-v023-source-binding-plan-v2"
SOURCE_ABLATION = "SOURCE_ABLATION"
BASELINE_SOURCE_KIND = "EXPLICIT_AUTHENTICATED_PRE_CATFISH_POLICY"
SPLIT = "TRAIN_DEVELOPMENT"
ARMS: tuple[str, ...] = (
    "FULL",
    "BASELINE",
    "DROP_C1",
    "DROP_C2",
    "DROP_C3",
)
ROUTE_ARMS = frozenset({"FULL", "DROP_C1", "DROP_C2", "DROP_C3"})
CHECKPOINT_EVERY = 100
EXPECTED_ROUTE_MODES: Mapping[str, tuple[str, str, str]] = {
    "FULL": ("INFORMED", "INFORMED", "INFORMED"),
    "DROP_C1": ("CLUSTER_MATCHED_NEUTRAL", "INFORMED", "INFORMED"),
    "DROP_C2": ("INFORMED", "EQUAL_BUDGET_NEUTRAL", "INFORMED"),
    "DROP_C3": ("INFORMED", "INFORMED", "MATCHED_PLACEBO_NEUTRAL"),
}


class FiveArmEvaluationBindingError(ValueError):
    """The physical-evaluation binding is not admissible."""


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise FiveArmEvaluationBindingError(
                    "canonical mappings require string keys"
                )
            result[key] = _jsonable(child)
        return result
    if isinstance(value, (tuple, list)):
        return [_jsonable(child) for child in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise FiveArmEvaluationBindingError(
                "canonical payloads require finite floats"
            )
        return value
    raise FiveArmEvaluationBindingError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_sha256(value: object) -> str:
    try:
        encoded = json.dumps(
            _jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise FiveArmEvaluationBindingError(
            "payload is not finite canonical ASCII JSON"
        ) from error
    return hashlib.sha256(encoded).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise FiveArmEvaluationBindingError(f"{field} must be a lowercase SHA-256")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise FiveArmEvaluationBindingError(f"{field} must be non-empty trimmed text")
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise FiveArmEvaluationBindingError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _sequence(value: object, *, field: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes, Mapping)):
        raise FiveArmEvaluationBindingError(f"{field} must be a sequence")
    try:
        result = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise FiveArmEvaluationBindingError(f"{field} must be a sequence") from error
    if not result:
        raise FiveArmEvaluationBindingError(f"{field} must be non-empty")
    return result


def _arm_block(source_plan: Mapping[str, object], arm: str) -> Mapping[str, object]:
    raw = source_plan.get("arms")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise FiveArmEvaluationBindingError("source plan arms are malformed")
    matches = [
        row
        for row in raw
        if isinstance(row, Mapping) and row.get("arm") == arm
    ]
    if len(matches) != 1:
        raise FiveArmEvaluationBindingError(
            f"source plan must contain exactly one {arm} block"
        )
    return matches[0]


def verify_source_plan_payload(source_plan: Mapping[str, object]) -> str:
    """Verify the serialized output of ``FiveArmSourceBindingPlan.to_dict``."""

    if not isinstance(source_plan, Mapping):
        raise FiveArmEvaluationBindingError("source plan must be a mapping")
    if source_plan.get("schema") != SOURCE_PLAN_SCHEMA:
        raise FiveArmEvaluationBindingError("source plan schema drifted")
    if source_plan.get("schema_version") != 2:
        raise FiveArmEvaluationBindingError("source plan version drifted")
    if source_plan.get("ablation_mode") != SOURCE_ABLATION:
        raise FiveArmEvaluationBindingError(
            "physical DROP arms require source-ablation semantics"
        )
    supplied = _digest(source_plan.get("plan_sha256"), field="source plan digest")
    payload = dict(source_plan)
    payload.pop("plan_sha256", None)
    if canonical_sha256(payload) != supplied:
        raise FiveArmEvaluationBindingError("source plan digest drifted")
    common = source_plan.get("common")
    if not isinstance(common, Mapping):
        raise FiveArmEvaluationBindingError("source plan common binding is malformed")
    split = common.get("split")
    if not isinstance(split, str) or not split.upper().startswith("TRAIN") or "TEST" in split.upper():
        raise FiveArmEvaluationBindingError("source plan common split is not TRAIN-only")
    world_ids = _sequence(common.get("world_ids"), field="common.world_ids")
    training_seeds = _sequence(
        common.get("training_seeds"), field="common.training_seeds"
    )
    if len(set(world_ids)) != len(world_ids):
        raise FiveArmEvaluationBindingError("common world IDs are not unique")
    if any(type(seed) is not int or seed < 0 for seed in training_seeds):
        raise FiveArmEvaluationBindingError("common training seeds are malformed")
    if len(set(training_seeds)) != len(training_seeds):
        raise FiveArmEvaluationBindingError("common training seeds are not unique")
    if common.get("world_sha256") != canonical_sha256({"world_ids": list(world_ids)}):
        raise FiveArmEvaluationBindingError("common world digest drifted")
    if common.get("seed_sha256") != canonical_sha256(
        {"training_seeds": list(training_seeds)}
    ):
        raise FiveArmEvaluationBindingError("common seed digest drifted")
    arm_names = tuple(
        row.get("arm") if isinstance(row, Mapping) else None
        for row in source_plan.get("arms", ())  # type: ignore[arg-type]
    )
    if arm_names != ARMS:
        raise FiveArmEvaluationBindingError("source plan arm order or coverage drifted")

    baseline = _arm_block(source_plan, "BASELINE")
    baseline_policy = baseline.get("baseline")
    if not isinstance(baseline_policy, Mapping):
        raise FiveArmEvaluationBindingError("BASELINE lacks an explicit policy binding")
    if baseline_policy.get("source_kind") != BASELINE_SOURCE_KIND:
        raise FiveArmEvaluationBindingError(
            "BASELINE is not the explicit pre-Catfish policy"
        )
    if baseline.get("routes") not in ([], ()):
        raise FiveArmEvaluationBindingError("BASELINE cannot carry C1/C2/C3 sources")
    baseline_checkpoint = _digest(
        baseline_policy.get("policy_sha256"), field="baseline policy digest"
    )
    baseline_authentication = _digest(
        baseline_policy.get("authentication_sha256"),
        field="baseline authentication digest",
    )
    if baseline_checkpoint == baseline_authentication:
        raise FiveArmEvaluationBindingError(
            "baseline policy and authentication digests must be distinct"
        )
    route_blocks: dict[str, dict[str, Mapping[str, object]]] = {}
    for arm in ROUTE_ARMS:
        block = _arm_block(source_plan, arm)
        if block.get("ablation_mode") != SOURCE_ABLATION:
            raise FiveArmEvaluationBindingError(f"{arm} is not a source ablation")
        routes = block.get("routes")
        if not isinstance(routes, Sequence) or isinstance(routes, (str, bytes)):
            raise FiveArmEvaluationBindingError(f"{arm} routes are malformed")
        if tuple(
            route.get("route") if isinstance(route, Mapping) else None
            for route in routes
        ) != ("C1", "C2", "C3"):
            raise FiveArmEvaluationBindingError(
                f"{arm} must retain C1, C2, and C3 policy routes"
            )
        actual_modes = tuple(
            route.get("mode") if isinstance(route, Mapping) else None
            for route in routes
        )
        if actual_modes != EXPECTED_ROUTE_MODES[arm]:
            raise FiveArmEvaluationBindingError(
                f"{arm} route modes do not match the declared source ablation"
            )
        indexed: dict[str, Mapping[str, object]] = {}
        for index, route in enumerate(routes):
            assert isinstance(route, Mapping)
            route_name = str(route["route"])
            _digest(
                route.get("source_sha256"),
                field=f"{arm}.routes[{index}].source_sha256",
            )
            _exact_int(
                route.get("row_budget"),
                field=f"{arm}.{route_name}.row_budget",
                minimum=1,
            )
            initialization_ids = _sequence(
                route.get("learner_initialization_ids"),
                field=f"{arm}.{route_name}.learner_initialization_ids",
            )
            if len(set(initialization_ids)) != len(initialization_ids):
                raise FiveArmEvaluationBindingError(
                    f"{arm}.{route_name} learner initializations are not unique"
                )
            if route.get("learner_initialization_count") != len(initialization_ids):
                raise FiveArmEvaluationBindingError(
                    f"{arm}.{route_name} initialization count drifted"
                )
            expected_initialization_sha = canonical_sha256(
                {"learner_initialization_ids": list(initialization_ids)}
            )
            if route.get("learner_initialization_sha256") != expected_initialization_sha:
                raise FiveArmEvaluationBindingError(
                    f"{arm}.{route_name} initialization digest drifted"
                )
            _digest(
                route.get("learner_config_sha256"),
                field=f"{arm}.{route_name}.learner_config_sha256",
            )
            _exact_int(
                route.get("learner_update_count"),
                field=f"{arm}.{route_name}.learner_update_count",
                minimum=1,
            )
            if route.get("common") != common:
                raise FiveArmEvaluationBindingError(
                    f"{arm}.{route_name} source-world binding drifted"
                )
            indexed[route_name] = route
        route_blocks[arm] = indexed

    full = route_blocks["FULL"]
    for route_name, drop_arm in (
        ("C1", "DROP_C1"),
        ("C2", "DROP_C2"),
        ("C3", "DROP_C3"),
    ):
        neutral = route_blocks[drop_arm][route_name]
        informed = full[route_name]
        for field_name in (
            "row_budget",
            "learner_initialization_ids",
            "learner_initialization_count",
            "learner_initialization_sha256",
            "learner_config_sha256",
            "learner_update_count",
            "common",
        ):
            if neutral.get(field_name) != informed.get(field_name):
                raise FiveArmEvaluationBindingError(
                    f"{route_name} informed/neutral learner or source budget drifted"
                )
        if neutral.get("source_sha256") == informed.get("source_sha256"):
            raise FiveArmEvaluationBindingError(
                f"{route_name} neutral source aliases its informed source"
            )
        for other_route in {"C1", "C2", "C3"} - {route_name}:
            if route_blocks[drop_arm][other_route] != full[other_route]:
                raise FiveArmEvaluationBindingError(
                    f"{drop_arm} changed non-ablated route {other_route}"
                )
    return supplied


@dataclass(frozen=True, slots=True)
class FrozenPolicyBinding:
    """One already trained, immutable policy used by one evaluation arm."""

    arm: str
    policy_id: str
    policy_family: str
    checkpoint_sha256: str
    authentication_sha256: str
    source_plan_sha256: str
    source_arm_sha256: str
    fixed_policy: bool = True
    checkpoint_selected_from_outcome: bool = False
    head_drop: bool = False
    test_split_opened: bool = False
    episode_training: bool = False

    def verify(self, source_plan: Mapping[str, object]) -> None:
        if self.arm not in ARMS:
            raise FiveArmEvaluationBindingError(f"unknown arm {self.arm!r}")
        _text(self.policy_id, field=f"{self.arm}.policy_id")
        _text(self.policy_family, field=f"{self.arm}.policy_family")
        checkpoint = _digest(
            self.checkpoint_sha256, field=f"{self.arm}.checkpoint_sha256"
        )
        authentication = _digest(
            self.authentication_sha256,
            field=f"{self.arm}.authentication_sha256",
        )
        if checkpoint == authentication:
            raise FiveArmEvaluationBindingError(
                f"{self.arm} checkpoint and authentication receipts must be distinct"
            )
        plan_digest = verify_source_plan_payload(source_plan)
        if self.source_plan_sha256 != plan_digest:
            raise FiveArmEvaluationBindingError(
                f"{self.arm} is not bound to the admitted source plan"
            )
        block = _arm_block(source_plan, self.arm)
        expected_block = canonical_sha256(block)
        if self.source_arm_sha256 != expected_block:
            raise FiveArmEvaluationBindingError(
                f"{self.arm} source-arm binding drifted"
            )
        for field_name, value in (
            ("fixed_policy", self.fixed_policy),
            ("checkpoint_selected_from_outcome", self.checkpoint_selected_from_outcome),
            ("head_drop", self.head_drop),
            ("test_split_opened", self.test_split_opened),
            ("episode_training", self.episode_training),
        ):
            if type(value) is not bool:
                raise FiveArmEvaluationBindingError(
                    f"{self.arm}.{field_name} must be an exact boolean"
                )
        if not self.fixed_policy:
            raise FiveArmEvaluationBindingError(f"{self.arm} policy is not frozen")
        if self.checkpoint_selected_from_outcome:
            raise FiveArmEvaluationBindingError(
                f"{self.arm} checkpoint was selected from evaluation outcomes"
            )
        if self.head_drop:
            raise FiveArmEvaluationBindingError(
                f"{self.arm} uses a forbidden post-hoc head drop"
            )
        if self.test_split_opened:
            raise FiveArmEvaluationBindingError(f"{self.arm} crossed TEST")
        if self.episode_training:
            raise FiveArmEvaluationBindingError(
                f"{self.arm} performed episode training"
            )
        if self.arm == "BASELINE":
            baseline = _arm_block(source_plan, "BASELINE").get("baseline")
            assert isinstance(baseline, Mapping)
            if checkpoint != baseline.get("policy_sha256"):
                raise FiveArmEvaluationBindingError(
                    "BASELINE checkpoint is not the authenticated pre-Catfish policy"
                )
            if "MODQN" not in self.policy_family.upper():
                raise FiveArmEvaluationBindingError(
                    "BASELINE policy family must identify MODQN"
                )
        elif "PRE_CATFISH" in self.policy_family.upper():
            raise FiveArmEvaluationBindingError(
                f"{self.arm} cannot masquerade as the pre-Catfish baseline"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "policy_id": self.policy_id,
            "policy_family": self.policy_family,
            "checkpoint_sha256": self.checkpoint_sha256,
            "authentication_sha256": self.authentication_sha256,
            "source_plan_sha256": self.source_plan_sha256,
            "source_arm_sha256": self.source_arm_sha256,
            "fixed_policy": self.fixed_policy,
            "checkpoint_selected_from_outcome": self.checkpoint_selected_from_outcome,
            "head_drop": self.head_drop,
            "test_split_opened": self.test_split_opened,
            "episode_training": self.episode_training,
        }


@dataclass(frozen=True, slots=True)
class EvaluationWorldBinding:
    episode_index: int
    world_id: str
    world_seed: int
    field_root_digest: str

    def verify(self) -> None:
        _exact_int(self.episode_index, field="episode_index", minimum=1)
        _text(self.world_id, field="world_id")
        if "TEST" in self.world_id.upper():
            raise FiveArmEvaluationBindingError("TEST world identifiers are closed")
        _exact_int(self.world_seed, field="world_seed", minimum=0)
        _digest(self.field_root_digest, field="field_root_digest")

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "episode_index": self.episode_index,
            "world_id": self.world_id,
            "world_seed": self.world_seed,
            "field_root_digest": self.field_root_digest,
        }


@dataclass(frozen=True, slots=True)
class FiveArmEvaluationBinding:
    """Immutable handoff from learned policy artifacts to physical evaluation."""

    source_plan: Mapping[str, object]
    policies: tuple[FrozenPolicyBinding, ...]
    worlds: tuple[EvaluationWorldBinding, ...]
    evaluation_contract_sha256: str
    checkpoint_every: int = CHECKPOINT_EVERY
    split: str = SPLIT
    schema: str = SCHEMA

    def verify(self) -> str:
        if self.schema != SCHEMA:
            raise FiveArmEvaluationBindingError("evaluation-binding schema drifted")
        if self.split != SPLIT or "TEST" in self.split.upper():
            raise FiveArmEvaluationBindingError(
                "five-arm preparation must remain TRAIN-development"
            )
        if self.checkpoint_every != CHECKPOINT_EVERY:
            raise FiveArmEvaluationBindingError(
                "physical checkpoints must be emitted every 100 episodes"
            )
        _digest(
            self.evaluation_contract_sha256,
            field="evaluation_contract_sha256",
        )
        source_plan_sha = verify_source_plan_payload(self.source_plan)
        if tuple(policy.arm for policy in self.policies) != ARMS:
            raise FiveArmEvaluationBindingError(
                "policy arm order or coverage is not the fixed five-arm order"
            )
        if not self.worlds:
            raise FiveArmEvaluationBindingError("evaluation world grid is empty")
        if len(self.worlds) % CHECKPOINT_EVERY != 0:
            raise FiveArmEvaluationBindingError(
                "episode budget must end on a 100-episode checkpoint boundary"
            )
        if tuple(world.episode_index for world in self.worlds) != tuple(
            range(1, len(self.worlds) + 1)
        ):
            raise FiveArmEvaluationBindingError(
                "world episode indices must be contiguous from one"
            )
        world_ids: set[str] = set()
        world_seeds: set[int] = set()
        for world in self.worlds:
            world.verify()
            if world.world_id in world_ids or world.world_seed in world_seeds:
                raise FiveArmEvaluationBindingError(
                    "evaluation worlds and seeds must be unique"
                )
            world_ids.add(world.world_id)
            world_seeds.add(world.world_seed)
        checkpoint_hashes: set[str] = set()
        for policy in self.policies:
            policy.verify(self.source_plan)
            if policy.checkpoint_sha256 in checkpoint_hashes:
                raise FiveArmEvaluationBindingError(
                    "distinct evaluation arms cannot alias one checkpoint"
                )
            checkpoint_hashes.add(policy.checkpoint_sha256)
        payload = {
            "schema": self.schema,
            "split": self.split,
            "source_plan_sha256": source_plan_sha,
            "evaluation_contract_sha256": self.evaluation_contract_sha256,
            "checkpoint_every": self.checkpoint_every,
            "policies": [policy.to_dict() for policy in self.policies],
            "worlds": [world.to_dict() for world in self.worlds],
            "learner_update": False,
            "episode_training": False,
            "test_split_opened": False,
            "outcome_selected_checkpoint": False,
            "head_drop": False,
        }
        return canonical_sha256(payload)

    def to_dict(self) -> dict[str, object]:
        binding_sha256 = self.verify()
        return {
            "schema": self.schema,
            "split": self.split,
            "source_plan_sha256": self.source_plan["plan_sha256"],
            "evaluation_contract_sha256": self.evaluation_contract_sha256,
            "checkpoint_every": self.checkpoint_every,
            "episode_budget": len(self.worlds),
            "policies": [policy.to_dict() for policy in self.policies],
            "worlds": [world.to_dict() for world in self.worlds],
            "learner_update": False,
            "episode_training": False,
            "test_split_opened": False,
            "outcome_selected_checkpoint": False,
            "head_drop": False,
            "binding_sha256": binding_sha256,
        }


def bind_five_arm_evaluation(
    *,
    source_plan: Mapping[str, object],
    policies: Sequence[FrozenPolicyBinding],
    worlds: Sequence[EvaluationWorldBinding],
    evaluation_contract_sha256: str,
) -> FiveArmEvaluationBinding:
    """Build and verify the pre-execution five-arm binding."""

    binding = FiveArmEvaluationBinding(
        source_plan=dict(source_plan),
        policies=tuple(policies),
        worlds=tuple(worlds),
        evaluation_contract_sha256=evaluation_contract_sha256,
    )
    binding.verify()
    return binding


__all__ = [
    "ARMS",
    "CHECKPOINT_EVERY",
    "EvaluationWorldBinding",
    "FiveArmEvaluationBinding",
    "FiveArmEvaluationBindingError",
    "FrozenPolicyBinding",
    "bind_five_arm_evaluation",
    "canonical_sha256",
    "verify_source_plan_payload",
]
