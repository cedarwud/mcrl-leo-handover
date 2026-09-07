"""Unit-only F3 fixtures; no simulator, TLE archive, or 2,000-update fit."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import f3_common as common
import f3_neutral_rule as neutral_rule
import build_f3_source_artifact as source
import run_v023_c3_contingency_f3_learner_screen as runner
from mcrl.env.link_budget import fixed_power_w, pa_efficiency, supply_power_w, system_power_w
from mcrl.runtime.ee_axis_lcsrs_c3_state import C3View


f2 = common.f2


def _profile(*, rate: float, other_rate: float) -> f2.f1.PhysicalProfile:
    beam_power = np.asarray([1.0], dtype=np.float64)
    supply = supply_power_w(beam_power, pa_efficiency(beam_power))
    counts = np.asarray([1.0], dtype=np.float64)
    return f2.f1.PhysicalProfile(
        link_rate_bps=np.asarray([rate, other_rate, *([0.0] * 98)], dtype=np.float64),
        served=np.asarray([True, True, *([False] * 98)], dtype=np.bool_),
        serving_satellite=np.asarray([10, 10, *([-1] * 98)], dtype=np.int64),
        serving_cell=np.asarray([1, 1, *([-1] * 98)], dtype=np.int64),
        active_beam_satellites=np.asarray([10], dtype=np.int64),
        active_beam_cells=np.asarray([1], dtype=np.int64),
        beam_power_w=beam_power,
        fixed_power_w=fixed_power_w(counts),
        system_power_w=system_power_w(supply, counts),
        interval_s=2.0,
    )


def _f2_tape(key: f2.UnitKey) -> dict[str, object]:
    """Build a small legal surface through F2's own step/tape writers."""

    reference_profile = _profile(rate=100.0, other_rate=100.0)
    candidate_profile = _profile(rate=100.0, other_rate=200.0)
    masks = np.zeros((100, 28), dtype=np.bool_)
    masks[:, 0] = True
    masks[0, 1] = True
    references = np.zeros(100, dtype=np.int64)
    q12 = np.full((100, 28), -100.0, dtype=np.float64)
    q12[:, 0] = 0.0
    q12[0, 1] = -1.0e-9
    physical_keys = []
    for user in range(100):
        row: list[list[int] | None] = [[10, user], *([None] * 27)]
        if user == 0:
            row[1] = [11, 1]
        physical_keys.append(row)
    link_power = np.asarray([1.0, *([0.0] * 99)], dtype=np.float64)
    candidate_joint = references.copy()
    candidate_joint[0] = 1
    candidates = [
        {
            "focal_user": 0,
            "reference_action": 0,
            "candidate_action": 1,
            "reference_physical_key": [10, 0],
            "candidate_physical_key": [11, 1],
            "candidate_joint_actions": candidate_joint.tolist(),
            "profile": candidate_profile,
            "link_power_w": link_power,
        }
    ]
    d_bits = np.zeros_like(q12)
    f_bits = np.zeros_like(q12)
    target = f2.f1.compute_c3_targets(
        reference_profile,
        candidate_profile,
        focal_user=0,
        lambda_bits_per_j=f2.f1.LAMBDA_BITS_PER_J,
    )
    d_bits[0, 1] = target.d_bits
    f_bits[0, 1] = target.f_bits
    d_actions = f2.f1.masked_argmax_q12_plus_z(q12, d_bits, masks)
    f_actions = f2.f1.masked_argmax_q12_plus_z(q12, f_bits, masks)
    steps = [
        f2.build_f2_step_payload(
            step_index=step,
            admitted_candidates=("D",),
            q12=q12,
            action_masks=masks,
            reference_actions=references,
            reference_profile=reference_profile,
            reference_link_power_w=link_power,
            candidates=candidates,
            deployment_actions={"D": d_actions, "F": f_actions},
            deployment_profiles={
                "D": (candidate_profile, link_power),
                "F": (reference_profile, link_power),
            },
            state_sha256=f"{step + 1:064x}",
            action_physical_key_table=physical_keys,
        )
        for step in f2.CANONICAL_STEP_INDICES
    ]
    return f2.build_unit_tape_payload(
        key=key,
        steps=steps,
        q1_parameter_sha256="a" * 64,
        q2_parameter_sha256="b" * 64,
        preflight_manifest_sha256="c" * 64,
        f1_binding={
            "path": "/tmp/f1.json",
            "sha256": "d" * 64,
            "surviving_candidates": ["D"],
        },
    )


@pytest.fixture(scope="module")
def shared_view() -> C3View:
    users = 100
    masks = np.zeros((users, 28), dtype=np.bool_)
    masks[:, 0] = True
    masks[0, 1] = True
    context = np.zeros((users, 28, 29), dtype=np.float32)
    tokens = np.zeros((users, 28, users + 1, 38), dtype=np.float32)
    token_mask = np.zeros((users, 28, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = masks
    tokens[:, :, users, 1][masks] = 1.0
    return C3View(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=masks,
        reference_actions=np.zeros(users, dtype=np.int64),
    )


def test_seed_derivation_is_deterministic_and_domain_separated() -> None:
    assert common.learner_seeds() == (
        9024197307195252515,
        6671349318246123539,
        6946862304711082547,
    )
    assert common.learner_seeds() == common.learner_seeds()
    assert len(set(common.learner_seeds())) == 3


def test_process_environment_is_exact() -> None:
    assert common.validate_process_environment(dict(common.PROCESS_ENVIRONMENT)) == common.PROCESS_ENVIRONMENT
    drifted = dict(common.PROCESS_ENVIRONMENT)
    drifted["OMP_NUM_THREADS"] = "2"
    with pytest.raises(common.F3Error, match="environment drifted"):
        common.validate_process_environment(drifted)


def test_source_rows_use_f2_writer_and_f0_target_path(shared_view: C3View) -> None:
    key = f2.ALL_UNITS[0]
    tape = _f2_tape(key)
    keys = source._physical_keys(tape["steps"][1]["action_physical_keys"])

    def provider(_key: f2.UnitKey, step: int, payload: object) -> source.ReplayedView:
        return source.ReplayedView(
            view=shared_view,
            state_sha256=f"{step + 1:064x}",
            q12=np.asarray(f2.f1._matrix_from_hex(payload["q12"], field="q12"), dtype=np.float32),
            action_physical_keys=keys,
        )

    records = source.build_source_records(
        {key: (tape, "e" * 64)},
        survivor="D",
        view_provider=provider,
        expected_units=(key,),
    )
    assert len(records) == 9
    assert records[0].targets_bits[0, 1] != 0.0
    assert records[0].targets_normalized[0, 1] == np.float32(
        records[0].targets_bits[0, 1] / common.KAPPA_BITS
    )
    assert records[0].targets_normalized[0, 0] == 0.0
    neutral = neutral_rule.build_f3_neutral(records, training_worlds=(key.world,))
    assert neutral.coverage == 1.0
    assert neutral.meets_coverage_gate is True
    assert all(target[0, 0] == 0.0 for target in neutral.targets_by_record)


def test_neutral_rule_is_imported_and_fold_safe() -> None:
    assert source.build_f3_neutral is neutral_rule.build_f3_neutral
    assert (
        neutral_rule.IMPORTED_NEUTRAL_RULES["c1_predecision_source_selection"]
        == neutral_rule.C1_CLUSTER_NEUTRAL_SOURCE_RULE
    )
    assert (
        neutral_rule.IMPORTED_NEUTRAL_RULES["c2_predecision_source_selection"]
        == neutral_rule.C2_NEUTRAL_SOURCE_RULE
    )
    assert (
        source.neutral_rule_binding()["c3_f3"]["scope"]
        == "FOLD_LOCAL_TRAINING_ONLY_LABEL_PERMUTATION"
    )


def _panel_records(shared_view: C3View) -> tuple[source.F3SourceRecord, ...]:
    q12 = np.full((100, 28), -100.0, dtype=np.float32)
    q12[:, 0] = 0.0
    q12[0, 1] = -0.01
    bits = np.zeros((100, 28), dtype=np.float64)
    bits[0, 1] = common.KAPPA_BITS * 0.1
    normalized = np.asarray(bits / common.KAPPA_BITS, dtype=np.float32)
    keys = tuple(tuple(None for _ in range(28)) for _ in range(100))
    return tuple(
        source.F3SourceRecord(
            world=world,
            lineage=lineage,
            step=step,
            anchor_id=f"w{world}:l{lineage}:t{step}",
            view=shared_view,
            q12=q12,
            targets_bits=bits,
            targets_normalized=normalized,
            tape_sha256="a" * 64,
            state_sha256="b" * 64,
            action_physical_keys=keys,
        )
        for world in common.WORLDS
        for lineage in common.LINEAGES
        for step in common.ANCHORS
    )


def test_lowo_holds_out_all_three_lineages(shared_view: C3View) -> None:
    training, heldout = runner.lowo_fold(
        _panel_records(shared_view), held_out_world=common.WORLDS[2]
    )
    assert len(training) == 81
    assert len(heldout) == 27
    assert {record.world for record in heldout} == {common.WORLDS[2]}
    assert {record.lineage for record in heldout} == set(common.LINEAGES)
    assert common.WORLDS[2] not in {record.world for record in training}


def _threshold_kwargs() -> dict[str, object]:
    return {
        "denominators_valid": True,
        "positive_rows": 24,
        "negative_rows": 24,
        "mean_informed_spearman": 0.20,
        "mean_informed_balanced_accuracy": 0.60,
        "mean_neutral_balanced_accuracy": 0.55,
        "informed_world_wins": 3,
        "per_seed_nonnegative_worlds": {seed: 3 for seed in common.learner_seeds()},
    }


def test_metric_truth_table_accepts_r7_copies_and_panel_adaptations() -> None:
    assert runner.observability_threshold_truth(**_threshold_kwargs()) is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("positive_rows", 23),
        ("negative_rows", 23),
        ("mean_informed_spearman", 0.199999),
        ("mean_informed_balanced_accuracy", 0.599999),
        ("mean_neutral_balanced_accuracy", 0.550001),
        ("informed_world_wins", 2),
    ],
)
def test_metric_truth_table_rejects_below_each_boundary(field: str, value: object) -> None:
    values = _threshold_kwargs()
    values[field] = value
    assert runner.observability_threshold_truth(**values) is False


def _composition_payload() -> dict[str, object]:
    worlds = {}
    for index, world in enumerate(common.WORLDS):
        improved = index < 2
        worlds[str(world)] = {
            "profiles": {
                "BASE": {"bits": 100.0, "energy_j": 1.0, "service_fraction": 1.0},
                "ORACLE": {"bits": 101.0 if improved else 100.0, "energy_j": 1.0, "service_fraction": 0.99},
                "INFORMED": {"bits": 101.0 if improved else 100.0, "energy_j": 1.0, "service_fraction": 0.99},
                "NEUTRAL": {"bits": 100.0, "energy_j": 1.0, "service_fraction": 0.99},
            },
        }
    return {
        "schema": runner.COMPOSITION_INPUT_SCHEMA,
        "integrity": True,
        "closure_diagnostics": {
            "selected_11": 0,
            "literal_11_fraction": 0.0,
            "harmful_partial_fraction": 1.0,
            "topology_consistency_fraction": None,
        },
        "worlds": worlds,
    }


def test_composition_check_is_mandatory_and_at_boundaries() -> None:
    result = runner.evaluate_composition_check(_composition_payload())
    assert result["passes"] is True
    assert runner.adjudicate(integrity=True, observability=True, composition=False) == "F3_STOP_COMPOSITION"
    assert runner.adjudicate(integrity=True, observability=False, composition=True) == "F3_STOP_OBSERVABILITY"
    assert runner.adjudicate(integrity=False, observability=True, composition=True) == "INVALID_RUN"


def test_closure_diagnostics_do_not_veto_nonclosure_candidates() -> None:
    payload = _composition_payload()
    result = runner.evaluate_composition_check(payload)
    assert set(result["predicates"]) == {"teacher_ee", "informed_ee", "service"}
    assert result["closure_diagnostics_role"] == "SERIALIZED_NONDECISIVE_IF_PRESENT"
    assert result["passes"] is True


def test_threshold_provenance_labels_r7_copies_and_panel_adaptations() -> None:
    bindings = common.threshold_bindings()
    assert bindings["r7_copy"]["informed_mean_spearman_min"] == 0.20
    assert (
        bindings["panel_adaptation"][
            "informed_over_neutral_mean_seed_spearman_wins_min"
        ]
        == 3
    )
    assert (
        bindings["composition"]["panel_adaptation"][
            "teacher_ee_above_base_worlds_min"
        ]
        == 2
    )
    assert common.panel_bindings()["loss"]["provenance"] == "panel_adaptation"


def test_native_composition_uses_lowest_exact_tie() -> None:
    q12 = np.asarray([[1.0, 1.0, 0.0]])
    q3 = np.zeros_like(q12)
    mask = np.asarray([[True, True, False]])
    assert runner.native_composition_actions(q12, q3, mask).tolist() == [0]


def test_refuses_launch_authority_without_f2_survivor(tmp_path: Path) -> None:
    authority = {
        "schema": common.LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": common.DESIGN_CLAIM_CEILING,
        "preflight_manifest": {"path": "x", "sha256": "a" * 64},
        "f2_terminal_receipt": {"path": "/tmp/x", "sha256": "b" * 64},
        "survivor": None,
        "test_split_opened": False,
        "episode_training": False,
        "efficacy_claim": False,
    }
    path = tmp_path / "authority.json"
    common.write_once_json(path, authority)
    with pytest.raises(common.F3NotAdmitted, match="F3_NOT_ADMITTED"):
        common.validate_launch_authority(
            path, preflight_path=Path("x"), preflight_sha256="a" * 64
        )


def test_resume_authenticates_and_skips_complete_checkpoint(tmp_path: Path) -> None:
    key = runner.ALL_JOBS[0]
    networks = {}
    optimizers = {}
    for arm in common.ARMS:
        networks[arm], optimizers[arm] = runner.make_lcsrs_c3_student(student_seed=key.seed)
    runner._write_checkpoint(
        tmp_path,
        key=key,
        cursor=0,
        networks=networks,
        optimizers=optimizers,
        rng=np.random.Generator(np.random.PCG64(key.seed)),
        losses={arm: [] for arm in common.ARMS},
        source_manifest_sha256="c" * 64,
        consumed_schedule_sha256="d" * 64,
    )
    assert runner.resume_cursor(tmp_path) == 0
    with pytest.raises(common.F3Error, match="overwrite"):
        runner._write_checkpoint(
            tmp_path,
            key=key,
            cursor=0,
            networks=networks,
            optimizers=optimizers,
            rng=np.random.Generator(np.random.PCG64(key.seed)),
            losses={arm: [] for arm in common.ARMS},
            source_manifest_sha256="c" * 64,
            consumed_schedule_sha256="d" * 64,
        )


def test_generic_write_once_refuses_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "sealed.json"
    common.write_once_json(path, {"value": 1})
    with pytest.raises(common.F3Error, match="overwrite"):
        common.write_once_json(path, {"value": 2})
