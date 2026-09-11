#!/usr/bin/env python3
"""ETAFIX phase C - the same exchange-rate tests with Phi included in F.

COORDVALUE-2026-09-10 scores the deployed objective as
    F_phi = B - eta*E - Phi_cost,  Phi_cost = -kappa * _phi_for(incumbent, config, rekeys)
whereas BASIN2 / CLEANPATH / PANELCEIL / ETAFIX phases A-B used runner._objective
alone (B - eta*E).  This phase repeats the order sweep, the Dinkelbach iteration
and the descent-from-RSS_MAX test under F_phi.  All helpers are imported
unchanged from run_etafix.py (sha256 0fcd90e5...).  Learner-free, development
anchors only, no sealed artefact written, scalar evaluate fail-closed.
"""

from __future__ import annotations

from fractions import Fraction
import gc
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import sys
import time

BASE_DRIVER = Path("/home/sat/mcrl-v025-etafix-ws/.scratch/etafix/run_etafix.py")
BASE_DRIVER_SHA = "0fcd90e5ce0447641549011e8df0ca41b119da04360026d8a68cd923f6b4d73e"
AB_RECEIPT = Path("/home/sat/mcrl-v025-etafix-ws/.scratch/etafix/etafix-receipt.json")
OUTPUT = Path("/home/sat/mcrl-v025-etafix-ws/.scratch/etafix/etafix-phi-receipt.json")


def load_base():
    digest = hashlib.sha256(BASE_DRIVER.read_bytes()).hexdigest()
    if digest != BASE_DRIVER_SHA:
        raise RuntimeError("base ETAFIX driver changed")
    spec = importlib.util.spec_from_file_location("etafix_base", BASE_DRIVER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["etafix_base"] = module
    spec.loader.exec_module(module)
    return module


E = load_base()
ARM_NAMES = E.ARM_NAMES
fp = E.fraction_payload


def write(payload: dict) -> None:
    payload["receipt_sha256"] = E.canonical_digest(payload)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_name(f".{OUTPUT.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n",
                   encoding="utf-8")
    tmp.replace(OUTPUT)


def phi_cost(runner, calibration, incumbent, config, rekeys) -> Fraction:
    """Positive Phi cost in bit units, exactly as COORDVALUE total_f."""
    preference = runner._phi_for(incumbent, config, cell_rekeyed_users=rekeys)
    return -calibration.kappa_bits_per_user_step * preference


def first_improvement_phi(panel, runner, calibration, tape, step_index, base, start,
                          incumbent, run_setting, kind):
    """BASIN2's declared first-improvement algorithm; objective is F_phi."""
    evaluator = E.fresh_evaluator(runner, tape, step_index, incumbent, run_setting,
                                  "realised", (0,))
    rekeys = runner._rekeyed_users(tape, step_index)
    options, census = runner._legal_options(tape, step_index)
    first_user = min(options)
    warm = tuple(panel.candidate(runner, base, start, first_user, identity, kind)
                 for identity in options[first_user] if identity != start.mapping[first_user])
    first_call = E.dedupe((base, start, *warm[:panel.UNILATERAL_BATCH_SIZE]))
    assert first_call[0].configuration_id == base.configuration_id
    assert len(first_call) > 1
    evaluator.evaluate_many(first_call)

    def score(config, prof):
        return runner._objective(prof, calibration) - phi_cost(
            runner, calibration, incumbent, config, rekeys)

    guard = panel.served(E.profile(evaluator, start))
    current = start
    moves = comparisons = submissions = passes = 0
    moves_per_pass = []
    while True:
        moved = 0
        for user in sorted(options):
            current_value = score(current, E.profile(evaluator, current))
            candidates = tuple(panel.candidate(runner, base, current, user, identity, kind)
                               for identity in options[user] if identity != current.mapping[user])
            accepted = None
            for offset in range(0, len(candidates), panel.UNILATERAL_BATCH_SIZE):
                batch = candidates[offset:offset + panel.UNILATERAL_BATCH_SIZE]
                evaluator.evaluate_many(batch)
                submissions += len(batch)
                for row in batch:
                    comparisons += 1
                    prof = evaluator._evaluated.get(row.configuration_id)
                    if prof is None or panel.served(prof) < guard:
                        continue
                    if score(row, prof) > current_value:
                        accepted = row
                        break
                if accepted is not None:
                    break
            if accepted is not None:
                current = accepted
                moves += 1
                moved += 1
        passes += 1
        moves_per_pass.append(moved)
        if moved == 0:
            break
        if passes > 100:
            raise RuntimeError("first-improvement exceeded 100 passes")
    result = {
        "selection_path": "fresh realised dense StepEvaluator(boundary_indices=(0,)); first evaluate_many contains BASE, start, and ordered first-user candidates; objective F_phi",
        "eta_used": fp(calibration.eta_ref),
        "start_configuration_id": start.configuration_id,
        "selected_configuration_id": current.configuration_id,
        "guard_from_start": guard,
        "fixed_point_at_start": moves_per_pass[0] == 0,
        "moves": moves,
        "passes_including_certificate": passes,
        "moves_per_pass": moves_per_pass,
        "comparisons": comparisons,
        "submitted_candidate_slots": submissions,
        "physical_boundary_evaluations": evaluator.physical_evaluations,
    }
    del evaluator
    gc.collect()
    return current, result


def order_phi(totals, phis, eta):
    values = {a: totals[a][0] - eta * totals[a][1] - phis[a] for a in ARM_NAMES}
    return sorted(ARM_NAMES, key=lambda a: (-values[a], a)), values


def sweep_phi(totals, phis, ee_order):
    lower, lower_from, upper, upper_from = Fraction(0), "eta >= 0", None, None
    never = []
    pairs = []
    for i, j in itertools.combinations(range(len(ee_order)), 2):
        hi, lo = ee_order[i], ee_order[j]
        d_num = (totals[hi][0] - phis[hi]) - (totals[lo][0] - phis[lo])
        d_e = totals[hi][1] - totals[lo][1]
        row = {"higher_ee_arm": hi, "lower_ee_arm": lo,
               "delta_bits_minus_phi_cost": fp(d_num), "delta_joules": fp(d_e)}
        if d_e == 0:
            row["constraint"] = "always" if d_num > 0 else "never"
            row["crossing_eta_bit_per_j"] = None
            if d_num <= 0:
                never.append(f"{hi} > {lo}")
        else:
            x = d_num / d_e
            row["crossing_eta_bit_per_j"] = fp(x)
            if d_e > 0:
                row["constraint"] = "upper"
                if upper is None or x < upper:
                    upper, upper_from = x, f"{hi} > {lo}"
            else:
                row["constraint"] = "lower"
                if x > lower:
                    lower, lower_from = x, f"{hi} > {lo}"
        pairs.append(row)
    nonempty = not never and (upper is None or lower < upper)
    return {"pairs": pairs, "binding_lower_bound": fp(lower), "binding_lower_from": lower_from,
            "binding_upper_bound": None if upper is None else fp(upper),
            "binding_upper_from": upper_from, "never_satisfiable": never,
            "matching_eta_interval_nonempty": bool(nonempty)}


def main() -> int:
    E.check_runtime()
    started = time.perf_counter()
    ab = json.loads(AB_RECEIPT.read_text(encoding="utf-8"))
    if ab.get("status") != "COMPLETE" or ab.get("receipt_sha256") != E.canonical_digest(ab):
        raise RuntimeError("phase A/B receipt incomplete or digest failed")
    clean = json.loads(E.CLEAN_RECEIPT.read_text(encoding="utf-8"))
    if clean.get("receipt_sha256") != E.canonical_digest(clean):
        raise RuntimeError("clean receipt digest failed")
    frozen = clean["panel"]
    panel = E.load_panel()
    pilot = panel.load_pilot()
    runner = pilot.ENGINE
    calibration = panel.load_calibration(pilot)
    run_setting = runner.run_setting_for("a-r0")
    E.forbid_scalar_evaluate(runner)
    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape

    print(f"peak RSS {E.peak_rss_bytes()/2**30:.3f} GiB before tape", flush=True)
    tape = build_world_tape(domain=pilot.TRAIN_WORLDS[0],
                            provider=LegacyWorldProvider(role="pilot-source"),
                            steps=33, start_time_s=0.0)
    E.check_runtime()
    print(f"peak RSS {E.peak_rss_bytes()/2**30:.3f} GiB after tape", flush=True)

    payload = {
        "schema": "mcrl-v025-etafix-phi-v1", "status": "RUNNING",
        "claim_status": "DESIGN_PHASE_DIAGNOSTIC_NOT_A_CLAIM", "learner_free": True,
        "python": sys.executable, "niceness": os.getpriority(os.PRIO_PROCESS, 0),
        "process_count": 1, "thread_pins": {n: os.environ[n] for n in E.THREAD_VARS},
        "base_driver_sha256": BASE_DRIVER_SHA, "ab_receipt_sha256": ab["receipt_sha256"],
        "objective": "F_phi = runner._objective(profile, cal) - Phi_cost; Phi_cost = -kappa * runner._phi_for(incumbent, config, cell_rekeyed_users=rekeys); incumbent = prior-step carrier BASE (COORDVALUE total_f)",
        "eta_ref_in_force": fp(calibration.eta_ref),
        "kappa_bits_per_user_step": fp(calibration.kappa_bits_per_user_step),
        "anchors": [], "descent_anchors": [],
    }
    write(payload)

    # Phase C1: in-process parity + per-arm Phi cost (configuration-only).
    contexts = []
    for position, row in enumerate(frozen, 1):
        index, step, carrier = int(row["global_anchor_index"]), int(row["step_index"]), str(row["carrier"])
        base = runner._base_configuration(tape, step, carrier)
        incumbent = runner._base_configuration(tape, max(0, step - 1), carrier)
        rekeys = runner._rekeyed_users(tape, step)
        configs = E.direct_configurations(runner, tape, step, base, index)
        for name in ("MYOPIC_GREEDY", "FIRST_IMPROVEMENT_FP"):
            configs[name] = E.configuration_from_receipt(
                runner, base, clean["anchors"][index]["arms"][name], f"etafix-phi-{name.lower()}")
        for name in ARM_NAMES:
            if configs[name].configuration_id != clean["anchors"][index]["arms"][name]["configuration_id"]:
                raise RuntimeError(f"{name} differs from sealed clean receipt at {index}")
        endpoint = E.endpoint_batch(panel, runner, tape, step, base, incumbent, run_setting, configs)
        phis = {n: phi_cost(runner, calibration, incumbent, configs[n], rekeys) for n in ARM_NAMES}
        changed = {n: sum(1 for u in configs[n].mapping if configs[n].mapping[u] != incumbent.mapping[u])
                   for n in ARM_NAMES}
        prior = ab["phase_a"][position - 1]["endpoint"]["metrics"]
        same = all(endpoint["metrics"][n]["bits_exact"] == prior[n]["bits_exact"]
                   and endpoint["metrics"][n]["joules_exact"] == prior[n]["joules_exact"]
                   for n in ARM_NAMES)
        payload["anchors"].append({
            "global_anchor_index": index, "step_index": step, "carrier": carrier,
            "endpoint": endpoint, "phi_cost_bits": {n: fp(phis[n]) for n in ARM_NAMES},
            "users_changed_vs_incumbent": changed,
            "endpoint_bit_identical_to_phase_a": same,
        })
        contexts.append((index, step, carrier, configs["RSS_MAX"]))
        write(payload)
        E.check_runtime()
        print(f"phase C1 anchor {position}/{len(frozen)} peak RSS {E.peak_rss_bytes()/2**30:.3f} GiB", flush=True)

    rows = [a["endpoint"]["metrics"] for a in payload["anchors"]]
    totals = {n: E.pooled_exact(rows, n) for n in ARM_NAMES}
    phis = {n: sum((Fraction(a["phi_cost_bits"][n]["numerator"], a["phi_cost_bits"][n]["denominator"])
                    for a in payload["anchors"]), Fraction()) for n in ARM_NAMES}
    parity = {n: float(totals[n][0] / totals[n][1]) / 1e6 for n in ("RSS_MAX", "FIRST_IMPROVEMENT_FP")}
    ok = round(parity["RSS_MAX"], 6) == 41.621560 and round(parity["FIRST_IMPROVEMENT_FP"], 6) == 31.028111
    payload["parity"] = {"measured": parity, "passed": ok,
                         "all_endpoints_bit_identical_to_phase_a": all(a["endpoint_bit_identical_to_phase_a"] for a in payload["anchors"])}
    if not ok:
        payload["status"] = "PARITY_FAILED"
        write(payload)
        raise RuntimeError(f"parity failed {parity}")
    print("parity reproduced: " + json.dumps(parity, sort_keys=True), flush=True)

    ee_order = sorted(ARM_NAMES, key=lambda a: (-(totals[a][0] / totals[a][1]), a))
    payload["pooled"] = {n: {"bits": fp(totals[n][0]), "joules": fp(totals[n][1]),
                             "phi_cost_bits": fp(phis[n]),
                             "phi_cost_over_bits": float(phis[n] / totals[n][0]),
                             "ee_mbit_per_j": float(totals[n][0] / totals[n][1]) / 1e6} for n in ARM_NAMES}
    payload["ee_order"] = ee_order
    payload["f_phi_order_at_eta_ref"] = order_phi(totals, phis, calibration.eta_ref)[0]
    payload["sweep_phi"] = sweep_phi(totals, phis, ee_order)
    crossings = sorted({Fraction(r["crossing_eta_bit_per_j"]["numerator"], r["crossing_eta_bit_per_j"]["denominator"])
                        for r in payload["sweep_phi"]["pairs"] if r["crossing_eta_bit_per_j"] is not None})
    probes = {Fraction(0), calibration.eta_ref, E.V023_ETA}
    probes |= {c + d for c in crossings if c > 0 for d in (Fraction(-1, 1000), Fraction(0), Fraction(1, 1000))}
    probes |= {totals[n][0] / totals[n][1] for n in ARM_NAMES}
    probes |= {Fraction(v) for v in (10**6, 5 * 10**6, 2 * 10**7, 3 * 10**7, 5 * 10**7, 10**8, 10**9, 10**12)}
    grid = []
    for eta in sorted(p for p in probes if p >= 0):
        order, values = order_phi(totals, phis, eta)
        bad = E.discordant_pairs(order, ee_order)
        grid.append({"eta_mbit_per_j": float(eta) / 1e6, "eta_bit_per_j": fp(eta), "f_phi_order": order,
                     "matches_ee_order": order == ee_order, "discordant_pair_count": len(bad),
                     "discordant_pairs": bad, "argmax": order[0]})
    payload["eta_grid_phi"] = grid
    payload["any_eta_matches_ee_order_phi"] = any(g["matches_ee_order"] for g in grid)
    payload["min_discordant_pairs_phi"] = min(g["discordant_pair_count"] for g in grid)

    eta, seq, fixed = calibration.eta_ref, [], None
    for it in range(20):
        order, values = order_phi(totals, phis, eta)
        best = order[0]
        nxt = totals[best][0] / totals[best][1]
        seq.append({"iteration": it, "eta_mbit_per_j": float(eta) / 1e6, "eta_bit_per_j": fp(eta),
                    "argmax_f_phi_arm": best, "f_phi_at_argmax": fp(values[best]),
                    "next_eta_mbit_per_j": float(nxt) / 1e6, "converged": nxt == eta})
        if nxt == eta:
            fixed = eta
            break
        eta = nxt
    payload["dinkelbach_phi"] = {"sequence": seq, "converged": fixed is not None,
                                 "fixed_point_bit_per_j": None if fixed is None else fp(fixed),
                                 "fixed_point_mbit_per_j": None if fixed is None else float(fixed) / 1e6,
                                 "note": "with Phi the Dinkelbach identity F(x;EE(x))=0 no longer holds; F_phi at the fixed point is -Phi_cost of the argmax"}
    write(payload)
    if fixed is None:
        raise RuntimeError("Phi Dinkelbach did not converge")

    cal_star = pilot.PilotCalibration(
        eta_ref=fixed, lambda_bits_per_j=fixed,
        kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
        bits_ref=fixed.numerator, joules_ref=Fraction(fixed.denominator),
        users=calibration.users, source="etafix-phi-dinkelbach-probe-not-deployed")
    assert cal_star.eta_ref == fixed

    # Phase C2: descent from RSS_MAX under F_phi at eta_ref and at the Phi fixed point.
    for position, (index, step, carrier, rss) in enumerate(contexts, 1):
        base = runner._base_configuration(tape, step, carrier)
        incumbent = runner._base_configuration(tape, max(0, step - 1), carrier)
        rekeys = runner._rekeyed_users(tape, step)
        from_ref, s_ref = first_improvement_phi(panel, runner, calibration, tape, step, base, rss,
                                                incumbent, run_setting, "etafix-phi-first-rss-eta-ref")
        from_star, s_star = first_improvement_phi(panel, runner, cal_star, tape, step, base, rss,
                                                  incumbent, run_setting, "etafix-phi-first-rss-eta-star")
        endpoint = E.endpoint_batch(panel, runner, tape, step, base, incumbent, run_setting, {
            "NEAREST_ELIGIBLE": base, "RSS_MAX": rss,
            "PHI_FROM_RSS_AT_ETA_REF": from_ref, "PHI_FROM_RSS_AT_ETA_STAR": from_star})
        payload["descent_anchors"].append({
            "global_anchor_index": index, "step_index": step, "carrier": carrier,
            "search_at_eta_ref": s_ref, "search_at_eta_star": s_star, "endpoint": endpoint,
            "phi_cost_bits": {"RSS_MAX": fp(phi_cost(runner, calibration, incumbent, rss, rekeys)),
                              "PHI_FROM_RSS_AT_ETA_REF": fp(phi_cost(runner, calibration, incumbent, from_ref, rekeys)),
                              "PHI_FROM_RSS_AT_ETA_STAR": fp(phi_cost(runner, calibration, incumbent, from_star, rekeys))},
        })
        write(payload)
        E.check_runtime()
        print(f"phase C2 anchor {position}/{len(contexts)} peak RSS {E.peak_rss_bytes()/2**30:.3f} GiB "
              + json.dumps({"moves_eta_ref": s_ref["moves"], "moves_eta_star": s_star["moves"]}), flush=True)

    brows = [a["endpoint"]["metrics"] for a in payload["descent_anchors"]]
    pooled = {}
    for tag in ("NEAREST_ELIGIBLE", "RSS_MAX", "PHI_FROM_RSS_AT_ETA_REF", "PHI_FROM_RSS_AT_ETA_STAR"):
        b, j = E.pooled_exact(brows, tag)
        pooled[tag] = {"bits_float": float(b), "joules_float": float(j),
                       "ee_mbit_per_j": float(b / j) / 1e6,
                       "served_count": sum(int(r[tag]["served_count"]) for r in brows)}
    for key, tag in (("search_at_eta_ref", "PHI_FROM_RSS_AT_ETA_REF"), ("search_at_eta_star", "PHI_FROM_RSS_AT_ETA_STAR")):
        pooled[tag]["total_moves"] = sum(a[key]["moves"] for a in payload["descent_anchors"])
        pooled[tag]["moved_anchor_count"] = sum(a[key]["moves"] > 0 for a in payload["descent_anchors"])
    rss_ee = pooled["RSS_MAX"]["ee_mbit_per_j"]
    payload["descent_phi"] = {"pooled": pooled, "rss_max_ee": rss_ee,
                              "descends_at_eta_ref": pooled["PHI_FROM_RSS_AT_ETA_REF"]["ee_mbit_per_j"] < rss_ee,
                              "descends_at_eta_star": pooled["PHI_FROM_RSS_AT_ETA_STAR"]["ee_mbit_per_j"] < rss_ee,
                              "delta_ee_at_eta_ref": pooled["PHI_FROM_RSS_AT_ETA_REF"]["ee_mbit_per_j"] - rss_ee,
                              "delta_ee_at_eta_star": pooled["PHI_FROM_RSS_AT_ETA_STAR"]["ee_mbit_per_j"] - rss_ee}
    payload["scalar_evaluate_calls"] = E.SCALAR_EVALUATE_CALLS
    assert E.SCALAR_EVALUATE_CALLS == 0
    payload["status"] = "COMPLETE"
    payload["peak_rss_bytes"] = E.peak_rss_bytes()
    payload["wall_seconds"] = time.perf_counter() - started
    payload["runner_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    write(payload)
    E.check_runtime()
    print(f"peak RSS {E.peak_rss_bytes()/2**30:.3f} GiB final ({E.peak_rss_bytes()} bytes)", flush=True)
    print(json.dumps({"any_eta_matches_phi": payload["any_eta_matches_ee_order_phi"],
                      "min_disc_phi": payload["min_discordant_pairs_phi"],
                      "dinkelbach_phi": payload["dinkelbach_phi"]["fixed_point_mbit_per_j"],
                      "descent_phi": payload["descent_phi"],
                      "scalar_evaluate_calls": E.SCALAR_EVALUATE_CALLS}, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
