from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from itertools import product
import time
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.physics_v025.targets import (
    NetworkOutcome,
    OffsetProjection,
    c2_persistence_forecast,
)
from mcrl.stagec_v025.acceptance import (
    crossed_inference_calibration,
    synthetic_crossed_clusters,
)
from mcrl.stagec_v025.canonical import StageCContractError, canonical_sha256
from mcrl.stagec_v025.coalitions import (
    AffectedBeamContext,
    CoalitionContext,
    CoalitionMember,
    build_coalition_row,
    exact_shapley_reporting_credit,
    pair_reporting_credit,
    read_coalition_shard,
    write_coalition_shard,
)
from mcrl.stagec_v025.deployment import (
    DeploymentAdapter,
    ProfileSelector,
    ResolvedProfile,
    UserActionTable,
    construct_reference_proposal,
)
from mcrl.stagec_v025.evaluation import (
    AllocationManifest,
    AllocationUnit,
    AttemptRegistry,
    EvaluationRunner,
    InitialTemporalState,
    StepOutcome,
)
from mcrl.stagec_v025.experiments import (
    ArchitectureRemovalExperiment,
    CheckpointKnockoutExperiment,
    LearnedNeutralSourceExperiment,
    OracleFactorScoreRemovalExperiment,
)
from mcrl.stagec_v025.interfaces import (
    ArmInformationInterface,
    CatalogueProfile,
    CoordinatorInformation,
    HeadsInformation,
    NominalProfileOutput,
    ReferenceProfiles,
    authenticate_matched_catalogues,
)
from mcrl.stagec_v025.learner import (
    LEARNED_ARMS,
    CoalitionBatch,
    LinearHead,
    PairwiseBatch,
    SetInteractionHead,
    ThreeRouteModel,
    V1LineageOrchestrator,
    V1ThreeRouteModel,
    default_synthetic_neutral_sources,
)
from mcrl.stagec_v025.merge import infer_cluster_totals, merge_receipts
from mcrl.stagec_v025.state import PhysicalAction
from mcrl.stagec_v025.state import extract_source_rows, kappa_normalization_bits
from mcrl.stagec_v025.synthetic import make_synthetic_anchors


def _digest(label: str) -> str:
    return canonical_sha256({"synthetic": label})


def _outcome(*, physical_f: float, phi: float = 0.0, kappa: float = 2.0) -> NetworkOutcome:
    # eta=1, E=100, so physical objective is bits-100.  The signed preference
    # enters F as +kappa*phi exactly once.
    del kappa
    return NetworkOutcome.build(
        bits=100.0 + physical_f,
        joules=100.0,
        phi=phi,
        decoding_availability=1.0,
        useful_availability=1.0,
    )


def _context(
    kind: str,
    members: tuple[int, ...],
    *,
    relabel: int = 0,
    omit_joint_context: bool = False,
) -> CoalitionContext:
    base = tuple((user, PhysicalAction(None, None)) for user in range(3))
    signals = {
        "synergy": (1.0, 0.0, 0.0),
        "antagonistic": (0.0, 1.0, 0.0),
        "additive": (0.0, 0.0, 1.0),
    }
    global_features = signals["additive"] if omit_joint_context else signals[kind]
    return CoalitionContext(
        anchor_id=f"{kind}-anchor",
        reference_profile=base,
        members=tuple(
            CoalitionMember(
                user_id=user,
                reference_action=base[user][1],
                selected_action=PhysicalAction(2000 + relabel + user, 20 + user),
                selected_q1_row=(1.0,),
                incumbent_q1_row=(float(user == 0),),
                missing_incumbent=False,
            )
            for user in members
        ),
        affected_beams=(
            AffectedBeamContext("affected", 0, len(members), False, bool(members), 2.0, 0.5),
        ),
        global_resource_features=global_features,
    )


def _coalition_row(
    kind: str, *, tmp_count: int = 2, members: tuple[int, ...] = (0, 1)
):
    context = _context(kind, members)
    joint = {
        "synergy": _outcome(physical_f=4.0, phi=-1.0),       # F=+2
        "antagonistic": _outcome(physical_f=-2.0, phi=-1.0), # F=-4
        "additive": _outcome(physical_f=-2.0, phi=0.0),      # F=-2
    }[kind]
    return build_coalition_row(
        context=context,
        reference_outcome=_outcome(physical_f=0.0),
        unilateral_outcomes={
            0: _outcome(physical_f=0.0, phi=-0.5),  # F=-1
            1: _outcome(physical_f=-1.0),           # F=-1
            **({2: _outcome(physical_f=0.0)} if 2 in members else {}),
        },
        coalition_outcome=joint,
        original_changed_user_count=tmp_count,
        world_id=f"synthetic/{kind}",
        world_seed=11,
        anchor_index=0,
        decision_time_utc="2026-01-01T00:00:00Z",
        decision_time_ns=0,
        setting_id="synthetic",
        lambda_bits_per_j=1.0,
        eta_ref_bits_per_j=1.0,
        kappa_normalization_bits=2.0,
        code_digest=_digest("code"),
        physics_digest=_digest("physics"),
        catalogue_digest=_digest("catalogue"),
        setting_digest=_digest("setting"),
        calibration_digest=_digest("calibration"),
        allocation_manifest_digest=_digest("allocation"),
    )


def _tables(*, relabel: int = 0) -> tuple[UserActionTable, ...]:
    result = []
    for user in range(3):
        delta = -0.5 if user < 2 else 0.0
        result.append(
            UserActionTable(
                user_id=user,
                actions=(
                    PhysicalAction(None, None),
                    PhysicalAction(2000 + relabel + user, 20 + user),
                ),
                action_mask=(True, True),
                q1_states=((0.0,), (delta,)),
                q2_states=((0.0,), (0.0,)),
            )
        )
    return tuple(result)


def _profile_contexts(kind: str, *, relabel: int = 0, omit: bool = False):
    result = {}
    for profile in product((0, 1), repeat=3):
        members = tuple(index for index, action in enumerate(profile) if action == 1)
        result[profile] = _context(kind, members, relabel=relabel, omit_joint_context=omit)
    return result


def _pair(route: str) -> PairwiseBatch:
    return PairwiseBatch.create(
        route,
        ((0.0,), (0.0,)),
        ((-0.5,), (-0.5,)),
        (-0.5, -0.5),
        (f"{route}-0", f"{route}-1"),
        _digest("action-source"),
    )


def _model_from_batch(batch: CoalitionBatch) -> V1ThreeRouteModel:
    rng = np.random.default_rng(17)
    model = V1ThreeRouteModel(
        LinearHead(np.asarray([1.0]), 0.0),
        LinearHead(np.asarray([0.0]), 0.0),
        SetInteractionHead(
            rng.normal(0.0, 0.05, (16, batch.invariant_states.shape[1])),
            np.zeros(16),
            np.zeros(16),
            0.0,
            batch.member_width,
        ),
    )
    model.psi.fit_closed_form(batch)
    return model


def test_T1_exhaustive_decomposition_and_intervention(tmp_path) -> None:
    synergy = _coalition_row("synergy")
    antagonistic = _coalition_row("antagonistic")
    additive = _coalition_row("additive")

    # Exact B4 identity with nonzero Phi charged once, and the second physical
    # identity without Phi.  Values are normalized by kappa=2.
    assert float.fromhex(synergy.c1_normalized_hex) == -1.0
    assert float.fromhex(synergy.psi_normalized_hex) == 2.0
    assert float.fromhex(synergy.objective_delta_normalized_hex) == 1.0
    assert float.fromhex(synergy.physical_c1_normalized_hex) == -0.5
    assert float.fromhex(synergy.physical_psi_normalized_hex) == 2.5
    assert float.fromhex(synergy.physical_delta_normalized_hex) == 2.0
    assert float.fromhex(antagonistic.psi_normalized_hex) == -1.0
    assert float.fromhex(additive.psi_normalized_hex) == 0.0
    # Exhaust all 2^3 profiles at each of the three hand-computed steps.  User
    # 2 is a dummy, so toggling only that bit never changes F or Psi.
    joint_f = {"additive": -2.0, "synergy": 2.0, "antagonistic": -4.0}
    for kind, profile in product(joint_f, product((0, 1), repeat=3)):
        u0, u1, dummy = profile
        value = joint_f[kind] if u0 and u1 else -float(u0 + u1)
        without_dummy = (u0, u1, 0)
        value_without_dummy = (
            joint_f[kind]
            if without_dummy[0] and without_dummy[1]
            else -float(without_dummy[0] + without_dummy[1])
        )
        assert value == value_without_dummy
        psi = value - (-float(u0)) - (-float(u1))
        assert psi == (joint_f[kind] + 2.0 if u0 and u1 else 0.0)
    assert kappa_normalization_bits(2.0) == pytest.approx(60.16)
    reporting_credit = pair_reporting_credit(
        psi_normalized=2.0, coalition_users=(0, 1), roster=(0, 1, 2)
    )
    assert reporting_credit == {0: 1.0, 1: 1.0, 2: 0.0}
    shapley = exact_shapley_reporting_credit(
        coalition_users=(0, 1),
        subset_values={
            frozenset(): 0.0,
            frozenset({0}): -1.0,
            frozenset({1}): -1.0,
            frozenset({0, 1}): 2.0,
        },
        roster=(0, 1, 2),
    )
    assert shapley == {0: 1.0, 1: 1.0, 2: 0.0}
    dummy_row = _coalition_row("synergy", tmp_count=3, members=(0, 1, 2))
    assert float.fromhex(dummy_row.psi_normalized_hex) == 2.0
    assert float.fromhex(dummy_row.objective_delta_normalized_hex) == 1.0
    assert _coalition_row("synergy", tmp_count=5).capped_decomposition is True

    def projection(index: int, *, survives: bool) -> OffsetProjection:
        return OffsetProjection(
            offset_index=index,
            valid=True,
            survives=survives,
            outcome=_outcome(physical_f=0.0),
            background_power_recomputed=True,
            required_power_w=0.5,
            power_cap_w=1.0,
            min_decoding_margin_db=1.0,
            mean_acm_se_bit_s_hz=1.0,
        )

    future = c2_persistence_forecast(
        (projection(1, survives=True), projection(2, survives=False), projection(3, survives=True)),
        tuple(projection(index, survives=True) for index in (1, 2, 3)),
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=2,
    )
    assert future.lost_offsets == 2
    assert future.normalized_total == -2

    shard = write_coalition_shard(tmp_path / "c3.jsonl", (synergy, antagonistic, additive))
    reopened = read_coalition_shard(shard.path)
    assert reopened.rows == shard.rows
    batch = CoalitionBatch.create((reopened,))
    model = _model_from_batch(batch)
    tables = _tables()
    catalogue = tuple(product((0, 1), repeat=3))
    legal = lambda profile: profile in catalogue
    guard = lambda profile: True
    exact_synergy = lambda profile: 2.0 if profile[0] == profile[1] == 1 else 0.0
    exact_antagonistic = lambda profile: -1.0 if profile[0] == profile[1] == 1 else 0.0
    s0 = ProfileSelector("S0")
    assert s0.select(
        base_profile=(0, 0, 0), tables=tables, catalogue=catalogue,
        jointly_legal=legal, service_guard=guard, model=model,
        coalition_context=_profile_contexts("synergy"), exact_psi=exact_synergy,
    ).profile == (1, 1, 0)
    assert s0.select(
        base_profile=(0, 0, 0), tables=tables, catalogue=catalogue,
        jointly_legal=legal, service_guard=guard, model=model,
        coalition_context=_profile_contexts("antagonistic"), exact_psi=exact_antagonistic,
    ).profile == (0, 0, 0)
    assert s0.select(
        base_profile=(0, 0, 0), tables=tables, catalogue=catalogue,
        jointly_legal=legal, service_guard=guard, model=model,
        coalition_context=_profile_contexts("synergy"), exact_psi=exact_synergy,
        knockout_route="C3",
    ).profile == (0, 0, 0)

    # Separately decisive additive factors exercise the other oracle DROPs.
    positive_tables = tuple(
        replace(table, q1_states=((0.0,), (1.0,)), q2_states=((0.0,), (1.0,)))
        if table.user_id == 0 else table
        for table in tables
    )
    one_move_catalogue = ((0, 0, 0), (1, 0, 0))
    for route in ("C1", "C2"):
        route_model = V1ThreeRouteModel(
            LinearHead(np.asarray([1.0 if route == "C1" else 0.0]), 0.0),
            LinearHead(np.asarray([1.0 if route == "C2" else 0.0]), 0.0),
            model.psi.clone(),
        )
        kwargs = dict(
            base_profile=(0, 0, 0), tables=positive_tables,
            catalogue=one_move_catalogue, jointly_legal=lambda profile: True,
            service_guard=lambda profile: True, model=route_model,
            coalition_context=_profile_contexts("additive"), exact_psi=lambda profile: 0.0,
        )
        assert s0.select(**kwargs).profile == (1, 0, 0)
        assert s0.select(**kwargs, knockout_route=route).profile == (0, 0, 0)

    orchestrator = V1LineageOrchestrator(
        learner_seed=101,
        q1_batch=_pair("C1"),
        q2_batch=_pair("C2"),
        c3_batch=batch,
        neutral_sources=default_synthetic_neutral_sources(),
        learning_rate=0.001,
    )
    initial = orchestrator.models["DROP_C3"].psi.output_weights.copy()
    orchestrator.train_epoch()
    assert isinstance(orchestrator.models["DROP_C3"].psi, SetInteractionHead)
    assert not np.array_equal(initial, orchestrator.models["DROP_C3"].psi.output_weights)
    assert orchestrator.checkpoint_payload()["source_map"]["DROP_C3"]["C3"] == "neutral"
    neutral_digests = tuple(
        (route, source.digest)
        for route, source in sorted(default_synthetic_neutral_sources().items())
    )
    experiments = (
        LearnedNeutralSourceExperiment(
            "mcrl-v025-learned-neutral-source-experiment-v1",
            ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL", "BASELINE"),
            neutral_digests,
            True,
            "informative source training improved pooled EE relative to the specified neutral source",
        ),
        OracleFactorScoreRemovalExperiment(
            "mcrl-v025-oracle-factor-score-removal-v1", ("C1", "C2", "C3"), True
        ),
        CheckpointKnockoutExperiment(
            "mcrl-v025-checkpoint-knockout-v1", _digest("checkpoint"), ("C1", "C2", "C3"), True
        ),
        ArchitectureRemovalExperiment("mcrl-v025-architecture-removal-v1"),
    )
    assert len({experiment.schema for experiment in experiments}) == 4


def test_T2_information_twins_reversal_and_additive_placebo(tmp_path) -> None:
    rows = tuple(_coalition_row(kind) for kind in ("synergy", "antagonistic", "additive"))
    batch = CoalitionBatch.create((write_coalition_shard(tmp_path / "twins.jsonl", rows),))
    model = _model_from_batch(batch)
    assert model.interaction(_context("synergy", ())) == 0.0
    assert model.interaction(_context("synergy", (0,))) == 0.0
    assert model.interaction(_context("synergy", (0, 1))) == pytest.approx(2.0, abs=1e-6)
    assert model.interaction(_context("antagonistic", (0, 1))) == pytest.approx(-1.0, abs=1e-6)
    ordered_context = _context("synergy", (0, 1))
    assert model.interaction(replace(ordered_context, members=tuple(reversed(ordered_context.members)))) == pytest.approx(
        model.interaction(ordered_context), abs=1e-12
    )

    catalogue = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0))
    selector = ProfileSelector("S3")
    choose = lambda kind, relabel=0, omit=False: selector.select(
        base_profile=(0, 0, 0), tables=_tables(relabel=relabel), catalogue=catalogue,
        jointly_legal=lambda profile: profile in catalogue,
        service_guard=lambda profile: True, model=model,
        coalition_context=_profile_contexts(kind, relabel=relabel, omit=omit),
    ).profile
    assert choose("synergy") == (1, 1, 0)
    assert choose("antagonistic") == (0, 0, 0)
    assert choose("synergy", omit=True) == choose("antagonistic", omit=True)

    # Post-decision poison and hidden legacy reset state are absent from the
    # builder, so changing them cannot affect current features/actions.
    current_before = canonical_sha256(_context("synergy", (0, 1)).payload())
    poisoned_future_fading = 1e300
    poisoned_hidden_reset = object()
    del poisoned_future_fading, poisoned_hidden_reset
    assert canonical_sha256(_context("synergy", (0, 1)).payload()) == current_before
    anchor = make_synthetic_anchors()[0]
    poisoned_anchor = SimpleNamespace(
        **{
            field: getattr(anchor, field)
            for field in anchor.__dataclass_fields__
        },
        realised_future_fading=1e300,
        post_decision_outcome={"bits": -999},
        hidden_legacy_reset_state=object(),
    )
    assert extract_source_rows(poisoned_anchor) == extract_source_rows(anchor)
    assert choose("synergy", relabel=9000) == choose("synergy")

    source_rows = extract_source_rows(anchor)
    HeadsInformation(
        anchor_id=anchor.anchor_id,
        decision_time_ns=anchor.decision_time_ns,
        user_id=anchor.user_id,
        legal_actions=tuple(row.action for row in source_rows),
        q1_rows=tuple(row.q1_state for row in source_rows),
        q2_rows=tuple(row.q2_state for row in source_rows),
        incumbent_context_nominal_decoding_margin_db=2.0,
        current_nominal_geometry_sha256=_digest("geometry"),
        own_history_sha256=_digest("history"),
        previous_committed_excluding_focal_sha256=_digest("background"),
        derived_feature_schema_sha256=_digest("schemas"),
    )
    catalogue_profile = CatalogueProfile(((0, PhysicalAction(None, None)),))
    catalogue_digest = canonical_sha256([catalogue_profile.payload()])
    CoordinatorInformation(
        anchor_id=anchor.anchor_id,
        decision_time_ns=anchor.decision_time_ns,
        global_nominal_geometry_sha256=_digest("global-geometry"),
        beam_specific_cross_gains_sha256=_digest("cross-gains"),
        legal_sets_sha256=_digest("legal-sets"),
        previous_committed_sha256=_digest("previous"),
        references=ReferenceProfiles((PhysicalAction(None, None),), (PhysicalAction(1, 1),)),
        catalogue=(catalogue_profile,),
        catalogue_sha256=catalogue_digest,
        nominal_model_sha256=_digest("nominal-model"),
        nominal_outputs=(NominalProfileOutput(
            profile_sha256=canonical_sha256(catalogue_profile.payload()),
            joint_load=(("beam", 0.0),), coupled_powers_w=(("beam", 0.0),),
            interference_w=(("beam", 0.0),), activation=(("beam", False),),
            service_by_user=((0, False),), bits=0.0, energy_j=0.0,
            continuation_normalized=0.0,
        ),),
    )

    interfaces = {
        arm: ArmInformationInterface(
            arm=arm, anchor_id="a", decision_time_ns=1,
            primitive_access_sha256=_digest("primitive"),
            forecast_method_sha256=_digest("forecast"),
            physical_identity_schema_sha256=_digest("identity"),
            catalogue_sha256=_digest("catalogue"), joint_search_sha256=_digest("search"),
            guards_sha256=_digest("guards"), tie_breaking_sha256=_digest("ties"),
            validation_sha256=_digest("validation"), deadline_sha256=_digest("deadline"),
            fallback_sha256=_digest("fallback"), learned_pruning=False,
        )
        for arm in (
            "FULL", "DROP_C1", "DROP_C2", "DROP_C3",
            "ALL_NEUTRAL_CONTROL", "BASELINE", "S0", "S_UNI",
        )
    }
    matched_arms = tuple(interfaces)
    assert len(authenticate_matched_catalogues(interfaces, required_arms=matched_arms)) == 64
    with pytest.raises(StageCContractError, match="catalogue_sha256"):
        authenticate_matched_catalogues(
            {**interfaces, "DROP_C3": replace(interfaces["DROP_C3"], catalogue_sha256=_digest("bad"))},
            required_arms=matched_arms,
        )

    legacy_model = ThreeRouteModel(
        {
            "C1": LinearHead(np.asarray([1.0]), 0.0),
            "C2": LinearHead(np.asarray([0.0]), 0.0),
            "C3": LinearHead(np.asarray([0.0, 0.0]), 0.0),
        }
    )
    two_tables = _tables()[:2]
    adapter = DeploymentAdapter(deadline_s=0.02)
    positive_tables = tuple(
        replace(table, q1_states=((0.0,), (1.0,))) for table in two_tables
    )
    repaired_a0 = construct_reference_proposal(
        model=legacy_model,
        tables=positive_tables,
        catalogue=((0, 0), (1, 0), (0, 1), (1, 1)),
        jointly_legal=lambda profile: profile != (1, 1),
    )
    assert repaired_a0 == (1, 0)
    decision = adapter.select(
        model=legacy_model, tables=positive_tables, base_profile=(0, 0),
        catalogue=((0, 0), (1, 0), (0, 1), (1, 1)),
        jointly_legal=lambda profile: profile != (1, 1),
        resolve_profile=lambda profile: ResolvedProfile(profile, 2),
    )
    assert decision.profile != (1, 1) and decision.jointly_legal

    started = time.monotonic()
    timeout = adapter.select_runner_timed(
        model=legacy_model, tables=positive_tables, base_profile=(0, 0), catalogue=((0, 0),),
        jointly_legal=lambda profile: True,
        resolve_profile=lambda profile: ResolvedProfile(profile, 2),
        coordinator=lambda **_kwargs: (time.sleep(0.10) or 0.0),
    )
    assert timeout.profile == (0, 0)
    assert timeout.fallback_reason == "runner_deadline_cancel"
    assert time.monotonic() - started < 0.08
    prep_timeout = adapter.select_with_preparation(
        model=legacy_model,
        prepare=lambda: (time.sleep(0.10) or (positive_tables, ((0, 0),))),
        base_profile=(0, 0),
        jointly_legal=lambda profile: True,
        resolve_profile=lambda profile: ResolvedProfile(profile, 2),
    )
    assert prep_timeout.profile == (0, 0)
    assert prep_timeout.fallback_reason == "runner_deadline_cancel"

    placebo = CoalitionBatch.create(
        (write_coalition_shard(tmp_path / "placebo.jsonl", (rows[2],)),)
    )
    placebo_model = _model_from_batch(placebo)
    assert abs(placebo_model.interaction(_context("additive", (0, 1)))) < 1e-7
    s3_profile = ProfileSelector("S3").select(
        base_profile=(0, 0, 0), tables=_tables(), catalogue=catalogue,
        jointly_legal=lambda profile: True, service_guard=lambda profile: True,
        model=placebo_model, coalition_context=_profile_contexts("additive"),
    ).profile
    suni_profile = ProfileSelector("S_UNI").select(
        base_profile=(0, 0, 0), tables=_tables(), catalogue=catalogue,
        jointly_legal=lambda profile: True, service_guard=lambda profile: True,
        exact_nominal_score=lambda profile: -0.5 * sum(profile[:2]),
    ).profile
    assert s3_profile == suni_profile == (0, 0, 0)


class _ReceiptEvaluator:
    action = PhysicalAction(1, 1)

    @classmethod
    def initial(cls, *, unit, arm):
        del unit, arm
        return InitialTemporalState((cls.action,), frozenset({0}))

    def __call__(self, *, unit, arm, model, step_index, previous_profile):
        del model, step_index, previous_profile
        energy = 1.0 if unit.world_seed % 2 else 4.0
        ee = 10.0
        if arm in {"DROP_C1", "FULL"}:
            bits = ee * energy
        elif arm == "DROP_C2":
            bits = 0.0
        elif arm == "DROP_C3":
            bits, energy = 0.0, 0.0
        else:
            bits = 9.0 * energy
        return StepOutcome(
            bits=bits, energy_components_j={"total": energy}, user_ids=(0,),
            profile=(self.action,), complete_service=(True,), decoding_user_seconds=1.0,
            useful_user_seconds=1.0, opportunity_user_seconds=1.0, jointly_legal=True,
        )


def _unit(date: str, seed: int, world: int) -> AllocationUnit:
    return AllocationUnit(
        experiment_id="T3", panel_id="synthetic", cell_id="a-r0",
        unit_id=f"{date}-{seed}-{world}", world_id=f"w/{date}/{seed}/{world}",
        resolved_start_utc=f"{date}T00:00:00Z", tle_date=date, split="TRAIN", role="synthetic",
        archive_digest=_digest("archive"), provider_digest=_digest("provider"),
        launch_digest=_digest("launch"), code_digest=_digest("code"),
        physics_digest=_digest("physics"), catalogue_digest=_digest("catalogue"),
        deployment_capability_digest=_digest("capability"), setting_digest=_digest("setting"),
        calibration_digest=_digest("calibration"), learner_seed=seed, world_seed=world,
    )


def test_T3_crossed_cluster_real_merger_coverage_and_power(tmp_path) -> None:
    units = tuple(
        _unit(date, seed, world)
        for date in ("2026-01-01", "2026-01-02", "2026-01-03")
        for seed in (5, 12)
        for world in (1, 2)
    )
    manifest = AllocationManifest.create(units, bootstrap_draws=79, bootstrap_seed=31)
    evaluator = _ReceiptEvaluator()
    dummy = ThreeRouteModel(
        {route: LinearHead(np.zeros(1), 0.0) for route in ("C1", "C2", "C3")}
    )
    models = {arm: dummy for arm in LEARNED_ARMS}
    conformance_runner = EvaluationRunner(
        manifest=manifest, registry=AttemptRegistry(tmp_path / "conformance.jsonl"),
        evaluator=evaluator, initial_temporal_state=evaluator.initial,
        output_directory=tmp_path / "conformance", steps=1,
    )
    conformance = conformance_runner.conformance_suite(unit=units[0], models=models)
    registry = AttemptRegistry(tmp_path / "attempts.jsonl")
    runner = EvaluationRunner(
        manifest=manifest, registry=registry, evaluator=evaluator,
        initial_temporal_state=evaluator.initial, output_directory=tmp_path / "receipts", steps=1,
    )
    receipts = [runner.run_unit(unit=unit, models=models, conformance=conformance) for unit in units]
    report = merge_receipts(receipts, manifest=manifest, registry=registry)
    assert report["contrasts"]["DROP_C1"]["point_estimates"]["ee_relative"] == 0.0
    assert report["pooled_additive_totals"]["DROP_C2"]["bits_hex"] == 0.0.hex()
    assert report["contrasts"]["DROP_C3"]["bootstrap"]["undefined_draws"]["ee_relative"] == 79
    assert report["bootstrap"].startswith("primary two-way pigeonhole")

    # Missing one crossed cell is not silently treated as independent replication.
    clusters = synthetic_crossed_clusters(
        date_count=3, seed_count=2, date_sd=0.03, seed_sd=0.01,
        true_relative_gain=(0.02, 0.02, 0.02), rng=np.random.default_rng(7),
    )
    clusters.pop(next(iter(clusters)))
    contrasts, claim = infer_cluster_totals(
        clusters, bootstrap_draws=19, bootstrap_seed=8, include_supplementary=False,
    )
    assert contrasts["DROP_C1"]["bootstrap"]["status"].startswith("UNDEFINED")
    assert claim["decision"] == "CLAIM_FAIL"

    qos_clusters = synthetic_crossed_clusters(
        date_count=160, seed_count=12, date_sd=0.0, seed_sd=0.0,
        true_relative_gain=(0.02, 0.02, 0.02), rng=np.random.default_rng(8), qos_failure=True,
    )
    _contrasts, qos_claim = infer_cluster_totals(
        qos_clusters, bootstrap_draws=49, bootstrap_seed=9, include_supplementary=False,
    )
    assert qos_claim["decision"] == "CLAIM_FAIL"

    calibration = crossed_inference_calibration(repetitions=64, bootstrap_draws=149)
    assert set(calibration["coverage"]) == {
        "date_sd_0.03_seed_sd_0.01",
        "date_sd_0.05_seed_sd_0.01",
        "date_sd_0.10_seed_sd_0.01",
    }
    for result in calibration["coverage"].values():
        assert result["normal_95_half_width"] > 0.0
        assert abs(result["estimate"] - 0.95) <= 2 * result["normal_95_half_width"] + 0.02
    power = calibration["power_date_sd_0.05_seed_sd_0.01"]
    assert power["5"]["interval_coverage"]["normal_95_half_width"] > 0.0
    assert power["12"]["interval_coverage"]["normal_95_half_width"] > 0.0
    assert power["12"]["conjunction_power"]["estimate"] > power["5"]["conjunction_power"]["estimate"]
    for seed_count, expected_component, expected_conjunction in (
        ("5", 0.70, 0.34), ("12", 0.86, 0.64)
    ):
        for key, expected in (
            ("component_power", expected_component),
            ("conjunction_power", expected_conjunction),
        ):
            observed = power[seed_count][key]
            assert abs(observed["estimate"] - expected) <= 2 * observed["normal_95_half_width"]
    assert calibration["least_favourable_conjunction_null"]["estimate"] <= 0.10
    assert "Monte Carlo uncertainty" in calibration["simulation_uncertainty"]
