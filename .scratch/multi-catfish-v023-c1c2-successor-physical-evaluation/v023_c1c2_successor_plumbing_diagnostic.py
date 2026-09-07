#!/usr/bin/env python3
"""Stage-B one-world plumbing diagnostic for the V0.23 C1/C2 successor."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import v023_c1c2_successor_physical_runner as runner


SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-plumbing-diagnostic-v1"
PASS = "PASS_PLUMBING_INTEGRITY"
STOP = "STOP_PLUMBING_INTEGRITY"
WORLD_INDEX = 1
WORLD_ID = "train-v023-c1c2-successor-plumbing-001"
WORLD_SEED = 936547238915053535
TLE_ROOT = Path("/home/sat/mcrl-runtime/tle-frozen-20260820")


class PlumbingError(RuntimeError):
    """The one-world runtime plumbing boundary failed."""


@dataclass(frozen=True, slots=True)
class PlumbingWorld:
    episode_index: int = WORLD_INDEX
    world_id: str = WORLD_ID
    world_seed: int = WORLD_SEED
    field_root_digest: str = ""

    def verify(self) -> None:
        expected = runner.KeyedFadingField.from_components(
            runner.FIELD_COMPONENT, WORLD_SEED
        ).root_digest
        if (
            self.episode_index != WORLD_INDEX
            or self.world_id != WORLD_ID
            or self.world_seed != WORLD_SEED
            or self.field_root_digest != expected
        ):
            raise PlumbingError("plumbing world identity drifted")


def build_plumbing_world() -> PlumbingWorld:
    return PlumbingWorld(
        field_root_digest=runner.KeyedFadingField.from_components(
            runner.FIELD_COMPONENT, WORLD_SEED
        ).root_digest
    )


def _make_environment(archive: Any, users: int) -> Any:
    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.runtime.trainer_env import TrainerEnvironment

    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=users)),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def _evaluation_rngs(seed: int) -> tuple[Any, Any]:
    import numpy as np

    sequence = np.random.SeedSequence(seed)
    children = sequence.spawn(2)
    return np.random.default_rng(children[0]), np.random.default_rng(children[1])


def _write_once(path: Path, payload: object) -> None:
    try:
        runner._write_once(path, payload)
    except runner.C1C2PhysicalError as error:
        raise PlumbingError(str(error)) from error


def run_diagnostic(args: argparse.Namespace) -> dict[str, object]:
    started = time.monotonic()
    timings: dict[str, float] = {}
    output = Path(args.output)
    if output.exists() or output.is_symlink():
        raise PlumbingError("diagnostic output root must be absent")
    output.mkdir(parents=True, exist_ok=False)
    try:
        phase = time.monotonic()
        tle_input = Path(args.tle_root)
        if tle_input.is_symlink() or tle_input.resolve(strict=False) != TLE_ROOT:
            raise PlumbingError("diagnostic TLE root differs from the declared frozen root")
        if not tle_input.is_dir():
            raise PlumbingError("declared frozen TLE root is unavailable")
        from mcrl.env.tle import TleArchive

        learned = tuple(
            runner.load_learned_two_route_checkpoint(
                path,
                arm=arm,
                expected_sha256=digest,
            )
            for arm, path, digest in zip(
                runner.LEARNED_ARMS,
                args.learned_checkpoint,
                args.learned_sha256,
                strict=True,
            )
        )
        baseline = runner.load_baseline_policy(
            checkpoint_path=args.baseline_checkpoint,
            status_path=args.baseline_status,
            expected_status_sha256=args.baseline_status_sha256,
        )
        policies = (*learned, baseline)
        bindings_before = [policy.binding() for policy in policies]
        archive = TleArchive(tle_input)
        timings["input_authentication_s"] = time.monotonic() - phase

        phase = time.monotonic()
        world = build_plumbing_world()
        world.verify()
        diagnostic_identity = runner.canonical_sha256(
            {
                "schema": SCHEMA,
                "world_index": WORLD_INDEX,
                "world_id": WORLD_ID,
                "world_seed": WORLD_SEED,
                "field_component": runner.FIELD_COMPONENT,
                "field_root_digest": world.field_root_digest,
                "arms": list(runner.ARMS),
                "users": runner.USERS,
                "steps": runner.STEPS,
                "split": runner.SPLIT,
            }
        )
        adapter = runner.FixedPolicyEpisodeAdapter(
            policies=policies,
            archive=archive,
            environment_factory=_make_environment,
            rng_factory=_evaluation_rngs,
        )
        receipts = []
        arm_times: dict[str, float] = {}
        for arm in runner.ARMS:
            arm_started = time.monotonic()
            receipts.append(
                adapter.run_episode(
                    arm=arm,
                    world=world,  # type: ignore[arg-type]
                    plan_sha256=diagnostic_identity,
                )
            )
            arm_times[arm] = time.monotonic() - arm_started
        timings["four_arm_execution_s"] = time.monotonic() - phase

        phase = time.monotonic()
        runner._verify_matched_episode(receipts, world)  # type: ignore[arg-type]
        if tuple(receipt.arm for receipt in receipts) != runner.ARMS:
            raise PlumbingError("diagnostic lacks complete four-arm coverage")
        if any(receipt.steps != 10 or receipt.users != 100 for receipt in receipts):
            raise PlumbingError("diagnostic did not complete 100 users by ten steps")
        if any(
            not (receipt.total_bits >= 0 and receipt.total_energy_j > 0)
            for receipt in receipts
        ):
            raise PlumbingError("diagnostic physical receipts are non-finite")
        bindings_after = [policy.binding() for policy in policies]
        if bindings_before != bindings_after:
            raise PlumbingError("policy bytes changed during plumbing inference")
        if baseline.binding()["routes"] != []:
            raise PlumbingError("BASELINE acquired successor routes")
        pooled = {
            arm: runner.pool_receipts(
                [receipt for receipt in receipts if receipt.arm == arm], arm=arm
            )
            for arm in runner.ARMS
        }
        timings["integrity_verification_s"] = time.monotonic() - phase
        timings["total_s"] = time.monotonic() - started
        result = {
            "schema": SCHEMA,
            "status": PASS,
            "split": runner.SPLIT,
            "world": {
                "episode_index": WORLD_INDEX,
                "world_id": WORLD_ID,
                "world_seed": WORLD_SEED,
                "field_component": runner.FIELD_COMPONENT,
                "field_root_digest": world.field_root_digest,
                "tle_root": str(TLE_ROOT),
            },
            "arms": list(runner.ARMS),
            "receipts": [receipt.as_dict() for receipt in receipts],
            "descriptive_physical_endpoints": pooled,
            "ee_directions_use": "DESCRIPTIVE_ONLY_NO_PROMOTION_REJECTION_OR_TUNING",
            "phase_wall_times_s": timings,
            "arm_wall_times_s": arm_times,
            "fresh_environment_count": len(runner.ARMS),
            "q3_evaluated": False,
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
            "claim_ceiling": runner.CLAIM_CEILING,
        }
        _write_once(output / "plumbing-receipt.json", result)
        return result
    except Exception as error:
        timings["total_s"] = time.monotonic() - started
        stop = {
            "schema": SCHEMA,
            "status": STOP,
            "error_type": type(error).__name__,
            "error": str(error),
            "phase_wall_times_s": timings,
            "scientific_decision_emitted": False,
            "q3_evaluated": False,
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
        }
        if not (output / "plumbing-stop.json").exists():
            try:
                _write_once(output / "plumbing-stop.json", stop)
            except PlumbingError:
                pass
        if isinstance(error, PlumbingError):
            raise
        raise PlumbingError("plumbing diagnostic failed integrity") from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tle-root", type=Path, default=TLE_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--learned-checkpoint",
        type=Path,
        action="append",
        required=True,
        help="repeat exactly three times in FULL2, DROP_C1, DROP_C2 order",
    )
    parser.add_argument(
        "--learned-sha256",
        action="append",
        required=True,
        help="repeat exactly three times in the same order",
    )
    parser.add_argument("--baseline-checkpoint", type=Path, required=True)
    parser.add_argument("--baseline-status", type=Path, required=True)
    parser.add_argument("--baseline-status-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if len(args.learned_checkpoint) != 3 or len(args.learned_sha256) != 3:
        print(f"{STOP}: exactly three learned checkpoints/digests are required", file=sys.stderr)
        return 2
    try:
        result = run_diagnostic(args)
    except Exception as error:
        print(f"{STOP}: {error}", file=sys.stderr)
        traceback.print_exception(error, file=sys.stderr)
        return 2
    print(f"{result['status']} receipt={Path(args.output) / 'plumbing-receipt.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PASS",
    "PlumbingError",
    "PlumbingWorld",
    "SCHEMA",
    "STOP",
    "TLE_ROOT",
    "WORLD_ID",
    "WORLD_INDEX",
    "WORLD_SEED",
    "build_plumbing_world",
    "run_diagnostic",
]
