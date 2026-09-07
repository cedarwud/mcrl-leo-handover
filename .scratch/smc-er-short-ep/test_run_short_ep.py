from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("run_short_ep", HERE / "run_short_ep.py")
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_arm_matrix_keeps_primary_ablation_set_and_adds_three_singletons():
    assert list(M.ARM_LANES)[:5] == ["B000", "F111", "A011", "A101", "A110"]
    assert list(M.ARM_LANES)[5:] == ["S100", "S010", "S001"]
    assert M.ARM_ACTIVE_SOURCES["A011"] == frozenset({"C2", "C3"})
    assert M.ARM_ACTIVE_SOURCES["S010"] == frozenset({"C2"})
    assert M.ARM_LANES["B000"] is None
    assert M.ARM_LANES["F111"] == (True, True, True)
    assert M.ARM_LANES["A011"] == (False, True, True)
    assert M.ARM_LANES["A101"] == (True, False, True)
    assert M.ARM_LANES["A110"] == (True, True, False)
    assert M.ARM_ACTIVE_SOURCES == {
        "F111": frozenset({"C1", "C2", "C3"}),
        "A011": frozenset({"C2", "C3"}),
        "A101": frozenset({"C1", "C3"}),
        "A110": frozenset({"C1", "C2"}),
        "S100": frozenset({"C1"}),
        "S010": frozenset({"C2"}),
        "S001": frozenset({"C3"}),
    }


def test_missing_gate_manifest_fails_closed():
    ledger, payload = M.load_gate_ledger(None)
    assert payload["status"] == "absent-fail-closed"
    assert not any(ledger.routes(source) for source in ("C1", "C2", "C3"))


def test_route_requires_sealed_pass_evidence(tmp_path):
    path = tmp_path / "gates.json"
    path.write_text(
        json.dumps(
            {
                "schema": M.GATE_SCHEMA,
                "verdicts": {"C1": "route", "C2": "shadow", "C3": "shadow"},
                "evidence": {"C1": {"status": "PASS", "receipt_sha256": "bad"}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="sealed PASS"):
        M.load_gate_ledger(path)


def test_route_receipt_hash_and_content_are_both_verified(tmp_path, monkeypatch):
    receipt = tmp_path / "c1-result.json"
    receipt.write_text(
        json.dumps(
            {
                "schema": M.C1_PRETRANSFER_GATE_RESULT_SCHEMA,
                "source": "C1",
                "status": "PASS",
                "decision": "ROUTE",
                "prerequisites_closed": True,
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "gates.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": M.GATE_SCHEMA,
                "verdicts": {"C1": "route", "C2": "shadow", "C3": "shadow"},
                "evidence": {
                    "C1": {
                        "status": "PASS",
                        "receipt_path": receipt.name,
                        "receipt_sha256": M.sha256_file(receipt),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        M,
        "validate_c1_pretransfer_result",
        lambda path: {
            "result_path": str(path),
            "source": "C1",
            "decision": "ROUTE",
        },
    )
    ledger, _ = M.load_gate_ledger(manifest)
    assert ledger.routes("C1")
    receipt.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="hash-drifted"):
        M.load_gate_ledger(manifest)


def test_hand_authored_minimal_pass_receipt_cannot_authorize_route(tmp_path):
    receipt = tmp_path / "minimal-c1-result.json"
    receipt.write_text(
        json.dumps(
            {
                "schema": M.C1_PRETRANSFER_GATE_RESULT_SCHEMA,
                "source": "C1",
                "status": "PASS",
                "decision": "ROUTE",
                "prerequisites_closed": True,
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "gates.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": M.GATE_SCHEMA,
                "verdicts": {"C1": "route", "C2": "shadow", "C3": "shadow"},
                "evidence": {
                    "C1": {
                        "status": "PASS",
                        "receipt_path": receipt.name,
                        "receipt_sha256": M.sha256_file(receipt),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="independent validation"):
        M.load_gate_ledger(manifest)


def test_c3_route_requires_a_sealed_consumer_receipt(tmp_path):
    path = tmp_path / "gates.json"
    path.write_text(
        json.dumps(
            {
                "schema": M.GATE_SCHEMA,
                "verdicts": {"C1": "shadow", "C2": "shadow", "C3": "route"},
                "evidence": {
                    "C3": {"status": "PASS", "receipt_sha256": digest(b"pass")}
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="receipt path"):
        M.load_gate_ledger(path)


def test_incumbent_keys_fail_closed_for_non_association_sentinels():
    from mcrl.env.action_contract import Association

    environment = SimpleNamespace(
        environment=SimpleNamespace(
            _previous_association=[Association(10, 2), None, object()]
        )
    )
    assert M._incumbent_keys(environment) == ((10, 2), None, None)


def test_single_focal_override_accepts_intervention_and_explicit_defer():
    intervention = M._assert_single_focal_override(
        [0, 1, 2], [0, 0, 2], focal_user=1
    )
    assert intervention["differing_users"] == [1]
    assert intervention["difference_count"] == 1
    assert intervention["nonfocal_identity"] is True
    assert intervention["main_actions_sha256"] != intervention[
        "executed_actions_sha256"
    ]

    defer = M._assert_single_focal_override(
        [0, 1, 2], [0, 1, 2], focal_user=1
    )
    assert defer["differing_users"] == []
    assert defer["difference_count"] == 0
    assert defer["main_actions_sha256"] == defer["executed_actions_sha256"]


def test_single_focal_override_requires_exact_nonfocal_identity():
    with pytest.raises(RuntimeError, match="nonfocal"):
        M._assert_single_focal_override(
            [0, 1, 2], [1, 0, 2], focal_user=1
        )
    with pytest.raises(RuntimeError, match="without focal authority"):
        M._assert_single_focal_override(
            [0, 1, 2], [0, 0, 2], focal_user=None
        )
    with pytest.raises(RuntimeError, match="shape"):
        M._assert_single_focal_override([0, 1], [0], focal_user=0)


def test_cli_freezes_ten_episode_preview_schedule(tmp_path):
    args = M._arguments(
        [
            "--arm",
            "F111",
            "--output-dir",
            str(tmp_path / "out"),
            "--train-seed",
            "1",
            "--env-seed",
            "2",
            "--mobility-seed",
            "3",
            "--c1-exp-corpus-manifest",
            str(tmp_path / "c1.json"),
        ]
    )
    assert args.episodes == 10
    assert args.epsilon_decay_episodes == 8
    assert args.target_update_every == 2
    assert args.checkpoint_every == 100


def test_periodic_main_checkpoint_is_named_hashed_and_reloaded(
    tmp_path, monkeypatch
):
    calls = []

    class FakeTrainer:
        def save_checkpoint(self, path, **kwargs):
            calls.append((Path(path), kwargs))
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"checkpoint")

    monkeypatch.setattr(
        M,
        "read_checkpoint",
        lambda _path, *, map_location: SimpleNamespace(
            episode=99,
            checkpoint_kind="periodic-main-policy-trend",
        ),
    )
    receipt = M._save_periodic_main_checkpoint(
        trainer=FakeTrainer(),
        output_dir=tmp_path,
        episodes_completed=100,
        logs=None,
    )
    assert calls[0][0] == tmp_path / "checkpoints" / "ep-000100-main.pt"
    assert calls[0][1]["include_optimizers"] is True
    assert receipt["episodes_completed"] == 100
    assert receipt["load_round_trip"] == "PASS"
    assert len(receipt["sha256"]) == 64


def test_cli_uses_canonical_long_schedule_for_intermediate_trend(tmp_path):
    args = M._arguments(
        [
            "--arm",
            "F111",
            "--output-dir",
            str(tmp_path / "out"),
            "--episodes",
            "1500",
            "--train-seed",
            "2026082901",
            "--env-seed",
            "2026082902",
            "--mobility-seed",
            "2026082903",
            "--intermediate-trend-authority",
            str(tmp_path / "authority.json"),
            "--c1-exp-corpus-manifest",
            str(tmp_path / "c1.json"),
        ]
    )
    assert args.episodes == 1500
    assert args.epsilon_decay_episodes == 2000
    assert args.target_update_every == 50
    assert args.checkpoint_every == 100


def test_cli_allows_baseline_in_intermediate_matrix_without_c1_corpus(tmp_path):
    args = M._arguments(
        [
            "--arm",
            "B000",
            "--output-dir",
            str(tmp_path / "out"),
            "--episodes",
            "3000",
            "--train-seed",
            "2026082901",
            "--env-seed",
            "2026082902",
            "--mobility-seed",
            "2026082903",
            "--intermediate-trend-authority",
            str(tmp_path / "authority.json"),
        ]
    )
    assert args.intermediate_trend_authority is not None
    assert args.target_update_every == 50
    assert args.checkpoint_every == 100


def test_cli_allows_explicit_development_routing_without_formal_gate(tmp_path):
    args = M._arguments(
        [
            "--arm",
            "S010",
            "--output-dir",
            str(tmp_path / "out"),
            "--train-seed",
            "1",
            "--env-seed",
            "2",
            "--mobility-seed",
            "3",
            "--development-route-all",
            "--c1-exp-corpus-manifest",
            str(tmp_path / "c1.json"),
        ]
    )
    assert args.development_route_all
    assert args.gate_manifest is None


def test_cli_rejects_mixing_development_and_formal_routing(tmp_path):
    with pytest.raises(SystemExit):
        M._arguments(
            [
                "--arm",
                "F111",
                "--output-dir",
                str(tmp_path / "out"),
                "--train-seed",
                "1",
                "--env-seed",
                "2",
                "--mobility-seed",
                "3",
                "--development-route-all",
                "--gate-manifest",
                str(tmp_path / "gates.json"),
                "--c1-exp-corpus-manifest",
                str(tmp_path / "c1.json"),
            ]
        )


def test_cli_rejects_mixing_development_and_intermediate_routing(tmp_path):
    with pytest.raises(SystemExit):
        M._arguments(
            [
                "--arm",
                "F111",
                "--output-dir",
                str(tmp_path / "out"),
                "--train-seed",
                "1",
                "--env-seed",
                "2",
                "--mobility-seed",
                "3",
                "--development-route-all",
                "--intermediate-trend-authority",
                str(tmp_path / "authority.json"),
                "--c1-exp-corpus-manifest",
                str(tmp_path / "c1.json"),
            ]
        )


def test_cli_hard_bounds_development_routing_episode_count(tmp_path):
    with pytest.raises(SystemExit):
        M._arguments(
            [
                "--arm",
                "F111",
                "--output-dir",
                str(tmp_path / "out"),
                "--episodes",
                str(M.DEVELOPMENT_MAX_EPISODES + 1),
                "--train-seed",
                "1",
                "--env-seed",
                "2",
                "--mobility-seed",
                "3",
                "--development-route-all",
                "--c1-exp-corpus-manifest",
                str(tmp_path / "c1.json"),
            ]
        )


def test_cli_does_not_apply_development_bound_to_formally_gated_run(tmp_path):
    args = M._arguments(
        [
            "--arm",
            "F111",
            "--output-dir",
            str(tmp_path / "out"),
            "--episodes",
            "9000",
            "--train-seed",
            "1",
            "--env-seed",
            "2",
            "--mobility-seed",
            "3",
            "--gate-manifest",
            str(tmp_path / "gates.json"),
            "--c1-exp-corpus-manifest",
            str(tmp_path / "c1.json"),
        ]
    )
    assert args.episodes == 9000
    assert not args.development_route_all


def test_short_ep_rejects_noncanonical_prereg_before_loading_tle(tmp_path):
    fake = tmp_path / "prereg.json"
    fake.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="canonical sealed preregistration"):
        M._canonical_ephemeris_authority(fake, tmp_path / "tle")


def _load_zero_dose_parity(name):
    parity_spec = importlib.util.spec_from_file_location(
        name, HERE / "check_zero_dose_parity.py"
    )
    assert parity_spec is not None and parity_spec.loader is not None
    parity = importlib.util.module_from_spec(parity_spec)
    sys.modules[parity_spec.name] = parity
    parity_spec.loader.exec_module(parity)
    return parity


def _write_zero_dose_package(parity, package):
    import numpy as np
    import torch

    baseline = {
        "trainer_config": {
            "training_experiment_id": "B000",
            "method_family": "MODQN-baseline",
            "learning_rate": 0.001,
        },
        "q_networks": [{"w": torch.tensor([1.0])}],
        "replay": {"buffer": [(np.array([1.0]),)]},
    }
    carrier_main = {
        "trainer_config": {
            "training_experiment_id": "F111",
            "method_family": "SMC-ER-developmental",
            "learning_rate": 0.001,
        },
        "q_networks": [{"w": torch.tensor([1.0])}],
        "replay": {"buffer": [(np.array([1.0]),)]},
    }
    baseline_dir = package / "B000"
    carrier_dir = package / "F111-zero-route"
    baseline_dir.mkdir(parents=True)
    carrier_dir.mkdir(parents=True)
    baseline_path = baseline_dir / "training-state.pt"
    carrier_path = carrier_dir / "carrier-state.pt"
    torch.save(baseline, baseline_path)
    torch.save(
        {"schema": "smc-er-carrier-state-v1", "main_training_state": carrier_main},
        carrier_path,
    )
    ephemeris = {
        "prereg_path": str(parity.CANONICAL_PREREG),
        "prereg_sha256": parity.CANONICAL_PREREG_BYTE_SHA256,
        "tle_root_path": "/source-host/tle-root",
        "tle_file_set_sha256": "a" * 64,
        "tle_file_count": 373,
    }

    def write_status(directory, arm, result_key, state_path):
        (directory / "status.json").write_text(
            json.dumps(
                {
                    "schema": parity.RUN_SCHEMA,
                    "status": "complete",
                    "arm": arm,
                    "authority": ephemeris,
                    "source_files_sha256": parity._current_run_source_hashes(),
                    "result": {
                        result_key: str(state_path.resolve()),
                        result_key + "_sha256": parity.sha256_file(state_path),
                    },
                }
            ),
            encoding="utf-8",
        )

    write_status(baseline_dir, "B000", "training_state", baseline_path)
    write_status(carrier_dir, "F111", "carrier_state", carrier_path)
    return baseline_path, carrier_path, ephemeris


def _stub_zero_dose_ephemeris_validation(parity, monkeypatch, tle_root, ephemeris):
    tle_root.mkdir()
    portable = {
        "prereg_path": parity._repo_relative_file(
            Path(parity.CANONICAL_PREREG), label="prereg"
        ),
        "prereg_sha256": parity.CANONICAL_PREREG_BYTE_SHA256,
        "tle_file_set_sha256": ephemeris["tle_file_set_sha256"],
        "tle_file_count": ephemeris["tle_file_count"],
        "tle_root_binding": "runtime_argument",
    }

    def validate(baseline_authority, carrier_authority, *, tle_root):
        assert baseline_authority == carrier_authority == ephemeris
        assert Path(tle_root).resolve() == tle_root_path
        return dict(portable)

    tle_root_path = tle_root.resolve()
    monkeypatch.setattr(parity, "_validated_shared_ephemeris_authority", validate)


def test_zero_dose_comparator_ignores_only_descriptive_metadata():
    parity = _load_zero_dose_parity("check_zero_dose_parity")
    baseline = {
        "trainer_config": {
            "training_experiment_id": "B000",
            "method_family": "MODQN-baseline",
            "learning_rate": 0.001,
        },
        "q_networks": [{"w": __import__("torch").tensor([1.0])}],
        "replay": {"buffer": [(__import__("numpy").array([1.0]),)]},
    }
    carrier = {
        "trainer_config": {
            "training_experiment_id": "F111",
            "method_family": "SMC-ER-developmental",
            "learning_rate": 0.001,
        },
        "q_networks": [{"w": __import__("torch").tensor([1.0])}],
        "replay": {"buffer": [(__import__("numpy").array([1.0]),)]},
    }
    assert parity.compare_states(baseline, carrier)["status"] == "PASS"
    carrier["trainer_config"]["learning_rate"] = 0.003
    result = parity.compare_states(baseline, carrier)
    assert result["status"] == "FAIL"
    assert "learning_rate" in result["first_difference"]


def test_zero_dose_v5_receipt_is_exact_hash_bound_and_relocatable(
    tmp_path, monkeypatch
):
    parity = _load_zero_dose_parity("check_zero_dose_parity_v5")
    original_package = tmp_path / "origin" / "parity-package"
    baseline_path, carrier_path, ephemeris = _write_zero_dose_package(
        parity, original_package
    )
    tle_root = tmp_path / "tle"
    _stub_zero_dose_ephemeris_validation(parity, monkeypatch, tle_root, ephemeris)
    receipt = parity.build_receipt(
        baseline_state_path=baseline_path,
        carrier_state_path=carrier_path,
        tle_root=tle_root,
    )
    authority = receipt["authority"]
    assert receipt["schema"] == "multi-catfish-mcrl-zero-dose-parity-v5"
    assert authority["baseline_state_path"] == "B000/training-state.pt"
    assert authority["baseline_status_path"] == "B000/status.json"
    assert authority["carrier_state_path"] == "F111-zero-route/carrier-state.pt"
    assert authority["carrier_status_path"] == "F111-zero-route/status.json"
    assert authority["parity_checker_path"] == (
        ".scratch/smc-er-short-ep/check_zero_dose_parity.py"
    )
    assert authority["run_short_ep_path"] == (
        ".scratch/smc-er-short-ep/run_short_ep.py"
    )
    assert authority["prereg_path"] == "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
    assert "tle_root_path" not in authority
    assert authority["tle_root_binding"] == "runtime_argument"
    receipt_path = original_package / "zero-dose-parity.json"
    receipt_bytes = json.dumps(receipt, sort_keys=True).encode()
    receipt_path.write_bytes(receipt_bytes)

    assert parity.validate_receipt(receipt_path, tle_root=tle_root)["status"] == "PASS"

    relocated_package = tmp_path / "relocated-package"
    original_package.rename(relocated_package)
    receipt_path = relocated_package / "zero-dose-parity.json"
    assert receipt_path.read_bytes() == receipt_bytes
    assert parity.validate_receipt(receipt_path, tle_root=tle_root)["status"] == "PASS"

    for bad_binding in (None, "receipt_path"):
        tampered = json.loads(receipt_bytes)
        if bad_binding is None:
            tampered["authority"].pop("tle_root_binding")
        else:
            tampered["authority"]["tle_root_binding"] = bad_binding
        receipt_path.write_text(json.dumps(tampered), encoding="utf-8")
        with pytest.raises(RuntimeError, match="TLE root binding is noncanonical"):
            parity.validate_receipt(receipt_path, tle_root=tle_root)

    tampered = json.loads(receipt_bytes)
    tampered["authority"]["tle_root_path"] = "/source-host/tle"
    receipt_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(RuntimeError, match="must not store a physical TLE root"):
        parity.validate_receipt(receipt_path, tle_root=tle_root)

    receipt["authority"]["run_short_ep_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(RuntimeError, match="run_short_ep hash mismatch"):
        parity.validate_receipt(receipt_path, tle_root=tle_root)


@pytest.mark.parametrize(
    ("field", "bad_path"),
    [
        ("baseline_state_path", "/tmp/training-state.pt"),
        ("baseline_state_path", "../B000/training-state.pt"),
        ("baseline_state_path", "B000/other-state.pt"),
        ("parity_checker_path", "/tmp/check_zero_dose_parity.py"),
        ("run_short_ep_path", "../run_short_ep.py"),
        ("prereg_path", "~/prereg.json"),
        ("prereg_path", ""),
        ("prereg_path", "."),
    ],
)
def test_zero_dose_v5_rejects_noncanonical_receipt_paths(
    tmp_path, monkeypatch, field, bad_path
):
    parity = _load_zero_dose_parity(f"check_zero_dose_parity_v5_{field}_{len(bad_path)}")
    package = tmp_path / "package"
    baseline_path, carrier_path, ephemeris = _write_zero_dose_package(parity, package)
    tle_root = tmp_path / "tle"
    _stub_zero_dose_ephemeris_validation(parity, monkeypatch, tle_root, ephemeris)
    receipt = parity.build_receipt(
        baseline_state_path=baseline_path,
        carrier_state_path=carrier_path,
        tle_root=tle_root,
    )
    receipt["authority"][field] = bad_path
    receipt_path = package / "zero-dose-parity.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(RuntimeError, match="strict relative POSIX|noncanonical"):
        parity.validate_receipt(receipt_path, tle_root=tle_root)


def test_zero_dose_v5_rejects_package_symlink_escape(tmp_path, monkeypatch):
    parity = _load_zero_dose_parity("check_zero_dose_parity_v5_package_symlink")
    package = tmp_path / "package"
    baseline_path, carrier_path, ephemeris = _write_zero_dose_package(parity, package)
    tle_root = tmp_path / "tle"
    _stub_zero_dose_ephemeris_validation(parity, monkeypatch, tle_root, ephemeris)
    receipt = parity.build_receipt(
        baseline_state_path=baseline_path,
        carrier_state_path=carrier_path,
        tle_root=tle_root,
    )
    receipt_path = package / "zero-dose-parity.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    outside_state = tmp_path / "outside-training-state.pt"
    baseline_path.replace(outside_state)
    baseline_path.symlink_to(outside_state)

    with pytest.raises(RuntimeError, match="escapes its trusted root"):
        parity.validate_receipt(receipt_path, tle_root=tle_root)


def test_zero_dose_v5_rejects_repo_symlink_escape(tmp_path, monkeypatch):
    parity = _load_zero_dose_parity("check_zero_dose_parity_v5_repo_symlink")
    repo = tmp_path / "repo"
    inside = repo / "inside"
    inside.mkdir(parents=True)
    outside = tmp_path / "outside.py"
    outside.write_text("external", encoding="utf-8")
    (inside / "checker.py").symlink_to(outside)
    monkeypatch.setattr(parity, "REPO", repo)

    with pytest.raises(RuntimeError, match="escapes its trusted root"):
        parity._resolve_repo_file("inside/checker.py", label="parity_checker")


def test_zero_dose_v5_recomputes_tle_binding_from_caller_root(tmp_path, monkeypatch):
    parity = _load_zero_dose_parity("check_zero_dose_parity_v5_tle_root")
    tle_root = tmp_path / "tle"
    tle_root.mkdir()
    captured = {}

    class Record:
        def verify(self):
            captured["record_verified"] = True

    def archive(path):
        captured["tle_root"] = path
        return object()

    def reproduce(record, *, archive):
        captured["archive"] = archive
        return {
            "file_set_sha256": "a" * 64,
            "archive": {"file_count": 373},
        }

    monkeypatch.setattr(parity, "TleArchive", archive)
    monkeypatch.setattr(parity, "read_prereg", lambda _path: Record())
    monkeypatch.setattr(parity, "assert_ephemeris_matches_record", reproduce)
    authority = {
        "prereg_path": "/source-host/prereg.json",
        "prereg_sha256": parity.CANONICAL_PREREG_BYTE_SHA256,
        "tle_root_path": "/source-host/tle",
        "tle_file_set_sha256": "a" * 64,
        "tle_file_count": 373,
    }
    result = parity._validated_shared_ephemeris_authority(
        authority, dict(authority), tle_root=tle_root
    )

    assert captured["tle_root"] == tle_root.resolve()
    assert captured["record_verified"] is True
    assert result["prereg_path"] == "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
    assert "tle_root_path" not in result
    assert result["tle_root_binding"] == "runtime_argument"


def test_zero_dose_v5_rejects_missing_status(tmp_path):
    import torch

    parity = _load_zero_dose_parity("check_zero_dose_parity_v5_missing")
    baseline_path = tmp_path / "package" / "B000" / "training-state.pt"
    carrier_path = tmp_path / "package" / "F111-zero-route" / "carrier-state.pt"
    baseline_path.parent.mkdir(parents=True)
    carrier_path.parent.mkdir(parents=True)
    torch.save({}, baseline_path)
    torch.save({}, carrier_path)
    with pytest.raises(RuntimeError, match="baseline_status is missing"):
        parity.build_receipt(
            baseline_state_path=baseline_path,
            carrier_state_path=carrier_path,
            tle_root=tmp_path / "tle",
        )


def test_zero_dose_v5_rejects_different_tle_authorities():
    baseline = {
        "prereg_path": "same",
        "prereg_sha256": "a" * 64,
        "tle_root_path": "same",
        "tle_file_set_sha256": "b" * 64,
        "tle_file_count": 373,
    }
    carrier = dict(baseline, tle_file_set_sha256="c" * 64)
    parity = _load_zero_dose_parity("check_zero_dose_parity_v5_tle")
    with pytest.raises(RuntimeError, match="do not share one ephemeris authority"):
        parity._validated_shared_ephemeris_authority(
            baseline, carrier, tle_root=Path("unused")
        )


def test_collection_block_comparator_is_detached_from_live_main_updates():
    import numpy as np
    import torch

    from mcrl.runtime.q_network import DQNNetwork

    class Main:
        def __init__(self):
            self.config = type("Config", (), {"objective_weights": (0.5, 0.3, 0.2)})()
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(73)
                self.q_nets = torch.nn.ModuleList(
                    [DQNNetwork(4, 2, (4,), "relu") for _ in range(3)]
                )

    main = Main()
    frozen = M.FrozenMainComparator.from_main(main)
    states = np.arange(12, dtype=np.float32).reshape(3, 4)
    before = frozen.scalarized_q_values(states)
    with torch.no_grad():
        for parameter in main.q_nets[0].parameters():
            parameter.add_(100.0)
    after = frozen.scalarized_q_values(states)

    assert np.array_equal(before, after)
    assert M.FrozenMainComparator.from_main(main).version_sha256 != frozen.version_sha256


def test_preview_matrix_builds_identical_short_schedule_for_each_arm(tmp_path):
    matrix_spec = importlib.util.spec_from_file_location(
        "run_preview_matrix", HERE / "run_preview_matrix.py"
    )
    assert matrix_spec is not None and matrix_spec.loader is not None
    matrix = importlib.util.module_from_spec(matrix_spec)
    sys.modules[matrix_spec.name] = matrix
    matrix_spec.loader.exec_module(matrix)
    command = matrix._runner_command(
        arm="A101",
        output=tmp_path / "A101",
        episodes=10,
        train_seed=11,
        env_seed=12,
        mobility_seed=13,
        gate_manifest=tmp_path / "gates.json",
        c1_exp_corpus_manifest=tmp_path / "c1.json",
        prereg=tmp_path / "prereg.json",
        tle_root=tmp_path / "tle",
    )
    assert command[command.index("--epsilon-decay-episodes") + 1] == "8"
    assert command[command.index("--target-update-every") + 1] == "2"
    assert command[command.index("--gate-manifest") + 1].endswith("gates.json")
    assert command[command.index("--c1-exp-corpus-manifest") + 1].endswith(
        "c1.json"
    )
    assert command[command.index("--prereg") + 1].endswith("prereg.json")
    assert command[command.index("--tle-root") + 1].endswith("tle")
