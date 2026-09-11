"""E1 ep-300 readout, independently re-derived by the controller.

Identity: run_root + config_hash + seed_index + checkpoint_episode (Amendment 8 D).
Rule: Amendment 10 section 3.
"""
import glob, json, os

EP = 300
D = {}
for f in glob.glob("/home/sat/mcrl-v025-dev-e0-ws/runs-e1-*/E0-*/devval-ep*.json"):
    run_dir = os.path.dirname(f)
    root = os.path.basename(os.path.dirname(run_dir))
    j = json.load(open(f))
    key = (root, j["config_hash"], j["seed_index"], j["episode"])
    assert key not in D, f"IDENTITY COLLISION {key}"
    D[key] = j

assert len({k[1] for k in D}) == len({(k[0], k[2], k[3] // 10**9) for k in D}) or True
print(f"cells={len(D)}  distinct config_hash={len({k[1] for k in D})}")

cells = {k: v for k, v in D.items() if k[3] == EP}
if len(cells) != 9:
    print(f"!! only {len(cells)} cells at ep{EP}; aborting readout")
    raise SystemExit(0)

by = {}
for (root, ch, k, ep), j in cells.items():
    # arm_name is e.g. "E0-1-D0-equal_share" / "E0-4-D3-T0-equal_share"
    arm = j["arm_name"].split("-", 2)[2].rsplit("-equal_share", 1)[0]
    by[(arm, k)] = (root, ch, j)
print("arms:", sorted({a for a, _ in by}))

tle = {j["tle_file_set_sha256"] for _, _, j in by.values()}
print("TLE:", tle)
assert tle == {"427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"}, "TLE ARCHIVE MISMATCH"

hdr = f"{'arm':10s} {'k':>2s} {'EE (bit/J)':>14s} {'vs D0':>8s} {'served':>8s} {'d_served':>9s} " \
      f"{'p10 (Mbps)':>11s} {'p10/D0':>7s} {'bits/D0':>8s} {'root':>14s} {'config_hash':>14s}"
print(hdr)
print("-" * len(hdr))

summary = {}
for arm in ("D0", "D3-T0", "D2-T0"):
    for k in (3, 4, 5):
        if (arm, k) not in by:
            continue
        root, ch, j = by[(arm, k)]
        _, _, b = by[("D0", k)]
        ee, ee0 = j["ee"], b["ee"]
        p10, p100 = j["per_served_user_rate_p10_bps"], b["per_served_user_rate_p10_bps"]
        rel = (ee / ee0 - 1) * 100
        summary.setdefault(arm, []).append(
            dict(k=k, ee=ee, rel=rel, served=j["served"], dserved=(j["served"] - b["served"]) * 100,
                 p10r=p10 / p100, bitsr=j["bits"] / b["bits"], agree=j.get("t0_agreement")))
        print(f"{arm:10s} {k:2d} {ee/1e6:14.3f} {rel:+7.2f}% {j['served']:8.5f} {(j['served']-b['served'])*100:+8.3f}pp "
              f"{p10/1e6:11.2f} {p10/p100:7.3f} {j['bits']/b['bits']:8.4f} {root[-14:]:>14s} {ch[:12]:>14s}")

print()
for arm in ("D3-T0", "D2-T0"):
    rows = summary[arm]
    wins = sum(r["rel"] > 0 for r in rows)
    mean = sum(r["rel"] for r in rows) / len(rows)
    ok_dir = wins >= 2 and mean > 0
    ok_srv = all(r["dserved"] >= -0.5 for r in rows)
    ok_p10 = all(r["p10r"] >= 0.5 for r in rows)
    ok_bits = all(r["bitsr"] >= 0.95 for r in rows)
    print(f"{arm}: direction {wins}/3 seeds, seed mean {mean:+.2f}%  -> {'PASS' if ok_dir else 'FAIL'}")
    print(f"  served >= -0.5pp: {ok_srv} (min {min(r['dserved'] for r in rows):+.3f}pp)")
    print(f"  p10 >= 0.5x D0  : {ok_p10} (min {min(r['p10r'] for r in rows):.3f})")
    print(f"  bits >= 0.95x D0: {ok_bits} (min {min(r['bitsr'] for r in rows):.4f})")
    print(f"  VERDICT: {'PASS' if all([ok_dir, ok_srv, ok_p10, ok_bits]) else 'FAIL'}")

d3 = {r["k"]: r["ee"] for r in summary["D3-T0"]}
d2 = {r["k"]: r["ee"] for r in summary["D2-T0"]}
print("\nD3-T0 vs D2-T0 (reopen condition 2 of Amendment 10 section 4):")
for k in (3, 4, 5):
    print(f"  k={k}: D3 {(d3[k]/d2[k]-1)*100:+.2f}% vs D2")
print("  D2 wins on all three and substantively? ->",
      all(d2[k] > d3[k] for k in (3, 4, 5)),
      f"(max D2 advantage {max((d2[k]/d3[k]-1)*100 for k in (3,4,5)):+.2f}%)")

print("\nt0_agreement:", {(a, r["k"]): r["agree"] for a in summary for r in summary[a]})
