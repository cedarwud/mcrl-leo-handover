#!/usr/bin/env python3
"""Fail closed on a frozen v4 ARLP shadow-gate receipt."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import run_arlp_shadow_gate as gate  # noqa: E402
import run_oracle_gate as v1  # noqa: E402


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--expect-stage", choices=("pilot", "confirmation"), required=True)
    return parser.parse_args()


def _assert_close(
    left: float,
    right: float,
    name: str,
    *,
    rel_tol: float = 1e-12,
    abs_tol: float = 1e-9,
) -> None:
    if not math.isclose(float(left), float(right), rel_tol=rel_tol, abs_tol=abs_tol):
        raise RuntimeError(f"{name} mismatch: {left!r} != {right!r}")


def _assert_equivalent(observed: Any, expected: Any, name: str) -> None:
    if isinstance(expected, dict):
        if not isinstance(observed, dict) or set(observed) != set(expected):
            raise RuntimeError(f"{name} mapping keys differ")
        for key in expected:
            _assert_equivalent(observed[key], expected[key], f"{name}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(observed, list) or len(observed) != len(expected):
            raise RuntimeError(f"{name} list shape differs")
        for index, (left, right) in enumerate(zip(observed, expected, strict=True)):
            _assert_equivalent(left, right, f"{name}[{index}]")
        return
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if observed != expected:
            raise RuntimeError(f"{name} differs: {observed!r} != {expected!r}")
        return
    if isinstance(expected, int):
        if observed != expected:
            raise RuntimeError(f"{name} differs: {observed!r} != {expected!r}")
        return
    if isinstance(expected, float):
        _assert_close(observed, expected, name)
        return
    raise TypeError(f"unsupported comparison type at {name}: {type(expected)!r}")


def _key(value: list[int] | None) -> gate.PhysicalKey | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise RuntimeError("physical key is not a two-element list")
    return int(value[0]), int(value[1])


def _candidate(value: dict[str, Any]) -> gate.ARLPCandidate:
    if "q1" in value:
        raise RuntimeError("selection candidate illegally contains Q1")
    key = _key(value["key"])
    if key is None:
        raise RuntimeError("physical candidate has no key")
    return gate.ARLPCandidate(
        action=int(value["action"]),
        key=key,
        prior_demand=float(value["prior_demand"]),
        candidate_sinr=float(value["candidate_sinr"]),
    )


def _verify_selection(row: dict[str, Any]) -> tuple[gate.ARLPProposal, list[gate.ARLPCandidate]]:
    if row.get("proposal_input_scope") != "focal_live_state_without_q1_or_outcome":
        raise RuntimeError("proposal input scope is not frozen v4")
    if row.get("proposal_frozen_before_q1_reference") is not True:
        raise RuntimeError("proposal timing receipt is absent")
    fields = row["selection_candidates"]
    candidates = [_candidate(value) for value in fields]
    if len({candidate.key for candidate in candidates}) != len(candidates):
        raise RuntimeError("selection candidates contain duplicate physical keys")
    proposal = gate.arlp_proposal(
        candidates=candidates,
        visible_incumbent_key=_key(row["visible_incumbent_key"]),
    )
    if proposal.choice.action != int(row["proposal_action"]) or proposal.choice.key != _key(
        row["proposal_key"]
    ):
        raise RuntimeError("ARLP proposal does not replay")
    replay_fields = gate._selection_fields(proposal)
    _assert_equivalent(fields, replay_fields, "selection_candidates")
    selected = next(
        item for item in replay_fields if int(item["action"]) == proposal.choice.action
    )
    _assert_close(
        row["proposal_marginal_cost"],
        selected["marginal_cost"],
        "proposal marginal cost",
    )
    visible_action = row["visible_incumbent_action"]
    visible_key = _key(row["visible_incumbent_key"])
    if (visible_action is None) != (visible_key is None):
        raise RuntimeError("visible incumbent action/key nullability differs")
    return proposal, candidates


def _loads(snapshot: dict[str, Any]) -> dict[gate.PhysicalKey, int]:
    loads: dict[gate.PhysicalKey, int] = {}
    for row in snapshot["eligible_loads"]:
        key = _key(row["key"])
        if key is None or key in loads:
            raise RuntimeError("eligible load key is absent or duplicated")
        value = int(row["load"])
        if value < 1 or float(row["load"]) != float(value):
            raise RuntimeError("eligible beam load is not a positive integer")
        loads[key] = value
    return loads


def _verify_snapshot(snapshot: dict[str, Any], *, focal_user: int, name: str) -> None:
    loads = _loads(snapshot)
    sum_squared = float(sum(value * value for value in loads.values()))
    _assert_close(snapshot["sum_squared_beam_load"], sum_squared, f"{name} sum U2")
    _assert_close(snapshot["c3"], gate.arlp_potential(loads), f"{name} C3")
    if int(snapshot["eff_beams"]) != len(loads):
        raise RuntimeError(f"{name} effective beam count differs from loads")
    if int(snapshot["served"]) != sum(loads.values()):
        raise RuntimeError(f"{name} served count differs from loads")
    active_keys = [_key(value) for value in snapshot["active_beam_keys"]]
    if active_keys != sorted(loads):
        raise RuntimeError(f"{name} active keys differ from eligible-load keys")
    if int(snapshot["active_satellites"]) != len({key[0] for key in loads}):
        raise RuntimeError(f"{name} active satellite count differs from loads")
    served_ids = [int(uid) for uid in snapshot["served_user_ids"]]
    if len(served_ids) != int(snapshot["served"]) or len(set(served_ids)) != len(
        served_ids
    ):
        raise RuntimeError(f"{name} served-user identities are inconsistent")
    focal_served = bool(snapshot["focal_served"])
    if (focal_user in served_ids) != focal_served:
        raise RuntimeError(f"{name} focal served flag differs from served identities")

    focal_key = _key(snapshot["focal_beam_key"])
    focal_load = int(snapshot["focal_beam_load"])
    without = dict(loads)
    if focal_served:
        if focal_key is None or focal_key not in loads or focal_load != loads[focal_key]:
            raise RuntimeError(f"{name} focal beam/load is inconsistent")
        expected_reward = gate.arlp_difference_reward(focal_load)
        if focal_load == 1:
            del without[focal_key]
        else:
            without[focal_key] = focal_load - 1
    else:
        if focal_key is not None or focal_load != 0:
            raise RuntimeError(f"{name} unserved focal has a beam/load")
        expected_reward = 0.0
    without_c3 = gate.arlp_potential(without)
    marginal = float(snapshot["c3"]) - without_c3
    _assert_close(
        snapshot["focal_difference_reward"], expected_reward, f"{name} reward"
    )
    _assert_close(snapshot["c3_without_focal"], without_c3, f"{name} C3-minus")
    _assert_close(snapshot["focal_marginal_c3"], marginal, f"{name} marginal")
    _assert_close(-expected_reward, marginal, f"{name} difference identity")
    _assert_close(
        snapshot["difference_reward_identity_residual"],
        0.0,
        f"{name} difference residual",
        abs_tol=1e-12,
    )
    if snapshot["difference_reward_identity_pass"] is not True:
        raise RuntimeError(f"{name} difference identity not marked passed")

    throughput = float(snapshot["system_throughput_bps"])
    power = float(snapshot["system_power_w"])
    if power <= 0.0:
        raise RuntimeError(f"{name} system power is not positive")
    _assert_close(
        snapshot["system_ee_bits_per_j"],
        throughput / power,
        f"{name} absolute EE",
        rel_tol=1e-11,
        abs_tol=1e-6,
    )


def _verify_contrast(
    observed: dict[str, Any],
    *,
    reference: dict[str, Any],
    alternative: dict[str, Any],
    name: str,
) -> None:
    expected = gate._contrast(reference, alternative)
    _assert_equivalent(observed, expected, name)


def _verify_row(row: dict[str, Any]) -> None:
    proposal, candidates = _verify_selection(row)
    reference_key = _key(row["reference_key"])
    _verify_snapshot(row["reference"], focal_user=int(row["focal_user"]), name="reference")
    if not math.isfinite(float(row["reference_q1"])):
        raise RuntimeError("reference Q1 is absent or non-finite")

    if row["status"] == "ineligible":
        if row["reason"] != "proposal_matches_q1_reference":
            raise RuntimeError("unexpected v4 ineligibility reason")
        if proposal.choice.key != reference_key:
            raise RuntimeError("ineligible proposal does not match Q1 physical key")
        for field in ("random_control", "arlp", "random"):
            if row[field] is not None:
                raise RuntimeError(f"ineligible row unexpectedly contains {field}")
        return
    if row["status"] != "evaluated" or row["reason"] != "eligible":
        raise RuntimeError("unexpected row status/reason")
    if proposal.choice.key == reference_key:
        raise RuntimeError("eligible proposal matches Q1 physical key")
    if row.get("exactly_one_focal_physical_action_changed") is not True:
        raise RuntimeError("one-focal-action receipt is absent")
    if row.get("common_random_number_contract_verified") is not True:
        raise RuntimeError("common-random-number receipt is absent")

    control = row["random_control"]
    if not isinstance(control, dict) or control.get("frozen_before_outcome") is not True:
        raise RuntimeError("random control was not frozen before outcome")
    expected_pool = [
        candidate for candidate in sorted(candidates, key=lambda item: item.action)
        if candidate.key != reference_key
    ]
    _assert_equivalent(
        control["pool"],
        [gate._candidate_fields(candidate) for candidate in expected_pool],
        "random control pool",
    )
    draw_index = int(control["draw_index"])
    if not 0 <= draw_index < len(expected_pool):
        raise RuntimeError("random draw index lies outside its pool")
    selected = expected_pool[draw_index]
    if int(control["action"]) != selected.action or _key(control["key"]) != selected.key:
        raise RuntimeError("random control does not match its frozen draw index")

    focal_user = int(row["focal_user"])
    _verify_snapshot(row["arlp"], focal_user=focal_user, name="arlp")
    _verify_snapshot(row["random"], focal_user=focal_user, name="random")
    _verify_contrast(
        row["arlp_vs_reference"],
        reference=row["reference"],
        alternative=row["arlp"],
        name="ARLP-reference",
    )
    _verify_contrast(
        row["random_vs_reference"],
        reference=row["reference"],
        alternative=row["random"],
        name="random-reference",
    )
    _verify_contrast(
        row["arlp_minus_random"],
        reference=row["random"],
        alternative=row["arlp"],
        name="ARLP-random",
    )


def verify(payload: dict[str, Any], *, expect_stage: str) -> dict[str, Any]:
    if payload.get("schema") != "mcrl-catfish-arlp-shadow-gate-v4":
        raise RuntimeError("unexpected receipt schema")
    if payload.get("status") != "complete" or payload.get("stage") != expect_stage:
        raise RuntimeError("receipt status/stage differs from expectation")
    if payload.get("spec_sha256") != gate.SPEC_SHA256:
        raise RuntimeError("embedded v4 spec digest differs from verifier")
    if v1._sha256(gate.SPEC) != gate.SPEC_SHA256:
        raise RuntimeError("local frozen v4 spec digest changed")
    runner = HERE / "run_arlp_shadow_gate.py"
    if payload.get("analysis_sha256") != v1._sha256(runner):
        raise RuntimeError("v4 runner digest differs from receipt")
    if payload.get("checkpoint", {}).get("checkpoint_sha256") != gate.EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError("checkpoint digest differs from frozen v4")
    for field in (
        "common_random_number_contract",
        "proposal_timing",
        "sampling",
        "independent_unit",
    ):
        if not payload.get(field):
            raise RuntimeError(f"missing provenance field: {field}")
    if float(payload.get("load_scale")) != gate.LOAD_SCALE:
        raise RuntimeError("receipt load scale differs from frozen v4")
    anchor = gate.activation_power_anchor()
    _assert_equivalent(payload["activation_power_anchor"], anchor, "power anchor")
    _assert_close(
        anchor["minimum_active_beam_consumed_power_w"],
        gate.EXPECTED_ACTIVATION_POWER_ANCHOR_W,
        "frozen power anchor",
        abs_tol=1e-12,
    )

    confirmation = expect_stage == "confirmation"
    expected_seeds = (
        list(gate.V4_EVALUATION_SEEDS) if confirmation else list(gate.PILOT_SEEDS)
    )
    expected_focal = (
        gate.CONFIRMATION_FOCAL_USERS if confirmation else gate.PILOT_FOCAL_USERS
    )
    if payload.get("evaluation_seeds") != expected_seeds:
        raise RuntimeError("evaluation seeds differ from frozen stage")
    if int(payload.get("users")) != gate.USERS:
        raise RuntimeError("user count differs from frozen v4")
    if int(payload.get("steps_per_seed")) != gate.STEPS_PER_SEED:
        raise RuntimeError("step count differs from frozen v4")
    if int(payload.get("focal_users_per_step")) != expected_focal:
        raise RuntimeError("focal sampling count differs from frozen stage")

    rollouts = payload["rollouts"]
    if len(rollouts) != len(expected_seeds):
        raise RuntimeError("rollout count differs from frozen seeds")
    all_rows: list[dict[str, Any]] = []
    observed_seeds: list[int] = []
    for rollout in rollouts:
        seed = int(rollout["evaluation_seed"])
        observed_seeds.append(seed)
        steps = rollout["baseline_steps"]
        rows = rollout["proposal_rows"]
        if len(steps) != gate.STEPS_PER_SEED or len(rows) != gate.STEPS_PER_SEED * expected_focal:
            raise RuntimeError("rollout step/row count differs from sampling contract")
        expected_rows: Counter[tuple[int, int]] = Counter()
        for expected_step, step in enumerate(steps):
            if int(step["step_index"]) != expected_step or step.get("preview_commit_parity") is not True:
                raise RuntimeError("baseline step index/parity differs from contract")
            focal_users = [int(uid) for uid in step["focal_users"]]
            if len(focal_users) != expected_focal or len(set(focal_users)) != expected_focal:
                raise RuntimeError("focal sampling is not without replacement")
            if any(not 0 <= uid < gate.USERS for uid in focal_users):
                raise RuntimeError("focal user lies outside the population")
            for uid in focal_users:
                expected_rows[(expected_step, uid)] += 1
        observed_rows = Counter(
            (int(row["step_index"]), int(row["focal_user"])) for row in rows
        )
        if observed_rows != expected_rows:
            raise RuntimeError("proposal rows do not match frozen focal sampling")
        for row in rows:
            if int(row["evaluation_seed"]) != seed:
                raise RuntimeError("row seed differs from rollout seed")
            _verify_row(row)
        all_rows.extend(rows)
    if observed_seeds != expected_seeds:
        raise RuntimeError("rollout seed order differs from frozen stage")

    expected_summary = gate.summarize_gate(
        all_rows,
        seeds=expected_seeds,
        confirmation=confirmation,
    )
    _assert_equivalent(payload["gate_summary"], expected_summary, "gate summary")
    expected_decision = (
        "PILOT_ONLY_NO_SCIENTIFIC_DECISION"
        if not confirmation
        else (
            "PASS_ADVANCE_TO_R3_IMPLEMENTATION_AUDIT_ONLY"
            if expected_summary["all_conditions_pass"]
            else "FAIL_DROP_ARLP_R3_DIRECTION"
        )
    )
    if payload["gate_summary"]["decision"] != expected_decision:
        raise RuntimeError("receipt decision does not follow the frozen rule")
    return {
        "status": "verified",
        "stage": expect_stage,
        "seeds": len(expected_seeds),
        "rows": len(all_rows),
        "eligible_rows": expected_summary["eligible_rows"],
        "decision": expected_summary["decision"],
        "frozen_conditions": expected_summary["frozen_conditions"],
    }


def main() -> int:
    args = _arguments()
    payload = json.loads(args.receipt.read_text(encoding="utf-8"))
    print(json.dumps(verify(payload, expect_stage=args.expect_stage), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
