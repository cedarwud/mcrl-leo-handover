#!/usr/bin/env python3
"""Read-only probe: run the controller's per-shard authentication against real shard dirs.

Monkeypatches only CLAIM_CEILING to the producer's literal (the known mismatch) so the
remaining checks (_read_receipt, _expected_schedule, _validate_shard) are exercised.
"""
import argparse, importlib.util, json, sys, traceback
from pathlib import Path
CK = Path(sys.argv[1]).resolve(); STAGINGS = [Path(p) for p in sys.argv[2].split(",")]
sys.path.insert(0, str(CK / "src"))
def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, CK / rel); m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m
ctrl = load("v023_c1c2_controller_probe", ".scratch/multi-catfish-v023-c1c2-target-generation-launch/run_v023_c1c2_targets_server.py")
gen = load("v023_c1c2_generator_probe", ".scratch/multi-catfish-v023-c1c2-target-generation/generate_v023_c1c2_targets.py")
print("controller CLAIM_CEILING:", ctrl.CLAIM_CEILING); print("generator  CLAIM_CEILING:", gen.CLAIM_CEILING)
ctrl.CLAIM_CEILING = gen.CLAIM_CEILING  # the one known mismatch, patched only in this probe process
args = argparse.Namespace(
    python=Path("/home/sat/mcrl-leo-handover/.venv/bin/python"),
    capture=Path("/home/sat/mcrl-v023-c1c2-predecision-20260906-r4/capture-run/panel-capture.json"),
    materialization_dir=Path("/home/sat/mcrl-v023-c1c2-predecision-20260906-r4/capture-run/materialized-source"),
    output=Path("/home/sat/probe-nonexistent-output"), tle_root=Path("/home/sat/mcrl-runtime/tle-frozen-20260820"),
    prereg=CK / "artifacts/PREREG-FROZEN-2026-08-25-R2.json",
    manifest=CK / ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json",
    manifest_digest=CK / ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256",
    execution_addendum=CK / "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md",
    users=100, max_workers=0,
)
try:
    schedule = ctrl._expected_schedule(args)
    print("expected schedule keys:", len(schedule), sorted(schedule)[:4], "...")
except Exception as e:
    print("EXPECTED_SCHEDULE_FAILED:", type(e).__name__, str(e)[:300]); traceback.print_exc(limit=2); sys.exit(2)
results = []
for staging in STAGINGS:
    for shard in sorted(staging.glob("*/world-*")):
        key = f"{shard.parent.name}:{shard.name.split('-')[1]}"
        rec = {"staging": staging.name, "key": key}
        try:
            receipt = ctrl._read_receipt(shard); rec["read_receipt"] = "PASS"
        except Exception as e:
            rec["read_receipt"] = f"FAIL: {type(e).__name__}: {str(e)[:200]}"; results.append(rec); print(json.dumps(rec)); continue
        try:
            ctrl._validate_shard(key, shard, receipt, schedule[key]); rec["validate_shard"] = "PASS"
        except Exception as e:
            rec["validate_shard"] = f"FAIL: {type(e).__name__}: {str(e)[:300]}"
        results.append(rec); print(json.dumps(rec))
print("PROBE_CONTROLLER_POSTSHARD_DONE", json.dumps({"shards": len(results), "read_pass": sum(r.get("read_receipt")=="PASS" for r in results), "validate_pass": sum(r.get("validate_shard")=="PASS" for r in results)}))
