#!/usr/bin/env python3
"""HCELL step 1 -- is treatment H live in the current code path?

Reproduces the engine-audit B1 KAT on a development anchor with handovers,
on the SEALED SCALAR path (this is a code-path verification, not a measured
surface; the scalar path is the only sealed implementation of H):

  * the event ledger is non-empty (runner._interruption_events);
  * a-rH differs from a-r0 in useful bits and useful time, with identical
    joules and decoding time;
  * the per-user difference is non-zero exactly on blackout users.

It also checks (i) that the sealed dense path is a-r0-only (evaluate_many on
an a-rH evaluator routes to scalar evaluate), and (ii) that the HCELL dense
H rescore reproduces the sealed scalar a-rH removal per user.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hcell_common as hc  # noqa: E402

OUTPUT = hc.SCRATCH / "hcell-kat-receipt.json"
KAT_ANCHORS = (3, 1)  # step-1 nearest-eligible (BASE itself hands over); step-0 stay


def scalar_profile(ctx, tape, step, incumbent, label, config, *, via_many=False):
    runner = ctx.runner
    evaluator = runner.StepEvaluator(
        tape, runner._setting(label), step,
        transition_from=incumbent,
        cell_rekeyed_users=runner._rekeyed_users(tape, step),
        field="realised", counter=runner.EvaluationCounter(),
        boundary_indices=tuple(range(48)),
    )
    routed = []
    if via_many:
        original = evaluator.evaluate

        def counting(cfg):
            routed.append(cfg.configuration_id)
            return original(cfg)

        evaluator.evaluate = counting  # instance-level, for the routing check only
        started = time.perf_counter()
        evaluator.evaluate_many((config,))
        profile = evaluator._evaluated[config.configuration_id]
    else:
        started = time.perf_counter()
        profile = evaluator.evaluate(config)
    seconds = time.perf_counter() - started
    return profile, seconds, routed, evaluator.run_setting.payload()


def main() -> int:
    hc.check_runtime()
    started = time.perf_counter()
    ctx = hc.setup(with_crowd=False)
    frozen = hc.frozen_panel(ctx)
    tape, tape_record = hc.build_tape(ctx)
    runner = ctx.runner
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB after tape", flush=True)
    payload = {
        "schema": "mcrl-v025-hcell-kat-v1",
        "status": "RUNNING",
        "claim_status": "DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM",
        "world_tape": tape_record,
        "sources": ctx.sources,
        "interruption_constants": ctx.interruption_constants,
        "anchors": [],
    }
    for position, anchor_index in enumerate(KAT_ANCHORS, 1):
        row = frozen[anchor_index]
        step = int(row["step_index"])
        carrier = str(row["carrier"])
        base = runner._base_configuration(tape, step, carrier)
        incumbent = runner._base_configuration(tape, max(0, step - 1), carrier)
        rss = ctx.cleanpath.rss_max_configuration(runner, tape, step, base)
        configs = {"BASE": base, "RSS_MAX": rss}

        dense = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised",
                                   boundaries=tuple(range(48)))
        dense.evaluate_many(tuple(configs.values()))
        side0 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(0,))
        side0.evaluate_many(tuple(configs.values()))
        side1 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(1,))
        side1.evaluate_many(tuple(configs.values()))

        anchor_record = {"global_anchor_index": anchor_index, "step_index": step,
                         "carrier": carrier, "configs": {}}
        for name, config in configs.items():
            census = hc.event_census(ctx, tape, step, incumbent, config)
            ledger = hc.h_ledger(ctx, tape, step, incumbent, config)
            p0, s0, _, rs0 = scalar_profile(ctx, tape, step, incumbent, "a-r0", config)
            pH, sH, routed, rsH = scalar_profile(ctx, tape, step, incumbent, "a-rH", config,
                                                 via_many=True)
            pd = dense._evaluated[config.configuration_id]
            r0, d0 = hc.per_user_rates(ctx, side0._evaluated[config.configuration_id])
            r1, d1 = hc.per_user_rates(ctx, side1._evaluated[config.configuration_id])
            removed, removed_useful, rinfo = hc.h_removal_endpoint(ctx, ledger, r0, r1, d0, d1)

            users = sorted(p0.score.bits)
            scalar_diff = {u: float(p0.score.bits[u]) - float(pH.score.bits[u]) for u in users}
            scalar_useful_diff = {u: float(p0.score.useful_time_s[u]) - float(pH.score.useful_time_s[u])
                                  for u in users}
            nonzero_users = sorted(u for u in users if scalar_diff[u] != 0.0)
            blackout_users = sorted(removed)
            dense_vs_scalar_removal = max(
                (abs(removed.get(u, 0.0) - scalar_diff[u]) for u in users), default=0.0)
            dense_vs_scalar_useful = max(
                (abs(removed_useful.get(u, 0.0) - scalar_useful_diff[u]) for u in users), default=0.0)
            dense_a0_vs_scalar_a0 = max(abs(float(pd.score.bits[u]) - float(p0.score.bits[u]))
                                        for u in users)
            denseH_vs_scalarH = max(
                abs(float(pd.score.bits[u]) - removed.get(u, 0.0) - float(pH.score.bits[u]))
                for u in users)
            record = {
                "configuration_id_sha256": __import__("hashlib").sha256(
                    config.configuration_id.encode()).hexdigest(),
                "event_census": census,
                "ledger_length": len(ledger),
                "ledger_kinds": dict(__import__("collections").Counter(e.kind for e in ledger)),
                "scalar_a0": {"bits": p0.bits, "joules": p0.joules,
                              "useful_s": math.fsum(p0.score.useful_time_s.values()),
                              "decoding_s": math.fsum(p0.score.decoding_time_s.values()),
                              "seconds": s0, "run_setting": rs0},
                "scalar_aH": {"bits": pH.bits, "joules": pH.joules,
                              "useful_s": math.fsum(pH.score.useful_time_s.values()),
                              "decoding_s": math.fsum(pH.score.decoding_time_s.values()),
                              "seconds": sH, "run_setting": rsH},
                "aH_evaluate_many_routed_to_scalar_evaluate": len(routed),
                "a0_minus_aH_bits_scalar": p0.bits - pH.bits,
                "a0_minus_aH_useful_s_scalar": math.fsum(scalar_useful_diff.values()),
                "joules_identical": p0.joules == pH.joules,
                "decoding_identical": all(p0.score.decoding_time_s[u] == pH.score.decoding_time_s[u]
                                          for u in users),
                "served_identical": all(p0.score.served_phy[u] == pH.score.served_phy[u] for u in users),
                "users_with_nonzero_scalar_difference": len(nonzero_users),
                "blackout_users": len(blackout_users),
                "nonzero_users_subset_of_blackout_users": set(nonzero_users) <= set(blackout_users),
                "blackout_users_with_zero_rate_at_t0": sum(1 for u in blackout_users if r0[u] == 0.0),
                "dense_a0": {"bits": pd.bits, "joules": pd.joules},
                "dense_removed_bits": math.fsum(removed.values()),
                "dense_removed_bits_by_kind": rinfo["removed_bits_by_kind"],
                "max_abs_user_dense_removal_minus_scalar_removal_bits": dense_vs_scalar_removal,
                "max_abs_user_dense_useful_removal_minus_scalar_s": dense_vs_scalar_useful,
                "max_abs_user_dense_a0_minus_scalar_a0_bits": dense_a0_vs_scalar_a0,
                "max_abs_user_denseH_minus_scalarH_bits": denseH_vs_scalarH,
                "dense_joules_minus_scalar_joules": pd.joules - p0.joules,
            }
            record["H_LIVE_on_this_config"] = bool(
                len(ledger) > 0 and census["h_events"] > 0
                and p0.bits != pH.bits and record["a0_minus_aH_useful_s_scalar"] > 0.0
                and record["joules_identical"] and record["decoding_identical"]
                and record["nonzero_users_subset_of_blackout_users"]
            )
            anchor_record["configs"][name] = record
            print(f"anchor {position}/{len(KAT_ANCHORS)} {name} "
                  f"events={census['h_events']} ledger={len(ledger)} "
                  f"a0-aH scalar={p0.bits - pH.bits:.6e} dense-removal={math.fsum(removed.values()):.6e} "
                  f"max|dense-scalar removal|={dense_vs_scalar_removal:.3e} "
                  f"max|denseA0-scalarA0|={dense_a0_vs_scalar_a0:.3e} "
                  f"routed={len(routed)} scalar_s={s0:.1f}/{sH:.1f} "
                  f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB", flush=True)
            hc.check_runtime()
        payload["anchors"].append(anchor_record)
        hc.atomic_write(OUTPUT, payload)
        del dense, side0, side1
        hc.gc.collect()

    payload["H_LIVE"] = all(
        rec["H_LIVE_on_this_config"]
        for a in payload["anchors"] for rec in a["configs"].values()
        if rec["event_census"]["h_events"] > 0
    ) and any(rec["event_census"]["h_events"] > 0
              for a in payload["anchors"] for rec in a["configs"].values())
    payload["status"] = "COMPLETE"
    payload["runtime"] = hc.runtime_record()
    payload["wall_seconds"] = time.perf_counter() - started
    payload["runner_sha256"] = hc.sha256(Path(__file__))
    hc.atomic_write(OUTPUT, payload)
    print(f"H_LIVE={payload['H_LIVE']}", flush=True)
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB final ({hc.peak_rss_bytes()} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
