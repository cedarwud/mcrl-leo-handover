#!/usr/bin/env python3
"""Fail closed on a state-observable Catfish gate receipt."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import run_oracle_gate as v1  # noqa: E402
import run_state_observable_gate as gate  # noqa: E402
from mcrl.env.action_contract import HANDOVER_COST, NUM_ACTIONS  # noqa: E402


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--expect-confirmation", action="store_true")
    return parser.parse_args()


def _assert_close(
    left: float,
    right: float,
    name: str,
    *,
    rel_tol: float = 1e-12,
    abs_tol: float = 1e-9,
) -> None:
    if not math.isclose(
        float(left), float(right), rel_tol=rel_tol, abs_tol=abs_tol
    ):
        raise RuntimeError(f"{name} mismatch: {left!r} != {right!r}")


def _key(value: list[int] | None) -> tuple[int, int] | None:
    return None if value is None else (int(value[0]), int(value[1]))


def _rebuild_proposal(row: dict[str, Any]) -> gate.StateProposal:
    candidates = [
        v1.CandidateChoice(
            action=int(candidate["action"]),
            key=_key(candidate["key"]),
            prior_demand=float(candidate["prior_demand"]),
            candidate_sinr=float(candidate["candidate_sinr"]),
            q1=0.0,
        )
        for candidate in row["selection_candidates"]
    ]
    if any(candidate.key is None for candidate in candidates):
        raise RuntimeError("selection candidate lacks a physical key")
    access = np.zeros(NUM_ACTIONS, dtype=np.float64)
    visible = row["visible_incumbent_action"]
    if visible is not None:
        access[int(visible)] = 1.0
    return gate.state_only_proposal(
        row["family"],
        baseline_action=int(row["reference_action"]),
        baseline_key=_key(row["reference_key"]),
        candidates=candidates,
        access_vector=access,
    )


def _verify_row(row: dict[str, Any]) -> None:
    if row["proposal_input_scope"] != "focal_user_live_observation_only":
        raise RuntimeError("row proposal scope is not focal-only")
    replay = _rebuild_proposal(row)
    if replay.reason != row["reason"]:
        raise RuntimeError("canonical proposal reason does not replay")
    expected_action = None if replay.choice is None else replay.choice.action
    expected_key = None if replay.choice is None else replay.choice.key
    if expected_action != row["proposal_action"] or expected_key != _key(
        row["proposal_key"]
    ):
        raise RuntimeError("canonical proposal choice does not replay")
    if replay.reference_prior_demand != row["reference_prior_demand"]:
        raise RuntimeError("reference prior demand does not replay")
    if row["status"] == "ineligible":
        if replay.choice is not None:
            raise RuntimeError("ineligible row replayed an eligible proposal")
        return
    if row["status"] != "evaluated" or replay.choice is None:
        raise RuntimeError("evaluated row did not replay an eligible proposal")

    certificate = v1.ee_certificate(
        baseline_throughput_bps=float(row["reference_system_throughput_bps"]),
        baseline_power_w=float(row["reference_system_power_w"]),
        alternative_throughput_bps=float(row["alternative_system_throughput_bps"]),
        alternative_power_w=float(row["alternative_system_power_w"]),
    )
    for name, expected in certificate.items():
        observed = row[name]
        if isinstance(expected, bool | int):
            if observed != expected:
                raise RuntimeError(f"EE certificate field {name} does not replay")
        else:
            _assert_close(observed, expected, name)
    _assert_close(
        row["alternative_system_ee_bits_per_j"]
        - row["reference_system_ee_bits_per_j"],
        row["delta_ee_bits_per_j"],
        "absolute EE delta",
    )
    _assert_close(
        row["alternative_focal_rate_bps"] - row["reference_focal_rate_bps"],
        row["focal_rate_delta_bps"],
        "focal rate delta",
    )
    _assert_close(
        row["alternative_other_users_rate_bps"]
        - row["reference_other_users_rate_bps"],
        row["other_users_rate_delta_bps"],
        "other-users rate delta",
        rel_tol=1e-10,
        abs_tol=1e-3,
    )

    if row["family"] == gate.R2_FAMILY:
        cost = {handover.value: value for handover, value in HANDOVER_COST.items()}
        role_positive = (
            cost[row["alternative_focal_handover"]]
            < cost[row["reference_focal_handover"]]
        )
    else:
        labels = gate.r3_role_labels(row["family"], row)
        for name, expected in labels.items():
            if row[name] != expected:
                raise RuntimeError(f"R3 label {name} does not replay")
        role_positive = labels["role_positive"]
    joint = bool(role_positive and row["ee_positive"] and row["service_safe"])
    if row["role_positive"] != role_positive or row["jointly_positive"] != joint:
        raise RuntimeError("role/joint opportunity label does not replay")


def verify(payload: dict[str, Any], *, expect_confirmation: bool) -> dict[str, Any]:
    if payload.get("schema") != "mcrl-catfish-state-observable-gate-v2":
        raise RuntimeError("unexpected receipt schema")
    if payload.get("status") != "complete":
        raise RuntimeError("receipt is not complete")
    expected_stage = "confirmation" if expect_confirmation else "engineering_pilot"
    if payload.get("stage") != expected_stage:
        raise RuntimeError(f"expected {expected_stage}, got {payload.get('stage')}")
    if payload.get("spec_sha256") != gate.SPEC_SHA256:
        raise RuntimeError("embedded spec digest differs from the verifier")
    if v1._sha256(gate.SPEC) != gate.SPEC_SHA256:
        raise RuntimeError("local frozen spec digest changed")
    if payload.get("analysis_sha256") != v1._sha256(
        HERE / "run_state_observable_gate.py"
    ):
        raise RuntimeError("runner digest differs from the receipt")
    for required in (
        "common_random_number_contract",
        "sampling",
        "independent_unit",
    ):
        if not payload.get(required):
            raise RuntimeError(f"missing provenance field: {required}")

    seeds = [int(seed) for seed in payload["evaluation_seeds"]]
    focal_per_step = int(payload["focal_users_per_step"])
    rollouts = payload["rollouts"]
    if len(rollouts) != len(seeds):
        raise RuntimeError("rollout count differs from evaluation seed count")
    all_rows: list[dict[str, Any]] = []
    for rollout in rollouts:
        seed = int(rollout["evaluation_seed"])
        if seed not in seeds:
            raise RuntimeError("rollout contains an undeclared seed")
        steps = rollout["baseline_steps"]
        rows = rollout["proposal_rows"]
        expected = len(steps) * focal_per_step * len(gate.FAMILIES)
        if len(rows) != expected:
            raise RuntimeError("proposal row count differs from the sampling contract")
        expected_keys: Counter[tuple[int, int, str]] = Counter()
        for step in steps:
            focal_users = [int(uid) for uid in step["focal_users"]]
            if len(focal_users) != focal_per_step or len(set(focal_users)) != len(
                focal_users
            ):
                raise RuntimeError("focal sampling is not without replacement")
            for focal_user in focal_users:
                for family in gate.FAMILIES:
                    expected_keys[(int(step["step_index"]), focal_user, family)] += 1
        observed_keys = Counter(
            (int(row["step_index"]), int(row["focal_user"]), row["family"])
            for row in rows
        )
        if observed_keys != expected_keys:
            raise RuntimeError("proposal rows do not match focal sampling")
        for row in rows:
            if int(row["evaluation_seed"]) != seed:
                raise RuntimeError("row seed differs from rollout seed")
            _verify_row(row)
        all_rows.extend(rows)

    confirmation = expected_stage == "confirmation"
    expected_summary = gate._summaries(all_rows, confirmation=confirmation)
    if payload["family_summary"] != expected_summary:
        raise RuntimeError("family summary does not recompute from proposal rows")
    return {
        "status": "verified",
        "stage": expected_stage,
        "seeds": len(seeds),
        "rows": len(all_rows),
        "evaluated_rows": sum(row["status"] == "evaluated" for row in all_rows),
        "family_summary": payload["family_summary"],
    }


def main() -> int:
    args = _arguments()
    payload = json.loads(args.receipt.read_text(encoding="utf-8"))
    print(json.dumps(verify(payload, expect_confirmation=args.expect_confirmation), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
