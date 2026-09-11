#!/usr/bin/env python3
"""HCELL steps 2-3 (+E_HO accounting): size of treatment H on the frozen panel.

DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM.  Learner-free; 12 frozen development
anchors only.

Per anchor:
  * configurations: NEAREST_ELIGIBLE (= carrier BASE), RANDOM, ROUND_ROBIN,
    RSS_MAX, MYOPIC_GREEDY and FIRST_IMPROVEMENT_FP rebuilt with the verified
    clean-path runner's own functions (search arms: one fresh dense
    boundary-0 evaluator each, BASE first through evaluate_many), CROWDED
    (the crowding runner's exact minimum-cover assignment), STAY_ELSE_RSS
    (keep the declared incumbent's physical identity when it is legal at t,
    otherwise the RSS_MAX choice).
  * endpoint: ONE separate fresh realised dense full-48 StepEvaluator and ONE
    evaluate_many call containing every configuration (BASE included).
  * H rescore side batches: one fresh realised dense boundary-(0,) and one
    boundary-(1,) evaluator, each ONE evaluate_many call on the same set, for
    the per-user rates that the sealed linear blackout integral needs.
  * StepEvaluator.evaluate is replaced class-wide by a raising stub before the
    tape is built; zero calls are asserted at exit.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hcell_common as hc  # noqa: E402

OUTPUT = hc.SCRATCH / "hcell-main-receipt.json"
ARMS = ("NEAREST_ELIGIBLE", "RANDOM", "ROUND_ROBIN", "RSS_MAX", "MYOPIC_GREEDY",
        "FIRST_IMPROVEMENT_FP", "CROWDED", "STAY_ELSE_RSS")
CLEAN_ARMS = ("RANDOM", "ROUND_ROBIN", "RSS_MAX", "NEAREST_ELIGIBLE",
              "MYOPIC_GREEDY", "FIRST_IMPROVEMENT_FP")
PARITY_MBIT_PER_J = {
    "NEAREST_ELIGIBLE": 11.027760, "RSS_MAX": 41.621560, "MYOPIC_GREEDY": 31.078504,
    "FIRST_IMPROVEMENT_FP": 31.028111, "CROWDED": 46.110374,
    "RANDOM": 11.233999, "ROUND_ROBIN": 3.441227,
}


def stay_else_rss(ctx, tape, step, base, incumbent, rss):
    options, _ = ctx.runner._legal_options(tape, step)
    held = incumbent.mapping
    fallback = rss.mapping
    mapping = {}
    kept = 0
    for user, identities in sorted(options.items()):
        if not identities:
            mapping[user] = None
        elif held.get(user) is not None and held[user] in identities:
            mapping[user] = held[user]
            kept += 1
        else:
            mapping[user] = fallback[user]
    return ctx.runner._configuration(base, mapping, kind="hcell-stay-else-rss"), kept


def main() -> int:
    hc.check_runtime()
    started = time.perf_counter()
    ctx = hc.setup(with_crowd=True)
    runner = ctx.runner
    frozen = hc.frozen_panel(ctx)
    clean = json.loads(hc.CLEANPATH_RECEIPT.read_text(encoding="utf-8"))
    if clean.get("status") != "COMPLETE" or clean["receipt_sha256"] != ctx.cleanpath.canonical_digest(clean):
        raise RuntimeError("clean-path receipt digest failed")
    crowd = json.loads(hc.CROWD_RECEIPT.read_text(encoding="utf-8"))
    if crowd.get("status") != "COMPLETE" or crowd["receipt_sha256"] != ctx.crowd.canonical_digest(crowd):
        raise RuntimeError("crowding receipt digest failed")
    hc.install_scalar_stub(runner)
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB before tape", flush=True)
    tape, tape_record = hc.build_tape(ctx)
    if tape.digest != clean["world_tape"]["digest"]:
        raise RuntimeError("world tape digest differs from the clean-path receipt")
    hc.check_runtime()
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB after tape", flush=True)

    payload = {
        "schema": "mcrl-v025-hcell-main-v1",
        "status": "RUNNING",
        "claim_status": "DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM",
        "panel": [{k: r[k] for k in ("global_anchor_index", "world_id", "step_index", "carrier")}
                  for r in frozen],
        "world_tape": tape_record,
        "sources": ctx.sources,
        "cleanpath_receipt_sha256": clean["receipt_sha256"],
        "crowd_receipt_sha256": crowd["receipt_sha256"],
        "interruption_constants": ctx.interruption_constants,
        "e_ho_values_j": list(hc.E_HO_VALUES_J),
        "h_event_kinds": list(hc.H_KINDS),
        "evaluator_path": {
            "selection": "clean-path dense_search: one fresh boundary-(0,) a-r0 evaluator per search arm, BASE through evaluate_many first",
            "endpoint": "one fresh realised full-48 a-r0 evaluator, one evaluate_many call with all arms (BASE included)",
            "h_side_batches": "one fresh realised boundary-(0,) and one boundary-(1,) evaluator, one evaluate_many call each, same arm set",
            "scalar_evaluate": "class-wide raising stub installed before tape construction",
        },
        "anchors": [],
    }
    beam_sets_by_step = {}
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
        anchor_started = time.perf_counter()
        index = int(panel_row["global_anchor_index"])
        step = int(panel_row["step_index"])
        carrier = str(panel_row["carrier"])
        base = runner._base_configuration(tape, step, carrier)
        incumbent = runner._base_configuration(tape, max(0, step - 1), carrier)
        options, _ = runner._legal_options(tape, step)
        configs = {
            "NEAREST_ELIGIBLE": base,
            "RANDOM": ctx.cleanpath.random_configuration(runner, tape, step, base, index),
            "ROUND_ROBIN": ctx.cleanpath.round_robin_configuration(runner, tape, step, base),
            "RSS_MAX": ctx.cleanpath.rss_max_configuration(runner, tape, step, base),
        }
        search = {}
        configs["MYOPIC_GREEDY"], search["MYOPIC_GREEDY"] = ctx.cleanpath.dense_search(
            ctx.panel, runner, ctx.calibration, tape, step, base, incumbent, ctx.run_setting,
            field="nominal", rule="best", converged=False, kind="cleanpath-myopic-greedy",
        )
        configs["FIRST_IMPROVEMENT_FP"], search["FIRST_IMPROVEMENT_FP"] = ctx.cleanpath.dense_search(
            ctx.panel, runner, ctx.calibration, tape, step, base, incumbent, ctx.run_setting,
            field="realised", rule="first", converged=True, kind="cleanpath-first-improvement",
        )
        if step not in beam_sets_by_step:
            beam_sets_by_step[step] = ctx.crowd.nested_beam_sets(options)
        crowded_mapping = ctx.crowd.assignment_for_beams(options, beam_sets_by_step[step][0])
        configs["CROWDED"] = runner._configuration(base, crowded_mapping, kind="crowding-cost-ladder")
        configs["STAY_ELSE_RSS"], kept = stay_else_rss(ctx, tape, step, base, incumbent,
                                                       configs["RSS_MAX"])

        clean_anchor = clean["anchors"][index]
        if int(clean_anchor["global_anchor_index"]) != index:
            raise RuntimeError("clean-path anchor order mismatch")
        id_match = {name: configs[name].configuration_id == clean_anchor["arms"][name]["configuration_id"]
                    for name in CLEAN_ARMS}

        unique = {}
        for name in ARMS:
            unique.setdefault(configs[name].configuration_id, configs[name])
        batch = tuple(unique.values())
        if base.configuration_id != batch[0].configuration_id:
            raise RuntimeError("BASE must lead the endpoint batch")
        endpoint = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised",
                                      boundaries=tuple(range(48)))
        endpoint.evaluate_many(batch)
        side0 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(0,))
        side0.evaluate_many(batch)
        side1 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(1,))
        side1.evaluate_many(batch)
        for evaluator in (endpoint, side0, side1):
            if base.configuration_id not in evaluator._evaluated:
                raise RuntimeError("BASE absent from a dense evaluator cache")

        arms = {}
        for name in ARMS:
            config = configs[name]
            profile = endpoint._evaluated.get(config.configuration_id)
            if profile is None:
                raise RuntimeError(f"invalid endpoint profile for {name}")
            r0, d0 = hc.per_user_rates(ctx, side0._evaluated[config.configuration_id])
            r1, d1 = hc.per_user_rates(ctx, side1._evaluated[config.configuration_id])
            ledger = hc.h_ledger(ctx, tape, step, incumbent, config)
            removed, removed_useful, rinfo = hc.h_removal_endpoint(ctx, ledger, r0, r1, d0, d1)
            a0 = hc.cell_metrics(ctx, profile)
            dense_attained = sum(1 for v in profile.score.rate_target_attained.values() if v)
            if a0["rate_target_attained_count"] != dense_attained:
                raise RuntimeError("recomputed a0 attainment disagrees with the dense profile")
            aH = hc.cell_metrics(ctx, profile, removed)
            census = hc.event_census(ctx, tape, step, incumbent, config)
            if rinfo["blackout_users"] != census["h_events"]:
                raise RuntimeError("blackout users disagree with the interrupting-event census")
            arms[name] = {
                "configuration_id": config.configuration_id,
                "changed_users_vs_base": int(config.changed_users),
                "a0": a0,
                "aH": aH,
                "events": census,
                "h_removed_bits": math.fsum(removed.values()),
                "h_removed_useful_s": math.fsum(removed_useful.values()),
                "h_removed_bits_by_kind": rinfo["removed_bits_by_kind"],
                "h_blackout_users_zero_rate_at_t0": sum(1 for u in removed if r0[u] == 0.0),
                "decoding_s": math.fsum(profile.score.decoding_time_s.values()),
                "active_beams": len({i for i in config.mapping.values() if i is not None}),
            }
            if name in id_match:
                arms[name]["configuration_matches_cleanpath"] = id_match[name]
                committed = clean_anchor["arms"][name]["committed"]
                arms[name]["cleanpath_bits_delta"] = a0["bits"] - float(committed["bits"])
                arms[name]["cleanpath_joules_delta"] = a0["joules"] - float(committed["joules"])
            if name in search:
                arms[name]["selection"] = {k: search[name][k] for k in
                                           ("moves", "passes_including_certificate", "guard",
                                            "comparisons", "physical_boundary_evaluations")}
        # crowded parity against the crowding receipt's retained most-crowded row
        crowd_anchor = crowd["anchors"][index]
        if crowd_anchor["anchor_id"] != f"{tape.domain}|{step}|{carrier}":
            raise RuntimeError("crowding anchor order mismatch")
        crowded_row = min(crowd_anchor["ladder"], key=lambda r: int(r["active"]))
        arms["CROWDED"]["crowd_receipt_bits_delta"] = arms["CROWDED"]["a0"]["bits"] - float(crowded_row["bits"])
        arms["CROWDED"]["crowd_receipt_joules_delta"] = arms["CROWDED"]["a0"]["joules"] - float(crowded_row["joules"])
        arms["CROWDED"]["crowd_receipt_active"] = int(crowded_row["active"])
        arms["CROWDED"]["passes_base_served_guard"] = (
            arms["CROWDED"]["a0"]["served_count"] >= arms["NEAREST_ELIGIBLE"]["a0"]["served_count"])
        arms["STAY_ELSE_RSS"]["users_kept_on_incumbent"] = kept

        payload["anchors"].append({
            "global_anchor_index": index,
            "anchor_id": f"{tape.domain}|{step}|{carrier}",
            "step_index": step,
            "carrier": carrier,
            "incumbent_is_step": max(0, step - 1),
            "arms": arms,
            "endpoint_physical_boundary_evaluations": endpoint.physical_evaluations,
            "anchor_seconds": time.perf_counter() - anchor_started,
            "peak_rss_bytes": hc.peak_rss_bytes(),
        })
        del endpoint, side0, side1
        hc.gc.collect()
        hc.check_runtime()
        payload["scalar_evaluate_calls"] = hc.SCALAR_CALLS["count"]
        hc.atomic_write(OUTPUT, payload)
        print(f"anchor {position}/{len(frozen)} completed peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB "
              + json.dumps({name: [round(arms[name]["a0"]["bits"] / arms[name]["a0"]["joules"] / 1e6, 4),
                                   round(arms[name]["aH"]["bits"] / arms[name]["aH"]["joules"] / 1e6, 4),
                                   arms[name]["events"]["h_events"]] for name in ARMS})
              + f" ids={sum(id_match.values())}/6 t={time.perf_counter()-anchor_started:.1f}s", flush=True)

    pooled = {}
    for name in ARMS:
        rows = [a["arms"][name] for a in payload["anchors"]]
        a0 = hc.pool_rows([r["a0"] for r in rows])
        aH = hc.pool_rows([r["aH"] for r in rows])
        events = {k: sum(int(r["events"][k]) for r in rows) for k in (*hc.ALL_KINDS, "h_events")}
        eho = {}
        for e in hc.E_HO_VALUES_J:
            added = events["h_events"] * e
            eho[f"{e:g}J"] = {
                "added_joules": added,
                "added_fraction_of_pooled_joules": added / a0["joules"],
                "a0_plus_eho_ee_mbit_per_j": hc.eho_ee(a0["bits"], a0["joules"], events["h_events"], e),
                "aH_plus_eho_ee_mbit_per_j": hc.eho_ee(aH["bits"], aH["joules"], events["h_events"], e),
            }
        pooled[name] = {
            "a0": a0, "aH": aH, "events": events,
            "h_removed_bits": math.fsum(r["h_removed_bits"] for r in rows),
            "h_removed_useful_s": math.fsum(r["h_removed_useful_s"] for r in rows),
            "h_removed_bits_by_kind": {
                k: math.fsum(r["h_removed_bits_by_kind"][k] for r in rows)
                for k in ("same_satellite_beam_change", "satellite_change")},
            "eho": eho,
            "configuration_ids_matching_cleanpath": (
                sum(bool(r.get("configuration_matches_cleanpath")) for r in rows)
                if name in CLEAN_ARMS else None),
            "parity_reference_mbit_per_j": PARITY_MBIT_PER_J.get(name),
            "parity_ok_6dp": (None if name not in PARITY_MBIT_PER_J else
                              round(a0["ee_mbit_per_j"], 6) == PARITY_MBIT_PER_J[name]),
        }
    payload["pooled"] = pooled
    payload["parity_all_ok"] = all(pooled[n]["parity_ok_6dp"] for n in PARITY_MBIT_PER_J)
    payload["scalar_evaluate_calls"] = hc.SCALAR_CALLS["count"]
    assert hc.SCALAR_CALLS["count"] == 0
    payload["status"] = "COMPLETE"
    payload["runtime"] = hc.runtime_record()
    payload["wall_seconds"] = time.perf_counter() - started
    payload["runner_sha256"] = hc.sha256(Path(__file__))
    hc.atomic_write(OUTPUT, payload)
    print(json.dumps({n: [pooled[n]["a0"]["ee_mbit_per_j"], pooled[n]["aH"]["ee_mbit_per_j"],
                          pooled[n]["events"]["h_events"], pooled[n]["parity_ok_6dp"]] for n in ARMS},
                     indent=1), flush=True)
    print(f"parity_all_ok={payload['parity_all_ok']} scalar_evaluate_calls={hc.SCALAR_CALLS['count']}", flush=True)
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB final ({hc.peak_rss_bytes()} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
