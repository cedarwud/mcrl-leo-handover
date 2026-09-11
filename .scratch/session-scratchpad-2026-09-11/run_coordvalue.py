#!/usr/bin/env python3
"""COORDVALUE learner-free EE barrier diagnostic.

Candidate performance is compared only on one fresh realised dense boundary-0
StepEvaluator per anchor.  BASE enters the first evaluate_many call alongside
candidates.  Scalar StepEvaluator.evaluate is replaced by a raising stub.
Endpoint parity is established first in a separate fresh realised dense full-48
batch per anchor.  No learner or checkpoint is imported or read.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
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


WORKSPACE = Path("/home/sat/mcrl-v025-coord-ws")
PANEL_RUNNER = Path("/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/run_panelceil.py")
CROWD_RUNNER = Path("/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run_crowding_cost.py")
CLEAN_RECEIPT = Path("/home/sat/mcrl-v025-rank2-ws/.scratch/cleanpath/cleanpath-receipt.json")
BASIN_RECEIPT = Path("/home/sat/mcrl-v025-basin-ws/.scratch/basin2/basin2-receipt.json")
CALIBRATION_PATH = Path("/home/sat/mcrl-v025-c1c2suff-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/PILOT_NOT_CLAIM-calibration.json")
OUTPUT = WORKSPACE / ".scratch/coordvalue/coordvalue-receipt.json"
CANDIDATES = WORKSPACE / ".scratch/coordvalue/candidates.jsonl"
PYTHON = "/home/sat/mcrl-leo-handover/.venv/bin/python"
THREAD_VARS = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
MAX_RSS_BYTES = 5_000_000_000
EVAL_BATCH = 32
SAMPLE_BUDGET = 128
K_VALUES = (1, 2, 3, 4, 6, 8)
RANDOM_SEED = 20260910
EXPECTED_ENDPOINT_EE = {
    "RSS_MAX": 41.621560,
    "CROWDED": 46.110374,
}
SCALAR_EVALUATE_CALLS = 0


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


def atomic_write(payload: dict) -> None:
    payload["receipt_sha256"] = canonical_digest(payload)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_name(f".{OUTPUT.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(OUTPUT)


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def check_runtime() -> None:
    if sys.executable != PYTHON:
        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        raise RuntimeError("niceness is below 15")
    bad = {name: os.environ.get(name) for name in THREAD_VARS if os.environ.get(name) != "1"}
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
        global SCALAR_EVALUATE_CALLS
        SCALAR_EVALUATE_CALLS += 1
        raise AssertionError("scalar StepEvaluator.evaluate is forbidden on COORDVALUE surfaces")

    forbidden.__name__ = "scalar_evaluate_forbidden_on_coordvalue"
    forbidden.__wrapped__ = original
    runner.StepEvaluator.evaluate = forbidden
    assert runner.StepEvaluator.evaluate is forbidden


def fresh_evaluator(runner, tape, step_index, incumbent, run_setting, field, boundaries):
    if tape.steps[step_index].arrays is None:
        raise AssertionError("dense primitive arrays are required")
    evaluator = runner.StepEvaluator(
        tape, runner._setting("a-r0"), step_index,
        transition_from=incumbent,
        cell_rekeyed_users=runner._rekeyed_users(tape, step_index),
        field=field, counter=runner.EvaluationCounter(),
        run_setting=run_setting, boundary_indices=boundaries,
    )
    assert evaluator.boundary_indices == boundaries
    assert evaluator.field == field
    return evaluator


def dedupe(configs):
    return tuple({row.configuration_id: row for row in configs}.values())


def profile(evaluator, config):
    result = evaluator._evaluated.get(config.configuration_id)
    if result is None:
        raise RuntimeError(f"profile absent from dense cache: {config.configuration_id}")
    return result


def fraction_payload(value: Fraction) -> dict[str, object]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "rational": str(value),
        "float": float(value),
    }


def total_f(runner, calibration, incumbent, rekeys, config, evaluated) -> tuple[Fraction, Fraction, Fraction]:
    """Return F=B-etaE-Phi_cost, physical core, and positive Phi cost in bit units."""
    physical = runner._objective(evaluated, calibration)
    phi_preference = runner._phi_for(
        incumbent, config, cell_rekeyed_users=rekeys,
    )
    phi_cost_bits = -calibration.kappa_bits_per_user_step * phi_preference
    return physical - phi_cost_bits, physical, phi_cost_bits


def endpoint_row(panel, evaluated) -> dict[str, object]:
    row = panel.metric(evaluated)
    row["ee_mbit_per_j"] = row.pop("ee_bit_per_j") / 1e6
    return row


def rss_configuration(runner, tape, step_index: int, base):
    options, _ = runner._legal_options(tape, step_index)
    arrays = tape.steps[step_index].arrays
    if arrays is None:
        raise RuntimeError("frozen exact panel omitted primitive arrays")
    row_of = arrays._row_index()
    mapping = {}
    for user, identities in sorted(options.items()):
        if not identities:
            mapping[user] = None
            continue
        _ordinal, identity = min(
            enumerate(identities),
            key=lambda item: (-float(arrays.nominal_gain[0, row_of[(user, item[1])]]), item[0]),
        )
        mapping[user] = identity
    return runner._configuration(base, mapping, kind="coordvalue-rss-max")


def crowded_configuration(runner, crowd, base, options, beam_sets_cache, step_index):
    if step_index not in beam_sets_cache:
        beam_sets_cache[step_index] = crowd.nested_beam_sets(options)
    beams = beam_sets_cache[step_index][0]
    mapping = crowd.assignment_for_beams(options, beams)
    return runner._configuration(base, mapping, kind="coordvalue-crowded")


def changed_users(start, candidate) -> tuple[int, ...]:
    left, right = start.mapping, candidate.mapping
    return tuple(user for user in sorted(left) if left[user] != right[user])


def single_candidates(runner, base, start, options, start_name):
    rows = []
    mapping0 = start.mapping
    for user in sorted(mapping0):
        alternatives = [identity for identity in options[user] if identity != mapping0[user]]
        if mapping0[user] is not None:
            alternatives.append(None)
        for identity in alternatives:
            mapping = dict(mapping0)
            mapping[user] = identity
            row = runner._configuration(base, mapping, kind=f"coordvalue-{start_name}-k1")
            rows.append((row, (user,), ((user, identity),), "exhaustive-legal-plus-null"))
    return rows


def add_sample(samples, seen, runner, base, start, mapping, k, method):
    changed = tuple(user for user in sorted(mapping) if mapping[user] != start.mapping[user])
    if len(changed) != k:
        return False
    row = runner._configuration(base, mapping, kind=f"coordvalue-sampled-k{k}")
    if row.configuration_id in seen:
        return False
    seen.add(row.configuration_id)
    edits = tuple((user, mapping[user]) for user in changed)
    samples.append((row, changed, edits, method))
    return True


def sampled_candidates(runner, base, start, target, options, k, budget, seed, best_by_user,
                       forced_mappings=()):
    """Fixed-budget deterministic mixture; every returned profile has exactly k edits."""
    rng = random.Random(seed)
    samples = []
    seen = set()
    start_map = start.mapping
    users = tuple(sorted(start_map))

    # Deterministic prior catalogue witness/subsets are candidates, not accepted
    # evidence: they are rescored below on the same fresh realised EE surface.
    for mapping in forced_mappings:
        add_sample(
            samples, seen, runner, base, start, dict(mapping), k,
            "prior-basin2-catalogue-witness-or-subset",
        )

    # 1. Combine the best guarded one-user EE move for promising users.
    ranked = [user for user, _row in sorted(
        best_by_user.items(), key=lambda item: (-item[1]["delta_ee_mbit_per_j"], item[0])
    )]
    top = ranked[:min(32, len(ranked))]
    if len(top) >= k:
        combos = itertools.combinations(top, k)
        for members in itertools.islice(combos, budget // 4):
            mapping = dict(start_map)
            for user in members:
                mapping[user] = best_by_user[user]["identity"]
            add_sample(samples, seen, runner, base, start, mapping, k, "top-single-combination")

    # 2. Move subsets toward the opposite known-good endpoint.
    target_users = [user for user in users if target.mapping[user] != start_map[user]]
    attempts = 0
    target_goal = min(budget // 2, budget)
    while len(samples) < target_goal and len(target_users) >= k and attempts < budget * 20:
        attempts += 1
        members = tuple(sorted(rng.sample(target_users, k)))
        mapping = dict(start_map)
        for user in members:
            mapping[user] = target.mapping[user]
        add_sample(samples, seen, runner, base, start, mapping, k, "opposite-endpoint-subset")

    # 3. Concentrate k users on one common legal destination beam.
    beam_users = defaultdict(list)
    for user in users:
        for beam in options[user]:
            if beam != start_map[user]:
                beam_users[beam].append(user)
    eligible_beams = [beam for beam, members in sorted(beam_users.items()) if len(members) >= k]
    consolidation_goal = min(3 * budget // 4, budget)
    attempts = 0
    while len(samples) < consolidation_goal and eligible_beams and attempts < budget * 30:
        attempts += 1
        beam = eligible_beams[rng.randrange(len(eligible_beams))]
        members = tuple(sorted(rng.sample(beam_users[beam], k)))
        mapping = dict(start_map)
        for user in members:
            mapping[user] = beam
        add_sample(samples, seen, runner, base, start, mapping, k, "common-destination-consolidation")

    # 4. Uniform users and uniform legal non-incumbent identities; 5% include null edits.
    attempts = 0
    while len(samples) < budget and attempts < budget * 100:
        attempts += 1
        members = tuple(sorted(rng.sample(users, k)))
        mapping = dict(start_map)
        possible = True
        for user in members:
            alternatives = [identity for identity in options[user] if identity != start_map[user]]
            if start_map[user] is not None and rng.random() < 0.05:
                alternatives.append(None)
            if not alternatives:
                possible = False
                break
            mapping[user] = alternatives[rng.randrange(len(alternatives))]
        if possible:
            add_sample(samples, seen, runner, base, start, mapping, k, "uniform-legal-mixture")
    if len(samples) != budget:
        raise RuntimeError(f"could only construct {len(samples)}/{budget} unique k={k} samples")
    return samples


def catalogue_support_ids(runner, calibration, tape, step_index, geometric_base, start, run_setting):
    """Rebuild bounded-union-v2 support around start without scalar evaluate.

    The auxiliary nominal evaluator identifies the catalogue's sealed top-10
    rank only.  It does not score or select any COORDVALUE candidate.
    """
    options, census = runner._selection_shortlist(tape, step_index, run_setting=run_setting)
    users = tuple(sorted(start.mapping))
    base_map = start.mapping
    unilaterals = {user: [] for user in users}
    rows = [start]
    for user in users:
        for identity in options[user]:
            if identity == base_map[user]:
                continue
            mapping = dict(base_map)
            mapping[user] = identity
            row = runner._configuration(start, mapping, kind="unilateral")
            rows.append(row)
            unilaterals[user].append(row)

    nominal = fresh_evaluator(
        runner, tape, step_index, start, run_setting, "nominal", (0,),
    )
    first_call = dedupe((geometric_base, start, *rows[1:]))
    assert first_call[0].configuration_id == geometric_base.configuration_id
    assert len(first_call) > 2
    for offset in range(0, len(first_call), EVAL_BATCH):
        nominal.evaluate_many(first_call[offset:offset + EVAL_BATCH])
    start_profile = profile(nominal, start)
    best_surplus = {}
    for user in users:
        values = []
        for row in unilaterals[user]:
            p = profile(nominal, row)
            core = Fraction(str(p.bits - start_profile.bits)) - calibration.eta_ref * Fraction(
                str(p.joules - start_profile.joules)
            )
            core += calibration.kappa_bits_per_user_step * runner._phi_for(start, row)
            values.append(core)
        best_surplus[user] = max(values, default=Fraction(-10**30))
    ranked_users = sorted(users, key=lambda user: (-best_surplus[user], user))[:runner.PAIRWISE_TOP_K_USERS]

    for proposal_rank in range(runner.TOP_PROPOSALS):
        mapping = dict(base_map)
        for user in users:
            if len(unilaterals[user]) > proposal_rank:
                mapping[user] = unilaterals[user][proposal_rank].mapping[user]
        if mapping != base_map:
            rows.append(runner._configuration(start, mapping, kind="s0-top-two"))
    for first, second in itertools.combinations(ranked_users, 2):
        for first_row in unilaterals[first][:runner.TOP_PROPOSALS]:
            for second_row in unilaterals[second][:runner.TOP_PROPOSALS]:
                mapping = dict(base_map)
                mapping[first] = first_row.mapping[first]
                mapping[second] = second_row.mapping[second]
                rows.append(runner._configuration(start, mapping, kind="pairwise-top10-top2"))
    for beam in sorted({identity for identity in base_map.values() if identity is not None}):
        mapping = dict(base_map)
        affected = [user for user in users if base_map[user] == beam]
        for user in affected:
            mapping[user] = next((identity for identity in options[user] if identity != beam), None)
        if mapping != base_map:
            rows.append(runner._configuration(start, mapping, kind="beam-evacuation"))
    unique = {row.configuration_id: row for row in rows}
    histogram = Counter(len(changed_users(start, row)) for row in unique.values())
    result = {
        "ids": frozenset(unique),
        "count": len(unique),
        "size_histogram": dict(sorted(histogram.items())),
        "top10_users": ranked_users,
        "shortlist_census": census,
        "nominal_physical_boundary_evaluations": nominal.physical_evaluations,
    }
    del nominal
    gc.collect()
    return result


def classify_candidate(panel, runner, calibration, incumbent, rekeys,
                       selection_evaluator, endpoint_metrics,
                       start, start_selection_profile, start_f, start_ee, start_served,
                       config, members, edits, method, support_ids, k):
    selection_profile = profile(selection_evaluator, config)
    endpoint_profile = endpoint_metrics[config.configuration_id]
    candidate_f, physical_f, phi_cost = total_f(
        runner, calibration, incumbent, rekeys, config, selection_profile,
    )
    served = endpoint_profile["served"]
    ee = endpoint_profile["ee_mbit_per_j"]
    delta_ee = ee - start_ee
    delta_f = candidate_f - start_f
    guarded = served >= start_served
    ee_improves = guarded and delta_ee > 0.0
    f_improves = guarded and delta_f > 0
    return {
        "k": k,
        "configuration_id": config.configuration_id,
        "changed_users": list(members),
        "edits": [[user, None if identity is None else list(identity)] for user, identity in edits],
        "method": method,
        "bits": endpoint_profile["bits"],
        "joules": endpoint_profile["joules"],
        "endpoint_boundaries": 48,
        "selection_boundary0_bits": selection_profile.bits,
        "selection_boundary0_joules": selection_profile.joules,
        "ee_mbit_per_j": ee,
        "delta_ee_mbit_per_j": delta_ee,
        "f": fraction_payload(candidate_f),
        "physical_core_b_minus_eta_e": fraction_payload(physical_f),
        "phi_cost_bits": fraction_payload(phi_cost),
        "delta_f": fraction_payload(delta_f),
        "served": served,
        "start_served": start_served,
        "guarded": guarded,
        "service_dropping_ee_increase": served < start_served and delta_ee > 0.0,
        "ee_improves": ee_improves,
        "f_improves": f_improves,
        "ee_improves_f_decreases": ee_improves and delta_f < 0,
        "f_improves_ee_decreases": f_improves and delta_ee < 0.0,
        "inside_current_catalogue": config.configuration_id in support_ids,
    }


def compact_best(row):
    if row is None:
        return None
    return {key: row[key] for key in (
        "configuration_id", "changed_users", "edits", "method", "bits", "joules",
        "ee_mbit_per_j", "delta_ee_mbit_per_j", "delta_f", "served", "guarded",
        "ee_improves", "f_improves", "inside_current_catalogue",
    )}


def summarize_rows(rows, k, mode, budget, exhaustive, support_count):
    guarded = [row for row in rows if row["guarded"]]
    improving = [row for row in guarded if row["ee_improves"]]
    best_any = max(guarded, key=lambda row: (row["delta_ee_mbit_per_j"], row["configuration_id"]), default=None)
    best_improving = max(improving, key=lambda row: (row["delta_ee_mbit_per_j"], row["configuration_id"]), default=None)
    rejected = [row for row in improving if row["delta_f"]["numerator"] < 0]
    best_rejected = max(rejected, key=lambda row: (row["delta_ee_mbit_per_j"], row["configuration_id"]), default=None)
    return {
        "k": k,
        "search_mode": mode,
        "budget": budget,
        "exhaustive": exhaustive,
        "candidates_evaluated": len(rows),
        "guarded_candidates": len(guarded),
        "service_dropping_candidates": sum(not row["guarded"] for row in rows),
        "service_dropping_ee_increase_count": sum(row["service_dropping_ee_increase"] for row in rows),
        "ee_improving_count": len(improving),
        "ee_improves_f_decreases_count": sum(row["ee_improves_f_decreases"] for row in rows),
        "f_improves_ee_decreases_count": sum(row["f_improves_ee_decreases"] for row in rows),
        "improving_inside_current_catalogue_count": sum(row["inside_current_catalogue"] for row in improving),
        "improving_outside_current_catalogue_count": sum(not row["inside_current_catalogue"] for row in improving),
        "candidate_inside_current_catalogue_count": support_count,
        "best_guarded": compact_best(best_any),
        "best_improving": compact_best(best_improving),
        "best_ee_improvement_f_rejects": compact_best(best_rejected),
    }


def evaluate_rows(handle, anchor_index, anchor_id, start_name, rows, k,
                  selection_evaluator, endpoint_metrics,
                  panel, runner, calibration, incumbent, rekeys, start,
                  start_selection_profile, start_f, start_ee, start_served, support_ids,
                  first_prefix=()):
    output_rows = []
    first = True
    for offset in range(0, len(rows), EVAL_BATCH):
        chunk = rows[offset:offset + EVAL_BATCH]
        configs = [item[0] for item in chunk]
        if first and first_prefix:
            selection_evaluator.evaluate_many(dedupe((*first_prefix, *configs)))
        else:
            selection_evaluator.evaluate_many(configs)
        first = False
        for config, members, edits, method in chunk:
            row = classify_candidate(
                panel, runner, calibration, incumbent, rekeys, selection_evaluator,
                endpoint_metrics, start, start_selection_profile,
                start_f, start_ee, start_served,
                config, members, edits, method, support_ids, k,
            )
            handle.write(json.dumps({
                "anchor_index": anchor_index, "anchor_id": anchor_id,
                "start": start_name, **row,
            }, sort_keys=True, separators=(",", ":")) + "\n")
            output_rows.append(row)
        keep = {row.configuration_id for row in first_prefix}
        keep.update((start.configuration_id,))
        for config in configs:
            if config.configuration_id not in keep:
                selection_evaluator._evaluated.pop(config.configuration_id, None)
    return output_rows


def endpoint_candidate_metrics(panel, evaluator, rows, keep_ids, label):
    result = {}
    for offset in range(0, len(rows), EVAL_BATCH):
        chunk = rows[offset:offset + EVAL_BATCH]
        configs = [item[0] for item in chunk]
        evaluator.evaluate_many(configs)
        for config in configs:
            p = profile(evaluator, config)
            result[config.configuration_id] = {
                "bits": p.bits,
                "joules": p.joules,
                "ee_mbit_per_j": p.bits / p.joules / 1e6,
                "served": panel.served(p),
            }
        for config in configs:
            if config.configuration_id not in keep_ids:
                evaluator._evaluated.pop(config.configuration_id, None)
        completed = min(offset + len(chunk), len(rows))
        if completed == len(rows) or completed % 256 == 0:
            print(
                f"endpoint {label} {completed}/{len(rows)} peak RSS "
                f"{peak_rss_bytes()/2**30:.3f} GiB",
                flush=True,
            )
    return result


def pool_endpoints(endpoint_anchors, name):
    rows = [anchor[name] for anchor in endpoint_anchors]
    bits = math.fsum(row["bits"] for row in rows)
    joules = math.fsum(row["joules"] for row in rows)
    return {
        "bits": bits, "joules": joules,
        "ee_mbit_per_j": bits / joules / 1e6,
        "served": sum(row["served_count"] for row in rows),
        "users": sum(row["user_count"] for row in rows),
    }


def main() -> int:
    check_runtime()
    started = time.perf_counter()
    panel = load_module("coordvalue_panel", PANEL_RUNNER)
    crowd = load_module("coordvalue_crowd", CROWD_RUNNER)
    clean = json.loads(CLEAN_RECEIPT.read_text(encoding="utf-8"))
    basin = json.loads(BASIN_RECEIPT.read_text(encoding="utf-8"))
    frozen = clean.get("panel", [])
    if clean.get("status") != "COMPLETE" or len(frozen) != 12:
        raise RuntimeError("frozen 12-anchor development panel unavailable")
    if basin.get("status") != "COMPLETE" or len(basin.get("anchors", [])) != 12:
        raise RuntimeError("BASIN2 deterministic seed receipt unavailable")
    pilot = panel.load_pilot()
    runner = pilot.ENGINE
    calibration = panel.load_calibration(pilot)
    run_setting = runner.run_setting_for("a-r0")
    forbid_scalar_evaluate(runner)
    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape

    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB before tape", flush=True)
    tape = build_world_tape(
        domain=pilot.TRAIN_WORLDS[0], provider=LegacyWorldProvider(role="pilot-source"),
        steps=33, start_time_s=0.0,
    )
    check_runtime()
    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB after tape", flush=True)

    # Physical profiles depend on step and mapping, not carrier.  Use one
    # full-48 endpoint evaluator per step, while retaining three distinct
    # carrier/transition selection surfaces for F and Phi below.
    beam_sets_cache = {}
    endpoint_anchors = []
    groups = []
    parity_position = 0
    for step_index in range(4):
        panel_rows = [row for row in frozen if int(row["step_index"]) == step_index]
        if len(panel_rows) != 3:
            raise RuntimeError(f"step {step_index} does not have three frozen carrier anchors")
        options, _ = runner._legal_options(tape, step_index)
        anchor_rows = []
        for panel_row in panel_rows:
            carrier = str(panel_row["carrier"])
            base = runner._base_configuration(tape, step_index, carrier)
            incumbent = runner._base_configuration(tape, max(0, step_index - 1), carrier)
            anchor_rows.append({"panel_row": panel_row, "base": base, "incumbent": incumbent})
        representative_base = anchor_rows[0]["base"]
        rss = rss_configuration(runner, tape, step_index, representative_base)
        crowded = crowded_configuration(
            runner, crowd, representative_base, options, beam_sets_cache, step_index,
        )
        endpoint = fresh_evaluator(
            runner, tape, step_index, anchor_rows[0]["incumbent"], run_setting,
            "realised", tuple(range(48)),
        )
        parity_configs = dedupe(tuple(row["base"] for row in anchor_rows) + (rss, crowded))
        assert any(row.configuration_id == representative_base.configuration_id for row in parity_configs)
        endpoint.evaluate_many(parity_configs)
        for row in anchor_rows:
            panel_row = row["panel_row"]
            index = int(panel_row["global_anchor_index"])
            carrier = str(panel_row["carrier"])
            endpoint_anchors.append({
                "anchor_index": index,
                "anchor_id": f"{panel_row['world_id']}|{step_index}|{carrier}",
                "BASE": endpoint_row(panel, profile(endpoint, row["base"])),
                "RSS_MAX": endpoint_row(panel, profile(endpoint, rss)),
                "CROWDED": endpoint_row(panel, profile(endpoint, crowded)),
                "physical_boundary_evaluations": endpoint.physical_evaluations,
            })
            parity_position += 1
            print(f"parity anchor {parity_position}/{len(frozen)} peak RSS {peak_rss_bytes()/2**30:.3f} GiB", flush=True)
        groups.append({
            "step_index": step_index, "options": options, "anchors": anchor_rows,
            "representative_base": representative_base, "RSS_MAX": rss,
            "CROWDED": crowded, "endpoint": endpoint,
        })
        check_runtime()

    endpoint_pooled = {
        name: pool_endpoints(endpoint_anchors, name)
        for name in ("BASE", "RSS_MAX", "CROWDED")
    }
    for name, expected in EXPECTED_ENDPOINT_EE.items():
        observed = endpoint_pooled[name]["ee_mbit_per_j"]
        if round(observed, 6) != round(expected, 6):
            raise RuntimeError(f"STOP: {name} parity failed: {observed} versus {expected}")
        if endpoint_pooled[name]["served"] != endpoint_pooled[name]["users"]:
            raise RuntimeError(f"STOP: {name} endpoint does not have full service")
    print("PARITY PASS " + json.dumps(endpoint_pooled, sort_keys=True), flush=True)

    payload = {
        "schema": "mcrl-v025-coordvalue-design-diagnostic-v1",
        "status": "RUNNING",
        "claim_status": "DESIGN_PHASE_DIAGNOSTIC_NOT_A_CLAIM",
        "learner_free": True,
        "python": sys.executable,
        "niceness": os.getpriority(os.PRIO_PROCESS, 0),
        "process_count": 1,
        "thread_pins": {name: os.environ[name] for name in THREAD_VARS},
        "panel": frozen,
        "eta_ref": fraction_payload(calibration.eta_ref),
        "kappa_bits_per_user_step": fraction_payload(calibration.kappa_bits_per_user_step),
        "eta_ref_source": str(CALIBRATION_PATH),
        "endpoint_parity": {
            "status": "PASS",
            "path": "per physical step: one separate fresh realised dense full-48 StepEvaluator; first evaluate_many contains all three carrier BASE mappings plus RSS_MAX and CROWDED; after parity passes, every carrier-invariant candidate mapping is added once to this same endpoint evaluator",
            "anchors": endpoint_anchors,
            "pooled": endpoint_pooled,
            "expected_rounded_six": EXPECTED_ENDPOINT_EE,
        },
        "selection_invariant": {
            "path": "per anchor: one fresh realised dense StepEvaluator(boundary_indices=(0,)); first evaluate_many contains BASE, both starts, and candidates; all later candidates use that same evaluator",
            "scalar_evaluate_fail_closed": True,
            "profile_reads": "StepEvaluator._evaluated only",
        },
        "support_reconstruction": {
            "definition": "exact bounded-union-v2 support rebuilt around the current carrier BASE; auxiliary fresh nominal dense evaluate_many only identifies the sealed top-10 support rank and never scores/selects a COORDVALUE move",
            "declared_reference_distribution": {"0": 37, "1": 28960, "2": 7104, "3": 292, "4": 177, "5": 125, "6": 4, "7": 12, "8": 3, "100": 74},
            "declared_reference_total": 36788,
        },
        "search": {
            "k_values": list(K_VALUES),
            "k1": "exhaustive over every declared legal non-incumbent physical identity plus explicit null for every currently assigned user",
            "sampled_budget_per_anchor_start_k": SAMPLE_BUDGET,
            "sample_mixture": [
                "top-single combinations", "opposite-endpoint subsets",
                "common-destination consolidation", "uniform legal mixture (5% null opportunity)",
            ],
            "random_seed_formula": "20260910 + 100000*step + 1000*start_ordinal + k",
        },
        "candidate_log": str(CANDIDATES),
        "anchors": [],
    }
    atomic_write(payload)
    CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    with CANDIDATES.open("w", encoding="utf-8") as handle:
        completed = 0
        for group in groups:
            step_index = group["step_index"]
            options = group["options"]
            endpoint = group["endpoint"]
            representative_base = group["representative_base"]
            start_configs = {"RSS_MAX": group["RSS_MAX"], "CROWDED": group["CROWDED"]}
            keep_ids = {row["base"].configuration_id for row in group["anchors"]}
            keep_ids.update(config.configuration_id for config in start_configs.values())
            candidate_sets = {}
            endpoint_metrics_by_start = {}

            # Generate and endpoint-score one carrier-invariant candidate set per
            # start.  K>1 construction may use the exhaustive K=1 EE ordering.
            for start_ordinal, (start_name, start) in enumerate(start_configs.items()):
                start_endpoint = profile(endpoint, start)
                start_ee = start_endpoint.bits / start_endpoint.joules / 1e6
                start_served = panel.served(start_endpoint)
                singles = single_candidates(runner, representative_base, start, options, start_name.lower())
                endpoint_metrics = {1: endpoint_candidate_metrics(
                    panel, endpoint, singles, keep_ids,
                    f"step={step_index} start={start_name} k=1",
                )}
                best_by_user = {}
                for config, members, edits, _method in singles:
                    metric = endpoint_metrics[1][config.configuration_id]
                    identity = edits[0][1]
                    if metric["served"] < start_served or identity is None:
                        continue
                    user = members[0]
                    candidate = {
                        "identity": identity,
                        "delta_ee_mbit_per_j": metric["ee_mbit_per_j"] - start_ee,
                        "configuration_id": config.configuration_id,
                    }
                    if user not in best_by_user or (
                        candidate["delta_ee_mbit_per_j"], candidate["configuration_id"]
                    ) > (
                        best_by_user[user]["delta_ee_mbit_per_j"], best_by_user[user]["configuration_id"]
                    ):
                        best_by_user[user] = candidate
                candidate_sets[start_name] = {1: singles}
                target = group["CROWDED"] if start_name == "RSS_MAX" else group["RSS_MAX"]
                for k in K_VALUES[1:]:
                    forced = []
                    if start_name == "RSS_MAX" and k in (2, 3, 4):
                        for anchor_row in group["anchors"]:
                            index = int(anchor_row["panel_row"]["global_anchor_index"])
                            assignments = basin["anchors"][index]["endpoint"]["metrics"]["RSS_MAX_CATALOGUE_BEST"]["assignments"]
                            seed_mapping = {
                                int(user): None if identity is None else (int(identity[0]), int(identity[1]))
                                for user, identity in assignments
                            }
                            changed = [user for user in sorted(seed_mapping) if seed_mapping[user] != start.mapping[user]]
                            if len(changed) != 4:
                                raise RuntimeError("BASIN2 catalogue seed is not a four-user RSS-relative move")
                            for members in itertools.combinations(changed, k):
                                mapping = dict(start.mapping)
                                for user in members:
                                    mapping[user] = seed_mapping[user]
                                forced.append(mapping)
                    samples = sampled_candidates(
                        runner, representative_base, start, target, options, k, SAMPLE_BUDGET,
                        RANDOM_SEED + 100000 * step_index + 1000 * start_ordinal + k,
                        best_by_user, forced,
                    )
                    candidate_sets[start_name][k] = samples
                    endpoint_metrics[k] = endpoint_candidate_metrics(
                        panel, endpoint, samples, keep_ids,
                        f"step={step_index} start={start_name} k={k}",
                    )
                endpoint_metrics_by_start[start_name] = endpoint_metrics

            for group_anchor in group["anchors"]:
                panel_row = group_anchor["panel_row"]
                base = group_anchor["base"]
                incumbent = group_anchor["incumbent"]
                index = int(panel_row["global_anchor_index"])
                carrier = str(panel_row["carrier"])
                anchor_id = f"{panel_row['world_id']}|{step_index}|{carrier}"
                current_support = catalogue_support_ids(
                    runner, calibration, tape, step_index, base, base, run_setting,
                )
                selection_evaluator = fresh_evaluator(
                    runner, tape, step_index, incumbent, run_setting, "realised", (0,),
                )
                anchor = {
                    "global_anchor_index": index, "anchor_id": anchor_id,
                    "step_index": step_index, "carrier": carrier, "starts": {},
                }
                first_prefix = (base, *start_configs.values())
                first_call_pending = True
                for start_name, start in start_configs.items():
                    summaries = []
                    rekeys = runner._rekeyed_users(tape, step_index)
                    rows1 = candidate_sets[start_name][1]
                    if start.configuration_id not in selection_evaluator._evaluated:
                        selection_evaluator.evaluate_many(dedupe((*first_prefix, rows1[0][0])))
                    start_selection = profile(selection_evaluator, start)
                    start_endpoint = profile(endpoint, start)
                    start_f, start_physical, start_phi = total_f(
                        runner, calibration, incumbent, rekeys, start, start_selection,
                    )
                    start_ee = start_endpoint.bits / start_endpoint.joules / 1e6
                    start_served = panel.served(start_endpoint)
                    for k in K_VALUES:
                        rows = candidate_sets[start_name][k]
                        prefix = first_prefix if first_call_pending else ()
                        first_call_pending = False
                        scored = evaluate_rows(
                            handle, index, anchor_id, start_name, rows, k,
                            selection_evaluator, endpoint_metrics_by_start[start_name][k],
                            panel, runner, calibration, incumbent, rekeys, start,
                            start_selection, start_f, start_ee, start_served,
                            current_support["ids"], first_prefix=prefix,
                        )
                        summaries.append(summarize_rows(
                            scored, k,
                            "exhaustive" if k == 1 else "sampled-fixed-mixture",
                            len(rows), k == 1,
                            sum(row["inside_current_catalogue"] for row in scored),
                        ))
                    minimum_k = next((row["k"] for row in summaries if row["ee_improving_count"]), None)
                    count_keys = (
                        "candidates_evaluated", "guarded_candidates", "service_dropping_candidates",
                        "service_dropping_ee_increase_count", "ee_improving_count",
                        "ee_improves_f_decreases_count", "f_improves_ee_decreases_count",
                        "improving_inside_current_catalogue_count", "improving_outside_current_catalogue_count",
                    )
                    all_counts = {key: sum(row[key] for row in summaries) for key in count_keys}
                    anchor["starts"][start_name] = {
                        "configuration_id": start.configuration_id,
                        "start": {
                            "bits": start_endpoint.bits, "joules": start_endpoint.joules,
                            "endpoint_boundaries": 48,
                            "selection_boundary0_bits": start_selection.bits,
                            "selection_boundary0_joules": start_selection.joules,
                            "ee_mbit_per_j": start_ee, "f": fraction_payload(start_f),
                            "physical_core_b_minus_eta_e": fraction_payload(start_physical),
                            "phi_cost_bits": fraction_payload(start_phi), "served": start_served,
                        },
                        "catalogue_support": {
                            key: value for key, value in current_support.items() if key != "ids"
                        },
                        "by_k": summaries,
                        "minimum_sampled_or_exhaustive_improving_k": minimum_k,
                        "counts": all_counts,
                    }
                anchor["selection_physical_boundary_evaluations"] = selection_evaluator.physical_evaluations
                anchor["endpoint_physical_boundary_evaluations_shared_for_step"] = endpoint.physical_evaluations
                payload["anchors"].append(anchor)
                completed += 1
                payload["peak_rss_bytes"] = peak_rss_bytes()
                atomic_write(payload)
                del selection_evaluator, current_support
                gc.collect()
                check_runtime()
                print(
                    f"anchor {completed}/{len(frozen)} peak RSS {peak_rss_bytes()/2**30:.3f} GiB "
                    + json.dumps({
                        name: {"minimum_k": anchor["starts"][name]["minimum_sampled_or_exhaustive_improving_k"],
                               "k1_improving": anchor["starts"][name]["by_k"][0]["ee_improving_count"]}
                        for name in start_configs
                    }, sort_keys=True), flush=True,
                )
            del endpoint, candidate_sets, endpoint_metrics_by_start
            gc.collect()

    pooled_counts = {}
    for start_name in ("RSS_MAX", "CROWDED"):
        pooled_counts[start_name] = {
            key: sum(anchor["starts"][start_name]["counts"][key] for anchor in payload["anchors"])
            for key in payload["anchors"][0]["starts"][start_name]["counts"]
        }
        pooled_counts[start_name]["minimum_k_distribution"] = dict(Counter(
            str(anchor["starts"][start_name]["minimum_sampled_or_exhaustive_improving_k"])
            for anchor in payload["anchors"]
        ))
        rejected = [
            row["best_ee_improvement_f_rejects"]
            for anchor in payload["anchors"]
            for row in anchor["starts"][start_name]["by_k"]
            if row["best_ee_improvement_f_rejects"] is not None
        ]
        pooled_counts[start_name]["best_ee_improvement_f_rejects"] = max(
            rejected, key=lambda row: (row["delta_ee_mbit_per_j"], row["configuration_id"]),
            default=None,
        )
    payload["pooled_candidate_counts"] = pooled_counts
    payload["candidate_log_sha256"] = sha256(CANDIDATES)
    payload["scalar_evaluate_calls"] = SCALAR_EVALUATE_CALLS
    assert SCALAR_EVALUATE_CALLS == 0
    payload["scalar_evaluate_assertion"] = "PASS: raising stub installed; zero calls"
    payload["status"] = "COMPLETE"
    payload["peak_rss_bytes"] = peak_rss_bytes()
    payload["wall_seconds"] = time.perf_counter() - started
    payload["runner_sha256"] = sha256(Path(__file__))
    atomic_write(payload)
    check_runtime()
    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB final ({peak_rss_bytes()} bytes)", flush=True)
    print(json.dumps({
        "endpoint_pooled": endpoint_pooled,
        "pooled_candidate_counts": pooled_counts,
        "scalar_evaluate_calls": SCALAR_EVALUATE_CALLS,
    }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
