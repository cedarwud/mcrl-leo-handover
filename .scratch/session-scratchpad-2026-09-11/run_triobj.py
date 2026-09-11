#!/usr/bin/env python3
"""TRIOBJ -- learner-free feasibility of a bits / energy / time objective decomposition.

DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM.  Reads sealed trees read-only; writes only
inside /home/sat/mcrl-v025-triobj-ws.  No learner, checkpoint, loss or
evaluation-only claim date is imported or read.  Development world 1, steps 0-3,
three carriers (the frozen 12-anchor panel).

Objective definitions are frozen in DEFINITIONS below and committed to git before
any measurement (see triobj-definitions.json).  They are not tuned afterwards.

Evaluator discipline
--------------------
* StepEvaluator.evaluate is replaced class-wide by a counting raising stub before
  any evaluator exists; the counter is asserted zero at completion.
* parity mode: per physical step one fresh realised dense full-48 evaluator whose
  single evaluate_many call holds the three carrier BASE mappings, RSS_MAX and
  CROWDED.  STOP unless pooled RSS_MAX == 41.621560 and CROWDED == 46.110374
  (rounded to 6 decimals) at full service.
* shard mode: per physical step one fresh realised dense full-48 endpoint
  evaluator; call 1 = the parity set (asserted bit-identical to the parity
  receipt), call 2 = every remaining pool mapping of that step's three carriers
  in ONE evaluate_many.  Physical mappings are carrier-invariant in the dense
  a-r0 path (transition_from is never read there), so one endpoint batch per
  step serves its three carrier anchors.  Per carrier anchor one fresh realised
  dense boundary-0 selection evaluator whose ONE evaluate_many call contains BASE
  and every pool candidate of that anchor.  Profiles are read only from
  StepEvaluator._evaluated.
* The deployed bounded-union-v2 catalogue is rebuilt around each carrier BASE
  with an auxiliary fresh nominal boundary-0 dense evaluator used only for the
  catalogue's own sealed top-10 user ranking (as COORDVALUE).  It scores or
  selects nothing here.
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

WORKSPACE = Path("/home/sat/mcrl-v025-triobj-ws")
OUTDIR = WORKSPACE / ".scratch/triobj"
PANEL_RUNNER = Path("/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/run_panelceil.py")
CROWD_RUNNER = Path("/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run_crowding_cost.py")
CLEAN_RECEIPT = Path("/home/sat/mcrl-v025-rank2-ws/.scratch/cleanpath/cleanpath-receipt.json")
CALIBRATION_PATH = Path(
    "/home/sat/mcrl-v025-c1c2suff-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/"
    "PILOT_NOT_CLAIM-calibration.json"
)
PYTHON = "/home/sat/mcrl-leo-handover/.venv/bin/python"
THREAD_VARS = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
MAX_RSS_BYTES = 5_000_000_000
EXPECTED = {"RSS_MAX": 41.621560, "CROWDED": 46.110374}
DECISION_INTERVAL_S = 30.08
H_BEAM_S = 0.062   # constants_v025.SAME_SATELLITE_INTERRUPTION_S (asserted below)
H_SAT_S = 0.142    # constants_v025.SATELLITE_CHANGE_INTERRUPTION_S (asserted below)
LADDER_K = (1, 2, 4, 8, 16, 32, 64)
FRACTIONS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
SCALAR_CALLS = 0

DEFINITIONS = {
    "schema": "mcrl-v025-triobj-definitions-v1",
    "frozen_before_measurement": True,
    "objectives": {
        "LQ_bits_side_link_quality": (
            "LQ(x) = sum over users with >=1 legal option of m_u(x_u), where m_u(b) = "
            "10*log10(BEAM_RF_CAP_W * nominal_gain[boundary 0, row(u,b)] / noise_power_w(500 MHz)) "
            "- SINR_MIN_DB, the engine's decision-instant nominal link margin "
            "(run_v025_matrix_probe.py:488-494).  A NULL assignment of a user who has legal options "
            "contributes that user's worst legal margin (never strictly preferred).  Its unconstrained "
            "per-user maximiser is RSS_MAX (per-user argmax nominal gain, slant-order tie-break)."
        ),
        "BC_energy_side_beam_concentration": (
            "BC(x) = -(number of distinct beam identities (NORAD, beam) assigned at the decision "
            "instant), the set-level quantity the dense path forms as beam_code/occupancy "
            "(batch.py:195, 208-209).  Higher = fewer opened beams."
        ),
        "P_time_side_persistence": (
            "P(x) = phi_qos(ledger(incumbent -> x)) = -(1.0 * #satellite_change + 0.5 * #beam_change) "
            "(targets.py:72-81 via run_v025_matrix_probe.py:_phi_for 1164-1175), incumbent = the "
            "prior-step carrier BASE (step max(0,t-1)), exactly the deployed Phi of COORDVALUE/ETAFIX.  "
            "Higher = fewer association changes.  exit/entry/reentry are free in the code."
        ),
        "S_time_side_secondary_lookahead_survival": (
            "S(x) = number of assigned users whose assigned identity is still a legal option at the "
            "next decision instant (step t+1 boundary 0, _legal_options), same exogenous development "
            "tape.  Secondary time-side definition with physical (geometric) content."
        ),
    },
    "selection": {
        "alone": "per anchor argmax of one objective over the pool",
        "guard": "realised full-48 PHY-served count >= that anchor's BASE full-48 served (primary); "
                 "boundary-0 served >= BASE boundary-0 served reported as a robustness line",
        "tie_break": "exact objective ties (LQ within 1e-9 dB) -> fewest users changed vs BASE -> "
                     "lexicographically smallest configuration_id; the full tie set's EE range is reported",
    },
    "pools": {
        "CAT": "BASE + exact bounded-union-v2 deployed catalogue rebuilt around the carrier BASE",
        "EXT": "CAT + RSS_MAX + crowding nested family (31, incl. CROWDED) + LQ-within-beam-set greedy "
               "drop family from RSS_MAX + greedy add family from the exact minimum cover (first member "
               "MINCOVER_LQ, last member RSS_MAX) + SURV_LQ + persistence families (HOLD_NULL, HOLD_MIN, "
               "HOLD ladder k in 1,2,4,8,16,32,64, HOLD->RSS ladder, HOLD->CROWDED beam-closing ladder)",
        "MIX": "bits-vs-energy mixing family: RSS_MAX + drop + add + crowding family (item 4/5)",
    },
    "combination": {
        "fixed_objective_space": "S_w = sum_i w_i * (obj_i - min_i)/(max_i - min_i), per-anchor min-max "
                                 "over the pool; one weight vector for all anchors; grid 0.01 (2 objectives), "
                                 "0.05 simplex (3 objectives LQ, BC, P)",
        "fixed_physical": "F = B - eta_ref E (and - kappa*Phi_cost), eta_ref = in-force V0.25 calibration, "
                          "on boundary-0 (deployed horizon) and full-48",
        "ratio_consistent": "Dinkelbach: eta <- pooled achieved B/E of the per-anchor argmax of B - eta E, "
                            "iterated to a fixed point, on full-48 and on boundary-0 (then scored full-48); "
                            "also per-anchor eta_a",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(payload: dict) -> str:
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    return hashlib.sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    payload["receipt_sha256"] = canonical_digest(payload)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def check_runtime() -> None:
    if sys.executable != PYTHON:
        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        raise RuntimeError("niceness is below 15")
    bad = {n: os.environ.get(n) for n in THREAD_VARS if os.environ.get(n) != "1"}
    if bad:
        raise RuntimeError(f"thread pins are not all one: {bad}")
    if peak_rss_bytes() >= MAX_RSS_BYTES:
        raise MemoryError(f"peak RSS {peak_rss_bytes()} is not below 5 GB")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def forbid_scalar_evaluate(runner) -> None:
    original = runner.StepEvaluator.evaluate

    def forbidden(*args, **kwargs):
        del args, kwargs
        global SCALAR_CALLS
        SCALAR_CALLS += 1
        raise AssertionError("scalar StepEvaluator.evaluate is forbidden on TRIOBJ surfaces")

    forbidden.__wrapped__ = original
    runner.StepEvaluator.evaluate = forbidden
    assert runner.StepEvaluator.evaluate is forbidden


def fresh_evaluator(runner, tape, step_index, incumbent, run_setting, field, boundaries):
    if tape.steps[step_index].arrays is None:
        raise AssertionError("dense primitive arrays are required")
    ev = runner.StepEvaluator(
        tape, runner._setting("a-r0"), step_index,
        transition_from=incumbent,
        cell_rekeyed_users=runner._rekeyed_users(tape, step_index),
        field=field, counter=runner.EvaluationCounter(),
        run_setting=run_setting, boundary_indices=boundaries,
    )
    assert ev.boundary_indices == boundaries and ev.field == field
    return ev


def dedupe(configs):
    return tuple({row.configuration_id: row for row in configs}.values())


def cached(ev, config):
    p = ev._evaluated.get(config.configuration_id)
    if p is None:
        raise RuntimeError(f"profile absent from dense cache: {config.configuration_id[:80]}")
    return p


def served(p) -> int:
    return sum(bool(v) for v in p.score.served_phy.values())


def attained(p) -> int:
    values = p.score.rate_target_attained
    if values is None:
        raise RuntimeError("profile omitted rate-target attainment")
    return sum(bool(v) for v in values.values())


def endpoint_metrics(p) -> dict:
    return {
        "bits": float(p.bits),
        "joules": float(p.joules),
        "served": served(p),
        "attained": attained(p),
        "pa_j": float(p.energy_components["pa_j"]),
        "circuit_j": float(p.energy_components["circuit_j"]),
        "baseband_j": float(p.energy_components["baseband_j"]),
        "mean_radiating_beams": float(p.lit_beam_seconds) / DECISION_INTERVAL_S,
        "rf_cap_hits": int(p.rf_cap_hits),
        "rf_transmissions": int(p.rf_transmission_observations),
    }


# ---------------------------------------------------------------- link tables

class StepLinks:
    def __init__(self, runner, tape, step_index, noise_fn, rf_cap, sinr_min_db):
        options, census = runner._legal_options(tape, step_index)
        self.options = {u: tuple(ids) for u, ids in options.items()}
        self.census = census
        arrays = tape.steps[step_index].arrays
        row_of = arrays._row_index()
        noise = noise_fn(500_000_000.0)
        self.gain, self.margin, self.ordinal = {}, {}, {}
        for u, ids in self.options.items():
            g, m, o = {}, {}, {}
            for k, b in enumerate(ids):
                value = float(arrays.nominal_gain[0, row_of[(u, b)]])
                g[b] = value
                m[b] = 10.0 * math.log10(max(rf_cap * value / noise, sys.float_info.min)) - sinr_min_db
                o[b] = k
            self.gain[u], self.margin[u], self.ordinal[u] = g, m, o
        self.users = tuple(sorted(self.options))
        self.all_beams = tuple(sorted({b for ids in self.options.values() for b in ids}))
        self.users_of = {}
        for u, ids in self.options.items():
            for b in ids:
                self.users_of.setdefault(b, []).append(u)

    def best_in(self, u, allowed=None):
        cands = [b for b in self.options[u] if allowed is None or b in allowed]
        if not cands:
            return None
        return min(cands, key=lambda b: (-self.gain[u][b], self.ordinal[u][b]))

    def lq(self, mapping) -> float:
        total = []
        for u in self.users:
            if not self.options[u]:
                continue
            b = mapping[u]
            total.append(min(self.margin[u].values()) if b is None else self.margin[u][b])
        return math.fsum(total)


def beams_of(mapping) -> int:
    return len({b for b in mapping.values() if b is not None})


def rss_mapping(links: StepLinks) -> dict:
    return {u: (links.best_in(u) if links.options[u] else None) for u in links.users}


def within_set(links: StepLinks, allowed) -> dict | None:
    mapping = {}
    for u in links.users:
        if not links.options[u]:
            mapping[u] = None
            continue
        b = links.best_in(u, allowed)
        if b is None:
            return None
        mapping[u] = b
    return mapping


def drop_family(links: StepLinks, start: dict) -> list[dict]:
    """Greedy: remove the opened beam whose removal loses least LQ; users re-best within set."""
    current = dict(start)
    opened = {b for b in current.values() if b is not None}
    members = [dict(current)]
    while True:
        best = None
        for b in sorted(opened):
            affected = [u for u in links.users if current[u] == b]
            rest = opened - {b}
            loss, feasible, moves = 0.0, True, {}
            for u in affected:
                nb = links.best_in(u, rest)
                if nb is None:
                    feasible = False
                    break
                loss += links.margin[u][b] - links.margin[u][nb]
                moves[u] = nb
            if not feasible:
                continue
            key = (loss, b)
            if best is None or key < best[0]:
                best = (key, b, moves)
        if best is None:
            break
        _, b, moves = best
        opened.remove(b)
        current.update(moves)
        members.append(dict(current))
    return members


def add_family(links: StepLinks, cover) -> list[dict]:
    """Greedy: from the exact minimum cover, add the beam with the largest LQ gain."""
    opened = set(cover)
    current = within_set(links, opened)
    if current is None:
        raise RuntimeError("minimum cover does not cover every user with options")
    members = [dict(current)]
    while True:
        best = None
        for b in links.all_beams:
            if b in opened:
                continue
            gain = 0.0
            for u in links.users_of.get(b, ()):
                cur = current[u]
                delta = links.margin[u][b] - links.margin[u][cur]
                if delta > 0.0:
                    gain += delta
            if gain <= 1e-12:
                continue
            key = (-gain, b)
            if best is None or key < best[0]:
                best = (key, b)
        if best is None:
            break
        b = best[1]
        opened.add(b)
        for u in links.users_of.get(b, ()):
            current[u] = links.best_in(u, opened)
        members.append(dict(current))
    return members


def surv_mapping(links: StepLinks, next_links: StepLinks) -> dict:
    mapping = {}
    for u in links.users:
        if not links.options[u]:
            mapping[u] = None
            continue
        nxt = set(next_links.options.get(u, ()))
        keep = [b for b in links.options[u] if b in nxt]
        mapping[u] = links.best_in(u, set(keep)) if keep else links.best_in(u)
    return mapping


def persistence_families(links: StepLinks, incumbent: dict, rss: dict, crowd_map: dict, cover):
    hold_min, changers, cost = {}, [], {}
    for u in links.users:
        if not links.options[u]:
            hold_min[u] = None
            continue
        inc = incumbent[u]
        if inc is not None and inc in links.options[u]:
            hold_min[u] = inc
        elif inc is None:
            hold_min[u] = links.best_in(u)            # entry/reentry: free in Phi
        else:
            same = {b for b in links.options[u] if b[0] == inc[0]}
            if same:
                hold_min[u], cost[u] = links.best_in(u, same), 0.5
            else:
                hold_min[u], cost[u] = links.best_in(u), 1.0
            changers.append(u)
    order = sorted(changers, key=lambda u: (cost[u], -links.margin[u][hold_min[u]], u))
    fam = {}
    hold_null = dict(hold_min)
    for u in changers:
        hold_null[u] = None                           # exit: free in Phi
    fam["HOLD_NULL"] = hold_null
    fam["HOLD_MIN"] = dict(hold_min)
    for k in LADDER_K:
        if k >= len(order):
            continue
        m = dict(hold_null)
        for u in order[:k]:
            m[u] = hold_min[u]
        fam[f"HOLD_LADDER_{k:02d}"] = m
    diff = [u for u in links.users if hold_min[u] != rss[u]]
    diff.sort(key=lambda u: (-(links.margin[u][rss[u]] - links.margin[u][hold_min[u]])
                             if hold_min[u] is not None and rss[u] is not None else 0.0, u))
    for f in FRACTIONS:
        k = int(round(f * len(diff)))
        m = dict(hold_min)
        for u in diff[:k]:
            m[u] = rss[u]
        fam[f"HOLD_TO_RSS_{int(f*100):02d}"] = m
    cover_set = set(cover)
    close = sorted(
        {b for b in hold_min.values() if b is not None and b not in cover_set},
        key=lambda b: (sum(1 for u in links.users if hold_min[u] == b), b),
    )
    for f in FRACTIONS + (1.0,):
        j = int(round(f * len(close)))
        closed = set(close[:j])
        m = dict(hold_min)
        for u in links.users:
            if m[u] in closed:
                m[u] = crowd_map[u]
        fam[f"HOLD_TO_CROWDED_{int(f*100):03d}"] = m
    return fam, {"changers": len(changers), "hold_to_rss_diff": len(diff), "closable_beams": len(close)}


# ---------------------------------------------------------------- catalogue

def catalogue_rows(runner, calibration, tape, step_index, base, run_setting, eval_batch=None):
    """Exact bounded-union-v2 catalogue rebuilt around BASE without scalar evaluate."""
    options, census = runner._selection_shortlist(tape, step_index, run_setting=run_setting)
    users = tuple(sorted(base.mapping))
    base_map = base.mapping
    unilaterals = {u: [] for u in users}
    rows = [base]
    for u in users:
        for identity in options[u]:
            if identity == base_map[u]:
                continue
            mapping = dict(base_map)
            mapping[u] = identity
            row = runner._configuration(base, mapping, kind="unilateral")
            rows.append(row)
            unilaterals[u].append(row)
    nominal = fresh_evaluator(runner, tape, step_index, base, run_setting, "nominal", (0,))
    first = dedupe((base, *rows[1:]))
    nominal.evaluate_many(first)
    base_p = cached(nominal, base)
    best_surplus = {}
    for u in users:
        values = []
        for row in unilaterals[u]:
            p = cached(nominal, row)
            core = Fraction(str(p.bits - base_p.bits)) - calibration.eta_ref * Fraction(str(p.joules - base_p.joules))
            core += calibration.kappa_bits_per_user_step * runner._phi_for(base, row)
            values.append(core)
        best_surplus[u] = max(values, default=Fraction(-10**30))
    ranked = sorted(users, key=lambda u: (-best_surplus[u], u))[:runner.PAIRWISE_TOP_K_USERS]
    for rank in range(runner.TOP_PROPOSALS):
        mapping = dict(base_map)
        for u in users:
            if len(unilaterals[u]) > rank:
                mapping[u] = unilaterals[u][rank].mapping[u]
        if mapping != base_map:
            rows.append(runner._configuration(base, mapping, kind="s0-top-two"))
    for a, b in itertools.combinations(ranked, 2):
        for ra in unilaterals[a][:runner.TOP_PROPOSALS]:
            for rb in unilaterals[b][:runner.TOP_PROPOSALS]:
                mapping = dict(base_map)
                mapping[a] = ra.mapping[a]
                mapping[b] = rb.mapping[b]
                rows.append(runner._configuration(base, mapping, kind="pairwise-top10-top2"))
    for beam in sorted({i for i in base_map.values() if i is not None}):
        mapping = dict(base_map)
        for u in users:
            if base_map[u] == beam:
                mapping[u] = next((i for i in options[u] if i != beam), None)
        if mapping != base_map:
            rows.append(runner._configuration(base, mapping, kind="beam-evacuation"))
    unique = dedupe(rows)
    if len(unique) > runner.CATALOGUE_CAP:
        raise RuntimeError("catalogue exceeded sealed cap")
    info = {"count": len(unique), "top10_users": ranked,
            "nominal_boundary_evaluations": nominal.physical_evaluations,
            "shortlist_census": {k: v for k, v in census.items() if isinstance(v, (int, float, str)) or v is None}}
    del nominal
    gc.collect()
    return unique, info


# ---------------------------------------------------------------- common setup

def setup():
    check_runtime()
    panel = load_module("triobj_panel", PANEL_RUNNER)
    crowd = load_module("triobj_crowd", CROWD_RUNNER)
    clean = json.loads(CLEAN_RECEIPT.read_text(encoding="utf-8"))
    frozen = clean.get("panel", [])
    if clean.get("status") != "COMPLETE" or len(frozen) != 12:
        raise RuntimeError("frozen 12-anchor development panel unavailable")
    pilot = panel.load_pilot()
    runner = pilot.ENGINE
    calibration = panel.load_calibration(pilot)
    run_setting = runner.run_setting_for("a-r0")
    forbid_scalar_evaluate(runner)
    from mcrl.physics_v025 import constants_v025 as C
    from mcrl.physics_v025.channel import noise_power_w
    assert C.SAME_SATELLITE_INTERRUPTION_S == H_BEAM_S and C.SATELLITE_CHANGE_INTERRUPTION_S == H_SAT_S
    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape
    if pilot.TRAIN_WORLDS[0] != "V025_PROBE/world/1":
        raise RuntimeError(f"unexpected development world {pilot.TRAIN_WORLDS[0]}")
    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB before tape", flush=True)
    tape = build_world_tape(domain=pilot.TRAIN_WORLDS[0], provider=LegacyWorldProvider(role="pilot-source"),
                            steps=33, start_time_s=0.0)
    check_runtime()
    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB after tape", flush=True)
    return panel, crowd, frozen, pilot, runner, calibration, run_setting, tape, C, noise_power_w


def step_anchors(runner, tape, frozen, step_index):
    rows = [r for r in frozen if int(r["step_index"]) == step_index]
    if len(rows) != 3:
        raise RuntimeError("step lacks three frozen carriers")
    out = []
    for r in sorted(rows, key=lambda r: int(r["global_anchor_index"])):
        carrier = str(r["carrier"])
        out.append({
            "global_anchor_index": int(r["global_anchor_index"]),
            "anchor_id": f"{r['world_id']}|{step_index}|{carrier}",
            "carrier": carrier,
            "base": runner._base_configuration(tape, step_index, carrier),
            "incumbent": runner._base_configuration(tape, max(0, step_index - 1), carrier),
        })
    return out


def parity_set(runner, crowd, tape, step_index, anchors, links):
    rep = anchors[0]["base"]
    rss = runner._configuration(rep, rss_mapping(links), kind="triobj-rss-max")
    cover = crowd.minimum_cover(links.options)
    crowded = runner._configuration(rep, crowd.assignment_for_beams(links.options, cover), kind="triobj-crowded")
    return rss, crowded, cover


def parity_mode() -> int:
    started = time.perf_counter()
    panel, crowd, frozen, pilot, runner, calibration, run_setting, tape, C, noise_fn = setup()
    steps = []
    totals = {"RSS_MAX": [0.0, 0.0, 0, 0], "CROWDED": [0.0, 0.0, 0, 0], "BASE": [0.0, 0.0, 0, 0]}
    for step_index in range(4):
        anchors = step_anchors(runner, tape, frozen, step_index)
        links = StepLinks(runner, tape, step_index, noise_fn, C.BEAM_RF_CAP_W, C.SINR_MIN_DB)
        rss, crowded, cover = parity_set(runner, crowd, tape, step_index, anchors, links)
        ev = fresh_evaluator(runner, tape, step_index, anchors[0]["incumbent"], run_setting, "realised", tuple(range(48)))
        call = dedupe(tuple(a["base"] for a in anchors) + (rss, crowded))
        ev.evaluate_many(call)
        rec = {"step_index": step_index, "configs": {}}
        for name, cfg in [("RSS_MAX", rss), ("CROWDED", crowded)] + [(f"BASE:{a['carrier']}", a["base"]) for a in anchors]:
            rec["configs"][name] = {"configuration_id_sha256": hashlib.sha256(cfg.configuration_id.encode()).hexdigest(),
                                    **endpoint_metrics(cached(ev, cfg))}
        for a in anchors:
            for name, cfg in (("RSS_MAX", rss), ("CROWDED", crowded), ("BASE", a["base"])):
                m = endpoint_metrics(cached(ev, cfg))
                t = totals[name]
                t[0] += m["bits"]; t[1] += m["joules"]; t[2] += m["served"]; t[3] += 100
        steps.append(rec)
        del ev
        gc.collect()
        check_runtime()
        print(f"parity step {step_index+1}/4 (anchors {3*step_index+1}-{3*step_index+3}/12) peak RSS {peak_rss_bytes()/2**30:.3f} GiB", flush=True)
    pooled = {k: {"bits": v[0], "joules": v[1], "ee_mbit_per_j": v[0] / v[1] / 1e6, "served": v[2], "users": v[3]}
              for k, v in totals.items()}
    status = "PASS"
    for name, expected in EXPECTED.items():
        if round(pooled[name]["ee_mbit_per_j"], 6) != round(expected, 6) or pooled[name]["served"] != pooled[name]["users"]:
            status = "STOP"
    payload = {"schema": "mcrl-v025-triobj-parity-v1", "status": status, "pooled": pooled, "steps": steps,
               "expected": EXPECTED, "scalar_evaluate_calls": SCALAR_CALLS,
               "peak_rss_bytes": peak_rss_bytes(), "wall_seconds": time.perf_counter() - started,
               "runner_sha256": sha256(Path(__file__))}
    write_json(OUTDIR / "parity-receipt.json", payload)
    print(f"PARITY {status} " + json.dumps(pooled, sort_keys=True), flush=True)
    assert SCALAR_CALLS == 0
    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB final ({peak_rss_bytes()} bytes); scalar_evaluate_calls={SCALAR_CALLS}", flush=True)
    return 0 if status == "PASS" else 2


# ---------------------------------------------------------------- shard

def shard_mode(steps, dry: bool) -> int:
    started = time.perf_counter()
    parity = json.loads((OUTDIR / "parity-receipt.json").read_text(encoding="utf-8"))
    if parity.get("status") != "PASS":
        raise RuntimeError("STOP: parity receipt is not PASS")
    panel, crowd, frozen, pilot, runner, calibration, run_setting, tape, C, noise_fn = setup()
    tag = "dry" if dry else "shard"
    rows_path = OUTDIR / f"{tag}-rows-steps{''.join(map(str, steps))}.jsonl"
    meta_path = OUTDIR / f"{tag}-meta-steps{''.join(map(str, steps))}.json"
    meta = {"schema": "mcrl-v025-triobj-shard-v1", "status": "RUNNING", "steps": steps, "dry": dry,
            "definitions_sha256": hashlib.sha256(json.dumps(DEFINITIONS, sort_keys=True).encode()).hexdigest(),
            "eta_ref": [calibration.eta_ref.numerator, calibration.eta_ref.denominator],
            "kappa": [calibration.kappa_bits_per_user_step.numerator, calibration.kappa_bits_per_user_step.denominator],
            "anchors": []}
    kappa = float(calibration.kappa_bits_per_user_step)
    done = 0
    with rows_path.open("w", encoding="utf-8") as handle:
        for step_index in steps:
            t0 = time.perf_counter()
            anchors = step_anchors(runner, tape, frozen, step_index)
            links = StepLinks(runner, tape, step_index, noise_fn, C.BEAM_RF_CAP_W, C.SINR_MIN_DB)
            next_links = StepLinks(runner, tape, step_index + 1, noise_fn, C.BEAM_RF_CAP_W, C.SINR_MIN_DB)
            rss, crowded, cover = parity_set(runner, crowd, tape, step_index, anchors, links)
            rep = anchors[0]["base"]
            rss_map = rss.mapping
            crowd_map = crowded.mapping
            # carrier-invariant families
            inv = {}                                    # configuration_id -> (config, set(tags))

            def add_inv(mapping, tagname):
                cfg = runner._configuration(rep, mapping, kind="triobj")
                entry = inv.setdefault(cfg.configuration_id, [cfg, set()])
                entry[1].add(tagname)
            add_inv(rss_map, "RSS_MAX")
            add_inv(crowd_map, "CROWDED")
            beam_sets = crowd.nested_beam_sets(links.options)
            for k, beams in enumerate(beam_sets):
                add_inv(crowd.assignment_for_beams(links.options, beams), f"CROWD_FAMILY_{k:02d}")
            drop = drop_family(links, rss_map)
            for k, m in enumerate(drop):
                add_inv(m, f"DROP_{k:03d}")
            add = add_family(links, cover)
            for k, m in enumerate(add):
                add_inv(m, f"ADD_{k:03d}")
            if add[-1] != rss_map:
                raise RuntimeError("greedy add family did not terminate at RSS_MAX")
            add_inv(add[0], "MINCOVER_LQ")
            add_inv(surv_mapping(links, next_links), "SURV_LQ")
            if dry:
                keep = {cid: v for cid, v in inv.items() if v[1] & {"RSS_MAX", "CROWDED", "MINCOVER_LQ", "SURV_LQ", "DROP_001", "ADD_001"}}
                inv = keep
            # carrier-specific pools
            per_anchor = []
            for a in anchors:
                cat, cat_info = catalogue_rows(runner, calibration, tape, step_index, a["base"], run_setting)
                if dry:
                    cat = cat[:12]
                fams, fam_info = persistence_families(links, a["incumbent"].mapping, rss_map, crowd_map, cover)
                pool = {}
                for cfg in cat:
                    entry = pool.setdefault(cfg.configuration_id, [cfg, set()])
                    entry[1].add("BASE" if cfg.configuration_id == a["base"].configuration_id else "CATALOGUE")
                for cid, (cfg, tags) in inv.items():
                    entry = pool.setdefault(cid, [cfg, set()])
                    entry[1].update(tags)
                for name, m in fams.items():
                    cfg = runner._configuration(a["base"], m, kind="triobj-persistence")
                    entry = pool.setdefault(cfg.configuration_id, [cfg, set()])
                    entry[1].add(name)
                per_anchor.append({"anchor": a, "pool": pool, "catalogue_info": cat_info, "family_info": fam_info})
            # endpoint evaluator: call 1 parity set, call 2 everything else
            endpoint = fresh_evaluator(runner, tape, step_index, anchors[0]["incumbent"], run_setting, "realised", tuple(range(48)))
            call1 = dedupe(tuple(a["base"] for a in anchors) + (rss, crowded))
            endpoint.evaluate_many(call1)
            prec = next(s for s in parity["steps"] if s["step_index"] == step_index)["configs"]
            for name, cfg in [("RSS_MAX", rss), ("CROWDED", crowded)] + [(f"BASE:{a['carrier']}", a["base"]) for a in anchors]:
                m = endpoint_metrics(cached(endpoint, cfg))
                ref = prec[name]
                if m["bits"] != ref["bits"] or m["joules"] != ref["joules"] or m["served"] != ref["served"]:
                    raise RuntimeError(f"STOP: step {step_index} {name} endpoint differs from parity receipt")
            remaining = dedupe(tuple(cfg for pa in per_anchor for cfg, _ in pa["pool"].values()))
            remaining = tuple(cfg for cfg in remaining if cfg.configuration_id not in endpoint._evaluated)
            print(f"step {step_index}: endpoint batch of {len(remaining)} mappings (+{len(call1)} parity)", flush=True)
            endpoint.evaluate_many(remaining)
            f48 = {}
            for cfg in (*call1, *remaining):
                if cfg.configuration_id in endpoint._invalid:
                    continue
                f48[cfg.configuration_id] = endpoint_metrics(cached(endpoint, cfg))
            invalid48 = len(endpoint._invalid)
            endpoint_evals = endpoint.physical_evaluations
            del endpoint
            gc.collect()
            check_runtime()
            print(f"step {step_index}: endpoint done in {time.perf_counter()-t0:.1f}s invalid={invalid48} peak RSS {peak_rss_bytes()/2**30:.3f} GiB", flush=True)
            for pa in per_anchor:
                a = pa["anchor"]
                base = a["base"]
                pool = pa["pool"]
                ordered = [base] + sorted((cfg for cid, (cfg, _) in pool.items() if cid != base.configuration_id),
                                          key=lambda c: c.configuration_id)
                sel = fresh_evaluator(runner, tape, step_index, a["incumbent"], run_setting, "realised", (0,))
                sel.evaluate_many(tuple(ordered))           # ONE call: BASE + every candidate
                rekeys = runner._rekeyed_users(tape, step_index)
                base_map = base.mapping
                n_rows = 0
                for cfg in ordered:
                    cid = cfg.configuration_id
                    if cid in sel._invalid or cid not in f48:
                        continue
                    p0 = cached(sel, cfg)
                    mapping = cfg.mapping
                    events = runner._physical_events(a["incumbent"], cfg, cell_rekeyed_users=rekeys)
                    kinds = Counter(e.kind for e in events)
                    removed = 0.0
                    for e in events:
                        if e.kind in ("beam_change", "cell_rekey"):
                            removed += float(p0.score.bits[e.user_id]) / DECISION_INTERVAL_S * H_BEAM_S
                        elif e.kind == "satellite_change":
                            removed += float(p0.score.bits[e.user_id]) / DECISION_INTERVAL_S * H_SAT_S
                    phi = runner._phi_for(a["incumbent"], cfg, cell_rekeyed_users=rekeys)
                    nxt = next_links.options
                    row = {
                        "anchor_index": a["global_anchor_index"], "anchor_id": a["anchor_id"],
                        "step_index": step_index, "carrier": a["carrier"],
                        "configuration_id_sha256": hashlib.sha256(cid.encode()).hexdigest(),
                        "tags": sorted(pool[cid][1]),
                        "changed_vs_base": sum(base_map[u] != mapping[u] for u in mapping),
                        "null_users": sum(mapping[u] is None for u in mapping),
                        "LQ": links.lq(mapping),
                        "beams": beams_of(mapping),
                        "P": float(phi),
                        "S": sum(1 for u, b in mapping.items() if b is not None and b in set(nxt.get(u, ()))),
                        "events": dict(kinds),
                        "phi_cost_bits": -kappa * float(phi),
                        "b0": {"bits": float(p0.bits), "joules": float(p0.joules), "served": served(p0)},
                        "f48": f48[cid],
                        "h_removed_bits_derived": removed,
                    }
                    handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
                    n_rows += 1
                sel_evals = sel.physical_evaluations
                invalid0 = len(sel._invalid)
                del sel
                gc.collect()
                done += 1
                meta["anchors"].append({
                    "anchor_index": a["global_anchor_index"], "anchor_id": a["anchor_id"],
                    "pool_size": len(pool), "rows_written": n_rows,
                    "catalogue": pa["catalogue_info"], "families": pa["family_info"],
                    "tag_counts": dict(Counter(t.split("_")[0] if t.startswith(("DROP", "ADD", "CROWD_FAMILY")) else t
                                               for _, tags in pool.values() for t in tags)),
                    "drop_family_len": len(drop), "add_family_len": len(add),
                    "cover_size": len(cover), "invalid_selection": invalid0, "invalid_endpoint_step": invalid48,
                    "selection_boundary_evaluations": sel_evals, "endpoint_boundary_evaluations_step": endpoint_evals,
                })
                meta["peak_rss_bytes"] = peak_rss_bytes()
                write_json(meta_path, meta)
                check_runtime()
                print(f"anchor {a['global_anchor_index']+1}/12 (shard {done}/{3*len(steps)}) {a['anchor_id']} rows={n_rows} "
                      f"elapsed={time.perf_counter()-started:.1f}s peak RSS {peak_rss_bytes()/2**30:.3f} GiB", flush=True)
            del per_anchor, f48, inv
            gc.collect()
    assert SCALAR_CALLS == 0
    meta.update({"status": "COMPLETE", "scalar_evaluate_calls": SCALAR_CALLS,
                 "scalar_evaluate_assertion": "PASS: raising stub installed; zero calls",
                 "rows_sha256": sha256(rows_path), "peak_rss_bytes": peak_rss_bytes(),
                 "wall_seconds": time.perf_counter() - started, "runner_sha256": sha256(Path(__file__)),
                 "python": sys.executable, "niceness": os.getpriority(os.PRIO_PROCESS, 0),
                 "thread_pins": {n: os.environ[n] for n in THREAD_VARS}})
    write_json(meta_path, meta)
    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB final ({peak_rss_bytes()} bytes); scalar_evaluate_calls={SCALAR_CALLS}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("definitions", "parity", "shard", "dry"))
    parser.add_argument("--steps", default="0,1,2,3")
    args = parser.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if args.mode == "definitions":
        (WORKSPACE / "triobj-definitions.json").write_text(json.dumps(DEFINITIONS, sort_keys=True, indent=1) + "\n")
        return 0
    if args.mode == "parity":
        return parity_mode()
    steps = [int(s) for s in args.steps.split(",")]
    return shard_mode(steps, dry=(args.mode == "dry"))


if __name__ == "__main__":
    raise SystemExit(main())
