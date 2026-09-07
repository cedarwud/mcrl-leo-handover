#!/usr/bin/env python3
"""Run the scalarized-Main C2 persistence Stage-0 candidate gate.

This V2 adapter deliberately reuses the already audited physical-ID,
forecast, twin, branch, and metric machinery from the legacy C2 runner while
replacing its Q1-only Main policy at one explicit seam.  The legacy runner and
its sealed evidence are never edited or treated as V2 authority.  V2 is
evaluation-only: it does not update a learner, optimizer, replay buffer,
reward implementation, or Main checkpoint.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DESIGN_DIR = REPO / ".scratch" / "catfish-design-data"
SPEC = DESIGN_DIR / "C2-PERSISTENCE-SCALARIZED-STAGE0-CANDIDATE-SPEC-V2-2026-08-28.md"
METHOD = REPO / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md"
PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
CHECKPOINT = (
    REPO
    / "artifacts"
    / "training-2026-08-25-rerun01"
    / "main"
    / "final-checkpoint.pt"
)
LEGACY_RUNNER = HERE / "run_c2_stage0.py"
LEGACY_TEST = HERE / "test_c2_stage0.py"
V2_TEST = HERE / "test_c2_scalarized_stage0.py"
PROVENANCE_HELPER = DESIGN_DIR / "run_c3_disjoint_median_shadow.py"
CHECKPOINT_LOADER = REPO / "scripts" / "run_head_pivotality_probe.py"

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(DESIGN_DIR))


def _load_legacy_runner() -> Any:
    """Load the legacy module under a private name without importing it as V2."""

    import importlib.util

    name = "_smc_er_c2_legacy_stage0_for_v2"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    module_spec = importlib.util.spec_from_file_location(name, LEGACY_RUNNER)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("cannot load legacy C2 Stage-0 helper")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module


legacy = _load_legacy_runner()


# These are byte authorities, not tunable experiment parameters.  If any
# authority changes, a new closure and a new seed reveal are required.
EXPECTED_SPEC_SHA256 = (
    "a9e6ca763264c07d5079e2b989007b869fecb6520d0ae9a28ddb53071b835cd7"
)
EXPECTED_METHOD_SHA256 = (
    "0e67e6aa570158dd1433afe98d4992ed278db1cb5d586f6aff6680e0c7696d2e"
)
EXPECTED_PREREG_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)
EXPECTED_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
EXPECTED_ANALYSIS_CODE_SHA256 = (
    "4cfc7e3043453994fc0686c3bbfa14d9a95156aeabc578b26decb2f210603a2e"
)

OBJECTIVE_WEIGHTS = (0.5, 0.3, 0.2)
POLICY_MODE = "masked-greedy-scalarized-main"
SEED_SCHEMA = "smc-er-c2-scalarized-stage0-seeds-v2"
CLOSURE_SCHEMA = "smc-er-c2-scalarized-stage0-closure-v2"
OUTPUT_SCHEMA = "smc-er-c2-scalarized-stage0-result-v2"
SEED_NAMESPACE = "C2-SCALARIZED-STAGE0-V2"
SEED_COUNT = 5
ANCHOR_STEPS = tuple(range(6))
FOCAL_USERS_PER_STEP = 5
FOCAL_SCHEDULE_OFFSET = 220003
FREEZE_CLOSURE_FILENAME = "c2-scalarized-stage0-closure-v2.json"
FREEZE_DISJOINTNESS_FILENAME = "c2-scalarized-stage0-disjointness-v1.json"
FREEZE_SEED_FILENAME = "c2-scalarized-stage0-seeds-v2.json"
FREEZE_OUTPUT_FILENAMES = (
    FREEZE_CLOSURE_FILENAME,
    FREEZE_DISJOINTNESS_FILENAME,
    FREEZE_SEED_FILENAME,
)


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _value_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalise_test_stdout(value: str) -> str:
    """Remove pytest's wall-clock duration while retaining its test output."""

    return re.sub(r"in [0-9]+(?:\.[0-9]+)?s", "in <duration>s", value)


def _relative_repo_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"closure path is outside repository: {path}") from exc


def _validate_freeze_output_directory(path: Path) -> Path:
    """Resolve a freeze directory and reject repository-owned output paths."""

    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(REPO.resolve())
    except ValueError:
        return resolved
    raise RuntimeError(
        "freeze output directory must be outside the repository"
    )


def _canonical_freeze_paths(output_dir: Path) -> tuple[Path, ...]:
    directory = output_dir.expanduser().resolve()
    return tuple(directory / name for name in FREEZE_OUTPUT_FILENAMES)


def _dependency_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {"python": platform.python_version()}
    for name in ("numpy", "torch", "sgp4"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _frozen_tle_hashes(prereg_path: Path) -> dict[str, str]:
    payload = json.loads(prereg_path.read_text(encoding="utf-8"))
    rows = payload["sections"]["ephemeris"]["frozen_files"]
    return {str(row["file"]): str(row["sha256"]) for row in rows}


def required_closure_files() -> set[str]:
    """Return the exact V2 files which must be sealed before seed reveal."""

    # The V2 adapter delegates physical execution to the legacy helper, the
    # checkpoint loader, and the reviewed source bundle.  Pin every delegated
    # file explicitly so a helper change cannot be hidden behind a new V2
    # wrapper hash.
    paths: set[Path] = {
        SPEC,
        Path(__file__).resolve(),
        V2_TEST,
        LEGACY_RUNNER,
        LEGACY_TEST,
        PROVENANCE_HELPER,
        CHECKPOINT_LOADER,
        METHOD,
        PREREG,
        CHECKPOINT,
        *legacy._default_code_paths(),
    }
    return {_relative_repo_path(path) for path in paths}


def _closure_file_map(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    files = payload.get("files")
    if not isinstance(files, Mapping) or not files:
        raise RuntimeError("closure manifest has no exact file hashes")
    for relative, digest in files.items():
        name = str(relative)
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError(f"closure path is not repository-relative: {name}")
        if not _valid_sha256(digest):
            raise RuntimeError(f"closure file digest is malformed: {name}")
        target = REPO / name
        if not target.is_file() or _sha256(target) != str(digest):
            raise RuntimeError(f"closure file drift: {name}")
    return files


def verify_closure_manifest(
    manifest_path: Path,
    *,
    prereg_path: Path = PREREG,
    tle_root: Path | None = None,
    recompute_tests: bool = True,
) -> dict[str, Any]:
    """Verify exact V2 authority and test closure without opening seeds."""

    if not manifest_path.exists():
        raise FileNotFoundError(f"closure manifest does not exist: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("closure manifest must be JSON") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != CLOSURE_SCHEMA:
        raise RuntimeError("invalid scalarized C2 closure-manifest schema")
    files = _closure_file_map(payload)

    expected = {
        "candidate_spec_sha256": _sha256(SPEC),
        "runner_sha256": _sha256(Path(__file__).resolve()),
        "test_sha256": _sha256(V2_TEST),
        "legacy_runner_sha256": _sha256(LEGACY_RUNNER),
        "legacy_test_sha256": _sha256(LEGACY_TEST),
        "method_sha256": _sha256(METHOD),
        "prereg_sha256": _sha256(prereg_path),
        "checkpoint_sha256": _sha256(CHECKPOINT),
        "analysis_code_sha256": legacy._code_sha256(legacy._default_code_paths()),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"closure manifest mismatch: {key}")
    if payload.get("candidate_spec_sha256") != EXPECTED_SPEC_SHA256:
        raise RuntimeError("candidate spec does not match V2 frozen digest")
    if payload.get("method_sha256") != EXPECTED_METHOD_SHA256:
        raise RuntimeError("closure method authority is not current scalarized V2")
    if payload.get("prereg_sha256") != EXPECTED_PREREG_SHA256:
        raise RuntimeError("closure preregistration digest mismatch")
    if payload.get("checkpoint_sha256") != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError("closure checkpoint digest mismatch")
    if payload.get("analysis_code_sha256") != EXPECTED_ANALYSIS_CODE_SHA256:
        raise RuntimeError("closure analysis-source digest mismatch")

    missing = sorted(required_closure_files() - set(files))
    if missing:
        raise RuntimeError("closure manifest misses required files: " + ", ".join(missing))

    versions = payload.get("runtime", payload.get("dependency_versions"))
    if not isinstance(versions, Mapping):
        raise RuntimeError("closure manifest omits runtime dependency versions")
    for key, value in _dependency_versions().items():
        if versions.get(key) != value:
            raise RuntimeError(f"closure dependency-version mismatch: {key}")

    attestations = payload.get("attestations", payload)
    if not isinstance(attestations, Mapping):
        raise RuntimeError("closure attestations are malformed")
    for key in (
        "tests_passed_before_seed_reveal",
        "repository_disjointness_checked_before_reveal",
    ):
        if attestations.get(key) is not True:
            raise RuntimeError(f"closure lacks pre-reveal attestation: {key}")

    receipts = payload.get("test_receipts")
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)):
        raise RuntimeError("closure test receipts are malformed")
    if not receipts:
        raise RuntimeError("closure requires at least one V2 test receipt")
    commands: list[str] = []
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            raise RuntimeError("closure test receipt is malformed")
        if receipt.get("exit_code") != 0 or not _valid_sha256(
            receipt.get("stdout_sha256")
        ):
            raise RuntimeError("closure test receipt is not a sealed pass")
        stdout = receipt.get("stdout")
        if not isinstance(stdout, str) or _sha256_text(stdout) != receipt.get(
            "stdout_sha256"
        ):
            raise RuntimeError("closure test receipt stdout hash is not recomputable")
        normalized_sha = receipt.get("stdout_normalized_sha256")
        if not _valid_sha256(normalized_sha) or _sha256_text(
            _normalise_test_stdout(stdout)
        ) != normalized_sha:
            raise RuntimeError("closure test normalized stdout is not recomputable")
        command = str(receipt.get("command", ""))
        if not command:
            raise RuntimeError("closure test receipt omits exact command")
        argv = receipt.get("argv")
        if not isinstance(argv, Sequence) or isinstance(argv, (str, bytes)) or not argv:
            raise RuntimeError("closure test receipt omits exact argv")
        if " ".join(str(value) for value in argv) != command:
            raise RuntimeError("closure test receipt command/argv mismatch")
        if len(argv) < 3 or [str(value) for value in argv[1:3]] != [
            "-m",
            "pytest",
        ]:
            raise RuntimeError("closure test receipt is not a safe pytest argv")
        for argument in argv[3:]:
            if str(argument).startswith("-"):
                if str(argument) not in {"-q", "-x", "--quiet"}:
                    raise RuntimeError("closure test receipt contains an unsafe pytest flag")
                continue
            relative = Path(str(argument))
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError("closure test receipt escapes repository")
            target = REPO / relative
            if not target.is_file() or not target.name.startswith("test_"):
                raise RuntimeError("closure test receipt names a non-test target")
        cwd = receipt.get("cwd")
        if cwd != str(REPO):
            raise RuntimeError("closure test receipt cwd drift")
        commands.append(command)
        if recompute_tests:
            tested = subprocess.run(
                [str(value) for value in argv],
                cwd=REPO,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if tested.returncode != 0:
                raise RuntimeError(
                    f"closure test no longer passes: {command}"
                )
            if _sha256_text(_normalise_test_stdout(tested.stdout)) != normalized_sha:
                raise RuntimeError(
                    f"closure test normalized stdout is not reproducible: {command}"
                )
    if not any("test_c2_scalarized_stage0.py" in command for command in commands):
        raise RuntimeError("closure omits explicit V2 test execution")
    if not any("test_c2_stage0.py" in command for command in commands):
        raise RuntimeError("closure omits explicit legacy semantic test execution")

    expected_tles = _frozen_tle_hashes(prereg_path)
    if payload.get("tle_files") != expected_tles:
        raise RuntimeError("closure TLE inventory does not match preregistration")
    actual_tle_root = (
        Path(legacy.TLE_ROOT_DEFAULT).expanduser() if tle_root is None else tle_root
    )
    for relative, expected_hash in expected_tles.items():
        target = actual_tle_root / relative
        if not target.is_file() or _sha256(target) != expected_hash:
            raise RuntimeError(f"closure TLE drift: {relative}")

    dependencies = payload.get("dependencies")
    if dependencies is not None:
        if not isinstance(dependencies, Mapping) or not dependencies:
            raise RuntimeError("closure dependencies must be a non-empty mapping")
        for name, digest in dependencies.items():
            if name not in files or files[name] != digest:
                raise RuntimeError(f"closure dependency is not in exact file map: {name}")
    return dict(payload)


def _normalise_receipt_path(value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("disjointness receipt path is missing")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"disjointness receipt does not exist: {path}")
    return path


def _repo_matches(seed: int) -> tuple[str, ...]:
    """Independent hidden-repository search used to recompute seed receipts."""

    pattern = rf"(?<![0-9]){int(seed)}(?![0-9])"
    completed = subprocess.run(
        [
            "rg",
            "-l",
            "--hidden",
            "--no-ignore",
            "--glob",
            "!.git/**",
            "--glob",
            "!.venv/**",
            "--glob",
            "!__pycache__/**",
            "--pcre2",
            pattern,
            str(REPO),
        ],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(f"repository disjointness search failed: {completed.stderr}")
    return tuple(line for line in completed.stdout.splitlines() if line)


def _verify_disjointness_receipt(
    payload: Mapping[str, Any],
    *,
    seeds: Sequence[int],
    prior: Sequence[int],
    post_reveal_paths: Sequence[Path],
) -> None:
    """Recompute the sealed pre-reveal repository-search receipt.

    The receipt is produced before the seed manifest exists.  During a later
    load, the only allowed new matches are the exact closure/search/seed files
    listed in ``post_reveal_paths``; every other path is searched again and
    must still agree with the sealed zero-match record.
    """

    if payload.get("schema") != "smc-er-c2-scalarized-stage0-disjointness-v1":
        raise RuntimeError("invalid disjointness-search receipt schema")
    if payload.get("status") != "PASS":
        raise RuntimeError("disjointness-search receipt is not PASS")
    if payload.get("namespace") != SEED_NAMESPACE:
        raise RuntimeError("disjointness-search namespace drift")
    if payload.get("repository_root") != str(REPO):
        raise RuntimeError("disjointness-search repository root drift")
    recorded_selected = payload.get("selected_seeds")
    if recorded_selected != [int(seed) for seed in seeds]:
        raise RuntimeError("disjointness receipt selected seeds drifted")
    recorded_prior = payload.get("known_prior_seed_values")
    if recorded_prior != [int(seed) for seed in prior]:
        raise RuntimeError("disjointness receipt prior seeds drifted")
    attempts = payload.get("candidate_attempts")
    if not isinstance(attempts, Sequence) or isinstance(attempts, (str, bytes)):
        raise RuntimeError("disjointness receipt attempts are malformed")
    ignored = {path.resolve() for path in post_reveal_paths}
    reconstructed: list[int] = []
    for row in attempts:
        if not isinstance(row, Mapping):
            raise RuntimeError("disjointness receipt attempt is malformed")
        candidate = row.get("candidate")
        if isinstance(candidate, bool) or not isinstance(candidate, (int, np.integer)):
            raise RuntimeError("disjointness receipt candidate is not an integer")
        candidate = int(candidate)
        matches = tuple(
            path
            for path in _repo_matches(candidate)
            if Path(path).expanduser().resolve() not in ignored
        )
        recorded_matches = tuple(str(path) for path in row.get("repository_matches", ()))
        if matches != recorded_matches:
            raise RuntimeError(
                f"disjointness receipt search is not reproducible for {candidate}"
            )
        known_collision = candidate in {int(value) for value in prior}
        selected_collision = candidate in reconstructed
        accepted = not known_collision and not selected_collision and not matches
        if row.get("known_prior_collision") is not known_collision:
            raise RuntimeError("disjointness receipt prior-collision flag drift")
        if row.get("selected_collision") is not selected_collision:
            raise RuntimeError("disjointness receipt selected-collision flag drift")
        if row.get("accepted") is not accepted:
            raise RuntimeError("disjointness receipt acceptance decision drift")
        if accepted:
            reconstructed.append(candidate)
    if tuple(reconstructed) != tuple(int(seed) for seed in seeds):
        raise RuntimeError("disjointness receipt does not reconstruct selected seeds")
    if payload.get("all_selected_have_zero_pre_reveal_matches") is not True:
        raise RuntimeError("disjointness receipt lacks zero-match conclusion")


def _validate_seed_manifest(
    payload: Mapping[str, Any],
    *,
    closure_sha256: str,
    closure_manifest_path: Path | None = None,
    seed_manifest_path: Path | None = None,
) -> tuple[int, ...]:
    if payload.get("schema") != SEED_SCHEMA:
        raise RuntimeError("invalid scalarized C2 seed-manifest schema")
    if payload.get("closure_manifest_sha256") != closure_sha256:
        raise RuntimeError("seed manifest does not bind the V2 closure")
    if payload.get("seed_namespace") != SEED_NAMESPACE:
        raise RuntimeError("seed manifest namespace is not scalarized C2 V2")
    if payload.get("seed_count") != SEED_COUNT:
        raise RuntimeError("scalarized C2 campaign requires exactly five seeds")
    raw = payload.get("c2_seeds")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise RuntimeError("seed manifest must contain c2_seeds")
    if len(raw) != SEED_COUNT:
        raise RuntimeError("scalarized C2 campaign requires exactly five seeds")
    if any(isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) for seed in raw):
        raise RuntimeError("C2 seeds must be integer values")
    seeds = tuple(int(seed) for seed in raw)
    if len(set(seeds)) != SEED_COUNT:
        raise RuntimeError("scalarized C2 seeds must be unique")
    if payload.get("repository_disjointness_checked_before_reveal") is not True:
        raise RuntimeError("seed manifest lacks pre-reveal disjointness attestation")
    if not _valid_sha256(payload.get("disjointness_search_receipt_sha256")):
        raise RuntimeError("seed manifest lacks sealed disjointness receipt")

    schedule = payload.get("focal_schedule")
    expected_schedule = {
        "anchor_steps": list(ANCHOR_STEPS),
        "focal_users_per_step": FOCAL_USERS_PER_STEP,
        "permutation_offset": FOCAL_SCHEDULE_OFFSET,
    }
    if schedule != expected_schedule:
        raise RuntimeError("seed manifest focal schedule is not frozen V2 schedule")

    prior = payload.get("prior_seed_values", payload.get("previous_seeds"))
    if prior is None:
        raise RuntimeError("seed manifest must list prior seed values for disjointness")
    if not isinstance(prior, Sequence) or isinstance(prior, (str, bytes)):
        raise RuntimeError("prior seed list is malformed")
    if any(isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) for seed in prior):
        raise RuntimeError("prior seed values must be integers")
    prior_values = tuple(int(seed) for seed in prior)
    if set(seeds) & set(prior_values):
        raise RuntimeError("scalarized C2 seeds are not disjoint from prior seeds")
    receipt_path = _normalise_receipt_path(payload.get("disjointness_search_receipt_path"))
    if _sha256(receipt_path) != payload.get("disjointness_search_receipt_sha256"):
        raise RuntimeError("disjointness receipt hash is not reproducible")
    freeze_output_dir = receipt_path.parent.resolve()
    try:
        freeze_output_dir.relative_to(REPO.resolve())
    except ValueError:
        pass
    else:
        raise RuntimeError("freeze output directory must be outside the repository")
    if receipt_path != freeze_output_dir / FREEZE_DISJOINTNESS_FILENAME:
        raise RuntimeError(
            "disjointness receipt must use the canonical freeze filename"
        )
    raw_ignored = payload.get("post_reveal_ignored_paths")
    if not isinstance(raw_ignored, Sequence) or isinstance(raw_ignored, (str, bytes)):
        raise RuntimeError("seed manifest omits exact post-reveal receipt paths")
    ignored = [_normalise_receipt_path(value) for value in raw_ignored]
    if any(path.parent.resolve() != freeze_output_dir for path in ignored):
        raise RuntimeError(
            "post-reveal ignored paths must remain in the same freeze output directory"
        )
    expected_ignored = set(_canonical_freeze_paths(freeze_output_dir))
    if len(ignored) != len(expected_ignored) or {
        path.resolve() for path in ignored
    } != expected_ignored:
        raise RuntimeError(
            "post-reveal ignored paths must be exactly the canonical freeze path set"
        )
    expected_closure_path, _, expected_seed_path = _canonical_freeze_paths(
        freeze_output_dir
    )
    if closure_manifest_path is not None and (
        closure_manifest_path.expanduser().resolve() != expected_closure_path
    ):
        raise RuntimeError("closure manifest is not the canonical freeze path")
    if seed_manifest_path is not None and (
        seed_manifest_path.expanduser().resolve() != expected_seed_path
    ):
        raise RuntimeError("seed manifest is not the canonical freeze path")
    _verify_disjointness_receipt(
        json.loads(receipt_path.read_text(encoding="utf-8")),
        seeds=seeds,
        prior=prior_values,
        post_reveal_paths=ignored,
    )
    return seeds


def load_seed_manifest(
    seed_manifest: Path,
    closure_manifest: Path,
    *,
    prereg_path: Path = PREREG,
    tle_root: Path | None = None,
) -> tuple[int, ...]:
    """Verify closure first, then open exactly five disjoint C2 seeds."""

    verify_closure_manifest(
        closure_manifest,
        prereg_path=prereg_path,
        tle_root=tle_root,
        recompute_tests=True,
    )
    closure_sha = _sha256(closure_manifest)
    if not seed_manifest.exists():
        raise FileNotFoundError(f"seed manifest does not exist: {seed_manifest}")
    payload = json.loads(seed_manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise RuntimeError("seed manifest must be a JSON object")
    return _validate_seed_manifest(
        payload,
        closure_sha256=closure_sha,
        closure_manifest_path=closure_manifest,
        seed_manifest_path=seed_manifest,
    )


def _scalarized_main_actions(
    trainer: Any, states: Sequence[Any], wrapped_masks: Sequence[Any]
) -> np.ndarray:
    """Use exactly the frozen deployed scalarized Main policy.

    The explicit objective-weight check makes an accidental Q1-only fallback
    fail before any anchor is evaluated.  The helper does not consume a policy
    RNG because Stage-0 Main is masked-greedy.
    """

    configured = tuple(float(value) for value in trainer.config.objective_weights)
    if configured != OBJECTIVE_WEIGHTS:
        raise RuntimeError(
            "scalarized Main objective weights drifted: "
            f"expected {OBJECTIVE_WEIGHTS}, got {configured}"
        )
    encoded = trainer.encode_states(list(states))
    masks = np.stack([row.mask for row in wrapped_masks])
    q_values = trainer.scalarized_q_values(
        encoded, objective_weights=OBJECTIVE_WEIGHTS
    )
    return np.asarray(legacy.masked_greedy_actions(q_values, masks), dtype=np.int32)


@contextlib.contextmanager
def _scalarized_policy_seam() -> Iterator[None]:
    """Temporarily bind every delegated legacy call to scalarized Main."""

    original = legacy._main_actions
    legacy._main_actions = _scalarized_main_actions
    try:
        yield
    finally:
        legacy._main_actions = original


def run_seed(archive: Any, trainer: Any, *, seed: int) -> dict[str, Any]:
    """Run one legacy physical gate seed through the V2 policy seam."""

    with _scalarized_policy_seam():
        rollout = legacy._run_seed(archive, trainer, seed=int(seed))
    rollout["main_policy"] = {
        "mode": POLICY_MODE,
        "objective_weights": list(OBJECTIVE_WEIGHTS),
        "scalarized_q_formula": "0.5*Q1 + 0.3*Q2 + 0.2*Q3",
    }
    return rollout


def _aggregate(rollouts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Reuse legacy metric arithmetic and namespace the V2 decisions."""

    aggregate = dict(legacy._aggregate(rollouts))
    mapping = {
        "C2_STAGE0_PASS_TO_FIXTURES_ONLY": "C2_SCALARIZED_STAGE0_PASS_TO_FIXTURES_ONLY",
        "C2_STAGE0_CERTIFICATE_FAILURE": "C2_SCALARIZED_STAGE0_CERTIFICATE_FAILURE",
        "C2_STAGE0_FAIL_DROP_ROLE": "C2_SCALARIZED_STAGE0_FAIL_DROP_ROLE",
    }
    decision = str(aggregate.get("decision"))
    aggregate["decision"] = mapping.get(decision, "C2_SCALARIZED_STAGE0_CERTIFICATE_FAILURE")
    aggregate["policy_mode"] = POLICY_MODE
    aggregate["objective_weights"] = list(OBJECTIVE_WEIGHTS)
    return aggregate


def _runtime_receipt() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            name: importlib.metadata.version(name)
            if importlib.util.find_spec(name) is not None
            else None
            for name in ("numpy", "torch", "sgp4")
        },
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=legacy.DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(legacy.TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--closure-manifest", type=Path, required=True)
    parser.add_argument("--seed-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    if EXPECTED_SPEC_SHA256.startswith("__") or _sha256(SPEC) != EXPECTED_SPEC_SHA256:
        raise RuntimeError("scalarized C2 candidate specification changed")
    if _sha256(METHOD) != EXPECTED_METHOD_SHA256:
        raise RuntimeError("current SMC-ER method contract changed")
    if _sha256(args.prereg) != EXPECTED_PREREG_SHA256:
        raise RuntimeError("frozen preregistration changed")
    if _sha256(CHECKPOINT) != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError("corrected Main checkpoint changed")
    if legacy._code_sha256(legacy._default_code_paths()) != EXPECTED_ANALYSIS_CODE_SHA256:
        raise RuntimeError("reviewed analysis source changed")

    closure = verify_closure_manifest(
        args.closure_manifest,
        prereg_path=args.prereg,
        tle_root=args.tle_root,
        recompute_tests=True,
    )
    seeds = load_seed_manifest(
        args.seed_manifest,
        args.closure_manifest,
        prereg_path=args.prereg,
        tle_root=args.tle_root,
    )
    record = legacy.read_prereg(args.prereg)

    with tempfile.TemporaryDirectory(prefix="mcrl-c2-scalarized-stage0-") as temp:
        archive = legacy.checkpoint_loader._frozen_archive(
            record, args.tle_root, Path(temp) / "frozen-tle"
        )
        trainer, checkpoint = legacy.checkpoint_loader._verify_and_load_trainer(
            record, archive, run_dir=args.input_dir / "main", users=legacy.USERS
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("loaded Main checkpoint digest changed")
        configured = tuple(float(value) for value in trainer.config.objective_weights)
        if configured != OBJECTIVE_WEIGHTS:
            raise RuntimeError(
                "loaded Main checkpoint/config is not the frozen scalarized policy"
            )
        rollouts = [run_seed(archive, trainer, seed=seed) for seed in seeds]

    output = {
        "schema": OUTPUT_SCHEMA,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "claim_boundary": (
            "scalarized-Main, legacy-geometry, fading-off, non-training Stage-0 "
            "paired evidence only; no Q2 learnability, Main transfer, actual-"
            "fading, carrier, training, effectiveness, EE, joint-benefit, or "
            "novelty claim"
        ),
        "policy": {
            "mode": POLICY_MODE,
            "objective_weights": list(OBJECTIVE_WEIGHTS),
            "formula": "Q_M^sc = 0.5 Q_1^M + 0.3 Q_2^M + 0.2 Q_3^M",
        },
        "inputs": {
            "candidate_spec_sha256": _sha256(SPEC),
            "method_sha256": _sha256(METHOD),
            "prereg_sha256": _sha256(args.prereg),
            "checkpoint_sha256": checkpoint["checkpoint_sha256"],
            "runner_sha256": _sha256(Path(__file__).resolve()),
            "legacy_runner_sha256": _sha256(LEGACY_RUNNER),
            "closure_manifest_sha256": _sha256(args.closure_manifest),
            "seed_manifest_sha256": _sha256(args.seed_manifest),
            "analysis_code_sha256": legacy._code_sha256(legacy._default_code_paths()),
            "closure_schema": closure["schema"],
        },
        "runtime": _runtime_receipt(),
        "seeds": list(seeds),
        "rollouts": rollouts,
        "aggregate": _aggregate(rollouts),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staged = args.output.with_name(args.output.name + ".tmp")
    if staged.exists():
        raise FileExistsError(f"refusing to overwrite staged output: {staged}")
    staged.write_text(
        json.dumps(output, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )
    os.replace(staged, args.output)
    print(json.dumps({"output": str(args.output), "decision": output["aggregate"]["decision"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
