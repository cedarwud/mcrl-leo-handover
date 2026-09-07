#!/usr/bin/env python3
"""Reopen the isolated R4 world-1706 source artifact fail closed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcrl.runtime.ee_axis_lcsrs_c3_source_artifact import (
    load_v023_world_source_artifact,
)


WORLD = 2026121706
PREFLIGHT_SHA256 = (
    "8ce6c78ebfa0ef75192e139c0163064ccfb4ca796a76495df80daf17a377b4e6"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    artifact = load_v023_world_source_artifact(
        args.source,
        expected_world=WORLD,
        expected_preflight_sha256=PREFLIGHT_SHA256,
    )
    print(
        json.dumps(
            {
                "status": "PASS_R4_WORLD_1706_REPLAY",
                "world": artifact.world,
                "index_sha256": artifact.index_sha256,
                "sidecar_sha256": artifact.sidecar_sha256,
                "record_count": len(artifact.records),
                "pair_count": artifact.pair_count,
                "supported_count": artifact.supported_count,
                "placebo_eligible_count": artifact.placebo_eligible_count,
                "preflight_manifest_sha256": PREFLIGHT_SHA256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
