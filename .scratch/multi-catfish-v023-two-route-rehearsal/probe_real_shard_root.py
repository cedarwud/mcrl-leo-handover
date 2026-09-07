#!/usr/bin/env python3
"""Read-only authentication and shape probe for real rehearsal shards."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

from rehearsal_real_shard_provider import (
    DISCOVERY_MODES,
    ROUTES,
    SOURCES,
    RehearsalRealShardProvider,
    RehearsalShardProviderError,
)


def _batch_shapes(batch: object) -> dict[str, list[int]]:
    target = (
        "target_surplus_bits"
        if hasattr(batch, "target_surplus_bits")
        else "normalized_target_deltas"
    )
    fields = (
        "states",
        "reference_actions",
        "candidate_actions",
        target,
        "action_masks",
    )
    return {field: list(np.asarray(getattr(batch, field)).shape) for field in fields}


def probe(root: str | Path) -> list[dict[str, Any]]:
    provider = RehearsalRealShardProvider(root, planned_epoch_budget=1)
    identity = provider.provider_identity_payload
    catalogue = identity["shard_digests_used"]
    lines: list[dict[str, Any]] = []
    for mode in DISCOVERY_MODES:
        lines.append(
            {
                "kind": "mode",
                "mode": mode,
                "worlds_used": identity["worlds_used_by_mode"][mode],
                "skipped": [
                    row
                    for row in identity["skipped_shards"]
                    if row["shard_dir"].split("/", 1)[0] == mode
                ],
                "digest_count": sum(row["mode"] == mode for row in catalogue),
            }
        )
    cursor = 0
    for route in ROUTES:
        for source in SOURCES:
            provided = provider.next_batch(
                route=route,
                source=source,
                update_cursor=cursor,
            )
            lines.append(
                {
                    "kind": "batch",
                    "route": route,
                    "source": source,
                    "file_id": provided.file_id,
                    "shapes": _batch_shapes(provided.batch),
                }
            )
        cursor += 1
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "shard_root",
        nargs="?",
        type=Path,
        default=Path("/home/sat/mcrl-v023-real-shards-rehearsal"),
    )
    args = parser.parse_args()
    try:
        lines = probe(args.shard_root)
    except RehearsalShardProviderError as cause:
        print(
            json.dumps(
                {
                    "kind": "error",
                    "error_type": type(cause).__name__,
                    "error": str(cause),
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2
    for line in lines:
        print(json.dumps(line, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
