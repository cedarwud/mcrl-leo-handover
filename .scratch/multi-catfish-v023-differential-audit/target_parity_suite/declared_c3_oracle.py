"""Pure four-profile oracle for the declared two-user LC-SRS C3 target.

The source definition is ``ee_axis_coalition_residual_c3.py:378-384``:
``joint_surplus = joint_delta_bits - lambda * joint_delta_energy``;
``interaction_surplus = interaction_bits - lambda * interaction_energy``;
``equal_share = interaction_surplus / members``; and
``z3 = nonfocal + equal_share``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class DecisionProfile:
    bits: np.ndarray
    energy_j: float

    def __post_init__(self) -> None:
        bits = np.asarray(self.bits, dtype=np.float64)
        if bits.ndim != 1 or bits.size < 2 or not np.all(np.isfinite(bits)):
            raise ValueError("bits must be a finite vector with at least two users")
        if not math.isfinite(float(self.energy_j)):
            raise ValueError("energy_j must be finite")
        frozen = np.array(bits, copy=True)
        frozen.setflags(write=False)
        object.__setattr__(self, "bits", frozen)
        object.__setattr__(self, "energy_j", float(self.energy_j))


@dataclass(frozen=True)
class AtomicSelection:
    profile: str
    users: tuple[int, ...]
    surplus: float


@dataclass(frozen=True)
class DeclaredC3Result:
    f00: float
    f10: float
    f01: float
    f11: float
    psi: float
    unilateral_nonfocal: np.ndarray
    z3: np.ndarray
    atomic_selection: AtomicSelection


def _validate_profiles(profiles: Sequence[DecisionProfile]) -> int:
    if len(profiles) != 4 or any(not isinstance(row, DecisionProfile) for row in profiles):
        raise TypeError("four DecisionProfile values are required")
    size = profiles[0].bits.size
    if any(row.bits.size != size for row in profiles):
        raise ValueError("profile bit vectors must have equal length")
    return int(size)


def _surplus(profile: DecisionProfile, multiplier: float) -> float:
    return math.fsum(float(value) for value in profile.bits) - multiplier * profile.energy_j


def executed_unilateral_c3(
    p00: DecisionProfile,
    p10: DecisionProfile,
    p01: DecisionProfile,
    *,
    users: tuple[int, int] = (0, 1),
) -> np.ndarray:
    """Legacy executed C3: each unilateral profile's nonfocal bit delta."""

    size = _validate_profiles((p00, p10, p01, p00))
    if len(set(users)) != 2 or any(not 0 <= user < size for user in users):
        raise ValueError("users must be two distinct valid user indices")
    rows = (p10, p01)
    values = np.array(
        [
            math.fsum(
                float(delta)
                for index, delta in enumerate(row.bits - p00.bits)
                if index != users[offset]
            )
            for offset, row in enumerate(rows)
        ],
        dtype=np.float64,
    )
    values.setflags(write=False)
    return values


def declared_c3_oracle(
    p00: DecisionProfile,
    p10: DecisionProfile,
    p01: DecisionProfile,
    p11: DecisionProfile,
    *,
    lambda_bits_per_j: float,
    users: tuple[int, int] = (0, 1),
) -> DeclaredC3Result:
    """Compute F00/F10/F01/F11, Psi, per-user z3, and atomic selection."""

    size = _validate_profiles((p00, p10, p01, p11))
    multiplier = float(lambda_bits_per_j)
    if not math.isfinite(multiplier) or multiplier < 0.0:
        raise ValueError("lambda_bits_per_j must be finite and nonnegative")
    if len(set(users)) != 2 or any(not 0 <= user < size for user in users):
        raise ValueError("users must be two distinct valid user indices")
    values = tuple(_surplus(row, multiplier) for row in (p00, p10, p01, p11))
    psi = values[3] - values[1] - values[2] + values[0]
    externality = executed_unilateral_c3(p00, p10, p01, users=users)
    z3 = np.asarray(externality + psi / 2.0, dtype=np.float64)
    z3.setflags(write=False)
    # Atomic means the chosen profile is indivisible: no independent per-row
    # argmax can synthesize a profile absent from {00,10,01,11}.
    labels = ("00", "10", "01", "11")
    members = ((), (users[0],), (users[1],), users)
    choice = max(range(4), key=lambda index: (values[index], -index))
    return DeclaredC3Result(
        f00=values[0],
        f10=values[1],
        f01=values[2],
        f11=values[3],
        psi=psi,
        unilateral_nonfocal=externality,
        z3=z3,
        atomic_selection=AtomicSelection(labels[choice], tuple(members[choice]), values[choice]),
    )
