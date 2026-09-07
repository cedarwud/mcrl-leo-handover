"""R5 regression for verifier/production floating-point semantics."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys

import numpy as np

from mcrl.runtime.ee_axis_coalition_residual_c3 import build_coalition_residual_c3


HERE = Path(__file__).resolve().parent
VERIFIER_PATH = HERE / "verify_v023_lcsrs_scientific.py"
_SPEC = importlib.util.spec_from_file_location("v023_r5_scientific_verifier", VERIFIER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
verifier = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = verifier
_SPEC.loader.exec_module(verifier)


def test_profile_total_uses_delta_domain_stable_sum() -> None:
    """The independent reducer must not silently use NumPy's order-sensitive sum."""

    profile = np.asarray([1.0e16, 1.0, 1.0], dtype=np.float64)
    assert np.sum(profile) != math.fsum(float(value) for value in profile.tolist())
    assert verifier._stable_sum(profile) == math.fsum(
        float(value) for value in profile.tolist()
    )


def test_cancelled_physical_fixture_matches_production_delta_formula() -> None:
    """Keep the R3 cancellation fixture aligned with the production builder."""

    reference_bits = np.asarray([605035526899.4789, 35818623467.93558])
    unilateral_bits = np.asarray(
        [
            [605022863453.9861, 35831688300.729614],
            [605063155861.6459, 35824157607.71982],
        ]
    )
    joint_bits = np.asarray([605040645185.1671, 35834419392.13486])
    reference_energy = 1000.0
    unilateral_energy = np.asarray([1000.804215736796, 1000.9537805128198])
    joint_energy = 1000.1763631196809
    members = np.asarray([0, 1], dtype=np.int64)
    legal = np.asarray([[True, True, False, False], [True, False, True, False]])
    production = build_coalition_residual_c3(
        B0_v=reference_bits,
        E0=reference_energy,
        Bu=unilateral_bits,
        Eu=unilateral_energy,
        BC=joint_bits,
        EC=joint_energy,
        coalition_user_ids=members,
        proposed_actions=np.asarray([1, 2], dtype=np.int64),
        lambda_bits_per_j=verifier.LAMBDA_BITS_PER_J,
        kappa_bits=verifier.KAPPA_BITS,
        action_count=4,
        reference_actions=np.asarray([0, 0], dtype=np.int64),
        legal_mask=legal,
    )
    independent = verifier._formula(
        np.vstack((reference_bits, unilateral_bits, joint_bits)),
        np.asarray(
            [reference_energy, unilateral_energy[0], unilateral_energy[1], joint_energy]
        ),
        members,
    )

    assert independent.joint_delta_bits == production.joint_delta_bits
    assert independent.joint_delta_energy == production.joint_delta_energy_j
    assert independent.joint_surplus == production.joint_surplus_bits
    assert independent.interaction_bits == production.interaction_bits
    assert independent.interaction_energy == production.interaction_energy_j
    assert independent.interaction_surplus == production.interaction_surplus_bits
    assert independent.equal_share == production.equal_share_bits
    np.testing.assert_array_equal(independent.own, production.own_bits)
    np.testing.assert_array_equal(independent.nonfocal, production.nonfocal_bits)
    np.testing.assert_array_equal(independent.z3, production.z3_bits)
    assert independent.residual == production.identity_residual_bits
