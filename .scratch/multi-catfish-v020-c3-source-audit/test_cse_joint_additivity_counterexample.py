"""Executable counterexample to the proposed CSE joint-additivity claim.

This is pure arithmetic: it does not import or run the simulator.
"""


def test_separate_unilateral_cost_shares_do_not_form_joint_potential() -> None:
    lambda_bits_per_j = 1.0

    # Reference (A, A): aggregate capacity=1, one active beam, equal shares.
    reference_bits = 1.0
    reference_energy = 1.0
    reference_share = 0.5

    # Either unilateral branch (B, A) or (A, B): capacities add, two beams lit.
    unilateral_focal_bits = 0.75
    unilateral_nonfocal_bits = 1.0
    reference_focal_bits = 0.5
    reference_nonfocal_bits = 0.5
    unilateral_energy = 2.0
    unilateral_focal_share = 1.0

    delta_focal_bits = unilateral_focal_bits - reference_focal_bits
    delta_nonfocal_bits = unilateral_nonfocal_bits - reference_nonfocal_bits
    delta_energy = unilateral_energy - reference_energy
    delta_share = unilateral_focal_share - reference_share

    z1 = delta_focal_bits - lambda_bits_per_j * delta_energy
    z3_cse = delta_nonfocal_bits - lambda_bits_per_j * (
        delta_share - delta_energy
    )
    summed_separate_unilateral_targets = 2.0 * (z1 + z3_cse)

    # Simultaneous branch (B, B): aggregate capacity=.75, one active beam.
    joint_bits = 0.75
    joint_energy = 1.0
    true_joint_surplus = (joint_bits - reference_bits) - lambda_bits_per_j * (
        joint_energy - reference_energy
    )

    assert z1 == -0.75
    assert z3_cse == 1.0
    assert summed_separate_unilateral_targets == 0.5
    assert true_joint_surplus == -0.25
    assert summed_separate_unilateral_targets > 0.0 > true_joint_surplus
