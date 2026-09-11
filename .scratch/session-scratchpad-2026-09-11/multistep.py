#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""MULTISTEP -- a multi-step realised continuation endpoint (learner-free).

For an anchor (world, step t, carrier) and a committed step-t configuration
a_t, the realised field is rolled forward to steps t+1, t+2, t+3 and pooled
full-buffer bits / joules are reported PER STEP, so an EE effect can be
attributed to "now" (step t) versus "later" (t+1..t+3).

Continuation policies (declared before any measurement; see the report):
  b_rss   PRIMARY.  Every arm re-decides at t+k with RSS_MAX(t+k): per user the
          legal identity with maximum boundary-0 nominal gain (legal-ordinal
          tie-break).  Identical for every arm; only step t differs.
  b_base  Every arm continues with the carrier geometric BASE(t+k, carrier).
          Also identical for every arm.
  a_hold  SECONDARY (commitment).  Each user keeps its previous-step identity
          while that identity is legal at t+k (visible & D2-eligible &
          cell-reachable at boundary 0, the sealed _legal_options set); a user
          whose held identity is illegal, or who holds NULL, takes RSS_MAX(t+k).

Horizon semantics: every step uses the same realised field, the same
full-48-boundary dense a-r0 integration and the same full-buffer numerator
(no demand cap) as the existing single-step endpoint.  Step t is scored
exactly as the existing endpoint (transition_from = carrier BASE at t-1).

Evaluator rule: ONE fresh realised dense full-48 StepEvaluator per
(anchor, step); the relevant BASE(step, carrier) enters the single
evaluate_many batch alongside every arm configuration for that step; profiles
are read from that evaluator's own _evaluated cache only.  StepEvaluator.evaluate
is replaced CLASS-WIDE by a raising stub before any tape is built, and the
call counter is asserted to be zero at exit.

Modes
  panel  <out.json> [anchor_limit]      12-anchor learner-free panel; arms
                                         BASE / RSS_MAX / CROWDED; parity gate.
  select <worker> <workers> <out.json>  oracle phase A: rebuild the exact-label
                                         C1_ONLY / FULL / C2_ONLY picks with the
                                         C2TARGET oracle_ee.py functions; cross-check
                                         against the C2TARGET worker receipts.
  oracle <picks.json> <out.json>        oracle phase B: continuation endpoint for
                                         BASE / C1_ONLY / FULL / C2_ONLY / RSS_MAX.
"""

from __future__ import annotations

from collections import Counter
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

WORKSPACE = Path("/home/sat/mcrl-v025-multistep-ws")
PYTHON = "/home/sat/mcrl-leo-handover/.venv/bin/python"
SOURCE_ROOT = Path("/home/sat/mcrl-v025-c1c2suff-ws")
PILOT_PATH = SOURCE_ROOT / "scripts/run_v025_pilot_c3.py"
PILOT_SHA256 = "95103bb96caaa130659fa0d509f19409574b406798a173e278a7d9dac12b7435"
ORACLE_EE = Path("/home/sat/mcrl-v025-c2target-ws/.scratch/c2target/oracle_ee.py")
ORACLE_EE_SHA256 = "3a1ca6b40849ac0498fdb770ab8042c0447c743370a7838a74b76e7101a9bcdb"
CROWD_RUNNER = Path("/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run_crowding_cost.py")
CALIBRATION_PATH = (
    SOURCE_ROOT / "artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM"
    / "PILOT_NOT_CLAIM-calibration.json"
)
CORPUS93 = Path("/home/sat/mcrl-v025-exact93-ws/artifacts/exact-label-corpus-93-20260910")
C2TARGET_WORKERS = tuple(
    Path(f"/home/sat/mcrl-v025-c2target-ws/.scratch/c2target/oracle-ee-93-w{index}.json")
    for index in range(3)
)
THREAD_VARS = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
MAX_RSS_BYTES = 5_000_000_000
MAX_AS_BYTES = 4_900_000_000
HORIZON = 3
FULL48 = tuple(range(48))
CARRIERS = ("nearest-eligible", "stay-if-possible", "random-masked")
POLICIES = ("b_rss", "b_base", "a_hold")
EXPECTED_PARITY = {"RSS_MAX": 41.621560, "CROWDED": 46.110374}
EXPECTED_PARITY_EXACT = {  # COORDVALUE / BASIN2 / CROWDCOST receipts
    "RSS_MAX": (1_653_612_586_626.6667, 39_729.71205047168),
    "CROWDED": (1_072_637_748_181.2688, 23_262.395146143634),
}
SCALAR_CALLS = {"count": 0}


# --------------------------------------------------------------------- runtime
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


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


def cap_address_space() -> None:
    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = MAX_AS_BYTES if hard == resource.RLIM_INFINITY else min(MAX_AS_BYTES, hard)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_pilot():
    if sha256(PILOT_PATH) != PILOT_SHA256:
        raise RuntimeError("sealed pilot changed")
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
    pilot = load_module(f"multistep_pilot_{os.getpid()}", PILOT_PATH)
    if pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK is not True:
        raise RuntimeError("pilot fallback flag is not the on-disk default")
    return pilot


def install_scalar_stub(engine) -> None:
    original = engine.StepEvaluator.evaluate

    def forbidden(*args, **kwargs):
        del args, kwargs
        SCALAR_CALLS["count"] += 1
        raise AssertionError("scalar StepEvaluator.evaluate is forbidden on MULTISTEP surfaces")

    forbidden.__name__ = "scalar_evaluate_forbidden_on_multistep"
    forbidden.__wrapped__ = original
    engine.StepEvaluator.evaluate = forbidden
    assert engine.StepEvaluator.evaluate is forbidden


def build_tape(pilot, world_index: int):
    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape

    return build_world_tape(
        domain=pilot.TRAIN_WORLDS[world_index - 1],
        provider=LegacyWorldProvider(role="pilot-source"),
        steps=33,
        start_time_s=0.0,
    )


# --------------------------------------------------------------- configuration
def cid_digest(config) -> str:
    return hashlib.sha256(config.configuration_id.encode("ascii")).hexdigest()


def legal_sets(engine, tape, step: int):
    options, _ = engine._legal_options(tape, step)
    return options, {user: frozenset(rows) for user, rows in options.items()}


def rss_mapping(engine, tape, step: int, options) -> dict:
    """RSS_MAX exactly as BASIN2 / COORDVALUE / CLEANPATH construct it."""
    arrays = tape.steps[step].arrays
    if arrays is None:
        raise RuntimeError("dense primitive arrays are required")
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
    return mapping


def crowded_mapping(crowd, options) -> dict:
    """CROWDCOST most-crowded endpoint: exact minimum cover, then coverage-first."""
    cover = crowd.minimum_cover(options)
    return crowd.assignment_for_beams(options, cover)


def continue_mapping(policy: str, previous: dict, legal: dict, rss: dict, base_map: dict) -> dict:
    if policy == "b_rss":
        return dict(rss)
    if policy == "b_base":
        return dict(base_map)
    if policy == "a_hold":
        result = {}
        for user in sorted(previous):
            held = previous[user]
            if held is not None and held in legal[user]:
                result[user] = held
            else:
                result[user] = rss[user]
        return result
    raise ValueError(policy)


def change_census(engine, before, after, rekeyed) -> dict:
    events = engine._physical_events(before, after, cell_rekeyed_users=rekeyed)
    counts = Counter(event.kind for event in events)
    phi = engine._phi_for(before, after, cell_rekeyed_users=rekeyed)
    return {
        "counts": dict(sorted(counts.items())),
        "association_changes": counts.get("beam_change", 0) + counts.get("satellite_change", 0)
        + counts.get("cell_rekey", 0),
        "phi_qos_preference": float(phi),
    }


def load_calibration(pilot):
    payload = json.loads(CALIBRATION_PATH.read_text())

    def ratio(name):
        numerator, denominator = payload[name]
        return Fraction(numerator, denominator)

    return pilot.PilotCalibration(
        eta_ref=ratio("eta_ref"),
        lambda_bits_per_j=ratio("lambda_bits_per_j"),
        kappa_bits_per_user_step=ratio("kappa_bits_per_user_step"),
        bits_ref=ratio("bits_ref"),
        joules_ref=ratio("joules_ref"),
        users=int(payload["users"]),
    )


def metric(profile) -> dict:
    attained = profile.score.rate_target_attained
    if attained is None:
        raise RuntimeError("rate-target attainment is absent from the cell score")
    served = profile.score.served_phy
    return {
        "bits": float(profile.bits),
        "joules": float(profile.joules),
        "served": int(sum(bool(value) for value in served.values())),
        "attained": int(sum(bool(value) for value in attained.values())),
        "users": int(len(attained)),
        "certificate_status": profile.certificate_status,
        "invalid": False,
    }


def fresh_endpoint(engine, tape, setting, run_setting, step: int, transition_from, configs, base):
    """ONE fresh realised dense full-48 evaluator; BASE inside the one batch."""
    if tape.steps[step].arrays is None:
        raise RuntimeError(f"step {step} has no dense primitive arrays")
    if setting.label != "a-r0":
        raise RuntimeError("only the in-force a-r0 cell is scored")
    evaluator = engine.StepEvaluator(
        tape, setting, step,
        transition_from=transition_from,
        cell_rekeyed_users=engine._rekeyed_users(tape, step),
        field="realised",
        counter=engine.EvaluationCounter(),
        run_setting=run_setting,
        boundary_indices=FULL48,
    )
    assert evaluator.boundary_indices == FULL48 and evaluator.field == "realised"
    assert not evaluator._evaluated
    batch = {base.configuration_id: base}
    for config in configs:
        batch.setdefault(config.configuration_id, config)
    evaluator.evaluate_many(tuple(batch.values()))
    if base.configuration_id not in evaluator._evaluated:
        raise RuntimeError("BASE did not populate through evaluate_many")
    return evaluator


def read_profile(evaluator, config) -> dict:
    profile = evaluator._evaluated.get(config.configuration_id)
    if profile is None:
        if config.configuration_id in evaluator._invalid:
            return {"invalid": True, "bits": 0.0, "joules": 0.0, "served": 0,
                    "attained": 0, "users": 0, "certificate_status": "INVALID"}
        raise RuntimeError("profile absent from the dense cache")
    return metric(profile)


# ------------------------------------------------------------------ core loop
def score_anchor(engine, tape, setting, run_setting, *, step: int, carrier: str,
                 arms: dict, probe_arms=(), probe_policies=()):
    """arms: name -> step-t Configuration.  Returns the per-step record."""
    base_t = engine._base_configuration(tape, step, carrier)
    incumbent = engine._base_configuration(tape, max(0, step - 1), carrier)
    if tape.steps[step + HORIZON].arrays is None:
        raise RuntimeError("horizon runs past the dense tape")

    # ---- step t: exactly the existing single-step endpoint construction
    evaluator = fresh_endpoint(
        engine, tape, setting, run_setting, step, incumbent, tuple(arms.values()), base_t,
    )
    step_t = {name: read_profile(evaluator, config) for name, config in arms.items()}
    base_t_metric = read_profile(evaluator, base_t)
    rekeyed_t = engine._rekeyed_users(tape, step)
    changes_t = {name: change_census(engine, incumbent, config, rekeyed_t)
                 for name, config in arms.items()}
    del evaluator

    record = {
        "step_index": step,
        "carrier": carrier,
        "base_by_offset": [dict(base_t_metric, cid_sha256=cid_digest(base_t))],
        "arms": {},
        "probes": [],
    }
    current = {(name, policy): config for name, config in arms.items() for policy in POLICIES}
    for name in arms:
        record["arms"][name] = {
            policy: [dict(step_t[name], offset=0, step=step,
                          cid_sha256=cid_digest(arms[name]), **changes_t[name])]
            for policy in POLICIES
        }

    previous_base = base_t
    for offset in range(1, HORIZON + 1):
        s = step + offset
        base_s = engine._base_configuration(tape, s, carrier)
        options, legal = legal_sets(engine, tape, s)
        rss = rss_mapping(engine, tape, s, options)
        rekeyed = engine._rekeyed_users(tape, s)
        nxt = {}
        for (name, policy), prev in current.items():
            mapping = continue_mapping(policy, prev.mapping, legal, rss, base_s.mapping)
            nxt[(name, policy)] = engine._configuration(base_s, mapping, kind=f"multistep-{policy}")
        evaluator = fresh_endpoint(
            engine, tape, setting, run_setting, s, previous_base, tuple(nxt.values()), base_s,
        )
        record["base_by_offset"].append(dict(read_profile(evaluator, base_s),
                                             cid_sha256=cid_digest(base_s)))
        for (name, policy), config in nxt.items():
            row = read_profile(evaluator, config)
            row.update(offset=offset, step=s, cid_sha256=cid_digest(config),
                       **change_census(engine, current[(name, policy)], config, rekeyed))
            record["arms"][name][policy].append(row)
        # Invariance probe: the same step-s configuration scored on TWO fresh
        # evaluators with IDENTICAL batches (BASE_s, config) that differ only
        # in transition_from: the arm's OWN previous-step configuration versus
        # the carrier BASE at s-1.  Exactly equal bits/joules => an association
        # change carries no physical cost in this path.  (Batch composition
        # itself moves results at the last ulp, so the probe never compares
        # across different batches; that ulp gap to the primary is recorded.)
        if offset == 1:
            for name in probe_arms:
                for policy in probe_policies:
                    config = nxt[(name, policy)]
                    own = current[(name, policy)]
                    probe_own = fresh_endpoint(
                        engine, tape, setting, run_setting, s, own, (config,), base_s,
                    )
                    got_own = read_profile(probe_own, config)
                    del probe_own
                    probe_car = fresh_endpoint(
                        engine, tape, setting, run_setting, s, previous_base, (config,), base_s,
                    )
                    got_car = read_profile(probe_car, config)
                    del probe_car
                    ref = record["arms"][name][policy][offset]
                    record["probes"].append({
                        "arm": name, "policy": policy, "step": s,
                        "transition_from": "arm's own step-t configuration vs carrier BASE(s-1)",
                        "association_changes_vs_own": ref["association_changes"],
                        "association_changes_own_vs_carrier_incumbent": change_census(
                            engine, previous_base, own, rekeyed)["association_changes"],
                        "bits_equal": got_own["bits"] == got_car["bits"],
                        "joules_equal": got_own["joules"] == got_car["joules"],
                        "bits": got_own["bits"], "joules": got_own["joules"],
                        "rel_gap_to_primary_batch_bits": abs(got_own["bits"] / ref["bits"] - 1.0),
                        "rel_gap_to_primary_batch_joules": abs(got_own["joules"] / ref["joules"] - 1.0),
                    })
        del evaluator
        current = nxt
        previous_base = base_s
        gc.collect()
    return record


# ------------------------------------------------- C2 forecast validity (v1.9.5)
SURFACES = {
    "nominal_b0": ("nominal", (0,)),    # the predictor the corpus C2 label uses
    "nominal_48": ("nominal", FULL48),  # same field, full integration
    "realised_b0": ("realised", (0,)),  # same integration as the predictor, realised field
    "realised_48": ("realised", FULL48),  # the endpoint
}


def forecast_validity(engine, tape, setting, run_setting, calibration, *, step, carrier, profiles):
    """v1.9 item 5 / v1.6 section 2(b).

    For each named step-t profile, hold it at t+1..t+3 exactly as the sealed
    forecast does (persist physical identities; an absent identity makes the
    offset invalid) and evaluate it on four surfaces.  The predicted change is
    the nominal boundary-0 snapshot the corpus C2 label is built from; the
    realised change is this endpoint's realised full-48 integral.  Their
    difference is split per offset into an integration error (same field,
    boundary-0 -> 48 boundaries) and a fading error (same integration,
    nominal -> realised field).
    """
    from mcrl.physics_v025.targets import c2_persistence_forecast

    eta = calibration.eta_ref
    per_offset = {name: [] for name in profiles}
    projections = {name: {surface: [] for surface in SURFACES} for name in profiles}
    for offset in range(1, HORIZON + 1):
        s = step + offset
        base_s = engine._base_configuration(tape, s, carrier)
        held = {
            name: engine._configuration(base_s, config.mapping, kind=f"multistep-held-{name}")
            for name, config in profiles.items()
        }
        changed = {
            name: tuple(u for u in config.mapping if config.mapping[u] != base_s.mapping.get(u))
            for name, config in held.items()
        }
        rows = {}
        for surface, (field, boundaries) in SURFACES.items():
            evaluator = engine.StepEvaluator(
                tape, setting, s,
                transition_from=base_s,
                cell_rekeyed_users=engine._rekeyed_users(tape, s),
                field=field,
                counter=engine.EvaluationCounter(),
                run_setting=run_setting,
                boundary_indices=boundaries,
            )
            batch = {base_s.configuration_id: base_s}
            for config in held.values():
                batch.setdefault(config.configuration_id, config)
            evaluator.evaluate_many(tuple(batch.values()))
            if base_s.configuration_id not in evaluator._evaluated:
                raise RuntimeError("relevant BASE did not populate through evaluate_many")
            rows[surface] = {}
            for name, config in held.items():
                prof = evaluator._evaluated.get(config.configuration_id)
                survives = prof is not None and all(
                    prof.score.served_phy.get(user, False) for user in changed[name]
                )
                projections[name][surface].append(
                    engine._projection_from_profile(offset=offset, profile=prof, survives=survives)
                )
                rows[surface][name] = {
                    "valid": prof is not None,
                    "survives": bool(survives),
                    "bits": 0.0 if prof is None else float(prof.bits),
                    "joules": 0.0 if prof is None else float(prof.joules),
                    "served": 0 if prof is None else int(sum(bool(v) for v in prof.score.served_phy.values())),
                    "attained": 0 if prof is None else int(sum(
                        bool(v) for v in prof.score.rate_target_attained.values())),
                    "changed_users": len(changed[name]),
                }
            del evaluator
            gc.collect()
        for name in profiles:
            entry = {"offset": offset, "step": s, "surfaces": {s2: rows[s2][name] for s2 in SURFACES}}
            for surface in SURFACES:
                cand, base_row = rows[surface][name], rows[surface]["BASE"]
                entry[f"delta_f_{surface}"] = float(
                    Fraction(str(cand["bits"])) - Fraction(str(base_row["bits"]))
                    - eta * (Fraction(str(cand["joules"])) - Fraction(str(base_row["joules"])))
                )
            entry["error_total"] = entry["delta_f_realised_48"] - entry["delta_f_nominal_b0"]
            entry["error_integration"] = entry["delta_f_nominal_48"] - entry["delta_f_nominal_b0"]
            entry["error_fading"] = entry["delta_f_realised_48"] - entry["delta_f_nominal_48"]
            entry["error_fading_at_b0"] = entry["delta_f_realised_b0"] - entry["delta_f_nominal_b0"]
            entry["error_integration_realised"] = entry["delta_f_realised_48"] - entry["delta_f_realised_b0"]
            per_offset[name].append(entry)
    labels = {}
    for name in profiles:
        labels[name] = {}
        for surface in SURFACES:
            label = c2_persistence_forecast(
                projections[name][surface], projections["BASE"][surface],
                lambda_bits_per_j=calibration.lambda_bits_per_j,
                eta_ref=calibration.eta_ref,
                kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
                horizon_offsets=run_setting.c2_horizon_offsets,
            )
            labels[name][surface] = {
                "forecast_surplus_bits": float(label.forecast_surplus_bits),
                "lost_offsets": int(label.lost_offsets),
                "persistence_penalty_bits": float(label.persistence_penalty_bits),
                "normalized_total_kappa": float(label.normalized_total),
            }
    return {"per_offset": per_offset, "c2_labels": labels}


# ------------------------------------------------------------------ mode: panel
def run_panel(out_path: Path, anchor_limit: int | None) -> int:
    check_runtime()
    cap_address_space()
    started = time.perf_counter()
    pilot = load_pilot()
    engine = pilot.ENGINE
    install_scalar_stub(engine)
    crowd = load_module("multistep_crowd", CROWD_RUNNER)
    setting = engine._setting("a-r0")
    run_setting = engine.run_setting_for("a-r0")
    tape = build_tape(pilot, 1)
    check_runtime()
    print(f"tape built in {time.perf_counter()-started:.1f}s peak RSS {peak_rss_bytes()/2**30:.3f} GiB", flush=True)

    anchors = [(index // 3, CARRIERS[index % 3], index) for index in range(12)]
    if anchor_limit is not None:
        anchors = anchors[:anchor_limit]
    records = []
    for position, (step, carrier, index) in enumerate(anchors, start=1):
        t0 = time.perf_counter()
        options, _legal = legal_sets(engine, tape, step)
        base = engine._base_configuration(tape, step, carrier)
        arms = {
            "BASE": base,
            "RSS_MAX": engine._configuration(base, rss_mapping(engine, tape, step, options), kind="multistep-rss-max"),
            "CROWDED": engine._configuration(base, crowded_mapping(crowd, options), kind="multistep-crowded"),
        }
        record = score_anchor(
            engine, tape, setting, run_setting, step=step, carrier=carrier, arms=arms,
            probe_arms=("RSS_MAX", "CROWDED", "BASE"), probe_policies=("b_rss", "a_hold"),
        )
        record.update(global_anchor_index=index, world_index=1, world_id=tape.domain,
                      wall_s=time.perf_counter() - t0)
        records.append(record)
        check_runtime()
        print(f"anchor {position}/{len(anchors)} (world 1 step {step} {carrier}) "
              f"{record['wall_s']:.1f}s peak RSS {peak_rss_bytes()/2**30:.3f} GiB", flush=True)

    # ---- parity gate on the step-t component
    parity = {}
    for name in ("RSS_MAX", "CROWDED", "BASE"):
        bits = math.fsum(r["arms"][name]["b_rss"][0]["bits"] for r in records)
        joules = math.fsum(r["arms"][name]["b_rss"][0]["joules"] for r in records)
        parity[name] = {"bits": bits, "joules": joules, "ee_mbit_per_j": bits / joules / 1e6,
                        "served": sum(r["arms"][name]["b_rss"][0]["served"] for r in records),
                        "users": sum(r["arms"][name]["b_rss"][0]["users"] for r in records)}
    parity_status = "SKIPPED_PARTIAL" if len(records) != 12 else "PASS"
    if len(records) == 12:
        for name, expected in EXPECTED_PARITY.items():
            if round(parity[name]["ee_mbit_per_j"], 6) != round(expected, 6):
                parity_status = f"FAIL:{name}"
    probes_ok = all(p["bits_equal"] and p["joules_equal"] for r in records for p in r["probes"])
    result = {
        "schema": "mcrl-v025-multistep-panel-v1",
        "status": "DIAGNOSTIC_NOT_CLAIM",
        "learner_free": True,
        "anchors": len(records),
        "parity": {"status": parity_status, "pooled": parity,
                   "expected_rounded_six": EXPECTED_PARITY,
                   "expected_exact_receipts": EXPECTED_PARITY_EXACT},
        "invariance_probes_all_equal": probes_ok,
        "invariance_probe_count": sum(len(r["probes"]) for r in records),
        "scalar_evaluate_calls": SCALAR_CALLS["count"],
        "policies": POLICIES,
        "records": records,
        "peak_rss_bytes": peak_rss_bytes(),
        "wall_s": time.perf_counter() - started,
        "python": sys.executable,
        "niceness": os.getpriority(os.PRIO_PROCESS, 0),
        "thread_pins": {name: os.environ.get(name) for name in THREAD_VARS},
    }
    out_path.write_text(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps({"parity": result["parity"], "probes_ok": probes_ok,
                      "scalar_calls": SCALAR_CALLS["count"]}, indent=1, sort_keys=True), flush=True)
    print(f"PEAK_RSS_BYTES={peak_rss_bytes()}", flush=True)
    if SCALAR_CALLS["count"]:
        raise RuntimeError("scalar evaluate was called")
    if parity_status.startswith("FAIL"):
        raise RuntimeError(f"STOP: parity {parity_status}")
    return 0


# ------------------------------------------------------------ mode: select (A)
def run_select(worker: int, workers: int, out_path: Path) -> int:
    """Rebuild the C2TARGET exact-label picks with oracle_ee.py's own functions.

    The glue below is copied from oracle_ee.run (the selection half only); the
    scoring shape, argmax and tie-break are oracle_ee.argmax_config /
    oracle_ee.read_anchor_labels.  The sealed catalogue builder
    _catalogue_with_census uses scalar evaluate on its OWN internal nominal
    evaluator; no endpoint evaluator exists in this process.
    """
    check_runtime()
    cap_address_space()
    if sha256(ORACLE_EE) != ORACLE_EE_SHA256:
        raise RuntimeError("oracle_ee.py changed")
    oracle = load_module("multistep_oracle_ee", ORACLE_EE)
    pilot = oracle.load_pilot()
    if sha256(PILOT_PATH) != PILOT_SHA256:
        raise RuntimeError("sealed pilot changed")
    engine = pilot.ENGINE
    setting = engine._setting("a-r0")
    run_setting = engine.run_setting_for("a-r0")
    calibration = oracle.load_calibration(pilot)

    recorded = {}
    for path in C2TARGET_WORKERS:
        for row in json.loads(path.read_text())["records"]:
            recorded[int(row["global_anchor_index"])] = {
                arm: row["arms"][arm]["configuration_id"] for arm in ("BASE", "C1_ONLY", "FULL", "C2_ONLY")
            }

    every = sorted(
        CORPUS93.glob("views/world-*/BUILD_NOT_CLAIM-exact-source-anchor-*.jsonl"),
        key=lambda p: (p.parent.name, p.name),
    )
    if len(every) != 93:
        raise RuntimeError(f"expected 93 shards, found {len(every)}")
    shards = [path for index, path in enumerate(every) if index % workers == worker]
    tape = None
    tape_world = None
    picks = []
    for position, shard in enumerate(shards, start=1):
        t0 = time.perf_counter()
        header, labels, incumbent_action = oracle.read_anchor_labels(shard)
        world_index = int(header["world_index"])
        if tape_world != world_index:
            tape = None
            gc.collect()
            tape = build_tape(pilot, world_index)
            tape_world = world_index
        if header["world_id"] != tape.domain:
            raise RuntimeError("world mismatch")
        step = int(header["step_index"])
        carrier = header["carrier"]
        base = engine._base_configuration(tape, step, carrier)
        base_map = base.mapping
        for user, identity in base_map.items():
            if incumbent_action.get(user, "absent") != identity:
                raise RuntimeError("corpus incumbent disagrees with BASE")
            if labels[(user, identity)]["c1"] != 0.0:
                raise RuntimeError("incumbent C1 label is not zero")
        catalogue, census = engine._catalogue_with_census(
            tape, step, base, setting=setting, calibration=calibration, run_setting=run_setting,
        )
        covered = [c for c in catalogue if all((u, c.mapping[u]) in labels for u in c.mapping)]
        base_c1 = {u: labels[(u, base_map[u])]["c1"] for u in base_map}
        base_c2 = {u: labels[(u, base_map[u])]["c2"] for u in base_map}
        scores = {"C1_ONLY": [], "FULL": [], "C2_ONLY": []}
        for config in covered:
            mapping = config.mapping
            d1 = math.fsum(labels[(u, mapping[u])]["c1"] - base_c1[u] for u in mapping)
            d2 = math.fsum(labels[(u, mapping[u])]["c2"] - base_c2[u] for u in mapping)
            scores["C1_ONLY"].append((d1, config.configuration_id, config))
            scores["FULL"].append((d1 + d2, config.configuration_id, config))
            scores["C2_ONLY"].append((d2, config.configuration_id, config))
        selections = {arm: oracle.argmax_config(scores[arm]) for arm in scores}
        # C2's exact label ranks these highest / lowest over the same catalogue.
        # argmin mirrors argmax_config's rule: worst score, tie-break lowest id.
        selections["C2_WORST"] = min(scores["C2_ONLY"], key=lambda row: (row[0], row[1]))[2]
        index = int(header["global_anchor_index"])
        match = {arm: selections[arm].configuration_id == recorded[index][arm]
                 for arm in ("C1_ONLY", "FULL", "C2_ONLY")}
        match["BASE"] = base.configuration_id == recorded[index]["BASE"]
        if not all(match.values()):
            raise RuntimeError(f"pick differs from C2TARGET receipt at anchor {index}: {match}")
        picks.append({
            "global_anchor_index": index,
            "world_index": world_index,
            "world_id": header["world_id"],
            "step_index": step,
            "carrier": carrier,
            "shard": shard.name,
            "catalogue_size": len(catalogue),
            "catalogue_covered": len(covered),
            "c2target_pick_match": match,
            "picks": {
                arm: {
                    "assignments": [[u, None if i is None else list(i)] for u, i in cfg.assignments],
                    "configuration_id_sha256": cid_digest(cfg),
                    "kind": cfg.kind,
                    "changed_users": int(cfg.changed_users),
                    "c1_score": next(v for v, cid, _c in scores["C1_ONLY"] if cid == cfg.configuration_id),
                    "c2_score": next(v for v, cid, _c in scores["C2_ONLY"] if cid == cfg.configuration_id),
                }
                for arm, cfg in selections.items()
            },
            "c2_score_range": [min(v for v, _c, _g in scores["C2_ONLY"]),
                               max(v for v, _c, _g in scores["C2_ONLY"])],
        })
        check_runtime()
        print(f"anchor {position}/{len(shards)} (global {index}) {time.perf_counter()-t0:.1f}s "
              f"match={all(match.values())} peak RSS {peak_rss_bytes()/2**30:.3f} GiB", flush=True)
        del catalogue, covered, scores, labels
        gc.collect()
    out_path.write_text(json.dumps({"schema": "mcrl-v025-multistep-oracle-picks-v1",
                                    "worker": worker, "workers": workers,
                                    "picks": picks, "peak_rss_bytes": peak_rss_bytes()},
                                   indent=1, sort_keys=True))
    print(f"PEAK_RSS_BYTES={peak_rss_bytes()}", flush=True)
    return 0


# ------------------------------------------------------------ mode: oracle (B)
def run_oracle(picks_path: Path, out_path: Path) -> int:
    check_runtime()
    cap_address_space()
    started = time.perf_counter()
    pilot = load_pilot()
    engine = pilot.ENGINE
    install_scalar_stub(engine)
    setting = engine._setting("a-r0")
    run_setting = engine.run_setting_for("a-r0")
    calibration = load_calibration(pilot)
    payload = json.loads(picks_path.read_text())
    rows = sorted(payload["picks"], key=lambda r: (r["world_index"], r["global_anchor_index"]))
    tape = None
    tape_world = None
    records = []
    for position, row in enumerate(rows, start=1):
        t0 = time.perf_counter()
        if tape_world != row["world_index"]:
            tape = None
            gc.collect()
            tape = build_tape(pilot, row["world_index"])
            tape_world = row["world_index"]
        if row["world_id"] != tape.domain:
            raise RuntimeError("world mismatch")
        step, carrier = int(row["step_index"]), row["carrier"]
        base = engine._base_configuration(tape, step, carrier)
        options, _legal = legal_sets(engine, tape, step)
        arms = {"BASE": base}
        for arm in ("C1_ONLY", "FULL", "C2_ONLY", "C2_WORST"):
            spec = row["picks"][arm]
            mapping = {int(u): None if i is None else (int(i[0]), int(i[1])) for u, i in spec["assignments"]}
            config = engine._configuration(base, mapping, kind=spec["kind"])
            if cid_digest(config) != spec["configuration_id_sha256"]:
                raise RuntimeError("pick did not round-trip")
            arms[arm] = config
        arms["RSS_MAX"] = engine._configuration(base, rss_mapping(engine, tape, step, options),
                                                kind="multistep-rss-max")
        record = score_anchor(
            engine, tape, setting, run_setting, step=step, carrier=carrier, arms=arms,
            probe_arms=("C1_ONLY", "FULL"), probe_policies=("a_hold",),
        )
        record["forecast"] = forecast_validity(
            engine, tape, setting, run_setting, calibration,
            step=step, carrier=carrier,
            profiles={name: arms[name] for name in
                      ("BASE", "RSS_MAX", "C1_ONLY", "FULL", "C2_ONLY", "C2_WORST")},
        )
        record.update(global_anchor_index=row["global_anchor_index"], world_index=row["world_index"],
                      world_id=row["world_id"], wall_s=time.perf_counter() - t0,
                      full_differs_from_c1_only=(arms["FULL"].configuration_id
                                                 != arms["C1_ONLY"].configuration_id))
        records.append(record)
        check_runtime()
        print(f"anchor {position}/{len(rows)} (global {row['global_anchor_index']}) "
              f"{record['wall_s']:.1f}s peak RSS {peak_rss_bytes()/2**30:.3f} GiB", flush=True)
        gc.collect()
    probes_ok = all(p["bits_equal"] and p["joules_equal"] for r in records for p in r["probes"])
    result = {
        "schema": "mcrl-v025-multistep-oracle-v1",
        "status": "DIAGNOSTIC_NOT_CLAIM",
        "learner_free": True,
        "anchors": len(records),
        "invariance_probes_all_equal": probes_ok,
        "invariance_probe_count": sum(len(r["probes"]) for r in records),
        "scalar_evaluate_calls": SCALAR_CALLS["count"],
        "policies": POLICIES,
        "records": records,
        "peak_rss_bytes": peak_rss_bytes(),
        "wall_s": time.perf_counter() - started,
        "picks_file": str(picks_path),
        "picks_sha256": sha256(picks_path),
    }
    out_path.write_text(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps({"anchors": len(records), "probes_ok": probes_ok,
                      "scalar_calls": SCALAR_CALLS["count"]}), flush=True)
    print(f"PEAK_RSS_BYTES={peak_rss_bytes()}", flush=True)
    if SCALAR_CALLS["count"]:
        raise RuntimeError("scalar evaluate was called")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "panel":
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
        raise SystemExit(run_panel(Path(sys.argv[2]), limit))
    if mode == "select":
        raise SystemExit(run_select(int(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])))
    if mode == "oracle":
        raise SystemExit(run_oracle(Path(sys.argv[2]), Path(sys.argv[3])))
    raise SystemExit(f"unknown mode {mode}")
