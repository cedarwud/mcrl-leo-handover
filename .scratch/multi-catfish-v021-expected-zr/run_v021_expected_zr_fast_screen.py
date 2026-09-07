#!/usr/bin/env python3
"""One-anchor V0.21 EXPECTED-ZR directional screen.

This is development triage, not an efficacy experiment or learner.  B/N/R/P
actions are sealed before independent evaluation fields are opened; E is a
privileged pathwise diagnostic.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_expected_zr_c3 import (  # noqa: E402
    expected_zr_from_measurements,
    zr_q3_from_measurement,
)


V020_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "run_v020_repriced_c3_gate.py"
)
CONTRACT = HERE / "EXPECTED-ZR-FAST-SCREEN-CONTRACT-2026-09-05.md"
CONTRACT_SHA256 = "9630e6c51784a8d8f36a7eeea34a2c3b611d9ee4b87f95be157a6adbc75e3c66"
WORLD = 2026121601
LINEAGE = 2026092101
INTEGRATION_DRAWS = 8
EVALUATION_DRAWS = 8
FIELD_COMPONENT = "MCRL_V021_EXPECTED_ZR_FAST_V1"
SCHEMA = "multi-catfish-mcrl-v021-expected-zr-fast-screen-v1"
CLAIM_CEILING = "TRAIN_ONE_ANCHOR_TRIAGE_NO_LEARNER_NO_EPISODE_TRAINING_NO_TEST"
ARMS = ("B", "N", "E", "R", "P")


class V021FastScreenError(RuntimeError):
    """The frozen V0.21 fast-screen boundary was violated."""


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V021FastScreenError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_default(value: object) -> bool | int | float:
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("non-finite scalar")
        return result
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=_canonical_default,
    ).encode("ascii")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _masked_argmax(values: np.ndarray, legal: np.ndarray) -> np.ndarray:
    if values.shape != legal.shape or legal.dtype != np.bool_:
        raise V021FastScreenError("score and native mask shapes differ")
    if not np.all(np.isfinite(values)) or not np.all(np.any(legal, axis=1)):
        raise V021FastScreenError("score surface is not finite and selectable")
    return np.argmax(np.where(legal, values, -np.inf), axis=1).astype(np.int64)


def _permuted_control(
    expected_q3: np.ndarray,
    *,
    compatible: np.ndarray,
    legal: np.ndarray,
    references: np.ndarray,
) -> np.ndarray:
    result = np.array(expected_q3, dtype=np.float64, copy=True)
    for uid in range(result.shape[0]):
        indices = np.flatnonzero(compatible[uid] & legal[uid])
        indices = indices[indices != int(references[uid])]
        if indices.size > 1:
            result[uid, indices] = np.roll(result[uid, indices], 1)
    result[~legal] = 0.0
    result[np.arange(result.shape[0]), references] = 0.0
    return result


def _arm_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    bits = float(sum(float(row["bits"]) for row in rows))
    energy = float(sum(float(row["energy_j"]) for row in rows))
    served = int(sum(int(row["served_users"]) for row in rows))
    total = int(sum(int(row["total_users"]) for row in rows))
    return {
        "bits": bits,
        "energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_fraction": served / total,
        "served_users": served,
        "total_users": total,
        "per_draw_ee_bits_per_j": [float(row["ee_bits_per_j"]) for row in rows],
    }


def run(*, output: Path, tle_root: Path, prereg: Path) -> dict[str, object]:
    if output.exists() or output.is_symlink():
        raise V021FastScreenError(f"refusing to overwrite {output}")
    if _sha256(CONTRACT) != CONTRACT_SHA256:
        raise V021FastScreenError("fast-screen contract bytes changed")
    v020 = _load_module("mcrl_v020_for_v021_fast", V020_PATH)
    v020._validate_global_inputs()
    v018 = v020._load_module("mcrl_v018_for_v021_fast", v020.V018_PATH)
    q1, q1_receipt, q2, q2_receipt = v020.load_repriced_heads(LINEAGE)
    record = v018._V015._V013.read_prereg(prereg)

    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="mcrl-v021-fast-tle-") as temporary:
        archive = v018._V015._V013.screen._frozen_archive(
            record, tle_root, Path(temporary) / "frozen-tle"
        )
        environment = v018._V015._V013.screen._make_environment(
            archive, users=v018.USERS
        )
        anchor_field = KeyedFadingField.from_components(
            FIELD_COMPONENT, "anchor", WORLD
        )
        environment.environment._fading_field = anchor_field
        env_rng, mobility_rng, _action_rng, _control_rng = (
            v018._V015._V013.screen._evaluation_rngs(WORLD)
        )
        _states, _masks, observation = environment.reset(env_rng, mobility_rng)
        step_env = environment.environment
        if int(observation.step_index) != 0:
            raise V021FastScreenError("fast screen did not open the initial anchor")
        interval_s = float(step_env.driver.config.ephemeris.time_step_s)
        native = v018.encode_ee_axis_state(step_env, observation)
        masks = np.asarray(native.action_masks, dtype=np.bool_)

        with torch.no_grad():
            q1_values = v018._q1_values(q1, native.state_matrix, masks)
            q1_reference = v018._V015.select_actions(
                q1_values,
                np.zeros_like(q1_values),
                np.zeros_like(q1_values),
                masks,
                include_c3=False,
            )
            anchor = v018.snapshot_ops3_anchor(step_env, observation)
            projection = v018.project_ops3_anchor(anchor)
            ops3 = v018.build_ops3_live_surfaces(anchor, projection, q1_reference)
            q2_state = v018._V015.encode_ee_axis_v014_q2_states(ops3)
            q2_state.verify()
            learned_q2 = v018._q2_values(
                q2, q2_state.state_matrix, q2_state.action_masks
            )

        base_surface = q1_values + learned_q2
        background = _masked_argmax(base_surface, masks)
        required_power, opening = v018._current_required_power_and_opening(
            current_gain_linear=anchor.current_gain_linear,
            segment_start_gain_linear=anchor.segment_start_gain_linear,
            action_masks=masks,
        )
        relational = v018.encode_relational_zr_c3_state(
            step_env,
            observation,
            reference_actions=background,
            required_power_surface=required_power,
            opening_feasibility_surface=opening,
            pmax_w=v018.BEAM_POWER_MAX_W,
        )
        relational.verify()
        _nominal_delta, nominal_q3 = v018.nominal_relational_zr_surface(
            step_env,
            observation,
            reference_actions=background,
            required_power_surface=required_power,
            opening_feasibility_surface=opening,
            interval_s=interval_s,
            kappa_bits=v018.OPS3_KAPPA_BITS,
            pmax_w=v018.BEAM_POWER_MAX_W,
        )
        nominal_q3 = np.asarray(nominal_q3, dtype=np.float64)

        live_before = v018._live_digest(environment, env_rng)
        rng_before = copy.deepcopy(env_rng.bit_generator.state)
        original_field = step_env._fading_field
        integration_fields = [
            KeyedFadingField.from_components(
                FIELD_COMPONENT, "integration", WORLD, draw
            )
            for draw in range(INTEGRATION_DRAWS)
        ]
        evaluation_fields = [
            KeyedFadingField.from_components(
                FIELD_COMPONENT, "evaluation", WORLD, draw
            )
            for draw in range(EVALUATION_DRAWS)
        ]
        integration_digests = [field.root_digest for field in integration_fields]
        evaluation_digests = [field.root_digest for field in evaluation_fields]
        if len(set(integration_digests + evaluation_digests)) != (
            INTEGRATION_DRAWS + EVALUATION_DRAWS
        ):
            raise V021FastScreenError("integration/evaluation fields are not disjoint")

        def integration_measurements():
            for field in integration_fields:
                step_env._fading_field = field
                measurement = v018.measure_zero_marginal_c3(
                    step_env,
                    observation=observation,
                    reference_actions=background,
                    rng=env_rng,
                    include_insertion=False,
                    interval_s=interval_s,
                )
                if not np.array_equal(
                    measurement.compatible,
                    relational.positive_credit_compatible,
                ):
                    raise V021FastScreenError(
                        "integration compatibility is not identified by the predecision state"
                    )
                yield measurement

        try:
            expected = expected_zr_from_measurements(
                integration_measurements(),
                kappa_bits=v018.OPS3_KAPPA_BITS,
            )
        finally:
            step_env._fading_field = original_field

        q4 = np.mean(expected.per_draw_q3_values[:4], axis=0, dtype=np.float64)
        actions_b = np.array(background, copy=True)
        actions_n = _masked_argmax(base_surface + nominal_q3, masks)
        actions_r = _masked_argmax(base_surface + expected.q3_values, masks)
        permuted_q3 = _permuted_control(
            expected.q3_values,
            compatible=expected.compatibility,
            legal=masks,
            references=background,
        )
        actions_p = _masked_argmax(base_surface + permuted_q3, masks)
        actions_k4 = _masked_argmax(base_surface + q4, masks)
        fixed_actions = {
            "B": actions_b,
            "N": actions_n,
            "R": actions_r,
            "P": actions_p,
        }

        by_arm_rows: dict[str, list[dict[str, object]]] = {
            arm: [] for arm in ARMS
        }
        evaluation_exact_hashes: list[str] = []
        try:
            for draw, field in enumerate(evaluation_fields):
                step_env._fading_field = field
                exact_measurement = v018.measure_zero_marginal_c3(
                    step_env,
                    observation=observation,
                    reference_actions=background,
                    rng=env_rng,
                    include_insertion=False,
                    interval_s=interval_s,
                )
                exact_q3 = zr_q3_from_measurement(
                    exact_measurement, kappa_bits=v018.OPS3_KAPPA_BITS
                )
                actions_e = _masked_argmax(base_surface + exact_q3, masks)
                evaluation_exact_hashes.append(v018.array_sha256(exact_q3))
                draw_actions = dict(fixed_actions)
                draw_actions["E"] = actions_e
                for arm in ARMS:
                    selected = draw_actions[arm]
                    evaluation = step_env.evaluate_actions(selected, env_rng)
                    bits = interval_s * float(
                        np.sum(evaluation.link_rate_bps, dtype=np.float64)
                    )
                    energy = interval_s * float(evaluation.system_power_w)
                    by_arm_rows[arm].append(
                        {
                            "draw": draw,
                            "bits": bits,
                            "energy_j": energy,
                            "ee_bits_per_j": bits / energy,
                            "served_users": int(
                                np.count_nonzero(evaluation.resolution.served)
                            ),
                            "total_users": int(v018.USERS),
                            "action_sha256": v018.array_sha256(selected),
                        }
                    )
        finally:
            step_env._fading_field = original_field

        live_after = v018._live_digest(environment, env_rng)
        rng_after = env_rng.bit_generator.state
        mechanics = {
            "contract_authenticated": True,
            "initial_anchor": int(observation.step_index) == 0,
            "integration_evaluation_fields_disjoint": True,
            "reference_zero": bool(
                np.all(
                    expected.q3_values[
                        np.arange(v018.USERS), expected.reference_actions
                    ]
                    == 0.0
                )
            ),
            "illegal_zero": bool(np.all(expected.q3_values[~masks] == 0.0)),
            "positive_support_preserved": bool(
                np.all(
                    expected.q3_values[masks & ~expected.compatibility] <= 0.0
                )
            ),
            "finite": bool(np.all(np.isfinite(expected.q3_values))),
            "live_state_unchanged": live_before == live_after,
            "rng_unchanged": rng_before == rng_after,
            "fixed_arm_actions_before_evaluation": True,
        }
        mechanics["passed"] = bool(all(mechanics.values()))
        metrics = {arm: _arm_metrics(by_arm_rows[arm]) for arm in ARMS}
        r_ee = float(metrics["R"]["ratio_of_sums_ee_bits_per_j"])
        b_ee = float(metrics["B"]["ratio_of_sums_ee_bits_per_j"])
        n_ee = float(metrics["N"]["ratio_of_sums_ee_bits_per_j"])
        p_ee = float(metrics["P"]["ratio_of_sums_ee_bits_per_j"])
        positive_draws = sum(
            float(r["ee_bits_per_j"]) > float(b["ee_bits_per_j"])
            for r, b in zip(by_arm_rows["R"], by_arm_rows["B"], strict=True)
        )
        exposure = int(np.count_nonzero(actions_r != actions_b))
        criteria = {
            "mechanics_pass": bool(mechanics["passed"]),
            "r_exposure_positive": exposure > 0,
            "r_gt_b": r_ee > b_ee,
            "r_gt_n": r_ee > n_ee,
            "r_gt_p": r_ee > p_ee,
            "service_guard": float(metrics["R"]["served_fraction"])
            >= float(metrics["B"]["served_fraction"]) - 0.001,
            "positive_draws_at_least_6_of_8": positive_draws >= 6,
        }
        decision = (
            "GO_FULL_EXPECTED_ZR_GATE"
            if all(criteria.values())
            else "STOP_EXPECTED_ZR_FAST"
        )
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "contract_sha256": CONTRACT_SHA256,
            "runner_sha256": _sha256(Path(__file__)),
            "split": "TRAIN_DEVELOPMENT",
            "world": WORLD,
            "lineage": LINEAGE,
            "anchor_step": int(observation.step_index),
            "integration_draws": INTEGRATION_DRAWS,
            "evaluation_draws": EVALUATION_DRAWS,
            "integration_field_root_digests": integration_digests,
            "evaluation_field_root_digests": evaluation_digests,
            "q1_receipt": q1_receipt,
            "q2_receipt": q2_receipt,
            "surface_receipts": {
                "base_sha256": v018.array_sha256(base_surface),
                "nominal_q3_sha256": v018.array_sha256(nominal_q3),
                "expected_q3_sha256": v018.array_sha256(expected.q3_values),
                "per_draw_expected_source_sha256": v018.array_sha256(
                    expected.per_draw_q3_values
                ),
                "permuted_q3_sha256": v018.array_sha256(permuted_q3),
                "evaluation_exact_q3_sha256": evaluation_exact_hashes,
            },
            "action_receipts": {
                arm: v018.array_sha256(actions)
                for arm, actions in fixed_actions.items()
            },
            "r_exposure_users": exposure,
            "n_exposure_users": int(np.count_nonzero(actions_n != actions_b)),
            "p_exposure_users": int(np.count_nonzero(actions_p != actions_b)),
            "k4_k8_action_agreement": float(np.mean(actions_k4 == actions_r)),
            "positive_r_vs_b_evaluation_draws": int(positive_draws),
            "mechanics": mechanics,
            "criteria": criteria,
            "metrics": metrics,
            "per_draw": by_arm_rows,
            "decision": decision,
            "elapsed_s": time.perf_counter() - started,
            "test_split_opened": False,
            "learner_update": False,
            "episode_training": False,
        }
        payload["result_sha256"] = _canonical_sha256(payload)
        output.mkdir(parents=True, exist_ok=False)
        (output / "result.json").write_bytes(_canonical_bytes(payload))
        print(
            f"{decision}: B={b_ee:.9g} N={n_ee:.9g} "
            f"R={r_ee:.9g} P={p_ee:.9g} exposure={exposure} "
            f"elapsed={float(payload['elapsed_s']):.1f}s",
            flush=True,
        )
        return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    args = parser.parse_args()
    run(output=args.output, tle_root=args.tle_root, prereg=args.prereg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
