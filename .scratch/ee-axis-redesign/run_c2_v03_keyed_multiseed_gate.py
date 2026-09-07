#!/usr/bin/env python3
"""Run the sealed no-training G-C2 keyed-fading multi-seed viability gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

import numpy as np

import run_c2_v03_deterministic_plumbing_probe as probe


REPO = Path(__file__).resolve().parents[2]
DEFAULT_GATE_DIR = REPO / "artifacts" / "c2-v03-gate-20260831"
DEFAULT_PREREG = DEFAULT_GATE_DIR / "prereg.json"
DEFAULT_SEAL = DEFAULT_GATE_DIR / "prereg.sha256"
DEFAULT_OUTPUT = DEFAULT_GATE_DIR / "result.json"
SOURCE_MANIFEST_SCHEMA = "multi-catfish-mcrl-v03-c2-keyed-gate-source-manifest-v1"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
    """Return the byte representation used by all integrity receipts."""

    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _source_paths() -> list[Path]:
    """Return every local source file used by the no-training gate.

    ``training_pipeline._default_code_paths`` covers the production simulator
    and configuration.  The gate also imports the real-TLE loader and the
    append-only C2 fork through ``.scratch`` modules, so those modules are
    explicitly included in the receipt as well.  This is deliberately an
    explicit manifest: hashing ``sys.modules`` would accidentally include
    third-party packages and make the receipt machine-dependent.
    """

    modules = (
        probe,
        probe.smoke,
        probe.loader,
        probe.backend,
        probe.backend.chronology,
        probe.backend.core,
        probe.backend.forecast,
        probe.backend.runtime,
    )
    paths: list[Path] = [Path(__file__)]
    for module in modules:
        module_path = getattr(module, "__file__", None)
        if module_path is not None:
            paths.append(Path(module_path))
    # The probe imports these helpers directly from this module, so their
    # module path is not otherwise visible in the explicit module tuple.
    paths.append(Path(probe._freeze_lambda.__globals__["__file__"]))
    paths.extend(Path(path) for path in probe._default_code_paths())
    return sorted({path.resolve() for path in paths}, key=lambda path: str(path))


def _build_source_manifest(paths: Sequence[Path] | None = None) -> dict[str, Any]:
    """Build a self-contained, per-file SHA-256 source receipt."""

    repo = REPO.resolve()
    entries: list[dict[str, Any]] = []
    for raw_path in paths if paths is not None else _source_paths():
        path = Path(raw_path).expanduser().resolve()
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError as error:
            raise RuntimeError(f"source manifest path escapes repository: {path}") from error
        if not path.is_file():
            raise RuntimeError(f"source manifest file is missing: {path}")
        entries.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    entries.sort(key=lambda row: row["path"])
    payload = {"schema": SOURCE_MANIFEST_SCHEMA, "files": entries}
    manifest_sha256 = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    return {**payload, "manifest_sha256": manifest_sha256}


def _validate_source_manifest(
    manifest: Mapping[str, Any], *, expected_paths: Sequence[Path] | None = None
) -> str:
    """Verify a source receipt and return its manifest digest.

    The check is intentionally fail-closed and re-hashes every listed file;
    the digest alone is not treated as evidence that the files still match.
    ``expected_paths`` is used by the gate to ensure no local dependency was
    silently omitted from the receipt.
    """

    if manifest.get("schema") != SOURCE_MANIFEST_SCHEMA:
        raise RuntimeError("source manifest schema is not supported")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("source manifest has no files")
    supplied_digest = manifest.get("manifest_sha256")
    if not isinstance(supplied_digest, str):
        raise RuntimeError("source manifest has no manifest SHA-256")
    payload = {"schema": manifest["schema"], "files": files}
    actual_digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    if actual_digest != supplied_digest:
        raise RuntimeError("source manifest digest disagrees with its contents")

    repo = REPO.resolve()
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, Mapping):
            raise RuntimeError("source manifest file entry is not an object")
        relative = entry.get("path")
        expected_sha = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if (
            not isinstance(relative, str)
            or not relative
            or relative in seen
            or not isinstance(expected_sha, str)
            or not isinstance(expected_size, int)
            or expected_size < 0
        ):
            raise RuntimeError("source manifest contains a malformed file entry")
        seen.add(relative)
        path = (repo / relative).resolve()
        if not path.is_relative_to(repo) or not path.is_file():
            raise RuntimeError(f"source manifest file is missing or escapes repository: {relative}")
        if path.stat().st_size != expected_size or _file_sha256(path) != expected_sha:
            raise RuntimeError(f"source manifest SHA-256 mismatch: {relative}")

    if expected_paths is not None:
        expected = {
            Path(path).expanduser().resolve().relative_to(repo).as_posix()
            for path in expected_paths
        }
        if seen != expected:
            raise RuntimeError("source manifest file set disagrees with expected source set")
    return supplied_digest


def _read_sealed_prereg(path: Path, seal_path: Path) -> tuple[dict[str, Any], str]:
    actual = _file_sha256(path)
    sealed = seal_path.read_text(encoding="utf-8").split()[0]
    if actual != sealed:
        raise RuntimeError("C2 prereg digest disagrees with its seal")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "SEALED_BEFORE_MULTI_SEED_OUTCOMES":
        raise RuntimeError("C2 prereg is not sealed for a multi-seed run")
    return payload, actual


def _write_once(path: Path, payload: Any) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite sealed gate output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json_bytes(payload)
    # Exclusive creation makes a concurrent writer fail closed instead of
    # allowing a check-then-write race to overwrite a receipt.
    with path.open("xb") as handle:
        handle.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def _validate_schedule(
    schedule: Mapping[str, Any],
    *,
    prereg_sha256: str,
    seed: int,
    source_manifest_sha256: str | None = None,
) -> None:
    """Validate all self-digests and sealed identity fields of a schedule."""

    if schedule.get("schema") != "multi-catfish-mcrl-v03-c2-seed-schedule-v1":
        raise RuntimeError("schedule schema is not supported")
    if schedule.get("prereg_sha256") != prereg_sha256:
        raise RuntimeError("schedule disagrees with the sealed prereg digest")
    if (
        source_manifest_sha256 is not None
        and schedule.get("source_manifest_sha256") != source_manifest_sha256
    ):
        raise RuntimeError("schedule disagrees with the source manifest digest")
    if schedule.get("seed") != int(seed):
        raise RuntimeError("schedule seed disagrees with its requested seed")
    anchors = schedule.get("anchors")
    if not isinstance(anchors, list):
        raise RuntimeError("schedule anchors are not a list")
    seen_steps: set[int] = set()
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            raise RuntimeError("schedule anchor is not an object")
        step = anchor.get("step_index")
        if not isinstance(step, int) or step in seen_steps:
            raise RuntimeError("schedule contains a duplicate or malformed anchor step")
        seen_steps.add(step)
        anchor_digest = anchor.get("anchor_schedule_sha256")
        if not isinstance(anchor_digest, str):
            raise RuntimeError("schedule anchor has no SHA-256")
        anchor_payload = dict(anchor)
        anchor_payload.pop("anchor_schedule_sha256")
        if _schedule_digest(anchor_payload) != anchor_digest:
            raise RuntimeError("schedule anchor digest disagrees with its contents")
    schedule_digest = schedule.get("schedule_sha256")
    if not isinstance(schedule_digest, str):
        raise RuntimeError("schedule has no SHA-256")
    schedule_payload = dict(schedule)
    schedule_payload.pop("schedule_sha256")
    if _schedule_digest(schedule_payload) != schedule_digest:
        raise RuntimeError("schedule digest disagrees with its contents")


def _persist_or_resume_schedule(
    path: Path,
    schedule: Mapping[str, Any],
    *,
    prereg_sha256: str,
    seed: int,
    source_manifest_sha256: str | None = None,
) -> str:
    """Create a schedule once, or reuse only an exactly matching schedule.

    The expected schedule is freshly discovered before any forecast outcome is
    scored.  If a file already exists, its bytes, JSON payload, sealed
    prereg/seed identity, and every nested digest must match that expected
    schedule.  Any mismatch—including a symlink or malformed partial file—
    raises without overwriting it.
    """

    _validate_schedule(
        schedule,
        prereg_sha256=prereg_sha256,
        seed=seed,
        source_manifest_sha256=source_manifest_sha256,
    )
    expected_payload = dict(schedule)
    encoded = _canonical_json_bytes(expected_payload)
    expected_file_sha256 = hashlib.sha256(encoded).hexdigest()
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"existing schedule is not a regular file: {path}")
        actual_bytes = path.read_bytes()
        if hashlib.sha256(actual_bytes).hexdigest() != expected_file_sha256:
            raise RuntimeError(f"existing schedule bytes disagree with sealed schedule: {path}")
        try:
            existing = json.loads(actual_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"existing schedule is not valid JSON: {path}") from error
        if not isinstance(existing, Mapping) or dict(existing) != expected_payload:
            raise RuntimeError(f"existing schedule content disagrees with sealed schedule: {path}")
        _validate_schedule(
            existing,
            prereg_sha256=prereg_sha256,
            seed=seed,
            source_manifest_sha256=source_manifest_sha256,
        )
        return expected_file_sha256

    return _write_once(path, expected_payload)


def _schedule_rng(prereg_sha256: str, *, seed: int, step: int) -> np.random.Generator:
    material = f"c2-v03-gate-schedule-v1:{prereg_sha256}:{seed}:{step}".encode()
    value = int.from_bytes(hashlib.sha256(material).digest()[:16], "big")
    return np.random.Generator(np.random.PCG64(value))


def _schedule_digest(value: Any) -> str:
    return probe.backend.forecast.canonical_payload_sha256(value)


def _discover_seed_schedule(
    trainer: Any,
    archive: Any,
    *,
    seed: int,
    prereg_sha256: str,
    source_manifest_sha256: str,
    max_anchors: int,
    max_candidates: int,
) -> dict[str, Any]:
    """Discover the whole pre-outcome Main schedule before any fork is scored."""

    wrapped = probe.loader._make_environment(archive, users=probe.smoke.USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = probe.loader._evaluation_rngs(
        seed
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    anchors: list[dict[str, Any]] = []
    steps_per_episode = int(wrapped.environment.driver.config.steps_per_episode)

    while int(observation.step_index) <= probe.smoke.MAX_ANCHOR_STEP:
        main_actions, main_physical = probe.smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        departures = probe._departure_users(wrapped, main_physical)
        step = int(observation.step_index)
        if departures and steps_per_episode - step >= len(probe.EXPECTED_OFFSETS):
            take = min(max_candidates, len(departures))
            schedule_rng = _schedule_rng(prereg_sha256, seed=seed, step=step)
            sampled = schedule_rng.choice(
                np.asarray(departures, dtype=np.int64),
                size=take,
                replace=False,
            )
            focal_users = sorted(int(value) for value in sampled.tolist())
            anchor = {
                "seed": seed,
                "step_index": step,
                "eligible_departure_users": [int(value) for value in departures],
                "scheduled_focal_users": focal_users,
                "opening_main_actions": [int(value) for value in main_actions.tolist()],
                "opening_main_physical_actions": [
                    None if value is None else [int(value[0]), int(value[1])]
                    for value in main_physical
                ],
            }
            anchor["anchor_schedule_sha256"] = _schedule_digest(anchor)
            anchors.append(anchor)
            if len(anchors) >= max_anchors:
                break

        result = wrapped.step(main_actions, env_rng)
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation

    schedule = {
        "schema": "multi-catfish-mcrl-v03-c2-seed-schedule-v1",
        "prereg_sha256": prereg_sha256,
        "source_manifest_sha256": source_manifest_sha256,
        "seed": seed,
        "selection": "uniform-without-replacement-domain-separated-preoutcome",
        "anchors": anchors,
    }
    schedule["schedule_sha256"] = _schedule_digest(schedule)
    return schedule


def _component_totals(
    receipts: Sequence[dict[str, Any]],
    *,
    interval_s: float,
    multiplier: float,
) -> dict[str, float]:
    downstream = receipts[1:]
    delta_bits = interval_s * math.fsum(
        float(row["delta_system_rate_bps"]) for row in downstream
    )
    delta_energy = interval_s * math.fsum(
        float(row["delta_system_power_w"]) for row in downstream
    )
    return {
        "delta_bits": delta_bits,
        "delta_energy_j": delta_energy,
        "lambda_delta_energy_bits": multiplier * delta_energy,
    }


def _execute_seed_schedule(
    trainer: Any,
    archive: Any,
    schedule: dict[str, Any],
    *,
    checkpoint_sha256: str,
    environment_source_sha256: str,
    reward_source_sha256: str,
    interval_s: float,
    multiplier: float,
) -> dict[str, Any]:
    seed = int(schedule["seed"])
    by_step = {int(row["step_index"]): row for row in schedule["anchors"]}
    wrapped = probe.loader._make_environment(archive, users=probe.smoke.USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = probe.loader._evaluation_rngs(
        seed
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    rows: list[dict[str, Any]] = []
    completed_steps: set[int] = set()

    while int(observation.step_index) <= probe.smoke.MAX_ANCHOR_STEP:
        main_actions, main_physical = probe.smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        step = int(observation.step_index)
        scheduled = by_step.get(step)
        if scheduled is not None:
            if [int(value) for value in main_actions.tolist()] != scheduled[
                "opening_main_actions"
            ]:
                raise RuntimeError("forecast replay Main actions disagree with sealed schedule")
            departures = probe._departure_users(wrapped, main_physical)
            if any(uid not in departures for uid in scheduled["scheduled_focal_users"]):
                raise RuntimeError("forecast replay eligibility disagrees with sealed schedule")
            completed_steps.add(step)
            for focal_user in scheduled["scheduled_focal_users"]:
                started = time.perf_counter()
                base = {
                    "seed": seed,
                    "step_index": step,
                    "anchor_schedule_sha256": scheduled["anchor_schedule_sha256"],
                    "focal_user": int(focal_user),
                }
                try:
                    service = probe.backend.C2TemporalForkTrainerBackend(
                        wrapped=wrapped,
                        states=states,
                        masks=masks,
                        observation=observation,
                        env_rng=env_rng,
                        trainer=trainer,
                        checkpoint_sha256=checkpoint_sha256,
                        environment_source_sha256=environment_source_sha256,
                        reward_source_sha256=reward_source_sha256,
                        evaluation_seed=seed,
                        focal_user=int(focal_user),
                        forecast_fading_mode=probe.KEYED_FADING_VERSION,
                    )
                    prepared = service.prepare_hold_or_max_lagged_gain_rival(
                        focal_user=int(focal_user)
                    )
                    build = prepared.run_forecast()
                    receipts, z2, service_guard = probe._trace_receipts(
                        prepared.reference_trace,
                        prepared.candidate_trace,
                        interval_s=interval_s,
                        multiplier=multiplier,
                        focal_user=int(focal_user),
                    )
                    rows.append(
                        {
                            **base,
                            "outcome": "COMPLETE_TRACE_SCORED",
                            "candidate_key": [int(value) for value in prepared.candidate_key],
                            "source_rule": prepared.source_rule,
                            "reference_trace_sha256": build.reference_trace_sha256,
                            "candidate_trace_sha256": build.candidate_trace_sha256,
                            "forecast_payload_sha256": build.forecast_payload_sha256,
                            "fading_authority_mode": build.authority.fading_mode,
                            "fading_field_receipt": prepared.forecast_rng_state[
                                "fading_field_receipt"
                            ],
                            "offset_receipts": receipts,
                            "components": _component_totals(
                                receipts,
                                interval_s=interval_s,
                                multiplier=multiplier,
                            ),
                            "z2_temporal_surplus_bits": z2,
                            "service_guard": service_guard,
                            "positive_service_safe": bool(
                                service_guard["passed"] and z2 > 0.0
                            ),
                            "elapsed_s": time.perf_counter() - started,
                        }
                    )
                except probe.backend.C2ForecastSupportRejection as error:
                    rows.append(
                        {
                            **base,
                            **probe._support_censor(error),
                            "elapsed_s": time.perf_counter() - started,
                        }
                    )
                except Exception as error:
                    rows.append(
                        {
                            **base,
                            "outcome": "INSTRUMENT_ERROR_NOT_SCORED",
                            "error_class": type(error).__name__,
                            "error": str(error),
                            "elapsed_s": time.perf_counter() - started,
                        }
                    )

        if len(completed_steps) == len(by_step):
            break
        result = wrapped.step(main_actions, env_rng)
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation

    if completed_steps != set(by_step):
        raise RuntimeError("forecast replay did not reach every sealed anchor")
    return {
        "seed": seed,
        "schedule_sha256": schedule["schedule_sha256"],
        "anchors_scheduled": len(schedule["anchors"]),
        "attempts_scheduled": sum(
            len(anchor["scheduled_focal_users"]) for anchor in schedule["anchors"]
        ),
        "rows": rows,
    }


def _adjudicate(prereg: dict[str, Any], seed_results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for seed in seed_results for row in seed["rows"]]
    complete = [row for row in rows if row["outcome"] == "COMPLETE_TRACE_SCORED"]
    censored = [
        row for row in rows if row["outcome"] == "RIGHT_CENSORED_SUPPORT_REJECTION"
    ]
    errors = [row for row in rows if row["outcome"] == "INSTRUMENT_ERROR_NOT_SCORED"]
    service_safe = [row for row in complete if row["service_guard"]["passed"]]
    positive = [row for row in complete if row["positive_service_safe"]]
    attempts = len(rows)
    complete_fraction = len(complete) / attempts if attempts else 0.0
    censor_fraction = len(censored) / attempts if attempts else 0.0
    positive_seeds = sorted({int(row["seed"]) for row in positive})
    positive_anchor_digests = sorted(
        {str(row["anchor_schedule_sha256"]) for row in positive}
    )
    decision = prereg["decision"]["go"]

    per_seed = []
    for seed_result in seed_results:
        seed_rows = seed_result["rows"]
        seed_complete = [
            row for row in seed_rows if row["outcome"] == "COMPLETE_TRACE_SCORED"
        ]
        seed_safe = [row for row in seed_complete if row["service_guard"]["passed"]]
        seed_positive = [row for row in seed_complete if row["positive_service_safe"]]
        per_seed.append(
            {
                "seed": seed_result["seed"],
                "anchors": seed_result["anchors_scheduled"],
                "attempts": len(seed_rows),
                "complete": len(seed_complete),
                "service_safe_complete": len(seed_safe),
                "positive_service_safe": len(seed_positive),
                "censored": sum(
                    row["outcome"] == "RIGHT_CENSORED_SUPPORT_REJECTION"
                    for row in seed_rows
                ),
                "errors": sum(
                    row["outcome"] == "INSTRUMENT_ERROR_NOT_SCORED"
                    for row in seed_rows
                ),
            }
        )

    coverage_ok = bool(
        attempts >= int(decision["minimum_total_attempts"])
        and all(
            row["anchors"] >= int(prereg["evaluation"]["minimum_anchors_per_seed"])
            and row["attempts"] >= int(prereg["evaluation"]["minimum_attempts_per_seed"])
            for row in per_seed
        )
    )
    completion_ok = bool(
        complete_fraction >= float(decision["minimum_complete_fraction"])
        and censor_fraction <= float(decision["maximum_censor_fraction"])
        and all(
            row["complete"] >= int(decision["minimum_complete_per_seed"])
            and row["service_safe_complete"]
            >= int(decision["minimum_service_safe_complete_per_seed"])
            for row in per_seed
        )
    )
    positive_ok = bool(
        len(positive_seeds) >= int(decision["minimum_positive_seeds"])
        and len(positive_anchor_digests)
        >= int(decision["minimum_distinct_positive_seed_anchor_digests"])
    )
    if errors:
        outcome = "INSTRUMENT_FAIL"
    elif not coverage_ok or not completion_ok:
        outcome = "INDETERMINATE"
    elif positive_ok:
        outcome = "GO_BOUNDED_LEARNABILITY_PILOT_ONLY"
    else:
        outcome = "SCIENTIFIC_NO_GO"
    return {
        "outcome": outcome,
        "attempts": attempts,
        "complete": len(complete),
        "complete_fraction": complete_fraction,
        "service_safe_complete": len(service_safe),
        "censored": len(censored),
        "censor_fraction": censor_fraction,
        "instrument_errors": len(errors),
        "positive_service_safe": len(positive),
        "positive_seeds": positive_seeds,
        "positive_anchor_digests": positive_anchor_digests,
        "coverage_ok": coverage_ok,
        "completion_ok": completion_ok,
        "positive_ok": positive_ok,
        "per_seed": per_seed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    prereg, prereg_sha256 = _read_sealed_prereg(args.prereg, args.seal)
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite gate result: {args.output}")

    record = probe.read_prereg(probe.DEFAULT_PREREG)
    frozen_temp = probe.tempfile.TemporaryDirectory(prefix="mcrl-c2-v03-gate-")
    archive = probe._frozen_archive(
        record,
        Path(probe.TLE_ROOT_DEFAULT).expanduser(),
        Path(frozen_temp.name) / "frozen-tle",
    )
    trainer, checkpoint = probe.loader._verify_and_load_trainer(
        record,
        archive,
        run_dir=probe.DEFAULT_INPUT / "main",
        users=probe.smoke.USERS,
    )
    if checkpoint["checkpoint_sha256"] != prereg["checkpoint_sha256"]:
        raise RuntimeError("loaded checkpoint disagrees with sealed C2 prereg")
    networks_before = probe.smoke._network_snapshot(trainer)
    replay_before = len(trainer.replay)
    checkpoint_before = _file_sha256(probe.DEFAULT_INPUT / "main" / "final-checkpoint.pt")
    expected_source_paths = _source_paths()
    source_manifest = _build_source_manifest(expected_source_paths)
    source_manifest_sha256 = _validate_source_manifest(
        source_manifest, expected_paths=expected_source_paths
    )
    # Retain the production-code-only digest for comparison with older
    # receipts, while binding the current C2 forecast authority to the full
    # manifest digest (including this runner and the .scratch adapters).
    code_source_sha256 = probe._code_sha256(probe._default_code_paths())
    environment_source_sha256 = source_manifest_sha256
    reward_source_sha256 = _file_sha256(REPO / "src/mcrl/env/step.py")

    calibration_environment = probe.loader._make_environment(
        archive, users=probe.smoke.USERS
    )
    calibration = probe._freeze_lambda(
        trainer,
        calibration_environment,
        seed=int(prereg["multiplier"]["calibration_seed"]),
    )
    multiplier = float(calibration["lambda_bits_per_j"])
    if multiplier.hex() != prereg["multiplier"]["lambda_hex"]:
        raise RuntimeError("recomputed global lambda disagrees with sealed lambda_hex")
    interval_s = float(calibration["interval_s"])

    schedules = []
    for seed in prereg["evaluation"]["seeds"]:
        schedule = _discover_seed_schedule(
            trainer,
            archive,
            seed=int(seed),
            prereg_sha256=prereg_sha256,
            source_manifest_sha256=source_manifest_sha256,
            max_anchors=int(prereg["evaluation"]["maximum_anchors_per_seed"]),
            max_candidates=int(
                prereg["evaluation"]["maximum_candidates_per_anchor"]
            ),
        )
        schedule_path = args.output.parent / f"schedule-{int(seed)}.json"
        schedule["file_sha256"] = _persist_or_resume_schedule(
            schedule_path,
            schedule,
            prereg_sha256=prereg_sha256,
            seed=int(seed),
            source_manifest_sha256=source_manifest_sha256,
        )
        schedules.append(schedule)

    started = time.perf_counter()
    seed_results = []
    for schedule in schedules:
        seed_results.append(
            _execute_seed_schedule(
                trainer,
                archive,
                schedule,
                checkpoint_sha256=checkpoint["checkpoint_sha256"],
                environment_source_sha256=environment_source_sha256,
                reward_source_sha256=reward_source_sha256,
                interval_s=interval_s,
                multiplier=multiplier,
            )
        )

    networks_unchanged = probe.smoke._networks_equal(trainer, networks_before)
    replay_unchanged = len(trainer.replay) == replay_before
    checkpoint_after = _file_sha256(probe.DEFAULT_INPUT / "main" / "final-checkpoint.pt")
    checkpoint_unchanged = checkpoint_after == checkpoint_before
    adjudication = _adjudicate(prereg, seed_results)
    if not (networks_unchanged and replay_unchanged and checkpoint_unchanged):
        adjudication["outcome"] = "INSTRUMENT_FAIL"
        adjudication["nonmutation_ok"] = False
    else:
        adjudication["nonmutation_ok"] = True

    result = {
        "schema": "multi-catfish-mcrl-v03-c2-keyed-multiseed-gate-result-v1",
        "prereg_sha256": prereg_sha256,
        "baseline_prereg_digest": record.digest,
        "ephemeris_file_set_sha256": record.sections["ephemeris"][
            "file_set_sha256"
        ],
        "claim_ceiling": prereg["claim_ceiling"],
        "fading_mode": prereg["fading"]["mode"],
        "checkpoint_sha256": checkpoint["checkpoint_sha256"],
        "environment_source_sha256": environment_source_sha256,
        "code_source_sha256": code_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "source_manifest": source_manifest,
        "source_manifest_sha256": source_manifest_sha256,
        "lambda_calibration": {
            **calibration,
            "lambda_hex": multiplier.hex(),
        },
        "schedule_files": [
            {
                "seed": schedule["seed"],
                "schedule_sha256": schedule["schedule_sha256"],
                "file_sha256": schedule["file_sha256"],
            }
            for schedule in schedules
        ],
        "seed_results": seed_results,
        "adjudication": adjudication,
        "main_networks_bitwise_unchanged": networks_unchanged,
        "main_replay_unchanged": replay_unchanged,
        "checkpoint_unchanged": checkpoint_unchanged,
        "training_or_replay_write": False,
        "elapsed_s": time.perf_counter() - started,
    }
    _write_once(args.output, result)
    frozen_temp.cleanup()
    print(json.dumps(adjudication, indent=2, sort_keys=True))
    return 0 if adjudication["outcome"] != "INSTRUMENT_FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
