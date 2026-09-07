"""Focused positive and mutation-negative tests for the formal launch bundle."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNNER_DIR = REPO / ".scratch/multi-catfish-v023-two-route-source-training-runner"
FACTORY_DIR = REPO / ".scratch/multi-catfish-v023-c1c2-provider-factory-v3"
for path in (HERE, REPO / "src", RUNNER_DIR, FACTORY_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_v023_c1c2_successor_one_epoch_diagnostic as DIAGNOSTIC
import bind_v023_c1c2_successor_freeze as BINDER
import build_v023_c1c2_successor_launch_manifest as MANIFEST
import preflight_v023_c1c2_successor as PREFLIGHT
import run_v023_c1c2_successor_formal as FORMAL
import successor_launch_common as COMMON
import test_v023_c1c2_provider_factory_v3 as PRODUCER_FIXTURE
import v023_c1c2_provider_factory_v3 as FACTORY
import verify_v023_c1c2_successor as VERIFY


def test_stage_a_placeholder_left_unresolved_makes_binding_fail():
    declarations = "\n".join(
        f"<<BIND_AT_FREEZE:{key}>>" for key in sorted(COMMON.STAGE_A_PLACEHOLDERS)
    ) + "\n## 2. next\n"
    resolved = {key: "bound" for key in COMMON.STAGE_A_PLACEHOLDERS}
    resolved.pop("runner_manifest_sha256")
    with pytest.raises(COMMON.SuccessorLaunchError, match="unresolved"):
        COMMON.assert_stage_a_placeholders(declarations, resolved)


def test_forbidden_predecessor_token_in_provider_config_is_rejected():
    payload = {
        "schema": COMMON.PROVIDER_CONFIG_SCHEMA,
        "target_root": "/home/sat/clean-" + "r" + "7",
    }
    with pytest.raises(COMMON.SuccessorLaunchError, match="forbidden"):
        COMMON.reject_forbidden_config(payload)


def test_digest_with_c3_is_validated_but_not_semantically_scanned():
    COMMON.reject_forbidden_config(
        {"contract_sha256": "c3" + "a" * 62, "target_root": "/srv/successor"}
    )
    with pytest.raises(COMMON.SuccessorLaunchError, match="SHA-256"):
        COMMON.reject_forbidden_config(
            {"contract_sha256": "g" * 64, "target_root": "/srv/successor"}
        )


def test_contract_deferrals_are_a_closed_stage_a_output_only_set():
    contract = (
        REPO / COMMON.SUCCESSOR_REL / COMMON.CONTRACT_NAME
    ).read_text(encoding="utf-8")
    names = set(COMMON.CONTRACT_PLACEHOLDER_RE.findall(contract))
    bindings = {
        name: {"status": "RESOLVED", "value": "a" * 64}
        for name in names
    }
    bindings["evaluation_runner_manifest_sha256"] = {
        "status": "DEFERRED",
        "reason": "DEFERRED_UNTIL_STAGEC_BUNDLE_LANDS",
    }
    with pytest.raises(COMMON.SuccessorLaunchError, match="evaluation_runner"):
        COMMON.assert_contract_placeholders(contract, bindings)
    bindings["evaluation_runner_manifest_sha256"] = {
        "status": "RESOLVED",
        "value": "b" * 64,
    }
    COMMON.assert_contract_placeholders(contract, bindings)
    bindings.pop("baseline_checkpoint_sha256")
    with pytest.raises(COMMON.SuccessorLaunchError, match="baseline_checkpoint"):
        COMMON.assert_contract_placeholders(contract, bindings)
    COMMON.assert_contract_placeholders(
        "<<BIND_AT_FREEZE:stage_a_manifest_sha256>>",
        {
            "stage_a_manifest_sha256": {
                "status": "DEFERRED",
                "reason": "filled from the sealed Stage-A output",
            }
        },
    )


def test_launch_manifest_is_exact_closure_union_enumerated_bundle_additions():
    rows = (
        REPO / COMMON.CLOSURE_LIST_REL
    ).read_text(encoding="utf-8").splitlines()
    assert rows == sorted(rows)
    assert [Path(row) for row in rows] != sorted(Path(row) for row in rows)
    groups = MANIFEST.closure_groups(REPO)
    observed = [
        Path(item["path"])
        for group in groups
        for item in group["files"]
    ]
    required = COMMON.required_sync_closure(REPO)
    assert len(required) == 246
    assert set(required) == {Path(row) for row in rows}
    additions = set(COMMON.launch_manifest_additions(REPO))
    assert set(observed) == set(required) | additions
    assert len(observed) == len(set(observed))


def test_binder_write_then_check_is_idempotent_on_clean_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    repo = tmp_path / "repo"
    bundle = repo / COMMON.BUNDLE_REL
    bundle.mkdir(parents=True)
    (repo / "tracked.txt").write_text("tracked\n", encoding="ascii")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=Binder Test", "-c",
            "user.email=binder@example.invalid", "commit", "-qm", "initial",
        ],
        cwd=repo,
        check=True,
    )

    def payloads(root: Path, _target_root: Path):
        return (
            {"schema": "learner"},
            {"schema": "provider"},
            {"schema": "bindings", "git": BINDER._git_identity(root)},
        )

    monkeypatch.setattr(BINDER, "build_payloads", payloads)
    arguments = ["--repo", str(repo), "--target-root", str(tmp_path / "target")]
    assert BINDER.main([*arguments, "--write"]) == 0
    assert BINDER.main([*arguments, "--check"]) == 0


def test_no_reconstruction_can_never_return_pass(tmp_path: Path):
    result = VERIFY.decision_for_output(
        repo=REPO,
        output_root=tmp_path / "invented-formal-root",
        provider_config_path=tmp_path / "invented-provider.json",
        model_config_path=tmp_path / "invented-model.json",
        preflight_receipt_path=tmp_path / "invented-preflight.json",
        reconstruct=False,
    )
    assert result["status"] == VERIFY.STOP
    assert "reconstruction" in result["error"]


def test_diagnostic_pass_without_complete_positive_evidence_is_rejected(
    tmp_path: Path,
):
    path = tmp_path / "diagnostic.json"
    DIAGNOSTIC._write_receipt(
        tmp_path,
        {
            "schema": PREFLIGHT.DIAGNOSTIC_SCHEMA,
            "status": PREFLIGHT.DIAGNOSTIC_STATUS,
            "formal": False,
            "failed_checks": [],
        },
    )
    generated = tmp_path / DIAGNOSTIC.RECEIPT_NAME
    with pytest.raises(COMMON.SuccessorLaunchError, match="behavioural evidence"):
        PREFLIGHT.verify_diagnostic_receipt(generated)


def test_circular_digest_attempt_is_rejected():
    mutation = {"authority": {"launch_manifest_sha256": "a" * 64}}
    with pytest.raises(COMMON.SuccessorLaunchError, match="circular"):
        COMMON.validate_no_circular_digest(mutation)


def test_diagnostic_failure_receipt_makes_launcher_refuse(tmp_path: Path):
    root = tmp_path / "diagnostic"
    root.mkdir()
    DIAGNOSTIC._write_receipt(
        root,
        {
            "schema": DIAGNOSTIC.SCHEMA,
            "status": DIAGNOSTIC.STATUS_FAIL,
            "formal": False,
            "failed_checks": ["mutation-negative"],
        },
    )
    result = subprocess.run(
        [
            "bash", str(HERE / "sync_launch_v023_c1c2_successor_server.sh"),
            "--check-diagnostic-receipt", str(root / DIAGNOSTIC.RECEIPT_NAME),
        ],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 2
    assert "LAUNCH_REFUSED" in result.stderr


@pytest.mark.parametrize(
    ("formal", "target_root", "expected"),
    [
        (False, Path("/tmp/rehearsal-target"), 0),
        (True, Path("/tmp/rehearsal-target"), 3),
        (True, COMMON.TARGET_ROOT, 0),
    ],
)
def test_preflight_target_root_mode(
    formal: bool, target_root: Path, expected: int,
    monkeypatch: pytest.MonkeyPatch,
):
    observed: dict[str, object] = {}

    def fake_run_preflight(**kwargs: object) -> dict[str, object]:
        observed.update(kwargs)
        PREFLIGHT._verify_target_root(
            bindings={"target": {"root": str(kwargs["target_root"])}},
            provider_config={"target_root": str(kwargs["target_root"])},
            target_root=kwargs["target_root"],
            formal=kwargs["formal"],
        )
        return {
            "input_sha256": "a" * 64,
            "input_binding": {"provider_identity": "test-provider"},
        }

    monkeypatch.setattr(PREFLIGHT, "run_preflight", fake_run_preflight)
    argv = [
        "--bindings", "bindings.json", "--manifest", "manifest.json",
        "--provider-config", "provider.json", "--model-config", "model.json",
        "--declaration", "declaration.md", "--output-root", "output",
        "--target-root", str(target_root),
    ]
    if formal:
        argv.append("--formal")
    assert PREFLIGHT.main(argv) == expected
    if expected == 0:
        assert observed["target_root"] == target_root
        assert observed["formal"] is formal


@pytest.mark.parametrize(
    ("contents", "reason"),
    [
        (None, "preflight receipt is missing or symlinked"),
        (b"not-json\n", "preflight receipt is not canonical ASCII JSON"),
    ],
)
def test_formal_wrapper_reports_preflight_receipt_faults(
    tmp_path: Path, contents: bytes | None, reason: str,
):
    receipt = tmp_path / "preflight.json"
    if contents is not None:
        receipt.write_bytes(contents)
    result = subprocess.run(
        [
            str(REPO / ".venv/bin/python"), str(HERE / FORMAL.__file__),
            "--output-root", str(tmp_path / "output"), "--epochs", "100",
            "--provider-factory", "unused:factory", "--model-config-json", "unused.json",
            "--train-seed", str(COMMON.TRAIN_SEED),
            "--preflight-receipt", str(receipt), "--execute",
        ],
        cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 3
    assert f"SUCCESSOR_FORMAL_RUN_FAIL: {reason}" in result.stderr


@pytest.fixture(scope="module")
def producer_output(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, Path]:
    """Create the fixture through the real two-route runner/writer."""

    root = tmp_path_factory.mktemp("producer-output")
    target = PRODUCER_FIXTURE._write_artifact(root / "targets")
    learner_manifest = PRODUCER_FIXTURE._write_learner_manifest(
        root / "learner-manifest.json"
    )
    provider_config = root / "provider-config.json"
    provider_payload = PRODUCER_FIXTURE._config_payload(target, learner_manifest)
    provider_config.write_bytes(PRODUCER_FIXTURE._canonical(provider_payload))
    provider_config_sha = COMMON.file_sha256(provider_config)
    COMMON.sidecar_path(provider_config).write_text(
        f"{provider_config_sha}  {provider_config.name}\n", encoding="ascii"
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(FACTORY.CONFIG_PATH_ENV, str(provider_config))
        patch.setenv(FACTORY.CONFIG_SHA256_ENV, provider_config_sha)
        patch.setenv(FACTORY.LEARNER_MANIFEST_PATH_ENV, str(learner_manifest))
        provider = FACTORY.make_provider()
    identity = provider.provider_identity
    identity_payload = dict(provider.provider_identity_payload)
    stage_c_code = COMMON.verify_stage_c_code_bundle(REPO)
    contract = (
        REPO / COMMON.SUCCESSOR_REL / COMMON.CONTRACT_NAME
    ).read_text(encoding="utf-8")
    placeholder_names = set(COMMON.CONTRACT_PLACEHOLDER_RE.findall(contract))
    placeholder_bindings = {
        name: {"status": "RESOLVED", "value": "a" * 64}
        for name in placeholder_names
    }
    placeholder_bindings["evaluation_runner_manifest_sha256"] = {
        "status": "RESOLVED",
        "value": stage_c_code[
            "physical_evaluation_package_manifest_sha256"
        ],
    }
    execution_bindings = root / "execution-bindings.json"
    execution_bindings.write_bytes(
        COMMON.canonical_bytes(
            {
                "schema": COMMON.EXECUTION_BINDINGS_SCHEMA,
                "status": "FROZEN_STAGE_A",
                "contract_placeholder_bindings": placeholder_bindings,
                "stage_c": {
                    "physical_evaluation_package_manifest_sha256": stage_c_code[
                        "physical_evaluation_package_manifest_sha256"
                    ],
                    "runner_bundle_manifest_sha256": stage_c_code[
                        "stage_c_bundle_manifest_sha256"
                    ],
                    "verifier_bundle_manifest_sha256": stage_c_code[
                        "stage_c_bundle_manifest_sha256"
                    ],
                    "code_bundle": stage_c_code,
                },
            }
        )
    )
    execution_bindings_sha = COMMON.file_sha256(execution_bindings)
    COMMON.sidecar_path(execution_bindings).write_text(
        f"{execution_bindings_sha}  {execution_bindings.name}\n",
        encoding="ascii",
    )
    launch_manifest = root / "launch-manifest.json"
    launch_manifest.write_bytes(MANIFEST.render(REPO))
    launch_manifest_sha = COMMON.file_sha256(launch_manifest)
    COMMON.sidecar_path(launch_manifest).write_text(
        f"{launch_manifest_sha}  {launch_manifest.name}\n", encoding="ascii"
    )
    output = root / "formal-output"
    preflight = root / "preflight.json"
    preflight.write_bytes(
        COMMON.canonical_bytes(
            {
                "schema": "multi-catfish-mcrl-v023-c1c2-successor-preflight-v1",
                "status": "PASS_FROZEN_C1C2_SUCCESSOR_PREFLIGHT",
                "formal": True,
                "output_root": str(output.resolve(strict=False)),
                "requested_output_root": str(output.resolve(strict=False)),
                "launch_manifest_path": str(launch_manifest.resolve()),
                "launch_manifest_sha256": launch_manifest_sha,
                "execution_bindings_path": str(execution_bindings.resolve()),
                "execution_bindings_sha256": execution_bindings_sha,
                "authority_sha256": provider_payload["contract_sha256"],
                "code_sha256": provider_payload["learner_manifest_sha256"],
                "input_sha256": provider_payload["target_manifest_sha256"],
                "input_binding": {
                    "provider_identity": identity,
                    "provider_identity_payload": identity_payload,
                    "provider_config_sha256": provider_config_sha,
                    "model_config_sha256": provider_payload["model_config_sha256"],
                    "learner_manifest_sha256": provider_payload["learner_manifest_sha256"],
                    "target_manifest_sha256": provider_payload["target_manifest_sha256"],
                    "bindings_sha256": execution_bindings_sha,
                    "launch_manifest_sha256": launch_manifest_sha,
                    "initialization_bytes_sha256": BINDER._initialization_bytes_sha256(
                        REPO,
                        REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME,
                    ),
                },
            }
        )
    )
    preflight_sha = COMMON.file_sha256(preflight)
    COMMON.sidecar_path(preflight).write_text(
        f"{preflight_sha}  {preflight.name}\n", encoding="ascii"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root), str(REPO / "src"), str(RUNNER_DIR), str(FACTORY_DIR), str(HERE)]
    )
    env.update(
        {
            "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
            FACTORY.CONFIG_PATH_ENV: str(provider_config),
            FACTORY.CONFIG_SHA256_ENV: provider_config_sha,
            FACTORY.LEARNER_MANIFEST_PATH_ENV: str(learner_manifest),
        }
    )
    result = subprocess.run(
        [
            str(REPO / ".venv/bin/python"),
            str(HERE / "run_v023_c1c2_successor_formal.py"),
            "--output-root", str(output), "--epochs", "100",
            "--provider-factory", "v023_c1c2_provider_factory_v3:make_provider",
            "--model-config-json", str(REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME),
            "--train-seed", str(COMMON.TRAIN_SEED),
            "--authority-sha256", provider_payload["contract_sha256"],
            "--code-sha256", provider_payload["learner_manifest_sha256"],
            "--input-sha256", provider_payload["target_manifest_sha256"],
            "--preflight-receipt", str(preflight),
            "--execute",
        ],
        cwd=REPO, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=180,
    )
    assert result.returncode == 0, result.stderr
    return output, preflight, provider_config


def test_preflight_rejects_factory_identity_field_set_drift(
    producer_output: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch,
):
    _output, _preflight, provider_config = producer_output
    learner_manifest = provider_config.parent / "learner-manifest.json"
    monkeypatch.setenv(FACTORY.CONFIG_PATH_ENV, str(provider_config))
    monkeypatch.setenv(
        FACTORY.CONFIG_SHA256_ENV, COMMON.file_sha256(provider_config)
    )
    monkeypatch.setenv(FACTORY.LEARNER_MANIFEST_PATH_ENV, str(learner_manifest))
    provider = FACTORY.make_provider()
    identity, payload = PREFLIGHT._provider_identity(provider)
    assert identity == provider.provider_identity
    assert set(payload) == set(FACTORY.PROVIDER_IDENTITY_FIELDS)

    class ExtraIdentityField:
        provider_identity = provider.provider_identity
        provider_identity_payload = {**payload, "unexpected": "field"}

    with pytest.raises(COMMON.SuccessorLaunchError, match="field set"):
        PREFLIGHT._provider_identity(ExtraIdentityField())


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("omit-launch-hash", "fields are missing"),
        ("substitute-bindings-hash", "digest binding drifted"),
        ("substitute-output-root", "output root drifted"),
    ],
)
def test_preflight_freeze_authority_omission_or_substitution_is_rejected(
    producer_output: tuple[Path, Path, Path], mutation: str, message: str,
):
    output, preflight_path, _provider_config = producer_output
    preflight = json.loads(preflight_path.read_text(encoding="ascii"))
    if mutation == "omit-launch-hash":
        preflight.pop("launch_manifest_sha256")
    elif mutation == "substitute-bindings-hash":
        preflight["execution_bindings_sha256"] = "0" * 64
    else:
        preflight["requested_output_root"] = str(output.parent / "substituted")
    with pytest.raises(COMMON.SuccessorLaunchError, match=message):
        COMMON.authenticate_preflight_freeze_authorities(
            repo=REPO,
            preflight=preflight,
            requested_output_root=output,
        )


def test_formal_output_passes_independent_epoch_zero_and_100_reconstruction(
    producer_output: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch,
):
    output, preflight, provider_config = producer_output
    learner_manifest = provider_config.parent / "learner-manifest.json"
    monkeypatch.setattr(VERIFY, "BUNDLE_REL", learner_manifest.parent)
    monkeypatch.setattr(VERIFY, "LEARNER_MANIFEST_NAME", learner_manifest.name)
    result = VERIFY.decision_for_output(
        repo=REPO,
        output_root=output,
        provider_config_path=provider_config,
        model_config_path=REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME,
        preflight_receipt_path=preflight,
        reconstruct=True,
    )
    assert result["status"] == VERIFY.PASS, result
    assert result["exact_epoch_100_resume"] is True


@pytest.fixture(scope="module")
def nonformal_output(
    producer_output: tuple[Path, Path, Path],
) -> tuple[Path, Path, Path]:
    """Traverse the same producer-derived chain with explicit non-formal mode."""

    _formal_output, formal_preflight, provider_config = producer_output
    root = provider_config.parent
    output = root / "chain-REHEARSAL-NONFORMAL"
    preflight = root / "nonformal-preflight.json"
    payload = json.loads(formal_preflight.read_text(encoding="ascii"))
    payload["formal"] = False
    payload["output_root"] = str(output.resolve(strict=False))
    payload["requested_output_root"] = str(output.resolve(strict=False))
    preflight.write_bytes(COMMON.canonical_bytes(payload))
    preflight_sha = COMMON.file_sha256(preflight)
    COMMON.sidecar_path(preflight).write_text(
        f"{preflight_sha}  {preflight.name}\n", encoding="ascii"
    )
    learner_manifest = provider_config.parent / "learner-manifest.json"
    provider_payload = json.loads(provider_config.read_text(encoding="ascii"))
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root), str(REPO / "src"), str(RUNNER_DIR), str(FACTORY_DIR), str(HERE)]
    )
    env.update(
        {
            "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
            FACTORY.CONFIG_PATH_ENV: str(provider_config),
            FACTORY.CONFIG_SHA256_ENV: COMMON.file_sha256(provider_config),
            FACTORY.LEARNER_MANIFEST_PATH_ENV: str(learner_manifest),
        }
    )
    command_tail = [
            "--epochs", "100", "--nonformal",
            "--provider-factory", "v023_c1c2_provider_factory_v3:make_provider",
            "--model-config-json", str(REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME),
            "--train-seed", str(COMMON.TRAIN_SEED),
            "--authority-sha256", provider_payload["contract_sha256"],
            "--code-sha256", provider_payload["learner_manifest_sha256"],
            "--input-sha256", provider_payload["target_manifest_sha256"],
            "--preflight-receipt", str(preflight), "--execute",
    ]
    result = subprocess.run(
        [
            str(REPO / ".venv/bin/python"),
            str(HERE / "run_v023_c1c2_successor_formal.py"),
            "--output-root", str(output), *command_tail,
        ],
        cwd=REPO, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=180,
    )
    assert result.returncode == 0, result.stderr
    assert "SUCCESSOR_NONFORMAL_RUN_COMPLETE" in result.stdout
    resumed = subprocess.run(
        [
            str(REPO / ".venv/bin/python"),
            str(HERE / "run_v023_c1c2_successor_formal.py"),
            "--resume", str(output), *command_tail,
        ],
        cwd=REPO, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=180,
    )
    assert resumed.returncode == 0, resumed.stderr
    return output, preflight, provider_config


def test_wrapper_mode_admission_and_nonformal_receipt_stamping(
    producer_output: tuple[Path, Path, Path],
    nonformal_output: tuple[Path, Path, Path],
):
    formal_output, formal_preflight, _formal_provider = producer_output
    output, preflight, _provider_config = nonformal_output
    common = [
        "--epochs", "100", "--provider-factory", "unused:factory",
        "--model-config-json", "unused.json", "--train-seed", str(COMMON.TRAIN_SEED),
        "--execute",
    ]
    missing_flag = subprocess.run(
        [
            str(REPO / ".venv/bin/python"), str(HERE / FORMAL.__file__),
            "--resume", str(output), "--preflight-receipt", str(preflight), *common,
        ],
        cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    assert missing_flag.returncode == 3
    assert "preflight receipt does not bind the requested formal run" in missing_flag.stderr

    laundering = subprocess.run(
        [
            str(REPO / ".venv/bin/python"), str(HERE / FORMAL.__file__),
            "--resume", str(formal_output), "--preflight-receipt", str(formal_preflight),
            "--nonformal", *common,
        ],
        cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    assert laundering.returncode == 3
    assert "cannot be laundered" in laundering.stderr

    json_receipts = [
        output / "canonical-status.json",
        output / "canonical-receipt.json",
        output / "update-ledger.json",
        output / "nonformal-provenance.json",
        *sorted((output / "checkpoint-receipts").glob("*.json")),
        *sorted((output / "exports").glob("epoch-*.json")),
    ]
    assert len(json_receipts) == 26
    assert all(json.loads(path.read_text(encoding="ascii"))["formal"] is False for path in json_receipts)
    assert not (output / "COMPLETE").exists()
    assert not (output / "MANIFEST.sha256").exists()


def test_nonformal_verifier_reconstructs_without_formal_pass_token(
    nonformal_output: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch,
):
    output, preflight, provider_config = nonformal_output
    learner_manifest = provider_config.parent / "learner-manifest.json"
    monkeypatch.setattr(VERIFY, "BUNDLE_REL", learner_manifest.parent)
    monkeypatch.setattr(VERIFY, "LEARNER_MANIFEST_NAME", learner_manifest.name)
    result = VERIFY.decision_for_output(
        repo=REPO, output_root=output, provider_config_path=provider_config,
        model_config_path=REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME,
        preflight_receipt_path=preflight, reconstruct=True, nonformal=True,
    )
    assert result["status"] == VERIFY.NONFORMAL_PASS, result
    assert result["formal"] is False
    assert VERIFY.PASS not in result["status"]

    formal_attempt = VERIFY.decision_for_output(
        repo=REPO, output_root=output, provider_config_path=provider_config,
        model_config_path=REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME,
        preflight_receipt_path=preflight, reconstruct=True,
    )
    assert formal_attempt["status"] == VERIFY.STOP
    assert "non-formal rehearsal roots" in formal_attempt["error"]


def test_formal_fixture_cannot_pass_nonformal_verifier(
    producer_output: tuple[Path, Path, Path],
):
    output, preflight, provider_config = producer_output
    result = VERIFY.decision_for_output(
        repo=REPO, output_root=output, provider_config_path=provider_config,
        model_config_path=REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME,
        preflight_receipt_path=preflight, reconstruct=True, nonformal=True,
    )
    assert result["status"] == VERIFY.NONFORMAL_FAIL
    assert VERIFY.PASS not in result["status"]


def test_nonformal_verifier_cli_uses_distinct_pass_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
):
    root = tmp_path / "root-REHEARSAL-NONFORMAL"
    root.mkdir()
    monkeypatch.setattr(
        VERIFY,
        "verify_output",
        lambda **_kwargs: {
            "status": VERIFY.NONFORMAL_PASS,
            "exact_epoch_100_resume": True,
        },
    )
    assert VERIFY.main(
        [
            "--repo", str(REPO),
            "--output-root", str(root),
            "--provider-config", str(tmp_path / "provider.json"),
            "--model-config", str(tmp_path / "model.json"),
            "--preflight-receipt", str(tmp_path / "preflight.json"),
            "--nonformal", "--write",
        ]
    ) == 0
    output = capsys.readouterr().out
    assert output.startswith("NONFORMAL_RECONSTRUCTION_PASS ")
    assert "PASS_SOURCE_TRAINING_INTEGRITY" not in output
    assert (root / "nonformal-verification.json").is_file()
    assert not (root / "COMPLETE").exists()
    assert not (root / "MANIFEST.sha256").exists()


def test_fourth_arm_mutation_produces_integrity_stop(
    producer_output: tuple[Path, Path, Path],
):
    output, preflight, provider_config = producer_output
    path = output / "exports/epoch-0100.json"
    manifest = json.loads(path.read_text(encoding="ascii"))
    manifest["arm_order"].append("FOURTH_ARM")
    extra = dict(manifest["exports"][-1])
    extra["arm"] = "FOURTH_ARM"
    manifest["exports"].append(extra)
    path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
        encoding="ascii",
    )
    result = VERIFY.decision_for_output(
        repo=REPO,
        output_root=output,
        provider_config_path=provider_config,
        model_config_path=REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME,
        preflight_receipt_path=preflight,
        reconstruct=True,
    )
    assert result["status"] == VERIFY.STOP
    assert "fourth arm" in result["error"]


def test_binder_records_all_stage_a_and_stage_c_authorities(
    producer_output: tuple[Path, Path, Path],
):
    _output, _preflight, provider_config = producer_output
    target_root = Path(json.loads(provider_config.read_text(encoding="ascii"))["target_root"])
    learner, provider, bindings = BINDER.build_payloads(REPO, target_root)
    assert provider["learner_manifest_sha256"] == hashlib.sha256(
        COMMON.canonical_bytes(learner)
    ).hexdigest()
    assert bindings["learner"]["runtime_file_count"] == len(
        FACTORY.derive_learner_runtime_modules()
    )
    assert bindings["learner"]["initialization_bytes_sha256"]
    assert bindings["baseline"]["status_authentication_sha256"]
    assert bindings["baseline"]["adapter_manifest_sha256"]
    assert bindings["predecessor_authorities"]["prereg_sha256"]
    assert bindings["predecessor_authorities"]["frozen_tle_file_set_sha256"]
    assert bindings["stage_c"]["world_plan_sha256"] == (
        "866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb"
    )
    assert bindings["stage_c"]["physical_evaluation_package_manifest_sha256"]
    stage_c_code = COMMON.verify_stage_c_code_bundle(REPO)
    assert bindings["contract_placeholder_bindings"][
        "evaluation_runner_manifest_sha256"
    ] == {
        "status": "RESOLVED",
        "value": stage_c_code["physical_evaluation_package_manifest_sha256"],
    }
    for name in ("runner_bundle_manifest_sha256", "verifier_bundle_manifest_sha256"):
        assert bindings["stage_c"][name] == stage_c_code[
            "stage_c_bundle_manifest_sha256"
        ]
    assert bindings["stage_c"]["code_bundle"] == stage_c_code
    COMMON.assert_predetermined_stage_c_bound(REPO, bindings)
    assert bindings["execution_policy"]["required_absent_roots"]
    COMMON.assert_contract_placeholders(
        (REPO / COMMON.SUCCESSOR_REL / COMMON.CONTRACT_NAME).read_text(
            encoding="utf-8"
        ),
        bindings["contract_placeholder_bindings"],
    )


def test_launcher_orders_freeze_manifest_sync_diagnostic_and_tmux():
    text = (HERE / "sync_launch_v023_c1c2_successor_server.sh").read_text(encoding="utf-8")
    assert text.index('"${local_bind_cmd[@]}"') < text.index('"${local_manifest_cmd[@]}"')
    assert text.index("rsync_args=(rsync") < text.rindex("--verify-learner-manifest-only")
    assert text.index("preflight_command=") < text.index("diagnostic_command=")
    assert text.index("diagnostic_command=") < text.rindex("tmux new-session")
    assert "OMP_NUM_THREADS=1" in text
    assert "'$remote_preflight' --repo '$checkout'" in text
    assert "--target-root '$target_root' --formal" in text
    assert "120 s" in text
