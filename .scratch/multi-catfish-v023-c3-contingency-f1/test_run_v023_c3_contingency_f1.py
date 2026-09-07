"""Unit-scale F1 mechanics tests; no TLE archive or simulator is opened."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
import stat
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.link_budget import fixed_power_w, pa_efficiency, supply_power_w, system_power_w

import build_f1_preflight_manifest as preflight
import c3_contingency_f0 as f0
import run_v023_c3_contingency_f1 as f1


def _profile(
    *,
    rates: list[float],
    cells: list[int],
    beam_cells: list[int],
    powers: list[float],
    interval_s: float = 2.0,
) -> f1.PhysicalProfile:
    served = np.asarray(cells, dtype=np.int64) >= 0
    satellites = np.where(served, 10, -1).astype(np.int64)
    beam_satellites = np.full(len(beam_cells), 10, dtype=np.int64)
    beam_power = np.asarray(powers, dtype=np.float64)
    supply = supply_power_w(beam_power, pa_efficiency(beam_power))
    counts = np.asarray([len(beam_cells)], dtype=np.float64)
    return f1.PhysicalProfile(
        link_rate_bps=np.asarray(rates, dtype=np.float64),
        served=served,
        serving_satellite=satellites,
        serving_cell=np.asarray(cells, dtype=np.int64),
        active_beam_satellites=beam_satellites,
        active_beam_cells=np.asarray(beam_cells, dtype=np.int64),
        beam_power_w=beam_power,
        fixed_power_w=fixed_power_w(counts),
        system_power_w=system_power_w(supply, counts),
        interval_s=interval_s,
    )


def _fixture_tape() -> dict[str, object]:
    """Build the fixture through the production serializers and F0 formula."""

    reference = _profile(
        rates=[100.0, 100.0, *([0.0] * 98)],
        cells=[1, 2, *([-1] * 98)],
        beam_cells=[1, 2],
        powers=[1.0, 1.0],
    )
    candidate0 = _profile(
        rates=[100.0, 1000.0, *([0.0] * 98)],
        cells=[3, 2, *([-1] * 98)],
        beam_cells=[2, 3],
        powers=[1.0, 1.0],
    )
    candidate1 = _profile(
        rates=[1000.0, 100.0, *([0.0] * 98)],
        cells=[1, 4, *([-1] * 98)],
        beam_cells=[1, 4],
        powers=[1.0, 1.0],
    )
    d_deployment = _profile(
        rates=[200.0, 200.0, *([0.0] * 98)],
        cells=[3, 4, *([-1] * 98)],
        beam_cells=[3, 4],
        powers=[1.0, 1.0],
    )
    masks = np.zeros((f1.USERS, f1.NUM_ACTIONS), dtype=np.bool_)
    masks[:2, :2] = True
    reference_actions = np.asarray([0, 0, *([f1.NO_OP_ACTION] * 98)], dtype=np.int64)
    key_table: list[list[list[int] | None]] = [
        [[10, 1], [10, 3], *([None] * 26)],
        [[10, 2], [10, 4], *([None] * 26)],
        *[[None] * f1.NUM_ACTIONS for _ in range(98)],
    ]
    skeletons = [
        {
            "focal_user": 0,
            "reference_action": 0,
            "candidate_action": 1,
            "reference_physical_key": [10, 1],
            "candidate_physical_key": [10, 3],
            "candidate_joint_actions": [1, 0, *([f1.NO_OP_ACTION] * 98)],
            "profile": candidate0,
            "link_power_w": np.asarray([1.0, 1.0, *([0.0] * 98)]),
        },
        {
            "focal_user": 1,
            "reference_action": 0,
            "candidate_action": 1,
            "reference_physical_key": [10, 2],
            "candidate_physical_key": [10, 4],
            "candidate_joint_actions": [0, 1, *([f1.NO_OP_ACTION] * 98)],
            "profile": candidate1,
            "link_power_w": np.asarray([1.0, 1.0, *([0.0] * 98)]),
        },
    ]
    q12 = np.full((f1.USERS, f1.NUM_ACTIONS), -1000.0, dtype=np.float64)
    q12[:2, 0] = 0.0
    q12[:2, 1] = -1.0e-8
    d = np.zeros_like(q12)
    ff = np.zeros_like(q12)
    for row in skeletons:
        target = f1.compute_c3_targets(
            reference,
            row["profile"],
            focal_user=row["focal_user"],
            lambda_bits_per_j=f1.LAMBDA_BITS_PER_J,
        )
        d[row["focal_user"], row["candidate_action"]] = target.d_bits
        ff[row["focal_user"], row["candidate_action"]] = target.f_bits
    d_actions = f1.masked_argmax_q12_plus_z(q12, d, masks)
    f_actions = f1.masked_argmax_q12_plus_z(q12, ff, masks)
    assert d_actions.tolist() == [1, 1, *([f1.NO_OP_ACTION] * 98)]
    assert f_actions.tolist() == [0, 0, *([f1.NO_OP_ACTION] * 98)]
    steps = []
    for step_index in f1.CANONICAL_STEP_INDICES:
        steps.append(
            f1.build_step_payload(
                step_index=step_index,
                q12=q12,
                action_masks=masks,
                reference_actions=reference_actions,
                reference_profile=reference,
                reference_link_power_w=np.asarray([1.0, 1.0, *([0.0] * 98)]),
                candidates=skeletons,
                deployment_actions={"D": d_actions, "F": f_actions},
                deployment_profiles={
                    "D": (
                        d_deployment,
                        np.asarray([1.0, 1.0, *([0.0] * 98)]),
                    ),
                    "F": (
                        reference,
                        np.asarray([1.0, 1.0, *([0.0] * 98)]),
                    ),
                },
                state_sha256=f"{step_index + 1:064x}",
                action_physical_key_table=key_table,
            )
        )
    return f1.build_tape_payload(
        steps,
        q1_parameter_sha256="a" * 64,
        q2_parameter_sha256="b" * 64,
        preflight_manifest_sha256="c" * 64,
    )


def test_targets_are_recomputed_through_f0_with_known_conservation() -> None:
    tape = _fixture_tape()
    step = tape["steps"][0]
    reference = f1.profile_from_payload(step["reference_profile"])
    candidate = f1.profile_from_payload(step["unilateral_candidates"][0]["profile"])

    direct = f1.compute_c3_targets(
        reference,
        candidate,
        focal_user=0,
        lambda_bits_per_j=f1.LAMBDA_BITS_PER_J,
    )
    d, ff = f1.target_surfaces_from_step(step)

    assert direct.share_delta_energy_j == pytest.approx(0.0)
    assert direct.network_delta_energy_j == pytest.approx(0.0)
    assert direct.f_bits == pytest.approx(0.0)
    assert direct.d_bits == pytest.approx(1800.0)
    assert d[0, 1] == direct.d_bits
    assert ff[0, 1] == direct.f_bits
    assert f1.verify_tape_payload(tape)["D"][0].tolist() == [
        1,
        1,
        *([f1.NO_OP_ACTION] * 98),
    ]


def test_real_base_anchor0_energy_roundoff_is_accepted() -> None:
    fixture_path = Path(__file__).resolve().parents[2] / ".tmp" / "base-profile-anchor0.npz"
    with np.load(fixture_path, allow_pickle=False) as fixture:
        profile = f1.PhysicalProfile(
            link_rate_bps=fixture["link_rate_bps"],
            served=fixture["served"],
            serving_satellite=fixture["serving_satellite"],
            serving_cell=fixture["serving_cell"],
            active_beam_satellites=fixture["active_beam_satellites"],
            active_beam_cells=fixture["active_beam_cells"],
            beam_power_w=fixture["beam_power_w"],
            fixed_power_w=float(fixture["fixed_power_w"]),
            system_power_w=float(fixture["system_power_w"]),
            interval_s=float(fixture["interval_s"]),
        )

    canonical = f0._canonical_power_components(profile)
    beam_keys = {
        tuple(key): index for index, key in enumerate(profile.active_beam_keys.tolist())
    }
    satellite_ids = canonical.active_satellite_ids.tolist()
    satellite_index = {satellite: index for index, satellite in enumerate(satellite_ids)}
    beam_occupancy = np.zeros(profile.active_beams, dtype=np.int64)
    satellite_occupancy = np.zeros(len(satellite_ids), dtype=np.int64)
    user_beam = np.full(profile.users, -1, dtype=np.int64)
    user_satellite = np.full(profile.users, -1, dtype=np.int64)
    for user in np.flatnonzero(profile.served).tolist():
        key = (int(profile.serving_satellite[user]), int(profile.serving_cell[user]))
        user_beam[user] = beam_keys[key]
        user_satellite[user] = satellite_index[key[0]]
        beam_occupancy[user_beam[user]] += 1
        satellite_occupancy[user_satellite[user]] += 1
    beam_share = np.zeros(profile.users, dtype=np.float64)
    satellite_share = np.zeros(profile.users, dtype=np.float64)
    for user in np.flatnonzero(profile.served).tolist():
        beam_share[user] = (
            canonical.beam_cost_power_w[user_beam[user]] / beam_occupancy[user_beam[user]]
        )
        satellite_share[user] = (
            f0.BASEBAND_POWER_PER_SATELLITE_W
            / satellite_occupancy[user_satellite[user]]
        )
    direct_energy = (beam_share + satellite_share) * profile.interval_s
    split_energy = (
        beam_share * profile.interval_s + satellite_share * profile.interval_s
    )
    discrepancy = float(np.max(np.abs(direct_energy - split_energy)))

    assert discrepancy == np.float64(2.842170943040401e-14)
    assert discrepancy <= f0._roundoff_tolerance(
        float(np.max(np.abs(direct_energy))),
        float(np.max(np.abs(split_energy))),
    )
    result = f0.compute_cost_shares(profile)
    assert result.sum_share_energy_j == profile.network_energy_j


def test_tape_is_write_once_readonly_and_manifest_authenticated(tmp_path: Path) -> None:
    tape = _fixture_tape()
    tape_path, manifest_path, tape_sha = f1.write_tape_bundle(tmp_path / "out", tape)

    reopened = f1.read_tape_bundle(tape_path, manifest_path)

    assert reopened == tape
    assert f1.file_sha256(tape_path) == tape_sha
    assert stat.S_IMODE(tape_path.stat().st_mode) == 0o444
    assert stat.S_IMODE(manifest_path.stat().st_mode) == 0o444
    with pytest.raises(f1.F1Error, match="overwrite"):
        f1.write_tape_bundle(tmp_path / "out", tape)


@pytest.mark.parametrize(
    ("candidate_service", "candidate_ee", "changed", "expected"),
    [
        (1.0, 101.0, True, True),
        (0.998, 101.0, True, False),
        (1.0, 100.0, True, False),
        (1.0, 101.0, False, False),
    ],
)
def test_kill_rule_truth_table_and_mutation_negatives(
    candidate_service: float,
    candidate_ee: float,
    changed: bool,
    expected: bool,
) -> None:
    rules = f1.evaluate_kill_rules(
        base_metrics={"service_fraction": 1.0, "ratio_of_sums_ee_bits_per_j": 100.0},
        candidate_metrics={
            "service_fraction": candidate_service,
            "ratio_of_sums_ee_bits_per_j": candidate_ee,
        },
        action_changed=changed,
        integrity_ok=True,
    )
    assert rules["survives"] is expected


def test_service_margin_equality_is_admitted() -> None:
    rules = f1.evaluate_kill_rules(
        base_metrics={"service_fraction": 1.0, "ratio_of_sums_ee_bits_per_j": 100.0},
        candidate_metrics={"service_fraction": 0.999, "ratio_of_sums_ee_bits_per_j": 101.0},
        action_changed=True,
        integrity_ok=True,
    )
    assert rules["service_noninferior"] is True
    assert rules["survives"] is True


def test_d_has_priority_over_f_and_integrity_has_priority_over_both() -> None:
    both = {
        "D": {"integrity": True, "survives": True},
        "F": {"integrity": True, "survives": True},
    }
    assert f1.adjudicate_outcome(both) == "F1_SURVIVES_D"
    assert f1.adjudicate_outcome(both, integrity_ok=False) == "INVALID_RUN"
    assert (
        f1.adjudicate_outcome(
            {
                "D": {"integrity": True, "survives": False},
                "F": {"integrity": True, "survives": True},
            }
        )
        == "F1_SURVIVES_F"
    )


def test_invalid_d_integrity_prevents_passing_f_sibling_from_surviving() -> None:
    base = {"service_fraction": 1.0, "ratio_of_sums_ee_bits_per_j": 100.0}
    passing = {"service_fraction": 1.0, "ratio_of_sums_ee_bits_per_j": 101.0}
    rules = {
        "D": f1.evaluate_kill_rules(
            base_metrics=base,
            candidate_metrics=passing,
            action_changed=True,
            integrity_ok=False,
        ),
        "F": f1.evaluate_kill_rules(
            base_metrics=base,
            candidate_metrics=passing,
            action_changed=True,
            integrity_ok=True,
        ),
    }
    assert rules["D"]["integrity"] is False
    assert rules["F"]["survives"] is True
    assert f1.adjudicate_outcome(rules) == "INVALID_RUN"


def test_both_nonfinite_candidate_bundles_are_invalid_run() -> None:
    base = {"service_fraction": 1.0, "ratio_of_sums_ee_bits_per_j": 100.0}
    nonfinite = {"service_fraction": 1.0, "ratio_of_sums_ee_bits_per_j": np.nan}
    rules = {
        name: f1.evaluate_kill_rules(
            base_metrics=base,
            candidate_metrics=nonfinite,
            action_changed=True,
            integrity_ok=True,
        )
        for name in ("D", "F")
    }
    assert rules["D"]["integrity"] is False
    assert rules["F"]["integrity"] is False
    assert f1.adjudicate_outcome(rules) == "INVALID_RUN"


def test_invalid_run_receipt_is_explicit_and_has_no_fake_tape_digest() -> None:
    receipt = f1.invalid_run_receipt(
        error=f1.F1Error("fixture integrity failure"),
        preflight_manifest_sha256="c" * 64,
        tape_sha256=None,
    )
    assert receipt["outcome"] == "INVALID_RUN"
    assert receipt["status"] == "INVALID_RUN"
    assert receipt["tape_sha256"] is None
    assert receipt["tape_complete"] is False
    assert receipt["efficacy_claim"] is False


def test_screen_uses_pooled_ratio_of_sums_and_selects_d() -> None:
    tape = _fixture_tape()
    receipt = f1.screen_tape(tape, tape_sha256=f1.canonical_sha256(tape))
    assert receipt["outcome"] == "F1_SURVIVES_D"
    assert receipt["kill_rules"]["D"]["survives"] is True
    assert receipt["kill_rules"]["F"]["action_changed"] is False
    assert receipt["claim_ceiling"] == f1.CLAIM_CEILING


def test_composition_matches_v022_masked_q12_plus_z_over_kappa_convention() -> None:
    rng = np.random.default_rng(20260907)
    for _ in range(32):
        q1 = rng.normal(size=(17, f1.NUM_ACTIONS))
        q2 = rng.normal(size=(17, f1.NUM_ACTIONS))
        z3_bits = rng.normal(size=(17, f1.NUM_ACTIONS)) * f1.KAPPA_BITS
        masks = rng.random(size=(17, f1.NUM_ACTIONS)) < 0.35
        masks[:, 0] = True
        expected_v022 = np.argmax(
            np.where(masks, q1 + q2 + z3_bits / f1.KAPPA_BITS, -np.inf),
            axis=1,
        ).astype(np.int64)
        observed = f1.masked_argmax_q12_plus_z(q1 + q2, z3_bits, masks)
        assert np.array_equal(observed, expected_v022)


def test_empty_mask_user_is_noop_and_has_no_unilateral_candidate() -> None:
    empty_mask = np.zeros(f1.NUM_ACTIONS, dtype=np.bool_)
    valid_mask = np.zeros(f1.NUM_ACTIONS, dtype=np.bool_)
    valid_mask[:2] = True
    empty = SimpleNamespace(mask=empty_mask)
    valid = SimpleNamespace(mask=valid_mask)
    empty.association = lambda action: f1.Association(-1, -1)
    valid.association = lambda action: f1.Association(10, 20 + int(action))
    observation = SimpleNamespace(
        candidates=SimpleNamespace(slot_tables=(empty, valid))
    )

    rows = f1.enumerate_unilateral_candidates(
        observation, np.asarray([f1.NO_OP_ACTION, 0], dtype=np.int64)
    )
    selected = f1.masked_argmax_q12_plus_z(
        np.zeros((2, f1.NUM_ACTIONS)),
        np.zeros((2, f1.NUM_ACTIONS)),
        np.stack((empty_mask, valid_mask)),
    )

    assert [row["focal_user"] for row in rows] == [1]
    assert rows[0]["candidate_joint_actions"] == [f1.NO_OP_ACTION, 1]
    assert selected.tolist() == [f1.NO_OP_ACTION, 0]


def test_tape_validation_requires_exactly_100_base_users() -> None:
    tape = _fixture_tape()
    short = _profile(
        rates=[100.0, *([0.0] * 98)],
        cells=[1, *([-1] * 98)],
        beam_cells=[1],
        powers=[1.0],
    )
    tape["steps"][0]["reference_profile"] = f1.profile_to_payload(
        short, link_power_w=np.zeros(99)
    )
    with pytest.raises(f1.F1Error, match="exactly 100 users"):
        f1.verify_tape_payload(tape)


@pytest.mark.parametrize("mutation", ["users", "interval"])
def test_tape_validation_requires_deployments_to_match_base(mutation: str) -> None:
    tape = _fixture_tape()
    if mutation == "users":
        profile = _profile(
            rates=[100.0, *([0.0] * 98)],
            cells=[1, *([-1] * 98)],
            beam_cells=[1],
            powers=[1.0],
        )
        link_power = np.zeros(99)
    else:
        base = f1.profile_from_payload(tape["steps"][0]["reference_profile"])
        profile = copy.copy(base)
        object.__setattr__(profile, "interval_s", base.interval_s + 1.0)
        link_power = np.zeros(f1.USERS)
    tape["steps"][0]["deployments"]["D"]["profile"] = f1.profile_to_payload(
        profile, link_power_w=link_power
    )
    with pytest.raises(f1.F1Error, match="match BASE users and interval"):
        f1.verify_tape_payload(tape)


@pytest.mark.parametrize(
    "bindings",
    [
        f1.F1Bindings(world=f1.WORLD + 1),
        f1.F1Bindings(lineage=f1.LINEAGE + 1),
        f1.F1Bindings(canonical_step_indices=(0, 1, 2), step_count=3),
        f1.F1Bindings(step_count=1),
    ],
)
def test_rejects_other_world_lineage_or_step_count(bindings: f1.F1Bindings) -> None:
    with pytest.raises(f1.F1Error):
        bindings.verify()


def test_preflight_builder_and_dry_run_validate_code_and_bindings(tmp_path: Path) -> None:
    manifest, sidecar, digest = preflight.write_manifest(tmp_path / "preflight.json")
    payload, observed = f1.validate_preflight_manifest(manifest)
    assert observed == digest
    assert sidecar.read_text(encoding="ascii").split() == [digest, manifest.name]
    assert payload["bindings"]["world"] == f1.WORLD
    assert payload["bindings"]["kappa_bits_hex"] == f1.KAPPA_BITS.hex()
    assert payload["bindings"]["candidate_deployment_rule"] == (
        "MASKED_ARGMAX_Q1_PLUS_Q2_PLUS_Z_OVER_KAPPA"
    )
    assert payload["authority"]["composition_units"]["model_config_sha256"] == (
        f1.MODEL_CONFIG_SHA256
    )
    args = argparse.Namespace(
        dry_run=True,
        preflight_manifest=manifest,
        launch_authority=None,
        tle_root=None,
        output=None,
    )
    assert f1.run(args) == {"preflight": manifest}
