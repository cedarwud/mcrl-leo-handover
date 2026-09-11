#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""OOSPANEL encoding/reference-path validation on in-sample world-1 anchor 000.

Reads (never writes) the authenticated training-corpus view shards for global
anchor 000 of each schema and the RANK2 clean-path receipt.  Rebuilds the same
anchor with the OOSPANEL encoders and clean first-improvement, then compares:

* every exact-source row's Q1/Q2 state per schema (row inventory + values);
* the clean fixed point's assignments/bits/joules against RANK2 anchor 0.

Development anchor 000 only; no evaluation-only claim date is read.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oospanel as oos  # noqa: E402

VIEWS = {
    "q1v1": "/home/sat/mcrl-v025-coalgen-ws/artifacts/v025-stagec-c3-coalition-20260910-BUILD_NOT_CLAIM/corpus/.staging-separated-v1/global-000/views/world-1/BUILD_NOT_CLAIM-exact-source-anchor-000.jsonl",
    "q1v2": "/home/sat/mcrl-v025-design-ws/artifacts/v025-stagec-c3-coalition-q1v2-20260910-BUILD_NOT_CLAIM/corpus/.staging-separated-v1/global-000/views/world-1/BUILD_NOT_CLAIM-exact-source-anchor-000.jsonl",
    "q1v2z": "/home/sat/mcrl-v025-design-ws/artifacts/v025-stagec-c3-coalition-q1v2z-20260910-BUILD_NOT_CLAIM/corpus/.staging-separated-v1/global-000/views/world-1/BUILD_NOT_CLAIM-exact-source-anchor-000.jsonl",
    "q1v3": "/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-exact-label-corpus-20260910/views/world-1/BUILD_NOT_CLAIM-exact-source-anchor-000.jsonl",
    "q1v3-control": "/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-control-exact-label-corpus-20260910/views/world-1/BUILD_NOT_CLAIM-exact-source-anchor-000.jsonl",
}
RANK2 = Path("/home/sat/mcrl-v025-rank2-ws/.scratch/cleanpath/cleanpath-receipt.json")
OUT = oos.WORKSPACE / "out/validate-encoding-anchor000.json"


def read_view(path: str):
    oos_sha = oos.sha256(Path(path))
    sidecar = Path(path + ".sha256").read_text(encoding="ascii").split()[0]
    if sidecar != oos_sha:
        raise RuntimeError(f"sidecar mismatch {path}")
    lines = Path(path).read_bytes().splitlines()
    header = json.loads(lines[0])
    rows = {}
    for raw in lines[1:]:
        payload = json.loads(raw)
        action = payload["action"]
        key = (int(payload["user_id"]), None if action["norad_id"] is None else (
            int(action["norad_id"]), int(action["beam_chain_id"])))
        rows[key] = (
            tuple(float.fromhex(v) for v in payload["q1_state"]),
            tuple(float.fromhex(v) for v in payload["q2_state"]),
            bool(payload["outage"]),
        )
    return header, rows, oos_sha


def compare(encoded: dict, reference: dict) -> dict:
    keys_equal = set(encoded) == set(reference)
    exact = 0
    max_q1 = max_q2 = 0.0
    worst = None
    for key in set(encoded) & set(reference):
        row = encoded[key]
        q1, q2, outage = reference[key]
        d1 = max((abs(a - b) for a, b in zip(row.q1_state, q1, strict=True)), default=0.0)
        d2 = max((abs(a - b) for a, b in zip(row.q2_state, q2, strict=True)), default=0.0)
        if d1 > max_q1:
            max_q1, worst = d1, [key[0], None if key[1] is None else list(key[1])]
        max_q2 = max(max_q2, d2)
        exact += int(tuple(row.q1_state) == q1 and tuple(row.q2_state) == q2 and row.outage == outage)
    return {
        "row_keys_equal": keys_equal, "encoded_rows": len(encoded), "reference_rows": len(reference),
        "rows_bit_identical": exact, "max_abs_q1_difference": max_q1,
        "max_abs_q2_difference": max_q2, "worst_q1_row": worst,
    }


def main() -> int:
    ctx = oos.Context()
    tape, provider = ctx.world("V025_PROBE/world/1")
    step, carrier = 0, "nearest-eligible"
    resolver = ctx.resolver("V025_PROBE/world/1", tape, provider, step)
    base = ctx.engine._base_configuration(tape, step, carrier)
    incumbent = ctx.engine._base_configuration(tape, 0, carrier)
    previous = ctx.pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK
    ctx.pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK = False
    try:
        built = ctx.pilot._build_anchor_rows(
            tape=tape, setting=ctx.setting, run_setting=ctx.run_setting,
            calibration=ctx.calibration, step_index=step, carrier=carrier,
            anchor_index=0, include_coalition=False, full_legal_actions=False,
        )
    finally:
        ctx.pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK = previous
    encoded, stats = oos.encode_all(ctx, built, tape, step, resolver)
    print(f"anchor 1/1 encoded rows={stats['rows']} peak_rss_bytes={oos.check_rss('encode')}", flush=True)
    result = {"anchor": "V025_PROBE/world/1|0|nearest-eligible", "tape": ctx.tape_records["V025_PROBE/world/1"],
              "encoding_stats": stats, "schemas": {}}
    for schema, path in VIEWS.items():
        header, reference, digest = read_view(path)
        cmp = compare(encoded[schema], reference)
        cmp.update({"view": path, "view_sha256": digest, "header_q1_slots": header.get("q1_slots")})
        result["schemas"][schema] = cmp
        print(schema, json.dumps({k: cmp[k] for k in ("row_keys_equal", "rows_bit_identical", "reference_rows", "max_abs_q1_difference", "max_abs_q2_difference")}), flush=True)

    # Clean reference path vs RANK2 clean fixed point at the same anchor.
    clean = oos.make_clean_first_improvement(ctx)
    run = clean(ctx.engine, ctx.calibration, tape, step, base, incumbent, ctx.run_setting)
    rank2 = json.loads(RANK2.read_text(encoding="utf-8"))
    r2 = rank2["anchors"][0]
    if r2["anchor_id"] != "V025_PROBE/world/1|0|nearest-eligible":
        raise RuntimeError("RANK2 anchor 0 identity drifted")
    r2fp = r2["arms"]["FIRST_IMPROVEMENT_FP"]
    mine = [[user, None if identity is None else list(identity)] for user, identity in run.selected.assignments]
    evaluator = ctx.engine.StepEvaluator(
        tape, ctx.engine._setting("a-r0"), step, transition_from=incumbent,
        cell_rekeyed_users=ctx.engine._rekeyed_users(tape, step), field="realised",
        counter=ctx.engine.EvaluationCounter(), run_setting=ctx.run_setting,
        boundary_indices=tuple(range(48)),
    )
    oos.GUARD.strict_phase = "validation_endpoint"
    try:
        evaluator.evaluate_many((run.selected,))
    finally:
        oos.GUARD.strict_phase = None
    profile = evaluator._evaluated[run.selected.configuration_id]
    result["reference_path"] = {
        "clean_moves": run.receipt["accepted_moves"],
        "clean_passes": run.receipt["total_passes_including_certificate"],
        "rank2_moves": r2fp["selection"]["moves"],
        "rank2_passes": r2fp["selection"]["passes_including_certificate"],
        "assignments_equal_rank2": mine == r2fp["committed"]["assignments"],
        "bits_equal_rank2": float(profile.bits) == float(r2fp["committed"]["bits"]),
        "joules_equal_rank2": float(profile.joules) == float(r2fp["committed"]["joules"]),
        "scalar_evaluate_calls_strict": oos.GUARD.strict_calls,
        "rank2_receipt_sha256": oos.sha256(RANK2),
    }
    print("reference_path", json.dumps(result["reference_path"]), flush=True)
    result["guard"] = oos.GUARD.snapshot()
    result["peak_rss_bytes"] = oos.check_rss("final")
    oos.streaming_json(OUT, result)
    print(f"PEAK_RSS_BYTES={result['peak_rss_bytes']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
