#!/usr/bin/env python3
"""Build/check the external two-level successor launch manifest."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys

from successor_launch_common import (
    BASELINE_ADAPTER_REL, BINDINGS_NAME, BUNDLE_REL, CLOSURE_LIST_REL, CONTRACT_NAME,
    DECLARATION_NAME, FACTORY_REL, LAUNCH_MANIFEST_NAME,
    LAUNCH_MANIFEST_SCHEMA, LAUNCH_MANIFEST_SIDECAR, LEARNER_MANIFEST_NAME,
    MODEL_CONFIG_NAME, PROTOCOL_REL, PROVIDER_CONFIG_NAME, REVIEW_REL,
    RUNNER_REL, SUCCESSOR_REL, TARGET_ADAPTER_REL, TRAINER_REL,
    SuccessorLaunchError, assert_sync_coverage, canonical_bytes, directory_files,
    file_manifest, required_sync_closure,
    sidecar_path, validate_no_circular_digest, verify_launch_manifest,
    write_reproducible,
)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def closure_groups(repo: Path) -> list[dict[str, object]]:
    bundle_excluded = {
        LAUNCH_MANIFEST_NAME, LAUNCH_MANIFEST_SIDECAR,
        "PREFLIGHT-RECEIPT.json", "PREFLIGHT-RECEIPT.json.sha256",
    }
    for entry in (repo / "src", repo / FACTORY_REL):
        if str(entry) not in sys.path:
            sys.path.insert(0, str(entry))
    factory = importlib.import_module("v023_c1c2_provider_factory_v3")
    learner_paths = [Path(path) for path in factory.derive_learner_runtime_modules()]
    authoritative_closure = required_sync_closure(repo)
    candidates: list[tuple[str, list[Path]]] = [
        ("launch_bundle", [p for p in directory_files(repo, BUNDLE_REL) if p.name not in bundle_excluded]),
        ("learner_runtime", learner_paths),
        ("factory_v3", directory_files(repo, FACTORY_REL)),
        ("runner_package", directory_files(repo, RUNNER_REL)),
        ("adapters", [TARGET_ADAPTER_REL, BASELINE_ADAPTER_REL]),
        ("support_runtime", [PROTOCOL_REL, TRAINER_REL]),
        ("successor_authority", [
            SUCCESSOR_REL / CONTRACT_NAME,
            SUCCESSOR_REL / DECLARATION_NAME,
            SUCCESSOR_REL / (DECLARATION_NAME + ".sha256"),
            SUCCESSOR_REL / MODEL_CONFIG_NAME,
            SUCCESSOR_REL / (MODEL_CONFIG_NAME + ".sha256"),
            REVIEW_REL,
        ]),
        ("sync_closure_authority", [CLOSURE_LIST_REL]),
        ("complete_shadow_closure", authoritative_closure),
    ]
    result = []
    seen: set[Path] = set()
    for name, paths in candidates:
        unique = sorted(set(paths) - seen)
        if not unique:
            continue
        seen.update(unique)
        record = {"name": name, **file_manifest(repo, unique)}
        result.append(record)
    assert_sync_coverage(authoritative_closure, sorted(seen))
    return result


def render(repo: Path) -> bytes:
    groups = closure_groups(repo)
    payload = {
        "schema": LAUNCH_MANIFEST_SCHEMA,
        "groups": groups,
        "file_count": sum(len(group["files"]) for group in groups),
    }
    validate_no_circular_digest(payload)
    return canonical_bytes(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--paths", action="store_true", help="print authenticated payload paths")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    if not arguments.paths and not (arguments.write or arguments.check):
        parser.error("one of --write, --check, or --paths is required")
    repo = arguments.repo.resolve()
    path = repo / BUNDLE_REL / LAUNCH_MANIFEST_NAME
    try:
        if arguments.paths:
            result = verify_launch_manifest(repo, path)
            assert_sync_coverage(
                required_sync_closure(repo), [Path(item) for item in result["paths"]]
            )
            print("\n".join(result["paths"]))
            return 0
        raw = render(repo)
        import hashlib
        value = hashlib.sha256(raw).hexdigest()
        sidecar = f"{value}  {path.name}\n".encode("ascii")
        write_reproducible(path, raw, check=arguments.check)
        write_reproducible(sidecar_path(path), sidecar, check=arguments.check)
        if arguments.check:
            verify_launch_manifest(repo, path)
        print(
            f"SUCCESSOR_LAUNCH_MANIFEST_{'CURRENT' if arguments.check else 'WRITTEN'} "
            f"sha256={value}"
        )
        return 0
    except (OSError, KeyError, TypeError, SuccessorLaunchError) as error:
        print(f"SUCCESSOR_LAUNCH_MANIFEST_FAIL: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
