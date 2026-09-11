#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""C2TARGET Q2 — what a PERFECT oracle C2 is worth in realised pooled EE.

Learner-free.  The selector score is built from the sealed EXACT C1/C2 labels
in the 22-anchor exact-label corpus, exactly in the shape the deployed
selector uses them (per-user delta against the incumbent action row, summed
over users, argmax over the sealed bounded catalogue, tie-break on the lowest
configuration id).

Arms
  BASE       the carrier reference configuration a0 (no move)
  C1_ONLY    argmax over the catalogue of sum_u [C1(u,a) - C1(u,a0)]      <- DROP_C2 reference
  FULL       argmax of sum_u [(C1+C2)(u,a) - (C1+C2)(u,a0)]
  C2_ONLY    argmax of sum_u [C2(u,a) - C2(u,a0)]
  EE_B0_BEST the catalogue member with the highest REALISED boundary-0 EE
             (an achievable-within-catalogue ceiling, not a policy)

Mandatory evaluator rule
  * ONE fresh dense realised StepEvaluator(boundary_indices=(0,)) per anchor,
    with BASE entering through evaluate_many alongside every candidate.
  * ONE separate fresh realised dense full-48 StepEvaluator per anchor for
    endpoints, again with BASE inside the same evaluate_many batch.
  * On BOTH evaluators, the bound method ``evaluate`` is replaced by a raising
    stub immediately after construction, and the call counter is asserted to
    be zero at the end.  Nothing is ever read from a foreign cache.
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
CALIBRATION = (
    SOURCE_ROOT
    / "artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM"
    / "PILOT_NOT_CLAIM-calibration.json"
)
CORPUS = Path("/home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-corpus-20260910")
OUTDIR = Path("/home/sat/mcrl-v025-c2target-ws/.scratch/c2target")
PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python").resolve()
THREAD_VARS = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
MAX_AS_BYTES = 4_900_000_000
ARMS = ("BASE", "C1_ONLY", "FULL", "C2_ONLY", "EE_B0_BEST")


class EvaluateForbidden(RuntimeError):
    pass


def enforce() -> None:
    if Path(sys.executable).resolve() != PYTHON:
        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    if os.getpriority(os.PRIO_PROCESS, 0) < 16:
        raise RuntimeError("niceness below 16")
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
    name = f"c2target_pilot_{os.getpid()}"
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if module.PILOT_PRIMITIVE_SOURCE_FALLBACK is not True:
        raise RuntimeError("pilot fallback flag is not the on-disk default")
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
    """(user, identity) -> {'c1':float,'c2':float}, plus the per-user incumbent
    action identity, straight out of the sealed shard."""
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
    """scored: list of (score, configuration_id, config).  Mirrors
    _select_for_anchor: max score, tie-break lowest configuration id."""
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


def run(corpus: Path, worker: int, workers: int, out_name: str) -> int:
    enforce()
    started = time.perf_counter()
    pilot = load_pilot()
    engine = pilot.ENGINE
    setting = engine._setting("a-r0")
    run_setting = engine.run_setting_for("a-r0")
    calibration = load_calibration(pilot)

    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape

    every = sorted(
        corpus.glob("views/world-*/BUILD_NOT_CLAIM-exact-source-anchor-*.jsonl"),
        key=lambda p: (p.parent.name, p.name),
    )
    shards = [path for index, path in enumerate(every) if index % workers == worker]

    tape = None
    tape_world = None
    tape_wall = {}

    evaluate_calls = {"selection": 0, "endpoint": 0}
    records = []
    peak_kb = 0

    for shard in shards:
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
        covered = []
        uncovered = 0
        for config in catalogue:
            mapping = config.mapping
            if all((user, mapping[user]) in labels for user in mapping):
                covered.append(config)
            else:
                uncovered += 1

        base_c1 = {user: labels[(user, base_map[user])]["c1"] for user in base_map}
        base_c2 = {user: labels[(user, base_map[user])]["c2"] for user in base_map}
        scores = {"C1_ONLY": [], "FULL": [], "C2_ONLY": []}
        for config in covered:
            mapping = config.mapping
            d1 = math.fsum(
                labels[(user, mapping[user])]["c1"] - base_c1[user] for user in mapping
            )
            d2 = math.fsum(
                labels[(user, mapping[user])]["c2"] - base_c2[user] for user in mapping
            )
            scores["C1_ONLY"].append((d1, config.configuration_id, config))
            scores["FULL"].append((d1 + d2, config.configuration_id, config))
            scores["C2_ONLY"].append((d2, config.configuration_id, config))
        selections = {arm: argmax_config(scores[arm]) for arm in ("C1_ONLY", "FULL", "C2_ONLY")}

        # ---- selection comparison: ONE fresh dense realised boundary-0 evaluator
        selection = engine.StepEvaluator(
            tape, setting, step_index,
            transition_from=incumbent,
            cell_rekeyed_users=rekeyed,
            field="realised",
            run_setting=run_setting,
            boundary_indices=(0,),
        )

        def selection_stub(config, _counter=evaluate_calls):
            _counter["selection"] += 1
            raise EvaluateForbidden("scalar evaluate is forbidden on the selection evaluator")

        batch = {base.configuration_id: base}
        for config in covered:
            batch[config.configuration_id] = config
        selection.evaluate_many(tuple(batch.values()))
        selection.evaluate = selection_stub  # type: ignore[method-assign]

        if base.configuration_id not in selection._evaluated:
            raise RuntimeError("BASE did not populate through evaluate_many")
        b0 = {}
        for cid, config in batch.items():
            profile = selection._evaluated.get(cid)
            if profile is None:
                continue
            if profile.joules > 0.0:
                b0[cid] = (float(profile.bits) / float(profile.joules), config)
        ee_best_cid = min(b0, key=lambda cid: (-b0[cid][0], cid))
        selections["EE_B0_BEST"] = b0[ee_best_cid][1]
        selections["BASE"] = base

        b0_ranked = sorted(b0, key=lambda cid: (-b0[cid][0], cid))
        b0_rank = {cid: index for index, cid in enumerate(b0_ranked)}
        selection_b0 = {
            arm: {
                "configuration_id": selections[arm].configuration_id,
                "ee_bits_per_j": b0.get(selections[arm].configuration_id, (None, None))[0],
                "rank_of_realised_b0_ee": b0_rank.get(selections[arm].configuration_id),
                "catalogue_size_ranked": len(b0_ranked),
            }
            for arm in ARMS
        }
        arm_kind = {arm: selections[arm].kind for arm in ARMS}
        arm_score = {}
        for name in ("C1_ONLY", "FULL", "C2_ONLY"):
            by_cid = {cid: value for value, cid, _cfg in scores[name]}
            arm_score[name] = {
                "own_pick_score": by_cid.get(selections[name].configuration_id),
                "c1_only_pick_score": by_cid.get(selections["C1_ONLY"].configuration_id),
                "full_pick_score": by_cid.get(selections["FULL"].configuration_id),
                "base_score": by_cid.get(base.configuration_id),
            }

        del selection, b0, b0_rank, b0_ranked, batch
        gc.collect()

        # ---- endpoints: ONE separate fresh realised dense full-48 evaluator
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

        endpoint_batch = {}
        for arm in ARMS:
            endpoint_batch[selections[arm].configuration_id] = selections[arm]
        endpoint.evaluate_many(tuple(endpoint_batch.values()))
        endpoint.evaluate = endpoint_stub  # type: ignore[method-assign]
        if base.configuration_id not in endpoint._evaluated:
            raise RuntimeError("BASE did not populate through the endpoint evaluate_many")

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
            stats["kind"] = arm_kind[arm]
            stats["invalid"] = False
            stats["boundary_0"] = selection_b0[arm]
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
            "catalogue_mode": census.get("catalogue_mode"),
            "arms": arm_records,
            "arm_scores": arm_score,
            "full_differs_from_c1_only": (
                selections["FULL"].configuration_id != selections["C1_ONLY"].configuration_id
            ),
            "full_differs_from_base": (
                selections["FULL"].configuration_id != base.configuration_id
            ),
            "c1_only_differs_from_base": (
                selections["C1_ONLY"].configuration_id != base.configuration_id
            ),
            "anchor_wall_s": time.perf_counter() - anchor_started,
        })
        peak_kb = max(peak_kb, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        print(json.dumps({
            "anchor": int(header["global_anchor_index"]),
            "wall_s": round(records[-1]["anchor_wall_s"], 2),
            "catalogue": len(catalogue),
            "full_vs_c1_only_differs": records[-1]["full_differs_from_c1_only"],
            "peak_rss_kb": peak_kb,
        }), flush=True)
        del endpoint, endpoint_batch, selections, scores, labels
        gc.collect()

    pooled = {}
    for arm in ARMS:
        bits = math.fsum(
            row["arms"][arm]["bits"] for row in records if not row["arms"][arm]["invalid"]
        )
        joules = math.fsum(
            row["arms"][arm]["joules"] for row in records if not row["arms"][arm]["invalid"]
        )
        served = math.fsum(
            row["arms"][arm]["served_users"] for row in records if not row["arms"][arm]["invalid"]
        )
        attained = math.fsum(
            row["arms"][arm]["attained_users"] for row in records if not row["arms"][arm]["invalid"]
        )
        users = math.fsum(
            row["arms"][arm]["users"] for row in records if not row["arms"][arm]["invalid"]
        )
        pooled[arm] = {
            "bits": bits, "joules": joules,
            "pooled_ee_bits_per_j": None if joules == 0 else bits / joules,
            "pooled_ee_mbit_per_j": None if joules == 0 else bits / joules / 1e6,
            "served_fraction": served / users,
            "rate_target_attainment_fraction": attained / users,
        }

    result = {
        "status": "DIAGNOSTIC_NOT_CLAIM",
        "anchors": len(records),
        "tape_wall_s": tape_wall,
        "total_wall_s": time.perf_counter() - started,
        "evaluate_stub_calls": evaluate_calls,
        "pooled": pooled,
        "marginals": {
            "FULL_minus_C1_ONLY_mbit_per_j": (
                pooled["FULL"]["pooled_ee_mbit_per_j"] - pooled["C1_ONLY"]["pooled_ee_mbit_per_j"]
            ),
            "FULL_relative_to_C1_ONLY": (
                pooled["FULL"]["pooled_ee_bits_per_j"] / pooled["C1_ONLY"]["pooled_ee_bits_per_j"] - 1.0
            ),
            "FULL_relative_to_BASE": (
                pooled["FULL"]["pooled_ee_bits_per_j"] / pooled["BASE"]["pooled_ee_bits_per_j"] - 1.0
            ),
            "C1_ONLY_relative_to_BASE": (
                pooled["C1_ONLY"]["pooled_ee_bits_per_j"] / pooled["BASE"]["pooled_ee_bits_per_j"] - 1.0
            ),
            "EE_B0_BEST_relative_to_BASE": (
                pooled["EE_B0_BEST"]["pooled_ee_bits_per_j"] / pooled["BASE"]["pooled_ee_bits_per_j"] - 1.0
            ),
        },
        "anchors_where_full_differs_from_c1_only": sum(
            1 for row in records if row["full_differs_from_c1_only"]
        ),
        "records": records,
        "peak_rss_kb": peak_kb,
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / out_name).write_text(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=1, sort_keys=True))
    print(f"PEAK_RSS_KB={max(peak_kb, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))}")
    if evaluate_calls["selection"] or evaluate_calls["endpoint"]:
        raise RuntimeError(f"scalar evaluate was called: {evaluate_calls}")
    return 0


if __name__ == "__main__":
    corpus_arg = Path(sys.argv[1])
    worker_arg, workers_arg = int(sys.argv[2]), int(sys.argv[3])
    name_arg = sys.argv[4]
    raise SystemExit(run(corpus_arg, worker_arg, workers_arg, name_arg))
