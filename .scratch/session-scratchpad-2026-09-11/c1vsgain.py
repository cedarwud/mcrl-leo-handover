#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""C1VSGAIN -- does exact C1 beat the gain heuristic it mostly selects?

Learner-free.  Derived from /home/sat/mcrl-v025-c2target-ws/.scratch/c2target/
oracle_ee.py (selection + endpoint harness, label reader, evaluator rule) and
from /home/sat/mcrl-v025-basin-ws/.scratch/basin2/run_basin2.py:198-215 (the
RSS_MAX mapping definition).

Arms (all evaluated on ONE fresh realised dense full-48 StepEvaluator per
anchor, with BASE inside the first evaluate_many batch)

  BASE                   the carrier reference configuration a0 (no move)
  C1_ONLY                argmax over the catalogue of sum_u [C1(u,a)-C1(u,a0)]
  C1_PSI                 argmax of  sum_u dC1  +  Psi(a)      (exact C3 term)
  S0_TOP1_UNCONDITIONAL  the catalogue's first s0-top-two proposal, no scoring
  S0_TOP2_BEST           the better of the two s0 proposals by exact C1
  RSS_MAX                per user, the legal option with the highest nominal
                         gain at boundary 0 (basin2 definition), no scoring
  GAIN_IN_SET            BEAMCOUNT's declared beam-set rule under the loose
                         cap C=50 with within-set max-nominal-gain assignment
                         (S1/S2/S3 x A2, best of the three by boundary-0 EE
                         under the carrier-BASE served guard), no local search
  GAIN_IN_SET_LADDER     BEAMCOUNT's full winner procedure at C=50: nine
                         declared rules, first-improvement boundary-0 polish
                         of the two best starts, RSS_MAX seeded when it fits,
                         and smaller-cap winners inherited over the truncated
                         cap ladder LADDER_CAPS
  CATALOGUE_ORACLE       the catalogue member with the highest REALISED
                         full-48 EE (the in-catalogue ceiling, not a policy)

Psi is the sealed exact set interaction of targets.py:set_score_decomposition:
Psi(a) = [F(a) - F(a0)]/kappa + dPhi(a)  -  sum_u [C1(u,a_u) - C1(u,a0_u)],
with F the nominal boundary-0 phi-inclusive objective, i.e. exactly the field
in which the sealed corpus C1 labels are defined.  So C1_PSI's score is the
joint nominal objective change, and it is asserted to equal the sum of the two
parts to 1e-9 relative.

Mandatory evaluator rule
  * ONE fresh dense nominal boundary-0 StepEvaluator per anchor for the
    selection comparison, BASE entering through evaluate_many with every
    candidate (this is the field the sealed labels live in).
  * ONE separate fresh realised dense full-48 StepEvaluator per anchor for the
    endpoints, BASE inside the first evaluate_many call together with every
    arm; the remaining catalogue members are added to that SAME fresh
    evaluator in further evaluate_many chunks (memory cap), never scalar.
  * On BOTH evaluators the bound method ``evaluate`` is replaced by a raising
    stub after the batches, and the call counters are asserted zero.
  * No foreign cache is read.
"""

from __future__ import annotations

from fractions import Fraction
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

import numpy as np

SOURCE_ROOT = Path("/home/sat/mcrl-v025-c1c2suff-ws")
RUNNER = SOURCE_ROOT / "scripts/run_v025_pilot_c3.py"
CALIBRATION = (
    SOURCE_ROOT
    / "artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM"
    / "PILOT_NOT_CLAIM-calibration.json"
)
OUTDIR = Path("/home/sat/mcrl-v025-c1vsgain-ws/.scratch/c1vsgain")
PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python").resolve()
THREAD_VARS = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
MAX_AS_BYTES = 4_900_000_000
ENDPOINT_CHUNK = 64
BEAMCOUNT = Path(
    "/home/sat/mcrl-v025-beamcount-ws/.scratch/beamcount/run_beamcount_sweep_frozen.py"
)
LADDER_CAPS = (8, 20, 30, 50)
LADDER_PASSES = 4          # BEAMCOUNT CAPPED_PASSES default
ARMS = (
    "BASE", "C1_ONLY", "C1_PSI", "S0_TOP1_UNCONDITIONAL", "S0_TOP2_BEST",
    "RSS_MAX", "GAIN_IN_SET", "GAIN_IN_SET_LADDER", "CATALOGUE_ORACLE",
)


class EvaluateForbidden(RuntimeError):
    pass


def enforce() -> None:
    if Path(sys.executable).resolve() != PYTHON:
        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        raise RuntimeError("niceness below 15")
    bad = {n: os.environ.get(n) for n in THREAD_VARS if os.environ.get(n) != "1"}
    if bad:
        raise RuntimeError(f"thread pins drifted: {bad}")
    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = MAX_AS_BYTES if hard == resource.RLIM_INFINITY else min(MAX_AS_BYTES, hard)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_pilot():
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
    name = f"c1vsgain_pilot_{os.getpid()}"
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if module.PILOT_PRIMITIVE_SOURCE_FALLBACK is not True:
        raise RuntimeError("pilot fallback flag is not the on-disk default")
    return module


def load_beamcount():
    """Import BEAMCOUNT's rule code (cover, matroid extension, assignments and
    the boundary-0 first-improvement search) instead of reimplementing it.
    Module level defines constants only; nothing is run and nothing is written."""
    name = f"c1vsgain_beamcount_{os.getpid()}"
    spec = importlib.util.spec_from_file_location(name, BEAMCOUNT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_calibration(pilot):
    payload = json.loads(CALIBRATION.read_text())

    def fraction(name):
        numerator, denominator = payload[name]
        return Fraction(numerator, denominator)

    return pilot.PilotCalibration(
        eta_ref=fraction("eta_ref"),
        lambda_bits_per_j=fraction("lambda_bits_per_j"),
        kappa_bits_per_user_step=fraction("kappa_bits_per_user_step"),
        bits_ref=fraction("bits_ref"),
        joules_ref=fraction("joules_ref"),
        users=int(payload["users"]),
    )


def read_anchor_labels(shard: Path):
    """(user, identity) -> {'c1','c2'}, plus the per-user incumbent identity."""
    expected = (shard.parent / (shard.name + ".sha256")).read_text().split()[0].strip()
    if sha256(shard) != expected:
        raise RuntimeError(f"sidecar mismatch: {shard}")
    labels = {}
    incumbent_action = {}
    with shard.open() as handle:
        header = json.loads(handle.readline())
        for line in handle:
            row = json.loads(line)
            user = int(row["user_id"])
            identity = (
                None if row["null_action"]
                else (int(row["action"]["norad_id"]), int(row["action"]["beam_chain_id"]))
            )
            labels[(user, identity)] = {
                "c1": float.fromhex(row["c1_label_normalized_hex"]),
                "c2": float.fromhex(row["c2_label_normalized_hex"]),
            }
            if row["reference_action"]:
                incumbent_action[user] = identity
    return header, labels, incumbent_action


def argmax_config(scored):
    """max score, tie-break lowest configuration id (mirrors _set_score_select)."""
    return min(scored, key=lambda row: (-row[0], row[1]))[2]


def profile_stats(profile):
    served = profile.score.served_phy
    attained = profile.score.rate_target_attained
    feasible = profile.score.rate_target_feasible
    users = len(served)
    if attained is None:
        raise RuntimeError("rate-target attainment is absent from the cell score")
    return {
        "bits": float(profile.bits),
        "joules": float(profile.joules),
        "ee_bits_per_j": None if profile.joules == 0 else float(profile.bits) / float(profile.joules),
        "served_users": int(sum(1 for value in served.values() if value)),
        "attained_users": int(sum(1 for value in attained.values() if value)),
        "users": users,
        "feasible_users": None if feasible is None else int(sum(1 for value in feasible.values() if value)),
        "served_fraction": sum(1 for value in served.values() if value) / users,
        "rate_target_attainment_fraction": sum(1 for value in attained.values() if value) / users,
        "certificate_status": profile.certificate_status,
    }


def rss_max_mapping(engine, tape, step_index, base):
    """basin2 run_basin2.py:198-215 -- per user the legal option with the
    highest boundary-0 nominal gain; ties by the legal-option ordinal."""
    options, _census = engine._legal_options(tape, step_index)
    arrays = tape.steps[step_index].arrays
    if arrays is None:
        raise RuntimeError("panel omitted primitive arrays; RSS_MAX undefined")
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
    return mapping, options


def s0_proposals(engine, tape, step_index, base, run_setting):
    """Rebuild the catalogue's s0-top-two proposals in builder order
    (run_v025_matrix_probe.py:625-632)."""
    all_options, _raw = engine._legal_options(tape, step_index)
    users = tuple(sorted(user.user_id for user in tape.user_layout))
    product_size = math.prod(
        len(all_options[user]) if all_options[user] else 1 for user in users
    )
    if product_size <= engine.COMPLETE_CATALOGUE_LIMIT:
        raise RuntimeError("anchor is complete-cartesian; the s0 proposals do not exist")
    options, _census = engine._selection_shortlist(tape, step_index, run_setting=run_setting)
    base_map = base.mapping
    unilaterals = {
        user: [identity for identity in options[user] if identity != base_map[user]]
        for user in users
    }
    proposals = []
    for rank in range(engine.TOP_PROPOSALS):
        mapping = dict(base_map)
        for user in users:
            if len(unilaterals[user]) > rank:
                mapping[user] = unilaterals[user][rank]
        if mapping != base_map:
            proposals.append(engine._configuration(base, mapping, kind="s0-top-two"))
    return proposals


def beam_state(bc, engine, tape, step_index, cache):
    """Per-step legal graph, exact minimum cover, coverage and gain tables,
    built with BEAMCOUNT's own functions (run_beamcount_sweep_frozen.py)."""
    if step_index in cache:
        return cache[step_index]
    options, _census = engine._legal_options(tape, step_index)
    cover, _greedy = bc.minimum_cover(options)
    rank = len(bc.maximum_matching(options))
    all_beams = tuple(sorted({b for rows in options.values() for b in rows}))
    coverage = {b: sum(b in options[u] for u in options) for b in all_beams}
    arrays = tape.steps[step_index].arrays
    if arrays is None:
        raise RuntimeError("panel omitted primitive arrays")
    row_of = arrays._row_index()

    def gain_of(user, beam, _a=arrays, _r=row_of):
        return float(_a.nominal_gain[0, _r[(user, beam)]])

    beam_gain = {
        b: math.fsum(gain_of(u, b) for u in options if b in options[u]) for b in all_beams
    }
    state = {
        "options": options, "cover": cover, "rank": rank, "coverage": coverage,
        "beam_gain": beam_gain, "gain_of": gain_of,
        "floor": len(cover), "distinct_legal_beams": len(all_beams),
    }
    cache.clear()
    cache[step_index] = state
    return state


def gain_in_set_arms(bc, engine, tape, step_index, base, incumbent, run_setting,
                     state, rss_mapping, counters):
    """Reproduce BEAMCOUNT's cap sweep at the loose cap, returning both the
    declared max-gain-in-set rule and the full ladder winner."""
    options = state["options"]
    coverage, beam_gain, gain_of = state["coverage"], state["beam_gain"], state["gain_of"]
    cover, rank = state["cover"], state["rank"]
    beam_set_rules = {
        "S1_ascending_coverage": lambda b: (coverage[b], b),
        "S2_descending_coverage": lambda b: (-coverage[b], b),
        "S3_descending_nominal_gain": lambda b: (-beam_gain[b], b),
    }
    rss_active = tuple(sorted({v for v in rss_mapping.values() if v is not None}))
    inherited: dict[str, dict] = {}
    detail = {}
    declared_best = None
    ladder_winner = None
    caps = tuple(cap for cap in LADDER_CAPS if cap >= state["floor"])
    for cap in caps:
        search = bc.Boundary0Search(
            engine, tape, step_index, incumbent, run_setting, base,
            f"c1vsgain-beamcount-c{cap:03d}",
        )

        def search_stub(config, _counter=counters):
            _counter["gain_in_set"] += 1
            raise EvaluateForbidden("scalar evaluate is forbidden on the search evaluator")

        search.evaluator.evaluate = search_stub  # type: ignore[method-assign]
        starts: dict[str, dict] = {}
        for set_name, key in beam_set_rules.items():
            beams = bc.matroid_extension(options, cover, key, cap, rank)
            for assign_name, mapping in (
                ("A1_coverage_first", bc.assignment_coverage_first(options, beams)),
                ("A2_max_nominal_gain", bc.assignment_max_gain(options, beams, gain_of)),
                ("A3_least_loaded", bc.assignment_least_loaded(options, beams)),
            ):
                starts[f"{set_name}|{assign_name}"] = {"beams": beams, "mapping": mapping}
        for name, row in inherited.items():
            starts[name] = dict(row)
        if len(rss_active) <= cap:
            starts["RSS_MAX_within_cap"] = {"beams": rss_active, "mapping": dict(rss_mapping)}
        start_cfgs = {name: search.make(row["mapping"]) for name, row in starts.items()}
        search.submit([base] + list(start_cfgs.values()))
        base_profile = search.read(base)
        base_guard = 0 if base_profile is None else bc.Boundary0Search.score(base_profile)[1]
        ranked = []
        for name, cfg in start_cfgs.items():
            profile = search.read(cfg)
            if profile is None:
                continue
            value, served = bc.Boundary0Search.score(profile)
            starts[name]["boundary0_ee"] = value
            starts[name]["boundary0_served"] = served
            ranked.append((value, served, name))
        if not ranked:
            raise RuntimeError(f"no valid start at cap {cap}")
        ranked.sort(key=lambda row: (-row[0], row[2]))
        polished = []
        for _value, _served, name in ranked[:2]:
            row = starts[name]
            result = search.run(row["mapping"], options, frozenset(row["beams"]), LADDER_PASSES)
            if result is None:
                continue
            mapping, cfg, value, served, moves, passes = result
            polished.append({
                "start": name, "mapping": mapping, "config": cfg,
                "boundary0_ee": value, "boundary0_served": served,
                "moves": moves, "passes": passes,
            })
        if not polished:
            raise RuntimeError(f"no polished candidate at cap {cap}")
        pool = list(polished) + [
            {"start": name, "mapping": row["mapping"], "config": start_cfgs[name],
             "boundary0_ee": row["boundary0_ee"], "boundary0_served": row["boundary0_served"],
             "moves": 0, "passes": 0}
            for name, row in starts.items() if "boundary0_ee" in row
        ]
        guarded = [row for row in pool if row["boundary0_served"] >= base_guard]
        chosen_from = guarded if guarded else pool
        chosen_from.sort(key=lambda row: (-row["boundary0_ee"], row["config"].configuration_id))
        winner = chosen_from[0]
        inherited[f"INHERITED_CAP_{cap:03d}_WINNER"] = {
            "beams": tuple(sorted({v for v in winner["mapping"].values() if v is not None})),
            "mapping": dict(winner["mapping"]),
        }
        if len({v for v in winner["mapping"].values() if v is not None}) > cap:
            raise RuntimeError("cap violated by the winning assignment")
        declared_pool = [
            row for name, row in starts.items()
            if name.endswith("A2_max_nominal_gain") and "boundary0_ee" in row
        ]
        declared_guarded = [
            row for row in declared_pool if row["boundary0_served"] >= base_guard
        ] or declared_pool
        declared_guarded.sort(key=lambda row: -row["boundary0_ee"])
        detail[f"CAP_{cap:03d}"] = {
            "cap": cap,
            "winner_start": winner["start"],
            "winner_boundary0_ee": winner["boundary0_ee"],
            "winner_boundary0_served": winner["boundary0_served"],
            "winner_active_beams": len({v for v in winner["mapping"].values() if v is not None}),
            "base_served_guard_boundary0": base_guard,
            "guard_satisfied": bool(guarded),
            "declared_max_gain_best_boundary0_ee": declared_guarded[0]["boundary0_ee"],
            "polished_moves": [row["moves"] for row in polished],
            "boundary0_configurations_submitted": search.submitted,
        }
        if cap == caps[-1]:
            ladder_winner = engine._configuration(
                base, winner["mapping"], kind=f"beamcount-ladder-c{cap:03d}"
            )
            declared_best = engine._configuration(
                base, declared_guarded[0]["mapping"], kind=f"beamcount-gain-in-set-c{cap:03d}"
            )
        search.close()
    return declared_best, ladder_winner, detail, caps


def run(corpus: Path, worker: int, workers: int, out_name: str, limit: int | None) -> int:
    enforce()
    started = time.perf_counter()
    pilot = load_pilot()
    bc = load_beamcount()
    engine = pilot.ENGINE
    setting = engine._setting("a-r0")
    run_setting = engine.run_setting_for("a-r0")
    calibration = load_calibration(pilot)
    kappa = calibration.kappa_bits_per_user_step
    eta = calibration.eta_ref

    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape

    every = sorted(
        corpus.glob("views/world-*/BUILD_NOT_CLAIM-exact-source-anchor-*.jsonl"),
        key=lambda p: (p.parent.name, p.name),
    )
    shards = [path for index, path in enumerate(every) if index % workers == worker]
    if limit is not None:
        shards = shards[:limit]

    tape = None
    tape_world = None
    tape_wall = {}
    evaluate_calls = {"selection": 0, "endpoint": 0, "gain_in_set": 0}
    records = []
    peak_kb = 0
    beam_cache: dict[int, dict] = {}

    # resume: reuse anchors already finished in a previous, interrupted run
    OUTDIR.mkdir(parents=True, exist_ok=True)
    partial_path = OUTDIR / f"{out_name}.partial"
    if partial_path.exists():
        resumed = json.loads(partial_path.read_text())
        records = resumed["records"]
        for key in evaluate_calls:
            evaluate_calls[key] += int(resumed["evaluate_stub_calls"].get(key, 0))
        peak_kb = int(resumed.get("peak_rss_kb", 0))
        print(json.dumps({"resumed_anchors": len(records)}), flush=True)
    done = {int(row["global_anchor_index"]) for row in records}

    def peek_anchor_index(path: Path) -> int:
        with path.open() as handle:
            return int(json.loads(handle.readline())["global_anchor_index"])

    for shard in shards:
        if peek_anchor_index(shard) in done:
            continue
        anchor_started = time.perf_counter()
        header, labels, incumbent_action = read_anchor_labels(shard)
        world_index = int(header["world_index"])
        if tape_world != world_index:
            tape = None
            gc.collect()
            tape_started = time.perf_counter()
            tape = build_world_tape(
                domain=pilot.TRAIN_WORLDS[world_index - 1],
                provider=LegacyWorldProvider(role="pilot-source"),
                steps=33,
                start_time_s=0.0,
            )
            tape_world = world_index
            tape_wall[world_index] = time.perf_counter() - tape_started
        if header["world_id"] != tape.domain:
            raise RuntimeError(f"world mismatch: {header['world_id']} vs {tape.domain}")
        step_index = int(header["step_index"])
        carrier = header["carrier"]

        base = engine._base_configuration(tape, step_index, carrier)
        incumbent = engine._base_configuration(tape, max(0, step_index - 1), carrier)
        rekeyed = engine._rekeyed_users(tape, step_index)

        base_map = base.mapping
        for user, identity in base_map.items():
            if incumbent_action.get(user, "absent") != identity:
                raise RuntimeError(
                    f"corpus incumbent action disagrees with base configuration at user {user}"
                )
            row = labels.get((user, identity))
            if row is None:
                raise RuntimeError(f"no corpus row for the incumbent action of user {user}")
            if row["c1"] != 0.0:
                raise RuntimeError(f"incumbent C1 label is not zero for user {user}: {row['c1']}")

        catalogue, census = engine._catalogue_with_census(
            tape, step_index, base,
            setting=setting, calibration=calibration, run_setting=run_setting,
        )
        if census.get("catalogue_mode") != "bounded-union-v2":
            raise RuntimeError(f"unexpected catalogue mode: {census.get('catalogue_mode')}")
        by_cid = {config.configuration_id: config for config in catalogue}
        covered = []
        uncovered = 0
        for config in catalogue:
            mapping = config.mapping
            if all((user, mapping[user]) in labels for user in mapping):
                covered.append(config)
            else:
                uncovered += 1

        # ---- heuristic arms, built without any score
        s0_rows = s0_proposals(engine, tape, step_index, base, run_setting)
        s0_in_catalogue = [row.configuration_id in by_cid for row in s0_rows]
        if not all(s0_in_catalogue) or not s0_rows:
            raise RuntimeError(f"s0 proposal reconstruction missed the catalogue: {s0_in_catalogue}")
        rss_mapping, all_options = rss_max_mapping(engine, tape, step_index, base)
        rss_config = engine._configuration(base, rss_mapping, kind="c1vsgain-rss-max")
        rss_in_catalogue = rss_config.configuration_id in by_cid
        rss_equals_base = rss_config.configuration_id == base.configuration_id
        rss_covered = all((user, rss_mapping[user]) in labels for user in rss_mapping)

        # ---- BEAMCOUNT comparators (their own code, their own fresh
        # boundary-0 evaluators, one per (anchor, cap))
        gain_started = time.perf_counter()
        state = beam_state(bc, engine, tape, step_index, beam_cache)
        gain_config, ladder_config, gain_detail, ladder_caps = gain_in_set_arms(
            bc, engine, tape, step_index, base, incumbent, run_setting,
            state, rss_mapping, evaluate_calls,
        )
        gain_wall = time.perf_counter() - gain_started
        gc.collect()

        # ---- selection comparison: ONE fresh dense NOMINAL boundary-0 evaluator
        # (the field the sealed C1/Psi labels are defined in)
        selection = engine.StepEvaluator(
            tape, setting, step_index,
            transition_from=incumbent,
            cell_rekeyed_users=rekeyed,
            field="nominal",
            run_setting=run_setting,
            boundary_indices=(0,),
        )

        def selection_stub(config, _counter=evaluate_calls):
            _counter["selection"] += 1
            raise EvaluateForbidden("scalar evaluate is forbidden on the selection evaluator")

        batch = {base.configuration_id: base}
        for config in covered:
            batch[config.configuration_id] = config
        if rss_covered and rss_config.configuration_id not in batch:
            batch[rss_config.configuration_id] = rss_config
        selection.evaluate_many(tuple(batch.values()))
        selection.evaluate = selection_stub  # type: ignore[method-assign]
        if base.configuration_id not in selection._evaluated:
            raise RuntimeError("BASE did not populate through evaluate_many")

        nominal_base = selection._evaluated[base.configuration_id]
        base_phi = engine._phi_for(incumbent, base, cell_rekeyed_users=rekeyed)

        def joint_normalized(config):
            """[F(a)-F(a0)]/kappa + dPhi(a): the sealed phi-inclusive objective
            change, in the same units and field as the C1 labels."""
            profile = selection._evaluated.get(config.configuration_id)
            if profile is None:
                return None
            core = Fraction(str(profile.bits - nominal_base.bits)) - eta * Fraction(
                str(profile.joules - nominal_base.joules)
            )
            phi = engine._phi_for(incumbent, config, cell_rekeyed_users=rekeyed) - base_phi
            return core / kappa + phi

        base_c1 = {user: labels[(user, base_map[user])]["c1"] for user in base_map}
        scored_c1 = []
        scored_joint = []
        psi_unilateral_max = 0.0
        psi_by_cid = {}
        d1_by_cid = {}
        nominal_invalid = 0
        for config in covered:
            mapping = config.mapping
            d1 = math.fsum(
                labels[(user, mapping[user])]["c1"] - base_c1[user] for user in mapping
            )
            scored_c1.append((d1, config.configuration_id, config))
            d1_by_cid[config.configuration_id] = d1
            joint = joint_normalized(config)
            if joint is None:
                nominal_invalid += 1
                continue
            joint_float = float(joint)
            psi = joint_float - d1
            psi_by_cid[config.configuration_id] = psi
            scored_joint.append((joint_float, config.configuration_id, config))
            if config.changed_users == 1:
                psi_unilateral_max = max(psi_unilateral_max, abs(psi))

        selections = {"BASE": base}
        selections["C1_ONLY"] = argmax_config(scored_c1)
        selections["C1_PSI"] = argmax_config(scored_joint)
        selections["S0_TOP1_UNCONDITIONAL"] = by_cid[s0_rows[0].configuration_id]
        s0_scored = [
            (d1_by_cid[row.configuration_id], row.configuration_id, by_cid[row.configuration_id])
            for row in s0_rows
            if row.configuration_id in d1_by_cid
        ]
        if not s0_scored:
            raise RuntimeError("no s0 proposal carries a complete exact C1 score")
        selections["S0_TOP2_BEST"] = argmax_config(s0_scored)
        selections["RSS_MAX"] = rss_config
        selections["GAIN_IN_SET"] = gain_config
        selections["GAIN_IN_SET_LADDER"] = ladder_config

        arm_scores = {
            arm: {
                "exact_c1_score": d1_by_cid.get(selections[arm].configuration_id),
                "psi": psi_by_cid.get(selections[arm].configuration_id),
                "joint_c1_plus_psi": (
                    None if selections[arm].configuration_id not in psi_by_cid
                    else d1_by_cid[selections[arm].configuration_id]
                    + psi_by_cid[selections[arm].configuration_id]
                ),
            }
            for arm in ARMS if arm != "CATALOGUE_ORACLE"
        }
        arm_scores["BASE"] = {"exact_c1_score": 0.0, "psi": 0.0, "joint_c1_plus_psi": 0.0}
        if rss_covered and rss_config.configuration_id in selection._evaluated:
            joint_rss = joint_normalized(rss_config)
            d1_rss = math.fsum(
                labels[(user, rss_mapping[user])]["c1"] - base_c1[user] for user in rss_mapping
            )
            arm_scores["RSS_MAX"] = {
                "exact_c1_score": d1_rss,
                "psi": None if joint_rss is None else float(joint_rss) - d1_rss,
                "joint_c1_plus_psi": None if joint_rss is None else float(joint_rss),
            }

        del selection
        gc.collect()

        # ---- endpoints: ONE separate fresh REALISED dense full-48 evaluator
        endpoint = engine.StepEvaluator(
            tape, setting, step_index,
            transition_from=incumbent,
            cell_rekeyed_users=rekeyed,
            field="realised",
            run_setting=run_setting,
            boundary_indices=tuple(range(48)),
        )

        def endpoint_stub(config, _counter=evaluate_calls):
            _counter["endpoint"] += 1
            raise EvaluateForbidden("scalar evaluate is forbidden on the endpoint evaluator")

        first_batch = {base.configuration_id: base}
        for arm in ARMS:
            if arm == "CATALOGUE_ORACLE":
                continue
            first_batch[selections[arm].configuration_id] = selections[arm]
        endpoint.evaluate_many(tuple(first_batch.values()))
        if base.configuration_id not in endpoint._evaluated:
            raise RuntimeError("BASE did not populate through the endpoint evaluate_many")
        remaining = [
            config for config in catalogue
            if config.configuration_id not in endpoint._evaluated
            and config.configuration_id not in endpoint._invalid
        ]
        for start in range(0, len(remaining), ENDPOINT_CHUNK):
            endpoint.evaluate_many(tuple(remaining[start:start + ENDPOINT_CHUNK]))
        endpoint.evaluate = endpoint_stub  # type: ignore[method-assign]

        ee = {}
        for cid, config in by_cid.items():
            profile = endpoint._evaluated.get(cid)
            if profile is not None and profile.joules > 0.0:
                ee[cid] = float(profile.bits) / float(profile.joules)
        oracle_cid = min(ee, key=lambda cid: (-ee[cid], cid))
        selections["CATALOGUE_ORACLE"] = by_cid[oracle_cid]
        arm_scores["CATALOGUE_ORACLE"] = {
            "exact_c1_score": d1_by_cid.get(oracle_cid),
            "psi": psi_by_cid.get(oracle_cid),
            "joint_c1_plus_psi": (
                None if oracle_cid not in psi_by_cid
                else d1_by_cid[oracle_cid] + psi_by_cid[oracle_cid]
            ),
        }
        ranked = sorted(ee, key=lambda cid: (-ee[cid], cid))
        rank_of = {cid: index for index, cid in enumerate(ranked)}

        arm_records = {}
        for arm in ARMS:
            cid = selections[arm].configuration_id
            profile = endpoint._evaluated.get(cid)
            if profile is None:
                arm_records[arm] = {"configuration_id": cid, "invalid": True}
                continue
            stats = profile_stats(profile)
            stats["configuration_id"] = cid
            stats["changed_users"] = int(selections[arm].changed_users)
            stats["kind"] = by_cid[cid].kind if cid in by_cid else selections[arm].kind
            stats["in_catalogue"] = cid in by_cid
            stats["invalid"] = False
            stats["rank_of_realised_full48_ee"] = rank_of.get(cid)
            stats["catalogue_size_ranked"] = len(ranked)
            arm_records[arm] = stats

        records.append({
            "global_anchor_index": int(header["global_anchor_index"]),
            "world_index": world_index,
            "step_index": step_index,
            "carrier": carrier,
            "shard": shard.name,
            "catalogue_size": len(catalogue),
            "catalogue_covered": len(covered),
            "catalogue_uncovered": uncovered,
            "catalogue_endpoint_valid": len(ee),
            "nominal_invalid_covered": nominal_invalid,
            "catalogue_mode": census.get("catalogue_mode"),
            "s0_proposal_count": len(s0_rows),
            "s0_proposal_ids": [row.configuration_id for row in s0_rows],
            "s0_top2_best_is_rank": (
                0 if selections["S0_TOP2_BEST"].configuration_id == s0_rows[0].configuration_id
                else 1
            ),
            "rss_in_catalogue": rss_in_catalogue,
            "rss_equals_base": rss_equals_base,
            "rss_covered_by_labels": rss_covered,
            "rss_equals_s0_top1": rss_config.configuration_id == s0_rows[0].configuration_id,
            "rss_changed_users_vs_base": int(rss_config.changed_users),
            "psi_max_abs_on_unilaterals": psi_unilateral_max,
            "beam_floor": state["floor"],
            "distinct_legal_beams": state["distinct_legal_beams"],
            "ladder_caps": list(ladder_caps),
            "gain_in_set_detail": gain_detail,
            "gain_in_set_wall_s": gain_wall,
            "arms": arm_records,
            "arm_scores": arm_scores,
            "c1_only_kind": by_cid[selections["C1_ONLY"].configuration_id].kind,
            "c1_only_is_s0_proposal": (
                selections["C1_ONLY"].configuration_id in {row.configuration_id for row in s0_rows}
            ),
            "c1_only_equals_rss": (
                selections["C1_ONLY"].configuration_id == rss_config.configuration_id
            ),
            "c1_psi_differs_from_c1_only": (
                selections["C1_PSI"].configuration_id != selections["C1_ONLY"].configuration_id
            ),
            "anchor_wall_s": time.perf_counter() - anchor_started,
        })
        peak_kb = max(peak_kb, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        tmp = partial_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "records": records,
            "evaluate_stub_calls": evaluate_calls,
            "peak_rss_kb": peak_kb,
        }))
        tmp.replace(partial_path)
        print(json.dumps({
            "anchor": int(header["global_anchor_index"]),
            "k_of_n": f"{len(records)}/{len(shards)}",
            "wall_s": round(records[-1]["anchor_wall_s"], 2),
            "catalogue": len(catalogue),
            "c1_only_kind": records[-1]["c1_only_kind"],
            "c1_only_ee": arm_records["C1_ONLY"].get("ee_bits_per_j"),
            "rss_ee": arm_records["RSS_MAX"].get("ee_bits_per_j"),
            "gain_in_set_ee": arm_records["GAIN_IN_SET"].get("ee_bits_per_j"),
            "ladder_ee": arm_records["GAIN_IN_SET_LADDER"].get("ee_bits_per_j"),
            "gain_wall_s": round(gain_wall, 1),
            "s0_top1_ee": arm_records["S0_TOP1_UNCONDITIONAL"].get("ee_bits_per_j"),
            "psi_max_abs_unilateral": psi_unilateral_max,
            "peak_rss_kb": peak_kb,
        }), flush=True)
        del endpoint, first_batch, remaining, ee, selections, scored_c1, scored_joint, labels
        gc.collect()

    pooled = {}
    for arm in ARMS:
        rows = [row["arms"][arm] for row in records if not row["arms"][arm]["invalid"]]
        bits = math.fsum(row["bits"] for row in rows)
        joules = math.fsum(row["joules"] for row in rows)
        users = math.fsum(row["users"] for row in rows)
        pooled[arm] = {
            "anchors": len(rows),
            "bits": bits,
            "joules": joules,
            "pooled_ee_bits_per_j": None if joules == 0 else bits / joules,
            "pooled_ee_mbit_per_j": None if joules == 0 else bits / joules / 1e6,
            "served_fraction": math.fsum(row["served_users"] for row in rows) / users,
            "rate_target_attainment_fraction": math.fsum(row["attained_users"] for row in rows) / users,
        }

    result = {
        "status": "DIAGNOSTIC_NOT_CLAIM",
        "anchors": len(records),
        "tape_wall_s": tape_wall,
        "total_wall_s": time.perf_counter() - started,
        "evaluate_stub_calls": evaluate_calls,
        "endpoint_chunk": ENDPOINT_CHUNK,
        "pooled": pooled,
        "records": records,
        "peak_rss_kb": peak_kb,
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / out_name).write_text(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=1, sort_keys=True))
    print(f"PEAK_RSS_KB={max(peak_kb, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))}")
    if any(evaluate_calls.values()):
        raise RuntimeError(f"scalar evaluate was called: {evaluate_calls}")
    return 0


if __name__ == "__main__":
    corpus_arg = Path(sys.argv[1])
    worker_arg, workers_arg = int(sys.argv[2]), int(sys.argv[3])
    name_arg = sys.argv[4]
    limit_arg = int(sys.argv[5]) if len(sys.argv) > 5 else None
    raise SystemExit(run(corpus_arg, worker_arg, workers_arg, name_arg, limit_arg))
