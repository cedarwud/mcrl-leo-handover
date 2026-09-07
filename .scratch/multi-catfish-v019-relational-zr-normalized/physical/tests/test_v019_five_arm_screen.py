from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "v019_five_arm_screen.py"
SPEC = importlib.util.spec_from_file_location("v019_five_arm_screen_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def digest(char: str) -> str:
    return char * 64


def surfaces() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    q1 = np.zeros((2, 28), dtype=np.float64)
    q2 = np.zeros((2, 28), dtype=np.float64)
    q3 = np.zeros((2, 28), dtype=np.float64)
    masks = np.zeros((2, 28), dtype=np.bool_)
    masks[:, :3] = True
    q1[0, :3] = [3.0, 0.0, 0.0]
    q2[0, :3] = [0.0, 2.0, 0.0]
    q3[0, :3] = [0.0, 0.0, 5.0]
    q1[1, :3] = [0.0, 4.0, 0.0]
    q2[1, :3] = [0.0, 0.0, 3.0]
    q3[1, :3] = [6.0, 0.0, 0.0]
    return q1, q2, q3, masks


def test_q3_reference_is_q1_plus_q2_and_active_drop_routes_reuse_binding() -> None:
    q1, q2, q3, masks = surfaces()
    refs = MODULE.q3_reference_actions(q1, q2, masks)
    assert refs.tolist() == [0, 1]
    binding = MODULE.Q3InputBinding.from_reference_and_state(refs, np.arange(7))

    full = MODULE.compose_route_scores(
        q1, q2, q3, masks, "FULL", reference_actions=refs, q3_input=binding
    )
    drop_c1 = MODULE.compose_route_scores(
        q1, q2, q3, masks, "DROP_C1", reference_actions=refs, q3_input=binding
    )
    drop_c2 = MODULE.compose_route_scores(
        q1, q2, q3, masks, "DROP_C2", reference_actions=refs, q3_input=binding
    )
    assert full.selected_actions.tolist() == [2, 0]
    assert drop_c1.selected_actions.tolist() == [2, 0]
    assert drop_c2.selected_actions.tolist() == [2, 0]
    assert full.q3_evaluated and drop_c1.q3_evaluated and drop_c2.q3_evaluated
    assert np.array_equal(full.q3_reference_actions, refs)
    assert np.array_equal(drop_c1.q3_reference_actions, refs)
    assert np.array_equal(drop_c2.q3_reference_actions, refs)


def test_q3_reference_cannot_be_recomputed_under_a_dropped_head() -> None:
    q1, q2, q3, masks = surfaces()
    refs = MODULE.q3_reference_actions(q1, q2, masks)
    binding = MODULE.Q3InputBinding.from_reference_and_state(refs, np.arange(7))
    changed = refs.copy()
    changed[0] = 2
    with pytest.raises(MODULE.V019FiveArmScreenError, match="reference actions changed"):
        MODULE.compose_route_scores(
            q1,
            q2,
            q3,
            masks,
            "DROP_C1",
            reference_actions=changed,
            q3_input=binding,
        )


def test_drop_c3_does_not_evaluate_or_carry_q3() -> None:
    q1, q2, q3, masks = surfaces()
    route = MODULE.compose_route_scores(q1, q2, None, masks, "DROP_C3")
    assert not route.q3_evaluated
    assert route.q3_input is None
    with pytest.raises(MODULE.V019FiveArmScreenError, match="must not evaluate Q3"):
        MODULE.compose_route_scores(q1, q2, q3, masks, "DROP_C3")


def _bindings() -> tuple[MODULE.LineageBinding, ...]:
    return tuple(
        MODULE.LineageBinding(
            initialization_seed=2026120511 + index,
            source_lineage=2026092101 + index,
            q1_checkpoint_sha256=digest(chr(ord("a") + index)),
            q2_checkpoint_sha256=digest(chr(ord("d") + index)),
            q3_checkpoint_sha256=digest(str(index + 1)),
        )
        for index in range(3)
    )


def test_v019_rejects_raw_q3_output_mode_at_every_binding_boundary() -> None:
    q1, q2, _q3, masks = surfaces()
    refs = MODULE.q3_reference_actions(q1, q2, masks)
    with pytest.raises(MODULE.V019FiveArmScreenError, match="output unit mode"):
        MODULE.Q3InputBinding.from_reference_and_state(refs, np.arange(7)).__class__(
            reference_actions_sha256=digest("1"),
            state_sha256=digest("2"),
            output_unit_mode="raw_bits",
        ).verify()

    binding = MODULE.LineageBinding(
        initialization_seed=1,
        source_lineage=2,
        q1_checkpoint_sha256=digest("3"),
        q2_checkpoint_sha256=digest("4"),
        q3_checkpoint_sha256=digest("5"),
    )
    with pytest.raises(MODULE.V019FiveArmScreenError, match="normalized_bits_per_kappa"):
        replace(binding, q3_output_unit_mode="raw_bits").verify()

    spec = _spec()
    with pytest.raises(MODULE.V019FiveArmScreenError, match="normalized_bits_per_kappa"):
        replace(spec, output_unit_mode="raw_bits").verify()


def _spec() -> MODULE.V019FiveArmScreenSpec:
    seeds = tuple(2027000001 + index for index in range(100))
    # Use readable, deterministic hexadecimal roots; each world has one
    # distinct field root.
    fields = tuple((seed, f"{index + 1:064x}") for index, seed in enumerate(seeds))
    return MODULE.V019FiveArmScreenSpec(
        evaluation_seeds=seeds,
        field_component="v019-test-field",
        field_root_digests=fields,
        lineage_bindings=_bindings(),
        main_policy_sha256=digest("e"),
    )


def _receipt(
    *,
    arm: str,
    episode_index: int,
    evaluation_seed: int,
    lineage: MODULE.LineageBinding | None,
    field_root_digest: str,
    bits: float,
) -> MODULE.V019EpisodeReceipt:
    if lineage is None:
        return MODULE.V019EpisodeReceipt(
            arm=arm,
            episode_index=episode_index,
            evaluation_seed=evaluation_seed,
            total_bits=bits,
            total_energy_j=1.0,
            decision_count=1000,
            served_user_steps=1000,
            field_root_digest=field_root_digest,
            main_policy_sha256=digest("e"),
        )
    active = arm in MODULE.Q3_ACTIVE_ARMS
    return MODULE.V019EpisodeReceipt(
        arm=arm,
        episode_index=episode_index,
        evaluation_seed=evaluation_seed,
        total_bits=bits,
        total_energy_j=1.0,
        decision_count=1000,
        served_user_steps=1000,
        field_root_digest=field_root_digest,
        initialization_seed=lineage.initialization_seed,
        source_lineage=lineage.source_lineage,
        q1_checkpoint_sha256=lineage.q1_checkpoint_sha256,
        q2_checkpoint_sha256=lineage.q2_checkpoint_sha256,
        q3_checkpoint_sha256=lineage.q3_checkpoint_sha256,
        q3_evaluated=active,
        q3_reference_mode=MODULE.Q3_REFERENCE_MODE if active else "NOT_APPLICABLE",
        q3_reference_actions_sha256=digest("4") if active else None,
        q3_state_sha256=digest("5") if active else None,
        q3_state_schema=MODULE.Q3_STATE_SCHEMA if active else None,
        q3_output_unit_mode=MODULE.Q3_OUTPUT_UNIT_MODE,
    )


def test_short_screen_runner_writes_100_episode_checkpoints_and_ordering(tmp_path: Path) -> None:
    spec = _spec()
    values = {"FULL": 120.0, "DROP_C1": 110.0, "DROP_C2": 105.0, "DROP_C3": 100.0}

    def route_runner(**kwargs: object) -> MODULE.V019EpisodeReceipt:
        lineage = kwargs["lineage"]
        assert isinstance(lineage, MODULE.LineageBinding)
        return _receipt(
            arm=str(kwargs["arm"]),
            episode_index=int(kwargs["episode_index"]),
            evaluation_seed=int(kwargs["evaluation_seed"]),
            lineage=lineage,
            field_root_digest=str(kwargs["field_root_digest"]),
            bits=values[str(kwargs["arm"])],
        )

    def main_runner(**kwargs: object) -> MODULE.V019EpisodeReceipt:
        return _receipt(
            arm=MODULE.MAIN_ARM,
            episode_index=int(kwargs["episode_index"]),
            evaluation_seed=int(kwargs["evaluation_seed"]),
            lineage=None,
            field_root_digest=str(kwargs["field_root_digest"]),
            bits=90.0,
        )

    result = MODULE.run_five_arm_screen(
        spec=spec,
        route_episode_runner=route_runner,
        main_episode_runner=main_runner,
        output_dir=tmp_path / "screen",
    )
    assert result["status"] == "COMPLETE_PLUMBING_ONLY"
    assert result["output_unit_mode"] == MODULE.Q3_OUTPUT_UNIT_MODE
    assert result["ordering"]["status"] == "PASS_SHORT_SCREEN_ORDERING"
    assert result["ordering"]["required_ordering"]["FULL_greater_than_each_drop"] == {
        "DROP_C1": True,
        "DROP_C2": True,
        "DROP_C3": True,
    }
    assert result["ordering"]["required_ordering"]["each_drop_greater_than_MAIN"] == {
        "DROP_C1": True,
        "DROP_C2": True,
        "DROP_C3": True,
    }
    checkpoints = sorted((tmp_path / "screen" / "checkpoints").glob("*.json"))
    assert [path.name for path in checkpoints] == [
        "drop_c1-episode-000100.json",
        "drop_c2-episode-000100.json",
        "drop_c3-episode-000100.json",
        "full-episode-000100.json",
        "main-episode-000100.json",
    ]
    for checkpoint in checkpoints:
        payload = checkpoint.read_text(encoding="utf-8")
        assert '"output_unit_mode": "normalized_bits_per_kappa"' in payload
    assert result["summaries"]["FULL"]["pooled_ratio_of_sums_ee_bits_per_j"] > result[
        "summaries"
    ]["DROP_C1"]["pooled_ratio_of_sums_ee_bits_per_j"]


def test_runner_rejects_active_q3_input_drift_between_arms() -> None:
    spec = _spec()
    calls: dict[tuple[int, int, str], int] = {}

    def route_runner(**kwargs: object) -> MODULE.V019EpisodeReceipt:
        arm = str(kwargs["arm"])
        lineage = kwargs["lineage"]
        assert isinstance(lineage, MODULE.LineageBinding)
        key = (int(kwargs["episode_index"]), int(kwargs["evaluation_seed"]), arm)
        calls[key] = 1
        receipt = _receipt(
            arm=arm,
            episode_index=key[0],
            evaluation_seed=key[1],
            lineage=lineage,
            field_root_digest=str(kwargs["field_root_digest"]),
            bits=100.0,
        )
        if arm == "DROP_C2":
            object.__setattr__(receipt, "q3_state_sha256", digest("6"))
        return receipt

    def main_runner(**kwargs: object) -> MODULE.V019EpisodeReceipt:
        return _receipt(
            arm=MODULE.MAIN_ARM,
            episode_index=int(kwargs["episode_index"]),
            evaluation_seed=int(kwargs["evaluation_seed"]),
            lineage=None,
            field_root_digest=str(kwargs["field_root_digest"]),
            bits=90.0,
        )

    # The short spec is intentionally large enough to satisfy the production
    # 100-episode cadence; the callback fails before completing it.
    with pytest.raises(MODULE.V019FiveArmScreenError, match="changed the learned Q3 input"):
        MODULE.run_five_arm_screen(
            spec=spec,
            route_episode_runner=route_runner,
            main_episode_runner=main_runner,
        )
