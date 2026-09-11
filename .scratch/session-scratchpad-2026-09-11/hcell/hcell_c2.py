#!/usr/bin/env python3
"""HCELL step 4: oracle C2 under treatment H -- SINGLE-STEP version only.

DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM.  The multi-step endpoint
(/home/sat/mcrl-v025-multistep-ws) does not exist, so only the step-t
open-loop endpoint is available; no future-step split is possible.

Restricted to the 12 frozen development anchors (world 1, steps 0-3 x three
carriers), which are the first 12 shards of the digest-anchored 22-anchor
exact-label corpus used by C2TARGET.  Reuses C2TARGET's oracle_ee.py
(read_anchor_labels, argmax_config) and its selector shape:
    sum_u [label(u, a) - label(u, a0)], argmax over the sealed bounded
    catalogue, tie-break on the lowest configuration id.

Arms
  BASE      carrier reference
  C1_ONLY   exact a0 C1 labels (sealed corpus)                 [C2TARGET parity]
  FULL      exact a0 C1 + exact C2                             [C2TARGET parity]
  C1H_ONLY  H-cell exact C1: c1 - (R_H(cand) - R_H(a0)) / kappa, where R_H is the
            blackout removal of every interrupting event versus the declared
            incumbent on the corpus's own nominal boundary-0 snapshot profile
  FULLH     C1H + exact C2.  C2 is unchanged under H by construction in the
            persistence forecast: candidate and default are each HELD at
            t+1..t+3, so neither makes a physical association change after t.

Every arm is scored at the step-t realised full-48 endpoint under a0 and aH.

Evaluator rule: the sealed catalogue builder (which internally uses scalar
evaluate on its own cache, as disclosed by C2TARGET) runs for all 12 anchors
BEFORE the class-wide raising stub is installed; everything after that is
dense evaluate_many only: one fresh nominal boundary-(0,) relabel evaluator
per anchor with BASE + every corpus row configuration in one batch, one fresh
realised full-48 endpoint batch with BASE + all arms, and the two
single-boundary realised H side batches.
"""

from __future__ import annotations

from fractions import Fraction
import json
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hcell_common as hc  # noqa: E402

ORACLE_EE = Path("/home/sat/mcrl-v025-c2target-ws/.scratch/c2target/oracle_ee.py")
ORACLE_EE_SHA256 = "3a1ca6b40849ac0498fdb770ab8042c0447c743370a7838a74b76e7101a9bcdb"
CORPUS = Path("/home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-corpus-20260910")
C2T_WORKERS = tuple(Path(f"/home/sat/mcrl-v025-c2target-ws/.scratch/c2target/oracle-ee-93-w{i}.json")
                    for i in range(3))
OUTPUT = hc.SCRATCH / "hcell-c2-receipt.json"
ARMS = ("BASE", "C1_ONLY", "FULL", "C1H_ONLY", "FULLH")


def parse_configuration_id(cid: str) -> dict:
    if not cid.startswith("CFG:"):
        raise RuntimeError(f"unexpected configuration id {cid[:40]}")
    mapping = {}
    for part in cid[4:].split(";"):
        fields = part.split(":")
        user = int(fields[0])
        mapping[user] = None if fields[1] == "NULL" else (int(fields[1]), int(fields[2]))
    return mapping


def read_rows(shard: Path):
    """(user, identity) -> physics configuration id and exact C1 core fraction."""
    rows = {}
    with shard.open() as handle:
        header = json.loads(handle.readline())
        for line in handle:
            row = json.loads(line)
            user = int(row["user_id"])
            identity = (None if row["null_action"] else
                        (int(row["action"]["norad_id"]), int(row["action"]["beam_chain_id"])))
            view = row["exact_source_view"]
            numerator, denominator = view["c1_difference_surplus"]["core_bits"]["fraction"]
            rows[(user, identity)] = {
                "cid": view["physics_configuration_id"],
                "c1_core_bits": Fraction(numerator, denominator),
                "kappa": float.fromhex(row["kappa_normalization_bits_hex"]),
            }
    return header, rows


def main() -> int:
    hc.check_runtime()
    started = time.perf_counter()
    if hc.sha256(ORACLE_EE) != ORACLE_EE_SHA256:
        raise RuntimeError("C2TARGET oracle_ee.py changed")
    oracle = hc.load_module("hcell_c2target_oracle_ee", ORACLE_EE)
    ctx = hc.setup(with_crowd=False)
    runner = ctx.runner
    calibration = ctx.calibration
    kappa_cal = float(calibration.kappa_bits_per_user_step)
    eta = calibration.eta_ref
    frozen = hc.frozen_panel(ctx)
    c2t = {}
    for path in C2T_WORKERS:
        for record in json.loads(path.read_text())["records"]:
            c2t[int(record["global_anchor_index"])] = record
    tape, tape_record = hc.build_tape(ctx)
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB after tape", flush=True)
    setting = runner._setting("a-r0")

    # ---- Phase A: sealed catalogue construction (before the stub) ----------
    prepared = []
    for panel_row in frozen:
        index = int(panel_row["global_anchor_index"])
        step = int(panel_row["step_index"])
        carrier = str(panel_row["carrier"])
        shard = CORPUS / "views/world-1" / f"BUILD_NOT_CLAIM-exact-source-anchor-{index:03d}.jsonl"
        header, labels, incumbent_action = oracle.read_anchor_labels(shard)  # sidecar-checked
        _header2, rows = read_rows(shard)
        if (int(header["global_anchor_index"]) != index or int(header["step_index"]) != step
                or header["carrier"] != carrier or header["world_id"] != tape.domain):
            raise RuntimeError(f"corpus shard/panel mismatch at anchor {index}")
        base = runner._base_configuration(tape, step, carrier)
        incumbent = runner._base_configuration(tape, max(0, step - 1), carrier)
        for user, identity in base.mapping.items():
            if incumbent_action.get(user, "absent") != identity:
                raise RuntimeError("corpus incumbent action disagrees with BASE")
            if labels[(user, identity)]["c1"] != 0.0:
                raise RuntimeError("incumbent C1 label is not zero")
        catalogue, census = runner._catalogue_with_census(
            tape, step, base, setting=setting, calibration=calibration,
            run_setting=ctx.run_setting)
        covered = [c for c in catalogue
                   if all((u, c.mapping[u]) in labels for u in c.mapping)]
        prepared.append((index, step, carrier, shard.name, labels, rows, base, incumbent,
                         covered, len(catalogue), census.get("catalogue_mode")))
        print(f"catalogue anchor {index}: {len(catalogue)} members, {len(covered)} covered", flush=True)

    hc.install_scalar_stub(runner)
    payload = {"schema": "mcrl-v025-hcell-c2-single-step-v1", "status": "RUNNING",
               "claim_status": "DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM",
               "multistep_endpoint": "ABSENT: /home/sat/mcrl-v025-multistep-ws does not exist; single-step only",
               "corpus": str(CORPUS), "world_tape": tape_record, "sources": ctx.sources,
               "oracle_ee_sha256": ORACLE_EE_SHA256,
               "c2_under_h": "unchanged by construction (held continuation, no post-t association change)",
               "anchors": []}

    # ---- Phase B: stubbed dense measurement ---------------------------------
    for position, item in enumerate(prepared, 1):
        (index, step, carrier, shard_name, labels, rows, base, incumbent,
         covered, catalogue_size, catalogue_mode) = item
        kappas = {r["kappa"] for r in rows.values()}
        if len(kappas) != 1 or abs(next(iter(kappas)) - kappa_cal) > 1e-6 * kappa_cal:
            raise RuntimeError("corpus kappa disagrees with calibration")
        kappa = next(iter(kappas))

        # relabel evaluator: nominal boundary-0, BASE + every corpus row configuration
        row_configs = {}
        for key, row in rows.items():
            mapping = parse_configuration_id(row["cid"])
            config = runner._configuration(base, mapping, kind="hcell-c2-row")
            if config.configuration_id != row["cid"]:
                raise RuntimeError("row configuration id does not round-trip")
            row_configs[key] = config
        batch = {base.configuration_id: base}
        for config in row_configs.values():
            batch.setdefault(config.configuration_id, config)
        relabel = hc.fresh_evaluator(ctx, tape, step, incumbent, field="nominal", boundaries=(0,))
        relabel.evaluate_many(tuple(batch.values()))
        base_profile = relabel._evaluated.get(base.configuration_id)
        if base_profile is None:
            raise RuntimeError("BASE absent from relabel evaluator")
        base_removal = hc.h_removal_snapshot(
            ctx, hc.h_ledger(ctx, tape, step, incumbent, base), base_profile.score.bits)
        removal_cache = {}
        c1h = {}
        core_abs_diff = []
        core_exact = 0
        invalid_rows = 0
        for key, config in row_configs.items():
            profile = relabel._evaluated.get(config.configuration_id)
            if profile is None:
                invalid_rows += 1
                c1h[key] = labels[key]["c1"]
                continue
            core = (Fraction(str(profile.bits - base_profile.bits))
                    - eta * Fraction(str(profile.joules - base_profile.joules)))
            core_exact += int(core == rows[key]["c1_core_bits"])
            core_abs_diff.append(abs(float(core - rows[key]["c1_core_bits"])))
            if config.configuration_id not in removal_cache:
                removal_cache[config.configuration_id] = hc.h_removal_snapshot(
                    ctx, hc.h_ledger(ctx, tape, step, incumbent, config), profile.score.bits)
            delta_removal = removal_cache[config.configuration_id] - base_removal
            c1h[key] = labels[key]["c1"] - delta_removal / kappa
        del relabel
        hc.gc.collect()

        base_map = base.mapping
        base_c1 = {u: labels[(u, base_map[u])]["c1"] for u in base_map}
        base_c2 = {u: labels[(u, base_map[u])]["c2"] for u in base_map}
        base_c1h = {u: c1h[(u, base_map[u])] for u in base_map}
        scores = {"C1_ONLY": [], "FULL": [], "C1H_ONLY": [], "FULLH": []}
        for config in covered:
            m = config.mapping
            d1 = math.fsum(labels[(u, m[u])]["c1"] - base_c1[u] for u in m)
            d2 = math.fsum(labels[(u, m[u])]["c2"] - base_c2[u] for u in m)
            d1h = math.fsum(c1h[(u, m[u])] - base_c1h[u] for u in m)
            scores["C1_ONLY"].append((d1, config.configuration_id, config))
            scores["FULL"].append((d1 + d2, config.configuration_id, config))
            scores["C1H_ONLY"].append((d1h, config.configuration_id, config))
            scores["FULLH"].append((d1h + d2, config.configuration_id, config))
        selections = {arm: oracle.argmax_config(scores[arm]) for arm in scores}
        selections["BASE"] = base

        unique = {base.configuration_id: base}
        for arm in ARMS:
            unique.setdefault(selections[arm].configuration_id, selections[arm])
        endpoint_batch = tuple(unique.values())
        endpoint = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised",
                                      boundaries=tuple(range(48)))
        endpoint.evaluate_many(endpoint_batch)
        side0 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(0,))
        side0.evaluate_many(endpoint_batch)
        side1 = hc.fresh_evaluator(ctx, tape, step, incumbent, field="realised", boundaries=(1,))
        side1.evaluate_many(endpoint_batch)
        arms = {}
        for arm in ARMS:
            config = selections[arm]
            profile = endpoint._evaluated[config.configuration_id]
            r0, d0 = hc.per_user_rates(ctx, side0._evaluated[config.configuration_id])
            r1, d1 = hc.per_user_rates(ctx, side1._evaluated[config.configuration_id])
            ledger = hc.h_ledger(ctx, tape, step, incumbent, config)
            removed, _useful, _info = hc.h_removal_endpoint(ctx, ledger, r0, r1, d0, d1)
            arms[arm] = {"configuration_id": config.configuration_id, "kind": config.kind,
                         "changed_users_vs_base": int(config.changed_users),
                         "a0": hc.cell_metrics(ctx, profile),
                         "aH": hc.cell_metrics(ctx, profile, removed),
                         "events": hc.event_census(ctx, tape, step, incumbent, config)}
        ref = c2t[index]
        parity = {}
        for arm in ("BASE", "C1_ONLY", "FULL"):
            parity[arm] = {
                "configuration_id_match": arms[arm]["configuration_id"] == ref["arms"][arm]["configuration_id"],
                "bits_delta": arms[arm]["a0"]["bits"] - float(ref["arms"][arm]["bits"]),
                "joules_delta": arms[arm]["a0"]["joules"] - float(ref["arms"][arm]["joules"]),
            }
        by_cid = {arm: {cid: v for v, cid, _ in scores[arm]} for arm in scores}
        payload["anchors"].append({
            "global_anchor_index": index, "step_index": step, "carrier": carrier,
            "shard": shard_name, "catalogue_size": catalogue_size, "catalogue_covered": len(covered),
            "catalogue_mode": catalogue_mode,
            "relabel_rows": len(row_configs), "relabel_invalid_rows": invalid_rows,
            "c1_core_exact_fraction_matches": core_exact,
            "c1_core_max_abs_diff_bits": max(core_abs_diff) if core_abs_diff else None,
            "base_h_removal_snapshot_bits": base_removal,
            "arms": arms, "parity_vs_c2target": parity,
            "picks": {arm: selections[arm].configuration_id for arm in ARMS},
            "c1h_changes_c1_pick": selections["C1H_ONLY"].configuration_id != selections["C1_ONLY"].configuration_id,
            "fullh_changes_full_pick": selections["FULLH"].configuration_id != selections["FULL"].configuration_id,
            "full_differs_from_c1_only": selections["FULL"].configuration_id != selections["C1_ONLY"].configuration_id,
            "fullh_differs_from_c1h_only": selections["FULLH"].configuration_id != selections["C1H_ONLY"].configuration_id,
            "h_label_score_of_c1_pick_minus_c1h_pick": (
                by_cid["C1H_ONLY"][selections["C1_ONLY"].configuration_id]
                - by_cid["C1H_ONLY"][selections["C1H_ONLY"].configuration_id]),
            "peak_rss_bytes": hc.peak_rss_bytes(),
        })
        del endpoint, side0, side1
        hc.gc.collect()
        hc.check_runtime()
        payload["scalar_evaluate_calls"] = hc.SCALAR_CALLS["count"]
        hc.atomic_write(OUTPUT, payload)
        print(f"anchor {position}/{len(prepared)} completed peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB "
              f"core_exact={core_exact}/{len(row_configs)} parity="
              + json.dumps({a: [p['configuration_id_match'], round(p['bits_delta'], 3)] for a, p in parity.items()})
              + f" c1h_changes={payload['anchors'][-1]['c1h_changes_c1_pick']}"
              f" full!=c1={payload['anchors'][-1]['full_differs_from_c1_only']}", flush=True)

    pooled = {}
    for arm in ARMS:
        rows_ = [a["arms"][arm] for a in payload["anchors"]]
        pooled[arm] = {"a0": hc.pool_rows([r["a0"] for r in rows_]),
                       "aH": hc.pool_rows([r["aH"] for r in rows_]),
                       "h_events": sum(int(r["events"]["h_events"]) for r in rows_)}
    payload["pooled"] = pooled
    payload["scalar_evaluate_calls"] = hc.SCALAR_CALLS["count"]
    assert hc.SCALAR_CALLS["count"] == 0
    payload["status"] = "COMPLETE"
    payload["runtime"] = hc.runtime_record()
    payload["wall_seconds"] = time.perf_counter() - started
    payload["runner_sha256"] = hc.sha256(Path(__file__))
    hc.atomic_write(OUTPUT, payload)
    print(json.dumps({a: [pooled[a]["a0"]["ee_mbit_per_j"], pooled[a]["aH"]["ee_mbit_per_j"],
                          pooled[a]["h_events"]] for a in ARMS}, indent=1), flush=True)
    print(f"scalar_evaluate_calls={hc.SCALAR_CALLS['count']}", flush=True)
    print(f"peak RSS {hc.peak_rss_bytes()/2**30:.3f} GiB final ({hc.peak_rss_bytes()} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
