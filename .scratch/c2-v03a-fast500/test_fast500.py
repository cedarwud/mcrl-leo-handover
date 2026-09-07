from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import fast500_matrix as matrix
import fast500_prefix_arm as prefix


def _validated() -> dict:
    return {
        "episodes": 1500,
        "learning_rate": 0.001,
        "arms": ["B000", "F111", "A011", "A101", "A110"],
        "canonical_prereg": "prereg.json",
        "c1_exp_corpus_manifest": "corpus.json",
        "tle_file_set_sha256": "a" * 64,
        "tle_file_count": 3,
        "epsilon_decay_episodes": 2000,
        "target_update_every": 50,
        "checkpoint_every_episodes": 100,
        "users": 100,
        "seeds": {"training": 1, "environment": 2, "mobility": 3},
        "donor_beta": 0.25,
        "max_c2_candidates": 9,
        "acrm_eta": 1.0,
    }


def test_parse_reuse_is_exact(tmp_path):
    checkpoint = tmp_path / "ep.pt"
    checkpoint.write_bytes(b"checkpoint")
    assert matrix._parse_reuse([f"0.001:A011={checkpoint}"]) == {
        ("0.001", "A011"): checkpoint.resolve()
    }
    with pytest.raises(matrix.Fast500MatrixError):
        matrix._parse_reuse([f"0.1:A011={checkpoint}"])
    with pytest.raises(matrix.Fast500MatrixError):
        matrix._parse_reuse([f"0.001:B000={checkpoint}"])


def test_stable_snapshot_is_create_only(tmp_path):
    source = tmp_path / "source.pt"
    destination = tmp_path / "snapshots" / "copy.pt"
    source.write_bytes(b"stable")
    digest = matrix._stable_snapshot(source, destination)
    assert digest == prefix.sha256_file(source) == prefix.sha256_file(destination)
    with pytest.raises(FileExistsError):
        matrix._stable_snapshot(source, destination)


def test_prefix_runs_same_1500_schedule_to_exact_ep500(monkeypatch, tmp_path):
    authority = tmp_path / "authority.json"
    authority.write_text("{}\n", encoding="utf-8")
    prereg = tmp_path / "prereg.json"
    corpus = tmp_path / "corpus.json"
    prereg.write_text("{}\n", encoding="utf-8")
    corpus.write_text("{}\n", encoding="utf-8")
    output = tmp_path / "output"

    validated = _validated()
    monkeypatch.setattr(prefix.trend_arm, "load_and_validate_authority", lambda *_a, **_k: validated)
    monkeypatch.setattr(
        prefix.trend_arm,
        "_repo_file",
        lambda value, **_k: prereg if value == "prereg.json" else corpus,
    )
    monkeypatch.setattr(
        prefix.trend_arm.legacy,
        "_canonical_ephemeris_authority",
        lambda *_a, **_k: (
            SimpleNamespace(),
            SimpleNamespace(),
            {"tle_file_set_sha256": "a" * 64, "tle_file_count": 3},
        ),
    )
    trainer = SimpleNamespace()
    monkeypatch.setattr(prefix.trend_arm.legacy, "_short_config", lambda *_a, **_k: trainer)
    monkeypatch.setattr(
        prefix.trend_arm.c2_runner,
        "C2EpisodeLoopConfig",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    observed = {}

    def fake_run(**kwargs):
        observed.update(kwargs)
        checkpoint = kwargs["output_dir"] / "checkpoints" / "ep-000500-main.pt"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_bytes(b"ep500")
        return {
            "episodes": 1500,
            "episodes_completed": 500,
            "checkpoint_every_episodes": 100,
            "artifact_scope": "bounded_initial_segment",
            "periodic_checkpoints": [
                {
                    "episodes_completed": 500,
                    "sha256": prefix.sha256_file(checkpoint),
                }
            ],
        }

    monkeypatch.setattr(prefix.trend_arm.c2_runner, "run_c2_v03_episode_loop", fake_run)
    monkeypatch.setattr(
        prefix.trend_arm.c2_runner,
        "_canonical_trainer_config",
        lambda *_a, **_k: {"episodes": 1500},
    )
    monkeypatch.setattr(
        prefix.trend_arm.legacy,
        "read_checkpoint",
        lambda *_a, **_k: SimpleNamespace(),
    )
    monkeypatch.setattr(
        prefix.checkpoint_tools,
        "validate_checkpoint_payload",
        lambda *_a, **_k: {"finite_state": "PASS"},
    )

    status = prefix.execute_prefix(
        authority_path=authority,
        expected_authority_sha256=prefix.sha256_file(authority),
        expected_runner_sha256=prefix.sha256_file(Path(prefix.__file__)),
        arm="A011",
        output_dir=output,
        tle_root=tmp_path,
    )
    assert observed["stop_episode"] == 500
    assert observed["config"].episodes == 1500
    assert status["source_schedule_episodes"] == 1500
    assert status["prefix_episodes_completed"] == 500
    assert status["checkpoint_identity"] == {"finite_state": "PASS"}
    written = json.loads((output / "prefix-status.json").read_text(encoding="utf-8"))
    assert written["status"] == "complete"


def test_prefix_rejects_runner_or_authority_drift(tmp_path):
    authority = tmp_path / "authority.json"
    authority.write_text("{}\n", encoding="utf-8")
    with pytest.raises(prefix.Fast500PrefixError, match="runner SHA drifted"):
        prefix.execute_prefix(
            authority_path=authority,
            expected_authority_sha256=prefix.sha256_file(authority),
            expected_runner_sha256="0" * 64,
            arm="A011",
            output_dir=tmp_path / "output",
            tle_root=tmp_path,
        )


def test_matrix_completes_exact_two_lr_five_arm_grid(monkeypatch, tmp_path):
    authorities = {}
    authority_shas = {}
    source_roots = {}
    for lr, directory in matrix.LR_DIRS.items():
        authority = tmp_path / f"authority-{directory}.json"
        authority.write_text("{}\n", encoding="utf-8")
        authorities[lr] = authority
        authority_shas[lr] = prefix.sha256_file(authority)
        source_root = tmp_path / f"source-{directory}"
        for arm in ("B000", "F111"):
            checkpoint = source_root / "arms" / arm / "checkpoints" / "ep-000500-main.pt"
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_bytes(f"{lr}:{arm}".encode("ascii"))
        source_roots[lr] = source_root

    def fake_inputs(*, authority_path, tle_root):
        lr = "0.001" if "lr0p001" in authority_path.name else "0.01"
        validated = _validated()
        validated.update(
            {
                "learning_rate": float(lr),
                "evaluation_users": [60, 100],
                "evaluation_seeds": [11, 12],
            }
        )
        return validated, SimpleNamespace(), SimpleNamespace(), tmp_path / "corpus.json"

    monkeypatch.setattr(prefix, "_canonical_inputs", fake_inputs)
    monkeypatch.setattr(matrix, "_validate_snapshot", lambda **_kwargs: {"finite_state": "PASS"})
    monkeypatch.setattr(matrix.time, "sleep", lambda _seconds: None)

    launched = []

    class FakeProcess:
        next_pid = 1000

        def __init__(self, command, **_kwargs):
            self.command = list(command)
            self.pid = FakeProcess.next_pid
            FakeProcess.next_pid += 1
            launched.append(self.command)
            output = Path(self.command[self.command.index("--output-dir") + 1])
            output.mkdir(parents=True, exist_ok=False)
            if Path(self.command[1]).name == matrix.RUNNER.name:
                checkpoint = output / "checkpoints" / "ep-000500-main.pt"
                checkpoint.parent.mkdir()
                checkpoint.write_bytes(b"new-prefix")
                (output / "prefix-status.json").write_text(
                    '{"status":"complete"}\n', encoding="utf-8"
                )
            else:
                (output / "sweep-summary.json").write_text(
                    '{"schema":"fake"}\n', encoding="utf-8"
                )

        def poll(self):
            return 0

        def wait(self):
            return 0

    monkeypatch.setattr(matrix.subprocess, "Popen", FakeProcess)
    output_root = tmp_path / "fast500"
    result = matrix.execute_matrix(
        authorities=authorities,
        authority_shas=authority_shas,
        source_roots=source_roots,
        output_root=output_root,
        tle_root=tmp_path,
        expected_runner_sha256=prefix.sha256_file(matrix.RUNNER),
        max_parallel=2,
    )
    assert result["status"] == "complete"
    assert len(result["runs"]) == 6
    assert len(result["snapshots"]) == 10
    assert set(result["evaluations"]) == {"0.001", "0.01"}
    assert len(launched) == 8
    assert json.loads((output_root / "matrix-status.json").read_text())["status"] == "complete"
