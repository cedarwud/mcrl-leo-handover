import json, glob, math, statistics as st
W = "/home/sat/mcrl-v025-dev-e0-ws"
D = {}
for f in sorted(glob.glob(W + "/runs-e0*/**/devval-ep*.json", recursive=True)):
    d = json.load(open(f))
    root = f.split(W + "/")[1].split("/")[0]
    ep = int(f.split("devval-ep")[1].split(".")[0])
    D[(root, d.get("mechanism", "?"), d.get("seed_index"), ep, d.get("config_hash", "")[:12])] = d
rows = [k for k in D if k[3] == 100 and k[0] in ("runs-e0a", "runs-e0b-d3", "runs-e0b-d3-k1", "runs-e0b-k1", "runs-e0b-d3null", "runs-e0b-k2")]
for k in sorted(rows, key=lambda x: (x[2], x[1], x[0])):
    d = D[k]
    print("%-16s %-10s k%s ep%d cfg=%-13s ee=%12.0f served=%.5f p10=%.3e min=%.2e agree=%.3f" % (
        k[0], k[1], k[2], k[3], k[4], d["ee"], d["served"], d["per_served_user_rate_p10_bps"],
        d["per_served_user_rate_min_bps"], d.get("t0_agreement", float("nan"))))
def find(seed, mech, root=None):
    hits = [D[k] for k in D if k[2] == seed and k[1] == mech and k[3] == 100 and (root is None or k[0] == root)]
    return hits[0] if len(hits) == 1 else hits
def cmp(A, B, label):
    if not isinstance(A, dict) or not isinstance(B, dict): print("AMBIGUOUS/MISSING", label, type(A), type(B)); return
    rel = [x / y - 1 for x, y in zip(A["ee_ep"], B["ee_ep"])]
    print("%-40s pooled %+7.2f%%  paired %+7.2f +- %.2f%%  wins %2d/24" % (
        label, (A["ee"] / B["ee"] - 1) * 100, st.mean(rel) * 100, st.stdev(rel) / math.sqrt(24) * 100, sum(r > 0 for r in rel)))
print()
print("mechanisms seen:", sorted({k[1] for k in D}))
for seed in (0, 1, 2):
    d0 = find(seed, "D0"); d3 = find(seed, "D3-T0"); dn = find(seed, "D3-null")
    cmp(d3, d0, "k%d D3-T0 vs D0" % seed)
    cmp(d3, dn, "k%d D3-T0 vs D3-null" % seed)
    cmp(dn, d0, "k%d D3-null vs D0" % seed)
