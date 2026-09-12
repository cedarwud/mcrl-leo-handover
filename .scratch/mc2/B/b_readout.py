#!/usr/bin/env python3
"""Lane B independent MC2 DEVVAL readout (development lane; not formal evidence).

Implements contract **r2** section 7 exactly
(`.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md`,
commit ``b6573b58``, blob sha256 ``37b3404e…``): v1 (``MC2-JGO-v1``) and v2
(``MC2-ARB-v2``) at ep 100 on k = 10, 11 with their own drop-ones and one shared
``B-only`` cell, the six qualification clauses, the version selection, and the
ep-300 survival gate with the F-2 fallback rule.

Recomputes from the RAW ``devval-epNNNNN.json`` files written by
``scripts/run_dev_e0.py``, WITHOUT lane A's aggregator and without importing any
``mcrl`` code (stdlib only):

* per (cell, seed): pooled EE = sum(bits)/sum(joules) over the 24 DEVVAL episodes
  (plain left-to-right accumulation, as ``cf_dev.dev_rollout``), bits, joules,
  served fraction, p10 (as stored: the file keeps only the pooled percentile);
* per version and seed: FULL over own A-only, D3-T0, B-only, own B-null and D0,
  with paired per-episode sign counts;
* the QoS floors (F-3) per seed; B activity (F-1 / R1-3) per seed from the FULL
  run's episode logs, numerator ``judge_challenger_wins_c_ne_a`` (the challenger
  won and a^B != a^A), denominator ``judge_decision_rows`` (user-steps with a legal
  action, all t), pooled over training episodes 1..ep;
* the r2 decision: clauses (i)-(vi) per version, the selection score
  ``mean_k min(FULL/own-A-only - 1, FULL/D3-T0 - 1, FULL/B-only - 1)``, the primary
  (ties within 0.10 pp -> v1), or the ep-300 gate per version;
* the "reported beside" block: FULL vs D3-T0 bits / joules / served / p10, win
  rates for FULL and B-null, doses, per-tag sampled rows and margin-loss share,
  judge evaluations and wall.

Identity checks per file (any failure makes the verdict ``INVALID-IDENTITY``):
devval config hash == status fingerprint == RUN-MANIFEST ``arm_configs`` == sha256
of the manifest's own arm payload; TLE file set; seed index (file, status,
directory); checkpoint episode; kind; DEVVAL seeds 9_211_000+i / 9_212_000+i; 24
episodes / 24,000 user-steps; code digest; recomputed EE / ee_ep / bits / joules /
served == file.  Per pair: same DEVVAL seeds, epochs and step-0 observation digest.

**Hygiene (r2 section 6):** reading a k = 15-17 file needs
``--fallback-authorised``, which is legitimate only after the primary's ep-300
verdict is written.

Usage::

    b_readout.py fetch --remote-root /home/sat/mcrl-v025-mc2-ws/runs-ep100 \\
                       --local .scratch/mc2/B/ep100 --episode 100
    b_readout.py read  --local .scratch/mc2/B/ep100 --preset mc2 --stage ep100
    b_readout.py read  --local .scratch/mc2/B/ep300 --preset mc2 --stage ep300 \\
                       --episode 300 --primary v1 --other-qualified
    b_readout.py read  --local .scratch/mc2/B/k8 --preset k8     # k8 regression
    b_readout.py selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

TLE = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
DEVVAL_ENV, DEVVAL_MOB, N_DEVVAL = 9_211_000, 9_212_000, 24
USERS, STEPS = 100, 10
FALLBACK_SEEDS = {15, 16, 17}

CELLS = ("D0", "D3-T0", "B-only", "FULL-v1", "B-null-v1", "A-only-v2", "FULL-v2", "B-null-v2")
VERSIONS: dict[str, dict[str, str]] = {
    "v1": {"FULL": "FULL-v1", "A-only": "D3-T0", "B-only": "B-only", "B-null": "B-null-v1"},
    "v2": {"FULL": "FULL-v2", "A-only": "A-only-v2", "B-only": "B-only", "B-null": "B-null-v2"},
}
TIE_PP = 0.0010            # "within 0.10 pp -> v1", on the relative ratio

PRESETS: dict[str, dict[str, str]] = {
    # k = 8 matrix (Amendment 15) mapped onto the v1 cells: FULL{T0,T_NEXT},
    # D3-T0 = arm 4, "B-only" = the T_NEXT-only set arm, "B-null" = the Bernoulli null.
    "k8": {
        "D0": r"^E0-1-D0-equal_share-k(\d+)$",
        "D3-T0": r"^E0-4-D3-T0-equal_share-k(\d+)$",
        "FULL-v1": r"^E0-8-D3-multi-T0\+T_NEXT-equal_share-k(\d+)$",
        "B-only": r"^E0-8-D3-multi-T_NEXT-equal_share-k(\d+)$",
        "B-null-v1": r"^E0-9-D3-multi-null-.*-k(\d+)$",
    },
    # MC2 r2 cells on lane A's committed arm names
    # (``E0-10-MC2-<cell label>-equal_share-k<k>``; the label comes from
    # ``dev_e0_common.judge_cell_label``: ``v1-A+B``, ``v1-A+R``, ``v2-A``,
    # ``v2-A+B``, ``v2-A+R``, and the rule-independent shared ``B``).
    "mc2": {
        "D0": r"^E0-1-D0-equal_share-k(\d+)$",
        "D3-T0": r"^E0-4-D3-T0-equal_share-k(\d+)$",
        "B-only": r"^E0-\d+-MC2-B-equal_share-k(\d+)$",
        "FULL-v1": r"^E0-\d+-MC2-v1-A\+B-equal_share-k(\d+)$",
        "B-null-v1": r"^E0-\d+-MC2-v1-A\+R-equal_share-k(\d+)$",
        "A-only-v2": r"^E0-\d+-MC2-v2-A-equal_share-k(\d+)$",
        "FULL-v2": r"^E0-\d+-MC2-v2-A\+B-equal_share-k(\d+)$",
        "B-null-v2": r"^E0-\d+-MC2-v2-A\+R-equal_share-k(\d+)$",
    },
}

# B activity (r2 section 7, F-1 / R1-3): numerator = the challenger won with
# a^B != a^A; denominator = user-steps with at least one legal action, all t.
# Both are lane A's ``cf_judge.EpisodeJudgeLog.as_log`` fields.
INERT_FIELDS = ("judge_challenger_wins_c_ne_a", "judge_decision_rows")
# "Reported beside" fields summed or averaged over the training episodes.
BESIDE_SUM = ("judge_evaluations", "judge_compared", "judge_overrides",
              "judge_challenger_wins", "judge_challenger_wins_c_ne_a",
              "judge_decision_rows", "judge_abstained_final_rows")
BESIDE_MEAN = ("judge_wall_s", "judge_margin_dose")
BESIDE_TAGS = ("judge_sampled_rows_by_tag", "judge_margin_loss_by_tag", "judge_pushed_by_tag")


# ------------------------------------------------------------------ fetch
def _ssh(host: str, cmd: str, timeout: int = 180) -> bytes:
    r = subprocess.run(["ssh", host, cmd], capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise FileNotFoundError(r.stderr.decode(errors="replace").strip() or cmd)
    return r.stdout


def fetch(a) -> int:
    local: Path = a.local
    local.mkdir(parents=True, exist_ok=True)
    root = a.remote_root.rstrip("/")
    man_bytes = _ssh(a.host, f"cat {shlex.quote(root + '/RUN-MANIFEST.json')}")
    (local / "RUN-MANIFEST.json").write_bytes(man_bytes)
    manifest = json.loads(man_bytes)
    wanted = ["RUN-MANIFEST.json"]
    for _key, payload in sorted(manifest["arm_payloads"].items()):
        k = int(payload["seed_index"])
        if a.seeds and k not in a.seeds:
            continue
        if k in FALLBACK_SEEDS and not a.fallback_authorised:
            print(f"SKIP k{k}: r2 hygiene -- a fallback seed needs --fallback-authorised")
            continue
        run = f"{payload['arm_name']}-k{k}"
        (local / run).mkdir(exist_ok=True)
        for name in ("status.json", f"devval-ep{a.episode:05d}.json", "episode-logs.json"):
            rel = f"{run}/{name}"
            try:
                data = _ssh(a.host, f"cat {shlex.quote(root + '/' + rel)}")
            except FileNotFoundError as err:
                print(f"MISSING {rel}: {err}")
                continue
            (local / rel).write_bytes(data)
            wanted.append(rel)
    # scp is known to corrupt silently on sat: verify every byte by sha256.
    remote = _ssh(a.host, "cd " + shlex.quote(root) + " && sha256sum "
                  + " ".join(shlex.quote(w) for w in wanted)).decode()
    bad = 0
    for line in remote.strip().splitlines():
        digest, rel = line.split(None, 1)
        rel = rel.strip().lstrip("*")
        ok = hashlib.sha256((local / rel).read_bytes()).hexdigest() == digest
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {digest[:16]} {rel}")
    print(f"fetched {len(wanted)} files, {bad} sha256 mismatches")
    return 1 if bad else 0


# ------------------------------------------------------------------ one run
def _sha_payload(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def load_run(run_dir: Path, episode: int, manifest: dict, k_dir: int) -> dict:
    dv = json.loads((run_dir / f"devval-ep{episode:05d}.json").read_text())
    st = json.loads((run_dir / "status.json").read_text())
    rows = dv["episodes"]
    bits = joules = 0.0
    for r in rows:
        bits += r["bits"]
        joules += r["joules"]
    served = sum(int(r["served"]) for r in rows)
    user_steps = sum(int(r["user_steps"]) for r in rows)
    ee = bits / joules
    ee_ep = [r["bits"] / r["joules"] if r["joules"] > 0 else float("nan") for r in rows]
    fp = st["fingerprint"]
    matches = [(key, p) for key, p in manifest["arm_payloads"].items()
               if p["arm_name"] == dv["arm_name"] and int(p["seed_index"]) == int(dv["seed_index"])]
    checks = {
        "kind": dv.get("kind") == "devval",
        "episode": int(dv["episode"]) == episode,
        "seed_index": int(dv["seed_index"]) == k_dir == int(st["seed_index"]) == int(fp["seed_index"]),
        "dir_name": run_dir.name == f"{dv['arm_name']}-k{int(dv['seed_index'])}",
        "tle": dv["tle_file_set_sha256"] == TLE == fp["tle_file_set_sha256"]
               == manifest.get("tle_file_set_sha256"),
        "devval_seeds": dv["devval_seeds"] == [[DEVVAL_ENV + i, DEVVAL_MOB + i] for i in range(N_DEVVAL)],
        "n_episodes": len(rows) == N_DEVVAL == int(dv["n_episodes"]),
        "user_steps": user_steps == int(dv["user_steps"]) == N_DEVVAL * USERS * STEPS,
        "hash_status": dv["config_hash"] == fp["config_hash"],
        "hash_manifest_unique": len(matches) == 1,
        "hash_manifest": len(matches) == 1 and manifest["arm_configs"].get(matches[0][0]) == dv["config_hash"],
        "hash_payload_recomputed": len(matches) == 1 and _sha_payload(matches[0][1]) == dv["config_hash"],
        "code_digest": fp["code_digest"] == manifest.get("code_digest"),
        "checkpoint_listed": str(episode) in st.get("checkpoints", {}),
        "ee_equals_file": ee == dv["ee"],
        "ee_ep_equals_file": ee_ep == dv["ee_ep"],
        "bits_joules_equal_file": bits == dv["bits"] and joules == dv["joules"],
        "served_equals_file": served / user_steps == dv["served"],
    }
    return {
        "dir": run_dir.name, "k": k_dir, "arm_name": dv["arm_name"], "mechanism": dv["mechanism"],
        "config_hash": dv["config_hash"], "ee": ee, "bits": bits, "joules": joules,
        "served": served / user_steps, "p10": float(dv["per_served_user_rate_p10_bps"]),
        "beams": float(dv["beams"]), "ee_ep": ee_ep,
        "epochs": [r.get("epoch") for r in rows],
        "obs0": [r.get("t0_obs112_sha256") for r in rows],
        "devval_seeds": dv["devval_seeds"], "checks": checks, "status": st.get("status"),
        "run_dir": str(run_dir),
    }


def _logs(run_dir: str, episode: int) -> list[dict] | None:
    path = Path(run_dir) / "episode-logs.json"
    if not path.is_file():
        return None
    logs = json.loads(path.read_text())
    return logs[:episode] if len(logs) >= episode else None


def b_activity(run_dir: str, episode: int, fields: tuple[str, str]) -> float | None:
    """B activity: numerator / denominator pooled over training episodes 1..episode."""
    logs = _logs(run_dir, episode)
    if logs is None:
        return None
    num = den = 0
    for log in logs:
        if fields[0] not in log or fields[1] not in log:
            return None
        num += int(log[fields[0]])
        den += int(log[fields[1]])
    return num / den if den else None


def beside(run_dir: str, episode: int) -> dict:
    """The r2 "reported beside" judge quantities of one run."""
    logs = _logs(run_dir, episode)
    if logs is None:
        return {}
    out: dict = {}
    for key in BESIDE_SUM:
        vals = [log[key] for log in logs if key in log]
        if vals:
            out[key] = sum(int(v) for v in vals)
    for key in BESIDE_MEAN:
        vals = [log[key] for log in logs if log.get(key) is not None]
        if vals:
            out[key + "_mean"] = sum(float(v) for v in vals) / len(vals)
    for key in BESIDE_TAGS:
        vals = [log[key] for log in logs if isinstance(log.get(key), dict)]
        if vals:
            out[key] = {t: sum(float(v[t]) for v in vals) for t in vals[0]}
    if out.get("judge_decision_rows"):
        out["win_rate_c_ne_a"] = out.get("judge_challenger_wins_c_ne_a", 0) / out["judge_decision_rows"]
        out["override_rate"] = out.get("judge_overrides", 0) / out["judge_decision_rows"]
    return out


def pair_stats(x: dict, y: dict) -> dict:
    same = (x["devval_seeds"] == y["devval_seeds"] and x["epochs"] == y["epochs"]
            and x["obs0"] == y["obs0"])
    wins = sum(1 for a, b in zip(x["ee_ep"], y["ee_ep"]) if a > b)
    losses = sum(1 for a, b in zip(x["ee_ep"], y["ee_ep"]) if a < b)
    return {"rel": x["ee"] / y["ee"] - 1.0, "wins": wins, "losses": losses,
            "ties": len(x["ee_ep"]) - wins - losses, "same_episodes": same,
            "bits": x["bits"] / y["bits"], "joules": x["joules"] / y["joules"],
            "served_pp": (x["served"] - y["served"]) * 100.0, "p10": x["p10"] / y["p10"]}


def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


# ------------------------------------------------------------------ r2 decision
def evaluate_version(per_seed: dict[int, dict], stage: str) -> dict:
    """Contract r2 section 7 for one version.

    ``per_seed[k]`` = {rA, rB, rN, rD3, floors_ok, activity (float|None)} where
    rA = FULL/own-A-only - 1, rD3 = FULL/D3-T0 - 1, rB = FULL/B-only - 1,
    rN = FULL/own-B-null - 1.
    """
    ks = sorted(per_seed)
    if not ks:
        return {"present": False, "criteria": {}, "passes": False, "pending": False}
    rA = [per_seed[k]["rA"] for k in ks]
    rB = [per_seed[k]["rB"] for k in ks]
    rN = [per_seed[k]["rN"] for k in ks]
    rD = [per_seed[k]["rD3"] for k in ks]
    act = [per_seed[k]["activity"] for k in ks]
    floors = all(per_seed[k]["floors_ok"] for k in ks)
    pos = lambda xs: sum(1 for x in xs if x > 0)                 # noqa: E731
    two_thirds = lambda xs: 3 * pos(xs) >= 2 * len(xs)            # noqa: E731
    # R1-2: seed-mean of the PER-SEED min over the three required margins.
    score = _mean([min(per_seed[k]["rA"], per_seed[k]["rD3"], per_seed[k]["rB"]) for k in ks])
    activity_ok = None if any(v is None for v in act) else all(v >= 0.01 for v in act)
    if stage == "ep100":
        crit = {
            "(i) seed-mean FULL / own A-only >= +0.5 %": _mean(rA) >= 0.005,
            "(ii) seed-mean FULL / D3-T0 >= +0.5 % [R1-1]": _mean(rD) >= 0.005,
            "(iii) seed-mean FULL / B-only > 0": _mean(rB) > 0,
            "(iv) seed-mean FULL / own B-null > 0": _mean(rN) > 0,
            "(v) QoS floors on each seed": floors,
            "(vi) B activity >= 1 % on each seed": activity_ok,
        }
    else:
        crit = {
            "(s-i) FULL / own A-only >= +1.0 % and >= 2/3 seeds > 0":
                _mean(rA) >= 0.01 and two_thirds(rA),
            "(s-ii) FULL / D3-T0 >= +1.0 % and >= 2/3 seeds > 0 [R1-1]":
                _mean(rD) >= 0.01 and two_thirds(rD),
            "(s-iii) FULL / B-only >= +1.0 % and >= 2/3 seeds > 0":
                _mean(rB) >= 0.01 and two_thirds(rB),
            "(s-iv) FULL / own B-null > 0 and >= 2/3 seeds > 0":
                _mean(rN) > 0 and two_thirds(rN),
            "(s-v) QoS floors on each seed": floors,
        }
    failed = any(v is False for v in crit.values())
    out = {"present": True, "seeds": ks, "criteria": crit, "score": score,
           "mean_rA": _mean(rA), "mean_rD3": _mean(rD), "mean_rB": _mean(rB),
           "mean_rN": _mean(rN), "pos": {"rA": pos(rA), "rD3": pos(rD), "rB": pos(rB),
                                         "rN": pos(rN), "n": len(ks)},
           "activity": act, "floors": floors}
    # A definitive failure decides the version even if another clause is missing.
    out["pending"] = (not failed) and any(v is None for v in crit.values())
    out["passes"] = (not failed) and (not out["pending"])
    return out


def select(ev: dict[str, dict]) -> str:
    """r2 section 7 ep-100 selection."""
    if any(e.get("present") and e.get("pending") for e in ev.values()):
        return "PENDING (a qualification clause could not be computed)"
    q = [v for v in ("v1", "v2") if ev.get(v, {}).get("present") and ev[v]["passes"]]
    if not q:
        return ("NEITHER version qualifies -> the data go to the owner "
                "(no third version, no relaxation)")
    if len(q) == 1:
        return (f"PRIMARY = {q[0]} (the only qualifier); the other did NOT qualify, so a "
                "primary failure at ep 300 goes to the owner, not to the fallback (F-2)")
    s1, s2 = ev["v1"]["score"], ev["v2"]["score"]
    if abs(s1 - s2) <= TIE_PP:
        return (f"PRIMARY = v1 (scores {100 * s1:+.3f} % vs {100 * s2:+.3f} %, within "
                "0.10 pp -> v1); v2 = fixed-order fallback confirmation on k = 15-17")
    prim, other = ("v1", "v2") if s1 > s2 else ("v2", "v1")
    return (f"PRIMARY = {prim} (score {100 * max(s1, s2):+.3f} % vs "
            f"{100 * min(s1, s2):+.3f} %); {other} = fixed-order fallback confirmation "
            "on k = 15-17, read ONLY if the primary fails (F-2)")


def survival(ev: dict[str, dict], primary: str | None, other_qualified: bool) -> str:
    """r2 ep-300: the primary's gate, then F-2."""
    lines = []
    for v in ("v1", "v2"):
        e = ev[v]
        if not e["present"]:
            continue
        state = "PASS" if e["passes"] else ("PENDING" if e["pending"] else "FAIL")
        lines.append(f"{v}: DEV SURVIVAL {state}")
    if primary is None:
        return "; ".join(lines) + " | pass --primary to apply the F-2 rule" if lines else \
            "no version present"
    e = ev.get(primary, {})
    if not e.get("present"):
        return f"primary {primary} has no complete cell set here; " + "; ".join(lines)
    if e["pending"]:
        return f"primary {primary}: PENDING; " + "; ".join(lines)
    if e["passes"]:
        return (f"primary {primary}: DEV SURVIVAL PASS (first attempt) -- the fallback is "
                "NOT read; " + "; ".join(lines))
    if other_qualified:
        return (f"primary {primary}: DEV SURVIVAL FAIL -> read the other version's "
                "fallback confirmation on k = 15-17 under the identical gate (F-2), and "
                "state in any report which attempt passed; " + "; ".join(lines))
    return (f"primary {primary}: DEV SURVIVAL FAIL and the other version did not qualify "
            "-> the data go to the owner (F-2); " + "; ".join(lines))


# ------------------------------------------------------------------ read
def read(a) -> int:
    local: Path = a.local
    manifest = json.loads((local / "RUN-MANIFEST.json").read_text())
    patterns = dict(PRESETS[a.preset])
    for item in a.cell or []:
        name, _, rx = item.partition("=")
        if name not in CELLS:
            raise SystemExit(f"unknown cell {name!r}; cells are {CELLS}")
        patterns[name] = rx
    fields = tuple(a.inert_fields)
    runs: dict[tuple[str, int], dict] = {}
    for run_dir in sorted(p for p in local.iterdir() if p.is_dir()):
        hits = [(c, m) for c, rx in patterns.items() for m in [re.match(rx, run_dir.name)] if m]
        if len(hits) > 1:
            raise SystemExit(f"{run_dir.name} matches several cells: {[c for c, _ in hits]}")
        if not hits or not (run_dir / f"devval-ep{a.episode:05d}.json").is_file():
            continue
        cell, m = hits[0]
        k = int(m.group(m.lastindex))
        if a.seeds and k not in a.seeds:
            continue
        if k in FALLBACK_SEEDS and not a.fallback_authorised:
            raise SystemExit(
                f"r2 section 6 hygiene: {run_dir.name} is a fallback seed (k = {k}). "
                "Nobody reads k = 15-17 before the primary's ep-300 verdict is written. "
                "Pass --fallback-authorised only after that."
            )
        if (cell, k) in runs:
            raise SystemExit(f"two runs for cell {cell} k{k}")
        runs[(cell, k)] = load_run(run_dir, a.episode, manifest, k)
    seeds = sorted({k for _c, k in runs})
    bad_identity = [(c, k, n) for (c, k), r in runs.items() for n, ok in r["checks"].items() if not ok]
    order = lambda kv: (kv[0][1], CELLS.index(kv[0][0]))            # noqa: E731

    print(f"# lane B readout (contract r2)  root={local}  episode={a.episode}  "
          f"preset={a.preset}  stage={a.stage}  seeds={seeds}")
    print("\n## identity")
    for (c, k), r in sorted(runs.items(), key=order):
        print(f"k{k:<3} {c:<9} {r['dir']:<58} hash {r['config_hash'][:12]}  "
              f"checks {sum(r['checks'].values())}/{len(r['checks'])}  status={r['status']}")
    for c, k, n in bad_identity:
        print(f"  IDENTITY FAIL  k{k} {c}: {n}")

    print("\n## cells (pooled over 24 DEVVAL episodes)")
    print("| k | cell | EE (bit/J) | bits | joules | served | p10 (bit/s) | beams |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for (c, k), r in sorted(runs.items(), key=order):
        print(f"| {k} | {c} | {r['ee']:,.2f} | {r['bits']:.6e} | {r['joules']:,.3f} | "
              f"{r['served']:.5f} | {r['p10']:.4e} | {r['beams']:.3f} |")

    per_version: dict[str, dict[int, dict]] = {}
    ratio_rows: dict[str, dict] = {}
    for v, cells in VERSIONS.items():
        full = cells["FULL"]
        per_version[v] = {}
        vseeds = [k for k in seeds if (full, k) in runs]
        if not vseeds:
            continue
        print(f"\n## {v}: seed-wise ratios (EE_X,k / EE_Y,k - 1; paired W/L/T per episode)")
        print("| comparison | k | rel EE | paired W/L/T | same eps | bits x | joules x "
              "| served pp | p10 x |")
        print("|---|---|---:|---|---|---:|---:|---:|---:|")
        comp = [("A-only", cells["A-only"]), ("D3-T0", "D3-T0"), ("B-only", cells["B-only"]),
                ("B-null", cells["B-null"]), ("D0", "D0")]
        for k in vseeds:
            need = [cells["A-only"], cells["B-only"], cells["B-null"], "D0", "D3-T0"]
            missing = [c for c in need if (c, k) not in runs]
            if missing:
                print(f"| {v} k{k} | MISSING {missing} | | | | | | | |")
                continue
            st = {}
            for label, cell in comp:
                s = pair_stats(runs[(full, k)], runs[(cell, k)])
                st[label] = s
                if label == "D3-T0" and cells["A-only"] == "D3-T0":
                    continue                       # v1: A-only IS D3-T0, printed once
                ratio_rows[f"{v}|{full}/{cell}|k{k}"] = s
                print(f"| {full}/{cell} | {k} | {100 * s['rel']:+.3f} % | "
                      f"{s['wins']}/{s['losses']}/{s['ties']} | {s['same_episodes']} | "
                      f"{s['bits']:.4f} | {s['joules']:.4f} | {s['served_pp']:+.3f} | "
                      f"{s['p10']:.4f} |")
            d0 = st["D0"]
            drop = -d0["served_pp"]
            floors_ok = drop <= 0.5 and d0["p10"] >= 0.5 and d0["bits"] >= 0.95
            activity = b_activity(runs[(full, k)]["run_dir"], a.episode, fields)
            per_version[v][k] = {
                "rA": st["A-only"]["rel"], "rD3": st["D3-T0"]["rel"],
                "rB": st["B-only"]["rel"], "rN": st["B-null"]["rel"],
                "floors_ok": floors_ok, "activity": activity,
                "floors": {"served_drop_pp": drop, "p10_x": d0["p10"], "bits_x": d0["bits"]},
                "same_episodes": all(s["same_episodes"] for s in st.values())}
            print(f"| {v} floors k{k} | served drop {drop:+.3f} pp (<= 0.5), p10 "
                  f"{d0['p10']:.4f}x (>= 0.5), bits {d0['bits']:.4f}x (>= 0.95) -> "
                  f"{'PASS' if floors_ok else 'FAIL'} | B activity "
                  f"{'--' if activity is None else f'{100 * activity:.3f} %'} | | | | | | |")

    ev = {v: evaluate_version(per_version.get(v, {}), a.stage) for v in VERSIONS}
    print(f"\n## contract r2 section 7 decision ({a.stage})")
    for v in VERSIONS:
        e = ev[v]
        if not e["present"]:
            print(f"- {v}: ABSENT (no complete cell set on these seeds)")
            continue
        state = "QUALIFIES" if e["passes"] else ("PENDING" if e["pending"] else "does NOT qualify")
        print(f"- {v}: {state}; selection score = mean_k min(own A-only, D3-T0, B-only) "
              f"= {100 * e['score']:+.3f} %")
        for name, val in e["criteria"].items():
            shown = "PENDING (log field absent)" if val is None else val
            print(f"    {name}: {shown}")
    verdict = (select(ev) if a.stage == "ep100"
               else survival(ev, a.primary, a.other_qualified))
    if bad_identity:
        verdict = f"INVALID-IDENTITY ({verdict})"
    mispaired = [f"{v}:k{k}" for v, d in per_version.items() for k, s in d.items()
                 if not s["same_episodes"]]
    if mispaired:
        verdict = f"INVALID-PAIRING {mispaired} ({verdict})"
    print(f"\nDECISION: {verdict}")
    if a.stage == "ep100" and any(ev[v]["present"] and ev[v]["criteria"].get(
            "(vi) B activity >= 1 % on each seed") is False for v in VERSIONS):
        print("NOTE (r2 section 7): if the P0 pre-training diagnostic showed a near-zero "
              "override rate, a failed (vi) is reported as STRUCTURAL, not as "
              "'B has no content'.")

    print("\n## reported beside (from the training episode logs)")
    beside_rows = {}
    for (c, k), r in sorted(runs.items(), key=order):
        b = beside(r["run_dir"], a.episode)
        if not b:
            continue
        beside_rows[f"{c}|k{k}"] = b
        dose = b.get("judge_margin_dose_mean")
        print(f"k{k} {c:<9} evals {b.get('judge_evaluations', 0):>9,}  "
              f"wall/ep {b.get('judge_wall_s_mean', float('nan')):.1f}s  "
              f"override {100 * b.get('override_rate', float('nan')):.3f} %  "
              f"challenger-win (c != a^A) {100 * b.get('win_rate_c_ne_a', float('nan')):.3f} %  "
              f"dose {'--' if dose is None else f'{dose:.4f}'}  "
              f"sampled rows/tag {b.get('judge_sampled_rows_by_tag', {})}")
    if not beside_rows:
        print("(no episode-logs.json fetched)")

    if a.json:
        out = {"contract": "r2", "root": str(local), "episode": a.episode,
               "preset": a.preset, "stage": a.stage, "seeds": seeds,
               "identity_failures": bad_identity,
               "cells": {f"{c}|k{k}": {kk: vv for kk, vv in r.items()
                                       if kk not in ("ee_ep", "epochs", "obs0", "devval_seeds")}
                         for (c, k), r in runs.items()},
               "ratios": ratio_rows, "per_version": per_version,
               "versions": ev, "verdict": verdict, "beside": beside_rows,
               "primary": a.primary, "other_qualified": bool(a.other_qualified)}
        Path(a.json).write_text(json.dumps(out, indent=2, sort_keys=True, default=str))
    return 0


# ------------------------------------------------------------------ selftest
def selftest() -> int:
    """Synthetic check of the r2 clauses, score, selection and F-2 fallback."""
    def seed(rA, rD3, rB, rN, floors=True, activity=0.05):
        return {"rA": rA, "rD3": rD3, "rB": rB, "rN": rN, "floors_ok": floors,
                "activity": activity}
    # v1: A-only IS D3-T0 (rA == rD3).  v2: a weak A-only-v2 and FULL-v2 BELOW D3-T0
    # -- the R1-1 case that r2 clause (ii) now rejects.
    v1 = {10: seed(0.006, 0.006, 0.030, 0.2), 11: seed(0.005, 0.005, 0.028, 0.2)}
    v2 = {10: seed(0.037, -0.004, 0.028, 0.2), 11: seed(0.035, -0.006, 0.026, 0.2)}
    e1, e2 = evaluate_version(v1, "ep100"), evaluate_version(v2, "ep100")
    assert e1["passes"] and not e2["passes"], (e1["criteria"], e2["criteria"])
    assert e2["criteria"]["(ii) seed-mean FULL / D3-T0 >= +0.5 % [R1-1]"] is False
    assert select({"v1": e1, "v2": e2}).startswith("PRIMARY = v1 (the only qualifier)")
    assert abs(e1["score"] - 0.0055) < 1e-9, e1["score"]      # min is rA/rD3, not rB
    # both qualify, v2 better by more than 0.10 pp
    v2b = {10: seed(0.020, 0.020, 0.030, 0.2), 11: seed(0.018, 0.018, 0.028, 0.2)}
    both = select({"v1": e1, "v2": evaluate_version(v2b, "ep100")})
    assert both.startswith("PRIMARY = v2") and "fallback" in both, both
    # tie within 0.10 pp -> v1
    v2c = {10: seed(0.0065, 0.0065, 0.030, 0.2), 11: seed(0.0050, 0.0050, 0.028, 0.2)}
    tie = select({"v1": e1, "v2": evaluate_version(v2c, "ep100")})
    assert tie.startswith("PRIMARY = v1") and "within" in tie, tie
    # (vi) missing -> PENDING; a definitive failure still decides
    pend = evaluate_version({10: seed(0.006, 0.006, 0.03, 0.2, activity=None)}, "ep100")
    assert pend["pending"] and not pend["passes"]
    hard = evaluate_version({10: seed(-0.01, -0.01, 0.03, 0.2, activity=None)}, "ep100")
    assert not hard["pending"] and not hard["passes"]
    # B activity below 1 %
    low = evaluate_version({10: seed(0.006, 0.006, 0.03, 0.2, activity=0.004)}, "ep100")
    assert low["criteria"]["(vi) B activity >= 1 % on each seed"] is False
    # ep300: 2/3 seeds and the R1-1 clause
    s_ok = evaluate_version({12: seed(0.02, 0.02, 0.02, 0.1), 13: seed(0.02, 0.02, 0.02, 0.1),
                             14: seed(-0.001, -0.001, 0.015, 0.1)}, "ep300")
    assert s_ok["passes"], s_ok["criteria"]
    s_bad = evaluate_version({12: seed(0.02, 0.001, 0.02, 0.1), 13: seed(0.02, 0.001, 0.02, 0.1),
                              14: seed(0.02, 0.001, 0.02, 0.1)}, "ep300")
    assert not s_bad["passes"]
    # F-2
    assert "NOT read" in survival({"v1": s_ok, "v2": {"present": False, "criteria": {}}},
                                  "v1", True)
    f_fail = survival({"v1": s_bad, "v2": {"present": False, "criteria": {}}}, "v1", True)
    assert "fallback confirmation on k = 15-17" in f_fail, f_fail
    owner = survival({"v1": s_bad, "v2": {"present": False, "criteria": {}}}, "v1", False)
    assert "go to the owner" in owner, owner
    print("selftest ok (r2 clauses, score, selection, F-2)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--remote-root", required=True)
    f.add_argument("--local", type=Path, required=True)
    f.add_argument("--episode", type=int, default=100)
    f.add_argument("--seeds", type=lambda s: [int(x) for x in s.split(",")], default=None)
    f.add_argument("--host", default="sat")
    f.add_argument("--fallback-authorised", action="store_true",
                   help="r2 hygiene: allow k = 15-17, only after the primary's verdict")
    r = sub.add_parser("read")
    r.add_argument("--local", type=Path, required=True)
    r.add_argument("--preset", choices=sorted(PRESETS), required=True)
    r.add_argument("--episode", type=int, default=100)
    r.add_argument("--stage", choices=("ep100", "ep300"), default="ep100")
    r.add_argument("--seeds", type=lambda s: [int(x) for x in s.split(",")], default=None)
    r.add_argument("--cell", action="append", help="NAME=REGEX on the run-directory name")
    r.add_argument("--inert-fields", type=lambda s: s.split(","), default=list(INERT_FIELDS),
                   help="B-activity numerator,denominator episode-log fields")
    r.add_argument("--primary", choices=("v1", "v2"), default=None,
                   help="ep300: the version selected at ep 100 (applies the F-2 rule)")
    r.add_argument("--other-qualified", action="store_true",
                   help="ep300: the non-primary also qualified at ep 100 (F-2)")
    r.add_argument("--fallback-authorised", action="store_true",
                   help="r2 hygiene: allow k = 15-17, only after the primary's verdict")
    r.add_argument("--json", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "fetch":
        return fetch(a)
    if a.cmd == "selftest":
        return selftest()
    return read(a)


if __name__ == "__main__":
    sys.exit(main())
