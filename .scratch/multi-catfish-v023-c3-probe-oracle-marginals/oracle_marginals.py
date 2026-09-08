#!/usr/bin/env python3
"""TRAIN-only oracle marginal probe over the authenticated E1 panel.

This is deliberately a development diagnostic.  It reconstructs each E1
pre-decision anchor, imports the canonical OPS-3 producer, substitutes exact
one-step C1/C2/C3 targets, and physically scores complete composed profiles.
It never trains, updates, admits, or opens TEST.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-existence-e1"
F1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f1"
F2_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f2"
for _path in (E1_DIR, F1_DIR, F2_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v023_c3_existence_e1 as e1  # noqa: E402


SCHEMA = "multi-catfish-v023-c3-probe-oracle-marginals-v1"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_DIAGNOSTIC_ORACLE_MARGINALS_NO_LEARNER_NO_ADMISSION_NO_TEST"
)
E1_INPUT = Path("/home/sat/mcrl-v023-c3-existence-e1-20260908-r1")
DEFAULT_OUTPUT = Path("/home/sat/mcrl-v023-c3-probe-marginals-20260908-r1")
DESIGN_MEMO = Path(
    "/home/sat/mcrl-v024-regime-b/.scratch/multi-catfish-v024-regime-b-design/"
    "V024-REGIME-B-DESIGN-CODEX-GPT6-ASTRA-ULTRA-2026-09-08.md"
)
MODEL_CONFIG = REPO / ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json"
SCIENTIFIC_DECLARATION = REPO / (
    ".scratch/multi-catfish-v023-c1c2-successor/"
    "V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md"
)
OPS3_FORMULA = REPO / "src/mcrl/runtime/ee_axis_ops3.py"
OPS3_LIVE = REPO / "src/mcrl/runtime/ee_axis_ops3_live.py"

LAMBDA_BITS_PER_J = 118424222.8550065
KAPPA_BITS = 10097071012.757404
DEMANDS_BPS: tuple[tuple[str, float | None], ...] = (
    ("G0", None), ("G1", 200e6), ("G2", 50e6), ("G3", 10e6)
)
ARMS = ("BASE", "O12", "O1", "O2", "O123", "O23", "O13", "ORACLE-J")
MARGINALS = {"C1": ("O123", "O23"), "C2": ("O123", "O13"), "C3": ("O123", "O12")}
THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")


class ProbeError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")).hexdigest()


def cap_bits(rates_bps: object, interval_s: float, demand_bps: float | None) -> np.ndarray:
    rates = np.asarray(rates_bps, dtype=np.float64)
    if rates.ndim != 1 or not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
        raise ProbeError("rates must be a finite nonnegative vector")
    if not math.isfinite(float(interval_s)) or interval_s <= 0.0:
        raise ProbeError("interval must be finite and positive")
    capacity = rates * float(interval_s)
    if demand_bps is None:
        return capacity
    if not math.isfinite(float(demand_bps)) or demand_bps <= 0.0:
        raise ProbeError("finite demand must be positive")
    return np.minimum(capacity, float(demand_bps) * float(interval_s))


def target_triplet(
    base_bits: object,
    candidate_bits: object,
    base_energy_j: float,
    candidate_energy_j: float,
    focal_user: int,
    *,
    lambda_bits_per_j: float = LAMBDA_BITS_PER_J,
) -> tuple[float, float, float]:
    base = np.asarray(base_bits, dtype=np.float64)
    candidate = np.asarray(candidate_bits, dtype=np.float64)
    if base.ndim != 1 or candidate.shape != base.shape or not 0 <= focal_user < base.size:
        raise ProbeError("target vectors/focal user are malformed")
    delta = candidate - base
    delta_energy = float(candidate_energy_j) - float(base_energy_j)
    t1 = float(delta[focal_user]) - float(lambda_bits_per_j) * delta_energy
    t3 = math.fsum(float(value) for index, value in enumerate(delta) if index != focal_user)
    t3_energy = t3 - float(lambda_bits_per_j) * delta_energy
    return t1, t3, t3_energy


def masked_argmax(surface: object, masks: object, *, noop: int = -1) -> np.ndarray:
    values = np.asarray(surface, dtype=np.float64)
    legal = np.asarray(masks)
    if values.ndim != 2 or legal.dtype != np.bool_ or legal.shape != values.shape:
        raise ProbeError("surface/mask shape is malformed")
    if not np.all(np.isfinite(values)):
        raise ProbeError("surface must be finite")
    selected = np.full(values.shape[0], noop, dtype=np.int64)
    eligible = np.any(legal, axis=1)
    selected[eligible] = np.argmax(
        np.where(legal[eligible], values[eligible], -np.inf), axis=1
    )
    return selected


def compose_actions(
    q1_float32: object,
    q2_float32: object,
    t1_bits: object,
    t2_normalized: object,
    t3_bits: object,
    masks: object,
    *,
    kappa_bits: float = KAPPA_BITS,
) -> dict[str, np.ndarray]:
    q1_raw = np.asarray(q1_float32)
    q2_raw = np.asarray(q2_float32)
    if q1_raw.dtype != np.float32 or q2_raw.dtype != np.float32 or q1_raw.shape != q2_raw.shape:
        raise ProbeError("learned Q1/Q2 inputs must be same-shape float32")
    q1 = q1_raw.astype(np.float64)
    q2 = q2_raw.astype(np.float64)
    one = np.asarray(t1_bits, dtype=np.float64) / float(kappa_bits)
    two = np.asarray(t2_normalized, dtype=np.float64)  # already divided once by kappa
    three = np.asarray(t3_bits, dtype=np.float64) / float(kappa_bits)
    if any(value.shape != q1.shape for value in (one, two, three)):
        raise ProbeError("target surfaces do not align with learned surfaces")
    q12_f32 = np.asarray(q1_raw + q2_raw, dtype=np.float32)
    return {
        "BASE": masked_argmax(q12_f32.astype(np.float64), masks),
        "O12": masked_argmax(one + two, masks),
        "O1": masked_argmax(one + q2, masks),
        "O2": masked_argmax(q1 + two, masks),
        "O123": masked_argmax(one + two + three, masks),
        "O23": masked_argmax(q1 + two + three, masks),
        "O13": masked_argmax(one + q2 + three, masks),
    }


def pooled_metrics(rows: Sequence[Mapping[str, object]], demand_bps: float | None) -> dict[str, object]:
    bits = math.fsum(float(row["bits"]) for row in rows)
    energy = math.fsum(float(row["energy_j"]) for row in rows)
    served = sum(int(row["served"]) for row in rows)
    opportunities = sum(int(row["opportunities"]) for row in rows)
    if energy <= 0.0 or opportunities <= 0:
        raise ProbeError("pooled denominator is not positive")
    result: dict[str, object] = {
        "pooled_ee_bits_per_j": bits / energy,
        "delivered_bits": bits,
        "energy_j": energy,
        "service_fraction": served / opportunities,
        "served_user_steps": served,
        "opportunities": opportunities,
    }
    if demand_bps is None:
        result.update({"demand_bits": None, "delivered_over_demand": None, "demand_satisfied_fraction": None})
    else:
        demand_bits = float(demand_bps) * float(e1.INTERVAL_S) * opportunities
        satisfied = sum(int(row["demand_satisfied"]) for row in rows)
        result.update({
            "demand_bits": demand_bits,
            "delivered_over_demand": bits / demand_bits,
            "demand_satisfied_fraction": satisfied / opportunities,
        })
    return result


def _profile_values(profile: Any, demand_bps: float | None) -> tuple[np.ndarray, float, int, int]:
    bits = cap_bits(profile.link_rate_bps, profile.interval_s, demand_bps)
    satisfied = 0 if demand_bps is None else int(np.count_nonzero(
        bits >= float(demand_bps) * float(profile.interval_s)
    ))
    return bits, float(profile.network_energy_j), int(np.count_nonzero(profile.served)), satisfied


def _decode_q12(value: Mapping[str, object]) -> np.ndarray:
    return e1._decode_q12_surface(value)


def _learned_surfaces(physical: Any, frozen: Any, step_env: Any, observation: Any):
    from mcrl.runtime.ee_axis_ops3_live import (
        build_ops3_live_surfaces, project_ops3_anchor, snapshot_ops3_anchor,
    )
    from mcrl.runtime.ee_axis_state import encode_ee_axis_state
    from mcrl.runtime.ee_axis_v014_q2_state import encode_ee_axis_v014_q2_states

    native = encode_ee_axis_state(step_env, observation)
    native.verify()
    masks = np.asarray(native.action_masks, dtype=np.bool_)
    eligible = np.any(masks, axis=1)
    q1 = e1.f1._network_surface_allow_empty(
        physical, frozen.q1, native.state_matrix, masks, field="Q1"
    )
    q1_reference = masked_argmax(np.asarray(q1, dtype=np.float64), masks)
    anchor = snapshot_ops3_anchor(step_env, observation)
    projection = project_ops3_anchor(anchor)
    exact_ops3 = build_ops3_live_surfaces(anchor, projection, q1_reference)
    q2 = np.zeros(masks.shape, dtype=np.float64)
    if np.any(eligible):
        carrier = encode_ee_axis_v014_q2_states(tuple(
            surface for index, surface in enumerate(exact_ops3) if bool(eligible[index])
        ))
        carrier.verify()
        if not np.array_equal(carrier.action_masks, masks[eligible]):
            raise ProbeError("Q2 carrier mask differs from native mask")
        q2[eligible] = physical._surface(
            frozen.q2, carrier.state_matrix, carrier.action_masks, field="Q2"
        )
    return native, np.asarray(q1, dtype=np.float32), np.asarray(q2, dtype=np.float32), q1_reference, anchor, projection, exact_ops3


def _ops3_target_surface(anchor: Any, projection: Any, references: np.ndarray, demand_bps: float | None) -> np.ndarray:
    """Call the imported canonical producer, changing only projected rates."""
    from mcrl.env.link_budget import BEAM_POWER_MAX_W, SEGMENT_START_POWER_W
    from mcrl.runtime.ee_axis_ops3 import build_ops3_surface, opening_service_feasibility_surface

    result = np.zeros((anchor.num_users, e1.f1.NUM_ACTIONS), dtype=np.float64)
    for uid in range(anchor.num_users):
        offsets = projection.offsets_by_user[uid]
        if demand_bps is not None:
            offsets = tuple(replace(
                offset,
                focal_rate_bps=np.minimum(
                    np.asarray(offset.focal_rate_bps, dtype=np.float64), float(demand_bps)
                ),
            ) for offset in offsets)
        surface = build_ops3_surface(
            legal_mask=anchor.legal_mask[uid],
            opening_service_feasible=opening_service_feasibility_surface(
                legal_mask=anchor.legal_mask[uid],
                segment_start_gain_linear=anchor.segment_start_gain_linear[uid],
                current_gain_linear=anchor.current_gain_linear[uid],
                p0_w=SEGMENT_START_POWER_W,
                pmax_w=BEAM_POWER_MAX_W,
            ),
            reference_action=int(references[uid]),
            candidate_norad_ids=anchor.candidate_norad_ids[uid],
            candidate_cell_ids=anchor.candidate_cell_ids[uid],
            segment_start_gain_linear=anchor.segment_start_gain_linear[uid],
            offsets=offsets,
            background=anchor.backgrounds[uid],
            user_count=anchor.num_users,
            step_index=anchor.step_index,
            total_steps=anchor.total_steps,
            lambda_bits_per_j=LAMBDA_BITS_PER_J,
            kappa_bits=KAPPA_BITS,
            interval_s=anchor.decision_step_s,
        )
        result[uid] = surface.q2_values
    return result


def _one_step_surfaces(step: Mapping[str, object], demand_bps: float | None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    masks = np.asarray(step["action_masks"], dtype=np.bool_)
    reference = np.asarray(step["reference_actions"], dtype=np.int64)
    base_profile = e1.f1.profile_from_payload(step["reference_profile"])
    base_bits, base_energy, _, _ = _profile_values(base_profile, demand_bps)
    t1 = np.zeros(masks.shape, dtype=np.float64)
    t3 = np.zeros(masks.shape, dtype=np.float64)
    t3_energy = np.zeros(masks.shape, dtype=np.float64)
    covered = {(user, int(action)) for user, action in enumerate(reference.tolist())}
    for row in step["unilateral_candidates"]:
        user, action = int(row["focal_user"]), int(row["candidate_action"])
        profile = e1.f1.profile_from_payload(row["profile"])
        candidate_bits, candidate_energy, _, _ = _profile_values(profile, demand_bps)
        t1[user, action], t3[user, action], t3_energy[user, action] = target_triplet(
            base_bits, candidate_bits, base_energy, candidate_energy, user
        )
        covered.add((user, action))
    expected = {(user, int(action)) for user, action in enumerate(reference.tolist())}
    keys = step["action_physical_keys"]
    for user in range(masks.shape[0]):
        reference_key = keys[user][int(reference[user])] if np.any(masks[user]) else None
        for raw_action in np.flatnonzero(masks[user]).tolist():
            action = int(raw_action)
            if keys[user][action] != reference_key:
                expected.add((user, action))
    if covered != expected:
        raise ProbeError("unilateral tape did not cover target surface")
    return t1, t3, t3_energy


def _evaluation_row(profile: Any, demand_bps: float | None) -> dict[str, object]:
    bits, energy, served, satisfied = _profile_values(profile, demand_bps)
    return {
        "bits": math.fsum(float(value) for value in bits),
        "energy_j": energy,
        "served": served,
        "opportunities": int(bits.size),
        "demand_satisfied": satisfied,
    }


def _unit_worker(arguments: tuple[int, int, str, str]) -> dict[str, object]:
    world, lineage, e1_root_text, terminal_text = arguments
    for name in THREAD_ENV:
        if os.environ.get(name) != "1":
            raise ProbeError(f"{name}=1 is required")
    e1.pin_single_thread_runtime()
    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.runtime.ee_axis_v04_c3_opening_source import _assert_evaluation_neutral, _evaluation_snapshot
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    e1_root = Path(e1_root_text)
    terminal = json.loads(terminal_text)
    preflight_sha = str(terminal["preflight_manifest_sha256"])
    key = e1.UnitKey(world, lineage)
    _, _, tape = e1.authenticate_unit_bundle(e1_root, key=key, preflight_sha256=preflight_sha)
    physical, server = e1.f1._runtime_modules()
    record = read_prereg(e1.f1.PREREG_PATH)
    if record.digest != e1.f1.PREREG_RECORD_DIGEST:
        raise ProbeError("TRAIN preregistration digest changed")
    frozen = e1.f2._load_frozen_heads(lineage)
    field = KeyedFadingField.from_components(e1.FIELD_COMPONENT, world)
    unit_rows: list[dict[str, object]] = []
    tmp_root = Path(os.environ.get("TMPDIR", str(REPO / ".tmp")))
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"oracle-marginals-{key.slug}-", dir=tmp_root) as temporary:
        archive = server._freeze_archive(record, e1.CANONICAL_TLE_ROOT, Path(temporary) / "frozen", physical)
        environment = server._make_environment(archive)
        step_env = environment.environment
        if getattr(step_env, "_started", False):
            raise ProbeError("environment started before keyed field binding")
        step_env._fading_field = field
        rngs = tuple(_evaluation_rngs(world))
        _, _, observation = environment.reset(rngs[0], rngs[1])
        for step_index, step in enumerate(tape["steps"]):
            if int(observation.step_index) != step_index or int(step["step_index"]) != step_index:
                raise ProbeError("anchor replay step drifted")
            native, q1, q2, q1_ref, anchor, projection, exact_ops3 = _learned_surfaces(
                physical, frozen, step_env, observation
            )
            if native.state_sha256 != step["state_sha256"]:
                raise ProbeError("replayed state digest differs from E1")
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            q12 = np.asarray(q1 + q2, dtype=np.float32)
            if not np.array_equal(q12, _decode_q12(step["q1_q2_float32"])):
                raise ProbeError("reconstructed Q1+Q2 bytes differ from E1")
            reference = np.asarray(step["reference_actions"], dtype=np.int64)
            if not np.array_equal(masked_argmax(q12.astype(np.float64), masks), reference):
                raise ProbeError("reconstructed BASE differs from E1")
            oracle_id = terminal["J1"]["chosen_profiles"][f"{world}:{lineage}:{step_index}"]
            if oracle_id == "BASE":
                oracle_actions = reference.copy()
                oracle_payload = step["reference_profile"]
            else:
                matches = [row for row in step["joint_witness_catalog"] if row["profile_id"] == oracle_id]
                if len(matches) != 1:
                    raise ProbeError("E1 J1 selected profile is absent or duplicated")
                oracle_actions = np.asarray(matches[0]["candidate_joint_actions"], dtype=np.int64)
                oracle_payload = matches[0]["profile"]
            for grid, demand in DEMANDS_BPS:
                t1, t3, t3_energy = _one_step_surfaces(step, demand)
                if demand is None:
                    t2 = np.stack([surface.q2_values for surface in exact_ops3])
                else:
                    t2 = _ops3_target_surface(anchor, projection, q1_ref, demand)
                actions = compose_actions(q1, q2, t1, t2, t3, masks)
                actions["ORACLE-J"] = oracle_actions
                if not np.array_equal(actions["BASE"], reference):
                    raise ProbeError("composed BASE differs from committed E1 BASE")
                for arm in ARMS:
                    before = _evaluation_snapshot(step_env, rngs[0])
                    evaluation = step_env.evaluate_actions(actions[arm], rngs[0])
                    _assert_evaluation_neutral(step_env, rngs[0], before)
                    profile, link_power = e1.f1.profile_from_evaluation(
                        evaluation, interval_s=e1.INTERVAL_S
                    )
                    if arm in ("BASE", "ORACLE-J") and e1.f1.profile_to_payload(
                        profile, link_power_w=link_power
                    ) != (step["reference_profile"] if arm == "BASE" else oracle_payload):
                        raise ProbeError(f"{arm} replay differs from authenticated E1 profile")
                    row = _evaluation_row(profile, demand)
                    row.update({
                        "world": world, "lineage": lineage, "step": step_index,
                        "grid": grid, "arm": arm,
                        "actions_sha256": canonical_sha256([int(value) for value in actions[arm].tolist()]),
                        "changed_users_vs_base": int(np.count_nonzero(actions[arm] != reference)),
                    })
                    unit_rows.append(row)
                # Record target receipts once per grid/anchor without emitting huge matrices.
                unit_rows[-1]["target_receipt"] = {
                    "t1_sha256": hashlib.sha256(np.ascontiguousarray(t1, dtype="<f8").tobytes()).hexdigest(),
                    "t2_sha256": hashlib.sha256(np.ascontiguousarray(t2, dtype="<f8").tobytes()).hexdigest(),
                    "t3_sha256": hashlib.sha256(np.ascontiguousarray(t3, dtype="<f8").tobytes()).hexdigest(),
                    "t3_energy_variant_sha256": hashlib.sha256(np.ascontiguousarray(t3_energy, dtype="<f8").tobytes()).hexdigest(),
                    "t3_energy_variant_min": float(np.min(t3_energy[masks])) if np.any(masks) else 0.0,
                    "t3_energy_variant_max": float(np.max(t3_energy[masks])) if np.any(masks) else 0.0,
                }
            # Advance only the authenticated deployed BASE, after every grid counterfactual.
            environment.step(reference, rngs[0])
            committed = environment.last_outcome
            committed_profile, committed_power = e1.f1.profile_from_evaluation(committed, interval_s=e1.INTERVAL_S)
            if e1.f1.profile_to_payload(committed_profile, link_power_w=committed_power) != step["reference_profile"]:
                raise ProbeError("committed BASE advancement differs from E1")
            if step_index < len(tape["steps"]) - 1:
                observation = committed.observation
    return {"world": world, "lineage": lineage, "rows": unit_rows}


def _input_digests(e1_root: Path) -> list[dict[str, object]]:
    paths = [MODEL_CONFIG, SCIENTIFIC_DECLARATION, DESIGN_MEMO, OPS3_FORMULA, OPS3_LIVE,
             E1_DIR / "run_v023_c3_existence_e1.py", e1_root / "terminal-receipt.json",
             e1_root / "budget-ledger.json", E1_DIR / "E1-PREFLIGHT-MANIFEST.json"]
    paths.extend(sorted((e1_root / "units").glob("*/*")))
    paths.extend(sorted(path for path in e1.CANONICAL_TLE_ROOT.rglob("*") if path.is_file()))
    # Loaded lineage checkpoint/authority files are already named in the E1 receipts.
    for receipt_path in sorted((e1_root / "units").glob("*/receipt.json")):
        receipt = json.loads(receipt_path.read_text())
        for binding in (receipt["lineage_authority"]["checkpoint"], receipt["lineage_authority"]["q12_authority"]):
            paths.append(REPO / str(binding["path"]))
    unique = sorted({path.resolve() for path in paths if path.is_file()}, key=str)
    return [{"path": str(path), "sha256": file_sha256(path), "bytes": path.stat().st_size} for path in unique]


def estimate(e1_root: Path) -> dict[str, object]:
    receipts = [json.loads(path.read_text()) for path in sorted((e1_root / "units").glob("*/receipt.json"))]
    anchors = sum(int(row["counts"]["anchors"]) for row in receipts)
    unilateral = sum(int(row["counts"]["unilateral_profiles"]) for row in receipts)
    return {
        "units": len(receipts), "anchors": anchors, "grids": len(DEMANDS_BPS), "arms": len(ARMS),
        "composed_physical_evaluations": anchors * len(DEMANDS_BPS) * len(ARMS),
        "base_advancement_evaluations": anchors,
        "new_unilateral_physical_evaluations": 0,
        "reused_authenticated_unilateral_profiles": unilateral,
        "ops3_live_projections": anchors,
        "maximum_workers": 8,
    }


def summarize(units: Sequence[Mapping[str, object]], input_digests: Sequence[Mapping[str, object]], elapsed: float) -> dict[str, object]:
    rows = [row for unit in units for row in unit["rows"]]
    summary: dict[str, object] = {}
    for grid, demand in DEMANDS_BPS:
        grid_rows = [row for row in rows if row["grid"] == grid]
        arms: dict[str, object] = {}
        for arm in ARMS:
            metrics = pooled_metrics([row for row in grid_rows if row["arm"] == arm], demand)
            arms[arm] = metrics
        base_ee = float(arms["BASE"]["pooled_ee_bits_per_j"])
        for metrics in arms.values():
            value = float(metrics["pooled_ee_bits_per_j"])
            metrics["percent_vs_base"] = 100.0 * (value / base_ee - 1.0)
        marginals = {}
        for head, (full, drop) in MARGINALS.items():
            full_ee = float(arms[full]["pooled_ee_bits_per_j"])
            drop_ee = float(arms[drop]["pooled_ee_bits_per_j"])
            marginals[head] = {
                "ee_delta_bits_per_j": full_ee - drop_ee,
                "percent_of_drop": 100.0 * (full_ee / drop_ee - 1.0),
                "positive": full_ee > drop_ee,
            }
        worlds = {}
        for world in e1.WORLDS:
            world_rows = [row for row in grid_rows if row["world"] == world]
            world_arms = {arm: pooled_metrics([row for row in world_rows if row["arm"] == arm], demand) for arm in ARMS}
            world_base = float(world_arms["BASE"]["pooled_ee_bits_per_j"])
            for metrics in world_arms.values():
                metrics["percent_vs_base"] = 100.0 * (float(metrics["pooled_ee_bits_per_j"]) / world_base - 1.0)
            world_marginals = {}
            for head, (full, drop) in MARGINALS.items():
                a = float(world_arms[full]["pooled_ee_bits_per_j"])
                b = float(world_arms[drop]["pooled_ee_bits_per_j"])
                world_marginals[head] = {"ee_delta_bits_per_j": a - b, "percent_of_drop": 100.0 * (a / b - 1.0), "positive": a > b}
            worlds[str(world)] = {"arms": world_arms, "marginals": world_marginals}
        summary[grid] = {"demand_bps": demand, "arms": arms, "marginals": marginals, "worlds": worlds}
    return {
        "schema": SCHEMA, "status": "COMPLETE", "claim_ceiling": CLAIM_CEILING,
        "task_exit": "DONE", "split": "TRAIN", "test_split_opened": False,
        "episode_training": False, "learner_update": False, "admission_authority": False,
        "efficacy_claim": False, "elapsed_seconds": elapsed,
        "constants": {"lambda_bits_per_j": LAMBDA_BITS_PER_J, "kappa_bits": KAPPA_BITS,
            "interval_s": e1.INTERVAL_S, "field_component": e1.FIELD_COMPONENT},
        "scaling": {
            "learned_q1_q2": "float32 network outputs promoted to float64 for mixed composition",
            "t1": "raw one-step bits-minus-lambda-joules divided exactly once by kappa",
            "t2": "canonical OPS3 reference-centered q2_values already divided by kappa; never divided again",
            "t3": "raw nonfocal delivered-bit delta divided exactly once by kappa",
            "composition": "unweighted masked argmax; lowest action index on ties; empty mask -> NOOP=-1",
        },
        "estimate": estimate(E1_INPUT), "input_digests": list(input_digests),
        "units_sha256": canonical_sha256(units), "anchor_rows": rows, "results": summary,
    }


def markdown_report(payload: Mapping[str, object]) -> str:
    lines = [
        "# V0.23 C1/C2/C3 oracle marginals — TRAIN development diagnostic", "",
        f"Claim ceiling: `{CLAIM_CEILING}`", "",
        "Scaling: C1 and C3 raw bit-valued targets receive exactly one `/κ`; imported OPS-3 `q2_values` are already reference-centered and `/κ`-normalised and are never divided again. Learned float32 Q1/Q2 are promoted to float64 before mixed composition. Ties use the lowest legal index; an empty mask uses NOOP `-1`.", "",
    ]
    for grid, block in payload["results"].items():
        demand = block["demand_bps"]
        lines.extend([f"## {grid} — demand {'∞' if demand is None else f'{float(demand)/1e6:g} Mbit/s/user'}", "",
                      "| Arm | pooled EE (bit/J) | % vs BASE | service | delivered/demand | demand satisfied |", "|---|---:|---:|---:|---:|---:|"])
        for arm in ARMS:
            row = block["arms"][arm]
            ratio = "n/a" if row["delivered_over_demand"] is None else f"{100*float(row['delivered_over_demand']):.6f}%"
            sat = "n/a" if row["demand_satisfied_fraction"] is None else f"{100*float(row['demand_satisfied_fraction']):.6f}%"
            lines.append(f"| {arm} | {float(row['pooled_ee_bits_per_j']):.9f} | {float(row['percent_vs_base']):+.6f}% | {100*float(row['service_fraction']):.6f}% | {ratio} | {sat} |")
        lines.extend(["", "| Marginal | EE delta (bit/J) | % of DROP | positive? |", "|---|---:|---:|:---:|"])
        for head in ("C1", "C2", "C3"):
            row = block["marginals"][head]
            lines.append(f"| {head} | {float(row['ee_delta_bits_per_j']):+.9f} | {float(row['percent_of_drop']):+.6f}% | {'YES' if row['positive'] else 'NO'} |")
        lines.extend(["", "Per-world marginal EE deltas (bit/J):", "", "| World | C1 | C2 | C3 |", "|---:|---:|---:|---:|"])
        for world, world_block in block["worlds"].items():
            lines.append("| " + world + " | " + " | ".join(f"{float(world_block['marginals'][head]['ee_delta_bits_per_j']):+.9f}" for head in ("C1", "C2", "C3")) + " |")
        lines.append("")
    lines.extend(["## Integrity", "", f"- Input files digested: {len(payload['input_digests'])}",
                  f"- Physical composed evaluations: {payload['estimate']['composed_physical_evaluations']}",
                  f"- Runtime: {float(payload['elapsed_seconds']):.3f} s", "- TEST opened: no", "- Learner/training/update: no", "- Admission or efficacy authority: no", ""])
    return "\n".join(lines)


def _write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run(args: argparse.Namespace) -> int:
    if args.workers < 1 or args.workers > 8:
        raise ProbeError("--workers must be between 1 and 8")
    if Path(args.e1_input).resolve() != E1_INPUT.resolve():
        raise ProbeError("E1 input root is fixed and read-only")
    for name in THREAD_ENV:
        if os.environ.get(name) != "1":
            raise ProbeError(f"{name}=1 is required")
    e1.pin_single_thread_runtime()
    config = json.loads(MODEL_CONFIG.read_text())
    if float(config["q1"]["kappa_bits"]) != KAPPA_BITS or float(config["q2"]["kappa_bits"]) != KAPPA_BITS:
        raise ProbeError("model config kappa differs from authenticating constant")
    if e1.f1.LAMBDA_BITS_PER_J != LAMBDA_BITS_PER_J or e1.f1.KAPPA_BITS != KAPPA_BITS:
        raise ProbeError("E1/F1 lambda or kappa binding differs")
    estimate_payload = estimate(Path(args.e1_input))
    if args.estimate:
        print(json.dumps(estimate_payload, indent=2, sort_keys=True))
        return 0
    output = Path(args.output)
    json_path, markdown_path = output / "oracle-marginals.json", output / "oracle-marginals.md"
    if json_path.exists() or markdown_path.exists():
        raise ProbeError("write-once output already exists")
    terminal = json.loads((E1_INPUT / "terminal-receipt.json").read_text())
    if terminal.get("status") != "COMPLETE" or terminal.get("test_split_opened") is not False:
        raise ProbeError("E1 terminal receipt is not a closed-TEST complete input")
    work = [(key.world, key.lineage, str(E1_INPUT), json.dumps(terminal, separators=(",", ":"))) for key in e1.ALL_UNITS]
    started = time.monotonic()
    context = mp.get_context("spawn")
    with context.Pool(processes=args.workers) as pool:
        units = list(pool.imap_unordered(_unit_worker, work, chunksize=1))
    units.sort(key=lambda row: (int(row["world"]), int(row["lineage"])))
    if len(units) != 12:
        raise ProbeError("unit count drifted")
    digests = _input_digests(E1_INPUT)
    payload = summarize(units, digests, time.monotonic() - started)
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    report = markdown_report(payload).encode("utf-8")
    _write_exclusive(json_path, encoded)
    try:
        _write_exclusive(markdown_path, report)
    except BaseException:
        json_path.unlink(missing_ok=True)
        raise
    print(json.dumps({"json": str(json_path), "markdown": str(markdown_path), "sha256": {
        json_path.name: file_sha256(json_path), markdown_path.name: file_sha256(markdown_path)
    }}, indent=2, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--estimate", action="store_true")
    result.add_argument("--workers", type=int, default=4)
    result.add_argument("--e1-input", type=Path, default=E1_INPUT)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return result


if __name__ == "__main__":
    try:
        raise SystemExit(run(parser().parse_args()))
    except Exception as error:
        print(f"TASK_EXIT=BLOCKED {type(error).__name__}: {error}", file=sys.stderr)
        raise
