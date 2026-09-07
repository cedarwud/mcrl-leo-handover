from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "intermediate_trend_authority", HERE / "intermediate_trend_authority.py"
)
assert SPEC is not None and SPEC.loader is not None
AUTH = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUTH
SPEC.loader.exec_module(AUTH)

TEST_TLE_ROOT = Path("/nonexistent-authority-unit-test-tle")


def _validate(request):
    return AUTH.validate_intermediate_trend_authority(
        request,
        tle_root=TEST_TLE_ROOT,
    )


def _current_paths() -> dict[str, Path]:
    repo = AUTH.REPO
    return {
        "repo": repo,
        "freeze": repo / AUTH.FREEZE_RELATIVE,
        "spec": repo / AUTH.SPEC_RELATIVE,
        "prereg": repo / AUTH.CANONICAL_PREREG_RELATIVE,
        "corpus": AUTH.DEFAULT_C1_MANIFEST,
        "runner": repo / AUTH.RUNNER_RELATIVE,
        "checkpoint": repo / "artifacts" / "training-2026-08-25-rerun01" / "main" / "final-checkpoint.pt",
    }


def _support_receipt(tmp_path: Path) -> Path:
    paths = _current_paths()
    payload = {
        "schema": AUTH.SUPPORT_SCHEMA,
        "status": "PASS",
        "support_version": AUTH.SUPPORT_VERSION,
        "partition": "TRAIN",
        "logical_steps": 300,
        "evidence_ceiling": "Pre-outcome support census only: establishes observable role choice exposure, not donor usefulness, reward improvement, EE direction, or Chapter 5 efficacy.",
        "roles": {"C2": {"floor_pass": True}, "C3": {"floor_pass": True}},
        "eligibility_contract": {
            "reward_used": False,
            "successor_outcome_used": False,
            "counterfactual_used": False,
            "forecast_used": False,
            "specialist_outcome_used": False,
        },
        "authority": {
            "path_binding": AUTH.REPOSITORY_PATH_BINDING,
            "freeze_manifest": AUTH.FREEZE_RELATIVE,
            "freeze_manifest_sha256": AUTH.sha256_file(paths["freeze"]),
            "spec": AUTH.SPEC_RELATIVE,
            "spec_sha256": AUTH.sha256_file(paths["spec"]),
            "c1_exp_corpus_manifest": AUTH.C1_MANIFEST_RELATIVE,
            "c1_exp_corpus_manifest_sha256": AUTH.sha256_file(paths["corpus"]),
            "canonical_prereg": AUTH.CANONICAL_PREREG_RELATIVE,
            "canonical_prereg_sha256": AUTH.sha256_file(paths["prereg"]),
            "tle_root_binding": AUTH.RUNTIME_TLE_ROOT_BINDING,
            "tle_file_set_sha256": AUTH.CANONICAL_TLE_FILE_SET_SHA256,
            "tle_file_count": AUTH.CANONICAL_TLE_FILE_COUNT,
            "baseline_checkpoint": paths["checkpoint"].relative_to(paths["repo"]).as_posix(),
            "baseline_checkpoint_sha256": AUTH.sha256_file(paths["checkpoint"]),
            "baseline_checkpoint_detached": True,
            "baseline_checkpoint_updated": False,
        },
    }
    target = tmp_path / "support-census.json"
    target.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return target


def _parity_receipt(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    paths = _current_paths()
    payload: dict[str, object] = {
        "schema": AUTH.ZERO_DOSE_SCHEMA,
        "status": "PASS",
        "exact_after_descriptive_metadata_normalisation": True,
        "first_difference": None,
        "authority": {
            "prereg_path": AUTH.CANONICAL_PREREG_RELATIVE,
            "prereg_sha256": AUTH.CANONICAL_PREREG_SHA256,
            "tle_root_binding": AUTH.RUNTIME_TLE_ROOT_BINDING,
            "tle_file_set_sha256": AUTH.CANONICAL_TLE_FILE_SET_SHA256,
            "tle_file_count": AUTH.CANONICAL_TLE_FILE_COUNT,
            "run_short_ep_path": AUTH.RUNNER_RELATIVE,
            "run_short_ep_sha256": AUTH.sha256_file(paths["runner"]),
        },
    }
    target = tmp_path / "zero-dose-parity.json"
    target.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return target, payload


def _request(tmp_path: Path, *, episodes: int = 1500, learning_rate: float = 0.001) -> dict[str, object]:
    paths = _current_paths()
    parity_path, _ = _parity_receipt(tmp_path)
    return {
        "episodes": episodes,
        "learning_rate": learning_rate,
        "claim_ceiling": AUTH.CLAIM_CEILING,
        "formal_training_authorized": False,
        "arms": list(AUTH.ALLOWED_ARMS),
        "seeds": {
            "training": AUTH.TREND_TRAINING_SEED,
            "environment": AUTH.TREND_ENVIRONMENT_SEED,
            "mobility": AUTH.TREND_MOBILITY_SEED,
        },
        "evaluation_seeds": list(AUTH.TREND_EVALUATION_SEEDS),
        "users": AUTH.TREND_USERS,
        "evaluation_users": list(AUTH.TREND_EVALUATION_USERS),
        "epsilon_decay_episodes": AUTH.TREND_EPSILON_DECAY_EPISODES,
        "target_update_every": AUTH.TREND_TARGET_UPDATE_EVERY,
        "checkpoint_every_episodes": AUTH.TREND_CHECKPOINT_EVERY_EPISODES,
        "specialist_bundle_replay_capacity": AUTH.TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
        "donor_beta": AUTH.TREND_DONOR_BETA,
        "acrm_eta": AUTH.TREND_ACRM_ETA,
        "freeze_manifest": str(paths["freeze"]),
        "support_census_receipt": str(_support_receipt(tmp_path)),
        "zero_dose_parity_receipt": str(parity_path),
        "prereg": str(paths["prereg"]),
        "tle_file_set_sha256": AUTH.CANONICAL_TLE_FILE_SET_SHA256,
        "c1_exp_corpus_manifest": str(paths["corpus"]),
        "selection_plan": {
            "path": AUTH.SELECTION_PLAN_RELATIVE,
            "sha256": AUTH.SELECTION_PLAN_SHA256,
        },
    }


@pytest.fixture
def valid_request(tmp_path, monkeypatch):
    _, parity_payload = _parity_receipt(tmp_path)
    monkeypatch.setattr(
        AUTH,
        "validate_zero_dose_receipt",
        lambda _path, *, tle_root: parity_payload,
    )
    monkeypatch.setattr(
        AUTH,
        "load_verified_c1_corpus",
        lambda *args, **kwargs: object(),
    )
    return _request(tmp_path)


def test_valid_1500_request_returns_bound_five_arm_authority(valid_request):
    result = _validate(valid_request)

    assert result["status"] == "PASS"
    assert result["episodes"] == 1500
    assert result["learning_rate"] == 0.001
    assert result["arms"] == list(AUTH.ALLOWED_ARMS)
    assert result["seeds"]["evaluation_seeds"] == list(AUTH.TREND_EVALUATION_SEEDS)
    assert result["claim_ceiling"] == AUTH.CLAIM_CEILING
    assert result["config"]["epsilon_decay_episodes"] == 2000
    assert result["config"]["target_update_every"] == 50
    assert result["config"]["checkpoint_every_episodes"] == 100
    assert result["config"]["specialist_bundle_replay_capacity"] == 2000
    assert result["authority"]["tle_file_set_sha256"] == AUTH.CANONICAL_TLE_FILE_SET_SHA256


@pytest.mark.parametrize("episodes,learning_rate", [(3000, 0.001), (1500, 0.01), (3000, 0.01)])
def test_second_stage_episode_and_learning_rate_choices_are_allowed(
    valid_request, episodes, learning_rate
):
    valid_request["episodes"] = episodes
    valid_request["learning_rate"] = learning_rate

    result = AUTH.validate_trend_authority(valid_request, tle_root=TEST_TLE_ROOT)

    assert result["status"] == "PASS"
    assert result["episodes"] == episodes
    assert result["learning_rate"] == learning_rate


def test_9000_episode_request_is_rejected_even_with_valid_evidence(valid_request):
    valid_request["episodes"] = 9000

    with pytest.raises(AUTH.IntermediateTrendAuthorityError, match="9000"):
        _validate(valid_request)


def test_claim_ceiling_and_explicit_nonformal_status_are_required(valid_request):
    valid_request.pop("claim_ceiling")
    valid_request.pop("formal_training_authorized")

    with pytest.raises(AUTH.IntermediateTrendAuthorityError) as error:
        _validate(valid_request)

    assert any("claim_ceiling" in item for item in error.value.failures)
    assert any("explicit false" in item for item in error.value.failures)


def test_missing_support_or_parity_evidence_is_fail_closed(valid_request):
    valid_request["support_census_receipt"] = None
    valid_request["zero_dose_parity_receipt"] = None

    with pytest.raises(AUTH.IntermediateTrendAuthorityError) as error:
        _validate(valid_request)

    assert any("support census receipt: path missing" in item for item in error.value.failures)
    assert any("zero-dose parity receipt: path missing" in item for item in error.value.failures)


def test_stale_support_receipt_bound_to_old_freeze_is_rejected(valid_request, tmp_path):
    path = Path(valid_request["support_census_receipt"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["authority"]["freeze_manifest_sha256"] = "0" * 64
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(AUTH.IntermediateTrendAuthorityError, match="current freeze mismatch"):
        _validate(valid_request)


@pytest.mark.parametrize(
    "raw",
    [
        "/tmp/absolute.json",
        "../escape.json",
        "docs/../escape.json",
        "~/escape.json",
        "docs\\windows.json",
    ],
)
def test_support_receipt_paths_reject_ambient_or_traversing_forms(raw, tmp_path):
    failures = []
    assert (
        AUTH._strict_repo_receipt_path(
            raw,
            repo=tmp_path,
            label="support path",
            failures=failures,
        )
        is None
    )
    assert failures


def test_support_receipt_path_rejects_symlink_escape(tmp_path):
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    (outside / "evidence.json").write_text("{}", encoding="utf-8")
    (repo / "linked").symlink_to(outside, target_is_directory=True)
    failures = []
    assert (
        AUTH._strict_repo_receipt_path(
            "linked/evidence.json",
            repo=repo,
            label="support path",
            failures=failures,
        )
        is None
    )
    assert any("escapes checkout" in item for item in failures)


@pytest.mark.parametrize(
    "request_field,old_schema",
    [
        ("support_census_receipt", "multi-catfish-mcrl-v0.2-support-census-v1"),
        ("zero_dose_parity_receipt", "multi-catfish-mcrl-zero-dose-parity-v4"),
    ],
)
def test_legacy_nonportable_receipt_schemas_fail_closed(
    valid_request, request_field, old_schema
):
    path = Path(valid_request[request_field])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema"] = old_schema
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(AUTH.IntermediateTrendAuthorityError, match="wrong schema"):
        _validate(valid_request)


@pytest.mark.parametrize(
    "field,value,needle",
    [
        ("arms", ["B000", "F111", "A011", "A101"], "exact matched order"),
        ("learning_rate", 0.003, "0.001 or 0.01"),
        ("tle_file_set_sha256", "f" * 64, "fixed canonical TLE hash"),
        ("target_update_every", 2, "fixed value 50"),
        ("checkpoint_every_episodes", 50, "fixed value 100"),
        ("specialist_bundle_replay_capacity", 50000, "fixed value 2000"),
        ("evaluation_users", [100], "fixed sweep"),
    ],
)
def test_drifted_screen_binding_is_rejected(valid_request, field, value, needle):
    valid_request[field] = value

    with pytest.raises(AUTH.IntermediateTrendAuthorityError, match=needle):
        _validate(valid_request)


def test_zero_dose_checker_failure_is_not_overridden_by_embedded_pass(valid_request, monkeypatch):
    monkeypatch.setattr(
        AUTH,
        "validate_zero_dose_receipt",
        lambda _path, *, tle_root: (_ for _ in ()).throw(RuntimeError("parity failed")),
    )

    with pytest.raises(AUTH.IntermediateTrendAuthorityError, match="independent replay failed"):
        _validate(valid_request)


def test_nested_c1_corpus_failure_blocks_authority(valid_request, monkeypatch):
    monkeypatch.setattr(
        AUTH,
        "load_verified_c1_corpus",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("nested corpus unavailable")
        ),
    )

    with pytest.raises(
        AUTH.IntermediateTrendAuthorityError,
        match="C1 EXP nested authority: rejected",
    ):
        _validate(valid_request)


def test_selection_plan_path_and_hash_are_not_decorative(valid_request):
    valid_request["selection_plan"]["sha256"] = "0" * 64
    with pytest.raises(
        AUTH.IntermediateTrendAuthorityError, match="frozen plan hash mismatch"
    ):
        _validate(valid_request)
