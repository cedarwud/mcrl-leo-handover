#!/usr/bin/env python3
"""Independently verify a sealed C1 EXP/control corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from c1_exp_corpus import load_verified_c1_corpus


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = load_verified_c1_corpus(args.manifest)
    local = corpus.prefill_bundles(informed=True)
    control = corpus.prefill_bundles(informed=False)
    payload = {
        "schema": "smc-er-c1-exp-corpus-verification-v1",
        "status": "PASS",
        "claim_ceiling": "C1_SPECIALIST_PREFILL_ONLY_NEVER_MAIN",
        "manifest_path": str(corpus.manifest_path),
        "manifest_sha256": corpus.manifest_sha256,
        "corpus_path": str(corpus.corpus_path),
        "corpus_sha256": corpus.corpus_sha256,
        "checkpoint_sha256": corpus.checkpoint_sha256,
        "tle_file_set_sha256": corpus.tle_file_set_sha256,
        "state_dim": corpus.state_dim,
        "action_dim": corpus.action_dim,
        "selected_bundles": {"local": len(local), "control": len(control)},
        "branch_ids_disjoint": not bool(
            {bundle.bundle_id for bundle in local}
            & {bundle.bundle_id for bundle in control}
        ),
        "enters_main": False,
    }
    args.output.expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.expanduser().resolve().write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(args.output.expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
