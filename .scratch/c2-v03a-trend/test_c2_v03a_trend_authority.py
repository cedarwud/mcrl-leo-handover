"""Public-contract tests for the C2 V0.3A trend authority."""

from __future__ import annotations

import hashlib
import copy
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_v03a_trend_authority as authority  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    repo = tmp_path / "repo"
    files = {
        "artifacts/PREREG-FROZEN-2026-08-25-R2.json": b"prereg\n",
        "artifacts/c1/c1-exp-corpus-manifest.json": b"corpus\n",
        "docs/C2-TEMPORAL-FORK-CANDIDATE-V0.3-2026-08-29.md": b"candidate\n",
        ".scratch/c2-v03/c2_temporal_fork_episode_runner.py": b"core\n",
        ".scratch/c2-v03a-trend/c2_v03a_trend_arm.py": b"arm\n",
    }
    for relative in authority.REQUIRED_PINNED_FILES:
        files.setdefault(relative, f"fixture:{relative}\n".encode("utf-8"))
    for relative, data in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    tle_root = tmp_path / "tle"
    tle_root.mkdir()
    tle = tle_root / "starlink_20260820.tle"
    tle.write_bytes(b"tle\n")
    tle_set_sha = hashlib.sha256(
        f"{tle.name}:{_sha256(tle)}".encode("utf-8")
    ).hexdigest()
    request = {
        "schema": authority.REQUEST_SCHEMA,
        "claim_ceiling": authority.CLAIM_CEILING,
        "formal_training_authorized": False,
        "c1_route_status": authority.C1_ROUTE_STATUS,
        "c2_route_status": authority.C2_ROUTE_STATUS,
        "c3_route_status": authority.C3_ROUTE_STATUS,
        "episodes": 1500,
        "learning_rate": 0.001,
        "arms": list(authority.ALLOWED_ARMS),
        "seeds": {
            "training": 2026082901,
            "environment": 2026082902,
            "mobility": 2026082903,
        },
        "evaluation_seeds": [
            2026082904,
            2026082905,
            2026082906,
            2026082907,
            2026082908,
        ],
        "users": 100,
        "evaluation_users": [60, 80, 100, 120, 140],
        "epsilon_decay_episodes": 2000,
        "target_update_every": 50,
        "checkpoint_every_episodes": 100,
        "specialist_bundle_replay_capacity": 2000,
        "donor_beta": 0.25,
        "acrm_eta": 1.0,
        "max_c2_candidates": 9,
        "lr_selection_rule": copy.deepcopy(authority.LR_SELECTION_RULE),
        "tle_file_set_sha256": tle_set_sha,
        "tle_file_count": 1,
        "pinned_files": {
            relative: _sha256(repo / relative) for relative in files
        },
        "canonical_prereg": "artifacts/PREREG-FROZEN-2026-08-25-R2.json",
        "c1_exp_corpus_manifest": "artifacts/c1/c1-exp-corpus-manifest.json",
    }
    return repo, tle_root, request


def test_valid_v03a_1500_request_passes_and_preserves_developmental_c3(tmp_path):
    repo, tle_root, request = _fixture(tmp_path)

    validated = authority.validate_v03a_trend_authority(
        request, repo=repo, tle_root=tle_root
    )

    assert validated["status"] == "PASS"
    assert validated["episodes"] == 1500
    assert validated["learning_rate"] == 0.001
    assert validated["arms"] == list(authority.ALLOWED_ARMS)
    assert validated["c3_route_status"] == authority.C3_ROUTE_STATUS
    assert validated["c1_route_status"] == authority.C1_ROUTE_STATUS
    assert validated["c2_route_status"] == authority.C2_ROUTE_STATUS
    assert validated["formal_training_authorized"] is False


def test_v03a_authority_rejects_unconditional_c3_route(tmp_path):
    repo, tle_root, request = _fixture(tmp_path)
    drifted = copy.deepcopy(request)
    drifted["c3_route_status"] = "ROUTE"

    try:
        authority.validate_v03a_trend_authority(
            drifted, repo=repo, tle_root=tle_root
        )
    except authority.V03ATrendAuthorityError as error:
        assert "C3 route status" in str(error)
    else:  # pragma: no cover - makes a false PASS explicit
        raise AssertionError("unconditional C3 routing was accepted")


def test_v03a_authority_rejects_prose_only_lr_rule(tmp_path):
    repo, tle_root, request = _fixture(tmp_path)
    drifted = copy.deepcopy(request)
    drifted["lr_selection_rule"] = {"tie_band_percentage_points": 0.25}

    try:
        authority.validate_v03a_trend_authority(
            drifted, repo=repo, tle_root=tle_root
        )
    except authority.V03ATrendAuthorityError as error:
        assert "LR selection rule" in str(error)
    else:  # pragma: no cover
        raise AssertionError("non-executable LR prose was accepted")
