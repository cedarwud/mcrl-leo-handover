from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_temporal_fork_segment_merge as merger  # noqa: E402


SOURCE_CLAIM = (
    "bounded implementation/smoke mechanics only; no EE efficacy, chapter-5 "
    "result, or deployment authorization"
)
TELEMETRY_CLAIM = (
    "training-carrier telemetry only; Main ratio-of-sums EE and C2 dose are "
    "descriptive, not an efficacy or Chapter-5 result"
)


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _telemetry(*, bits: float, energy: float, reward: float) -> dict:
    return {
        "schema": merger.TELEMETRY_SCHEMA,
        "claim_ceiling": TELEMETRY_CLAIM,
        "main": {
            "steps": 1,
            "useful_bits": bits,
            "energy_j": energy,
            "ratio_of_sums_ee_bits_per_j": bits / energy,
            "served_user_intervals": 1,
            "user_intervals": 1,
            "served_fraction": 1.0,
            "canonical_reward_sum": [reward, -1.0, -1.0],
        },
        "c2": {
            "schedules": 0,
            "empty_anchor_attempts": 0,
            "scheduled_candidates": 0,
            "candidate_outcomes": {
                "certificate_pass": 0,
                "certificate_fail": 0,
                "support_rejection": 0,
                "contract_error": 0,
            },
            "choice_counts": {"K0": 0, "K1": 0, "K>=2": 0},
            "forecast_wall_time_s": 0.0,
            "options_executed": 0,
            "option_primitive_steps": 0,
            "admitted_options": 0,
            "q2f_updates": 0,
            "joint_commits": 0,
            "joint_commit_per_main_step": 0.0,
        },
    }


def _make_segment(
    root: Path,
    *,
    episode: int,
    total_episodes: int = 2,
    bits: float = 10.0,
    energy: float = 1.0,
    beta: float = 0.25,
    authority_suffix: str = "a",
    claim: str = SOURCE_CLAIM,
) -> Path:
    root.mkdir(parents=True)
    telemetry = _telemetry(bits=bits, energy=energy, reward=bits)
    episode_row = {
        "episode": episode,
        "epsilon": 1.0,
        "main_source_reward_sum": telemetry["main"]["canonical_reward_sum"],
        "main_steps": 1,
        "c2_environment_steps": 1,
        "c2_options": 0,
        "c2_admitted_options": 0,
        "c2_updated_options": 0,
        "active_sources": ["C1", "C2", "C3"],
        "frozen_main_comparator_sha256": "f" * 64,
        "telemetry": telemetry,
    }
    main_receipt = {
        "episode": episode,
        "step": 0,
        "main_bundle_id": f"bundle-{episode}",
        "main_replay_rows": episode + 1,
        "c2_training": None,
        "main_carrier": {},
        "main_update_calls": 1,
        "c2_environment_steps_consumed": 1,
        "formal_c2_owned_main_update": False,
    }
    artifacts = {
        "episode-logs.json": [episode_row],
        "c2-training-receipts.json": [],
        "main-update-receipts.json": [main_receipt],
        "c2-option-chronology-audits.json": [],
        "run-telemetry.json": telemetry,
    }
    for name, value in artifacts.items():
        _write_json(root / name, value)
    authority = {
        "prereg_path": f"/host/{authority_suffix}/prereg.json",
        "prereg_sha256": authority_suffix * 64,
        "tle_file_count": 373,
        "tle_file_set_sha256": "b" * 64,
        "tle_root_path": f"/host/{authority_suffix}/tle",
    }
    result = {
        "dispatch": "C2-V0.3-formal-selection-training-step-joint-transaction",
        "episodes": total_episodes,
        "start_episode": episode,
        "episodes_executed": 1,
        "episodes_completed": episode + 1,
        "active_sources": ["C1", "C2", "C3"],
        "claim_ceiling": claim,
        "episode_rows": [episode_row],
        "telemetry": telemetry,
        "telemetry_sha256": _sha(root / "run-telemetry.json"),
        "c2_option_chronology_audit_count": 0,
        "c2_option_chronology_audit_sha256": _sha(
            root / "c2-option-chronology-audits.json"
        ),
        "periodic_checkpoints": [],
        "periodic_checkpoint_count": 0,
    }
    status = {
        "schema": merger.STATUS_SCHEMA,
        "status": "complete",
        "arm": "F111",
        "label": "synthetic bounded segment",
        "claim_ceiling": claim,
        "trainer_config": {
            "activation": "tanh",
            "hidden_layers": [100, 50, 50],
            "learning_rate": 0.001,
        },
        "authority": authority,
        "config": {
            "arm": "F111",
            "beta": beta,
            "checkpoint_every": 1,
            "env_seed": 2,
            "episodes": total_episodes,
            "max_c2_candidates": 1,
            "mobility_seed": 3,
            "train_seed": 1,
            "users": 1,
        },
        "result": result,
        "runtime": {"python": "test", "numpy": "test", "torch": "test"},
    }
    _write_json(root / "status.json", status)
    return root


def _rewrite_status(root: Path, mutate) -> None:
    path = root / "status.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    _write_json(path, value)


def _rewrite_consistent_telemetry(root: Path, mutate) -> None:
    run_path = root / "run-telemetry.json"
    telemetry = json.loads(run_path.read_text(encoding="utf-8"))
    mutate(telemetry)
    _write_json(run_path, telemetry)

    episodes_path = root / "episode-logs.json"
    episodes = json.loads(episodes_path.read_text(encoding="utf-8"))
    episodes[0]["telemetry"] = copy.deepcopy(telemetry)
    episodes[0]["main_source_reward_sum"] = copy.deepcopy(
        telemetry["main"]["canonical_reward_sum"]
    )
    _write_json(episodes_path, episodes)

    def update(status):
        status["result"]["telemetry"] = copy.deepcopy(telemetry)
        status["result"]["telemetry_sha256"] = _sha(run_path)
        status["result"]["episode_rows"] = copy.deepcopy(episodes)

    _rewrite_status(root, update)


def test_merges_contiguous_segments_and_uses_ratio_of_sums(tmp_path: Path):
    first = _make_segment(tmp_path / "first", episode=0, bits=10.0, energy=1.0)
    second = _make_segment(tmp_path / "second", episode=1, bits=10.0, energy=9.0)
    output = tmp_path / "merged"

    receipt = merger.merge_segments([first, second], output)

    telemetry = json.loads((output / "run-telemetry.json").read_text())
    assert receipt["status"] == "PASS"
    assert receipt["episode_range"] == {
        "start_episode": 0,
        "episodes_completed": 2,
        "episode_count": 2,
    }
    assert telemetry["main"]["useful_bits"] == pytest.approx(20.0)
    assert telemetry["main"]["energy_j"] == pytest.approx(10.0)
    assert telemetry["main"]["ratio_of_sums_ee_bits_per_j"] == pytest.approx(2.0)
    assert telemetry["main"]["ratio_of_sums_ee_bits_per_j"] != pytest.approx(
        (10.0 + 10.0 / 9.0) / 2.0
    )
    assert len(json.loads((output / "episode-logs.json").read_text())) == 2


@pytest.mark.parametrize(
    ("episodes", "match"),
    [((0, 2), "gap"), ((0, 0), "overlap")],
)
def test_rejects_gap_and_overlap(tmp_path: Path, episodes, match):
    first = _make_segment(tmp_path / "first", episode=episodes[0], total_episodes=3)
    second = _make_segment(tmp_path / "second", episode=episodes[1], total_episodes=3)
    with pytest.raises(merger.SegmentMergeError, match=match):
        merger.merge_segments([first, second], tmp_path / "merged")


def test_rejects_config_mismatch(tmp_path: Path):
    first = _make_segment(tmp_path / "first", episode=0)
    second = _make_segment(tmp_path / "second", episode=1, beta=0.5)
    with pytest.raises(merger.SegmentMergeError, match="config differs"):
        merger.merge_segments([first, second], tmp_path / "merged")


def test_rejects_authority_identity_mismatch_but_not_locator_drift(tmp_path: Path):
    first = _make_segment(tmp_path / "first", episode=0)
    second = _make_segment(tmp_path / "second", episode=1)
    _rewrite_status(
        second,
        lambda status: status["authority"].update(
            prereg_path="/different-host/prereg.json",
            tle_root_path="/different-host/tle",
        ),
    )
    merger.merge_segments([first, second], tmp_path / "locator-only")

    third = _make_segment(tmp_path / "third", episode=1, authority_suffix="c")
    with pytest.raises(merger.SegmentMergeError, match="authority differs"):
        merger.merge_segments([first, third], tmp_path / "identity-drift")


def test_rejects_claim_ceiling_mismatch(tmp_path: Path):
    first = _make_segment(tmp_path / "first", episode=0)
    second = _make_segment(tmp_path / "second", episode=1, claim="different claim")
    with pytest.raises(merger.SegmentMergeError, match="claim_ceiling differs"):
        merger.merge_segments([first, second], tmp_path / "merged")


def test_rejects_duplicate_or_reordered_main_step_identity(tmp_path: Path):
    segment = _make_segment(tmp_path / "segment", episode=0, total_episodes=1)
    path = segment / "main-update-receipts.json"
    rows = json.loads(path.read_text())
    rows.append(copy.deepcopy(rows[0]))
    _write_json(path, rows)
    with pytest.raises(merger.SegmentMergeError, match="chronology or coverage"):
        merger.merge_segments([segment], tmp_path / "merged")


@pytest.mark.parametrize("bad_ratio", [999.0, True])
def test_rejects_tampered_or_boolean_telemetry_ratio(tmp_path: Path, bad_ratio):
    segment = _make_segment(tmp_path / "segment", episode=0, total_episodes=1)
    _rewrite_consistent_telemetry(
        segment,
        lambda telemetry: telemetry["main"].update(
            ratio_of_sums_ee_bits_per_j=bad_ratio
        ),
    )
    with pytest.raises(merger.SegmentMergeError, match="ratio_of_sums"):
        merger.merge_segments([segment], tmp_path / "merged")


def test_refuses_to_overwrite_output(tmp_path: Path):
    segment = _make_segment(tmp_path / "segment", episode=0, total_episodes=1)
    output = tmp_path / "merged"
    output.mkdir()
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        merger.merge_segments([segment], output)


def test_output_publish_is_atomic_on_write_failure(tmp_path: Path, monkeypatch):
    segment = _make_segment(tmp_path / "segment", episode=0, total_episodes=1)
    output = tmp_path / "merged"
    original = merger._write_json
    calls = 0

    def fail_second_write(path, value):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected output failure")
        original(path, value)

    monkeypatch.setattr(merger, "_write_json", fail_second_write)
    with pytest.raises(OSError, match="injected output failure"):
        merger.merge_segments([segment], output)
    assert not output.exists()
    assert list(tmp_path.glob(".merged.staging-*")) == []
