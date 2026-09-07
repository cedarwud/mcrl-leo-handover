"""W-122 -- mechanically sealed V0.7 C2 three-arm parallel manifest."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json

import pytest

from mcrl.runtime.ee_axis_v07_c2_d2 import D2_LINEAGES, D2_SEEDS
from mcrl.runtime.ee_axis_v07_c2_parallel_manifest import (
    FastProxyStageSpec,
    CommonSeedSchedule,
    LineageAuthority,
    OutcomeFirewall,
    ParallelArmJobSpec,
    PhysicalAnchorSpec,
    SelectionRules,
    SharedStageBudgets,
    V07C2ParallelManifestError,
    V07C2PreOutcomeParallelManifest,
    V07_C2_KEYED_FIELD_GRAMMAR,
    V07_C2_NONFOCAL_TAPE_GRAMMAR,
    V07_C2_FAST_PROXY_LABEL,
    V07_C2_FAST_PROXY_MAX_ACTIONS,
    V07_C2_NATIVE_ACTION_COUNT,
    V07_C2_PARALLEL_ARMS,
    V07_C2_STAGE_PLAN,
    build_v07_c2_parallel_manifest,
    canonical_json_bytes,
    current_target_authorities,
    load_v07_c2_parallel_manifest,
)
from mcrl.runtime.ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)


def _sha(value: int) -> str:
    return f"{value:064x}"


def _anchors() -> tuple[PhysicalAnchorSpec, ...]:
    anchors: list[PhysicalAnchorSpec] = []
    for index, seed in enumerate(D2_SEEDS):
        anchors.extend(
            (
                PhysicalAnchorSpec(
                    seed=seed,
                    window="early",
                    step_index=1 + index % 2,
                    focal_user=index % 4,
                    anchor_receipt_sha256=_sha(100 + 2 * index),
                ),
                PhysicalAnchorSpec(
                    seed=seed,
                    window="late",
                    step_index=5 + index % 2,
                    focal_user=(index + 1) % 4,
                    anchor_receipt_sha256=_sha(101 + 2 * index),
                ),
            )
        )
    return tuple(anchors)


def _lineages() -> tuple[LineageAuthority, ...]:
    return tuple(
        LineageAuthority(
            lineage=lineage,
            q1_checkpoint_sha256=_sha(300 + index * 3),
            q3_checkpoint_sha256=_sha(301 + index * 3),
            direct_policy_sha256=_sha(302 + index * 3),
        )
        for index, lineage in enumerate(D2_LINEAGES)
    )


def _seeds() -> CommonSeedSchedule:
    return CommonSeedSchedule(
        stage_a_physical_seeds=D2_SEEDS,
        stage_b_train_world_seeds=(2026105001, 2026105002),
        stage_b_validation_world_seeds=(2026105101,),
        stage_b_initialization_seeds=(2026105201, 2026105202),
        stage_c_evaluation_world_seeds=(2026106001, 2026106002),
    )


def _budgets() -> SharedStageBudgets:
    return SharedStageBudgets(
        stage_a_physical_anchors=20,
        stage_a_lineages=3,
        stage_a_lineage_cells=60,
        stage_b_updates=100,
        stage_b_train_worlds=2,
        stage_b_validation_worlds=1,
        stage_b_initializations=2,
        stage_c_evaluation_worlds=2,
        stage_c_lineages=3,
    )


def _manifest() -> V07C2PreOutcomeParallelManifest:
    return build_v07_c2_parallel_manifest(
        anchors=_anchors(),
        lineages=_lineages(),
        seeds=_seeds(),
        budgets=_budgets(),
        keyed_field_implementation_sha256=_sha(401),
        nonfocal_tape_implementation_sha256=_sha(402),
        stage_a_rules_sha256=_sha(403),
        stage_b_rules_sha256=_sha(404),
        stage_c_rules_sha256=_sha(405),
        practical_tie_band_fraction_hex=(0.001).hex(),
        service_guard_sha256=_sha(406),
    )


def test_manifest_roundtrip_binds_exact_common_three_arm_block() -> None:
    manifest = _manifest()
    assert manifest.arms == ("P0", "B1", "B2")
    assert len(manifest.anchors) == 20
    assert manifest.seeds.stage_a_physical_seeds == D2_SEEDS
    assert tuple(lineage.lineage for lineage in manifest.lineages) == D2_LINEAGES
    assert manifest.q2_state_schema == V07_C2_Q2_STATE_SCHEMA
    assert manifest.q2_state_schema_sha256 == V07_C2_Q2_STATE_SCHEMA_SHA256
    assert tuple(target.arm for target in manifest.targets) == V07_C2_PARALLEL_ARMS
    assert all(len(target.target_code_sha256) == 64 for target in manifest.targets)
    assert manifest.protocol.keyed_field_grammar == V07_C2_KEYED_FIELD_GRAMMAR
    assert (
        manifest.protocol.nonfocal_tape_grammar
        == V07_C2_NONFOCAL_TAPE_GRAMMAR
    )
    assert manifest.verify() == manifest.manifest_sha256

    decoded = json.loads(canonical_json_bytes(manifest.to_mapping()))
    loaded = load_v07_c2_parallel_manifest(
        decoded, expected_manifest_sha256=manifest.manifest_sha256
    )
    assert loaded.to_mapping() == manifest.to_mapping()
    assert loaded.file_sha256 == manifest.file_sha256


def test_three_jobs_are_standalone_immutable_and_share_every_budget() -> None:
    manifest = _manifest()
    jobs = manifest.parallel_job_specs
    assert tuple(job.arm for job in jobs) == V07_C2_PARALLEL_ARMS
    assert len(jobs) == 3
    assert {job.manifest_sha256 for job in jobs} == {manifest.manifest_sha256}
    assert {job.seeds.schedule_sha256 for job in jobs} == {
        manifest.seeds.schedule_sha256
    }
    assert {job.budgets.budget_sha256 for job in jobs} == {
        manifest.budgets.budget_sha256
    }
    assert {tuple(anchor.anchor_id_sha256 for anchor in job.anchors) for job in jobs} == {
        tuple(anchor.anchor_id_sha256 for anchor in manifest.anchors)
    }
    assert {tuple(lineage.authority_sha256 for lineage in job.lineages) for job in jobs} == {
        tuple(lineage.authority_sha256 for lineage in manifest.lineages)
    }
    assert all(job.stage_plan == V07_C2_STAGE_PLAN for job in jobs)
    assert jobs[0].target.uses_common_nonfocal_tape is False
    assert all(job.target.uses_common_nonfocal_tape for job in jobs[1:])
    assert len({job.job_sha256 for job in jobs}) == 3
    assert all(
        ParallelArmJobSpec.from_mapping(job.to_mapping()).to_mapping()
        == job.to_mapping()
        for job in jobs
    )
    with pytest.raises(FrozenInstanceError):
        jobs[0].arm = "B1"  # type: ignore[misc]


def test_manifest_rejects_missing_or_redefined_arm_and_code_drift() -> None:
    manifest = _manifest()
    with pytest.raises(V07C2ParallelManifestError, match="exactly P0, B1, and B2"):
        replace(manifest, targets=manifest.targets[:2])

    current = current_target_authorities()
    with pytest.raises(V07C2ParallelManifestError, match="code hash"):
        replace(current[0], target_code_sha256="f" * 64)

    with pytest.raises(V07C2ParallelManifestError, match="Q2 state schema"):
        replace(manifest, q2_state_schema_sha256="f" * 64)
    with pytest.raises(V07C2ParallelManifestError, match="exact integer"):
        replace(manifest, version=True)

    with pytest.raises(V07C2ParallelManifestError, match="must be a Boolean"):
        replace(
            current[1],
            uses_common_nonfocal_tape=1,  # type: ignore[arg-type]
        )


def test_serialized_jobs_cannot_be_omitted_or_replaced() -> None:
    manifest = _manifest()
    omitted = deepcopy(manifest.to_mapping())
    omitted["jobs"] = omitted["jobs"][:-1]
    # Jobs are outside the manifest body hash, so this proves the independent
    # exact-derived-job check rather than merely exercising digest mismatch.
    assert omitted["manifest_sha256"] == manifest.manifest_sha256
    with pytest.raises(V07C2ParallelManifestError, match="omit, cancel, replace"):
        load_v07_c2_parallel_manifest(omitted)

    alternate_seeds = CommonSeedSchedule(
        stage_a_physical_seeds=D2_SEEDS,
        stage_b_train_world_seeds=(2026105001, 2026105002),
        stage_b_validation_world_seeds=(2026105101,),
        stage_b_initialization_seeds=(2026105201, 2026105202),
        stage_c_evaluation_world_seeds=(2026107001, 2026107002),
    )
    rogue_job = replace(manifest.parallel_job_specs[1], seeds=alternate_seeds)
    replaced = deepcopy(manifest.to_mapping())
    replaced["jobs"][1] = rogue_job.to_mapping()
    with pytest.raises(V07C2ParallelManifestError, match="omit, cancel, replace"):
        load_v07_c2_parallel_manifest(replaced)


def test_anchor_schedule_is_exactly_one_early_and_late_per_seed() -> None:
    manifest = _manifest()
    with pytest.raises(V07C2ParallelManifestError, match="exactly 20"):
        replace(manifest, anchors=manifest.anchors[:-1])

    duplicate = PhysicalAnchorSpec(
        seed=D2_SEEDS[-1],
        window="early",
        step_index=1,
        focal_user=9,
        anchor_receipt_sha256=_sha(999),
    )
    with pytest.raises(V07C2ParallelManifestError, match="one early and one late"):
        replace(manifest, anchors=manifest.anchors[:-1] + (duplicate,))

    with pytest.raises(V07C2ParallelManifestError, match="selection window"):
        PhysicalAnchorSpec(
            seed=D2_SEEDS[0],
            window="early",
            step_index=5,
            focal_user=0,
            anchor_receipt_sha256=_sha(998),
        )


def test_seed_roles_are_disjoint_and_budgets_match_common_schedule() -> None:
    with pytest.raises(V07C2ParallelManifestError, match="seed roles overlap"):
        replace(_seeds(), stage_c_evaluation_world_seeds=(2026105001,))

    with pytest.raises(V07C2ParallelManifestError, match="ten-seed D2 block"):
        replace(_seeds(), stage_a_physical_seeds=D2_SEEDS[:-1])

    with pytest.raises(V07C2ParallelManifestError, match="exactly 100 updates"):
        replace(_budgets(), stage_b_updates=101)

    with pytest.raises(V07C2ParallelManifestError, match="budgets disagree"):
        build_v07_c2_parallel_manifest(
            anchors=_anchors(),
            lineages=_lineages(),
            seeds=_seeds(),
            budgets=replace(_budgets(), stage_c_evaluation_worlds=1),
            keyed_field_implementation_sha256=_sha(401),
            nonfocal_tape_implementation_sha256=_sha(402),
            stage_a_rules_sha256=_sha(403),
            stage_b_rules_sha256=_sha(404),
            stage_c_rules_sha256=_sha(405),
            practical_tie_band_fraction_hex=(0.001).hex(),
            service_guard_sha256=_sha(406),
        )


def test_outcome_firewall_forbids_cancel_retry_replacement_and_mutation() -> None:
    invalid_values = (
        {"target_outcomes_opened": True},
        {"arm_omission_allowed": True},
        {"cross_arm_cancellation_allowed": True},
        {"retry_count": 1},
        {"replacement_count": 1},
        {"partial_results_may_mutate_manifest": True},
        {"ineligible_jobs_retained_for_report": False},
    )
    for changes in invalid_values:
        with pytest.raises(V07C2ParallelManifestError, match="outcome-driven"):
            OutcomeFirewall(**changes)  # type: ignore[arg-type]

    payload = deepcopy(_manifest().to_mapping())
    payload["outcome"] = {"winner": "P0"}
    with pytest.raises(V07C2ParallelManifestError, match="forbidden/unknown"):
        load_v07_c2_parallel_manifest(payload)


def test_selection_tie_order_and_report_all_are_frozen() -> None:
    manifest = _manifest()
    assert manifest.selection.practical_tie_band_fraction_hex == (0.001).hex()
    assert manifest.selection.simplicity_order == ("P0", "B1", "B2")
    assert manifest.selection.report_all_arms is True

    with pytest.raises(V07C2ParallelManifestError, match="tie order"):
        SelectionRules(
            practical_tie_band_fraction_hex=(0.001).hex(),
            service_guard_sha256=_sha(406),
            simplicity_order=("B1", "P0", "B2"),
        )
    with pytest.raises(V07C2ParallelManifestError, match="all three"):
        SelectionRules(
            practical_tie_band_fraction_hex=(0.001).hex(),
            service_guard_sha256=_sha(406),
            report_all_arms=False,
        )
    with pytest.raises(V07C2ParallelManifestError, match="canonical finite"):
        SelectionRules(
            practical_tie_band_fraction_hex="0.001",
            service_guard_sha256=_sha(406),
        )


def test_fast_proxy_is_separate_diagnostic_stage_and_full_b2_stays_native_28() -> None:
    manifest = _manifest()
    proxy = manifest.fast_proxy
    assert proxy.stage_label == V07_C2_FAST_PROXY_LABEL
    assert proxy.arm == "B2"
    assert 1 <= len(proxy.action_panel) <= V07_C2_FAST_PROXY_MAX_ACTIONS
    assert proxy.final_evidence is False
    assert proxy.is_final_evidence is False
    assert proxy.full_b2_action_count == V07_C2_NATIVE_ACTION_COUNT == 28
    assert proxy.full_b2_is_native_28 is True
    assert manifest.parallel_job_specs[0].fast_proxy is None
    assert manifest.parallel_job_specs[1].fast_proxy is None
    assert manifest.parallel_job_specs[2].fast_proxy == proxy

    custom = build_v07_c2_parallel_manifest(
        anchors=_anchors(),
        lineages=_lineages(),
        seeds=_seeds(),
        budgets=_budgets(),
        keyed_field_implementation_sha256=_sha(401),
        nonfocal_tape_implementation_sha256=_sha(402),
        stage_a_rules_sha256=_sha(403),
        stage_b_rules_sha256=_sha(404),
        stage_c_rules_sha256=_sha(405),
        practical_tie_band_fraction_hex=(0.001).hex(),
        service_guard_sha256=_sha(406),
        fast_proxy_action_panel=(3, 7, 11),
    )
    assert custom.fast_proxy.action_panel == (3, 7, 11)
    assert custom.parallel_job_specs[-1].fast_proxy == custom.fast_proxy


def test_fast_proxy_panel_and_final_evidence_flag_are_frozen() -> None:
    with pytest.raises(V07C2ParallelManifestError, match="at most"):
        FastProxyStageSpec(action_panel=(0, 1, 2, 3, 4))
    with pytest.raises(V07C2ParallelManifestError, match="strictly increasing"):
        FastProxyStageSpec(action_panel=(0, 0))
    with pytest.raises(V07C2ParallelManifestError, match="action IDs"):
        FastProxyStageSpec(action_panel=(27, 28))
    with pytest.raises(V07C2ParallelManifestError, match="final evidence"):
        FastProxyStageSpec(final_evidence=True)
    with pytest.raises(V07C2ParallelManifestError, match="native 28"):
        FastProxyStageSpec(full_confirmation_action_count=27)


def test_fast_proxy_serialization_is_digest_bound() -> None:
    manifest = _manifest()
    payload = deepcopy(manifest.to_mapping())
    payload["fast_proxy"]["action_panel"] = [0]
    with pytest.raises(V07C2ParallelManifestError, match="disagrees"):
        load_v07_c2_parallel_manifest(payload)

    job_payload = deepcopy(manifest.to_mapping())
    job_payload["jobs"][2]["fast_proxy"] = None
    with pytest.raises(V07C2ParallelManifestError, match="B2 job"):
        load_v07_c2_parallel_manifest(job_payload)
