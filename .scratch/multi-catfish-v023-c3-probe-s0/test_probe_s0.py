from __future__ import annotations

from fractions import Fraction
import hashlib
import json

import pytest

import run_probe_s0 as probe


def metric(bits: float, energy: float, served: int = 10) -> dict[str, object]:
    return {"total_bits": bits, "total_energy_j": energy, "served": served, "opportunities": 10}


def tiny_tape() -> dict[str, object]:
    return {
        "anchors": [{
            "anchor_id": "1:2:0",
            "profiles": [
                {"profile_id": "BASE", "kind": "base", "nominal": metric(100.0, 10.0), "realised": metric(100.0, 10.0)},
                {"profile_id": "U:0:1", "kind": "unilateral", "nominal": metric(130.0, 10.0), "realised": metric(20.0, 10.0)},
                {"profile_id": "J:1->2", "kind": "joint", "nominal": metric(120.0, 10.0, served=9), "realised": metric(500.0, 10.0, served=9)},
            ],
        }]
    }


def test_tiny_synthetic_tape_nominal_ranking_realised_scoring_exact_pooling() -> None:
    selected = probe.process_synthetic_tape(tiny_tape(), Fraction(10))
    assert selected[0]["profile_id"] == "U:0:1"
    pooled = probe.exact_pool(row["realised"] for row in selected)
    assert probe.parse_exact(pooled["eta_exact"], label="eta") == Fraction(2)
    assert pooled["served"] == 10


def test_never_score_with_nominal_invariant() -> None:
    tape = tiny_tape()
    selected = probe.process_synthetic_tape(tape, Fraction(10))
    # Nominal winner has 130 nominal bits but only 20 realised bits.
    assert selected[0]["realised"]["total_bits"] == 20.0
    assert probe.exact_pool(row["realised"] for row in selected)["eta_bits_per_j"] == 2.0
    assert probe.exact_pool(row["realised"] for row in selected)["eta_bits_per_j"] != 13.0


def test_nominal_service_constraint_and_arm_restrictions() -> None:
    profiles = tiny_tape()["anchors"][0]["profiles"]
    all_choice = probe.choose_profile(
        profiles, eta_ref=Fraction(10), allowed_kinds=frozenset({"base", "unilateral", "joint"})
    )
    joint_choice = probe.choose_profile(
        profiles, eta_ref=Fraction(10), allowed_kinds=frozenset({"base", "joint"})
    )
    assert all_choice["profile_id"] == "U:0:1"
    # The higher-score joint is nominally below BASE service, hence BASE.
    assert joint_choice["profile_id"] == "BASE"


def test_determinism_and_rank_ties() -> None:
    first = probe.process_synthetic_tape(tiny_tape(), Fraction(10))
    second = probe.process_synthetic_tape(tiny_tape(), Fraction(10))
    assert probe.canonical_bytes(first) == probe.canonical_bytes(second)
    values = [Fraction(1), Fraction(1), Fraction(3)]
    assert probe.spearman_exact_scores(values, values) == 1.0


def test_refuses_modified_tape_digest(tmp_path) -> None:
    tape = tmp_path / "tape.json"
    tape.write_bytes(b'{"sealed":true}\n')
    digest = hashlib.sha256(tape.read_bytes()).hexdigest()
    probe.require_file_digest(tape, digest, label="synthetic tape")
    tape.write_bytes(json.dumps({"sealed": False}).encode() + b"\n")
    with pytest.raises(probe.ProbeError, match="digest mismatch"):
        probe.require_file_digest(tape, digest, label="synthetic tape")


def test_write_once_refuses_overwrite(tmp_path) -> None:
    path = tmp_path / "result.json"
    probe.write_once(path, {"a": 1})
    with pytest.raises(probe.ProbeError, match="overwrite"):
        probe.write_once(path, {"a": 1})
