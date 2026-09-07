"""W-31 — corrected probes execute the frozen grid, not the old smoke grid."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.corrected_probes import (
    CORRECTED_PROBE_SEED,
    CORRECTIVE_PROTOCOL,
    assert_corrective_protocol_matches_plan,
    assert_decision_count,
    assert_live_ephemeris_unchanged,
    build_probe_fingerprint,
    build_probe_plan,
    create_fresh_output_dir,
    draw_matched_epochs,
    read_corrective_protocol,
    run_corrected_probes,
    summarise_calibration_gate,
)
from mcrl.runtime.prereg import read_prereg


REPO = Path(__file__).resolve().parents[1]
PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25.json"


def _load_launcher():
    path = REPO / "scripts" / "run_corrected_probes.py"
    spec = importlib.util.spec_from_file_location("run_corrected_probes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plan_is_derived_from_the_frozen_grid_and_corrective_seams():
    plan = build_probe_plan(read_prereg(PREREG))

    assert plan["master_seed"] == 20260823
    assert plan["steps_per_episode"] == 10
    assert plan["stream_layout"] == {
        "env": 0,
        "mobility": 1,
        "action": 2,
        "episode_epoch": 3,
    }
    assert plan["P2"] == {
        "episodes": 200,
        "users": 100,
        "policy": "stay-if-possible",
        "dwell_steps": [2, 3, 4],
    }
    assert plan["P3"] == {
        "episodes": 200,
        "users": 100,
        "policies": [
            "nearest-eligible",
            "random-masked",
            "stay-if-possible",
        ],
        "selection_mapping_policy": "stay-if-possible",
    }
    assert plan["P7"] == {
        "episodes": 100,
        "users": 100,
        "policy": "random-masked",
        "arms": {
            "main": {"mode": "uniform-episode-length"},
            "sensitivity": {
                "mode": "uniform-segment-length",
                "segment_age_steps": 6,
            },
        },
    }
    assert plan["runtime_invariants"] == {
        "warm_start_history_key": ["segment_age_steps", "norad_id"],
        "fading_path_key": ["user_id", "norad_id", "observation_step"],
        "candidate_previous_overlap": "reuse_candidate_draw",
    }


def test_corrective_execution_protocol_is_sealed_before_results():
    protocol = read_corrective_protocol(CORRECTIVE_PROTOCOL)

    assert protocol["status"] == "SEALED-BEFORE-CORRECTED-PROBE-RESULTS"
    assert protocol["augments_prereg_digest"] == (
        "d469d81fab617485b86897180ff52bacc2c514ca604bb676ab1585c8b15560f6"
    )
    assert protocol["master_seed"] == CORRECTED_PROBE_SEED
    assert protocol["stream_layout"] == {
        "env": 0,
        "mobility": 1,
        "action": 2,
        "episode_epoch": 3,
    }
    assert protocol["result_policy"]["p6_on_mapping_change"] == "BLOCK"
    assert protocol["result_policy"]["c1_comparison_decimals"] == 3


def test_protocol_result_and_epoch_policies_are_bound_to_the_runner():
    record = read_prereg(PREREG)
    plan = build_probe_plan(record)
    protocol = read_corrective_protocol(CORRECTIVE_PROTOCOL)

    changed = dict(protocol)
    changed["result_policy"] = dict(protocol["result_policy"]) | {
        "p6_on_mapping_change": "UNLOCK"
    }
    with pytest.raises(MCRLContractError, match="result_policy"):
        assert_corrective_protocol_matches_plan(changed, record, plan)

    changed = dict(protocol) | {"epoch_protocol": {"matching": "different"}}
    with pytest.raises(MCRLContractError, match="epoch_protocol"):
        assert_corrective_protocol_matches_plan(changed, record, plan)

    changed = dict(protocol) | {"master_seed_provenance": "chosen after results"}
    with pytest.raises(MCRLContractError, match="master_seed_provenance"):
        assert_corrective_protocol_matches_plan(changed, record, plan)


class _RecordingSampler:
    def draw(self, rng: np.random.Generator) -> int:
        return int(rng.integers(0, 2**31))


def test_epoch_schedule_is_deterministic_and_uses_the_fourth_seed_child():
    sampler = _RecordingSampler()
    actual = draw_matched_epochs(sampler, count=5, seed=CORRECTED_PROBE_SEED)

    child = np.random.SeedSequence(CORRECTED_PROBE_SEED).spawn(4)[3]
    rng = np.random.default_rng(child)
    expected = tuple(int(rng.integers(0, 2**31)) for _ in range(5))

    assert actual == expected
    assert actual == draw_matched_epochs(
        _RecordingSampler(), count=5, seed=CORRECTED_PROBE_SEED
    )


def test_output_directory_must_be_new(tmp_path):
    output = tmp_path / "rerun01"
    create_fresh_output_dir(output)
    assert output.is_dir()

    with pytest.raises(MCRLContractError, match="already exists"):
        create_fresh_output_dir(output)


def _p3_result(*, c1: float, c3: int) -> dict[str, object]:
    return {
        "r1": {"p95": -999.0},
        "r1_over_served_steps": {"p95": c1},
        "qd_scale_p95_rounded": c3,
        "decision_steps": 200_000,
    }


def test_calibration_gate_blocks_p6_if_either_frozen_mapping_moves():
    record = read_prereg(PREREG)
    changed = summarise_calibration_gate(
        record,
        {"stay-if-possible": _p3_result(c1=2_500_000.0, c3=7)},
    )

    assert changed["selection_mapping_policy"] == "stay-if-possible"
    assert changed["c1"]["matches_frozen"] is False
    assert changed["c3"]["matches_frozen"] is False
    assert changed["p6_unlocked"] is False
    assert changed["required_next_action"] == "corrective_refreeze"


def test_calibration_gate_passes_only_when_both_mappings_are_unchanged():
    record = read_prereg(PREREG)
    mappings = record.sections["selection_mappings"]
    unchanged = summarise_calibration_gate(
        record,
        {
            "stay-if-possible": _p3_result(
                c1=float(mappings["Q-F c1 calibration scale"]["resolved"]),
                c3=int(mappings["Q-D r3 calibration scale"]["resolved"]),
            )
        },
    )

    assert unchanged["c1"]["matches_frozen"] is True
    assert unchanged["c3"]["matches_frozen"] is True
    assert unchanged["p6_unlocked"] is True
    assert unchanged["required_next_action"] == "run_p6"


def test_c1_gate_compares_at_the_frozen_artifact_precision_not_binary_exactness():
    record = read_prereg(PREREG)
    old_full_precision_p95 = 2471140.576075691
    same_literal = summarise_calibration_gate(
        record,
        {"stay-if-possible": _p3_result(c1=old_full_precision_p95, c3=6)},
    )
    moved_literal = summarise_calibration_gate(
        record,
        {"stay-if-possible": _p3_result(c1=2471140.577, c3=6)},
    )

    assert same_literal["c1"]["matches_frozen"] is True
    assert same_literal["p6_unlocked"] is True
    assert moved_literal["c1"]["matches_frozen"] is False
    assert moved_literal["p6_unlocked"] is False


def test_actual_decision_rows_must_match_episodes_users_and_steps():
    assert_decision_count(
        {"decision_steps": 200_000}, expected=200_000, label="P3/stay"
    )
    with pytest.raises(MCRLContractError, match="expected 200000.*got 199999"):
        assert_decision_count(
            {"decision_steps": 199_999}, expected=200_000, label="P3/stay"
        )


def test_probe_fingerprint_covers_the_launcher_full_runtime_and_dependencies():
    fingerprint = build_probe_fingerprint(read_prereg(PREREG), PREREG)
    files = fingerprint["source_files_sha256"]

    assert "scripts/run_corrected_probes.py" in files
    assert "src/mcrl/env/ephemeris.py" in files
    assert "src/mcrl/runtime/training_pipeline.py" in files
    assert "pyproject.toml" in files
    assert set(fingerprint["dependencies"]) >= {"python", "numpy", "sgp4", "PyYAML"}
    assert len(fingerprint["fingerprint_sha256"]) == 64


def test_final_tle_check_reopens_the_root_instead_of_reusing_archive_cache(
    monkeypatch, tmp_path
):
    from mcrl.runtime import corrected_probes as runner
    from mcrl.runtime import training_pipeline

    stale = SimpleNamespace(root=tmp_path / "tle")
    fresh = object()
    reopened: list[Path] = []
    checked: list[object] = []
    monkeypatch.setattr(
        runner,
        "TleArchive",
        lambda root: (reopened.append(Path(root)), fresh)[1],
    )
    monkeypatch.setattr(
        training_pipeline,
        "assert_ephemeris_matches_record",
        lambda _record, *, archive: checked.append(archive),
    )

    assert_live_ephemeris_unchanged(object(), stale)

    assert reopened == [stale.root]
    assert checked == [fresh]


def test_cli_defaults_to_validation_and_run_surfaces_a_closed_p6_gate(
    monkeypatch, tmp_path, capsys
):
    launcher = _load_launcher()
    args = launcher.parse_args([])
    assert args.mode == "validate"
    assert args.prereg == launcher.CANONICAL_PREREG
    assert args.out_dir == launcher.DEFAULT_OUTPUT_DIR

    monkeypatch.setattr(
        launcher,
        "validate_corrected_probe_setup",
        lambda _path: (
            type("Record", (), {"digest": "seal"})(),
            {
                "P2": {"episodes": 200},
                "P3": {"episodes": 200, "policies": ["a", "b", "c"]},
                "P7": {"episodes": 100, "arms": {"main": {}, "sensitivity": {}}},
            },
            object(),
            tuple(range(200)),
        ),
    )
    assert launcher.main(["validate"]) == 0
    assert "corrected probe guards PASS" in capsys.readouterr().out

    monkeypatch.setattr(
        launcher,
        "run_corrected_probes",
        lambda _prereg, _output: {
            "status": "complete",
            "p6_unlocked": False,
            "calibration_gate": {"required_next_action": "corrective_refreeze"},
        },
    )
    exit_code = launcher.main(
        ["run", "--out-dir", str(tmp_path / "fresh-rerun")]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "P6 remains BLOCKED" in captured.err


def test_runner_executes_every_frozen_arm_and_writes_only_to_a_fresh_root(
    monkeypatch, tmp_path
):
    from mcrl.runtime import corrected_probes as runner

    record = read_prereg(PREREG)
    plan = build_probe_plan(record)
    epochs = tuple(
        dt.datetime(2026, 8, 8, tzinfo=dt.timezone.utc)
        + dt.timedelta(minutes=index)
        for index in range(200)
    )
    monkeypatch.setattr(
        runner,
        "validate_corrected_probe_setup",
        lambda _path: (record, plan, object(), epochs),
    )
    monkeypatch.setattr(runner, "_environment", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(runner, "_source_hashes", lambda _path: {"source": "hash"})
    monkeypatch.setattr(
        runner, "assert_live_ephemeris_unchanged", lambda _record, _archive: None
    )

    calls: list[str] = []
    mappings = record.sections["selection_mappings"]

    def fake_p3(*, policy, epochs, **_kwargs):
        calls.append(f"P3:{policy.name}:{len(epochs)}")
        return _p3_result(
            c1=float(mappings["Q-F c1 calibration scale"]["resolved"]),
            c3=int(mappings["Q-D r3 calibration scale"]["resolved"]),
        )

    def fake_p7(*, environment, epochs, **_kwargs):
        calls.append(f"P7:{len(epochs)}")
        return {
            "environment": str(environment),
            "epochs": len(epochs),
            "decision_steps": 100_000,
        }

    def fake_p2(*, epochs, dwell_candidates, **_kwargs):
        calls.append(f"P2:{len(epochs)}")
        return {
            "arms": {
                f"N={n}": {"decision_steps": 200_000}
                for n in dwell_candidates
            }
        }

    monkeypatch.setattr(runner, "run_probe_p3", fake_p3)
    monkeypatch.setattr(runner, "run_probe_p7", fake_p7)
    monkeypatch.setattr(runner, "run_probe_p2", fake_p2)

    output = tmp_path / "rerun01"
    summary = run_corrected_probes(PREREG, output)

    assert summary["p6_unlocked"] is True
    assert calls == [
        "P3:nearest-eligible:200",
        "P3:random-masked:200",
        "P3:stay-if-possible:200",
        "P7:100",
        "P7:100",
        "P2:200",
    ]
    assert sorted(path.name for path in output.iterdir()) == [
        "execution-manifest.json",
        "p2.json",
        "p3-nearest-eligible.json",
        "p3-random-masked.json",
        "p3-stay-if-possible.json",
        "p7-main.json",
        "p7-sensitivity.json",
        "status.json",
        "summary.json",
    ]
    assert json.loads((output / "status.json").read_text())["status"] == "complete"

    with pytest.raises(MCRLContractError, match="already exists"):
        run_corrected_probes(PREREG, output)
