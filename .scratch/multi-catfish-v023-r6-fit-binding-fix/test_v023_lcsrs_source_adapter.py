"""Non-heavy source-adapter seam tests.

These tests deliberately use immutable fakes only.  They do not open TLE,
construct a simulator, evaluate a physical profile, fit a learner, or open
TEST.  The server-side source run remains a separate execution boundary.
"""

from __future__ import annotations

from pathlib import Path
import copy
from types import SimpleNamespace
import importlib.util
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location("v023_source_adapter_test_module", HERE / "v023_lcsrs_source_adapter.py")
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


def _fake_capture(users: int = 2) -> SimpleNamespace:
    context = np.zeros((users, adapter.ACTIONS, 29), dtype=np.float32)
    tokens = np.zeros((users, adapter.ACTIONS, users + 1, 38), dtype=np.float32)
    token_mask = np.zeros((users, adapter.ACTIONS, users + 1), dtype=np.bool_)
    action_mask = np.ones((users, adapter.ACTIONS), dtype=np.bool_)
    reference = np.zeros(users, dtype=np.int64)
    view = SimpleNamespace(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=reference,
        content_digest="a" * 64,
    )
    snapshot = SimpleNamespace(
        q1=np.zeros((users, adapter.ACTIONS), dtype=np.float32),
        q2=np.zeros((users, adapter.ACTIONS), dtype=np.float32),
        q12=np.zeros((users, adapter.ACTIONS), dtype=np.float32),
    )
    topology_capture = SimpleNamespace(
        opening_feasibility=action_mask.copy(),
        physical_keys=np.zeros((users, adapter.ACTIONS, 2), dtype=np.int64),
        q12_snapshot=snapshot,
    )
    topology = SimpleNamespace(
        phase=1,
        capture=topology_capture,
        content_digest="b" * 64,
    )
    return SimpleNamespace(
        view=view,
        topology=topology,
        content_digest="c" * 64,
    )


def _fake_q2_context(users: int = 2) -> dict[str, object]:
    return {
        "state_matrix": np.zeros((users, adapter.V014_Q2_STATE_DIM), dtype=np.float32),
        "features": np.zeros((users, adapter.ACTIONS, 16), dtype=np.float64),
        "target_values": np.zeros((users, adapter.ACTIONS), dtype=np.float64),
        "persistence": np.zeros(
            (users, adapter.OPS3_HORIZON, adapter.ACTIONS), dtype=np.float64
        ),
        "rate_bps": np.zeros(
            (users, adapter.OPS3_HORIZON, adapter.ACTIONS), dtype=np.float64
        ),
        "marginal_power_w": np.zeros(
            (users, adapter.OPS3_HORIZON, adapter.ACTIONS), dtype=np.float64
        ),
        "required_power_w": np.zeros(
            (users, adapter.OPS3_HORIZON, adapter.ACTIONS), dtype=np.float64
        ),
        "horizon": 0,
    }


def test_draw_field_excludes_pair_and_profile_axes() -> None:
    config = adapter.V023SourceAdapterConfig(tle_root=Path("/unused"), prereg=Path("/unused"))
    instance = adapter.V023RuntimeSourceAdapter(config)
    first = instance._make_draw_field(2026121705, "w2026121705:t1", 7)
    same_anchor = instance._make_draw_field(2026121705, "w2026121705:t1", 7)
    different_anchor = instance._make_draw_field(2026121705, "w2026121705:t2", 7)
    different_draw = instance._make_draw_field(2026121705, "w2026121705:t1", 8)
    assert first.root_digest == same_anchor.root_digest
    assert first.root_digest != different_anchor.root_digest
    assert first.root_digest != different_draw.root_digest


def test_action_digest_uses_binding_teacher_grammar() -> None:
    values = np.asarray([0, 3, 27], dtype=np.int64)
    assert adapter._action_digest(values) == adapter.lcsrs_action_sha256(values)
    with pytest.raises(adapter.V023SourceAdapterError):
        adapter._action_digest(np.zeros((1, 3), dtype=np.int64))


def test_ratio_tolerance_scales_from_operands_not_cancelled_difference() -> None:
    left = 1.0e20
    right = np.nextafter(left, np.inf)
    receipt = adapter._ratio_sign_receipt(
        reference_bits=left,
        reference_energy_j=1.0,
        joint_bits=right,
        joint_energy_j=1.0,
    )
    assert receipt["ratio_cross_product"] > 0.0
    assert receipt["ratio_tolerance"] > receipt["ratio_cross_product"]
    assert receipt["ratio_sign"] == 0
    assert receipt["ratio_sign_identity_pass"] is True


def test_ordinary_closure_failures_are_countable_not_fatal() -> None:
    records = {
        code: {
            "active_beam_keys": [[1, 0]] if code != "11" else [[2, 0]],
            "served": [True, False],
            "served_users": 1,
        }
        for code in adapter.PROFILE_ORDER
    }
    failures = adapter._closure_mechanics_failure_codes(
        records,
        source=(0, 0),
        destinations={(1, 0)},
        members=np.asarray([0, 1], dtype=np.int64),
        ratio_sign_identity_pass=False,
    )
    assert failures == [
        "SOURCE_NOT_RETAINED_00_10_01",
        "DESIGNATED_DESTINATION_LOST_11",
        "NEW_BEAM_OPENED_11",
        "NOT_EXACT_SOURCE_ONLY_REMOVAL_11",
        "MEMBER_UNSERVED",
        "RATIO_SIGN_IDENTITY",
    ]


def test_rng_state_comparison_handles_numpy_state_arrays() -> None:
    rng = np.random.default_rng(123)
    before = copy.deepcopy(rng.bit_generator.state)
    assert adapter._rng_state_unchanged(before, copy.deepcopy(before))
    rng.random()
    assert not adapter._rng_state_unchanged(before, rng.bit_generator.state)


def test_sidecar_has_complete_fixed_width_control_and_profile_names() -> None:
    capture = _fake_capture()
    arrays = adapter._build_sidecar_arrays(
        captures=[capture],
        q2_contexts=[_fake_q2_context()],
        anchor_records=[None],
        pair_teachers=[],
        profile_rows=[],
        controls=[
            {
                "control_id": "control-1",
                "phase": 1,
                "source_key": [1, 2],
                "member_users": [0, 1],
                "third_user": 2,
                "eligible": False,
                "profile_draws": [],
            }
        ],
    )
    required = {
        "anchor_status",
        "draw_pair_index",
        "profile_active_satellite_counts",
        "common_field_digest",
        "action_digest",
        "control_profile_active_satellite_counts",
        "control_common_field_digest",
        "control_action_digest",
    }
    assert required.issubset(arrays)
    assert arrays["anchor_status"].tolist() == [0]
    assert arrays["control_evaluated"].shape == (adapter.DRAW_COUNT,)
    assert all(np.asarray(value).dtype != object for value in arrays.values())


def test_sidecar_keeps_one_pair_profile_and_scalar_formula_fields() -> None:
    """Exercise the non-empty pair path without opening the simulator."""

    capture = _fake_capture()
    digest = "d" * 64
    profiles = {}
    for code in adapter.PROFILE_ORDER:
        profiles[code] = {
            "actions": np.asarray([1, 2], dtype=np.int64),
            "per_user_bits": np.asarray([10.0, 20.0], dtype=np.float64),
            "link_rate_bps": np.asarray([100.0, 200.0], dtype=np.float64),
            "link_power_w": np.asarray([1.0, 2.0], dtype=np.float64),
            "link_sinr": np.asarray([3.0, 4.0], dtype=np.float64),
            "energy_j": 3.0,
            "g_bits": 30.0,
            "system_power_w": 3.0,
            "fixed_power_w": 0.5,
            "served": np.asarray([True, True], dtype=np.bool_),
            "active_beam_keys": [[0, 1]],
            "beam_power_w": [3.0],
            "active_satellites": [0],
            "action_sha256": digest,
        }
    row = {
        "pair_index": 0,
        "pair_id": "pair-0",
        "draw_index": 0,
        "profiles": profiles,
        "formula": {
            "z3_bits": [1.0, -2.0],
            "identity_residual_bits": 0.0,
            "own_bits": [1.0, 2.0],
            "nonfocal_bits": [3.0, 4.0],
            "d_bits": [5.0, 6.0],
            "joint_delta_bits": 7.0,
            "joint_delta_energy_j": 8.0,
            "joint_surplus_bits": 9.0,
            "interaction_bits": 10.0,
            "interaction_energy_j": 11.0,
            "interaction_surplus_bits": 12.0,
            "equal_share_bits": 13.0,
        },
        "ratio_identity_value_bits": 0.0,
        "ratio_cross_product": 1.0,
        "ratio_sign": 1,
        "ratio_tolerance": 1.0e-12,
        "ratio_local_tolerance": 1.0e-12,
        "joint_ee_bits_per_j": 10.0,
        "nonmutation_flags": [True, True, True, True, True],
        "common_field_sha256": digest,
    }
    targets = SimpleNamespace(
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 2], dtype=np.int64),
        normalized_targets_by_draw=np.zeros((adapter.DRAW_COUNT, 2), dtype=np.float64),
    )
    teacher = SimpleNamespace(pair_id="pair-0", pair_targets=targets)
    arrays = adapter._build_sidecar_arrays(
        captures=[capture],
        q2_contexts=[_fake_q2_context()],
        anchor_records=[None],
        pair_teachers=[(0, teacher)],
        profile_rows=[row],
    )
    assert arrays["pair_id"].tolist() == [b"pair-0"]
    assert arrays["formula_equal_share_bits"].shape == (1,)
    assert float(arrays["formula_equal_share_bits"][0]) == 13.0
    assert arrays["profile_active_satellite_counts"].tolist() == [[1, 1, 1, 1]]
    assert all(np.asarray(value).dtype != object for value in arrays.values())


def test_pair_evaluator_runs_all_32_common_field_draws_and_profiles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the physical seam against a tiny deterministic fake environment."""

    adapter_instance = adapter.V023RuntimeSourceAdapter(
        adapter.V023SourceAdapterConfig(tle_root=Path("/unused"), prereg=Path("/unused"))
    )
    pair = SimpleNamespace(
        pair_id="pair-fake",
        source_key=(0, 0),
        member_users=(0, 1),
        designated_actions=(1, 2),
        destination_keys=((1, 0), (2, 0)),
    )
    reference = np.zeros(2, dtype=np.int64)
    masks = np.ones((2, adapter.ACTIONS), dtype=np.bool_)
    physical_keys = np.zeros((2, adapter.ACTIONS, 2), dtype=np.int64)
    physical_keys[0, 1] = (1, 0)
    physical_keys[1, 2] = (2, 0)
    capture = SimpleNamespace(
        topology=SimpleNamespace(
            capture=SimpleNamespace(physical_keys=physical_keys)
        )
    )
    anchor_data = {
        "background": reference,
        "masks": masks,
        "q1": np.zeros((2, adapter.ACTIONS), dtype=np.float32),
        "q2": np.zeros((2, adapter.ACTIONS), dtype=np.float32),
        "q2_context": {
            "target_values": np.zeros((2, adapter.ACTIONS), dtype=np.float64)
        },
        "capture": capture,
    }

    class FakeResolution:
        served = np.asarray([True, True], dtype=np.bool_)

    class FakeRadiating:
        def __init__(self, keys: list[tuple[int, int]]) -> None:
            self.norad_ids = np.asarray([key[0] for key in keys], dtype=np.int64)
            self.cell_ids = np.asarray([key[1] for key in keys], dtype=np.int64)
            self.power_w = np.ones(len(keys), dtype=np.float64)

    class FakeEvaluation:
        link_rate_bps = np.asarray([100.0, 200.0], dtype=np.float64)
        link_power_w = np.asarray([1.0, 1.0], dtype=np.float64)
        link_sinr = np.asarray([3.0, 4.0], dtype=np.float64)
        resolution = FakeResolution()
        system_power_w = 3.0
        fixed_power_w = 0.5

        def __init__(self, keys: list[tuple[int, int]]) -> None:
            self.radiating = FakeRadiating(keys)

    class FakeStep:
        _fading_field = object()

        def __init__(self) -> None:
            self.calls = 0

        def evaluate_actions(self, actions: np.ndarray, rng: np.random.Generator) -> FakeEvaluation:
            del actions, rng
            self.calls += 1
            # Calls are ordered 00/10/01/11 for every draw.
            if self.calls % 4 == 0:
                return FakeEvaluation([(1, 0), (2, 0)])
            return FakeEvaluation([(0, 0), (1, 0), (2, 0)])

    class FakeV015:
        @staticmethod
        def _q_parameter_sha256(network: object) -> str:
            del network
            return "a" * 64

    fake_v018 = SimpleNamespace(
        _V015=FakeV015,
        _live_digest=lambda environment, rng: "b" * 64,
    )
    formula_results = []
    for _ in range(adapter.DRAW_COUNT):
        formula_results.append(
            SimpleNamespace(
                schema="fake-formula",
                own_bits=np.asarray([1.0, 2.0]),
                nonfocal_bits=np.asarray([3.0, 4.0]),
                d_bits=np.asarray([5.0, 6.0]),
                joint_delta_bits=7.0,
                joint_delta_energy_j=8.0,
                joint_surplus_bits=9.0,
                interaction_bits=10.0,
                interaction_energy_j=11.0,
                interaction_surplus_bits=12.0,
                equal_share_bits=13.0,
                z3_bits=np.asarray([1.0, 2.0]),
                combined_bits=np.asarray([1.0, 2.0]),
                identity_residual_bits=0.0,
                q3_values=np.asarray([[0.0] * adapter.ACTIONS, [0.0] * adapter.ACTIONS]),
            )
        )
    fake_targets = SimpleNamespace(mean_targets=np.asarray([1.0, 2.0]))
    fake_teacher = SimpleNamespace(
        pair_id="pair-fake",
        pair_targets=fake_targets,
        formula_results=tuple(formula_results),
    )
    monkeypatch.setattr(adapter, "build_lcsrs_topology_teacher", lambda **kwargs: fake_teacher)
    step = FakeStep()
    _, profile_rows, diagnostics = adapter_instance._evaluate_pair(
        v018=fake_v018,
        environment=object(),
        env_rng=np.random.default_rng(7),
        step_env=step,
        observation=None,
        world=2026121705,
        anchor_id="w2026121705:t1",
        pair_index=0,
        pair=pair,
        anchor_data=anchor_data,
        interval_s=1.0,
        q1_network=object(),
        q2_network=object(),
        q1_before="a" * 64,
        q2_before="a" * 64,
    )
    assert len(profile_rows) == adapter.DRAW_COUNT
    assert step.calls == adapter.DRAW_COUNT * 4
    assert len({row["common_field_sha256"] for row in profile_rows}) == adapter.DRAW_COUNT
    assert all(len(row["profiles"]) == 4 for row in profile_rows)
    assert all(len(set(row["profiles"][code]["action_sha256"] for code in adapter.PROFILE_ORDER)) >= 1 for row in profile_rows)
    assert diagnostics["c1"]["target_filter_applied"] is False
    assert diagnostics["c2"]["target_filter_applied"] is False


def test_empty_placebo_receipt_is_explicitly_zero() -> None:
    receipt = adapter._placebo_strata_receipt(anchor_records=[None])
    assert receipt["supported_count"] == 0
    assert receipt["placebo_eligible_count"] == 0
    assert receipt["within_world_only"] is True
    assert receipt["outcome_filter_applied"] is False
    assert receipt["placebo_key_sha256"] == adapter.PLACEBO_KEY_SHA256


def test_npz_writer_is_atomic_and_refuses_overwrite(tmp_path: Path) -> None:
    destination = tmp_path / "world.arrays.npz"
    digest = adapter._write_npz_once(
        destination,
        {"x": np.arange(4, dtype=np.int64), "flags": np.asarray([True, False])},
    )
    assert len(digest) == 64
    assert adapter.file_sha256(destination) == digest
    assert not (tmp_path / "world.arrays.npz.sha256").exists()
    with pytest.raises(adapter.V023SourceAdapterError, match="overwrite"):
        adapter._write_npz_once(destination, {"x": np.arange(1, dtype=np.int64)})
