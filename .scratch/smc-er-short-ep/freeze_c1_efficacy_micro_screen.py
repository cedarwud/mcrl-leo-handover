#!/usr/bin/env python3
"""Close C1 efficacy-screen code/tests, then reveal eight disjoint seeds."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import run_c1_consumer_gate as screen  # noqa: E402
from c1_exp_corpus import load_verified_c1_corpus, sha256_file  # noqa: E402
from c1_pretransfer_gate_validator import validate_c1_pretransfer_result  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)


CLOSURE_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-closure-v1"
DISJOINTNESS_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-disjointness-v1"
INVENTORY_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-pre-reveal-inventory-v1"
CAMPAIGN_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-single-campaign-v1"
SEED_COUNT = 8
CAMPAIGN_LEDGER = HERE / "c1-efficacy-microscreen-campaign-v1.json"
EXECUTION_LEDGER = HERE / "c1-efficacy-microscreen-execution-v1.json"
FREEZE_LOCK = Path("/tmp/mcrl-smc-er-c1-efficacy-microscreen-freeze.lock")
TEST_FILES = screen.CLOSURE_TEST_FILES


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


def _acquire_freeze_lock():
    """Hold a process-scoped nonblocking lock across the entire freeze."""

    stream = FREEZE_LOCK.open("a+b")
    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        stream.close()
        raise RuntimeError("another C1 efficacy freeze is already in progress") from exc
    return stream


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _main_source_tree_binding(repo: Path = REPO) -> tuple[str, int]:
    root = Path(repo).resolve() / "src" / "mcrl"
    rows = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]
    if not rows:
        raise RuntimeError("Main source-tree authority is empty")
    return hashlib.sha256(_canonical_bytes(rows)).hexdigest(), len(rows)


def _validate_source_gate_verification(
    source_gate: Path, source_gate_verification: Path
) -> dict[str, Any]:
    """Use the same exact-replay prerequisite enforced by execution."""

    return screen._validate_source_gate_verification(
        source_gate, source_gate_verification
    )


def _normalise_pytest_stdout(value: str) -> str:
    """Remove pytest wall-clock text from the seed-derivation material."""

    return re.sub(r"\bin\s+[0-9]+(?:\.[0-9]+)?s\b", "in <elapsed>s", value.strip())


def _numeric_inventory(repo: Path = REPO) -> tuple[str, int]:
    """Hash the set of all pre-reveal integer tokens in durable repo files."""

    completed = subprocess.run(
        [
            "rg",
            "-o",
            "--no-filename",
            "--hidden",
            "--no-ignore",
            "--glob",
            "!.git/**",
            "--glob",
            "!.venv/**",
            "--glob",
            "!.pytest_cache/**",
            "--glob",
            "!.mypy_cache/**",
            "--glob",
            "!.ruff_cache/**",
            "--glob",
            "!__pycache__/**",
            "--glob",
            "!*.pyc",
            "--glob",
            "!.scratch/smc-er-short-ep/c1-efficacy-microscreen-campaign-v1.json",
            "--glob",
            "!.scratch/smc-er-short-ep/c1-efficacy-microscreen-execution-v1.json",
            "--pcre2",
            r"(?<![0-9])[0-9]{1,20}(?![0-9])",
            str(Path(repo).resolve()),
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(f"repository numeric inventory failed: {completed.stderr}")
    tokens = sorted({int(line) for line in completed.stdout.splitlines() if line})
    return hashlib.sha256(_canonical_bytes(tokens)).hexdigest(), len(tokens)


def _bindings(
    *,
    prereg: Path,
    source_gate: Path,
    source_gate_verification: Path,
    corpus_manifest: Path,
    corpus_verification: Path,
    pretransfer_gate: Path,
    checkpoint: Path,
    tle_root: Path,
) -> dict[str, Any]:
    if (
        prereg.resolve() != Path(CANONICAL_PREREG).resolve()
        or sha256_file(prereg) != CANONICAL_PREREG_BYTE_SHA256
    ):
        raise RuntimeError("C1 efficacy screen requires the canonical sealed preregistration")
    archive = TleArchive(tle_root.resolve())
    ephemeris = assert_ephemeris_matches_record(read_prereg(prereg), archive=archive)
    return screen._authority_bindings(
        prereg=prereg,
        source_gate=source_gate,
        source_gate_verification=source_gate_verification,
        corpus_manifest=corpus_manifest,
        corpus_verification=corpus_verification,
        pretransfer_gate=pretransfer_gate,
        checkpoint=checkpoint,
        archive=archive,
        ephemeris=ephemeris,
    )


def _prior_seeds(
    *,
    source_gate: Path,
    corpus_manifest: Path,
    pretransfer_gate: Path,
    checkpoint: Path,
) -> tuple[set[int], set[int], set[int]]:
    source_payload = json.loads(source_gate.read_text(encoding="utf-8"))
    corpus_payload = json.loads(corpus_manifest.read_text(encoding="utf-8"))
    payload = read_checkpoint(checkpoint, map_location="cpu")
    checkpoint_seeds = {
        int(payload.train_seed),
        int(payload.env_seed),
        int(payload.mobility_seed),
    }
    gate1_seeds = screen._gate1_prior_seeds(pretransfer_gate)
    prior = (
        screen._authenticated_parent_seed_values(
            source_payload, label="C1 Source Gate", base=source_gate.parent
        )
        | screen._authenticated_parent_seed_values(
            corpus_payload, label="C1 corpus build", base=corpus_manifest.parent
        )
        | checkpoint_seeds
        | gate1_seeds
        | {
            20260822,
            20260823,
            *range(2026082401, 2026082431),
            *range(2026082601, 2026082611),
            *range(2026082701, 2026082711),
            *range(2026082801, 2026082831),
        }
    )
    return prior, checkpoint_seeds, gate1_seeds


def _derive_candidate(closure_sha256: str, counter: int) -> int:
    material = _canonical_bytes(
        [screen.SEED_NAMESPACE, closure_sha256, int(counter)]
    )
    return int.from_bytes(hashlib.sha256(material).digest()[:4], "big")


def _runtime_derived_seeds(training_seed: int) -> dict[str, int]:
    return {
        "C1_specialist": int(training_seed) + 10_001,
        "C2_specialist": int(training_seed) + 20_003,
        "C3_specialist": int(training_seed) + 30_007,
    }


def _repo_matches(seed: int) -> tuple[str, ...]:
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
            "--glob",
            "!.pytest_cache/**",
            "--glob",
            "!.mypy_cache/**",
            "--glob",
            "!.ruff_cache/**",
            "--glob",
            "!*.pyc",
            "--glob",
            "!.scratch/smc-er-short-ep/c1-efficacy-microscreen-campaign-v1.json",
            "--glob",
            "!.scratch/smc-er-short-ep/c1-efficacy-microscreen-execution-v1.json",
            "--pcre2",
            rf"(?<![0-9]){int(seed)}(?![0-9])",
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


def derive_disjoint_seeds(
    *, closure_sha256: str, prior: set[int]
) -> tuple[tuple[int, ...], list[dict[str, Any]], dict[str, int]]:
    selected: list[int] = []
    attempts: list[dict[str, Any]] = []
    runtime_derived: dict[str, int] = {}
    counter = 0
    while len(selected) < SEED_COUNT:
        candidate = _derive_candidate(closure_sha256, counter)
        matches = _repo_matches(candidate)
        proposed_derived = _runtime_derived_seeds(candidate) if not selected else {}
        derived_matches = {
            name: list(_repo_matches(value))
            for name, value in proposed_derived.items()
        }
        reserved_runtime_values = set(runtime_derived.values())
        proposed_values = set(proposed_derived.values())
        accepted = bool(
            candidate not in prior
            and candidate not in selected
            and candidate not in reserved_runtime_values
            and not matches
            and not (proposed_values & prior)
            and not (proposed_values & set(selected))
            and len(proposed_values) == len(proposed_derived)
            and all(not value for value in derived_matches.values())
        )
        attempts.append(
            {
                "counter": counter,
                "candidate": candidate,
                "accepted": accepted,
                "known_prior_collision": candidate in prior,
                "selected_collision": candidate in selected,
                "runtime_derived_collision": candidate in reserved_runtime_values,
                "repository_matches": list(matches),
                "proposed_runtime_derived_seeds": proposed_derived,
                "proposed_runtime_derived_repository_matches": derived_matches,
            }
        )
        if accepted:
            selected.append(candidate)
            if len(selected) == 1:
                runtime_derived = proposed_derived
        counter += 1
        if counter > 10_000:
            raise RuntimeError("unable to derive eight disjoint C1 efficacy-screen seeds")
    return tuple(selected), attempts, runtime_derived


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-gate-result", type=Path, required=True)
    parser.add_argument("--source-gate-verification", type=Path, required=True)
    parser.add_argument("--corpus-manifest", type=Path, required=True)
    parser.add_argument("--corpus-verification", type=Path, required=True)
    parser.add_argument("--pretransfer-gate-result", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, default=CANONICAL_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    freeze_lock = _acquire_freeze_lock()
    output = args.output_dir.expanduser().resolve()
    source_gate = args.source_gate_result.expanduser().resolve()
    source_gate_verification = args.source_gate_verification.expanduser().resolve()
    corpus_manifest = args.corpus_manifest.expanduser().resolve()
    corpus_verification = args.corpus_verification.expanduser().resolve()
    pretransfer_gate = args.pretransfer_gate_result.expanduser().resolve()
    prereg = args.prereg.expanduser().resolve()
    tle_root = args.tle_root.expanduser().resolve()
    campaign_ledger = CAMPAIGN_LEDGER.resolve()
    if output.is_relative_to(REPO.resolve()):
        raise RuntimeError("C1 efficacy freeze artifacts must live outside the repository")
    if output.exists():
        raise FileExistsError(f"refusing to reuse freeze output: {output}")
    if campaign_ledger.exists():
        raise FileExistsError(
            f"the one allowed C1 efficacy campaign is already reserved: {campaign_ledger}"
        )
    if EXECUTION_LEDGER.resolve().exists():
        raise FileExistsError(
            f"a C1 efficacy execution ledger already exists: {EXECUTION_LEDGER.resolve()}"
        )
    for path in (
        source_gate,
        source_gate_verification,
        corpus_manifest,
        corpus_verification,
        pretransfer_gate,
        prereg,
        *TEST_FILES,
        screen.SPEC,
        screen.VALIDATOR,
        screen.FREEZE_TEST,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    pretransfer = validate_c1_pretransfer_result(pretransfer_gate)
    if pretransfer.get("status") != "PASS" or pretransfer.get("decision") != "ROUTE":
        raise RuntimeError("pre-transfer Gate 2 is not an independently validated PASS")
    _validate_source_gate_verification(source_gate, source_gate_verification)
    corpus_payload = json.loads(corpus_manifest.read_text(encoding="utf-8"))
    checkpoint = Path(corpus_payload["authority"]["checkpoint_path"]).resolve()
    screen._validate_pretransfer_lineage(
        pretransfer_gate,
        checkpoint=checkpoint,
        corpus_manifest=corpus_manifest,
    )
    corpus = load_verified_c1_corpus(
        corpus_manifest,
        expected_checkpoint_sha256=sha256_file(checkpoint),
    )
    verification = json.loads(corpus_verification.read_text(encoding="utf-8"))
    if (
        verification.get("status") != "PASS"
        or verification.get("manifest_sha256") != corpus.manifest_sha256
        or verification.get("corpus_sha256") != corpus.corpus_sha256
    ):
        raise RuntimeError("corpus verification is not bound to the supplied corpus")
    if (
        Path(corpus_payload["authority"]["source_gate_result_path"]).resolve()
        != source_gate
        or corpus_payload["authority"].get("source_gate_result_sha256")
        != sha256_file(source_gate)
    ):
        raise RuntimeError("source gate is not the supplied corpus predecessor")

    test_command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *[str(path.relative_to(REPO)) for path in TEST_FILES],
    ]
    tested = subprocess.run(
        test_command,
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if tested.returncode != 0:
        raise RuntimeError("C1 efficacy-screen closure tests failed before seed reveal")

    bindings = _bindings(
        prereg=prereg,
        source_gate=source_gate,
        source_gate_verification=source_gate_verification,
        corpus_manifest=corpus_manifest,
        corpus_verification=corpus_verification,
        pretransfer_gate=pretransfer_gate,
        checkpoint=checkpoint,
        tle_root=tle_root,
    )
    output.mkdir(parents=True, exist_ok=False)
    inventory_sha256, inventory_count = _numeric_inventory()
    inventory = {
        "schema": INVENTORY_SCHEMA,
        "status": "CAPTURED_BEFORE_SEED_DERIVATION",
        "claim_ceiling": screen.CLAIM_CEILING,
        "repository_root": str(REPO.resolve()),
        "numeric_token_set_sha256": inventory_sha256,
        "numeric_token_count": inventory_count,
        "excludes_only_generated_caches_and_campaign_ledgers": True,
    }
    inventory_path = output / "c1-efficacy-microscreen-pre-reveal-inventory-v1.json"
    _write_new(inventory_path, inventory)
    normalised_stdout = _normalise_pytest_stdout(tested.stdout)
    closure = {
        "schema": CLOSURE_SCHEMA,
        "status": "CLOSED_BEFORE_SEED_DERIVATION",
        "claim_ceiling": screen.CLAIM_CEILING,
        "bindings": bindings,
        "pre_reveal_inventory": {
            "path": str(inventory_path),
            "sha256": sha256_file(inventory_path),
            "numeric_token_set_sha256": inventory_sha256,
            "numeric_token_count": inventory_count,
        },
        "test_receipt": {
            "command": " ".join(test_command),
            "exit_code": tested.returncode,
            "normalised_stdout": normalised_stdout,
            "normalised_stdout_sha256": hashlib.sha256(
                normalised_stdout.encode("utf-8")
            ).hexdigest(),
            "wall_clock_text_excluded_from_seed_material": True,
        },
        "attestations": {
            "tests_completed_before_seed_derivation": True,
            "pretransfer_gate_revalidated_before_seed_derivation": True,
            "corpus_revalidated_before_seed_derivation": True,
        },
    }
    closure_path = output / "c1-efficacy-microscreen-closure-v1.json"
    _write_new(closure_path, closure)
    closure_sha = sha256_file(closure_path)

    manifest_path = output / "c1-efficacy-microscreen-seeds-v1.json"
    campaign = {
        "schema": CAMPAIGN_SCHEMA,
        "status": "SEALED_SINGLE_CAMPAIGN_BEFORE_SEED_REVEAL",
        "claim_ceiling": screen.CLAIM_CEILING,
        "closure_manifest_path": str(closure_path),
        "closure_manifest_sha256": closure_sha,
        "seed_manifest_path": str(manifest_path),
        "freeze_output_dir": str(output),
        "execution_ledger_path": str(EXECUTION_LEDGER.resolve()),
        "no_second_freeze_or_execution_is_authorised": True,
    }
    _write_new(campaign_ledger, campaign)

    prior, checkpoint_seeds, gate1_seeds = _prior_seeds(
        source_gate=source_gate,
        corpus_manifest=corpus_manifest,
        pretransfer_gate=pretransfer_gate,
        checkpoint=checkpoint,
    )
    seeds, attempts, runtime_derived = derive_disjoint_seeds(
        closure_sha256=closure_sha, prior=prior
    )
    search = {
        "schema": DISJOINTNESS_SCHEMA,
        "status": "PASS",
        "seed_namespace": screen.SEED_NAMESPACE,
        "closure_manifest_sha256": closure_sha,
        "derivation": "first eight collision-free uint32 values from closure-bound counter-separated SHA-256",
        "candidate_attempts": attempts,
        "selected_seeds": list(seeds),
        "runtime_derived_seeds": runtime_derived,
        "known_prior_seed_values": sorted(prior),
        "known_prior_seed_values_sha256": hashlib.sha256(
            _canonical_bytes(sorted(prior))
        ).hexdigest(),
        "pre_reveal_inventory_path": str(inventory_path),
        "pre_reveal_inventory_sha256": sha256_file(inventory_path),
        "all_selected_have_zero_pre_reveal_matches": all(
            not row["repository_matches"]
            and all(
                not matches
                for matches in row["proposed_runtime_derived_repository_matches"].values()
            )
            for row in attempts
            if row["accepted"]
        ),
    }
    search_path = output / "c1-efficacy-microscreen-disjointness-v1.json"
    _write_new(search_path, search)
    manifest = {
        "schema": screen.SEED_SCHEMA,
        "status": "frozen",
        "seed_namespace": screen.SEED_NAMESPACE,
        "seed_count": SEED_COUNT,
        "derivation": search["derivation"],
        "closure_manifest_path": str(closure_path),
        "closure_manifest_sha256": closure_sha,
        "disjointness_search_receipt_path": str(search_path),
        "disjointness_search_receipt_sha256": sha256_file(search_path),
        "repository_disjointness_checked_before_reveal": True,
        "pre_reveal_inventory_path": str(inventory_path),
        "pre_reveal_inventory_sha256": sha256_file(inventory_path),
        "campaign_ledger_path": str(campaign_ledger),
        "campaign_ledger_sha256": sha256_file(campaign_ledger),
        "execution_ledger_path": str(EXECUTION_LEDGER.resolve()),
        "forbidden_checkpoint_seeds": sorted(checkpoint_seeds),
        "forbidden_gate1_seeds": sorted(gate1_seeds),
        "training_seed": seeds[0],
        "environment_seed": seeds[1],
        "mobility_seed": seeds[2],
        "evaluation_seeds": list(seeds[3:]),
        "runtime_derived_seeds": runtime_derived,
        **bindings,
    }
    _write_new(manifest_path, manifest)
    print(
        json.dumps(
            {
                "closure": str(closure_path),
                "disjointness": str(search_path),
                "seeds": str(manifest_path),
            },
            sort_keys=True,
        )
    )
    freeze_lock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SEED_COUNT",
    "_derive_candidate",
    "_prior_seeds",
    "_repo_matches",
    "derive_disjoint_seeds",
]
