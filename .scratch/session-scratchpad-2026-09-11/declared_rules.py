#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""C1VSGAIN addendum: the NINE BEAMCOUNT declared rules at cap 50, each scored
at the FULL-48 realised endpoint on the same 93 development anchors.

No selection of any kind happens here: every declared rule is a fixed
construction from the step's legal graph, and each one is carried to the
endpoint.  This separates the *declared rule* reference class from the
*search winner* reference class (BEAMCOUNT's CAP_050 winner), which the main
harness measures as GAIN_IN_SET_LADDER.

Evaluator rule: ONE fresh realised dense full-48 StepEvaluator per anchor,
BASE inside the single evaluate_many batch with all rule configurations;
``evaluate`` is then replaced by a raising stub and the counter asserted zero.
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

SOURCE_ROOT = Path("/home/sat/mcrl-v025-c1c2suff-ws")
RUNNER = SOURCE_ROOT / "scripts/run_v025_pilot_c3.py"
BEAMCOUNT = Path(
    "/home/sat/mcrl-v025-beamcount-ws/.scratch/beamcount/run_beamcount_sweep_frozen.py"
)
OUTDIR = Path("/home/sat/mcrl-v025-c1vsgain-ws/.scratch/c1vsgain")
PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python").resolve()
THREAD_VARS = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
MAX_AS_BYTES = 4_900_000_000
CAP = 50


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


def load_module(path: Path, tag: str):
    name = f"c1vsgain_{tag}_{os.getpid()}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def profile_stats(profile):
    served = profile.score.served_phy
    attained = profile.score.rate_target_attained
    users = len(served)
    return {
        "bits": float(profile.bits),
        "joules": float(profile.joules),
        "ee_bits_per_j": float(profile.bits) / float(profile.joules),
        "served_users": int(sum(1 for value in served.values() if value)),
        "attained_users": int(sum(1 for value in attained.values() if value)),
        "users": users,
    }


def run(corpus: Path, worker: int, workers: int, out_name: str) -> int:
    enforce()
    started = time.perf_counter()
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
    pilot = load_module(RUNNER, "pilot")
    bc = load_module(BEAMCOUNT, "beamcount")
    engine = pilot.ENGINE
    setting = engine._setting("a-r0")
    run_setting = engine.run_setting_for("a-r0")

    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape

    every = sorted(
        corpus.glob("views/world-*/BUILD_NOT_CLAIM-exact-source-anchor-*.jsonl"),
        key=lambda p: (p.parent.name, p.name),
    )
    shards = [path for index, path in enumerate(every) if index % workers == worker]

    tape = None
    tape_world = None
    calls = {"endpoint": 0}
    records = []
    peak_kb = 0
    step_cache: dict[int, dict] = {}

    partial_path = OUTDIR / f"{out_name}.partial"
    if partial_path.exists():
        resumed = json.loads(partial_path.read_text())
        records = resumed["records"]
        calls["endpoint"] += int(resumed["evaluate_stub_calls"]["endpoint"])
    done = {int(row["global_anchor_index"]) for row in records}

    for shard in shards:
        with shard.open() as handle:
            header = json.loads(handle.readline())
        anchor_index = int(header["global_anchor_index"])
        if anchor_index in done:
            continue
        expected = (shard.parent / (shard.name + ".sha256")).read_text().split()[0].strip()
        if sha256(shard) != expected:
            raise RuntimeError(f"sidecar mismatch: {shard}")
        anchor_started = time.perf_counter()
        world_index = int(header["world_index"])
        step_index = int(header["step_index"])
        carrier = header["carrier"]
        if tape_world != world_index:
            tape = None
            step_cache.clear()
            gc.collect()
            tape = build_world_tape(
                domain=pilot.TRAIN_WORLDS[world_index - 1],
                provider=LegacyWorldProvider(role="pilot-source"),
                steps=33, start_time_s=0.0,
            )
            tape_world = world_index
        if header["world_id"] != tape.domain:
            raise RuntimeError("world mismatch")

        base = engine._base_configuration(tape, step_index, carrier)
        incumbent = engine._base_configuration(tape, max(0, step_index - 1), carrier)
        rekeyed = engine._rekeyed_users(tape, step_index)

        if step_index not in step_cache:
            options, _census = engine._legal_options(tape, step_index)
            cover, _greedy = bc.minimum_cover(options)
            rank = len(bc.maximum_matching(options))
            all_beams = tuple(sorted({b for rows in options.values() for b in rows}))
            coverage = {b: sum(b in options[u] for u in options) for b in all_beams}
            arrays = tape.steps[step_index].arrays
            row_of = arrays._row_index()

            def gain_of(user, beam, _a=arrays, _r=row_of):
                return float(_a.nominal_gain[0, _r[(user, beam)]])

            beam_gain = {
                b: math.fsum(gain_of(u, b) for u in options if b in options[u])
                for b in all_beams
            }
            step_cache.clear()
            step_cache[step_index] = {
                "options": options, "cover": cover, "rank": rank,
                "coverage": coverage, "beam_gain": beam_gain, "gain_of": gain_of,
                "floor": len(cover),
            }
        state = step_cache[step_index]
        options, gain_of = state["options"], state["gain_of"]
        coverage, beam_gain = state["coverage"], state["beam_gain"]

        rules = {}
        for set_name, key in (
            ("S1_ascending_coverage", lambda b: (coverage[b], b)),
            ("S2_descending_coverage", lambda b: (-coverage[b], b)),
            ("S3_descending_nominal_gain", lambda b: (-beam_gain[b], b)),
        ):
            beams = bc.matroid_extension(options, state["cover"], key, CAP, state["rank"])
            for assign_name, mapping in (
                ("A1_coverage_first", bc.assignment_coverage_first(options, beams)),
                ("A2_max_nominal_gain", bc.assignment_max_gain(options, beams, gain_of)),
                ("A3_least_loaded", bc.assignment_least_loaded(options, beams)),
            ):
                rules[f"{set_name}|{assign_name}"] = (beams, mapping)
        rss_mapping = {}
        for user, identities in sorted(options.items()):
            if not identities:
                rss_mapping[user] = None
                continue
            rss_mapping[user] = min(
                enumerate(identities),
                key=lambda item: (-gain_of(user, item[1]), item[0]),
            )[1]
        rules["RSS_MAX"] = (
            tuple(sorted({v for v in rss_mapping.values() if v is not None})), rss_mapping
        )

        configs = {
            name: engine._configuration(base, mapping, kind=f"declared-{name}")
            for name, (_beams, mapping) in rules.items()
        }
        endpoint = engine.StepEvaluator(
            tape, setting, step_index,
            transition_from=incumbent, cell_rekeyed_users=rekeyed,
            field="realised", run_setting=run_setting,
            boundary_indices=tuple(range(48)),
        )
        batch = {base.configuration_id: base}
        for config in configs.values():
            batch[config.configuration_id] = config
        endpoint.evaluate_many(tuple(batch.values()))

        def endpoint_stub(config, _counter=calls):
            _counter["endpoint"] += 1
            raise EvaluateForbidden("scalar evaluate is forbidden")

        endpoint.evaluate = endpoint_stub  # type: ignore[method-assign]
        if base.configuration_id not in endpoint._evaluated:
            raise RuntimeError("BASE did not populate through evaluate_many")

        row = {
            "global_anchor_index": anchor_index,
            "world_index": world_index,
            "step_index": step_index,
            "carrier": carrier,
            "beam_floor": state["floor"],
            "cap": CAP,
            "rules": {},
        }
        base_profile = endpoint._evaluated[base.configuration_id]
        row["rules"]["BASE"] = {
            **profile_stats(base_profile),
            "active_beams": bc.mapping_stats(base.mapping)["active_beams_mapping"],
        }
        for name, config in configs.items():
            profile = endpoint._evaluated.get(config.configuration_id)
            if profile is None:
                row["rules"][name] = {"invalid": True}
                continue
            row["rules"][name] = {
                **profile_stats(profile),
                "active_beams": bc.mapping_stats(config.mapping)["active_beams_mapping"],
            }
        records.append(row)
        peak_kb = max(peak_kb, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        tmp = partial_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"records": records, "evaluate_stub_calls": calls}))
        tmp.replace(partial_path)
        print(json.dumps({
            "anchor": anchor_index, "k_of_n": f"{len(records)}/{len(shards)}",
            "wall_s": round(time.perf_counter() - anchor_started, 1),
            "peak_rss_kb": peak_kb,
            "S2A2_ee": row["rules"]["S2_descending_coverage|A2_max_nominal_gain"]["ee_bits_per_j"],
        }), flush=True)
        del endpoint, batch, configs
        gc.collect()

    names = ["BASE"] + [
        f"{s}|{a}" for s in (
            "S1_ascending_coverage", "S2_descending_coverage", "S3_descending_nominal_gain",
        ) for a in ("A1_coverage_first", "A2_max_nominal_gain", "A3_least_loaded")
    ] + ["RSS_MAX"]
    pooled = {}
    for name in names:
        rows = [row["rules"][name] for row in records if not row["rules"][name].get("invalid")]
        bits = math.fsum(r["bits"] for r in rows)
        joules = math.fsum(r["joules"] for r in rows)
        users = math.fsum(r["users"] for r in rows)
        pooled[name] = {
            "anchors": len(rows),
            "pooled_ee_mbit_per_j": bits / joules / 1e6,
            "served_fraction": math.fsum(r["served_users"] for r in rows) / users,
            "rate_target_attainment_fraction": math.fsum(r["attained_users"] for r in rows) / users,
            "mean_active_beams": math.fsum(r["active_beams"] for r in rows) / len(rows),
        }
    result = {
        "status": "DIAGNOSTIC_NOT_CLAIM",
        "cap": CAP,
        "anchors": len(records),
        "evaluate_stub_calls": calls,
        "total_wall_s": time.perf_counter() - started,
        "pooled": pooled,
        "records": records,
        "peak_rss_kb": peak_kb,
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / out_name).write_text(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=1, sort_keys=True))
    print(f"PEAK_RSS_KB={max(peak_kb, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))}")
    if calls["endpoint"]:
        raise RuntimeError(f"scalar evaluate was called: {calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]))
