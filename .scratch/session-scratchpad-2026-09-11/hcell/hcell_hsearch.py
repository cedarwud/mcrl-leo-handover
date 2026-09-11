#!/usr/bin/env python3
"""HCELL step 2b: re-select the two objective-search arms WITH treatment H.

DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM.  Same rules as the clean path
(MYOPIC_GREEDY: nominal field, exact best choice, one ascending sweep;
FIRST_IMPROVEMENT_FP: realised field, first strict guarded improvement,
repeated to a zero-move certificate), same objective F = B - eta_ref E,
except that B is the H-cell bits: the one-boundary snapshot profile's bits
minus the zero-order-hold blackout removal of every interrupting event in
the sealed ledger (events versus the declared incumbent).

One fresh dense boundary-(0,) a-r0 evaluator per search arm per anchor, BASE
first through evaluate_many; endpoints in one fresh realised full-48 batch
plus the two single-boundary H side batches; scalar evaluate stubbed.
"""

from __future__ import annotations

from fractions import Fraction
import json
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hcell_common as hc  # noqa: E402

OUTPUT = hc.SCRATCH / "hcell-hsearch-receipt.json"
ARMS = ("NEAREST_ELIGIBLE", "MYOPIC_GREEDY_H", "FIRST_IMPROVEMENT_FP_H")


def dense_search_h(ctx, tape, step, base, incumbent, *, field, rule, converged, kind):
    runner, panel, calibration = ctx.runner, ctx.panel, ctx.calibration
    evaluator = hc.fresh_evaluator(ctx, tape, step, incumbent, field=field, boundaries=(0,))
    options, _census = runner._legal_options(tape, step)
    evaluator.evaluate_many((base,))
    base_profile = evaluator._evaluated.get(base.configuration_id)
    if base_profile is None:
        raise RuntimeError("dense BASE is invalid")
    guard = panel.served(base_profile)

    def objective(config, profile) -> Fraction:
        ledger = hc.h_ledger(ctx, tape, step, incumbent, config)
        removal = hc.h_removal_snapshot(ctx, ledger, profile.score.bits)
        return runner._objective(profile, calibration) - Fraction(removal)

    current = base
    passes = moves = comparisons = 0
    started = time.perf_counter()
    while True:
        moves_this_pass = 0
        for user in sorted(options):
            current_profile = evaluator._evaluated.get(current.configuration_id)
            if current_profile is None:
                raise RuntimeError("current profile absent from dense cache")
            current_value = objective(current, current_profile)
            candidates = tuple(
                panel.candidate(runner, base, current, user, identity, kind)
                for identity in options[user]
                if identity != current.mapping[user]
            )
            accepted = None
            if rule == "first":
                for offset in range(0, len(candidates), panel.UNILATERAL_BATCH_SIZE):
                    batch = candidates[offset:offset + panel.UNILATERAL_BATCH_SIZE]
                    evaluator.evaluate_many(batch)
                    for row in batch:
                        comparisons += 1
                        profile = evaluator._evaluated.get(row.configuration_id)
                        if profile is None or panel.served(profile) < guard:
                            continue
                        if objective(row, profile) > current_value:
                            accepted = row
                            break
                    if accepted is not None:
                        break
            elif rule == "best":
                for offset in range(0, len(candidates), panel.UNILATERAL_BATCH_SIZE):
                    evaluator.evaluate_many(candidates[offset:offset + panel.UNILATERAL_BATCH_SIZE])
                eligible = [(current_value, current.configuration_id, current)]
                for row in candidates:
                    comparisons += 1
                    profile = evaluator._evaluated.get(row.configuration_id)
                    if profile is None or panel.served(profile) < guard:
                        continue
                    eligible.append((objective(row, profile), row.configuration_id, row))
                selected = min(eligible, key=lambda item: (-item[0], item[1]))[2]
                if selected.mapping[user] != current.mapping[user]:
                    accepted = selected
            else:
                raise ValueError(rule)
            if accepted is not None:
                current = accepted
                moves += 1
                moves_this_pass += 1
        passes += 1
        if not converged or moves_this_pass == 0:
            break
        if passes > 100:
            raise RuntimeError("search exceeded 100 passes")
    detail = {"field": field, "rule": rule, "moves": moves,
              "passes_including_certificate": passes, "guard": guard,
              "comparisons": comparisons, "selection_seconds": time.perf_counter() - started,
              "physical_boundary_evaluations": evaluator.physical_evaluations}
    del evaluator
    hc.gc.collect()
    return current, detail


def main() -> int:
    hc.check_runtime()
    started = time.perf_counter()
    ctx = hc.setup(with_crowd=False)
    runner = ctx.runner
    frozen = hc.frozen_panel(ctx)
    clean = json.loads(hc.CLEANPATH_RECEIPT.read_text(encoding="utf-8"))
    if clean["receipt_sha256"] != ctx.cleanpath.canonical_digest(clean):
        raise RuntimeError("clean-path receipt digest failed")
    hc.install_scalar_stub(runner)
    tape, tape_record = hc.build_tape(ctx)
    if tape.digest != clean["world_tape"]["digest"]:
        raise RuntimeError("world tape digest differs from the clean-path receipt")
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB after tape", flush=True)
    payload = {"schema": "mcrl-v025-hcell-hsearch-v1", "status": "RUNNING",
               "claim_status": "DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM",
               "world_tape": tape_record, "sources": ctx.sources,
               "selection_objective": "F_H = (snapshot bits - ZOH blackout removal) - eta_ref * joules; Phi excluded as on the clean path",
               "anchors": []}
    runner_sha = hc.sha256(Path(__file__))
    payload["runner_sha256_pending"] = runner_sha
    resumed = {}
    if OUTPUT.exists():
        old = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if (old.get("status") == "RUNNING" and old.get("runner_sha256_pending") == runner_sha
                and old.get("sources") == ctx.sources
                and old.get("world_tape", {}).get("digest") == tape_record["digest"]):
            resumed = {int(a["global_anchor_index"]): a for a in old.get("anchors", [])}
            print(f"resuming: {len(resumed)} anchors already complete", flush=True)
    payload["resumed_anchor_indices"] = sorted(resumed)
    for position, panel_row in enumerate(frozen, 1):
        if int(panel_row["global_anchor_index"]) in resumed:
            payload["anchors"].append(resumed[int(panel_row["global_anchor_index"])])
            print(f"anchor {position}/{len(frozen)} resumed from receipt", flush=True)
            continue
        index = int(panel_row["global_anchor_index"])
        step = int(panel_row["step_index"])
        carrier = str(panel_row["carrier"])
        base = runner._base_configuration(tape, step, carrier)
        incumbent = runner._base_configuration(tape, max(0, step - 1), carrier)
        configs, details = {"NEAREST_ELIGIBLE": base}, {}
        configs["MYOPIC_GREEDY_H"], details["MYOPIC_GREEDY_H"] = dense_search_h(
            ctx, tape, step, base, incumbent, field="nominal", rule="best", converged=False,
            kind="cleanpath-myopic-greedy")
        configs["FIRST_IMPROVEMENT_FP_H"], details["FIRST_IMPROVEMENT_FP_H"] = dense_search_h(
            ctx, tape, step, base, incumbent, field="realised", rule="first", converged=True,
            kind="cleanpath-first-improvement")
        unique = {}
        for name in ARMS:
            unique.setdefault(configs[name].configuration_id, configs[name])
        batch = tuple(unique.values())
        endpoint = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised",
                                      boundaries=tuple(range(48)))
        endpoint.evaluate_many(batch)
        side0 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(0,))
        side0.evaluate_many(batch)
        side1 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(1,))
        side1.evaluate_many(batch)
        clean_arms = clean["anchors"][index]["arms"]
        arms = {}
        for name in ARMS:
            config = configs[name]
            profile = endpoint._evaluated[config.configuration_id]
            r0, d0 = hc.per_user_rates(ctx, side0._evaluated[config.configuration_id])
            r1, d1 = hc.per_user_rates(ctx, side1._evaluated[config.configuration_id])
            ledger = hc.h_ledger(ctx, tape, step, incumbent, config)
            removed, _useful, rinfo = hc.h_removal_endpoint(ctx, ledger, r0, r1, d0, d1)
            reference = {"MYOPIC_GREEDY_H": "MYOPIC_GREEDY",
                         "FIRST_IMPROVEMENT_FP_H": "FIRST_IMPROVEMENT_FP",
                         "NEAREST_ELIGIBLE": "NEAREST_ELIGIBLE"}[name]
            arms[name] = {
                "configuration_id": config.configuration_id,
                "same_configuration_as_a0_selected_cleanpath": (
                    config.configuration_id == clean_arms[reference]["configuration_id"]),
                "a0": hc.cell_metrics(ctx, profile),
                "aH": hc.cell_metrics(ctx, profile, removed),
                "events": hc.event_census(ctx, tape, step, incumbent, config),
                "h_removed_bits": math.fsum(removed.values()),
                "selection": details.get(name),
            }
        payload["anchors"].append({"global_anchor_index": index, "step_index": step,
                                   "carrier": carrier, "arms": arms,
                                   "peak_rss_bytes": hc.peak_rss_bytes()})
        del endpoint, side0, side1
        hc.gc.collect()
        hc.check_runtime()
        payload["scalar_evaluate_calls"] = hc.SCALAR_CALLS["count"]
        hc.atomic_write(OUTPUT, payload)
        print(f"anchor {position}/{len(frozen)} completed peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB "
              + json.dumps({n: [arms[n]["same_configuration_as_a0_selected_cleanpath"],
                                arms[n]["events"]["h_events"],
                                (details.get(n) or {}).get("moves")] for n in ARMS}), flush=True)
    pooled = {}
    for name in ARMS:
        rows = [a["arms"][name] for a in payload["anchors"]]
        pooled[name] = {
            "a0": hc.pool_rows([r["a0"] for r in rows]),
            "aH": hc.pool_rows([r["aH"] for r in rows]),
            "h_events": sum(int(r["events"]["h_events"]) for r in rows),
            "anchors_same_configuration_as_a0_selected": sum(
                bool(r["same_configuration_as_a0_selected_cleanpath"]) for r in rows),
        }
    payload["pooled"] = pooled
    payload["scalar_evaluate_calls"] = hc.SCALAR_CALLS["count"]
    assert hc.SCALAR_CALLS["count"] == 0
    payload["status"] = "COMPLETE"
    payload["runtime"] = hc.runtime_record()
    payload["wall_seconds"] = time.perf_counter() - started
    payload["runner_sha256"] = hc.sha256(Path(__file__))
    hc.atomic_write(OUTPUT, payload)
    print(json.dumps(pooled, indent=1), flush=True)
    print(f"scalar_evaluate_calls={hc.SCALAR_CALLS['count']}", flush=True)
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB final ({hc.peak_rss_bytes()} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
