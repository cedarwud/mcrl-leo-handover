import json, glob, math, statistics as st
W = "/home/sat/mcrl-v025-dev-e0-ws"
cand = {}
for f in glob.glob(W + "/**/*.json", recursive=True):
    try: d = json.load(open(f))
    except Exception: continue
    if isinstance(d, dict) and "ee_ep" in d and len(d.get("ee_ep", [])) == 24:
        cand[f] = d
refs = {f: d for f, d in cand.items() if "runs-e0" not in f and "proctest" not in f}
print("=== non-run DEVVAL-shaped files (references) ===")
for f, d in sorted(refs.items()):
    print("%-64s ee=%12.0f served=%.5f p10=%.3e %s" % (
        f.replace(W + "/", ""), d["ee"], d["served"], d["per_served_user_rate_p10_bps"],
        str(d.get("arm_name") or d.get("arm") or d.get("rule") or d.get("kind") or "")[:28]))
def get(pred):
    hits = [d for f, d in cand.items() if pred(f, d)]
    return hits[0] if len(hits) == 1 else (hits if hits else None)
d3k1 = get(lambda f, d: "runs-e0b-d3-k1" in f and "ep00100" in f)
d0k1 = get(lambda f, d: "runs-e0b-k1" in f and "D0" in f and "ep00100" in f)
d2k1 = get(lambda f, d: "runs-e0b-k1" in f and "D2-T0" in f and "ep00100" in f)
base = get(lambda f, d: ("modqn" in f.lower() or "baseline" in f.lower() or "eq16" in f.lower()) and "runs-e0" not in f)
def cmp(A, B, label):
    if not isinstance(A, dict) or not isinstance(B, dict): print("MISSING", label); return
    rel = [x / y - 1 for x, y in zip(A["ee_ep"], B["ee_ep"])]
    print("%-42s pooled %+7.2f%%  paired %+7.2f +- %.2f%%  wins %2d/24" % (
        label, (A["ee"] / B["ee"] - 1) * 100, st.mean(rel) * 100, st.stdev(rel) / math.sqrt(24) * 100, sum(r > 0 for r in rel)))
print()
cmp(d3k1, d0k1, "k1 ep100 D3-T0 vs D0")
cmp(d3k1, d2k1, "k1 ep100 D3-T0 vs D2-T0(tau3)")
if isinstance(base, dict):
    print("baseline file ee=%.0f served=%.5f p10=%.3e" % (base["ee"], base["served"], base["per_served_user_rate_p10_bps"]))
    cmp(d3k1, base, "k1 ep100 D3-T0 vs frozen MODQN eq16")
else:
    print("baseline not found in this workspace:", base)
