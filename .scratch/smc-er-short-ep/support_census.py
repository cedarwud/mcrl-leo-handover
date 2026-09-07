#!/usr/bin/env python3
"""Run the frozen pre-outcome V0.2 observable-support census.

This is a premise screen, not a training or efficacy experiment.  It loads
the sealed 9000-episode baseline Main checkpoint as a detached greedy policy,
draws only from the canonical TRAIN sampler, and counts whether the frozen
V0.2 C2/C3 predicates expose at least two current choices.  Main's selected
action is executed only to advance the real environment; rewards, successor
outcomes, counterfactuals, forecasts, and specialist data are never passed
to either eligibility predicate.

The command deliberately verifies every hash named by the V0.2 freeze before
touching the checkpoint or the TLE archive.  A scientifically valid census
that misses a role's pre-registered floor writes a ``NO_GO`` receipt and exits
successfully.  Malformed or hash-drifted authority is a command error.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = REPO / "src"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.action_contract import Association, NUM_ACTIONS  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.ephemeris import (  # noqa: E402
    TRAIN,
    BlockAlternatingSplit,
    EpisodeStartSampler,
)
from mcrl.env.mobility import MobilityConfig  # noqa: E402
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver  # noqa: E402
from mcrl.env.step import StepEnvironment  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.state_encoding import state_dim_for  # noqa: E402
from mcrl.runtime.trainer_env import TrainerEnvironment  # noqa: E402
from mcrl.runtime.trainer_spec import TrainerConfig  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from smc_er_roles import (  # noqa: E402
    main_greedy_actions,
    observable_c2_supports,
    observable_c3_supports,
)


FREEZE_SCHEMA = "multi-catfish-mcrl-v0.2-observable-support-freeze-v1"
FREEZE_STATUS = "FROZEN_BEFORE_SUPPORT_CENSUS"
PUBLIC_METHOD_NAME = "Multi-Catfish MCRL"
SUPPORT_VERSION = "V0.2_OBSERVABLE_ELIGIBILITY"
CENSUS_SCHEMA = "multi-catfish-mcrl-v0.2-support-census-v2"
TLE_ROOT_BINDING = "runtime_argument"
FREEZE_PATH = REPO / "docs" / "CATFISH-V0.2-OBSERVABLE-SUPPORT-FREEZE-2026-08-28.json"
EXPECTED_SPEC_SCHEMA = "Multi-Catfish MCRL V0.2 Observable-Support Specification"
FROZEN_PARTITION_LABEL = "TRAIN"
EXPECTED_USERS = 100
EXPECTED_STATE_DIM = state_dim_for(NUM_ACTIONS)
EXPECTED_ACTION_DIM = NUM_ACTIONS
EXPECTED_CHECKPOINT_EPISODE = 8999
EXPECTED_CHECKPOINT_EPISODES = 9000
EXPECTED_CHECKPOINT_KIND = "final-episode-policy"
EXPECTED_PAIR_COUNT = 3
EXPECTED_EPISODES_PER_PAIR = 10
EXPECTED_STEPS_PER_EPISODE = 10
EXPECTED_LOGICAL_STEPS = 300
EXPECTED_FLOOR_FRACTION = 0.1
EXPECTED_FLOOR_STEPS = 30
EXPECTED_SEED_PAIRS: tuple[tuple[int, int], ...] = (
    (2026082811, 2026082821),
    (2026082812, 2026082822),
    (2026082813, 2026082823),
)


class CensusAuthorityError(RuntimeError):
    """The requested census cannot run under the sealed authority."""


@dataclass(frozen=True)
class CensusAuthority:
    """Validated freeze, checkpoint, preregistration, and TLE inputs."""

    freeze_path: Path
    freeze_sha256: str
    freeze: Mapping[str, Any]
    spec_path: Path
    spec_sha256: str
    implementation_hashes: Mapping[str, str]
    test_hashes: Mapping[str, str]
    census_implementation_hashes: Mapping[str, str]
    c1_corpus_path: Path
    c1_corpus_sha256: str
    prereg_path: Path
    prereg_sha256: str
    checkpoint_path: Path
    checkpoint_sha256: str
    checkpoint_payload: Any
    archive: TleArchive
    ephemeris: Mapping[str, Any]
    tle_root: Path
    tle_file_set_sha256: str
    census: Mapping[str, Any]


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 for one file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise CensusAuthorityError(f"{label} must be a 64-character SHA-256")
    lowered = value.lower()
    if lowered != value or any(char not in "0123456789abcdef" for char in value):
        raise CensusAuthorityError(f"{label} must be lowercase hexadecimal SHA-256")
    return value


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CensusAuthorityError(f"cannot read {label}: {path}") from error
    if not isinstance(payload, dict):
        raise CensusAuthorityError(f"{label} must be a JSON object")
    return payload


def _repo_file(raw: Any, *, label: str) -> Path:
    """Resolve a freeze-owned path without permitting path escape."""

    if not isinstance(raw, str) or not raw:
        raise CensusAuthorityError(f"{label} path is missing")
    candidate = Path(raw)
    resolved = (candidate if candidate.is_absolute() else REPO / candidate).resolve()
    try:
        resolved.relative_to(REPO.resolve())
    except ValueError as error:
        raise CensusAuthorityError(f"{label} path escapes the repository") from error
    return resolved


def _repo_relative_posix(path: Path, *, label: str) -> str:
    """Encode one already-validated authority file without checkout coupling."""

    resolved = Path(path).expanduser().resolve()
    try:
        relative = resolved.relative_to(REPO.resolve())
    except ValueError as error:
        raise CensusAuthorityError(f"{label} is outside the repository") from error
    if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise CensusAuthorityError(f"{label} is not a canonical repository-relative path")
    return relative.as_posix()


def _assert_file_hash(path: Path, expected: Any, *, label: str) -> str:
    expected_digest = _digest(expected, label=f"{label} expected hash")
    if not path.is_file():
        raise CensusAuthorityError(f"{label} is missing: {path}")
    actual = sha256_file(path)
    if actual != expected_digest:
        raise CensusAuthorityError(
            f"{label} hash mismatch: expected {expected_digest}, got {actual}"
        )
    return actual


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CensusAuthorityError(f"{label} must be a JSON object")
    return value


def _validate_census_block(raw: Any) -> Mapping[str, Any]:
    census = _mapping(raw, label="support_census")
    if census.get("partition") != FROZEN_PARTITION_LABEL:
        raise CensusAuthorityError("support census must use the TRAIN partition")
    if census.get("episodes_per_seed_pair") != EXPECTED_EPISODES_PER_PAIR:
        raise CensusAuthorityError("support census episodes_per_seed_pair drifted")
    if census.get("steps_per_episode") != EXPECTED_STEPS_PER_EPISODE:
        raise CensusAuthorityError("support census steps_per_episode drifted")
    if census.get("logical_steps_total") != EXPECTED_LOGICAL_STEPS:
        raise CensusAuthorityError("support census logical step count drifted")
    raw_pairs = census.get("environment_mobility_seed_pairs")
    if raw_pairs != [list(pair) for pair in EXPECTED_SEED_PAIRS]:
        raise CensusAuthorityError("support census seed pairs drifted")
    if census.get("minimum_exposed_step_fraction_per_role") != EXPECTED_FLOOR_FRACTION:
        raise CensusAuthorityError("support census floor fraction drifted")
    if census.get("minimum_exposed_steps_per_role") != EXPECTED_FLOOR_STEPS:
        raise CensusAuthorityError("support census floor step count drifted")
    if census.get("reward_or_successor_used_for_eligibility") is not False:
        raise CensusAuthorityError(
            "support census authority permits reward/successor leakage"
        )
    return census


def _validate_checkpoint_payload(payload: Any) -> None:
    """Ensure the named artifact is the detached final 9000EP Main policy."""

    for field in ("episode", "state_dim", "action_dim", "checkpoint_kind"):
        if not hasattr(payload, field):
            raise CensusAuthorityError(f"checkpoint payload has no {field}")
    if int(payload.episode) != EXPECTED_CHECKPOINT_EPISODE:
        raise CensusAuthorityError("baseline checkpoint is not episode 8999")
    if str(payload.checkpoint_kind) != EXPECTED_CHECKPOINT_KIND:
        raise CensusAuthorityError("baseline checkpoint is not final-episode-policy")
    if int(payload.state_dim) != EXPECTED_STATE_DIM:
        raise CensusAuthorityError("baseline checkpoint state dimension drifted")
    if int(payload.action_dim) != EXPECTED_ACTION_DIM:
        raise CensusAuthorityError("baseline checkpoint action dimension drifted")
    config = _mapping(getattr(payload, "trainer_config", None), label="checkpoint trainer_config")
    if config.get("episodes") != EXPECTED_CHECKPOINT_EPISODES:
        raise CensusAuthorityError("baseline checkpoint trainer episodes are not 9000")
    if config.get("method_family") != "MODQN-baseline":
        raise CensusAuthorityError("named checkpoint is not the baseline Main policy")


def validate_freeze_manifest(
    freeze_manifest: Path,
    *,
    tle_root: Path,
) -> CensusAuthority:
    """Validate the complete V0.2 freeze and return immutable run inputs.

    This function intentionally performs the hash and canonical-prereg checks
    before loading the baseline checkpoint.  The freeze is the authority for
    the run, not a descriptive label attached after an experiment.
    """

    freeze_path = Path(freeze_manifest).expanduser().resolve()
    if not freeze_path.is_file():
        raise CensusAuthorityError(f"freeze manifest is missing: {freeze_path}")
    freeze = _read_json(freeze_path, label="freeze manifest")
    if freeze.get("schema") != FREEZE_SCHEMA:
        raise CensusAuthorityError("freeze manifest has the wrong schema")
    if freeze.get("status") != FREEZE_STATUS:
        raise CensusAuthorityError("freeze manifest is not frozen before census")
    if freeze.get("public_method_name") != PUBLIC_METHOD_NAME:
        raise CensusAuthorityError("freeze public method name drifted")
    if freeze.get("support_version") != SUPPORT_VERSION:
        raise CensusAuthorityError("freeze support version drifted")
    if freeze.get("formal_training_authorized") is not False:
        raise CensusAuthorityError("formal training must remain unauthorized at census")

    spec = _mapping(freeze.get("spec"), label="spec")
    spec_path = _repo_file(spec.get("path"), label="spec")
    spec_sha256 = _assert_file_hash(spec_path, spec.get("sha256"), label="spec")
    # The title check catches a path/hash pair accidentally pointing at a
    # different document while remaining independent of prose wording below.
    spec_text = spec_path.read_text(encoding="utf-8")
    if not spec_text.startswith(f"# {EXPECTED_SPEC_SCHEMA}"):
        raise CensusAuthorityError("spec is not the V0.2 observable-support specification")

    implementation = _mapping(freeze.get("implementation"), label="implementation")
    implementation_hashes: dict[str, str] = {}
    for raw_path, raw_hash in implementation.items():
        path = _repo_file(raw_path, label=f"implementation {raw_path}")
        implementation_hashes[str(raw_path)] = _assert_file_hash(
            path, raw_hash, label=f"implementation {raw_path}"
        )
    required_implementation = {
        ".scratch/smc-er-short-ep/smc_er_core.py",
        ".scratch/smc-er-short-ep/smc_er_roles.py",
        ".scratch/smc-er-short-ep/run_short_ep.py",
        ".scratch/smc-er-short-ep/c1_exp_corpus.py",
        ".scratch/smc-er-short-ep/build_c1_exp_corpus.py",
    }
    if set(implementation_hashes) != required_implementation:
        raise CensusAuthorityError("freeze implementation input set drifted")

    tests = _mapping(freeze.get("tests"), label="tests")
    test_hashes: dict[str, str] = {}
    for raw_path, raw_hash in tests.items():
        path = _repo_file(raw_path, label=f"test {raw_path}")
        test_hashes[str(raw_path)] = _assert_file_hash(
            path, raw_hash, label=f"test {raw_path}"
        )
    required_tests = {
        ".scratch/smc-er-short-ep/test_smc_er_core.py",
        ".scratch/smc-er-short-ep/test_smc_er_roles.py",
        ".scratch/smc-er-short-ep/test_run_short_ep.py",
        ".scratch/smc-er-short-ep/test_c1_exp_corpus.py",
        ".scratch/smc-er-short-ep/test_build_c1_exp_corpus.py",
    }
    if set(test_hashes) != required_tests:
        raise CensusAuthorityError("freeze test input set drifted")

    census_implementation = _mapping(
        freeze.get("census_implementation"), label="census_implementation"
    )
    census_implementation_hashes: dict[str, str] = {}
    for raw_path, raw_hash in census_implementation.items():
        path = _repo_file(raw_path, label=f"census implementation {raw_path}")
        census_implementation_hashes[str(raw_path)] = _assert_file_hash(
            path, raw_hash, label=f"census implementation {raw_path}"
        )
    required_census_implementation = {
        ".scratch/smc-er-short-ep/support_census.py",
        ".scratch/smc-er-short-ep/test_support_census.py",
    }
    if set(census_implementation_hashes) != required_census_implementation:
        raise CensusAuthorityError("freeze census implementation set drifted")

    fixed_inputs = _mapping(freeze.get("fixed_inputs"), label="fixed_inputs")
    expected_tle_hash = _digest(
        fixed_inputs.get("tle_file_set_sha256"), label="fixed TLE file-set hash"
    )
    checkpoint_entry = _mapping(
        fixed_inputs.get("baseline_checkpoint"), label="baseline_checkpoint"
    )
    checkpoint_path = _repo_file(
        checkpoint_entry.get("path"), label="baseline checkpoint"
    )
    checkpoint_sha256 = _assert_file_hash(
        checkpoint_path,
        checkpoint_entry.get("sha256"),
        label="baseline checkpoint",
    )

    corpus_entry = _mapping(
        fixed_inputs.get("c1_exp_corpus_manifest"), label="c1_exp_corpus_manifest"
    )
    corpus_path = _repo_file(corpus_entry.get("path"), label="C1 EXP corpus manifest")
    _assert_file_hash(
        corpus_path,
        corpus_entry.get("sha256"),
        label="C1 EXP corpus manifest",
    )

    census = _validate_census_block(freeze.get("support_census"))
    if int(census["logical_steps_total"]) != (
        EXPECTED_PAIR_COUNT * EXPECTED_EPISODES_PER_PAIR * EXPECTED_STEPS_PER_EPISODE
    ):
        raise CensusAuthorityError("support census logical-step arithmetic drifted")

    prereg_path = Path(CANONICAL_PREREG).expanduser().resolve()
    if not prereg_path.is_file():
        raise CensusAuthorityError(f"canonical preregistration is missing: {prereg_path}")
    prereg_sha256 = sha256_file(prereg_path)
    if prereg_sha256 != CANONICAL_PREREG_BYTE_SHA256:
        raise CensusAuthorityError("canonical preregistration byte hash drifted")
    try:
        prereg = read_prereg(prereg_path)
        prereg.verify()
    except Exception as error:  # pragma: no cover - concrete error varies by prereg guard
        raise CensusAuthorityError("canonical preregistration failed verification") from error

    archive_path = Path(tle_root).expanduser().resolve()
    try:
        archive = TleArchive(archive_path)
        ephemeris = assert_ephemeris_matches_record(prereg, archive=archive)
    except Exception as error:  # pragma: no cover - concrete error varies by ephemeris guard
        raise CensusAuthorityError(
            "TLE archive does not satisfy the canonical preregistered ephemeris"
        ) from error
    if ephemeris.get("file_set_sha256") != expected_tle_hash:
        raise CensusAuthorityError(
            "TLE file-set hash mismatch: "
            f"expected {expected_tle_hash}, got {ephemeris.get('file_set_sha256')}"
        )
    if ephemeris.get("split", {}).get("train_files", 0) <= 0:
        raise CensusAuthorityError("canonical TRAIN partition is empty")

    try:
        checkpoint_payload = read_checkpoint(checkpoint_path, map_location="cpu")
    except Exception as error:  # pragma: no cover - concrete loader error varies
        raise CensusAuthorityError("baseline checkpoint could not be loaded") from error
    _validate_checkpoint_payload(checkpoint_payload)

    return CensusAuthority(
        freeze_path=freeze_path,
        freeze_sha256=sha256_file(freeze_path),
        freeze=freeze,
        spec_path=spec_path,
        spec_sha256=spec_sha256,
        implementation_hashes=implementation_hashes,
        test_hashes=test_hashes,
        census_implementation_hashes=census_implementation_hashes,
        c1_corpus_path=corpus_path,
        c1_corpus_sha256=sha256_file(corpus_path),
        prereg_path=prereg_path,
        prereg_sha256=prereg_sha256,
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=checkpoint_sha256,
        checkpoint_payload=checkpoint_payload,
        archive=archive,
        ephemeris=ephemeris,
        tle_root=archive_path,
        tle_file_set_sha256=expected_tle_hash,
        census=census,
    )


def _assert_authority_still_current(authority: CensusAuthority) -> None:
    """Reject a receipt if a freeze-owned source changed during execution."""

    _assert_file_hash(
        authority.freeze_path,
        authority.freeze_sha256,
        label="freeze manifest at census completion",
    )
    _assert_file_hash(
        authority.spec_path,
        authority.spec_sha256,
        label="spec at census completion",
    )
    for raw_path, expected in authority.implementation_hashes.items():
        _assert_file_hash(
            _repo_file(raw_path, label=f"implementation {raw_path}"),
            expected,
            label=f"implementation {raw_path} at census completion",
        )
    for raw_path, expected in authority.test_hashes.items():
        _assert_file_hash(
            _repo_file(raw_path, label=f"test {raw_path}"),
            expected,
            label=f"test {raw_path} at census completion",
        )
    for raw_path, expected in authority.census_implementation_hashes.items():
        _assert_file_hash(
            _repo_file(raw_path, label=f"census implementation {raw_path}"),
            expected,
            label=f"census implementation {raw_path} at census completion",
        )
    _assert_file_hash(
        authority.c1_corpus_path,
        authority.c1_corpus_sha256,
        label="C1 EXP corpus manifest at census completion",
    )
    _assert_file_hash(
        authority.checkpoint_path,
        authority.checkpoint_sha256,
        label="baseline checkpoint at census completion",
    )
    _assert_file_hash(
        authority.prereg_path,
        authority.prereg_sha256,
        label="canonical preregistration at census completion",
    )


def _config_from_checkpoint(payload: Any) -> TrainerConfig:
    config = dict(_mapping(payload.trainer_config, label="checkpoint trainer_config"))
    try:
        return TrainerConfig(**config)
    except (TypeError, ValueError) as error:
        raise CensusAuthorityError("baseline checkpoint trainer config is invalid") from error


def make_census_environment(
    archive: TleArchive,
    *,
    config: TrainerConfig,
    users: int = EXPECTED_USERS,
) -> TrainerEnvironment:
    """Construct the exact real-TLE TRAIN environment used by the census."""

    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=int(users))),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    if sampler.part != TRAIN:
        raise CensusAuthorityError("census sampler is not TRAIN")
    return TrainerEnvironment(StepEnvironment(driver, trainer=config), sampler)


def load_detached_main(
    authority: CensusAuthority,
    *,
    users: int = EXPECTED_USERS,
) -> tuple[MODQNTrainer, TrainerEnvironment]:
    """Load baseline Q networks with optimizers excluded and gradients off."""

    config = _config_from_checkpoint(authority.checkpoint_payload)
    environment = make_census_environment(
        authority.archive, config=config, users=users
    )
    main = MODQNTrainer(
        environment,
        config,
        train_seed=int(authority.checkpoint_payload.train_seed),
        env_seed=int(authority.checkpoint_payload.env_seed),
        mobility_seed=int(authority.checkpoint_payload.mobility_seed),
        device="cpu",
    )
    try:
        main.load_checkpoint(authority.checkpoint_path, load_optimizers=False)
    except Exception as error:  # pragma: no cover - concrete loader error varies
        raise CensusAuthorityError("baseline checkpoint failed to load into Main") from error
    for network in main.q_nets:
        network.eval()
        for parameter in network.parameters():
            parameter.requires_grad_(False)
    for network in main.target_nets:
        network.eval()
        for parameter in network.parameters():
            parameter.requires_grad_(False)
    return main, environment


def current_incumbents(environment: TrainerEnvironment) -> tuple[tuple[int, int] | None, ...]:
    """Read current physical incumbents from the environment's state seam."""

    raw = getattr(environment.environment, "_previous_association", None)
    if raw is None:
        raise CensusAuthorityError("environment does not expose current incumbents")
    result: list[tuple[int, int] | None] = []
    for association in raw:
        if isinstance(association, Association):
            result.append((int(association.norad_id), int(association.cell_id)))
        else:
            result.append(None)
    return tuple(result)


def _current_slot_tables(environment: TrainerEnvironment) -> Sequence[Any]:
    candidates = getattr(environment.environment, "_candidates", None)
    if candidates is None or not hasattr(candidates, "slot_tables"):
        raise CensusAuthorityError("environment does not expose current slot tables")
    return candidates.slot_tables


def _sha256_actions(actions: Sequence[int]) -> str:
    return hashlib.sha256(np.asarray(actions, dtype=np.int64).tobytes(order="C")).hexdigest()


def _step_record(
    *,
    pair_index: int,
    env_seed: int,
    mobility_seed: int,
    episode: int,
    step: int,
    main_actions: Sequence[int],
    c2_supports: Mapping[int, Sequence[int]],
    c3_supports: Mapping[int, Sequence[int]],
) -> dict[str, Any]:
    def role_record(supports: Mapping[int, Sequence[int]]) -> dict[str, Any]:
        sizes = [len(tuple(value)) for _, value in sorted(supports.items())]
        return {
            "exposed": bool(supports),
            "exposed_user_ids": [int(uid) for uid in sorted(supports)],
            "support_sizes": sizes,
            "support_count": len(sizes),
        }

    return {
        "pair_index": int(pair_index),
        "environment_seed": int(env_seed),
        "mobility_seed": int(mobility_seed),
        "episode": int(episode),
        "step": int(step),
        "main_actions_sha256": _sha256_actions(main_actions),
        "C2": role_record(c2_supports),
        "C3": role_record(c3_supports),
        "eligibility_inputs": {
            "current_state": True,
            "detached_main_greedy_action": True,
            "current_slot_tables": True,
            "current_physical_incumbents": True,
            "reward_used": False,
            "successor_outcome_used": False,
            "counterfactual_used": False,
            "forecast_used": False,
            "specialist_outcome_used": False,
        },
    }


def _role_summary(step_rows: Sequence[Mapping[str, Any]], role: str) -> dict[str, Any]:
    exposed_steps = sum(1 for row in step_rows if row[role]["exposed"])
    support_count = sum(int(row[role]["support_count"]) for row in step_rows)
    support_sizes = [
        int(size)
        for row in step_rows
        for size in row[role]["support_sizes"]
    ]
    total_steps = len(step_rows)
    return {
        "role": role,
        "logical_steps": total_steps,
        "exposed_steps": exposed_steps,
        "exposed_step_fraction": exposed_steps / total_steps if total_steps else 0.0,
        "exposed_support_count": support_count,
        "mean_exposed_support_size": (
            float(np.mean(support_sizes)) if support_sizes else 0.0
        ),
        "minimum_exposed_steps": EXPECTED_FLOOR_STEPS,
        "minimum_exposed_step_fraction": EXPECTED_FLOOR_FRACTION,
        "floor_pass": exposed_steps >= EXPECTED_FLOOR_STEPS,
    }


def _new_pair_summary(
    *,
    pair_index: int,
    env_seed: int,
    mobility_seed: int,
) -> dict[str, Any]:
    return {
        "pair_index": int(pair_index),
        "environment_seed": int(env_seed),
        "mobility_seed": int(mobility_seed),
        "partition": FROZEN_PARTITION_LABEL,
        "episodes": EXPECTED_EPISODES_PER_PAIR,
        "steps_per_episode": EXPECTED_STEPS_PER_EPISODE,
        "logical_steps": EXPECTED_EPISODES_PER_PAIR * EXPECTED_STEPS_PER_EPISODE,
    }


def run_census(
    authority: CensusAuthority,
    *,
    users: int = EXPECTED_USERS,
    main_factory: Any | None = None,
    environment_factory: Any | None = None,
    c2_support_fn: Any = observable_c2_supports,
    c3_support_fn: Any = observable_c3_supports,
) -> dict[str, Any]:
    """Execute exactly the frozen 300 logical pre-outcome steps.

    ``main_factory`` and ``environment_factory`` are narrow test seams.  The
    production defaults always use the detached checkpoint and real TRAIN
    environment validated by :func:`validate_freeze_manifest`.
    """

    config = _config_from_checkpoint(authority.checkpoint_payload)
    all_steps: list[dict[str, Any]] = []
    per_seed: list[dict[str, Any]] = []
    for pair_index, (env_seed, mobility_seed) in enumerate(EXPECTED_SEED_PAIRS):
        if environment_factory is None:
            environment = make_census_environment(
                authority.archive, config=config, users=users
            )
        else:
            environment = environment_factory(
                authority.archive, config=config, users=users
            )
        if main_factory is None:
            main, _main_environment = load_detached_main(authority, users=users)
        else:
            main = main_factory(authority, users=users, config=config)
        env_rng = np.random.default_rng(env_seed)
        mobility_rng = np.random.default_rng(mobility_seed)
        pair_steps: list[dict[str, Any]] = []

        for episode in range(EXPECTED_EPISODES_PER_PAIR):
            states, masks, _observation = environment.reset(env_rng, mobility_rng)
            for step in range(EXPECTED_STEPS_PER_EPISODE):
                encoded = main.encode_states(states)
                main_actions = main_greedy_actions(main, encoded, masks)
                slot_tables = _current_slot_tables(environment)
                incumbents = current_incumbents(environment)

                # These are the only eligibility calls.  No result from the
                # step below is available yet, and no reward/outcome object is
                # passed into either pure predicate.
                c2_supports = c2_support_fn(
                    states=states,
                    main_actions=main_actions,
                    slot_tables=slot_tables,
                    incumbents=incumbents,
                )
                c3_supports = c3_support_fn(
                    states=states,
                    main_actions=main_actions,
                    slot_tables=slot_tables,
                    incumbents=incumbents,
                )
                row = _step_record(
                    pair_index=pair_index,
                    env_seed=env_seed,
                    mobility_seed=mobility_seed,
                    episode=episode,
                    step=step,
                    main_actions=main_actions,
                    c2_supports=c2_supports,
                    c3_supports=c3_supports,
                )
                pair_steps.append(row)
                all_steps.append(row)

                # Execute the detached Main greedy vector only as a state
                # advance.  Deliberately discard the StepResult's reward and
                # outcome; its next observation is only the next current
                # state/table for the following pre-outcome decision.
                step_result = environment.step(main_actions, env_rng)
                if step < EXPECTED_STEPS_PER_EPISODE - 1:
                    states = list(step_result.user_states)
                    masks = list(step_result.action_masks)

        pair_summary = _new_pair_summary(
            pair_index=pair_index,
            env_seed=env_seed,
            mobility_seed=mobility_seed,
        )
        pair_summary["roles"] = {
            role: _role_summary(pair_steps, role) for role in ("C2", "C3")
        }
        pair_summary["steps"] = pair_steps
        per_seed.append(pair_summary)

    if len(all_steps) != EXPECTED_LOGICAL_STEPS:
        raise CensusAuthorityError(
            f"census executed {len(all_steps)} logical steps; expected {EXPECTED_LOGICAL_STEPS}"
        )
    aggregate_roles = {
        role: _role_summary(all_steps, role) for role in ("C2", "C3")
    }
    if isinstance(authority, CensusAuthority):
        _assert_authority_still_current(authority)
    status = "PASS" if all(row["floor_pass"] for row in aggregate_roles.values()) else "NO_GO"
    return {
        "schema": CENSUS_SCHEMA,
        "status": status,
        "support_version": SUPPORT_VERSION,
        "public_method_name": PUBLIC_METHOD_NAME,
        "partition": FROZEN_PARTITION_LABEL,
        "seed_pair_count": EXPECTED_PAIR_COUNT,
        "episodes_per_seed_pair": EXPECTED_EPISODES_PER_PAIR,
        "steps_per_episode": EXPECTED_STEPS_PER_EPISODE,
        "logical_steps": EXPECTED_LOGICAL_STEPS,
        "roles": aggregate_roles,
        "per_seed_pair": per_seed,
        "evidence_ceiling": (
            "Pre-outcome support census only: establishes observable role "
            "choice exposure, not donor usefulness, reward improvement, EE "
            "direction, or Chapter 5 efficacy."
        ),
        "eligibility_contract": {
            "reward_used": False,
            "successor_outcome_used": False,
            "counterfactual_used": False,
            "forecast_used": False,
            "specialist_outcome_used": False,
            "main_action_execution": "detached_greedy_only_for_state_advance",
        },
        "authority": {
            "path_binding": "repository_relative_posix_v1",
            "freeze_manifest": _repo_relative_posix(
                authority.freeze_path, label="freeze manifest"
            ),
            "freeze_manifest_sha256": authority.freeze_sha256,
            "spec": _repo_relative_posix(authority.spec_path, label="spec"),
            "spec_sha256": authority.spec_sha256,
            "implementation_sha256": dict(authority.implementation_hashes),
            "test_sha256": dict(authority.test_hashes),
            "census_implementation_sha256": dict(
                authority.census_implementation_hashes
            ),
            "c1_exp_corpus_manifest": _repo_relative_posix(
                authority.c1_corpus_path, label="C1 EXP corpus manifest"
            ),
            "c1_exp_corpus_manifest_sha256": authority.c1_corpus_sha256,
            "canonical_prereg": _repo_relative_posix(
                authority.prereg_path, label="canonical preregistration"
            ),
            "canonical_prereg_sha256": authority.prereg_sha256,
            "tle_root_binding": TLE_ROOT_BINDING,
            "tle_file_set_sha256": authority.tle_file_set_sha256,
            "tle_file_count": int(authority.ephemeris["archive"]["file_count"]),
            "baseline_checkpoint": _repo_relative_posix(
                authority.checkpoint_path, label="baseline checkpoint"
            ),
            "baseline_checkpoint_sha256": authority.checkpoint_sha256,
            "baseline_checkpoint_episode": EXPECTED_CHECKPOINT_EPISODE,
            "baseline_checkpoint_detached": True,
            "baseline_checkpoint_updated": False,
        },
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a deterministic receipt atomically."""

    path = Path(path).expanduser().resolve()
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


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--freeze-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        authority = validate_freeze_manifest(
            args.freeze_manifest,
            tle_root=args.tle_root,
        )
        receipt = run_census(authority)
        write_json(args.output, receipt)
    except CensusAuthorityError as error:
        print(f"support census authority error: {error}", file=sys.stderr)
        return 2
    print(Path(args.output).expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
