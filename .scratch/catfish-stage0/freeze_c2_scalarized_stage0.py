#!/usr/bin/env python3
"""Seal the C2 scalarized V2 closure, then reveal five disjoint seeds."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import run_c2_scalarized_stage0 as c2
from mcrl.artifacts import read_checkpoint


DERIVATION_SCHEMA = "smc-er-c2-scalarized-stage0-freeze-v1"
FREEZE_TEST = Path(__file__).with_name("test_freeze_c2_scalarized_stage0.py")
KNOWN_SEED_FILES = (
    c2.REPO / ".scratch" / "smc-er-short-ep" / "c1-source-gate-a-seeds-v1.json",
    c2.REPO / ".scratch" / "smc-er-short-ep" / "c1-exp-build-seeds-v1.json",
)


def _write_new(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"refusing to overwrite staged file {temporary}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _known_prior_seeds() -> set[int]:
    values: set[int] = {
        20260822,
        20260823,
        *range(2026082401, 2026082431),
        *range(2026082601, 2026082611),
        *range(2026082701, 2026082711),
        *range(2026082801, 2026082831),
    }
    for path in KNOWN_SEED_FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        values.update(int(value) for value in payload["seeds"])
    checkpoint = read_checkpoint(c2.CHECKPOINT, map_location="cpu")
    values.update(
        (
            int(checkpoint.train_seed),
            int(checkpoint.env_seed),
            int(checkpoint.mobility_seed),
        )
    )
    return values


def _derive_candidate(counter: int) -> int:
    material = c2._canonical_bytes(
        [
            c2.SEED_NAMESPACE,
            c2._sha256(c2.SPEC),
            c2._sha256(Path(c2.__file__).resolve()),
            int(counter),
        ]
    )
    return int.from_bytes(hashlib.sha256(material).digest()[:4], "big")


def _repo_matches(seed: int) -> tuple[str, ...]:
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
            str(c2.REPO),
        ],
        cwd=c2.REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(f"repository disjointness search failed: {completed.stderr}")
    return tuple(line for line in completed.stdout.splitlines() if line)


def derive_disjoint_seeds() -> tuple[tuple[int, ...], list[dict[str, Any]], tuple[int, ...]]:
    """Select five deterministic candidates before writing/revealing them."""

    prior = _known_prior_seeds()
    selected: list[int] = []
    attempts: list[dict[str, Any]] = []
    counter = 0
    while len(selected) < c2.SEED_COUNT:
        candidate = _derive_candidate(counter)
        matches = _repo_matches(candidate)
        accepted = candidate not in prior and candidate not in selected and not matches
        attempts.append(
            {
                "counter": counter,
                "candidate": candidate,
                "accepted": accepted,
                "known_prior_collision": candidate in prior,
                "selected_collision": candidate in selected,
                "repository_matches": list(matches),
            }
        )
        if accepted:
            selected.append(candidate)
        counter += 1
        if counter > 10_000:
            raise RuntimeError("unable to derive five disjoint C2 seeds")
    return tuple(selected), attempts, tuple(sorted(prior))


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    output_dir = c2._validate_freeze_output_directory(args.output_dir)
    if output_dir.exists():
        raise FileExistsError(f"refusing to reuse freeze directory: {output_dir}")

    # Close the executable/test authority before deriving or writing any
    # candidate seed.  This is the pre-reveal gate: a later seed search cannot
    # influence which code/tests are considered closed.
    test_command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(c2.V2_TEST.relative_to(c2.REPO)),
        str(c2.LEGACY_TEST.relative_to(c2.REPO)),
        str(FREEZE_TEST.relative_to(c2.REPO)),
    ]
    tested = subprocess.run(
        test_command,
        cwd=c2.REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if tested.returncode != 0:
        raise RuntimeError("C2 scalarized V2 tests failed before seed reveal")

    output_dir.mkdir(parents=True, exist_ok=False)
    test_stdout = tested.stdout.encode("utf-8")
    file_map = {
        relative: c2._sha256(c2.REPO / relative)
        for relative in sorted(c2.required_closure_files())
    }
    freeze_relative = c2._relative_repo_path(Path(__file__).resolve())
    file_map[freeze_relative] = c2._sha256(Path(__file__).resolve())
    freeze_test_relative = c2._relative_repo_path(FREEZE_TEST)
    file_map[freeze_test_relative] = c2._sha256(FREEZE_TEST)
    closure = {
        "schema": c2.CLOSURE_SCHEMA,
        "freeze_schema": DERIVATION_SCHEMA,
        "candidate_spec_sha256": c2._sha256(c2.SPEC),
        "runner_sha256": c2._sha256(Path(c2.__file__).resolve()),
        "test_sha256": c2._sha256(c2.V2_TEST),
        "legacy_runner_sha256": c2._sha256(c2.LEGACY_RUNNER),
        "legacy_test_sha256": c2._sha256(c2.LEGACY_TEST),
        "freeze_test_sha256": c2._sha256(FREEZE_TEST),
        "method_sha256": c2._sha256(c2.METHOD),
        "prereg_sha256": c2._sha256(c2.PREREG),
        "checkpoint_sha256": c2._sha256(c2.CHECKPOINT),
        "analysis_code_sha256": c2.legacy._code_sha256(c2.legacy._default_code_paths()),
        "runtime": c2._dependency_versions(),
        "attestations": {
            "tests_passed_before_seed_reveal": True,
            "repository_disjointness_checked_before_reveal": True,
        },
        "test_receipts": [
            {
                "command": " ".join(test_command),
                "argv": test_command,
                "cwd": str(c2.REPO),
                "exit_code": int(tested.returncode),
                "stdout_sha256": hashlib.sha256(test_stdout).hexdigest(),
                "stdout_normalized_sha256": c2._sha256_text(
                    c2._normalise_test_stdout(tested.stdout)
                ),
                "stdout": tested.stdout,
            }
        ],
        "tle_files": c2._frozen_tle_hashes(c2.PREREG),
        "files": file_map,
    }
    closure_path = output_dir / c2.FREEZE_CLOSURE_FILENAME
    _write_new(closure_path, closure)
    c2.verify_closure_manifest(closure_path, recompute_tests=True)

    # Only after the verified closure exists may deterministic candidate
    # values be derived.  The receipt is written before the seed manifest so
    # its zero-match search is genuinely pre-reveal.
    seeds, attempts, prior = derive_disjoint_seeds()

    search_receipt = {
        "schema": "smc-er-c2-scalarized-stage0-disjointness-v1",
        "status": "PASS",
        "namespace": c2.SEED_NAMESPACE,
        "derivation": "first five collision-free uint32 values from counter-separated SHA-256",
        "candidate_attempts": attempts,
        "selected_seeds": list(seeds),
        "known_prior_seed_values": list(prior),
        "repository_root": str(c2.REPO),
        "all_selected_have_zero_pre_reveal_matches": all(
            not row["repository_matches"] for row in attempts if row["accepted"]
        ),
    }
    search_path = output_dir / c2.FREEZE_DISJOINTNESS_FILENAME
    _write_new(search_path, search_receipt)
    seed_manifest = {
        "schema": c2.SEED_SCHEMA,
        "status": "frozen",
        "seed_namespace": c2.SEED_NAMESPACE,
        "seed_count": c2.SEED_COUNT,
        "closure_manifest_sha256": c2._sha256(closure_path),
        "derivation": search_receipt["derivation"],
        "c2_seeds": list(seeds),
        "prior_seed_values": list(prior),
        "repository_disjointness_checked_before_reveal": True,
        "disjointness_search_receipt_path": str(search_path),
        "disjointness_search_receipt_sha256": c2._sha256(search_path),
        "post_reveal_ignored_paths": [
            str(closure_path),
            str(search_path),
            str(output_dir / c2.FREEZE_SEED_FILENAME),
        ],
        "focal_schedule": {
            "anchor_steps": list(c2.ANCHOR_STEPS),
            "focal_users_per_step": c2.FOCAL_USERS_PER_STEP,
            "permutation_offset": c2.FOCAL_SCHEDULE_OFFSET,
        },
    }
    seed_path = output_dir / c2.FREEZE_SEED_FILENAME
    _write_new(seed_path, seed_manifest)
    loaded = c2.load_seed_manifest(seed_path, closure_path)
    if loaded != seeds:
        raise RuntimeError("C2 seed manifest did not round-trip exactly")
    print(json.dumps({"closure": str(closure_path), "seeds": str(seed_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
