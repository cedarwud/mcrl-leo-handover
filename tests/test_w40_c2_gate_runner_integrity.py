"""W-40 — C2 gate source and schedule receipt integrity."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
GATE_DIR = ROOT / ".scratch" / "ee-axis-redesign"
if str(GATE_DIR) not in sys.path:
    sys.path.insert(0, str(GATE_DIR))

import run_c2_v03_keyed_multiseed_gate as gate  # noqa: E402


def _schedule(seed: int = 2026083101) -> dict[str, object]:
    anchor: dict[str, object] = {
        "seed": seed,
        "step_index": 2,
        "eligible_departure_users": [3, 7],
        "scheduled_focal_users": [7],
        "opening_main_actions": [1, 2, 3],
        "opening_main_physical_actions": [[101, 1], None, [303, 3]],
    }
    anchor["anchor_schedule_sha256"] = gate._schedule_digest(anchor)
    schedule: dict[str, object] = {
        "schema": "multi-catfish-mcrl-v03-c2-seed-schedule-v1",
        "prereg_sha256": "a" * 64,
        "source_manifest_sha256": "c" * 64,
        "seed": seed,
        "selection": "uniform-without-replacement-domain-separated-preoutcome",
        "anchors": [anchor],
    }
    schedule["schedule_sha256"] = gate._schedule_digest(schedule)
    return schedule


def test_source_manifest_has_per_file_receipts_and_revalidates() -> None:
    paths = [ROOT / "pyproject.toml", ROOT / "src/mcrl/env/step.py"]
    manifest = gate._build_source_manifest(paths)

    assert manifest["schema"] == gate.SOURCE_MANIFEST_SCHEMA
    assert manifest["manifest_sha256"] == gate._validate_source_manifest(
        manifest, expected_paths=paths
    )
    assert {entry["path"] for entry in manifest["files"]} == {
        "pyproject.toml",
        "src/mcrl/env/step.py",
    }
    assert all(len(entry["sha256"]) == 64 for entry in manifest["files"])


def test_source_manifest_rejects_tampering() -> None:
    manifest = gate._build_source_manifest([ROOT / "pyproject.toml"])
    tampered = json.loads(json.dumps(manifest))
    tampered["files"][0]["sha256"] = "b" * 64

    with pytest.raises(RuntimeError, match="digest disagrees"):
        gate._validate_source_manifest(tampered)


def test_schedule_is_created_once_and_exactly_matching_file_is_resumed(tmp_path: Path) -> None:
    schedule = _schedule()
    path = tmp_path / "schedule.json"

    first_sha = gate._persist_or_resume_schedule(
        path,
        schedule,
        prereg_sha256="a" * 64,
        seed=2026083101,
        source_manifest_sha256="c" * 64,
    )
    second_sha = gate._persist_or_resume_schedule(
        path,
        schedule,
        prereg_sha256="a" * 64,
        seed=2026083101,
        source_manifest_sha256="c" * 64,
    )

    assert first_sha == second_sha
    assert first_sha == gate._file_sha256(path)
    assert json.loads(path.read_text(encoding="utf-8")) == schedule


@pytest.mark.parametrize(
    ("prereg_sha256", "seed", "source_manifest_sha256", "match"),
    [
        ("b" * 64, 2026083101, "c" * 64, "sealed prereg"),
        ("a" * 64, 2026083102, "c" * 64, "seed"),
        ("a" * 64, 2026083101, "d" * 64, "source manifest"),
    ],
)
def test_existing_schedule_cannot_be_resumed_under_different_identity(
    tmp_path: Path,
    prereg_sha256: str,
    seed: int,
    source_manifest_sha256: str,
    match: str,
) -> None:
    schedule = _schedule()
    path = tmp_path / "schedule.json"
    gate._persist_or_resume_schedule(
        path,
        schedule,
        prereg_sha256="a" * 64,
        seed=2026083101,
        source_manifest_sha256="c" * 64,
    )

    with pytest.raises(RuntimeError, match=match):
        gate._persist_or_resume_schedule(
            path,
            schedule,
            prereg_sha256=prereg_sha256,
            seed=seed,
            source_manifest_sha256=source_manifest_sha256,
        )


def test_existing_schedule_bytes_must_match_before_resume(tmp_path: Path) -> None:
    schedule = _schedule()
    path = tmp_path / "schedule.json"
    gate._persist_or_resume_schedule(
        path,
        schedule,
        prereg_sha256="a" * 64,
        seed=2026083101,
        source_manifest_sha256="c" * 64,
    )
    path.write_text(path.read_text(encoding="utf-8").replace('"step_index": 2', '"step_index": 9'), encoding="utf-8")

    with pytest.raises(RuntimeError, match="bytes disagree"):
        gate._persist_or_resume_schedule(
            path,
            schedule,
            prereg_sha256="a" * 64,
            seed=2026083101,
            source_manifest_sha256="c" * 64,
        )


def test_existing_schedule_symlink_is_rejected(tmp_path: Path) -> None:
    schedule = _schedule()
    target = tmp_path / "outside.json"
    target.write_text("{}\n", encoding="utf-8")
    path = tmp_path / "schedule.json"
    path.symlink_to(target)

    with pytest.raises(RuntimeError, match="regular file"):
        gate._persist_or_resume_schedule(
            path,
            schedule,
            prereg_sha256="a" * 64,
            seed=2026083101,
            source_manifest_sha256="c" * 64,
        )
