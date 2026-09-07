#!/usr/bin/env python3
"""Join the Stage 1b H-A and OPS-3 result files into one factual report.

Reads only; writes SCRATCH/oracle/stage1b-report.md.  Every decision string is
produced by applying the frozen contract's section 4 rules literally, with the
full boolean evidence printed beside it.  No efficacy language.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
CONTRACTS = HERE.parent / "contracts"
HA_DIR = HERE / "stage1b-HA-20260902"
OPS3_DIR = HERE / "stage1b-OPS3-20260902"
OUT = HERE / "stage1b-report.md"

BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 2026090299

WORLD_IDENTITY_FIELDS = (
    "initial_world_sha256",
    "initial_state_sha256",
    "initial_mask_sha256",
    "fading_field_sha256",
    "start_epoch",
)

ARM_ORDER = (
    "P1", "P2", "P3", "P12", "P13", "P23", "P123",
    "O2", "O12", "O23", "O123", "MAIN",
)

ROUTES = {
    "H-A": {
        "top": "P123",
        "directions": (("D-C2", "P123", "P13"), ("D-C3", "P123", "P12"), ("D-C1", "P123", "P23")),
        "guard_pairs": ("P13", "P12", "P23"),
        "arms": ("P1", "P2", "P3", "P12", "P13", "P23", "P123", "MAIN"),
    },
    "OPS-3": {
        "top": "O123",
        "directions": (("D-C2", "O123", "P13"), ("D-C3", "O123", "O12"), ("D-C1", "O123", "O23")),
        "guard_pairs": ("P13", "O12", "O23"),
        "arms": ("O2", "O12", "O23", "O123"),
    },
}


def sha256_file(path: Path) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            d.update(block)
    return d.hexdigest()


def load(path: Path) -> Mapping[str, Any]:
    return json.loads((path / "result.json").read_text())


def rows_by_arm(*results: Mapping[str, Any]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for result in results:
        for row in result["rows"]:
            out.setdefault(str(row["policy_label"]), []).append(row)
    return out


def pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"episodes": 0, "ee": None, "bits": 0.0, "energy": 0.0,
                "served": None, "hold": None, "infeasible": 0, "decisions": 0}
    bits = math.fsum(float(r["total_bits"]) for r in rows)
    energy = math.fsum(float(r["total_energy_j"]) for r in rows)
    served = sum(int(r["served_user_steps"]) for r in rows)
    dec = sum(int(r["decision_count"]) for r in rows)
    holds = sum(int(r["hold_decisions"]) for r in rows)
    infeas = sum(int(r["infeasible_hold_count"]) for r in rows)
    return {
        "episodes": len(rows), "ee": bits / energy, "bits": bits, "energy": energy,
        "served": served / dec, "hold": holds / dec, "infeasible": infeas,
        "decisions": dec,
    }


def subset(rows: Sequence[Mapping[str, Any]], *, lineage=None, world=None):
    out = list(rows)
    if lineage is not None:
        out = [r for r in out if r.get("initialization_seed") in (None, lineage)]
    if world is not None:
        out = [r for r in out if int(r["evaluation_seed"]) == int(world)]
    return out


def pct(left: Mapping[str, Any], right: Mapping[str, Any]) -> float | None:
    a, b = left.get("ee"), right.get("ee")
    if a is None or b is None or not b:
        return None
    return a / b - 1.0


def bootstrap(all_rows: Mapping[str, list], worlds, pairs) -> dict[str, Any]:
    idx: dict[str, dict[int, tuple[float, float]]] = {}
    for arm, rows in all_rows.items():
        per: dict[int, list] = {}
        for r in rows:
            per.setdefault(int(r["evaluation_seed"]), []).append(r)
        idx[arm] = {
            w: (math.fsum(float(x["total_bits"]) for x in v),
                math.fsum(float(x["total_energy_j"]) for x in v))
            for w, v in per.items()
        }
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    order = list(worlds)
    draws = rng.integers(0, len(order), size=(BOOTSTRAP_REPLICATES, len(order)))
    out = {}
    for label, left, right in pairs:
        if left not in idx or right not in idx:
            continue
        samples = np.empty(BOOTSTRAP_REPLICATES)
        for i in range(BOOTSTRAP_REPLICATES):
            picked = [order[j] for j in draws[i]]
            lb = math.fsum(idx[left][w][0] for w in picked)
            le = math.fsum(idx[left][w][1] for w in picked)
            rb = math.fsum(idx[right][w][0] for w in picked)
            re = math.fsum(idx[right][w][1] for w in picked)
            samples[i] = (lb / le) / (rb / re) - 1.0
        out[f"{label} {left} vs {right}"] = {
            "mean_pct": float(np.mean(samples)) * 100,
            "ci_lo_pct": float(np.percentile(samples, 2.5)) * 100,
            "ci_hi_pct": float(np.percentile(samples, 97.5)) * 100,
            "fraction_positive": float(np.mean(samples > 0.0)),
        }
    return out


def fmt(x, spec=".4f", none="n/a"):
    return none if x is None else format(x, spec)


def main() -> int:
    ha, ops3 = load(HA_DIR), load(OPS3_DIR)
    worlds = [int(s) for s in ha["evaluation_seeds"]]
    lineages = [int(s) for s in ha["initialization_seeds"]]
    if [int(s) for s in ops3["evaluation_seeds"]] != worlds:
        raise SystemExit("world seed lists differ between the two result files")
    if [int(s) for s in ops3["initialization_seeds"]] != lineages:
        raise SystemExit("lineage lists differ between the two result files")

    # ---- world-identity check (STEP 3) ----------------------------------
    def world_key(result, seed):
        keys = {
            tuple(str(r[f]) for f in WORLD_IDENTITY_FIELDS)
            for r in result["rows"] if int(r["evaluation_seed"]) == seed
        }
        if len(keys) != 1:
            raise SystemExit(f"world {seed} is not internally consistent in one file")
        return next(iter(keys))

    identity_rows, identity_ok = [], True
    for seed in worlds:
        a, b = world_key(ha, seed), world_key(ops3, seed)
        ok = a == b
        identity_ok &= ok
        identity_rows.append((seed, a, b, ok))

    by_arm = rows_by_arm(ha, ops3)
    all_rows = ha["rows"] + ops3["rows"]

    # ---- per-route analysis ---------------------------------------------
    analysis: dict[str, Any] = {}
    for route, cfg in ROUTES.items():
        top = cfg["top"]
        dirs = {}
        for label, left, right in cfg["directions"]:
            pooled = pct(pool(by_arm.get(left, [])), pool(by_arm.get(right, [])))
            per_lin = {
                L: pct(pool(subset(by_arm.get(left, []), lineage=L)),
                       pool(subset(by_arm.get(right, []), lineage=L)))
                for L in lineages
            }
            per_world = {
                w: pct(pool(subset(by_arm.get(left, []), world=w)),
                       pool(subset(by_arm.get(right, []), world=w)))
                for w in worlds
            }
            positive_lineages = sum(1 for v in per_lin.values() if v is not None and v > 0.0)
            dirs[label] = {
                "left": left, "right": right, "pooled": pooled,
                "per_lineage": per_lin, "per_world": per_world,
                "positive_lineages": positive_lineages,
                "pooled_positive": bool(pooled is not None and pooled > 0.0),
                "passes": bool(pooled is not None and pooled > 0.0 and positive_lineages == 3),
            }
        # ---- service guard S ---------------------------------------------
        guard = {}
        for right in cfg["guard_pairs"]:
            pooled_ok = pool(by_arm.get(top, []))["served"] >= pool(by_arm.get(right, []))["served"]
            lin_deltas = {
                L: pool(subset(by_arm.get(top, []), lineage=L))["served"]
                   - pool(subset(by_arm.get(right, []), lineage=L))["served"]
                for L in lineages
            }
            nonneg = sum(1 for v in lin_deltas.values() if v >= 0.0)
            guard[right] = {
                "pooled_delta": pool(by_arm.get(top, []))["served"] - pool(by_arm.get(right, []))["served"],
                "pooled_not_below": bool(pooled_ok),
                "lineage_deltas": lin_deltas,
                "nonnegative_lineages": nonneg,
                "passes": bool(pooled_ok and nonneg >= 2),
            }
        guard_passes = all(g["passes"] for g in guard.values())

        # ---- literal decision (contract section 4) ------------------------
        d2, d3, d1 = dirs["D-C2"], dirs["D-C3"], dirs["D-C1"]
        nonpositive_lineages_c2 = 3 - d2["positive_lineages"]
        if (not d2["pooled_positive"]) or nonpositive_lineages_c2 >= 2:
            decision = "C2_DIRECTION_FAIL"
            why = ("D-C2 non-positive pooled" if not d2["pooled_positive"]
                   else f"D-C2 non-positive in {nonpositive_lineages_c2}/3 lineages")
        elif d2["pooled_positive"] and d2["positive_lineages"] == 2:
            decision = "C2_MIXED"
            why = "D-C2 positive pooled and in exactly 2/3 lineages"
        elif d2["passes"] and d3["passes"] and d1["passes"] and guard_passes:
            decision = "PASS_STAGE1B"
            why = "D-C2, D-C3, D-C1 all strictly positive pooled and 3/3 lineages; S passes"
        else:
            failed = [n for n in ("D-C3", "D-C1") if not dirs[n]["passes"]]
            if failed == ["D-C3"]:
                decision, why = "C3_CONTEXT_FAIL", "D-C2 passes; D-C3 fails"
            elif failed == ["D-C1"]:
                decision, why = "C1_CONTEXT_FAIL", "D-C2 passes; D-C1 fails"
            elif failed:
                decision = "C3_CONTEXT_FAIL + C1_CONTEXT_FAIL"
                why = "D-C2 passes; D-C3 and D-C1 both fail (contract names each separately)"
            else:
                decision = "NO_NAMED_BRANCH__SERVICE_GUARD_S_FAIL"
                why = ("D-C2, D-C3, D-C1 all pass but S fails; contract section 4 "
                       "names no branch for this combination - escalated verbatim")
        analysis[route] = {
            "directions": dirs, "guard": guard, "guard_passes": guard_passes,
            "decision": decision, "reason": why,
        }

    # ---- diagnostics ------------------------------------------------------
    lattice = []
    present = [a for a in ARM_ORDER if a in by_arm]
    for i, left in enumerate(present):
        for right in present[i + 1:]:
            lattice.append((left, right, pct(pool(by_arm.get(left, [])), pool(by_arm.get(right, []))),
                            pool(by_arm.get(left, []))["served"] - pool(by_arm.get(right, []))["served"]))

    boot_pairs = [(lbl, l, r) for route, cfg in ROUTES.items()
                  for lbl, l, r in [(f"{route} {n}", a, b) for n, a, b in cfg["directions"]]]
    boot = bootstrap(by_arm, worlds, boot_pairs)

    # ---- render -----------------------------------------------------------
    L = []
    w = L.append
    w("# V0.8 C2 Stage 1b oracle screen - result report\n")
    w(f"Generated from `{HA_DIR.name}/result.json` and `{OPS3_DIR.name}/result.json`.\n")
    w("Two pre-declared oracle routes evaluated on identical matched worlds, "
      "lineages and keyed fading field. Ratio-of-sums endpoints throughout. "
      "This report states measured quantities and the contract's own mechanical "
      "decision strings; it makes no claim beyond them.\n")

    w("## 0. Provenance\n")
    w("| item | value |")
    w("|---|---|")
    w(f"| runner file | `{ha['code_file']}` |")
    w(f"| runner sha256 | `{ha['code_file_sha256']}` |")
    w(f"| OPS-3 run runner sha256 | `{ops3['code_file_sha256']}` |")
    w(f"| H-A contract sha256 | `{ha['contract_sha256']}` |")
    w(f"| OPS-3 addendum sha256 | `{ops3['contract_sha256']}` |")
    w(f"| evaluation split | {ha['evaluation_split']} |")
    w(f"| TEST opened | {ha['test_split_opened']} / {ops3['test_split_opened']} |")
    w(f"| episode training | {ha['episode_training']} / {ops3['episode_training']} |")
    w(f"| learned Q2 used | {ha['learned_q2_used']} / {ops3['learned_q2_used']} |")
    w(f"| lambda0 | {ha['oracle']['lambda0_bits_per_j']!r} = `{ha['oracle']['lambda0_hex']}` |")
    w(f"| kappa | {ha['oracle']['kappa_bits']!r} = `{ha['oracle']['kappa_bits_hex']}` |")
    w(f"| worlds | {worlds} |")
    w(f"| lineages | {lineages} |")
    w(f"| episodes | H-A {ha['episode_count']}, OPS-3 {ops3['episode_count']}, "
      f"total {ha['episode_count'] + ops3['episode_count']} |")
    w(f"| source-closure mode | {ha['source_closure_mode']} / {ops3['source_closure_mode']} |")
    w("")
    for name, res in (("H-A", ha), ("OPS-3", ops3)):
        w(f"Checkpoint sha256 ({name} run):\n")
        w("| key | sha256 |")
        w("|---|---|")
        for k, v in sorted(res["checkpoint_sha256"].items()):
            w(f"| `{k}` | `{v}` |")
        w("")
    w("Source-closure note, verbatim:\n")
    w("```")
    w(str(ha["source_closure_note"]))
    w("```")
    w("```")
    w(str(ops3["source_closure_note"]))
    w("```\n")

    w("## 1. World-identity check (H-A block vs OPS-3 block)\n")
    w("The keyed field root is `(component, evaluation_seed)` and mobility depends "
      "only on the seed, so the two blocks must draw byte-identical worlds.\n")
    w("| seed | initial_world_sha256 | identical across blocks |")
    w("|---|---|---|")
    for seed, a, b, ok in identity_rows:
        w(f"| {seed} | `{a[0][:16]}...` | {'YES' if ok else 'NO'} |")
    w("")
    w(f"All five fields {WORLD_IDENTITY_FIELDS} matched for every seed: "
      f"**{'PASS' if identity_ok else 'FAIL'}**\n")

    for route, cfg in ROUTES.items():
        res = analysis[route]
        w(f"## 2{'a' if route == 'H-A' else 'b'}. {route} arm table\n")
        w("Pooled over all rows of the arm.\n")
        w("| arm | episodes | EE bit/J | total bits | total energy J | served | hold | infeasible-hold |")
        w("|---|---|---|---|---|---|---|---|")
        for arm in cfg["arms"]:
            p = pool(by_arm.get(arm, []))
            w(f"| {arm} | {p['episodes']} | {fmt(p['ee'], '.6g')} | {p['bits']:.6g} | "
              f"{p['energy']:.6g} | {fmt(p['served'])} | {fmt(p['hold'])} | {p['infeasible']} |")
        w("")
        w("Per lineage (MAIN has no lineage axis and repeats its world-pooled rows):\n")
        w("| arm | lineage | episodes | EE bit/J | served | hold | infeasible-hold |")
        w("|---|---|---|---|---|---|---|")
        for arm in cfg["arms"]:
            for Lg in lineages:
                p = pool(subset(by_arm.get(arm, []), lineage=Lg))
                w(f"| {arm} | {Lg} | {p['episodes']} | {fmt(p['ee'], '.6g')} | "
                  f"{fmt(p['served'])} | {fmt(p['hold'])} | {p['infeasible']} |")
        w("")

    w("## 3. Primary directions (percentage contrasts, EE_X/EE_Y - 1)\n")
    for route, cfg in ROUTES.items():
        res = analysis[route]
        w(f"### {route}\n")
        w("| direction | contrast | pooled | " + " | ".join(str(Lg) for Lg in lineages)
          + " | positive lineages | passes |")
        w("|---|---|---|" + "---|" * len(lineages) + "---|---|")
        for label in ("D-C2", "D-C3", "D-C1"):
            d = res["directions"][label]
            cells = " | ".join(
                fmt(None if d["per_lineage"][Lg] is None else d["per_lineage"][Lg] * 100, "+.4f")
                for Lg in lineages)
            w(f"| {label} | {d['left']} vs {d['right']} | "
              f"{fmt(None if d['pooled'] is None else d['pooled'] * 100, '+.4f')} | {cells} | "
              f"{d['positive_lineages']}/3 | {'YES' if d['passes'] else 'NO'} |")
        w("\n(values are percent)\n")

    w("## 4. Service guard S\n")
    w("S as stated: pooled served fraction of the top arm is not below that of each "
      "comparator, AND at least two of three lineage served-fraction contrasts are "
      "nonnegative for each pair.\n")
    for route, cfg in ROUTES.items():
        res = analysis[route]
        w(f"### {route} (top arm {cfg['top']})\n")
        w("| pair | pooled delta served | pooled not below | nonneg lineages | passes |")
        w("|---|---|---|---|---|")
        for right, g in res["guard"].items():
            w(f"| {cfg['top']} vs {right} | {g['pooled_delta']:+.6f} | "
              f"{'YES' if g['pooled_not_below'] else 'NO'} | {g['nonnegative_lineages']}/3 | "
              f"{'PASS' if g['passes'] else 'FAIL'} |")
        w(f"\nS overall: **{'PASS' if res['guard_passes'] else 'FAIL'}**\n")

    w("## 5. Mechanical decision (contract section 4, applied literally)\n")
    for route in ROUTES:
        res = analysis[route]
        d2 = res["directions"]["D-C2"]
        w(f"### {route}\n")
        w(f"- D-C2 pooled positive: {d2['pooled_positive']}; positive lineages "
          f"{d2['positive_lineages']}/3")
        for label in ("D-C3", "D-C1"):
            d = res["directions"][label]
            w(f"- {label} pooled positive: {d['pooled_positive']}; positive lineages "
              f"{d['positive_lineages']}/3; passes: {d['passes']}")
        w(f"- S passes: {res['guard_passes']}")
        w(f"\n**Decision string: `{res['decision']}`**  ({res['reason']})\n")

    w("Notes on the rule application, stated so nothing is read into it:\n")
    w("- The section 4 branches are evaluated in the order the contract writes "
      "them: the D-C2 branches first, then `PASS_STAGE1B`, then the "
      "`C3_CONTEXT_FAIL` / `C1_CONTEXT_FAIL` branch. Under that ordering "
      "`C3_CONTEXT_FAIL` fires on the D-C3 result alone; the state of the "
      "service guard S does not change the string. S is measured and reported "
      "above regardless, and it FAILS for both routes.")
    w("- `D-C3 fails` is read as the negation of the contract's own pass "
      "condition, i.e. NOT (strictly positive pooled AND positive in 3/3 "
      "lineages).")
    w("- Both routes produced the same decision string. Addendum A's "
      "\"exactly one route passes\" and \"both pass\" clauses therefore do "
      "not apply; its \"if neither passes\" clause is the one whose "
      "precondition is met.\n")
    w("## 6. Diagnostics (reported, never decisional)\n")
    w("### 6.1 All lattice contrasts, pooled\n")
    w("| left | right | EE contrast % | served delta |")
    w("|---|---|---|---|")
    for left, right, v, sd in lattice:
        w(f"| {left} | {right} | {fmt(None if v is None else v * 100, '+.4f')} | {sd:+.6f} |")
    w("")
    w("### 6.2 Per-world paired contrasts and sign counts\n")
    for route, cfg in ROUTES.items():
        for label, left, right in cfg["directions"]:
            d = analysis[route]["directions"][label]
            vals = [d["per_world"][x] for x in worlds]
            pos = sum(1 for v in vals if v is not None and v > 0)
            w(f"- {route} {label} ({left} vs {right}): "
              + ", ".join(f"{x}:{fmt(None if v is None else v*100, '+.3f')}%"
                          for x, v in zip(worlds, vals))
              + f"  -> positive in {pos}/{len(worlds)} worlds")
    w("")
    w("### 6.3 Paired-world bootstrap of the primary contrasts\n")
    w(f"{BOOTSTRAP_REPLICATES} replicates, `numpy.default_rng({BOOTSTRAP_SEED})`, "
      "resampling worlds with replacement, statistic = percentage contrast of the "
      "pooled ratio of sums. Report only.\n")
    w("| contrast | mean % | 2.5% | 97.5% | P(>0) |")
    w("|---|---|---|---|---|")
    for k, v in boot.items():
        w(f"| {k} | {v['mean_pct']:+.4f} | {v['ci_lo_pct']:+.4f} | {v['ci_hi_pct']:+.4f} | "
          f"{v['fraction_positive']:.3f} |")
    w("")
    w("### 6.4 OPS-3 internal self-check and reference row\n")
    chk = ops3.get("ops3_ratio_self_check") or {}
    w(f"- {chk.get('statement')}: max relative error {chk.get('max_rel_error'):.3e} over "
      f"{chk.get('samples')} legal actions, tolerance {chk.get('tolerance')}, "
      f"passed = {chk.get('passed')}")
    deltas = [r["oracle_diagnostics"]["ops3_reference_row_delta_bits"]
              for r in ops3["rows"]
              if (r.get("oracle_diagnostics") or {}).get("ops3_reference_row_delta_bits")]
    if deltas:
        w(f"- `Z_a - Z_(a^M)` diagnostic over {len(deltas)} episodes: "
          f"median of per-episode medians {np.median([d['median'] for d in deltas]):.6g} bits, "
          f"mean |delta| {np.mean([d['mean_abs'] for d in deltas]):.6g} bits. "
          "Not subtracted in the deployed surface (per-state constant).")
    hz = None
    for r in ops3["rows"]:
        hz = (r.get("oracle_diagnostics") or {}).get("ops3_horizon_t_by_step") or hz
    w(f"- H_t by decision step: {hz}")
    w("")
    w("### 6.5 Timings\n")
    w("| block | episodes | wall s | mean s/episode |")
    w("|---|---|---|---|")
    for name, res in (("H-A", ha), ("OPS-3", ops3)):
        t = [float(x["elapsed_s"]) for x in res["timings"]]
        w(f"| {name} | {res['episode_count']} | {res['elapsed_s']:.1f} | {np.mean(t):.2f} |")
    w("")

    w("## 7. Contract files\n")
    w("| file | sha256 |")
    w("|---|---|")
    for f in sorted(CONTRACTS.glob("*.md")):
        w(f"| `{f.name}` | `{sha256_file(f)}` |")
    w("")

    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT}")
    print(f"world identity: {'PASS' if identity_ok else 'FAIL'}")
    for route in ROUTES:
        print(f"{route}: {analysis[route]['decision']}  ({analysis[route]['reason']})")
    print(json.dumps({
        r: {k: {"pooled_pct": None if v["pooled"] is None else v["pooled"] * 100,
                "per_lineage_pct": {str(a): None if b is None else b * 100
                                    for a, b in v["per_lineage"].items()},
                "passes": v["passes"]}
            for k, v in analysis[r]["directions"].items()}
        for r in ROUTES}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
