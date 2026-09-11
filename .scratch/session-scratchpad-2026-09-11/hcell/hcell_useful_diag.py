#!/usr/bin/env python3
"""Diagnose the one-user dense-vs-scalar USEFUL-TIME removal difference seen in
the KAT (bits agreed to 5e-7 bit/user; useful seconds differed by 0.142 s for
at least one user at anchor 3 BASE).  Bits are the EE quantity; this isolates
whether the difference is a decode-indicator convention at a zero-rate user."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hcell_common as hc  # noqa: E402

OUTPUT = hc.SCRATCH / "hcell-useful-diag.json"


def main() -> int:
    hc.check_runtime()
    ctx = hc.setup(with_crowd=False)
    runner = ctx.runner
    frozen = hc.frozen_panel(ctx)
    tape, _rec = hc.build_tape(ctx)
    from mcrl.physics_v025.adapter import _rescore_boundary, build_shared_tape
    from mcrl.physics_v025.architectures import RadiationConfig
    out = []
    for anchor_index in (3, 1):
        row = frozen[anchor_index]
        step, carrier = int(row["step_index"]), str(row["carrier"])
        base = runner._base_configuration(tape, step, carrier)
        incumbent = runner._base_configuration(tape, max(0, step - 1), carrier)
        rss = ctx.cleanpath.rss_max_configuration(runner, tape, step, base)
        for name, config in (("BASE", base), ("RSS_MAX", rss)):
            side0 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(0,))
            side0.evaluate_many((config,))
            side1 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(1,))
            side1.evaluate_many((config,))
            r0, d0 = hc.per_user_rates(ctx, side0._evaluated[config.configuration_id])
            r1, d1 = hc.per_user_rates(ctx, side1._evaluated[config.configuration_id])
            ledger = hc.h_ledger(ctx, tape, step, incumbent, config)
            removed, removed_useful, _info = hc.h_removal_endpoint(ctx, ledger, r0, r1, d0, d1)

            ev0 = runner.StepEvaluator(
                tape, runner._setting("a-r0"), step, transition_from=incumbent,
                cell_rekeyed_users=runner._rekeyed_users(tape, step), field="realised",
                boundary_indices=tuple(range(48)))
            p0 = ev0.evaluate(config)
            evH = runner.StepEvaluator(
                tape, runner._setting("a-rH"), step, transition_from=incumbent,
                cell_rekeyed_users=runner._rekeyed_users(tape, step), field="realised",
                boundary_indices=tuple(range(48)))
            pH = evH.evaluate(config)
            geometry = tape.geometry_for(step_index=step, assignments=config.mapping)
            shared = build_shared_tape(
                runner._setting("a-r0").architecture, geometry, tape.inventory,
                field="realised", roster=tuple(u.user_id for u in tape.user_layout),
                config=RadiationConfig(rate_target_bps=ctx.run_setting.rate_target_bps),
                circuit_power_per_active_chain_w=ctx.run_setting.circuit_power_per_active_chain_w)
            samples = [_rescore_boundary(shared.integrated[b], tape.inventory,
                                         runner._setting("a-r0"), shared.users,
                                         shared.circuit_power_per_active_chain_w)
                       for b in (0, 1)]
            mismatches = []
            for user in sorted(p0.score.bits):
                scalar_useful = float(p0.score.useful_time_s[user]) - float(pH.score.useful_time_s[user])
                dense_useful = removed_useful.get(user, 0.0)
                scalar_bits = float(p0.score.bits[user]) - float(pH.score.bits[user])
                if abs(scalar_useful - dense_useful) > 1e-9:
                    mismatches.append({
                        "user": user,
                        "scalar_useful_removed_s": scalar_useful,
                        "dense_useful_removed_s": dense_useful,
                        "scalar_bits_removed": scalar_bits,
                        "dense_bits_removed": removed.get(user, 0.0),
                        "dense_rate_b0": r0[user], "dense_rate_b1": r1[user],
                        "dense_decode_b0": d0[user], "dense_decode_b1": d1[user],
                        "scalar_rate_b0": samples[0].rate_bps.get(user),
                        "scalar_rate_b1": samples[1].rate_bps.get(user),
                        "scalar_decode_b0": samples[0].decoding.get(user),
                        "scalar_decode_b1": samples[1].decoding.get(user),
                        "scalar_decoding_time_s": float(p0.score.decoding_time_s[user]),
                        "scalar_useful_time_s_a0": float(p0.score.useful_time_s[user]),
                        "dense_decoding_time_s_full48": None,
                    })
            out.append({"anchor": anchor_index, "config": name,
                        "mismatch_count": len(mismatches), "mismatches": mismatches[:10],
                        "total_scalar_useful_removed_s": math.fsum(
                            float(p0.score.useful_time_s[u]) - float(pH.score.useful_time_s[u])
                            for u in p0.score.bits),
                        "total_dense_useful_removed_s": math.fsum(removed_useful.values())})
            print(json.dumps(out[-1], default=str)[:2000], flush=True)
            del ev0, evH, side0, side1, shared
            hc.gc.collect()
    payload = {"schema": "mcrl-v025-hcell-useful-diag-v1", "status": "COMPLETE",
               "claim_status": "DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM", "results": out,
               "runtime": hc.runtime_record()}
    hc.atomic_write(OUTPUT, payload)
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB final", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
