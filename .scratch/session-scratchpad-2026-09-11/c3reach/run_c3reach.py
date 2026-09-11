#!/usr/bin/env python3
"""C3REACH: does per-user realised-EE climbing reach the crowded joint optimum?

DESIGN-PHASE DIAGNOSTIC, NOT A CLAIM.  Learner-free: no learner module or
checkpoint is imported or read.  Only the frozen 12-anchor development panel
(world 1, steps 0-3, three carriers) is touched; no evaluation-only claim date.

Scoring surface (every comparison): realised field, all 48 within-step
boundaries, dense ``a-r0`` path (``StepEvaluator.evaluate_many``).  For every
scoring round at a unit, ONE fresh StepEvaluator is built and the incumbent
enters its FIRST ``evaluate_many`` call together with candidates; candidate
values are read only from that evaluator's ``_evaluated`` store.  Scalar
``StepEvaluator.evaluate`` is replaced class-wide by a raising stub.

Objective: pooled panel EE = sum(bits)/sum(joules) over the 12 anchors.  A
"unit" is one distinct (physical step, mapping) pair with integer weight equal
to the number of carrier anchors carrying that mapping (dense full-48 physics
depends on step and mapping only).  A candidate at unit u with deltas (dB, dE)
improves pooled EE iff w_u*(dB - lam*dE) > TOL_REL*B_tot, lam = B_tot/E_tot.
Service guard: served at the unit must not fall below the unit incumbent's
served count (monotone, hence never below the starting profile's).
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import random
import resource
import sys
import time

WORKSPACE = Path("/home/sat/mcrl-v025-c3reach-ws")
OUT = WORKSPACE / ".scratch/c3reach"
PANEL_RUNNER = Path("/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/run_panelceil.py")
CROWD_RUNNER = Path("/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run_crowding_cost.py")
COORD_RUNNER = Path("/home/sat/mcrl-v025-coord-ws/.scratch/coordvalue/run_coordvalue.py")
PYTHON = "/home/sat/mcrl-leo-handover/.venv/bin/python"
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")
MAX_RSS_BYTES = 5_000_000_000
EVAL_BATCH = 32
TOL_REL = 1e-12
BOUNDARIES = tuple(range(48))
EXPECTED = {"RSS_MAX": 41.621560, "CROWDED": 46.110374, "BASE": 11.027760}
K_ESCAPE = (2, 3, 4, 6, 8)
SCALAR_CALLS = 0


def peak_rss() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def check_runtime() -> None:
    if sys.executable != PYTHON:
        raise RuntimeError(f"wrong interpreter {sys.executable}")
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        raise RuntimeError("niceness below 15")
    bad = {n: os.environ.get(n) for n in THREAD_VARS if os.environ.get(n) != "1"}
    if bad:
        raise RuntimeError(f"thread pins not 1: {bad}")
    if peak_rss() >= MAX_RSS_BYTES:
        raise MemoryError(f"peak RSS {peak_rss()} >= 5 GB")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, payload) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=1, allow_nan=False) + "\n")
    tmp.replace(path)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg} | peak RSS {peak_rss()/2**30:.3f} GiB", flush=True)


class World:
    """Tape, runner, legal options and the three reference profiles per step."""

    def __init__(self):
        check_runtime()
        self.panel = load("c3reach_panel", PANEL_RUNNER)
        self.crowd = load("c3reach_crowd", CROWD_RUNNER)
        self.coord = load("c3reach_coord", COORD_RUNNER)
        self.pilot = self.panel.load_pilot()
        self.runner = self.pilot.ENGINE
        self.run_setting = self.runner.run_setting_for("a-r0")
        original = self.runner.StepEvaluator.evaluate

        def forbidden(*args, **kwargs):
            global SCALAR_CALLS
            SCALAR_CALLS += 1
            raise AssertionError("scalar StepEvaluator.evaluate is forbidden on C3REACH surfaces")

        forbidden.__wrapped__ = original
        self.runner.StepEvaluator.evaluate = forbidden
        assert self.runner.StepEvaluator.evaluate is forbidden
        from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
        from mcrl.physics_v025.tapes import build_world_tape
        log("building tape")
        self.tape = build_world_tape(
            domain=self.pilot.TRAIN_WORLDS[0], provider=LegacyWorldProvider(role="pilot-source"),
            steps=33, start_time_s=0.0,
        )
        check_runtime()
        log("tape built")
        self.carriers = tuple(self.panel.CARRIERS)
        self.steps = {}
        cache = {}
        for step in range(4):
            options, _ = self.runner._legal_options(self.tape, step)
            bases = {c: self.runner._base_configuration(self.tape, step, c) for c in self.carriers}
            rep = bases[self.carriers[0]]
            rss = self.coord.rss_configuration(self.runner, self.tape, step, rep)
            crowded = self.coord.crowded_configuration(self.runner, self.crowd, rep, options, cache, step)
            self.steps[step] = {"options": options, "bases": bases, "rep": rep,
                                "RSS_MAX": rss, "CROWDED": crowded}

    def config(self, step, mapping, kind):
        return self.runner._configuration(self.steps[step]["rep"], mapping, kind=kind)

    def fresh(self, step, incumbent):
        ev = self.runner.StepEvaluator(
            self.tape, self.runner._setting("a-r0"), step,
            transition_from=incumbent,
            cell_rekeyed_users=self.runner._rekeyed_users(self.tape, step),
            field="realised", counter=self.runner.EvaluationCounter(),
            run_setting=self.run_setting, boundary_indices=BOUNDARIES,
        )
        assert ev.boundary_indices == BOUNDARIES and ev.field == "realised"
        if self.tape.steps[step].arrays is None:
            raise AssertionError("dense arrays required")
        return ev

    def summarize(self, p):
        attained = p.score.rate_target_attained
        if attained is None:
            raise RuntimeError("profile omitted rate-target attainment")
        return {
            "bits": float(p.bits), "joules": float(p.joules),
            "served": sum(bool(v) for v in p.score.served_phy.values()),
            "attained": sum(bool(v) for v in attained.values()),
            "users": len(attained),
        }

    def score(self, step, incumbent, candidates):
        """One fresh evaluator: incumbent in the first evaluate_many call.

        Returns (incumbent_summary, list of summaries-or-None aligned to candidates).
        """
        ev = self.fresh(step, incumbent)
        inc_id = incumbent.configuration_id
        first = [incumbent] + [c for c in candidates[:EVAL_BATCH - 1] if c.configuration_id != inc_id]
        ev.evaluate_many(tuple(first))
        inc_p = ev._evaluated.get(inc_id)
        if inc_p is None:
            raise RuntimeError("incumbent invalid in fresh evaluator")
        inc = self.summarize(inc_p)
        out = []
        pending = list(candidates[EVAL_BATCH - 1:])

        def harvest(batch):
            for c in batch:
                p = ev._evaluated.pop(c.configuration_id, None) if c.configuration_id != inc_id else None
                out.append(None if p is None else self.summarize(p))

        harvest(candidates[:EVAL_BATCH - 1])
        for off in range(0, len(pending), EVAL_BATCH):
            batch = pending[off:off + EVAL_BATCH]
            ev.evaluate_many(tuple(c for c in batch if c.configuration_id != inc_id))
            harvest(batch)
        physical = ev.physical_evaluations
        del ev
        gc.collect()
        return inc, out, physical


def active_beams(mapping) -> int:
    return len({identity for identity in mapping.values() if identity is not None})


def max_occupancy(mapping) -> int:
    counts = Counter(identity for identity in mapping.values() if identity is not None)
    return max(counts.values(), default=0)


def singles_for(options, mapping, users=None):
    """Declared order: ascending user; legal options in declared (slant) order; NULL last."""
    rows = []
    for user in (sorted(mapping) if users is None else users):
        alternatives = [identity for identity in options[user] if identity != mapping[user]]
        if mapping[user] is not None:
            alternatives.append(None)
        for identity in alternatives:
            rows.append((user, identity))
    return rows


def enc(identity):
    return None if identity is None else [int(identity[0]), int(identity[1])]


def dec(value):
    return None if value is None else (int(value[0]), int(value[1]))


class Climb:
    def __init__(self, world: World, start: str, algo: str, tag: str, max_moves: int, wall_cap: float,
                 carriers=None, dry_cands=0):
        self.dry_cands = dry_cands
        self.w = world
        self.start = start
        self.algo = algo
        self.tag = tag
        self.max_moves = max_moves
        self.wall_cap = wall_cap
        self.state_path = OUT / f"{tag}-state.json"
        self.traj_path = OUT / f"{tag}-trajectory.jsonl"
        # Units: distinct (step, mapping) with carrier multiplicity weights.
        self.units = []
        for step in range(4):
            info = world.steps[step]
            if start == "RSS_MAX":
                groups = {info["RSS_MAX"].configuration_id: (info["RSS_MAX"], list(world.carriers))}
            elif start == "CROWDED":
                groups = {info["CROWDED"].configuration_id: (info["CROWDED"], list(world.carriers))}
            else:
                groups = {}
                for carrier in (carriers or world.carriers):
                    cfg = info["bases"][carrier]
                    key = json.dumps(sorted((u, enc(i)) for u, i in cfg.mapping.items()))
                    groups.setdefault(key, (cfg, []))[1].append(carrier)
            for cfg, carriers in groups.values():
                self.units.append({
                    "step": step, "weight": len(carriers), "carriers": carriers,
                    "mapping": dict(cfg.mapping), "config": cfg,
                    "start_config_id": cfg.configuration_id,
                })
        self.moves = []

    # ------------------------------------------------------------------
    def unit_config(self, u, mapping=None):
        unit = self.units[u]
        return self.w.config(unit["step"], unit["mapping"] if mapping is None else mapping,
                             kind=f"c3reach-{self.tag}")

    def totals(self):
        b = math.fsum(unit["weight"] * unit["inc"]["bits"] for unit in self.units)
        e = math.fsum(unit["weight"] * unit["inc"]["joules"] for unit in self.units)
        served = sum(unit["weight"] * unit["inc"]["served"] for unit in self.units)
        attained = sum(unit["weight"] * unit["inc"]["attained"] for unit in self.units)
        users = sum(unit["weight"] * unit["inc"]["users"] for unit in self.units)
        return b, e, served, attained, users

    def pooled_row(self):
        b, e, served, attained, users = self.totals()
        anchors = sum(unit["weight"] for unit in self.units)
        return {
            "pooled_bits": b, "pooled_joules": e, "pooled_ee_mbit_per_j": b / e / 1e6,
            "served": served, "rate_target_attained": attained, "users": users,
            "mean_active_beams": sum(unit["weight"] * active_beams(unit["mapping"]) for unit in self.units) / anchors,
            "active_beams_by_unit": [active_beams(unit["mapping"]) for unit in self.units],
            "max_occupancy_by_unit": [max_occupancy(unit["mapping"]) for unit in self.units],
        }

    def rescore_unit(self, u):
        """Fresh evaluator: incumbent + all singles for unit u."""
        unit = self.units[u]
        options = self.w.steps[unit["step"]]["options"]
        edits = singles_for(options, unit["mapping"])
        if self.dry_cands:
            edits = edits[:self.dry_cands]
        configs = []
        for user, identity in edits:
            mapping = dict(unit["mapping"])
            mapping[user] = identity
            configs.append(self.unit_config(u, mapping))
        t0 = time.perf_counter()
        inc, rows, physical = self.w.score(unit["step"], unit["config"], configs)
        unit["inc"] = inc
        unit["table"] = [(user, identity, row) for (user, identity), row in zip(edits, rows)]
        unit["table_seconds"] = time.perf_counter() - t0
        unit["table_physical"] = physical
        return time.perf_counter() - t0

    def gain(self, unit, row, b_tot, e_tot):
        lam = b_tot / e_tot
        db = row["bits"] - unit["inc"]["bits"]
        de = row["joules"] - unit["inc"]["joules"]
        g = unit["weight"] * (db - lam * de)
        new_ee = (b_tot + unit["weight"] * db) / (e_tot + unit["weight"] * de)
        return g, new_ee, db, de

    def apply(self, u, user, identity, row, meta):
        unit = self.units[u]
        before = unit["mapping"][user]
        unit["mapping"][user] = identity
        unit["config"] = self.unit_config(u)
        unit["inc_candidate_values"] = row  # values from the evaluator that selected it
        self.moves.append({"unit": u, "user": user, "from": enc(before), "to": enc(identity), **meta})

    def save_state(self, status, extra=None):
        payload = {
            "tag": self.tag, "start": self.start, "algo": self.algo, "status": status,
            "units": [{
                "step": unit["step"], "weight": unit["weight"], "carriers": unit["carriers"],
                "start_config_id": unit["start_config_id"],
                "mapping": [[user, enc(identity)] for user, identity in sorted(unit["mapping"].items())],
                "inc": unit.get("inc"),
            } for unit in self.units],
            "moves": self.moves, "peak_rss_bytes": peak_rss(),
            "scalar_evaluate_calls": SCALAR_CALLS,
        }
        if extra:
            payload.update(extra)
        atomic_json(self.state_path, payload)

    def resume(self):
        if not self.state_path.exists():
            return 0
        payload = json.loads(self.state_path.read_text())
        for move in payload["moves"]:
            unit = self.units[move["unit"]]
            assert unit["mapping"][move["user"]] == dec(move["from"]), "resume replay mismatch"
            unit["mapping"][move["user"]] = dec(move["to"])
        for u, unit in enumerate(self.units):
            if unit["mapping"] != dict(unit["config"].mapping):
                unit["config"] = self.unit_config(u)
        self.moves = payload["moves"]
        log(f"{self.tag}: resumed after {len(self.moves)} moves")
        return len(self.moves)

    def traj(self, row):
        with self.traj_path.open("a") as f:
            f.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")

    # ------------------------------------------------------------------
    def run_best(self):
        started = time.perf_counter()
        self.resume()
        for u in range(len(self.units)):
            sec = self.rescore_unit(u)
            log(f"{self.tag}: initial table unit {u+1}/{len(self.units)} (anchor {sum(x['weight'] for x in self.units[:u+1])}/{sum(x['weight'] for x in self.units)}) step={self.units[u]['step']} "
                f"cands={len(self.units[u]['table'])} {sec:.1f}s")
        row0 = self.pooled_row()
        if not self.moves:
            self.traj({"move": 0, "wall_s": 0.0, **row0})
        log(f"{self.tag}: start pooled EE {row0['pooled_ee_mbit_per_j']:.6f} served {row0['served']}")
        certificate = None
        while True:
            b_tot, e_tot, *_ = self.totals()
            best = None
            improving = 0
            guard_rejected = 0
            invalid = 0
            for u, unit in enumerate(self.units):
                for order, (user, identity, row) in enumerate(unit["table"]):
                    if row is None:
                        invalid += 1
                        continue
                    if row["served"] < unit["inc"]["served"]:
                        guard_rejected += 1
                        continue
                    g, new_ee, db, de = self.gain(unit, row, b_tot, e_tot)
                    if g > TOL_REL * b_tot:
                        improving += 1
                        key = (new_ee, -u, -user, -order)
                        if best is None or key > best[0]:
                            best = (key, u, user, identity, row, g, new_ee, db, de)
            if best is None:
                certificate = {"complete": True, "improving": 0, "guard_rejected": guard_rejected,
                               "invalid": invalid,
                               "candidates": sum(len(unit["table"]) for unit in self.units),
                               "statement": "every legal single-user alternative (plus NULL) at every unit was scored against the current incumbent in that unit's fresh evaluator; none strictly improves guarded pooled EE"}
                break
            if len(self.moves) >= self.max_moves or time.perf_counter() - started > self.wall_cap:
                certificate = {"complete": False, "reason": "move or wall cap", "improving_remaining": improving}
                break
            _, u, user, identity, row, g, new_ee, db, de = best
            it0 = time.perf_counter()
            self.apply(u, user, identity, row, {"predicted_pooled_ee": new_ee, "gain": g,
                                                "d_bits": db, "d_joules": de,
                                                "improving_candidates": improving})
            sec = self.rescore_unit(u)
            cand = self.units[u]["inc_candidate_values"]
            repro = {"bits_diff": self.units[u]["inc"]["bits"] - cand["bits"],
                     "joules_diff": self.units[u]["inc"]["joules"] - cand["joules"]}
            row_now = self.pooled_row()
            self.moves[-1].update({"iteration_seconds": time.perf_counter() - it0, "repro": repro,
                                   "pooled_ee_after": row_now["pooled_ee_mbit_per_j"]})
            self.traj({"move": len(self.moves), "wall_s": time.perf_counter() - started,
                       "iteration_seconds": sec, "unit": u, "user": user, "to": enc(identity),
                       "improving_candidates": improving, "repro": repro, **row_now})
            self.save_state("RUNNING")
            if len(self.moves) % 5 == 0 or len(self.moves) < 5:
                log(f"{self.tag}: move {len(self.moves)} unit {u} user {user} EE {row_now['pooled_ee_mbit_per_j']:.6f} "
                    f"served {row_now['served']} active {row_now['mean_active_beams']:.2f} "
                    f"improving {improving} iter {sec:.1f}s")
            check_runtime()
        return certificate, time.perf_counter() - started

    def run_first(self):
        """Cyclic first-improvement: passes over units (step order), users ascending,
        options in declared legal order then NULL; accept the first guarded strict
        pooled improvement for a user, then continue with the next user."""
        started = time.perf_counter()
        self.resume()
        # establish incumbent values for all units (fresh evaluator, incumbent only + nothing)
        for u, unit in enumerate(self.units):
            inc, _, _ = self.w.score(unit["step"], unit["config"], [])
            unit["inc"] = inc
        row0 = self.pooled_row()
        if not self.moves:
            self.traj({"move": 0, "wall_s": 0.0, "pass": 0, **row0})
        log(f"{self.tag}: start pooled EE {row0['pooled_ee_mbit_per_j']:.6f} served {row0['served']}")
        passes = 0
        certificate = None
        capped = False
        while not capped:
            passes += 1
            pass_moves = 0
            counts = Counter()
            pass_t0 = time.perf_counter()
            for u, unit in enumerate(self.units):
                options = self.w.steps[unit["step"]]["options"]
                for user in sorted(unit["mapping"])[:(3 if self.dry_cands else None)]:
                    edits = singles_for(options, unit["mapping"], users=[user])
                    if not edits:
                        continue
                    if len(self.moves) >= self.max_moves or time.perf_counter() - started > self.wall_cap:
                        capped = True
                        break
                    configs = []
                    for _u, identity in edits:
                        mapping = dict(unit["mapping"])
                        mapping[user] = identity
                        configs.append(self.unit_config(u, mapping))
                    it0 = time.perf_counter()
                    inc, rows, _phys = self.w.score(unit["step"], unit["config"], configs)
                    unit["inc"] = inc
                    b_tot, e_tot, *_ = self.totals()
                    accepted = None
                    for (_u, identity), row in zip(edits, rows):
                        counts["evaluated"] += 1
                        if row is None:
                            counts["invalid"] += 1
                            continue
                        if row["served"] < inc["served"]:
                            counts["guard_rejected"] += 1
                            continue
                        g, new_ee, db, de = self.gain(unit, row, b_tot, e_tot)
                        if g > TOL_REL * b_tot:
                            counts["improving"] += 1
                            accepted = (identity, row, g, new_ee, db, de)
                            break
                    if accepted is None:
                        continue
                    identity, row, g, new_ee, db, de = accepted
                    self.apply(u, user, identity, row, {"predicted_pooled_ee": new_ee, "gain": g,
                                                        "d_bits": db, "d_joules": de, "pass": passes})
                    unit["inc"] = dict(row)  # next visit re-evaluates it in a fresh evaluator
                    pass_moves += 1
                    row_now = self.pooled_row()
                    self.moves[-1]["pooled_ee_after"] = row_now["pooled_ee_mbit_per_j"]
                    self.traj({"move": len(self.moves), "wall_s": time.perf_counter() - started,
                               "iteration_seconds": time.perf_counter() - it0, "pass": passes,
                               "unit": u, "user": user, "to": enc(identity), **row_now})
                    self.save_state("RUNNING", {"passes": passes})
                    if len(self.moves) % 10 == 0:
                        log(f"{self.tag}: move {len(self.moves)} pass {passes} EE {row_now['pooled_ee_mbit_per_j']:.6f} "
                            f"served {row_now['served']} active {row_now['mean_active_beams']:.2f}")
                    check_runtime()
                if capped:
                    break
            log(f"{self.tag}: pass {passes} moves {pass_moves} {time.perf_counter()-pass_t0:.0f}s counts {dict(counts)}")
            if capped:
                certificate = {"complete": False, "reason": "move or wall cap", "passes": passes}
                break
            if pass_moves == 0:
                if counts["improving"]:
                    raise RuntimeError("zero-move pass contains an improvement")
                certificate = {"complete": True, "passes_including_certificate": passes, **dict(counts),
                               "statement": "final pass: every user at every unit had every legal alternative (plus NULL) scored against the unchanged incumbent in a fresh evaluator; none strictly improves guarded pooled EE"}
                break
        # final tables for the escape stage and exact end-point values
        for u in range(len(self.units)):
            self.rescore_unit(u)
        return certificate, time.perf_counter() - started


# ----------------------------------------------------------------------
def escape_candidates(world, climb, u, k, budget, seed):
    """Deterministic sampled k-user edits at unit u (exactly k changed users)."""
    unit = climb.units[u]
    options = world.steps[unit["step"]]["options"]
    start_map = unit["mapping"]
    crowded = world.steps[unit["step"]]["CROWDED"].mapping
    rng = random.Random(seed)
    users = tuple(sorted(start_map))
    out, seen = [], set()
    b_tot, e_tot, *_ = climb.totals()

    def add(mapping, method):
        changed = tuple(x for x in users if mapping[x] != start_map[x])
        if len(changed) != k:
            return False
        key = tuple((x, mapping[x]) for x in changed)
        if key in seen:
            return False
        seen.add(key)
        out.append((dict(mapping), changed, method))
        return True

    # Least-bad guarded single move per user (from the final exhaustive table).
    best_single = {}
    for user, identity, row in unit["table"]:
        if row is None or identity is None or row["served"] < unit["inc"]["served"]:
            continue
        g, *_ = climb.gain(unit, row, b_tot, e_tot)
        if user not in best_single or g > best_single[user][0]:
            best_single[user] = (g, identity)
    occupancy = defaultdict(list)
    for user, identity in start_map.items():
        if identity is not None:
            occupancy[identity].append(user)
    active = set(occupancy)
    # 1. Beam evacuations (close a beam with exactly k occupants).
    for beam, members in sorted(occupancy.items()):
        if len(members) != k or len(out) >= budget // 2:
            continue
        # (a) each occupant to its best-scoring single destination among other active beams
        mapping = dict(start_map)
        ok = True
        for user in members:
            dest = [row for row in unit["table"] if row[0] == user and row[1] in active and row[1] != beam
                    and row[2] is not None]
            if not dest:
                ok = False
                break
            dest.sort(key=lambda r: -climb.gain(unit, r[2], b_tot, e_tot)[0])
            mapping[user] = dest[0][1]
        if ok:
            add(mapping, "beam-evacuation-best-single-destination")
        # (b) every occupant to one common other active beam
        commons = [b for b in sorted(active) if b != beam and all(b in options[x] for x in members)]
        for dest in commons[:4]:
            mapping = dict(start_map)
            for user in members:
                mapping[user] = dest
            add(mapping, "beam-evacuation-common-destination")
    # 2. Top least-bad single combinations.
    ranked = [user for user, _ in sorted(best_single.items(), key=lambda it: (-it[1][0], it[0]))][:24]
    for members in itertools.islice(itertools.combinations(ranked, k), budget // 4):
        if len(out) >= (3 * budget) // 4:
            break
        mapping = dict(start_map)
        for user in members:
            mapping[user] = best_single[user][1]
        add(mapping, "top-single-combination")
    # 3. Subsets moved toward the crowded endpoint.
    target_users = [x for x in users if crowded[x] != start_map[x] and crowded[x] is not None]
    attempts = 0
    while len(out) < (7 * budget) // 8 and len(target_users) >= k and attempts < budget * 20:
        attempts += 1
        mapping = dict(start_map)
        for user in rng.sample(target_users, k):
            mapping[user] = crowded[user]
        add(mapping, "toward-crowded-subset")
    # 4. Common-destination consolidation onto an active beam.
    beam_users = defaultdict(list)
    for x in users:
        for beam in options[x]:
            if beam != start_map[x] and beam in active:
                beam_users[beam].append(x)
    eligible = [b for b, m in sorted(beam_users.items()) if len(m) >= k]
    attempts = 0
    while len(out) < budget and eligible and attempts < budget * 30:
        attempts += 1
        beam = eligible[rng.randrange(len(eligible))]
        mapping = dict(start_map)
        for user in rng.sample(beam_users[beam], k):
            mapping[user] = beam
        add(mapping, "common-destination-consolidation")
    # 5. Uniform legal edits.
    attempts = 0
    while len(out) < budget and attempts < budget * 100:
        attempts += 1
        mapping = dict(start_map)
        possible = True
        for user in rng.sample(users, k):
            alternatives = [i for i in options[user] if i != start_map[user]]
            if not alternatives:
                possible = False
                break
            mapping[user] = alternatives[rng.randrange(len(alternatives))]
        if possible:
            add(mapping, "uniform-legal")
    return out


def run_escape(world, climb, budget):
    b_tot, e_tot, *_ = climb.totals()
    lam = b_tot / e_tot
    result = {"budget_per_unit_per_k": budget, "search": "sampled deterministic mixture (not exhaustive)",
              "units": []}
    for u, unit in enumerate(climb.units):
        cand = []
        for k in K_ESCAPE:
            for mapping, changed, method in escape_candidates(world, climb, u, k, budget,
                                                             20260911 + 1000 * u + k):
                cand.append((k, mapping, changed, method))
        configs = [climb.unit_config(u, m) for _k, m, _c, _m in cand]
        t0 = time.perf_counter()
        inc, rows, _ = world.score(unit["step"], unit["config"], configs)
        # consistency: incumbent must reproduce the climb's final incumbent values
        repro = {"bits_diff": inc["bits"] - unit["inc"]["bits"], "joules_diff": inc["joules"] - unit["inc"]["joules"]}
        unit["inc"] = inc
        b_tot, e_tot, *_ = climb.totals()
        by_k = {}
        for (k, mapping, changed, method), row in zip(cand, rows):
            entry = by_k.setdefault(k, {"k": k, "evaluated": 0, "invalid": 0, "guard_rejected": 0,
                                        "improving": 0, "best": None, "best_any": None,
                                        "methods": Counter()})
            entry["evaluated"] += 1
            entry["methods"][method] += 1
            if row is None:
                entry["invalid"] += 1
                continue
            if row["served"] < inc["served"]:
                entry["guard_rejected"] += 1
                continue
            g, new_ee, db, de = climb.gain(unit, row, b_tot, e_tot)
            rec = {"gain": g, "pooled_ee_if_applied": new_ee,
                   "delta_pooled_ee_mbit_per_j": (new_ee - b_tot / e_tot) / 1e6,
                   "d_bits": db, "d_joules": de, "served": row["served"], "attained": row["attained"],
                   "changed_users": list(changed), "method": method,
                   "edits": [[x, enc(mapping[x])] for x in changed]}
            if entry["best_any"] is None or g > entry["best_any"]["gain"]:
                entry["best_any"] = rec
            if g > TOL_REL * b_tot:
                entry["improving"] += 1
                if entry["best"] is None or g > entry["best"]["gain"]:
                    entry["best"] = rec
        for entry in by_k.values():
            entry["methods"] = dict(entry["methods"])
        smallest = next((k for k in K_ESCAPE if by_k.get(k, {}).get("improving")), None)
        result["units"].append({"unit": u, "step": unit["step"], "weight": unit["weight"],
                                "incumbent_repro": repro, "seconds": time.perf_counter() - t0,
                                "by_k": [by_k[k] for k in K_ESCAPE if k in by_k],
                                "smallest_improving_k": smallest})
        log(f"{climb.tag}: escape unit {u+1}/{len(climb.units)} smallest k {smallest} "
            + " ".join(f"k{k}:{by_k[k]['improving']}/{by_k[k]['evaluated']}" for k in K_ESCAPE if k in by_k))
        check_runtime()
    return result


def parity(world):
    rows = {"RSS_MAX": [], "CROWDED": [], "BASE": []}
    for step in range(4):
        info = world.steps[step]
        configs = list({c.configuration_id: c for c in
                        [info["RSS_MAX"], info["CROWDED"], *info["bases"].values()]}.values())
        ev_inc = info["RSS_MAX"]
        inc, out, _ = world.score(step, ev_inc, [c for c in configs if c.configuration_id != ev_inc.configuration_id])
        vals = {ev_inc.configuration_id: inc}
        for c, r in zip([c for c in configs if c.configuration_id != ev_inc.configuration_id], out):
            vals[c.configuration_id] = r
        for carrier in world.carriers:
            rows["RSS_MAX"].append(vals[info["RSS_MAX"].configuration_id])
            rows["CROWDED"].append(vals[info["CROWDED"].configuration_id])
            rows["BASE"].append(vals[info["bases"][carrier].configuration_id])
        log(f"parity step {step} done (anchors {3*(step+1)}/12)")
    pooled = {}
    for name, rs in rows.items():
        b = math.fsum(r["bits"] for r in rs)
        e = math.fsum(r["joules"] for r in rs)
        pooled[name] = {"bits": b, "joules": e, "ee_mbit_per_j": b / e / 1e6,
                        "served": sum(r["served"] for r in rs), "attained": sum(r["attained"] for r in rs),
                        "users": sum(r["users"] for r in rs),
                        "mean_active_beams": None}
    for name in ("RSS_MAX", "CROWDED"):
        pooled[name]["mean_active_beams"] = sum(active_beams(world.steps[s][name].mapping) for s in range(4)) / 4
    pooled["BASE"]["mean_active_beams"] = sum(active_beams(world.steps[s]["bases"][c].mapping)
                                              for s in range(4) for c in world.carriers) / 12
    for name, expected in EXPECTED.items():
        if round(pooled[name]["ee_mbit_per_j"], 6) != round(expected, 6):
            raise RuntimeError(f"STOP parity {name}: {pooled[name]['ee_mbit_per_j']} vs {expected}")
    return pooled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", choices=("RSS_MAX", "BASE", "CROWDED"), required=True)
    ap.add_argument("--algo", choices=("best", "first"), required=True)
    ap.add_argument("--max-moves", type=int, default=400)
    ap.add_argument("--wall-cap", type=float, default=30 * 3600)
    ap.add_argument("--escape-budget", type=int, default=192)
    ap.add_argument("--no-escape", action="store_true")
    ap.add_argument("--carriers", default="", help="comma list; BASE start only")
    ap.add_argument("--dry-cands", type=int, default=0)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    tag = args.tag or f"{args.start.lower()}-{args.algo}"
    started = time.perf_counter()
    world = World()
    pooled = parity(world)
    log("PARITY PASS " + json.dumps({k: round(v["ee_mbit_per_j"], 6) for k, v in pooled.items()}))
    carriers = tuple(c for c in args.carriers.split(",") if c) or None
    climb = Climb(world, args.start, args.algo, tag, args.max_moves, args.wall_cap,
                  carriers=carriers, dry_cands=args.dry_cands)
    log(f"{tag}: units {len(climb.units)} weights {[u['weight'] for u in climb.units]}")
    if args.algo == "best":
        certificate, climb_seconds = climb.run_best()
    else:
        certificate, climb_seconds = climb.run_first()
    final = climb.pooled_row()
    climb.save_state("CLIMB_DONE", {"certificate": certificate, "final": final, "parity": pooled})
    log(f"{tag}: CLIMB DONE EE {final['pooled_ee_mbit_per_j']:.6f} served {final['served']} "
        f"attained {final['rate_target_attained']} moves {len(climb.moves)} cert {certificate.get('complete')}")
    escape = None
    if not args.no_escape and certificate.get("complete") and final["pooled_ee_mbit_per_j"] < EXPECTED["CROWDED"]:
        escape = run_escape(world, climb, args.escape_budget)
    assert SCALAR_CALLS == 0
    climb.save_state("COMPLETE", {
        "certificate": certificate, "final": final, "parity": pooled, "escape": escape,
        "climb_seconds": climb_seconds, "wall_seconds": time.perf_counter() - started,
        "scalar_evaluate_assertion": "PASS: raising stub installed; zero calls",
        "driver_sha256": sha256_file(Path(__file__)),
        "config": {"eval_batch": EVAL_BATCH, "tol_rel": TOL_REL, "boundaries": 48, "field": "realised",
                   "setting": "a-r0", "max_moves": args.max_moves, "wall_cap_s": args.wall_cap,
                   "escape_budget": args.escape_budget, "carriers": list(carriers or world.carriers),
                   "dry_cands": args.dry_cands},
        "runtime": {"python": sys.executable, "niceness": os.getpriority(os.PRIO_PROCESS, 0),
                    "threads": {n: os.environ.get(n) for n in THREAD_VARS}},
    })
    log(f"{tag}: COMPLETE scalar calls {SCALAR_CALLS} peak RSS bytes {peak_rss()}")


if __name__ == "__main__":
    main()
