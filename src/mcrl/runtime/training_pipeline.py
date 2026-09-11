"""Server-side P6 sweep and main-training orchestration.

The launcher is intentionally boring: it verifies the corrected frozen
record, constructs the real train-split environment, runs the three matched
learning-rate arms, applies the frozen selection rule, and only then starts
an independent main run.  No learning-rate default exists on this path.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.metadata
import json
import platform
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np
import torch

from ..artifacts import read_checkpoint
from ..algorithms.modqn import MODQNTrainer
from ..env.action_contract import no_op_actions
from ..env.constants import TLE_ROOT_DEFAULT
from ..env.ephemeris import (
    TEST,
    TRAIN,
    BlockAlternatingSplit,
    EpisodeStartSampler,
    EphemerisConfig,
    file_set_hash,
)
from ..env.mobility import MobilityConfig
from ..env.scenario import ScenarioConfig, ScenarioDriver
from ..env.step import StepEnvironment
from ..env.tle import TleArchive
from ..errors import (
    MCRLContractError,
    NonFiniteTrainingError,
    P6NonFiniteEvaluationError,
)
from .objective_math import apply_reward_calibration, scalarize_objectives
from .prereg import PreregRecord, read_prereg
from .probe_p6 import (
    MAIN_ENV_SEED,
    MAIN_MOBILITY_SEED,
    MAIN_TRAIN_SEED,
    P6_ENV_SEED,
    P6_EVALUATION_SEEDS,
    P6_LEARNING_RATES,
    P6_MOBILITY_SEED,
    P6_NEAR_TIE_FRACTION,
    P6_PERTURBATION_REPLICATES,
    P6_PERTURBATION_STD_FRACTION,
    P6_SELECTION_RULE,
    P6_TRAIN_SEED,
    choose_learning_rate,
    near_tie_actions,
    perturbation_stability,
)
from .trainer_env import TrainerEnvironment
from .trainer_spec import CollapseSample, EpisodeLog, TrainerConfig

REPO = Path(__file__).resolve().parents[3]
CANONICAL_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
CANONICAL_PREREG_RECORD_DIGEST = (
    "3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4"
)
CANONICAL_PREREG_BYTE_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)
CORRECTED_PROBE_SUMMARY = (
    REPO / "artifacts" / "probes-2026-08-25-rerun01" / "summary.json"
)
DEFAULT_OUTPUT_DIR = REPO / "artifacts" / "training-2026-08-25-rerun01"
RESUME_EVERY_EPISODES = 100


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Mapping[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _json_sha256(payload: Mapping[str, Any] | list[Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json_mapping(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MCRLContractError(f"cannot read {label}: {path}") from error
    if not isinstance(payload, dict):
        raise MCRLContractError(f"{label} must be a JSON object")
    return payload


def _recorded_evidence_path(entry: Mapping[str, Any], *, label: str) -> Path:
    raw = entry.get("path")
    if not isinstance(raw, str) or not raw:
        raise MCRLContractError(f"R2 has no {label} evidence path")
    relative = Path(raw)
    if relative.is_absolute():
        raise MCRLContractError(f"R2 {label} evidence path must be repo-relative")
    resolved = (REPO / relative).resolve()
    if not resolved.is_relative_to(REPO.resolve()):
        raise MCRLContractError(f"R2 {label} evidence path escapes the repo")
    return resolved


def _assert_recorded_file(
    entry: Mapping[str, Any], *, label: str
) -> Path:
    path = _recorded_evidence_path(entry, label=label)
    if not path.is_file():
        raise MCRLContractError(f"R2 {label} evidence is missing: {path}")
    expected = entry.get("byte_sha256")
    actual = _file_sha256(path)
    if not isinstance(expected, str) or actual != expected:
        raise MCRLContractError(
            f"R2 {label} evidence SHA-256 mismatch: expected {expected!r}, "
            f"got {actual}"
        )
    return path


def _json_self_digest(
    payload: Mapping[str, Any], *, digest_field: str
) -> str:
    hashable = dict(payload)
    hashable.pop(digest_field, None)
    encoded = json.dumps(
        hashable,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def assert_corrective_probe_refreeze(
    record: PreregRecord,
    summary_path: Path = CORRECTED_PROBE_SUMMARY,
) -> dict[str, Any]:
    """Prove that R2 applies the presealed P3 mapping before P6.

    The corrected runner was intentionally bound to the superseded 2026-08-25
    seal.  A result that reported ``p6_unlocked = false`` may unlock P6 only
    through a new immutable record whose Q-F value exactly equals the raw
    served-step p95 and whose evidence files still match their recorded bytes.
    """
    record.verify()
    provenance = record.sections.get("refreeze_provenance")
    if not isinstance(provenance, Mapping):
        raise MCRLContractError("the canonical record has no R2 provenance")
    if provenance.get("kind") != "deterministic-selection-mapping-application":
        raise MCRLContractError("the canonical record is not the corrective R2 seal")

    evidence = provenance.get("corrected_probe_evidence")
    if not isinstance(evidence, Mapping):
        raise MCRLContractError("R2 has no corrected-probe evidence bundle")
    required = {
        name: evidence.get(name)
        for name in (
            "summary",
            "execution_manifest",
            "p3_selection_mapping",
            "protocol",
        )
    }
    if any(not isinstance(entry, Mapping) for entry in required.values()):
        raise MCRLContractError("R2 corrected-probe evidence bundle is incomplete")

    summary_entry = required["summary"]
    assert isinstance(summary_entry, Mapping)
    recorded_summary_path = _recorded_evidence_path(
        summary_entry, label="corrected-probe summary"
    )
    if Path(summary_path).resolve() != recorded_summary_path:
        raise MCRLContractError(
            "the supplied corrected-probe summary is not the R2-recorded artifact"
        )
    summary_file = _assert_recorded_file(
        summary_entry, label="corrected-probe summary"
    )
    manifest_entry = required["execution_manifest"]
    p3_entry = required["p3_selection_mapping"]
    protocol_entry = required["protocol"]
    assert isinstance(manifest_entry, Mapping)
    assert isinstance(p3_entry, Mapping)
    assert isinstance(protocol_entry, Mapping)
    manifest_file = _assert_recorded_file(
        manifest_entry, label="corrected-probe execution manifest"
    )
    p3_file = _assert_recorded_file(
        p3_entry, label="corrected P3 selection-mapping result"
    )
    protocol_file = _assert_recorded_file(
        protocol_entry, label="corrected-probe protocol"
    )

    superseded_ref = {
        "path": provenance.get("supersedes"),
        "byte_sha256": provenance.get("superseded_byte_sha256"),
    }
    superseded_file = _assert_recorded_file(
        superseded_ref, label="superseded prereg"
    )
    superseded = read_prereg(superseded_file)
    if superseded.digest != provenance.get("superseded_digest"):
        raise MCRLContractError("R2 superseded prereg digest mismatch")

    summary = _read_json_mapping(summary_file, label="corrected-probe summary")
    manifest = _read_json_mapping(
        manifest_file, label="corrected-probe execution manifest"
    )
    p3 = _read_json_mapping(p3_file, label="corrected P3 result")
    protocol = _read_json_mapping(protocol_file, label="corrected-probe protocol")

    manifest_digest = manifest_entry.get("self_digest")
    if (
        not isinstance(manifest_digest, str)
        or manifest.get("manifest_digest") != manifest_digest
        or _json_self_digest(manifest, digest_field="manifest_digest")
        != manifest_digest
    ):
        raise MCRLContractError("corrected-probe manifest self-digest mismatch")
    protocol_digest = protocol_entry.get("self_digest")
    if (
        not isinstance(protocol_digest, str)
        or protocol.get("digest") != protocol_digest
        or _json_self_digest(protocol, digest_field="digest") != protocol_digest
    ):
        raise MCRLContractError("corrected-probe protocol self-digest mismatch")

    old_digest = superseded.digest
    if (
        summary.get("status") != "complete"
        or summary.get("prereg_digest") != old_digest
        or summary.get("manifest_digest") != manifest_digest
        or manifest.get("prereg_digest") != old_digest
        or manifest.get("manifest_digest") != manifest_digest
        or protocol.get("augments_prereg_digest") != old_digest
    ):
        raise MCRLContractError(
            "corrected-probe summary/manifest/protocol provenance is inconsistent"
        )
    manifest_protocol = manifest.get("corrective_protocol")
    if (
        not isinstance(manifest_protocol, Mapping)
        or manifest_protocol.get("digest") != protocol_digest
    ):
        raise MCRLContractError("execution manifest uses a different probe protocol")
    fingerprint = manifest.get("run_fingerprint")
    if not isinstance(fingerprint, Mapping):
        raise MCRLContractError("execution manifest has no run fingerprint")
    fingerprint_hashable = dict(fingerprint)
    fingerprint_digest = fingerprint_hashable.pop("fingerprint_sha256", None)
    sources = fingerprint.get("source_files_sha256")
    if (
        not isinstance(fingerprint_digest, str)
        or _json_sha256(fingerprint_hashable) != fingerprint_digest
        or fingerprint.get("prereg_digest") != old_digest
        or fingerprint.get("corrective_protocol_digest") != protocol_digest
        or not isinstance(sources, Mapping)
        or sources.get("artifacts/PREREG-FROZEN-2026-08-25.json")
        != provenance.get("superseded_byte_sha256")
        or sources.get("artifacts/CORRECTED-PROBE-PROTOCOL-2026-08-25.json")
        != protocol_entry.get("byte_sha256")
    ):
        raise MCRLContractError("corrected-probe run fingerprint is inconsistent")

    calibration = summary.get("calibration_gate")
    if not isinstance(calibration, Mapping):
        raise MCRLContractError("corrected-probe summary has no calibration gate")
    c1_gate = calibration.get("c1")
    c3_gate = calibration.get("c3")
    if not isinstance(c1_gate, Mapping) or not isinstance(c3_gate, Mapping):
        raise MCRLContractError("corrected-probe calibration gate is incomplete")
    if (
        summary.get("p6_unlocked") is not False
        or calibration.get("p6_unlocked") is not False
        or calibration.get("required_next_action") != "corrective_refreeze"
        or c1_gate.get("matches_frozen") is not False
        or c3_gate.get("matches_frozen") is not True
    ):
        raise MCRLContractError(
            "corrected-probe result is not the pre-R2 mapping-mismatch state"
        )

    policy = record.sections.get("reference_policy", {}).get("name")
    r1 = p3.get("r1_over_served_steps")
    if not isinstance(r1, Mapping):
        raise MCRLContractError("corrected P3 has no served-step r1 distribution")
    p3_policy = p3.get("policy")
    if not isinstance(p3_policy, Mapping):
        raise MCRLContractError("corrected P3 has no policy identity")
    observed_c1 = r1.get("p95")
    observed_c3 = p3.get("qd_scale_p95_rounded")
    if (
        p3.get("prereg_digest") != old_digest
        or p3_policy.get("name") != policy
        or p3_entry.get("policy") != policy
        or p3.get("decision_steps") != p3_entry.get("decision_steps")
        or r1.get("count") != p3_entry.get("served_steps")
        or observed_c1 != c1_gate.get("corrected_observed")
        or observed_c3 != c3_gate.get("corrected_observed")
    ):
        raise MCRLContractError("corrected P3 does not match the R2 evidence record")
    result_files = manifest.get("result_files")
    if (
        not isinstance(result_files, Mapping)
        or not isinstance(result_files.get("P3"), Mapping)
        or result_files["P3"].get(policy) != p3_file.name
    ):
        raise MCRLContractError("execution manifest does not own the R2 P3 result")

    mappings = record.sections.get("selection_mappings")
    applied = provenance.get("applied_mapping")
    if not isinstance(mappings, Mapping) or not isinstance(applied, Mapping):
        raise MCRLContractError("R2 has no applied selection mapping")
    qf = mappings.get("Q-F c1 calibration scale")
    qd = mappings.get("Q-D r3 calibration scale")
    if not isinstance(qf, Mapping) or not isinstance(qd, Mapping):
        raise MCRLContractError("R2 reward-scale mappings are incomplete")
    if (
        qf.get("resolved") != observed_c1
        or applied.get("observed_raw") != observed_c1
        or applied.get("resolved") != observed_c1
        or applied.get("representation") != "full raw continuous p95"
        or qd.get("resolved") != observed_c3
    ):
        raise MCRLContractError(
            "R2 does not exactly apply the corrected P3 c1/c3 mappings"
        )
    if record.digest != CANONICAL_PREREG_RECORD_DIGEST:
        raise MCRLContractError(
            "canonical R2 digest mismatch; a re-hashed edit cannot unlock P6"
        )

    return {
        "status": "corrective-refreeze-accepted",
        "superseded_prereg_digest": old_digest,
        "current_prereg_digest": record.digest,
        "manifest_digest": manifest_digest,
        "c1": observed_c1,
        "c3": observed_c3,
    }


def _default_code_paths() -> list[Path]:
    return sorted((REPO / "src" / "mcrl").rglob("*.py")) + [
        REPO / "scripts" / "run_server_training.py",
        REPO / "pyproject.toml",
    ]


def _code_sha256(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted((Path(item) for item in paths), key=lambda item: str(item)):
        try:
            label = path.resolve().relative_to(REPO.resolve()).as_posix()
        except ValueError:
            label = path.name
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _installed_dependency_versions() -> dict[str, str]:
    distributions = {
        "numpy": "numpy",
        "sgp4": "sgp4",
        "torch": "torch",
        "PyYAML": "PyYAML",
    }
    versions = {"python": platform.python_version()}
    for label, distribution in distributions.items():
        try:
            versions[label] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[label] = "MISSING"
    return versions


def build_run_fingerprint(
    record: PreregRecord,
    *,
    role: str,
    learning_rate: float,
    train_seed: int,
    env_seed: int,
    mobility_seed: int,
    code_paths: list[Path] | None = None,
    dependency_versions: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Hash every live input that can change a reusable run's meaning."""
    config = _trainer_config(record, learning_rate=learning_rate)
    payload: dict[str, Any] = {
        "schema": "mcrl-run-fingerprint-v1",
        "prereg_digest": record.digest,
        "code_sha256": _code_sha256(
            _default_code_paths() if code_paths is None else code_paths
        ),
        "ephemeris_file_set_sha256": record.sections["ephemeris"][
            "file_set_sha256"
        ],
        "dependencies": dict(
            _installed_dependency_versions()
            if dependency_versions is None
            else dependency_versions
        ),
        "run": {
            "role": role,
            "learning_rate": float(learning_rate),
            "train_seed": int(train_seed),
            "environment_seed": int(env_seed),
            "mobility_seed": int(mobility_seed),
        },
        "frozen_seed_sets": {
            "p6_matched": {
                "train": P6_TRAIN_SEED,
                "environment": P6_ENV_SEED,
                "mobility": P6_MOBILITY_SEED,
            },
            "p6_evaluation": list(P6_EVALUATION_SEEDS),
            "main": {
                "train": MAIN_TRAIN_SEED,
                "environment": MAIN_ENV_SEED,
                "mobility": MAIN_MOBILITY_SEED,
            },
        },
        "trainer_config_sha256": _json_sha256(asdict(config)),
        "reward_calibration_scales": list(config.reward_calibration_scales),
    }
    return payload | {"fingerprint_sha256": _json_sha256(payload)}


def _all_finite_json(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return bool(np.isfinite(value))
    if isinstance(value, (list, tuple)):
        return all(_all_finite_json(item) for item in value)
    if isinstance(value, dict):
        return all(_all_finite_json(item) for item in value.values())
    return False


OBJECTIVE_WEIGHTS_FOR_LOG_RECONSTRUCTION = TrainerConfig().objective_weights
"""B0 D-3: the weights used to rebuild a pre-D-3 row's calibrated scalar.

Read off the config default rather than written out, so the reconstruction
cannot drift from the deployed selector's weights.
"""


def _episode_log_from_dict(row: Mapping[str, Any]) -> EpisodeLog:
    def collapse(name: str) -> CollapseSample | None:
        value = row.get(name)
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise TypeError(f"resume episode log {name} must be a mapping")
        return CollapseSample(**{key: float(item) for key, item in value.items()})

    losses = row.get("losses", ())
    if not isinstance(losses, (list, tuple)) or len(losses) != 3:
        raise ValueError("resume episode log losses must contain three values")
    # B0 D-3: a row logged before 2026-09-11 carries the ambiguous
    # ``scalar_reward`` key, and what it holds is the UNCALIBRATED number.  It
    # is read into the deprecated field, never into the headline one, so
    # resuming an old run cannot smuggle 0.5*r1 in as the objective.
    if "scalar_reward_uncalibrated_deprecated" in row:
        uncalibrated = float(row["scalar_reward_uncalibrated_deprecated"])
    else:
        uncalibrated = float(row["scalar_reward"])
    if "scalar_reward_calibrated" in row:
        calibrated_scalar = float(row["scalar_reward_calibrated"])
    else:
        # A pre-D-3 row never carried it.  Reconstruct it from the calibrated
        # head means the row does carry, rather than leaving a silent zero.
        calibrated_scalar = float(
            sum(
                weight * float(row.get(name, 0.0))
                for weight, name in zip(
                    OBJECTIVE_WEIGHTS_FOR_LOG_RECONSTRUCTION,
                    (
                        "r1_mean_calibrated",
                        "r2_mean_calibrated",
                        "r3_mean_calibrated",
                    ),
                )
            )
        )
    return EpisodeLog(
        episode=int(row["episode"]),
        epsilon=float(row["epsilon"]),
        r1_mean=float(row["r1_mean"]),
        r2_mean=float(row["r2_mean"]),
        r3_mean=float(row["r3_mean"]),
        scalar_reward_calibrated=calibrated_scalar,
        scalar_reward_uncalibrated_deprecated=uncalibrated,
        total_handovers=int(row["total_handovers"]),
        replay_size=int(row["replay_size"]),
        losses=tuple(float(value) for value in losses),
        collapse_first=collapse("collapse_first"),
        collapse_last=collapse("collapse_last"),
        r1_mean_calibrated=float(row.get("r1_mean_calibrated", 0.0)),
        r2_mean_calibrated=float(row.get("r2_mean_calibrated", 0.0)),
        r3_mean_calibrated=float(row.get("r3_mean_calibrated", 0.0)),
    )


def _write_resume_checkpoint(
    path: Path,
    *,
    trainer: MODQNTrainer,
    logs: list[EpisodeLog],
    run_fingerprint: Mapping[str, Any],
) -> str:
    payload = {
        "schema": "mcrl-resume-v1",
        "next_episode": len(logs),
        "run_fingerprint": dict(run_fingerprint),
        "episode_logs": [asdict(log) for log in logs],
        "trainer_state": trainer.training_state_dict(),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    temporary.replace(path)
    return _file_sha256(path)


def _load_resume_checkpoint(
    path: Path,
    *,
    trainer: MODQNTrainer,
    expected_fingerprint: Mapping[str, Any],
    expected_episodes: int,
) -> tuple[int, list[EpisodeLog]]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, Mapping) or payload.get("schema") != "mcrl-resume-v1":
        raise MCRLContractError("resume checkpoint has an unknown schema")
    if payload.get("run_fingerprint") != dict(expected_fingerprint):
        raise MCRLContractError("resume checkpoint run fingerprint does not match")
    raw_logs = payload.get("episode_logs")
    if not isinstance(raw_logs, list) or not _all_finite_json(raw_logs):
        raise MCRLContractError("resume checkpoint episode logs are invalid")
    logs = [_episode_log_from_dict(row) for row in raw_logs]
    next_episode = int(payload.get("next_episode", -1))
    if (
        next_episode != len(logs)
        or not 0 <= next_episode <= expected_episodes
        or any(log.episode != index for index, log in enumerate(logs))
    ):
        raise MCRLContractError(
            "resume checkpoint episode boundary is not contiguous"
        )
    state = payload.get("trainer_state")
    if not isinstance(state, Mapping):
        raise MCRLContractError("resume checkpoint has no trainer state")
    trainer.load_training_state_dict(state)
    return next_episode, logs


def _valid_episode_logs(path: Path, *, expected_count: int) -> bool:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return (
        isinstance(rows, list)
        and len(rows) == expected_count
        and all(
            isinstance(row, dict)
            and row.get("episode") == index
            and _all_finite_json(row)
            for index, row in enumerate(rows)
        )
    )


def arm_status_is_reusable(
    candidate: Mapping[str, Any],
    arm_dir: Path,
    *,
    expected_fingerprint: Mapping[str, Any],
    expected_episodes: int,
    evaluate_p6: bool,
) -> bool:
    """Validate provenance and every required artifact before reuse."""
    try:
        status = str(candidate.get("status"))
        if candidate.get("run_fingerprint") != dict(expected_fingerprint):
            return False
        if status not in {"complete", "nonfinite", "incomplete"}:
            return False
        logs_path = Path(arm_dir) / "episode-logs.json"
        if not logs_path.is_file():
            return False
        if candidate.get("episode_logs_sha256") != _file_sha256(logs_path):
            return False
        episodes_completed = int(candidate.get("episodes_completed", -1))
        if not 0 <= episodes_completed <= expected_episodes:
            return False
        if not _valid_episode_logs(logs_path, expected_count=episodes_completed):
            return False

        if status == "nonfinite":
            return bool(candidate.get("failure_kind") and candidate.get("error"))

        checkpoint_path = Path(arm_dir) / "final-checkpoint.pt"
        if episodes_completed != expected_episodes or not checkpoint_path.is_file():
            return False
        if candidate.get("checkpoint_sha256") != _file_sha256(checkpoint_path):
            return False
        checkpoint = read_checkpoint(checkpoint_path, map_location="cpu")
        run = expected_fingerprint["run"]
        if (
            checkpoint.episode != expected_episodes - 1
            or checkpoint.train_seed != run["train_seed"]
            or checkpoint.env_seed != run["environment_seed"]
            or checkpoint.mobility_seed != run["mobility_seed"]
            or float(checkpoint.trainer_config["learning_rate"])
            != float(run["learning_rate"])
            or _json_sha256(checkpoint.trainer_config)
            != expected_fingerprint["trainer_config_sha256"]
        ):
            return False

        if status == "incomplete":
            return (
                candidate.get("failure_kind") == "nonfinite-evaluation"
                and bool(candidate.get("error"))
            )
        if not evaluate_p6:
            return True
        seeds = candidate.get("evaluation_seeds")
        scores = candidate.get("calibrated_scalar_reward_by_seed")
        if seeds != list(P6_EVALUATION_SEEDS) or not isinstance(scores, list):
            return False
        if len(scores) != len(P6_EVALUATION_SEEDS) or not _all_finite_json(scores):
            return False
        for key in ("greedy", "random_near_tie", "paired_control_deltas"):
            rows = candidate.get(key)
            if not isinstance(rows, list) or len(rows) != len(P6_EVALUATION_SEEDS):
                return False
            if not _all_finite_json(rows):
                return False
        return True
    except Exception:
        return False


def assert_p6_protocol_matches_record(record: PreregRecord) -> dict[str, Any]:
    """Fail if the launcher and the corrected freeze describe different P6s."""
    record.verify()
    p6 = record.sections.get("probe_grid", {}).get("P6")
    if not isinstance(p6, dict):
        raise MCRLContractError("the frozen record has no P6 protocol")
    protocol = p6.get("operational_protocol")
    if not isinstance(protocol, dict):
        raise MCRLContractError("P6 is named but not operationally frozen")

    expected = {
        "learning_rates": list(P6_LEARNING_RATES),
        "episodes": 9000,
        "users": 100,
        "evaluation_seeds": list(P6_EVALUATION_SEEDS),
        "matched_training_seeds": {
            "train": P6_TRAIN_SEED,
            "environment": P6_ENV_SEED,
            "mobility": P6_MOBILITY_SEED,
        },
        "main_training_seeds": {
            "train": MAIN_TRAIN_SEED,
            "environment": MAIN_ENV_SEED,
            "mobility": MAIN_MOBILITY_SEED,
        },
        "near_tie_fraction": P6_NEAR_TIE_FRACTION,
        "perturbation_std_fraction": P6_PERTURBATION_STD_FRACTION,
        "perturbation_replicates": P6_PERTURBATION_REPLICATES,
        "selection_rule": P6_SELECTION_RULE,
        "device": "cpu",
    }
    actual = {
        "learning_rates": p6.get("sweep", {}).get("learning_rate"),
        "episodes": p6.get("episodes"),
        "users": p6.get("users"),
        "evaluation_seeds": protocol.get("evaluation_seeds"),
        "matched_training_seeds": protocol.get("matched_training_seeds"),
        "main_training_seeds": protocol.get("main_training_seeds"),
        "near_tie_fraction": protocol.get("near_tie_control", {}).get(
            "threshold"
        ),
        "perturbation_std_fraction": protocol.get(
            "perturbation_stability", {}
        ).get("std_fraction_of_valid_q_range"),
        "perturbation_replicates": protocol.get(
            "perturbation_stability", {}
        ).get("replicates_per_user_decision"),
        "selection_rule": protocol.get("learning_rate_selection"),
        "device": protocol.get("device"),
    }
    if actual != expected:
        raise MCRLContractError(
            "server launcher disagrees with the frozen P6 protocol: "
            f"expected {expected!r}, got {actual!r}"
        )
    return p6


def _frozen_reward_scales(record: PreregRecord) -> tuple[float, float, float]:
    """Read c1/c2/c3 from the corrected record, never from live defaults."""
    mappings = record.sections.get("selection_mappings")
    if not isinstance(mappings, dict):
        raise MCRLContractError("the frozen record has no selection mappings")
    keys = (
        "Q-F c1 calibration scale",
        "Q-G c2 calibration scale",
        "Q-D r3 calibration scale",
    )
    try:
        values = tuple(float(mappings[key]["resolved"]) for key in keys)
    except (KeyError, TypeError, ValueError) as error:
        raise MCRLContractError(
            "the frozen reward calibration mapping is incomplete"
        ) from error
    if len(values) != 3 or not np.all(np.isfinite(values)) or min(values) <= 0:
        raise MCRLContractError(
            f"the frozen reward calibration scales are invalid: {values!r}"
        )
    return values  # type: ignore[return-value]


def make_training_environment(*, users: int = 100) -> TrainerEnvironment:
    """Construct a fresh real-ephemeris environment on the frozen train split."""
    archive = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=users)),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def assert_ephemeris_matches_record(
    record: PreregRecord,
    *,
    archive: TleArchive | None = None,
    sgp4_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild the portable live ephemeris contract and compare the freeze."""
    frozen = record.sections.get("ephemeris")
    if not isinstance(frozen, dict):
        raise MCRLContractError("the frozen record has no ephemeris contract")
    live_archive = archive or TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
    dates = list(live_archive.dates)
    rows = live_archive.manifest_rows(dates)
    first, last = live_archive.date_range
    present = set(dates)
    missing_dates = [
        (first + dt.timedelta(days=offset)).isoformat()
        for offset in range((last - first).days + 1)
        if (first + dt.timedelta(days=offset)) not in present
    ]
    split = BlockAlternatingSplit.for_archive(live_archive)
    live_config = EphemerisConfig(tle_root=str(live_archive.root)).as_dict()
    live_config.pop("tle_root", None)

    if sgp4_contract is None:
        import sgp4
        from sgp4.api import accelerated

        sgp4_contract = {
            "version": sgp4.__version__,
            "accelerated": bool(accelerated),
            "gravity_model": live_config["gravity_model"],
        }

    live: dict[str, Any] = {
        "frozen_files": rows,
        "file_set_sha256": file_set_hash(rows),
        "archive": {
            "date_first": first.isoformat(),
            "date_last": last.isoformat(),
            "file_count": len(dates),
            "calendar_span_days": (last - first).days + 1,
            "missing_dates": missing_dates,
        },
        "config_without_portable_root": live_config,
        "sgp4": dict(sgp4_contract),
        "split": dict(split.as_dict())
        | {
            "train_files": len(split.available_dates(live_archive, TRAIN)),
            "test_files": len(split.available_dates(live_archive, TEST)),
            "embargoed_files": len(split.embargoed_dates(live_archive)),
            "minimum_train_test_gap_days": split.minimum_gap_days(live_archive),
        },
        "sampling": EpisodeStartSampler.for_archive(
            live_archive, split, TRAIN
        ).as_dict(),
    }
    frozen_config = dict(frozen.get("config", {}))
    frozen_config.pop("tle_root", None)
    expected = {
        "frozen_files": frozen.get("frozen_files"),
        "file_set_sha256": frozen.get("file_set_sha256"),
        "archive": frozen.get("archive"),
        "config_without_portable_root": frozen_config,
        "sgp4": frozen.get("sgp4"),
        "split": frozen.get("split"),
        "sampling": frozen.get("sampling"),
    }
    if live != expected:
        differing = sorted(key for key in expected if live[key] != expected[key])
        raise MCRLContractError(
            "live ephemeris disagrees with the corrected frozen record in: "
            + ", ".join(differing)
        )
    return live


def validate_server_setup(
    prereg_path: Path = CANONICAL_PREREG,
    *,
    probe_summary_path: Path = CORRECTED_PROBE_SUMMARY,
) -> PreregRecord:
    """Run refreeze/protocol/live guards and instantiate the real environment."""
    record = read_prereg(prereg_path)
    if _file_sha256(Path(prereg_path)) != CANONICAL_PREREG_BYTE_SHA256:
        raise MCRLContractError(
            "canonical R2 byte SHA-256 mismatch; use the sealed artifact bytes"
        )
    assert_corrective_probe_refreeze(record, probe_summary_path)
    p6 = assert_p6_protocol_matches_record(record)
    assert_ephemeris_matches_record(record)
    environment = make_training_environment(users=int(p6["users"]))
    environment.assert_ready_to_train()
    return record


def _trainer_config(record: PreregRecord, *, learning_rate: float) -> TrainerConfig:
    training = record.sections["training"]
    network = record.sections["action_and_state"]
    return TrainerConfig(
        hidden_layers=tuple(int(value) for value in network["hidden_layers"]),
        activation=str(network["activation"]),
        learning_rate=float(learning_rate),
        discount_factor=float(training["discount_factor"]),
        batch_size=int(training["batch_size"]),
        episodes=int(training["episodes"]),
        objective_weights=tuple(float(value) for value in training["objective_weights"]),
        epsilon_start=float(training["epsilon_start"]),
        epsilon_end=float(training["epsilon_end"]),
        epsilon_decay_episodes=int(training["epsilon_decay_episodes"]),
        target_update_every_episodes=int(
            training["target_update_every_episodes"]
        ),
        replay_capacity=int(training["replay_capacity"]),
        reward_calibration_enabled=True,
        reward_calibration_scales=_frozen_reward_scales(record),
        device="cpu",
    )


def _evaluation_rngs(
    seed: int,
) -> tuple[np.random.Generator, np.random.Generator, np.random.Generator, np.random.Generator]:
    children = np.random.SeedSequence(int(seed)).spawn(4)
    return tuple(np.random.default_rng(child) for child in children)  # type: ignore[return-value]


def _evaluate_one_rollout(
    trainer: MODQNTrainer,
    environment: TrainerEnvironment,
    *,
    evaluation_seed: int,
    policy: str,
) -> dict[str, Any]:
    env_rng, mobility_rng, action_rng, perturb_rng = _evaluation_rngs(
        evaluation_seed
    )
    states, masks, _observation = environment.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    raw_reward = np.zeros(3, dtype=np.float64)
    calibrated_reward = np.zeros(3, dtype=np.float64)
    decisions = 0
    near_tie_decisions = 0
    interventions = 0
    perturbation_rows: list[dict[str, float]] = []

    while True:
        scalarized = trainer.scalarized_q_values(encoded)
        actions = no_op_actions(environment.num_users)
        for uid, wrapped_mask in enumerate(masks):
            mask = wrapped_mask.mask
            valid = np.flatnonzero(mask)
            if valid.size == 0:
                continue
            decisions += 1
            greedy = int(valid[np.argmax(scalarized[uid, valid])])
            tied = near_tie_actions(scalarized[uid], mask)
            if tied.size > 1:
                near_tie_decisions += 1
            if policy == "greedy":
                selected = greedy
                stability = perturbation_stability(
                    scalarized[uid],
                    mask,
                    perturb_rng,
                    std_fraction=P6_PERTURBATION_STD_FRACTION,
                    replicates=P6_PERTURBATION_REPLICATES,
                )
                if stability is not None:
                    perturbation_rows.append(stability)
            elif policy == "random-near-tie":
                selected = int(action_rng.choice(tied))
                interventions += int(selected != greedy)
            else:
                raise ValueError(f"unknown P6 evaluation policy {policy!r}")
            actions[uid] = selected

        result = environment.step(actions, env_rng)
        for uid in range(environment.num_users):
            vector = np.asarray(
                trainer.reward_vector_from_step_result(result, uid, is_eval=True),
                dtype=np.float64,
            )
            if vector.shape != (3,):
                raise MCRLContractError(
                    f"P6 evaluation reward vector has shape {vector.shape}, need (3,)"
                )
            if not np.all(np.isfinite(vector)):
                raise P6NonFiniteEvaluationError(
                    "P6 evaluation produced a non-finite raw reward vector"
                )
            calibrated_vector = apply_reward_calibration(vector, trainer.config)
            if not np.all(np.isfinite(calibrated_vector)):
                raise P6NonFiniteEvaluationError(
                    "P6 evaluation produced a non-finite calibrated reward vector"
                )
            raw_reward += vector
            calibrated_reward += calibrated_vector
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        encoded = trainer.encode_states(states)

    raw_mean = raw_reward / environment.num_users
    calibrated_mean = calibrated_reward / environment.num_users
    if not np.all(np.isfinite(raw_mean)) or not np.all(
        np.isfinite(calibrated_mean)
    ):
        raise P6NonFiniteEvaluationError(
            "P6 evaluation produced a non-finite accumulated reward"
        )
    scalar_raw = float(
        scalarize_objectives(raw_mean, trainer.config.objective_weights)
    )
    scalar_calibrated = float(
        scalarize_objectives(
            calibrated_mean, trainer.config.objective_weights
        )
    )
    if not np.isfinite(scalar_raw) or not np.isfinite(scalar_calibrated):
        raise P6NonFiniteEvaluationError(
            "P6 evaluation produced a non-finite scalar reward"
        )
    perturbation = None
    if perturbation_rows:
        perturbation = {
            "greedy_action_retention": float(
                np.mean(
                    [row["greedy_action_retention"] for row in perturbation_rows]
                )
            ),
            "kendall_tau": float(
                np.mean([row["kendall_tau"] for row in perturbation_rows])
            ),
            "rows": len(perturbation_rows),
        }
    return {
        "evaluation_seed": int(evaluation_seed),
        "policy": policy,
        "objective_reward_mean_raw": [float(value) for value in raw_mean],
        "objective_reward_mean_calibrated": [
            float(value) for value in calibrated_mean
        ],
        "scalar_reward_raw": scalar_raw,
        "scalar_reward_calibrated": scalar_calibrated,
        "system_ee_reward_r1": float(raw_mean[0]),
        "decisions": int(decisions),
        "near_tie_decisions": int(near_tie_decisions),
        "near_tie_fraction": float(near_tie_decisions / max(decisions, 1)),
        "interventions": int(interventions),
        "intervention_fraction": float(interventions / max(decisions, 1)),
        "perturbation_stability": perturbation,
    }


def evaluate_p6_arm(
    trainer: MODQNTrainer,
    environment_factory: Callable[[], TrainerEnvironment],
) -> dict[str, Any]:
    """Evaluate one final policy on all matched seeds and both control arms."""
    greedy_rows: list[dict[str, Any]] = []
    random_rows: list[dict[str, Any]] = []
    for seed in P6_EVALUATION_SEEDS:
        greedy_rows.append(
            _evaluate_one_rollout(
                trainer,
                environment_factory(),
                evaluation_seed=seed,
                policy="greedy",
            )
        )
        random_rows.append(
            _evaluate_one_rollout(
                trainer,
                environment_factory(),
                evaluation_seed=seed,
                policy="random-near-tie",
            )
        )

    perturbation_rows = [
        row["perturbation_stability"]
        for row in greedy_rows
        if row["perturbation_stability"] is not None
    ]
    action_retention = (
        float(
            np.mean(
                [row["greedy_action_retention"] for row in perturbation_rows]
            )
        )
        if perturbation_rows
        else None
    )
    kendall_tau = (
        float(np.mean([row["kendall_tau"] for row in perturbation_rows]))
        if perturbation_rows
        else None
    )
    paired = []
    for greedy, randomised in zip(greedy_rows, random_rows, strict=True):
        paired.append(
            {
                "evaluation_seed": greedy["evaluation_seed"],
                "delta_system_ee_random_minus_greedy": float(
                    randomised["system_ee_reward_r1"]
                    - greedy["system_ee_reward_r1"]
                ),
                "delta_calibrated_scalar_random_minus_greedy": float(
                    randomised["scalar_reward_calibrated"]
                    - greedy["scalar_reward_calibrated"]
                ),
            }
        )
    return {
        "evaluation_seeds": list(P6_EVALUATION_SEEDS),
        "greedy": greedy_rows,
        "random_near_tie": random_rows,
        "paired_control_deltas": paired,
        "calibrated_scalar_reward_by_seed": [
            float(row["scalar_reward_calibrated"]) for row in greedy_rows
        ],
        "perturbation_diagnostic_available": bool(perturbation_rows),
        "perturbation_diagnostic_unavailable_reason": (
            None
            if perturbation_rows
            else "no evaluation decision had at least two valid actions"
        ),
        "perturbation_greedy_action_retention": action_retention,
        "perturbation_kendall_tau": kendall_tau,
    }


def _collapse_summary(logs: list[EpisodeLog]) -> dict[str, Any] | None:
    if not logs:
        return None
    tail = logs[-min(1000, len(logs)) :]
    result: dict[str, Any] = {
        "episodes": len(logs),
        "tail_window": len(tail),
        "aggregation": "median",
    }
    for point in ("first", "last"):
        result[point] = {
            metric: float(
                np.median([log.collapse_report(point)[metric] for log in tail])
            )
            for metric in (
                "active_beam_count",
                "argmax_agreement",
                "q_margin",
                "q_entropy",
            )
        }
    result["drift_last_minus_first"] = {
        metric: float(np.median([log.collapse_drift()[metric] for log in tail]))
        for metric in (
            "active_beam_count",
            "argmax_agreement",
            "q_margin",
            "q_entropy",
        )
    }
    return result


def _run_training(
    *,
    record: PreregRecord,
    learning_rate: float,
    output_dir: Path,
    role: str,
    train_seed: int,
    env_seed: int,
    mobility_seed: int,
    evaluate_p6: bool,
) -> dict[str, Any]:
    """Run one explicit-LR training job; no default can reach this function."""
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "status.json"
    logs_path = output_dir / "episode-logs.json"
    checkpoint_path = output_dir / "final-checkpoint.pt"
    resume_path = output_dir / "resume-checkpoint.pt"
    run_fingerprint = build_run_fingerprint(
        record,
        role=role,
        learning_rate=learning_rate,
        train_seed=train_seed,
        env_seed=env_seed,
        mobility_seed=mobility_seed,
    )
    previous_status: dict[str, Any] | None = None
    if status_path.is_file():
        try:
            candidate = json.loads(status_path.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                previous_status = candidate
        except (OSError, json.JSONDecodeError):
            previous_status = None
    previous_matches = bool(
        previous_status is not None
        and previous_status.get("run_fingerprint") == run_fingerprint
    )
    previous_resume_episode = (
        int(previous_status.get("resume_next_episode", 0))
        if previous_matches and previous_status is not None
        else 0
    )
    status: dict[str, Any] = {
        "status": "running",
        "role": role,
        "learning_rate": float(learning_rate),
        "prereg_digest": record.digest,
        "run_fingerprint": run_fingerprint,
        "started_utc": _utc_now(),
        "seeds": {
            "train": train_seed,
            "environment": env_seed,
            "mobility": mobility_seed,
        },
    }
    _write_json(status_path, status)
    observed_logs: list[EpisodeLog] = []
    failure_stage = "environment-setup"

    def observe(log: EpisodeLog) -> None:
        observed_logs.append(log)
        if (log.episode + 1) % RESUME_EVERY_EPISODES == 0:
            resume_sha256 = _write_resume_checkpoint(
                resume_path,
                trainer=trainer,
                logs=observed_logs,
                run_fingerprint=run_fingerprint,
            )
            _write_json(logs_path, [asdict(item) for item in observed_logs])
            status["episodes_completed"] = log.episode + 1
            status["resume_next_episode"] = log.episode + 1
            status["resume_checkpoint"] = str(resume_path)
            status["resume_checkpoint_sha256"] = resume_sha256
            status["episode_logs"] = str(logs_path)
            status["episode_logs_sha256"] = _file_sha256(logs_path)
            status["last_scalar_reward_raw"] = log.scalar_reward
            # B0 D-3: the live status file used to carry ONLY the uncalibrated
            # scalar, which is numerically 0.5*r1.  The headline and all three
            # calibrated heads go beside it, so a run being watched in flight
            # cannot show a curve with two of its three terms invisible.
            status["last_scalar_reward_calibrated"] = log.scalar_reward_calibrated
            status["last_r1_mean_calibrated"] = log.r1_mean_calibrated
            status["last_r2_mean_calibrated"] = log.r2_mean_calibrated
            status["last_r3_mean_calibrated"] = log.r3_mean_calibrated
            status["updated_utc"] = _utc_now()
            _write_json(status_path, status)

    try:
        environment = make_training_environment(users=100)
        environment.assert_ready_to_train()
        failure_stage = "trainer-construction"
        config = _trainer_config(record, learning_rate=learning_rate)
        trainer = MODQNTrainer(
            environment,
            config,
            train_seed=train_seed,
            env_seed=env_seed,
            mobility_seed=mobility_seed,
            device="cpu",
        )
        failure_stage = "resume-load"
        start_episode = 0
        initial_logs: list[EpisodeLog] = []
        if resume_path.is_file():
            try:
                start_episode, initial_logs = _load_resume_checkpoint(
                    resume_path,
                    trainer=trainer,
                    expected_fingerprint=run_fingerprint,
                    expected_episodes=config.episodes,
                )
            except Exception:
                if previous_matches and previous_resume_episode > 0:
                    raise
                start_episode, initial_logs = 0, []
        if previous_resume_episode > start_episode:
            raise MCRLContractError(
                "status reports progress beyond the durable resume checkpoint"
            )
        observed_logs.extend(initial_logs)
        status |= {
            "episodes_completed": start_episode,
            "resume_next_episode": start_episode,
            "resumed": bool(start_episode),
        }
        if start_episode:
            status |= {
                "resume_checkpoint": str(resume_path),
                "resume_checkpoint_sha256": _file_sha256(resume_path),
            }
        _write_json(status_path, status)
        failure_stage = "training"
        logs = trainer.train(
            progress_every=100,
            start_episode=start_episode,
            initial_logs=initial_logs,
            episode_callback=observe,
        )
    except NonFiniteTrainingError as error:
        _write_json(logs_path, [asdict(log) for log in observed_logs])
        payload = status | {
            "status": "nonfinite",
            "failure_kind": "nonfinite-training",
            "failure_stage": failure_stage,
            "expected_for_learning_rate_0_01": bool(
                np.isclose(learning_rate, 0.01)
            ),
            "error": str(error),
            "episodes_completed": len(observed_logs),
            "finished_utc": _utc_now(),
            "collapse_summary": _collapse_summary(observed_logs),
            "episode_logs": str(logs_path),
            "episode_logs_sha256": _file_sha256(logs_path),
        }
        _write_json(status_path, payload)
        return payload
    except Exception as error:
        if observed_logs:
            _write_json(logs_path, [asdict(log) for log in observed_logs])
        payload = status | {
            "status": "failed",
            "failure_stage": failure_stage,
            "error_type": type(error).__name__,
            "error": str(error),
            "episodes_completed": int(status.get("resume_next_episode", 0)),
            "episodes_observed_before_failure": len(observed_logs),
            "finished_utc": _utc_now(),
        }
        if logs_path.is_file():
            payload |= {
                "episode_logs": str(logs_path),
                "episode_logs_sha256": _file_sha256(logs_path),
            }
        _write_json(status_path, payload)
        raise

    try:
        if len(logs) != config.episodes or len(observed_logs) != len(logs):
            raise MCRLContractError(
                "training callback and returned episode logs disagree"
            )
        failure_stage = "final-checkpoint"
        temporary_checkpoint = checkpoint_path.with_suffix(".pt.tmp")
        trainer.save_checkpoint(
            temporary_checkpoint,
            episode=config.episodes - 1,
            checkpoint_kind=config.checkpoint_primary_report,
            logs=logs,
        )
        temporary_checkpoint.replace(checkpoint_path)
        failure_stage = "episode-log-write"
        _write_json(logs_path, [asdict(log) for log in logs])
        base_payload = status | {
            "episodes_completed": len(logs),
            "checkpoint": str(checkpoint_path),
            "checkpoint_sha256": _file_sha256(checkpoint_path),
            "episode_logs": str(logs_path),
            "episode_logs_sha256": _file_sha256(logs_path),
            "collapse_summary": _collapse_summary(logs),
        }
        evaluation = None
        if evaluate_p6:
            failure_stage = "P6-evaluation"
            evaluation = evaluate_p6_arm(
                trainer,
                lambda: make_training_environment(users=100),
            )
        payload = base_payload | {
            "status": "complete",
            "finished_utc": _utc_now(),
        }
        if evaluation is not None:
            payload |= evaluation
        _write_json(status_path, payload)
        return payload
    except P6NonFiniteEvaluationError as error:
        payload = base_payload | {
            "status": "incomplete",
            "failure_kind": "nonfinite-evaluation",
            "failure_stage": failure_stage,
            "error_type": type(error).__name__,
            "error": str(error),
            "finished_utc": _utc_now(),
        }
        _write_json(status_path, payload)
        return payload
    except Exception as error:
        payload = status | {
            "status": "failed",
            "failure_stage": failure_stage,
            "error_type": type(error).__name__,
            "error": str(error),
            "episodes_completed": len(observed_logs),
            "finished_utc": _utc_now(),
        }
        if logs_path.is_file():
            payload |= {
                "episode_logs": str(logs_path),
                "episode_logs_sha256": _file_sha256(logs_path),
            }
        if checkpoint_path.is_file():
            payload |= {
                "checkpoint": str(checkpoint_path),
                "checkpoint_sha256": _file_sha256(checkpoint_path),
            }
        _write_json(status_path, payload)
        raise


def run_p6_sweep(
    record: PreregRecord,
    output_dir: Path,
) -> tuple[float, dict[str, Any]]:
    """Run/reuse the three arms, then apply the frozen LR mapping."""
    assert_p6_protocol_matches_record(record)
    arms: dict[float, dict[str, Any]] = {}
    for learning_rate in P6_LEARNING_RATES:
        arm_dir = output_dir / f"p6-lr-{learning_rate:g}"
        status_path = arm_dir / "status.json"
        reusable = None
        expected_fingerprint = build_run_fingerprint(
            record,
            role="P6-learning-rate-arm",
            learning_rate=learning_rate,
            train_seed=P6_TRAIN_SEED,
            env_seed=P6_ENV_SEED,
            mobility_seed=P6_MOBILITY_SEED,
        )
        if status_path.exists():
            try:
                candidate = json.loads(status_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                candidate = None
            if isinstance(candidate, dict) and arm_status_is_reusable(
                candidate,
                arm_dir,
                expected_fingerprint=expected_fingerprint,
                expected_episodes=_trainer_config(
                    record, learning_rate=learning_rate
                ).episodes,
                evaluate_p6=True,
            ):
                reusable = candidate
        arms[learning_rate] = reusable or _run_training(
            record=record,
            learning_rate=learning_rate,
            output_dir=arm_dir,
            role="P6-learning-rate-arm",
            train_seed=P6_TRAIN_SEED,
            env_seed=P6_ENV_SEED,
            mobility_seed=P6_MOBILITY_SEED,
            evaluate_p6=True,
        )
    selected, selection = choose_learning_rate(arms)
    summary = {
        "status": "complete",
        "prereg_digest": record.digest,
        "learning_rate_arms": {
            str(lr): arms[lr] for lr in P6_LEARNING_RATES
        },
        "selection": selection,
        "finished_utc": _utc_now(),
    }
    _write_json(output_dir / "p6-summary.json", summary)
    return selected, summary


def run_main_training(
    record: PreregRecord,
    output_dir: Path,
    *,
    learning_rate: float,
) -> dict[str, Any]:
    """Start the independent main run with the explicitly selected LR."""
    if float(learning_rate) not in P6_LEARNING_RATES:
        raise MCRLContractError(
            f"main learning rate {learning_rate} is outside frozen P6 arms"
        )
    main_dir = output_dir / "main"
    expected_fingerprint = build_run_fingerprint(
        record,
        role="main-training",
        learning_rate=float(learning_rate),
        train_seed=MAIN_TRAIN_SEED,
        env_seed=MAIN_ENV_SEED,
        mobility_seed=MAIN_MOBILITY_SEED,
    )
    status_path = main_dir / "status.json"
    if status_path.is_file():
        try:
            candidate = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            candidate = None
        if isinstance(candidate, dict) and arm_status_is_reusable(
            candidate,
            main_dir,
            expected_fingerprint=expected_fingerprint,
            expected_episodes=_trainer_config(
                record, learning_rate=float(learning_rate)
            ).episodes,
            evaluate_p6=False,
        ):
            return candidate
    return _run_training(
        record=record,
        learning_rate=float(learning_rate),
        output_dir=main_dir,
        role="main-training",
        train_seed=MAIN_TRAIN_SEED,
        env_seed=MAIN_ENV_SEED,
        mobility_seed=MAIN_MOBILITY_SEED,
        evaluate_p6=False,
    )


def run_training_pipeline(
    prereg_path: Path = CANONICAL_PREREG,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    probe_summary_path: Path = CORRECTED_PROBE_SUMMARY,
) -> dict[str, Any]:
    """P6 -> frozen selection -> main, suitable for one tmux command."""
    pipeline_status = {
        "status": "running",
        "phase": "validation",
        "prereg": str(prereg_path),
        "corrected_probe_summary": str(probe_summary_path),
        "started_utc": _utc_now(),
    }
    _write_json(output_dir / "pipeline-status.json", pipeline_status)
    try:
        record = validate_server_setup(
            prereg_path,
            probe_summary_path=probe_summary_path,
        )
        pipeline_status |= {
            "phase": "P6",
            "prereg_digest": record.digest,
            "validation_finished_utc": _utc_now(),
        }
        _write_json(output_dir / "pipeline-status.json", pipeline_status)
        selected, p6_summary = run_p6_sweep(record, output_dir)
        if p6_summary.get("status") != "complete":
            raise MCRLContractError("P6 sweep did not reach complete status")
        pipeline_status |= {
            "phase": "main",
            "selected_learning_rate": selected,
            "main_started_utc": _utc_now(),
        }
        _write_json(output_dir / "pipeline-status.json", pipeline_status)
        main = run_main_training(
            record,
            output_dir,
            learning_rate=selected,
        )
        if main.get("status") != "complete":
            raise MCRLContractError(
                "main training did not reach complete status: "
                f"{main.get('status')!r}"
            )
        final = pipeline_status | {
            "status": "complete",
            "phase": "complete",
            "finished_utc": _utc_now(),
            "p6_summary": p6_summary,
            "main": main,
        }
        _write_json(output_dir / "pipeline-status.json", final)
        return final
    except Exception as error:
        failed = pipeline_status | {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "finished_utc": _utc_now(),
        }
        _write_json(output_dir / "pipeline-status.json", failed)
        raise
