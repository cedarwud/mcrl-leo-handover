"""Bounded episode-loop adapter for the C2 V0.3 Multi-Catfish seam.

This module is deliberately append-only.  The historical ``run_short_ep.py``
runner remains the V0.2 implementation; this file is the smallest runner that
can exercise the V0.3 path without changing that baseline.  A treatment arm
owns one canonical Main trajectory and up to three independent source
trajectories.  Main rows are admitted once per environment decision.  A
formal C2 option, when selected, consumes its realised one-to-four primitive
steps and owns the one combined Main update through
``selection -> training_step -> joint_transaction``.  If C2 is K=0 or has no
admitted option, the C1/C3 donors (if enabled) share one combined Main update.

The command-line entry point is intentionally bounded and developmental.  It
supports ``B000``/``F111``/``A011``/``A101``/``A110`` for a short smoke only;
it never launches a 1500/3000/9000 episode run.  The caller may later choose a
longer schedule after reviewing the smoke receipts.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import platform
import sys
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SMC_DIR = HERE.parent / "smc-er-short-ep"
for _path in (HERE, SMC_DIR, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import c2_temporal_fork_core as c2_core  # noqa: E402
import c2_temporal_fork_combined_carrier as c2_combined  # noqa: E402
import c2_temporal_fork_joint_transaction as c2_joint  # noqa: E402
import c2_temporal_fork_option_runner as c2_option_runner  # noqa: E402
import c2_temporal_fork_selection as c2_selection  # noqa: E402
import c2_temporal_fork_telemetry as c2_telemetry  # noqa: E402
import c2_temporal_fork_torch_adapter as c2_torch  # noqa: E402
import c2_temporal_fork_training_step as c2_training_step  # noqa: E402
import c2_temporal_fork_trainer_backend as c2_backend  # noqa: E402
import run_short_ep as legacy  # noqa: E402
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.env.action_contract import Association  # noqa: E402
from mcrl.env.step_types import ActionMask  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
)
from smc_er_core import (  # noqa: E402
    AtomicBundle,
    BundleReplay,
    ConsumedBundleLedger,
    ObjectiveSpecialist,
)


SCHEMA = "multi-catfish-c2-v03-episode-loop-v2"
RUNTIME_STATE_SCHEMA = "c2-v03-episode-loop-state-v4"
RUNTIME_STATE_FORMAT_VERSION = 4
RUN_JOURNAL_SCHEMA = "c2-v03-bounded-run-journal-v2"
CLAIM_CEILING = (
    "bounded implementation/smoke mechanics only; no EE efficacy, chapter-5 "
    "result, or deployment authorization"
)
C2_CODE_AUTHORITY_RELATIVE_PATHS = (
    ".scratch/c2-v03/c2_stage0_receipt_adapter.py",
    ".scratch/c2-v03/c2_temporal_fork_chronology.py",
    ".scratch/c2-v03/c2_temporal_fork_combined_carrier.py",
    ".scratch/c2-v03/c2_temporal_fork_core.py",
    ".scratch/c2-v03/c2_temporal_fork_episode_runner.py",
    ".scratch/c2-v03/c2_temporal_fork_forecast_adapter.py",
    ".scratch/c2-v03/c2_temporal_fork_joint_transaction.py",
    ".scratch/c2-v03/c2_temporal_fork_learning_adapter.py",
    ".scratch/c2-v03/c2_temporal_fork_option_runner.py",
    ".scratch/c2-v03/c2_temporal_fork_runtime_adapter.py",
    ".scratch/c2-v03/c2_temporal_fork_selection.py",
    ".scratch/c2-v03/c2_temporal_fork_telemetry.py",
    ".scratch/c2-v03/c2_temporal_fork_torch_adapter.py",
    ".scratch/c2-v03/c2_temporal_fork_trainer_backend.py",
    ".scratch/c2-v03/c2_temporal_fork_training_step.py",
    ".scratch/smc-er-short-ep/c1_exp_corpus.py",
    ".scratch/smc-er-short-ep/c1_pretransfer_gate_validator.py",
    ".scratch/smc-er-short-ep/gate_receipt_validator.py",
    ".scratch/smc-er-short-ep/intermediate_trend_authority.py",
    ".scratch/smc-er-short-ep/run_short_ep.py",
    ".scratch/smc-er-short-ep/smc_er_core.py",
    ".scratch/smc-er-short-ep/smc_er_roles.py",
    ".scratch/catfish-stage0/c3_reward_aligned_v3_core.py",
    ".scratch/catfish-stage0/c3_reward_aligned_v3_runtime_adapter.py",
    ".scratch/catfish-stage0/c3_reward_aligned_v3_shadow_runner.py",
    ".scratch/catfish-stage0/c3_reward_aligned_v3_trainer_backend.py",
    ".scratch/catfish-stage0/run_c3_stage0.py",
    ".scratch/catfish-oracle-gate/run_oracle_gate.py",
    "scripts/run_head_pivotality_probe.py",
)


def _c2_code_authority_paths() -> list[Path]:
    """Return the exact implementation manifest bound to every C2 anchor."""

    paths = [*_default_code_paths()]
    paths.extend(REPO / relative for relative in C2_CODE_AUTHORITY_RELATIVE_PATHS)
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "C2 code-authority manifest contains missing files: "
            + ", ".join(str(path) for path in missing)
        )
    return sorted(set(paths), key=lambda path: path.relative_to(REPO).as_posix())


def _mechanism_authority(
    *, environment_source_sha256: str | None = None
) -> dict[str, Any]:
    """Return one code/reward authority shared by baseline and treatment arms."""

    paths = _c2_code_authority_paths()
    return {
        "candidate_version": c2_core.CANDIDATE_VERSION,
        "forecast_authority_schema": c2_core.FORECAST_AUTHORITY_SCHEMA,
        "main_policy_version": c2_backend.MAIN_POLICY_VERSION,
        "policy_compositor_version": c2_backend.POLICY_COMPOSITOR_VERSION,
        "environment_source_sha256": (
            _code_sha256(paths)
            if environment_source_sha256 is None
            else str(environment_source_sha256)
        ),
        "reward_source_sha256": _sha256_file(
            REPO / "src" / "mcrl" / "env" / "step.py"
        ),
        "code_authority_paths": [
            path.relative_to(REPO).as_posix() for path in paths
        ],
    }
SUPPORTED_ARMS = ("B000", "F111", "A011", "A101", "A110")
MAX_DEVELOPMENT_EPISODES = 24

# Preserve the old arm names and meaning.  The first tuple controls whether a
# source uses its informed behaviour policy; the active-source set controls
# whether that source is present in Main's combined carrier.
ARM_LANES: dict[str, tuple[bool, bool, bool] | None] = {
    "B000": None,
    "F111": (True, True, True),
    "A011": (False, True, True),  # no C1
    "A101": (True, False, True),  # no C2
    "A110": (True, True, False),  # no C3
}
ARM_ACTIVE_SOURCES: dict[str, frozenset[str]] = {
    "F111": frozenset({"C1", "C2", "C3"}),
    "A011": frozenset({"C2", "C3"}),
    "A101": frozenset({"C1", "C3"}),
    "A110": frozenset({"C1", "C2"}),
}
ARM_LABELS = {
    "B000": "Baseline MODQN",
    "F111": "Full Multi-Catfish MCRL",
    "A011": "Full - C1",
    "A101": "Full - C2",
    "A110": "Full - C3",
}


@dataclass(frozen=True)
class C2EpisodeLoopConfig:
    """Only loop-level knobs; physics and network values stay in prereg."""

    arm: str
    episodes: int
    users: int
    train_seed: int
    env_seed: int
    mobility_seed: int
    checkpoint_every: int = 100
    beta: float = 0.25
    max_c2_candidates: int = 9
    acrm_eta: float = legacy.DEFAULT_ACRM_ETA

    def __post_init__(self) -> None:
        if self.arm not in SUPPORTED_ARMS:
            raise ValueError(f"unsupported arm {self.arm!r}")
        for name in ("episodes", "users", "checkpoint_every", "max_c2_candidates"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive exact integer")
        for name in ("train_seed", "env_seed", "mobility_seed"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative exact integer")
        if isinstance(self.beta, bool) or not isinstance(self.beta, (int, float)):
            raise ValueError("beta must be finite in [0,1]")
        if not np.isfinite(float(self.beta)) or not 0.0 <= float(self.beta) <= 1.0:
            raise ValueError("beta must be finite in [0,1]")
        if isinstance(self.acrm_eta, bool) or not isinstance(self.acrm_eta, (int, float)):
            raise ValueError("acrm_eta must be finite and nonnegative")
        if not np.isfinite(float(self.acrm_eta)) or float(self.acrm_eta) < 0.0:
            raise ValueError("acrm_eta must be finite and nonnegative")


@dataclass
class _C2Runtime:
    """Mutable state owned by one bounded run."""

    main: MODQNTrainer
    trajectories: dict[str, legacy.Trajectory]
    specialists: dict[str, ObjectiveSpecialist]
    replays: dict[str, BundleReplay]
    consumed_ledger: ConsumedBundleLedger
    c2_option_ledger: c2_torch.C2OptionLedger
    transaction_ledger: c2_joint.JointOptionLedger
    selection_rng: np.random.Generator
    checkpoint_sha256: str
    environment_source_sha256: str
    reward_source_sha256: str
    # Kept optional for small fixture runtimes.  Production runtimes created
    # by ``_make_runtime`` bind this exact loop config into every snapshot.
    loop_config: C2EpisodeLoopConfig | None = None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _masks_from_observation(observation: Any) -> list[ActionMask]:
    masks = np.asarray(getattr(observation, "masks", None))
    if masks.dtype != np.bool_ or masks.ndim != 2:
        raise RuntimeError("successor observation lacks a Boolean mask matrix")
    return [ActionMask(mask=row.copy()) for row in masks]


def _advance_from_outcome(
    trajectory: legacy.Trajectory,
    *,
    observation: Any | None = None,
    states: Sequence[Any] | None = None,
    masks: Sequence[Any] | None = None,
) -> None:
    """Advance a trajectory from a real environment result/observation."""

    if observation is None:
        outcome = trajectory.environment.last_outcome
        observation = outcome.observation
    if states is None:
        states = getattr(observation, "user_states", None)
    if masks is None:
        masks = _masks_from_observation(observation)
    if states is None or masks is None:
        raise RuntimeError("trajectory successor lacks states or masks")
    trajectory.states = list(states)
    trajectory.masks = list(masks)
    trajectory.observation = observation


def _network_digest(trainer: MODQNTrainer) -> str:
    digest = hashlib.sha256()
    for objective, network in enumerate(trainer.q_nets):
        for name, tensor in sorted(network.state_dict().items()):
            digest.update(f"{objective}:{name}".encode("utf-8"))
            digest.update(np.asarray(tensor.detach().cpu()).tobytes(order="C"))
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            default=lambda item: (
                item.tolist()
                if isinstance(item, np.ndarray)
                else item.item()
                if isinstance(item, np.generic)
                else str(item)
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


_CHRONOLOGY_TIME_FIELDS = (
    "forecast_started_ns",
    "forecast_completed_ns",
    "live_step_started_ns",
    "live_step_completed_ns",
)


def _canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _c2_option_audit(
    unit: Any,
    receipt: Any,
    *,
    episode: int,
    step_index: int,
) -> dict[str, Any]:
    """Persist the chronology preimage behind time-varying integrity hashes.

    The four monotonic timestamps deliberately differ after a process restart.
    Keeping their complete receipt plus a clock-excluded identity digest lets a
    resume verifier distinguish expected provenance variance from training-state
    divergence without weakening the chronology receipt itself.
    """

    chronology = getattr(unit, "chronology_receipt", None)
    closure = getattr(unit, "closure", None)
    plan = getattr(closure, "plan", None)
    if chronology is None or plan is None or not hasattr(
        chronology, "__dataclass_fields__"
    ):
        return {
            "schema": "c2-v03-option-chronology-audit-v1",
            "episode": int(episode),
            "step": int(step_index),
            "audit_available": False,
            "reason": "test-double-or-nonstandard-runner-unit",
            "claim_ceiling": (
                "diagnostic availability only; no chronology, training, or EE claim"
            ),
        }

    chronology_payload = asdict(chronology)
    timing = {
        name: chronology_payload[name] for name in _CHRONOLOGY_TIME_FIELDS
    }
    ordered = tuple(int(timing[name]) for name in _CHRONOLOGY_TIME_FIELDS)
    if tuple(sorted(ordered)) != ordered:
        raise RuntimeError("C2 chronology audit contains out-of-order timestamps")
    clock_excluded = dict(chronology_payload)
    for name in _CHRONOLOGY_TIME_FIELDS:
        del clock_excluded[name]

    sequence = getattr(unit, "sequence", None)
    transition = getattr(unit, "transition", None)
    proof = getattr(sequence, "admission_proof", None)
    return {
        "schema": "c2-v03-option-chronology-audit-v1",
        "episode": int(episode),
        "step": int(step_index),
        "audit_available": True,
        "option_id": getattr(plan, "option_id", None),
        "bundle_ids": list(getattr(plan, "main_bundle_ids", ())),
        "selection_receipt_sha256": getattr(
            sequence, "selection_receipt_sha256", None
        ),
        "chronology_receipt_sha256": getattr(
            plan, "chronology_receipt_sha256", None
        ),
        "chronology_receipt": chronology_payload,
        "clock_excluded_identity_sha256": _canonical_json_sha256(clock_excluded),
        "admission_plan_sha256": getattr(proof, "plan_sha256", None),
        "admission_proof_sha256": getattr(proof, "proof_sha256", None),
        "transition_sha256": getattr(transition, "sequence_sha256", None),
        "primitive_sequence_sha256": getattr(sequence, "sequence_sha256", None),
        "joint_record_sha256": getattr(receipt, "joint_record_sha256", None),
        "claim_ceiling": (
            "chronology provenance and resume diagnosis only; no EE efficacy or "
            "training-trend result"
        ),
    }


def _write_run_journal(
    output_dir: Path,
    *,
    status: str,
    config: C2EpisodeLoopConfig,
    trainer_config: Mapping[str, Any],
    result: Mapping[str, Any] | None = None,
    error: BaseException | None = None,
) -> None:
    if status not in {"running", "complete", "failed"}:
        raise ValueError("run journal status is invalid")
    if status == "failed" and error is None:
        raise ValueError("failed run journal requires an error")
    if status != "failed" and error is not None:
        raise ValueError("only a failed run journal may carry an error")
    payload: dict[str, Any] = {
        "schema": RUN_JOURNAL_SCHEMA,
        "status": status,
        "config": asdict(config),
        "trainer_config": copy.deepcopy(dict(trainer_config)),
        "claim_ceiling": CLAIM_CEILING,
    }
    if result is not None:
        payload["result_summary"] = {
            "dispatch": result.get("dispatch"),
            "episodes": result.get("episodes"),
            "joint_transaction_count": result.get("joint_transaction_count"),
            "checkpoint_sha256": result.get("checkpoint_sha256"),
        }
    if error is not None:
        payload["failure"] = {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
    _write_json(Path(output_dir) / "run-journal.json", payload)


def _copy_rng_state(rng: np.random.Generator, *, field: str) -> dict[str, Any]:
    """Copy one NumPy stream and fail closed for a non-Generator object."""

    if not isinstance(rng, np.random.Generator):
        raise TypeError(f"{field} must be a numpy Generator")
    return copy.deepcopy(rng.bit_generator.state)


def _validate_rng_state(value: Any, *, field: str) -> None:
    """Validate a serialized NumPy stream without mutating live state."""

    try:
        candidate = np.random.default_rng()
        candidate.bit_generator.state = copy.deepcopy(value)
    except (TypeError, ValueError, KeyError) as error:
        raise ValueError(f"invalid runtime snapshot {field}") from error


def _config_mapping(value: Any, *, field: str) -> dict[str, Any]:
    """Return a detached dataclass/config mapping for binding checks."""

    if isinstance(value, Mapping):
        return copy.deepcopy(dict(value))
    try:
        return copy.deepcopy(asdict(value))
    except (TypeError, ValueError):
        values = getattr(value, "__dict__", None)
        if isinstance(values, Mapping):
            return copy.deepcopy(dict(values))
    raise TypeError(f"{field} must expose a mapping or dataclass fields")


def _canonical_json_value(value: Any, *, field: str = "value") -> Any:
    """Convert a config mapping to one deterministic JSON-safe representation."""

    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError(f"{field} mapping keys must be strings")
        return {
            key: _canonical_json_value(value[key], field=f"{field}.{key}")
            for key in sorted(value)
        }
    if isinstance(value, (tuple, list)):
        return [
            _canonical_json_value(item, field=f"{field}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, np.ndarray):
        return _canonical_json_value(value.tolist(), field=field)
    if isinstance(value, np.generic):
        return _canonical_json_value(value.item(), field=field)
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError(f"{field} contains a non-finite float")
        return value
    raise TypeError(f"{field} contains unsupported value {type(value).__name__}")


def _canonical_trainer_config(value: Any, *, field: str = "trainer_config") -> dict[str, Any]:
    """Return the exact JSON-facing trainer config identity for provenance."""

    canonical = _canonical_json_value(_config_mapping(value, field=field), field=field)
    if not isinstance(canonical, dict):  # pragma: no cover - guarded above
        raise TypeError(f"{field} must canonicalize to a mapping")
    if "learning_rate" not in canonical:
        raise ValueError(f"{field} must bind learning_rate")
    return canonical


def _bound_acrm_eta(config: C2EpisodeLoopConfig, supplied: float | None = None) -> float:
    """Resolve the loop-owned ACRM eta and reject an unbound override."""

    configured = float(config.acrm_eta)
    if not np.isfinite(configured) or configured < 0.0:
        raise ValueError("config.acrm_eta must be finite and nonnegative")
    if supplied is not None:
        if isinstance(supplied, bool) or not isinstance(supplied, (int, float)):
            raise ValueError("acrm_eta override must be finite and nonnegative")
        if not np.isfinite(float(supplied)) or float(supplied) < 0.0:
            raise ValueError("acrm_eta override must be finite and nonnegative")
        if not np.isclose(float(supplied), configured, rtol=0.0, atol=0.0):
            raise ValueError("acrm_eta override does not match loop config identity")
    return configured


def _environment_binding(environment: Any) -> dict[str, Any]:
    config = getattr(environment, "config", None)
    if config is None:
        raise TypeError("trajectory environment lacks a config binding")
    return _config_mapping(config, field="trajectory environment config")


def _trajectory_snapshot(trajectory: legacy.Trajectory) -> dict[str, Any]:
    """Capture every source cursor, stream, and wrapped environment state."""

    environment_state_method = getattr(trajectory.environment, "training_state_dict", None)
    if not callable(environment_state_method):
        raise TypeError(
            "trajectory environment must expose training_state_dict for C2 resume"
        )
    environment_state = environment_state_method()
    if not isinstance(environment_state, Mapping):
        raise TypeError("trajectory environment training state must be a mapping")
    commitment = getattr(trajectory, "_c3_option", None)
    if commitment is not None:
        if not isinstance(commitment, legacy.OptionCommitment):
            raise TypeError("C3 option commitment has an unsupported type")
        commitment_state: dict[str, Any] | None = copy.deepcopy(asdict(commitment))
    else:
        commitment_state = None
    return {
        "environment_binding": _environment_binding(trajectory.environment),
        "env_rng_state": _copy_rng_state(trajectory.env_rng, field="env_rng"),
        "mobility_rng_state": _copy_rng_state(
            trajectory.mobility_rng, field="mobility_rng"
        ),
        # These are terminal at an episode boundary in the current loop, but
        # retaining them makes the snapshot an exact source cursor rather than
        # a seed-only restart and keeps the loader fail-closed if a caller
        # resumes from another boundary implementation.
        "states": copy.deepcopy(trajectory.states),
        "masks": copy.deepcopy(trajectory.masks),
        "observation": copy.deepcopy(trajectory.observation),
        "environment_state": copy.deepcopy(dict(environment_state)),
        "c3_option_commitment": commitment_state,
    }


def _capture_runtime_state(
    runtime_state: _C2Runtime,
    *,
    config: C2EpisodeLoopConfig,
    episode: int,
    refresh_checkpoint_digest: bool = False,
) -> dict[str, Any]:
    """Build an isolated, complete episode-boundary state payload."""

    if type(episode) is not int or episode < 0:
        raise ValueError("runtime snapshot episode must be a nonnegative exact integer")
    if episode > config.episodes:
        raise ValueError("runtime snapshot episode exceeds configured episodes")
    main_state = runtime_state.main.training_state_dict()
    if not isinstance(main_state, Mapping):
        raise TypeError("Main training state must be a mapping")
    main_state = copy.deepcopy(dict(main_state))
    if "trainer_config" not in main_state:
        raise ValueError("Main training state lacks trainer_config binding")
    canonical_trainer_config = _canonical_trainer_config(
        main_state["trainer_config"], field="Main training state trainer_config"
    )
    if refresh_checkpoint_digest:
        runtime_state.checkpoint_sha256 = _network_digest(runtime_state.main)
    source_order = ("Main", "C1", "C2", "C3")
    if tuple(runtime_state.trajectories) != source_order:
        raise ValueError("runtime trajectories must use Main/C1/C2/C3 source order")
    if tuple(runtime_state.specialists) != ("C1", "C2", "C3"):
        raise ValueError("runtime specialists must use C1/C2/C3 source order")
    if tuple(runtime_state.replays) != ("C1", "C2", "C3"):
        raise ValueError("runtime replays must use C1/C2/C3 source order")
    trajectories = {
        source: _trajectory_snapshot(runtime_state.trajectories[source])
        for source in source_order
    }
    return {
        "schema": RUNTIME_STATE_SCHEMA,
        "format_version": RUNTIME_STATE_FORMAT_VERSION,
        "c2_policy_version": c2_core.CANDIDATE_VERSION,
        "boundary": "episode",
        "episodes_completed": int(episode),
        "source_order": list(source_order),
        "loop_config": copy.deepcopy(asdict(config)),
        "trainer_config": canonical_trainer_config,
        "authority": {
            "checkpoint_sha256": str(runtime_state.checkpoint_sha256),
            "environment_source_sha256": str(runtime_state.environment_source_sha256),
            "reward_source_sha256": str(runtime_state.reward_source_sha256),
        },
        "main_training_state": main_state,
        "specialists": {
            source: copy.deepcopy(runtime_state.specialists[source].state_dict())
            for source in ("C1", "C2", "C3")
        },
        "bundle_replays": {
            source: copy.deepcopy(runtime_state.replays[source].state_dict())
            for source in ("C1", "C2", "C3")
        },
        "consumed_ledger": copy.deepcopy(runtime_state.consumed_ledger.state_dict()),
        "c2_option_ledger": copy.deepcopy(runtime_state.c2_option_ledger.state_dict()),
        "joint_transaction_ledger": copy.deepcopy(
            runtime_state.transaction_ledger.state_dict()
        ),
        "selection_rng_state": _copy_rng_state(
            runtime_state.selection_rng, field="selection_rng"
        ),
        "source_trajectories": trajectories,
    }


def _save_runtime_state(
    path: Path,
    runtime_state: _C2Runtime,
    *,
    episode: int,
    config: C2EpisodeLoopConfig | None = None,
) -> None:
    """Persist a complete, authority-bound episode-boundary resume snapshot."""

    if config is None:
        config = runtime_state.loop_config
    if config is None:
        raise ValueError("C2 runtime snapshot requires a bound loop config")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = _capture_runtime_state(
        runtime_state,
        config=config,
        episode=episode,
        refresh_checkpoint_digest=True,
    )
    torch.save(payload, temporary)
    temporary.replace(path)


def _torch_load_runtime_state(path: Path) -> Mapping[str, Any]:
    """Load one local snapshot with an explicit non-weights-only policy."""

    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:  # PyTorch < 2.6 has no weights_only keyword.
        payload = torch.load(path, map_location="cpu")
    if not isinstance(payload, Mapping):
        raise TypeError("C2 runtime snapshot must contain a mapping")
    return payload


def _digest_format(value: Any, *, field: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"runtime snapshot {field} must be a SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"runtime snapshot {field} must be a SHA-256 hex digest") from error
    return value


def _validate_runtime_snapshot(
    payload: Mapping[str, Any],
    *,
    runtime_state: _C2Runtime,
    config: C2EpisodeLoopConfig,
) -> int:
    """Validate all bindings before any live object is changed."""

    if payload.get("schema") != RUNTIME_STATE_SCHEMA:
        raise ValueError("unsupported C2 runtime snapshot schema")
    if payload.get("format_version") != RUNTIME_STATE_FORMAT_VERSION:
        raise ValueError("unsupported C2 runtime snapshot format version")
    if payload.get("c2_policy_version") != c2_core.CANDIDATE_VERSION:
        raise ValueError("unsupported C2 runtime snapshot policy version")
    if payload.get("boundary") != "episode":
        raise ValueError("C2 runtime snapshot is not an episode-boundary state")
    episode = payload.get("episodes_completed")
    if type(episode) is not int or episode < 0 or episode > config.episodes:
        raise ValueError("runtime snapshot episodes_completed is outside config")
    if payload.get("source_order") != ["Main", "C1", "C2", "C3"]:
        raise ValueError("runtime snapshot source order is invalid")
    expected_loop_config = asdict(config)
    if payload.get("loop_config") != expected_loop_config:
        raise ValueError("runtime snapshot loop_config does not match requested config")

    main_state = payload.get("main_training_state")
    if not isinstance(main_state, Mapping):
        raise TypeError("runtime snapshot main_training_state is malformed")
    trainer_config = payload.get("trainer_config")
    if trainer_config != _canonical_trainer_config(
        trainer_config, field="runtime snapshot trainer_config"
    ):
        raise ValueError("runtime snapshot trainer_config is not canonical")
    if trainer_config != _canonical_trainer_config(
        main_state.get("trainer_config"),
        field="runtime snapshot Main state trainer_config",
    ):
        raise ValueError("runtime snapshot trainer_config disagrees with Main state")
    expected_main_config = _canonical_trainer_config(
        getattr(runtime_state.main, "config", None), field="Main trainer config"
    )
    if trainer_config != expected_main_config:
        raise ValueError("runtime snapshot trainer_config does not match runtime")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise TypeError("runtime snapshot authority is malformed")
    checkpoint_sha = _digest_format(
        authority.get("checkpoint_sha256"), field="authority.checkpoint_sha256"
    )
    for field in ("environment_source_sha256", "reward_source_sha256"):
        value = _digest_format(authority.get(field), field=f"authority.{field}")
        if value != str(getattr(runtime_state, field)):
            raise ValueError(f"runtime snapshot {field} does not match runtime")

    specialists = payload.get("specialists")
    replays = payload.get("bundle_replays")
    if not isinstance(specialists, Mapping) or set(specialists) != {"C1", "C2", "C3"}:
        raise ValueError("runtime snapshot specialists are incomplete")
    if not isinstance(replays, Mapping) or set(replays) != {"C1", "C2", "C3"}:
        raise ValueError("runtime snapshot bundle replays are incomplete")
    for source in ("C1", "C2", "C3"):
        if not isinstance(specialists[source], Mapping):
            raise TypeError(f"runtime snapshot {source} specialist is malformed")
        if not isinstance(replays[source], Mapping):
            raise TypeError(f"runtime snapshot {source} replay is malformed")
    for field in (
        "consumed_ledger",
        "c2_option_ledger",
        "joint_transaction_ledger",
    ):
        if not isinstance(payload.get(field), Mapping):
            raise TypeError(f"runtime snapshot {field} is malformed")
    _validate_rng_state(payload.get("selection_rng_state"), field="selection_rng_state")

    source_trajectories = payload.get("source_trajectories")
    if not isinstance(source_trajectories, Mapping) or set(source_trajectories) != {
        "Main",
        "C1",
        "C2",
        "C3",
    }:
        raise ValueError("runtime snapshot source trajectories are incomplete")
    for source in ("Main", "C1", "C2", "C3"):
        item = source_trajectories[source]
        if not isinstance(item, Mapping):
            raise TypeError(f"runtime snapshot {source} trajectory is malformed")
        expected_binding = _environment_binding(runtime_state.trajectories[source].environment)
        if item.get("environment_binding") != expected_binding:
            raise ValueError(f"runtime snapshot {source} environment config mismatch")
        for field in ("env_rng_state", "mobility_rng_state"):
            _validate_rng_state(item.get(field), field=f"{source}.{field}")
        if not isinstance(item.get("environment_state"), Mapping):
            raise TypeError(f"runtime snapshot {source} environment state is malformed")
        if "states" not in item or "masks" not in item or "observation" not in item:
            raise ValueError(f"runtime snapshot {source} trajectory cursor is incomplete")
        commitment = item.get("c3_option_commitment")
        if commitment is not None:
            if source != "C3" or not isinstance(commitment, Mapping):
                raise ValueError("runtime snapshot has an invalid C3 commitment")
            expected_fields = {"focal_user", "physical_key", "remaining", "opened_step"}
            if set(commitment) != expected_fields:
                raise ValueError("runtime snapshot C3 commitment fields are invalid")
            remaining = commitment["remaining"]
            if isinstance(remaining, bool) or not isinstance(remaining, (int, np.integer)):
                raise TypeError("runtime snapshot C3 commitment remaining is invalid")
            if int(remaining) < 0:
                raise ValueError("runtime snapshot C3 commitment remaining is negative")
            focal_user = commitment["focal_user"]
            if focal_user is not None and (
                isinstance(focal_user, bool)
                or not isinstance(focal_user, (int, np.integer))
                or int(focal_user) < 0
            ):
                raise ValueError("runtime snapshot C3 commitment focal user is invalid")
            key = commitment["physical_key"]
            if key is not None and (
                isinstance(key, (str, bytes))
                or not isinstance(key, Sequence)
                or len(key) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, np.integer)) for v in key)
            ):
                raise ValueError("runtime snapshot C3 commitment physical key is invalid")
            opened_step = commitment["opened_step"]
            if opened_step is not None and (
                isinstance(opened_step, bool)
                or not isinstance(opened_step, (int, np.integer))
                or int(opened_step) < 0
            ):
                raise ValueError("runtime snapshot C3 commitment opened step is invalid")
        elif source == "C3":
            # A missing commitment means the C3 source was never opened.  It
            # is valid, but the loader will install a closed commitment.
            pass
    return int(episode)


def _restore_runtime_state_payload(
    runtime_state: _C2Runtime, payload: Mapping[str, Any]
) -> None:
    """Apply a previously validated payload to all mutable runtime objects."""

    runtime_state.main.load_training_state_dict(
        copy.deepcopy(payload["main_training_state"])
    )
    for source in ("C1", "C2", "C3"):
        runtime_state.specialists[source].load_state_dict(
            copy.deepcopy(payload["specialists"][source])
        )
        runtime_state.replays[source].load_state_dict(
            copy.deepcopy(payload["bundle_replays"][source])
        )
    runtime_state.consumed_ledger.load_state_dict(
        copy.deepcopy(payload["consumed_ledger"])
    )
    runtime_state.c2_option_ledger.load_state_dict(
        copy.deepcopy(payload["c2_option_ledger"])
    )
    runtime_state.transaction_ledger.load_state_dict(
        copy.deepcopy(payload["joint_transaction_ledger"])
    )
    runtime_state.selection_rng.bit_generator.state = copy.deepcopy(
        payload["selection_rng_state"]
    )
    for source in ("Main", "C1", "C2", "C3"):
        trajectory = runtime_state.trajectories[source]
        item = payload["source_trajectories"][source]
        trajectory.env_rng.bit_generator.state = copy.deepcopy(item["env_rng_state"])
        trajectory.mobility_rng.bit_generator.state = copy.deepcopy(
            item["mobility_rng_state"]
        )
        loader = getattr(trajectory.environment, "load_training_state_dict", None)
        if not callable(loader):
            raise TypeError(f"{source} trajectory environment cannot load training state")
        loader(copy.deepcopy(item["environment_state"]))
        trajectory.states = copy.deepcopy(item["states"])
        trajectory.masks = copy.deepcopy(item["masks"])
        trajectory.observation = copy.deepcopy(item["observation"])
        commitment = item.get("c3_option_commitment")
        if source == "C3":
            restored_commitment = legacy.OptionCommitment()
            if commitment is not None:
                key = commitment["physical_key"]
                restored_commitment.focal_user = commitment["focal_user"]
                restored_commitment.physical_key = (
                    None if key is None else (int(key[0]), int(key[1]))
                )
                restored_commitment.remaining = int(commitment["remaining"])
                restored_commitment.opened_step = commitment["opened_step"]
            setattr(trajectory, "_c3_option", restored_commitment)
    runtime_state.checkpoint_sha256 = str(payload["authority"]["checkpoint_sha256"])
    if _network_digest(runtime_state.main) != runtime_state.checkpoint_sha256:
        raise ValueError("restored Main network does not match checkpoint authority")


def _load_runtime_state(
    path: Path,
    runtime_state: _C2Runtime,
    *,
    config: C2EpisodeLoopConfig,
) -> int:
    """Fail-closed, transactional load of an episode-boundary C2 snapshot."""

    payload = _torch_load_runtime_state(Path(path).expanduser().resolve())
    episode = _validate_runtime_snapshot(
        payload, runtime_state=runtime_state, config=config
    )
    # Capture the pre-load state so a nested loader (optimizer/replay/env)
    # failure cannot leave a partially restored live run.
    current = _capture_runtime_state(
        runtime_state,
        config=config,
        episode=episode,
        refresh_checkpoint_digest=True,
    )
    try:
        _restore_runtime_state_payload(runtime_state, payload)
    except BaseException as error:
        try:
            _restore_runtime_state_payload(runtime_state, current)
        except BaseException as rollback_error:
            raise RuntimeError("C2 runtime snapshot rollback failed") from rollback_error
        raise error
    return episode


def load_c2_v03_runtime_state(
    path: Path,
    runtime_state: _C2Runtime,
    *,
    config: C2EpisodeLoopConfig,
) -> int:
    """Public name for exact episode-boundary load-and-continue callers."""

    return _load_runtime_state(path, runtime_state, config=config)


def _save_periodic_checkpoint(
    runtime_state: _C2Runtime,
    output_dir: Path,
    *,
    episodes_completed: int,
) -> dict[str, Any]:
    checkpoint = (
        Path(output_dir)
        / "checkpoints"
        / f"ep-{int(episodes_completed):06d}-main.pt"
    )
    runtime_state.main.save_checkpoint(
        checkpoint,
        episode=int(episodes_completed) - 1,
        checkpoint_kind="periodic-main-policy-trend",
        include_optimizers=True,
    )
    payload = legacy.read_checkpoint(checkpoint, map_location="cpu")
    if payload.episode != int(episodes_completed) - 1:
        raise RuntimeError("periodic checkpoint episode failed round-trip")
    return {
        "episodes_completed": int(episodes_completed),
        "episode_index": int(payload.episode),
        "path": str(checkpoint),
        "sha256": _sha256_file(checkpoint),
        "checkpoint_kind": payload.checkpoint_kind,
        "load_round_trip": "PASS",
    }


def _run_baseline_with_telemetry(
    *,
    output_dir: Path,
    archive: Any,
    trainer_config: Any,
    users: int,
    train_seed: int,
    env_seed: int,
    mobility_seed: int,
    checkpoint_every: int,
) -> dict[str, Any]:
    """Run the unchanged Main trainer behind a read-only outcome observer."""

    telemetry = c2_telemetry.C2RunTelemetry()
    canonical_environment = legacy._make_environment(archive, users=users)
    observed_environment = c2_telemetry.OutcomeTelemetryEnvironment(
        canonical_environment,
        telemetry,
    )
    trainer = MODQNTrainer(
        observed_environment,
        trainer_config,
        train_seed=train_seed,
        env_seed=env_seed,
        mobility_seed=mobility_seed,
        device="cpu",
    )
    periodic_checkpoints: list[dict[str, Any]] = []
    observed_logs: list[Any] = []
    rolling_state = output_dir / "resume" / "latest-training-state.pt"

    def checkpoint_callback(log: Any) -> None:
        observed_logs.append(log)
        episodes_completed = int(log.episode) + 1
        if episodes_completed % int(checkpoint_every) != 0:
            return
        periodic_checkpoints.append(
            legacy._save_periodic_main_checkpoint(
                trainer=trainer,
                output_dir=output_dir,
                episodes_completed=episodes_completed,
                logs=observed_logs,
            )
        )
        legacy._save_training_state(rolling_state, trainer.training_state_dict())

    logs = trainer.train(progress_every=1, episode_callback=checkpoint_callback)
    checkpoint = output_dir / "final-checkpoint.pt"
    trainer.save_checkpoint(
        checkpoint,
        episode=trainer_config.episodes - 1,
        checkpoint_kind="final-episode-policy",
        logs=logs,
        include_optimizers=True,
    )
    training_state = output_dir / "training-state.pt"
    legacy._save_training_state(training_state, trainer.training_state_dict())
    _write_json(output_dir / "episode-logs.json", [asdict(row) for row in logs])
    telemetry_path = output_dir / "run-telemetry.json"
    telemetry_payload = telemetry.snapshot()
    _write_json(telemetry_path, telemetry_payload)
    return {
        "dispatch": "unchanged_MODQNTrainer.train+read_only_outcome_telemetry",
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": _sha256_file(checkpoint),
        "training_state": str(training_state),
        "training_state_sha256": _sha256_file(training_state),
        "episodes": len(logs),
        "checkpoint_every_episodes": int(checkpoint_every),
        "periodic_checkpoints": periodic_checkpoints,
        "periodic_checkpoint_count": len(periodic_checkpoints),
        "rolling_resume_state": (
            {
                "episodes_completed": int(
                    periodic_checkpoints[-1]["episodes_completed"]
                ),
                "path": str(rolling_state),
                "sha256": _sha256_file(rolling_state),
            }
            if periodic_checkpoints
            else None
        ),
        "masking_diagnostics": trainer.get_masking_diagnostics(),
        "telemetry": telemetry_payload,
        "telemetry_path": str(telemetry_path),
        "telemetry_sha256": _sha256_file(telemetry_path),
    }


def _departure_users(environment: Any, main_physical: Sequence[Any]) -> list[int]:
    previous = getattr(getattr(environment, "environment", None), "_previous_association", ())
    users: list[int] = []
    for uid, (incumbent, physical) in enumerate(zip(previous, main_physical, strict=True)):
        if (
            isinstance(incumbent, Association)
            and physical is not None
            and tuple(physical) != (int(incumbent.norad_id), int(incumbent.cell_id))
        ):
            users.append(uid)
    return users


def _make_runtime(
    *,
    config: C2EpisodeLoopConfig,
    archive: Any,
    trainer_config: Any,
    output_dir: Path,
) -> _C2Runtime:
    main_environment = legacy._make_environment(archive, users=config.users)
    main = MODQNTrainer(
        main_environment,
        trainer_config,
        train_seed=config.train_seed,
        env_seed=config.env_seed,
        mobility_seed=config.mobility_seed,
        device="cpu",
    )
    trajectories: dict[str, legacy.Trajectory] = {
        "Main": legacy.Trajectory(
            main_environment,
            main._env_rng,
            main._mobility_rng,
        )
    }
    # Independent objects but matched source seeds preserve the old paired
    # treatment design while allowing C2 to consume a four-step option.
    for source in ("C1", "C2", "C3"):
        trajectories[source] = legacy.Trajectory(
            legacy._make_environment(archive, users=config.users),
            np.random.default_rng(config.env_seed),
            np.random.default_rng(config.mobility_seed),
        )
    specialists = {
        "C1": ObjectiveSpecialist(
            objective_index=0,
            state_dim=main.state_dim,
            action_dim=main.action_dim,
            config=trainer_config,
            seed=config.train_seed + 10_001,
        ),
        "C2": ObjectiveSpecialist(
            objective_index=1,
            state_dim=main.state_dim,
            action_dim=main.action_dim,
            config=trainer_config,
            seed=config.train_seed + 20_003,
        ),
        "C3": ObjectiveSpecialist(
            objective_index=2,
            state_dim=main.state_dim,
            action_dim=main.action_dim,
            config=trainer_config,
            seed=config.train_seed + 30_007,
        ),
    }
    replays = {
        source: BundleReplay(legacy.SPECIALIST_BUNDLE_REPLAY_CAPACITY)
        for source in ("C1", "C2", "C3")
    }

    # The digest is a real artifact authority: a fresh initial policy is
    # snapshotted before the first episode and its SHA is bound to C2 anchors.
    initial_checkpoint = Path(output_dir) / "initial-main-checkpoint.pt"
    main.save_checkpoint(
        initial_checkpoint,
        episode=-1,
        checkpoint_kind="initial-c2-v03-policy-authority",
        include_optimizers=True,
    )
    checkpoint_sha = _sha256_file(initial_checkpoint)
    reward_source = REPO / "src" / "mcrl" / "env" / "step.py"
    return _C2Runtime(
        main=main,
        trajectories=trajectories,
        specialists=specialists,
        replays=replays,
        consumed_ledger=ConsumedBundleLedger(),
        c2_option_ledger=c2_torch.C2OptionLedger(),
        transaction_ledger=c2_joint.JointOptionLedger(),
        selection_rng=np.random.default_rng(config.train_seed + 40_009),
        checkpoint_sha256=checkpoint_sha,
        environment_source_sha256=_code_sha256(_c2_code_authority_paths()),
        reward_source_sha256=_sha256_file(reward_source),
        loop_config=config,
    )


def _main_source_step(
    runtime_state: _C2Runtime,
    *,
    arm: str,
    episode: int,
    step_index: int,
    epsilon: float,
) -> tuple[AtomicBundle, Any, np.ndarray]:
    trajectory = runtime_state.trajectories["Main"]
    if trajectory.states is None or trajectory.masks is None:
        raise RuntimeError("Main trajectory is not reset")
    encoded = runtime_state.main.encode_states(trajectory.states)
    actions = runtime_state.main.select_actions(
        encoded,
        trajectory.masks,
        epsilon,
        raw_states=trajectory.states,
    )
    probabilities = legacy.epsilon_greedy_probabilities(
        runtime_state.main,
        encoded,
        trajectory.masks,
        actions,
        epsilon=epsilon,
    )
    result = trajectory.environment.step(actions, trajectory.env_rng)
    outcome = trajectory.environment.last_outcome
    next_encoded = runtime_state.main.encode_states(result.user_states)
    bundle = legacy._bundle(
        arm=arm,
        train_seed=runtime_state.main.train_seed,
        source="Main",
        policy_version=episode // max(
            int(runtime_state.main.config.target_update_every_episodes), 1
        ),
        episode=episode,
        step_index=step_index,
        encoded=encoded,
        actions=actions,
        outcome=outcome,
        next_encoded=next_encoded,
        masks=trajectory.masks,
        next_masks=result.action_masks,
        focal_user=None,
        specialist_rewards=None,
        probabilities=probabilities,
        provenance={"behavior": "Main_scalarized_epsilon_greedy", "source": "Main"},
    )
    legacy._admit_main_rows_exactly_as_baseline(runtime_state.main, bundle)
    trajectory.advance(result)
    return bundle, outcome, actions


def _collect_c1(
    runtime_state: _C2Runtime,
    *,
    arm: str,
    episode: int,
    step_index: int,
    epsilon: float,
    informed: bool,
    frozen_main: legacy.FrozenMainComparator,
    acrm_eta: float,
) -> tuple[AtomicBundle, Any, float]:
    trajectory = runtime_state.trajectories["C1"]
    if trajectory.states is None or trajectory.masks is None:
        raise RuntimeError("C1 trajectory is not reset")
    encoded = runtime_state.main.encode_states(trajectory.states)
    comparator_actions = legacy.main_greedy_actions(
        frozen_main, encoded, trajectory.masks
    )
    actions, probabilities = legacy.specialist_joint_actions(
        runtime_state.specialists["C1"],
        encoded,
        trajectory.masks,
        epsilon=epsilon,
        informed=informed,
    )
    comparator = trajectory.environment.environment.evaluate_actions(
        comparator_actions, trajectory.env_rng
    )
    result = trajectory.environment.step(actions, trajectory.env_rng)
    outcome = trajectory.environment.last_outcome
    next_encoded = runtime_state.main.encode_states(result.user_states)
    private_rewards = (
        legacy.acrm_rewards(
            outcome.reward_matrix[:, 0],
            comparator.reward_matrix[:, 0],
            eta=acrm_eta,
        )
        if informed
        else outcome.reward_matrix[:, 0].copy()
    )
    bundle = legacy._bundle(
        arm=arm,
        train_seed=runtime_state.main.train_seed,
        source="C1",
        policy_version=runtime_state.specialists["C1"].policy_version,
        episode=episode,
        step_index=step_index,
        encoded=encoded,
        actions=actions,
        outcome=outcome,
        next_encoded=next_encoded,
        masks=trajectory.masks,
        next_masks=result.action_masks,
        focal_user=None,
        specialist_rewards=private_rewards,
        probabilities=probabilities,
        provenance={
            "behavior": "Q1_specialist" if informed else "uniform_control",
            "acrm_enabled": bool(informed),
            "acrm_eta": float(acrm_eta) if informed else 0.0,
            "main_counterfactual_selected_before_outcome": True,
            "frozen_main_comparator_sha256": frozen_main.version_sha256,
            "comparator_block": episode,
        },
    )
    replay = runtime_state.replays["C1"]
    replay.push(bundle)
    loss, _sampled = runtime_state.specialists["C1"].update_from_replay(replay)
    trajectory.advance(result)
    return bundle, outcome, float(loss)


def _collect_c3(
    runtime_state: _C2Runtime,
    *,
    arm: str,
    episode: int,
    step_index: int,
    epsilon: float,
    informed: bool,
    frozen_main: legacy.FrozenMainComparator,
) -> tuple[AtomicBundle | None, Any, float | None, str]:
    trajectory = runtime_state.trajectories["C3"]
    if (
        trajectory.states is None
        or trajectory.masks is None
        or trajectory.observation is None
    ):
        raise RuntimeError("C3 trajectory is not reset")
    commitment = getattr(trajectory, "_c3_option", None)
    if commitment is None:
        commitment = legacy.OptionCommitment()
        setattr(trajectory, "_c3_option", commitment)
    encoded = runtime_state.main.encode_states(trajectory.states)
    main_actions = legacy.main_greedy_actions(
        frozen_main, encoded, trajectory.masks
    )
    incumbents = legacy._incumbent_keys(trajectory.environment)
    supports = legacy.observable_c3_supports(
        states=trajectory.states,
        main_actions=main_actions,
        slot_tables=trajectory.observation.candidates.slot_tables,
        incumbents=incumbents,
    )
    decision = legacy.c3_relocation_decision(
        specialist=runtime_state.specialists["C3"],
        encoded=encoded,
        main_actions=main_actions,
        slot_tables=trajectory.observation.candidates.slot_tables,
        eligible_supports=supports,
        commitment=commitment,
        epsilon=epsilon,
        informed=informed,
        step_index=step_index,
    )
    result = trajectory.environment.step(decision.actions, trajectory.env_rng)
    outcome = trajectory.environment.last_outcome
    next_encoded = runtime_state.main.encode_states(result.user_states)
    termination = None
    if decision.focal_user is not None:
        termination = legacy.advance_option_after_execution(
            commitment,
            focal_served=bool(outcome.resolution.served[decision.focal_user]),
            done=bool(result.done),
        )
    identity = legacy._assert_single_focal_override(
        main_actions, decision.actions, decision.focal_user
    )
    bundle = legacy._bundle(
        arm=arm,
        train_seed=runtime_state.main.train_seed,
        source="C3",
        policy_version=runtime_state.specialists["C3"].policy_version,
        episode=episode,
        step_index=step_index,
        encoded=encoded,
        actions=decision.actions,
        outcome=outcome,
        next_encoded=next_encoded,
        masks=trajectory.masks,
        next_masks=result.action_masks,
        focal_user=decision.focal_user,
        specialist_rewards=None,
        probabilities=decision.probabilities,
        provenance={
            "behavior": "Q3_relocation" if informed else "uniform_relocation_control",
            "trigger": decision.trigger,
            "selected_key": decision.selected_key,
            "support_actions": decision.support_actions,
            "frozen_main_comparator_sha256": frozen_main.version_sha256,
            "comparator_block": episode,
            "selection_termination": decision.termination,
            "post_execution_termination": termination,
            "support_version": legacy.ROLE_SUPPORT_VERSION,
            "future_outcome_used_for_admission": False,
            "counterfactual_certificate_used_for_admission": False,
            "focal_override_identity": identity,
        },
    )
    loss: float | None = None
    if decision.focal_user is not None:
        replay = runtime_state.replays["C3"]
        replay.push(bundle)
        loss, _sampled = runtime_state.specialists["C3"].update_from_replay(replay)
    else:
        bundle = None
    trajectory.advance(result)
    return bundle, outcome, None if loss is None else float(loss), decision.trigger


def _build_c2_choice(
    runtime_state: _C2Runtime,
    *,
    config: C2EpisodeLoopConfig,
    trajectory: legacy.Trajectory,
    episode: int,
    epsilon: float,
    informed: bool,
    remaining_steps: int,
    timestamp_ns: int,
) -> tuple[c2_selection.C2PreparedForkSelection, list[dict[str, Any]]]:
    """Forecast a bounded candidate set and seal K0/K1/K>=2 selection."""

    if trajectory.states is None or trajectory.masks is None or trajectory.observation is None:
        raise RuntimeError("C2 trajectory is not reset")
    prepared_candidates: list[Any] = []
    diagnostics: list[dict[str, Any]] = []
    candidate_schedule: list[c2_selection.C2CandidateScheduleRow] = []
    if remaining_steps >= c2_core.HOLD_STEPS + 1:
        probe = c2_backend.C2ForecastBranch(
            wrapped=trajectory.environment,
            env_rng=trajectory.env_rng,
            mobility_rng=trajectory.mobility_rng,
            states=list(trajectory.states),
            masks=list(trajectory.masks),
            observation=trajectory.observation,
            trainer=runtime_state.main,
            focal_user=0,
            role="c2-v03-episode-anchor",
        )
        _main_actions, main_physical = c2_backend._main_actions(
            runtime_state.main, probe
        )
        departures = _departure_users(trajectory.environment, main_physical)
        for schedule_index, focal_user in enumerate(
            departures[: config.max_c2_candidates]
        ):
            started = __import__("time").perf_counter()
            prepared = None
            try:
                service = c2_backend.C2TemporalForkTrainerBackend(
                    wrapped=trajectory.environment,
                    states=list(trajectory.states),
                    masks=list(trajectory.masks),
                    observation=trajectory.observation,
                    env_rng=trajectory.env_rng,
                    trainer=runtime_state.main,
                    checkpoint_sha256=runtime_state.checkpoint_sha256,
                    environment_source_sha256=runtime_state.environment_source_sha256,
                    reward_source_sha256=runtime_state.reward_source_sha256,
                    evaluation_seed=episode,
                    focal_user=focal_user,
                )
                prepared = service.prepare_incumbent_hold(focal_user=focal_user)
                built = prepared.run_forecast()
                prepared_candidates.append(prepared)
                candidate_schedule.append(
                    c2_selection.candidate_schedule_row_from_prepared(
                        prepared,
                        schedule_index=schedule_index,
                    )
                )
                diagnostics.append(
                    {
                        "schedule_index": schedule_index,
                        "focal_user": focal_user,
                        "passed": bool(built.certificate.passed),
                        "candidate_key": list(prepared.candidate_key),
                        "failures": [failure.value for failure in built.certificate.failures],
                        "ee_surplus_bits": built.certificate.ee_surplus_bits,
                        "elapsed_s": __import__("time").perf_counter() - started,
                    }
                )
            except c2_backend.C2ForecastSupportRejection as error:
                candidate_schedule.append(
                    c2_selection.rejected_candidate_schedule_row(
                        schedule_index=schedule_index,
                        focal_user=focal_user,
                        candidate_key=(
                            None if prepared is None else prepared.candidate_key
                        ),
                        outcome=c2_selection.CANDIDATE_OUTCOME_SUPPORT_REJECTION,
                        rejection_reason=error.reason,
                    )
                )
                diagnostics.append(
                    {
                        "schedule_index": schedule_index,
                        "focal_user": focal_user,
                        "passed": False,
                        "candidate_key": (
                            None
                            if prepared is None
                            else list(prepared.candidate_key)
                        ),
                        "support_rejection": error.reason,
                        "forecast_offset": error.forecast_offset,
                        "affected_user": error.user,
                        "missing_physical_key": (
                            None
                            if error.physical_key is None
                            else list(error.physical_key)
                        ),
                        "elapsed_s": __import__("time").perf_counter() - started,
                    }
                )
            except Exception as error:
                raise c2_backend.C2BackendError(
                    f"C2 candidate {schedule_index} for focal user {focal_user} "
                    f"violated the runtime contract: {type(error).__name__}: {error}"
                ) from error
    mode = (
        c2_selection.CHOICE_MODE_Q2F
        if informed
        else c2_selection.CHOICE_MODE_RANDOM
    )
    choice = c2_selection.select_prepared_fork(
        prepared_candidates,
        candidate_schedule=candidate_schedule,
        behavior_rng=runtime_state.selection_rng,
        q2f=runtime_state.specialists["C2"] if len(prepared_candidates) >= 2 else None,
        epsilon=epsilon,
        mode=mode,
        preoutcome_timestamp_ns=timestamp_ns,
    )
    c2_selection.assert_prepared_selection_bound(choice)
    return choice, diagnostics


def _fallback_c2_step(
    runtime_state: _C2Runtime,
    *,
    trajectory: legacy.Trajectory,
) -> None:
    """Consume one ordinary C2 source step when no formal option is live."""

    if trajectory.states is None or trajectory.masks is None:
        raise RuntimeError("C2 trajectory is not reset")
    encoded = runtime_state.main.encode_states(trajectory.states)
    actions = legacy.main_greedy_actions(runtime_state.main, encoded, trajectory.masks)
    result = trajectory.environment.step(actions, trajectory.env_rng)
    trajectory.advance(result)


def _combined_main_update(
    runtime_state: _C2Runtime,
    *,
    c1_bundle: AtomicBundle | None,
    c3_bundle: AtomicBundle | None,
    episode: int,
    beta: float,
) -> Any:
    """Perform exactly one Main carrier call for the current logical step."""

    return c2_combined.update_main_with_combined_carrier(
        runtime_state.main,
        c1_bundle=c1_bundle,
        c3_bundle=c3_bundle,
        beta=beta,
        consumed_ledger=runtime_state.consumed_ledger,
        c2_option_ledger=runtime_state.c2_option_ledger,
        consumer_block_id=episode if c1_bundle is not None or c3_bundle is not None else None,
    )


def _run_treatment(
    *,
    runtime_state: _C2Runtime,
    config: C2EpisodeLoopConfig,
    output_dir: Path,
    acrm_eta: float | None = None,
    start_episode: int = 0,
    stop_episode: int | None = None,
) -> dict[str, Any]:
    if type(start_episode) is not int or not 0 <= start_episode < config.episodes:
        raise ValueError("start_episode must identify an unfinished absolute episode")
    end_episode = config.episodes if stop_episode is None else stop_episode
    if type(end_episode) is not int or not start_episode < end_episode <= config.episodes:
        raise ValueError(
            "stop_episode must be after start_episode and at most config.episodes"
        )
    acrm_eta = _bound_acrm_eta(config, acrm_eta)
    informed_c1, informed_c2, informed_c3 = ARM_LANES[config.arm]  # type: ignore[misc]
    active = ARM_ACTIVE_SOURCES[config.arm]
    main_environment = runtime_state.trajectories["Main"].environment
    episode_rows: list[dict[str, Any]] = []
    step_receipts: list[dict[str, Any]] = []
    c2_diagnostics: list[dict[str, Any]] = []
    c2_option_audits: list[dict[str, Any]] = []
    periodic_checkpoints: list[dict[str, Any]] = []
    run_telemetry = c2_telemetry.C2RunTelemetry()

    for episode in range(start_episode, end_episode):
        episode_telemetry = c2_telemetry.C2RunTelemetry()
        epsilon = runtime_state.main.epsilon(episode)
        frozen_main = legacy.FrozenMainComparator.from_main(runtime_state.main)
        # C2 forecasts use the current online Main policy at this collection
        # block, not the initial checkpoint forever.  Bind every anchor to the
        # exact current network bytes before any update in this episode.
        runtime_state.checkpoint_sha256 = _network_digest(runtime_state.main)
        for trajectory in runtime_state.trajectories.values():
            trajectory.reset()
            if trajectory is runtime_state.trajectories["C3"]:
                setattr(trajectory, "_c3_option", legacy.OptionCommitment())
        c2_trajectory = runtime_state.trajectories["C2"]
        c2_consumed_steps = 0
        # Keep the bounded smoke deterministic and affordable: at most one
        # nonempty candidate schedule is sealed per episode.  Empty reset
        # frames advance by Main fallback and retry; after a real K0/K1/K>=2
        # candidate schedule, later source slots use ordinary one-step fallback
        # until the episode clock is exhausted.
        c2_option_attempted = False
        episode_reward = np.zeros(3, dtype=np.float64)
        option_count = 0
        c2_admitted_count = 0
        c2_updated_count = 0

        for step_index in range(main_environment.config.steps_per_episode):
            main_bundle, main_outcome, _main_actions = _main_source_step(
                runtime_state,
                arm=config.arm,
                episode=episode,
                step_index=step_index,
                epsilon=epsilon,
            )
            episode_reward += main_outcome.reward_matrix.sum(axis=0)
            run_telemetry.observe_main(main_outcome)
            episode_telemetry.observe_main(main_outcome)
            c1_bundle = None
            c3_bundle = None
            if "C1" in active:
                c1_bundle, _c1_outcome, _c1_loss = _collect_c1(
                    runtime_state,
                    arm=config.arm,
                    episode=episode,
                    step_index=step_index,
                    epsilon=epsilon,
                    informed=bool(informed_c1),
                    frozen_main=frozen_main,
                    acrm_eta=acrm_eta,
                )
            if "C3" in active:
                c3_bundle, _c3_outcome, _c3_loss, _c3_trigger = _collect_c3(
                    runtime_state,
                    arm=config.arm,
                    episode=episode,
                    step_index=step_index,
                    epsilon=epsilon,
                    informed=bool(informed_c3),
                    frozen_main=frozen_main,
                )

            c2_receipt = None
            formal_c2_committed = False
            if (
                "C2" in active
                and c2_consumed_steps < main_environment.config.steps_per_episode
                # A reset frame has no incumbent association.  Prime the C2
                # trajectory with one ordinary source step before trying to
                # construct a detached-Main handover candidate; otherwise
                # every episode is permanently K=0.
                and c2_consumed_steps > 0
                and not c2_option_attempted
            ):
                remaining = main_environment.config.steps_per_episode - c2_consumed_steps
                # Main may have been updated by the preceding priming source
                # step (or by a prior carrier in this block).  Refresh the
                # network authority at the exact pre-forecast boundary so a
                # candidate can never be certified against an episode-start
                # policy snapshot.
                runtime_state.checkpoint_sha256 = _network_digest(runtime_state.main)
                choice, candidate_rows = _build_c2_choice(
                    runtime_state,
                    config=config,
                    trajectory=c2_trajectory,
                    episode=episode,
                    epsilon=epsilon,
                    informed=bool(informed_c2),
                    remaining_steps=remaining,
                    timestamp_ns=episode * 1_000_000 + step_index,
                )
                # A reset frame can have no detached-Main departure.  That is
                # not an attempted candidate schedule: advance one fallback
                # step and retry at the next pre-outcome boundary.  Once at
                # least one focal candidate was actually inspected (pass or
                # fail), freeze the one-schedule-per-episode budget.
                c2_option_attempted = bool(candidate_rows)
                support_count = len(choice.receipt.support)
                run_telemetry.observe_schedule(
                    candidate_rows,
                    support_count=support_count,
                )
                episode_telemetry.observe_schedule(
                    candidate_rows,
                    support_count=support_count,
                )
                c2_diagnostics.append(
                    {
                        "episode": episode,
                        "step": step_index,
                        "candidate_rows": candidate_rows,
                        "choice_class": (
                            "K0"
                            if not choice.receipt.support
                            else "K1"
                            if len(choice.receipt.support) == 1
                            else "K>=2"
                        ),
                        "selection_receipt_sha256": choice.receipt.receipt_sha256,
                        "candidate_schedule_sha256": (
                            choice.receipt.candidate_schedule_sha256
                        ),
                        "candidate_schedule_size": (
                            choice.receipt.candidate_schedule_size
                        ),
                    }
                )
                if choice.receipt.support:
                    c2_training_step.assert_real_candidate_main_identity(
                        choice,
                        runtime_state.main,
                    )
                holder: dict[str, Any] = {}

                def _runner(prepared: Any, **kwargs: Any) -> Any:
                    unit = c2_option_runner.commit_prepared_option(prepared, **kwargs)
                    holder["unit"] = unit
                    return unit

                c2_receipt = c2_training_step.run_c2_training_step(
                    choice,
                    specialist=(
                        runtime_state.specialists["C2"]
                        if choice.receipt.support
                        else None
                    ),
                    main=runtime_state.main if choice.receipt.support else None,
                    beta=config.beta,
                    discount_factor=float(runtime_state.main.config.discount_factor),
                    block_id=episode,
                    c2_option_ledger=(
                        runtime_state.c2_option_ledger
                        if choice.receipt.support
                        else None
                    ),
                    transaction_ledger=(
                        runtime_state.transaction_ledger
                        if choice.receipt.support
                        else None
                    ),
                    consumed_ledger=runtime_state.consumed_ledger,
                    c1_bundle=c1_bundle,
                    c3_bundle=c3_bundle,
                    runner_fn=_runner,
                )
                unit = holder.get("unit")
                option_live_consumed = unit is not None
                if unit is not None:
                    # ``commit_prepared_option`` advances the live C2 wrapper
                    # through the opening, H=3 hold/release steps.  The
                    # outer trajectory must consume that exact successor;
                    # otherwise the next source slot replays the stale
                    # opening state and its incumbent ledger diverges from
                    # the environment.  Read raw successor states/masks from
                    # the live outcome, never from forecast payloads.
                    _advance_from_outcome(c2_trajectory)
                    c2_consumed_steps += len(unit.committed_payloads)
                    option_count += 1
                    # Admission only means that the real option produced a
                    # valid learning item.  During replay warm-up the joint
                    # transaction deliberately performs neither the Q2F nor
                    # the Main optimizer step, so it must not suppress the
                    # ordinary C1/C3 (or baseline) Main carrier for this
                    # logical step.  Only a durable joint commit owns the
                    # single Main update slot.
                    formal_c2_committed = bool(c2_receipt.joint_committed)
                    c2_admitted_count += int(c2_receipt.admitted)
                    c2_updated_count += int(c2_receipt.updated)
                    run_telemetry.observe_execution(c2_receipt, unit)
                    episode_telemetry.observe_execution(c2_receipt, unit)
                    c2_option_audits.append(
                        _c2_option_audit(
                            unit,
                            c2_receipt,
                            episode=episode,
                            step_index=step_index,
                        )
                    )
                # A real terminal option may be non-admitted, but its one
                # (or more) live payloads were already consumed.  Only K=0
                # needs the ordinary one-step Main fallback; never append a
                # fifth step to a live option that returned no learning item.
                if not option_live_consumed:
                    _fallback_c2_step(runtime_state, trajectory=c2_trajectory)
                    c2_consumed_steps += 1
            elif "C2" in active and c2_consumed_steps < main_environment.config.steps_per_episode:
                _fallback_c2_step(runtime_state, trajectory=c2_trajectory)
                c2_consumed_steps += 1
            elif "C2" not in active and c2_consumed_steps < main_environment.config.steps_per_episode:
                # Keep the disabled source trajectory matched to the episode
                # clock for diagnostics; it never enters a specialist ledger.
                _fallback_c2_step(runtime_state, trajectory=c2_trajectory)
                c2_consumed_steps += 1

            if formal_c2_committed:
                carrier_receipt = None
            else:
                carrier_receipt = _combined_main_update(
                    runtime_state,
                    c1_bundle=c1_bundle,
                    c3_bundle=c3_bundle,
                    episode=episode,
                    beta=config.beta,
                )
            step_receipts.append(
                {
                    "episode": episode,
                    "step": step_index,
                    "main_bundle_id": main_bundle.bundle_id,
                    "main_replay_rows": len(runtime_state.main.replay),
                    "c2_training": None if c2_receipt is None else asdict(c2_receipt),
                    "main_carrier": (
                        None if carrier_receipt is None else asdict(carrier_receipt)
                    ),
                    "main_update_calls": 1,
                    "c2_environment_steps_consumed": c2_consumed_steps,
                    "formal_c2_owned_main_update": formal_c2_committed,
                }
            )

        if (episode + 1) % int(runtime_state.main.config.target_update_every_episodes) == 0:
            runtime_state.main.sync_targets()
            for specialist in runtime_state.specialists.values():
                specialist.sync_target()
        episode_rows.append(
            {
                "episode": episode,
                "epsilon": epsilon,
                "main_source_reward_sum": episode_reward.tolist(),
                "main_steps": main_environment.config.steps_per_episode,
                "c2_environment_steps": c2_consumed_steps,
                "c2_options": option_count,
                "c2_admitted_options": c2_admitted_count,
                "c2_updated_options": c2_updated_count,
                "active_sources": sorted(active),
                "frozen_main_comparator_sha256": frozen_main.version_sha256,
                "telemetry": episode_telemetry.snapshot(),
            }
        )
        episodes_completed = episode + 1
        if episodes_completed % int(config.checkpoint_every) == 0:
            periodic_checkpoints.append(
                _save_periodic_checkpoint(
                    runtime_state,
                    output_dir,
                    episodes_completed=episodes_completed,
                )
            )
            _save_runtime_state(
                output_dir / "resume" / "latest-c2-v03-training-state.pt",
                runtime_state,
                episode=episodes_completed,
            )

    final_checkpoint = output_dir / "final-checkpoint.pt"
    runtime_state.main.save_checkpoint(
        final_checkpoint,
        episode=end_episode - 1,
        checkpoint_kind=(
            "final-episode-policy"
            if end_episode == config.episodes
            else "bounded-segment-end-policy"
        ),
        include_optimizers=True,
    )
    carrier_state = output_dir / "carrier-state.pt"
    _save_runtime_state(carrier_state, runtime_state, episode=end_episode)
    _write_json(output_dir / "episode-logs.json", episode_rows)
    _write_json(output_dir / "c2-training-receipts.json", c2_diagnostics)
    option_audit_path = output_dir / "c2-option-chronology-audits.json"
    _write_json(option_audit_path, c2_option_audits)
    _write_json(output_dir / "main-update-receipts.json", step_receipts)
    telemetry_path = output_dir / "run-telemetry.json"
    telemetry_payload = run_telemetry.snapshot()
    _write_json(telemetry_path, telemetry_payload)
    return {
        "dispatch": "C2-V0.3-formal-selection-training-step-joint-transaction",
        "episodes": config.episodes,
        "start_episode": int(start_episode),
        "episodes_executed": int(end_episode - start_episode),
        "episodes_completed": int(end_episode),
        "artifact_scope": (
            "complete_run"
            if start_episode == 0 and end_episode == config.episodes
            else "bounded_initial_segment"
            if start_episode == 0
            else "resume_segment_only"
        ),
        "checkpoint": str(final_checkpoint),
        "checkpoint_sha256": _sha256_file(final_checkpoint),
        "carrier_state": str(carrier_state),
        "carrier_state_sha256": _sha256_file(carrier_state),
        "periodic_checkpoints": periodic_checkpoints,
        "periodic_checkpoint_count": len(periodic_checkpoints),
        "checkpoint_every_episodes": config.checkpoint_every,
        "active_sources": sorted(active),
        "c2_option_ledger_count": len(runtime_state.c2_option_ledger),
        "c2_option_chronology_audit_count": len(c2_option_audits),
        "c2_option_chronology_audit_path": str(option_audit_path),
        "c2_option_chronology_audit_sha256": _sha256_file(option_audit_path),
        "joint_transaction_count": len(runtime_state.transaction_ledger),
        "consumed_bundle_count": len(runtime_state.consumed_ledger),
        "episode_rows": episode_rows,
        "telemetry": telemetry_payload,
        "telemetry_path": str(telemetry_path),
        "telemetry_sha256": _sha256_file(telemetry_path),
        "mechanism_authority": _mechanism_authority(
            environment_source_sha256=runtime_state.environment_source_sha256
        ),
        "claim_ceiling": CLAIM_CEILING,
    }


def run_c2_v03_episode_loop(
    *,
    config: C2EpisodeLoopConfig,
    output_dir: Path,
    archive: Any,
    trainer_config: Any,
    acrm_eta: float | None = None,
    c1_corpus_manifest: Path | None = None,
    resume_state: Path | None = None,
    stop_episode: int | None = None,
) -> dict[str, Any]:
    """Run one bounded B000/treatment arm with formal C2 integration."""

    output_dir = Path(output_dir).expanduser().resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    if config.arm == "B000" and c1_corpus_manifest is not None:
        raise ValueError("baseline cannot consume a C1 EXP corpus")
    acrm_eta = _bound_acrm_eta(config, acrm_eta)
    canonical_trainer_config = _canonical_trainer_config(
        trainer_config, field="trainer_config"
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_run_journal(
        output_dir,
        status="running",
        config=config,
        trainer_config=canonical_trainer_config,
    )
    try:
        if config.arm == "B000":
            if resume_state is not None:
                raise ValueError(
                    "C2 V0.3 resume_state is treatment-only; use the canonical "
                    "Main trainer resume path for B000"
                )
            if stop_episode is not None:
                raise ValueError(
                    "C2 V0.3 stop_episode is treatment-only; use the canonical "
                    "Main trainer checkpoint callback for B000"
                )
            # Keep the baseline on the unchanged trainer seam.  The transparent
            # environment observer reads canonical outcomes after each real
            # step without changing actions, RNG consumption, replay, or
            # optimizer calls.
            result = _run_baseline_with_telemetry(
                output_dir=output_dir,
                archive=archive,
                trainer_config=trainer_config,
                users=config.users,
                train_seed=config.train_seed,
                env_seed=config.env_seed,
                mobility_seed=config.mobility_seed,
                checkpoint_every=config.checkpoint_every,
            )
        else:
            runtime_state = _make_runtime(
                config=config,
                archive=archive,
                trainer_config=trainer_config,
                output_dir=output_dir,
            )
            c1_prefill = None
            if c1_corpus_manifest is not None:
                manifest = Path(c1_corpus_manifest).expanduser().resolve()
                c1_corpus = legacy.load_verified_c1_corpus(
                    manifest,
                    expected_state_dim=runtime_state.main.state_dim,
                    expected_action_dim=runtime_state.main.action_dim,
                    tle_root=archive.root,
                )
                lanes = ARM_LANES[config.arm]
                if lanes is None:  # pragma: no cover - baseline rejected above
                    raise RuntimeError("treatment arm unexpectedly lacks Catfish lanes")
                c1_prefill = legacy._prefill_c1(
                    specialist=runtime_state.specialists["C1"],
                    replay=runtime_state.replays["C1"],
                    informed=bool(lanes[0]),
                    corpus=c1_corpus,
                )
            start_episode = 0
            resume_receipt = None
            if resume_state is not None:
                resume_path = Path(resume_state).expanduser().resolve()
                start_episode = load_c2_v03_runtime_state(
                    resume_path,
                    runtime_state,
                    config=config,
                )
                if start_episode >= config.episodes:
                    raise ValueError("resume snapshot already completed the requested run")
                resume_receipt = {
                    "path": str(resume_path),
                    "sha256": _sha256_file(resume_path),
                    "episodes_completed": int(start_episode),
                    "artifact_scope": "new continuation segment",
                }
            result = _run_treatment(
                runtime_state=runtime_state,
                config=config,
                output_dir=output_dir,
                acrm_eta=acrm_eta,
                start_episode=start_episode,
                stop_episode=stop_episode,
            )
            if c1_prefill is not None:
                result["c1_prefill"] = copy.deepcopy(c1_prefill)
            if resume_receipt is not None:
                result["resume_source"] = resume_receipt
    except BaseException as error:
        _write_run_journal(
            output_dir,
            status="failed",
            config=config,
            trainer_config=canonical_trainer_config,
            error=error,
        )
        raise
    if not isinstance(result, dict):
        result = dict(result)
    if "mechanism_authority" not in result:
        result["mechanism_authority"] = _mechanism_authority()
    result["trainer_config"] = copy.deepcopy(canonical_trainer_config)
    result["acrm_eta"] = acrm_eta
    _write_run_journal(
        output_dir,
        status="complete",
        config=config,
        trainer_config=canonical_trainer_config,
        result=result,
    )
    return result


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=SUPPORTED_ARMS, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--train-seed", type=int, required=True)
    parser.add_argument("--env-seed", type=int, required=True)
    parser.add_argument("--mobility-seed", type=int, required=True)
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--max-c2-candidates", type=int, default=9)
    parser.add_argument("--learning-rate", type=float, default=legacy.DEFAULT_LEARNING_RATE)
    parser.add_argument("--acrm-eta", type=float, default=legacy.DEFAULT_ACRM_ETA)
    parser.add_argument("--prereg", type=Path, default=legacy.CANONICAL_PREREG)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument(
        "--resume-state",
        type=Path,
        help=(
            "optional C2 V0.3 episode-boundary state; writes a new continuation "
            "segment and never overwrites the source run"
        ),
    )
    parser.add_argument(
        "--stop-after-episodes",
        type=int,
        help=(
            "bounded smoke only: close a normal episode-boundary segment at "
            "this absolute completed-episode count"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    if args.episodes < 1 or args.users < 1:
        raise ValueError("--episodes and --users must be positive")
    if args.episodes > MAX_DEVELOPMENT_EPISODES:
        raise ValueError(
            "this append-only runner is bounded to at most "
            f"{MAX_DEVELOPMENT_EPISODES} developmental episodes; use a reviewed "
            "long-run launcher after the smoke gate"
        )
    prereg, archive, authority = legacy._canonical_ephemeris_authority(
        args.prereg, args.tle_root
    )
    config = C2EpisodeLoopConfig(
        arm=args.arm,
        episodes=args.episodes,
        users=args.users,
        train_seed=args.train_seed,
        env_seed=args.env_seed,
        mobility_seed=args.mobility_seed,
        checkpoint_every=args.checkpoint_every,
        max_c2_candidates=args.max_c2_candidates,
        acrm_eta=args.acrm_eta,
    )
    trainer_config = legacy._short_config(
        prereg,
        arm=args.arm,
        episodes=args.episodes,
        epsilon_decay_episodes=max(1, args.episodes - 2),
        target_update_every=2,
        learning_rate=args.learning_rate,
    )
    result = run_c2_v03_episode_loop(
        config=config,
        output_dir=args.output_dir,
        archive=archive,
        trainer_config=trainer_config,
        resume_state=args.resume_state,
        stop_episode=args.stop_after_episodes,
    )
    status = {
        "schema": SCHEMA,
        "status": "complete",
        "arm": args.arm,
        "label": ARM_LABELS[args.arm],
        "config": asdict(config),
        "authority": authority,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
        },
        "trainer_config": _canonical_trainer_config(
            trainer_config, field="trainer_config"
        ),
        "result": result,
        "claim_ceiling": CLAIM_CEILING,
    }
    _write_json(Path(args.output_dir).expanduser().resolve() / "status.json", status)
    print(Path(args.output_dir).expanduser().resolve() / "status.json")
    return 0


__all__ = [
    "ARM_ACTIVE_SOURCES",
    "ARM_LABELS",
    "ARM_LANES",
    "C2EpisodeLoopConfig",
    "CLAIM_CEILING",
    "MAX_DEVELOPMENT_EPISODES",
    "RUNTIME_STATE_FORMAT_VERSION",
    "RUNTIME_STATE_SCHEMA",
    "SCHEMA",
    "SUPPORTED_ARMS",
    "load_c2_v03_runtime_state",
    "run_c2_v03_episode_loop",
]


if __name__ == "__main__":
    raise SystemExit(main())
