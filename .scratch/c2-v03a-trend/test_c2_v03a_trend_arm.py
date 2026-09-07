"""Public arm-launcher tests for the C2 V0.3A trend carrier."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_v03a_trend_arm as arm_runner  # noqa: E402


def test_execution_controls_allow_short_checkpoint_gate_for_baseline_and_treatment():
    for arm in ("B000", "F111"):
        arm_runner._execution_controls(
            arm=arm,
            stop_after_episodes=2,
            checkpoint_every_override=1,
            resume_state=None,
        )


def test_execution_controls_reject_checkpoint_override_on_long_run():
    try:
        arm_runner._execution_controls(
            arm="F111",
            stop_after_episodes=None,
            checkpoint_every_override=1,
            resume_state=None,
        )
    except arm_runner.V03ATrendArmError as error:
        assert "bounded throughput smoke" in str(error)
    else:  # pragma: no cover
        raise AssertionError("long-run checkpoint cadence override was accepted")


def test_execution_controls_expose_treatment_resume_but_not_baseline(tmp_path):
    resume = tmp_path / "state.pt"
    arm_runner._execution_controls(
        arm="F111",
        stop_after_episodes=None,
        checkpoint_every_override=None,
        resume_state=resume,
    )
    try:
        arm_runner._execution_controls(
            arm="B000",
            stop_after_episodes=None,
            checkpoint_every_override=None,
            resume_state=resume,
        )
    except arm_runner.V03ATrendArmError as error:
        assert "treatment-only" in str(error)
    else:  # pragma: no cover
        raise AssertionError("baseline was routed through the C2 resume seam")


def test_execute_arm_binds_formal_schedule_prefill_and_100ep_checkpoints(
    monkeypatch, tmp_path
):
    authority_path = tmp_path / "authority.json"
    authority_path.write_text("{}\n", encoding="utf-8")
    prereg = tmp_path / "prereg.json"
    prereg.write_text("{}\n", encoding="utf-8")
    corpus = tmp_path / "c1.json"
    corpus.write_text("{}\n", encoding="utf-8")
    tle_root = tmp_path / "tle"
    tle_root.mkdir()
    validated = {
        "status": "PASS",
        "claim_ceiling": "trend-only",
        "formal_training_authorized": False,
        "c1_route_status": arm_runner.C1_ROUTE_STATUS,
        "c2_route_status": arm_runner.C2_ROUTE_STATUS,
        "c3_route_status": arm_runner.C3_ROUTE_STATUS,
        "episodes": 1500,
        "learning_rate": 0.01,
        "arms": ["B000", "F111", "A011", "A101", "A110"],
        "seeds": {
            "training": 2026082901,
            "environment": 2026082902,
            "mobility": 2026082903,
        },
        "users": 100,
        "epsilon_decay_episodes": 2000,
        "target_update_every": 50,
        "checkpoint_every_episodes": 100,
        "max_c2_candidates": 9,
        "donor_beta": 0.25,
        "acrm_eta": 1.0,
        "canonical_prereg": str(prereg),
        "c1_exp_corpus_manifest": str(corpus),
        "tle_file_set_sha256": "a" * 64,
        "tle_file_count": 373,
    }
    monkeypatch.setattr(
        arm_runner,
        "load_and_validate_authority",
        lambda *_args, **_kwargs: validated,
    )
    archive = SimpleNamespace(root=tle_root)
    monkeypatch.setattr(
        arm_runner.legacy,
        "_canonical_ephemeris_authority",
        lambda *_args, **_kwargs: (
            object(),
            archive,
            {"tle_file_set_sha256": "a" * 64, "tle_file_count": 373},
        ),
    )
    config_calls = []

    def short_config(prereg_record, **kwargs):
        config_calls.append((prereg_record, kwargs))
        return SimpleNamespace(episodes=kwargs["episodes"], learning_rate=kwargs["learning_rate"])

    monkeypatch.setattr(arm_runner.legacy, "_short_config", short_config)
    run_calls = []

    def run_loop(**kwargs):
        run_calls.append(kwargs)
        return {
            "dispatch": "c2-v03a-fixture",
            "checkpoint": str(tmp_path / "final.pt"),
            "checkpoint_sha256": "b" * 64,
            "episodes_completed": 1500,
            "periodic_checkpoint_count": 15,
            "c1_prefill": {"bundles": 60, "enters_main": False},
        }

    monkeypatch.setattr(arm_runner.c2_runner, "run_c2_v03_episode_loop", run_loop)

    status = arm_runner.execute_arm(
        authority_path=authority_path,
        arm="F111",
        output_dir=tmp_path / "out",
        tle_root=tle_root,
    )

    assert config_calls[0][1] == {
        "arm": "F111",
        "episodes": 1500,
        "epsilon_decay_episodes": 2000,
        "target_update_every": 50,
        "learning_rate": 0.01,
    }
    call = run_calls[0]
    assert call["config"].checkpoint_every == 100
    assert call["config"].max_c2_candidates == 9
    assert call["c1_corpus_manifest"] == corpus.resolve()
    assert status["status"] == "complete"
    assert status["c3_route_status"].startswith("DEVELOPMENT_ONLY")
    assert status["role_route_status"] == {
        "C1": arm_runner.C1_ROUTE_STATUS,
        "C2": arm_runner.C2_ROUTE_STATUS,
        "C3": arm_runner.C3_ROUTE_STATUS,
    }
    assert json.loads((tmp_path / "out" / "status.json").read_text())["arm"] == "F111"
