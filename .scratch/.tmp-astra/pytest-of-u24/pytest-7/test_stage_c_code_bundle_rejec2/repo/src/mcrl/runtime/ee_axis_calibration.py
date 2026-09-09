"""TRAIN-only common-unit calibration for the V0.3 pairwise learner."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from ..algorithms.ee_axis_pairwise import EEAxisPairwiseConfig
from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_state import EE_AXIS_STATE_DIM


EE_AXIS_CALIBRATION_SCHEMA = "multi-catfish-mcrl-v03-pilot-calibration-v1"


class EEAxisCalibrationError(MCRLContractError):
    """The shared lambda/kappa calibration is malformed or inconsistent."""


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _finite_positive(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EEAxisCalibrationError(f"{field} must be a positive finite number")
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0.0:
        raise EEAxisCalibrationError(f"{field} must be a positive finite number")
    return converted


@dataclass(frozen=True)
class EEAxisPilotCalibration:
    """One frozen Main-reference window shared by all three routes."""

    calibration_seed: int
    useful_bits: float
    energy_j: float
    steps: int
    users: int
    decision_count: int
    lambda_bits_per_j: float
    kappa_bits: float
    beta: float
    loss_weights: tuple[float, float, float]
    schema: str = EE_AXIS_CALIBRATION_SCHEMA

    def verify(self) -> str:
        if self.schema != EE_AXIS_CALIBRATION_SCHEMA:
            raise EEAxisCalibrationError("calibration schema is stale")
        for field in ("calibration_seed", "steps", "users", "decision_count"):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise EEAxisCalibrationError(f"{field} must be a positive exact integer")
        useful = _finite_positive(self.useful_bits, field="useful_bits")
        energy = _finite_positive(self.energy_j, field="energy_j")
        multiplier = _finite_positive(self.lambda_bits_per_j, field="lambda_bits_per_j")
        scale = _finite_positive(self.kappa_bits, field="kappa_bits")
        if self.decision_count != self.steps * self.users:
            raise EEAxisCalibrationError("decision_count must equal steps times users")
        if not math.isclose(multiplier, useful / energy, rel_tol=0.0, abs_tol=1e-9):
            raise EEAxisCalibrationError("lambda does not equal Main bits over energy")
        if not math.isclose(scale, useful / self.decision_count, rel_tol=0.0, abs_tol=1e-9):
            raise EEAxisCalibrationError("kappa does not equal Main bits per decision")
        if not math.isfinite(self.beta) or self.beta < 0.0:
            raise EEAxisCalibrationError("beta must be finite and nonnegative")
        if len(self.loss_weights) != 3 or any(
            not math.isfinite(value) or value <= 0.0 for value in self.loss_weights
        ):
            raise EEAxisCalibrationError("loss_weights must contain three positive values")
        return _canonical_sha256(self.as_payload())

    def as_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "calibration_seed": self.calibration_seed,
            "useful_bits_hex": float(self.useful_bits).hex(),
            "energy_j_hex": float(self.energy_j).hex(),
            "steps": self.steps,
            "users": self.users,
            "decision_count": self.decision_count,
            "lambda_bits_per_j_hex": float(self.lambda_bits_per_j).hex(),
            "kappa_bits_hex": float(self.kappa_bits).hex(),
            "beta_hex": float(self.beta).hex(),
            "loss_weights_hex": [float(value).hex() for value in self.loss_weights],
        }

    def pairwise_config(
        self,
        *,
        learning_rate: float,
        hidden_layers: tuple[int, ...] = (100, 50, 50),
        activation: str = "tanh",
    ) -> EEAxisPairwiseConfig:
        self.verify()
        return EEAxisPairwiseConfig(
            state_dim=EE_AXIS_STATE_DIM,
            action_dim=NUM_ACTIONS,
            hidden_layers=hidden_layers,
            activation=activation,
            learning_rate=learning_rate,
            kappa_bits=self.kappa_bits,
            beta=self.beta,
            loss_weights=self.loss_weights,
        )


def calibrate_ee_axis_pilot(
    *,
    calibration_seed: int,
    useful_bits: float,
    energy_j: float,
    steps: int,
    users: int,
    beta: float = 0.1,
    loss_weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> EEAxisPilotCalibration:
    if type(steps) is not int or steps <= 0 or type(users) is not int or users <= 0:
        raise EEAxisCalibrationError("steps and users must be positive exact integers")
    useful = _finite_positive(useful_bits, field="useful_bits")
    energy = _finite_positive(energy_j, field="energy_j")
    decisions = steps * users
    result = EEAxisPilotCalibration(
        calibration_seed=calibration_seed,
        useful_bits=useful,
        energy_j=energy,
        steps=steps,
        users=users,
        decision_count=decisions,
        lambda_bits_per_j=useful / energy,
        kappa_bits=useful / decisions,
        beta=float(beta),
        loss_weights=tuple(float(value) for value in loss_weights),
    )
    result.verify()
    return result


__all__ = [
    "EE_AXIS_CALIBRATION_SCHEMA",
    "EEAxisCalibrationError",
    "EEAxisPilotCalibration",
    "calibrate_ee_axis_pilot",
]
