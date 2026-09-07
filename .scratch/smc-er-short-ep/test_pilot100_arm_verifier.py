from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "pilot100_arm_verifier", HERE / "pilot100_arm_verifier.py"
)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V
SPEC.loader.exec_module(V)


EPISODES = 2


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _write_episode_logs(root: Path) -> None:
    _write_json(
        root / "episode-logs.json",
        [{"episode": episode} for episode in range(EPISODES)],
    )


def _baseline_fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "B000"
    root.mkdir()
    _write_episode_logs(root)
    training_state = root / "training-state.pt"
    training_state.write_bytes(b"synthetic-baseline-state")
    status = {
        "result": {
            "dispatch": "unchanged_MODQNTrainer.train",
            "training_state": str(training_state.resolve()),
            "training_state_sha256": V.sha256_file(training_state),
        }
    }
    status_path = root / "status.json"
    _write_json(status_path, status)
    return status_path, training_state


def _treatment_fixture(tmp_path: Path, *, arm: str = "A011") -> dict[str, object]:
    root = tmp_path / arm
    root.mkdir()
    _write_episode_logs(root)
    expected_lanes = V.LANES[arm]
    expected_gates = V.GATES[arm]
    expected_sources = [source for source, enabled in expected_lanes.items() if enabled]

    main_rows = []
    eligibility_rows = []
    replay_rows = []
    for episode in range(EPISODES):
        for step in range(10):
            main_rows.append(
                {
                    "episode": episode,
                    "step": step,
                    "losses": [0.1, 0.2, 0.3],
                    "quota_receipt": {
                        "role_to_objective": {"C1": 0, "C2": 1, "C3": 2},
                        "dose_borrowing": False,
                        "requested_source_ids": expected_sources,
                        "runner_resubmits_deferred_bundles": False,
                    },
                }
            )
            for source in ("C2", "C3"):
                eligibility_rows.append(
                    {
                        "episode": episode,
                        "step": step,
                        "source": source,
                        "support_version": "V0.2_OBSERVABLE_ELIGIBILITY",
                        "future_outcome_used_for_admission": False,
                    }
                )
            for source in ("C1", "C2", "C3"):
                replay_rows.append(
                    {"episode": episode, "step": step, "source": source}
                )
    _write_json(root / "main-update-receipts.json", main_rows)
    _write_json(root / "role-eligibility-receipts.json", eligibility_rows)
    _write_json(root / "specialist-replay-receipts.json", replay_rows)

    carrier = root / "carrier-state.pt"
    rolling = root / "resume" / "latest-carrier-state.pt"
    rolling.parent.mkdir()
    carrier.write_bytes(b"synthetic-carrier-state")
    rolling.write_bytes(b"synthetic-rolling-carrier-state")
    result = {
        "lanes_informed": expected_lanes,
        "gates": expected_gates,
        "counterfactual_used_for_runtime_admission": False,
        "role_support_version": "V0.2_OBSERVABLE_ELIGIBILITY",
        "specialist_bundle_replay_capacity": 2000,
        "consumed_specialist_bundle_count": 7,
        "carrier_state": str(carrier.resolve()),
        "carrier_state_sha256": V.sha256_file(carrier),
        "rolling_resume_state": {
            "episodes_completed": EPISODES,
            "path": str(rolling.resolve()),
            "sha256": V.sha256_file(rolling),
        },
    }
    status_path = root / "status.json"
    _write_json(status_path, {"result": result})
    state_payload = {
        "schema": "smc-er-carrier-state-v1",
        "episodes_completed": EPISODES,
        "gates": expected_gates,
        "main_training_state": {},
        "specialists": {},
        "bundle_replays": {},
        "main_consumed_specialist_bundles": [],
        "source_rng_states": {},
    }
    return {
        "arm": arm,
        "root": root,
        "status_path": status_path,
        "carrier": carrier,
        "rolling": rolling,
        "state_payload": state_payload,
    }


def _mock_states(monkeypatch, payloads: dict[Path, dict[str, object]]) -> None:
    def fake_load(path, *, map_location, weights_only):
        assert map_location == "cpu"
        assert weights_only is False
        return payloads[Path(path).resolve()]

    monkeypatch.setattr(V.torch, "load", fake_load)


def test_valid_baseline_receipt_and_state_pass(tmp_path, monkeypatch):
    status_path, training_state = _baseline_fixture(tmp_path)
    _mock_states(
        monkeypatch,
        {
            training_state.resolve(): {
                "q_networks": {},
                "target_networks": {},
                "optimizers": {},
            }
        },
    )

    receipt = V.verify_pilot100_arm(
        status_path=status_path,
        arm="B000",
        episodes=EPISODES,
    )

    assert receipt["status"] == "PASS"
    assert receipt["receipt_artifacts"]["training_state"]["load_round_trip"] == "PASS"
    assert receipt["failures"] == []


def test_baseline_state_missing_core_key_fails(tmp_path, monkeypatch):
    status_path, training_state = _baseline_fixture(tmp_path)
    _mock_states(monkeypatch, {training_state.resolve(): {"optimizers": {}}})

    receipt = V.verify_pilot100_arm(
        status_path=status_path,
        arm="B000",
        episodes=EPISODES,
    )

    assert receipt["status"] == "FAIL"
    assert "baseline training state: core keys missing" in receipt["failures"]


def test_valid_treatment_grids_and_carrier_states_pass(tmp_path, monkeypatch):
    fixture = _treatment_fixture(tmp_path)
    payload = fixture["state_payload"]
    _mock_states(
        monkeypatch,
        {
            Path(fixture["carrier"]).resolve(): payload,
            Path(fixture["rolling"]).resolve(): payload,
        },
    )

    receipt = V.verify_pilot100_arm(
        status_path=Path(fixture["status_path"]),
        arm=str(fixture["arm"]),
        episodes=EPISODES,
    )

    assert receipt["status"] == "PASS"
    assert receipt["receipt_artifacts"]["main_update"]["rows"] == 20
    assert receipt["receipt_artifacts"]["role_eligibility"]["rows"] == 40
    assert receipt["receipt_artifacts"]["specialist_replay"]["rows"] == 60
    assert receipt["receipt_artifacts"]["carrier_state"]["load_round_trip"] == "PASS"
    assert receipt["failures"] == []


def test_duplicate_treatment_grid_cell_fails(tmp_path, monkeypatch):
    fixture = _treatment_fixture(tmp_path)
    path = Path(fixture["root"]) / "main-update-receipts.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows[-1]["episode"] = rows[0]["episode"]
    rows[-1]["step"] = rows[0]["step"]
    _write_json(path, rows)
    payload = fixture["state_payload"]
    _mock_states(
        monkeypatch,
        {
            Path(fixture["carrier"]).resolve(): payload,
            Path(fixture["rolling"]).resolve(): payload,
        },
    )

    receipt = V.verify_pilot100_arm(
        status_path=Path(fixture["status_path"]),
        arm=str(fixture["arm"]),
        episodes=EPISODES,
    )

    assert receipt["status"] == "FAIL"
    assert any("duplicate grid cell" in failure for failure in receipt["failures"])


def test_treatment_admission_and_state_semantic_drift_fail(tmp_path, monkeypatch):
    fixture = _treatment_fixture(tmp_path)
    eligibility_path = Path(fixture["root"]) / "role-eligibility-receipts.json"
    eligibility = json.loads(eligibility_path.read_text(encoding="utf-8"))
    eligibility[0]["future_outcome_used_for_admission"] = True
    _write_json(eligibility_path, eligibility)
    bad_payload = dict(fixture["state_payload"])
    bad_payload["episodes_completed"] = EPISODES - 1
    _mock_states(
        monkeypatch,
        {
            Path(fixture["carrier"]).resolve(): bad_payload,
            Path(fixture["rolling"]).resolve(): bad_payload,
        },
    )

    receipt = V.verify_pilot100_arm(
        status_path=Path(fixture["status_path"]),
        arm=str(fixture["arm"]),
        episodes=EPISODES,
    )

    assert receipt["status"] == "FAIL"
    assert any("future outcome admission forbidden" in failure for failure in receipt["failures"])
    assert any("carrier state episode mismatch" in failure for failure in receipt["failures"])
    assert any("rolling carrier state payload episode mismatch" in failure for failure in receipt["failures"])
