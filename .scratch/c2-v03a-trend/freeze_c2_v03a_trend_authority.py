#!/usr/bin/env python3
"""Freeze revised V0.3A trend authorities with the complete runtime code set."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_DIR = REPO / ".scratch" / "c2-v03"
for path in (HERE, C2_DIR, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_temporal_fork_episode_runner as c2_runner  # noqa: E402
import c2_v03a_trend_authority as authority  # noqa: E402


def _read(path: Path) -> Mapping[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise TypeError(f"authority source must be an object: {path}")
    return value


def freeze(source: Path, output: Path) -> dict[str, Any]:
    request = copy.deepcopy(dict(_read(source)))
    request.update(
        {
            "claim_ceiling": authority.CLAIM_CEILING,
            "formal_training_authorized": False,
            "c1_route_status": authority.C1_ROUTE_STATUS,
            "c2_route_status": authority.C2_ROUTE_STATUS,
            "c3_route_status": authority.C3_ROUTE_STATUS,
            "lr_selection_rule": copy.deepcopy(authority.LR_SELECTION_RULE),
        }
    )
    relative_paths = set(authority.REQUIRED_PINNED_FILES)
    relative_paths.update(
        path.relative_to(REPO).as_posix()
        for path in c2_runner._c2_code_authority_paths()
    )
    relative_paths.update(
        {
            str(request["canonical_prereg"]),
            str(request["c1_exp_corpus_manifest"]),
        }
    )
    missing = [relative for relative in sorted(relative_paths) if not (REPO / relative).is_file()]
    if missing:
        raise FileNotFoundError("runtime pin closure is missing: " + ", ".join(missing))
    request["pinned_files"] = {
        relative: authority.sha256_file(REPO / relative)
        for relative in sorted(relative_paths)
    }
    output = Path(output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite frozen authority: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(request, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return request


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    source_dir = Path(args.source_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite authority directory: {output_dir}")
    for name in ("1500-lr0p001.json", "1500-lr0p01.json"):
        freeze(source_dir / name, output_dir / name)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
