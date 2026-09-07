"""Pure receipt validation and aggregation for the V0.23 five-arm evaluator.

No simulator or learner is imported here.  The eventual runtime emits one
receipt per arm and physical world; this module verifies matched-world and
policy provenance, computes ratio-of-sums EE, and builds deterministic
100-episode checkpoint payloads.  It intentionally makes no scientific
PASS/FAIL decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import math
from typing import Any

from v023_five_arm_eval_binding import (
    ARMS,
    CHECKPOINT_EVERY,
    EvaluationWorldBinding,
    FiveArmEvaluationBinding,
    FiveArmEvaluationBindingError,
    FrozenPolicyBinding,
    canonical_sha256,
)


RECEIPT_SCHEMA = "multi-catfish-mcrl-v023-five-arm-episode-receipt-v1"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v023-five-arm-evaluation-checkpoint-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v023-five-arm-evaluation-result-v1"


class FiveArmEvaluationResultError(ValueError):
    """A physical receipt set does not match its frozen binding."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise FiveArmEvaluationResultError(f"{field} must be a lowercase SHA-256")
    return value


def _finite(value: object, *, field: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FiveArmEvaluationResultError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise FiveArmEvaluationResultError(
            f"{field} must be finite and >= {minimum}"
        )
    return result


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise FiveArmEvaluationResultError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


@dataclass(frozen=True, slots=True)
class FiveArmEpisodeReceipt:
    schema: str
    arm: str
    episode_index: int
    world_id: str
    world_seed: int
    field_root_digest: str
    initial_world_sha256: str
    policy_checkpoint_sha256: str
    source_arm_sha256: str
    evaluation_binding_sha256: str
    action_trace_sha256: str
    total_bits: float
    total_energy_j: float
    ratio_of_sums_ee_bits_per_j: float
    served_user_steps: int
    service_opportunities: int
    service_fraction: float
    fixed_policy: bool = True
    learner_update: bool = False
    episode_training: bool = False
    test_split_opened: bool = False
    head_drop: bool = False

    def verify(
        self,
        *,
        world: EvaluationWorldBinding,
        policy: FrozenPolicyBinding,
        binding_sha256: str,
    ) -> None:
        if self.schema != RECEIPT_SCHEMA:
            raise FiveArmEvaluationResultError("episode receipt schema drifted")
        if self.arm != policy.arm or self.arm not in ARMS:
            raise FiveArmEvaluationResultError("episode arm/policy binding drifted")
        if self.episode_index != world.episode_index:
            raise FiveArmEvaluationResultError("episode index drifted")
        if self.world_id != world.world_id or self.world_seed != world.world_seed:
            raise FiveArmEvaluationResultError("episode world identity drifted")
        if self.field_root_digest != world.field_root_digest:
            raise FiveArmEvaluationResultError("common keyed field root drifted")
        for field_name in (
            "field_root_digest",
            "initial_world_sha256",
            "policy_checkpoint_sha256",
            "source_arm_sha256",
            "evaluation_binding_sha256",
            "action_trace_sha256",
        ):
            _digest(getattr(self, field_name), field=field_name)
        if self.policy_checkpoint_sha256 != policy.checkpoint_sha256:
            raise FiveArmEvaluationResultError("policy checkpoint provenance drifted")
        if self.source_arm_sha256 != policy.source_arm_sha256:
            raise FiveArmEvaluationResultError("source-arm provenance drifted")
        if self.evaluation_binding_sha256 != binding_sha256:
            raise FiveArmEvaluationResultError("evaluation binding provenance drifted")
        bits = _finite(self.total_bits, field="total_bits")
        energy = _finite(self.total_energy_j, field="total_energy_j")
        if energy <= 0.0:
            raise FiveArmEvaluationResultError("total_energy_j must be positive")
        ee = _finite(
            self.ratio_of_sums_ee_bits_per_j,
            field="ratio_of_sums_ee_bits_per_j",
        )
        if not _close(ee, bits / energy):
            raise FiveArmEvaluationResultError(
                "episode EE is not the physical bits/energy ratio"
            )
        served = _exact_int(
            self.served_user_steps, field="served_user_steps", minimum=0
        )
        opportunities = _exact_int(
            self.service_opportunities,
            field="service_opportunities",
            minimum=1,
        )
        if served > opportunities:
            raise FiveArmEvaluationResultError(
                "served_user_steps exceeds service_opportunities"
            )
        service = _finite(self.service_fraction, field="service_fraction")
        if service > 1.0 or not _close(service, served / opportunities):
            raise FiveArmEvaluationResultError("service fraction is inconsistent")
        flags = {
            "fixed_policy": self.fixed_policy,
            "learner_update": self.learner_update,
            "episode_training": self.episode_training,
            "test_split_opened": self.test_split_opened,
            "head_drop": self.head_drop,
        }
        if any(type(value) is not bool for value in flags.values()):
            raise FiveArmEvaluationResultError("receipt flags must be exact booleans")
        if not self.fixed_policy:
            raise FiveArmEvaluationResultError("receipt is not fixed-policy evaluation")
        for field_name in (
            "learner_update",
            "episode_training",
            "test_split_opened",
            "head_drop",
        ):
            if getattr(self, field_name):
                raise FiveArmEvaluationResultError(
                    f"receipt crossed forbidden boundary: {field_name}"
                )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _binding_parts(
    binding: FiveArmEvaluationBinding,
) -> tuple[str, dict[str, FrozenPolicyBinding], dict[int, EvaluationWorldBinding]]:
    if not isinstance(binding, FiveArmEvaluationBinding):
        raise FiveArmEvaluationResultError("binding has the wrong type")
    try:
        binding_sha = binding.verify()
    except FiveArmEvaluationBindingError as error:
        raise FiveArmEvaluationResultError("evaluation binding failed verification") from error
    policies = {policy.arm: policy for policy in binding.policies}
    worlds = {world.episode_index: world for world in binding.worlds}
    return binding_sha, policies, worlds


def _verify_receipts(
    binding: FiveArmEvaluationBinding,
    receipts: Sequence[FiveArmEpisodeReceipt],
    *,
    through_episode: int,
) -> list[FiveArmEpisodeReceipt]:
    binding_sha, policies, worlds = _binding_parts(binding)
    completed = _exact_int(
        through_episode, field="through_episode", minimum=1
    )
    if completed % CHECKPOINT_EVERY != 0:
        raise FiveArmEvaluationResultError(
            "through_episode must be on the 100-episode checkpoint cadence"
        )
    if completed > len(binding.worlds):
        raise FiveArmEvaluationResultError("through_episode exceeds the world grid")
    rows = list(receipts)
    if len(rows) != completed * len(ARMS):
        raise FiveArmEvaluationResultError("receipt count does not cover five arms")
    index: dict[tuple[int, str], FiveArmEpisodeReceipt] = {}
    for row in rows:
        if not isinstance(row, FiveArmEpisodeReceipt):
            raise FiveArmEvaluationResultError("receipt has the wrong type")
        key = (row.episode_index, row.arm)
        if key in index:
            raise FiveArmEvaluationResultError("duplicate episode/arm receipt")
        world = worlds.get(row.episode_index)
        policy = policies.get(row.arm)
        if world is None or policy is None or row.episode_index > completed:
            raise FiveArmEvaluationResultError("receipt falls outside the bound prefix")
        row.verify(world=world, policy=policy, binding_sha256=binding_sha)
        index[key] = row
    ordered: list[FiveArmEpisodeReceipt] = []
    for episode in range(1, completed + 1):
        group = [index.get((episode, arm)) for arm in ARMS]
        if any(row is None for row in group):
            raise FiveArmEvaluationResultError("one world lacks complete five-arm coverage")
        exact = [row for row in group if row is not None]
        for field_name in (
            "world_id",
            "world_seed",
            "field_root_digest",
            "initial_world_sha256",
            "service_opportunities",
        ):
            if len({getattr(row, field_name) for row in exact}) != 1:
                raise FiveArmEvaluationResultError(
                    f"paired arms disagree on {field_name}"
                )
        ordered.extend(exact)
    return ordered


def _pool(rows: Sequence[FiveArmEpisodeReceipt]) -> dict[str, object]:
    if not rows:
        raise FiveArmEvaluationResultError("cannot pool an empty arm")
    bits = math.fsum(row.total_bits for row in rows)
    energy = math.fsum(row.total_energy_j for row in rows)
    served = sum(row.served_user_steps for row in rows)
    opportunities = sum(row.service_opportunities for row in rows)
    if energy <= 0.0 or opportunities <= 0:
        raise FiveArmEvaluationResultError("pooled denominators must be positive")
    return {
        "arm": rows[0].arm,
        "episodes": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
    }


def _aggregate_verified(
    rows: Sequence[FiveArmEpisodeReceipt],
) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, float]]]:
    pooled = {
        arm: _pool([row for row in rows if row.arm == arm]) for arm in ARMS
    }
    full = float(pooled["FULL"]["ratio_of_sums_ee_bits_per_j"])
    comparisons: dict[str, dict[str, float]] = {}
    for comparator in ("BASELINE", "DROP_C1", "DROP_C2", "DROP_C3"):
        other = float(pooled[comparator]["ratio_of_sums_ee_bits_per_j"])
        if other <= 0.0:
            raise FiveArmEvaluationResultError(
                f"{comparator} pooled EE must be positive"
            )
        comparisons[f"FULL_VS_{comparator}"] = {
            "full_ee_bits_per_j": full,
            "comparator_ee_bits_per_j": other,
            "relative_difference_percent": (full / other - 1.0) * 100.0,
            "full_minus_comparator_served_user_steps": float(
                int(pooled["FULL"]["served_user_steps"])
                - int(pooled[comparator]["served_user_steps"])
            ),
        }
    return pooled, comparisons


def build_checkpoint_payload(
    *,
    binding: FiveArmEvaluationBinding,
    receipts: Sequence[FiveArmEpisodeReceipt],
    through_episode: int,
) -> dict[str, object]:
    """Validate one complete prefix and produce a descriptive checkpoint."""

    rows = _verify_receipts(
        binding, receipts, through_episode=through_episode
    )
    pooled, comparisons = _aggregate_verified(rows)
    binding_sha = binding.verify()
    payload: dict[str, object] = {
        "schema": CHECKPOINT_SCHEMA,
        "status": "CHECKPOINTED",
        "completed_episode": through_episode,
        "planned_episodes": len(binding.worlds),
        "checkpoint_every": CHECKPOINT_EVERY,
        "arms": list(ARMS),
        "evaluation_binding_sha256": binding_sha,
        "receipt_count": len(rows),
        "receipt_set_sha256": canonical_sha256([row.to_dict() for row in rows]),
        "pooled_by_arm": pooled,
        "comparisons": comparisons,
        "scientific_decision": None,
        "learner_update": False,
        "episode_training": False,
        "test_split_opened": False,
        "outcome_selected_checkpoint": False,
        "head_drop": False,
    }
    payload["checkpoint_sha256"] = canonical_sha256(payload)
    return payload


def build_result_payload(
    *,
    binding: FiveArmEvaluationBinding,
    receipts: Sequence[FiveArmEpisodeReceipt],
) -> dict[str, object]:
    """Build a complete descriptive result; adjudication remains external."""

    checkpoint = build_checkpoint_payload(
        binding=binding,
        receipts=receipts,
        through_episode=len(binding.worlds),
    )
    payload = dict(checkpoint)
    payload["schema"] = RESULT_SCHEMA
    payload["status"] = "COMPLETE_UNADJUDICATED"
    payload.pop("checkpoint_sha256", None)
    payload["result_sha256"] = canonical_sha256(payload)
    return payload


__all__ = [
    "CHECKPOINT_SCHEMA",
    "FiveArmEpisodeReceipt",
    "FiveArmEvaluationResultError",
    "RECEIPT_SCHEMA",
    "RESULT_SCHEMA",
    "build_checkpoint_payload",
    "build_result_payload",
]
