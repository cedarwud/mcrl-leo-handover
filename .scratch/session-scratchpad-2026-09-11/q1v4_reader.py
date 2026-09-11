#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Consumer entry point: select a Q1-v4 subset and run the unchanged production
reader on it, then (``--dry-run``) advance each of the five sealed arms by one
source epoch in memory.  No checkpoint is written; no production file is edited.

How a consumer selects a subset
-------------------------------
1. Pick a subset name: none | gain_only | congestion_only | both.
2. Its corpus is artifacts/q1v4-<subset>-exact-label-corpus-93-20260911 (a column
   projection of the stored 'both' vector; rows outside Q1 are byte-identical).
3. Call ``register_subset_adapter(runner, subset)`` in-process before
   ``runner.load_corpus(corpus)``.  The adapter is keyed by
   (subset Q1 digest, Q2 digest); the reader resolves the encoder from the rows'
   own digests, so a corpus/subset mismatch fails closed.
4. The reader's Q1 width, member width and C3 width are checked against the
   family table (fail closed).
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path("/home/sat/mcrl-v025-q1v4-ws")
SRC = Path("/home/sat/mcrl-v025-retrain-ws/src")
PRODUCTION_RUNNER = Path("/home/sat/mcrl-v025-exacttrain-ws/scripts/run_stagec_training_v2.py")
PRODUCTION_RUNNER_SHA256 = "47313ed05ff5e3a7c85d4b89e307dba534b5cef882a30d267970bbf35e900e1f"
FAMILY = ROOT / "artifacts/q1v4-schema-family.json"
RECEIPT = ROOT / "artifacts/q1v4-build-verification.json"
Q2_DIGEST = "a891dd9831d76bccd981cef054ff204fa1d49c3cf6e5f3265015f16f1057019c"
Q1_V1_DIGEST = "c002ea883a4ab727f9e00cc15866f5b9d37abca645963fd3db2f2db7c6cc887a"
ARMS = ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL")
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_runner():
    if file_sha256(PRODUCTION_RUNNER) != PRODUCTION_RUNNER_SHA256:
        raise RuntimeError("production runner drifted")
    sys.path.insert(0, str(SRC))
    spec = importlib.util.spec_from_file_location("q1v4_production_runner", PRODUCTION_RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["q1v4_production_runner"] = module
    spec.loader.exec_module(module)
    import mcrl
    if not str(Path(mcrl.__file__).resolve()).startswith(str(SRC)):
        raise RuntimeError(f"mcrl resolved outside the V0.25 tree: {mcrl.__file__}")
    return module


def register_subset_adapter(runner, subset: str) -> dict[str, object]:
    import mcrl.stagec_v025.encoders as encoders
    from mcrl.stagec_v025.canonical import StageCContractError

    family = json.loads(FAMILY.read_text(encoding="ascii"))
    entry = family["named"][subset]
    digest = entry["q1_schema_sha256"]
    schema = entry["schema"]
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                           allow_nan=False).encode("ascii")
    if hashlib.sha256(canonical).hexdigest() != digest:
        raise RuntimeError("family schema object does not hash to its recorded digest")
    features = tuple(encoders.FeatureSpec(f["name"], f["unit"], float.fromhex(f["scale_hex"]))
                     for f in schema["features"])
    if len(features) != entry["q1_width"]:
        raise RuntimeError("schema feature count disagrees with recorded Q1 width")
    key = (digest, Q2_DIGEST)
    try:
        existing = encoders.variant_for_digests(*key)
    except StageCContractError:
        existing = None
    if existing is not None:
        if tuple((f.name, f.unit, float(f.scale)) for f in existing.q1_features) != \
                tuple((f.name, f.unit, f.scale) for f in features):
            raise RuntimeError("a pre-registered encoder claims this digest with different features")
        variant, source = existing, "pre-registered"
    else:
        parent = encoders.variant_for_digests(Q1_V1_DIGEST, Q2_DIGEST)
        name = f"CORPUS_Q1_V4_{subset.upper()}_READER_ADAPTER"
        variant = encoders.EncoderVariant(
            name=name, q1_features=features, q2_features=parent.q2_features,
            q1_raw=lambda _item: (), q2_raw=parent.q2_raw, q1_schema=schema, q2_schema=parent.q2_schema,
            q1_schema_sha256=digest, q2_schema_sha256=Q2_DIGEST)
        encoders._REGISTRY[name] = variant
        encoders._DIGEST_INDEX[key] = name
        source = "in-process adapter"
    if runner.variant_for_digests(*key) is not variant:
        raise RuntimeError("production reader did not resolve the subset adapter")
    return {"subset": subset, "registration": source, "persistent_source_edits": False,
            "q1_schema_sha256": digest, "q1_width": variant.q1_width, "q2_width": variant.q2_width}


def dry_run(subset: str) -> dict[str, object]:
    started = time.perf_counter()
    runner = load_runner()
    runner._enforce_resources()
    if os.getpriority(os.PRIO_PROCESS, 0) < 16:
        raise RuntimeError("niceness below 16")
    family = json.loads(FAMILY.read_text(encoding="ascii"))
    receipt = json.loads(RECEIPT.read_text(encoding="ascii"))
    entry = family["named"][subset]
    corpus = Path(receipt["named_subsets"][subset]["corpus_root"])
    adapter = register_subset_adapter(runner, subset)
    batches, corpus_receipt, feature = runner.load_corpus(corpus)
    print(f"reader loaded subset={subset} rows={corpus_receipt['source_rows']} peak_rss={peak_rss_bytes()}", flush=True)
    checks = {
        "corpus_digest_matches_build": corpus_receipt["digest"] == receipt["named_subsets"][subset]["corpus_digest"],
        "q1_digest": feature["q1_schema_sha256"] == entry["q1_schema_sha256"],
        "q1_width": int(feature["q1_width"]) == entry["q1_width"],
        "q2_width": int(feature["q2_width"]) == 22,
        "member_width": int(batches["c3"].member_width) == entry["member_width"],
        "c3_width": int(batches["c3"].invariant_states.shape[1]) == entry["c3_width"],
        "anchors": len(corpus_receipt["anchor_list"]) == 93,
        "arm_inventory": tuple(runner.LEARNED_ARMS) == ARMS,
    }
    if not all(checks.values()):
        raise RuntimeError(f"fail-closed reader check failed: {checks}")
    seed = runner.seed_from_domain(f"Q1V4/20260911/one-step/{subset}")
    trainer = runner.V1LineageOrchestrator(
        learner_seed=seed, q1_batch=batches["pairs"]["C1"], q2_batch=batches["pairs"]["C2"],
        c3_batch=batches["c3"], neutral_sources=runner.default_synthetic_neutral_sources())

    def cursors():
        return {arm: {"C1": int(trainer.models[arm].q1.adam_step), "C2": int(trainer.models[arm].q2.adam_step),
                      "C3": int(trainer.models[arm].psi.network.adam_step)} for arm in ARMS}

    before = cursors()
    if any(v != 0 for arm in before.values() for v in arm.values()):
        raise RuntimeError("fresh trainer did not start at cursor zero")
    t0 = time.perf_counter()
    trainer.train_epoch()
    step_wall = time.perf_counter() - t0
    after = cursors()
    if any(v != 1 for arm in after.values() for v in arm.values()):
        raise RuntimeError(f"one step did not advance every arm/route exactly once: {after}")
    if trainer.completed_source_epochs != 1 or trainer.route_update_count != 3:
        raise RuntimeError("one-step source cursor drifted")
    result = {
        "subset": subset, "reader": "PASS", "adapter": adapter, "checks": checks,
        "corpus_digest": corpus_receipt["digest"], "source_rows": corpus_receipt["source_rows"],
        "coalition_rows": corpus_receipt["coalition_rows"], "feature": feature,
        "c3_member_width": int(batches["c3"].member_width), "c3_width": int(batches["c3"].invariant_states.shape[1]),
        "arm_inventory": list(ARMS), "adam_cursors_before": before, "adam_cursors_after": after,
        "completed_source_epochs": trainer.completed_source_epochs, "route_update_count": trainer.route_update_count,
        "one_step_wall_s": step_wall, "checkpoint_written": False, "losses_recorded_as_evidence": False,
        "production_runner_sha256": PRODUCTION_RUNNER_SHA256,
        "resources": {"peak_rss_bytes": peak_rss_bytes(), "nice": os.getpriority(os.PRIO_PROCESS, 0),
                      "threads": {n: os.environ.get(n) for n in THREAD_VARS}, "wall_s": time.perf_counter() - started},
    }
    del trainer, batches
    gc.collect()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("subset", choices=("none", "gain_only", "congestion_only", "both"))
    parser.add_argument("--dry-run", action="store_true", required=True)
    args = parser.parse_args()
    out = ROOT / f"artifacts/q1v4-dryrun-{args.subset}.json"
    if out.exists():
        raise RuntimeError(f"refusing to overwrite {out}")
    result = dry_run(args.subset)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"DRYRUN PASS subset={args.subset} c3_width={result['c3_width']} "
          f"cursors_after={json.dumps(result['adam_cursors_after'])}", flush=True)
    print(f"PEAK_RSS_BYTES={peak_rss_bytes()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
