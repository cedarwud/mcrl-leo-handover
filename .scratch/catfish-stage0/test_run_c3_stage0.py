"""Deterministic unit/fixture tests for the isolated C3 Stage-0 runner."""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("run_c3_stage0.py")
spec = importlib.util.spec_from_file_location("c3_stage0", MODULE_PATH)
c3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = c3
spec.loader.exec_module(c3)


def _record(interval: int, *, candidate: bool = True) -> dict:
    return {
        "nonfocal_actions": ((8, 1), (8, 2)),
        "served_users": (0, 1, 2),
        "active_beams": ((8, 1), (8, 2)),
        "active_satellites": (8,),
        "reference_hold_valid": True,
        "service": True,
        "destination_max_unchanged": True,
        "source_bottleneck_relief": True,
        "system_payload_power_w": 9.0 if candidate else 10.0,
        # The adapter residual is deliberately nonsense: the certificate
        # must derive this identity from the independent source maxima and
        # realised system-power delta below.
        "pa_residual_w": 999.0,
        "reference_max_power_w": 10.0,
        "reference_next_power_w": 9.0,
        "fading_enabled": False,
        "preview_commit_parity": True,
        "phi1": 1 if candidate and interval == 0 else 0,
        "phi2": 0,
    }


class FixtureFactory:
    def replay_prefix(self, anchor):
        return {"anchor": dict(anchor)}

    def fingerprint(self, twin):
        return c3.state_sha256(twin)


def test_domain_separated_forecast_stream_is_exact_and_independent():
    args = ("checkpoint", 17, 2, 4)
    first = c3.derive_rng(c3.NAMESPACES["forecast"], *args)
    second = c3.derive_rng(c3.NAMESPACES["forecast"], *args)
    other_namespace = c3.derive_rng(c3.NAMESPACES["cert_control"], *args)
    assert first is not second
    assert c3.rng_state_sha256(first) == c3.rng_state_sha256(second)
    assert c3.rng_state_sha256(first) != c3.rng_state_sha256(other_namespace)
    assert first.integers(0, 2**31) == second.integers(0, 2**31)


def test_pa_identity_is_independent_and_marginal_helper_is_removed():
    supply = lambda value: 2.0 * value
    assert c3.pa_identity_residual(
        -4.0, reference_max_power_w=3.0, reference_next_power_w=1.0,
        supply_power=supply
    ) == pytest.approx(0.0)
    assert not hasattr(c3, "marginal_power_reward")


def test_physical_id_is_remapped_after_table_rebuild():
    rebuilt = {("sat", 4): 0, ("sat", 2): 1}
    assert c3.remap_action_by_physical_id(rebuilt, ("sat", 2)) == 1
    with pytest.raises(RuntimeError):
        c3.remap_action_by_physical_id(rebuilt, ("sat", 9))


def test_replay_twins_use_prefix_reconstruction_and_fingerprint():
    reference, candidate, fingerprint = c3.replay_twins(FixtureFactory(), {"step": 2})
    assert reference == candidate
    assert fingerprint == c3.state_sha256(reference)


def test_h3_certificate_accepts_persistent_power_relief():
    factory = FixtureFactory()

    def roll(twin, focal_id, interval, rng):
        return _record(interval, candidate=focal_id == (8, 2))

    reference, candidate, _ = c3.replay_twins(factory, {"step": 2})
    result = c3.certify_candidate(
        source_id=(8, 1), candidate_id=(8, 2), reference_twin=reference,
        candidate_twin=candidate, twin_factory=factory, roll_forward=roll,
        forecast_rng_reference=c3.derive_rng(c3.NAMESPACES["forecast"], "checkpoint", 17, 2, 4),
        forecast_rng_candidate=c3.derive_rng(c3.NAMESPACES["forecast"], "checkpoint", 17, 2, 4),
    )
    assert result.certified
    assert result.reasons == ()
    assert result.gain_j == pytest.approx(3 * c3.DELTA_S)


def test_certificate_rejects_nonfocal_divergence_and_late_event():
    factory = FixtureFactory()

    def roll(twin, focal_id, interval, rng):
        row = _record(interval, candidate=focal_id == (8, 2))
        if focal_id == (8, 2) and interval == 1:
            row["nonfocal_actions"] = ((99, 9), (8, 2))
            row["phi1"] = 1
        return row

    reference, candidate, _ = c3.replay_twins(factory, {"step": 2})
    result = c3.certify_candidate(
        source_id=(8, 1), candidate_id=(8, 2), reference_twin=reference,
        candidate_twin=candidate, twin_factory=factory, roll_forward=roll,
        forecast_rng_reference=c3.derive_rng(c3.NAMESPACES["forecast"], "checkpoint", 17, 2, 4),
        forecast_rng_candidate=c3.derive_rng(c3.NAMESPACES["forecast"], "checkpoint", 17, 2, 4),
    )
    assert not result.certified
    assert "nonfocal_action_mismatch" in result.reasons
    assert "later_phi1_event" in result.reasons


def test_selection_is_gain_then_lexicographic_id_and_rank_is_uniform():
    results = [
        c3.CertificateResult((8, 3), True, (), 2.0, ()),
        c3.CertificateResult((8, 2), True, (), 2.0, ()),
        c3.CertificateResult((8, 4), False, ("rejected",), 100.0, ()),
    ]
    assert c3.select_top_gain(results).candidate_id == (8, 2)
    chosen = c3.select_rank_control(results, np.random.default_rng(3))
    assert chosen in {(8, 2), (8, 3)}
    assert c3.select_certificate_control(((8, 2),), np.random.default_rng(3)) == (8, 2)


def test_negative_gain_condition_survivor_is_retained_until_terminal_rule():
    survivor = c3.CertificateResult((8, 2), True, (), -1.0, ())
    assert c3.select_top_gain([survivor]) is survivor
    effects = {
        "Delta_E_payload_ref": 1.0,
        "Delta_E_payload_cert": 1.0,
        "Delta_EE_ref": 1.0,
        "Delta_EE_cert": 1.0,
    }
    rows = [
        {
            "evaluation_seed": f"fixture-{index}",
            "gain_j": 1.0,
            "selected_gain_j": {"top_gp": -1.0},
            **effects,
        }
        for index in range(5)
        for _ in range(4)
    ]
    assert c3.stage0_decision(
        rows, c3.aggregate_effects(rows), engineering_ok=True, branch_guards_ok=True
    ) == c3.DROP_ROLE


def _branch(name, *, bits, energy, ee):
    return c3.BranchOutcome(
        name=name, useful_bits=bits, payload_energy_j=energy, canonical_ee=ee,
        service=True,
        intervals=tuple(_record(i, candidate=name != "reference") for i in range(3)),
        evidence={"anchor_fingerprint_sha256": "common-anchor"},
    )


def test_four_branch_effects_and_five_seed_equal_weight_aggregation():
    branches = {
        "reference": _branch("reference", bits=100.0, energy=100.0, ee=1.0),
        "top_gp": _branch("top_gp", bits=101.0, energy=90.0, ee=1.2),
        "C3-RANK-R": _branch("C3-RANK-R", bits=100.0, energy=80.0, ee=1.3),
        "C3-CERT-R": _branch("C3-CERT-R", bits=99.0, energy=100.0, ee=1.0),
    }
    effects = c3.paired_effects(branches)
    assert effects["Delta_E_payload_ref"] == 10.0
    assert effects["Delta_EE_ref"] == pytest.approx(0.2)
    assert effects["Delta_E_payload_cert"] == 20.0
    rows = [
        {"evaluation_seed": label, **effects}
        for label in ("fixture-a", "fixture-b", "fixture-c", "fixture-d", "fixture-e")
    ]
    aggregate = c3.aggregate_effects(rows)
    assert aggregate["eligible_anchors"] == 5
    assert all(value == 1 for value in aggregate["support_by_seed"].values())
    assert aggregate["seed_t95_lower"]["Delta_EE_ref"] == pytest.approx(0.2)


def test_terminal_rule_requires_all_five_seed_support_and_twenty_proposals():
    effects = {
        "Delta_E_payload_ref": 1.0,
        "Delta_E_payload_cert": 1.0,
        "Delta_EE_ref": 1.0,
        "Delta_EE_cert": 1.0,
    }
    labels = ("fixture-a", "fixture-b", "fixture-c", "fixture-d", "fixture-e")
    rows = [
        {"evaluation_seed": labels[index % 5], "gain_j": 1.0, **effects}
        for index in range(20)
    ]
    aggregate = c3.aggregate_effects(rows)
    assert c3.stage0_decision(
        rows, aggregate, engineering_ok=True, branch_guards_ok=True
    ) == c3.PASS_RESULT
    short = rows[:-1]
    assert c3.stage0_decision(
        short, c3.aggregate_effects(short), engineering_ok=True, branch_guards_ok=True
    ) == c3.DROP_ROLE
    assert c3.stage0_decision(
        rows, aggregate, engineering_ok=False, branch_guards_ok=True
    ) == c3.CERTIFICATE_FAILURE


def test_postselection_uses_one_common_anchor_fingerprint():
    outcomes = {
        "reference": _branch("reference", bits=100.0, energy=100.0, ee=1.0),
        "top_gp": _branch("top_gp", bits=101.0, energy=90.0, ee=1.2),
        "C3-RANK-R": _branch("C3-RANK-R", bits=100.0, energy=80.0, ee=1.3),
        "C3-CERT-R": _branch("C3-CERT-R", bits=99.0, energy=100.0, ee=1.0),
    }

    def evaluate(twin, selected, rng):
        return replace(
            outcomes[selected],
            evidence={"anchor_fingerprint_sha256": c3.state_sha256(twin)},
        )

    selected = {
        "reference": "reference",
        "top_gp": "top_gp",
        "C3-RANK-R": "C3-RANK-R",
        "C3-CERT-R": "C3-CERT-R",
    }
    result = c3.evaluate_postselection(
        factory=FixtureFactory(), anchor={"step": 2}, selected_ids=selected,
        evaluate_branch=evaluate, realised_rng_factory=lambda: np.random.default_rng(7),
    )
    assert set(result) == set(selected)

    class DriftingFactory(FixtureFactory):
        def __init__(self):
            self.calls = 0

        def replay_prefix(self, anchor):
            self.calls += 1
            return {"anchor": dict(anchor), "call": self.calls}

        def fingerprint(self, twin):
            return f"fp-{twin['call']}"

    with pytest.raises(RuntimeError, match="common.*fingerprint|replay.*fingerprint"):
        c3.evaluate_postselection(
            factory=DriftingFactory(), anchor={"step": 2}, selected_ids=selected,
            evaluate_branch=evaluate, realised_rng_factory=lambda: np.random.default_rng(7),
        )


def test_malformed_closure_and_seed_manifests_fail_closed(tmp_path, monkeypatch):
    malformed = tmp_path / "closure.json"
    malformed.write_text('{"schema":"wrong"}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="schema"):
        c3.verify_closure_manifest(malformed)

    # Exercise the exact seed-shape/content validator without revealing any
    # formal seed values in the test output or invoking the real closure.
    closure = tmp_path / "closure-ok.json"
    closure.write_text('{}', encoding="utf-8")
    monkeypatch.setattr(c3, "verify_closure_manifest", lambda *args, **kwargs: {})
    seed_manifest = tmp_path / "seeds.json"
    seed_manifest.write_text(
        '{"schema":"smc-er-c3-stage0-seeds-v1",'
        '"closure_manifest_sha256":"%s",'
        '"c3_seeds":[1,2,3,4],'
        '"repository_disjointness_checked_before_reveal":true}'
        % c3.sha256_file(closure),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="exactly five"):
        c3.load_seed_manifest(seed_manifest, closure)


def test_stage0_cli_requires_nonexistent_explicit_seed_manifest(tmp_path):
    with pytest.raises(FileNotFoundError):
        c3.load_seed_manifest(tmp_path / "sealed-seeds.json", tmp_path / "closure.json")
