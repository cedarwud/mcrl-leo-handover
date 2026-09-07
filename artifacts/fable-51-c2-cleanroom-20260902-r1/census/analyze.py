#!/usr/bin/env python3
"""Analyse the H-A hold-horizon census; writes census-result.json / .md."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

SCRATCH = Path(
    "/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/"
    "d47a2ac0-70e1-49ca-b412-995b22bcb231/scratchpad/census"
)
STEPS = 10
USERS = 100


def pct(values, qs=(5, 25, 50, 75, 95)):
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {f"p{q}": None for q in qs}
    return {f"p{q}": float(np.percentile(values, q)) for q in qs}


def summ(values):
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"n": 0, "median": None, "iqr": None, "mean": None,
                "p5": None, "p95": None}
    return {
        "n": int(values.size),
        "median": float(np.median(values)),
        "iqr": [float(np.percentile(values, 25)), float(np.percentile(values, 75))],
        "mean": float(values.mean()),
        "p5": float(np.percentile(values, 5)),
        "p95": float(np.percentile(values, 95)),
    }


def average_rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    tmp = np.empty(values.size, dtype=np.float64)
    tmp[order] = np.arange(values.size, dtype=np.float64)
    sorted_values = values[order]
    start = 0
    for index in range(1, values.size + 1):
        if index == values.size or sorted_values[index] != sorted_values[start]:
            tmp[order[start:index]] = tmp[order[start:index]].mean()
            start = index
    return tmp


def main() -> None:
    t0 = time.perf_counter()
    data = np.load(SCRATCH / "census-raw.npz")
    meta = json.loads((SCRATCH / "census-meta.json").read_text())
    kappa = float(data["_kappa_bits"][0])
    lam = float(data["_lambda0"][0])
    dt_s = float(data["_interval_s"][0])

    legal = data["legal"]
    zeta = data["zeta2"]
    zeta_full = data["zeta2_full"]
    rate = data["rate_part"]
    energy = data["energy_part"]
    q1 = data["q1"]
    q3 = data["q3"]
    q13 = q1 + q3
    a_taken = data["a_taken"]
    incumbent = data["a_incumbent"]
    step = data["step"]
    lineage = data["lineage"]
    world = data["world"]
    n_legal = data["n_legal"]
    empty_mask = data["empty_mask"]
    gain_ratio = data["gain_ratio"]          # (N, 28, 3)
    feasible = data["feasible"]              # (N, 28, 3)
    hold_h = data["hold_h"]
    sinr_zero = data["sinr_zero"]
    anchors = zeta.shape[0]
    zk = zeta / kappa
    zk_full = zeta_full / kappa
    rk = rate / kappa
    ek = energy / kappa

    out: dict[str, object] = {
        "schema": "h-a-hold-horizon-census-development-v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "constants": {
            "lambda0_bits_per_j": lam,
            "lambda0_hex": float(lam).hex(),
            "lambda0_source": meta["lambda0_source"],
            "kappa_bits": kappa,
            "kappa_bits_hex": float(kappa).hex(),
            "decision_step_s": dt_s,
            "p0_w": 0.825,
            "beam_power_max_w": 1.65,
            "horizon_offsets": [1, 2, 3],
        },
        "provenance": {
            "evaluation_seeds": meta["worlds"],
            "initialization_seeds": meta["lineages"],
            "behaviour_policy": "DROP_C2 (Q1+Q3 argmax under the common legal mask)",
            "checkpoint_sha256": meta["checkpoint_sha256"],
            "validation": meta["diagnostics"],
            "census_runtime_s": meta["elapsed_s"],
        },
    }

    # -- 1. coverage ----------------------------------------------------
    counts = np.bincount(n_legal, minlength=29)
    out["coverage"] = {
        "anchors": int(anchors),
        "episodes": int(len(meta["worlds"]) * len(meta["lineages"])),
        "legal_actions_total": int(legal.sum()),
        "legal_count_distribution": {
            str(k): int(v) for k, v in enumerate(counts) if v
        },
        "legal_count_summary": summ(n_legal.astype(float)),
        "step0_anchors": int((step == 0).sum()),
        "empty_mask_anchors": int(empty_mask.sum()),
        "anchors_with_incumbent": int((incumbent >= 0).sum()),
        "anchors_with_geometry_dropped_actions": int(
            (legal.sum(axis=1) < data["gamma0"].shape[1]).sum()
        ),
        "legal_actions_with_zero_candidate_sinr": int((sinr_zero & legal).sum()),
    }

    # -- 2. geometry headroom -------------------------------------------
    geo = {}
    for k in range(3):
        ratios = gain_ratio[:, :, k][legal]
        geo[f"gain_ratio_k{k+1}"] = pct(ratios)
    inf_by = {}
    fk = feasible[legal]                      # (L, 3)
    inf_by["k1"] = float((~fk[:, 0]).mean())
    inf_by["k<=2"] = float((~(fk[:, 0] & fk[:, 1])).mean())
    inf_by["k<=3"] = float((~(fk[:, 0] & fk[:, 1] & fk[:, 2])).mean())
    hh = hold_h[legal]
    hold_dist = {str(int(h)): int((hh == h).sum()) for h in range(4)}
    has_inc = incumbent >= 0
    inc_rows = np.arange(anchors)[has_inc]
    inc_cols = incumbent[has_inc]
    inc_feas1 = feasible[inc_rows, inc_cols, 0]
    inc_legal = legal[inc_rows, inc_cols]
    inc_hold = hold_h[inc_rows, inc_cols]
    out["geometry_headroom"] = {
        "gain_ratio_percentiles_over_legal_actions": geo,
        "fraction_legal_actions_infeasible": inf_by,
        "hold_horizon_distribution_over_legal_actions": hold_dist,
        "mean_hold_horizon_legal_actions": float(hh.mean()),
        "incumbent": {
            "anchors_with_incumbent": int(has_inc.sum()),
            "incumbent_legal_fraction": float(inc_legal.mean()),
            "fraction_incumbent_infeasible_at_k1": float((~inc_feas1).mean()),
            "incumbent_hold_horizon_distribution": {
                str(h): int((inc_hold == h).sum()) for h in range(4)
            },
        },
    }

    # -- 3/4/5/6 per-anchor within-action structure ---------------------
    multi = n_legal >= 2
    std_z, rng_z, std_q, rng_q = [], [], [], []
    share_rate, share_energy, share_full, share_cens = [], [], [], []
    rank_equal_energy, argmax_equal_energy = [], []
    var_z_tot = cov_zr = cov_ze = cov_zf = cov_zd = 0.0
    positive_alt = []
    gap = []
    flip = {str(s): [] for s in meta["lineages"]}
    flip_half = {str(s): [] for s in meta["lineages"]}
    flip_double = {str(s): [] for s in meta["lineages"]}
    corr_zq = []

    for row in range(anchors):
        mask = legal[row]
        if not mask.any():
            continue
        z = zk[row][mask]
        q = q13[row][mask]
        take = a_taken[row]
        if take < 0:
            continue
        z_take = zk[row, take]
        best = z.max()
        gap.append(float(best - z_take))
        positive_alt.append(bool(best > z_take + 0.0))
        base_arg = int(np.argmax(np.where(mask, q13[row], -np.inf)))
        for scale, bucket in ((1.0, flip), (0.5, flip_half), (2.0, flip_double)):
            arg = int(np.argmax(np.where(mask, q13[row] + scale * zk[row], -np.inf)))
            bucket[str(int(lineage[row]))].append(arg != base_arg)
        if not multi[row]:
            continue
        std_z.append(float(z.std(ddof=0)))
        rng_z.append(float(z.max() - z.min()))
        std_q.append(float(q.std(ddof=0)))
        rng_q.append(float(q.max() - q.min()))
        if z.std(ddof=0) > 0 and q.std(ddof=0) > 0:
            corr_zq.append(float(np.corrcoef(z, q)[0, 1]))
        r = rk[row][mask]
        e = ek[row][mask]
        zf = zk_full[row][mask]
        d = z - zf
        vz = float(np.var(z))
        var_z_tot += vz
        czr = float(np.mean((z - z.mean()) * (r - r.mean())))
        cze = float(np.mean((z - z.mean()) * (e - e.mean())))
        czf = float(np.mean((z - z.mean()) * (zf - zf.mean())))
        czd = float(np.mean((z - z.mean()) * (d - d.mean())))
        cov_zr += czr
        cov_ze += cze
        cov_zf += czf
        cov_zd += czd
        if vz > 0:
            share_rate.append(czr / vz)
            share_energy.append(-cze / vz)
            share_full.append(czf / vz)
            share_cens.append(czd / vz)
        rz = average_rank(z)
        re = average_rank(-e)
        rank_equal_energy.append(bool(np.array_equal(rz, re)))
        argmax_equal_energy.append(
            bool(int(np.argmax(z)) == int(np.argmax(-e)))
        )

    out["within_anchor_headroom"] = {
        "anchors_with_ge2_legal_actions": int(multi.sum()),
        "zeta2_over_kappa_std": summ(std_z),
        "zeta2_over_kappa_range": summ(rng_z),
        "q1_plus_q3_std": summ(std_q),
        "q1_plus_q3_range": summ(rng_q),
        "median_ratio_std_zeta2_over_std_q13": float(
            np.median(np.asarray(std_z) / np.maximum(np.asarray(std_q), 1e-300))
        ),
        "fraction_anchors_nonzero_zeta2_range": float(
            (np.asarray(rng_z) > 0).mean()
        ),
        "corr_zeta2_vs_q13_within_anchor": summ(corr_zq),
    }

    out["positive_alternatives"] = {
        "anchors_scored": int(len(positive_alt)),
        "fraction_anchors_with_better_alternative": float(np.mean(positive_alt)),
        "median_max_gain_kappa_units": float(np.median(gap)),
        "gap_summary_kappa_units": summ(gap),
    }

    flips = {}
    for scale_name, bucket in (("x1.0", flip), ("x0.5", flip_half), ("x2.0", flip_double)):
        per = {
            key: float(np.mean(value)) if value else None
            for key, value in bucket.items()
        }
        pooled = float(np.mean(np.concatenate(
            [np.asarray(v, dtype=bool) for v in bucket.values() if v]
        )))
        flips[scale_name] = {"per_lineage": per, "pooled": pooled}
    out["oracle_flip_rate"] = flips

    # censoring binds only where some legal action has h < 3
    cens_bind = ((hold_h < 3) & legal).any(axis=1)
    cens_rows = np.flatnonzero(cens_bind & multi)
    cens_share_bind = []
    for row in cens_rows:
        mask = legal[row]
        z = zk[row][mask]
        d = z - zk_full[row][mask]
        vz = float(np.var(z))
        if vz > 0:
            cens_share_bind.append(
                float(np.mean((z - z.mean()) * (d - d.mean())) / vz))

    out["component_decomposition"] = {
        "fraction_anchors_where_censoring_binds": float(cens_bind.mean()),
        "median_share_censoring_where_it_binds": (
            float(np.median(cens_share_bind)) if cens_share_bind else None),
        "p95_share_censoring_where_it_binds": (
            float(np.percentile(cens_share_bind, 95)) if cens_share_bind else None),
        "median_share_rate_term": float(np.median(share_rate)) if share_rate else None,
        "median_share_energy_term": float(np.median(share_energy)) if share_energy else None,
        "pooled_share_rate_term": float(cov_zr / var_z_tot) if var_z_tot else None,
        "pooled_share_energy_term": float(-cov_ze / var_z_tot) if var_z_tot else None,
        "median_share_uncensored": float(np.median(share_full)) if share_full else None,
        "median_share_censoring": float(np.median(share_cens)) if share_cens else None,
        "pooled_share_uncensored": float(cov_zf / var_z_tot) if var_z_tot else None,
        "pooled_share_censoring": float(cov_zd / var_z_tot) if var_z_tot else None,
        "fraction_anchors_ranking_equals_energy_alone": float(
            np.mean(rank_equal_energy)) if rank_equal_energy else None,
        "fraction_anchors_argmax_equals_energy_alone": float(
            np.mean(argmax_equal_energy)) if argmax_equal_energy else None,
    }

    # -- extra: incumbent positioning and scale-matched flip -------------
    inc_delta, inc_rank_frac, inc_is_argmax = [], [], []
    argmax_agree = []
    matched_scale = 1.0 / max(
        float(out["within_anchor_headroom"]["median_ratio_std_zeta2_over_std_q13"]),
        1e-12)
    flip_matched = {str(s_): [] for s_ in meta["lineages"]}
    for row in range(anchors):
        mask = legal[row]
        if not mask.any() or a_taken[row] < 0:
            continue
        base_arg = int(np.argmax(np.where(mask, q13[row], -np.inf)))
        z_arg = int(np.argmax(np.where(mask, zk[row], -np.inf)))
        argmax_agree.append(base_arg == z_arg)
        arg = int(np.argmax(
            np.where(mask, q13[row] + matched_scale * zk[row], -np.inf)))
        flip_matched[str(int(lineage[row]))].append(arg != base_arg)
        inc = incumbent[row]
        if inc < 0 or not mask[inc]:
            continue
        z = zk[row][mask]
        inc_delta.append(float(zk[row, inc] - z.mean()))
        inc_rank_frac.append(float((z < zk[row, inc]).mean()))
        inc_is_argmax.append(bool(inc == z_arg))

    out["incumbent_positioning"] = {
        "n": len(inc_delta),
        "zeta2_incumbent_minus_anchor_mean_kappa": summ(inc_delta),
        "incumbent_percentile_rank_by_zeta2": summ(inc_rank_frac),
        "fraction_incumbent_is_zeta2_argmax": float(np.mean(inc_is_argmax)),
    }
    out["oracle_flip_rate"]["scale_matched"] = {
        "scale": matched_scale,
        "rationale": "1 / median within-anchor std ratio; equalises the "
                     "typical within-anchor spread of ZETA2/kappa and Q1+Q3",
        "per_lineage": {k: float(np.mean(v)) for k, v in flip_matched.items()},
        "pooled": float(np.mean(np.concatenate(
            [np.asarray(v, dtype=bool) for v in flip_matched.values()]))),
    }
    out["within_anchor_headroom"]["fraction_argmax_zeta2_equals_argmax_q13"] = float(
        np.mean(argmax_agree))

    # -- 7. hold realism -------------------------------------------------
    took_incumbent = (a_taken >= 0) & (incumbent >= 0) & (a_taken == incumbent)
    denom_all = (a_taken >= 0)
    per_step = {}
    for s in range(STEPS):
        sel = (step == s) & denom_all
        sel_inc = sel & (incumbent >= 0)
        per_step[str(s)] = {
            "decisions": int(sel.sum()),
            "with_incumbent": int(sel_inc.sum()),
            "fraction_continue_of_all": float(took_incumbent[sel].mean()) if sel.any() else None,
            "fraction_continue_of_those_with_incumbent": (
                float(took_incumbent[sel_inc].mean()) if sel_inc.any() else None
            ),
        }
    per_lineage = {}
    for seed in meta["lineages"]:
        sel = (lineage == seed) & denom_all
        sel_inc = sel & (incumbent >= 0)
        per_lineage[str(seed)] = {
            "fraction_continue_of_all": float(took_incumbent[sel].mean()),
            "fraction_continue_of_those_with_incumbent": float(
                took_incumbent[sel_inc].mean()),
        }
    out["hold_realism"] = {
        "overall_fraction_continue_of_all": float(took_incumbent[denom_all].mean()),
        "overall_fraction_continue_of_those_with_incumbent": float(
            took_incumbent[denom_all & (incumbent >= 0)].mean()),
        "per_step": per_step,
        "per_lineage": per_lineage,
    }

    # -- 8. prediction check --------------------------------------------
    served = data["served_now"]
    s_norad = data["served_norad"]
    s_cell = data["served_cell"]
    realized = data["realized_link_power"]
    pred = data["taken_pred_power"]
    order = np.lexsort((data["user"], step, world, lineage))
    assert np.array_equal(order, np.arange(anchors))
    index = np.arange(anchors).reshape(-1, STEPS, USERS)
    cont_err, cont_err0, sw_err, sw_err0 = [], [], [], []
    n_pairs = 0
    for ep in range(index.shape[0]):
        for s in range(STEPS - 1):
            here = index[ep, s]
            there = index[ep, s + 1]
            both = served[here] & served[there]
            same = both & (s_norad[here] == s_norad[there]) & (
                s_cell[here] == s_cell[there])
            switch = both & ~same
            n_pairs += int(both.sum())
            p = pred[here]
            r_next = realized[there]
            ok = same & np.isfinite(p) & (r_next > 0)
            err = np.abs(r_next[ok] - p[ok]) / r_next[ok]
            (cont_err0 if s == 0 else cont_err).extend(err.tolist())
            ok2 = switch & (r_next > 0)
            err2 = np.abs(r_next[ok2] - 0.825) / 0.825
            (sw_err0 if s == 0 else sw_err).extend(err2.tolist())

    def err_summary(values):
        values = np.asarray(values, dtype=np.float64)
        if values.size == 0:
            return {"n": 0}
        return {
            "n": int(values.size),
            "median_rel_err": float(np.median(values)),
            "p95_rel_err": float(np.percentile(values, 95)),
            "p99_rel_err": float(np.percentile(values, 99)),
            "max_rel_err": float(values.max()),
            "fraction_within_1pct": float((values <= 0.01).mean()),
            "fraction_within_5pct": float((values <= 0.05).mean()),
        }

    out["prediction_check"] = {
        "served_pairs_examined": int(n_pairs),
        "continue_t_ge_1": err_summary(cont_err),
        "continue_t_eq_0_warm_start_affected": err_summary(cont_err0),
        "switch_t_ge_1_prediction_is_p0": err_summary(sw_err),
        "switch_t_eq_0_prediction_is_p0": err_summary(sw_err0),
    }

    out["approximations"] = [
        "Future user position is frozen at the decision-time ECEF "
        "(driver.user_ecef_km()); users move ~250 m per 30.08 s step, so the "
        "off-axis angle at t+k inherits up to ~0.03 deg/step of drift.",
        "Shadow fading and Rician fading are set to their unity/expected "
        "value in link_power_factor for every horizon offset AND in the "
        "decision-time inversion of the candidate SINR; the inversion is "
        "therefore equivalent to SINR_a(t+k) = gamma_a(t) * (start/G_a(0)) * "
        "(path_a(t+k)/path_a(t)).",
        "I_a + N is frozen at its decision-time value for all k (no "
        "re-evaluation of the interference field at t+k).",
        "Non-focal context (n_a, m_a, sat_active_a) is frozen at the previous "
        "StepOutcome, the same one-step lag the deployed state uses.",
        "At step 0 there is no previous outcome: every beam is treated as "
        "empty/inactive and every action starts a NEW segment with start = "
        "G_a(0).  The simulator additionally applies a uniform-episode-length "
        "segment WARM START at step 0 (PhysicsConfig.segment_warm_start), so "
        "the step-0 start gain is an approximation and the step-0 prediction "
        "check is reported separately.",
        "The forward-geometry guard (satellite ephemeris available at every "
        "offset and G_a(0) > 0) removed zero legal actions: over a two-episode "
        "audit the deployment mask and the census legal set were identical "
        "(51583 == 51583 legal actions, 0 rows with attrition).",
        "The behaviour actions computed here are byte-identical to "
        "five_arm.route_actions(..., 'DROP_C2') on a 2000-decision audit.",
        "The strict cross-artifact hash authentication of the five-arm "
        "evaluator was skipped (the working tree's source closure has drifted "
        "from the sealed V0.4 manifest); every checkpoint file actually loaded "
        "is SHA-256 recorded above.",
    ]
    out["runtime_s"] = {
        "census_rollout": meta["elapsed_s"],
        "analysis": time.perf_counter() - t0,
    }

    (SCRATCH / "census-result.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
