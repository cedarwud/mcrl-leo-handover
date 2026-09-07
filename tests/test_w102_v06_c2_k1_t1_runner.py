"""W-102 -- V0.6 T1 runner preparation, complete rows, and seals."""

from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_v06_c2_k1 import canonical_bytes


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / ".scratch" / "c3-v04" / "run_v06_c2_k1_t1.py"
spec = importlib.util.spec_from_file_location("v06_c2_k1_t1_runner", RUNNER)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _worlds() -> list[dict[str, object]]:
    result = []
    for pool, start in (("early", 2026101001), ("mid", 2026101011), ("late", 2026101021)):
        steps = [1, 2] if pool == "early" else ([3, 4] if pool == "mid" else [5, 6])
        for world in range(start, start + 4):
            result.append({"pool": pool, "world_id": world,
                           "eligible_steps": steps, "eligible_users": [1, 0]})
    return result


def _valid_live_prepare(tmp_path: Path, *,
                        simulator_manifest: str = "e" * 64,
                        q13_manifest: str = "9" * 64,
                        simulator_prereg_sha256: str = "f" * 64,
                        t1_prereg_sha256: str = "0" * 64) -> dict[str, object]:
    """Build one fully validator-conformant target-free v2 receipt."""
    anchors = []
    bindings = {}
    hybrid_hashes = {lineage: chr(99 + index) * 64
                     for index, lineage in enumerate(mod.LINEAGES)}
    for pool, start, step in (("early", 2026101001, 1),
                              ("mid", 2026101011, 3),
                              ("late", 2026101021, 5)):
        for world in range(start, start + 4):
            anchors.append({
                "pool": pool, "world_id": world, "step": step,
                "focal_user": 0, "reference_action": 2,
                "physical_main_departure": True,
                "complete_forecast_horizon": True,
                "complete_28_action_census": True, "alias_absence": True,
                "world_anchor_sha256": "1" * 64,
                "anchor_sha256": "2" * 64,
                "reference_physical_key": [1, 2],
                "incumbent_physical_key": [3, 4],
                "legal_action_mask": [True] * NUM_ACTIONS,
                "candidate_actions": [action for action in range(NUM_ACTIONS)
                                      if action != 2],
                "candidate_physical_keys": [[100 + action, 5]
                                            for action in range(NUM_ACTIONS)
                                            if action != 2],
                "checkpoint_sha256": "3" * 64,
                "source_manifest_sha256": simulator_manifest,
                "policy_sha256": "5" * 64,
                "evaluation_seed": world,
            })
            key = f"{pool}:{world}:{step}:0"
            bindings[key] = {
                lineage: {
                    "q1_sha256": "a" * 64, "q3_sha256": "b" * 64,
                    "hybrid_sha256": hybrid_hashes[lineage],
                    "initialization_seed": mod.Q13_INITIALIZATION_SEEDS[index],
                    "crn_sha256": "d" * 64,
                    "q13_score_vector": [0.0] * NUM_ACTIONS, "a_D": 0,
                }
                for index, lineage in enumerate(mod.LINEAGES)
            }
    return mod.build_prepare_live(
        anchors, lineage_bindings=bindings,
        simulator_source_manifest_sha256=simulator_manifest,
        q13_gate_source_manifest_sha256=q13_manifest,
        simulator_prereg_file_sha256=simulator_prereg_sha256,
        t1_prereg_file_sha256=t1_prereg_sha256,
        main_dir=tmp_path / "main", main_checkpoint_sha256="3" * 64,
        expected_initialization_seeds=mod.Q13_INITIALIZATION_SEEDS,
        expected_hybrid_hashes=hybrid_hashes,
    )


def test_prepare_binds_12_anchors_policy_and_gates(tmp_path: Path) -> None:
    payload = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64,
                                t1_prereg_file_sha256="e" * 64)
    assert payload["counts"]["expected_pairs"] == 1008
    assert len(payload["anchors"]) == 12
    assert payload["training"] is False and payload["test_split_opened"] is False
    assert payload["outcome_selection"] is False
    assert payload["prepare_sha256"] == mod.canonical_sha256({k: v for k, v in payload.items() if k != "prepare_sha256"})
    mod.prepare(_worlds(), tmp_path, q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                source_manifest_sha256="a" * 64,
                simulator_prereg_file_sha256="d" * 64,
                t1_prereg_file_sha256="e" * 64)
    with pytest.raises(FileExistsError):
        mod.prepare(_worlds(), tmp_path, q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                    source_manifest_sha256="a" * 64,
                    simulator_prereg_file_sha256="d" * 64,
                    t1_prereg_file_sha256="e" * 64)


def _lineage_rows(policy_sha256: str | None = None) -> list[dict[str, object]]:
    rows = []
    for action in range(NUM_ACTIONS):
        vector = np.zeros(NUM_ACTIONS)
        vector[action] = 1.0
        candidate_k1 = 3 if action == 2 else 5
        candidate_rates = [100., 1.] if action == 7 else ([1., 1.] if action == 2 else [2., 1.])
        z_vector = np.zeros(NUM_ACTIONS)
        z_vector[action] = 100. if action == 7 else 0.0
        reference_q13_sum = np.zeros((2, NUM_ACTIONS), dtype=float)
        reference_q13_sum[:, 3] = 2.0
        candidate_q13_sum = np.zeros((2, NUM_ACTIONS), dtype=float)
        candidate_q13_sum[:, candidate_k1] = 2.0
        rows.append({
            "q1_k0": np.eye(NUM_ACTIONS, dtype=float)[2],
            "q3_k0": np.eye(NUM_ACTIONS, dtype=float)[2],
            "mask_k0": np.ones(NUM_ACTIONS, dtype=bool),
            "reference_action": 2,
            "reference_q1_k1": np.eye(NUM_ACTIONS, dtype=float)[3],
            "reference_q3_k1": np.eye(NUM_ACTIONS, dtype=float)[3],
            "reference_mask_k1": np.ones(NUM_ACTIONS, dtype=bool),
            "candidate_q1_k1": np.eye(NUM_ACTIONS, dtype=float)[candidate_k1],
            "candidate_q3_k1": np.eye(NUM_ACTIONS, dtype=float)[candidate_k1],
            "candidate_mask_k1": np.ones(NUM_ACTIONS, dtype=bool),
            "candidate_rates_k1": candidate_rates, "reference_rates_k1": [1., 1.],
            "candidate_power_k1": 1. if action == 2 else 2., "reference_power_k1": 1.,
            "candidate_rates_k0": [1., 1.], "reference_rates_k0": [1., 1.],
            "candidate_power_k0": 1., "reference_power_k0": 1.,
            "z2_k1_normalized_by_action": z_vector,
            "policy_sha256": policy_sha256 or "b" * 64, "crn_sha256": "c" * 64,
            "reference_k1_executed_actions": [3, 3],
            "candidate_k1_executed_actions": [candidate_k1, candidate_k1],
            "reference_k1_q13_actions": [3, 3],
            "candidate_k1_q13_actions": [candidate_k1, candidate_k1],
            "reference_k1_q13_sum": reference_q13_sum.tolist(),
            "candidate_k1_q13_sum": candidate_q13_sum.tolist(),
            "reference_k1_q13_mask": np.ones(
                (2, NUM_ACTIONS), dtype=bool).tolist(),
            "candidate_k1_q13_mask": np.ones(
                (2, NUM_ACTIONS), dtype=bool).tolist(),
            "reference_k0_executed_actions": [2, 0],
            "candidate_k0_executed_actions": [action, 0],
            "k0_action_mask": np.ones(
                (2, NUM_ACTIONS), dtype=bool).tolist(),
            # Selected oracle/DROP branch-local continuations, k=0..3.
            "oracle_rates_bps": [[1., 1.], [100., 1.], [4., 0.], [4., 0.]],
            "drop_rates_bps": [[1., 1.], [1., 1.], [3., 0.], [3., 0.]],
            "oracle_actions": [[7, 0], [5, 5], [5, 5], [5, 5]],
            "drop_actions": [[2, 0], [3, 3], [3, 3], [3, 3]],
            "oracle_power_w": [1., 2., 2., 2.],
            "drop_power_w": [1., 1., 2., 2.],
            "oracle_served": [[True, True]] * 4,
            "drop_served": [[True, True]] * 4,
            "oracle_reference_rates_bps": [[1., 1.], [1., 1.], [1., 0.], [1., 0.]],
            "drop_reference_rates_bps": [[1., 1.], [1., 1.], [1., 0.], [1., 0.]],
            "oracle_reference_power_w": [1., 1., 2., 2.],
            "drop_reference_power_w": [1., 1., 2., 2.],
            "oracle_reference_served": [[True, True]] * 4,
            "drop_reference_served": [[True, True]] * 4,
            "oracle_reference_actions": [[2, 0], [3, 3], [3, 3], [3, 3]],
            "drop_reference_actions": [[2, 0], [3, 3], [3, 3], [3, 3]],
        })
    return rows


def test_generate_emits_all_1008_rows_without_q2_or_sign_filter() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    result = mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    assert result["counts"]["pairs"] == 1008
    assert len(result["rows"]) == 1008
    assert result["q2_consulted"] is False
    assert all(row["candidate_differs_only_at_k0"] and not row["sign_filter"] for row in result["rows"])
    assert result["counts"]["controls"] == 36
    assert result["gates"]["launchable"] is True
    assert result["prepare_sha256"] == prepare["prepare_sha256"]
    assert result["source_sha256"] == mod._source_payload_sha256(result)


def test_nonfocal_k1_execution_must_match_explicit_q13_decision() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    first = next(iter(lineage.values()))["q13-a"][0]
    first["candidate_k1_executed_actions"][1] = 4
    result = mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    assert result["gates"]["G-M"]["passed"] is False


def test_missing_explicit_q13_action_vector_has_no_executed_fallback() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    del next(iter(lineage.values()))["q13-a"][0]["candidate_k1_q13_actions"]
    result = mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    assert result["gates"]["G-M"]["passed"] is False


def test_reference_trace_evidence_is_mandatory_and_digest_bound() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    result = mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    del result["controls"][0]["oracle_reference_trace"]
    assert mod.adjudicate_gates(result["rows"], result["controls"])["G-M"]["passed"] is False


def test_adjudicator_recomputes_k1_execution_equality() -> None:
    prepare = mod.build_prepare(
        _worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
        source_manifest_sha256="a" * 64,
        simulator_prereg_file_sha256="d" * 64,
        t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"])
                for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    result = mod.generate(
        prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    row = result["rows"][0]
    row["reference_k1_executed_actions"] = [4, 4]
    row["candidate_k1_executed_actions"] = [4, 4]
    row["k1_executed_matches"] = True
    assert mod.adjudicate_gates(
        result["rows"], result["controls"])["G-M"]["passed"] is False

    truncated = mod.generate(
        prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    for field in ("reference_k1_executed_actions",
                  "candidate_k1_executed_actions",
                  "reference_k1_q13_actions",
                  "candidate_k1_q13_actions"):
        truncated["rows"][0][field] = truncated["rows"][0][field][:1]
    truncated["rows"][0]["k1_executed_matches"] = True
    assert mod.adjudicate_gates(
        truncated["rows"], truncated["controls"])["G-M"]["passed"] is False

    co_tampered = mod.generate(
        prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    co_tampered["rows"][0]["reference_k1_executed_actions"][1] = 4
    co_tampered["rows"][0]["reference_k1_q13_actions"][1] = 4
    assert mod.adjudicate_gates(
        co_tampered["rows"], co_tampered["controls"])["G-M"]["passed"] is False


def test_recomputed_q13_actions_accept_noop_only_for_empty_mask() -> None:
    assert mod._recompute_k1_q13_actions(
        [[0.0] * NUM_ACTIONS, [1.0] * NUM_ACTIONS],
        [[False] * NUM_ACTIONS, [True] * NUM_ACTIONS],
        users=2, field="test") == [-1, 0]


def test_nonfocal_k0_change_is_a_red_mechanics_gate() -> None:
    prepare = mod.build_prepare(
        _worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
        source_manifest_sha256="a" * 64,
        simulator_prereg_file_sha256="d" * 64,
        t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"])
                for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    result = mod.generate(
        prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    result["rows"][0]["candidate_k0_executed_actions"][1] = 1
    assert mod.adjudicate_gates(
        result["rows"], result["controls"])["G-M"]["passed"] is False


def test_adjudicator_recomputes_arm_metrics_from_digest_bound_traces() -> None:
    prepare = mod.build_prepare(
        _worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
        source_manifest_sha256="a" * 64,
        simulator_prereg_file_sha256="d" * 64,
        t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"])
                for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    clean = mod.generate(
        prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    assert "oracle_trace" in clean["controls"][0]
    assert "drop_trace_sha256" in clean["controls"][0]

    metric_tamper = copy.deepcopy(clean)
    metric_tamper["controls"][0]["oracle_metrics"]["total_bits"] *= 3.0
    gates = mod.adjudicate_gates(
        metric_tamper["rows"], metric_tamper["controls"])
    assert gates["G-M"]["passed"] is False
    assert gates["G-E"]["pooled_oracle_gt_drop"] is True

    digest_tamper = copy.deepcopy(clean)
    digest_tamper["controls"][0]["oracle_trace"]["rates_bps"][0][0] += 1.0
    assert mod.adjudicate_gates(
        digest_tamper["rows"], digest_tamper["controls"])["G-M"]["passed"] is False

    truncated = copy.deepcopy(clean)
    truncated["controls"][0]["oracle_trace"]["rates_bps"] = \
        truncated["controls"][0]["oracle_trace"]["rates_bps"][:2]
    truncated["controls"][0]["oracle_trace"]["power_w"] = \
        truncated["controls"][0]["oracle_trace"]["power_w"][:2]
    truncated["controls"][0]["oracle_trace"]["served"] = \
        truncated["controls"][0]["oracle_trace"]["served"][:2]
    truncated["controls"][0]["oracle_trace_sha256"] = mod.canonical_sha256(
        truncated["controls"][0]["oracle_trace"])
    assert mod.adjudicate_gates(
        truncated["rows"], truncated["controls"])["G-M"]["passed"] is False

    user_truncated = copy.deepcopy(clean)
    arm = user_truncated["controls"][0]["drop_trace"]
    arm["rates_bps"] = [offset[:1] for offset in arm["rates_bps"]]
    arm["served"] = [offset[:1] for offset in arm["served"]]
    arm["actions"] = [offset[:1] for offset in arm["actions"]]
    user_truncated["controls"][0]["drop_trace_sha256"] = mod.canonical_sha256(arm)
    user_truncated["controls"][0]["drop_metrics"] = mod.selected_continuation_metrics(
        {"drop_rates_bps": arm["rates_bps"],
         "drop_power_w": arm["power_w"],
         "drop_served": arm["served"]}, policy="drop", interval_s=1.0)
    assert mod.adjudicate_gates(
        user_truncated["rows"], user_truncated["controls"])["G-M"]["passed"] is False

    interval_tamper = copy.deepcopy(clean)
    interval_tamper["controls"][0]["interval_s"] = 999.0
    for policy in ("oracle", "drop"):
        trace = interval_tamper["controls"][0][f"{policy}_trace"]
        interval_tamper["controls"][0][f"{policy}_metrics"] = \
            mod.selected_continuation_metrics(
                {f"{policy}_rates_bps": trace["rates_bps"],
                 f"{policy}_power_w": trace["power_w"],
                 f"{policy}_served": trace["served"]},
                policy=policy, interval_s=999.0)
        ref = interval_tamper["controls"][0][f"{policy}_reference_trace"]
        interval_tamper["controls"][0][f"{policy}_reference_metrics"] = \
            mod.selected_continuation_metrics(
                {f"{policy}_rates_bps": ref["rates_bps"],
                 f"{policy}_power_w": ref["power_w"],
                 f"{policy}_served": ref["served"]},
                policy=policy, interval_s=999.0)
    assert mod.adjudicate_gates(
        interval_tamper["rows"], interval_tamper["controls"],
        expected_interval_s=1.0)["G-M"]["passed"] is False


def test_formal_policy_actions_are_rederived_from_prepare_and_28_targets(
        tmp_path: Path) -> None:
    generic = mod.build_prepare(
        _worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
        source_manifest_sha256="a" * 64,
        simulator_prereg_file_sha256="d" * 64,
        t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(generic["policy_sha256"])
                for name in mod.LINEAGES}
               for a in generic["anchors"]}
    generated = mod.generate(
        generic, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    live_prepare = _valid_live_prepare(tmp_path)
    q13 = [0.0] * NUM_ACTIONS
    q13[2] = 2.0
    for cell in live_prepare["lineage_bindings"].values():
        for binding in cell.values():
            binding["q13_score_vector"] = list(q13)
            binding["a_D"] = 2
    mod._validate_formal_policy_actions(
        generated["rows"], generated["controls"], live_prepare)
    tampered = copy.deepcopy(generated["controls"])
    tampered[0]["oracle_action"] = 6
    tampered[0]["oracle_drop_tie"] = False
    tampered[0]["tie_trace_reused"] = False
    with pytest.raises(mod.T1RunnerError, match="a_D/a_O"):
        mod._validate_formal_policy_actions(
            generated["rows"], tampered, live_prepare)


def test_generate_rejects_tampered_prepare_hash() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    prepare["anchors"] = []
    with pytest.raises(mod.T1RunnerError, match="prepare hash"):
        mod.generate(prepare, {}, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)


def test_prepare_live_generate_rejects_nonfrozen_constants() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64,
                                t1_prereg_file_sha256="e" * 64)
    body = dict(prepare)
    body.pop("prepare_sha256")
    body["schema"] = mod.PREPARE_LIVE_SCHEMA
    body["formula_contract"] = mod.T1_FORMULA_CONTRACT
    body["gate_contract"] = mod.T1_GATE_CONTRACT
    body["code_authority"] = mod._code_authority_manifest()
    live_prepare = body | {"prepare_sha256": mod.canonical_sha256(body)}
    with pytest.raises(mod.T1RunnerError, match="constants"):
        mod.generate(live_prepare, {}, interval_s=1.,
                     lambda_bits_per_j=mod.LAMBDA_BITS_PER_J,
                     kappa_bits=mod.KAPPA_BITS)


def test_prepare_live_code_authority_binds_frozen_server_launcher() -> None:
    authority = mod._code_authority_manifest()
    launcher = ROOT / ".scratch" / "c3-v04" / "launch_v06_c2_k1_t1_server.sh"
    assert authority["files"]["server_launcher"] == hashlib.sha256(
        launcher.read_bytes()).hexdigest()
    prereg = (ROOT / "docs" /
              "MULTI-CATFISH-MCRL-V06-C2-K1-T1-PREREG-2026-09-01.md").read_text()
    assert "will be inserted" not in prereg
    assert "launch_v06_c2_k1_t1_server.sh shard q13-a" in prereg
    assert "exactly one attempt" in prereg


def test_source_digest_rejects_gate_tamper() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    result = mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    result["gates"]["G-S"]["passed"] = False
    assert result["source_sha256"] != mod._source_payload_sha256(result)


def test_crn_drift_is_a_red_mechanics_gate() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    result = mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    result["rows"][0]["crn_sha256"] = "d" * 64
    gates = mod.adjudicate_gates(result["rows"], result["controls"])
    assert gates["G-M"]["passed"] is False


def test_crn_must_be_shared_across_lineages_for_each_physical_world() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    result = mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    # Change only q13-b in one physical world; this is not an admissible new CRN.
    anchor_key = f"{prepare['anchors'][0]['pool']}:{prepare['anchors'][0]['world_id']}:{prepare['anchors'][0]['step']}:{prepare['anchors'][0]['focal_user']}"
    for row in result["rows"]:
        if row["anchor"]["world_id"] == prepare["anchors"][0]["world_id"] and row["lineage"] == "q13-b":
            row["crn_sha256"] = "d" * 64
    assert mod.adjudicate_gates(result["rows"], result["controls"])["G-M"]["passed"] is False


def test_main_gauge_array_tamper_is_a_red_mechanics_gate() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    result = mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    result["rows"][0]["main_gauge_candidate_rates_k1"][0] = 99.0
    assert mod.adjudicate_gates(result["rows"], result["controls"])["G-M"]["passed"] is False


def test_launchable_requires_lineage_and_world_ee_quotas() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    result = mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)
    # Preserve pooled oracle > DROP while leaving only one positive lineage
    # and seven positive worlds.  The hard launch gate must still stop.
    positive_worlds = {a["world_id"] for a in prepare["anchors"][:7]}
    for control in result["controls"]:
        world = int(control["anchor"]["world_id"])
        keep = control["lineage"] == "q13-c" and world in positive_worlds
        if not keep:
            control["oracle_trace"] = copy.deepcopy(control["drop_trace"])
            control["oracle_trace_sha256"] = mod.canonical_sha256(
                control["oracle_trace"])
            control["oracle_metrics"] = mod.selected_continuation_metrics(
                {"oracle_rates_bps": control["oracle_trace"]["rates_bps"],
                 "oracle_power_w": control["oracle_trace"]["power_w"],
                 "oracle_served": control["oracle_trace"]["served"]},
                policy="oracle", interval_s=1.0)
    gates = mod.adjudicate_gates(result["rows"], result["controls"])
    assert gates["G-E"]["pooled_oracle_gt_drop"] is True
    assert gates["G-E"]["positive_lineages"] == 1
    assert gates["G-E"]["positive_worlds"] == 7
    assert gates["launchable"] is False


def test_prepare_live_binds_per_lineage_scores_a_d_and_shared_crn() -> None:
    anchors = []
    bindings = {}
    for pool, start, steps in (("early", 2026101001, 1), ("mid", 2026101011, 3), ("late", 2026101021, 5)):
        for world in range(start, start + 4):
            anchor = {"pool": pool, "world_id": world, "step": steps, "focal_user": 0,
                      "reference_action": 2, "physical_main_departure": True,
                      "complete_forecast_horizon": True, "complete_28_action_census": True,
                      "alias_absence": True, "world_anchor_sha256": "1" * 64,
                      "anchor_sha256": "2" * 64, "reference_physical_key": [1, 2],
                      "incumbent_physical_key": [3, 4], "legal_action_mask": [True] * NUM_ACTIONS,
                      "candidate_actions": [a for a in range(NUM_ACTIONS) if a != 2],
                      "candidate_physical_keys": [[a, 5] for a in range(NUM_ACTIONS) if a != 2],
                      "checkpoint_sha256": "3" * 64, "source_manifest_sha256": "e" * 64,
                      "policy_sha256": "5" * 64, "evaluation_seed": world}
            anchors.append(anchor)
            key = f"{pool}:{world}:{steps}:0"
            bindings[key] = {lineage: {"q1_sha256": "a" * 64, "q3_sha256": "b" * 64,
                                       "hybrid_sha256": chr(99 + i) * 64,
                                       "initialization_seed": i + 1, "crn_sha256": "d" * 64,
                                       "q13_score_vector": [0.0] * NUM_ACTIONS, "a_D": 0}
                                      for i, lineage in enumerate(mod.LINEAGES)}
    payload = mod.build_prepare_live(anchors, lineage_bindings=bindings,
                                     simulator_source_manifest_sha256="e" * 64,
                                     q13_gate_source_manifest_sha256="9" * 64,
                                     simulator_prereg_file_sha256="f" * 64,
                                     t1_prereg_file_sha256="0" * 64)
    assert payload["schema"] == mod.PREPARE_LIVE_SCHEMA
    assert len(payload["lineage_bindings"]) == 12
    assert all(len(cell) == 3 for cell in payload["lineage_bindings"].values())


def test_prepare_live_rejects_a_d_that_is_not_lowest_index_argmax() -> None:
    anchors = []
    bindings = {}
    for pool, start, step in (("early", 2026101001, 1), ("mid", 2026101011, 3), ("late", 2026101021, 5)):
        for world in range(start, start + 4):
            anchor = {"pool": pool, "world_id": world, "step": step, "focal_user": 0,
                      "reference_action": 2, "physical_main_departure": True,
                      "complete_forecast_horizon": True, "complete_28_action_census": True,
                      "alias_absence": True, "world_anchor_sha256": "1" * 64,
                      "anchor_sha256": "2" * 64, "reference_physical_key": [1, 2],
                      "incumbent_physical_key": [3, 4], "legal_action_mask": [True] * NUM_ACTIONS,
                      "candidate_actions": [a for a in range(NUM_ACTIONS) if a != 2],
                      "candidate_physical_keys": [[a, 5] for a in range(NUM_ACTIONS) if a != 2],
                      "checkpoint_sha256": "3" * 64, "source_manifest_sha256": "e" * 64,
                      "policy_sha256": "5" * 64, "evaluation_seed": world}
            anchors.append(anchor)
            key = f"{pool}:{world}:{step}:0"
            bindings[key] = {lineage: {"q1_sha256": "a" * 64, "q3_sha256": "b" * 64,
                                       "hybrid_sha256": "c" * 64, "initialization_seed": i + 1,
                                       "crn_sha256": "d" * 64,
                                       "q13_score_vector": [0.0] * NUM_ACTIONS, "a_D": 2}
                                      for i, lineage in enumerate(mod.LINEAGES)}
    with pytest.raises(mod.T1RunnerError, match="argmax"):
        mod.build_prepare_live(anchors, lineage_bindings=bindings,
                               simulator_source_manifest_sha256="e" * 64,
                               q13_gate_source_manifest_sha256="9" * 64,
                               simulator_prereg_file_sha256="f" * 64,
                               t1_prereg_file_sha256="0" * 64)


def test_v06_scanner_wrapper_lowers_only_minimum_focal_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = []
    class Backend:
        def _main_decision(self, _trainer, _wrapped, _states, _masks, observation, _rng):
            observed.append(("main", observation.step_index))
            return (), ()
    class Pair:
        def _departure_users(self, _wrapped, _main_physical):
            return (1, 2)
    class Support:
        FOCAL_USERS_PER_WORLD = 4
        def _real_seed_topology(self, **kwargs):
            assert self.FOCAL_USERS_PER_WORLD == 1
            for step in (1, 3):
                observation = type("Observation", (), {"step_index": step})()
                kwargs["modules"]["backend_smoke"]._main_decision(
                    None, None, None, None, observation, None)
                departures = kwargs["modules"]["pair_smoke"]._departure_users(None, None)
                observed.append(("departures", step, departures))
            return ("one",)
    support = Support()
    assert mod._v06_real_seed_topology(support=support, source_seed=1,
                                       modules={"backend_smoke": Backend(), "pair_smoke": Pair()}, context={},
                                       eligible_steps=(3, 4)) == ("one",)
    assert support.FOCAL_USERS_PER_WORLD == 4
    assert observed == [
        ("main", 1), ("departures", 1, ()),
        ("main", 3), ("departures", 3, (1, 2)),
    ]


def test_v06_scanner_field_injection_restores_loader_and_preserves_root() -> None:
    calls = []
    class Wrapped:
        environment = type("Env", (), {})()
    class Loader:
        def _make_environment(self, _archive, *, users):
            calls.append(("original", users))
            return Wrapped()
    class Support:
        FOCAL_USERS_PER_WORLD = 4
        def _real_seed_topology(self, **_kwargs):
            wrapped = _kwargs["modules"]["loader"]._make_environment(object(), users=1)
            assert wrapped.environment._fading_field is field
            assert self.FOCAL_USERS_PER_WORLD == 1
            return ()
    support = Support(); loader = Loader(); field = object()
    original = loader._make_environment.__func__
    mod._v06_real_seed_topology(support=support, source_seed=1,
                                modules={"loader": loader}, context={}, field=field)
    assert loader._make_environment.__func__ is original
    assert calls == [("original", 1)]


def test_prepare_live_main_dir_must_bind_checkpoint_digest(tmp_path: Path) -> None:
    anchors = []
    bindings = {}
    for pool, start, step in (("early", 2026101001, 1), ("mid", 2026101011, 3), ("late", 2026101021, 5)):
        for world in range(start, start + 4):
            anchors.append({"pool": pool, "world_id": world, "step": step, "focal_user": 0,
                            "physical_main_departure": True, "complete_forecast_horizon": True,
                            "complete_28_action_census": True, "alias_absence": True,
                            "reference_action": 2, "world_anchor_sha256": "1" * 64,
                            "anchor_sha256": "2" * 64, "reference_physical_key": [1, 2],
                            "incumbent_physical_key": [3, 4], "legal_action_mask": [True] * NUM_ACTIONS,
                            "candidate_actions": [a for a in range(NUM_ACTIONS) if a != 2],
                            "candidate_physical_keys": [[a, 5] for a in range(NUM_ACTIONS) if a != 2],
                            "checkpoint_sha256": "3" * 64, "source_manifest_sha256": "e" * 64,
                            "policy_sha256": "5" * 64, "evaluation_seed": world})
            key = f"{pool}:{world}:{step}:0"
            bindings[key] = {lineage: {"q1_sha256": "a" * 64, "q3_sha256": "b" * 64,
                                       "hybrid_sha256": "c" * 64, "initialization_seed": i + 1,
                                       "crn_sha256": "d" * 64, "q13_score_vector": [1.0] + [0.0] * (NUM_ACTIONS - 1),
                                       "a_D": 0}
                                      for i, lineage in enumerate(mod.LINEAGES)}
    with pytest.raises(mod.T1RunnerError, match="checkpoint digest"):
        mod.build_prepare_live(anchors, lineage_bindings=bindings,
                               simulator_source_manifest_sha256="e" * 64,
                               q13_gate_source_manifest_sha256="9" * 64,
                               simulator_prereg_file_sha256="f" * 64,
                               t1_prereg_file_sha256="0" * 64,
                               main_dir=tmp_path)


def test_authenticated_main_dir_rejects_legacy_default_mismatch(tmp_path: Path) -> None:
    class Legacy:
        BASE_CHECKPOINT_DIR = tmp_path / "legacy-main"
    with pytest.raises(mod.T1RunnerError, match="does not match"):
        mod._authenticated_main_dir({"legacy_source": Legacy()}, tmp_path / "cli-main")


def test_formal_merge_rejects_generic_materializer_and_mixed_prepare(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(mod.T1RunnerError, match="PREPARE_LIVE"):
        mod.merge_sources([{}], {"schema": mod.PREPARE_SCHEMA})
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64,
                                t1_prereg_file_sha256="e" * 64)
    lineage_payload = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
                       {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
                       for a in prepare["anchors"]}
    monkeypatch.setattr(mod, "USER_COUNT", 2)
    generated = mod.generate(
        prepare, lineage_payload,
        interval_s=float(mod.T1_FORMULA_CONTRACT["interval_s"]),
        lambda_bits_per_j=mod.LAMBDA_BITS_PER_J,
        kappa_bits=mod.KAPPA_BITS)
    prepare_sha = prepare["prepare_sha256"]
    fake_prepare = dict(prepare)
    fake_prepare["code_authority"] = {
        "files": {"live_adapter": "f" * 64}, "sha256": "e" * 64}
    anchor_map = {mod._anchor_key(anchor): anchor for anchor in prepare["anchors"]}
    monkeypatch.setattr(mod, "_validate_live_prepare_for_merge", lambda _payload: prepare_sha)
    monkeypatch.setattr(mod, "_sealed_anchor_map", lambda _payload: anchor_map)
    monkeypatch.setattr(mod, "_validate_formal_policy_actions", lambda *_args: None)

    shards = []
    for lineage in mod.LINEAGES:
        rows = [row for row in generated["rows"] if row["lineage"] == lineage]
        controls = [control for control in generated["controls"] if control["lineage"] == lineage]
        gates = mod.adjudicate_gates(rows, controls,
                                     expected_pairs=12 * NUM_ACTIONS,
                                     expected_controls=12, expected_users=2,
                                     expected_interval_s=float(mod.T1_FORMULA_CONTRACT["interval_s"]),
                                     expected_lambda_bits_per_j=mod.LAMBDA_BITS_PER_J,
                                     expected_kappa_bits=mod.KAPPA_BITS)
        shard = {"schema": mod.SOURCE_SCHEMA, "algorithm_schema": mod.SCHEMA,
                 "source_rule": mod.SOURCE_RULE, "claim_ceiling": mod.CLAIM_CEILING,
                 "prepare_sha256": prepare_sha,
                 "materializer": "authenticated-v06-live-adapter",
                 "materialized_lineage": lineage, "materialized_lineages": [lineage],
                 "materializer_code_sha256": "f" * 64,
                 "rows": rows, "controls": controls, "gates": gates,
                 "counts": {"anchors": 12, "lineages": 1,
                            "opening_actions": NUM_ACTIONS, "pairs": len(rows),
                            "controls": len(controls)},
                 "training": False, "test_split_opened": False,
                 "outcome_selection": False, "q2_consulted": False}
        shard["source_sha256"] = mod._source_payload_sha256(shard)
        shards.append(shard)

    merged = mod.merge_sources(shards, fake_prepare)
    assert merged["counts"]["pairs"] == 1008
    assert merged["counts"]["controls"] == 36

    generic = copy.deepcopy(shards)
    generic[0]["materializer"] = "generic-explicit-input"
    generic[0]["source_sha256"] = mod._source_payload_sha256(generic[0])
    with pytest.raises(mod.T1RunnerError, match="generic|unauthenticated"):
        mod.merge_sources(generic, fake_prepare)

    mixed = copy.deepcopy(shards)
    mixed[0]["prepare_sha256"] = "b" * 64
    mixed[0]["source_sha256"] = mod._source_payload_sha256(mixed[0])
    with pytest.raises(mod.T1RunnerError, match="bound"):
        mod.merge_sources(mixed, fake_prepare)

    out_of_pool = copy.deepcopy(shards)
    for row in out_of_pool[2]["rows"]:
        row["anchor"]["world_id"] += 100000
    for control in out_of_pool[2]["controls"]:
        control["anchor"]["world_id"] += 100000
    out_of_pool[2]["gates"] = mod.adjudicate_gates(
        out_of_pool[2]["rows"], out_of_pool[2]["controls"],
        expected_pairs=12 * NUM_ACTIONS, expected_controls=12,
        expected_users=2,
        expected_interval_s=float(mod.T1_FORMULA_CONTRACT["interval_s"]),
        expected_lambda_bits_per_j=mod.LAMBDA_BITS_PER_J,
        expected_kappa_bits=mod.KAPPA_BITS)
    out_of_pool[2]["source_sha256"] = mod._source_payload_sha256(out_of_pool[2])
    with pytest.raises(mod.T1RunnerError, match="anchor"):
        mod.merge_sources(out_of_pool, fake_prepare)


def test_cli_parser_builds_without_argument_conflicts(capsys: pytest.CaptureFixture[str]) -> None:
    assert mod._main(["help-contract"]) == 0
    assert '"expected_pairs": 1008' in capsys.readouterr().out


def test_real_support_loader_registers_module_before_dataclass_exec() -> None:
    support = mod._support_census_loader()
    assert support.C2V04TopologyAnchor.__module__ in sys.modules
    assert support.C2V04TopologyFocal.__module__ in sys.modules


def test_real_phase_b_loader_is_defined_and_registered_before_exec() -> None:
    phase_b = mod._phase_b_loader()
    assert tuple(phase_b.Q13_INIT_SEEDS)
    assert phase_b.__name__ in sys.modules


def test_prepare_live_function_resolves_phase_b_loader_before_scan(monkeypatch: pytest.MonkeyPatch,
                                                                    tmp_path: Path) -> None:
    called = []
    class Legacy:
        BASE_CHECKPOINT_DIR = tmp_path / "main"
    class Support:
        FOCAL_USERS_PER_WORLD = 4
        def _production_modules(self):
            return {"legacy_source": Legacy()}
        def _production_main_context(self, **_kwargs):
            return {"checkpoint_sha256": "a" * 64, "source_manifest_sha256": "b" * 64}
    class PhaseB:
        Q13_INIT_SEEDS = mod.Q13_INITIALIZATION_SEEDS
        def _authenticate_q13_gate(self, *_args, **_kwargs):
            called.append("phase-b")
            return {"source_manifest_sha256": "d" * 64,
                    "selected_hybrid_file_sha256": {str(seed): "c" * 64
                    for seed in self.Q13_INIT_SEEDS}}
    monkeypatch.setattr(mod, "_support_census_loader", lambda: Support())
    monkeypatch.setattr(mod, "_phase_b_loader", lambda: PhaseB())
    monkeypatch.setattr(mod, "_authenticated_main_dir", lambda _modules, requested: requested.resolve())
    monkeypatch.setattr(mod, "_v06_real_seed_topology", lambda **_kwargs: ())
    (tmp_path / "sim.json").write_bytes(b"sim")
    (tmp_path / "t1.md").write_bytes(b"t1")
    with pytest.raises(mod.T1RunnerError, match="found only 0"):
        mod._production_prepare_live(
            tle_root=tmp_path / "tle", simulator_prereg=tmp_path / "sim.json",
            t1_prereg=tmp_path / "t1.md", main_dir=tmp_path / "main",
            lineage_bindings_path=None, output_dir=tmp_path / "out",
            gate_dir=tmp_path / "gate", source_dir=tmp_path / "source",
            v03_root=tmp_path / "v03")
    assert called == ["phase-b"]


def test_generate_missing_continuation_fails_with_action_context() -> None:
    prepare = mod.build_prepare(_worlds(), q1_bytes=b"q1", q3_bytes=b"q3", mask_bytes=b"m",
                                source_manifest_sha256="a" * 64,
                                simulator_prereg_file_sha256="d" * 64, t1_prereg_file_sha256="e" * 64)
    key = f"{prepare['anchors'][0]['pool']}:{prepare['anchors'][0]['world_id']}:{prepare['anchors'][0]['step']}:{prepare['anchors'][0]['focal_user']}"
    lineage = {f"{a['pool']}:{a['world_id']}:{a['step']}:{a['focal_user']}":
               {name: _lineage_rows(prepare["policy_sha256"]) for name in mod.LINEAGES}
               for a in prepare["anchors"]}
    del lineage[key]["q13-a"][7]["oracle_rates_bps"]
    with pytest.raises(mod.T1RunnerError, match=r"q13-a/\d+ lacks the oracle"):
        mod.generate(prepare, lineage, interval_s=1., lambda_bits_per_j=1., kappa_bits=10.)


def test_live_prepare_v2_accepts_distinct_simulator_and_q13_manifests(
        tmp_path: Path) -> None:
    prepare = _valid_live_prepare(tmp_path)
    assert prepare["simulator_source_manifest_sha256"] == "e" * 64
    assert prepare["q13_gate_source_manifest_sha256"] == "9" * 64
    assert prepare["simulator_source_manifest_sha256"] != prepare["q13_gate_source_manifest_sha256"]
    assert all(anchor["simulator_source_manifest_sha256"] == "e" * 64
               for anchor in prepare["anchors"])
    assert mod._validate_live_prepare_for_merge(prepare) == prepare["prepare_sha256"]


def test_live_prepare_v2_rejects_v1_and_manifest_tampering(tmp_path: Path) -> None:
    prepare = _valid_live_prepare(tmp_path)
    v1 = copy.deepcopy(prepare)
    v1["schema"] = "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-v1"
    unsigned = dict(v1); unsigned.pop("prepare_sha256")
    v1["prepare_sha256"] = mod.canonical_sha256(unsigned)
    with pytest.raises(mod.T1RunnerError, match="PREPARE_LIVE_SCHEMA"):
        mod._validate_live_prepare_for_merge(v1)

    tampered = copy.deepcopy(prepare)
    tampered["q13_gate_source_manifest_sha256"] = "8" * 64
    with pytest.raises(mod.T1RunnerError, match="digest"):
        mod._validate_live_prepare_for_merge(tampered)

    anchor_drift = copy.deepcopy(prepare)
    anchor_drift["anchors"][0]["simulator_source_manifest_sha256"] = "7" * 64
    unsigned = dict(anchor_drift); unsigned.pop("prepare_sha256")
    anchor_drift["prepare_sha256"] = mod.canonical_sha256(unsigned)
    with pytest.raises(mod.T1RunnerError, match="authority fields"):
        mod._validate_live_prepare_for_merge(anchor_drift)

    outcome_tamper = copy.deepcopy(prepare)
    outcome_tamper["outcome_selection"] = True
    unsigned = dict(outcome_tamper); unsigned.pop("prepare_sha256")
    outcome_tamper["prepare_sha256"] = mod.canonical_sha256(unsigned)
    with pytest.raises(mod.T1RunnerError, match="target-free"):
        mod._validate_live_prepare_for_merge(outcome_tamper)

    extra = copy.deepcopy(prepare)
    extra["outcomes"] = {"pooled_ee": 1.0}
    unsigned = dict(extra); unsigned.pop("prepare_sha256")
    extra["prepare_sha256"] = mod.canonical_sha256(unsigned)
    with pytest.raises(mod.T1RunnerError, match="top-level schema"):
        mod._validate_live_prepare_for_merge(extra)


def test_formal_prepare_reads_exact_seal_and_current_prereg(tmp_path: Path) -> None:
    prereg = tmp_path / "t1.md"
    prereg.write_bytes(b"frozen-prereg")
    prepare = _valid_live_prepare(
        tmp_path,
        t1_prereg_sha256=hashlib.sha256(prereg.read_bytes()).hexdigest())
    root = tmp_path / "prepare-live"
    root.mkdir()
    prepare_path = root / "prepare-live.json"
    prepare_path.write_bytes(canonical_bytes(prepare))
    seal = {
        "schema": "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-seal-v2",
        "prepare_sha256": prepare["prepare_sha256"],
        "prepare_file_sha256": hashlib.sha256(
            prepare_path.read_bytes()).hexdigest(),
        "training": False, "test_split_opened": False,
        "outcome_selection": False,
    }
    (root / "prepare-live-seal.json").write_bytes(canonical_bytes(seal))
    assert mod._read_formal_prepare(prepare_path, prereg) == prepare

    prereg.write_bytes(b"changed-after-prepare")
    with pytest.raises(mod.T1RunnerError, match="current T1 prereg"):
        mod._read_formal_prepare(prepare_path, prereg)


@pytest.mark.parametrize("command", ("merge", "verify"))
def test_cli_authenticates_prepare_before_opening_outcome_files(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, command: str) -> None:
    opened = []
    monkeypatch.setattr(
        mod, "_read_formal_prepare",
        lambda *_args: (_ for _ in ()).throw(
            mod.T1RunnerError("formal prepare blocked")))
    monkeypatch.setattr(
        mod, "_canonical_read",
        lambda path: opened.append(Path(path)) or {})
    common = ["--prepare", str(tmp_path / "prepare-live.json"),
              "--t1-prereg", str(tmp_path / "t1.md")]
    argv = (["merge", "--shards", str(tmp_path / "a.json"),
             "--output-dir", str(tmp_path / "merged"), *common]
            if command == "merge" else
            ["verify", "--source", str(tmp_path / "source.json"), *common])
    assert mod._main(argv) == 2
    assert opened == []


def test_live_shard_rejects_self_digested_24_anchor_prepare_before_runtime(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prepare = _valid_live_prepare(tmp_path)
    prepare["anchors"] = copy.deepcopy(prepare["anchors"] + prepare["anchors"])
    unsigned = dict(prepare); unsigned.pop("prepare_sha256")
    prepare["prepare_sha256"] = mod.canonical_sha256(unsigned)
    prepare_path = tmp_path / "fake-24.json"
    prepare_path.write_bytes(canonical_bytes(prepare))
    touched = []
    monkeypatch.setattr(
        mod, "_support_census_loader",
        lambda: touched.append("runtime-opened") or (_ for _ in ()).throw(
            AssertionError("runtime must not open")))
    with pytest.raises(mod.T1RunnerError, match="exactly 12 anchors"):
        mod._production_shard_live(
            prepare_path=prepare_path, tle_root=tmp_path / "tle",
            prereg=tmp_path / "sim.json", main_dir=tmp_path / "main",
            gate_dir=tmp_path / "gate", source_dir=tmp_path / "source",
            v03_root=tmp_path / "v03", lineage="q13-a",
            output=tmp_path / "out.json")
    assert touched == []


def test_live_shard_authenticates_distinct_manifest_namespaces_before_replay(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prereg = tmp_path / "sim.json"
    prereg.write_bytes(b"simulator-prereg")
    prepare = _valid_live_prepare(
        tmp_path,
        simulator_prereg_sha256=hashlib.sha256(prereg.read_bytes()).hexdigest())
    prepare_path = tmp_path / "prepare-v2.json"
    prepare_path.write_bytes(canonical_bytes(prepare))
    calls = []

    class ReachedReplay(RuntimeError):
        pass

    class Support:
        def _production_modules(self):
            return {}

        def _production_source_manifest(self, _modules):
            calls.append("simulator-manifest")
            return {"source_manifest_sha256": "e" * 64}

    class Runtime:
        checkpoint_sha256 = "3" * 64
        q13_gate_source_manifest_sha256 = "9" * 64
        archive = object()
        trainer = object()
        hybrid_hashes = {lineage: chr(99 + index) * 64
                         for index, lineage in enumerate(mod.LINEAGES)}

    class Live:
        @staticmethod
        @contextmanager
        def authenticated_runtime(**_kwargs):
            calls.append("q13-runtime")
            yield Runtime()

        @staticmethod
        def replay_main_to_anchor(*_args, **_kwargs):
            calls.append("anchor-replay")
            raise ReachedReplay

    monkeypatch.setattr(mod, "_support_census_loader", lambda: Support())
    monkeypatch.setattr(mod, "_authenticated_main_dir",
                        lambda _modules, requested: requested.resolve())
    monkeypatch.setattr(mod, "_live_adapter_loader", lambda: Live())

    with pytest.raises(ReachedReplay):
        mod._production_shard_live(
            prepare_path=prepare_path, tle_root=tmp_path / "tle", prereg=prereg,
            main_dir=tmp_path / "main", gate_dir=tmp_path / "gate",
            source_dir=tmp_path / "source", v03_root=tmp_path / "v03",
            lineage="q13-a", output=tmp_path / "out.json")
    assert calls == ["simulator-manifest", "q13-runtime", "anchor-replay"]

    calls.clear()
    Runtime.q13_gate_source_manifest_sha256 = "8" * 64
    with pytest.raises(mod.T1RunnerError, match="Q13 source manifest"):
        mod._production_shard_live(
            prepare_path=prepare_path, tle_root=tmp_path / "tle", prereg=prereg,
            main_dir=tmp_path / "main", gate_dir=tmp_path / "gate",
            source_dir=tmp_path / "source", v03_root=tmp_path / "v03",
            lineage="q13-a", output=tmp_path / "out.json")
    assert calls == ["simulator-manifest", "q13-runtime"]

    class WrongSimulatorSupport(Support):
        def _production_source_manifest(self, _modules):
            calls.append("simulator-manifest")
            return {"source_manifest_sha256": "7" * 64}

    calls.clear()
    Runtime.q13_gate_source_manifest_sha256 = "9" * 64
    monkeypatch.setattr(mod, "_support_census_loader",
                        lambda: WrongSimulatorSupport())
    with pytest.raises(mod.T1RunnerError, match="simulator source manifest"):
        mod._production_shard_live(
            prepare_path=prepare_path, tle_root=tmp_path / "tle", prereg=prereg,
            main_dir=tmp_path / "main", gate_dir=tmp_path / "gate",
            source_dir=tmp_path / "source", v03_root=tmp_path / "v03",
            lineage="q13-a", output=tmp_path / "out.json")
    assert calls == ["simulator-manifest"]


def test_live_binding_producer_rejects_q13_manifest_before_replay(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = []

    class Runtime:
        checkpoint_sha256 = "3" * 64
        q13_gate_source_manifest_sha256 = "8" * 64

    class Live:
        @staticmethod
        @contextmanager
        def authenticated_runtime(**_kwargs):
            calls.append("runtime")
            yield Runtime()

        @staticmethod
        def replay_main_to_anchor(*_args, **_kwargs):
            calls.append("replay")
            raise AssertionError("replay must not open")

    monkeypatch.setattr(mod, "_live_adapter_loader", lambda: Live())
    with pytest.raises(mod.T1RunnerError, match="producer Q13 source manifest"):
        mod._produce_live_lineage_bindings(
            selected=[], tle_root=tmp_path / "tle",
            simulator_prereg=tmp_path / "sim", main_dir=tmp_path / "main",
            gate_dir=tmp_path / "gate", source_dir=tmp_path / "source",
            v03_root=tmp_path / "v03", checkpoint_sha256="3" * 64,
            simulator_source_manifest_sha256="e" * 64,
            q13_gate_source_manifest_sha256="9" * 64,
            simulator_prereg_file_sha256="f" * 64)
    assert calls == ["runtime"]
