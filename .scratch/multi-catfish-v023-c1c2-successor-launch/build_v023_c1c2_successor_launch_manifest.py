#!/usr/bin/env python3
"""Build/check the external two-level successor launch manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from successor_launch_common import (
    BUNDLE_REL, LAUNCH_MANIFEST_NAME, LAUNCH_MANIFEST_SCHEMA,
    SuccessorLaunchError, assert_sync_coverage, canonical_bytes, file_manifest,
    launch_manifest_additions, required_sync_closure,
    sidecar_path, validate_no_circular_digest, verify_launch_manifest,
    write_reproducible,
)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def closure_groups(repo: Path) -> list[dict[str, object]]:
    authoritative_closure = required_sync_closure(repo)
    candidates: list[tuple[str, list[Path]]] = [
        ("authoritative_shadow_closure", authoritative_closure),
        ("enumerated_bundle_additions", launch_manifest_additions(repo)),
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
