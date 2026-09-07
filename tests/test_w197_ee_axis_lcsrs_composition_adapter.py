"""W-197 -- V0.23 held-out LC-SRS literal composition adapter."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


ADAPTER_PATH = (
    Path(__file__).resolve().parents[1]
    / ".scratch"
    / "multi-catfish-v023-c3-observability"
    / "v023_lcsrs_composition_adapter.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "v023_lcsrs_composition_adapter_test", ADAPTER_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
adapter = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = adapter
_SPEC.loader.exec_module(adapter)


def test_native_argmax_masks_illegal_actions_and_uses_lowest_exact_tie() -> None:
    scores = np.asarray(
        [[1.0, 1.0, 1000.0, -2.0], [0.0, 3.0, 3.0, 4.0]],
        dtype=np.float32,
    )
    mask = np.asarray(
        [[True, True, False, False], [False, True, True, False]],
        dtype=np.bool_,
    )

    receipt = adapter.native_masked_argmax(scores, mask)

    np.testing.assert_array_equal(receipt.actions, np.asarray([0, 1]))
    np.testing.assert_array_equal(receipt.exact_tie_count, np.asarray([2, 2]))
    assert not receipt.actions.flags.writeable


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class _FakeView:
    action_mask: np.ndarray
    reference_actions: np.ndarray
    content_digest: str

    def __post_init__(self) -> None:
        mask = np.array(self.action_mask, dtype=np.bool_, copy=True)
        references = np.array(self.reference_actions, dtype=np.int64, copy=True)
        mask.setflags(write=False)
        references.setflags(write=False)
        object.__setattr__(self, "action_mask", mask)
        object.__setattr__(self, "reference_actions", references)

    def verify(self) -> str:
        return self.content_digest


@dataclass(frozen=True)
class _FakeModel:
    digest: str


def _inference_anchor() -> tuple[object, object, object]:
    users, actions = 2, 28
    mask = np.zeros((users, actions), dtype=np.bool_)
    mask[:, :2] = True
    references = np.zeros(users, dtype=np.int64)
    q1 = np.zeros((users, actions), dtype=np.float32)
    q1[:, 0] = 1.0
    q1[:, 2] = 1000.0  # illegal and therefore never selectable
    q2 = np.zeros_like(q1)
    view_digest = _digest("view")
    view = _FakeView(mask.copy(), references.copy(), view_digest)
    declared = adapter.DeclaredAnchor(
        world=2026121705,
        phase=1,
        anchor_id="w2026121705:t1",
        predecision_sha256=_digest("predecision"),
        state_schema_sha256=_digest("state-schema"),
        state_sha256=_digest("state"),
        q12_snapshot_sha256=_digest("snapshot"),
        q12_model_sha256=_digest("q12-model"),
        q12_source_state_sha256=_digest("q12-state"),
        q12_event_sha256=_digest("event"),
        view_sha256=view_digest,
        topology_sha256=_digest("topology"),
        q1=q1,
        q2=q2,
        action_mask=mask,
        reference_actions=references,
        physical_keys=np.zeros((users, actions, 2), dtype=np.int64),
        teacher_q3=np.zeros((users, actions), dtype=np.float32),
        pairs=(),
    )
    replayed = adapter.ReplayedAnchor(
        handle=adapter.ImmutableAnchorHandle(
            token="fake-anchor-1", content_digest=_digest("handle")
        ),
        world=declared.world,
        phase=declared.phase,
        anchor_id=declared.anchor_id,
        predecision_sha256=declared.predecision_sha256,
        state_schema_sha256=declared.state_schema_sha256,
        state_sha256=declared.state_sha256,
        q12_snapshot_sha256=declared.q12_snapshot_sha256,
        q12_model_sha256=declared.q12_model_sha256,
        q12_source_state_sha256=declared.q12_source_state_sha256,
        q12_event_sha256=declared.q12_event_sha256,
        view_sha256=declared.view_sha256,
        topology_sha256=declared.topology_sha256,
        q1=declared.q1,
        q2=declared.q2,
        action_mask=declared.action_mask,
        reference_actions=declared.reference_actions,
        view=view,
    )
    model = _FakeModel(_digest("model"))
    fitted = adapter.AuthenticatedFitArtifact(
        held_out_world=declared.world,
        student_seed=2026135101,
        arm="INFORMED",
        preflight_manifest_sha256=_digest("preflight"),
        source_manifest_sha256=_digest("source-manifest"),
        fit_receipt_sha256=_digest("fit-receipt"),
        fit_receipt_content_sha256=_digest("fit-receipt-content"),
        model_bytes_sha256=_digest("model-bytes"),
        model_sha256=model.digest,
        source_index_sha256=_digest("source-index"),
        model=model,
    )
    return declared, replayed, fitted


def test_learned_inference_calls_q3_and_native_argmax_exactly_once() -> None:
    declared, replayed, fitted = _inference_anchor()
    q3_calls: list[object] = []
    argmax_calls: list[tuple[tuple[int, ...], tuple[int, ...]]] = []

    def q3_evaluator(request):
        q3_calls.append(request)
        assert {field.name for field in fields(request)}.isdisjoint(
            {"teacher", "teacher_q3", "targets", "labels", "pairs"}
        )
        result = np.zeros_like(declared.q1)
        result[:, 1] = 1.0  # exact tie with native action zero
        return result

    def selector(scores, mask):
        argmax_calls.append((scores.shape, mask.shape))
        return adapter.native_masked_argmax(scores, mask)

    selection = adapter.select_learned_once(
        declared=declared,
        replayed=replayed,
        fitted=fitted,
        q3_evaluator=q3_evaluator,
        native_selector=selector,
        model_digestor=lambda model: model.digest,
    )

    assert len(q3_calls) == 1
    assert len(argmax_calls) == 1
    np.testing.assert_array_equal(selection.actions, np.asarray([0, 0]))
    np.testing.assert_array_equal(selection.exact_tie_count, np.asarray([2, 2]))
    assert selection.q3_calls == selection.argmax_calls == 1


def test_replay_digest_mismatch_is_rejected_before_q3() -> None:
    declared, replayed, fitted = _inference_anchor()
    calls = 0

    def forbidden(_request):
        nonlocal calls
        calls += 1
        raise AssertionError("Q3 must not run for an unauthenticated replay")

    with pytest.raises(adapter.V023CompositionAdapterError, match="state_sha256"):
        adapter.select_learned_once(
            declared=declared,
            replayed=replace(replayed, state_sha256=_digest("different-state")),
            fitted=fitted,
            q3_evaluator=forbidden,
            model_digestor=lambda model: model.digest,
        )
    assert calls == 0


def test_replay_rejects_teacher_bearing_or_mutable_learned_view() -> None:
    _declared, replayed, _fitted = _inference_anchor()
    leaky = SimpleNamespace(
        action_mask=replayed.action_mask,
        reference_actions=replayed.reference_actions,
        content_digest=replayed.view_sha256,
        teacher_q3=np.zeros_like(replayed.q1),
        verify=lambda: replayed.view_sha256,
    )
    with pytest.raises(adapter.V023CompositionAdapterError, match="forbidden learned input"):
        replace(replayed, view=leaky)

    mutable_mask = np.array(replayed.action_mask, copy=True)
    mutable_references = np.array(replayed.reference_actions, copy=True)
    mutable = SimpleNamespace(
        action_mask=mutable_mask,
        reference_actions=mutable_references,
        content_digest=replayed.view_sha256,
        verify=lambda: replayed.view_sha256,
    )
    with pytest.raises(adapter.V023CompositionAdapterError, match="must be immutable"):
        replace(replayed, view=mutable)


def _physical_result(request, *, edit_action: bool = False):
    draws = 32
    users = request.actions.size
    actions = np.array(request.actions, copy=True)
    if edit_action:
        actions[0] = (actions[0] + 1) % 2
    bits = np.full((draws, users), 10.0, dtype=np.float64)
    energy = np.full(draws, 2.0, dtype=np.float64)
    served = np.ones((draws, users), dtype=np.bool_)
    nonmutation_names = (
        "environment",
        "rng",
        "q1",
        "q2",
        "q3",
        "matched_field",
    )
    before = np.asarray(
        [
            [
                _digest(f"{request.role}-{draw}-{name}").encode("ascii")
                for name in nonmutation_names
            ]
            for draw in range(draws)
        ],
        dtype="S64",
    )
    return adapter.PhysicalEvaluation(
        role=request.role,
        actions=actions,
        draw_index=np.arange(draws, dtype=np.int64),
        total_bits=np.sum(bits, axis=1),
        per_user_bits=bits,
        energy_j=energy,
        served=served,
        active_beam_counts=np.full(draws, 2, dtype=np.int64),
        active_beam_keys=np.tile(
            np.asarray([[[10, 0], [20, 0]]], dtype=np.int64), (draws, 1, 1)
        ),
        active_satellite_counts=np.ones(draws, dtype=np.int64),
        active_satellites=np.full((draws, 1), 10, dtype=np.int64),
        beam_power_w=np.ones((draws, 2), dtype=np.float64),
        action_sha256=adapter.action_vector_sha256(actions),
        common_field_digest=np.asarray(
            [_digest(f"pair-field-{draw}").encode("ascii") for draw in range(draws)],
            dtype="S64",
        ),
        nonmutation_names=nonmutation_names,
        nonmutation_before_sha256=before,
        nonmutation_after_sha256=before.copy(),
        nonmutation_flags=np.ones((draws, len(nonmutation_names)), dtype=np.bool_),
    )


def test_physical_boundary_receives_immutable_complete_vectors_without_repair() -> None:
    declared, replayed, fitted = _inference_anchor()
    requests: list[object] = []

    def q3_evaluator(_request):
        result = np.zeros_like(declared.q1)
        result[:, 1] = 2.0
        return result

    def physical(request):
        requests.append(request)
        with pytest.raises(ValueError):
            request.actions[0] = 27
        return _physical_result(request)

    result = adapter.compose_anchor_once(
        declared=declared,
        replayed=replayed,
        fitted=fitted,
        q3_evaluator=q3_evaluator,
        physical_evaluator=physical,
        model_digestor=lambda model: model.digest,
    )

    assert [request.role for request in requests] == [
        "ZERO_SURFACE_B",
        "INFORMED",
        "TEACHER_ORACLE",
    ]
    np.testing.assert_array_equal(result.learned.actions, np.asarray([1, 1]))
    np.testing.assert_array_equal(requests[1].actions, result.learned.actions)
    assert result.learned.argmax_calls == 1
    assert result.teacher_argmax_calls == 1


def test_physical_boundary_rejects_post_selection_action_edit() -> None:
    declared, replayed, fitted = _inference_anchor()

    def q3_evaluator(_request):
        return np.zeros_like(declared.q1)

    calls = 0

    def physical(request):
        nonlocal calls
        calls += 1
        return _physical_result(request, edit_action=(calls == 1))

    with pytest.raises(adapter.V023CompositionAdapterError, match="edited selected actions"):
        adapter.compose_anchor_once(
            declared=declared,
            replayed=replayed,
            fitted=fitted,
            q3_evaluator=q3_evaluator,
            physical_evaluator=physical,
            model_digestor=lambda model: model.digest,
        )


def test_physical_result_requires_named_frozen_state_receipts() -> None:
    declared, _replayed, _fitted = _inference_anchor()
    request = adapter.PhysicalEvaluationRequest(
        world=declared.world,
        phase=declared.phase,
        anchor_id=declared.anchor_id,
        role="ZERO_SURFACE_B",
        handle=adapter.ImmutableAnchorHandle(
            token="physical-names", content_digest=_digest("physical-names")
        ),
        actions=declared.reference_actions,
        draw_index=np.arange(32, dtype=np.int64),
    )
    valid = _physical_result(request)

    with pytest.raises(
        adapter.V023CompositionAdapterError, match="omits frozen fields"
    ):
        replace(valid, nonmutation_names=("environment", "rng"))


def _declared_pair() -> tuple[object, np.ndarray, np.ndarray]:
    users, actions, draws = 4, 28, 32
    baseline = np.zeros(users, dtype=np.int64)
    designated = np.asarray([1, 1], dtype=np.int64)
    profile_actions = np.repeat(baseline[None, None, :], draws * 4, axis=0).reshape(
        draws, 4, users
    )
    profile_actions[:, 1, 0] = designated[0]
    profile_actions[:, 2, 1] = designated[1]
    profile_actions[:, 3, 0:2] = designated
    profile_bits = np.zeros((draws, 4, users), dtype=np.float64)
    profile_bits[:, 0, :] = 10.0
    profile_bits[:, 1, :] = 7.5   # harmful 10 relative to 00
    profile_bits[:, 2, :] = 12.5  # beneficial 01 relative to 00
    profile_bits[:, 3, :] = 15.0
    energy = np.full((draws, 4), 2.0, dtype=np.float64)
    served = np.ones((draws, 4, users), dtype=np.bool_)
    fields_by_draw = np.asarray(
        [_digest(f"pair-field-{draw}").encode("ascii") for draw in range(draws)],
        dtype="S64",
    )
    target_by_draw = np.full((draws, 2), 2.0, dtype=np.float64)
    action_digest = np.empty((draws, 4), dtype="S64")
    for draw_index in range(draws):
        for profile_index in range(4):
            action_digest[draw_index, profile_index] = adapter.action_vector_sha256(
                profile_actions[draw_index, profile_index]
            ).encode("ascii")
    beam_keys = np.full((draws, 4, 2, 2), -1, dtype=np.int64)
    beam_keys[:, :, 0] = (10, 0)
    beam_keys[:, :, 1] = (20, 0)
    mechanics = adapter.PairSourceMechanics(
        target_by_draw=target_by_draw,
        profile_link_rate_bps=profile_bits * 10.0,
        profile_link_power_w=np.ones((draws, 4, users), dtype=np.float64),
        profile_link_sinr=np.ones((draws, 4, users), dtype=np.float64),
        profile_g_bits=np.sum(profile_bits, axis=2, dtype=np.float64),
        profile_system_power_w=np.ones((draws, 4), dtype=np.float64),
        profile_fixed_power_w=np.full((draws, 4), 0.5, dtype=np.float64),
        profile_active_beam_keys=beam_keys,
        profile_active_beam_counts=np.full((draws, 4), 2, dtype=np.int64),
        profile_active_satellites=np.full((draws, 4, 1), 10, dtype=np.int64),
        profile_active_satellite_counts=np.ones((draws, 4), dtype=np.int64),
        profile_beam_power_w=np.ones((draws, 4, 2), dtype=np.float64),
        z3_bits_by_draw=target_by_draw * adapter.V023_KAPPA_BITS,
        z3_normalized_by_draw=target_by_draw,
        formula_identity_residual_bits=np.zeros(draws, dtype=np.float64),
        ratio_identity_value_bits=np.zeros(draws, dtype=np.float64),
        joint_ee_bits_per_j=np.ones(draws, dtype=np.float64),
        source_nonmutation_flags=np.ones((draws, 5), dtype=np.bool_),
        action_digest=action_digest,
        ratio_cross_product=np.zeros(draws, dtype=np.float64),
        ratio_sign=np.zeros(draws, dtype=np.int8),
        ratio_tolerance=np.ones(draws, dtype=np.float64),
        ratio_local_tolerance=np.ones(draws, dtype=np.float64),
        formula_own_bits=np.ones((draws, 2), dtype=np.float64),
        formula_nonfocal_bits=np.ones((draws, 2), dtype=np.float64),
        formula_d_bits=np.ones((draws, 2), dtype=np.float64),
        formula_joint_delta_bits=np.zeros(draws, dtype=np.float64),
        formula_joint_delta_energy_j=np.full(draws, -0.25, dtype=np.float64),
        formula_joint_surplus_bits=np.zeros(draws, dtype=np.float64),
        formula_interaction_bits=np.zeros(draws, dtype=np.float64),
        formula_interaction_energy_j=np.full(draws, -0.125, dtype=np.float64),
        formula_interaction_surplus_bits=np.zeros(draws, dtype=np.float64),
        formula_equal_share_bits=np.ones(draws, dtype=np.float64),
    )
    pair = adapter.DeclaredPair(
        pair_id="pair-0",
        member_users=(0, 1),
        designated_actions=(1, 1),
        source_key=(10, 0),
        destination_keys=((20, 0), (30, 0)),
        profile_actions=profile_actions,
        profile_bits=profile_bits,
        profile_energy_j=energy,
        profile_served=served,
        common_field_digest=fields_by_draw,
        mechanics=mechanics,
    )
    physical_keys = np.full((users, actions, 2), -1, dtype=np.int64)
    physical_keys[:, 0] = np.asarray([(10, 0), (10, 0), (20, 0), (30, 0)])
    physical_keys[0, 1] = (20, 0)
    physical_keys[1, 1] = (30, 0)
    physical_keys[2, 1] = (40, 0)
    physical_keys[3, 1] = (40, 0)
    physical_keys[0, 2] = (50, 0)
    return pair, baseline, physical_keys


@pytest.mark.parametrize(
    ("selected", "expected", "harmful"),
    [
        ([0, 0, 0, 0], "00", False),
        ([1, 0, 0, 0], "10", True),
        ([0, 1, 0, 0], "01", False),
        ([1, 1, 0, 0], "11", False),
        ([2, 0, 0, 0], "OTHER", False),
    ],
)
def test_pair_classification_retains_00_10_01_11_and_other(
    selected, expected, harmful
) -> None:
    pair, baseline, physical_keys = _declared_pair()
    result = adapter.classify_pair_actions(
        pair=pair,
        baseline_actions=baseline,
        selected_actions=np.asarray(selected, dtype=np.int64),
        physical_keys=physical_keys,
    )

    assert result.class_name == expected
    assert result.class_code == adapter.PAIR_CLASS_CODES[expected]
    assert result.action_change is (expected != "00")
    assert result.literal_11 is (expected == "11")
    assert result.harmful_partial is harmful
    assert result.harmful_partial_evaluated is (expected in {"10", "01"})


def test_selected_11_topology_uses_nonmembers_and_never_repairs_actions() -> None:
    pair, baseline, physical_keys = _declared_pair()
    consistent = adapter.classify_pair_actions(
        pair=pair,
        baseline_actions=baseline,
        selected_actions=np.asarray([1, 1, 0, 0], dtype=np.int64),
        physical_keys=physical_keys,
    )
    inconsistent = adapter.classify_pair_actions(
        pair=pair,
        baseline_actions=baseline,
        selected_actions=np.asarray([1, 1, 1, 1], dtype=np.int64),
        physical_keys=physical_keys,
    )

    assert consistent.topology_evaluated and consistent.topology_consistent
    assert inconsistent.topology_evaluated and not inconsistent.topology_consistent
    assert inconsistent.collateral_changed_count == 2
    np.testing.assert_array_equal(
        inconsistent.selected_member_actions, np.asarray([1, 1], dtype=np.int64)
    )


def _composition_fixture(tmp_path: Path):
    world = 2026121705
    preflight = _digest("composition-preflight")
    source_manifest = _digest("composition-source-manifest")
    model = _FakeModel(_digest("composition-model"))
    fitted = adapter.AuthenticatedFitArtifact(
        held_out_world=world,
        student_seed=2026135101,
        arm="INFORMED",
        preflight_manifest_sha256=preflight,
        source_manifest_sha256=source_manifest,
        fit_receipt_sha256=_digest("composition-fit-receipt"),
        fit_receipt_content_sha256=_digest("composition-fit-receipt-content"),
        model_bytes_sha256=_digest("composition-model-bytes"),
        model_sha256=model.digest,
        source_index_sha256=_digest("composition-source-index"),
        model=model,
    )
    template_pair, references, physical_keys = _declared_pair()
    action_mask = np.zeros((4, 28), dtype=np.bool_)
    action_mask[:, :3] = True
    q1 = np.zeros((4, 28), dtype=np.float32)
    q1[:, 0] = 1.0
    q2 = np.zeros_like(q1)
    anchors = []
    views = {}
    for phase in range(1, 10):
        anchor_id = f"w{world}:t{phase}"
        view_digest = _digest(f"composition-view-{phase}")
        view = _FakeView(action_mask, references, view_digest)
        views[phase] = view
        pair = replace(template_pair, pair_id=f"pair-{phase}")
        teacher = np.zeros((4, 28), dtype=np.float32)
        teacher[0:2, 1] = 2.0
        anchors.append(
            adapter.DeclaredAnchor(
                world=world,
                phase=phase,
                anchor_id=anchor_id,
                predecision_sha256=_digest(f"predecision-{phase}"),
                state_schema_sha256=_digest("composition-state-schema"),
                state_sha256=_digest(f"composition-state-{phase}"),
                q12_snapshot_sha256=_digest(f"composition-snapshot-{phase}"),
                q12_model_sha256=_digest("composition-q12-model"),
                q12_source_state_sha256=_digest(f"composition-q12-state-{phase}"),
                q12_event_sha256=_digest(f"composition-event-{phase}"),
                view_sha256=view_digest,
                topology_sha256=_digest(f"composition-topology-{phase}"),
                q1=q1,
                q2=q2,
                action_mask=action_mask,
                reference_actions=references,
                physical_keys=physical_keys,
                teacher_q3=teacher,
                pairs=(pair,),
            )
        )
    source = adapter.AuthenticatedSourceArtifact(
        world=world,
        preflight_manifest_sha256=preflight,
        source_manifest_sha256=source_manifest,
        source_index_sha256=_digest("composition-source-index"),
        field_root_sha256=_digest("composition-field-root"),
        anchors=tuple(anchors),
    )
    spec = adapter.CompositionShardSpec(
        held_out_world=world,
        student_seed=2026135101,
        arm="INFORMED",
        source_directory=tmp_path / "source-root",
        source_manifest=tmp_path / "source-manifest.json",
        fit_receipt=tmp_path / "fit.json",
        preflight_manifest_sha256=preflight,
        source_manifest_sha256=source_manifest,
        output=tmp_path / "composition" / "informed.json",
    )

    def replay(request):
        declared = anchors[request.phase - 1]
        return adapter.ReplayedAnchor(
            handle=adapter.ImmutableAnchorHandle(
                token=f"anchor-{request.phase}",
                content_digest=_digest(f"handle-{request.phase}"),
            ),
            world=declared.world,
            phase=declared.phase,
            anchor_id=declared.anchor_id,
            predecision_sha256=declared.predecision_sha256,
            state_schema_sha256=declared.state_schema_sha256,
            state_sha256=declared.state_sha256,
            q12_snapshot_sha256=declared.q12_snapshot_sha256,
            q12_model_sha256=declared.q12_model_sha256,
            q12_source_state_sha256=declared.q12_source_state_sha256,
            q12_event_sha256=declared.q12_event_sha256,
            view_sha256=declared.view_sha256,
            topology_sha256=declared.topology_sha256,
            q1=declared.q1,
            q2=declared.q2,
            action_mask=declared.action_mask,
            reference_actions=declared.reference_actions,
            view=views[request.phase],
        )

    def physical(request):
        return _physical_result(request)

    return spec, source, fitted, replay, physical


def _phase_class_q3(request):
    result = np.zeros((4, 28), dtype=np.float32)
    if request.phase == 2:
        result[0, 1] = 2.0
    elif request.phase == 3:
        result[1, 1] = 2.0
    elif request.phase == 4:
        result[0:2, 1] = 2.0
    elif request.phase == 5:
        result[0, 2] = 2.0
    return result


def _shard_adapter(source, fitted, replay, physical, *, q3=_phase_class_q3):
    return adapter.V023CompositionAdapter(
        source_authenticator=lambda _spec: source,
        fit_authenticator=lambda _spec: fitted,
        anchor_replayer=replay,
        q3_evaluator=q3,
        physical_evaluator=physical,
        model_digestor=lambda model: model.digest,
    )


def test_shard_persists_raw_pair_classes_physics_and_closed_boundaries(
    tmp_path: Path,
) -> None:
    spec, source, fitted, replay, physical = _composition_fixture(tmp_path)
    result = _shard_adapter(source, fitted, replay, physical).compose_shard(spec)

    assert result.index_path == spec.output
    receipt = result.index
    assert receipt["test_split_opened"] is False
    assert receipt["episode_training"] is False
    assert receipt["learner_update"] is False
    assert receipt["fit_already_completed"] is True
    assert receipt["scientific_decision_opened"] is False
    assert receipt["c3_decision"] is None
    assert receipt["inference"]["q3_calls"] == 9
    assert receipt["inference"]["learned_argmax_calls"] == 9
    assert receipt["inference"]["teacher_argmax_calls"] == 9
    assert receipt["inference"]["physical_evaluator_calls"] == 27
    with np.load(result.arrays_path, allow_pickle=False) as arrays:
        assert set(arrays["learned_pair_class"].tolist()) == {0, 1, 2, 3, 4}
        assert arrays["physical_per_user_bits"].shape == (9, 3, 32, 4)
        assert arrays["physical_energy_j"].shape == (9, 3, 32)
        assert arrays["physical_served"].dtype == np.bool_
        assert arrays["pair_profile_bits"].shape == (9, 32, 4, 4)
        assert arrays["pair_profile_energy_j"].shape == (9, 32, 4)
        assert arrays["pair_target_by_draw"].shape == (9, 32, 2)
        assert arrays["pair_profile_link_rate_bps"].shape == (9, 32, 4, 4)
        assert arrays["pair_profile_active_beam_keys"].shape == (9, 32, 4, 2, 2)
        assert arrays["pair_z3_bits_by_draw"].shape == (9, 32, 2)
        assert arrays["pair_formula_joint_delta_energy_j"].shape == (9, 32)
        assert arrays["pair_source_nonmutation_flags"].all()
        assert arrays["pair_profile_action_sha256"].dtype == np.dtype("S64")
        assert arrays["pair_harmful_partial_evaluated"].sum() == 2
        assert arrays["pair_harmful_partial"].sum() == 1
        np.testing.assert_array_equal(
            arrays["pair_partial_ratio_direction"][[1, 2]],
            np.asarray([-1, 1], dtype=np.int8),
        )
        assert all(arrays[name].dtype != object for name in arrays.files)
    assert receipt["denominators"]["physical_ratio_direction"] == {
        "denominator": 18,
        "tie_count": 18,
        "missing_count": 0,
    }
    assert receipt["denominators"]["source_pair_draw_ratio_direction"] == {
        "denominator": 9 * 32,
        "tie_count": 9 * 32,
        "missing_count": 0,
    }
    assert receipt["denominators"]["harmful_partial_ratio_direction"] == {
        "denominator": 2,
        "tie_count": 0,
        "missing_count": 0,
        "na_nonpartial_count": 7,
    }


def test_zero_selected_11_is_explicit_na_and_false_ready(tmp_path: Path) -> None:
    spec, source, fitted, replay, physical = _composition_fixture(tmp_path)

    def zero_q3(_request):
        return np.zeros((4, 28), dtype=np.float32)

    result = _shard_adapter(
        source, fitted, replay, physical, q3=zero_q3
    ).compose_shard(spec)
    topology = result.index["denominators"]["topology_consistency"]
    assert topology == {
        "denominator": 0,
        "numerator": 0,
        "value": None,
        "status": "NA_ZERO_SELECTED_11",
        "predicate_ready": False,
        "predicate": False,
    }


def test_shard_rejects_source_and_fit_identity_hash_mismatch_before_replay(
    tmp_path: Path,
) -> None:
    spec, source, fitted, replay, physical = _composition_fixture(tmp_path)
    calls = 0

    def forbidden_replay(request):
        nonlocal calls
        calls += 1
        return replay(request)

    bad_source = replace(
        source, source_manifest_sha256=_digest("wrong-source-manifest")
    )
    with pytest.raises(adapter.V023CompositionAdapterError, match="source manifest"):
        _shard_adapter(bad_source, fitted, forbidden_replay, physical).compose_shard(spec)
    assert calls == 0

    bad_fit = replace(fitted, arm="MATCHED_PLACEBO")
    with pytest.raises(adapter.V023CompositionAdapterError, match="fit arm"):
        _shard_adapter(source, bad_fit, forbidden_replay, physical).compose_shard(spec)
    assert calls == 0

    bad_fit_index = replace(
        fitted, source_index_sha256=_digest("different-heldout-source-index")
    )
    with pytest.raises(
        adapter.V023CompositionAdapterError, match="fit held-out source index"
    ):
        _shard_adapter(
            source, bad_fit_index, forbidden_replay, physical
        ).compose_shard(spec)
    assert calls == 0


def test_sidecars_are_write_once_tamper_evident_and_never_allow_pickle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, source, fitted, replay, physical = _composition_fixture(tmp_path)
    worker = _shard_adapter(source, fitted, replay, physical)
    result = worker.compose_shard(spec)
    with pytest.raises(adapter.V023CompositionAdapterError, match="overwrite"):
        worker.compose_shard(spec)

    load_calls: list[object] = []
    real_load = np.load

    def safe_load(*args, **kwargs):
        load_calls.append(kwargs.get("allow_pickle"))
        return real_load(*args, **kwargs)

    monkeypatch.setattr(adapter.np, "load", safe_load)
    verified = adapter.verify_composition_sidecars(result.index_path)
    assert verified["status"] == "PASS_COMPOSITION_SIDECARS"
    assert load_calls and set(load_calls) == {False}

    result.arrays_path.write_bytes(result.arrays_path.read_bytes() + b"tamper")
    with pytest.raises(adapter.V023CompositionAdapterError, match="NPZ byte hash"):
        adapter.verify_composition_sidecars(result.index_path)


def test_object_dtype_is_rejected_before_persistence() -> None:
    with pytest.raises(adapter.V023CompositionAdapterError, match="object dtype"):
        adapter.composition_array_metadata(
            {"unsafe": np.asarray([object()], dtype=object)}
        )


def _canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_production_source_authenticator_reopens_raw_profiles_without_pickle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, source, _fitted, _replay, _physical = _composition_fixture(tmp_path)
    source_root = tmp_path / "source-root"
    source_root.mkdir()
    sidecar = source_root / "world.arrays.npz"
    anchors = source.anchors
    template_pair = anchors[0].pairs[0]
    pair_count = len(anchors)
    draw_pair_index = np.repeat(np.arange(pair_count, dtype=np.int64), 32)
    draw_index = np.tile(np.arange(32, dtype=np.int64), pair_count)
    np.savez_compressed(
        sidecar,
        anchor_phase=np.arange(1, 10, dtype=np.int64),
        anchor_content_digest=np.asarray(
            [item.predecision_sha256.encode("ascii") for item in anchors], dtype="S64"
        ),
        anchor_view_content_digest=np.asarray(
            [item.view_sha256.encode("ascii") for item in anchors], dtype="S64"
        ),
        anchor_topology_content_digest=np.asarray(
            [item.topology_sha256.encode("ascii") for item in anchors], dtype="S64"
        ),
        action_mask=np.stack([item.action_mask for item in anchors]),
        reference_actions=np.stack([item.reference_actions for item in anchors]),
        physical_keys=np.stack([item.physical_keys for item in anchors]),
        q1_values=np.stack([item.q1 for item in anchors]).astype(np.float64),
        q2_values=np.stack([item.q2 for item in anchors]).astype(np.float64),
        q12_values=np.stack([item.q12 for item in anchors]).astype(np.float64),
        pair_anchor_index=np.arange(pair_count, dtype=np.int64),
        pair_id=np.asarray(
            [item.pairs[0].pair_id.encode("ascii") for item in anchors], dtype="S256"
        ),
        pair_user_ids=np.asarray(
            [item.pairs[0].member_users for item in anchors], dtype=np.int64
        ),
        pair_action_ids=np.asarray(
            [item.pairs[0].designated_actions for item in anchors], dtype=np.int64
        ),
        pair_target_by_draw=np.stack(
            [item.pairs[0].mechanics.target_by_draw for item in anchors]
        ),
        pair_target_mean=np.asarray(
            [
                np.mean(item.pairs[0].mechanics.target_by_draw, axis=0)
                for item in anchors
            ],
            dtype=np.float64,
        ),
        draw_pair_index=draw_pair_index,
        draw_index=draw_index,
        draw_pair_id=np.asarray(
            [
                anchors[int(pair_index)].pairs[0].pair_id.encode("ascii")
                for pair_index in draw_pair_index.tolist()
            ],
            dtype="S256",
        ),
        profile_actions=np.concatenate(
            [item.pairs[0].profile_actions for item in anchors], axis=0
        ),
        profile_bits=np.concatenate(
            [item.pairs[0].profile_bits for item in anchors], axis=0
        ),
        profile_link_rate_bps=np.concatenate(
            [item.pairs[0].mechanics.profile_link_rate_bps for item in anchors],
            axis=0,
        ),
        profile_link_power_w=np.concatenate(
            [item.pairs[0].mechanics.profile_link_power_w for item in anchors],
            axis=0,
        ),
        profile_link_sinr=np.concatenate(
            [item.pairs[0].mechanics.profile_link_sinr for item in anchors], axis=0
        ),
        profile_energy_j=np.concatenate(
            [item.pairs[0].profile_energy_j for item in anchors], axis=0
        ),
        profile_g_bits=np.concatenate(
            [item.pairs[0].mechanics.profile_g_bits for item in anchors], axis=0
        ),
        profile_system_power_w=np.concatenate(
            [item.pairs[0].mechanics.profile_system_power_w for item in anchors],
            axis=0,
        ),
        profile_fixed_power_w=np.concatenate(
            [item.pairs[0].mechanics.profile_fixed_power_w for item in anchors],
            axis=0,
        ),
        profile_served=np.concatenate(
            [item.pairs[0].profile_served for item in anchors], axis=0
        ),
        profile_active_beam_keys=np.concatenate(
            [item.pairs[0].mechanics.profile_active_beam_keys for item in anchors],
            axis=0,
        ),
        profile_active_beam_counts=np.concatenate(
            [item.pairs[0].mechanics.profile_active_beam_counts for item in anchors],
            axis=0,
        ),
        profile_active_satellites=np.concatenate(
            [item.pairs[0].mechanics.profile_active_satellites for item in anchors],
            axis=0,
        ),
        profile_active_satellite_counts=np.concatenate(
            [
                item.pairs[0].mechanics.profile_active_satellite_counts
                for item in anchors
            ],
            axis=0,
        ),
        profile_beam_power_w=np.concatenate(
            [item.pairs[0].mechanics.profile_beam_power_w for item in anchors],
            axis=0,
        ),
        z3_bits_by_draw=np.concatenate(
            [item.pairs[0].mechanics.z3_bits_by_draw for item in anchors], axis=0
        ),
        z3_normalized_by_draw=np.concatenate(
            [item.pairs[0].mechanics.z3_normalized_by_draw for item in anchors],
            axis=0,
        ),
        formula_identity_residual_bits=np.concatenate(
            [
                item.pairs[0].mechanics.formula_identity_residual_bits
                for item in anchors
            ],
            axis=0,
        ),
        ratio_identity_value_bits=np.concatenate(
            [item.pairs[0].mechanics.ratio_identity_value_bits for item in anchors],
            axis=0,
        ),
        joint_ee_bits_per_j=np.concatenate(
            [item.pairs[0].mechanics.joint_ee_bits_per_j for item in anchors],
            axis=0,
        ),
        nonmutation_flags=np.concatenate(
            [item.pairs[0].mechanics.source_nonmutation_flags for item in anchors],
            axis=0,
        ),
        common_field_digest=np.concatenate(
            [item.pairs[0].common_field_digest for item in anchors], axis=0
        ),
        action_digest=np.concatenate(
            [item.pairs[0].mechanics.action_digest for item in anchors], axis=0
        ),
        ratio_cross_product=np.concatenate(
            [item.pairs[0].mechanics.ratio_cross_product for item in anchors],
            axis=0,
        ),
        ratio_sign=np.concatenate(
            [item.pairs[0].mechanics.ratio_sign for item in anchors], axis=0
        ),
        ratio_tolerance=np.concatenate(
            [item.pairs[0].mechanics.ratio_tolerance for item in anchors], axis=0
        ),
        ratio_local_tolerance=np.concatenate(
            [item.pairs[0].mechanics.ratio_local_tolerance for item in anchors],
            axis=0,
        ),
        formula_own_bits=np.concatenate(
            [item.pairs[0].mechanics.formula_own_bits for item in anchors], axis=0
        ),
        formula_nonfocal_bits=np.concatenate(
            [item.pairs[0].mechanics.formula_nonfocal_bits for item in anchors],
            axis=0,
        ),
        formula_d_bits=np.concatenate(
            [item.pairs[0].mechanics.formula_d_bits for item in anchors], axis=0
        ),
        formula_joint_delta_bits=np.concatenate(
            [item.pairs[0].mechanics.formula_joint_delta_bits for item in anchors],
            axis=0,
        ),
        formula_joint_delta_energy_j=np.concatenate(
            [
                item.pairs[0].mechanics.formula_joint_delta_energy_j
                for item in anchors
            ],
            axis=0,
        ),
        formula_joint_surplus_bits=np.concatenate(
            [
                item.pairs[0].mechanics.formula_joint_surplus_bits
                for item in anchors
            ],
            axis=0,
        ),
        formula_interaction_bits=np.concatenate(
            [item.pairs[0].mechanics.formula_interaction_bits for item in anchors],
            axis=0,
        ),
        formula_interaction_energy_j=np.concatenate(
            [
                item.pairs[0].mechanics.formula_interaction_energy_j
                for item in anchors
            ],
            axis=0,
        ),
        formula_interaction_surplus_bits=np.concatenate(
            [
                item.pairs[0].mechanics.formula_interaction_surplus_bits
                for item in anchors
            ],
            axis=0,
        ),
        formula_equal_share_bits=np.concatenate(
            [item.pairs[0].mechanics.formula_equal_share_bits for item in anchors],
            axis=0,
        ),
    )
    entries = []
    for item in anchors:
        pair = item.pairs[0]
        entries.append(
            {
                "phase": item.phase,
                "anchor_id": item.anchor_id,
                "predecision_sha256": item.predecision_sha256,
                "state_schema_sha256": item.state_schema_sha256,
                "state_sha256": item.state_sha256,
                "q12_snapshot_sha256": item.q12_snapshot_sha256,
                "q12_model_sha256": item.q12_model_sha256,
                "q12_source_state_sha256": item.q12_source_state_sha256,
                "q12_event_sha256": item.q12_event_sha256,
                "reference_actions_sha256": item.reference_actions_sha256,
                "topology": {
                    "content_digest": item.topology_sha256,
                    "pairs": [
                        {
                            "pair_id": pair.pair_id,
                            "member_users": list(pair.member_users),
                            "designated_actions": list(pair.designated_actions),
                            "source_key": list(pair.source_key),
                            "destination_keys": [list(value) for value in pair.destination_keys],
                        }
                    ]
                },
            }
        )
    artifact = SimpleNamespace(
        world=spec.held_out_world,
        sidecar_path=sidecar,
        sidecar_sha256=_file_digest(sidecar),
        index_sha256=source.source_index_sha256,
        index={
            "anchors": entries,
            "world_receipt": {"field_root_digest": source.field_root_sha256},
        },
    )
    panel = SimpleNamespace(
        source_manifest_sha256=spec.source_manifest_sha256,
        preflight_manifest_sha256=spec.preflight_manifest_sha256,
        artifacts=(artifact,),
    )
    loader_calls = 0

    def load_v023_source_panel(**kwargs):
        nonlocal loader_calls
        loader_calls += 1
        assert kwargs["source_manifest"] == spec.source_manifest
        return panel

    fake_module = SimpleNamespace(load_v023_source_panel=load_v023_source_panel)
    load_calls = []
    real_load = np.load

    def safe_load(*args, **kwargs):
        load_calls.append(kwargs.get("allow_pickle"))
        return real_load(*args, **kwargs)

    monkeypatch.setattr(adapter.np, "load", safe_load)
    authenticated = adapter.authenticate_source_artifact(
        spec, fit_adapter_module=fake_module
    )

    assert loader_calls == 1
    assert load_calls == [False]
    assert authenticated.world == spec.held_out_world
    assert len(authenticated.anchors) == 9
    assert all(len(item.pairs) == 1 for item in authenticated.anchors)
    np.testing.assert_array_equal(
        authenticated.anchors[0].pairs[0].profile_bits,
        template_pair.profile_bits,
    )
    np.testing.assert_array_equal(
        authenticated.anchors[0].pairs[0].mechanics.target_by_draw,
        template_pair.mechanics.target_by_draw,
    )
    np.testing.assert_array_equal(
        authenticated.anchors[0].pairs[0].mechanics.formula_joint_delta_energy_j,
        template_pair.mechanics.formula_joint_delta_energy_j,
    )

    sidecar.write_bytes(sidecar.read_bytes() + b"tamper")
    with pytest.raises(
        adapter.V023CompositionAdapterError, match="source numeric sidecar byte hash"
    ):
        adapter.authenticate_source_artifact(spec, fit_adapter_module=fake_module)


def test_production_fit_authenticator_verifies_receipt_and_rebuilds_eval_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    torch = pytest.importorskip("torch")
    optimizer_calls = 0

    def forbidden_optimizer(*_args, **_kwargs):
        nonlocal optimizer_calls
        optimizer_calls += 1
        raise AssertionError("composition authentication must not construct an optimizer")

    for optimizer_name in ("Adam", "AdamW", "SGD"):
        monkeypatch.setattr(torch.optim, optimizer_name, forbidden_optimizer)
    spec, _source, _fitted, _replay, _physical = _composition_fixture(tmp_path)
    fit_root = tmp_path / "fit-root"
    fit_root.mkdir()
    fit_path = fit_root / "fit.json"
    model_path = fit_root / "model.npz"

    class FakeNetwork(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.zeros((2, 3), dtype=torch.float32))

    def network_digest(network) -> str:
        return adapter.array_sha256(
            network.weight.detach().cpu().numpy(), domain="w197-fake-network-v1"
        )

    original = FakeNetwork()
    with torch.no_grad():
        original.weight.copy_(torch.arange(6, dtype=torch.float32).reshape(2, 3))
    weight = original.weight.detach().cpu().numpy()
    np.savez_compressed(model_path, p0000=weight)
    logical = network_digest(original)
    domain = "w197-fit-model-array-v1"
    unsigned = {
        "schema": "w197-fit-schema",
        "status": "PASS",
        "claim_ceiling": adapter.V023_CLAIM_CEILING,
        "contract_sha256": adapter.V023_CONTRACT_SHA256,
        "held_out_world": spec.held_out_world,
        "student_seed": spec.student_seed,
        "arm": spec.arm,
        "preflight_manifest_sha256": spec.preflight_manifest_sha256,
        "source_manifest_sha256": spec.source_manifest_sha256,
        "update_count": 2000,
        "split": "TRAIN_DEVELOPMENT",
        "learner_update": True,
        "test_split_opened": False,
        "episode_training": False,
        "test_worlds": [],
        "source_panel": {
            "source_index_sha256s": {
                str(spec.held_out_world): _digest("fit-heldout-source-index")
            }
        },
        "model_sha256": _file_digest(model_path),
        "network_sha256": logical,
        "model_state": {
            "path": model_path.name,
            "npz_sha256": _file_digest(model_path),
            "logical_network_sha256": logical,
            "array_domain": domain,
            "no_pickle": True,
            "arrays": {
                "weight": {
                    "npz_key": "p0000",
                    "dtype": weight.dtype.str,
                    "shape": list(weight.shape),
                    "sha256": adapter.array_sha256(weight, domain=domain),
                }
            },
        },
    }
    payload = dict(unsigned)
    payload["receipt_sha256"] = adapter.canonical_sha256(unsigned)
    fit_path.write_bytes(_canonical_json_bytes(payload) + b"\n")
    spec = replace(spec, fit_receipt=fit_path)
    verify_calls = 0

    def verify_v023_fit_sidecars(path):
        nonlocal verify_calls
        verify_calls += 1
        assert Path(path).parent == fit_root
        return {"status": "PASS_FIT_SIDECARS"}

    fake_module = SimpleNamespace(
        verify_v023_fit_sidecars=verify_v023_fit_sidecars,
        V023_FIT_SCHEMA="w197-fit-schema",
        V023_FIT_CLAIM_CEILING=adapter.V023_CLAIM_CEILING,
        V023_FIT_MODEL_ARRAY_DOMAIN=domain,
        LCSRSC3QNetwork=FakeNetwork,
        lcsrs_c3_network_sha256=network_digest,
    )
    load_calls = []
    real_load = np.load

    def safe_load(*args, **kwargs):
        load_calls.append(kwargs.get("allow_pickle"))
        return real_load(*args, **kwargs)

    monkeypatch.setattr(adapter.np, "load", safe_load)
    authenticated = adapter.authenticate_fit_artifact(
        spec, fit_adapter_module=fake_module
    )

    assert verify_calls == 1
    assert load_calls == [False]
    assert authenticated.fit_receipt_sha256 == _file_digest(fit_path)
    assert authenticated.fit_receipt_content_sha256 == payload["receipt_sha256"]
    assert authenticated.source_index_sha256 == _digest("fit-heldout-source-index")
    assert authenticated.model_sha256 == logical
    assert authenticated.model.training is False
    assert optimizer_calls == 0
    np.testing.assert_array_equal(
        authenticated.model.weight.detach().cpu().numpy(), weight
    )

    bad_unsigned = dict(unsigned)
    bad_unsigned["update_count"] = 1999
    bad_payload = dict(bad_unsigned)
    bad_payload["receipt_sha256"] = adapter.canonical_sha256(bad_unsigned)
    bad_path = fit_root / "bad-fit.json"
    bad_path.write_bytes(_canonical_json_bytes(bad_payload) + b"\n")
    with pytest.raises(
        adapter.V023CompositionAdapterError, match="update_count disagrees"
    ):
        adapter.authenticate_fit_artifact(
            replace(spec, fit_receipt=bad_path), fit_adapter_module=fake_module
        )

    model_path.write_bytes(model_path.read_bytes() + b"tamper")
    with pytest.raises(
        adapter.V023CompositionAdapterError, match="fit model byte hash"
    ):
        adapter.authenticate_fit_artifact(spec, fit_adapter_module=fake_module)
