#!/usr/bin/env python3
"""Benchmark one frozen TRAIN predecision anchor without stepping physics."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import time

import numpy as np


REPO = Path(__file__).resolve().parents[3]
RUNNER_PATH = (
    REPO
    / ".scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py"
)
for path in (REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

SPEC = importlib.util.spec_from_file_location("v018_perf_runner", RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load V0.18 runner: {RUNNER_PATH}")
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)

from mcrl.runtime.ee_axis_ops3_live import snapshot_ops3_anchor  # noqa: E402
from mcrl.runtime.ee_axis_relational_zr_c3 import (  # noqa: E402
    encode_relational_zr_c3_state,
    nominal_relational_zr_surface,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402


def timed(label: str, function) -> float:
    start = time.perf_counter()
    function()
    elapsed = time.perf_counter() - start
    print(f"{label}_s={elapsed:.9f}", flush=True)
    return elapsed


def main() -> None:
    world = int(RUNNER.WORLD_SEEDS[0])
    record = RUNNER._V015._V013.read_prereg(RUNNER.DEFAULT_PREREG)
    field = RUNNER.field_for_world(world)
    with tempfile.TemporaryDirectory(prefix="mcrl-v018-perf-tle-") as temporary:
        archive = RUNNER._V015._V013.screen._frozen_archive(
            record,
            RUNNER.DEFAULT_TLE_ROOT,
            Path(temporary) / "frozen-tle",
        )
        environment = RUNNER._V015._V013.screen._make_environment(
            archive, users=RUNNER.USERS
        )
        environment.environment._fading_field = field
        env_rng, mobility_rng, _action_rng, _control_rng = (
            RUNNER._V015._V013.screen._evaluation_rngs(world)
        )
        _states, _masks, observation = environment.reset(env_rng, mobility_rng)
        step_env = environment.environment
        native = encode_ee_axis_state(step_env, observation)
        masks = np.asarray(native.action_masks, dtype=np.bool_)
        sinr = np.asarray(observation.candidate_sinr, dtype=np.float64)
        references = np.argmax(np.where(masks, sinr, -np.inf), axis=1).astype(
            np.int64
        )
        anchor = snapshot_ops3_anchor(step_env, observation)
        required, opening = RUNNER._current_required_power_and_opening(
            current_gain_linear=anchor.current_gain_linear,
            segment_start_gain_linear=anchor.segment_start_gain_linear,
            action_masks=masks,
        )
        print(f"users={RUNNER.USERS}")
        print(f"legal_actions={int(np.count_nonzero(masks))}")
        print(f"world={world}")

        def cached_surface() -> None:
            nominal_relational_zr_surface(
                step_env,
                observation,
                reference_actions=references,
                required_power_surface=required,
                opening_feasibility_surface=opening,
                interval_s=float(step_env.driver.config.ephemeris.time_step_s),
                kappa_bits=RUNNER.OPS3_KAPPA_BITS,
                pmax_w=RUNNER.BEAM_POWER_MAX_W,
            )

        def cached_encoder() -> None:
            encode_relational_zr_c3_state(
                step_env,
                observation,
                reference_actions=references,
                required_power_surface=required,
                opening_feasibility_surface=opening,
                pmax_w=RUNNER.BEAM_POWER_MAX_W,
            )

        cached_surface_s = timed("cached_surface", cached_surface)
        cached_encoder_s = timed("cached_encoder", cached_encoder)

        tables, legal = RUNNER.encode_relational_zr_c3_state.__globals__["_anchor"](
            step_env, observation
        )
        internal = RUNNER.encode_relational_zr_c3_state.__globals__
        refs, power, opening_values, identity = internal["_validate_context_inputs"](
            tables, legal, references, required, opening
        )
        norads = identity[:, :, 0]
        cells = identity[:, :, 1]
        centres, colours, positions = internal["_grid_data"](
            step_env, observation, norads, cells
        )
        users_ecef = internal["_user_positions"](step_env, len(tables))
        theta, slant, elevation = internal["_candidate_geometry"](
            step_env,
            observation,
            norads,
            cells,
            centres,
            positions,
            users_ecef,
        )
        signal = internal["_nominal_signal_surface"](
            theta=theta,
            slant=slant,
            elevation=elevation,
            required_power=power,
            legal=legal,
        )
        cache = internal["_build_nominal_reference_cache"](
            environment=step_env,
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
        sample_users = (0, 1, 2, 10, 25, 50, 75, 99)
        sample: list[tuple[int, int]] = []
        for uid in sample_users:
            actions = np.flatnonzero(legal[uid]).tolist()
            sample.append((uid, int(actions[0])))
            if int(actions[-1]) != int(actions[0]):
                sample.append((uid, int(actions[-1])))

        started = time.perf_counter()
        for uid, action in sample:
            branch = internal["_branch_actions"](
                refs, focal_user=uid, focal_action=action
            )
            served = internal["_branch_served"](
                branch, opening_values, legal
            )
            old_rates, old_interference = internal["_nominal_rates"](
                environment=step_env,
                actions=branch,
                served=served,
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
            new_rates, new_interference = internal[
                "_cached_nominal_nonfocal_branch"
            ](
                cache,
                focal_user=uid,
                focal_action=action,
                opening=opening_values,
                power=power,
                norads=norads,
                cells=cells,
            )
            nonfocal = np.arange(RUNNER.USERS) != uid
            np.testing.assert_allclose(
                new_rates[nonfocal],
                np.asarray(old_rates)[nonfocal],
                rtol=1e-12,
                atol=1e-9,
            )
            np.testing.assert_allclose(
                new_interference[nonfocal],
                np.asarray(old_interference)[nonfocal],
                rtol=1e-12,
                atol=1e-18,
            )
        sampled_reference_s = time.perf_counter() - started
        print(f"sampled_reference_branches={len(sample)}")
        print(f"sampled_reference_s={sampled_reference_s:.9f}")
        print("sampled_reference_equivalence=PASS")
        projected_reference_s = (
            sampled_reference_s / len(sample) * int(np.count_nonzero(legal))
        )
        print(f"projected_full_reference_s={projected_reference_s:.9f}")
        print(f"projected_surface_speedup={projected_reference_s / cached_surface_s:.6f}")
        print(
            f"cached_pair_s={cached_surface_s + cached_encoder_s:.9f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
