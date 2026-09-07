from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import HandoverClass, NUM_ACTIONS, SlotTable


RUNNER = Path(__file__).with_name("run_c2_stage0.py")
SPEC = importlib.util.spec_from_file_location("run_c2_stage0", RUNNER)
assert SPEC is not None and SPEC.loader is not None
c2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c2)


def _table(rows: dict[int, tuple[int, int]]) -> SlotTable:
    norad = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cell = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=bool)
    for action, key in rows.items():
        norad[action], cell[action] = key
        mask[action] = True
    return SlotTable(norad_ids=norad, cell_ids=cell, mask=mask)


def test_forecast_rng_is_reproducible_and_domain_separated() -> None:
    kwargs = {"evaluation_seed": 17, "step_index": 2, "focal_user": 9}
    left = c2._derived_rng(c2.FORECAST_NAMESPACE, **kwargs).integers(
        0, 2**31, size=16
    )
    repeat = c2._derived_rng(c2.FORECAST_NAMESPACE, **kwargs).integers(
        0, 2**31, size=16
    )
    control = c2._derived_rng(c2.RANDOM_NAMESPACE, **kwargs).integers(
        0, 2**31, size=16
    )
    assert np.array_equal(left, repeat)
    assert not np.array_equal(left, control)


def test_realised_branch_rng_contract_requires_distinct_common_streams() -> None:
    def branch() -> dict:
        env_rng = np.random.default_rng(17)
        mobility_rng = np.random.default_rng(29)
        age_rng = np.random.default_rng(37)
        return {
            "env_rng": env_rng,
            "wrapped": SimpleNamespace(
                environment=SimpleNamespace(
                    _mobility_rng=mobility_rng,
                    _age_rng=age_rng,
                    physics=SimpleNamespace(fading_enabled=False),
                )
            ),
        }

    branches = {name: branch() for name in ("C2-PRE", "C2-STAY", "C2-RANDOM")}
    # Common-random-number lineage is equal by construction, while every
    # mutable generator is a distinct object and environment/mobility use
    # separate domains.
    assert c2._branch_rng_contract(branches)["passed"] is True

    branches["C2-STAY"]["env_rng"] = np.random.default_rng(31)
    assert c2._branch_rng_contract(branches)["passed"] is False


def test_physical_key_remapping_ignores_candidate_index() -> None:
    first = _table({0: (11, 3), 5: (22, 7)})
    reordered = _table({1: (22, 7), 9: (11, 3)})
    assert c2._action_for_key(first, (11, 3)) == 0
    assert c2._action_for_key(reordered, (11, 3)) == 9
    assert c2._key_for_action(reordered, 9) == (11, 3)
    assert c2._action_for_key(reordered, (99, 1)) is None


def test_select_pre_uses_r2_then_margin_then_physical_id() -> None:
    rows = [
        {
            "eligible": True,
            "s2_pre": -0.5,
            "worst_link_margin_w": 0.2,
            "candidate_key": [20, 2],
        },
        {
            "eligible": True,
            "s2_pre": -0.5,
            "worst_link_margin_w": 0.3,
            "candidate_key": [30, 3],
        },
        {
            "eligible": True,
            "s2_pre": -0.5,
            "worst_link_margin_w": 0.3,
            "candidate_key": [10, 1],
        },
        {
            "eligible": False,
            "s2_pre": 0.0,
            "worst_link_margin_w": 1.0,
            "candidate_key": [1, 1],
        },
    ]
    assert c2._select_pre(rows)["candidate_key"] == [10, 1]


@dataclass(frozen=True)
class _Physics:
    fading_enabled: bool = True


class _ReferenceEnvironment:
    def __init__(self, *, served: bool) -> None:
        self.physics = _Physics()
        self._served = served

    def evaluate_actions(self, actions, rng):
        del actions, rng
        return SimpleNamespace(
            resolution=SimpleNamespace(served=np.asarray([self._served]))
        )


def test_reference_anchor_requires_main_to_continue_and_serve_incumbent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _table({0: (11, 3), 1: (22, 7)})
    anchor = {
        "wrapped": SimpleNamespace(environment=_ReferenceEnvironment(served=True)),
        "states": [object()],
        "masks": [object()],
        "observation": SimpleNamespace(
            candidates=SimpleNamespace(slot_tables=[table])
        ),
    }
    monkeypatch.setattr(
        c2, "_main_actions", lambda trainer, states, masks: np.asarray([0])
    )
    assert c2._reference_incumbent_qualification(
        anchor, object(), focal_user=0, incumbent_key=(11, 3)
    ) == (True, None, (11, 3))

    monkeypatch.setattr(
        c2, "_main_actions", lambda trainer, states, masks: np.asarray([1])
    )
    assert c2._reference_incumbent_qualification(
        anchor, object(), focal_user=0, incumbent_key=(11, 3)
    )[1] == "main_reference_not_continuing_incumbent"

    anchor["wrapped"].environment = _ReferenceEnvironment(served=False)
    monkeypatch.setattr(
        c2, "_main_actions", lambda trainer, states, masks: np.asarray([0])
    )
    assert c2._reference_incumbent_qualification(
        anchor, object(), focal_user=0, incumbent_key=(11, 3)
    )[1] == "main_reference_incumbent_not_served"


def _forecast_observation(table: SlotTable) -> SimpleNamespace:
    return SimpleNamespace(candidates=SimpleNamespace(slot_tables=[table]))


class _ForecastWrapped:
    def __init__(
        self,
        tables_by_step: list[SlotTable],
        served_by_step: list[bool],
        *,
        done_at: int | None = None,
    ) -> None:
        self._tables_by_step = tables_by_step
        self._served_by_step = served_by_step
        self._done_at = done_at
        self._offset = 0
        self.actions: list[np.ndarray] = []
        self.last_outcome = None
        self.environment = SimpleNamespace(
            physics=SimpleNamespace(beam_power_max_w=2.0, fading_enabled=False)
        )

    def step(self, actions: np.ndarray, rng: np.random.Generator) -> SimpleNamespace:
        del rng
        offset = self._offset
        self.actions.append(np.asarray(actions).copy())
        table_index = min(offset + 1, len(self._tables_by_step) - 1)
        done = self._done_at is not None and offset == self._done_at
        self.last_outcome = SimpleNamespace(
            resolution=SimpleNamespace(
                served=np.asarray([self._served_by_step[offset]], dtype=bool)
            ),
            reward_matrix=np.asarray([[0.0, -float(offset + 1), 0.0]]),
            link_power_w=np.asarray([1.0]),
            observation=_forecast_observation(self._tables_by_step[table_index]),
        )
        self._offset += 1
        return SimpleNamespace(
            done=done,
            user_states=[object()],
            action_masks=[object()],
        )


def _run_forecast_fixture(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tables_by_step: list[SlotTable],
    served_by_step: list[bool],
    done_at: int | None = None,
    expected_anchor_fingerprint: dict | None = None,
    expected_anchor_fingerprint_sha256: str | None = None,
    anchor_fingerprint: dict | None = None,
    anchor_fingerprint_sha256: str | None = None,
) -> tuple[dict, _ForecastWrapped]:
    wrapped = _ForecastWrapped(
        tables_by_step, served_by_step, done_at=done_at
    )
    anchor = {
        "wrapped": wrapped,
        "states": [object()],
        "masks": [object()],
        "observation": _forecast_observation(tables_by_step[0]),
        "fingerprint": (
            {"fixture": "canonical"}
            if anchor_fingerprint is None
            else anchor_fingerprint
        ),
        "fingerprint_sha256": (
            "fixture-canonical"
            if anchor_fingerprint_sha256 is None
            else anchor_fingerprint_sha256
        ),
    }
    monkeypatch.setattr(
        c2,
        "_prepare_forecast_anchor",
        lambda *args, **kwargs: (
            anchor,
            np.random.default_rng(9),
            {"fixture": True},
        ),
    )
    monkeypatch.setattr(
        c2,
        "_main_actions",
        lambda trainer, states, masks: np.asarray([0], dtype=np.int32),
    )
    result = c2._forecast_candidate(
        object(),
        object(),
        seed=17,
        prefix_actions=(),
        step_index=0,
        focal_user=0,
        candidate_key=(11, 3),
        nonfocal_script=[(None,)] * (c2.RELEASE_OFFSET + 1),
        nonfocal_script_match=True,
        expected_anchor_fingerprint=expected_anchor_fingerprint,
        expected_anchor_fingerprint_sha256=expected_anchor_fingerprint_sha256,
    )
    return result, wrapped


def test_forecast_service_failure_keeps_interval_and_releases_next_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _table({0: (99, 1), 1: (11, 3)})
    result, wrapped = _run_forecast_fixture(
        monkeypatch,
        tables_by_step=[table] * 4,
        served_by_step=[False, True, True, True],
    )

    assert result["eligible"] is True
    assert result["failure"] is None
    assert len(result["intervals"]) == c2.RELEASE_OFFSET + 1
    assert [int(actions[0]) for actions in wrapped.actions] == [1, 0, 0, 0]
    assert result["intervals"][0]["controller"] == "persistence-option"
    assert result["intervals"][0]["termination_reason"] == "focal_service_failure"
    assert result["intervals"][1]["controller"] == "scalarized-main"
    assert result["intervals"][1]["focal_action_key"] == (99, 1)


def test_forecast_physical_expiry_keeps_interval_and_uses_main_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _table({0: (99, 1), 1: (11, 3)})
    main_only = _table({0: (99, 1)})
    result, wrapped = _run_forecast_fixture(
        monkeypatch,
        tables_by_step=[candidate, main_only, main_only, main_only],
        served_by_step=[True, True, True, True],
    )

    assert result["eligible"] is True
    assert len(result["intervals"]) == c2.RELEASE_OFFSET + 1
    assert [int(actions[0]) for actions in wrapped.actions] == [1, 0, 0, 0]
    assert result["intervals"][1]["termination_reason"] == "physical_id_expired"
    assert result["intervals"][1]["controller"] == "scalarized-main"
    assert result["intervals"][2]["controller"] == "scalarized-main"


def test_forecast_horizon_expiry_keeps_fourth_interval_on_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _table({0: (99, 1), 1: (11, 3)})
    result, wrapped = _run_forecast_fixture(
        monkeypatch,
        tables_by_step=[table] * 4,
        served_by_step=[True, True, True, True],
    )

    assert result["eligible"] is True
    assert [int(actions[0]) for actions in wrapped.actions] == [1, 1, 1, 0]
    assert result["intervals"][3]["termination_reason"] == "option_horizon_expired"
    assert result["intervals"][3]["controller"] == "scalarized-main"


def test_forecast_episode_end_after_fourth_interval_is_retained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _table({0: (99, 1), 1: (11, 3)})
    # Keep the option open through the final forecast interval so the
    # episode-end termination, rather than the normal three-step horizon, is
    # the recorded reason.
    monkeypatch.setattr(c2, "HOLD_STEPS", c2.RELEASE_OFFSET + 1)
    result, wrapped = _run_forecast_fixture(
        monkeypatch,
        tables_by_step=[table] * 4,
        served_by_step=[True, True, True, True],
        done_at=3,
    )

    assert result["eligible"] is True
    assert result["failure"] is None
    assert len(result["intervals"]) == c2.RELEASE_OFFSET + 1
    assert [int(actions[0]) for actions in wrapped.actions] == [1, 1, 1, 1]
    assert result["intervals"][3]["termination_reason"] == "episode_end"


def test_forecast_episode_end_before_horizon_is_structural_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _table({0: (99, 1), 1: (11, 3)})
    result, _ = _run_forecast_fixture(
        monkeypatch,
        tables_by_step=[table] * 4,
        served_by_step=[True, True, True, True],
        done_at=1,
    )

    assert result["eligible"] is False
    assert result["failure"] == "episode_end_before_forecast_horizon"
    assert len(result["intervals"]) == 2
    assert result["intervals"][1]["termination_reason"] == "episode_end"


def test_forecast_rejects_replay_anchor_fingerprint_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _table({0: (99, 1), 1: (11, 3)})
    result, wrapped = _run_forecast_fixture(
        monkeypatch,
        tables_by_step=[table] * 4,
        served_by_step=[True, True, True, True],
        expected_anchor_fingerprint={"fixture": "canonical"},
        expected_anchor_fingerprint_sha256="fixture-canonical",
        anchor_fingerprint={"fixture": "drifted"},
        anchor_fingerprint_sha256="fixture-drifted",
    )

    assert result["eligible"] is False
    assert result["failure"] == "forecast_anchor_fingerprint_mismatch"
    assert result["forecast_rng_independence"]["anchor_fingerprint_match"] is False
    assert wrapped.actions == []


def test_actual_replay_rejects_any_branch_anchor_fingerprint_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical = {"fixture": "canonical"}
    drifted = {"fixture": "drifted"}
    fingerprints = [canonical, drifted, canonical]
    calls = 0

    def fake_reconstruct(archive, *, seed, prefix_actions):
        del archive, seed, prefix_actions
        nonlocal calls
        fingerprint = fingerprints[calls]
        calls += 1
        return {
            "fingerprint": fingerprint,
            "fingerprint_sha256": (
                "fixture-canonical"
                if fingerprint is canonical
                else "fixture-drifted"
            ),
        }

    monkeypatch.setattr(c2, "_reconstruct_anchor", fake_reconstruct)
    result = c2._run_actual_branches(
        object(),
        object(),
        seed=17,
        prefix_actions=(),
        focal_user=0,
        choices={
            "C2-PRE": (11, 3),
            "C2-RANDOM": (22, 7),
            "C2-STAY": (33, 9),
        },
        expected_anchor_fingerprint=canonical,
        expected_anchor_fingerprint_sha256="fixture-canonical",
    )

    assert result["anchor_replay_fingerprint_match"] == {
        "C2-PRE": True,
        "C2-RANDOM": False,
        "C2-STAY": True,
    }
    assert result["engineering_failures"] == [
        "anchor_replay_fingerprint_mismatch_C2-RANDOM"
    ]
    assert result["metrics"] == {}


def test_forecast_all_unserved_fails_closed_without_margin_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _table({0: (99, 1), 1: (11, 3)})
    result, _ = _run_forecast_fixture(
        monkeypatch,
        tables_by_step=[table] * 4,
        served_by_step=[False, False, False, False],
    )

    assert result["eligible"] is False
    assert result["failure"] == "forecast_no_served_interval_for_link_margin"
    assert result["worst_link_margin_w"] is None
    assert len(result["intervals"]) == c2.RELEASE_OFFSET + 1
    assert c2._select_pre([result]) is None


def test_outcome_row_checks_canonical_ee_identity() -> None:
    table = _table({0: (11, 3)})
    observation = SimpleNamespace(
        candidates=SimpleNamespace(slot_tables=[table]),
        masks=np.asarray([[True] + [False] * (NUM_ACTIONS - 1)]),
    )
    outcome = SimpleNamespace(
        step_index=0,
        reward_matrix=np.zeros((1, 3)),
        resolution=SimpleNamespace(
            served=np.asarray([True]), served_count=1, active_beams={(11, 3)}
        ),
        handovers=[HandoverClass.NONE],
        link_rate_bps=np.asarray([10.0]),
        system_power_w=2.0,
        energy=SimpleNamespace(system_ee_bits_per_j=5.0),
    )
    kwargs = {
        "rng_before": {"environment_rng_sha256": "a", "mobility_rng_sha256": "b"},
        "rng_after": {"environment_rng_sha256": "c", "mobility_rng_sha256": "d"},
        "option_receipt": {"open_before": True},
        "preview_parity_passed": True,
    }
    row = c2._outcome_row(outcome, np.asarray([0]), observation, **kwargs)
    assert row["ee_identity_passed"] is True
    assert row["ee_identity_residual"] == pytest.approx(0.0)

    outcome.energy.system_ee_bits_per_j = 4.0
    row = c2._outcome_row(outcome, np.asarray([0]), observation, **kwargs)
    assert row["ee_identity_passed"] is False


def _metric(r2: float, ee: float = 10.0, service: float = 1.0) -> dict:
    return {
        "focal_r2": r2,
        "system_ee_bits_per_j": ee,
        "served_fraction": service,
        "focal_served_all": True,
    }


def _evaluated(seed: int, delta: float) -> dict:
    pre = {
        "full": _metric(delta, ee=11.0),
        "post_release": _metric(delta, ee=11.0),
    }
    control = {
        "full": _metric(0.0),
        "post_release": _metric(0.0),
    }
    return {
        "status": "evaluated",
        "evaluation_seed": seed,
        "step_index": 1,
        "focal_user": 0,
        "actual": {
            "engineering_failures": [],
            "metrics": {
                "C2-PRE": pre,
                "C2-RANDOM": control,
                "C2-STAY": control,
            },
        },
    }


def test_aggregate_pass_needs_five_seed_support_and_both_controls() -> None:
    rollouts = []
    for seed in range(5):
        rollouts.append(
            {
                "evaluation_seed": seed,
                "anchors": [_evaluated(seed, 1.0) for _ in range(4)],
            }
        )
    aggregate = c2._aggregate(rollouts)
    assert aggregate["evaluated_anchors"] == 20
    assert aggregate["decision"] == "C2_STAGE0_PASS_TO_FIXTURES_ONLY"


def test_aggregate_fails_closed_on_nonfocal_divergence() -> None:
    rollouts = []
    for seed in range(5):
        rows = [_evaluated(seed, 1.0) for _ in range(4)]
        rollouts.append({"evaluation_seed": seed, "anchors": rows})
    rollouts[0]["anchors"][0]["actual"]["engineering_failures"] = [
        "nonfocal_physical_action_divergence_offset_1"
    ]
    assert c2._aggregate(rollouts)["decision"] == "C2_STAGE0_CERTIFICATE_FAILURE"


def test_closure_manifest_is_required(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        c2._verify_closure(missing)


def test_seed_manifest_is_closure_bound_and_cross_role_disjoint(
    tmp_path: Path,
) -> None:
    path = tmp_path / "seeds.json"
    closure_sha = "a" * 64
    payload = {
        "schema": c2.SEED_SCHEMA,
        "closure_manifest_sha256": closure_sha,
        "c2_seeds": [1, 2, 3, 4, 5],
        "c3_seeds": [6, 7, 8, 9, 10],
        "repository_disjointness_checked_before_reveal": True,
        "disjointness_search_receipt_sha256": "b" * 64,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert c2._read_formal_seeds(path, closure_sha256=closure_sha) == (1, 2, 3, 4, 5)

    payload["c3_seeds"][0] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="mutually disjoint"):
        c2._read_formal_seeds(path, closure_sha256=closure_sha)
