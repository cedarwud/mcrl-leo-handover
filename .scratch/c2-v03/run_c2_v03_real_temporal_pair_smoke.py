#!/usr/bin/env python3
"""Read-only real C2 -> Q2 temporal-pair integration smoke.

This is deliberately a small companion to the existing C2 runners.  It uses
the existing frozen-archive and Main/checkpoint loader, finds one real
Main-departure anchor, and exercises the current temporal adapter in its
required order::

    prepare -> capture_temporal_anchor -> run_forecast
           -> materialize_temporal_pair -> Q2 route batch

The smoke never updates a network, replay buffer, checkpoint, or live option.
It reads only the frozen PREREG record needed by the existing loader; no C2
gate result JSON is read, rewritten, or relabelled.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EE_AXIS_RUNNERS = REPO / ".scratch" / "ee-axis-redesign"
STAGE0 = REPO / ".scratch" / "catfish-stage0"
SMC = REPO / ".scratch" / "smc-er-short-ep"
for _path in (HERE, EE_AXIS_RUNNERS, STAGE0, SMC, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import c2_temporal_fork_core as core  # noqa: E402
import c2_temporal_fork_forecast_adapter as forecast  # noqa: E402
import c2_temporal_fork_trainer_backend as backend  # noqa: E402
import run_c2_v03_deterministic_plumbing_probe as gate_runner  # noqa: E402
import run_c2_v03_real_backend_smoke as existing_smoke  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM  # noqa: E402
from mcrl.runtime.ee_axis_c2_neutral_source import (  # noqa: E402
    C2_NEUTRAL_SOURCE_RULE,
    predecision_anchor_from_observation,
    prepare_selected_c2_candidate,
    select_c2_neutral_source,
)
from mcrl.runtime.ee_axis_temporal_capture import (  # noqa: E402
    C2TemporalAnchorCapture,
    capture_temporal_anchor,
    materialize_temporal_pair,
)
from mcrl.runtime.ee_axis_temporal_pairs import (  # noqa: E402
    EEAxisTemporalPair,
    EEAxisTemporalRouteBatch,
    build_temporal_route_batch,
)
from mcrl.runtime.ee_axis_temporal_dataset import (  # noqa: E402
    EEAxisTemporalDataset,
    write_temporal_dataset,
)
from mcrl.env.keyed_fading import KEYED_FADING_VERSION  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
)


# Keep the environment random-field version and backend mode explicitly bound
# without changing the existing temporal capture/pair modules.
KEYED_FADING = core.FADING_MODE_KEYED
if KEYED_FADING_VERSION != KEYED_FADING:  # pragma: no cover - drift guard
    raise RuntimeError("keyed fading version disagrees with the C2 backend")


DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_INPUT = REPO / "artifacts" / "training-2026-08-25-rerun01"
DEFAULT_TLE_ROOT = Path(TLE_ROOT_DEFAULT).expanduser()
DEFAULT_USERS = 100
DEFAULT_SEED = 2026082801
DEFAULT_CALIBRATION_SEED = 2026082401
DEFAULT_MAX_ANCHOR_STEPS = 6
DEFAULT_MAX_CANDIDATES = 1
DEFAULT_NEUTRAL_SELECTION_SEED = 2026083163
SCHEMA = "mcrl-multi-catfish-v03-real-temporal-pair-smoke-v1"
CLAIM_CEILING = (
    "one real Main/TLE C2-to-Q2 temporal-pair plumbing receipt only; "
    "no training, learnability, EE efficacy, or deployment claim"
)


class RealTemporalPairSmokeError(RuntimeError):
    """The bounded real temporal-pair smoke could not close."""


@dataclass(frozen=True)
class Q2TemporalPairMaterialization:
    """The objects handed across the current C2 -> Q2 adapter boundary."""

    capture: C2TemporalAnchorCapture
    build: Any
    pair: EEAxisTemporalPair
    route_batch: EEAxisTemporalRouteBatch


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _current_source_manifest_sha256() -> str:
    """Hash the current loader/backend/adapter closure for pair provenance.

    The existing keyed gate has a larger persisted source-manifest helper.  A
    one-row smoke does not read that sealed artifact; instead it binds the
    exact live sources used here, plus the package source set used by the
    frozen Main loader, with the repository's canonical code hash helper.
    """

    modules = (
        gate_runner,
        existing_smoke,
        loader,
        core,
        forecast,
        backend,
    )
    paths: list[Path] = [Path(__file__)]
    for module in modules:
        module_path = getattr(module, "__file__", None)
        if module_path is not None:
            paths.append(Path(module_path))
    # Bind the two current adapter files explicitly and deduplicate all paths.
    paths.extend(
        [
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_capture.py",
            REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_pairs.py",
        ]
    )
    paths.extend(Path(path) for path in _default_code_paths())
    unique = sorted({path.resolve() for path in paths}, key=lambda path: str(path))
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise RealTemporalPairSmokeError(
            "current source manifest has missing files: "
            + ", ".join(str(path) for path in missing)
        )
    return _code_sha256(unique)


def _anchor_schedule_sha256(
    prepared: Any,
    *,
    anchor_step: int,
    scheduled_focal_users: Sequence[int],
) -> str:
    """Seal a pre-outcome candidate schedule before forecasting."""

    anchor = prepared.anchor
    focal_user = int(anchor.focal_user)
    main_actions = tuple(int(value) for value in anchor.main_actions)
    payload = {
        "schema": "mcrl-multi-catfish-v03-real-temporal-pair-schedule-v1",
        "anchor_sha256": str(anchor.anchor_sha256),
        "anchor_step": int(anchor_step),
        "scheduled_focal_users": [int(value) for value in scheduled_focal_users],
        "focal_user": focal_user,
        "reference_action": main_actions[focal_user],
        "candidate_key": [int(value) for value in prepared.candidate_key],
        "source_rule": str(prepared.source_rule),
    }
    return forecast.canonical_payload_sha256(payload)


def capture_and_materialize_q2_pair(
    prepared: Any,
    *,
    anchor_schedule_sha256: str,
    source_manifest_sha256: str,
    lambda_bits_per_j: float,
    interval_s: float,
) -> Q2TemporalPairMaterialization:
    """Run the strict current C2 capture/forecast/materialization sequence.

    This is public so a parent runner that already owns a real prepared C2
    fork can reuse exactly the same adapter seam without loading a second
    checkpoint.  The call order is intentionally kept in this one function.
    """

    captured = capture_temporal_anchor(
        prepared,
        anchor_schedule_sha256=anchor_schedule_sha256,
        source_manifest_sha256=source_manifest_sha256,
    )
    build = prepared.run_forecast()
    pair = materialize_temporal_pair(
        captured,
        prepared,
        anchor_schedule_sha256=anchor_schedule_sha256,
        lambda_bits_per_j=lambda_bits_per_j,
        interval_s=interval_s,
    )
    route_batch = build_temporal_route_batch((pair,))
    route_batch.verify()
    if pair.source_route != "C2":
        raise RealTemporalPairSmokeError("materialized temporal pair is not a C2/Q2 row")
    if tuple(np.asarray(pair.state).shape) != (EE_AXIS_STATE_DIM,):
        raise RealTemporalPairSmokeError("materialized temporal state is not 228-D")
    batch_states = np.asarray(route_batch.pair_batch.states)
    if tuple(batch_states.shape) != (1, EE_AXIS_STATE_DIM):
        raise RealTemporalPairSmokeError(
            "materialized Q2 route batch does not expose shape (1, 228)"
        )
    return Q2TemporalPairMaterialization(
        capture=captured,
        build=build,
        pair=pair,
        route_batch=route_batch,
    )


def _departure_users(wrapped: Any, main_physical: Sequence[Any]) -> list[int]:
    """Use the existing deterministic runner's departure schedule helper."""

    return gate_runner._departure_users(wrapped, main_physical)


def run_real_temporal_pair_smoke(
    *,
    input_dir: Path = DEFAULT_INPUT,
    prereg: Path = DEFAULT_PREREG,
    tle_root: Path = DEFAULT_TLE_ROOT,
    users: int = DEFAULT_USERS,
    seed: int = DEFAULT_SEED,
    calibration_seed: int = DEFAULT_CALIBRATION_SEED,
    max_anchor_steps: int = DEFAULT_MAX_ANCHOR_STEPS,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    materialization_out: list[Q2TemporalPairMaterialization] | None = None,
    source_manifest_override: str | None = None,
    source_mode: str = "informed",
    neutral_selection_seed: int = DEFAULT_NEUTRAL_SELECTION_SEED,
) -> dict[str, Any]:
    """Materialize one real frozen-Main/TLE 228-D pair without training."""

    if users <= 0 or max_anchor_steps < 0 or max_candidates <= 0:
        raise ValueError("users/max-candidates must be positive and anchor steps nonnegative")
    if seed < 0 or calibration_seed < 0:
        raise ValueError("seeds must be nonnegative")
    if source_mode not in ("informed", "neutral"):
        raise ValueError("source_mode must be 'informed' or 'neutral'")
    if type(neutral_selection_seed) is not int or neutral_selection_seed < 0:
        raise ValueError("neutral_selection_seed must be a nonnegative exact integer")

    started = time.perf_counter()
    record = read_prereg(Path(prereg))
    source_manifest_sha256 = (
        _current_source_manifest_sha256()
        if source_manifest_override is None
        else source_manifest_override
    )
    if (
        not isinstance(source_manifest_sha256, str)
        or len(source_manifest_sha256) != 64
        or any(value not in "0123456789abcdef" for value in source_manifest_sha256)
    ):
        raise ValueError("source manifest override must be lowercase SHA-256")
    environment_source_sha256 = _code_sha256(_default_code_paths())
    reward_source_sha256 = _sha256_file(REPO / "src" / "mcrl" / "env" / "step.py")

    network_before = None
    replay_before = None
    pair_materialization: Q2TemporalPairMaterialization | None = None
    candidate_rows: list[dict[str, Any]] = []
    anchor_step: int | None = None
    departure_users: list[int] = []
    calibration: dict[str, Any]
    checkpoint: dict[str, Any]

    with tempfile.TemporaryDirectory(prefix="mcrl-real-c2-temporal-") as temporary:
        # This reuses the existing frozen TLE materializer.  It hard-links (or
        # symlinks) only the files named by the frozen PREREG record and checks
        # the ephemeris contract before the backend sees the archive.
        archive = gate_runner._frozen_archive(
            record,
            Path(tle_root),
            Path(temporary) / "frozen-tle",
        )
        trainer, checkpoint = loader._verify_and_load_trainer(
            record,
            archive,
            run_dir=Path(input_dir) / "main",
            users=int(users),
        )
        network_before = existing_smoke._network_snapshot(trainer)
        replay_before = len(trainer.replay)

        # Reuse the existing TRAIN-only Main-reference multiplier helper.  It
        # evaluates a separate temporary environment and does not update Qs or
        # replay.
        calibration_environment = loader._make_environment(archive, users=int(users))
        calibration = gate_runner._freeze_lambda(
            trainer,
            calibration_environment,
            seed=int(calibration_seed),
        )
        multiplier = float(calibration["lambda_bits_per_j"])
        interval_s = float(calibration["interval_s"])

        wrapped = loader._make_environment(archive, users=int(users))
        env_rng, _mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(
            int(seed)
        )
        states, masks, observation = wrapped.reset(env_rng, _mobility_rng)

        for _ in range(int(max_anchor_steps) + 1):
            main_actions, main_physical = existing_smoke._main_decision(
                trainer,
                wrapped,
                states,
                masks,
                observation,
                env_rng,
            )
            departure_users = _departure_users(wrapped, main_physical)
            remaining = int(wrapped.environment.driver.config.steps_per_episode) - int(
                observation.step_index
            )
            if departure_users and remaining >= core.HOLD_STEPS + 1:
                anchor_step = int(observation.step_index)
                scheduled = departure_users[: int(max_candidates)]
                for focal_user in scheduled:
                    row_started = time.perf_counter()
                    try:
                        service = backend.C2TemporalForkTrainerBackend(
                            wrapped=wrapped,
                            states=states,
                            masks=masks,
                            observation=observation,
                            env_rng=env_rng,
                            trainer=trainer,
                            checkpoint_sha256=checkpoint["checkpoint_sha256"],
                            environment_source_sha256=environment_source_sha256,
                            reward_source_sha256=reward_source_sha256,
                            evaluation_seed=int(seed),
                            focal_user=int(focal_user),
                            forecast_fading_mode=KEYED_FADING,
                        )
                        neutral_selection = None
                        if source_mode == "neutral":
                            neutral_anchor = predecision_anchor_from_observation(
                                anchor_sha256=service.anchor_sha256,
                                step_index=int(anchor_step),
                                focal_user=int(focal_user),
                                reference_action=int(main_actions[int(focal_user)]),
                                observation=observation,
                            )
                            neutral_selection = select_c2_neutral_source(
                                (neutral_anchor,),
                                informed_budget=1,
                                rng=np.random.default_rng(neutral_selection_seed),
                                random_seed=neutral_selection_seed,
                            )
                            prepared = prepare_selected_c2_candidate(
                                service, neutral_selection.opportunities[0]
                            )
                        else:
                            prepared = service.prepare_hold_or_max_lagged_gain_rival(
                                focal_user=int(focal_user)
                            )
                        schedule_sha256 = _anchor_schedule_sha256(
                            prepared,
                            anchor_step=int(anchor_step),
                            scheduled_focal_users=scheduled,
                        )
                        materialized = capture_and_materialize_q2_pair(
                            prepared,
                            anchor_schedule_sha256=schedule_sha256,
                            source_manifest_sha256=source_manifest_sha256,
                            lambda_bits_per_j=multiplier,
                            interval_s=interval_s,
                        )
                        pair_materialization = materialized
                        pair = materialized.pair
                        route_batch = materialized.route_batch
                        candidate_rows.append(
                            {
                                "outcome": "REAL_Q2_TEMPORAL_PAIR",
                                "focal_user": int(focal_user),
                                "candidate_key": [int(value) for value in prepared.candidate_key],
                                "source_rule": str(prepared.source_rule),
                                "source_mode": source_mode,
                                "neutral_selection_sha256": (
                                    None
                                    if neutral_selection is None
                                    else neutral_selection.selection_digest
                                ),
                                "anchor_schedule_sha256": schedule_sha256,
                                "state_shape": list(np.asarray(pair.state).shape),
                                "state_dtype": str(np.asarray(pair.state).dtype),
                                "route": pair.source_route,
                                "q2_batch_states_shape": list(
                                    np.asarray(route_batch.pair_batch.states).shape
                                ),
                                "reference_action": int(pair.reference_action),
                                "candidate_action": int(pair.candidate_action),
                                "zeta2_temporal_surplus_bits": float(
                                    pair.zeta2_temporal_surplus_bits
                                ),
                                "release_offset": int(pair.release_offset),
                                "release_reason": str(pair.release_reason),
                                "comparison_sha256": pair.comparison_sha256,
                                "elapsed_s": time.perf_counter() - row_started,
                            }
                        )
                        # One complete row is the entire scope of this smoke;
                        # do not advance the live world or inspect another
                        # forecast after the adapter proof closes.
                        break
                    except backend.C2ForecastSupportRejection as error:
                        candidate_rows.append(
                            {
                                "outcome": "RIGHT_CENSORED_SUPPORT_REJECTION",
                                "focal_user": int(focal_user),
                                "reason": str(error.reason),
                                "forecast_offset": int(error.forecast_offset),
                                "elapsed_s": time.perf_counter() - row_started,
                            }
                        )
                    except Exception as error:
                        candidate_rows.append(
                            {
                                "outcome": "INSTRUMENT_ERROR_NOT_SCORED",
                                "focal_user": int(focal_user),
                                "error": f"{type(error).__name__}: {error}",
                                "elapsed_s": time.perf_counter() - row_started,
                            }
                        )
                break

            result = wrapped.step(main_actions, env_rng)
            if result.done:
                break
            states = result.user_states
            masks = result.action_masks
            observation = wrapped.last_outcome.observation

        networks_unchanged = existing_smoke._networks_equal(trainer, network_before)
        replay_after = len(trainer.replay)
        replay_unchanged = replay_after == replay_before

        if pair_materialization is None:
            raise RealTemporalPairSmokeError(
                "no complete real C2 temporal pair was materialized; rows="
                + json.dumps(candidate_rows, sort_keys=True)
            )
        if not networks_unchanged or not replay_unchanged:
            raise RealTemporalPairSmokeError(
                "real temporal smoke mutated Main networks or replay"
            )

    pair = pair_materialization.pair
    route_batch = pair_materialization.route_batch
    payload = {
        "schema": SCHEMA,
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "training_or_replay_write": False,
        "checkpoint_sha256": checkpoint["checkpoint_sha256"],
        "checkpoint_episode": int(checkpoint["checkpoint_episode"]),
        "prereg_path": str(Path(prereg)),
        "tle_root": str(Path(tle_root)),
        "frozen_loader": "run_head_pivotality_probe._verify_and_load_trainer",
        "frozen_archive_loader": "run_c2_v03_deterministic_plumbing_probe._frozen_archive",
        "source_manifest_sha256": source_manifest_sha256,
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "evaluation_seed": int(seed),
        "source_mode": source_mode,
        "neutral_selection_seed": (
            neutral_selection_seed if source_mode == "neutral" else None
        ),
        "calibration": {
            **calibration,
            "lambda_hex": float(calibration["lambda_bits_per_j"]).hex(),
            "helper": "run_c2_v03_deterministic_plumbing_probe._freeze_lambda",
        },
        "anchor_step": anchor_step,
        "departure_users": [int(value) for value in departure_users],
        "candidate_rows": candidate_rows,
        "pair": {
            "source_route": pair.source_route,
            "c2_policy_version": pair.c2_policy_version,
            "source_rule": pair.source_rule,
            "state_shape": list(np.asarray(pair.state).shape),
            "state_dtype": str(np.asarray(pair.state).dtype),
            "action_mask_shape": list(np.asarray(pair.action_mask).shape),
            "reference_action": int(pair.reference_action),
            "candidate_action": int(pair.candidate_action),
            "zeta2_temporal_surplus_bits": float(pair.zeta2_temporal_surplus_bits),
            "release_offset": int(pair.release_offset),
            "release_reason": pair.release_reason,
            "comparison_sha256": pair.comparison_sha256,
        },
        "q2_route_batch": {
            "route": route_batch.route,
            "states_shape": list(np.asarray(route_batch.pair_batch.states).shape),
            "reference_actions_shape": list(
                np.asarray(route_batch.pair_batch.reference_actions).shape
            ),
            "candidate_actions_shape": list(
                np.asarray(route_batch.pair_batch.candidate_actions).shape
            ),
            "target_shape": list(
                np.asarray(route_batch.pair_batch.target_surplus_bits).shape
            ),
            "batch_sha256": route_batch.batch_sha256,
        },
        "main_networks_bitwise_unchanged": True,
        "main_replay_unchanged": True,
        "main_replay_length_before": int(replay_before),
        "main_replay_length_after": int(replay_before),
        "elapsed_s": time.perf_counter() - started,
    }
    if materialization_out is not None:
        if materialization_out:
            raise RealTemporalPairSmokeError(
                "materialization_out must be an empty caller-owned list"
            )
        materialization_out.append(pair_materialization)
    return payload


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return str(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    parser.add_argument("--users", type=int, default=DEFAULT_USERS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--calibration-seed", type=int, default=DEFAULT_CALIBRATION_SEED)
    parser.add_argument("--max-anchor-steps", type=int, default=DEFAULT_MAX_ANCHOR_STEPS)
    parser.add_argument("--max-candidates", type=int, default=DEFAULT_MAX_CANDIDATES)
    parser.add_argument(
        "--source-mode", choices=("informed", "neutral"), default="informed"
    )
    parser.add_argument(
        "--neutral-selection-seed",
        type=int,
        default=DEFAULT_NEUTRAL_SELECTION_SEED,
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--dataset-output", type=Path, default=None)
    args = parser.parse_args(argv)
    materializations: list[Q2TemporalPairMaterialization] | None = (
        [] if args.dataset_output is not None else None
    )
    payload = run_real_temporal_pair_smoke(
        input_dir=args.input_dir,
        prereg=args.prereg,
        tle_root=args.tle_root,
        users=args.users,
        seed=args.seed,
        calibration_seed=args.calibration_seed,
        max_anchor_steps=args.max_anchor_steps,
        max_candidates=args.max_candidates,
        source_mode=args.source_mode,
        neutral_selection_seed=args.neutral_selection_seed,
        materialization_out=materializations,
    )
    if args.dataset_output is not None:
        if materializations is None or len(materializations) != 1:
            raise RealTemporalPairSmokeError(
                "dataset output requires exactly one materialized temporal pair"
            )
        write_temporal_dataset(
            args.dataset_output,
            EEAxisTemporalDataset.from_pairs((materializations[0].pair,)),
        )
    rendered = json.dumps(payload, indent=2, sort_keys=True, default=_json_default)
    if args.output is not None:
        if args.output.exists():
            raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
