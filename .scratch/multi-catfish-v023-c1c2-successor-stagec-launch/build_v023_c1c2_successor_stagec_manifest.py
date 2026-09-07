#!/usr/bin/env python3
"""Build/check the external Stage-B/C code manifest and frozen pin."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

from stagec_common import CODE_MANIFEST_NAME, CODE_PIN_NAME, HERE, PHYSICAL, REPO


EXCLUDED = {
    CODE_MANIFEST_NAME,
    CODE_PIN_NAME,
    "V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json",
    "V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json.sha256",
    "early_baseline_admission.json",
    "early_baseline_admission.json.sha256",
}
SYNC_LIST_NAME = "V023-C1C2-SUCCESSOR-STAGEC-SYNC-LIST.txt"
EXCLUDED.add(SYNC_LIST_NAME)
def closure(repo: Path = REPO) -> list[str]:
    owned = [path for path in HERE.iterdir() if path.is_file() and path.name not in EXCLUDED and not path.name.endswith(".pyc")]
    physical = [path for path in PHYSICAL.iterdir() if path.is_file() and not path.name.endswith(".pyc")]
    paths = owned + physical
    closure_list = repo / ".scratch/multi-catfish-v023-controller-handoff-20260907/SHADOW-CLOSURE-LIST-2026-09-07.txt"
    if not closure_list.is_file() or closure_list.is_symlink():
        raise SystemExit(f"required closure list missing or symlinked: {closure_list}")
    for line in closure_list.read_text(encoding="ascii").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            fields = line.split()
            if len(fields) == 2 and len(fields[0]) == 64 and all(character in "0123456789abcdef" for character in fields[0]):
                line = fields[1]
            paths.append(repo / line)
    for relative in (
        ".scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py",
        ".scratch/multi-catfish-v023-two-route-source-training-runner/ee_axis_two_route_model.py",
        ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json",
        ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json.sha256",
        ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md",
        ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md",
        ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md.sha256",
        ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-07.md",
        ".scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-STAGEC-BASELINE-DECOUPLING-AND-EPISODE-CHUNKING-CODEX-GPT6-ASTRA-2026-09-07.md",
        "artifacts/PREREG-FROZEN-2026-08-25-R2.json",
        "artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt",
        "artifacts/training-2026-08-25-rerun01/main/status.json",
    ):
        paths.append(repo / relative)
    relative_paths: list[str] = []
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"closure member missing or symlinked: {path}")
        try:
            relative_paths.append(path.resolve().relative_to(repo.resolve()).as_posix())
        except ValueError as error:
            raise SystemExit(f"closure member escapes repository: {path}") from error
    result = sorted(set(relative_paths))
    if not result:
        raise SystemExit("empty Stage-C closure")
    return result


def render(repo: Path = REPO) -> bytes:
    rows = []
    for relative in closure(repo):
        data = (repo / relative).read_bytes()
        rows.append(f"{hashlib.sha256(data).hexdigest()}  {relative}")
    return ("\n".join(rows) + "\n").encode("ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = render(args.repo.resolve())
    sha = hashlib.sha256(payload).hexdigest()
    manifest = HERE / CODE_MANIFEST_NAME
    pin = HERE / CODE_PIN_NAME
    pin_payload = f"{sha}  {CODE_MANIFEST_NAME}\n".encode("ascii")
    sync = HERE / SYNC_LIST_NAME
    sync_payload = "".join(
        f"{relative}\n" for relative in [*closure(args.repo.resolve()), f"{HERE.relative_to(args.repo.resolve()).as_posix()}/{CODE_MANIFEST_NAME}", f"{HERE.relative_to(args.repo.resolve()).as_posix()}/{CODE_PIN_NAME}", f"{HERE.relative_to(args.repo.resolve()).as_posix()}/{SYNC_LIST_NAME}"]
    ).encode("ascii")
    if args.write:
        manifest.write_bytes(payload)
        pin.write_bytes(pin_payload)
        sync.write_bytes(sync_payload)
        print(f"STAGEC_CODE_MANIFEST_WRITTEN entries={len(closure(args.repo.resolve()))} sha256={sha}")
        return 0
    if manifest.read_bytes() != payload or pin.read_bytes() != pin_payload or sync.read_bytes() != sync_payload:
        print("STAGEC_CODE_MANIFEST_DRIFTED", file=sys.stderr)
        return 3
    print(f"STAGEC_CODE_MANIFEST_CURRENT entries={len(closure(args.repo.resolve()))} sha256={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
