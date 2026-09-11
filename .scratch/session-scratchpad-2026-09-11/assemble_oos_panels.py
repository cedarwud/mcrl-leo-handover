#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""OOSPANEL assembler: five schema panels from the per-anchor fragments.

The panel/receipt layout is PANELBUILD main()'s (same top-level, identity,
reference-object and anchor fields; the unmodified scorer validates it).  One
schema is assembled at a time.  Cross-schema physical identity (catalogue,
outcomes, reference profiles) is verified by per-anchor digests before any
panel is written.  Writes only below the OOSPANEL workspace.
"""
from __future__ import annotations

import gc
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oospanel as oos  # noqa: E402

FLAG_ASSERTION = (
    "synthetic_smoke_not_evidence=false asserts that every panel-carried "
    "physical field comes from exact physics on real development anchors; it "
    "does not assert that a checkpoint used during construction is evidence, "
    "does not determine global evaluator-path authority, and does not make "
    "this development panel claim-grade"
)
CLEAN_PATH = (
    "clean dense evaluator path: one fresh realised StepEvaluator(boundary_indices=(0,)) per "
    "anchor, BASE entering through evaluate_many with the candidate microbatches, profiles read "
    "from the dense cache only, scalar StepEvaluator.evaluate replaced by a raising stub "
    "(0 calls); endpoint outcomes re-evaluated in one separate fresh realised full-48 "
    "evaluate_many batch and equal to the catalogue outcomes"
)


def load(path: Path):
    return json.loads(path.read_text(encoding="ascii"))


def anchor_digests(anchor: dict) -> dict[str, str]:
    return {
        "identity": oos.canonical_sha256({k: anchor[k] for k in (
            "anchor_id", "world_id", "date", "world_seed", "base_profile_id",
            "certified_fixed_point_profile_id", "anytime_incumbent_profile_id")}),
        "catalogue": oos.canonical_sha256([p["profile_id"] for p in anchor["profiles"]]),
        "orders": oos.canonical_sha256([p["catalogue_order"] for p in anchor["profiles"]]),
        "outcomes": oos.canonical_sha256([p["outcome"] for p in anchor["profiles"]]),
        "coalition_sizes": oos.canonical_sha256([p["C3"]["coalition_size"] for p in anchor["profiles"]]),
    }


def main() -> int:
    oos.enforce_runtime()
    specs = oos.panel_specs()
    builder = oos.load_module("oospanel_assemble_upstream", oos.UPSTREAM)
    bindings = oos.bind_schemas(builder)
    cores = []
    for spec in specs:
        core = load(oos.fragment_paths(spec["panel_index"])["core"])
        if core["spec"] != spec:
            raise RuntimeError(f"core fragment spec drifted at {spec['panel_index']}")
        if core["guard_after"]["strict_surface_scalar_evaluate_calls"] != 0:
            raise RuntimeError("strict scalar-evaluate count is nonzero")
        for name in ("base", "certified_fixed_point", "anytime_incumbent"):
            if core["endpoint_batch"][name]["catalogue_outcome_equal"] is not True:
                raise RuntimeError("endpoint batch differs from catalogue outcome")
        cores.append(core)
    digests: dict[str, list[dict[str, str]]] = {}
    for schema in oos.SCHEMAS:
        rows = []
        for spec in specs:
            fragment = load(oos.fragment_paths(spec["panel_index"])[schema])
            if fragment["spec"] != spec:
                raise RuntimeError(f"{schema} fragment spec drifted at {spec['panel_index']}")
            rows.append(anchor_digests(fragment["anchor"]))
            del fragment
        digests[schema] = rows
        gc.collect()
    for schema in oos.SCHEMAS[1:]:
        if digests[schema] != digests["q1v1"]:
            raise RuntimeError(f"{schema}: physical content differs from q1v1")
    print("cross-schema physical identity PASS (20 anchors x 5 schemas)", flush=True)

    disjointness_path = oos.WORKSPACE / "out/disjointness.json"
    disjointness = load(disjointness_path)
    if disjointness["max_overlap_any_corpus"] != 0 or [d for d in disjointness["panel"]] != specs:
        raise RuntimeError("disjointness record is not the declared panel or overlap is nonzero")
    tapes = {core["tape"]["world_id"]: core["tape"] for core in cores}
    summary = []
    for schema in oos.SCHEMAS:
        anchors, audits = [], []
        for spec in specs:
            fragment = load(oos.fragment_paths(spec["panel_index"])[schema])
            anchors.append(fragment["anchor"])
            audits.append(fragment["audit"])
            del fragment
        widths = oos.EXPECTED_WIDTHS[schema]
        c1 = {len(pair[side]) for a in anchors for p in a["profiles"] for pair in p["C1"] for side in ("reference", "selected")}
        c2 = {len(pair[side]) for a in anchors for p in a["profiles"] for pair in p["C2"] for side in ("reference", "selected")}
        c3 = {len(p["C3"]["invariant_state"]) for a in anchors for p in a["profiles"]}
        if (c1, c2, c3) != ({widths["C1"]}, {widths["C2"]}, {widths["C3"]}):
            raise RuntimeError(f"{schema}: widths {c1}/{c2}/{c3} differ from {widths}")
        anchor_ids = [a["anchor_id"] for a in anchors]
        if anchor_ids != [s["anchor_id"] for s in specs]:
            raise RuntimeError(f"{schema}: anchor order drifted")
        panel = {
            "schema": builder.PANEL_SCHEMA,
            "panel_identity": {
                "name": f"panel-oos-{schema} out-of-sample development 20-anchor Stage-C scoring panel",
                "information_class": (
                    "causal decision-instant exact C1/C2 and physical C3 state; outcomes and "
                    "reference endpoints use realised 48-boundary full-buffer evaluation; "
                    + FLAG_ASSERTION + "; reference objects: " + CLEAN_PATH
                    + "; out-of-sample: 0 anchors and 0 worlds shared with the 22- and 93-anchor "
                    "exact training corpora or any other learner corpus found"
                ),
                "estimand": (
                    "pooled sum(full-buffer decoded bits)/sum(modelled partial-payload DC "
                    "joules) over 48 realised boundaries, with operational co-metrics"
                ),
                "numerator": builder.NUMERATOR, "energy_boundary": builder.ENERGY_BOUNDARY,
                "anchors": anchor_ids,
                "worlds": list(dict.fromkeys(a["world_id"] for a in anchors)),
                "dates": list(dict.fromkeys(str(a["date"])[:10] for a in anchors)),
                "world_seeds": list(dict.fromkeys(int(a["world_seed"]) for a in anchors)),
                "fixed_point_traversal_order": builder.TRAVERSAL,
                "provisioning_rule": (
                    "first ten anchors in exact-source within-world generation order (step "
                    "ascending; carriers nearest-eligible, stay-if-possible, random-masked) of "
                    "each of V025_PROBE/world/3 and V025_PROBE_R2/world/1, declared development "
                    "worlds whose start dates are not a training-source date of any learner "
                    "corpus; per anchor, the deployed bounded-union-v2 catalogue plus the two "
                    "named reference profiles; base first then configuration-ID order"
                ),
            },
            "reference_objects": {
                "certified_fixed_point": {
                    "name": "offline certified guarded-F first-improvement fixed point",
                    "construction": (
                        "exact realised boundary-0 deterministic cyclic first-improvement from "
                        "the anchor base; complete no-strict-improvement terminal certificate; "
                        + CLEAN_PATH
                    ),
                    "information_class": "exact realised boundary-0 oracle; no future-boundary information",
                    "budget_s": None, "fixed_point_traversal_order": builder.TRAVERSAL,
                },
                "anytime_incumbent": {
                    "name": "10 s anytime first-improvement incumbent",
                    "construction": (
                        "last fully evaluated and accepted iterate no later than 10.0 seconds "
                        "under the same ordered first-improvement traversal on the same clean "
                        "dense path; wall-clock dependent (host load recorded in receipt)"
                    ),
                    "information_class": "exact realised boundary-0 oracle available by the 10 s checkpoint",
                    "budget_s": 10.0, "fixed_point_traversal_order": builder.TRAVERSAL,
                },
            },
            "coordinator_budget_s": 10.0,
            "runner_instrumentation": {
                "producer": str(Path(oos.__file__).resolve()),
                "physics_evaluations_per_arm_recorded": False,
                "wall_clock_to_decision_per_arm_recorded": False,
                "missing_fields_required_addition": (
                    "the five-arm online runner must record per-arm physics evaluations and "
                    "wall-clock time to committed decision; panel construction timings are not substitutes"
                ),
            },
            "anchors": anchors,
            "synthetic_smoke_not_evidence": False,
            "full_buffer_no_demand_cap": True,
        }
        output = oos.ARTIFACTS / f"panel-oos-{schema}.json"
        if output.exists():
            raise RuntimeError(f"refusing to overwrite {output}")
        oos.streaming_json(output, panel)
        del panel, anchors
        gc.collect()
        digest = oos.sha256(output)
        output.with_name(output.name + ".sha256").write_text(f"{digest}  {output.name}\n", encoding="ascii")
        binding = bindings[schema]
        receipt = {
            "schema": "mcrl-v025-panelbuild-receipt-v1",
            "panel": str(output.resolve()), "panel_sha256": digest, "anchor_count": len(specs),
            "run_identity": {
                "producer_chain": {
                    "oospanel": str(Path(oos.__file__).resolve()),
                    "assembler": str(Path(__file__).resolve()),
                    "assembler_sha256": oos.sha256(Path(__file__).resolve()),
                    "upstream_panelbuild_build_anchor": str(oos.UPSTREAM),
                    "fail_closed_c3_pattern": "/home/sat/mcrl-v025-panelz-ws/scripts/build_panel_q1v2z.py",
                    "clean_reference_pattern": "/home/sat/mcrl-v025-rank2-ws/.scratch/cleanpath/run_cleanpath.py",
                },
                "input_sha256_at_build": cores[0]["input_sha256"],
                "sources": specs, "tapes": tapes,
                "feature_source_contract": (
                    "exact non-primitive shortlist rows (EXACTGEN2 view emulation) plus exact "
                    "full-legal regeneration for required actions outside the shortlist; "
                    "primitive fallback disabled"
                ),
                "outcome_cache": None,
            },
            "audits": audits,
            "encoder_binding": {
                "view": schema,
                "q1_schema_sha256": binding["q1_schema_sha256"],
                "q1_width": oos.EXPECTED_WIDTHS[schema]["C1"],
                "q2_schema_sha256": binding["q2_schema_sha256"],
                "q2_width": oos.EXPECTED_WIDTHS[schema]["C2"],
                "c3_member_width": oos.EXPECTED_WIDTHS[schema]["C3_MEMBER"],
                "c3_full_width": oos.EXPECTED_WIDTHS[schema]["C3"],
                "bound_from_launch_receipt": binding["run"] + "/launch-receipt.json",
                "launch_receipt_sha256": binding["launch_receipt_sha256"],
                "in_sample_panel_receipt_with_same_binding": binding["in_sample_panel_receipt"],
            },
            "c3_encoding": {
                "checkpoint_input_width": oos.EXPECTED_WIDTHS[schema]["C3"],
                "member_width": oos.EXPECTED_WIDTHS[schema]["C3_MEMBER"],
                "production_full_width": oos.EXPECTED_WIDTHS[schema]["C3"],
                "global_resource_feature_prefix_count": 6,
                "width_policy": "exact equality; suffix truncation forbidden",
                "fixture_limitation": None,
            },
            "reference_object_provenance": {
                "total_objects": 2 * len(specs), "clean_path_objects": 2 * len(specs),
                "contaminated_objects": 0, "panelceil_reused": 0,
                "selection_evaluator_path": CLEAN_PATH,
                "strict_surface_scalar_evaluate_calls": sum(
                    c["guard_after"]["strict_surface_scalar_evaluate_calls"] for c in cores),
                "endpoint_batch_equal_to_catalogue": sum(
                    all(c["endpoint_batch"][n]["catalogue_outcome_equal"] for n in
                        ("base", "certified_fixed_point", "anytime_incumbent")) for c in cores),
                "per_anchor": [{
                    "anchor_id": c["spec"]["anchor_id"],
                    "accepted_moves": c["reference_search"]["accepted_moves"],
                    "accepted_moves_by_10s": c["reference_search"]["accepted_moves_by_10s"],
                    "passes_including_certificate": c["reference_search"]["total_passes_including_certificate"],
                    "certified_equals_anytime": c["certified_equals_anytime"],
                    "termination_certificate_complete": c["reference_search"]["termination_certificate"]["complete"],
                } for c in cores],
            },
            "disjointness": {
                "record": str(disjointness_path), "record_sha256": oos.sha256(disjointness_path),
                "headline": disjointness["headline"],
                "max_overlap_any_corpus": disjointness["max_overlap_any_corpus"],
            },
            "synthetic_smoke_not_evidence": False, "synthetic_flag_semantics": FLAG_ASSERTION,
            "material_class": "development; out-of-sample with respect to every learner corpus found; not claim-grade",
            "global_evaluator_path_authority": "UNDETERMINED by EVALPATH-2026-09-10",
            "process_count_during_build_max": 3, "nice": os.getpriority(os.PRIO_PROCESS, 0),
            "thread_pins": {name: os.environ[name] for name in oos.THREAD_VARIABLES},
            "builder_peak_rss_bytes_max": max(c["peak_rss_bytes"] for c in cores),
            "assembler_peak_rss_bytes": oos.check_rss("assemble"),
        }
        receipt_path = oos.ARTIFACTS / f"panel-oos-{schema}.receipt.json"
        oos.streaming_json(receipt_path, receipt)
        summary.append((schema, digest, oos.EXPECTED_WIDTHS[schema]))
        print(f"panel-oos-{schema} sha256={digest} widths={oos.EXPECTED_WIDTHS[schema]} "
              f"peak_rss_bytes={oos.check_rss('assemble')}", flush=True)
        gc.collect()
    print(json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
