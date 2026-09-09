"""Tiny synthetic-only fixture connecting Stage C end to end.

This module never imports the TLE environment or a real-world provider.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from mcrl.physics_v025.targets import NetworkOutcome

from .canonical import StageCContractError, canonical_sha256, write_once_json
from .deployment import (
    ProfileSelector,
    ResolvedProfile,
    UserActionTable,
    deployment_capability_manifest,
    select_s_uni,
)
from .interfaces import (
    ArmInformationInterface,
    CatalogueProfile,
    CoordinatorInformation,
    NominalProfileOutput,
    ReferenceProfiles,
    authenticate_matched_catalogues,
)
from .evaluation import (
    AllocationManifest,
    AllocationUnit,
    AttemptRegistry,
    EvaluationRunner,
    InitialTemporalState,
    StepOutcome,
)
from .coalitions import (
    AffectedBeamContext,
    CoalitionContext,
    CoalitionMember,
    CoalitionShard,
    build_coalition_row,
    write_coalition_shard,
)
from .learner import (
    LEARNER_SEEDS,
    CoalitionBatch,
    V1LineageOrchestrator,
    V1ThreeRouteModel,
    build_pairwise_batches,
    default_synthetic_neutral_sources,
)
from .experiments import LearnedNeutralSourceExperiment, bind_experiment
from .merge import merge_receipts, write_terminal_report
from .shards import write_source_shard
from .state import (
    ActionEvaluation,
    ForecastObservation,
    PhysicalAction,
    Q1_FEATURES,
    Q2_FEATURES,
    SourceRow,
    extract_source_rows,
    seal_action_evaluation,
)


def _digest(label: str) -> str:
    return canonical_sha256({"synthetic": label})


@dataclass(frozen=True, slots=True)
class SyntheticAnchor:
    world_id: str
    split: str
    world_seed: int
    anchor_id: str
    anchor_index: int
    decision_time_utc: str
    decision_time_ns: int
    user_id: int
    setting_id: str
    code_digest: str
    physics_digest: str
    launch_digest: str
    catalogue_digest: str
    setting_digest: str
    calibration_digest: str
    provider_digest: str
    archive_digest: str
    allocation_manifest_digest: str
    lambda_bits_per_j: float
    eta_ref_bits_per_j: float
    kappa_normalization_bits: float
    base_action_index: int
    actions: Sequence[ActionEvaluation]


def make_synthetic_anchors() -> tuple[SyntheticAnchor, ...]:
    forecasts = tuple(
        ForecastObservation(True, True, 4.0 + offset, 2.0 + 0.1 * offset)
        for offset in range(3)
    )
    anchors: list[SyntheticAnchor] = []
    source_provenance = _digest("synthetic-tape-adapter-visible-primitives-v1")
    forecast_method = _digest("synthetic-nominal-three-offset-forecast-v1")
    seal = lambda item: seal_action_evaluation(
        item,
        source_provenance_sha256=source_provenance,
        forecast_method_sha256=forecast_method,
    )
    for anchor_index in range(2):
        for user_id in range(2):
            common = {
                "refresh_phase": anchor_index,
                "missing_incumbent": False,
                "candidate_current_nominal_decoding_margin_db": 2.0,
                "incumbent_nominal_decoding_margin_db": 2.0,
                "forecasts": forecasts,
            }
            base = seal(ActionEvaluation(
                action=PhysicalAction(100 + user_id, 10 + user_id),
                nominal_sinr_margin_at_rate_target_db=2.0,
                nominal_required_power_over_cap=0.7,
                nominal_mode_spectral_efficiency=2.0,
                background_occupancy_excluding_focal=1,
                beam_active_before_focal=True,
                satellite_active_before_focal=True,
                off_axis_angle_rad=0.1,
                remaining_d2_time_s=90.0,
                remaining_visibility_time_s=100.0,
                previous_served_association_for_action=True,
                previous_served_load_for_action=1,
                previous_beam_active_for_action=True,
                previous_satellite_active_for_action=True,
                previous_beam_max_rf_over_cap=0.7,
                forecast_se_trend_bit_s_hz_per_s=0.0,
                required_power_cap_margin_w=0.5,
                c1_label_bits=0.0,
                c1_phi_difference=0.0,
                c2_label_bits=0.0,
                **common,
            ))
            candidate = seal(ActionEvaluation(
                action=PhysicalAction(200 + user_id, 20 + user_id),
                nominal_sinr_margin_at_rate_target_db=8.0 + user_id,
                nominal_required_power_over_cap=0.45,
                nominal_mode_spectral_efficiency=3.2,
                background_occupancy_excluding_focal=0,
                beam_active_before_focal=False,
                satellite_active_before_focal=False,
                off_axis_angle_rad=0.03,
                remaining_d2_time_s=115.0,
                remaining_visibility_time_s=118.0,
                previous_served_association_for_action=False,
                previous_served_load_for_action=0,
                previous_beam_active_for_action=False,
                previous_satellite_active_for_action=False,
                previous_beam_max_rf_over_cap=0.0,
                forecast_se_trend_bit_s_hz_per_s=0.02,
                required_power_cap_margin_w=0.9,
                c1_label_bits=120.0 + user_id,
                c1_phi_difference=0.0,
                c2_label_bits=80.0 + user_id,
                **{
                    **common,
                    "candidate_current_nominal_decoding_margin_db": 8.0 + user_id,
                },
            ))
            null = seal(replace(
                base,
                action=PhysicalAction(None, None),
                nominal_sinr_margin_at_rate_target_db=0.0,
                nominal_required_power_over_cap=0.0,
                nominal_mode_spectral_efficiency=0.0,
                previous_served_association_for_action=False,
                previous_served_load_for_action=0,
                previous_beam_active_for_action=False,
                previous_satellite_active_for_action=False,
                previous_beam_max_rf_over_cap=0.0,
                missing_incumbent=True,
                incumbent_nominal_decoding_margin_db=0.0,
                required_power_cap_margin_w=0.0,
                c1_label_bits=-20.0,
                c2_label_bits=-20.0,
            ))
            anchors.append(
                SyntheticAnchor(
                    world_id="V025_SYNTHETIC/source/1",
                    split="TRAIN",
                    world_seed=771,
                    anchor_id=f"source-{anchor_index}-user-{user_id}",
                    anchor_index=anchor_index,
                    decision_time_utc=f"2026-01-0{anchor_index + 1}T00:00:00Z",
                    decision_time_ns=anchor_index * 30_080_000_000,
                    user_id=user_id,
                    setting_id="a-r0",
                    code_digest=_digest("stagec-code"),
                    physics_digest=_digest("synthetic-physics"),
                    launch_digest=_digest("synthetic-launch"),
                    catalogue_digest=_digest("synthetic-catalogue"),
                    setting_digest=_digest("setting"),
                    calibration_digest=_digest("calibration"),
                    provider_digest=_digest("fixture-provider"),
                    archive_digest=_digest("no-real-archive"),
                    allocation_manifest_digest=_digest("source-allocation"),
                    lambda_bits_per_j=10.0,
                    eta_ref_bits_per_j=10.0,
                    kappa_normalization_bits=100.0,
                    base_action_index=0,
                    actions=(base, candidate, null),
                )
            )
    return tuple(anchors)


class TinySyntheticEvaluator:
    """A deterministic two-user joint-feasibility fixture."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []

    @classmethod
    def selection_authority(
        cls, tables: Sequence[UserActionTable], base: tuple[int, ...]
    ) -> tuple[CoordinatorInformation, dict[str, ArmInformationInterface], str, tuple[tuple[int, ...], ...]]:
        catalogue = ((0, 0), (1, 0), (0, 1), (1, 1))
        catalogue_profiles = tuple(
            CatalogueProfile(tuple(
                (table.user_id, table.actions[index])
                for table, index in zip(tables, profile, strict=True)
            ))
            for profile in catalogue
        )
        catalogue_sha256 = canonical_sha256([profile.payload() for profile in catalogue_profiles])
        source_provenance = _digest("synthetic-tape-adapter-visible-primitives-v1")
        coordinator = CoordinatorInformation(
            anchor_id="synthetic-evaluation-anchor",
            decision_time_ns=0,
            global_nominal_geometry_sha256=_digest("global-geometry"),
            beam_specific_cross_gains_sha256=_digest("cross-gains"),
            legal_sets_sha256=_digest("legal-sets"),
            previous_committed_sha256=_digest("previous-committed"),
            references=ReferenceProfiles(
                tuple(table.actions[index] for table, index in zip(tables, base, strict=True)),
                tuple(table.actions[0] for table in tables),
            ),
            catalogue=catalogue_profiles,
            catalogue_sha256=catalogue_sha256,
            nominal_model_sha256=_digest("nominal-model"),
            source_provenance_sha256=source_provenance,
            forecast_method_sha256=_digest("synthetic-nominal-three-offset-forecast-v1"),
            nominal_outputs=tuple(
                NominalProfileOutput(
                    profile_sha256=canonical_sha256(profile.payload()),
                    joint_load=(("beam", float(sum(index == 1 for index in raw))),),
                    coupled_powers_w=(("beam", 1.0),),
                    interference_w=(("beam", 0.0),),
                    activation=(("beam", True),),
                    service_by_user=((0, True), (1, True)),
                    bits=1000.0,
                    energy_j=9.0,
                    continuation_normalized=0.0,
                )
                for raw, profile in zip(catalogue, catalogue_profiles, strict=True)
            ),
        )
        interfaces = {
            arm: ArmInformationInterface(
                arm=arm,
                anchor_id=coordinator.anchor_id,
                decision_time_ns=coordinator.decision_time_ns,
                primitive_access_sha256=_digest("primitive-access"),
                forecast_method_sha256=coordinator.forecast_method_sha256,
                physical_identity_schema_sha256=_digest("physical-identity"),
                catalogue_sha256=catalogue_sha256,
                joint_search_sha256=_digest("joint-search"),
                guards_sha256=_digest("guards"),
                tie_breaking_sha256=_digest("tie-breaking"),
                validation_sha256=_digest("validation"),
                deadline_sha256=_digest("deadline"),
                fallback_sha256=_digest("fallback"),
                source_provenance_sha256=source_provenance,
                learned_pruning=False,
            )
            for arm in ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL", "BASELINE", "S0", "S_UNI")
        }
        digest = authenticate_matched_catalogues(interfaces, required_arms=tuple(interfaces))
        return coordinator, interfaces, digest, catalogue

    @staticmethod
    def tables() -> tuple[UserActionTable, ...]:
        result: list[UserActionTable] = []
        for user_id in range(2):
            q1_base = tuple(0.0 for _ in Q1_FEATURES)
            q2_base = tuple(0.0 for _ in Q2_FEATURES)
            q1_candidate = tuple(
                1.0 if index in {0, 2, 7} else 0.0
                for index in range(len(Q1_FEATURES))
            )
            q2_candidate = tuple(
                1.0 if index in {1, 3, 12} else 0.0
                for index in range(len(Q2_FEATURES))
            )
            result.append(
                UserActionTable(
                    user_id=user_id,
                    actions=(
                        PhysicalAction(100 + user_id, 10 + user_id),
                        PhysicalAction(200 + user_id, 20 + user_id),
                        PhysicalAction(None, None),
                    ),
                    action_mask=(True, True, True),
                    q1_states=(q1_base, q1_candidate, q1_base),
                    q2_states=(q2_base, q2_candidate, q2_base),
                )
            )
        return tuple(result)

    @classmethod
    def initial_temporal_state(
        cls, *, unit: AllocationUnit, arm: str
    ) -> InitialTemporalState:
        del unit, arm
        tables = cls.tables()
        return InitialTemporalState(
            profile=tuple(table.actions[0] for table in tables),
            ever_served_user_ids=frozenset(table.user_id for table in tables),
        )

    def __call__(
        self,
        *,
        unit: AllocationUnit,
        arm: str,
        model: V1ThreeRouteModel | None,
        step_index: int,
        previous_profile: tuple[PhysicalAction, ...] | None,
    ) -> StepOutcome:
        self.calls.append((arm, unit.learner_seed, step_index))
        tables = self.tables()
        base = (0, 0)
        if arm in {"BASELINE", "NULL"}:
            profile = base
        elif arm == "S_UNI":
            coordinator, interfaces, matched, catalogue = self.selection_authority(tables, base)
            profile = ProfileSelector("S_UNI").select(
                base_profile=base,
                tables=tables,
                catalogue=catalogue,
                jointly_legal=lambda candidate: candidate != (1, 1),
                service_guard=lambda _candidate: True,
                exact_nominal_score=lambda candidate: float(
                    sum(action_index == 1 for action_index in candidate)
                ),
                coordinator_information=coordinator,
                arm_information_interfaces=interfaces,
                matched_information_sha256=matched,
            ).profile
        else:
            if model is None:
                raise StageCContractError(
                    "learned synthetic arm requires a model"
                )
            contexts = {
                profile: self.coalition_context(profile, tables)
                for profile in ((0, 0), (1, 0), (0, 1), (1, 1))
            }
            coordinator, interfaces, matched, catalogue = self.selection_authority(tables, base)
            selector = ProfileSelector("S0" if arm == "S0" else "S3")
            decision = selector.select_timed(
                deadline_s=10.0,
                model=model,
                tables=tables,
                catalogue=catalogue,
                base_profile=base,
                jointly_legal=lambda candidate: candidate != (1, 1),
                service_guard=lambda _candidate: True,
                coalition_context=contexts,
                exact_psi=(lambda profile: 2.0 if profile == (1, 1) else 0.0),
                coordinator_information=coordinator,
                arm_information_interfaces=interfaces,
                matched_information_sha256=matched,
                model_checkpoint_sha256=model.checkpoint_sha256,
            )
            profile = decision.profile
        identities = tuple(
            table.actions[action_index]
            for table, action_index in zip(tables, profile, strict=True)
        )
        changed = sum(action_index == 1 for action_index in profile)
        bits = 1000.0 + 40.0 * changed + 0.01 * unit.world_seed
        energy = {
            "pa": 6.0 + 0.1 * changed + 0.01 * (unit.world_seed % 7),
            "circuit": 2.0,
            "baseband": 1.0,
            "standby": 0.0,
        }
        return StepOutcome(
            bits=bits,
            energy_components_j=energy,
            user_ids=(0, 1),
            profile=identities,
            complete_service=(True, True),
            decoding_user_seconds=60.16,
            useful_user_seconds=60.16,
            opportunity_user_seconds=60.16,
            jointly_legal=True,
            coordinator_latency_s=0.001,
            selected_profile_differs_from_additive=changed == 2,
            rejected_harmful_joint_move=arm == "FULL" and changed == 0,
        )

    @staticmethod
    def coalition_context(
        profile: tuple[int, ...], tables: Sequence[UserActionTable]
    ) -> CoalitionContext:
        members = tuple(
            CoalitionMember(
                user_id=table.user_id,
                reference_action=table.actions[0],
                selected_action=table.actions[action_index],
                selected_q1_row=table.q1_states[action_index],
                incumbent_q1_row=table.q1_states[0],
                missing_incumbent=False,
            )
            for table, action_index in zip(tables, profile, strict=True)
            if action_index != 0
        )
        return CoalitionContext(
            anchor_id="synthetic-evaluation-anchor",
            reference_profile=tuple((table.user_id, table.actions[0]) for table in tables),
            members=members,
            affected_beams=(
                AffectedBeamContext(
                    beam_key="synthetic-beam",
                    occupancy_before=len(tables),
                    occupancy_after=len(tables),
                    active_before=True,
                    active_after=True,
                    shared_capacity=1.0,
                    interference_summary=0.0,
                    capacity_margin=1.0,
                ),
            ),
            global_resource_features=(0.0, 0.0, 1.0),
        )


def _synthetic_coalition_batch(
    output: Path, rows: Sequence[SourceRow]
) -> tuple[CoalitionBatch, CoalitionShard]:
    by_user = {
        row.user_id: row
        for row in rows
        if row.anchor_index == 0 and row.action_index == 1
    }
    reference_by_user = {
        row.user_id: row
        for row in rows
        if row.anchor_index == 0 and row.reference_action
    }
    context = CoalitionContext(
        anchor_id="source-coalition-0",
        reference_profile=tuple(
            (user, reference_by_user[user].action) for user in sorted(reference_by_user)
        ),
        members=tuple(
            CoalitionMember(
                user_id=user,
                reference_action=reference_by_user[user].action,
                selected_action=by_user[user].action,
                selected_q1_row=by_user[user].q1_state,
                incumbent_q1_row=reference_by_user[user].q1_state,
                missing_incumbent=False,
            )
            for user in sorted(by_user)
        ),
        affected_beams=(
            AffectedBeamContext(
                "synthetic-beam", 2, 2, True, True, 1.0, 0.0, 1.0
            ),
        ),
        global_resource_features=(1.0, 0.0, 0.0),
    )
    outcome = lambda bits: NetworkOutcome.build(
        bits=bits,
        joules=100.0,
        phi=0.0,
        decoding_availability=1.0,
        useful_availability=1.0,
    )
    coalition_row = build_coalition_row(
        context=context,
        reference_outcome=outcome(1000.0),
        unilateral_outcomes={user: outcome(900.0) for user in by_user},
        coalition_outcome=outcome(1000.0),
        world_id="V025_SYNTHETIC/source/coalition/1",
        world_seed=771,
        anchor_index=0,
        decision_time_utc="2026-01-01T00:00:00Z",
        decision_time_ns=0,
        setting_id="a-r0",
        lambda_bits_per_j=10.0,
        eta_ref_bits_per_j=10.0,
        kappa_normalization_bits=100.0,
        code_digest=_digest("stagec-code"),
        physics_digest=_digest("synthetic-physics"),
        catalogue_digest=_digest("synthetic-catalogue"),
        setting_digest=_digest("setting"),
        calibration_digest=_digest("calibration"),
        allocation_manifest_digest=_digest("source-allocation"),
    )
    shard = write_coalition_shard(output / "synthetic-coalitions.jsonl", (coalition_row,))
    return CoalitionBatch.create((shard,)), shard


def run_synthetic_pipeline(
    root: str | Path,
    *,
    epochs: int = 3,
    bootstrap_draws: int = 50,
) -> dict[str, object]:
    output = Path(root)
    output.mkdir(parents=True, exist_ok=True)
    rows = tuple(
        row
        for anchor in make_synthetic_anchors()
        for row in extract_source_rows(anchor)
    )
    shard = write_source_shard(output / "synthetic-source.jsonl", rows)
    batches = build_pairwise_batches((shard,))
    coalition_batch, coalition_shard = _synthetic_coalition_batch(output, rows)
    orchestrators = {
        seed: V1LineageOrchestrator(
            learner_seed=seed,
            q1_batch=batches["C1"],
            q2_batch=batches["C2"],
            c3_batch=coalition_batch,
            neutral_sources=default_synthetic_neutral_sources(),
        )
        for seed in LEARNER_SEEDS
    }
    for orchestrator in orchestrators.values():
        orchestrator.train(epochs)
        orchestrator.bind_checkpoint_identity()
    _coordinator, _interfaces, matched_information, _catalogue = TinySyntheticEvaluator.selection_authority(
        TinySyntheticEvaluator.tables(), (0, 0)
    )
    capability = deployment_capability_manifest(
        code_digest=_digest("stagec-code"),
        physics_digest=_digest("synthetic-physics"),
        catalogue_digest=_coordinator.catalogue_sha256,
        measured_end_to_end_latency_s=(0.001, 0.0012, 0.0011),
    )
    write_once_json(output / "deployment-capability.json", capability)
    neutral_digests = tuple(
        (route, source.digest)
        for route, source in sorted(default_synthetic_neutral_sources().items())
    )
    experiment = LearnedNeutralSourceExperiment(
        "mcrl-v025-learned-neutral-source-experiment-v1",
        tuple((*orchestrators[next(iter(orchestrators))].models, "BASELINE")),
        neutral_digests,
        True,
        "informative source training improved pooled EE relative to the specified neutral source",
    )
    binding = bind_experiment("V025_SYNTHETIC_E2E", experiment)
    units: list[AllocationUnit] = []
    for date_index, date in enumerate(("2026-01-10", "2026-01-11")):
        for seed in orchestrators:
            for world_replica in range(2):
                units.append(
                    AllocationUnit(
                        experiment_id="V025_SYNTHETIC_E2E",
                        panel_id="synthetic-panel",
                        cell_id="a-r0",
                        unit_id=f"d{date_index}-s{seed}-w{world_replica}",
                        world_id=(
                            f"V025_SYNTHETIC/eval/{date_index}/{seed}/{world_replica}"
                        ),
                        resolved_start_utc=f"{date}T00:00:00Z",
                        tle_date=date,
                        split="TRAIN",
                        role="synthetic",
                        archive_digest=_digest("no-real-archive"),
                        provider_digest=_digest("fixture-provider"),
                        launch_digest=_digest("synthetic-launch"),
                        code_digest=_digest("stagec-code"),
                        physics_digest=_digest("synthetic-physics"),
                        catalogue_digest=_coordinator.catalogue_sha256,
                        deployment_capability_digest=str(capability["manifest_sha256"]),
                        setting_digest=_digest("setting"),
                        calibration_digest=_digest("calibration"),
                        learner_seed=seed,
                        world_seed=9000 + 10 * date_index + world_replica,
                        experiment_schema=binding.schema,
                        experiment_definition_sha256=binding.definition_sha256,
                        experiment_execution_kind=binding.execution_kind,
                        experiment_checkpoint_sha256=binding.checkpoint_sha256,
                        matched_information_sha256=matched_information,
                        tle_provenance="nearest_epoch_retrospective_benchmark",
                    )
                )
    manifest = AllocationManifest.create(
        units,
        bootstrap_draws=bootstrap_draws,
        bootstrap_seed=20260908,
        experiment_bindings=(binding,),
        training_physics_digest=_digest("synthetic-physics"),
        baseline_implementation_sha256=_digest("synthetic-baseline-implementation"),
    )
    write_once_json(output / "allocation-manifest.json", manifest.payload())
    evaluator = TinySyntheticEvaluator()
    conformance_registry = AttemptRegistry(
        output / "CONFORMANCE-ATTEMPT-REGISTRY-2026-09.jsonl"
    )
    conformance_runner = EvaluationRunner(
        manifest=manifest,
        registry=conformance_registry,
        evaluator=evaluator,
        initial_temporal_state=evaluator.initial_temporal_state,
        output_directory=output / "conformance",
        steps=1,
    )
    conformance = conformance_runner.conformance_suite(
        unit=units[0], models=orchestrators[units[0].learner_seed].models
    )
    registry = AttemptRegistry(output / "ATTEMPT-REGISTRY-2026-09.jsonl")
    runner = EvaluationRunner(
        manifest=manifest,
        registry=registry,
        evaluator=evaluator,
        initial_temporal_state=evaluator.initial_temporal_state,
        output_directory=output / "receipts",
        steps=3,
    )
    receipt_paths: list[Path] = []
    for unit in units:
        receipt_paths.append(
            runner.run_unit(
                unit=unit,
                models=orchestrators[unit.learner_seed].models,
                conformance=conformance,
            )
        )
    physics_admission = {
        "decision": "HOLD",
        "reason": "synthetic fixtures confer no PHYSICS-GO authority",
    }
    report = merge_receipts(
        receipt_paths,
        manifest=manifest,
        registry=registry,
        bootstrap_draws=bootstrap_draws,
        physics_admission=physics_admission,
        artifact_digests={
            "source_shards": [
                {
                    "file_sha256": shard.file_sha256,
                    "rows_sha256": shard.rows_sha256,
                },
                {
                    "file_sha256": coalition_shard.file_sha256,
                    "rows_sha256": coalition_shard.rows_sha256,
                },
            ],
            "batches": {
                "C1": batches["C1"].digest,
                "C2": batches["C2"].digest,
                "C3": coalition_batch.digest,
            },
            "source_authority_sha256": next(
                iter(batches.values())
            ).source_authority_sha256,
            "checkpoints": {
                str(seed): canonical_sha256(orchestrator.checkpoint_payload())
                for seed, orchestrator in orchestrators.items()
            },
            "deployment_capability": [capability["manifest_sha256"]],
        },
        interface_assumptions=(
            "SyntheticAnchor stands in for one stage-4 per-anchor evaluation.",
            "Physical actions use (norad_id, beam_chain_id); slot indices are local only.",
            "The adapter supplies labels, masks, forecasts, and authority digests.",
            "Joint resolution is authoritative and never silently rewrites a profile.",
            "Synthetic fixtures confer no PHYSICS-GO authority.",
        ),
        controller_decide=(
            "COALITION-FEATURE-SCALES",
            "NEUTRAL-SOURCE-SEALS",
            "CATALOGUE-CB2",
            "FORMAL-ALLOCATION-MANIFEST",
            "OPERATIONAL-CAPABILITY-VALUES",
            "CAUSAL-OPERATIONAL-VARIANT",
        ),
    )
    report["synthetic"] = {
        "learner_seeds": sorted(orchestrators),
        "arms_per_seed": 6,
        "learned_arms_per_seed": 5,
        "external_baseline_per_seed": 1,
        "source_epochs": epochs,
        "steps_per_world": 3,
        "conformance": conformance,
        "evaluator_call_count": len(evaluator.calls),
    }
    write_terminal_report(output / "terminal-report.json", report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the V0.25 Stage-C synthetic-only end-to-end fixture"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--bootstrap-draws", type=int, default=50)
    arguments = parser.parse_args(argv)
    run_synthetic_pipeline(
        arguments.output,
        epochs=arguments.epochs,
        bootstrap_draws=arguments.bootstrap_draws,
    )
    return 0


__all__ = [
    "SyntheticAnchor",
    "TinySyntheticEvaluator",
    "make_synthetic_anchors",
    "run_synthetic_pipeline",
]


if __name__ == "__main__":
    raise SystemExit(main())
