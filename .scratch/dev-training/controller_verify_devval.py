import json, glob, math, statistics as st
W = "/home/sat/mcrl-v025-dev-e0-ws"
D = {}
for f in sorted(glob.glob(W + "/runs-e0*/*/devval-ep*.json")):
    d = json.load(open(f))
    root = f.split("/runs-")[1].split("/")[0]
    ep = int(f.split("devval-ep")[1].split(".")[0])
    key = (root, d["arm_name"], d.get("seed_index"), ep)
    D[key] = d
for k in sorted(D):
    d = D[k]
    print("%-10s %-26s k%s ep%3d ee=%12.0f cfg=%s served=%.5f beams=%5.2f p10=%.3e agree=%.3f" % (
        k[0], k[1][3:], k[2], k[3], d["ee"], d.get("config_hash", "?")[:8], d["served"], d["beams"],
        d["per_served_user_rate_p10_bps"], d.get("t0_agreement", float("nan"))))
def cmp(ka, kb, label):
    A, B = D.get(ka), D.get(kb)
    if not A or not B: return
    rel = [x / y - 1 for x, y in zip(A["ee_ep"], B["ee_ep"])]
    print("%-52s pooled %+6.2f%%  paired %+6.2f +- %.2f%%  wins %2d/24  served %.5f vs %.5f  p10 %.2fx" % (
        label, (A["ee"] / B["ee"] - 1) * 100, st.mean(rel) * 100, st.stdev(rel) / math.sqrt(len(rel)) * 100,
        sum(r > 0 for r in rel), A["served"], B["served"],
        A["per_served_user_rate_p10_bps"] / B["per_served_user_rate_p10_bps"]))
print()
e0a, d3, k1 = "e0a", "e0b-d3", "e0b-k1"
t1, t03 = "e0b-tau1", "e0b-tau0p3"
A2, A1, A3, A4 = "E0-2-D2-T0-equal_share", "E0-1-D0-equal_share", "E0-3-D2-null-equal_share", "E0-4-D3-T0-equal_share"
for ep in (100, 200, 300):
    cmp((d3, A4, 0, ep), (e0a, A2, 0, ep), "k0 ep%d  D3-T0 vs D2-T0(tau3)" % ep)
    cmp((d3, A4, 0, ep), (e0a, A1, 0, ep), "k0 ep%d  D3-T0 vs D0" % ep)
    cmp((e0a, A2, 0, ep), (e0a, A1, 0, ep), "k0 ep%d  D2-T0(tau3) vs D0" % ep)
    cmp((e0a, A2, 0, ep), (e0a, A3, 0, ep), "k0 ep%d  D2-T0(tau3) vs D2-null" % ep)
print()
cmp((t1, A2, 0, 100), (d3, A4, 0, 100), "k0 ep100 D2-T0 tau=1   vs D3-T0")
cmp((t03, A2, 0, 100), (d3, A4, 0, 100), "k0 ep100 D2-T0 tau=0.3 vs D3-T0")
cmp((t1, A2, 0, 100), (e0a, A2, 0, 100), "k0 ep100 D2-T0 tau=1   vs D2-T0 tau=3")
cmp((t03, A2, 0, 100), (e0a, A2, 0, 100), "k0 ep100 D2-T0 tau=0.3 vs D2-T0 tau=3")
cmp((t1, A2, 0, 100), (e0a, A1, 0, 100), "k0 ep100 D2-T0 tau=1   vs D0")
