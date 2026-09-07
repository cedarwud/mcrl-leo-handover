"""Held-out Main-only evaluation for a trained V0.3 three-Q policy."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

import numpy as np

from ..algorithms.ee_axis_pairwise import EEAxisPairwiseTrainer
from ..env.keyed_fading import KeyedFadingField
from ..errors import MCRLContractError
from .ee_axis_state import EE_AXIS_STATE_DIM, encode_ee_axis_state
from .trainer_env import TrainerEnvironment


EE_AXIS_EVALUATION_SCHEMA = "multi-catfish-mcrl-v03-heldout-ee-evaluation-v1"


class EEAxisEvaluationError(MCRLContractError):
    """A held-out episode violates the V0.3 deployment/evaluation boundary."""


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class EEAxisEpisodeEvaluation:
    """One fresh-seed ratio-of-sums endpoint receipt."""

    policy_label: str
    evaluation_seed: int
    fading_field_sha256: str
    steps: int
    users: int
    decision_count: int
    total_bits: float
    total_energy_j: float
    ratio_of_sums_ee_bits_per_j: float
    served_user_steps: int
    served_fraction: float
    outage_fraction: float
    action_trace_sha256: str
    schema: str = EE_AXIS_EVALUATION_SCHEMA

    def verify(self) -> str:
        if self.schema != EE_AXIS_EVALUATION_SCHEMA:
            raise EEAxisEvaluationError("evaluation schema is stale")
        if not isinstance(self.policy_label, str) or not self.policy_label.strip():
            raise EEAxisEvaluationError("policy_label must be nonempty")
        for field in ("evaluation_seed", "steps", "users", "decision_count", "served_user_steps"):
            value = getattr(self, field)
            minimum = 0 if field in ("evaluation_seed", "served_user_steps") else 1
            if type(value) is not int or value < minimum:
                raise EEAxisEvaluationError(f"{field} is invalid")
        for field in ("fading_field_sha256", "action_trace_sha256"):
            value = getattr(self, field)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise EEAxisEvaluationError(f"{field} must be lowercase SHA-256")
        if self.decision_count != self.steps * self.users:
            raise EEAxisEvaluationError("decision_count must equal steps times users")
        if not math.isfinite(self.total_bits) or self.total_bits < 0.0:
            raise EEAxisEvaluationError("total_bits must be finite and nonnegative")
        if not math.isfinite(self.total_energy_j) or self.total_energy_j < 0.0:
            raise EEAxisEvaluationError("total_energy_j must be finite and nonnegative")
        if self.total_energy_j == 0.0:
            if self.total_bits != 0.0:
                raise EEAxisEvaluationError("positive bits with zero total energy is invalid")
            expected_ee = 0.0
        else:
            expected_ee = self.total_bits / self.total_energy_j
        if not math.isclose(
            self.ratio_of_sums_ee_bits_per_j,
            expected_ee,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise EEAxisEvaluationError("reported EE is not ratio of sums")
        if not 0 <= self.served_user_steps <= self.decision_count:
            raise EEAxisEvaluationError("served_user_steps is outside decision count")
        expected_served = self.served_user_steps / self.decision_count
        if not math.isclose(self.served_fraction, expected_served, rel_tol=0.0, abs_tol=1e-15):
            raise EEAxisEvaluationError("served_fraction disagrees with counts")
        if not math.isclose(self.outage_fraction, 1.0 - expected_served, rel_tol=0.0, abs_tol=1e-15):
            raise EEAxisEvaluationError("outage_fraction disagrees with service")
        return _canonical_sha256(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "policy_label": self.policy_label,
            "evaluation_seed": self.evaluation_seed,
            "fading_field_sha256": self.fading_field_sha256,
            "steps": self.steps,
            "users": self.users,
            "decision_count": self.decision_count,
            "total_bits_hex": float(self.total_bits).hex(),
            "total_energy_j_hex": float(self.total_energy_j).hex(),
            "ratio_of_sums_ee_bits_per_j_hex": float(
                self.ratio_of_sums_ee_bits_per_j
            ).hex(),
            "served_user_steps": self.served_user_steps,
            "served_fraction_hex": float(self.served_fraction).hex(),
            "outage_fraction_hex": float(self.outage_fraction).hex(),
            "action_trace_sha256": self.action_trace_sha256,
        }


def evaluate_ee_axis_episode(
    trainer: EEAxisPairwiseTrainer,
    environment: TrainerEnvironment,
    *,
    env_rng: np.random.Generator,
    mobility_rng: np.random.Generator,
    evaluation_seed: int,
    policy_label: str,
) -> EEAxisEpisodeEvaluation:
    """Execute only the deployed masked argmax of Q1+Q2+Q3."""

    if not isinstance(trainer, EEAxisPairwiseTrainer):
        raise EEAxisEvaluationError("trainer must be EEAxisPairwiseTrainer")
    if trainer.config.state_dim != EE_AXIS_STATE_DIM:
        raise EEAxisEvaluationError("trainer does not use the current 228-D state")
    if not isinstance(environment, TrainerEnvironment):
        raise EEAxisEvaluationError("environment must be TrainerEnvironment")
    if not isinstance(env_rng, np.random.Generator) or not isinstance(
        mobility_rng, np.random.Generator
    ):
        raise EEAxisEvaluationError("evaluation requires explicit NumPy generators")
    field = getattr(environment.environment, "_fading_field", None)
    if not isinstance(field, KeyedFadingField):
        raise EEAxisEvaluationError("held-out evaluation requires keyed common fading")
    if environment.environment._started:
        raise EEAxisEvaluationError("held-out evaluation requires a fresh environment")
    if type(evaluation_seed) is not int or evaluation_seed < 0:
        raise EEAxisEvaluationError("evaluation_seed must be nonnegative")
    if not isinstance(policy_label, str) or not policy_label.strip():
        raise EEAxisEvaluationError("policy_label must be nonempty")

    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    if not math.isfinite(interval_s) or interval_s <= 0.0:
        raise EEAxisEvaluationError("evaluation interval must be positive")
    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    steps = 0
    action_trace: list[list[int]] = []
    while True:
        state = encode_ee_axis_state(environment.environment, observation)
        actions = trainer.select_greedy_actions(
            state.state_matrix,
            state.action_masks,
        )
        action_trace.append([int(value) for value in actions.tolist()])
        result = environment.step(actions, env_rng)
        outcome = environment.last_outcome
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        if rates.shape != (environment.num_users,) or not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
            raise EEAxisEvaluationError("evaluation rates are malformed")
        system_power = float(outcome.system_power_w)
        if not math.isfinite(system_power) or system_power < 0.0:
            raise EEAxisEvaluationError("evaluation system power is invalid")
        system_rate = float(math.fsum(float(value) for value in rates))
        if system_power == 0.0 and system_rate > 0.0:
            raise EEAxisEvaluationError(
                "positive evaluation throughput with zero system power is invalid"
            )
        total_bits += system_rate * interval_s
        total_energy += system_power * interval_s
        served_user_steps += int(outcome.resolution.served_count)
        steps += 1
        if result.done:
            break
        observation = outcome.observation
    decisions = steps * environment.num_users
    served_fraction = served_user_steps / decisions
    action_trace_sha256 = _canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v03-action-trace-v1",
            "policy_label": policy_label,
            "evaluation_seed": evaluation_seed,
            "actions": action_trace,
        }
    )
    receipt = EEAxisEpisodeEvaluation(
        policy_label=policy_label,
        evaluation_seed=evaluation_seed,
        fading_field_sha256=field.root_digest,
        steps=steps,
        users=environment.num_users,
        decision_count=decisions,
        total_bits=total_bits,
        total_energy_j=total_energy,
        ratio_of_sums_ee_bits_per_j=(
            total_bits / total_energy if total_energy > 0.0 else 0.0
        ),
        served_user_steps=served_user_steps,
        served_fraction=served_fraction,
        outage_fraction=1.0 - served_fraction,
        action_trace_sha256=action_trace_sha256,
    )
    receipt.verify()
    return receipt


__all__ = [
    "EE_AXIS_EVALUATION_SCHEMA",
    "EEAxisEpisodeEvaluation",
    "EEAxisEvaluationError",
    "evaluate_ee_axis_episode",
]
