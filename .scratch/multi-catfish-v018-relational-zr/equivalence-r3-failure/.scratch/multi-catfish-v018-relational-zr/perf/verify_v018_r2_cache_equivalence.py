#!/usr/bin/env python3
"""Full 100-user public-surface equivalence check for the V0.18 R2 cache."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
from pathlib import Path
import sys
import tempfile
import time
import traceback
from typing import Any
from unittest.mock import patch

import numpy as np


REPO = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO / ".scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py"
R1_PATH = REPO / ".scratch/multi-catfish-v018-relational-zr/r1-abort/ee_axis_relational_zr_c3-r1.py"
CONTRACT_PATH = REPO / ".scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-R3-CACHE-EQUIVALENCE-CHECK-2026-09-04.md"
R1_SHA256 = "6a3d61940175f0e4e422fa4ac9818fd64652dd4f6e699408f6189cec164425a2"
R2_SHA256 = "e66f61d7ad8833115eb0542ca2b4ea6718a23ecc26aa0729f5cf879c64cf6166"
PREREG_SHA256 = "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
WORLD_SEED = 2026104901
LINEAGE = 2026092101
CONTEXTS = (12, 1, 2)
MAX_WORKERS = 18
RESULT_SCHEMA = "multi-catfish-mcrl-v018-r2-cache-equivalence-v1"

for path in (REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = _load_module("v018_r2_equivalence_runner", RUNNER_PATH)
R1 = _load_module("mcrl.runtime.ee_axis_relational_zr_c3_r1_reference", R1_PATH)

import mcrl.runtime.ee_axis_relational_zr_c3 as R2  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402


_WORK: dict[str, Any] = {}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def validate_contract() -> str:
    if not CONTRACT_PATH.is_file() or CONTRACT_PATH.is_symlink():
        raise RuntimeError("equivalence contract is missing or symlinked")
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    if "Status: `FROZEN_BEFORE_CHECK`" not in text:
        raise RuntimeError("equivalence contract is not frozen before check")
    if file_sha256(R1_PATH) != R1_SHA256:
        raise RuntimeError("sealed R1 reference hash mismatch")
    if file_sha256(Path(R2.__file__).resolve()) != R2_SHA256:
        raise RuntimeError("R2 cached runtime hash mismatch")
    if file_sha256(RUNNER.DEFAULT_PREREG) != PREREG_SHA256:
        raise RuntimeError("frozen base preregistration hash mismatch")
    return file_sha256(CONTRACT_PATH)


def _old_user_branches(uid: int) -> list[tuple[tuple[int, ...], np.ndarray, np.ndarray]]:
    refs = _WORK["refs"]
    opening = _WORK["opening"]
    legal = _WORK["legal"]
    results: list[tuple[tuple[int, ...], np.ndarray, np.ndarray]] = []
    for action_raw in np.flatnonzero(legal[uid]).tolist():
        action = int(action_raw)
        branch = R1._branch_actions(refs, focal_user=uid, focal_action=action)
        served = R1._branch_served(branch, opening, legal)
        rates, interference = R1._nominal_rates(
            environment=_WORK["environment"],
            actions=branch,
            served=served,
            required_power=_WORK["power"],
            signal_surface=_WORK["signal"],
            norads=_WORK["norads"],
            cells=_WORK["cells"],
            legal=legal,
            colours=_WORK["colours"],
            centres=_WORK["centres"],
            positions=_WORK["positions"],
            users_ecef=_WORK["users_ecef"],
        )
        results.append(
            (
                tuple(int(value) for value in branch.tolist()),
                np.asarray(rates, dtype=np.float64),
                np.asarray(interference, dtype=np.float64),
            )
        )
    return results


def _masked_argmax(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    return np.argmax(np.where(masks, scores, -np.inf), axis=1).astype(np.int64)


def _minimum_top_two_margin(scores: np.ndarray, masks: np.ndarray) -> float:
    margins: list[float] = []
    for row, mask in zip(scores, masks, strict=True):
        legal = np.asarray(row)[np.asarray(mask)]
        if legal.size < 2:
            continue
        ordered = np.partition(legal, -2)
        margins.append(float(ordered[-1] - ordered[-2]))
    return min(margins) if margins else math.inf


def _context_result(
    *,
    environment: Any,
    observation: Any,
    references: np.ndarray,
    background: np.ndarray,
    required: np.ndarray,
    opening: np.ndarray,
    workers: int,
) -> dict[str, Any]:
    tables, legal = R1._anchor(environment, observation)
    refs, power, opening_values, identity = R1._validate_context_inputs(
        tables, legal, references, required, opening
    )
    norads = identity[:, :, 0]
    cells = identity[:, :, 1]
    centres, colours, positions = R1._grid_data(
        environment, observation, norads, cells
    )
    users_ecef = R1._user_positions(environment, len(tables))
    theta, slant, elevation = R1._candidate_geometry(
        environment,
        observation,
        norads,
        cells,
        centres,
        positions,
        users_ecef,
    )
    signal = R1._nominal_signal_surface(
        theta=theta,
        slant=slant,
        elevation=elevation,
        required_power=power,
        legal=legal,
    )
    reference_branch = R1._branch_actions(refs)
    reference_served = R1._branch_served(reference_branch, opening_values, legal)
    reference_rates, reference_interference = R1._nominal_rates(
        environment=environment,
        actions=reference_branch,
        served=reference_served,
        required_power=power,
        signal_surface=signal,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )

    interval_s = float(environment.driver.config.ephemeris.time_step_s)
    r2_delta, r2_q3 = R2.nominal_relational_zr_surface(
        environment,
        observation,
        reference_actions=refs,
        required_power_surface=power,
        opening_feasibility_surface=opening_values,
        interval_s=interval_s,
        kappa_bits=RUNNER.OPS3_KAPPA_BITS,
        pmax_w=RUNNER.BEAM_POWER_MAX_W,
    )
    r2_state = R2.encode_relational_zr_c3_state(
        environment,
        observation,
        reference_actions=refs,
        required_power_surface=power,
        opening_feasibility_surface=opening_values,
        pmax_w=RUNNER.BEAM_POWER_MAX_W,
    )

    global _WORK
    _WORK = {
        "environment": environment,
        "refs": refs,
        "opening": opening_values,
        "power": power,
        "signal": signal,
        "norads": norads,
        "cells": cells,
        "legal": legal,
        "colours": colours,
        "centres": centres,
        "positions": positions,
        "users_ecef": users_ecef,
    }
    started = time.perf_counter()
    branch_results: dict[tuple[int, ...], tuple[np.ndarray, np.ndarray]] = {
        tuple(int(value) for value in reference_branch.tolist()): (
            np.asarray(reference_rates, dtype=np.float64),
            np.asarray(reference_interference, dtype=np.float64),
        )
    }
    context = mp.get_context("fork")
    with context.Pool(processes=workers) as pool:
        for rows in pool.imap_unordered(
            _old_user_branches, range(len(tables)), chunksize=1
        ):
            for key, rates, interference in rows:
                branch_results[key] = (rates, interference)
    reference_elapsed_s = time.perf_counter() - started

    # Compare the cached primitive itself across every legal unilateral
    # branch.  C3 deliberately removes the focal user's own outcome, so the
    # primitive contract is equality on every non-focal reference victim.
    # Public delta/state comparisons below separately verify that this
    # exclusion is propagated exactly through the complete C3 surfaces.
    r2_cache = R2._build_nominal_reference_cache(
        environment=environment,
        refs=refs,
        opening=opening_values,
        power=power,
        signal=signal,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )
    maximum_rate_deviation = 0.0
    maximum_interference_deviation = 0.0
    checked_nonfocal_values = 0
    for uid in range(len(tables)):
        nonfocal = np.arange(len(tables)) != uid
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            branch = R1._branch_actions(refs, focal_user=uid, focal_action=action)
            key = tuple(int(value) for value in branch.tolist())
            r1_rates, r1_interference = branch_results[key]
            cached_rates, cached_interference = R2._cached_nominal_nonfocal_branch(
                r2_cache,
                focal_user=uid,
                focal_action=action,
                opening=opening_values,
                power=power,
                norads=norads,
                cells=cells,
            )
            np.testing.assert_allclose(
                r1_rates[nonfocal],
                cached_rates[nonfocal],
                rtol=1e-12,
                atol=1e-9,
            )
            np.testing.assert_allclose(
                r1_interference[nonfocal],
                cached_interference[nonfocal],
                rtol=1e-12,
                atol=1e-18,
            )
            maximum_rate_deviation = max(
                maximum_rate_deviation,
                float(np.max(np.abs(r1_rates[nonfocal] - cached_rates[nonfocal]))),
            )
            maximum_interference_deviation = max(
                maximum_interference_deviation,
                float(
                    np.max(
                        np.abs(
                            r1_interference[nonfocal]
                            - cached_interference[nonfocal]
                        )
                    )
                ),
            )
            checked_nonfocal_values += int(np.count_nonzero(nonfocal))

    def rate_dispatch(*args: object, **kwargs: object) -> tuple[np.ndarray, np.ndarray]:
        actions = kwargs.get("actions", args[1] if len(args) > 1 else None)
        key = tuple(int(value) for value in np.asarray(actions).tolist())
        rates, interference = branch_results[key]
        return np.array(rates, copy=True), np.array(interference, copy=True)

    def interference_dispatch(*args: object, **kwargs: object) -> np.ndarray:
        actions = kwargs.get("actions", args[0] if args else None)
        key = tuple(int(value) for value in np.asarray(actions).tolist())
        return np.array(branch_results[key][1], copy=True)

    with patch.object(R1, "_nominal_rates", rate_dispatch):
        r1_delta, r1_q3 = R1.nominal_relational_zr_surface(
            environment,
            observation,
            reference_actions=refs,
            required_power_surface=power,
            opening_feasibility_surface=opening_values,
            interval_s=interval_s,
            kappa_bits=RUNNER.OPS3_KAPPA_BITS,
            pmax_w=RUNNER.BEAM_POWER_MAX_W,
        )
    with patch.object(R1, "_nominal_interference", interference_dispatch):
        r1_state = R1.encode_relational_zr_c3_state(
            environment,
            observation,
            reference_actions=refs,
            required_power_surface=power,
            opening_feasibility_surface=opening_values,
            pmax_w=RUNNER.BEAM_POWER_MAX_W,
        )

    comparisons = (
        ("delta", r1_delta, r2_delta, 1e-9),
        ("q3", r1_q3, r2_q3, 1e-9),
        ("action_context", r1_state.action_context, r2_state.action_context, 1e-12),
        ("victim_tokens", r1_state.victim_tokens, r2_state.victim_tokens, 1e-12),
    )
    deviations: dict[str, float] = {}
    for name, left, right, atol in comparisons:
        np.testing.assert_allclose(left, right, rtol=1e-12, atol=atol)
        deviations[name] = float(np.max(np.abs(np.asarray(left) - np.asarray(right))))
    for name in (
        "action_mask",
        "victim_mask",
        "positive_credit_compatible",
        "reference_actions",
    ):
        np.testing.assert_array_equal(getattr(r1_state, name), getattr(r2_state, name))
    # The digest is byte-exact and can differ when algebraically equivalent
    # floating-point operations are reordered.  Numerical array equality at
    # the frozen tolerances plus exact masked argmax identity is the binding
    # acceptance; retain digest identity as a diagnostic only.
    content_digest_equal = r1_state.content_digest == r2_state.content_digest

    r1_score = np.asarray(background, dtype=np.float64) + np.asarray(r1_q3)
    r2_score = np.asarray(background, dtype=np.float64) + np.asarray(r2_q3)
    r1_actions = _masked_argmax(r1_score, legal)
    r2_actions = _masked_argmax(r2_score, legal)
    np.testing.assert_array_equal(r1_actions, r2_actions)
    maximum_score_deviation = float(np.max(np.abs(r1_score - r2_score)))
    minimum_margin = _minimum_top_two_margin(r1_score, legal)
    margin_ratio = (
        math.inf
        if maximum_score_deviation == 0.0
        else minimum_margin / maximum_score_deviation
    )
    return {
        "legal_branch_count": int(np.count_nonzero(legal)),
        "unique_branch_vector_count": len(branch_results),
        "reference_reconstruction_elapsed_s": reference_elapsed_s,
        "checked_nonfocal_rate_and_interference_values": checked_nonfocal_values,
        "maximum_nonfocal_rate_deviation_bps": maximum_rate_deviation,
        "maximum_nonfocal_interference_deviation_w": maximum_interference_deviation,
        "maximum_absolute_deviation": deviations,
        "state_content_digest_equal": content_digest_equal,
        "selected_actions_equal": True,
        "selected_action_sha256": RUNNER.array_sha256(r1_actions),
        "maximum_score_deviation": maximum_score_deviation,
        "minimum_top_two_margin": minimum_margin,
        "margin_to_deviation_ratio": margin_ratio,
    }


def run(output: Path, *, workers: int, tle_root: Path) -> dict[str, Any]:
    contract_sha256 = validate_contract()
    initial_runner_sha256 = file_sha256(Path(__file__).resolve())
    initial_r2_sha256 = file_sha256(Path(R2.__file__).resolve())
    if output.exists() or output.is_symlink():
        raise RuntimeError(f"refusing to overwrite output: {output}")
    if workers < 1 or workers > MAX_WORKERS:
        raise RuntimeError(f"workers must be in [1,{MAX_WORKERS}]")
    tle_source = Path(tle_root)
    if not tle_source.is_absolute() or tle_source.is_symlink() or not tle_source.is_dir():
        raise RuntimeError("TLE root must be an existing non-symlink absolute directory")
    q2_gate = RUNNER._V015.validate_v014_gate_receipts(RUNNER.V014_GATE_ROOT)
    q1, q1_receipt = RUNNER._V015.load_frozen_q1(RUNNER.V03_ROOT, LINEAGE)
    q2, q2_receipt = RUNNER._V015.load_frozen_q2(
        RUNNER.V014_GATE_ROOT, lineage=LINEAGE, gate_receipt=q2_gate
    )
    record = RUNNER._V015._V013.read_prereg(RUNNER.DEFAULT_PREREG)
    tle_file_set_sha256 = hashlib.sha256(
        canonical_bytes(record.sections["ephemeris"]["frozen_files"])
    ).hexdigest()
    field = KeyedFadingField.from_components(RUNNER.FIELD_COMPONENT, WORLD_SEED)
    with tempfile.TemporaryDirectory(prefix="mcrl-v018-r2-equivalence-tle-") as temporary:
        archive = RUNNER._V015._V013.screen._frozen_archive(
            record, tle_source, Path(temporary) / "frozen-tle"
        )
        wrapper = RUNNER._V015._V013.screen._make_environment(
            archive, users=RUNNER.USERS
        )
        wrapper.environment._fading_field = field
        env_rng, mobility_rng, _action_rng, _control_rng = (
            RUNNER._V015._V013.screen._evaluation_rngs(WORLD_SEED)
        )
        _states, _masks, observation = wrapper.reset(env_rng, mobility_rng)
        environment = wrapper.environment
        initial_digest = RUNNER._live_digest(wrapper, env_rng)
        initial_world_sha256 = RUNNER._initial_world_sha(wrapper, observation)
        native = encode_ee_axis_state(environment, observation)
        masks = np.asarray(native.action_masks, dtype=np.bool_)
        q1_values = RUNNER._q1_values(q1, native.state_matrix, masks)
        q1_reference = RUNNER._V015.select_actions(
            q1_values,
            np.zeros_like(q1_values),
            np.zeros_like(q1_values),
            masks,
            include_c3=False,
        )
        anchor = snapshot_ops3_anchor(environment, observation)
        projection = project_ops3_anchor(anchor)
        ops3_surfaces = build_ops3_live_surfaces(anchor, projection, q1_reference)
        q2_state = RUNNER._V015.encode_ee_axis_v014_q2_states(ops3_surfaces)
        learned_q2 = RUNNER._q2_values(
            q2, q2_state.state_matrix, q2_state.action_masks
        )
        required, opening = RUNNER._current_required_power_and_opening(
            current_gain_linear=anchor.current_gain_linear,
            segment_start_gain_linear=anchor.segment_start_gain_linear,
            action_masks=masks,
        )
        backgrounds = {12: q1_values + learned_q2, 1: q1_values, 2: learned_q2}
        reports: dict[str, Any] = {}
        for context_code in CONTEXTS:
            background = np.asarray(backgrounds[context_code], dtype=np.float64)
            references = _masked_argmax(background, masks)
            reports[str(context_code)] = _context_result(
                environment=environment,
                observation=observation,
                references=references,
                background=background,
                required=required,
                opening=opening,
                workers=workers,
            )
        final_digest = RUNNER._live_digest(wrapper, env_rng)
        if final_digest != initial_digest:
            raise RuntimeError("equivalence check changed live environment or RNG")
    if file_sha256(Path(__file__).resolve()) != initial_runner_sha256:
        raise RuntimeError("equivalence runner changed during execution")
    if file_sha256(Path(R2.__file__).resolve()) != initial_r2_sha256:
        raise RuntimeError("R2 cached runtime changed during execution")
    if file_sha256(CONTRACT_PATH) != contract_sha256:
        raise RuntimeError("equivalence contract changed during execution")
    if file_sha256(R1_PATH) != R1_SHA256:
        raise RuntimeError("sealed R1 reference changed during execution")
    if file_sha256(RUNNER.DEFAULT_PREREG) != PREREG_SHA256:
        raise RuntimeError("frozen base preregistration changed during execution")
    result = {
        "schema": RESULT_SCHEMA,
        "execution_attempt": "r3",
        "decision": "PASS_R2_CACHE_EQUIVALENCE",
        "passed": True,
        "split": "TRAIN_PREVIOUSLY_OPENED",
        "test_split_opened": False,
        "action_executed": False,
        "exact_teacher_opened": False,
        "learner_update": False,
        "episode_training": False,
        "world_seed": WORLD_SEED,
        "lineage": LINEAGE,
        "users": RUNNER.USERS,
        "contexts": list(CONTEXTS),
        "workers": workers,
        "tle_root": str(tle_source.resolve()),
        "prereg_sha256": file_sha256(RUNNER.DEFAULT_PREREG),
        "tle_file_set_sha256": tle_file_set_sha256,
        "field_component": RUNNER.FIELD_COMPONENT,
        "initial_world_sha256": initial_world_sha256,
        "initial_live_state_rng_sha256": initial_digest,
        "contract_sha256": contract_sha256,
        "r1_source_sha256": file_sha256(R1_PATH),
        "r2_source_sha256": initial_r2_sha256,
        "runner_sha256": initial_runner_sha256,
        "q1_checkpoint": q1_receipt,
        "q2_checkpoint": q2_receipt,
        "live_state_rng_unchanged": True,
        "reports": reports,
    }
    output.mkdir(parents=True, exist_ok=False)
    result_path = output / "result.json"
    result_path.write_bytes(canonical_bytes(result))
    receipt = {
        "result_sha256": file_sha256(result_path),
        "contract_sha256": contract_sha256,
        "decision": result["decision"],
    }
    (output / "receipt.json").write_bytes(canonical_bytes(receipt))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    execute = subparsers.add_parser("run")
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--workers", type=int, default=MAX_WORKERS)
    execute.add_argument(
        "--tle-root",
        type=Path,
        default=RUNNER.DEFAULT_TLE_ROOT,
    )
    args = parser.parse_args()
    if args.command == "plan":
        print(
            json.dumps(
                {
                    "world_seed": WORLD_SEED,
                    "lineage": LINEAGE,
                    "users": RUNNER.USERS,
                    "contexts": list(CONTEXTS),
                    "max_workers": MAX_WORKERS,
                    "default_tle_root": str(RUNNER.DEFAULT_TLE_ROOT),
                    "test_split_opened": False,
                    "action_executed": False,
                },
                sort_keys=True,
            )
        )
        return
    try:
        result = run(args.output, workers=args.workers, tle_root=args.tle_root)
    except Exception as error:
        if args.output.exists() or args.output.is_symlink():
            raise
        failure = {
            "schema": RESULT_SCHEMA,
            "execution_attempt": "r3",
            "decision": "STOP_R2_CACHE_EQUIVALENCE",
            "passed": False,
            "split": "TRAIN_PREVIOUSLY_OPENED",
            "test_split_opened": False,
            "action_executed": False,
            "exact_teacher_opened": False,
            "learner_update": False,
            "episode_training": False,
            "world_seed": WORLD_SEED,
            "lineage": LINEAGE,
            "users": RUNNER.USERS,
            "contexts": list(CONTEXTS),
            "workers": args.workers,
            "tle_root": str(Path(args.tle_root).resolve()),
            "contract_sha256": (
                file_sha256(CONTRACT_PATH) if CONTRACT_PATH.is_file() else None
            ),
            "r1_source_sha256": (
                file_sha256(R1_PATH) if R1_PATH.is_file() else None
            ),
            "r2_source_sha256": file_sha256(Path(R2.__file__).resolve()),
            "runner_sha256": file_sha256(Path(__file__).resolve()),
            "error_type": type(error).__name__,
            "error": str(error)[:4000],
            "traceback": traceback.format_exc(limit=20)[:12000],
        }
        args.output.mkdir(parents=True, exist_ok=False)
        result_path = args.output / "result.json"
        result_path.write_bytes(canonical_bytes(failure))
        receipt = {
            "result_sha256": file_sha256(result_path),
            "contract_sha256": failure["contract_sha256"],
            "decision": failure["decision"],
        }
        (args.output / "receipt.json").write_bytes(canonical_bytes(receipt))
        print(json.dumps({"decision": failure["decision"], "error": failure["error"]}, sort_keys=True))
        raise SystemExit(1) from error
    print(
        json.dumps(
            {"decision": result["decision"], "reports": result["reports"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
