#!/usr/bin/env python3
"""BEAMCOUNT: price a cap on the NUMBER OF ACTIVE BEAMS on the 12-anchor
frozen V0.25 development panel.

DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM.  Reads sealed trees read-only; writes
only inside /home/sat/mcrl-v025-beamcount-ws.

Evaluator discipline
--------------------
* Selection: one fresh dense StepEvaluator(boundary_indices=(0,)) per
  (anchor, cap).  BASE enters that evaluator through evaluate_many alongside
  the candidates.  Profiles are read only from StepEvaluator._evaluated.
* Endpoints: one separate fresh realised dense StepEvaluator(range(48)) per
  anchor, populated by exactly one evaluate_many call.
* Scalar StepEvaluator.evaluate is replaced by a raising stub; the call
  counter is asserted zero at completion.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
from typing import Iterable, Mapping, Sequence

import numpy as np

WORKSPACE = Path("/home/sat/mcrl-v025-beamcount-ws")
OUTDIR = WORKSPACE / ".scratch/beamcount"
OUTPUT = OUTDIR / "beamcount-receipt.json"
PARTIAL = OUTDIR / "beamcount-partial.json"

SOURCE_ROOT = Path("/home/sat/mcrl-v025-c1c2suff-ws")
PILOT_PATH = SOURCE_ROOT / "scripts/run_v025_pilot_c3.py"
ENGINE_PATH = SOURCE_ROOT / ".scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"

LEARNED_RUN = Path("/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z")
CORPUS_ROOT = Path(
    "/home/sat/mcrl-v025-coalgen-ws/artifacts/"
    "v025-stagec-c3-coalition-20260910-BUILD_NOT_CLAIM/corpus"
)
TARGET_EPOCH = 500

PYTHON = "/home/sat/mcrl-leo-handover/.venv/bin/python"
THREAD_VARS = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
MAX_RSS_BYTES = 5_000_000_000
CARRIERS = ("nearest-eligible", "stay-if-possible", "random-masked")
DECISION_INTERVAL_S = 30.08

REQUESTED_CAPS = (4, 5, 6, 8, 10, 15, 20, 30, 50)
# The sibling constraint verified on this server is per-satellite
# (k_universe = l_w * k_cap), so its translated form is measured too.
PER_SATELLITE_CAPS = (1, 2, 3)
# Rehearsal knobs.  Defaults are the reported configuration; the rehearsal sets
# them so that every arm and every code path executes at reduced depth.
REHEARSAL = os.environ.get("BEAMCOUNT_REHEARSAL") == "1"
CAPPED_PASSES = int(os.environ.get("BEAMCOUNT_CAPPED_PASSES", "4"))
UNCAPPED_PASSES = int(os.environ.get("BEAMCOUNT_UNCAPPED_PASSES", "3"))
ANCHOR_LIMIT = int(os.environ.get("BEAMCOUNT_ANCHOR_LIMIT", "12"))
SEED_LIMIT = int(os.environ.get("BEAMCOUNT_SEED_LIMIT", "0"))
# MODE: "full" (single process, rehearsal), "sweep" (pass 1 for one carrier
# shard), or "project" (merge the three shards, then pass 2 projections).
MODE = os.environ.get("BEAMCOUNT_MODE", "full")
SHARD_CARRIER = os.environ.get("BEAMCOUNT_CARRIER", "")
if MODE not in ("full", "sweep", "project"):
    raise SystemExit(f"unknown BEAMCOUNT_MODE {MODE}")
PREFIX = "rehearsal-" if REHEARSAL else ""


def shard_path(carrier: str) -> Path:
    return OUTDIR / f"{PREFIX}beamcount-shard-{carrier}.json"


if MODE == "sweep":
    OUTPUT = shard_path(SHARD_CARRIER)
    PARTIAL = OUTDIR / f"{PREFIX}beamcount-shard-{SHARD_CARRIER}-partial.json"
elif REHEARSAL:
    OUTPUT = OUTDIR / f"rehearsal-beamcount-{MODE}-receipt.json"
    PARTIAL = OUTDIR / f"rehearsal-beamcount-{MODE}-partial.json"

# Parity targets (transcribed from the two prior reports).
PARITY_RSS_MAX_MBIT_J = 41.621560
PARITY_CROWDED_BIT_J = 46_110_374.337747

SCALAR_EVALUATE_CALLS = 0


# --------------------------------------------------------------------------
# housekeeping
# --------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(payload: Mapping[str, object]) -> str:
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    return hashlib.sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


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


def atomic_write(path: Path, payload: dict) -> None:
    payload = dict(payload)
    payload["receipt_sha256"] = canonical_digest(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_pilot():
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
    name = "beamcount_v025_pilot"
    spec = importlib.util.spec_from_file_location(name, PILOT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load V0.25 pilot adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def forbid_scalar_evaluate(runner) -> None:
    original = runner.StepEvaluator.evaluate

    def forbidden(*args, **kwargs):
        del args, kwargs
        global SCALAR_EVALUATE_CALLS
        SCALAR_EVALUATE_CALLS += 1
        raise AssertionError("scalar StepEvaluator.evaluate is forbidden in BEAMCOUNT")

    forbidden.__name__ = "scalar_evaluate_forbidden_in_beamcount"
    forbidden.__wrapped__ = original
    runner.StepEvaluator.evaluate = forbidden
    assert runner.StepEvaluator.evaluate is forbidden


# --------------------------------------------------------------------------
# combinatorics reproduced from CROWDCOST run_crowding_cost.py
# --------------------------------------------------------------------------
def maximum_matching(options, allowed_beams=None):
    allowed = None if allowed_beams is None else frozenset(allowed_beams)
    beam_to_user: dict[tuple[int, int], int] = {}

    def augment(user: int, seen: set) -> bool:
        for beam in sorted(options[user]):
            if (allowed is not None and beam not in allowed) or beam in seen:
                continue
            seen.add(beam)
            incumbent = beam_to_user.get(beam)
            if incumbent is None or augment(incumbent, seen):
                beam_to_user[beam] = user
                return True
        return False

    for user in sorted(options):
        augment(user, set())
    return {user: beam for beam, user in beam_to_user.items()}


def greedy_cover(users, beam_users):
    uncovered = set(users)
    chosen = []
    while uncovered:
        beam = min(beam_users, key=lambda v: (-len(beam_users[v] & uncovered), v))
        gain = beam_users[beam] & uncovered
        if not gain:
            raise RuntimeError("legal-option graph does not cover every user")
        chosen.append(beam)
        uncovered -= gain
    return tuple(chosen)


def minimum_cover(options):
    """Exact minimum set cover, byte-for-byte the CROWDCOST procedure."""
    users = tuple(sorted(u for u, rows in options.items() if rows))
    user_index = {u: i for i, u in enumerate(users)}
    by_beam: dict[tuple[int, int], int] = {}
    for user in users:
        bit = 1 << user_index[user]
        for beam in options[user]:
            by_beam[beam] = by_beam.get(beam, 0) | bit

    mask_to_beam: dict[int, tuple[int, int]] = {}
    for beam, mask in sorted(by_beam.items()):
        mask_to_beam.setdefault(mask, beam)
    unique = sorted(mask_to_beam.items(), key=lambda item: (-item[0].bit_count(), item[1]))
    maximal = []
    for mask, beam in unique:
        if any(mask | kept == kept for kept, _ in maximal):
            continue
        maximal.append((mask, beam))
    masks = tuple(m for m, _ in maximal)
    beams = tuple(b for _, b in maximal)
    universe = (1 << len(users)) - 1

    beam_users = {
        beam: frozenset(u for u in users if mask & (1 << user_index[u]))
        for mask, beam in maximal
    }
    greedy = greedy_cover(frozenset(users), beam_users)
    candidates_by_bit = {
        bit: tuple(i for i, mask in enumerate(masks) if mask & bit)
        for bit in (1 << i for i in range(len(users)))
    }

    def solve(limit: int):
        failed: set[tuple[int, int]] = set()

        def search(uncovered: int, remaining: int):
            if uncovered == 0:
                return ()
            if remaining == 0 or (uncovered, remaining) in failed:
                return None
            gains = tuple((mask & uncovered).bit_count() for mask in masks)
            max_gain = max(gains, default=0)
            if max_gain == 0 or math.ceil(uncovered.bit_count() / max_gain) > remaining:
                failed.add((uncovered, remaining))
                return None
            uncovered_bits = tuple(
                1 << i for i in range(len(users)) if uncovered & (1 << i)
            )
            pivot = min(uncovered_bits, key=lambda bit: (
                sum(gains[i] > 0 for i in candidates_by_bit[bit]), bit,
            ))
            candidates = sorted(
                (i for i in candidates_by_bit[pivot] if gains[i] > 0),
                key=lambda i: (-gains[i], beams[i]),
            )
            for i in candidates:
                suffix = search(uncovered & ~masks[i], remaining - 1)
                if suffix is not None:
                    return (i, *suffix)
            failed.add((uncovered, remaining))
            return None

        return search(universe, limit)

    solution = None
    for limit in range(1, len(greedy) + 1):
        solution = solve(limit)
        if solution is not None:
            break
    if solution is None:
        raise RuntimeError("exact set-cover search failed despite a greedy upper bound")
    best = tuple(sorted(beams[i] for i in solution))
    if len(maximum_matching(options, best)) != len(best):
        raise RuntimeError("minimum cover lacks a distinct witness for every beam")
    return best, len(greedy)


def greedy_cover_persat(options, per_sat_cap):
    """Greedy cover using at most `per_sat_cap` beams per NORAD id."""
    all_beams = sorted({b for r in options.values() for b in r})
    beam_users = {b: frozenset(u for u in options if b in options[u]) for b in all_beams}
    uncovered = {u for u, r in options.items() if r}
    used: Counter = Counter()
    chosen: list = []
    while uncovered:
        eligible = [
            b for b in all_beams
            if b not in chosen and used[b[0]] < per_sat_cap and (beam_users[b] & uncovered)
        ]
        if not eligible:
            return None
        beam = min(eligible, key=lambda b: (-len(beam_users[b] & uncovered), b))
        chosen.append(beam)
        used[beam[0]] += 1
        uncovered -= beam_users[beam]
    return tuple(sorted(chosen))


def minimum_cover_persat(options, per_sat_cap, upper, node_budget=4_000_000):
    """Exact minimum legal-beam cover with at most `per_sat_cap` beams per
    satellite.  Coverage-dominance pruning is applied only within a satellite,
    because a dominated beam on another satellite can still be required."""
    users = tuple(sorted(u for u, r in options.items() if r))
    idx = {u: i for i, u in enumerate(users)}
    by_beam: dict[tuple[int, int], int] = {}
    for u in users:
        bit = 1 << idx[u]
        for b in options[u]:
            by_beam[b] = by_beam.get(b, 0) | bit
    by_sat: dict[int, list] = {}
    for beam, mask in sorted(by_beam.items()):
        by_sat.setdefault(beam[0], []).append((mask, beam))
    kept: list = []
    for _, rows in sorted(by_sat.items()):
        rows.sort(key=lambda r: (-r[0].bit_count(), r[1]))
        maximal: list = []
        for mask, beam in rows:
            if any(mask | k == k for k, _ in maximal):
                continue
            maximal.append((mask, beam))
        kept.extend(maximal)
    kept.sort(key=lambda r: (-r[0].bit_count(), r[1]))
    masks = tuple(m for m, _ in kept)
    beams = tuple(b for _, b in kept)
    sats = tuple(b[0] for b in beams)
    universe = (1 << len(users)) - 1
    cand_by_bit = {
        bit: tuple(i for i, m in enumerate(masks) if m & bit)
        for bit in (1 << i for i in range(len(users)))
    }
    nodes = 0

    def solve(limit):
        nonlocal nodes
        failed = set()

        def search(uncovered, remaining, used):
            nonlocal nodes
            nodes += 1
            if nodes > node_budget:
                raise TimeoutError("node budget exhausted")
            if uncovered == 0:
                return ()
            if remaining == 0:
                return None
            key = (uncovered, remaining, tuple(sorted(used.items())))
            if key in failed:
                return None
            avail = [
                i for i in range(len(masks))
                if used.get(sats[i], 0) < per_sat_cap and (masks[i] & uncovered)
            ]
            if not avail:
                failed.add(key)
                return None
            max_gain = max((masks[i] & uncovered).bit_count() for i in avail)
            if math.ceil(uncovered.bit_count() / max_gain) > remaining:
                failed.add(key)
                return None
            bits = tuple(1 << i for i in range(len(users)) if uncovered & (1 << i))
            pivot = min(bits, key=lambda bit: (
                sum(1 for i in cand_by_bit[bit]
                    if used.get(sats[i], 0) < per_sat_cap and (masks[i] & uncovered)),
                bit,
            ))
            cands = sorted(
                (i for i in cand_by_bit[pivot]
                 if used.get(sats[i], 0) < per_sat_cap and (masks[i] & uncovered)),
                key=lambda i: (-(masks[i] & uncovered).bit_count(), beams[i]),
            )
            for i in cands:
                used[sats[i]] = used.get(sats[i], 0) + 1
                suffix = search(uncovered & ~masks[i], remaining - 1, used)
                used[sats[i]] -= 1
                if suffix is not None:
                    return (i, *suffix)
            failed.add(key)
            return None

        return search(universe, limit, {})

    for limit in range(1, upper + 1):
        try:
            solution = solve(limit)
        except TimeoutError:
            return None, "NODE_BUDGET_EXHAUSTED", nodes
        if solution is not None:
            return tuple(sorted(beams[i] for i in solution)), "EXACT", nodes
    return None, f"INFEASIBLE_UP_TO_{upper}", nodes


def matroid_extension(options, minimum, order_key, target_size, maximum_rank):
    """Extend the minimum cover to `target_size` beams while every selected beam
    keeps a private witness user (independent in the beam/user transversal
    matroid), adding beams in the order given by `order_key`."""
    all_beams = tuple(sorted({b for rows in options.values() for b in rows}))
    beam_users = {
        beam: tuple(sorted(u for u, rows in options.items() if beam in rows))
        for beam in all_beams
    }
    beam_to_user: dict[tuple[int, int], int] = {}
    user_to_beam: dict[int, tuple[int, int]] = {}

    def augment(start):
        seen_users: set[int] = set()

        def visit(beam) -> bool:
            for user in beam_users[beam]:
                if user in seen_users:
                    continue
                seen_users.add(user)
                incumbent = user_to_beam.get(user)
                if incumbent is None or visit(incumbent):
                    beam_to_user[beam] = user
                    user_to_beam[user] = beam
                    return True
            return False

        return visit(start)

    selected = set(minimum)
    for beam in sorted(minimum):
        if not augment(beam):
            raise RuntimeError("minimum cover is unexpectedly not beam-matchable")
    if target_size <= len(selected):
        return tuple(sorted(selected))
    for beam in sorted(all_beams, key=order_key):
        if beam in selected:
            continue
        if augment(beam):
            selected.add(beam)
            if len(selected) >= min(target_size, maximum_rank):
                break
    return tuple(sorted(selected))


def assignment_coverage_first(options, beams):
    """CROWDCOST A1: distinct witness per selected beam, then crowd the rest
    onto the selected legal beam with greatest anchor-wide coverage."""
    selected = frozenset(beams)
    matched = maximum_matching(options, selected)
    if len(matched) != len(selected):
        raise RuntimeError("selected beam set cannot be fully activated")
    coverage = {beam: sum(beam in options[u] for u in options) for beam in selected}
    mapping: dict[int, tuple[int, int] | None] = {}
    for user in sorted(options):
        if not options[user]:
            mapping[user] = None
        elif user in matched:
            mapping[user] = matched[user]
        else:
            choices = [b for b in options[user] if b in selected]
            if not choices:
                raise RuntimeError("selected cover omitted a legal user")
            mapping[user] = min(choices, key=lambda b: (-coverage[b], b))
    return mapping


def assignment_max_gain(options, beams, gain_of):
    """A2: every user takes the in-set legal beam of greatest boundary-0
    nominal gain (RSS_MAX restricted to the selected beam set)."""
    selected = frozenset(beams)
    mapping: dict[int, tuple[int, int] | None] = {}
    for user in sorted(options):
        choices = [b for b in options[user] if b in selected]
        if not choices:
            mapping[user] = None
            continue
        mapping[user] = min(
            enumerate(choices), key=lambda item: (-gain_of(user, item[1]), item[0])
        )[1]
    return mapping


def assignment_least_loaded(options, beams):
    """A3: least-loaded in-set legal beam, stable by option index."""
    selected = frozenset(beams)
    loads: Counter = Counter()
    mapping: dict[int, tuple[int, int] | None] = {}
    for user in sorted(options):
        choices = [b for b in options[user] if b in selected]
        if not choices:
            mapping[user] = None
            continue
        beam = min(enumerate(choices), key=lambda item: (loads[item[1]], item[0]))[1]
        mapping[user] = beam
        loads[beam] += 1
    return mapping


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------
def mapping_stats(mapping) -> dict:
    counts = Counter(v for v in mapping.values() if v is not None)
    assigned = sum(counts.values())
    return {
        "assigned": assigned,
        "null_users": sum(v is None for v in mapping.values()),
        "active_beams_mapping": len(counts),
        "active_satellites_mapping": len({b[0] for b in counts}),
        "modal_count": max(counts.values(), default=0),
        "modal_frac": 0.0 if assigned == 0 else max(counts.values()) / assigned,
        "occupancies_desc": sorted(counts.values(), reverse=True),
    }


def endpoint_metrics(profile, mapping) -> dict:
    attained = profile.score.rate_target_attained
    if attained is None:
        raise RuntimeError("committed profile omitted rate-target attainment")
    served = sum(bool(v) for v in profile.score.served_phy.values())
    return {
        **mapping_stats(mapping),
        "configuration_id": profile.config.configuration_id,
        "bits": float(profile.bits),
        "joules": float(profile.joules),
        "ee_bit_per_j": float(profile.bits) / float(profile.joules),
        "served_phy": served,
        "user_count": len(profile.score.served_phy),
        "rate_target_attained": sum(bool(v) for v in attained.values()),
        "rate_target_user_count": len(attained),
        "pa_j": float(profile.energy_components["pa_j"]),
        "circuit_j": float(profile.energy_components["circuit_j"]),
        "baseband_j": float(profile.energy_components["baseband_j"]),
        "mean_radiating_beams": float(profile.lit_beam_seconds) / DECISION_INTERVAL_S,
        "mean_active_satellites": float(profile.lit_satellite_seconds) / DECISION_INTERVAL_S,
        "rf_cap_hits": int(profile.rf_cap_hits),
        "rf_transmission_observations": int(profile.rf_transmission_observations),
        "max_rf_power_w": float(profile.required_power_w_max),
    }


def pool(rows: Sequence[Mapping[str, object]]) -> dict:
    bits = math.fsum(float(r["bits"]) for r in rows)
    joules = math.fsum(float(r["joules"]) for r in rows)
    assigned = sum(int(r["assigned"]) for r in rows)
    modal = sum(int(r["modal_count"]) for r in rows)
    return {
        "anchors": len(rows),
        "bits": bits,
        "joules": joules,
        "ee_bit_per_j": bits / joules,
        "ee_mbit_per_j": bits / joules / 1e6,
        "served_phy": sum(int(r["served_phy"]) for r in rows),
        "user_count": sum(int(r["user_count"]) for r in rows),
        "rate_target_attained": sum(int(r["rate_target_attained"]) for r in rows),
        "assigned": assigned,
        "null_users": sum(int(r["null_users"]) for r in rows),
        "modal_frac": modal / assigned if assigned else 0.0,
        "active_beams_mapping_mean": math.fsum(
            float(r["active_beams_mapping"]) for r in rows) / len(rows),
        "active_beams_mapping_range": [
            min(int(r["active_beams_mapping"]) for r in rows),
            max(int(r["active_beams_mapping"]) for r in rows),
        ],
        "mean_radiating_beams_mean": math.fsum(
            float(r["mean_radiating_beams"]) for r in rows) / len(rows),
        "mean_active_satellites_mean": math.fsum(
            float(r["mean_active_satellites"]) for r in rows) / len(rows),
        "pa_j": math.fsum(float(r["pa_j"]) for r in rows),
        "circuit_j": math.fsum(float(r["circuit_j"]) for r in rows),
        "baseband_j": math.fsum(float(r["baseband_j"]) for r in rows),
        "rf_cap_hits": sum(int(r["rf_cap_hits"]) for r in rows),
        "rf_transmission_observations": sum(
            int(r["rf_transmission_observations"]) for r in rows),
        "max_rf_power_w": max(float(r["max_rf_power_w"]) for r in rows),
    }


# --------------------------------------------------------------------------
# boundary-0 local search
# --------------------------------------------------------------------------
class Boundary0Search:
    """First-improvement single-user reassignment on one fresh dense
    boundary-0 evaluator.  BASE is submitted in the same evaluate_many batch
    as the first candidates.  Profiles are read only from _evaluated."""

    def __init__(self, runner, tape, step_index, incumbent, run_setting, base, kind):
        self.runner = runner
        self.base = base
        self.kind = kind
        self.evaluator = runner.StepEvaluator(
            tape, runner._setting("a-r0"), step_index,
            transition_from=incumbent,
            cell_rekeyed_users=runner._rekeyed_users(tape, step_index),
            field="realised", counter=runner.EvaluationCounter(),
            run_setting=run_setting, boundary_indices=(0,),
        )
        self.submitted = 0
        self.serial = 0

    def submit(self, configs) -> None:
        configs = list(configs)
        if not configs:
            return
        self.evaluator.evaluate_many(configs)
        self.submitted += len(configs)

    def read(self, config):
        if config.configuration_id in self.evaluator._invalid:
            return None
        return self.evaluator._evaluated.get(config.configuration_id)

    def make(self, mapping):
        self.serial += 1
        return self.runner._configuration(
            self.base, mapping, kind=f"{self.kind}-{self.serial:06d}"
        )

    @staticmethod
    def score(profile):
        served = sum(bool(v) for v in profile.score.served_phy.values())
        return (float(profile.bits) / float(profile.joules), served)

    def run(self, mapping, options, allowed, max_passes):
        """Return (mapping, config, ee, served, moves, passes)."""
        current_map = dict(mapping)
        current_cfg = self.make(current_map)
        self.submit([self.base, current_cfg])
        profile = self.read(current_cfg)
        if profile is None:
            return None
        current_ee, current_served = self.score(profile)
        moves = 0
        passes = 0
        for _ in range(max_passes):
            passes += 1
            moved_this_pass = 0
            for user in sorted(options):
                held = current_map.get(user)
                alternatives = [
                    b for b in options[user]
                    if b != held and (allowed is None or b in allowed)
                ]
                if not alternatives:
                    continue
                trials = []
                for beam in alternatives:
                    trial_map = dict(current_map)
                    trial_map[user] = beam
                    trials.append((beam, self.make(trial_map), trial_map))
                self.submit([row[1] for row in trials])
                best = None
                for beam, cfg, trial_map in trials:
                    trial_profile = self.read(cfg)
                    if trial_profile is None:
                        continue
                    ee, served = self.score(trial_profile)
                    if served < current_served:
                        continue
                    if ee <= current_ee:
                        continue
                    key = (-ee, cfg.configuration_id)
                    if best is None or key < best[0]:
                        best = (key, ee, served, cfg, trial_map)
                if best is not None:
                    _, current_ee, current_served, current_cfg, current_map = best
                    moves += 1
                    moved_this_pass += 1
            if moved_this_pass == 0:
                break
        return current_map, current_cfg, current_ee, current_served, moves, passes

    def close(self):
        del self.evaluator
        gc.collect()


# --------------------------------------------------------------------------
# learned a0
# --------------------------------------------------------------------------
def decode_hex_array(value) -> np.ndarray:
    raw = np.asarray(value, dtype=object)
    return np.asarray(
        [float.fromhex(str(item)) for item in raw.reshape(-1)]
    ).reshape(raw.shape)


def mlp_scores(head, states) -> np.ndarray:
    current = np.asarray(states, dtype=np.float64)
    weights = [decode_hex_array(v) for v in head["weights_hex"]]
    biases = [decode_hex_array(v) for v in head["biases_hex"]]
    activation = str(head["activation"])
    for index, (weight, bias) in enumerate(zip(weights, biases, strict=True)):
        current = current @ weight + bias
        if index != len(weights) - 1:
            current = np.maximum(current, 0.0) if activation == "relu" else np.tanh(current)
    return current[:, 0]


def row_action(row):
    payload = row["action"]
    norad, beam = payload["norad_id"], payload["beam_chain_id"]
    if norad is None and beam is None:
        return None
    return (int(norad), int(beam))


def load_corpus_tables(anchor_ids):
    """Read the 12 development-anchor exact-source shards named by the learned
    run's launch receipt; verify every shard digest."""
    receipt = json.loads((LEARNED_RUN / "launch-receipt.json").read_text(encoding="utf-8"))
    corpus = receipt["corpus"]
    root = Path(corpus["root"]).resolve()
    if root != CORPUS_ROOT.resolve():
        raise RuntimeError(f"unexpected corpus root: {root}")
    source_files = [r for r in corpus["files"] if "exact-source" in str(r["path"])]
    if len(source_files) != 22:
        raise RuntimeError("launch receipt does not name exactly 22 source shards")
    tables: dict[str, dict[int, tuple]] = {}
    verified = []
    for binding in source_files:
        index = int(Path(binding["path"]).name.split("-anchor-")[1].split(".")[0])
        if index > 11:
            continue  # anchors 12..21 are steps 4..7; outside the 12-anchor panel
        path = (root / Path(binding["path"])).resolve()
        if not path.is_relative_to(root):
            raise RuntimeError("source shard escapes corpus root")
        digest = sha256_file(path)
        if digest != binding["sha256"]:
            raise RuntimeError(f"source shard digest mismatch: {path}")
        lines = path.read_bytes().splitlines()
        header = json.loads(lines[0])
        rows = [json.loads(line) for line in lines[1:]]
        if header.get("row_count") != len(rows):
            raise RuntimeError(f"row count mismatch: {path}")
        if {r["split"] for r in rows} != {"TRAIN"}:
            raise RuntimeError("non-TRAIN row in development shard")
        anchor_id = rows[0]["anchor_id"]
        if len({r["anchor_id"] for r in rows}) != 1:
            raise RuntimeError("shard mixes anchors")
        by_user: dict[int, list] = defaultdict(list)
        for row in rows:
            by_user[int(row["user_id"])].append(row)
        table = {}
        for user, values in by_user.items():
            ordered = tuple(sorted(values, key=lambda r: int(r["action_index"])))
            if tuple(int(r["action_index"]) for r in ordered) != tuple(range(len(ordered))):
                raise RuntimeError("non-contiguous action indices")
            masks = {tuple(bool(v) for v in r["action_mask"]) for r in ordered}
            if len(masks) != 1 or len(next(iter(masks))) != len(ordered):
                raise RuntimeError("action mask mismatch")
            if sum(bool(r["reference_action"]) for r in ordered) != 1:
                raise RuntimeError("BASE multiplicity mismatch")
            table[user] = ordered
        tables[anchor_id] = table
        verified.append({
            "global_anchor_index": index, "anchor_id": anchor_id,
            "path": str(path), "sha256": digest, "rows": len(rows),
        })
    if set(tables) != set(anchor_ids):
        raise RuntimeError(
            f"corpus anchors {sorted(tables)} do not match panel {sorted(anchor_ids)}"
        )
    return tables, verified, receipt


def load_checkpoints():
    directory = LEARNED_RUN / "checkpoints"
    selected = []
    for path in sorted(directory.glob(f"learner-*-epoch-{TARGET_EPOCH:06d}.json")):
        stem = path.name.removesuffix(".json")
        seed = int(stem.removeprefix("learner-").split("-epoch-")[0])
        encoded = path.read_bytes()
        digest = hashlib.sha256(encoded).hexdigest()
        sidecar = path.with_name(path.name + ".sha256")
        if sidecar.is_file():
            fields = sidecar.read_text(encoding="ascii").split()
            if not fields or fields[0] != digest:
                raise RuntimeError(f"checkpoint sidecar mismatch: {path}")
        payload = json.loads(encoded)
        if (
            payload.get("schema") != "mcrl-v025-stagec-v1-lineage-checkpoint-v1"
            or int(payload.get("learner_seed", -1)) != seed
            or int(payload.get("completed_source_epochs", -1)) != TARGET_EPOCH
            or set(payload.get("arms", {})) != {
                "FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL"}
        ):
            raise RuntimeError(f"checkpoint authority mismatch: {path}")
        selected.append({
            "seed": seed, "epoch": TARGET_EPOCH, "path": str(path),
            "sha256": digest, "payload": payload,
        })
    if not selected:
        raise RuntimeError("no epoch-500 checkpoints found")
    return tuple(sorted(selected, key=lambda r: r["seed"]))


def a0_profiles(tables, checkpoints, arm="FULL"):
    """Raw independent masked argmax(Q1+Q2) per user, before joint repair."""
    result: dict[int, dict[str, dict[int, tuple | None]]] = {}
    for checkpoint in checkpoints:
        model = checkpoint["payload"]["arms"][arm]
        by_anchor = {}
        for anchor_id, users in tables.items():
            mapping = {}
            for user in sorted(users):
                rows = users[user]
                q1 = np.asarray([[float.fromhex(str(v)) for v in r["q1_state"]] for r in rows])
                q2 = np.asarray([[float.fromhex(str(v)) for v in r["q2_state"]] for r in rows])
                scores = mlp_scores(model["C1"], q1) + mlp_scores(model["C2"], q2)
                mask = np.asarray(rows[0]["action_mask"], dtype=bool)
                scores = np.where(mask, scores, -np.inf)
                mapping[user] = row_action(rows[int(np.argmax(scores))])
            by_anchor[anchor_id] = mapping
        result[int(checkpoint["seed"])] = by_anchor
    return result


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    check_runtime()
    started = time.perf_counter()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    pilot = load_pilot()
    runner = pilot.ENGINE
    run_setting = runner.run_setting_for("a-r0")
    forbid_scalar_evaluate(runner)
    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape

    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB before tape", flush=True)
    tape_started = time.perf_counter()
    tape = build_world_tape(
        domain=pilot.TRAIN_WORLDS[0],
        provider=LegacyWorldProvider(role="pilot-source"),
        steps=33, start_time_s=0.0,
    )
    tape_seconds = time.perf_counter() - tape_started
    check_runtime()
    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB after tape ({tape_seconds:.1f}s)", flush=True)

    full_panel = [(step, carrier) for step in range(4) for carrier in CARRIERS]
    if MODE == "sweep":
        if SHARD_CARRIER not in CARRIERS:
            raise RuntimeError(f"sweep mode needs BEAMCOUNT_CARRIER in {CARRIERS}")
        panel = [(s, c) for s, c in full_panel if c == SHARD_CARRIER][:ANCHOR_LIMIT]
    else:
        panel = full_panel[:ANCHOR_LIMIT]
    anchor_ids = [f"{tape.domain}|{s}|{c}" for s, c in panel]
    corpus_anchor_ids = [f"{tape.domain}|{s}|{c}" for s, c in full_panel]

    # ---- per-step legal graph, feasibility floor, matching rank ------------
    steps: dict[int, dict] = {}
    for step_index in sorted({s for s, _ in panel}):
        options, census = runner._legal_options(tape, step_index)
        t0 = time.perf_counter()
        cover, greedy_size = minimum_cover(options)
        cover_seconds = time.perf_counter() - t0
        rank = len(maximum_matching(options))
        all_beams = tuple(sorted({b for rows in options.values() for b in rows}))
        coverage = {b: sum(b in options[u] for u in options) for b in all_beams}
        arrays = tape.steps[step_index].arrays
        if arrays is None:
            raise RuntimeError("frozen exact panel must expose primitive arrays")
        row_of = arrays._row_index()

        def gain_of(user, beam, _a=arrays, _r=row_of):
            return float(_a.nominal_gain[0, _r[(user, beam)]])

        beam_gain = {
            b: math.fsum(gain_of(u, b) for u in options if b in options[u])
            for b in all_beams
        }
        satellites = sorted({b[0] for b in all_beams})
        persat: dict[int, dict] = {}
        for per_sat_cap in PER_SATELLITE_CAPS:
            t1 = time.perf_counter()
            greedy = greedy_cover_persat(options, per_sat_cap)
            upper = len(greedy) if greedy is not None else per_sat_cap * len(satellites)
            solution, status, nodes = minimum_cover_persat(options, per_sat_cap, upper)
            persat[per_sat_cap] = {
                "per_satellite_cap": per_sat_cap,
                "system_wide_beam_universe": per_sat_cap * len(satellites),
                "greedy_feasible": greedy is not None,
                "greedy_cover_size": None if greedy is None else len(greedy),
                "exact_status": status,
                "exact_minimum_cover_size": None if solution is None else len(solution),
                "cover": solution,
                "cover_beams": None if solution is None else [list(b) for b in solution],
                "cover_beams_per_satellite": None if solution is None else {
                    str(s): sum(1 for b in solution if b[0] == s) for s in satellites
                },
                "search_nodes": nodes,
                "seconds": time.perf_counter() - t1,
            }
            print(f"  step {step_index} per-sat cap {per_sat_cap}: "
                  f"{status} size={persat[per_sat_cap]['exact_minimum_cover_size']} "
                  f"nodes={nodes}", flush=True)
        steps[step_index] = {
            "satellites": satellites,
            "persat": persat,
            "options": options, "census": census, "cover": cover,
            "greedy_cover_size": greedy_size, "matching_rank": rank,
            "all_beams": all_beams, "coverage": coverage,
            "beam_gain": beam_gain, "gain_of": gain_of,
            "cover_seconds": cover_seconds,
            "option_sizes": sorted({len(v) for v in options.values()}),
            "users_without_legal_option": sorted(u for u, v in options.items() if not v),
        }
        print(
            f"step {step_index}: floor={len(cover)} greedy={greedy_size} rank={rank} "
            f"beams={len(all_beams)} cover_s={cover_seconds:.2f}",
            flush=True,
        )
        check_runtime()

    floors = {s: len(steps[s]["cover"]) for s in steps}
    floor = max(floors.values())
    if len(set(floors.values())) != 1:
        print(f"WARNING: per-step floors differ: {floors}", flush=True)

    caps: list[int] = sorted({
        *(c for c in REQUESTED_CAPS if c >= floor),
        floor, floor + 1, floor + 2,
    })
    infeasible = sorted(c for c in REQUESTED_CAPS if c < floor)
    print(f"floor={floor} caps={caps} infeasible={infeasible}", flush=True)

    # ---- learned a0 (not needed by sweep shards) ----------------------------
    a0: dict = {}
    checkpoint_index: list = []
    shard_receipts: list = []
    shortlist_audit: list = []
    tables: dict = {}
    if MODE != "sweep":
        tables, shard_receipts, launch_receipt = load_corpus_tables(corpus_anchor_ids)
        tables = {k: v for k, v in tables.items() if k in set(anchor_ids)}
        checkpoints = load_checkpoints()
        if SEED_LIMIT:
            checkpoints = checkpoints[:SEED_LIMIT]
        print(f"corpus shards={len(shard_receipts)} checkpoints={len(checkpoints)}", flush=True)
        a0 = a0_profiles(tables, checkpoints)
        checkpoint_index = [
            {k: v for k, v in row.items() if k != "payload"} for row in checkpoints
        ]
        del checkpoints
        gc.collect()
    # corpus shortlist versus tape legal options
    for step_index, carrier in (panel if MODE != "sweep" else []):
        anchor_id = f"{tape.domain}|{step_index}|{carrier}"
        options = steps[step_index]["options"]
        table = tables[anchor_id]
        sizes = []
        escapes = 0
        for user in sorted(table):
            acts = {row_action(r) for r in table[user] if row_action(r) is not None}
            sizes.append(len(table[user]))
            escapes += len(acts - set(options[user]))
        shortlist_audit.append({
            "anchor_id": anchor_id,
            "corpus_actions_per_user_min": min(sizes),
            "corpus_actions_per_user_max": max(sizes),
            "tape_legal_options_per_user": sorted({len(v) for v in options.values()}),
            "corpus_actions_not_legal_in_tape": escapes,
        })
    if any(r["corpus_actions_not_legal_in_tape"] for r in shortlist_audit):
        raise RuntimeError("corpus shortlist contains actions illegal in the tape")
    print("corpus shortlist audit clean", flush=True)
    del tables
    gc.collect()
    check_runtime()

    payload: dict = {
        "schema": "mcrl-v025-beam-count-cap-design-measurement-v1",
        "status": "RUNNING",
        "claim_status": "DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM",
        "rehearsal_not_reportable": REHEARSAL,
        "search_depth": {
            "capped_passes": CAPPED_PASSES,
            "uncapped_passes": UNCAPPED_PASSES,
            "anchor_limit": ANCHOR_LIMIT,
            "seed_limit": SEED_LIMIT,
        },
        "panel": {
            "domain": tape.domain, "world_tape_digest": tape.digest,
            "anchors": len(panel), "anchor_ids": anchor_ids,
            "rule": "steps 0..3 x nearest-eligible, stay-if-possible, random-masked",
            "numerator": "saturated full-buffer decoded information bits; no demand cap",
            "evaluation_boundaries": list(range(48)),
        },
        "evaluator_discipline": {
            "selection": "one fresh dense StepEvaluator(field=realised, boundary_indices=(0,)) per (anchor, cap); BASE submitted in the first evaluate_many batch with the first candidate",
            "profile_reads": "StepEvaluator._evaluated only",
            "endpoints": "one separate fresh realised StepEvaluator(boundary_indices=range(48)) per anchor, populated by exactly one evaluate_many call",
            "scalar_evaluate_fail_closed": True,
        },
        "source": {
            "root": str(SOURCE_ROOT),
            "pilot": str(PILOT_PATH), "pilot_sha256": sha256_file(PILOT_PATH),
            "engine": str(ENGINE_PATH), "engine_sha256": sha256_file(ENGINE_PATH),
            "batch_sha256": sha256_file(SOURCE_ROOT / "src/mcrl/physics_v025/batch.py"),
            "energy_sha256": sha256_file(SOURCE_ROOT / "src/mcrl/physics_v025/energy.py"),
            "targets_sha256": sha256_file(SOURCE_ROOT / "src/mcrl/physics_v025/targets.py"),
        },
        "mode": MODE,
        "shard_carrier": SHARD_CARRIER if MODE == "sweep" else None,
        "learned_arm": None if MODE == "sweep" else {
            "run_directory": str(LEARNED_RUN),
            "launch_receipt_sha256": sha256_file(LEARNED_RUN / "launch-receipt.json"),
            "training_result_sha256": sha256_file(LEARNED_RUN / "training-result.json"),
            "corpus_root": str(CORPUS_ROOT),
            "arm": "FULL", "epoch": TARGET_EPOCH,
            "seed_count": len(checkpoint_index),
            "checkpoints": checkpoint_index,
            "development_shards": shard_receipts,
            "rule": "raw independent masked argmax(Q1+Q2) per user, before joint-conflict repair",
            "shortlist_audit": shortlist_audit,
        },
        "feasibility": {
            "per_step": {
                str(s): {
                    "minimum_legal_beam_set_cover": len(steps[s]["cover"]),
                    "cover_beams": [list(b) for b in steps[s]["cover"]],
                    "greedy_cover_size": steps[s]["greedy_cover_size"],
                    "maximum_distinct_beam_matching_rank": steps[s]["matching_rank"],
                    "distinct_legal_beams": len(steps[s]["all_beams"]),
                    "legal_options_per_user": steps[s]["option_sizes"],
                    "users_without_legal_option": steps[s]["users_without_legal_option"],
                    "exact_cover_seconds": steps[s]["cover_seconds"],
                    "legal_option_census": steps[s]["census"],
                    "satellites": steps[s]["satellites"],
                    "satellite_count": len(steps[s]["satellites"]),
                    "unconstrained_cover_beams_per_satellite": {
                        str(sat): sum(1 for b in steps[s]["cover"] if b[0] == sat)
                        for sat in steps[s]["satellites"]
                    },
                    "per_satellite_cap": {
                        str(k): {
                            key: value for key, value in row.items() if key != "cover"
                        } for k, row in sorted(steps[s]["persat"].items())
                    },
                } for s in sorted(steps)
            },
            "panel_floor": floor,
            "per_step_floors": {str(s): floors[s] for s in sorted(floors)},
            "requested_caps": list(REQUESTED_CAPS),
            "evaluated_caps": caps,
            "infeasible_caps_below_floor": infeasible,
            "three_beam_cap_feasible": 3 >= floor,
        },
        "runtime": {
            "python": sys.executable,
            "niceness": os.getpriority(os.PRIO_PROCESS, 0),
            "processes": 1,
            "thread_pins": {n: os.environ[n] for n in THREAD_VARS},
            "world_tape_seconds": tape_seconds,
        },
        "anchors": [],
    }
    atomic_write(PARTIAL, dict(payload, status="PARTIAL"))

    # ---------------------------------------------------------------- pass 1
    winning_sets: dict[str, dict[str, list]] = {}
    anchor_rows: list[dict] = []

    shard_digests: dict[str, dict] = {}
    if MODE == "project":
        by_id: dict[str, dict] = {}
        for carrier in CARRIERS:
            path = shard_path(carrier)
            shard = json.loads(path.read_text(encoding="utf-8"))
            if shard.get("status") != "COMPLETE" or shard.get("mode") != "sweep":
                raise RuntimeError(f"shard not complete: {path}")
            if shard.get("receipt_sha256") != canonical_digest(shard):
                raise RuntimeError(f"shard digest mismatch: {path}")
            if shard["panel"]["world_tape_digest"] != tape.digest:
                raise RuntimeError(f"shard tape digest differs: {path}")
            frozen = OUTDIR / "run_beamcount_sweep_frozen.py"
            if not REHEARSAL and shard.get("runner_sha256") != sha256_file(frozen):
                raise RuntimeError(f"shard runner hash differs from frozen sweep runner: {path}")
            if bool(shard.get("rehearsal_not_reportable")) != REHEARSAL:
                raise RuntimeError(f"shard rehearsal flag differs: {path}")
            if shard["scalar_evaluate_calls"] != 0:
                raise RuntimeError(f"shard recorded scalar evaluate calls: {path}")
            if shard["feasibility"]["evaluated_caps"] != caps:
                raise RuntimeError(f"shard cap list differs: {path}")
            shard_digests[carrier] = {
                "path": str(path), "file_sha256": sha256_file(path),
                "receipt_sha256": shard["receipt_sha256"],
                "scalar_evaluate_calls": shard["scalar_evaluate_calls"],
                "peak_rss_bytes": shard["runtime"]["peak_rss_bytes"],
                "wall_seconds": shard["runtime"]["wall_seconds"],
                "search_depth": shard["search_depth"],
                "runner_sha256": shard.get("runner_sha256"),
            }
            for row in shard["anchors"]:
                by_id[row["anchor_id"]] = row
            for anchor_id, sets in shard["winning_sets"].items():
                winning_sets[anchor_id] = {
                    label: tuple(tuple(b) for b in beams) for label, beams in sets.items()
                }
        anchor_rows = [by_id[a] for a in anchor_ids]
        payload["anchors"] = anchor_rows
        payload["shards"] = shard_digests

    for position, (step_index, carrier) in enumerate(panel if MODE != "project" else [], 1):
        anchor_id = f"{tape.domain}|{step_index}|{carrier}"
        anchor_started = time.perf_counter()
        state = steps[step_index]
        options = state["options"]
        coverage, beam_gain, gain_of = state["coverage"], state["beam_gain"], state["gain_of"]
        cover, rank = state["cover"], state["matching_rank"]
        base = runner._base_configuration(tape, step_index, carrier)
        incumbent = runner._base_configuration(tape, max(0, step_index - 1), carrier)

        beam_set_rules = {
            "S1_ascending_coverage": lambda b: (coverage[b], b),
            "S2_descending_coverage": lambda b: (-coverage[b], b),
            "S3_descending_nominal_gain": lambda b: (-beam_gain[b], b),
        }

        cap_rows: dict[str, dict] = {}
        endpoint_jobs: list[tuple[str, object, dict]] = []
        search_detail: dict[str, dict] = {}

        rss_map = {}
        for user in sorted(options):
            if not options[user]:
                rss_map[user] = None
                continue
            rss_map[user] = min(
                enumerate(options[user]),
                key=lambda item: (-gain_of(user, item[1]), item[0]),
            )[1]
        rss_active = tuple(sorted({v for v in rss_map.values() if v is not None}))
        # winners of smaller caps are feasible at every larger cap; carrying
        # them forward makes the boundary-0 selection nested (monotone) in C
        inherited: dict[str, dict] = {}

        for cap in caps:
            search = Boundary0Search(
                runner, tape, step_index, incumbent, run_setting, base,
                f"beamcount-c{cap:03d}",
            )
            starts: dict[str, dict] = {}
            sets_by_rule: dict[str, tuple] = {}
            for set_name, key in beam_set_rules.items():
                beams = matroid_extension(options, cover, key, cap, rank)
                sets_by_rule[set_name] = beams
                for assign_name, mapping in (
                    ("A1_coverage_first", assignment_coverage_first(options, beams)),
                    ("A2_max_nominal_gain", assignment_max_gain(options, beams, gain_of)),
                    ("A3_least_loaded", assignment_least_loaded(options, beams)),
                ):
                    starts[f"{set_name}|{assign_name}"] = {
                        "beams": beams, "mapping": mapping,
                    }
            declared_names = tuple(starts)
            for name, row in inherited.items():
                starts[name] = dict(row)
            if len(rss_active) <= cap:
                starts["RSS_MAX_within_cap"] = {"beams": rss_active, "mapping": dict(rss_map)}
            # one evaluate_many holding BASE and every start for this cap
            start_cfgs = {}
            for name, row in starts.items():
                start_cfgs[name] = search.make(row["mapping"])
            search.submit([base] + list(start_cfgs.values()))
            base_profile = search.read(base)
            base_guard = (
                0 if base_profile is None else Boundary0Search.score(base_profile)[1]
            )
            # every declared rule is carried to the full-48 endpoint batch, so
            # the cap curve does not depend on boundary-0 as a selector
            for name in declared_names:
                endpoint_jobs.append(
                    (f"CAP_{cap:03d}__{name}", start_cfgs[name], starts[name]["mapping"])
                )
            ranked = []
            for name, cfg in start_cfgs.items():
                profile = search.read(cfg)
                if profile is None:
                    continue
                ee, served = Boundary0Search.score(profile)
                ranked.append((ee, served, name))
                starts[name]["boundary0_ee"] = ee
                starts[name]["boundary0_served"] = served
            if not ranked:
                raise RuntimeError(f"no valid start for cap {cap} at {anchor_id}")
            ranked.sort(key=lambda r: (-r[0], r[2]))
            polished = []
            for _, _, name in ranked[:2]:
                row = starts[name]
                result = search.run(
                    row["mapping"], options, frozenset(row["beams"]), CAPPED_PASSES
                )
                if result is None:
                    continue
                m, cfg, ee, served, moves, passes = result
                polished.append({
                    "start": name, "beams": row["beams"], "mapping": m, "config": cfg,
                    "boundary0_ee": ee, "boundary0_served": served,
                    "moves": moves, "passes": passes,
                })
            if not polished:
                raise RuntimeError(f"no polished candidate for cap {cap} at {anchor_id}")
            # winner: greatest boundary-0 EE among every start and polished
            # point in this evaluator that meets the carrier-BASE served guard
            pool_rows = list(polished) + [
                {"start": name, "beams": row["beams"], "mapping": row["mapping"],
                 "config": start_cfgs[name], "boundary0_ee": row["boundary0_ee"],
                 "boundary0_served": row["boundary0_served"], "moves": 0, "passes": 0}
                for name, row in starts.items() if "boundary0_ee" in row
            ]
            guarded = [r for r in pool_rows if r["boundary0_served"] >= base_guard]
            chosen_from = guarded if guarded else pool_rows
            chosen_from.sort(key=lambda r: (-r["boundary0_ee"], r["config"].configuration_id))
            winner = chosen_from[0]
            inherited[f"INHERITED_CAP_{cap:03d}_WINNER"] = {
                "beams": tuple(sorted({v for v in winner["mapping"].values() if v is not None})),
                "mapping": dict(winner["mapping"]),
            }
            realised_active = len({v for v in winner["mapping"].values() if v is not None})
            if realised_active > cap:
                raise RuntimeError("cap violated by winning assignment")
            label = f"CAP_{cap:03d}"
            search_detail[label] = {
                "cap": cap,
                "beam_set_sizes": {k: len(v) for k, v in sets_by_rule.items()},
                "starts_boundary0": {
                    n: {"ee_bit_per_j": r.get("boundary0_ee"),
                        "served_phy": r.get("boundary0_served")}
                    for n, r in starts.items()
                },
                "polished": [
                    {"start": r["start"], "boundary0_ee_bit_per_j": r["boundary0_ee"],
                     "boundary0_served_phy": r["boundary0_served"],
                     "moves": r["moves"], "passes": r["passes"]} for r in polished
                ],
                "winner_start": winner["start"],
                "winner_boundary0_ee_bit_per_j": winner["boundary0_ee"],
                "winner_boundary0_served_phy": winner["boundary0_served"],
                "base_served_guard_boundary0": base_guard,
                "guard_satisfied": bool(guarded),
                "winner_realised_active_beams": realised_active,
                "boundary0_configurations_submitted": search.submitted,
            }
            endpoint_jobs.append((label, winner["config"], winner["mapping"]))
            anchor_sets = winning_sets.setdefault(anchor_id, {})
            anchor_sets[label] = winner["beams"]
            for name, row in starts.items():
                anchor_sets[f"CAP_{cap:03d}__{name}"] = row["beams"]
            cap_rows[label] = {"cap": cap}
            search.close()
            check_runtime()

        # ---- uncapped: natural seeds (BASE, RSS_MAX) and best-known --------
        rss_map = {}
        for user in sorted(options):
            if not options[user]:
                rss_map[user] = None
                continue
            rss_map[user] = min(
                enumerate(options[user]),
                key=lambda item: (-gain_of(user, item[1]), item[0]),
            )[1]
        rss_cfg_kind = "cleanpath-rss-max"
        rss_config = runner._configuration(base, rss_map, kind=rss_cfg_kind)

        search = Boundary0Search(
            runner, tape, step_index, incumbent, run_setting, base, "beamcount-uncapped",
        )
        natural = []
        for seed_name, seed_map in (
            ("BASE", dict(base.mapping)), ("RSS_MAX", dict(rss_map)),
        ):
            result = search.run(seed_map, options, None, UNCAPPED_PASSES)
            if result is None:
                continue
            m, cfg, ee, served, moves, passes = result
            natural.append({
                "seed": seed_name, "mapping": m, "config": cfg,
                "boundary0_ee": ee, "boundary0_served": served,
                "moves": moves, "passes": passes,
            })
        natural.sort(key=lambda r: (-r["boundary0_ee"], r["config"].configuration_id))
        uncapped_natural = natural[0]
        search_detail["UNCAPPED_NATURAL_SEEDS"] = {
            "cap": None,
            "seeds": [
                {"seed": r["seed"], "boundary0_ee_bit_per_j": r["boundary0_ee"],
                 "boundary0_served_phy": r["boundary0_served"],
                 "moves": r["moves"], "passes": r["passes"]} for r in natural
            ],
            "winner_seed": uncapped_natural["seed"],
            "winner_realised_active_beams": len(
                {v for v in uncapped_natural["mapping"].values() if v is not None}),
            "boundary0_configurations_submitted": search.submitted,
        }
        endpoint_jobs.append(
            ("UNCAPPED_NATURAL", uncapped_natural["config"], uncapped_natural["mapping"])
        )
        search.close()
        check_runtime()

        # best-known unconstrained: unrestricted search seeded from the best
        # capped winner (a constrained optimum is a feasible unconstrained point)
        best_capped = max(
            (row for row in search_detail.values() if row["cap"] is not None),
            key=lambda r: max(p["boundary0_ee_bit_per_j"] for p in r["polished"]),
        )
        best_capped_label = f"CAP_{best_capped['cap']:03d}"
        best_capped_mapping = next(
            m for label, _, m in endpoint_jobs if label == best_capped_label
        )
        search = Boundary0Search(
            runner, tape, step_index, incumbent, run_setting, base,
            "beamcount-uncapped-best",
        )
        result = search.run(dict(best_capped_mapping), options, None, UNCAPPED_PASSES)
        if result is None:
            raise RuntimeError("best-known unconstrained search failed")
        m, cfg, ee, served, moves, passes = result
        # best known unconstrained point = argmax over both unconstrained runs
        capped_seeded = {
            "source": f"seeded_from_{best_capped_label}", "mapping": m, "config": cfg,
            "boundary0_ee": ee, "boundary0_served": served,
            "moves": moves, "passes": passes,
        }
        natural_best = dict(uncapped_natural)
        natural_best["source"] = f"seeded_from_{uncapped_natural['seed']}"
        best_known = max(
            (capped_seeded, natural_best),
            key=lambda r: (r["boundary0_ee"], r["config"].configuration_id),
        )
        search_detail["UNCAPPED_BEST_KNOWN"] = {
            "cap": None,
            "candidates": [
                {"source": r["source"], "boundary0_ee_bit_per_j": r["boundary0_ee"],
                 "boundary0_served_phy": r["boundary0_served"],
                 "moves": r["moves"], "passes": r["passes"]}
                for r in (natural_best, capped_seeded)
            ],
            "winner_source": best_known["source"],
            "boundary0_ee_bit_per_j": best_known["boundary0_ee"],
            "boundary0_served_phy": best_known["boundary0_served"],
            "winner_realised_active_beams": len(
                {v for v in best_known["mapping"].values() if v is not None}),
            "boundary0_configurations_submitted": search.submitted,
        }
        endpoint_jobs.append(
            ("UNCAPPED_BEST_KNOWN", best_known["config"], best_known["mapping"])
        )
        search.close()
        check_runtime()

        # ---- per-satellite active-beam caps (the sibling's actual object) --
        for per_sat_cap, row in sorted(state["persat"].items()):
            cover_set = row["cover"]
            if cover_set is None:
                search_detail[f"PERSAT_{per_sat_cap}"] = {
                    "cap": None, "per_satellite_cap": per_sat_cap,
                    "status": row["exact_status"], "evaluated": False,
                }
                continue
            for assign_name, mapping in (
                ("A1_coverage_first", assignment_coverage_first(options, cover_set)),
                ("A2_max_nominal_gain", assignment_max_gain(options, cover_set, gain_of)),
                ("A3_least_loaded", assignment_least_loaded(options, cover_set)),
            ):
                cfg = runner._configuration(
                    base, mapping, kind=f"beamcount-persat{per_sat_cap}-{assign_name}"
                )
                endpoint_jobs.append(
                    (f"PERSAT_{per_sat_cap}__{assign_name}", cfg, mapping)
                )
                winning_sets.setdefault(anchor_id, {})[
                    f"PERSAT_{per_sat_cap}__{assign_name}"] = cover_set
            search_detail[f"PERSAT_{per_sat_cap}"] = {
                "cap": None, "per_satellite_cap": per_sat_cap,
                "status": row["exact_status"], "evaluated": True,
                "cover_size": len(cover_set),
                "cover_beams_per_satellite": row["cover_beams_per_satellite"],
            }

        # ---- parity configurations ----------------------------------------
        crowded_map = assignment_coverage_first(options, cover)
        crowded_config = runner._configuration(
            base, crowded_map, kind="crowding-cost-ladder"
        )
        endpoint_jobs.append(("PARITY_CROWDED_MIN_COVER", crowded_config, crowded_map))
        endpoint_jobs.append(("PARITY_RSS_MAX", rss_config, dict(rss_map)))
        endpoint_jobs.append(("BASE_CARRIER", base, dict(base.mapping)))

        # ---- one fresh full-48 realised evaluator, one evaluate_many -------
        endpoint_evaluator = runner.StepEvaluator(
            tape, runner._setting("a-r0"), step_index,
            transition_from=incumbent,
            cell_rekeyed_users=runner._rekeyed_users(tape, step_index),
            field="realised", counter=runner.EvaluationCounter(),
            run_setting=run_setting, boundary_indices=tuple(range(48)),
        )
        endpoint_evaluator.evaluate_many([cfg for _, cfg, _ in endpoint_jobs])
        endpoints = {}
        for label, cfg, mapping in endpoint_jobs:
            profile = endpoint_evaluator._evaluated.get(cfg.configuration_id)
            if profile is None:
                raise RuntimeError(f"endpoint config invalid: {label} at {anchor_id}")
            endpoints[label] = endpoint_metrics(profile, mapping)
        del endpoint_evaluator
        gc.collect()

        anchor_rows.append({
            "anchor_index": position - 1, "anchor_id": anchor_id,
            "step_index": step_index, "carrier": carrier,
            "floor": len(cover),
            "base_served_phy_guard": endpoints["BASE_CARRIER"]["served_phy"],
            "search": search_detail,
            "endpoints": endpoints,
            "anchor_seconds": time.perf_counter() - anchor_started,
            "peak_rss_bytes": peak_rss_bytes(),
        })
        payload["anchors"] = anchor_rows
        atomic_write(PARTIAL, dict(payload, status="PARTIAL"))
        check_runtime()
        print(
            f"anchor {position}/{len(panel)} k/N done {anchor_id} "
            f"{time.perf_counter()-anchor_started:.1f}s peak RSS "
            f"{peak_rss_bytes()/2**30:.3f} GiB "
            + json.dumps({
                lbl: round(endpoints[lbl]["ee_bit_per_j"] / 1e6, 4)
                for lbl in sorted(endpoints)
            }, sort_keys=True),
            flush=True,
        )

    if MODE == "sweep":
        payload["anchors"] = anchor_rows
        payload["winning_sets"] = {
            anchor_id: {label: [list(b) for b in beams] for label, beams in sets.items()}
            for anchor_id, sets in winning_sets.items()
        }
        payload["scalar_evaluate_calls"] = SCALAR_EVALUATE_CALLS
        assert SCALAR_EVALUATE_CALLS == 0
        payload["scalar_evaluate_assertion"] = "PASS: zero scalar StepEvaluator.evaluate calls"
        payload["status"] = "COMPLETE"
        payload["runtime"]["peak_rss_bytes"] = peak_rss_bytes()
        payload["runtime"]["wall_seconds"] = time.perf_counter() - started
        payload["runner_sha256"] = sha256_file(Path(__file__))
        atomic_write(OUTPUT, payload)
        check_runtime()
        print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB final ({peak_rss_bytes()} bytes)", flush=True)
        print(f"scalar_evaluate_calls={SCALAR_EVALUATE_CALLS}", flush=True)
        print("SHARD COMPLETE " + str(OUTPUT), flush=True)
        return 0

    # ---- pooled sweep ------------------------------------------------------
    labels = sorted({lbl for row in anchor_rows for lbl in row["endpoints"]})
    labels = [
        lbl for lbl in labels
        if all(lbl in row["endpoints"] for row in anchor_rows)
    ]
    pooled = {lbl: pool([row["endpoints"][lbl] for row in anchor_rows]) for lbl in labels}

    def label_cap(lbl):
        if lbl.startswith("CAP_"):
            return int(lbl.split("__")[0].removeprefix("CAP_"))
        return None

    def label_persat(lbl):
        if lbl.startswith("PERSAT_"):
            return int(lbl.split("__")[0].removeprefix("PERSAT_"))
        return None

    for lbl in labels:
        pooled[lbl]["cap"] = label_cap(lbl)
        pooled[lbl]["per_satellite_cap"] = label_persat(lbl)
        pooled[lbl]["rule"] = lbl.split("__")[1] if "__" in lbl else None
    payload["pooled"] = pooled

    # parity
    parity = {
        "rss_max": {
            "target_mbit_per_j": PARITY_RSS_MAX_MBIT_J,
            "measured_mbit_per_j": pooled["PARITY_RSS_MAX"]["ee_mbit_per_j"],
            "delta_mbit_per_j": pooled["PARITY_RSS_MAX"]["ee_mbit_per_j"] - PARITY_RSS_MAX_MBIT_J,
            "matches_to_6dp": round(pooled["PARITY_RSS_MAX"]["ee_mbit_per_j"], 6) == PARITY_RSS_MAX_MBIT_J,
        },
        "crowded_endpoint": {
            "target_bit_per_j": PARITY_CROWDED_BIT_J,
            "measured_bit_per_j": pooled["PARITY_CROWDED_MIN_COVER"]["ee_bit_per_j"],
            "delta_bit_per_j": pooled["PARITY_CROWDED_MIN_COVER"]["ee_bit_per_j"] - PARITY_CROWDED_BIT_J,
            "matches_to_6dp": round(pooled["PARITY_CROWDED_MIN_COVER"]["ee_bit_per_j"], 6) == PARITY_CROWDED_BIT_J,
            "served_phy": pooled["PARITY_CROWDED_MIN_COVER"]["served_phy"],
            "active_beams_mapping_mean": pooled["PARITY_CROWDED_MIN_COVER"]["active_beams_mapping_mean"],
        },
    }
    payload["parity"] = parity
    print("PARITY " + json.dumps(parity, sort_keys=True), flush=True)

    # per-cap frontier: best pooled EE over every declared arm at that cap
    cap_frontier = {}
    for cap in caps:
        members = [lbl for lbl in labels if label_cap(lbl) == cap]
        winner = max(members, key=lambda lbl: (
            pooled[lbl]["ee_bit_per_j"], lbl))
        cap_frontier[str(cap)] = {
            "cap": cap,
            "best_label": winner,
            "best_pooled_ee_bit_per_j": pooled[winner]["ee_bit_per_j"],
            "best_pooled_ee_mbit_per_j": pooled[winner]["ee_mbit_per_j"],
            "served_phy": pooled[winner]["served_phy"],
            "user_count": pooled[winner]["user_count"],
            "rate_target_attained": pooled[winner]["rate_target_attained"],
            "modal_frac": pooled[winner]["modal_frac"],
            "realised_active_beams_mean": pooled[winner]["active_beams_mapping_mean"],
            "mean_radiating_beams_mean": pooled[winner]["mean_radiating_beams_mean"],
            "members": {
                lbl: {
                    "ee_mbit_per_j": pooled[lbl]["ee_mbit_per_j"],
                    "served_phy": pooled[lbl]["served_phy"],
                    "rate_target_attained": pooled[lbl]["rate_target_attained"],
                    "active_beams_mapping_mean": pooled[lbl]["active_beams_mapping_mean"],
                } for lbl in sorted(members)
            },
        }
    payload["cap_frontier"] = cap_frontier

    persat_frontier = {}
    for per_sat_cap in PER_SATELLITE_CAPS:
        members = [lbl for lbl in labels if label_persat(lbl) == per_sat_cap]
        if not members:
            persat_frontier[str(per_sat_cap)] = {
                "per_satellite_cap": per_sat_cap, "evaluated": False,
            }
            continue
        winner = max(members, key=lambda lbl: (pooled[lbl]["ee_bit_per_j"], lbl))
        persat_frontier[str(per_sat_cap)] = {
            "per_satellite_cap": per_sat_cap, "evaluated": True,
            "best_label": winner,
            "best_pooled_ee_mbit_per_j": pooled[winner]["ee_mbit_per_j"],
            "served_phy": pooled[winner]["served_phy"],
            "rate_target_attained": pooled[winner]["rate_target_attained"],
            "realised_active_beams_mean": pooled[winner]["active_beams_mapping_mean"],
            "members": {
                lbl: {
                    "ee_mbit_per_j": pooled[lbl]["ee_mbit_per_j"],
                    "served_phy": pooled[lbl]["served_phy"],
                    "rate_target_attained": pooled[lbl]["rate_target_attained"],
                } for lbl in sorted(members)
            },
        }
    payload["per_satellite_frontier"] = persat_frontier

    best_cap = max(caps, key=lambda c: cap_frontier[str(c)]["best_pooled_ee_bit_per_j"])
    best_cap_label = cap_frontier[str(best_cap)]["best_label"]
    payload["ee_optimal_cap"] = {
        "label": best_cap_label, "cap": best_cap,
        "pooled_ee_bit_per_j": pooled[best_cap_label]["ee_bit_per_j"],
        "pooled_ee_mbit_per_j": pooled[best_cap_label]["ee_mbit_per_j"],
        "served_phy": pooled[best_cap_label]["served_phy"],
        "user_count": pooled[best_cap_label]["user_count"],
        "rate_target_attained": pooled[best_cap_label]["rate_target_attained"],
        "realised_active_beams_mean": pooled[best_cap_label]["active_beams_mapping_mean"],
        "uncapped_best_known_ee_mbit_per_j": pooled["UNCAPPED_BEST_KNOWN"]["ee_mbit_per_j"],
        "uncapped_natural_ee_mbit_per_j": pooled["UNCAPPED_NATURAL"]["ee_mbit_per_j"],
        "uncapped_natural_active_beams_mean": pooled["UNCAPPED_NATURAL"]["active_beams_mapping_mean"],
    }
    print(f"EE-optimal cap C={best_cap} via {best_cap_label} -> "
          f"{pooled[best_cap_label]['ee_mbit_per_j']:.6f} Mbit/J", flush=True)
    print("CAP FRONTIER " + json.dumps({
        c: round(cap_frontier[c]["best_pooled_ee_mbit_per_j"], 6) for c in cap_frontier
    }, sort_keys=True), flush=True)
    atomic_write(PARTIAL, dict(payload, status="PARTIAL"))

    # ---------------------------------------------------------------- pass 2
    projection_rows: list[dict] = []
    for position, (step_index, carrier) in enumerate(panel, 1):
        anchor_id = f"{tape.domain}|{step_index}|{carrier}"
        state = steps[step_index]
        options, gain_of = state["options"], state["gain_of"]
        base = runner._base_configuration(tape, step_index, carrier)
        incumbent = runner._base_configuration(tape, max(0, step_index - 1), carrier)
        targets = {
            cap: frozenset(tuple(b) for b in winning_sets[anchor_id][f"CAP_{cap:03d}"])
            for cap in caps
        }
        target = frozenset(tuple(b) for b in winning_sets[anchor_id][best_cap_label])

        def project(mapping, target):
            out, kept, moved, rescued = {}, 0, 0, 0
            for user in sorted(options):
                choice = mapping.get(user)
                if choice is not None and choice in target:
                    out[user] = choice
                    kept += 1
                    continue
                inside = [b for b in options[user] if b in target]
                if not inside:
                    out[user] = None
                    continue
                out[user] = min(
                    enumerate(inside),
                    key=lambda item: (-gain_of(user, item[1]), item[0]),
                )[1]
                if choice is None:
                    rescued += 1
                else:
                    moved += 1
            return out, kept, moved, rescued

        def project_own_footprint(mapping, cap):
            """Squeeze the policy onto at most `cap` beams drawn only from
            its own active footprint, most-occupied first, then move stranded
            users to the best in-footprint legal kept beam."""
            counts = Counter(v for v in mapping.values() if v is not None)
            ordered = sorted(counts, key=lambda b: (-counts[b], b))
            kept_set = set(ordered[:cap])
            stranded = [
                u for u in sorted(options)
                if not [b for b in options[u] if b in kept_set]
            ]
            covers_all = not stranded
            out = {}
            for user in sorted(options):
                choice = mapping.get(user)
                if choice is not None and choice in kept_set:
                    out[user] = choice
                    continue
                inside = [b for b in options[user] if b in kept_set]
                out[user] = None if not inside else min(
                    enumerate(inside),
                    key=lambda item: (-gain_of(user, item[1]), item[0]),
                )[1]
            return out, covers_all, len(stranded)

        rss_map = {}
        for user in sorted(options):
            rss_map[user] = None if not options[user] else min(
                enumerate(options[user]),
                key=lambda item: (-gain_of(user, item[1]), item[0]),
            )[1]

        jobs: list[tuple[str, object, dict, dict]] = []

        def add(label, mapping, kind, extra):
            cfg = runner._configuration(base, mapping, kind=kind)
            jobs.append((label, cfg, dict(mapping), extra))

        policies = [("RSS_MAX", dict(rss_map), {})] + [
            (f"A0_SEED_{row['seed']}", dict(a0[row["seed"]][anchor_id]), {"seed": row["seed"]})
            for row in checkpoint_index
        ]
        for name, mapping, extra in policies:
            add(name, mapping, f"beamcount-{name.lower()}", extra)
            for cap in caps:
                pr, kept, moved, rescued = project(mapping, targets[cap])
                add(f"{name}_PROJECTED_C{cap:03d}", pr,
                    f"beamcount-proj-c{cap:03d}-{name.lower()}",
                    {**extra, "cap": cap, "kept": kept, "moved": moved,
                     "rescued_from_null": rescued})
                own, covers_all, stranded = project_own_footprint(mapping, cap)
                add(f"{name}_OWN_FOOTPRINT_C{cap:03d}", own,
                    f"beamcount-own-c{cap:03d}-{name.lower()}",
                    {**extra, "cap": cap, "own_footprint_covers_all_users": covers_all,
                     "stranded_users": stranded})

        evaluator = runner.StepEvaluator(
            tape, runner._setting("a-r0"), step_index,
            transition_from=incumbent,
            cell_rekeyed_users=runner._rekeyed_users(tape, step_index),
            field="realised", counter=runner.EvaluationCounter(),
            run_setting=run_setting, boundary_indices=tuple(range(48)),
        )
        evaluator.evaluate_many([cfg for _, cfg, _, _ in jobs])
        rows = {}
        for label, cfg, mapping, extra in jobs:
            profile = evaluator._evaluated.get(cfg.configuration_id)
            if profile is None:
                raise RuntimeError(f"projection config invalid: {label} at {anchor_id}")
            rows[label] = {**endpoint_metrics(profile, mapping), **extra}
        del evaluator
        gc.collect()
        projection_rows.append({
            "anchor_id": anchor_id, "target_cap": best_cap,
            "target_beam_set": sorted(list(b) for b in target),
            "rows": rows,
        })
        check_runtime()
        print(f"projection anchor {position}/{len(panel)} k/N done {anchor_id} "
              f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB", flush=True)

    projection_labels = sorted({lbl for r in projection_rows for lbl in r["rows"]})
    projection_pooled = {
        lbl: pool([r["rows"][lbl] for r in projection_rows])
        for lbl in projection_labels
    }
    seeds = [row["seed"] for row in checkpoint_index]
    families = [("A0_ALL_SEEDS", "")]
    for cap in caps:
        families += [
            (f"A0_ALL_SEEDS_PROJECTED_C{cap:03d}", f"_PROJECTED_C{cap:03d}"),
            (f"A0_ALL_SEEDS_OWN_FOOTPRINT_C{cap:03d}", f"_OWN_FOOTPRINT_C{cap:03d}"),
        ]
    for family, suffix in families:
        collected = [
            r["rows"][f"A0_SEED_{seed}{suffix}"]
            for r in projection_rows for seed in seeds
        ]
        projection_pooled[family] = pool(collected)
    # aliases at the EE-optimal cap
    for base_name in ("RSS_MAX", "A0_ALL_SEEDS"):
        for kind in ("PROJECTED", "OWN_FOOTPRINT"):
            projection_pooled[f"{base_name}_{kind}"] = projection_pooled[
                f"{base_name}_{kind}_C{best_cap:03d}"]
    for seed in seeds:
        for kind in ("PROJECTED", "OWN_FOOTPRINT"):
            projection_pooled[f"A0_SEED_{seed}_{kind}"] = projection_pooled[
                f"A0_SEED_{seed}_{kind}_C{best_cap:03d}"]
    for r in projection_rows:
        for name in ["RSS_MAX"] + [f"A0_SEED_{seed}" for seed in seeds]:
            for kind in ("PROJECTED", "OWN_FOOTPRINT"):
                r["rows"][f"{name}_{kind}"] = r["rows"][f"{name}_{kind}_C{best_cap:03d}"]
    payload["projection"] = {
        "target_cap": best_cap,
        "target_label": best_cap_label,
        "projection_rule": (
            "keep the policy's beam when it lies in the anchor's winning C*-beam set; "
            "otherwise move the user to the in-set legal beam of greatest boundary-0 "
            "nominal gain; null choices are rescued the same way"
        ),
        "own_footprint_rule": (
            "keep the C* most-occupied beams of the policy's own active footprint, "
            "then move every other user to its best legal kept beam; users with no "
            "legal kept beam become null"
        ),
        "pooled": projection_pooled,
        "anchors": projection_rows,
    }

    # cross-pass consistency: the same RSS_MAX configuration scored in two
    # different fresh full-48 evaluators, in batches of different composition
    payload["cross_pass_rss_max_consistency"] = {
        "pass1_pooled_ee_bit_per_j": pooled["PARITY_RSS_MAX"]["ee_bit_per_j"],
        "pass2_pooled_ee_bit_per_j": projection_pooled["RSS_MAX"]["ee_bit_per_j"],
        "absolute_difference_bit_per_j": abs(
            pooled["PARITY_RSS_MAX"]["ee_bit_per_j"]
            - projection_pooled["RSS_MAX"]["ee_bit_per_j"]
        ),
        "identical": (
            pooled["PARITY_RSS_MAX"]["ee_bit_per_j"]
            == projection_pooled["RSS_MAX"]["ee_bit_per_j"]
        ),
    }

    payload["scalar_evaluate_calls"] = SCALAR_EVALUATE_CALLS
    assert SCALAR_EVALUATE_CALLS == 0
    payload["scalar_evaluate_assertion"] = "PASS: zero scalar StepEvaluator.evaluate calls"
    payload["status"] = "COMPLETE"
    payload["runtime"]["peak_rss_bytes"] = peak_rss_bytes()
    payload["runtime"]["wall_seconds"] = time.perf_counter() - started
    payload["runner_sha256"] = sha256_file(Path(__file__))
    atomic_write(OUTPUT, payload)
    check_runtime()
    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB final ({peak_rss_bytes()} bytes)", flush=True)
    print(f"scalar_evaluate_calls={SCALAR_EVALUATE_CALLS}", flush=True)
    print("COMPLETE " + str(OUTPUT), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
