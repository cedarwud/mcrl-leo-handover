"""W-41 — V0.3B reactive C2 headroom-gate integrity and adjudication."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
GATE_DIR = ROOT / ".scratch" / "ee-axis-redesign"
if str(GATE_DIR) not in sys.path:
    sys.path.insert(0, str(GATE_DIR))

import run_c2_v03b_keyed_physical_headroom_gate as gate  # noqa: E402


SEEDS = [2026090101, 2026090102, 2026090103, 2026090104, 2026090105]
BURNED = [
    *range(2026082401, 2026082414),
    2026082801,
    *range(2026083101, 2026083106),
]


def _prereg(*, seeds: list[int] | None = None) -> dict[str, object]:
    return {
        "schema": gate.PREREG_SCHEMA,
        "status": "SEALED_BEFORE_V03B_HEADROOM_OUTCOMES",
        "implementation": {
            "c2_policy_version": gate.core.CANDIDATE_VERSION,
            "forecast_authority_schema": gate.core.FORECAST_AUTHORITY_SCHEMA,
            "chronology_schema": gate.core.CHRONOLOGY_RECEIPT_SCHEMA,
            "forecast_schema": gate.backend.FORECAST_SCHEMA,
            "anchor_schema": gate.backend.ANCHOR_SCHEMA,
            "horizon_steps": gate.core.HORIZON_STEPS,
            "offsets": list(gate.EXPECTED_OFFSETS),
            "release_reasons": ["horizon", "support_expired"],
            "fading_mode": gate.KEYED_FADING_VERSION,
            "policy_compositor_version": gate.backend.POLICY_COMPOSITOR_VERSION,
            "opening_source_rules": [
                "incumbent-hold",
                "max-lagged-candidate-sinr-rival",
            ],
        },
        "evaluation": {
            "seeds": list(SEEDS if seeds is None else seeds),
            "horizon_offsets": list(gate.EXPECTED_OFFSETS),
            "temporal_target_offsets": list(gate.TEMPORAL_OFFSETS),
            "early_stopping": False,
            "maximum_anchors_per_seed": 3,
            "maximum_candidates_per_anchor": 3,
            "minimum_anchors_per_seed": 2,
            "minimum_attempts_per_seed": 6,
        },
        "burned_seeds": {"ids": list(BURNED)},
        "decision": {
            "contract_or_numeric_errors": 0,
            "unresolved_infrastructure_errors": 0,
            "minimum_total_attempts": 30,
            "minimum_anchors_per_seed": 2,
            "minimum_attempts_per_seed": 6,
            "minimum_complete_fraction": 0.90,
            "maximum_opening_censor_fraction": 0.10,
            "maximum_postopening_censor_count": 0,
            "minimum_complete_per_seed": 4,
            "minimum_service_safe_complete_per_seed": 3,
            "minimum_release_offset_values": 2,
            "minimum_support_expired_traces": 1,
            "minimum_horizon_traces": 1,
            "minimum_positive_seeds": 4,
            "minimum_positive_anchor_digests": 4,
            "minimum_anchor_digests_per_source_rule": 1,
            "main_networks_replay_checkpoint_unchanged": True,
        },
        "supersedes": {
            "path": "artifacts/c2-v03-gate-20260831",
            "status": "SEALED_INDETERMINATE_IMMUTABLE_NOT_REUSED",
            "result_sha256": "f8fa59c3b274e730c0029d4b2ecfacf9c1c9f041f29863a3983bda02d904a2bd",
            "prereg_sha256": "3bb277ac5e50c32a4a45499e675dd40cdf1231ffec88d60464355e5dda70828f",
        },
    }


def _anchor(seed: int, index: int) -> str:
    return f"anchor-{seed}-{index}"


def _row(
    seed: int,
    anchor: str,
    index: int,
    *,
    positive: bool = True,
    source_rule: str = "incumbent-hold",
    release_offset: int = 3,
    release_reason: str = "horizon",
) -> dict[str, object]:
    return {
        "seed": seed,
        "anchor_schedule_sha256": anchor,
        "outcome": "COMPLETE_TRACE_SCORED",
        "service_guard": {"passed": True},
        "positive_service_safe": positive,
        "source_rule": source_rule,
        "release_offset": release_offset,
        "release_reason": release_reason,
        "index": index,
    }


def _seed_result(seed: int, rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "seed": seed,
        "anchors_scheduled": 2,
        "attempts_scheduled": len(rows),
        "eligible_departure_user_total": 8,
        "scheduled_focal_user_total": len(rows),
        "rows": rows,
    }


def _valid_results() -> list[dict[str, object]]:
    results = []
    for seed_index, seed in enumerate(SEEDS):
        rows = []
        for index in range(6):
            anchor = _anchor(seed, index // 3)
            rows.append(
                _row(
                    seed,
                    anchor,
                    index,
                    positive=seed_index < 4,
                    source_rule=(
                        "max-lagged-candidate-sinr-rival"
                        if index == 0
                        else "incumbent-hold"
                    ),
                    release_offset=1 if index == 0 else 3,
                    release_reason="support_expired" if index == 0 else "horizon",
                )
            )
        results.append(_seed_result(seed, rows))
    return results


def _schedule() -> dict[str, object]:
    anchor: dict[str, object] = {
        "seed": SEEDS[0],
        "step_index": 2,
        "eligible_departure_users": [3, 7],
        "eligible_departure_user_count": 2,
        "scheduled_focal_users": [7],
        "opening_main_actions": [1, 2, 3],
        "opening_main_physical_actions": [[101, 1], None, [303, 3]],
        "c2_policy_version": gate.core.CANDIDATE_VERSION,
        "horizon_offsets": list(gate.EXPECTED_OFFSETS),
    }
    anchor["anchor_schedule_sha256"] = gate._schedule_digest(anchor)
    schedule: dict[str, object] = {
        "schema": gate.SCHEDULE_SCHEMA,
        "prereg_sha256": "a" * 64,
        "source_manifest_sha256": "b" * 64,
        "seed": SEEDS[0],
        "c2_policy_version": gate.core.CANDIDATE_VERSION,
        "horizon_offsets": list(gate.EXPECTED_OFFSETS),
        "selection": "uniform-without-replacement-domain-separated-preoutcome",
        "anchors": [anchor],
    }
    schedule["schedule_sha256"] = gate._schedule_digest(schedule)
    return schedule


def test_v03b_schema_and_policy_domain_are_distinct_from_sealed_v1() -> None:
    old = json.loads(
        (ROOT / "artifacts/c2-v03-gate-20260831/prereg.json").read_text()
    )
    assert gate.PREREG_SCHEMA != old["schema"]
    assert gate.SOURCE_MANIFEST_SCHEMA != "multi-catfish-mcrl-v03-c2-keyed-gate-source-manifest-v1"
    assert gate.RESULT_SCHEMA.endswith("-result-v1")
    assert gate.core.CANDIDATE_VERSION == "C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE"


def test_old_fixed_hold_schedule_is_rejected() -> None:
    old = _schedule()
    old["schema"] = "multi-catfish-mcrl-v03-c2-seed-schedule-v1"
    with pytest.raises(RuntimeError, match="schema"):
        gate._validate_schedule(
            old,
            prereg_sha256="a" * 64,
            source_manifest_sha256="b" * 64,
            seed=SEEDS[0],
        )


def test_valid_adjudication_surfaces_release_census_fallback_and_anchor_replication() -> None:
    decision = gate._adjudicate(_prereg(), _valid_results())
    assert decision["outcome"] == "GO_BOUNDED_LEARNABILITY_PILOT_ONLY"
    assert decision["release_offset_diversity_ok"] is True
    assert decision["release_offset_counts"] == {"1": 5, "2": 0, "3": 25}
    assert decision["release_reason_counts"] == {"support_expired": 5, "horizon": 25}
    assert decision["fallback_coverage_ok"] is True
    assert decision["source_rule_counts"]["max-lagged-candidate-sinr-rival"] == 5
    assert decision["anchor_replication_ok"] is True
    assert decision["departure_mass_ok"] is True


def test_missing_release_diversity_or_fallback_is_indeterminate() -> None:
    results = _valid_results()
    for result in results:
        for row in result["rows"]:
            row["release_offset"] = 3
            row["release_reason"] = "horizon"
            row["source_rule"] = "incumbent-hold"
    decision = gate._adjudicate(_prereg(), results)
    assert decision["outcome"] == "INDETERMINATE"
    assert decision["release_offset_diversity_ok"] is False
    assert decision["fallback_coverage_ok"] is False


def test_positive_rows_clustered_on_one_anchor_fail_anchor_replication() -> None:
    results = _valid_results()
    for result in results:
        for row in result["rows"]:
            row["anchor_schedule_sha256"] = "one-shared-anchor"
    decision = gate._adjudicate(_prereg(), results)
    assert decision["anchor_replication_ok"] is False
    assert decision["outcome"] == "SCIENTIFIC_NO_GO"


def test_valid_instrument_with_no_positive_headroom_is_scientific_no_go() -> None:
    results = _valid_results()
    for result in results:
        for row in result["rows"]:
            row["positive_service_safe"] = False
    decision = gate._adjudicate(_prereg(), results)
    assert decision["instrument_ok"] is True
    assert decision["support_ok"] is True
    assert decision["anchor_replication_ok"] is False
    assert decision["outcome"] == "SCIENTIFIC_NO_GO"


def test_dynamic_branch_copier_is_bound_into_source_manifest() -> None:
    relative = {
        path.resolve().relative_to(ROOT.resolve()).as_posix()
        for path in gate._source_paths()
    }
    assert ".scratch/catfish-stage0/c3_reward_aligned_v3_trainer_backend.py" in relative
    expected_closure = {
        path.resolve().relative_to(ROOT.resolve()).as_posix()
        for runtime_root in (gate.C2_V03, gate.STAGE0, gate.SMC, gate.LEGACY)
        for path in runtime_root.glob("*.py")
    }
    assert expected_closure <= relative


def test_preserved_namespace_snapshot_detects_byte_drift(tmp_path: Path) -> None:
    namespace = tmp_path / "old"
    namespace.mkdir()
    artifact = namespace / "result.json"
    artifact.write_text("before", encoding="utf-8")
    before = gate._namespace_snapshot(namespace)
    artifact.write_text("after", encoding="utf-8")
    after = gate._namespace_snapshot(namespace)
    assert before != after


def test_source_manifest_rejects_tampering_and_omission() -> None:
    paths = [ROOT / "pyproject.toml", ROOT / "src/mcrl/env/step.py"]
    manifest = gate._build_source_manifest(paths)
    assert gate._validate_source_manifest(manifest, expected_paths=paths) == manifest["manifest_sha256"]

    tampered = copy.deepcopy(manifest)
    tampered["files"][0]["sha256"] = "c" * 64
    with pytest.raises(RuntimeError, match="digest disagrees"):
        gate._validate_source_manifest(tampered)

    omitted = gate._build_source_manifest(paths[:1])
    with pytest.raises(RuntimeError, match="file set disagrees"):
        gate._validate_source_manifest(omitted, expected_paths=paths)


def test_evaluation_seed_overlapping_burned_block_is_rejected() -> None:
    invalid = _prereg(seeds=[BURNED[0], *SEEDS[1:]])
    with pytest.raises(RuntimeError, match="overlaps"):
        gate._validate_prereg(invalid)


def test_new_seed_block_is_disjoint_from_explicitly_burned_ids() -> None:
    gate._validate_prereg(_prereg())
    assert not set(SEEDS) & set(BURNED)


def test_sealed_v03b_prereg_and_manifest_validate_against_current_source_set() -> None:
    artifact_dir = ROOT / "artifacts" / "c2-v03b-reactive-keyed-physical-headroom-gate-20260831"
    prereg, prereg_sha256 = gate._read_sealed_prereg(
        artifact_dir / "prereg.json", artifact_dir / "prereg.sha256"
    )
    gate._validate_prereg(prereg)
    manifest = gate._read_source_manifest(artifact_dir / "source-manifest.json")
    manifest_sha256 = gate._validate_source_manifest(
        manifest, expected_paths=gate._source_paths()
    )
    assert prereg_sha256 == "84cd4704e510df33772d41628f919109ccd047219542d2ab346c26fcefab4790"
    assert manifest_sha256 == "55acddaff4ece4564b20df5b96ad780f99c0906ec4e184eb9868c76d6032bc78"
