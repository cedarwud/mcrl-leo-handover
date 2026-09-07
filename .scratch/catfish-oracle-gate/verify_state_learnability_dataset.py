#!/usr/bin/env python3
"""Fail closed on a frozen R3 state-learnability dataset receipt."""

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
sys.path.insert(0, str(HERE))

import run_oracle_gate as v1  # noqa: E402
import run_state_observable_gate as v2  # noqa: E402
import run_state_learnability_dataset as dataset  # noqa: E402
import verify_state_observable_receipt as v2_verify  # noqa: E402


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument(
        "--expect-partition",
        choices=("pilot", "development", "heldout"),
        required=True,
    )
    return parser.parse_args()


def _verify_state(row: dict[str, Any]) -> None:
    state = np.asarray(row["focal_encoded_state"], dtype=np.float64)
    mask = np.asarray(row["focal_action_mask"], dtype=bool)
    if state.shape != (dataset.STATE_DIM,) or not np.all(np.isfinite(state)):
        raise RuntimeError("row has an invalid 112-dimensional model input")
    if mask.shape != (28,):
        raise RuntimeError("row has an invalid 28-dimensional action mask")
    if row["state_input_scope"] != "exact_live_q_head_input_only":
        raise RuntimeError("row state scope is not the exact live Q-head input")
    action = row["proposal_action"]
    if row["status"] == "evaluated":
        if action is None or not mask[int(action)]:
            raise RuntimeError("evaluated proposal action is not valid in its mask")
    access = state[:28]
    visible = row["visible_incumbent_action"]
    if visible is None:
        if np.any(access > 0.5):
            raise RuntimeError("encoded access block contradicts visible incumbent")
    elif access[int(visible)] <= 0.5 or np.count_nonzero(access > 0.5) != 1:
        raise RuntimeError("encoded access block contradicts visible incumbent")
    encoded_sinr = state[28:56]
    encoded_load = state[84:112]
    for candidate in row["selection_candidates"]:
        candidate_action = int(candidate["action"])
        if not mask[candidate_action]:
            raise RuntimeError("selection candidate is invalid in encoded mask")
        expected_sinr = np.float32(
            math.log1p(max(float(candidate["candidate_sinr"]), 0.0))
        )
        expected_load = np.float32(float(candidate["prior_demand"]) / 100.0)
        if np.float32(encoded_sinr[candidate_action]) != expected_sinr:
            raise RuntimeError("encoded SINR block contradicts selection receipt")
        if np.float32(encoded_load[candidate_action]) != expected_load:
            raise RuntimeError("encoded load block contradicts selection receipt")


def verify(payload: dict[str, Any], *, partition: str) -> dict[str, Any]:
    if payload.get("schema") != "mcrl-catfish-r3-state-learnability-dataset-v3":
        raise RuntimeError("unexpected dataset schema")
    if payload.get("status") != "complete" or payload.get("partition") != partition:
        raise RuntimeError("dataset status/partition mismatch")
    if payload.get("spec_sha256") != dataset.SPEC_SHA256:
        raise RuntimeError("dataset spec digest differs from verifier")
    if v1._sha256(dataset.SPEC) != dataset.SPEC_SHA256:
        raise RuntimeError("local frozen v3 spec digest changed")
    if payload.get("amendment_sha256") != dataset.AMENDMENT_SHA256:
        raise RuntimeError("dataset amendment digest differs from verifier")
    if v1._sha256(dataset.AMENDMENT) != dataset.AMENDMENT_SHA256:
        raise RuntimeError("local frozen v3.1 amendment digest changed")
    if payload.get("analysis_sha256") != v1._sha256(
        HERE / "run_state_learnability_dataset.py"
    ):
        raise RuntimeError("dataset runner digest differs from receipt")
    if payload["checkpoint"]["checkpoint_sha256"] != dataset.EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError("dataset checkpoint digest changed")
    if payload.get("state_dim") != dataset.STATE_DIM:
        raise RuntimeError("dataset state dimension changed")

    if partition == "pilot":
        expected_seeds = (dataset.DEVELOPMENT_SEEDS[0],)
        expected_focal = 2
    elif partition == "development":
        expected_seeds = dataset.DEVELOPMENT_SEEDS
        expected_focal = 10
    else:
        expected_seeds = dataset.HELDOUT_SEEDS
        expected_focal = 10
    if tuple(payload["evaluation_seeds"]) != expected_seeds:
        raise RuntimeError("dataset seeds differ from frozen partition")
    if int(payload["focal_users_per_step"]) != expected_focal:
        raise RuntimeError("dataset focal sample size differs from frozen partition")

    all_rows: list[dict[str, Any]] = []
    for rollout in payload["rollouts"]:
        seed = int(rollout["evaluation_seed"])
        expected_keys: Counter[tuple[int, int]] = Counter()
        for step in rollout["baseline_steps"]:
            focal_users = [int(uid) for uid in step["focal_users"]]
            if len(focal_users) != expected_focal or len(set(focal_users)) != len(
                focal_users
            ):
                raise RuntimeError("focal sample is not without replacement")
            for focal_user in focal_users:
                expected_keys[(int(step["step_index"]), focal_user)] += 1
        rows = rollout["proposal_rows"]
        observed_keys = Counter(
            (int(row["step_index"]), int(row["focal_user"])) for row in rows
        )
        if observed_keys != expected_keys:
            raise RuntimeError("dataset rows do not match focal samples")
        for row in rows:
            if row["family"] != dataset.R3_FAMILY:
                raise RuntimeError("dataset contains a non-R3-split family")
            if int(row["evaluation_seed"]) != seed:
                raise RuntimeError("dataset row seed differs from rollout")
            _verify_state(row)
            base_row = dict(row)
            if row["status"] == "evaluated":
                base_labels = v2.r3_role_labels(dataset.R3_FAMILY, base_row)
                base_row.update(base_labels)
                base_row["jointly_positive"] = bool(
                    base_labels["role_positive"]
                    and base_row["ee_positive"]
                    and base_row["service_safe"]
                )
            v2_verify._verify_row(base_row)
            if row["status"] == "evaluated":
                strict_row = dict(row)
                dataset._apply_strict_split_labels(strict_row)
                for name in (
                    "topology_contract",
                    "topology_endpoint_positive",
                    "load_endpoint_positive",
                    "role_positive",
                    "jointly_positive",
                ):
                    if strict_row[name] != row[name]:
                        raise RuntimeError(f"strict v3.1 label {name} does not replay")
        all_rows.extend(rows)

    expected_summary = dataset._label_summary(all_rows)
    if payload["label_summary"] != expected_summary:
        raise RuntimeError("dataset label summary does not recompute")
    if partition == "development":
        parity = payload.get("development_source_parity")
        if parity is None or parity.get("status") != "exact":
            raise RuntimeError("development dataset lacks exact v2 parity")
        if parity.get("rows_exactly_reproduced") != 1000:
            raise RuntimeError("development dataset did not reproduce 1,000 rows")
        if expected_summary["eligible"] != 1000 or expected_summary[
            "jointly_positive"
        ] != 184:
            raise RuntimeError("development labels differ from frozen v2 evidence")
    return {
        "status": "verified",
        "partition": partition,
        "seeds": len(expected_seeds),
        "rows": len(all_rows),
        "eligible": expected_summary["eligible"],
        "jointly_positive": expected_summary["jointly_positive"],
        "service_unsafe": expected_summary["service_unsafe"],
    }


def main() -> int:
    args = _arguments()
    payload = json.loads(args.receipt.read_text(encoding="utf-8"))
    print(json.dumps(verify(payload, partition=args.expect_partition), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
