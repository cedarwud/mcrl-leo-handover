#!/usr/bin/env python3
"""Print the frozen R7 verifier's first return and dispatch counts, read-only."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


CHECKOUT = Path("/home/sat/mcrl-v023-r7-launch-ready-20260906-r4")
RUN_ROOT = Path("/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1")
REPAIR = CHECKOUT / ".scratch/multi-catfish-v023-r7-domain-repair"
R7 = CHECKOUT / ".scratch/multi-catfish-v023-r7-launch-ready"
WORLDS = tuple(range(2026121801, 2026121809))
SEEDS = tuple(range(2026135201, 2026135204))
ARMS = ("informed", "matched_placebo")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    adapter = _load("v023_r7_domain_repair_diagnostic", REPAIR / "verify_v023_lcsrs_final_domain_repair.py")
    original = adapter._load_original()
    original_loader, counts = adapter._install_domain_dispatch(original)
    sources = [RUN_ROOT / "source" / f"world-{world}.json" for world in WORLDS]
    fits = [
        RUN_ROOT / "fit" / f"world-{world}" / f"seed-{seed}" / f"{arm}.json"
        for world in WORLDS
        for seed in SEEDS
        for arm in ARMS
    ]
    compositions = [
        RUN_ROOT / "composition" / f"world-{world}" / f"seed-{seed}" / f"{arm}.json"
        for world in WORLDS
        for seed in SEEDS
        for arm in ARMS
    ]
    try:
        result = original.verify_v023_final_gate(
            source_paths=tuple(sources),
            fit_paths=tuple(fits),
            composition_paths=tuple(compositions),
            source_manifest_path=RUN_ROOT / "source-manifest.json",
            expected_preflight_manifest_sha256=adapter.EXPECTED_PREFLIGHT_MANIFEST_SHA256,
            launch_manifest_path=R7 / "R7-PREFLIGHT-MANIFEST.json",
            launch_manifest_digest_path=R7 / "R7-PREFLIGHT-MANIFEST.sha256",
        )
    finally:
        original._load_npz = original_loader
    print(json.dumps({"dispatch_counts": counts, "result": result}, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
