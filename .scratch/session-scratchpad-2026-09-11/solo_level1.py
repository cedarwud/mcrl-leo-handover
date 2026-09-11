#!/usr/bin/env python3
"""SOLO Level 1 -- learner-free route-alone oracle on the deployed bounded catalogue.

Per anchor:
  * the deployed bounded-union-v2 catalogue is rebuilt exactly as
    ENGINE._catalogue_with_census does, reading the ranking evaluator's dense
    cache instead of calling scalar evaluate (one evaluate_many of BASE plus
    every shortlisted unilateral, as deployed);
  * ONE fresh dense nominal boundary-0 StepEvaluator (transition = prior-step
    carrier incumbent, the declared target path) receives BASE together with
    every catalogue profile and every member unilateral in one evaluate_many;
    the exact C1 difference surplus, the exact coalition interaction psi and
    their Phi-free physical twins are recomputed from that cache;
  * the exact C2 persistence forecast is recomputed with the declared engine
    helper _batched_stage2_forecasts (fresh dense nominal evaluators at offsets
    1..3, boundary 0, evaluate_many only) and targets.c2_persistence_forecast;
  * corpus labels (93-anchor exact corpus) are read for parity only;
  * ONE separate fresh realised dense full-48 StepEvaluator receives BASE and
    RSS_MAX alongside the first catalogue chunk, then every catalogue profile.
StepEvaluator.evaluate is replaced by a raising stub before any work.
No learner, checkpoint or loss is read.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gc
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

WORKSPACE = Path("/home/sat/mcrl-v025-solo-ws")
SOURCE_ROOT = Path("/home/sat/mcrl-v025-c1c2suff-ws")
PILOT_PATH = SOURCE_ROOT / "scripts/run_v025_pilot_c3.py"
PILOT_SHA256 = "95103bb96caaa130659fa0d509f19409574b406798a173e278a7d9dac12b7435"
CALIBRATION_PATH = SOURCE_ROOT / "artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-calibration.json"
CORPUS93 = Path("/home/sat/mcrl-v025-exact93-ws/artifacts/exact-label-corpus-93-20260910/views")
PYTHON = "/home/sat/mcrl-leo-handover/.venv/bin/python"
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")
MAX_RSS_BYTES = 5_000_000_000
ENDPOINT_BATCH = 32
CARRIERS = ("nearest-eligible", "stay-if-possible", "random-masked")
ROUTES = ("C1", "C2", "C3")
LATTICE = tuple(
    tuple(r for r, keep in zip(ROUTES, bits) if keep)
    for bits in itertools.product((0, 1), repeat=3)
)
SCALAR_CALLS = 0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def check_runtime() -> None:
    if sys.executable != PYTHON:
        raise RuntimeError(f"wrong interpreter {sys.executable}")
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        raise RuntimeError("niceness below 15")
    bad = {k: os.environ.get(k) for k in THREAD_VARS if os.environ.get(k) != "1"}
    if bad:
        raise RuntimeError(f"thread pins not 1: {bad}")
    if peak_rss() >= MAX_RSS_BYTES:
        raise MemoryError(f"peak RSS {peak_rss()} >= 5 GB")


def load_pilot():
    if sha256(PILOT_PATH) != PILOT_SHA256:
        raise RuntimeError("pilot bytes drifted")
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
    name = "solo_pilot"
    spec = importlib.util.spec_from_file_location(name, PILOT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_calibration(pilot):
    payload = json.loads(CALIBRATION_PATH.read_text(encoding="ascii"))
    ratio = lambda n: Fraction(*payload[n])
    return pilot.PilotCalibration(
        eta_ref=ratio("eta_ref"), lambda_bits_per_j=ratio("lambda_bits_per_j"),
        kappa_bits_per_user_step=ratio("kappa_bits_per_user_step"),
        bits_ref=ratio("bits_ref"), joules_ref=ratio("joules_ref"), users=int(payload["users"]),
    )


def install_stub(engine) -> None:
    original = engine.StepEvaluator.evaluate

    def forbidden(*args, **kwargs):
        global SCALAR_CALLS
        SCALAR_CALLS += 1
        raise AssertionError("scalar StepEvaluator.evaluate is forbidden on SOLO surfaces")

    forbidden.__wrapped__ = original
    engine.StepEvaluator.evaluate = forbidden
    assert engine.StepEvaluator.evaluate is forbidden


def cached(evaluator, config):
    p = evaluator._evaluated.get(config.configuration_id)
    if p is None:
        raise RuntimeError(f"absent from dense cache (invalid={config.configuration_id in evaluator._invalid}): {config.configuration_id[:80]}")
    return p


def identity_of(action):
    if action is None or action.get("norad_id") is None:
        return None
    return (int(action["norad_id"]), int(action["beam_chain_id"]))


# --------------------------------------------------------------------------
# corpus index (parity only)
# --------------------------------------------------------------------------

def verify_sidecar(path: Path) -> str:
    side = path.with_name(path.name + ".sha256")
    digest = sha256(path)
    recorded = side.read_text(encoding="ascii").split()[0]
    if recorded != digest:
        raise RuntimeError(f"sidecar mismatch {path}")
    return digest


def corpus_index():
    sources, coalitions = {}, {}
    for world_dir in sorted(CORPUS93.iterdir()):
        for path in sorted(world_dir.glob("*.jsonl")):
            with path.open(encoding="ascii") as fh:
                header = json.loads(fh.readline())
            if path.name.startswith("BUILD_NOT_CLAIM-exact-source-anchor-"):
                sources[int(header["global_anchor_index"])] = path
            elif path.name.startswith("COALITION_BUILD-c3-anchor-"):
                # rows carry a within-world anchor_index; the file name carries the global index
                global_index = int(path.name.removeprefix("COALITION_BUILD-c3-anchor-").removesuffix(".jsonl"))
                if global_index in coalitions:
                    raise RuntimeError(f"duplicate coalition shard for global {global_index}")
                coalitions[global_index] = path
    return sources, coalitions


def fh_line(path: Path, index: int) -> str:
    with path.open(encoding="ascii") as fh:
        for i, line in enumerate(fh):
            if i == index:
                return line
    raise RuntimeError(f"{path} has no line {index}")


def corpus_labels(source_path: Path, coalition_path: Path, base_mapping):
    digests = {"source_view_sha256": verify_sidecar(source_path),
               "coalition_shard_sha256": verify_sidecar(coalition_path)}
    c1, c2, meta = {}, {}, {}
    with source_path.open(encoding="ascii") as fh:
        header = json.loads(fh.readline())
        for line in fh:
            row = json.loads(line)
            key = (int(row["user_id"]), identity_of(row["action"]))
            c1[key] = float.fromhex(row["c1_label_normalized_hex"])
            c2[key] = float.fromhex(row["c2_label_normalized_hex"])
            meta.setdefault("archive_digest", row["archive_digest"])
            meta.setdefault("world_id", row["world_id"])
    psi, psi_phys = {}, {}
    with coalition_path.open(encoding="ascii") as fh:
        json.loads(fh.readline())
        for line in fh:
            row = json.loads(line)
            if row["world_id"] != meta["world_id"] or not row["anchor_id"].endswith(
                    f"|{header['step_index']}|BASE:{header['carrier']}"):
                raise RuntimeError(f"coalition shard anchor mismatch: {row['anchor_id']}")
            mapping = dict(base_mapping)
            for member in row["context"]["members"]:
                mapping[int(member["user_id"])] = identity_of(member["selected_action"])
            key = tuple(sorted(mapping.items()))
            psi[key] = float.fromhex(row["psi_normalized_hex"])
            psi_phys[key] = float.fromhex(row["physical_psi_normalized_hex"])
    return header, c1, c2, psi, psi_phys, meta, digests


# --------------------------------------------------------------------------
# catalogue: exact replica of ENGINE._catalogue_with_census, cache reads only
# --------------------------------------------------------------------------

def deployed_catalogue(E, tape, step, base, calibration, run_setting):
    users = tuple(sorted(u.user_id for u in tape.user_layout))
    all_options, _raw = E._legal_options(tape, step)
    product = math.prod(len(all_options[u]) if all_options[u] else 1 for u in users)
    if product <= E.COMPLETE_CATALOGUE_LIMIT:
        raise RuntimeError("complete-cartesian branch not replicated")
    options, census = E._selection_shortlist(tape, step, run_setting=run_setting)
    rows = [base]
    base_map = base.mapping
    unilaterals = {u: [] for u in users}
    for u in users:
        for identity in options[u]:
            if identity == base_map[u]:
                continue
            m = dict(base_map)
            m[u] = identity
            row = E._configuration(base, m, kind="unilateral")
            rows.append(row)
            unilaterals[u].append(row)
    nominal = E.StepEvaluator(tape, E._setting("a-r0"), step, transition_from=base, field="nominal",
                              counter=E.EvaluationCounter(), run_setting=run_setting, boundary_indices=(0,))
    rank_rows = [base] + [r for vals in unilaterals.values() for r in vals]
    nominal.evaluate_many(rank_rows)          # one call, exactly as deployed
    nb = cached(nominal, base)
    eta, kappa = calibration.eta_ref, calibration.kappa_bits_per_user_step
    best = {}
    for u in users:
        vals = []
        for row in unilaterals[u]:
            p = cached(nominal, row)
            core = Fraction(str(p.bits - nb.bits)) - eta * Fraction(str(p.joules - nb.joules))
            core += kappa * E._phi_for(base, row)
            vals.append(core)
        best[u] = max(vals, default=Fraction(-10**30))
    ranked = sorted(users, key=lambda u: (-best[u], u))[:E.PAIRWISE_TOP_K_USERS]
    for rank in range(E.TOP_PROPOSALS):
        m = dict(base_map)
        for u in users:
            if len(unilaterals[u]) > rank:
                m[u] = unilaterals[u][rank].mapping[u]
        if m != base_map:
            rows.append(E._configuration(base, m, kind="s0-top-two"))
    for a, b in itertools.combinations(ranked, 2):
        for ra in unilaterals[a][:E.TOP_PROPOSALS]:
            for rb in unilaterals[b][:E.TOP_PROPOSALS]:
                m = dict(base_map)
                m[a] = ra.mapping[a]
                m[b] = rb.mapping[b]
                rows.append(E._configuration(base, m, kind="pairwise-top10-top2"))
    for beam in sorted({i for i in base_map.values() if i is not None}):
        m = dict(base_map)
        for u in users:
            if base_map[u] == beam:
                m[u] = next((i for i in options[u] if i != beam), None)
        if m != base_map:
            rows.append(E._configuration(base, m, kind="beam-evacuation"))
    unique = {r.assignments: r for r in rows}
    ordered = (base,) + tuple(sorted((r for a, r in unique.items() if a != base.assignments),
                                     key=lambda r: r.configuration_id))
    if len(ordered) > E.CATALOGUE_CAP:
        raise RuntimeError("catalogue cap exceeded")
    invalid_rank = len(nominal._invalid)
    del nominal
    return ordered, {"bounded_catalogue_count": len(ordered), "top10_users": ranked,
                     "ranking_invalid": invalid_rank, "catalogue_mode": "bounded-union-v2",
                     "shortlist_census": census}


def rss_max_configuration(E, tape, step, base):
    options, _ = E._legal_options(tape, step)
    arrays = tape.steps[step].arrays
    row_of = arrays._row_index()
    mapping = {}
    for user, identities in sorted(options.items()):
        if not identities:
            mapping[user] = None
            continue
        _o, ident = min(enumerate(identities),
                        key=lambda it: (-float(arrays.nominal_gain[0, row_of[(user, it[1])]]), it[0]))
        mapping[user] = ident
    return E._configuration(base, mapping, kind="solo-rss-max")


def outcome_metrics(E, tape, step, incumbent, profile):
    attained = profile.score.rate_target_attained
    events = E._physical_events(incumbent, profile.config,
                                cell_rekeyed_users=E._rekeyed_users(tape, step))
    return {
        "bits": float(profile.bits), "joules": float(profile.joules),
        "served": sum(bool(v) for v in profile.score.served_phy.values()),
        "rate_attained": sum(bool(v) for v in attained.values()),
        "users": len(profile.config.assignments),
        "handovers": sum(ev.kind in {"beam_change", "satellite_change", "cell_rekey"} for ev in events),
    }


def select(scores, order):
    """Deployed tie rule: catalogue order, first strict maximum; order[0] is BASE (score 0)."""
    best_i, best_s = order[0], scores[order[0]]
    for i in order[1:]:
        if scores[i] > best_s:
            best_i, best_s = i, scores[i]
    return best_i


def run_anchor(pilot, E, calibration, tape, world_index, step, carrier, global_index,
               corpus_src, corpus_coal, targets_mod):
    t0 = time.perf_counter()
    setting = E._setting("a-r0")
    run_setting = E.run_setting_for("a-r0")
    base = E._base_configuration(tape, step, carrier)
    incumbent = E._base_configuration(tape, max(0, step - 1), carrier)
    rekeys = E._rekeyed_users(tape, step)
    eta, kappa, lam = calibration.eta_ref, calibration.kappa_bits_per_user_step, calibration.lambda_bits_per_j
    users = tuple(sorted(base.mapping))
    base_map = base.mapping

    catalogue, cat_meta = deployed_catalogue(E, tape, step, base, calibration, run_setting)
    t_cat = time.perf_counter()

    # member unilaterals (user, identity) needed for C1/C2 decomposition
    changed = {}
    needed = {}
    for cfg in catalogue:
        m = cfg.mapping
        A = tuple(u for u in users if m[u] != base_map[u])
        changed[cfg.configuration_id] = A
        for u in A:
            key = (u, m[u])
            if key not in needed:
                um = dict(base_map)
                um[u] = m[u]
                needed[key] = E._configuration(base, um, kind="solo-member-unilateral")
    ref_cfg = E._configuration(base, dict(base_map), kind="solo-reference-action")

    # ---- ONE fresh dense nominal boundary-0 selection evaluator ----------
    sel = E.StepEvaluator(tape, setting, step, transition_from=incumbent, cell_rekeyed_users=rekeys,
                          field="nominal", counter=E.EvaluationCounter(), run_setting=run_setting,
                          boundary_indices=(0,))
    first_call = {base.configuration_id: base}
    for cfg in catalogue[1:]:
        first_call.setdefault(cfg.configuration_id, cfg)
    for cfg in needed.values():
        first_call.setdefault(cfg.configuration_id, cfg)
    first_call = tuple(first_call.values())
    assert first_call[0].configuration_id == base.configuration_id
    sel.evaluate_many(first_call)
    sel_invalid = set(sel._invalid)

    def f_incl(cfg):
        p = cached(sel, cfg)
        phi = E._phi_for(incumbent, cfg, cell_rekeyed_users=rekeys)
        out = p.outcome(phi=phi)
        phys = out.bits - eta * out.joules
        return phys + kappa * out.phi, phys

    fb_incl, fb_phys = f_incl(base)
    d_incl, d_phys = {}, {}
    for key, cfg in needed.items():
        if cfg.configuration_id in sel_invalid:
            continue
        fi, fp = f_incl(cfg)
        d_incl[key] = (fi - fb_incl) / kappa
        d_phys[key] = (fp - fb_phys) / kappa

    # ---- C2 via declared forecast helper (fresh nominal evaluators, offsets 1..3, boundary 0)
    c2_configs = {base.configuration_id: base, ref_cfg.configuration_id: ref_cfg}
    for key, cfg in needed.items():
        if cfg.configuration_id not in sel_invalid:
            c2_configs.setdefault(cfg.configuration_id, cfg)
    forecasts, _receipts = E._batched_stage2_forecasts(
        tape=tape, setting=setting, anchor_step=step, carrier=carrier,
        configs=tuple(c2_configs.values()), counter=E.EvaluationCounter(),
        calibration=calibration, run_setting=run_setting,
    )
    base_fc = forecasts[base.configuration_id]

    def c2_label(cfg):
        lab = targets_mod.c2_persistence_forecast(
            forecasts[cfg.configuration_id], base_fc, lambda_bits_per_j=lam, eta_ref=eta,
            kappa_bits_per_user_step=kappa)
        return lab

    ref_lab = c2_label(ref_cfg)
    c2_ref = ref_lab.normalized_total
    c2_ref_surplus = ref_lab.forecast_surplus_bits / kappa
    c2_val, c2_surplus = {}, {}
    for key, cfg in needed.items():
        if cfg.configuration_id in sel_invalid:
            continue
        lab = c2_label(cfg)
        c2_val[key] = lab.normalized_total
        c2_surplus[key] = lab.forecast_surplus_bits / kappa
    t_sel = time.perf_counter()

    # ---- corpus labels (parity only) --------------------------------------
    header, lab_c1, lab_c2, lab_psi, lab_psi_phys, meta, digests = corpus_labels(
        corpus_src, corpus_coal, base_map)
    if meta["archive_digest"] != pilot._archive_digest(tape):
        raise RuntimeError("tape archive digest differs from corpus")
    if int(header["step_index"]) != step or header["carrier"] != carrier:
        raise RuntimeError("corpus anchor identity mismatch")
    lab_c2_ref = {lab_c2[(u, base_map[u])] for u in users}

    # ---- per-profile targets ---------------------------------------------
    profiles = []
    for order, cfg in enumerate(catalogue):
        cid = cfg.configuration_id
        A = changed[cid]
        rec = {"order": order, "id": cid, "k": len(A), "kind": cfg.kind}
        if cid in sel_invalid or any((u, cfg.mapping[u]) not in d_incl for u in A):
            rec["selection_invalid"] = True
            profiles.append(rec)
            continue
        m = cfg.mapping
        c1 = sum((d_incl[(u, m[u])] for u in A), Fraction())
        c1p = sum((d_phys[(u, m[u])] for u in A), Fraction())
        c2 = sum((c2_val[(u, m[u])] - c2_ref for u in A), Fraction())
        c2s = sum((c2_surplus[(u, m[u])] - c2_ref_surplus for u in A), Fraction())
        if A:
            fi, fp = f_incl(cfg)
            dF, dFp = (fi - fb_incl) / kappa, (fp - fb_phys) / kappa
        else:
            dF = dFp = Fraction()
        if len(A) >= 2:
            c3, c3p = dF - c1, dFp - c1p
        else:
            c3 = c3p = Fraction()
            if A and abs(float(dF - c1)) > 1e-9:
                raise RuntimeError("singleton psi not zero")
        rec.update({
            "C1": float(c1), "C2": float(c2), "C3": float(c3),
            "C1_phys": float(c1p), "C2_surplus": float(c2s), "C3_phys": float(c3p),
            "dF": float(dF), "dF_phys": float(dFp),
        })
        # corpus-label versions
        try:
            lc1 = math.fsum(lab_c1[(u, m[u])] for u in A)
            lc2 = math.fsum(lab_c2[(u, m[u])] - lab_c2[(u, base_map[u])] for u in A)
            lc3 = lab_psi[cfg.assignments] if len(A) >= 2 else 0.0
            rec.update({"L_C1": lc1, "L_C2": lc2, "L_C3": lc3,
                        "L_C3_phys": lab_psi_phys[cfg.assignments] if len(A) >= 2 else 0.0})
        except KeyError as exc:
            rec["label_missing"] = repr(exc)[:120]
        profiles.append(rec)

    multi_cat = {cfg.assignments for cfg in catalogue if len(changed[cfg.configuration_id]) >= 2}
    coalition_set_equal = multi_cat == set(lab_psi)
    del sel
    gc.collect()

    # ---- ONE separate fresh realised dense full-48 endpoint evaluator ------
    rss = rss_max_configuration(E, tape, step, base)
    end = E.StepEvaluator(tape, setting, step, transition_from=incumbent, cell_rekeyed_users=rekeys,
                          field="realised", counter=E.EvaluationCounter(), run_setting=run_setting,
                          boundary_indices=tuple(range(48)))
    rest = [cfg for cfg in catalogue[1:]]
    first = (base, rss, *rest[:ENDPOINT_BATCH])
    end.evaluate_many(first)
    keep = {base.configuration_id, rss.configuration_id}
    metrics = {}
    for cid in keep:
        metrics[cid] = outcome_metrics(E, tape, step, incumbent, end._evaluated[cid])
    done = rest[:ENDPOINT_BATCH]
    offset = ENDPOINT_BATCH
    while True:
        for cfg in done:
            p = end._evaluated.get(cfg.configuration_id)
            if p is not None:
                metrics[cfg.configuration_id] = outcome_metrics(E, tape, step, incumbent, p)
                if cfg.configuration_id not in keep:
                    end._evaluated.pop(cfg.configuration_id, None)
        if offset >= len(rest):
            break
        done = rest[offset:offset + ENDPOINT_BATCH]
        end.evaluate_many(done)
        offset += ENDPOINT_BATCH
    end_invalid = len(end._invalid)
    end_evals = end.physical_evaluations
    del end
    gc.collect()
    t_end = time.perf_counter()

    base_m = metrics[base.configuration_id]
    base_ee = base_m["bits"] / base_m["joules"]
    for rec in profiles:
        m = metrics.get(rec["id"])
        if m is None:
            rec["endpoint_invalid"] = True
            continue
        rec.update(m)
        rec["dEE"] = (m["bits"] / m["joules"] - base_ee) / 1e6
        rec["dF48_phys"] = float(((Fraction(m["bits"]) - Fraction(base_m["bits"]))
                                   - eta * (Fraction(m["joules"]) - Fraction(base_m["joules"]))) / kappa)

    eligible = [i for i, r in enumerate(profiles)
                if not r.get("selection_invalid") and not r.get("endpoint_invalid")]
    assert eligible[0] == 0
    selections = {}
    for family, prefix in (("fresh", ""), ("label", "L_")):
        for subset in LATTICE:
            name = "+".join(subset) if subset else "NONE"
            if family == "label" and any("label_missing" in profiles[i] for i in eligible):
                selections[f"{family}:{name}"] = None
                continue
            scores = {i: math.fsum(profiles[i].get(prefix + r, 0.0) for r in subset) for i in eligible}
            selections[f"{family}:{name}"] = select(scores, eligible)
    for name, field in (("C1_phys", "C1_phys"), ("C2_surplus", "C2_surplus"), ("C3_phys", "C3_phys"),
                        ("dF", "dF"), ("dF_phys", "dF_phys")):
        scores = {i: profiles[i][field] for i in eligible}
        selections[f"diag:{name}"] = select(scores, eligible)

    # parity summaries
    def maxdiff(a, b, rows):
        vals = [abs(r[a] - r[b]) for r in rows if a in r and b in r]
        return max(vals) if vals else None
    valid_rows = [profiles[i] for i in eligible]
    parity = {
        "C1_max_abs": maxdiff("C1", "L_C1", valid_rows),
        "C2_max_abs": maxdiff("C2", "L_C2", valid_rows),
        "C3_max_abs": maxdiff("C3", "L_C3", valid_rows),
        "C3_phys_max_abs": maxdiff("C3_phys", "L_C3_phys", valid_rows),
        "c2_reference_fresh": float(c2_ref), "c2_reference_corpus_values": sorted(lab_c2_ref),
        "coalition_set_equals_catalogue_multi_user_set": coalition_set_equal,
        "catalogue_multi_user_count": len(multi_cat), "coalition_rows": len(lab_psi),
        "label_missing_profiles": sum("label_missing" in r for r in profiles),
    }
    return {
        "global_anchor_index": global_index, "world_index": world_index, "step_index": step,
        "carrier": carrier, "anchor_id": f"{meta['world_id']}|{step}|{carrier}",
        "catalogue": cat_meta, "base_id": base.configuration_id, "rss_max": metrics[rss.configuration_id],
        "base": base_m, "selection_invalid": len(sel_invalid), "endpoint_invalid": end_invalid,
        "endpoint_physical_boundary_evaluations": end_evals,
        "eligible_profiles": len(eligible), "selections": selections, "parity": parity,
        "corpus_digests": digests, "profiles": profiles,
        "wall": {"catalogue": t_cat - t0, "selection_and_c2": t_sel - t_cat, "endpoint": t_end - t_sel},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", required=True, help="global index range a-b inclusive")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    lo, hi = (int(x) for x in args.anchors.split("-"))
    check_runtime()
    out = Path(args.out)
    if out.exists():
        raise RuntimeError(f"refusing to overwrite {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    pilot = load_pilot()
    E = pilot.ENGINE
    assert E.SELECTION_BOUNDARY_INDICES == (0,), E.SELECTION_BOUNDARY_INDICES
    install_stub(E)
    from mcrl.physics_v025 import targets as targets_mod
    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape
    calibration = load_calibration(pilot)
    sources, coalitions = corpus_index()
    tapes = {}
    todo = list(range(lo, hi + 1))
    started = time.perf_counter()
    with out.open("w", encoding="utf-8") as fh:
        for k, g in enumerate(todo, 1):
            if g < 90:
                world_index, step, ci = 1, g // 3, g % 3
            else:
                world_index, step, ci = 2, (g - 90) // 3, (g - 90) % 3
            if world_index not in tapes:
                tapes.clear()
                gc.collect()
                tapes[world_index] = build_world_tape(
                    domain=pilot.TRAIN_WORLDS[world_index - 1],
                    provider=LegacyWorldProvider(role="pilot-source"), steps=33, start_time_s=0.0)
                print(f"tape world {world_index} built peak RSS {peak_rss()/2**30:.3f} GiB", flush=True)
            rec = run_anchor(pilot, E, calibration, tapes[world_index], world_index, step, CARRIERS[ci],
                             g, sources[g], coalitions[g], targets_mod)
            rec["peak_rss_bytes"] = peak_rss()
            fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
            fh.flush()
            check_runtime()
            print(f"anchor {k}/{len(todo)} global={g} profiles={len(rec['profiles'])} "
                  f"wall={json.dumps({a: round(b, 1) for a, b in rec['wall'].items()})} "
                  f"parity={json.dumps({a: rec['parity'][a] for a in ('C1_max_abs','C2_max_abs','C3_max_abs','coalition_set_equals_catalogue_multi_user_set')})} "
                  f"peak RSS {peak_rss()/2**30:.3f} GiB", flush=True)
            gc.collect()
    assert SCALAR_CALLS == 0
    print(f"DONE scalar_evaluate_calls={SCALAR_CALLS} wall={time.perf_counter()-started:.1f}s "
          f"PEAK_RSS_BYTES={peak_rss()} script_sha256={sha256(Path(__file__))}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
