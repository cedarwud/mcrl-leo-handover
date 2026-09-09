#!/usr/bin/env python3
"""Explicit server entrypoint for the bounded V0.23 DROP_C3 evaluation.

This command is intentionally separate from the generic two-arm adapter.  It
loads exactly one frozen ``DROP_C3`` policy arm over 100 TRAIN-development
worlds, records timing separately from the scientific result, and supports
resume only from the runner's episode-100 checkpoint.  Importing this module
does not import NumPy, PyTorch, TLE, or the simulator.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback
from types import ModuleType
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNNER_PATH = HERE / "v023_physical_episode_runner.py"
CONTRACT_PATH = HERE / "V023-DROPC3-DEVELOPMENT-EVALUATION-CONTRACT-2026-09-06.md"
PREREG_PATH = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
USERS = 100
STEPS = 10
EPISODES = 100
WORLD_SEEDS = tuple(2026090601 + offset for offset in range(EPISODES))
WORLD_IDS = tuple(f"world-{offset:06d}" for offset in range(1, EPISODES + 1))


class V023DropC3ServerError(RuntimeError):
    """A frozen development-evaluation input or output boundary failed."""


def _load_runner() -> ModuleType:
    target = RUNNER_PATH
    if target.is_symlink() or not target.is_file():
        raise V023DropC3ServerError(f"runner is missing or symlinked: {target}")
    spec = importlib.util.spec_from_file_location(
        "mcrl_v023_dropc3_physical_runner_server", target
    )
    if spec is None or spec.loader is None:
        raise V023DropC3ServerError(f"cannot load runner: {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise V023DropC3ServerError("runner import failed") from error
    return module


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023DropC3ServerError("server receipt is not canonical JSON") from error


def _write_once(path: Path, payload: Mapping[str, object]) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise V023DropC3ServerError(f"refusing to overwrite server receipt: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.is_symlink() or not target.parent.is_dir():
        raise V023DropC3ServerError(f"server receipt parent is not a directory: {target.parent}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, target)
        except FileExistsError as error:
            raise V023DropC3ServerError(
                f"refusing to overwrite concurrently-created receipt: {target}"
            ) from error
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _read_mapping(path: Path, *, label: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023DropC3ServerError(f"{label} is missing or symlinked: {target}")
    try:
        value = json.loads(target.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V023DropC3ServerError(f"{label} is not ASCII JSON: {target}") from error
    if not isinstance(value, dict):
        raise V023DropC3ServerError(f"{label} is not a JSON object: {target}")
    return value


def _freeze_archive(record: Any, source_root: Path, target_root: Path, runner: ModuleType) -> Any:
    """Copy exactly the PREREG-listed TLE files into a fresh archive."""

    from mcrl.env.tle import TleArchive
    from mcrl.runtime.training_pipeline import assert_ephemeris_matches_record

    source_input = Path(source_root)
    source = source_input.resolve(strict=False)
    if source_input.is_symlink() or not source.is_dir():
        raise V023DropC3ServerError(f"TLE root is not a regular directory: {source_input}")
    target = Path(target_root)
    target.mkdir(parents=True, exist_ok=False)
    ephemeris = record.sections.get("ephemeris")
    rows = ephemeris.get("frozen_files") if isinstance(ephemeris, Mapping) else None
    if not isinstance(rows, list) or not rows:
        raise V023DropC3ServerError("PREREG has no frozen TLE file list")
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("file"), str):
            raise V023DropC3ServerError("PREREG TLE file row is malformed")
        relative = Path(row["file"])
        if relative.is_absolute() or relative.name != str(relative) or relative.name != relative.as_posix():
            raise V023DropC3ServerError("PREREG TLE file path is not a flat filename")
        source_file = source / relative.name
        destination = target / relative.name
        if source_file.is_symlink() or not source_file.is_file():
            raise V023DropC3ServerError(f"frozen TLE file is missing or symlinked: {source_file}")
        expected = row.get("sha256")
        actual = runner.file_sha256(source_file)
        if actual != expected:
            raise V023DropC3ServerError(
                f"frozen TLE file hash mismatch: {relative.name}"
            )
        try:
            os.link(source_file, destination)
        except OSError:
            try:
                shutil.copyfile(source_file, destination)
            except OSError as error:
                raise V023DropC3ServerError(
                    f"cannot stage frozen TLE file: {relative.name}"
                ) from error
    archive = TleArchive(target)
    try:
        assert_ephemeris_matches_record(record, archive=archive)
    except Exception as error:
        raise V023DropC3ServerError("staged TLE archive disagrees with PREREG") from error
    return archive


def _make_environment(archive: Any) -> Any:
    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.runtime.trainer_env import TrainerEnvironment

    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=USERS)),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, default=PREREG_PATH)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume-checkpoint", type=Path)
    return parser


def _authenticate_inputs(args: argparse.Namespace, runner: ModuleType) -> Any:
    contract_input = Path(args.contract)
    if contract_input.is_symlink():
        raise V023DropC3ServerError("development contract must not be symlinked")
    contract = contract_input.resolve(strict=False)
    if contract != CONTRACT_PATH.resolve(strict=False):
        raise V023DropC3ServerError("only the declared development contract path is permitted")
    if runner.file_sha256(contract) != runner.DEVELOPMENT_CONTRACT_SHA256:
        raise V023DropC3ServerError("development contract bytes changed")
    prereg_input = Path(args.prereg)
    if prereg_input.is_symlink():
        raise V023DropC3ServerError("canonical TRAIN PREREG must not be symlinked")
    prereg = prereg_input.resolve(strict=False)
    if prereg != PREREG_PATH.resolve(strict=False):
        raise V023DropC3ServerError("only the canonical TRAIN PREREG is permitted")
    if runner.file_sha256(prereg) != runner.DEVELOPMENT_PREREG_SHA256:
        raise V023DropC3ServerError("canonical TRAIN PREREG bytes changed")
    from mcrl.runtime.prereg import read_prereg

    try:
        record = read_prereg(prereg)
    except Exception as error:
        raise V023DropC3ServerError("canonical TRAIN PREREG cannot be reopened") from error
    if record.digest != runner.DEVELOPMENT_PREREG_RECORD_DIGEST:
        raise V023DropC3ServerError("canonical TRAIN PREREG record digest changed")
    return record


def _build_plan(runner: ModuleType) -> Any:
    worlds = tuple(
        runner.make_world_binding(
            episode_index=index,
            world_id=world_id,
            world_seed=seed,
        )
        for index, (world_id, seed) in enumerate(zip(WORLD_IDS, WORLD_SEEDS), start=1)
    )
    return runner.V023EpisodePlan(
        worlds=worlds,
        arms=runner.DROP_C3_ONLY_ARMS,
        evaluation_contract_sha256=runner.DEVELOPMENT_CONTRACT_SHA256,
    )


def _validate_result(result: Mapping[str, object], output: Path, runner: ModuleType) -> None:
    expected = {
        "schema": runner.RESULT_SCHEMA,
        "status": runner.STATUS,
        "split": runner.EVALUATION_SPLIT,
        "completed_episode": EPISODES,
        "planned_episodes": EPISODES,
        "arms": list(runner.DROP_C3_ONLY_ARMS),
        "receipt_count": EPISODES,
        "evaluation_contract_sha256": runner.DEVELOPMENT_CONTRACT_SHA256,
        "q3_evaluated": False,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "baseline_artifact_emitted": False,
        "between_arm_comparison_performed": False,
    }
    for field, value in expected.items():
        if result.get(field) != value:
            raise V023DropC3ServerError(f"result disagrees with DROP_C3 contract: {field}")
    if result.get("checkpoints") != ["checkpoints/checkpoint-000100.json"]:
        raise V023DropC3ServerError("result lacks the episode-100 checkpoint")
    result_path = output / "result.json"
    if runner.file_sha256(result_path) == "":  # pragma: no cover - impossible guard
        raise V023DropC3ServerError("result hash is empty")


def _validate_checkpoint(output: Path, runner: ModuleType, plan: Any) -> None:
    """Reopen the published block before publishing a timing receipt."""

    checkpoint_path = output / "checkpoints" / "checkpoint-000100.json"
    try:
        payload = runner._read_checkpoint(checkpoint_path)
    except Exception as error:
        raise V023DropC3ServerError("episode-100 checkpoint cannot be reopened") from error
    if (
        payload.get("completed_episode") != EPISODES
        or payload.get("plan_sha256") != plan.plan_sha256
        or payload.get("evaluation_contract_sha256") != runner.DEVELOPMENT_CONTRACT_SHA256
        or payload.get("arms") != list(runner.DROP_C3_ONLY_ARMS)
        or payload.get("checkpoint_every") != runner.CHECKPOINT_EVERY
    ):
        raise V023DropC3ServerError("episode-100 checkpoint disagrees with development plan")
    raw_rows = payload.get("receipts")
    if not isinstance(raw_rows, list) or len(raw_rows) != EPISODES:
        raise V023DropC3ServerError("episode-100 checkpoint lacks exactly 100 DROP_C3 receipts")
    for expected_index, raw_row in enumerate(raw_rows, start=1):
        try:
            row = runner._receipt_from_mapping(raw_row)
        except Exception as error:
            raise V023DropC3ServerError("episode-100 checkpoint contains an invalid receipt") from error
        world = plan.worlds[expected_index - 1]
        if (
            row.arm != "DROP_C3"
            or row.episode_index != expected_index
            or row.world_id != world.world_id
            or row.world_seed != world.world_seed
            or row.field_root_digest != world.field_root_digest
        ):
            raise V023DropC3ServerError("episode-100 checkpoint world/arm coverage drifted")
    states = payload.get("resume_states")
    if not isinstance(states, Mapping) or set(states) != {"DROP_C3"}:
        raise V023DropC3ServerError("episode-100 checkpoint resume state is not DROP_C3-only")


def launch(args: argparse.Namespace) -> dict[str, object]:
    runner = _load_runner()
    record = _authenticate_inputs(args, runner)
    output_input = Path(args.output)
    if output_input.is_symlink():
        raise V023DropC3ServerError(f"output is symlinked: {output_input}")
    output = output_input.resolve(strict=False)
    if output.exists() and not output.is_dir():
        raise V023DropC3ServerError(f"output is not a regular directory: {output_input}")
    if args.resume_checkpoint is None and output.exists() and any(output.iterdir()):
        raise V023DropC3ServerError(f"refusing to overwrite non-empty output: {output}")
    if args.resume_checkpoint is not None:
        checkpoint_input = Path(args.resume_checkpoint)
        if checkpoint_input.is_symlink():
            raise V023DropC3ServerError(
                f"resume checkpoint is missing or symlinked: {checkpoint_input}"
            )
        checkpoint = checkpoint_input.resolve(strict=False)
        if not checkpoint.is_file():
            raise V023DropC3ServerError(f"resume checkpoint is missing: {checkpoint_input}")
        if not checkpoint.is_relative_to(output):
            raise V023DropC3ServerError("resume checkpoint must be below output")
    plan = _build_plan(runner)
    plan.verify(checkpoint=runner.V020CheckpointBinding())
    with tempfile.TemporaryDirectory(prefix="mcrl-v023-dropc3-tle-") as temporary:
        archive = _freeze_archive(record, Path(args.tle_root), Path(temporary) / "frozen", runner)
        from mcrl.runtime.training_pipeline import _evaluation_rngs

        frozen = runner.load_v020_q12()
        adapter = runner.V023PhysicalEpisodeAdapter(
            frozen=frozen,
            archive=archive,
            environment_factory=lambda _archive, _users: _make_environment(_archive),
            rng_factory=_evaluation_rngs,
        )
        evaluation_runner = runner.V023PhysicalEpisodeRunner(
            adapter=adapter,
            plan=plan,
        )
        started = time.monotonic()
        result = evaluation_runner.run(
            output_dir=output,
            resume_checkpoint=args.resume_checkpoint,
        )
        elapsed = time.monotonic() - started
    if not isinstance(result, Mapping):
        raise V023DropC3ServerError("evaluation runner returned a non-mapping result")
    _validate_result(result, output, runner)
    _validate_checkpoint(output, runner, plan)
    result_path = output / "result.json"
    timing = {
        "schema": f"{runner.RESULT_SCHEMA}-timing",
        "status": runner.STATUS,
        "split": runner.EVALUATION_SPLIT,
        "arm": "DROP_C3",
        "completed_episode": EPISODES,
        "evaluation_contract_sha256": runner.DEVELOPMENT_CONTRACT_SHA256,
        "result_sha256": runner.file_sha256(result_path),
        "wall_time_s": float(elapsed),
        "baseline_artifact_emitted": False,
        "between_arm_comparison_performed": False,
        "q3_evaluated": False,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    _write_once(output / "timing.json", timing)
    return {"result": result_path, "timing": output / "timing.json"}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        paths = launch(args)
    except Exception as error:
        # Runner/environment failures are intentionally reported through the
        # same fail-closed controller boundary as input/output failures.  Do
        # not let a raw V023PhysicalError escape as an ambiguous traceback
        # with a successful-looking server invocation.
        print(f"DROP_C3_EVALUATION_ERROR pid={os.getpid()}: {error}", file=sys.stderr)
        traceback.print_exception(error, file=sys.stderr)
        return 2
    print(f"DROP_C3_EVALUATION_PASS result={paths['result']} timing={paths['timing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
