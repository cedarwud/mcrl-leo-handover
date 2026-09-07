#!/usr/bin/env python3
"""Compare a canonical B000 run with an all-shadow treatment carrier.

The check is exact: networks, targets, optimizers, replay FIFO contents,
trainer/environment RNGs, masking diagnostics, and persistent Main environment
state must match.  Only descriptive experiment metadata may differ.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
RUN_SHORT_EP = HERE / "run_short_ep.py"
PARITY_CHECKER = HERE / "check_zero_dose_parity.py"
SCHEMA = "multi-catfish-mcrl-zero-dose-parity-v5"
RUN_SCHEMA = "multi-catfish-mcrl-one-arm-short-ep-v2"
PACKAGE_ARTIFACT_PATHS = {
    "baseline_state": PurePosixPath("B000/training-state.pt"),
    "baseline_status": PurePosixPath("B000/status.json"),
    "carrier_state": PurePosixPath("F111-zero-route/carrier-state.pt"),
    "carrier_status": PurePosixPath("F111-zero-route/status.json"),
}

from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)
DESCRIPTIVE_CONFIG_KEYS = {
    "training_experiment_kind",
    "training_experiment_id",
    "method_family",
    "phase",
    "comparison_role",
}


def _normalise_training_state(value: Mapping[str, Any]) -> dict[str, Any]:
    state = copy.deepcopy(dict(value))
    config = dict(state["trainer_config"])
    for key in DESCRIPTIVE_CONFIG_KEYS:
        config.pop(key, None)
    state["trainer_config"] = config
    return state


def _first_difference(left: Any, right: Any, path: str = "root") -> str | None:
    if isinstance(left, torch.Tensor) or isinstance(right, torch.Tensor):
        if not isinstance(left, torch.Tensor) or not isinstance(right, torch.Tensor):
            return f"{path}: tensor/type mismatch"
        return None if torch.equal(left, right) else f"{path}: tensor values differ"
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        if not isinstance(left, np.ndarray) or not isinstance(right, np.ndarray):
            return f"{path}: ndarray/type mismatch"
        return None if np.array_equal(left, right) else f"{path}: array values differ"
    if isinstance(left, Mapping) or isinstance(right, Mapping):
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            return f"{path}: mapping/type mismatch"
        if set(left) != set(right):
            return f"{path}: mapping keys differ"
        for key in sorted(left, key=str):
            difference = _first_difference(left[key], right[key], f"{path}.{key}")
            if difference is not None:
                return difference
        return None
    if (
        isinstance(left, Sequence)
        and not isinstance(left, (str, bytes))
    ) or (
        isinstance(right, Sequence)
        and not isinstance(right, (str, bytes))
    ):
        if (
            not isinstance(left, Sequence)
            or isinstance(left, (str, bytes))
            or not isinstance(right, Sequence)
            or isinstance(right, (str, bytes))
        ):
            return f"{path}: sequence/type mismatch"
        if len(left) != len(right):
            return f"{path}: sequence lengths differ"
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            difference = _first_difference(
                left_item, right_item, f"{path}[{index}]"
            )
            if difference is not None:
                return difference
        return None
    if type(left) is not type(right):
        return f"{path}: types differ ({type(left).__name__}, {type(right).__name__})"
    return None if left == right else f"{path}: values differ ({left!r}, {right!r})"


def compare_states(
    baseline_state: Mapping[str, Any], carrier_main_state: Mapping[str, Any]
) -> dict[str, Any]:
    left = _normalise_training_state(baseline_state)
    right = _normalise_training_state(carrier_main_state)
    difference = _first_difference(left, right)
    return {
        "schema": SCHEMA,
        "status": "PASS" if difference is None else "FAIL",
        "exact_after_descriptive_metadata_normalisation": difference is None,
        "first_difference": difference,
        "compared_surfaces": [
            "online_networks",
            "target_networks",
            "optimizers",
            "train_env_mobility_and_torch_rngs",
            "canonical_replay_fifo",
            "masking_diagnostics",
            "persistent_main_environment_state",
        ],
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _current_run_source_hashes() -> dict[str, str]:
    stage0 = HERE.parent / "catfish-stage0"
    paths = (
        RUN_SHORT_EP,
        HERE / "smc_er_core.py",
        HERE / "smc_er_roles.py",
        HERE / "c1_exp_corpus.py",
        stage0 / "c2_activation_churn_core.py",
        stage0 / "c2_activation_churn_runtime_adapter.py",
        stage0 / "c2_activation_churn_dev_support.py",
        stage0 / "c3_reward_aligned_v3_core.py",
        stage0 / "c3_reward_aligned_v3_runtime_adapter.py",
        stage0 / "c3_reward_aligned_v3_shadow_runner.py",
        stage0 / "c3_reward_aligned_v3_trainer_backend.py",
        HERE / "sweep_evaluation.py",
        HERE / "intermediate_trend_authority.py",
        REPO / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md",
        REPO / "docs" / "MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md",
        REPO / "docs" / "THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.1-2026-08-28.md",
        REPO / "docs" / "CATFISH-V0.2-OBSERVABLE-SUPPORT-SPEC-2026-08-28.md",
        REPO / "docs" / "CATFISH-V0.2-OBSERVABLE-SUPPORT-FREEZE-2026-08-28.json",
        Path(CANONICAL_PREREG).resolve(),
    )
    return {path.name: sha256_file(path) for path in paths}


def _strict_relative_posix(raw: Any, *, label: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise RuntimeError(f"zero-dose parity {label} must be a strict relative POSIX path")
    relative = PurePosixPath(raw)
    if (
        relative.is_absolute()
        or raw != relative.as_posix()
        or raw in {".", ".."}
        or any(part in {".", ".."} or part.startswith("~") for part in relative.parts)
    ):
        raise RuntimeError(f"zero-dose parity {label} must be a strict relative POSIX path")
    return relative


def _resolve_confined_file(raw: Any, *, root: Path, label: str) -> Path:
    relative = _strict_relative_posix(raw, label=label)
    canonical_root = Path(root).resolve()
    target = (canonical_root / Path(*relative.parts)).resolve()
    try:
        target.relative_to(canonical_root)
    except ValueError as error:
        raise RuntimeError(f"zero-dose parity {label} escapes its trusted root") from error
    if not target.is_file():
        raise RuntimeError(f"zero-dose parity {label} is missing")
    return target


def _repo_relative_file(path: Path, *, label: str) -> str:
    canonical_root = REPO.resolve()
    target = Path(path).resolve()
    try:
        relative = target.relative_to(canonical_root).as_posix()
    except ValueError as error:
        raise RuntimeError(f"zero-dose parity {label} escapes the repository") from error
    _strict_relative_posix(relative, label=label)
    if not target.is_file():
        raise RuntimeError(f"zero-dose parity {label} is missing")
    return relative


def _resolve_repo_file(raw: Any, *, label: str) -> Path:
    return _resolve_confined_file(raw, root=REPO, label=label)


def _receipt_package_paths(
    baseline_state_path: Path, carrier_state_path: Path
) -> tuple[Path, dict[str, Path]]:
    baseline_input = Path(baseline_state_path).expanduser().absolute()
    carrier_input = Path(carrier_state_path).expanduser().absolute()
    baseline_root = baseline_input.parent.parent.resolve()
    carrier_root = carrier_input.parent.parent.resolve()
    if baseline_root != carrier_root:
        raise RuntimeError("zero-dose states do not share one receipt package")
    paths = {
        name: _resolve_confined_file(relative.as_posix(), root=baseline_root, label=name)
        for name, relative in PACKAGE_ARTIFACT_PATHS.items()
    }
    if (
        baseline_input.resolve() != paths["baseline_state"]
        or carrier_input.resolve() != paths["carrier_state"]
    ):
        raise RuntimeError("zero-dose states are not at their exact package paths")
    return baseline_root, paths


def _load_bound_run_status(
    state_path: Path, status_path: Path, *, expected_arm: str, result_key: str
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    if not status_path.is_file():
        raise RuntimeError(f"zero-dose {expected_arm} status.json is missing")
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema") != RUN_SCHEMA
        or payload.get("status") != "complete"
        or payload.get("arm") != expected_arm
    ):
        raise RuntimeError(f"zero-dose {expected_arm} run status is malformed")
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise RuntimeError(f"zero-dose {expected_arm} result authority is missing")
    recorded_state_path = result.get(result_key)
    if (
        not isinstance(recorded_state_path, str)
        or not recorded_state_path
        or result.get(result_key + "_sha256") != sha256_file(state_path)
    ):
        raise RuntimeError(f"zero-dose {expected_arm} state/status binding mismatch")
    sources = payload.get("source_files_sha256")
    if (
        not isinstance(sources, Mapping)
        or dict(sources) != _current_run_source_hashes()
    ):
        raise RuntimeError(f"zero-dose {expected_arm} run source authority mismatch")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise RuntimeError(f"zero-dose {expected_arm} ephemeris authority is missing")
    return status_path, dict(payload), dict(authority)


def _validated_shared_ephemeris_authority(
    baseline: Mapping[str, Any], carrier: Mapping[str, Any], *, tle_root: Path
) -> dict[str, Any]:
    content_keys = (
        "prereg_sha256",
        "tle_file_set_sha256",
        "tle_file_count",
    )
    if any(baseline.get(key) != carrier.get(key) for key in content_keys):
        raise RuntimeError("zero-dose arms do not share one ephemeris authority")
    prereg_relative = _repo_relative_file(
        Path(CANONICAL_PREREG), label="prereg"
    )
    prereg = _resolve_repo_file(prereg_relative, label="prereg")
    if (
        prereg != Path(CANONICAL_PREREG).resolve()
        or not prereg.is_file()
        or sha256_file(prereg) != CANONICAL_PREREG_BYTE_SHA256
        or baseline.get("prereg_sha256") != CANONICAL_PREREG_BYTE_SHA256
    ):
        raise RuntimeError("zero-dose parity does not bind the canonical preregistration")
    canonical_tle_root = Path(tle_root).expanduser().resolve()
    if not canonical_tle_root.is_dir():
        raise RuntimeError("zero-dose parity caller-supplied TLE root is missing")
    archive = TleArchive(canonical_tle_root)
    record = read_prereg(prereg)
    record.verify()
    ephemeris = assert_ephemeris_matches_record(record, archive=archive)
    if (
        baseline.get("tle_file_set_sha256") != ephemeris["file_set_sha256"]
        or baseline.get("tle_file_count")
        != int(ephemeris["archive"]["file_count"])
    ):
        raise RuntimeError("zero-dose parity TLE authority does not reproduce")
    return {
        "prereg_path": prereg_relative,
        "prereg_sha256": CANONICAL_PREREG_BYTE_SHA256,
        "tle_file_set_sha256": ephemeris["file_set_sha256"],
        "tle_file_count": int(ephemeris["archive"]["file_count"]),
        "tle_root_binding": "runtime_argument",
    }


def build_receipt(
    *, baseline_state_path: Path, carrier_state_path: Path, tle_root: Path
) -> dict[str, Any]:
    _, package_paths = _receipt_package_paths(
        baseline_state_path, carrier_state_path
    )
    baseline_path = package_paths["baseline_state"]
    carrier_path = package_paths["carrier_state"]
    baseline_status_path, _, baseline_authority = _load_bound_run_status(
        baseline_path,
        package_paths["baseline_status"],
        expected_arm="B000",
        result_key="training_state",
    )
    carrier_status_path, _, carrier_authority = _load_bound_run_status(
        carrier_path,
        package_paths["carrier_status"],
        expected_arm="F111",
        result_key="carrier_state",
    )
    ephemeris_authority = _validated_shared_ephemeris_authority(
        baseline_authority, carrier_authority, tle_root=tle_root
    )
    baseline = torch.load(baseline_path, map_location="cpu", weights_only=False)
    carrier = torch.load(carrier_path, map_location="cpu", weights_only=False)
    if not isinstance(baseline, Mapping):
        raise RuntimeError("baseline training state must be a mapping")
    if not isinstance(carrier, Mapping) or carrier.get("schema") != "smc-er-carrier-state-v1":
        raise RuntimeError("carrier state has the wrong schema")
    main_state = carrier.get("main_training_state")
    if not isinstance(main_state, Mapping):
        raise RuntimeError("carrier Main training state is missing")
    result = compare_states(baseline, main_state)
    result["authority"] = {
        "baseline_state_path": PACKAGE_ARTIFACT_PATHS["baseline_state"].as_posix(),
        "baseline_state_sha256": sha256_file(baseline_path),
        "carrier_state_path": PACKAGE_ARTIFACT_PATHS["carrier_state"].as_posix(),
        "carrier_state_sha256": sha256_file(carrier_path),
        "baseline_status_path": PACKAGE_ARTIFACT_PATHS["baseline_status"].as_posix(),
        "baseline_status_sha256": sha256_file(baseline_status_path),
        "carrier_status_path": PACKAGE_ARTIFACT_PATHS["carrier_status"].as_posix(),
        "carrier_status_sha256": sha256_file(carrier_status_path),
        "parity_checker_path": _repo_relative_file(
            PARITY_CHECKER, label="parity_checker"
        ),
        "parity_checker_sha256": sha256_file(PARITY_CHECKER.resolve()),
        "run_short_ep_path": _repo_relative_file(RUN_SHORT_EP, label="run_short_ep"),
        "run_short_ep_sha256": sha256_file(RUN_SHORT_EP.resolve()),
        **ephemeris_authority,
    }
    return result


def validate_receipt(path: Path, *, tle_root: Path) -> dict[str, Any]:
    receipt_path = Path(path).expanduser().resolve()
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise RuntimeError("zero-dose parity receipt schema mismatch")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise RuntimeError("zero-dose parity receipt lacks authority")

    def bound_artifact(name: str) -> Path:
        raw = authority.get(name + "_path")
        relative = _strict_relative_posix(raw, label=name)
        if relative != PACKAGE_ARTIFACT_PATHS[name]:
            raise RuntimeError(f"zero-dose parity {name} path is noncanonical")
        target = _resolve_confined_file(raw, root=receipt_path.parent, label=name)
        if authority.get(name + "_sha256") != sha256_file(target):
            raise RuntimeError(f"zero-dose parity {name} hash mismatch")
        return target

    def bound_repo_file(name: str, expected: Path) -> Path:
        raw = authority.get(name + "_path")
        relative = _strict_relative_posix(raw, label=name)
        expected_relative = _repo_relative_file(expected, label=name)
        if relative.as_posix() != expected_relative:
            raise RuntimeError(f"zero-dose parity {name} path is noncanonical")
        target = _resolve_repo_file(raw, label=name)
        if authority.get(name + "_sha256") != sha256_file(target):
            raise RuntimeError(f"zero-dose parity {name} hash mismatch")
        return target

    baseline_path = bound_artifact("baseline_state")
    carrier_path = bound_artifact("carrier_state")
    bound_artifact("baseline_status")
    bound_artifact("carrier_status")
    bound_repo_file("parity_checker", PARITY_CHECKER)
    bound_repo_file("run_short_ep", RUN_SHORT_EP)
    prereg_path = bound_repo_file("prereg", Path(CANONICAL_PREREG))
    if (
        prereg_path != Path(CANONICAL_PREREG).resolve()
        or authority.get("prereg_sha256") != CANONICAL_PREREG_BYTE_SHA256
    ):
        raise RuntimeError("zero-dose parity prereg is noncanonical")
    if "tle_root_path" in authority:
        raise RuntimeError("zero-dose parity receipt must not store a physical TLE root")
    if authority.get("tle_root_binding") != "runtime_argument":
        raise RuntimeError("zero-dose parity TLE root binding is noncanonical")
    replayed = build_receipt(
        baseline_state_path=baseline_path,
        carrier_state_path=carrier_path,
        tle_root=tle_root,
    )
    if dict(payload) != replayed:
        raise RuntimeError("zero-dose parity receipt does not reproduce exactly")
    if (
        payload.get("status") != "PASS"
        or payload.get("exact_after_descriptive_metadata_normalisation") is not True
        or payload.get("first_difference") is not None
    ):
        raise RuntimeError("zero-dose parity is not an exact PASS")
    return dict(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-state", type=Path, required=True)
    parser.add_argument("--carrier-state", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.expanduser().resolve()
    package_root, _ = _receipt_package_paths(
        args.baseline_state, args.carrier_state
    )
    if target.parent != package_root:
        raise RuntimeError("zero-dose parity output must be in the receipt package root")
    result = build_receipt(
        baseline_state_path=args.baseline_state,
        carrier_state_path=args.carrier_state,
        tle_root=args.tle_root,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SCHEMA",
    "_first_difference",
    "build_receipt",
    "compare_states",
    "sha256_file",
    "validate_receipt",
]
