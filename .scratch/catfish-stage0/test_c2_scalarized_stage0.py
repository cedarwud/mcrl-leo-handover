"""Unit and closure tests for the scalarized-Main C2 Stage-0 candidate."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("run_c2_scalarized_stage0.py")
module_spec = importlib.util.spec_from_file_location("c2_scalarized_stage0", MODULE_PATH)
assert module_spec is not None and module_spec.loader is not None
c2 = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(c2)


def test_main_policy_is_scalarized_and_not_q1_only() -> None:
    seen: list[tuple[float, ...]] = []

    class FakeTrainer:
        config = SimpleNamespace(objective_weights=(0.5, 0.3, 0.2))

        def encode_states(self, states):
            return np.zeros((len(states), 4), dtype=np.float32)

        def scalarized_q_values(self, encoded, *, objective_weights):
            del encoded
            seen.append(tuple(objective_weights))
            # The expected scalarized surface is deliberately different from
            # a Q1-only ranking: Q1 alone prefers action 0, while the frozen
            # three-head composition prefers action 1.
            return np.asarray([[1.0, 2.0], [3.0, 0.0]], dtype=np.float64)

    masks = [
        SimpleNamespace(mask=np.asarray([True, True])),
        SimpleNamespace(mask=np.asarray([True, False])),
    ]
    actions = c2._scalarized_main_actions(FakeTrainer(), [object(), object()], masks)
    assert actions.tolist() == [1, 0]
    assert seen == [c2.OBJECTIVE_WEIGHTS]


def test_main_policy_rejects_weight_drift_before_inference() -> None:
    class FakeTrainer:
        config = SimpleNamespace(objective_weights=(1.0, 0.0, 0.0))

        def encode_states(self, states):
            return np.zeros((len(states), 4), dtype=np.float32)

    with pytest.raises(RuntimeError, match="objective weights drifted"):
        c2._scalarized_main_actions(
            FakeTrainer(), [object()], [SimpleNamespace(mask=np.asarray([True]))]
        )


def test_policy_seam_is_restored_after_delegated_run(monkeypatch: pytest.MonkeyPatch) -> None:
    original = c2.legacy._main_actions
    observed = []

    def fake_run_seed(archive, trainer, *, seed):
        del archive, trainer
        observed.append(c2.legacy._main_actions is c2._scalarized_main_actions)
        return {"evaluation_seed": seed, "anchors": []}

    monkeypatch.setattr(c2.legacy, "_run_seed", fake_run_seed)
    assert c2.run_seed(object(), object(), seed=7)["evaluation_seed"] == 7
    assert observed == [True]
    assert c2.legacy._main_actions is original


def _seed_payload(tmp_path: Path, *, closure_sha: str = "a" * 64) -> dict:
    receipt_path = tmp_path / c2.FREEZE_DISJOINTNESS_FILENAME
    closure_path = tmp_path / c2.FREEZE_CLOSURE_FILENAME
    seed_path = tmp_path / c2.FREEZE_SEED_FILENAME
    closure_path.write_text("{}", encoding="utf-8")
    seed_path.write_text("{}", encoding="utf-8")
    prior = [2026082401, 2026082402, 2026082403]
    selected = [901, 902, 903, 904, 905]
    attempts = [
        {
            "counter": index,
            "candidate": value,
            "accepted": True,
            "known_prior_collision": False,
            "selected_collision": False,
            "repository_matches": [],
        }
        for index, value in enumerate(selected)
    ]
    receipt = {
        "schema": "smc-er-c2-scalarized-stage0-disjointness-v1",
        "status": "PASS",
        "namespace": c2.SEED_NAMESPACE,
        "repository_root": str(c2.REPO),
        "candidate_attempts": attempts,
        "selected_seeds": selected,
        "known_prior_seed_values": prior,
        "all_selected_have_zero_pre_reveal_matches": True,
    }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return {
        "schema": c2.SEED_SCHEMA,
        "closure_manifest_sha256": closure_sha,
        "seed_namespace": c2.SEED_NAMESPACE,
        "seed_count": c2.SEED_COUNT,
        "c2_seeds": [901, 902, 903, 904, 905],
        "prior_seed_values": prior,
        "repository_disjointness_checked_before_reveal": True,
        "disjointness_search_receipt_path": str(receipt_path),
        "disjointness_search_receipt_sha256": c2._sha256(receipt_path),
        "post_reveal_ignored_paths": [
            str(closure_path),
            str(receipt_path),
            str(seed_path),
        ],
        "focal_schedule": {
            "anchor_steps": list(c2.ANCHOR_STEPS),
            "focal_users_per_step": c2.FOCAL_USERS_PER_STEP,
            "permutation_offset": c2.FOCAL_SCHEDULE_OFFSET,
        },
    }


def test_seed_manifest_requires_five_disjoint_closure_bound_seeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(c2, "_repo_matches", lambda seed: ())
    payload = _seed_payload(tmp_path)
    assert c2._validate_seed_manifest(payload, closure_sha256="a" * 64) == (
        901,
        902,
        903,
        904,
        905,
    )

    payload["c2_seeds"][0] = 2026082401
    with pytest.raises(RuntimeError, match="not disjoint"):
        c2._validate_seed_manifest(payload, closure_sha256="a" * 64)


def test_disjointness_receipt_is_recomputed_and_tamper_evident(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(c2, "_repo_matches", lambda seed: ())
    payload = _seed_payload(tmp_path)
    receipt_path = Path(payload["disjointness_search_receipt_path"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    c2._verify_disjointness_receipt(
        receipt,
        seeds=payload["c2_seeds"],
        prior=payload["prior_seed_values"],
        post_reveal_paths=[Path(value) for value in payload["post_reveal_ignored_paths"]],
    )
    receipt["candidate_attempts"][0]["accepted"] = False
    with pytest.raises(RuntimeError, match="acceptance decision"):
        c2._verify_disjointness_receipt(
            receipt,
            seeds=payload["c2_seeds"],
            prior=payload["prior_seed_values"],
            post_reveal_paths=[
                Path(value) for value in payload["post_reveal_ignored_paths"]
            ],
        )


def test_seed_manifest_rejects_post_reveal_path_outside_freeze_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(c2, "_repo_matches", lambda seed: ())
    payload = _seed_payload(tmp_path)
    outside = tmp_path.parent / "post-reveal-outside.json"
    outside.write_text("{}", encoding="utf-8")
    payload["post_reveal_ignored_paths"].append(str(outside))

    with pytest.raises(RuntimeError, match="same freeze output directory"):
        c2._validate_seed_manifest(payload, closure_sha256="a" * 64)


def test_seed_manifest_rejects_extra_same_directory_post_reveal_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(c2, "_repo_matches", lambda seed: ())
    payload = _seed_payload(tmp_path)
    extra = tmp_path / "extra-post-reveal.json"
    extra.write_text("{}", encoding="utf-8")
    payload["post_reveal_ignored_paths"].append(str(extra))

    with pytest.raises(RuntimeError, match="exactly the canonical freeze path set"):
        c2._validate_seed_manifest(payload, closure_sha256="a" * 64)


def test_seed_manifest_rejects_noncanonical_bound_manifest_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(c2, "_repo_matches", lambda seed: ())
    payload = _seed_payload(tmp_path)

    with pytest.raises(RuntimeError, match="canonical freeze path"):
        c2._validate_seed_manifest(
            payload,
            closure_sha256="a" * 64,
            closure_manifest_path=tmp_path / "closure-alias.json",
            seed_manifest_path=tmp_path / c2.FREEZE_SEED_FILENAME,
        )


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("closure_manifest_sha256", "c" * 64, "does not bind"),
        ("seed_namespace", "C2-Q1-ONLY", "namespace"),
        ("seed_count", 4, "exactly five"),
        ("repository_disjointness_checked_before_reveal", False, "attestation"),
        ("focal_schedule", {}, "schedule"),
    ],
)
def test_seed_manifest_rejects_contract_drift(
    field, value, message, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(c2, "_repo_matches", lambda seed: ())
    payload = _seed_payload(tmp_path)
    payload[field] = value
    with pytest.raises(RuntimeError, match=message):
        c2._validate_seed_manifest(payload, closure_sha256="a" * 64)


def _valid_closure_payload() -> dict:
    files = {
        relative: c2._sha256(c2.REPO / relative)
        for relative in c2.required_closure_files()
    }
    return {
        "schema": c2.CLOSURE_SCHEMA,
        "candidate_spec_sha256": c2._sha256(c2.SPEC),
        "runner_sha256": c2._sha256(Path(c2.__file__).resolve()),
        "test_sha256": c2._sha256(c2.V2_TEST),
        "legacy_runner_sha256": c2._sha256(c2.LEGACY_RUNNER),
        "legacy_test_sha256": c2._sha256(c2.LEGACY_TEST),
        "method_sha256": c2._sha256(c2.METHOD),
        "prereg_sha256": c2._sha256(c2.PREREG),
        "checkpoint_sha256": c2._sha256(c2.CHECKPOINT),
        "analysis_code_sha256": c2.legacy._code_sha256(
            c2.legacy._default_code_paths()
        ),
        "runtime": c2._dependency_versions(),
        "attestations": {
            "tests_passed_before_seed_reveal": True,
            "repository_disjointness_checked_before_reveal": True,
        },
        "test_receipts": [
            {
                "command": (
                    f"{sys.executable} -m pytest "
                    ".scratch/catfish-stage0/test_c2_scalarized_stage0.py"
                ),
                "argv": [
                    sys.executable,
                    "-m",
                    "pytest",
                    ".scratch/catfish-stage0/test_c2_scalarized_stage0.py",
                ],
                "cwd": str(c2.REPO),
                "exit_code": 0,
                "stdout": "scalarized tests passed\n",
                "stdout_sha256": c2._sha256_text("scalarized tests passed\n"),
                "stdout_normalized_sha256": c2._sha256_text(
                    "scalarized tests passed\n"
                ),
            },
            {
                "command": (
                    f"{sys.executable} -m pytest "
                    ".scratch/catfish-stage0/test_c2_stage0.py"
                ),
                "argv": [
                    sys.executable,
                    "-m",
                    "pytest",
                    ".scratch/catfish-stage0/test_c2_stage0.py",
                ],
                "cwd": str(c2.REPO),
                "exit_code": 0,
                "stdout": "legacy tests passed\n",
                "stdout_sha256": c2._sha256_text("legacy tests passed\n"),
                "stdout_normalized_sha256": c2._sha256_text("legacy tests passed\n"),
            }
        ],
        "tle_files": c2._frozen_tle_hashes(c2.PREREG),
        "files": files,
    }


def test_closure_manifest_binds_current_scalarized_authority(tmp_path: Path) -> None:
    path = tmp_path / "closure.json"
    path.write_text(json.dumps(_valid_closure_payload()), encoding="utf-8")
    receipt = c2.verify_closure_manifest(path, recompute_tests=False)
    assert receipt["schema"] == c2.CLOSURE_SCHEMA


def test_closure_manifest_rejects_method_or_file_drift(tmp_path: Path) -> None:
    payload = _valid_closure_payload()
    payload["method_sha256"] = "e" * 64
    path = tmp_path / "closure.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="method_sha256"):
        c2.verify_closure_manifest(path, recompute_tests=False)


def test_v2_aggregate_has_scalarized_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        c2.legacy,
        "_aggregate",
        lambda rollouts: {"decision": "C2_STAGE0_PASS_TO_FIXTURES_ONLY", "n": len(rollouts)},
    )
    aggregate = c2._aggregate([{}])
    assert aggregate["decision"] == "C2_SCALARIZED_STAGE0_PASS_TO_FIXTURES_ONLY"
    assert aggregate["policy_mode"] == c2.POLICY_MODE
    assert aggregate["objective_weights"] == list(c2.OBJECTIVE_WEIGHTS)
