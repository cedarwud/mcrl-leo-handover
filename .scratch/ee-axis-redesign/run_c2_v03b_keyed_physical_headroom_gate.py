#!/usr/bin/env python3
"""Run the prospective, no-training C2 V0.3B physical-headroom gate.

This runner is intentionally a new namespace.  It never reuses the sealed
fixed-hold gate's output directory or schedules.  A fresh run first validates
the sealed V0.3B preregistration and a per-file source manifest, then discovers
and seals each Main departure schedule before scoring any detached fork.

The candidate branch is the implemented V0.3B policy: hold the opening
physical key while it is uniquely legal in the candidate branch's current
predecision table, release once on the first support loss (or at the planned
horizon), and execute complete branch-local Main thereafter.  A downstream
support expiry is therefore a complete trace; an opening-support failure is
right-censored, while any unexpected post-opening rejection is an instrument
failure.  No Q-network, replay buffer, checkpoint, or live Main environment is
updated by this gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_V03 = REPO / ".scratch" / "c2-v03"
STAGE0 = REPO / ".scratch" / "catfish-stage0"
SMC = REPO / ".scratch" / "smc-er-short-ep"
LEGACY = REPO / ".scratch" / "catfish-oracle-gate"
for path in (HERE, C2_V03, STAGE0, SMC, LEGACY, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_temporal_fork_chronology as chronology  # noqa: E402
import c2_temporal_fork_core as core  # noqa: E402
import c2_temporal_fork_episode_runner as episode_runner  # noqa: E402
import c2_temporal_fork_forecast_adapter as forecast  # noqa: E402
import c2_temporal_fork_learning_adapter as learning  # noqa: E402
import c2_temporal_fork_option_runner as option_runner  # noqa: E402
import c2_temporal_fork_runtime_adapter as runtime  # noqa: E402
import c2_temporal_fork_torch_adapter as torch_adapter  # noqa: E402
import c2_temporal_fork_trainer_backend as backend  # noqa: E402
import c2_temporal_fork_training_step as training_step  # noqa: E402
import run_c2_v03_deterministic_plumbing_probe as probe  # noqa: E402
import run_c2_v03_real_backend_smoke as smoke  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KEYED_FADING_VERSION  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402


GATE_NAME = "c2-v03b-reactive-keyed-physical-headroom-gate-20260831"
DEFAULT_GATE_DIR = REPO / "artifacts" / GATE_NAME
DEFAULT_PREREG = DEFAULT_GATE_DIR / "prereg.json"
DEFAULT_SEAL = DEFAULT_GATE_DIR / "prereg.sha256"
DEFAULT_SOURCE_MANIFEST = DEFAULT_GATE_DIR / "source-manifest.json"
DEFAULT_OUTPUT = DEFAULT_GATE_DIR / "result.json"
SOURCE_MANIFEST_SCHEMA = "multi-catfish-mcrl-v03b-c2-reactive-gate-source-manifest-v1"
PREREG_SCHEMA = "multi-catfish-mcrl-v03b-c2-reactive-keyed-headroom-prereg-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v03b-c2-reactive-keyed-headroom-result-v1"
SCHEDULE_SCHEMA = "multi-catfish-mcrl-v03b-c2-reactive-seed-schedule-v1"
EXPECTED_OFFSETS = tuple(range(core.HORIZON_STEPS + 1))
TEMPORAL_OFFSETS = EXPECTED_OFFSETS[1:]
SOURCE_RULES = frozenset(
    ("incumbent-hold", "max-lagged-candidate-sinr-rival")
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
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


def _schedule_digest(payload: Any) -> str:
    return forecast.canonical_payload_sha256(payload)


def _source_paths() -> list[Path]:
    """Return the exact current source set used or versioned by this gate."""

    modules = (
        probe,
        probe.smoke,
        probe.loader,
        probe.backend,
        chronology,
        core,
        forecast,
        runtime,
        episode_runner,
        learning,
        option_runner,
        torch_adapter,
        training_step,
        backend,
    )
    paths: list[Path] = [Path(__file__), REPO / "pyproject.toml"]
    for module in modules:
        module_path = getattr(module, "__file__", None)
        if module_path is not None:
            paths.append(Path(module_path))
    # ``_freeze_lambda`` is imported into the probe from the C3 pilot; bind
    # that helper's defining source instead of relying on sys.modules order.
    paths.append(Path(probe._freeze_lambda.__globals__["__file__"]))
    # These four directories are placed on ``sys.path`` above and several
    # modules use delayed or re-exported imports.  Bind the complete local
    # Python closure conservatively so a newly reached dynamic dependency
    # cannot escape the manifest merely because it was not loaded yet.
    for runtime_root in (C2_V03, STAGE0, SMC, LEGACY):
        paths.extend(runtime_root.glob("*.py"))
    paths.extend(Path(path) for path in probe._default_code_paths())
    return sorted({path.resolve() for path in paths}, key=lambda path: str(path))


def _namespace_snapshot(path: Path) -> dict[str, str]:
    """Hash every regular file in one preserved artifact namespace."""

    root = path.expanduser().resolve()
    if path.is_symlink() or not root.is_dir():
        raise RuntimeError(f"preserved namespace is missing or not a directory: {path}")
    snapshot: dict[str, str] = {}
    for candidate in sorted(root.rglob("*"), key=lambda value: str(value)):
        if candidate.is_symlink():
            raise RuntimeError(f"preserved namespace contains a symlink: {candidate}")
        if candidate.is_file():
            snapshot[candidate.relative_to(root).as_posix()] = _file_sha256(candidate)
    if not snapshot:
        raise RuntimeError(f"preserved namespace contains no files: {path}")
    return snapshot


def _namespace_snapshot_sha256(snapshot: Mapping[str, str]) -> str:
    return hashlib.sha256(_canonical_json_bytes(dict(sorted(snapshot.items())))).hexdigest()


def _build_source_manifest(paths: Sequence[Path] | None = None) -> dict[str, Any]:
    repo = REPO.resolve()
    entries: list[dict[str, Any]] = []
    for raw_path in paths if paths is not None else _source_paths():
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"source manifest file is missing: {path}")
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError as error:
            raise RuntimeError(
                f"source manifest path escapes repository: {path}"
            ) from error
        entries.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    entries.sort(key=lambda row: row["path"])
    payload = {"schema": SOURCE_MANIFEST_SCHEMA, "files": entries}
    return {
        **payload,
        "manifest_sha256": hashlib.sha256(_canonical_json_bytes(payload)).hexdigest(),
    }


def _validate_source_manifest(
    manifest: Mapping[str, Any], *, expected_paths: Sequence[Path] | None = None
) -> str:
    """Re-hash every listed file and reject omissions, duplicates, or drift."""

    if manifest.get("schema") != SOURCE_MANIFEST_SCHEMA:
        raise RuntimeError("V0.3B source manifest schema is not supported")
    files = manifest.get("files")
    supplied_digest = manifest.get("manifest_sha256")
    if not isinstance(files, list) or not files:
        raise RuntimeError("V0.3B source manifest has no files")
    if not isinstance(supplied_digest, str):
        raise RuntimeError("V0.3B source manifest has no manifest SHA-256")
    payload = {"schema": manifest["schema"], "files": files}
    actual_digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    if actual_digest != supplied_digest:
        raise RuntimeError("V0.3B source manifest digest disagrees with contents")

    repo = REPO.resolve()
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, Mapping):
            raise RuntimeError("V0.3B source manifest entry is not an object")
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
            raise RuntimeError("V0.3B source manifest contains a malformed entry")
        seen.add(relative)
        path = (repo / relative).resolve()
        if not path.is_relative_to(repo) or not path.is_file():
            raise RuntimeError(
                f"V0.3B source manifest file is missing or escapes repository: {relative}"
            )
        if path.stat().st_size != expected_size or _file_sha256(path) != expected_sha:
            raise RuntimeError(f"V0.3B source manifest SHA-256 mismatch: {relative}")
    if expected_paths is not None:
        repo_expected = {
            Path(path).expanduser().resolve().relative_to(repo).as_posix()
            for path in expected_paths
        }
        if seen != repo_expected:
            raise RuntimeError(
                "V0.3B source manifest file set disagrees with expected source set"
            )
    return supplied_digest


def _write_once(path: Path, payload: Any) -> str:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite V0.3B gate output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json_bytes(payload)
    with path.open("xb") as handle:
        handle.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def _read_sealed_prereg(path: Path, seal_path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or seal_path.is_symlink():
        raise RuntimeError("V0.3B preregistration and seal must be regular files")
    actual = _file_sha256(path)
    seal_tokens = seal_path.read_text(encoding="utf-8").split()
    if not seal_tokens or actual != seal_tokens[0]:
        raise RuntimeError("V0.3B preregistration digest disagrees with its seal")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != PREREG_SCHEMA:
        raise RuntimeError("V0.3B preregistration schema is not supported")
    if payload.get("status") != "SEALED_BEFORE_V03B_HEADROOM_OUTCOMES":
        raise RuntimeError("V0.3B preregistration is not sealed before outcomes")
    return payload, actual


def _read_source_manifest(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V0.3B source manifest must be a regular file")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("V0.3B source manifest must be a JSON object")
    return payload


def _validate_prereg(payload: Mapping[str, Any]) -> None:
    """Validate frozen policy, seed, and adjudication identities before a run."""

    implementation = payload.get("implementation")
    evaluation = payload.get("evaluation")
    burned = payload.get("burned_seeds")
    decision = payload.get("decision")
    if not isinstance(implementation, Mapping):
        raise RuntimeError("V0.3B prereg lacks implementation block")
    if implementation.get("c2_policy_version") != core.CANDIDATE_VERSION:
        raise RuntimeError("V0.3B prereg policy version disagrees with runner")
    if implementation.get("forecast_authority_schema") != core.FORECAST_AUTHORITY_SCHEMA:
        raise RuntimeError("V0.3B prereg forecast schema disagrees with runner")
    if implementation.get("chronology_schema") != core.CHRONOLOGY_RECEIPT_SCHEMA:
        raise RuntimeError("V0.3B prereg chronology schema disagrees with runner")
    if implementation.get("forecast_schema") != backend.FORECAST_SCHEMA:
        raise RuntimeError("V0.3B prereg backend forecast schema disagrees with runner")
    if implementation.get("anchor_schema") != backend.ANCHOR_SCHEMA:
        raise RuntimeError("V0.3B prereg backend anchor schema disagrees with runner")
    if implementation.get("horizon_steps") != core.HORIZON_STEPS:
        raise RuntimeError("V0.3B prereg horizon disagrees with runner")
    if implementation.get("offsets") != list(EXPECTED_OFFSETS):
        raise RuntimeError("V0.3B prereg offsets disagree with runner")
    if implementation.get("release_reasons") != ["horizon", "support_expired"]:
        raise RuntimeError("V0.3B prereg release reasons disagree with runner")
    if implementation.get("fading_mode") != KEYED_FADING_VERSION:
        raise RuntimeError("V0.3B prereg does not require keyed fading")
    if implementation.get("policy_compositor_version") != backend.POLICY_COMPOSITOR_VERSION:
        raise RuntimeError("V0.3B prereg compositor version disagrees with runner")
    if implementation.get("opening_source_rules") != [
        "incumbent-hold",
        "max-lagged-candidate-sinr-rival",
    ]:
        raise RuntimeError("V0.3B prereg source rules disagree with runner")
    if not isinstance(evaluation, Mapping):
        raise RuntimeError("V0.3B prereg lacks evaluation block")
    seeds = evaluation.get("seeds")
    if (
        not isinstance(seeds, list)
        or len(seeds) != len(set(seeds))
        or not seeds
        or any(type(seed) is not int or seed < 0 for seed in seeds)
    ):
        raise RuntimeError("V0.3B prereg evaluation seeds are malformed")
    if not isinstance(burned, Mapping):
        raise RuntimeError("V0.3B prereg lacks burned-seed block")
    burned_ids = burned.get("ids")
    if (
        not isinstance(burned_ids, list)
        or len(burned_ids) != len(set(burned_ids))
        or any(type(seed) is not int or seed < 0 for seed in burned_ids)
    ):
        raise RuntimeError("V0.3B burned seed IDs are malformed")
    if set(seeds) & set(burned_ids):
        raise RuntimeError("V0.3B evaluation seed overlaps an explicitly burned seed")
    if evaluation.get("horizon_offsets") != list(EXPECTED_OFFSETS):
        raise RuntimeError("V0.3B prereg horizon offsets are malformed")
    if evaluation.get("temporal_target_offsets") != list(TEMPORAL_OFFSETS):
        raise RuntimeError("V0.3B prereg target offsets are malformed")
    if evaluation.get("early_stopping") is not False:
        raise RuntimeError("V0.3B gate must not use early stopping")
    if not isinstance(decision, Mapping):
        raise RuntimeError("V0.3B prereg lacks adjudication block")
    required = {
        "contract_or_numeric_errors",
        "unresolved_infrastructure_errors",
        "minimum_total_attempts",
        "minimum_anchors_per_seed",
        "minimum_attempts_per_seed",
        "minimum_complete_fraction",
        "maximum_opening_censor_fraction",
        "maximum_postopening_censor_count",
        "minimum_complete_per_seed",
        "minimum_service_safe_complete_per_seed",
        "minimum_release_offset_values",
        "minimum_support_expired_traces",
        "minimum_horizon_traces",
        "minimum_positive_seeds",
        "minimum_positive_anchor_digests",
        "minimum_anchor_digests_per_source_rule",
        "main_networks_replay_checkpoint_unchanged",
    }
    if not required.issubset(decision):
        raise RuntimeError("V0.3B prereg adjudication fields are incomplete")
    if decision.get("contract_or_numeric_errors") != 0:
        raise RuntimeError("V0.3B gate must require zero instrument errors")
    if decision.get("unresolved_infrastructure_errors") != 0:
        raise RuntimeError("V0.3B gate must require zero infrastructure errors")
    if decision.get("maximum_postopening_censor_count") != 0:
        raise RuntimeError("V0.3B gate must require zero post-opening censors")
    if decision.get("main_networks_replay_checkpoint_unchanged") is not True:
        raise RuntimeError("V0.3B gate must require Main nonmutation")

    supersedes = payload.get("supersedes")
    if not isinstance(supersedes, Mapping):
        raise RuntimeError("V0.3B prereg lacks preserved old-gate identity")
    if supersedes.get("status") != "SEALED_INDETERMINATE_IMMUTABLE_NOT_REUSED":
        raise RuntimeError("V0.3B prereg does not preserve the old gate")
    for field in ("path", "result_sha256", "prereg_sha256"):
        if not isinstance(supersedes.get(field), str) or not supersedes[field]:
            raise RuntimeError(f"V0.3B prereg old-gate {field} is malformed")


def _schedule_rng(prereg_sha256: str, *, seed: int, step: int) -> np.random.Generator:
    material = f"c2-v03b-reactive-gate-schedule-v1:{prereg_sha256}:{seed}:{step}".encode()
    value = int.from_bytes(hashlib.sha256(material).digest()[:16], "big")
    return np.random.Generator(np.random.PCG64(value))


def _validate_schedule(
    schedule: Mapping[str, Any],
    *,
    prereg_sha256: str,
    source_manifest_sha256: str,
    seed: int,
) -> None:
    if schedule.get("schema") != SCHEDULE_SCHEMA:
        raise RuntimeError("V0.3B schedule schema is not supported")
    if schedule.get("prereg_sha256") != prereg_sha256:
        raise RuntimeError("V0.3B schedule disagrees with sealed preregistration")
    if schedule.get("source_manifest_sha256") != source_manifest_sha256:
        raise RuntimeError("V0.3B schedule disagrees with source manifest")
    if schedule.get("seed") != int(seed):
        raise RuntimeError("V0.3B schedule seed disagrees with requested seed")
    if schedule.get("c2_policy_version") != core.CANDIDATE_VERSION:
        raise RuntimeError("V0.3B schedule policy version is stale")
    if schedule.get("horizon_offsets") != list(EXPECTED_OFFSETS):
        raise RuntimeError("V0.3B schedule horizon is malformed")
    anchors = schedule.get("anchors")
    if not isinstance(anchors, list):
        raise RuntimeError("V0.3B schedule anchors are not a list")
    seen_steps: set[int] = set()
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            raise RuntimeError("V0.3B schedule anchor is not an object")
        step = anchor.get("step_index")
        digest = anchor.get("anchor_schedule_sha256")
        if not isinstance(step, int) or step in seen_steps or not isinstance(digest, str):
            raise RuntimeError("V0.3B schedule anchor identity is malformed")
        seen_steps.add(step)
        body = dict(anchor)
        body.pop("anchor_schedule_sha256")
        if _schedule_digest(body) != digest:
            raise RuntimeError("V0.3B anchor schedule digest disagrees with contents")
    schedule_body = dict(schedule)
    supplied_digest = schedule_body.pop("schedule_sha256", None)
    if not isinstance(supplied_digest, str) or _schedule_digest(schedule_body) != supplied_digest:
        raise RuntimeError("V0.3B schedule digest disagrees with contents")


def _persist_or_resume_schedule(
    path: Path,
    schedule: Mapping[str, Any],
    *,
    prereg_sha256: str,
    source_manifest_sha256: str,
    seed: int,
) -> str:
    _validate_schedule(
        schedule,
        prereg_sha256=prereg_sha256,
        source_manifest_sha256=source_manifest_sha256,
        seed=seed,
    )
    encoded = _canonical_json_bytes(schedule)
    expected_file_sha256 = hashlib.sha256(encoded).hexdigest()
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V0.3B existing schedule is not a regular file: {path}")
        actual = path.read_bytes()
        if hashlib.sha256(actual).hexdigest() != expected_file_sha256:
            raise RuntimeError(f"V0.3B existing schedule bytes disagree: {path}")
        try:
            existing = json.loads(actual.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"V0.3B existing schedule is invalid JSON: {path}") from error
        if not isinstance(existing, Mapping) or dict(existing) != dict(schedule):
            raise RuntimeError(f"V0.3B existing schedule content disagrees: {path}")
        _validate_schedule(
            existing,
            prereg_sha256=prereg_sha256,
            source_manifest_sha256=source_manifest_sha256,
            seed=seed,
        )
        return expected_file_sha256
    return _write_once(path, schedule)


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
    """Discover all anchor/focal IDs before any C2 forecast is scored."""

    wrapped = probe.loader._make_environment(archive, users=probe.smoke.USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = probe.loader._evaluation_rngs(seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    anchors: list[dict[str, Any]] = []
    steps_per_episode = int(wrapped.environment.driver.config.steps_per_episode)
    while int(observation.step_index) <= probe.smoke.MAX_ANCHOR_STEP:
        main_actions, main_physical = probe.smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        step = int(observation.step_index)
        departures = probe._departure_users(wrapped, main_physical)
        if departures and steps_per_episode - step >= len(EXPECTED_OFFSETS):
            take = min(max_candidates, len(departures))
            if take <= 0:
                raise RuntimeError("V0.3B schedule selected no focal users")
            rng = _schedule_rng(prereg_sha256, seed=seed, step=step)
            sampled = rng.choice(np.asarray(departures, dtype=np.int64), size=take, replace=False)
            focal_users = sorted(int(value) for value in sampled.tolist())
            anchor = {
                "seed": int(seed),
                "step_index": step,
                "eligible_departure_users": [int(value) for value in departures],
                "eligible_departure_user_count": len(departures),
                "scheduled_focal_users": focal_users,
                "opening_main_actions": [int(value) for value in main_actions.tolist()],
                "opening_main_physical_actions": [
                    None if value is None else [int(value[0]), int(value[1])]
                    for value in main_physical
                ],
                "c2_policy_version": core.CANDIDATE_VERSION,
                "horizon_offsets": list(EXPECTED_OFFSETS),
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
    schedule: dict[str, Any] = {
        "schema": SCHEDULE_SCHEMA,
        "prereg_sha256": prereg_sha256,
        "source_manifest_sha256": source_manifest_sha256,
        "seed": int(seed),
        "c2_policy_version": core.CANDIDATE_VERSION,
        "horizon_offsets": list(EXPECTED_OFFSETS),
        "selection": "uniform-without-replacement-domain-separated-preoutcome",
        "anchors": anchors,
    }
    schedule["schedule_sha256"] = _schedule_digest(schedule)
    return schedule


def _policy_release_receipt(
    build: Any,
    prepared: Any,
    *,
    focal_user: int,
) -> dict[str, Any]:
    """Recheck V0.3B row metadata and branch-local release semantics."""

    certificate = build.certificate
    if certificate.version != core.CANDIDATE_VERSION:
        raise RuntimeError("forecast certificate carries a stale C2 policy version")
    if build.authority.schema != core.FORECAST_AUTHORITY_SCHEMA:
        raise RuntimeError("forecast authority schema is not V0.3B")
    if build.authority.fading_mode != KEYED_FADING_VERSION:
        raise RuntimeError("physical-headroom gate requires keyed fading")
    if not build.authority.generated_preoutcome:
        raise RuntimeError("forecast authority is not marked pre-outcome")
    source_rule = getattr(prepared, "source_rule", None)
    if source_rule not in SOURCE_RULES:
        raise RuntimeError(f"unknown C2 source rule: {source_rule!r}")
    trace = tuple(prepared.candidate_trace)
    if tuple(step.offset for step in trace) != EXPECTED_OFFSETS:
        raise RuntimeError("V0.3B candidate trace offsets are not complete 0..H")
    candidate_key = tuple(certificate.candidate_key)
    policy_rows = {
        (
            step.release_offset,
            step.release_reason,
            tuple(step.held_physical_key) if step.held_physical_key is not None else None,
        )
        for step in trace
    }
    if len(policy_rows) != 1:
        raise RuntimeError("V0.3B candidate rows disagree on release metadata")
    release_offset, release_reason, held_key = next(iter(policy_rows))
    try:
        release_offset, release_reason, horizon = core._release_policy(  # type: ignore[attr-defined]
            release_offset=release_offset,
            release_reason=release_reason,
            horizon_steps=core.HORIZON_STEPS,
            field_prefix="gate.candidate",
        )
    except core.C2ContractError as error:
        raise RuntimeError("V0.3B candidate release metadata is malformed") from error
    if held_key != candidate_key:
        raise RuntimeError("V0.3B held physical key disagrees with candidate key")
    if certificate.release_offset != release_offset or certificate.release_reason != release_reason:
        raise RuntimeError("certificate and candidate row release metadata disagree")
    if build.evidence.release_offset != release_offset or build.evidence.release_reason != release_reason:
        raise RuntimeError("evidence and candidate row release metadata disagree")

    support_counts: list[int] = []
    for offset, step in enumerate(trace):
        if step.held_physical_key != candidate_key:
            raise RuntimeError(f"held key changed at offset {offset}")
        if step.held_key_match_count is None or type(step.held_key_match_count) is not int:
            raise RuntimeError(f"support count missing at offset {offset}")
        bindings = tuple(step.action_bindings_by_user[focal_user])
        recomputed = sum(1 for row in bindings if tuple(row.physical_key) == candidate_key)
        if recomputed != step.held_key_match_count:
            raise RuntimeError(f"support count disagrees with contemporaneous table at offset {offset}")
        support_counts.append(int(recomputed))
        if offset < release_offset:
            if recomputed != 1 or tuple(step.executed_physical_actions[focal_user]) != candidate_key:
                raise RuntimeError(f"V0.3B hold is not uniquely supported at offset {offset}")
        else:
            if (
                tuple(step.executed_actions) != tuple(step.detached_main_actions)
                or tuple(step.executed_physical_actions) != tuple(step.detached_main_physical_actions)
            ):
                raise RuntimeError(f"release suffix is not branch-local Main at offset {offset}")
            if offset == release_offset and release_reason == "support_expired" and recomputed == 1:
                raise RuntimeError("support-expired release still has unique support")
            if offset == release_offset and release_reason == "horizon" and recomputed != 1:
                raise RuntimeError("horizon release did not retain unique support")
    if release_reason == "support_expired":
        first_loss = next((offset for offset, count in enumerate(support_counts) if offset > 0 and count != 1), None)
        if first_loss != release_offset:
            raise RuntimeError("release was not latched on the first support loss")
    elif release_offset != core.HORIZON_STEPS:
        raise RuntimeError("horizon release occurred before the frozen horizon")
    return {
        "c2_policy_version": certificate.version,
        "source_rule": source_rule,
        "held_physical_key": list(candidate_key),
        "support_match_counts": support_counts,
        "release_offset": release_offset,
        "release_reason": release_reason,
        "horizon_steps": horizon,
        "candidate_trace_sha256": build.candidate_trace_sha256,
        "reference_trace_sha256": build.reference_trace_sha256,
        "forecast_payload_sha256": build.forecast_payload_sha256,
        "fading_field_receipt": getattr(prepared, "forecast_rng_state", {}).get(
            "fading_field_receipt"
        ),
    }


def _trace_receipts(
    reference_trace: Sequence[Any],
    candidate_trace: Sequence[Any],
    *,
    interval_s: float,
    multiplier: float,
    focal_user: int,
) -> tuple[list[dict[str, Any]], float, dict[str, Any]]:
    if len(reference_trace) != len(EXPECTED_OFFSETS) or len(candidate_trace) != len(EXPECTED_OFFSETS):
        raise RuntimeError("V0.3B scored trace must contain exactly offsets 0..H")
    receipts: list[dict[str, Any]] = []
    for expected, reference, candidate in zip(EXPECTED_OFFSETS, reference_trace, candidate_trace, strict=True):
        if int(reference.offset) != expected or int(candidate.offset) != expected:
            raise RuntimeError("V0.3B trace offsets are not ordered 0..H")
        reference_rates = [float(value) for value in reference.link_rate_bps]
        candidate_rates = [float(value) for value in candidate.link_rate_bps]
        reference_served = [bool(value) for value in reference.served]
        candidate_served = [bool(value) for value in candidate.served]
        if len(reference_rates) != len(candidate_rates) or len(reference_rates) != len(reference_served) or len(candidate_rates) != len(candidate_served):
            raise RuntimeError("V0.3B matched trace vectors disagree in length")
        if not np.all(np.isfinite(reference_rates)) or not np.all(np.isfinite(candidate_rates)):
            raise RuntimeError("V0.3B trace rates are nonfinite")
        delta_rates = [candidate - reference for reference, candidate in zip(reference_rates, candidate_rates, strict=True)]
        delta_rate_sum = math.fsum(delta_rates)
        reference_power = float(reference.system_power_w)
        candidate_power = float(candidate.system_power_w)
        if not math.isfinite(reference_power) or not math.isfinite(candidate_power) or reference_power <= 0.0 or candidate_power <= 0.0:
            raise RuntimeError("V0.3B trace power is not positive finite")
        delta_power = candidate_power - reference_power
        g_k = interval_s * delta_rate_sum - multiplier * interval_s * delta_power
        new_outage_users = [
            uid
            for uid, (served_m, served_c) in enumerate(zip(reference_served, candidate_served, strict=True))
            if served_m and not served_c
        ]
        receipts.append(
            {
                "offset": expected,
                "reference_per_user_rate_bps": reference_rates,
                "candidate_per_user_rate_bps": candidate_rates,
                "delta_per_user_rate_bps": delta_rates,
                "reference_system_rate_bps": math.fsum(reference_rates),
                "candidate_system_rate_bps": math.fsum(candidate_rates),
                "delta_system_rate_bps": delta_rate_sum,
                "reference_system_power_w": reference_power,
                "candidate_system_power_w": candidate_power,
                "delta_system_power_w": delta_power,
                "g_k_fixed_lambda_bits": g_k,
                "reference_served": reference_served,
                "candidate_served": candidate_served,
                "reference_served_count": sum(reference_served),
                "candidate_served_count": sum(candidate_served),
                "new_outage_users": new_outage_users,
            }
        )
    downstream = receipts[1:]
    if not 0 <= focal_user < len(receipts[0]["reference_served"]):
        raise RuntimeError("V0.3B focal user is outside served vectors")
    service_guard = {
        "offsets": [int(row["offset"]) for row in downstream],
        "no_new_outage_for_any_reference_served_user": all(not row["new_outage_users"] for row in downstream),
        "served_count_not_lower": all(row["candidate_served_count"] >= row["reference_served_count"] for row in downstream),
        "focal_reference_service_preserved": all(
            not row["reference_served"][focal_user] or row["candidate_served"][focal_user]
            for row in downstream
        ),
    }
    service_guard["passed"] = all(service_guard.values())
    return receipts, float(math.fsum(row["g_k_fixed_lambda_bits"] for row in downstream)), service_guard


def _execute_seed_schedule(
    trainer: Any,
    archive: Any,
    schedule: Mapping[str, Any],
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
    env_rng, mobility_rng, _action_rng, _control_rng = probe.loader._evaluation_rngs(seed)
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
            if [int(value) for value in main_actions.tolist()] != scheduled["opening_main_actions"]:
                raise RuntimeError("V0.3B replay Main actions disagree with sealed schedule")
            departures = probe._departure_users(wrapped, main_physical)
            if any(uid not in departures for uid in scheduled["scheduled_focal_users"]):
                raise RuntimeError("V0.3B replay eligibility disagrees with sealed schedule")
            completed_steps.add(step)
            for focal_user in scheduled["scheduled_focal_users"]:
                started = time.perf_counter()
                base = {
                    "seed": seed,
                    "step_index": step,
                    "anchor_schedule_sha256": scheduled["anchor_schedule_sha256"],
                    "focal_user": int(focal_user),
                    "eligible_departure_user_count": int(scheduled["eligible_departure_user_count"]),
                    "scheduled_focal_user_count": len(scheduled["scheduled_focal_users"]),
                }
                try:
                    service = backend.C2TemporalForkTrainerBackend(
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
                        forecast_fading_mode=KEYED_FADING_VERSION,
                    )
                    prepared = service.prepare_hold_or_max_lagged_gain_rival(focal_user=int(focal_user))
                    build = prepared.run_forecast()
                    policy = _policy_release_receipt(build, prepared, focal_user=int(focal_user))
                    offset_receipts, z2, service_guard = _trace_receipts(
                        prepared.reference_trace,
                        prepared.candidate_trace,
                        interval_s=interval_s,
                        multiplier=multiplier,
                        focal_user=int(focal_user),
                    )
                    certificate = build.certificate
                    rows.append(
                        {
                            **base,
                            "outcome": "COMPLETE_TRACE_SCORED",
                            "candidate_key": list(prepared.candidate_key),
                            "source_rule": policy["source_rule"],
                            "c2_policy_version": policy["c2_policy_version"],
                            "release_offset": policy["release_offset"],
                            "release_reason": policy["release_reason"],
                            "held_physical_key": policy["held_physical_key"],
                            "support_match_counts": policy["support_match_counts"],
                            "fading_field_receipt": policy["fading_field_receipt"],
                            "reference_trace_sha256": policy["reference_trace_sha256"],
                            "candidate_trace_sha256": policy["candidate_trace_sha256"],
                            "forecast_payload_sha256": policy["forecast_payload_sha256"],
                            "old_certificate_diagnostic": {
                                "passed": bool(certificate.passed),
                                "failures": [failure.value for failure in certificate.failures],
                                "ee_surplus_bits": float(certificate.ee_surplus_bits),
                                "ee_surplus_floor_bits": float(certificate.ee_surplus_floor_bits),
                            },
                            "offset_receipts": offset_receipts,
                            "z2_temporal_surplus_bits": z2,
                            "service_guard": service_guard,
                            "positive_service_safe": bool(service_guard["passed"] and z2 > 0.0),
                            "elapsed_s": time.perf_counter() - started,
                        }
                    )
                except backend.C2ForecastSupportRejection as error:
                    if int(error.forecast_offset) == 0 and error.reason == "opening_candidate_unavailable":
                        outcome = "RIGHT_CENSORED_OPENING_SUPPORT"
                    else:
                        # V0.3B must release on downstream support loss.  A
                        # downstream rejection means the running source is not
                        # the sealed policy and is an instrument failure.
                        outcome = "INSTRUMENT_ERROR_NOT_SCORED"
                    rows.append(
                        {
                            **base,
                            "outcome": outcome,
                            "error_class": type(error).__name__,
                            "censor_reason": error.reason,
                            "forecast_offset": int(error.forecast_offset),
                            "branch_side": "candidate",
                            "physical_key": None if error.physical_key is None else list(error.physical_key),
                            "detail": str(error),
                            "elapsed_s": time.perf_counter() - started,
                        }
                    )
                except Exception as error:
                    rows.append(
                        {
                            **base,
                            "outcome": "INSTRUMENT_ERROR_NOT_SCORED",
                            "error_class": type(error).__name__,
                            "detail": str(error),
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
        raise RuntimeError("V0.3B replay did not reach every sealed anchor")
    return {
        "seed": seed,
        "schedule_sha256": schedule["schedule_sha256"],
        "anchors_scheduled": len(schedule["anchors"]),
        "attempts_scheduled": sum(len(anchor["scheduled_focal_users"]) for anchor in schedule["anchors"]),
        "eligible_departure_user_total": sum(int(anchor["eligible_departure_user_count"]) for anchor in schedule["anchors"]),
        "scheduled_focal_user_total": sum(len(anchor["scheduled_focal_users"]) for anchor in schedule["anchors"]),
        "rows": rows,
    }


def _adjudicate(
    prereg: Mapping[str, Any],
    seed_results: Sequence[Mapping[str, Any]],
    *,
    nonmutation_ok: bool = True,
) -> dict[str, Any]:
    rows = [row for result in seed_results for row in result["rows"]]
    complete = [row for row in rows if row.get("outcome") == "COMPLETE_TRACE_SCORED"]
    opening_censored = [row for row in rows if row.get("outcome") == "RIGHT_CENSORED_OPENING_SUPPORT"]
    postopening_censored = [
        row
        for row in rows
        if row.get("outcome") == "RIGHT_CENSORED_POSTOPENING_SUPPORT"
    ]
    errors = [row for row in rows if row.get("outcome") == "INSTRUMENT_ERROR_NOT_SCORED"]
    attempts = len(rows)
    complete_fraction = len(complete) / attempts if attempts else 0.0
    opening_censor_fraction = len(opening_censored) / attempts if attempts else 0.0
    decision = prereg["decision"]
    per_seed: list[dict[str, Any]] = []
    for result in seed_results:
        seed_rows = list(result["rows"])
        seed_complete = [row for row in seed_rows if row.get("outcome") == "COMPLETE_TRACE_SCORED"]
        seed_safe = [row for row in seed_complete if bool(row.get("service_guard", {}).get("passed"))]
        seed_positive = [row for row in seed_complete if bool(row.get("positive_service_safe"))]
        per_seed.append(
            {
                "seed": int(result["seed"]),
                "anchors": int(result["anchors_scheduled"]),
                "attempts": len(seed_rows),
                "complete": len(seed_complete),
                "service_safe_complete": len(seed_safe),
                "positive_service_safe": len(seed_positive),
                "opening_censored": sum(row.get("outcome") == "RIGHT_CENSORED_OPENING_SUPPORT" for row in seed_rows),
                "postopening_censored": sum(row.get("outcome") == "RIGHT_CENSORED_POSTOPENING_SUPPORT" for row in seed_rows),
                "errors": sum(row.get("outcome") == "INSTRUMENT_ERROR_NOT_SCORED" for row in seed_rows),
                "eligible_departure_user_total": int(result.get("eligible_departure_user_total", 0)),
                "scheduled_focal_user_total": int(result.get("scheduled_focal_user_total", 0)),
            }
        )
    offsets = [int(row["release_offset"]) for row in complete]
    reasons = [str(row["release_reason"]) for row in complete]
    release_offset_counts = {str(offset): offsets.count(offset) for offset in EXPECTED_OFFSETS[1:]}
    release_reason_counts = {reason: reasons.count(reason) for reason in ("support_expired", "horizon")}
    source_rule_counts = {rule: sum(row.get("source_rule") == rule for row in complete) for rule in sorted(SOURCE_RULES)}
    source_rule_anchor_digests = {
        rule: sorted({str(row["anchor_schedule_sha256"]) for row in complete if row.get("source_rule") == rule})
        for rule in sorted(SOURCE_RULES)
    }
    positive = [row for row in complete if bool(row.get("positive_service_safe"))]
    positive_seeds = sorted({int(row["seed"]) for row in positive})
    positive_anchor_digests = sorted({str(row["anchor_schedule_sha256"]) for row in positive})
    coverage_ok = bool(
        attempts >= int(decision["minimum_total_attempts"])
        and all(
            row["anchors"] >= int(decision["minimum_anchors_per_seed"])
            and row["attempts"] >= int(decision["minimum_attempts_per_seed"])
            and row["eligible_departure_user_total"] > 0
            and row["scheduled_focal_user_total"] > 0
            for row in per_seed
        )
    )
    completion_ok = bool(
        complete_fraction >= float(decision["minimum_complete_fraction"])
        and opening_censor_fraction <= float(decision["maximum_opening_censor_fraction"])
        and len(postopening_censored)
        <= int(decision["maximum_postopening_censor_count"])
        and all(
            row["complete"] >= int(decision["minimum_complete_per_seed"])
            and row["service_safe_complete"] >= int(decision["minimum_service_safe_complete_per_seed"])
            for row in per_seed
        )
    )
    release_offset_diversity_ok = bool(
        len(set(offsets)) >= int(decision["minimum_release_offset_values"])
        and release_reason_counts["support_expired"] >= int(decision["minimum_support_expired_traces"])
        and release_reason_counts["horizon"] >= int(decision["minimum_horizon_traces"])
    )
    fallback_coverage_ok = bool(
        all(source_rule_counts[rule] > 0 for rule in SOURCE_RULES)
        and all(
            len(source_rule_anchor_digests[rule])
            >= int(decision["minimum_anchor_digests_per_source_rule"])
            for rule in SOURCE_RULES
        )
    )
    anchor_replication_ok = bool(
        len(positive_seeds) >= int(decision["minimum_positive_seeds"])
        and len(positive_anchor_digests) >= int(decision["minimum_positive_anchor_digests"])
    )
    departure_mass_ok = bool(
        all(
            int(result.get("eligible_departure_user_total", 0)) > 0
            and int(result.get("scheduled_focal_user_total", 0)) > 0
            for result in seed_results
        )
    )
    instrument_ok = bool(
        len(errors) == int(decision["contract_or_numeric_errors"])
        and int(decision["unresolved_infrastructure_errors"]) == 0
        and nonmutation_ok
    )
    support_ok = bool(
        coverage_ok
        and completion_ok
        and release_offset_diversity_ok
        and fallback_coverage_ok
        and departure_mass_ok
    )
    if not instrument_ok:
        outcome = "INSTRUMENT_FAIL"
    elif not support_ok:
        outcome = "INDETERMINATE"
    elif anchor_replication_ok:
        outcome = "GO_BOUNDED_LEARNABILITY_PILOT_ONLY"
    else:
        outcome = "SCIENTIFIC_NO_GO"
    return {
        "outcome": outcome,
        "attempts": attempts,
        "complete": len(complete),
        "complete_fraction": complete_fraction,
        "opening_censored": len(opening_censored),
        "opening_censor_fraction": opening_censor_fraction,
        "postopening_censored": len(postopening_censored),
        "instrument_errors": len(errors),
        "coverage_ok": coverage_ok,
        "completion_ok": completion_ok,
        "release_offset_diversity_ok": release_offset_diversity_ok,
        "fallback_coverage_ok": fallback_coverage_ok,
        "anchor_replication_ok": anchor_replication_ok,
        "departure_mass_ok": departure_mass_ok,
        "release_offset_counts": release_offset_counts,
        "release_reason_counts": release_reason_counts,
        "source_rule_counts": source_rule_counts,
        "source_rule_anchor_digests": source_rule_anchor_digests,
        "positive_service_safe": len(positive),
        "positive_seeds": positive_seeds,
        "positive_anchor_digests": positive_anchor_digests,
        "per_seed": per_seed,
        "instrument_ok": instrument_ok,
        "support_ok": support_ok,
        "nonmutation_ok": bool(nonmutation_ok),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--input-dir", type=Path, default=probe.DEFAULT_INPUT)
    parser.add_argument("--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser())
    parser.add_argument("--users", type=int, default=probe.smoke.USERS)
    args = parser.parse_args(argv)
    if args.users <= 0:
        raise ValueError("V0.3B user count must be positive")

    prereg, prereg_sha256 = _read_sealed_prereg(args.prereg, args.seal)
    _validate_prereg(prereg)
    source_manifest = _read_source_manifest(args.source_manifest)
    expected_sources = _source_paths()
    source_manifest_sha256 = _validate_source_manifest(
        source_manifest, expected_paths=expected_sources
    )
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(f"refusing to overwrite V0.3B result: {args.output}")

    old_namespace = REPO / str(prereg["supersedes"]["path"])
    old_namespace_before = _namespace_snapshot(old_namespace)
    if old_namespace_before.get("prereg.json") != prereg["supersedes"]["prereg_sha256"]:
        raise RuntimeError("preserved old preregistration hash disagrees with V0.3B prereg")
    if old_namespace_before.get("result.json") != prereg["supersedes"]["result_sha256"]:
        raise RuntimeError("preserved old result hash disagrees with V0.3B prereg")

    baseline_path = REPO / str(prereg["baseline"]["prereg_path"])
    baseline_record = read_prereg(baseline_path)
    if baseline_record.digest != prereg["baseline"]["prereg_sha256"]:
        raise RuntimeError("baseline preregistration digest disagrees with V0.3B prereg")
    temp = tempfile.TemporaryDirectory(prefix="mcrl-c2-v03b-headroom-")
    try:
        archive = probe._frozen_archive(
            baseline_record,
            args.tle_root,
            Path(temp.name) / "frozen-tle",
        )
        trainer, checkpoint = probe.loader._verify_and_load_trainer(
            baseline_record,
            archive,
            run_dir=args.input_dir / "main",
            users=args.users,
        )
        if checkpoint["checkpoint_sha256"] != prereg["baseline"]["checkpoint_sha256"]:
            raise RuntimeError("loaded checkpoint disagrees with V0.3B prereg")
        checkpoint_path = args.input_dir / "main" / "final-checkpoint.pt"
        checkpoint_before = _file_sha256(checkpoint_path)
        networks_before = probe.smoke._network_snapshot(trainer)
        replay_before = len(trainer.replay)
        environment_source_sha256 = source_manifest_sha256
        reward_path = REPO / "src/mcrl/env/step.py"
        reward_source_sha256 = _file_sha256(reward_path)
        calibration_env = probe.loader._make_environment(archive, users=args.users)
        calibration = probe._freeze_lambda(
            trainer,
            calibration_env,
            seed=int(prereg["multiplier"]["calibration_seed"]),
        )
        multiplier = float(calibration["lambda_bits_per_j"])
        if multiplier.hex() != prereg["multiplier"]["lambda_hex"]:
            raise RuntimeError("recomputed lambda disagrees with V0.3B prereg")
        interval_s = float(calibration["interval_s"])

        schedules: list[dict[str, Any]] = []
        for seed in prereg["evaluation"]["seeds"]:
            schedule = _discover_seed_schedule(
                trainer,
                archive,
                seed=int(seed),
                prereg_sha256=prereg_sha256,
                source_manifest_sha256=source_manifest_sha256,
                max_anchors=int(prereg["evaluation"]["maximum_anchors_per_seed"]),
                max_candidates=int(prereg["evaluation"]["maximum_candidates_per_anchor"]),
            )
            schedule_path = args.output.parent / f"schedule-{int(seed)}.json"
            schedule["file_sha256"] = _persist_or_resume_schedule(
                schedule_path,
                schedule,
                prereg_sha256=prereg_sha256,
                source_manifest_sha256=source_manifest_sha256,
                seed=int(seed),
            )
            schedules.append(schedule)

        started = time.perf_counter()
        seed_results = [
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
            for schedule in schedules
        ]
        networks_unchanged = probe.smoke._networks_equal(trainer, networks_before)
        replay_unchanged = len(trainer.replay) == replay_before
        checkpoint_unchanged = _file_sha256(checkpoint_path) == checkpoint_before
        old_namespace_after = _namespace_snapshot(old_namespace)
        old_namespace_unchanged = old_namespace_after == old_namespace_before
        nonmutation_ok = bool(
            networks_unchanged
            and replay_unchanged
            and checkpoint_unchanged
            and old_namespace_unchanged
        )
        adjudication = _adjudicate(prereg, seed_results, nonmutation_ok=nonmutation_ok)
        result = {
            "schema": RESULT_SCHEMA,
            "gate_name": GATE_NAME,
            "prereg_sha256": prereg_sha256,
            "source_manifest_sha256": source_manifest_sha256,
            "claim_ceiling": prereg["claim_ceiling"],
            "baseline_prereg_sha256": baseline_record.digest,
            "ephemeris_file_set_sha256": baseline_record.sections["ephemeris"]["file_set_sha256"],
            "checkpoint_sha256": checkpoint["checkpoint_sha256"],
            "environment_source_sha256": environment_source_sha256,
            "reward_source_sha256": reward_source_sha256,
            "c2_policy_version": core.CANDIDATE_VERSION,
            "policy_compositor_version": backend.POLICY_COMPOSITOR_VERSION,
            "fading_mode": KEYED_FADING_VERSION,
            "lambda_calibration": {**calibration, "lambda_hex": multiplier.hex()},
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
            "old_gate_namespace_unchanged": old_namespace_unchanged,
            "old_gate_namespace_snapshot_sha256": _namespace_snapshot_sha256(
                old_namespace_after
            ),
            "training_or_replay_write": False,
            "elapsed_s": time.perf_counter() - started,
        }
        _write_once(args.output, result)
        print(json.dumps(adjudication, indent=2, sort_keys=True))
        return 0 if adjudication["outcome"] != "INSTRUMENT_FAIL" else 1
    finally:
        temp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
