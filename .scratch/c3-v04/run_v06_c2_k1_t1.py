#!/usr/bin/env python3
"""V0.6 C2-k1 T1 source/oracle-headroom runner.

The runner is a contract and shard producer.  ``prepare`` seals the 12 fresh
TRAIN-design anchors and the frozen Q1+Q3 policy lineage before any source
rows can be materialised.  ``generate`` consumes an explicitly supplied
branch-local payload and emits all 28 opening actions for each of the three
frozen lineages.  It does not run a simulator, train a network, open TEST, or
select rows by their outcomes.

The real-TLE/environment adapter belongs outside this file.  Its payload must
contain the branch-local k1 arrays required by
``mcrl.runtime.ee_axis_v06_c2_k1.build_opening_pairs``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.runtime.ee_axis_v06_c2_k1 import (  # noqa: E402
    ACTION_COUNT,
    C2K1ContractError,
    CLAIM_CEILING,
    POLICY_RULE,
    SCHEMA,
    SOURCE_RULE,
    TRAIN_STEP_WINDOWS,
    TRAIN_WORLD_POOLS,
    build_opening_pairs,
    canonical_sha256,
    c2_k1_surplus_bits,
    four_offset_metrics,
    oracle_and_drop_scores,
    policy_hash,
    selected_continuation_metrics,
    select_anchor,
    select_train_worlds,
    write_once_json,
)


PREPARE_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-prepare-v1"
PREPARE_SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-prepare-seal-v1"
SOURCE_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-source-v1"
SOURCE_SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-source-seal-v1"
LINEAGES = ("q13-a", "q13-b", "q13-c")
USER_COUNT = 100
# These are the frozen initialization lineages authenticated by V0.4 Phase-B.
# Production prepare-live passes the Phase-B receipt explicitly; keeping the
# values here also prevents a caller from silently substituting three ad-hoc
# policies when using the pure prepare builder.
Q13_INITIALIZATION_SEEDS = (2026092101, 2026092102, 2026092103)
PREPARE_LIVE_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-v2"
KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
LAMBDA_BITS_PER_J = float.fromhex("0x1.443a8f481639ap+26")
T1_FORMULA_CONTRACT = {
    "interval_s": 30.08,
    "lambda_bits_per_j": LAMBDA_BITS_PER_J,
    "kappa_bits": KAPPA_BITS,
    "z1": "dt*delta_rate_focal_k0-lambda*dt*delta_power_k0",
    "z3": "dt*sum_delta_rate_nonfocal_k0",
    "z2_k1": "dt*sum_delta_rate_k1-lambda*dt*delta_power_k1",
    "oracle": "argmax_masked(Q1_k0+Q3_k0+z2_k1/kappa)",
    "drop": "argmax_masked(Q1_k0+Q3_k0)",
    "ee": "sum_canonical_rates/sum_energy",
}
T1_GATE_CONTRACT = {
    "pairs": 1008, "controls": 36, "positive_lineages": 2,
    "positive_worlds": 8, "service_nonnegative_lineages": 2,
    "users": USER_COUNT,
    "identity_relative_tolerance": 1e-9,
    "claim_ceiling": CLAIM_CEILING,
}
T1_SOURCE_AUTHORITY = {
    "scanner": "run_v04_c2_support_complete_census._real_seed_topology",
    "simulator_manifest": "run_v04_c2_support_complete_census._production_source_manifest",
    "loader": "run_v04_c3_source._default_runtime",
    "q13_gate": "run_v04_c2_phase_b._authenticate_q13_gate",
    "q13_gate_manifest": "q13_gate.source_manifest_sha256",
    "field": "mcrl.env.keyed_fading.KeyedFadingField",
}


class T1RunnerError(RuntimeError):
    """Malformed or unauthorised T1 source request."""


def _digest(value: object, *, field: str) -> str:
    if (not isinstance(value, str) or len(value) != 64 or value != value.lower()
            or any(char not in "0123456789abcdef" for char in value)):
        raise T1RunnerError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and value == value.lower() and all(
        char in "0123456789abcdef" for char in value
    )


def _canonical_read(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise T1RunnerError(f"missing regular JSON: {source}")
    raw = source.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise T1RunnerError(f"invalid JSON: {source}") from exc
    if not isinstance(value, dict) or raw != __import__("mcrl.runtime.ee_axis_v06_c2_k1", fromlist=["canonical_bytes"]).canonical_bytes(value):
        raise T1RunnerError(f"JSON is not canonical: {source}")
    return value


def _source_payload_sha256(payload: Mapping[str, Any]) -> str:
    """Bind every source field, including its PREPARE_LIVE provenance."""
    body = dict(payload)
    body.pop("source_sha256", None)
    return canonical_sha256(body)


def _recompute_k1_q13_actions(q13_sum: object, mask: object, *,
                              users: int, field: str) -> list[int]:
    """Derive all-user k1 actions from persisted Q1+Q3 sums and masks."""
    scores = np.asarray(q13_sum, dtype=np.float64)
    legal = np.asarray(mask)
    if (scores.shape != (users, ACTION_COUNT)
            or not np.all(np.isfinite(scores))
            or legal.shape != (users, ACTION_COUNT)
            or legal.dtype != np.bool_):
        raise T1RunnerError(f"{field} Q13 evidence is malformed")
    result: list[int] = []
    for user in range(users):
        if not bool(np.any(legal[user])):
            result.append(-1)
        else:
            result.append(int(np.argmax(
                np.where(legal[user], scores[user], -np.inf))))
    return result


def build_prepare(world_records: Sequence[Mapping[str, Any]], *,
                  q1_bytes: bytes, q3_bytes: bytes, mask_bytes: bytes,
                  source_manifest_sha256: str,
                  simulator_prereg_file_sha256: str | None = None,
                  t1_prereg_file_sha256: str | None = None) -> dict[str, Any]:
    """Build the write-once pre-generation authority payload."""
    _digest(source_manifest_sha256, field="source_manifest_sha256")
    if simulator_prereg_file_sha256 is None or t1_prereg_file_sha256 is None:
        raise T1RunnerError("prepare must bind simulator and T1 prereg digests separately")
    _digest(simulator_prereg_file_sha256, field="simulator_prereg_file_sha256")
    _digest(t1_prereg_file_sha256, field="t1_prereg_file_sha256")
    by_pool: dict[str, list[int]] = {"early": [], "mid": [], "late": []}
    records: dict[int, Mapping[str, Any]] = {}
    for index, record in enumerate(world_records):
        if not isinstance(record, Mapping):
            raise T1RunnerError(f"world record {index} is malformed")
        pool = record.get("pool")
        world = record.get("world_id")
        if pool not in by_pool or type(world) is not int:
            raise T1RunnerError(f"world record {index} has invalid pool/world")
        by_pool[pool].append(world)
        if world in records:
            raise T1RunnerError("duplicate world record")
        records[world] = record
    selected = select_train_worlds(by_pool)
    anchors = []
    for pool, world in selected:
        record = records[world]
        anchor = select_anchor(pool, world, record.get("eligible_steps", []), record.get("eligible_users", []))
        anchors.append({"pool": anchor.pool, "world_id": anchor.world_id,
                        "step": anchor.step, "focal_user": anchor.focal_user,
                        "predecision_only": True})
    p_hash = policy_hash(q1_bytes, q3_bytes, mask_bytes)
    digest_bytes = lambda value: hashlib.sha256(value).hexdigest()
    policy_hashes = {lineage: {"q1": digest_bytes(q1_bytes), "q3": digest_bytes(q3_bytes),
                               "mask": digest_bytes(mask_bytes)} for lineage in LINEAGES}
    live_code = HERE / "v06_c2_k1_live_adapter.py"
    payload = {
        "schema": PREPARE_SCHEMA, "algorithm_schema": SCHEMA,
        "source_rule": SOURCE_RULE, "policy_rule": POLICY_RULE,
        "claim_ceiling": CLAIM_CEILING, "source_manifest_sha256": source_manifest_sha256,
        "simulator_prereg_file_sha256": simulator_prereg_file_sha256,
        "t1_prereg_file_sha256": t1_prereg_file_sha256,
        "policy_sha256": p_hash,
        "policy_hashes": policy_hashes,
        "runner_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "live_adapter_code_sha256": hashlib.sha256(live_code.read_bytes()).hexdigest() if live_code.is_file() else None,
        "lineages": list(LINEAGES), "anchors": anchors,
        "counts": {"pools": 3, "worlds": 12, "worlds_per_pool": 4,
                    "openings_per_anchor_lineage": ACTION_COUNT,
                    "lineages": len(LINEAGES), "expected_pairs": 12 * ACTION_COUNT * len(LINEAGES)},
        "training": False, "test_split_opened": False,
        "outcome_selection": False, "prepared_before_generation": True,
    }
    return payload | {"prepare_sha256": canonical_sha256(payload)}


def prepare(world_records: Sequence[Mapping[str, Any]], output_dir: Path, *,
            q1_bytes: bytes, q3_bytes: bytes, mask_bytes: bytes,
            source_manifest_sha256: str,
            simulator_prereg_file_sha256: str | None = None,
            t1_prereg_file_sha256: str | None = None) -> dict[str, Any]:
    """Seal schedule/policy/gates exactly once."""
    payload = build_prepare(world_records, q1_bytes=q1_bytes, q3_bytes=q3_bytes,
                            mask_bytes=mask_bytes, source_manifest_sha256=source_manifest_sha256,
                            simulator_prereg_file_sha256=simulator_prereg_file_sha256,
                            t1_prereg_file_sha256=t1_prereg_file_sha256)
    root = Path(output_dir)
    result_sha = write_once_json(root / "prepare.json", payload)
    seal = {"schema": PREPARE_SEAL_SCHEMA, "prepare_sha256": canonical_sha256(payload),
            "prepare_file_sha256": result_sha, "training": False,
            "test_split_opened": False, "outcome_selection": False}
    write_once_json(root / "prepare-seal.json", seal)
    return payload


def build_prepare_live(selected_anchors: Sequence[Mapping[str, Any]], *,
                       lineage_bindings: Mapping[str, Mapping[str, Mapping[str, Any]]],
                       simulator_source_manifest_sha256: str,
                       q13_gate_source_manifest_sha256: str,
                       simulator_prereg_file_sha256: str,
                       t1_prereg_file_sha256: str,
                       main_dir: str | Path | None = None,
                       main_checkpoint_sha256: str | None = None,
                       expected_initialization_seeds: Sequence[int] | None = None,
                       expected_hybrid_hashes: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Seal the production topology selection and per-lineage Q13 inputs.

    This is the target-free half of T1.  It accepts only scanner-produced
    topology records; every cell must already prove the physical Main
    departure, complete native 28-action support, and a complete forecast
    horizon.  Scores/a_D are frozen policy metadata, not outcomes.
    """
    _digest(simulator_source_manifest_sha256,
            field="simulator_source_manifest_sha256")
    _digest(q13_gate_source_manifest_sha256,
            field="q13_gate_source_manifest_sha256")
    _digest(simulator_prereg_file_sha256, field="simulator_prereg_file_sha256")
    _digest(t1_prereg_file_sha256, field="t1_prereg_file_sha256")
    if main_dir is not None:
        if main_checkpoint_sha256 is None:
            raise T1RunnerError("prepare-live main_dir requires checkpoint digest")
        _digest(main_checkpoint_sha256, field="main_checkpoint_sha256")
    if not isinstance(selected_anchors, Sequence) or len(selected_anchors) != 12:
        raise T1RunnerError("prepare-live requires exactly 12 selected anchors")
    anchors: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    per_pool: dict[str, int] = {pool: 0 for pool in ("early", "mid", "late")}
    for raw in selected_anchors:
        if not isinstance(raw, Mapping):
            raise T1RunnerError("prepare-live anchor is malformed")
        pool, world = raw.get("pool"), raw.get("world_id")
        step, focal = raw.get("step"), raw.get("focal_user")
        if pool not in per_pool or type(world) is not int or world not in TRAIN_WORLD_POOLS[pool]:
            raise T1RunnerError("prepare-live anchor is outside fixed world pools")
        if (pool, world) in seen:
            raise T1RunnerError("prepare-live selected duplicate physical world")
        lo, hi = TRAIN_STEP_WINDOWS[pool]
        if type(step) is not int or not lo <= step <= hi:
            raise T1RunnerError(f"prepare-live {pool} step is outside {lo}..{hi}")
        if type(focal) is not int or focal < 0:
            raise T1RunnerError("prepare-live focal user is malformed")
        reference_action = raw.get("reference_action")
        if type(reference_action) is not int or not 0 <= reference_action < ACTION_COUNT:
            raise T1RunnerError("prepare-live reference action is not a native action")
        if raw.get("physical_main_departure") is not True or raw.get("complete_forecast_horizon") is not True:
            raise T1RunnerError("prepare-live anchor lacks physical Main/horizon eligibility")
        if raw.get("complete_28_action_census") is not True or raw.get("alias_absence") is not True:
            raise T1RunnerError("prepare-live anchor lacks complete 28-action/alias gate")
        for name in ("world_anchor_sha256", "anchor_sha256", "checkpoint_sha256",
                     "source_manifest_sha256", "policy_sha256"):
            _digest(raw.get(name), field=f"prepare-live {name}")
        if raw["source_manifest_sha256"] != simulator_source_manifest_sha256:
            raise T1RunnerError("prepare-live anchor source manifest disagrees with context")
        if main_checkpoint_sha256 is not None and raw["checkpoint_sha256"] != main_checkpoint_sha256:
            raise T1RunnerError("prepare-live anchor checkpoint disagrees with Main authority")
        if raw.get("evaluation_seed") != world:
            raise T1RunnerError("prepare-live evaluation seed is not the physical source seed")
        reference_physical = raw.get("reference_physical_key")
        incumbent_physical = raw.get("incumbent_physical_key")
        if (not isinstance(reference_physical, (list, tuple)) or len(reference_physical) != 2
                or any(type(value) is not int for value in reference_physical)):
            raise T1RunnerError("prepare-live reference physical key is malformed")
        if (not isinstance(incumbent_physical, (list, tuple)) or len(incumbent_physical) != 2
                or any(type(value) is not int for value in incumbent_physical)):
            raise T1RunnerError("prepare-live incumbent physical key is malformed")
        legal_mask = raw.get("legal_action_mask")
        candidate_actions = raw.get("candidate_actions")
        candidate_keys = raw.get("candidate_physical_keys")
        if (not isinstance(legal_mask, (list, tuple)) or len(legal_mask) != ACTION_COUNT
                or any(type(value) is not bool for value in legal_mask)
                or not all(legal_mask)):
            raise T1RunnerError("prepare-live legal action mask is not the complete 28-action mask")
        if (not isinstance(candidate_actions, (list, tuple)) or len(candidate_actions) != ACTION_COUNT - 1
                or any(type(value) is not int or not 0 <= value < ACTION_COUNT for value in candidate_actions)
                or len(set(candidate_actions)) != ACTION_COUNT - 1
                or set(candidate_actions) != set(range(ACTION_COUNT)) - {reference_action}):
            raise T1RunnerError("prepare-live candidate actions are not the exact 27-action complement")
        if (not isinstance(candidate_keys, (list, tuple)) or len(candidate_keys) != ACTION_COUNT - 1
                or any(not isinstance(key, (list, tuple)) or len(key) != 2
                       or any(type(value) is not int for value in key) for key in candidate_keys)
                or len({tuple(key) for key in candidate_keys}) != ACTION_COUNT - 1):
            raise T1RunnerError("prepare-live candidate physical keys are not exact unique 27 entries")
        seen.add((pool, world)); per_pool[pool] += 1
        anchors.append({"pool": pool, "world_id": world, "step": step, "focal_user": focal,
                        "reference_action": reference_action,
                        "world_anchor_sha256": raw["world_anchor_sha256"],
                        "anchor_sha256": raw["anchor_sha256"],
                        "reference_physical_key": list(reference_physical),
                        "incumbent_physical_key": list(incumbent_physical),
                        "legal_action_mask": list(legal_mask),
                        "candidate_actions": list(candidate_actions),
                        "candidate_physical_keys": [list(key) for key in candidate_keys],
                        "checkpoint_sha256": raw["checkpoint_sha256"],
                        "simulator_source_manifest_sha256": raw["source_manifest_sha256"],
                        "policy_sha256": raw["policy_sha256"],
                        "evaluation_seed": raw["evaluation_seed"],
                        "predecision_only": True,
                        "physical_main_departure": True,
                        "complete_forecast_horizon": True})
    if per_pool != {"early": 4, "mid": 4, "late": 4}:
        raise T1RunnerError("prepare-live must select exactly four worlds per fixed pool")
    pool_order = {pool: index for index, pool in enumerate(("early", "mid", "late"))}
    if tuple(sorted(anchors, key=lambda item: (pool_order[item["pool"]], item["world_id"]))) != tuple(anchors):
        raise T1RunnerError("prepare-live anchors must be canonically pool/world sorted")
    if set(lineage_bindings) != set(_anchor_key(anchor) for anchor in anchors):
        raise T1RunnerError("prepare-live lineage binding keys do not match anchors")
    bindings: dict[str, dict[str, Any]] = {}
    stable_lineage: dict[str, dict[str, Any]] = {}
    if expected_initialization_seeds is not None:
        expected_seeds = tuple(expected_initialization_seeds)
        if expected_seeds != Q13_INITIALIZATION_SEEDS or len(set(expected_seeds)) != 3:
            raise T1RunnerError("prepare-live Q13 initialization seeds are not the frozen three")
    else:
        expected_seeds = None
    if expected_hybrid_hashes is not None:
        if set(expected_hybrid_hashes) != set(LINEAGES):
            raise T1RunnerError("prepare-live authenticated hybrid hashes lack a lineage")
        for lineage in LINEAGES:
            _digest(expected_hybrid_hashes[lineage], field=f"authenticated_hybrid_hashes/{lineage}")
    for anchor in anchors:
        key = _anchor_key(anchor); cell = lineage_bindings[key]
        if set(cell) != set(LINEAGES):
            raise T1RunnerError(f"{key} must bind all three Q13 lineages")
        physical_crn: set[str] = set(); normalized: dict[str, Any] = {}
        for lineage in LINEAGES:
            item = cell[lineage]
            if not isinstance(item, Mapping):
                raise T1RunnerError(f"{key}/{lineage} binding is malformed")
            for name in ("q1_sha256", "q3_sha256", "hybrid_sha256", "crn_sha256"):
                _digest(item.get(name), field=f"{key}/{lineage}/{name}")
            seed = item.get("initialization_seed")
            if type(seed) is not int or seed <= 0:
                raise T1RunnerError(f"{key}/{lineage} initialization seed is malformed")
            if expected_seeds is not None and seed != expected_seeds[LINEAGES.index(lineage)]:
                raise T1RunnerError(f"{key}/{lineage} initialization seed is not authenticated")
            if expected_hybrid_hashes is not None and item.get("hybrid_sha256") != expected_hybrid_hashes[lineage]:
                raise T1RunnerError(f"{key}/{lineage} hybrid digest disagrees with authenticated gate")
            scores = item.get("q13_score_vector")
            if not isinstance(scores, Sequence) or isinstance(scores, (str, bytes)) or len(scores) != ACTION_COUNT:
                raise T1RunnerError(f"{key}/{lineage} frozen Q1+Q3 score vector is not 28 entries")
            if any(not math.isfinite(float(value)) for value in scores):
                raise T1RunnerError(f"{key}/{lineage} score vector is nonfinite")
            a_d = item.get("a_D")
            if type(a_d) is not int or not 0 <= a_d < ACTION_COUNT:
                raise T1RunnerError(f"{key}/{lineage} a_D is not a native action")
            finite_scores = tuple(float(value) for value in scores)
            expected_a_d = min(range(ACTION_COUNT), key=lambda action: (-finite_scores[action], action))
            if a_d != expected_a_d:
                raise T1RunnerError(f"{key}/{lineage} a_D disagrees with lowest-index Q1+Q3 argmax")
            physical_crn.add(str(item["crn_sha256"]))
            lineage_signature = {"q1_sha256": item["q1_sha256"], "q3_sha256": item["q3_sha256"],
                                 "hybrid_sha256": item["hybrid_sha256"],
                                 "initialization_seed": seed}
            previous = stable_lineage.get(lineage)
            if previous is None:
                stable_lineage[lineage] = lineage_signature
            elif previous != lineage_signature:
                raise T1RunnerError(f"{lineage} frozen policy digest/seed drifted across cells")
            normalized[lineage] = {"q1_sha256": item["q1_sha256"], "q3_sha256": item["q3_sha256"],
                                    "hybrid_sha256": item["hybrid_sha256"], "initialization_seed": seed,
                                    "crn_sha256": item["crn_sha256"], "q13_score_vector": list(finite_scores),
                                    "a_D": a_d}
        if len(physical_crn) != 1:
            raise T1RunnerError(f"{key} CRN root differs across Q13 lineages")
        bindings[key] = normalized
    code_authority = _code_authority_manifest()
    body = {"schema": PREPARE_LIVE_SCHEMA, "algorithm_schema": SCHEMA,
            "source_rule": SOURCE_RULE, "policy_rule": POLICY_RULE,
            "claim_ceiling": CLAIM_CEILING,
            "simulator_source_manifest_sha256": simulator_source_manifest_sha256,
            "q13_gate_source_manifest_sha256": q13_gate_source_manifest_sha256,
            "simulator_prereg_file_sha256": simulator_prereg_file_sha256,
            "t1_prereg_file_sha256": t1_prereg_file_sha256,
            "formula_contract": T1_FORMULA_CONTRACT,
            "gate_contract": T1_GATE_CONTRACT,
            "code_authority": code_authority,
            "source_authority": T1_SOURCE_AUTHORITY,
            **({"main_dir": str(Path(main_dir).resolve()),
                "main_checkpoint_sha256": main_checkpoint_sha256} if main_dir is not None else {}),
            "lineages": list(LINEAGES), "anchors": anchors, "lineage_bindings": bindings,
            "counts": {"pools": 3, "worlds": 12, "lineages": 3,
                       "users": USER_COUNT,
                       "openings_per_anchor_lineage": ACTION_COUNT, "expected_pairs": 1008,
                       "expected_controls": 36},
            "training": False, "test_split_opened": False, "outcome_selection": False,
            "q2_consulted": False, "prepared_before_generation": True}
    return body | {"prepare_sha256": canonical_sha256(body)}


def _anchor_key(anchor: Mapping[str, Any]) -> str:
    return f"{anchor['pool']}:{anchor['world_id']}:{anchor['step']}:{anchor['focal_user']}"


def _main_gauge(row: Mapping[str, Any], *, focal_user: int, interval_s: float,
                lambda_bits_per_j: float, prefix: str = "") -> dict[str, Any]:
    """Reconstruct the Main-gauge identity from persisted k0/k1 arrays.

    The arrays are deliberately persisted in each source row so adjudication
    does not trust a precomputed scalar supplied by a producer.  At k0 the
    focal rate change plus the complete opening power change is ``z1`` and
    the non-focal rate change is ``z3``.  ``z2^1`` and ``g1`` are the same
    complete k1 surplus.  Thus the checked identity is
    ``z1 + z3 + z2^1 = g0 + g1``.
    """
    def field(name: str) -> str:
        return f"{prefix}{name}"
    names = tuple(field(name) for name in
                  ("candidate_rates_k0", "reference_rates_k0", "candidate_rates_k1",
                   "reference_rates_k1"))
    if any(name not in row for name in names):
        raise T1RunnerError("row lacks persisted Main-gauge k0/k1 rate arrays")
    c0 = np.asarray(row[field("candidate_rates_k0")], dtype=np.float64)
    r0 = np.asarray(row[field("reference_rates_k0")], dtype=np.float64)
    c1 = np.asarray(row[field("candidate_rates_k1")], dtype=np.float64)
    r1 = np.asarray(row[field("reference_rates_k1")], dtype=np.float64)
    if any(array.ndim != 1 for array in (c0, r0, c1, r1)) or not (c0.shape == r0.shape == c1.shape == r1.shape):
        raise T1RunnerError("Main-gauge arrays must be equal-length user vectors")
    if not 0 <= focal_user < c0.size:
        raise T1RunnerError("Main-gauge focal user is outside persisted arrays")
    try:
        c0p = float(row[field("candidate_power_k0")]); r0p = float(row[field("reference_power_k0")])
        c1p = float(row[field("candidate_power_k1")]); r1p = float(row[field("reference_power_k1")])
    except (KeyError, TypeError, ValueError) as exc:
        raise T1RunnerError("row lacks finite Main-gauge k0/k1 powers") from exc
    if not all(math.isfinite(value) for value in (c0p, r0p, c1p, r1p)):
        raise T1RunnerError("Main-gauge powers must be finite")
    delta0 = c0 - r0
    z1 = interval_s * float(delta0[focal_user]) - lambda_bits_per_j * interval_s * (c0p - r0p)
    z3 = interval_s * math.fsum(float(value) for value in delta0[np.arange(c0.size) != focal_user])
    g0 = interval_s * math.fsum(float(value) for value in delta0) - lambda_bits_per_j * interval_s * (c0p - r0p)
    g1 = c2_k1_surplus_bits(c1, r1, c1p, r1p, interval_s=interval_s,
                            lambda_bits_per_j=lambda_bits_per_j)
    z2 = g1
    lhs = z1 + z3 + z2
    rhs = g0 + g1
    identity_tolerance = float(T1_GATE_CONTRACT["identity_relative_tolerance"])
    tolerance = identity_tolerance * max(abs(rhs), 1.0)
    return {"z1_bits": z1, "z3_bits": z3, "z2_k1_bits": z2,
            "g0_bits": g0, "g1_bits": g1, "identity_residual_bits": lhs - rhs,
            "identity_passed": abs(lhs - rhs) <= tolerance,
            "identity_rel_tolerance": identity_tolerance}


def generate(prepare_payload: Mapping[str, Any], lineage_payloads: Mapping[str, Mapping[str, Sequence[Mapping[str, object]]]],
             *, interval_s: float, lambda_bits_per_j: float, kappa_bits: float,
             requested_lineages: Sequence[str] = LINEAGES) -> dict[str, Any]:
    """Materialise every clean pair and direct oracle/drop headroom row.

    The input payload represents already sealed physics and frozen Q1/Q3
    bytes.  It is deliberately explicit: there is no hidden fallback, tape,
    Q2, or outcome-dependent filter in this consumer.
    """
    if prepare_payload.get("schema") not in (PREPARE_SCHEMA, PREPARE_LIVE_SCHEMA) or prepare_payload.get("training") is not False or prepare_payload.get("test_split_opened") is not False:
        raise T1RunnerError("prepare payload is not a sealed pre-generation authority")
    unsigned_prepare = dict(prepare_payload)
    supplied_prepare_sha = unsigned_prepare.pop("prepare_sha256", None)
    if supplied_prepare_sha != canonical_sha256(unsigned_prepare):
        raise T1RunnerError("prepare hash does not bind the schedule/policy/gates")
    if prepare_payload.get("schema") == PREPARE_LIVE_SCHEMA:
        if prepare_payload.get("formula_contract") != T1_FORMULA_CONTRACT:
            raise T1RunnerError("prepare-live formula/constants are not the frozen T1 contract")
        if prepare_payload.get("gate_contract") != T1_GATE_CONTRACT:
            raise T1RunnerError("prepare-live gates are not the frozen T1 contract")
        sealed_code = prepare_payload.get("code_authority")
        if sealed_code != _code_authority_manifest():
            raise T1RunnerError("prepare-live code authority has drifted")
        if (interval_s != T1_FORMULA_CONTRACT["interval_s"]
                or lambda_bits_per_j != T1_FORMULA_CONTRACT["lambda_bits_per_j"]
                or kappa_bits != T1_FORMULA_CONTRACT["kappa_bits"]):
            raise T1RunnerError("prepare-live generation constants differ from frozen T1 contract")
    anchors = prepare_payload.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != 12:
        raise T1RunnerError("prepare must contain exactly 12 anchors")
    if tuple(prepare_payload.get("lineages", ())) != LINEAGES:
        raise T1RunnerError("prepare lineages are not exactly q13-a/q13-b/q13-c")
    requested = tuple(requested_lineages)
    if not requested or any(lineage not in LINEAGES for lineage in requested) or len(set(requested)) != len(requested):
        raise T1RunnerError("requested lineages must be a nonempty subset of the three frozen lineages")
    output_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            raise T1RunnerError("anchor is malformed")
        key = _anchor_key(anchor)
        data = lineage_payloads.get(key)
        if not isinstance(data, Mapping) or any(lineage not in data for lineage in requested):
            raise T1RunnerError(f"missing all three lineages for {key}")
        for lineage in requested:
            rows = data[lineage]
            if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
                raise T1RunnerError(f"{key}/{lineage} rows are malformed")
            explicit_reference = rows[0].get("reference_action") if rows else None
            if type(explicit_reference) is not int:
                raise T1RunnerError(f"{key}/{lineage} lacks explicit Main reference_action")
            pairs = build_opening_pairs(
                rows[0]["q1_k0"], rows[0]["q3_k0"], rows[0]["mask_k0"], rows,
                reference_action=explicit_reference,
                interval_s=interval_s, lambda_bits_per_j=lambda_bits_per_j,
                kappa_bits=kappa_bits,
            )
            reference_action = pairs[0].reference_action
            if any(row.get("reference_action") != reference_action for row in rows):
                raise T1RunnerError(f"{key}/{lineage} Main reference action drifted")
            live_binding = prepare_payload.get("lineage_bindings", {}).get(key, {}).get(lineage) if isinstance(prepare_payload.get("lineage_bindings"), Mapping) else None
            if isinstance(live_binding, Mapping):
                expected_scores = np.asarray(live_binding.get("q13_score_vector"), dtype=np.float64)
                observed_scores = np.asarray(rows[0]["q1_k0"], dtype=np.float64) + np.asarray(rows[0]["q3_k0"], dtype=np.float64)
                if expected_scores.shape != (ACTION_COUNT,) or observed_scores.shape != expected_scores.shape or not np.array_equal(observed_scores, expected_scores):
                    raise T1RunnerError(f"{key}/{lineage} sealed Q1+Q3 k0 vector drifted")
                expected_a_d = min(range(ACTION_COUNT), key=lambda action: (-float(observed_scores[action]), action))
                if int(live_binding.get("a_D", -1)) != expected_a_d:
                    raise T1RunnerError(f"{key}/{lineage} sealed a_D disagrees with k0 Q1+Q3")
                first_mask = np.asarray(rows[0]["mask_k0"])
                if first_mask.shape != (ACTION_COUNT,) or first_mask.dtype != np.bool_:
                    raise T1RunnerError(f"{key}/{lineage} sealed k0 mask is malformed")
                for check_row in rows:
                    if not (np.array_equal(np.asarray(check_row["q1_k0"], dtype=np.float64), np.asarray(rows[0]["q1_k0"], dtype=np.float64))
                            and np.array_equal(np.asarray(check_row["q3_k0"], dtype=np.float64), np.asarray(rows[0]["q3_k0"], dtype=np.float64))
                            and np.array_equal(np.asarray(check_row["mask_k0"], dtype=np.bool_), first_mask)):
                        raise T1RunnerError(f"{key}/{lineage} k0 Q13 surfaces differ across 28 actions")
                if int(anchor.get("reference_action", -1)) != reference_action:
                    raise T1RunnerError(f"{key}/{lineage} reference action disagrees with prepare")
            for opening_action, (pair, row) in enumerate(zip(pairs, rows)):
                    expected_policy = (canonical_sha256({"q1_sha256": live_binding["q1_sha256"],
                                                         "q3_sha256": live_binding["q3_sha256"],
                                                         "hybrid_sha256": live_binding["hybrid_sha256"],
                                                         "initialization_seed": live_binding["initialization_seed"]})
                                       if isinstance(live_binding, Mapping) else prepare_payload["policy_sha256"])
                    row_policy = row.get("policy_sha256")
                    if not _valid_digest(row_policy) or row_policy != expected_policy:
                        raise T1RunnerError(f"{key}/{lineage}/{opening_action} policy hash drifted")
                    if isinstance(live_binding, Mapping) and row.get("crn_sha256") != live_binding["crn_sha256"]:
                        raise T1RunnerError(f"{key}/{lineage}/{opening_action} physical CRN drifted")
                    ref_exec = row.get("reference_k1_executed_actions")
                    cand_exec = row.get("candidate_k1_executed_actions")
                    ref_expected = row.get("reference_k1_q13_actions")
                    cand_expected = row.get("candidate_k1_q13_actions")
                    reference_evidence = {
                        "q13_sum": row.get("reference_k1_q13_sum"),
                        "mask": row.get("reference_k1_q13_mask"),
                    }
                    candidate_evidence = {
                        "q13_sum": row.get("candidate_k1_q13_sum"),
                        "mask": row.get("candidate_k1_q13_mask"),
                    }
                    try:
                        ref_recomputed = _recompute_k1_q13_actions(
                            reference_evidence["q13_sum"],
                            reference_evidence["mask"],
                            users=len(ref_exec), field="reference-k1")
                        cand_recomputed = _recompute_k1_q13_actions(
                            candidate_evidence["q13_sum"],
                            candidate_evidence["mask"],
                            users=len(cand_exec), field="candidate-k1")
                    except (T1RunnerError, TypeError):
                        ref_recomputed = cand_recomputed = None
                    executed_match = (
                        isinstance(ref_exec, list) and isinstance(cand_exec, list)
                        and isinstance(ref_expected, list) and isinstance(cand_expected, list)
                        and len(ref_exec) > 0 and len(ref_exec) == len(ref_expected)
                        and len(cand_exec) == len(cand_expected)
                        and all(type(value) is int for value in ref_exec + cand_exec)
                        and ref_exec == ref_expected == ref_recomputed
                        and cand_exec == cand_expected == cand_recomputed
                        and int(ref_exec[int(anchor["focal_user"])]) == pair.reference_k1_action
                        and int(cand_exec[int(anchor["focal_user"])]) == pair.candidate_k1_action
                    )
                    reference_opening_evidence = {
                        "rates_k0": row["reference_rates_k0"],
                        "rates_k1": row["reference_rates_k1"],
                        "power_k0": row["reference_power_k0"],
                        "power_k1": row["reference_power_k1"],
                        "actions_k0": row.get("reference_k0_executed_actions"),
                        "actions_k1": ref_exec,
                        "q13_k1": reference_evidence,
                    }
                    gauge = _main_gauge(row, focal_user=int(anchor["focal_user"]),
                                        interval_s=interval_s,
                                        lambda_bits_per_j=lambda_bits_per_j)
                    output_rows.append({
                    "anchor": dict(anchor), "lineage": lineage,
                    "opening_action": pair.action, "reference_action": pair.reference_action,
                    "reference_k1_action": pair.reference_k1_action,
                        "candidate_k1_action": pair.candidate_k1_action,
                    "z2_k1_bits": pair.z2_k1_bits,
                    "z2_k1_normalized": pair.z2_k1_normalized,
                        "candidate_differs_only_at_k0": True,
                        "q2_consulted": False, "sign_filter": False,
                        "policy_sha256": row_policy,
                        "crn_sha256": row.get("crn_sha256"),
                        "reference_target_zero": abs(pairs[pair.reference_action].z2_k1_bits) <= 1e-6,
                        "reference_k1_executed_actions": ref_exec,
                        "candidate_k1_executed_actions": cand_exec,
                        "reference_k1_q13_actions": ref_expected,
                        "candidate_k1_q13_actions": cand_expected,
                        "reference_k1_q13_evidence": reference_evidence,
                        "candidate_k1_q13_evidence": candidate_evidence,
                        "reference_k1_q13_evidence_sha256": canonical_sha256(
                            reference_evidence),
                        "candidate_k1_q13_evidence_sha256": canonical_sha256(
                            candidate_evidence),
                        "reference_k0_executed_actions": row.get(
                            "reference_k0_executed_actions"),
                        "candidate_k0_executed_actions": row.get(
                            "candidate_k0_executed_actions"),
                        "k0_action_mask": row.get("k0_action_mask"),
                        "reference_opening_evidence_sha256": canonical_sha256(
                            reference_opening_evidence),
                        "k1_executed_matches": executed_match,
                        "main_gauge_candidate_rates_k0": row["candidate_rates_k0"],
                        "main_gauge_reference_rates_k0": row["reference_rates_k0"],
                        "main_gauge_candidate_rates_k1": row["candidate_rates_k1"],
                        "main_gauge_reference_rates_k1": row["reference_rates_k1"],
                        "main_gauge_candidate_power_k0": row["candidate_power_k0"],
                        "main_gauge_reference_power_k0": row["reference_power_k0"],
                        "main_gauge_candidate_power_k1": row["candidate_power_k1"],
                        "main_gauge_reference_power_k1": row["reference_power_k1"],
                        "main_gauge": gauge,
                        "main_gauge_interval_s": interval_s,
                        "main_gauge_lambda_bits_per_j": lambda_bits_per_j,
                    })
            # Headroom is selected once per anchor-lineage after all 28
            # signed k1 targets are sealed.  Only those two selected openings
            # are continued through k2/k3; continuation metrics are stored in
            # one control cell, never duplicated in the 28 action rows.
            q1_k0, q3_k0, mask_k0 = rows[0]["q1_k0"], rows[0]["q3_k0"], rows[0]["mask_k0"]
            z2_vector = np.asarray([pair.z2_k1_normalized for pair in pairs], dtype=float)
            oracle, drop = oracle_and_drop_scores(q1_k0, q3_k0, z2_vector, mask_k0)
            selected_rows = {"oracle": (oracle, rows[oracle]), "drop": (drop, rows[drop])}
            control: dict[str, Any] = {"anchor": dict(anchor), "lineage": lineage,
                                       "oracle_action": oracle, "drop_c2_action": drop,
                                       "oracle_drop_tie": oracle == drop,
                                       "tie_trace_reused": oracle == drop,
                                       "interval_s": interval_s,
                                       "q2_consulted": False, "outcome_selection": False}
            for selected, (selected_action, selected_row) in selected_rows.items():
                if not all(f"{selected}_{suffix}" in selected_row
                           for suffix in ("rates_bps", "power_w", "served", "actions")):
                    raise T1RunnerError(f"{key}/{lineage}/{selected_action} lacks the {selected} four-offset continuation")
                trace = {
                    "rates_bps": selected_row[f"{selected}_rates_bps"],
                    "power_w": selected_row[f"{selected}_power_w"],
                    "served": selected_row[f"{selected}_served"],
                    "actions": selected_row[f"{selected}_actions"],
                }
                control[f"{selected}_metrics"] = selected_continuation_metrics(
                    selected_row, policy=selected, interval_s=interval_s
                )
                control[f"{selected}_trace"] = trace
                control[f"{selected}_trace_sha256"] = canonical_sha256(trace)
                reference_fields = tuple(
                    f"{selected}_reference_{suffix}"
                    for suffix in ("rates_bps", "power_w", "served", "actions"))
                if not all(field in selected_row for field in reference_fields):
                    raise T1RunnerError(
                        f"{key}/{lineage}/{selected_action} lacks the {selected} Main reference trace")
                reference_trace = {
                    "rates_bps": selected_row[f"{selected}_reference_rates_bps"],
                    "power_w": selected_row[f"{selected}_reference_power_w"],
                    "served": selected_row[f"{selected}_reference_served"],
                    "actions": selected_row[f"{selected}_reference_actions"],
                }
                reference_row = {
                    f"{selected}_{suffix}": reference_trace[suffix]
                    for suffix in ("rates_bps", "power_w", "served")
                }
                control[f"{selected}_reference_metrics"] = selected_continuation_metrics(
                    reference_row, policy=selected, interval_s=interval_s)
                control[f"{selected}_reference_trace"] = reference_trace
                control[f"{selected}_reference_trace_sha256"] = canonical_sha256(reference_trace)
            control["reference_trace_shared"] = bool(
                control["oracle_reference_trace"] == control["drop_reference_trace"]
                and control["oracle_reference_trace_sha256"]
                == control["drop_reference_trace_sha256"])
            if not control["reference_trace_shared"]:
                raise T1RunnerError(f"{key}/{lineage} oracle/DROP Main reference traces differ")
            control_rows.append(control)
    expected_pairs = 12 * ACTION_COUNT * len(requested)
    expected_controls = 12 * len(requested)
    if len(output_rows) != expected_pairs:
        raise T1RunnerError(f"T1 source row count is not exactly {expected_pairs}")
    if len(control_rows) != expected_controls:
        raise T1RunnerError(f"T1 control row count is not exactly {expected_controls}")
    gates = adjudicate_gates(output_rows, control_rows,
                             expected_pairs=expected_pairs,
                             expected_controls=expected_controls,
                             **({"expected_users": USER_COUNT,
                                 "expected_interval_s": float(T1_FORMULA_CONTRACT["interval_s"]),
                                 "expected_lambda_bits_per_j": LAMBDA_BITS_PER_J,
                                 "expected_kappa_bits": KAPPA_BITS}
                                if prepare_payload.get("schema") == PREPARE_LIVE_SCHEMA else {}))
    payload = {"schema": SOURCE_SCHEMA, "algorithm_schema": SCHEMA,
               "source_rule": SOURCE_RULE, "claim_ceiling": CLAIM_CEILING,
               "prepare_sha256": supplied_prepare_sha,
               "materialized_lineages": list(requested),
               "rows": output_rows, "controls": control_rows, "gates": gates,
               "counts": {"anchors": 12, "lineages": len(requested), "opening_actions": ACTION_COUNT,
                          "pairs": len(output_rows), "controls": len(control_rows)},
               "training": False, "test_split_opened": False,
               "outcome_selection": False, "q2_consulted": False}
    return payload | {"source_sha256": _source_payload_sha256(payload)}


def adjudicate_gates(rows: Sequence[Mapping[str, Any]], controls: Sequence[Mapping[str, Any]], *,
                     expected_pairs: int = 1008, expected_controls: int = 36,
                     expected_users: int | None = None,
                     expected_interval_s: float | None = None,
                     expected_lambda_bits_per_j: float | None = None,
                     expected_kappa_bits: float | None = None) -> dict[str, Any]:
    """Apply predeclared mechanics, EE-finiteness, and service gates."""
    # One physical keyed-random field per anchor/world, shared by every
    # lineage, action, and branch.  A lineage-specific field would turn the
    # three cells into different physical worlds.
    crn_groups: dict[str, set[str]] = {}
    for row in rows:
        if isinstance(row.get("anchor"), Mapping):
            crn_groups.setdefault(_anchor_key(row["anchor"]), set()).add(str(row.get("crn_sha256")))

    def row_user_count(row: Mapping[str, Any]) -> int | None:
        try:
            arrays = tuple(np.asarray(row[name], dtype=np.float64) for name in (
                "main_gauge_candidate_rates_k0", "main_gauge_reference_rates_k0",
                "main_gauge_candidate_rates_k1", "main_gauge_reference_rates_k1"))
            if (any(value.ndim != 1 or value.size <= 0
                    or not np.all(np.isfinite(value)) for value in arrays)
                    or len({value.size for value in arrays}) != 1):
                return None
            count = int(arrays[0].size)
            if expected_users is not None and count != expected_users:
                return None
            return count
        except (KeyError, TypeError, ValueError):
            return None

    row_users: dict[tuple[str, str], int | None] = {}
    row_index: dict[tuple[str, str, int], Mapping[str, Any]] = {}
    for row in rows:
        try:
            key = (_anchor_key(row["anchor"]), str(row["lineage"]))
            count = row_user_count(row)
            previous = row_users.get(key, count)
            row_users[key] = count if previous == count else None
            action = int(row["opening_action"])
            row_index[(key[0], key[1], action)] = row
        except (KeyError, TypeError, ValueError):
            pass

    reference_signatures: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        try:
            key = (_anchor_key(row["anchor"]), str(row["lineage"]))
            evidence = {
                "rates_k0": row["main_gauge_reference_rates_k0"],
                "rates_k1": row["main_gauge_reference_rates_k1"],
                "power_k0": row["main_gauge_reference_power_k0"],
                "power_k1": row["main_gauge_reference_power_k1"],
                "actions_k0": row["reference_k0_executed_actions"],
                "actions_k1": row["reference_k1_executed_actions"],
                "q13_k1": row["reference_k1_q13_evidence"],
            }
            if (row.get("reference_opening_evidence_sha256")
                    != canonical_sha256(evidence)):
                reference_signatures.setdefault(key, set()).add("INVALID")
            else:
                reference_signatures.setdefault(key, set()).add(
                    row["reference_opening_evidence_sha256"])
        except (KeyError, TypeError, ValueError):
            pass
    def gauge_ok(row: Mapping[str, Any]) -> bool:
        try:
            interval = float(row["main_gauge_interval_s"])
            multiplier = float(row["main_gauge_lambda_bits_per_j"])
            recomputed = _main_gauge(row, focal_user=int(row["anchor"]["focal_user"]),
                                     interval_s=interval, lambda_bits_per_j=multiplier,
                                     prefix="main_gauge_")
            supplied = row.get("main_gauge")
            if not isinstance(supplied, Mapping):
                return False
            # Recompute from the persisted arrays and require the producer's
            # persisted scalars to agree, at the declared 1e-9 relative gate.
            tol = float(T1_GATE_CONTRACT["identity_relative_tolerance"]) * max(
                abs(float(recomputed["g0_bits"] + recomputed["g1_bits"])), 1.0)
            return bool(recomputed["identity_passed"] and
                        abs(float(supplied.get("identity_residual_bits")) - float(recomputed["identity_residual_bits"])) <= tol and
                        abs(float(row["z2_k1_bits"]) - float(recomputed["z2_k1_bits"])) <= tol and
                        supplied.get("identity_passed") is True)
        except (KeyError, TypeError, ValueError, IndexError, FloatingPointError):
            return False

    def main_row_ok(row: Mapping[str, Any]) -> bool:
        if row.get("opening_action") != row.get("reference_action"):
            return True
        try:
            return (row["main_gauge_candidate_rates_k0"] == row["main_gauge_reference_rates_k0"]
                    and row["main_gauge_candidate_rates_k1"] == row["main_gauge_reference_rates_k1"]
                    and float(row["main_gauge_candidate_power_k0"]) == float(row["main_gauge_reference_power_k0"])
                    and float(row["main_gauge_candidate_power_k1"]) == float(row["main_gauge_reference_power_k1"])
                    and row.get("reference_k1_executed_actions") == row.get("candidate_k1_executed_actions"))
        except (KeyError, TypeError, ValueError):
            return False

    def reference_control_ok(control: Mapping[str, Any]) -> bool:
        try:
            oracle = control["oracle_reference_trace"]
            drop = control["drop_reference_trace"]
            oracle_sha = control["oracle_reference_trace_sha256"]
            drop_sha = control["drop_reference_trace_sha256"]
            if not bool(
                isinstance(oracle, Mapping) and isinstance(drop, Mapping)
                and set(oracle) == {"rates_bps", "power_w", "served", "actions"}
                and set(drop) == set(oracle)
                and _valid_digest(oracle_sha) and _valid_digest(drop_sha)
                and oracle_sha == canonical_sha256(oracle)
                and drop_sha == canonical_sha256(drop)
                and oracle == drop and oracle_sha == drop_sha
                and control.get("reference_trace_shared") is True
            ):
                return False
            for policy, trace in (("oracle", oracle), ("drop", drop)):
                key = (_anchor_key(control["anchor"]), str(control["lineage"]))
                users = row_users.get(key)
                selected_action = int(control[
                    "oracle_action" if policy == "oracle" else "drop_c2_action"])
                selected_row = row_index.get((key[0], key[1], selected_action))
                rates = np.asarray(trace["rates_bps"], dtype=np.float64)
                power = np.asarray(trace["power_w"], dtype=np.float64)
                served = np.asarray(trace["served"])
                actions = np.asarray(trace["actions"])
                reference_action = (control["anchor"].get("reference_action")
                                    if isinstance(control["anchor"], Mapping)
                                    else None)
                if reference_action is None and selected_row is not None:
                    reference_action = selected_row.get("reference_action")
                if (users is None or selected_row is None
                        or rates.shape != (4, users)
                        or not np.all(np.isfinite(rates))
                        or power.shape != (4,)
                        or not np.all(np.isfinite(power)) or np.any(power <= 0.0)
                        or served.shape != (4, users)
                        or served.dtype != np.bool_
                        or actions.shape != (4, users)
                        or not np.issubdtype(actions.dtype, np.integer)
                        or np.any(actions < -1) or np.any(actions >= ACTION_COUNT)
                        or int(actions[0, int(control["anchor"]["focal_user"])])
                        != int(reference_action)
                        or actions[0].tolist()
                        != selected_row["reference_k0_executed_actions"]
                        or actions[1].tolist()
                        != selected_row["reference_k1_executed_actions"]
                        or not np.array_equal(
                            rates[0], np.asarray(
                                selected_row["main_gauge_reference_rates_k0"],
                                dtype=np.float64))
                        or not np.array_equal(
                            rates[1], np.asarray(
                                selected_row["main_gauge_reference_rates_k1"],
                                dtype=np.float64))
                        or float(power[0]) != float(
                            selected_row["main_gauge_reference_power_k0"])
                        or float(power[1]) != float(
                            selected_row["main_gauge_reference_power_k1"])):
                    return False
                recomputed = selected_continuation_metrics(
                    {f"{policy}_{name}": trace[name]
                     for name in ("rates_bps", "power_w", "served")},
                    policy=policy,
                    interval_s=float(control["interval_s"]))
                if control.get(f"{policy}_reference_metrics") != recomputed:
                    return False
            return True
        except (KeyError, TypeError, ValueError, C2K1ContractError):
            return False

    def k1_execution_ok(row: Mapping[str, Any]) -> bool:
        """Recompute every user's executed action from full Q13 evidence."""
        try:
            ref_exec = row["reference_k1_executed_actions"]
            cand_exec = row["candidate_k1_executed_actions"]
            ref_expected = row["reference_k1_q13_actions"]
            cand_expected = row["candidate_k1_q13_actions"]
            focal = int(row["anchor"]["focal_user"])
            users = row_user_count(row)
            vectors = (ref_exec, cand_exec, ref_expected, cand_expected)
            if (any(not isinstance(value, list) or not value for value in vectors)
                    or len({len(value) for value in vectors}) != 1
                    or users is None or len(ref_exec) != users
                    or not 0 <= focal < len(ref_exec)
                    or any(type(action) is not int or not -1 <= action < ACTION_COUNT
                           for vector in vectors for action in vector)):
                return False
            ref_evidence = row["reference_k1_q13_evidence"]
            cand_evidence = row["candidate_k1_q13_evidence"]
            if (not isinstance(ref_evidence, Mapping)
                    or set(ref_evidence) != {"q13_sum", "mask"}
                    or not isinstance(cand_evidence, Mapping)
                    or set(cand_evidence) != {"q13_sum", "mask"}
                    or row.get("reference_k1_q13_evidence_sha256")
                    != canonical_sha256(ref_evidence)
                    or row.get("candidate_k1_q13_evidence_sha256")
                    != canonical_sha256(cand_evidence)):
                return False
            ref_recomputed = _recompute_k1_q13_actions(
                ref_evidence["q13_sum"], ref_evidence["mask"],
                users=users, field="reference-k1")
            cand_recomputed = _recompute_k1_q13_actions(
                cand_evidence["q13_sum"], cand_evidence["mask"],
                users=users, field="candidate-k1")
            return bool(
                ref_exec == ref_expected == ref_recomputed
                and cand_exec == cand_expected == cand_recomputed
                and ref_exec[focal] == row["reference_k1_action"]
                and cand_exec[focal] == row["candidate_k1_action"]
                and row.get("k1_executed_matches") is True)
        except (KeyError, TypeError, ValueError, IndexError):
            return False

    def k0_intervention_ok(row: Mapping[str, Any]) -> bool:
        """Prove that the opening intervention changes only the focal user."""
        try:
            users = row_user_count(row)
            focal = int(row["anchor"]["focal_user"])
            reference = np.asarray(row["reference_k0_executed_actions"])
            candidate = np.asarray(row["candidate_k0_executed_actions"])
            masks = np.asarray(row["k0_action_mask"])
            if (users is None or reference.shape != (users,)
                    or candidate.shape != (users,)
                    or not np.issubdtype(reference.dtype, np.integer)
                    or not np.issubdtype(candidate.dtype, np.integer)
                    or masks.shape != (users, ACTION_COUNT)
                    or masks.dtype != np.bool_
                    or not 0 <= focal < users
                    or int(reference[focal]) != int(row["reference_action"])
                    or int(candidate[focal]) != int(row["opening_action"])
                    or not np.array_equal(
                        np.delete(candidate, focal), np.delete(reference, focal))):
                return False
            for actions in (reference, candidate):
                for user, action in enumerate(actions.tolist()):
                    if bool(np.any(masks[user])):
                        if not (0 <= int(action) < ACTION_COUNT
                                and bool(masks[user, int(action)])):
                            return False
                    elif int(action) != -1:
                        return False
            return True
        except (KeyError, TypeError, ValueError, IndexError):
            return False

    def arm_control_ok(control: Mapping[str, Any], policy: str) -> bool:
        """Authenticate and recompute one four-offset oracle/DROP trace."""
        try:
            trace = control[f"{policy}_trace"]
            digest = control[f"{policy}_trace_sha256"]
            key = (_anchor_key(control["anchor"]), str(control["lineage"]))
            users = row_users.get(key)
            if (not isinstance(trace, Mapping)
                    or set(trace) != {"rates_bps", "power_w", "served", "actions"}
                    or not _valid_digest(digest)
                    or digest != canonical_sha256(trace)
                    or users is None):
                return False
            rates = np.asarray(trace["rates_bps"], dtype=np.float64)
            power = np.asarray(trace["power_w"], dtype=np.float64)
            served = np.asarray(trace["served"])
            actions = np.asarray(trace["actions"])
            selected_action = int(control[
                "oracle_action" if policy == "oracle" else "drop_c2_action"])
            selected_row = row_index.get((key[0], key[1], selected_action))
            focal = int(control["anchor"]["focal_user"])
            if (rates.shape != (4, users) or not np.all(np.isfinite(rates))
                    or power.shape != (4,) or not np.all(np.isfinite(power))
                    or np.any(power <= 0.0)
                    or served.shape != (4, users) or served.dtype != np.bool_
                    or actions.shape != (4, users)
                    or not np.issubdtype(actions.dtype, np.integer)
                    or np.any(actions < -1) or np.any(actions >= ACTION_COUNT)
                    or selected_row is None
                    or int(actions[0, focal]) != selected_action
                    or actions[0].tolist()
                    != selected_row["candidate_k0_executed_actions"]
                    or actions[1].tolist()
                    != selected_row["candidate_k1_executed_actions"]
                    or not np.array_equal(
                        rates[0], np.asarray(
                            selected_row["main_gauge_candidate_rates_k0"],
                            dtype=np.float64))
                    or not np.array_equal(
                        rates[1], np.asarray(
                            selected_row["main_gauge_candidate_rates_k1"],
                            dtype=np.float64))
                    or float(power[0]) != float(
                        selected_row["main_gauge_candidate_power_k0"])
                    or float(power[1]) != float(
                        selected_row["main_gauge_candidate_power_k1"])):
                return False
            recomputed = selected_continuation_metrics(
                {f"{policy}_{name}": trace[name]
                 for name in ("rates_bps", "power_w", "served")},
                policy=policy,
                interval_s=float(control["interval_s"]))
            return control.get(f"{policy}_metrics") == recomputed
        except (KeyError, TypeError, ValueError, C2K1ContractError):
            return False

    def tie_control_ok(control: Mapping[str, Any]) -> bool:
        try:
            oracle = int(control["oracle_action"])
            drop = int(control["drop_c2_action"])
            if not (0 <= oracle < ACTION_COUNT and 0 <= drop < ACTION_COUNT):
                return False
            if oracle != drop:
                return (control.get("oracle_drop_tie") is False
                        and control.get("tie_trace_reused") is False)
            return bool(
                control.get("oracle_drop_tie") is True
                and control.get("tie_trace_reused") is True
                and control["oracle_trace"] == control["drop_trace"]
                and control["oracle_trace_sha256"]
                == control["drop_trace_sha256"])
        except (KeyError, TypeError, ValueError):
            return False

    def constants_ok(row: Mapping[str, Any]) -> bool:
        try:
            interval = float(row["main_gauge_interval_s"])
            multiplier = float(row["main_gauge_lambda_bits_per_j"])
            z_bits = float(row["z2_k1_bits"])
            z_normalized = float(row["z2_k1_normalized"])
            if not all(math.isfinite(value) for value in
                       (interval, multiplier, z_bits, z_normalized)):
                return False
            if expected_interval_s is not None and interval != expected_interval_s:
                return False
            if (expected_lambda_bits_per_j is not None
                    and multiplier != expected_lambda_bits_per_j):
                return False
            if expected_kappa_bits is not None:
                tolerance = 1e-12 * max(abs(z_normalized), 1.0)
                if abs(z_normalized - z_bits / expected_kappa_bits) > tolerance:
                    return False
            return True
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return False

    def control_constants_ok(control: Mapping[str, Any]) -> bool:
        try:
            interval = float(control["interval_s"])
            return (math.isfinite(interval) and interval > 0.0
                    and (expected_interval_s is None
                         or interval == expected_interval_s))
        except (KeyError, TypeError, ValueError):
            return False

    mechanics = (len(rows) == expected_pairs and len(controls) == expected_controls
        and len(reference_signatures) == expected_controls
        and all(signatures != {"INVALID"} and len(signatures) == 1
                for signatures in reference_signatures.values()) and all(
        row.get("candidate_differs_only_at_k0") is True and row.get("q2_consulted") is False
        and row.get("sign_filter") is False
        and _valid_digest(row.get("policy_sha256"))
        and _valid_digest(row.get("crn_sha256"))
        and constants_ok(row) and k0_intervention_ok(row) and k1_execution_ok(row)
        and gauge_ok(row) and main_row_ok(row) for row in rows
    ) and all(len(values) == 1 for values in crn_groups.values()) and all(control.get("q2_consulted") is False and control.get("outcome_selection") is False
              and control_constants_ok(control)
              and reference_control_ok(control)
              and arm_control_ok(control, "oracle")
              and arm_control_ok(control, "drop")
              and tie_control_ok(control)
              for control in controls) and all(row.get("reference_target_zero") is True for row in rows))
    def recomputed_metrics(control: Mapping[str, Any], policy: str) -> Mapping[str, Any]:
        trace = control[f"{policy}_trace"]
        return selected_continuation_metrics(
            {f"{policy}_{name}": trace[name]
             for name in ("rates_bps", "power_w", "served")},
            policy=policy,
            interval_s=float(control["interval_s"]))

    def pooled(policy: str, selected: Sequence[Mapping[str, Any]] = controls) -> tuple[float, float]:
        metrics = [recomputed_metrics(control, policy) for control in selected]
        bits = math.fsum(float(value["total_bits"]) for value in metrics)
        energy = math.fsum(float(value["total_energy_j"]) for value in metrics)
        if not math.isfinite(bits) or not math.isfinite(energy) or energy <= 0:
            raise T1RunnerError("non-finite pooled EE control")
        return bits, energy

    def pooled_service(policy: str,
                       selected: Sequence[Mapping[str, Any]] = controls) -> float:
        served_count = 0
        total_count = 0
        for control in selected:
            served = np.asarray(control[f"{policy}_trace"]["served"])
            key = (_anchor_key(control["anchor"]), str(control["lineage"]))
            users = row_users.get(key)
            if (users is None or served.dtype != np.bool_
                    or served.shape != (4, users)):
                raise T1RunnerError("malformed pooled service trace")
            served_count += int(np.count_nonzero(served))
            total_count += int(served.size)
        if total_count <= 0:
            raise T1RunnerError("empty pooled service trace")
        return float(served_count / total_count)
    ee = False
    service = False
    lineage_ee_positive = 0
    world_ee_positive = 0
    lineage_service_nonnegative = 0
    try:
        ob, oe = pooled("oracle"); db, de = pooled("drop")
        ee = ob / oe > db / de
        for lineage in LINEAGES:
            subset = [row for row in controls if row.get("lineage") == lineage]
            if subset:
                a, b = pooled("oracle", subset); c, d = pooled("drop", subset)
                lineage_ee_positive += int(a / b > c / d)
                oracle_served = pooled_service("oracle", subset)
                drop_served = pooled_service("drop", subset)
                lineage_service_nonnegative += int(oracle_served >= drop_served)
        for world in sorted({_anchor_key(row["anchor"]) for row in controls}):
            subset = [row for row in controls if _anchor_key(row["anchor"]) == world]
            a, b = pooled("oracle", subset); c, d = pooled("drop", subset)
            world_ee_positive += int(a / b > c / d)
        oracle_fraction = pooled_service("oracle")
        drop_fraction = pooled_service("drop")
        service = (oracle_fraction >= drop_fraction
                   and lineage_service_nonnegative >= int(T1_GATE_CONTRACT["service_nonnegative_lineages"]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError,
            T1RunnerError, C2K1ContractError):
        ee = service = False
    ee_gate = (ee
               and lineage_ee_positive >= int(T1_GATE_CONTRACT["positive_lineages"])
               and world_ee_positive >= int(T1_GATE_CONTRACT["positive_worlds"]))
    return {"G-M": {"passed": mechanics, "disposition": "PASS" if mechanics else "STOP"},
            "G-E": {"passed": ee_gate, "disposition": "PASS" if ee_gate else "STOP",
                    "pooled_oracle_gt_drop": ee, "positive_lineages": lineage_ee_positive,
                    "positive_worlds": world_ee_positive},
            "G-S": {"passed": service, "disposition": "PASS" if service else "STOP",
                    "nonnegative_lineages": lineage_service_nonnegative},
            "launchable": mechanics and ee_gate and service}


def _sealed_anchor_map(prepare_payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    anchors = prepare_payload.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != 12:
        raise T1RunnerError("PREPARE_LIVE does not contain exactly 12 anchors")
    result: dict[str, Mapping[str, Any]] = {}
    per_pool = {pool: 0 for pool in ("early", "mid", "late")}
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            raise T1RunnerError("PREPARE_LIVE contains a malformed anchor")
        if set(anchor) != {
                "pool", "world_id", "step", "focal_user", "reference_action",
                "world_anchor_sha256", "anchor_sha256",
                "reference_physical_key", "incumbent_physical_key",
                "legal_action_mask", "candidate_actions",
                "candidate_physical_keys", "checkpoint_sha256",
                "simulator_source_manifest_sha256", "policy_sha256",
                "evaluation_seed", "predecision_only",
                "physical_main_departure", "complete_forecast_horizon"}:
            raise T1RunnerError("PREPARE_LIVE anchor schema is not exact")
        pool = anchor.get("pool")
        world = anchor.get("world_id")
        step = anchor.get("step")
        focal = anchor.get("focal_user")
        if (pool not in per_pool or type(world) is not int
                or world not in TRAIN_WORLD_POOLS[pool]):
            raise T1RunnerError("PREPARE_LIVE anchor is outside the frozen world pools")
        lo, hi = TRAIN_STEP_WINDOWS[pool]
        if type(step) is not int or not lo <= step <= hi:
            raise T1RunnerError("PREPARE_LIVE anchor is outside its frozen step window")
        if type(focal) is not int or focal < 0:
            raise T1RunnerError("PREPARE_LIVE focal user is malformed")
        key = _anchor_key(anchor)
        if key in result:
            raise T1RunnerError("PREPARE_LIVE contains duplicate anchor identity")
        for field in ("world_anchor_sha256", "anchor_sha256", "checkpoint_sha256",
                      "simulator_source_manifest_sha256", "policy_sha256"):
            _digest(anchor.get(field), field=f"PREPARE_LIVE anchor.{field}")
        reference = anchor.get("reference_action")
        candidates = anchor.get("candidate_actions")
        physical = anchor.get("candidate_physical_keys")
        mask = anchor.get("legal_action_mask")
        reference_physical = anchor.get("reference_physical_key")
        incumbent_physical = anchor.get("incumbent_physical_key")
        if (type(reference) is not int or not 0 <= reference < ACTION_COUNT
                or not isinstance(candidates, list)
                or any(type(action) is not int or not 0 <= action < ACTION_COUNT
                       for action in candidates)
                or set(candidates) != set(range(ACTION_COUNT)) - {reference}
                or not isinstance(physical, list) or len(physical) != ACTION_COUNT - 1
                or any(not isinstance(item, list) or len(item) != 2
                       or any(type(value) is not int for value in item)
                       for item in physical)
                or len({tuple(item) for item in physical}) != ACTION_COUNT - 1
                or not isinstance(reference_physical, list) or len(reference_physical) != 2
                or any(type(value) is not int for value in reference_physical)
                or not isinstance(incumbent_physical, list) or len(incumbent_physical) != 2
                or any(type(value) is not int for value in incumbent_physical)
                or tuple(reference_physical) in {tuple(item) for item in physical}
                or not isinstance(mask, list) or len(mask) != ACTION_COUNT
                or any(type(value) is not bool for value in mask) or not all(mask)):
            raise T1RunnerError("PREPARE_LIVE anchor action topology is malformed")
        if (anchor.get("evaluation_seed") != world
                or anchor.get("predecision_only") is not True
                or anchor.get("physical_main_departure") is not True
                or anchor.get("complete_forecast_horizon") is not True
                or anchor.get("checkpoint_sha256") != prepare_payload.get("main_checkpoint_sha256")
                or anchor.get("simulator_source_manifest_sha256")
                != prepare_payload.get("simulator_source_manifest_sha256")):
            raise T1RunnerError("PREPARE_LIVE anchor authority fields drifted")
        result[key] = anchor
        per_pool[pool] += 1
    if per_pool != {"early": 4, "mid": 4, "late": 4}:
        raise T1RunnerError("PREPARE_LIVE does not contain four anchors per stratum")
    return result


def _validate_live_lineage_bindings(
    prepare_payload: Mapping[str, Any], anchors: Mapping[str, Mapping[str, Any]]
) -> None:
    bindings = prepare_payload.get("lineage_bindings")
    if not isinstance(bindings, Mapping) or set(bindings) != set(anchors):
        raise T1RunnerError("PREPARE_LIVE lineage bindings do not match sealed anchors")
    stable: dict[str, tuple[str, str, str, int]] = {}
    for key in anchors:
        cell = bindings.get(key)
        if not isinstance(cell, Mapping) or set(cell) != set(LINEAGES):
            raise T1RunnerError("PREPARE_LIVE cell does not bind all frozen lineages")
        crn_roots: set[str] = set()
        for index, lineage in enumerate(LINEAGES):
            item = cell.get(lineage)
            if (not isinstance(item, Mapping) or set(item) != {
                    "q1_sha256", "q3_sha256", "hybrid_sha256",
                    "initialization_seed", "crn_sha256",
                    "q13_score_vector", "a_D"}):
                raise T1RunnerError("PREPARE_LIVE lineage binding is malformed")
            q1 = _digest(item.get("q1_sha256"), field=f"{key}/{lineage}/q1")
            q3 = _digest(item.get("q3_sha256"), field=f"{key}/{lineage}/q3")
            hybrid = _digest(item.get("hybrid_sha256"), field=f"{key}/{lineage}/hybrid")
            crn_roots.add(_digest(item.get("crn_sha256"), field=f"{key}/{lineage}/crn"))
            seed = item.get("initialization_seed")
            if seed != Q13_INITIALIZATION_SEEDS[index]:
                raise T1RunnerError("PREPARE_LIVE lineage initialization seed drifted")
            scores = item.get("q13_score_vector")
            if (not isinstance(scores, list) or len(scores) != ACTION_COUNT
                    or any(type(value) not in (int, float) or not math.isfinite(float(value))
                           for value in scores)):
                raise T1RunnerError("PREPARE_LIVE lineage Q1+Q3 vector is malformed")
            a_d = item.get("a_D")
            expected_a_d = min(
                range(ACTION_COUNT), key=lambda action: (-float(scores[action]), action))
            if a_d != expected_a_d:
                raise T1RunnerError("PREPARE_LIVE lineage a_D is not its sealed argmax")
            signature = (q1, q3, hybrid, int(seed))
            if lineage in stable and stable[lineage] != signature:
                raise T1RunnerError("PREPARE_LIVE lineage policy drifted across anchors")
            stable.setdefault(lineage, signature)
        if len(crn_roots) != 1:
            raise T1RunnerError("PREPARE_LIVE physical CRN differs across lineages")


def _validate_live_prepare_for_merge(prepare_payload: Mapping[str, Any]) -> str:
    if prepare_payload.get("schema") != PREPARE_LIVE_SCHEMA:
        raise T1RunnerError("formal merge requires PREPARE_LIVE_SCHEMA")
    if set(prepare_payload) != {
            "schema", "algorithm_schema", "source_rule", "policy_rule",
            "claim_ceiling", "simulator_source_manifest_sha256",
            "q13_gate_source_manifest_sha256", "simulator_prereg_file_sha256",
            "t1_prereg_file_sha256", "formula_contract", "gate_contract",
            "code_authority", "source_authority", "main_dir",
            "main_checkpoint_sha256", "lineages", "anchors",
            "lineage_bindings", "counts", "training", "test_split_opened",
            "outcome_selection", "q2_consulted", "prepared_before_generation",
            "prepare_sha256"}:
        raise T1RunnerError("PREPARE_LIVE top-level schema is not exact")
    unsigned = dict(prepare_payload); supplied = unsigned.pop("prepare_sha256", None)
    if supplied != canonical_sha256(unsigned):
        raise T1RunnerError("PREPARE_LIVE digest is invalid")
    if prepare_payload.get("formula_contract") != T1_FORMULA_CONTRACT or prepare_payload.get("gate_contract") != T1_GATE_CONTRACT:
        raise T1RunnerError("PREPARE_LIVE constants/gates are not frozen")
    if prepare_payload.get("code_authority") != _code_authority_manifest():
        raise T1RunnerError("PREPARE_LIVE code authority drifted before merge")
    if prepare_payload.get("source_authority") != T1_SOURCE_AUTHORITY:
        raise T1RunnerError("PREPARE_LIVE source authority drifted")
    if (prepare_payload.get("algorithm_schema") != SCHEMA
            or prepare_payload.get("source_rule") != SOURCE_RULE
            or prepare_payload.get("policy_rule") != POLICY_RULE
            or prepare_payload.get("claim_ceiling") != CLAIM_CEILING
            or prepare_payload.get("training") is not False
            or prepare_payload.get("test_split_opened") is not False
            or prepare_payload.get("outcome_selection") is not False
            or prepare_payload.get("q2_consulted") is not False
            or prepare_payload.get("prepared_before_generation") is not True
            or not isinstance(prepare_payload.get("main_dir"), str)
            or not Path(str(prepare_payload["main_dir"])).is_absolute()):
        raise T1RunnerError("PREPARE_LIVE target-free authority fields drifted")
    if tuple(prepare_payload.get("lineages", ())) != LINEAGES:
        raise T1RunnerError("PREPARE_LIVE lineages are not the frozen three")
    if prepare_payload.get("counts") != {
        "pools": 3, "worlds": 12, "lineages": 3, "users": USER_COUNT,
        "openings_per_anchor_lineage": ACTION_COUNT,
        "expected_pairs": 1008, "expected_controls": 36,
    }:
        raise T1RunnerError("PREPARE_LIVE cardinality contract drifted")
    _digest(prepare_payload.get("simulator_source_manifest_sha256"),
            field="PREPARE_LIVE simulator source manifest")
    _digest(prepare_payload.get("q13_gate_source_manifest_sha256"),
            field="PREPARE_LIVE Q13 gate source manifest")
    _digest(prepare_payload.get("simulator_prereg_file_sha256"), field="PREPARE_LIVE simulator prereg")
    _digest(prepare_payload.get("t1_prereg_file_sha256"), field="PREPARE_LIVE T1 prereg")
    _digest(prepare_payload.get("main_checkpoint_sha256"), field="PREPARE_LIVE Main checkpoint")
    anchors = _sealed_anchor_map(prepare_payload)
    _validate_live_lineage_bindings(prepare_payload, anchors)
    return str(supplied)


def _read_formal_prepare(prepare_path: Path, t1_prereg_path: Path) -> dict[str, Any]:
    """Authenticate PREPARE_LIVE, its file seal, and current prereg bytes."""
    prepare_file = Path(prepare_path)
    prepared = _canonical_read(prepare_file)
    supplied = _validate_live_prepare_for_merge(prepared)
    seal = _canonical_read(prepare_file.with_name("prepare-live-seal.json"))
    if (set(seal) != {"schema", "prepare_sha256", "prepare_file_sha256",
                      "training", "test_split_opened", "outcome_selection"}
            or seal.get("schema")
            != "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-seal-v2"
            or seal.get("prepare_sha256") != supplied
            or seal.get("prepare_file_sha256") != _file_sha256(prepare_file)
            or seal.get("training") is not False
            or seal.get("test_split_opened") is not False
            or seal.get("outcome_selection") is not False):
        raise T1RunnerError("PREPARE_LIVE file seal is invalid")
    if prepared.get("t1_prereg_file_sha256") != _file_sha256(t1_prereg_path):
        raise T1RunnerError("current T1 prereg differs from PREPARE_LIVE authority")
    return prepared


def _validate_formal_policy_actions(rows: Sequence[Mapping[str, Any]],
                                    controls: Sequence[Mapping[str, Any]],
                                    prepare_payload: Mapping[str, Any]) -> None:
    """Re-derive a_D/a_O from sealed Q13 scores and all 28 signed targets."""
    row_groups: dict[tuple[str, str], dict[int, Mapping[str, Any]]] = {}
    for row in rows:
        try:
            key = (_anchor_key(row["anchor"]), str(row["lineage"]))
            action = int(row["opening_action"])
        except (KeyError, TypeError, ValueError) as exc:
            raise T1RunnerError("formal action row identity is malformed") from exc
        group = row_groups.setdefault(key, {})
        if action in group:
            raise T1RunnerError("formal action row is duplicated")
        group[action] = row
    control_groups: dict[tuple[str, str], Mapping[str, Any]] = {}
    for control in controls:
        try:
            key = (_anchor_key(control["anchor"]), str(control["lineage"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise T1RunnerError("formal control identity is malformed") from exc
        if key in control_groups:
            raise T1RunnerError("formal policy control is duplicated")
        control_groups[key] = control
    if set(row_groups) != set(control_groups):
        raise T1RunnerError("formal action/control cells differ")
    bindings = prepare_payload.get("lineage_bindings")
    if not isinstance(bindings, Mapping):
        raise T1RunnerError("formal action validation lacks sealed Q13 bindings")
    for (anchor_key, lineage), control in control_groups.items():
        group = row_groups[(anchor_key, lineage)]
        if set(group) != set(range(ACTION_COUNT)):
            raise T1RunnerError("formal action cell is not the complete 28 actions")
        binding = bindings.get(anchor_key, {}).get(lineage)
        if not isinstance(binding, Mapping):
            raise T1RunnerError("formal action cell lacks its Q13 binding")
        scores = np.asarray(binding.get("q13_score_vector"), dtype=np.float64)
        targets = np.asarray(
            [group[action].get("z2_k1_normalized")
             for action in range(ACTION_COUNT)], dtype=np.float64)
        if (scores.shape != (ACTION_COUNT,) or targets.shape != (ACTION_COUNT,)
                or not np.all(np.isfinite(scores))
                or not np.all(np.isfinite(targets))):
            raise T1RunnerError("formal action scores/targets are malformed")
        drop = min(range(ACTION_COUNT),
                   key=lambda action: (-float(scores[action]), action))
        oracle = min(range(ACTION_COUNT),
                     key=lambda action: (-float(scores[action] + targets[action]), action))
        if binding.get("a_D") != drop:
            raise T1RunnerError("sealed a_D differs from its Q13 score vector")
        if (control.get("drop_c2_action") != drop
                or control.get("oracle_action") != oracle):
            raise T1RunnerError("formal control a_D/a_O differs from sealed scores and targets")


def merge_sources(shards: Sequence[Mapping[str, Any]],
                  prepare_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Merge disjoint lineage shards and adjudicate the final 1008/36 gate."""
    prepare_sha = _validate_live_prepare_for_merge(prepare_payload)
    anchors = _sealed_anchor_map(prepare_payload)
    if (len(shards) != 3
            or sorted(shard.get("materialized_lineage") for shard in shards) != sorted(LINEAGES)):
        raise T1RunnerError("formal merge requires one exact shard for each Q13 lineage")
    rows: list[Mapping[str, Any]] = []
    controls: list[Mapping[str, Any]] = []
    seen_rows: set[tuple[str, str, int]] = set()
    seen_controls: set[tuple[str, str]] = set()
    for shard in shards:
        lineage = shard.get("materialized_lineage")
        if (shard.get("schema") != SOURCE_SCHEMA or shard.get("training") is not False
                or shard.get("test_split_opened") is not False
                or shard.get("outcome_selection") is not False
                or shard.get("q2_consulted") is not False
                or shard.get("materializer") != "authenticated-v06-live-adapter"
                or lineage not in LINEAGES
                or shard.get("materialized_lineages") != [lineage]
                or shard.get("materializer_code_sha256")
                != prepare_payload["code_authority"]["files"]["live_adapter"]):
            raise T1RunnerError("formal merge rejects a generic or unauthenticated source shard")
        if shard.get("prepare_sha256") != prepare_sha:
            raise T1RunnerError("source shard is not bound to the authenticated PREPARE_LIVE")
        if shard.get("source_sha256") != _source_payload_sha256(shard):
            raise T1RunnerError("source shard digest does not bind its PREPARE_LIVE provenance")
        shard_rows = shard.get("rows")
        shard_controls = shard.get("controls")
        if not isinstance(shard_rows, list) or not isinstance(shard_controls, list):
            raise T1RunnerError("source shard rows/controls are malformed")
        if shard.get("counts") != {
            "anchors": 12, "lineages": 1, "opening_actions": ACTION_COUNT,
            "pairs": 12 * ACTION_COUNT, "controls": 12,
        }:
            raise T1RunnerError("source shard cardinality receipt is malformed")
        local_rows: set[tuple[str, str, int]] = set()
        local_controls: set[tuple[str, str]] = set()
        for row in shard_rows:
            anchor_key = _anchor_key(row["anchor"])
            if anchor_key not in anchors or dict(row["anchor"]) != dict(anchors[anchor_key]):
                raise T1RunnerError("source shard row anchor differs from PREPARE_LIVE")
            key = (anchor_key, str(row["lineage"]), int(row["opening_action"]))
            if key[1] != lineage:
                raise T1RunnerError("source shard row crossed lineage identity")
            if key in seen_rows:
                raise T1RunnerError("duplicate source action row across shards")
            seen_rows.add(key); local_rows.add(key); rows.append(row)
        for control in shard_controls:
            anchor_key = _anchor_key(control["anchor"])
            if anchor_key not in anchors or dict(control["anchor"]) != dict(anchors[anchor_key]):
                raise T1RunnerError("source shard control anchor differs from PREPARE_LIVE")
            key = (anchor_key, str(control["lineage"]))
            if key[1] != lineage:
                raise T1RunnerError("source shard control crossed lineage identity")
            if key in seen_controls:
                raise T1RunnerError("duplicate source control across shards")
            seen_controls.add(key); local_controls.add(key); controls.append(control)
        expected_local_rows = {(key, str(lineage), action)
                               for key in anchors for action in range(ACTION_COUNT)}
        expected_local_controls = {(key, str(lineage)) for key in anchors}
        if local_rows != expected_local_rows or local_controls != expected_local_controls:
            raise T1RunnerError("source shard is not the exact 12x28 lineage cross-product")
        _validate_formal_policy_actions(shard_rows, shard_controls, prepare_payload)
        local_gates = adjudicate_gates(
            shard_rows, shard_controls,
            expected_pairs=12 * ACTION_COUNT, expected_controls=12,
            expected_users=USER_COUNT,
            expected_interval_s=float(T1_FORMULA_CONTRACT["interval_s"]),
            expected_lambda_bits_per_j=LAMBDA_BITS_PER_J,
            expected_kappa_bits=KAPPA_BITS)
        if shard.get("gates") != local_gates:
            raise T1RunnerError("source shard gate adjudication is stale")
    rows.sort(key=lambda row: (_anchor_key(row["anchor"]), str(row["lineage"]), int(row["opening_action"])))
    controls.sort(key=lambda row: (_anchor_key(row["anchor"]), str(row["lineage"])))
    gates = adjudicate_gates(
        rows, controls, expected_users=USER_COUNT,
        expected_interval_s=float(T1_FORMULA_CONTRACT["interval_s"]),
        expected_lambda_bits_per_j=LAMBDA_BITS_PER_J,
        expected_kappa_bits=KAPPA_BITS)
    expected_rows = {(key, lineage, action) for key in anchors
                     for lineage in LINEAGES for action in range(ACTION_COUNT)}
    expected_controls = {(key, lineage) for key in anchors for lineage in LINEAGES}
    if seen_rows != expected_rows or seen_controls != expected_controls:
        raise T1RunnerError("formal merge rows/controls do not exactly match PREPARE_LIVE")
    _validate_formal_policy_actions(rows, controls, prepare_payload)
    payload = {"schema": SOURCE_SCHEMA, "algorithm_schema": SCHEMA,
               "source_rule": SOURCE_RULE, "claim_ceiling": CLAIM_CEILING,
               "prepare_sha256": prepare_sha,
               "materializer": "merged-authenticated-v06-live-adapter",
               "materialized_lineages": list(LINEAGES),
               "code_authority_sha256": prepare_payload["code_authority"]["sha256"],
               "rows": rows, "controls": controls, "gates": gates,
               "counts": {"anchors": 12, "lineages": 3, "opening_actions": ACTION_COUNT,
                          "pairs": len(rows), "controls": len(controls)},
               "training": False, "test_split_opened": False,
               "outcome_selection": False, "q2_consulted": False}
    return payload | {"source_sha256": _source_payload_sha256(payload)}


def seal_source(payload: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    if payload.get("schema") != SOURCE_SCHEMA or payload.get("training") is not False:
        raise T1RunnerError("source payload is not a clean pre-training result")
    if payload.get("source_sha256") != _source_payload_sha256(payload):
        raise T1RunnerError("source payload digest is stale before sealing")
    root = Path(output_dir)
    result_sha = write_once_json(root / "source.json", payload)
    seal = {"schema": SOURCE_SEAL_SCHEMA, "source_sha256": canonical_sha256(payload),
            "source_file_sha256": result_sha,
            "prepare_sha256": payload.get("prepare_sha256"), "training": False,
            "test_split_opened": False, "outcome_selection": False}
    write_once_json(root / "source-seal.json", seal)
    return seal


def verify_source(payload: Mapping[str, Any],
                  prepare_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Independently verify final complete-source counts, identity, and gates."""
    if (payload.get("schema") != SOURCE_SCHEMA
            or payload.get("training") is not False
            or payload.get("test_split_opened") is not False
            or payload.get("outcome_selection") is not False
            or payload.get("q2_consulted") is not False):
        raise T1RunnerError("source is not a clean pre-training artifact")
    prepare_sha = _validate_live_prepare_for_merge(prepare_payload)
    anchors = _sealed_anchor_map(prepare_payload)
    if payload.get("prepare_sha256") != prepare_sha:
        raise T1RunnerError("source is not bound to the authenticated PREPARE_LIVE")
    if (payload.get("materializer") != "merged-authenticated-v06-live-adapter"
            or payload.get("materialized_lineages") != list(LINEAGES)
            or payload.get("code_authority_sha256") != prepare_payload["code_authority"]["sha256"]):
        raise T1RunnerError("source lacks authenticated live materializer provenance")
    rows = payload.get("rows")
    controls = payload.get("controls")
    if not isinstance(rows, list) or not isinstance(controls, list):
        raise T1RunnerError("source rows/controls are malformed")
    if len(rows) != 1008 or len(controls) != 36:
        raise T1RunnerError("source is not the complete 1008-pair/36-control artifact")
    if payload.get("counts") != {
        "anchors": 12, "lineages": 3, "opening_actions": ACTION_COUNT,
        "pairs": 1008, "controls": 36,
    }:
        raise T1RunnerError("source cardinality receipt is malformed")
    row_keys = []
    for row in rows:
        anchor_key = _anchor_key(row["anchor"])
        if anchor_key not in anchors or dict(row["anchor"]) != dict(anchors[anchor_key]):
            raise T1RunnerError("source row anchor differs from PREPARE_LIVE")
        row_keys.append((anchor_key, str(row["lineage"]), int(row["opening_action"])))
    control_keys = []
    for control in controls:
        anchor_key = _anchor_key(control["anchor"])
        if anchor_key not in anchors or dict(control["anchor"]) != dict(anchors[anchor_key]):
            raise T1RunnerError("source control anchor differs from PREPARE_LIVE")
        control_keys.append((anchor_key, str(control["lineage"])))
    if len(set(row_keys)) != 1008 or len(set(control_keys)) != 36:
        raise T1RunnerError("source contains duplicate action or control identity")
    expected_rows = {(key, lineage, action) for key in anchors
                     for lineage in LINEAGES for action in range(ACTION_COUNT)}
    expected_controls = {(key, lineage) for key in anchors for lineage in LINEAGES}
    if set(row_keys) != expected_rows or set(control_keys) != expected_controls:
        raise T1RunnerError("source identities do not exactly match PREPARE_LIVE")
    _validate_formal_policy_actions(rows, controls, prepare_payload)
    expected_digest = _source_payload_sha256(payload)
    if payload.get("source_sha256") != expected_digest:
        raise T1RunnerError("source digest disagrees with rows/controls/gates")
    gates = adjudicate_gates(
        rows, controls, expected_users=USER_COUNT,
        expected_interval_s=float(T1_FORMULA_CONTRACT["interval_s"]),
        expected_lambda_bits_per_j=LAMBDA_BITS_PER_J,
        expected_kappa_bits=KAPPA_BITS)
    if payload.get("gates") != gates:
        raise T1RunnerError("source gate adjudication is stale")
    if gates["G-M"]["passed"] is not True:
        raise T1RunnerError("G-M mechanics/source integrity did not pass")
    disposition = ("AUTHORIZE_ONE_BOUNDED_C2_K1_LEARNER_SCREEN"
                   if gates["launchable"] is True
                   else "C2_K1_SOURCE_FALSIFIED_NO_TRAINING")
    return {"status": "VERIFIED", "disposition": disposition,
            "gates": gates, "pairs": len(rows), "controls": len(controls)}


def _bytes_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise T1RunnerError(f"missing regular policy file: {path}")
    return path.read_bytes()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(_bytes_file(Path(path))).hexdigest()


def _code_authority_manifest() -> dict[str, Any]:
    paths = {
        "runner": HERE / "run_v06_c2_k1_t1.py",
        "live_adapter": HERE / "v06_c2_k1_live_adapter.py",
        "server_launcher": HERE / "launch_v06_c2_k1_t1_server.sh",
        "runtime": REPO / "src/mcrl/runtime/ee_axis_v06_c2_k1.py",
        "support_scanner": HERE / "run_v04_c2_support_complete_census.py",
        "main_loader": HERE / "run_v04_c3_source.py",
        "phase_b_loader": HERE / "run_v04_c2_phase_b.py",
    }
    manifest = {name: _file_sha256(path) for name, path in paths.items()}
    return {"files": manifest, "sha256": canonical_sha256(manifest)}


def _physical_world_field(*, checkpoint_sha256: str, source_manifest_sha256: str,
                          simulator_prereg_file_sha256: str, source_seed: int) -> Any:
    """Build the one immutable CRN root shared by scanner, producer, and shard."""
    from mcrl.env.keyed_fading import KeyedFadingField
    return KeyedFadingField.from_components(
        "multi-catfish-mcrl-v06-c2-k1-physical-world-field-v1",
        checkpoint_sha256, source_manifest_sha256,
        simulator_prereg_file_sha256, int(source_seed))


def _support_census_loader() -> Any:
    """Load the existing support-complete production scanner, not a clone."""
    import importlib.util
    path = HERE / "run_v04_c2_support_complete_census.py"
    name = "v04_support_census_for_v06_" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise T1RunnerError("cannot load authenticated V0.4 support census")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _authenticated_main_dir(modules: Mapping[str, Any], requested: Path) -> Path:
    """Resolve the V0.4 loader's immutable Main directory without guessing.

    The legacy support scanner still reads ``BASE_CHECKPOINT_DIR`` internally.
    V0.6 therefore refuses a CLI path that is not exactly that authenticated
    default rather than silently scanning one checkpoint and sealing another.
    """
    legacy = modules.get("legacy_source")
    default = getattr(legacy, "BASE_CHECKPOINT_DIR", None)
    if default is None:
        raise T1RunnerError("authenticated V0.4 loader has no Main checkpoint directory")
    resolved = Path(requested).resolve()
    expected = Path(default).resolve()
    if resolved != expected:
        raise T1RunnerError(f"main_dir does not match authenticated V0.4 default: {resolved} != {expected}")
    return resolved


class _ReadOnlyModuleView:
    """Expose narrow callable overrides without mutating an authority module."""

    def __init__(self, base: Any, **overrides: Any) -> None:
        self._base = base
        self._overrides = dict(overrides)

    def __getattr__(self, name: str) -> Any:
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._base, name)


def _v06_real_seed_topology(*, support: Any, source_seed: int,
                            modules: Mapping[str, Any], context: Mapping[str, Any],
                            field: Any | None = None,
                            eligible_steps: Sequence[int] | None = None) -> tuple[Any, ...]:
    """Reuse the production scanner with the V0.6 one-focal minimum.

    V0.4's scanner has a four-focal world gate.  V0.6 intentionally needs only
    one eligible focal, so the narrow wrapper changes that gate for the call
    and restores it even on failure; all physical checks remain in the source
    scanner itself.
    """
    scan_modules: Mapping[str, Any] = modules
    if eligible_steps is not None:
        if (
            not eligible_steps
            or any(type(value) is not int or value < 1 for value in eligible_steps)
        ):
            raise T1RunnerError("eligible_steps must contain positive integers")
        allowed_steps = frozenset(eligible_steps)
        backend_smoke = modules.get("backend_smoke")
        pair_smoke = modules.get("pair_smoke")
        if backend_smoke is None or pair_smoke is None:
            raise T1RunnerError("step-window scan lacks decision/departure authorities")
        current_step: dict[str, int | None] = {"value": None}

        def main_decision(trainer: Any, wrapped: Any, states: Any, masks: Any,
                          observation: Any, env_rng: Any) -> Any:
            current_step["value"] = int(observation.step_index)
            return backend_smoke._main_decision(
                trainer, wrapped, states, masks, observation, env_rng)

        def departure_users(wrapped: Any, main_physical: Any) -> tuple[int, ...]:
            departures = tuple(pair_smoke._departure_users(wrapped, main_physical))
            step = current_step["value"]
            if step is None:
                raise T1RunnerError("departure scan occurred before Main decision")
            return departures if step in allowed_steps else ()

        filtered = dict(modules)
        filtered["backend_smoke"] = _ReadOnlyModuleView(
            backend_smoke, _main_decision=main_decision)
        filtered["pair_smoke"] = _ReadOnlyModuleView(
            pair_smoke, _departure_users=departure_users)
        scan_modules = filtered

    old_minimum = support.FOCAL_USERS_PER_WORLD
    loader = modules.get("loader")
    original_make_environment = getattr(loader, "_make_environment", None)
    if field is not None and callable(original_make_environment):
        def make_field_environment(archive: Any, *, users: int) -> Any:
            wrapped = original_make_environment(archive, users=users)
            environment = getattr(wrapped, "environment", wrapped)
            if bool(getattr(environment, "_started", False)):
                raise T1RunnerError("V0.6 field injection occurred after environment start")
            environment._fading_field = field
            return wrapped
        loader._make_environment = make_field_environment
    try:
        support.FOCAL_USERS_PER_WORLD = 1
        return tuple(support._real_seed_topology(
            source_seed=source_seed,
            modules=scan_modules,
            context=context,
        ))
    finally:
        support.FOCAL_USERS_PER_WORLD = old_minimum
        if field is not None and callable(original_make_environment):
            loader._make_environment = original_make_environment


def _live_adapter_loader() -> Any:
    import importlib.util
    path = HERE / "v06_c2_k1_live_adapter.py"
    name = "v06_c2_k1_prepare_live_adapter_" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise T1RunnerError("cannot load V0.6 live adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _phase_b_loader() -> Any:
    """Load the authenticated V0.4 Phase-B gate consumer safely."""
    import importlib.util
    path = HERE / "run_v04_c2_phase_b.py"
    name = "v04_phase_b_for_v06_runner_" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise T1RunnerError("cannot load authenticated V0.4 Phase-B loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _produce_live_lineage_bindings(*, selected: Sequence[Mapping[str, Any]],
                                   tle_root: Path, simulator_prereg: Path,
                                   main_dir: Path, gate_dir: Path,
                                   source_dir: Path, v03_root: Path,
                                   checkpoint_sha256: str,
                                   simulator_source_manifest_sha256: str,
                                   q13_gate_source_manifest_sha256: str,
                                   simulator_prereg_file_sha256: str) -> dict[str, dict[str, Any]]:
    """Create prepare bindings from authenticated hybrids and live states.

    No user-supplied score vector is accepted on this path.  The producer
    replays frozen Main to each already-selected anchor, evaluates each of the
    three authenticated Q13 hybrids on that anchor, and records only the
    target-free Q1+Q3 surface/a_D metadata needed by prepare.
    """
    live = _live_adapter_loader()
    result: dict[str, dict[str, Any]] = {}
    with live.authenticated_runtime(tle_root=Path(tle_root), prereg_path=Path(simulator_prereg),
                                     main_dir=Path(main_dir), gate_dir=Path(gate_dir),
                                     source_dir=Path(source_dir), v03_root=Path(v03_root)) as runtime:
        if runtime.checkpoint_sha256 != checkpoint_sha256:
            raise T1RunnerError("prepare-live producer Main checkpoint drifted")
        if (runtime.q13_gate_source_manifest_sha256
                != q13_gate_source_manifest_sha256):
            raise T1RunnerError("prepare-live producer Q13 source manifest drifted")
        for anchor in selected:
            seed = int(anchor["world_id"])
            field = _physical_world_field(
                checkpoint_sha256=checkpoint_sha256,
                source_manifest_sha256=simulator_source_manifest_sha256,
                simulator_prereg_file_sha256=simulator_prereg_file_sha256,
                source_seed=seed)
            wrapped, history, observation = live.replay_main_to_anchor(
                runtime, runtime.archive, runtime.trainer, source_seed=seed,
                target_step=int(anchor["step"]), field=field)
            if int(observation.step_index) != int(anchor["step"]):
                raise T1RunnerError(f"producer replay step drifted for {_anchor_key(anchor)}")
            reference = np.asarray(history[-1], dtype=np.int64)
            focal = int(anchor["focal_user"])
            if focal >= reference.size or int(reference[focal]) != int(anchor["reference_action"]):
                raise T1RunnerError(f"producer Main reference drifted for {_anchor_key(anchor)}")
            cell: dict[str, Any] = {}
            for lineage in LINEAGES:
                hybrid = runtime.hybrids[lineage]
                q1, q3, masks = live._q13_surfaces(
                    hybrid, wrapped, observation,
                    interval_s=float(T1_FORMULA_CONTRACT["interval_s"]),
                    kappa_bits=KAPPA_BITS)
                focal_mask = np.asarray(masks[focal])
                if focal_mask.shape != (ACTION_COUNT,) or focal_mask.dtype != np.bool_ or not bool(np.all(focal_mask)):
                    raise T1RunnerError(f"producer anchor lacks complete 28-action Q13 mask for {_anchor_key(anchor)}/{lineage}")
                scores = np.asarray(q1[focal] + q3[focal], dtype=np.float64)
                if scores.shape != (ACTION_COUNT,) or not np.all(np.isfinite(scores)):
                    raise T1RunnerError(f"producer Q1+Q3 scores are malformed for {_anchor_key(anchor)}/{lineage}")
                a_d = min(range(ACTION_COUNT), key=lambda action: (-float(scores[action]), action))
                cell[lineage] = {
                    "q1_sha256": live.frozen_network_digest(hybrid.q_nets[0]),
                    "q3_sha256": live.frozen_network_digest(hybrid.q_nets[2]),
                    "hybrid_sha256": runtime.hybrid_hashes[lineage],
                    "initialization_seed": int(hybrid.initialization_seed),
                    "crn_sha256": field.root_digest,
                    "q13_score_vector": [float(value) for value in scores.tolist()],
                    "a_D": int(a_d),
                }
            result[_anchor_key(anchor)] = cell
    return result


def _production_prepare_live(*, tle_root: Path, simulator_prereg: Path,
                             t1_prereg: Path, main_dir: Path,
                             lineage_bindings_path: Path | None, output_dir: Path,
                             gate_dir: Path, source_dir: Path, v03_root: Path) -> dict[str, Any]:
    """Run target-free fixed-pool topology selection through the real scanner.

    This command deliberately stops after topology and frozen-policy binding;
    it does not call a forecast, generate a counterfactual, or train.
    """
    support = _support_census_loader()
    modules = support._production_modules()
    authenticated_main_dir = _authenticated_main_dir(modules, Path(main_dir))
    if Path(output_dir).exists() or Path(output_dir).is_symlink():
        raise T1RunnerError(f"refusing to overwrite prepare-live output: {output_dir}")
    # Authenticate the exact three gate-selected hybrid bytes before accepting
    # the producer's per-cell metadata.  The metadata may contain state-local
    # Q13 score vectors, but its lineage artifact digest must be this receipt's
    # digest for every one of the twelve cells.
    phase_b = _phase_b_loader()
    try:
        q13_gate = phase_b._authenticate_q13_gate(
            Path(gate_dir), source_dir=Path(source_dir),
            prereg_path=Path(simulator_prereg), v03_root=Path(v03_root))
        expected_seeds = tuple(phase_b.Q13_INIT_SEEDS)
        selected_hashes = q13_gate.get("selected_hybrid_file_sha256", {})
        expected_hashes = {lineage: str(selected_hashes[str(seed)])
                           for lineage, seed in zip(LINEAGES, expected_seeds, strict=True)}
        q13_gate_source_manifest_sha256 = _digest(
            q13_gate.get("source_manifest_sha256"),
            field="Q1+Q3 gate source_manifest_sha256")
    except Exception as exc:
        raise T1RunnerError(f"Q1+Q3 gate authentication failed for prepare-live: {exc}") from exc
    with __import__("tempfile").TemporaryDirectory(prefix="mcrl-v06-prepare-live-") as temporary:
        context = support._production_main_context(
            modules=modules, prereg_path=Path(simulator_prereg),
            tle_root=Path(tle_root), temporary=Path(temporary))
        simulator_prereg_sha256 = _file_sha256(simulator_prereg)
        context = dict(context)
        context["prereg_file_sha256"] = simulator_prereg_sha256
        selected: list[dict[str, Any]] = []
        for pool, start in (("early", 2026101001), ("mid", 2026101011), ("late", 2026101021)):
            candidates: list[dict[str, Any]] = []
            for source_seed in range(start, start + 10):
                lo, hi = TRAIN_STEP_WINDOWS[pool]
                topologies = _v06_real_seed_topology(
                    support=support, source_seed=source_seed, modules=modules, context=context,
                    field=_physical_world_field(
                        checkpoint_sha256=context["checkpoint_sha256"],
                        source_manifest_sha256=context["source_manifest_sha256"],
                        simulator_prereg_file_sha256=simulator_prereg_sha256,
                        source_seed=source_seed),
                    eligible_steps=tuple(range(lo, hi + 1)))
                # The first eligible chronology for a source seed is the only
                # admissible world anchor.  Never let a later topology from
                # the same physical seed compete for a fourth slot.
                for topology in sorted(topologies, key=lambda item: int(item.step_index)):
                    if not lo <= int(topology.step_index) <= hi:
                        continue
                    departures = set(int(value) for value in topology.physical_main_departures)
                    focals = tuple(sorted(focal.focal_user for focal in topology.focal_candidates
                                          if focal.focal_user in departures and focal.complete_28_action_census))
                    if not focals:
                        continue
                    focal = int(min(focals))
                    focal_record = next(item for item in topology.focal_candidates
                                        if item.focal_user == focal)
                    candidates.append({"pool": pool, "world_id": source_seed,
                                       "step": int(topology.step_index), "focal_user": focal,
                                       "reference_action": int(focal_record.reference_action),
                                       "world_anchor_sha256": topology.world_anchor_sha256,
                                       "anchor_sha256": focal_record.anchor_sha256,
                                       "reference_physical_key": list(focal_record.reference_physical_key),
                                       "incumbent_physical_key": list(focal_record.incumbent_physical_key),
                                       "legal_action_mask": list(focal_record.legal_action_mask),
                                       "candidate_actions": list(focal_record.candidate_actions),
                                       "candidate_physical_keys": [list(key) for key in focal_record.candidate_physical_keys],
                                       "checkpoint_sha256": context["checkpoint_sha256"],
                                       "source_manifest_sha256": context["source_manifest_sha256"],
                                       "policy_sha256": context["policy_sha256"],
                                       "evaluation_seed": int(topology.evaluation_seed),
                                       "physical_main_departure": focal in topology.physical_main_departures,
                                       "complete_forecast_horizon": bool(topology.complete_forecast_horizon),
                                       "complete_28_action_census": bool(focal_record.complete_28_action_census),
                                       "alias_absence": len(set(focal_record.candidate_physical_keys)) == len(focal_record.candidate_physical_keys)})
                    break
            if len(candidates) < 4:
                raise T1RunnerError(f"prepare-live found only {len(candidates)} eligible {pool} worlds")
            selected.extend(sorted(candidates, key=lambda item: item["world_id"])[:4])
        # The production producer is authoritative.  A bindings JSON, when
        # supplied for debugging, is intentionally not consumed as source
        # truth; all vectors/digests are regenerated from authenticated bytes.
        bindings = _produce_live_lineage_bindings(
            selected=selected, tle_root=Path(tle_root), simulator_prereg=Path(simulator_prereg),
            main_dir=authenticated_main_dir, gate_dir=Path(gate_dir),
            source_dir=Path(source_dir), v03_root=Path(v03_root),
            checkpoint_sha256=context["checkpoint_sha256"],
            simulator_source_manifest_sha256=context["source_manifest_sha256"],
            q13_gate_source_manifest_sha256=q13_gate_source_manifest_sha256,
            simulator_prereg_file_sha256=simulator_prereg_sha256)
        result = build_prepare_live(
            selected, lineage_bindings=bindings,
            simulator_source_manifest_sha256=context["source_manifest_sha256"],
            q13_gate_source_manifest_sha256=q13_gate_source_manifest_sha256,
            simulator_prereg_file_sha256=simulator_prereg_sha256,
            t1_prereg_file_sha256=_file_sha256(t1_prereg),
            main_dir=authenticated_main_dir,
            main_checkpoint_sha256=context["checkpoint_sha256"],
            expected_initialization_seeds=expected_seeds,
            expected_hybrid_hashes=expected_hashes)
    root = Path(output_dir); root.mkdir(parents=True, exist_ok=False)
    prepare_file_sha256 = write_once_json(root / "prepare-live.json", result)
    write_once_json(root / "prepare-live-seal.json", {
        "schema": "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-seal-v2",
        "prepare_sha256": result["prepare_sha256"],
        "prepare_file_sha256": prepare_file_sha256, "training": False,
        "test_split_opened": False, "outcome_selection": False})
    return result


def _production_shard_live(*, prepare_path: Path, tle_root: Path, prereg: Path,
                           main_dir: Path, gate_dir: Path, source_dir: Path,
                           v03_root: Path, lineage: str, output: Path) -> dict[str, Any]:
    """Materialise one authenticated physical lineage shard from live TLE.

    This is intentionally separate from ``generate``: no external rows JSON
    is accepted.  The exact adapter path replays each sealed anchor, executes
    the 28 opening branches, and continues only the selected oracle/DROP pair.
    """
    if lineage not in LINEAGES:
        raise T1RunnerError("shard lineage is not one of the three frozen Q13 lineages")
    prepared = _canonical_read(Path(prepare_path))
    # Authenticate the complete target-free receipt before loading a live
    # runtime or opening any counterfactual outcome.  Partial checks here would
    # let a self-digested but structurally invalid schedule reach simulation.
    supplied = _validate_live_prepare_for_merge(prepared)
    sealed_anchors = _sealed_anchor_map(prepared)
    support = _support_census_loader()
    modules = support._production_modules()
    authenticated_main_dir = _authenticated_main_dir(modules, Path(main_dir))
    if prepared.get("main_dir") != str(authenticated_main_dir):
        raise T1RunnerError("shard main_dir differs from PREPARE_LIVE authority")
    if prepared.get("simulator_prereg_file_sha256") != _file_sha256(prereg):
        raise T1RunnerError("shard simulator prereg digest differs from PREPARE_LIVE authority")
    # Re-authenticate the current simulator source closure separately from the
    # frozen Q13 gate closure.  This is file-only and avoids loading Main/TLE a
    # second time; authenticated_runtime below verifies the checkpoint itself.
    simulator_manifest = support._production_source_manifest(modules)
    if (simulator_manifest.get("source_manifest_sha256")
            != prepared.get("simulator_source_manifest_sha256")):
        raise T1RunnerError("current simulator source manifest differs from PREPARE_LIVE authority")
    live = _live_adapter_loader()
    key_to_payload: dict[str, dict[str, list[Mapping[str, Any]]]] = {}
    with live.authenticated_runtime(tle_root=Path(tle_root), prereg_path=Path(prereg),
                                     main_dir=Path(main_dir), gate_dir=Path(gate_dir),
                                     source_dir=Path(source_dir), v03_root=Path(v03_root)) as runtime:
        checkpoint = prepared.get("main_checkpoint_sha256")
        simulator_source_manifest = prepared.get("simulator_source_manifest_sha256")
        prereg_sha256 = _file_sha256(prereg)
        if not _valid_digest(checkpoint) or not _valid_digest(simulator_source_manifest):
            raise T1RunnerError("prepare-live lacks authenticated Main/source digests")
        if runtime.checkpoint_sha256 != checkpoint:
            raise T1RunnerError("live runtime checkpoint differs from PREPARE_LIVE authority")
        if (runtime.q13_gate_source_manifest_sha256
                != prepared.get("q13_gate_source_manifest_sha256")):
            raise T1RunnerError("live runtime Q13 source manifest differs from PREPARE_LIVE authority")
        for anchor in sealed_anchors.values():
            seed = int(anchor["world_id"])
            binding = prepared.get("lineage_bindings", {}).get(_anchor_key(anchor), {}).get(lineage)
            if not isinstance(binding, Mapping):
                raise T1RunnerError(f"prepare-live lacks sealed binding for {_anchor_key(anchor)}/{lineage}")
            expected_seed = Q13_INITIALIZATION_SEEDS[LINEAGES.index(lineage)]
            if binding.get("initialization_seed") != expected_seed:
                raise T1RunnerError(f"sealed Q13 seed drifted for {_anchor_key(anchor)}/{lineage}")
            if runtime.hybrid_hashes.get(lineage) != binding.get("hybrid_sha256"):
                raise T1RunnerError(f"authenticated hybrid digest drifted for {_anchor_key(anchor)}/{lineage}")
            field = _physical_world_field(
                checkpoint_sha256=checkpoint,
                source_manifest_sha256=simulator_source_manifest,
                simulator_prereg_file_sha256=prereg_sha256,
                source_seed=seed)
            wrapped, history, observation = live.replay_main_to_anchor(
                runtime, runtime.archive, runtime.trainer, source_seed=seed,
                target_step=int(anchor["step"]), field=field)
            if int(observation.step_index) != int(anchor["step"]):
                raise T1RunnerError(f"shard replay step drifted for {_anchor_key(anchor)}")
            table = observation.candidates.slot_tables[int(anchor["focal_user"])]
            actual_mask = np.asarray(table.mask)
            if actual_mask.dtype != np.bool_ or not np.array_equal(actual_mask, np.asarray(anchor["legal_action_mask"], dtype=bool)):
                raise T1RunnerError(f"shard live legal mask differs for {_anchor_key(anchor)}")
            actual_keys = []
            for action in range(ACTION_COUNT):
                association = table.association(action)
                actual_keys.append([int(association.norad_id), int(association.cell_id)])
            if actual_keys[int(anchor["reference_action"])] != anchor["reference_physical_key"]:
                raise T1RunnerError(f"shard Main reference physical key differs for {_anchor_key(anchor)}")
            expected_keys = {int(action): key for action, key in zip(anchor["candidate_actions"], anchor["candidate_physical_keys"], strict=True)}
            if any(actual_keys[action] != key for action, key in expected_keys.items()):
                raise T1RunnerError(f"shard candidate physical keys differ for {_anchor_key(anchor)}")
            result = live.run_one_anchor_lineage(
                runtime, runtime.archive, runtime.hybrids[lineage], source_seed=seed,
                target_step=int(anchor["step"]), focal_user=int(anchor["focal_user"]),
                history=history, field=field,
                interval_s=float(T1_FORMULA_CONTRACT["interval_s"]),
                kappa_bits=KAPPA_BITS, lambda_bits_per_j=LAMBDA_BITS_PER_J,
                hybrid_sha256=runtime.hybrid_hashes[lineage])
            rows = result.get("opening_rows")
            if not isinstance(rows, list) or len(rows) != ACTION_COUNT:
                raise T1RunnerError(f"live shard did not produce 28 rows for {_anchor_key(anchor)}")
            if any(row.get("crn_sha256") != binding["crn_sha256"] or
                   row.get("policy_sha256") != canonical_sha256({
                       "q1_sha256": binding["q1_sha256"], "q3_sha256": binding["q3_sha256"],
                       "hybrid_sha256": binding["hybrid_sha256"],
                       "initialization_seed": binding["initialization_seed"]}) for row in rows):
                raise T1RunnerError(f"live shard row authentication drifted for {_anchor_key(anchor)}/{lineage}")
            observed_scores = np.asarray(rows[0]["q1_k0"], dtype=np.float64) + np.asarray(rows[0]["q3_k0"], dtype=np.float64)
            if not np.array_equal(observed_scores, np.asarray(binding["q13_score_vector"], dtype=np.float64)):
                raise T1RunnerError(f"live shard Q13 k0 vector drifted for {_anchor_key(anchor)}/{lineage}")
            key_to_payload[_anchor_key(anchor)] = {lineage: rows}
    # The generic consumer performs exact pair construction and all G-M/G-E/G-S
    # bookkeeping; it now accepts the sealed PREPARE_LIVE schema and checks the
    # persisted Q13 opening surface against the prepare seal.
    payload = generate(prepared, key_to_payload,
                       interval_s=float(T1_FORMULA_CONTRACT["interval_s"]),
                       lambda_bits_per_j=LAMBDA_BITS_PER_J,
                       kappa_bits=KAPPA_BITS, requested_lineages=(lineage,))
    payload["materializer"] = "authenticated-v06-live-adapter"
    payload["materialized_lineage"] = lineage
    payload["materialized_lineages"] = [lineage]
    payload["materializer_code_sha256"] = prepared["code_authority"]["files"]["live_adapter"]
    payload["prepare_sha256"] = supplied
    payload["source_sha256"] = _source_payload_sha256(payload)
    write_once_json(Path(output), payload)
    return payload


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    info = sub.add_parser("help-contract")
    info.set_defaults(command="help-contract")
    p = sub.add_parser("prepare", help="seal anchors, policy hashes, and gates")
    p.add_argument("--world-records", type=Path, required=True)
    p.add_argument("--q1", type=Path, required=True)
    p.add_argument("--q3", type=Path, required=True)
    p.add_argument("--mask", type=Path, required=True)
    p.add_argument("--source-manifest-sha256", required=True)
    p.add_argument("--simulator-prereg-file-sha256", required=True)
    p.add_argument("--t1-prereg-file-sha256", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    pl = sub.add_parser("prepare-live", help="scan fixed pools and seal target-free production topology")
    pl.add_argument("--tle-root", type=Path, required=True)
    pl.add_argument("--simulator-prereg", type=Path, required=True)
    pl.add_argument("--t1-prereg", type=Path, required=True)
    pl.add_argument("--main-dir", type=Path, required=True)
    pl.add_argument("--lineage-bindings", type=Path,
                    help="deprecated diagnostic input; production bindings are regenerated from authenticated hybrids")
    pl.add_argument("--gate-dir", type=Path, required=True)
    pl.add_argument("--q13-source-dir", type=Path, required=True)
    pl.add_argument("--v03-root", type=Path, required=True)
    pl.add_argument("--output-dir", type=Path, required=True)
    g = sub.add_parser("generate", help="materialise one or all frozen lineages")
    g.add_argument("--prepare", type=Path, required=True)
    g.add_argument("--lineages", type=Path, required=True)
    g.add_argument("--lineage", choices=LINEAGES, action="append")
    g.add_argument("--output", type=Path, required=True)
    g.add_argument("--interval-s", type=float,
                   default=float(T1_FORMULA_CONTRACT["interval_s"]))
    g.add_argument("--lambda-bits-per-j", type=float, default=LAMBDA_BITS_PER_J)
    g.add_argument("--kappa-bits", type=float, default=KAPPA_BITS)
    sh = sub.add_parser("shard", help="materialise one or all frozen lineage shards")
    sh.add_argument("--prepare", type=Path, required=True)
    sh.add_argument("--t1-prereg", type=Path, required=True)
    sh.add_argument("--tle-root", type=Path, required=True)
    sh.add_argument("--prereg", type=Path, required=True)
    sh.add_argument("--main-dir", type=Path, required=True)
    sh.add_argument("--gate-dir", type=Path, required=True)
    sh.add_argument("--q13-source-dir", type=Path, required=True)
    sh.add_argument("--v03-root", type=Path, required=True)
    sh.add_argument("--lineage", choices=LINEAGES, required=True)
    sh.add_argument("--output", type=Path, required=True)
    m = sub.add_parser("merge", help="merge disjoint lineage shards and adjudicate")
    m.add_argument("--shards", type=Path, nargs="+", required=True)
    m.add_argument("--prepare", type=Path, required=True)
    m.add_argument("--t1-prereg", type=Path, required=True)
    m.add_argument("--output-dir", type=Path, required=True)
    v = sub.add_parser("verify", help="verify final source rows and G-M/G-E/G-S")
    v.add_argument("--source", type=Path, required=True)
    v.add_argument("--prepare", type=Path, required=True)
    v.add_argument("--t1-prereg", type=Path, required=True)
    s = sub.add_parser("live-smoke", help="run one authenticated real-TLE anchor/lineage smoke")
    s.add_argument("--tle-root", type=Path, required=True)
    s.add_argument("--prereg", type=Path, required=True)
    s.add_argument("--main-dir", type=Path, required=True)
    s.add_argument("--gate-dir", type=Path, required=True)
    s.add_argument("--q13-source-dir", type=Path, required=True)
    s.add_argument("--v03-root", type=Path, required=True)
    s.add_argument("--lineage", choices=("q13-a", "q13-b", "q13-c"), required=True)
    s.add_argument("--source-seed", type=int, default=2026101001)
    s.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "help-contract":
            print(json.dumps({"schema": SCHEMA, "source_rule": SOURCE_RULE,
                              "claim_ceiling": CLAIM_CEILING, "expected_pairs": 1008,
                              "expected_controls": 36}, sort_keys=True))
            return 0
        if args.command == "prepare":
            records = _canonical_read(args.world_records).get("worlds")
            if not isinstance(records, list):
                raise T1RunnerError("world-records JSON must contain worlds list")
            payload = prepare(records, args.output_dir, q1_bytes=_bytes_file(args.q1),
                              q3_bytes=_bytes_file(args.q3), mask_bytes=_bytes_file(args.mask),
                              source_manifest_sha256=args.source_manifest_sha256,
                              simulator_prereg_file_sha256=args.simulator_prereg_file_sha256,
                              t1_prereg_file_sha256=args.t1_prereg_file_sha256)
            print(json.dumps({"status": "PREPARED", "prepare_sha256": payload["prepare_sha256"]}, sort_keys=True))
            return 0
        if args.command == "prepare-live":
            payload = _production_prepare_live(
                tle_root=args.tle_root, simulator_prereg=args.simulator_prereg,
                t1_prereg=args.t1_prereg, main_dir=args.main_dir,
                lineage_bindings_path=args.lineage_bindings, output_dir=args.output_dir,
                gate_dir=args.gate_dir, source_dir=args.q13_source_dir,
                v03_root=args.v03_root)
            print(json.dumps({"status": "PREPARED_LIVE", "prepare_sha256": payload["prepare_sha256"],
                              "anchors": len(payload["anchors"])}, sort_keys=True))
            return 0
        if args.command in {"generate", "shard"}:
            if args.command == "shard":
                _read_formal_prepare(args.prepare, args.t1_prereg)
                payload = _production_shard_live(
                    prepare_path=args.prepare, tle_root=args.tle_root,
                    prereg=args.prereg, main_dir=args.main_dir,
                    gate_dir=args.gate_dir, source_dir=args.q13_source_dir,
                    v03_root=args.v03_root, lineage=args.lineage,
                    output=args.output)
                print(json.dumps({"status": "SHARD_GENERATED", "pairs": payload["counts"]["pairs"],
                                  "controls": payload["counts"]["controls"], "lineage": args.lineage}, sort_keys=True))
                return 0
            prepared = _canonical_read(args.prepare)
            lineages = _canonical_read(args.lineages)
            payload = generate(prepared, lineages, interval_s=args.interval_s,
                               lambda_bits_per_j=args.lambda_bits_per_j,
                               kappa_bits=args.kappa_bits,
                               requested_lineages=tuple(args.lineage or LINEAGES))
            write_once_json(args.output, payload)
            print(json.dumps({"status": "GENERATED", "pairs": payload["counts"]["pairs"],
                              "controls": payload["counts"]["controls"]}, sort_keys=True))
            return 0
        if args.command == "merge":
            prepared = _read_formal_prepare(args.prepare, args.t1_prereg)
            shards = [_canonical_read(path) for path in args.shards]
            payload = merge_sources(shards, prepared)
            seal = seal_source(payload, args.output_dir)
            print(json.dumps({"status": "MERGED", "pairs": payload["counts"]["pairs"],
                              "controls": payload["counts"]["controls"], "gates": payload["gates"],
                              "source_file_sha256": seal["source_file_sha256"]}, sort_keys=True))
            return 0
        if args.command == "verify":
            prepared = _read_formal_prepare(args.prepare, args.t1_prereg)
            payload = _canonical_read(args.source)
            print(json.dumps(verify_source(payload, prepared), sort_keys=True))
            return 0
        if args.command == "live-smoke":
            live_spec = __import__("importlib.util", fromlist=["spec_from_file_location"])
            live_path = HERE / "v06_c2_k1_live_adapter.py"
            live_name = "v06_c2_k1_live_adapter_cli_" + hashlib.sha256(live_path.read_bytes()).hexdigest()[:16]
            live_loader = live_spec.spec_from_file_location(live_name, live_path)
            if live_loader is None or live_loader.loader is None:
                raise T1RunnerError("cannot load V0.6 live adapter")
            live = live_spec.module_from_spec(live_loader)
            sys.modules[live_name] = live
            try:
                live_loader.loader.exec_module(live)
            except BaseException:
                sys.modules.pop(live_name, None)
                raise
            support = _support_census_loader()
            simulator_manifest = support._production_source_manifest(
                support._production_modules())
            simulator_source_manifest_sha256 = _digest(
                simulator_manifest.get("source_manifest_sha256"),
                field="live-smoke simulator source manifest")
            with live.authenticated_runtime(tle_root=args.tle_root, prereg_path=args.prereg,
                                             main_dir=args.main_dir, gate_dir=args.gate_dir,
                                             source_dir=args.q13_source_dir, v03_root=args.v03_root) as runtime:
                field_base = _physical_world_field(
                    checkpoint_sha256=runtime.checkpoint_sha256,
                    source_manifest_sha256=simulator_source_manifest_sha256,
                    simulator_prereg_file_sha256=runtime.prereg_file_sha256,
                    source_seed=args.source_seed)
                focal, history, observation = live.discover_anchor(
                    runtime, runtime.archive, runtime.trainer, source_seed=args.source_seed,
                    field=field_base, eligible_steps=(1, 2)
                )
                field = _physical_world_field(
                    checkpoint_sha256=runtime.checkpoint_sha256,
                    source_manifest_sha256=simulator_source_manifest_sha256,
                    simulator_prereg_file_sha256=runtime.prereg_file_sha256,
                    source_seed=args.source_seed)
                focal2, history2, observation2 = live.discover_anchor(
                    runtime, runtime.archive, runtime.trainer, source_seed=args.source_seed,
                    field=field, eligible_steps=(1, 2)
                )
                if (focal2, int(observation2.step_index)) != (focal, int(observation.step_index)):
                    raise T1RunnerError("final keyed field changed the predecision anchor")
                history = history2
                observation = observation2
                result = live.run_one_anchor_lineage(
                    runtime, runtime.archive, runtime.hybrids[args.lineage], source_seed=args.source_seed,
                    target_step=int(observation.step_index), focal_user=focal, history=history,
                    field=field, interval_s=float(T1_FORMULA_CONTRACT["interval_s"]),
                    kappa_bits=KAPPA_BITS,
                    lambda_bits_per_j=LAMBDA_BITS_PER_J,
                    hybrid_sha256=runtime.hybrid_hashes[args.lineage]
                )
                result.update({"schema": SOURCE_SCHEMA, "claim_ceiling": CLAIM_CEILING,
                               "training": False, "test_split_opened": False,
                               "prereg_file_sha256": runtime.prereg_file_sha256,
                               "checkpoint_sha256": runtime.checkpoint_sha256,
                               "simulator_source_manifest_sha256": simulator_source_manifest_sha256,
                               "q13_gate_source_manifest_sha256": runtime.q13_gate_source_manifest_sha256,
                               "lineage": args.lineage,
                               "lineage_hybrid_sha256": runtime.hybrid_hashes[args.lineage],
                               "physical_crn_sha256": field.root_digest,
                               "physical_field_receipt": field.receipt(),
                               "source_code_sha256": hashlib.sha256(live_path.read_bytes()).hexdigest()})
                path = args.output_dir / "live-smoke.json"
                write_once_json(path, result)
                print(json.dumps({"status": "LIVE_SMOKE_COMPLETE", "output": str(path)}, sort_keys=True))
            return 0
    # The live adapter is loaded dynamically, so its fail-closed exception
    # class cannot be imported at module import time.  RuntimeError is the
    # deliberately narrow shared boundary (never catches KeyboardInterrupt or
    # SystemExit) and converts live failures into the CLI's declared status.
    except (OSError, T1RunnerError, RuntimeError, ValueError, TypeError,
            ImportError, AttributeError, SyntaxError) as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2
    raise T1RunnerError("unhandled command")


if __name__ == "__main__":
    raise SystemExit(_main())
