"""CFSCREEN screens 1 (metrics), 2, 3, 4 -- pure analysis of the logs written by
collect.py and bc_probe.py.  No rollout, no training, no gradient step anywhere.

Sources (rolled):  A0 = MAX_NOMINAL_GAIN, A2 = A m=2dB      -> C1 (C-gain)
                   A9 = A m=9dB,          A12 = A m=12dB    -> C2 (C-hold)
                   B1 = B1_NO_NEW_BEAM,   B2 = B2_PREFER_SHARED -> C3 (C-consolidate)
                   TR = trained e6b063ef greedy (reference)
Query columns on every rolled state: A0 A2 A9 A12 B1 B2 HOLD TR.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
SRC = ["A0", "A2", "A9", "A12", "B1", "B2", "TR"]
CAT = {"A0": "C1", "A2": "C1", "A9": "C2", "A12": "C2", "B1": "C3", "B2": "C3", "TR": "L"}
MARG = {"A0": 0.0, "A2": 2.0, "A9": 9.0, "A12": 12.0}
BLK = {"access": slice(0, 28), "snr": slice(28, 56), "theta": slice(56, 84),
       "loads": slice(84, 112)}
CKPT = ("/home/u24/papers/mcrl-leo-handover/artifacts/"
        "training-2026-08-25-rerun01/main/final-checkpoint.pt")
OUT = []


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    OUT.append(s)


D = {t: dict(np.load(RAW / f"{t}.npz")) for t in SRC}
QC = [str(x) for x in D["A0"]["qcols"]]
for t in SRC:                                   # row alignment across cells
    for k in ("ep", "t", "u"):
        assert np.array_equal(D[t][k], D["A0"][k]), (t, k)
N = len(D["A0"]["act"])
ROWS = np.arange(N)


def gdb(g):
    return 10.0 * np.log10(np.maximum(g, 1e-300))


def a_score(d, m):
    s = gdb(d["gain"]).copy()
    inc, mask = d["inc"], d["mask"]
    ok = (inc >= 0)
    ok[ok] = mask[ROWS[ok], inc[ok]]
    if m > 0:
        s[ROWS[ok], inc[ok]] += m
    s[~mask] = -np.inf
    return s


def b_allowed(tag, d):
    load, inc, mask = d["load"], d["inc"], d["mask"]
    if tag == "B1":
        allowed = load > 0.5
    else:
        occ = load.copy()
        r = inc >= 0
        occ[ROWS[r], inc[r]] -= 1.0
        strong = occ > 0.5
        has = (strong & mask).any(1)
        allowed = np.where(has[:, None], strong, load > 0.5)
    none = ~(allowed & mask).any(1)
    allowed = allowed.copy()
    allowed[none] = True
    return allowed & mask


def contested(d):
    """Incumbent legal AND not the max-gain legal option: the only decisions on
    which always-incumbent and always-max-gain disagree."""
    inc, mask = d["inc"], d["mask"]
    g = np.where(mask, d["gain"], -np.inf)
    best = g.argmax(1)
    ok = inc >= 0
    ok[ok] = mask[ROWS[ok], inc[ok]]
    return ok & (inc != best) & mask.any(1), best, ok


# ======================================================== sanity: rule reconstruction
p("# SANITY: rule reconstructions from logged raw gain/load/incumbent vs logged actions")
for t in ["A0", "A2", "A9", "A12"]:
    d = D[t]
    keep = d["mask"].any(1)
    for q in ["A0", "A2", "A9", "A12"]:
        rec = a_score(d, MARG[q]).argmax(1)
        mis = int((rec[keep] != d["qry"][keep, QC.index(q)]).sum())
        if mis:
            p(f"  states={t} rule={q}: argmax(gain_dB + m*1[inc]) mismatches {mis}")
p("  A-family: argmax(gain_dB + m*1[incumbent legal]) reproduces every A-rule query on "
  "every A-source state unless a mismatch line is printed above")
for t in SRC:
    d = D[t]
    keep = d["mask"].any(1)
    for q in ["B1", "B2"]:
        al = b_allowed(q, d)
        rec = np.where(al, d["gain"], -np.inf).argmax(1)
        mis = int((rec[keep] != d["qry"][keep, QC.index(q)]).sum())
        p(f"  states={t} rule={q}: restricted-argmax reconstruction mismatches {mis}")
    tr_self = int((D["TR"]["act"] != D["TR"]["qry"][:, QC.index("TR")]).sum())
p(f"  TR states: select_actions vs recomputed masked argmax mismatches {tr_self}")
for t in SRC:
    d = D[t]
    p(f"  {t}: rows {N}, empty-mask rows {int((~d['mask'].any(1)).sum())}, "
      f"mean |legal| {d['mask'].sum(1)[d['mask'].any(1)].mean():.2f}")

# ======================================================== screen 1 metrics
p("\n# SCREEN 1: representability (held-out by episode, 3 folds pooled)")


def rank_top(scores, y, k):
    top = np.argsort(-scores, axis=1)[:, :k]
    return (top == y[:, None]).any(1)


def regret(tag, d, pred, keep):
    """Rule's own score gap.  A: dB of (gain_dB + m*1[inc]); B: (violation rate,
    mean gain-dB gap on non-violating); TR: scalarized-Q gap."""
    y = d["act"][keep]
    if tag in MARG:
        s = a_score(d, MARG[tag])[keep]
        r = s[np.arange(len(y)), y] - s[np.arange(len(y)), pred]
        return dict(kind="dB", mean=float(r.mean()), frac_pos=float((r > 1e-9).mean()),
                    p95=float(np.percentile(r, 95)), pmax=float(r.max()))
    if tag in ("B1", "B2"):
        al = b_allowed(tag, d)[keep]
        viol = ~al[np.arange(len(y)), pred]
        g = gdb(d["gain"])[keep]
        gap = g[np.arange(len(y)), y] - g[np.arange(len(y)), pred]
        return dict(kind="viol+dB", viol=float(viol.mean()),
                    mean=float(gap[~viol].mean()),
                    frac_pos=float((gap[~viol] > 1e-9).mean()),
                    p95=float(np.percentile(gap[~viol], 95)))
    q = d["q"].astype(np.float64)[keep]
    r = q[np.arange(len(y)), y] - q[np.arange(len(y)), pred]
    return dict(kind="Qscal", mean=float(r.mean()), frac_pos=float((r > 0).mean()),
                p95=float(np.percentile(r, 95)))


S1 = {}
for tag in SRC + ["NULL"]:
    src = "A0" if tag == "NULL" else tag
    d = D[src]
    keep = d["mask"].any(1)
    con, best, incok = contested(d)
    conk = con[keep]
    for var in ["raw", "z", "raw400"]:
        f = RAW / f"bc_{tag}_{var}.npz"
        if not f.exists():
            continue
        b = np.load(f)
        y, pred, lg, ep = b["y"], b["pred"], b["logits"], b["ep"]
        jf = json.loads((RAW / f"bc_{tag}_{var}.json").read_text())
        top1 = (pred == y)
        top3 = rank_top(lg, y, 3)
        folds = [x["test_top1"] for x in jf["folds"]]
        row = dict(n=int(len(y)), top1=float(top1.mean()), top3=float(top3.mean()),
                   fold_min=min(folds), fold_max=max(folds),
                   con_frac=float(conk.mean()),
                   con_top1=float(top1[conk].mean()) if conk.any() else float("nan"),
                   epochs=[x["best_epoch"] for x in jf["folds"]])
        if tag != "NULL":
            assert np.array_equal(y, d["act"][keep])
            row["regret"] = regret(tag, d, pred, keep)
        else:
            nl = d["mask"].sum(1)[keep]
            row["chance_top1"] = float((1.0 / nl).mean())
            row["chance_top3"] = float(np.minimum(3.0 / nl, 1.0).mean())
        S1[(tag, var)] = row
    # trivial baselines on this source's own rows
    if tag != "NULL":
        y = d["act"][keep]
        g = np.where(d["mask"], gdb(d["gain"]), -np.inf)
        gi = g.copy()
        gi[ROWS[incok], d["inc"][incok]] += 1e6
        for bname, sc in (("always-max-gain", g), ("always-incumbent", gi)):
            sc = sc[keep]
            pr = sc.argmax(1)
            t1 = pr == y
            S1[(tag, bname)] = dict(n=int(len(y)), top1=float(t1.mean()),
                                    top3=float(rank_top(sc, y, 3).mean()),
                                    con_top1=float(t1[conk].mean()) if conk.any() else float("nan"),
                                    con_frac=float(conk.mean()),
                                    regret=regret(tag, d, pr, keep))

hdr = (f"  {'source':6s} {'predictor':17s} {'n':>6s} {'top1':>7s} {'fold rng':>13s} "
       f"{'top3':>7s} {'contested':>9s} {'top1|con':>8s}  regret")
p(hdr)
for tag in SRC + ["NULL"]:
    for pr in ["raw", "z", "raw400", "always-max-gain", "always-incumbent"]:
        r = S1.get((tag, pr))
        if r is None:
            continue
        fr = (f"{r['fold_min']:.4f}-{r['fold_max']:.4f}" if "fold_min" in r else "")
        if "regret" in r:
            g = r["regret"]
            if g["kind"] == "viol+dB":
                rg = (f"viol={g['viol']:.4f} gapdB(mean={g['mean']:.3f},>0:{g['frac_pos']:.4f},"
                      f"p95={g['p95']:.2f})")
            else:
                rg = (f"{g['kind']} mean={g['mean']:.4g} >0:{g['frac_pos']:.4f} "
                      f"p95={g['p95']:.4g}")
        else:
            rg = f"chance top1={r['chance_top1']:.4f} top3={r['chance_top3']:.4f}"
        ep_s = f" best_ep={r['epochs']}" if "epochs" in r else ""
        p(f"  {tag:6s} {pr:17s} {r['n']:6d} {r['top1']:7.4f} {fr:>13s} {r['top3']:7.4f} "
          f"{r['con_frac']:9.4f} {r['con_top1']:8.4f}  {rg}{ep_s}")

# ======================================================== screen 2
p("\n# SCREEN 2: action disagreement D(row-states, column-rule) = fraction of "
  "(user,step) decisions with a non-empty mask where the rolled source's action "
  "differs from the column rule's action ON THE ROW SOURCE'S STATES")
p("  " + f"{'states':8s}" + "".join(f"{c:>8s}" for c in QC))
DM = {}
for t in SRC:
    d = D[t]
    keep = d["mask"].any(1)
    a = d["qry"][keep]
    own = a[:, QC.index(t)]
    row = [float((own != a[:, j]).mean()) for j in range(len(QC))]
    DM[t] = row
    p("  " + f"{t:8s}" + "".join(f"{x:8.4f}" for x in row))
p("\n  same, restricted to CONTESTED decisions (incumbent legal and not the max-gain option)")
p("  " + f"{'states':8s}{'n_con':>7s}" + "".join(f"{c:>8s}" for c in QC))
for t in SRC:
    d = D[t]
    con, _, _ = contested(d)
    a = d["qry"][con]
    own = a[:, QC.index(t)]
    p("  " + f"{t:8s}{int(con.sum()):7d}" +
      "".join(f"{float((own != a[:, j]).mean()):8.4f}" for j in range(len(QC))))

p("\n  catfish-level D (mean over member pairs, both directions)")
cats = {"C1": ["A0", "A2"], "C2": ["A9", "A12"], "C3": ["B1", "B2"], "L": ["TR"]}
for c1 in cats:
    for c2 in cats:
        if c1 > c2:
            continue
        vals = []
        for x in cats[c1]:
            for y in cats[c2]:
                if x == y:
                    continue
                vals.append(DM[x][QC.index(y)])
                vals.append(DM[y][QC.index(x)])
        if vals:
            p(f"  D({c1},{c2}) mean={np.mean(vals):.4f} min={np.min(vals):.4f} "
              f"max={np.max(vals):.4f}  (n={len(vals)} directed member pairs)")

p("\n  gain-gap band of each source's decisions: g = gain_dB(best legal) - gain_dB(incumbent)")
p(f"  {'states':8s} {'inc gone/illegal':>16s} {'g=0 (inc best)':>15s} {'0<g<=2':>8s} "
  f"{'2<g<=9':>8s} {'9<g<=12':>8s} {'g>12':>8s}")
for t in SRC:
    d = D[t]
    keep = d["mask"].any(1)
    con, best, incok = contested(d)
    gg = gdb(d["gain"])
    gap = np.full(N, np.nan)
    gap[incok] = gg[ROWS[incok], best[incok]] - gg[ROWS[incok], d["inc"][incok]]
    k = keep
    fr = [(~incok & k).sum(), (incok & k & (gap <= 0)).sum(),
          (incok & k & (gap > 0) & (gap <= 2)).sum(), (incok & k & (gap > 2) & (gap <= 9)).sum(),
          (incok & k & (gap > 9) & (gap <= 12)).sum(), (incok & k & (gap > 12)).sum()]
    fr = [x / k.sum() for x in fr]
    p(f"  {t:8s} {fr[0]:16.4f} {fr[1]:15.4f} {fr[2]:8.4f} {fr[3]:8.4f} {fr[4]:8.4f} "
      f"{fr[5]:8.4f}")


# ======================================================== screen 3
def d2mat(q, pp):
    return np.maximum((q ** 2).sum(1)[:, None] + (pp ** 2).sum(1)[None, :]
                      - 2.0 * q @ pp.T, 0.0)


p("\n# SCREEN 3: state visitation overlap, FEASFRONT JSRL measure. Query = X's 2400 encoded "
  "observations at step index t; pool = Y's 2400 at the same t (same episodes); z-scored "
  "on Y's own per-dim mean/sd over all its 24,000 rows (constant dims sd=1). "
  "R = mean 1-NN(query->pool) / mean leave-one-out 1-NN within pool; out95 = frac of "
  "query 1-NN > pool LOO 95th pct.  Averages over t = 1..9; t = 0 is the reset state.")
T = int(D["A0"]["t"].max()) + 1
Z = {}
for t in SRC:
    X = D[t]["obs"].astype(np.float64)
    mu, sd = X.mean(0), X.std(0)
    sd[sd < 1e-12] = 1.0
    Z[t] = (mu, sd)
LOO = {}


def pool_loo(y, t, sl):
    key = (y, t, sl.start if sl is not None else -1)
    if key not in LOO:
        mu, sd = Z[y]
        P = (D[y]["obs"][D[y]["t"] == t].astype(np.float64) - mu) / sd
        if sl is not None:
            P = P[:, sl]
        M = d2mat(P, P)
        np.fill_diagonal(M, np.inf)
        loo = np.sqrt(M.min(1))
        LOO[key] = (P, loo)
    return LOO[key]


S3 = {}
p(f"  {'X->Y':10s} {'R t=0':>7s} {'R(1..9)':>8s} {'out95':>7s} | share of sq 1-NN dist: "
  f"{'access':>7s} {'snr':>6s} {'theta':>6s} {'loads':>6s} | block-only R: "
  f"{'snr':>6s} {'theta':>6s} {'loads':>6s} | paired-identical rows: "
  f"{'access':>7s} {'snr':>6s} {'theta':>6s} {'loads':>6s}")
for x in SRC:
    for y in SRC:
        if x == y:
            continue
        mu, sd = Z[y]
        Rs, Os, SH, BR, ID, R0 = [], [], [], [], [], None
        for t in range(T):
            P, loo = pool_loo(y, t, None)
            Xr = D[x]["obs"][D[x]["t"] == t].astype(np.float64)
            Yr = D[y]["obs"][D[y]["t"] == t].astype(np.float64)
            Q = (Xr - mu) / sd
            M = d2mat(Q, P)
            j = M.argmin(1)
            dd = np.sqrt(M[np.arange(len(j)), j])
            R = dd.mean() / loo.mean()
            if t == 0:
                R0 = R
                continue
            Rs.append(R)
            Os.append(float((dd > np.percentile(loo, 95)).mean()))
            diff2 = (Q - P[j]) ** 2
            tot = diff2.sum(1)
            tot[tot == 0] = np.nan
            SH.append([np.nanmean(diff2[:, s].sum(1) / tot) for s in BLK.values()])
            br = []
            for bn in ("snr", "theta", "loads"):
                Pb, loob = pool_loo(y, t, BLK[bn])
                ddb = np.sqrt(d2mat(Q[:, BLK[bn]], Pb).min(1))
                br.append(ddb.mean() / loob.mean())
            BR.append(br)
            ID.append([float(np.all(Xr[:, s] == Yr[:, s], axis=1).mean())
                       for s in BLK.values()])
        sh, brm, idm = np.mean(SH, 0), np.mean(BR, 0), np.mean(ID, 0)
        S3[(x, y)] = dict(R0=R0, R=float(np.mean(Rs)), out95=float(np.mean(Os)),
                          Rt=[float(v) for v in Rs])
        p(f"  {x + '->' + y:10s} {R0:7.4f} {np.mean(Rs):8.4f} {np.mean(Os):7.4f} | "
          f"{'':22s}{sh[0]:7.3f} {sh[1]:6.3f} {sh[2]:6.3f} {sh[3]:6.3f} | "
          f"{'':14s}{brm[0]:6.3f} {brm[1]:6.3f} {brm[2]:6.3f} | "
          f"{'':23s}{idm[0]:7.3f} {idm[1]:6.3f} {idm[2]:6.3f} {idm[3]:6.3f}")

p("\n  per-t R(X->Y) for the C1/C2 cross pairs and within-catfish references")
for x, y in [("A0", "A2"), ("A2", "A0"), ("A9", "A12"), ("A12", "A9"), ("A2", "A9"),
             ("A9", "A2"), ("A0", "A12"), ("A12", "A0"), ("B1", "B2"), ("B2", "B1"),
             ("A2", "B1"), ("B1", "A2")]:
    p(f"  {x + '->' + y:10s} " + " ".join(f"{v:6.3f}" for v in S3[(x, y)]["Rt"]))

# ======================================================== screen 4
import torch  # noqa: E402
sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover/src")
from mcrl.artifacts import read_checkpoint             # noqa: E402
from mcrl.runtime.q_network import DQNNetwork          # noqa: E402
from mcrl.runtime.trainer_spec import TrainerConfig    # noqa: E402

torch.set_num_threads(1)
cfg = TrainerConfig()
W = cfg.objective_weights
pay = read_checkpoint(Path(CKPT), map_location="cpu")
nets = []
for sd_ in pay.q_networks:
    n_ = DQNNetwork(112, 28, tuple(cfg.hidden_layers), cfg.activation)
    n_.load_state_dict(sd_)
    n_.eval()
    nets.append(n_)

p(f"\n# SCREEN 4: margin scale of the trained checkpoint (scalarized Q = "
  f"{W[0]}*Q1 + {W[1]}*Q2 + {W[2]}*Q3, as select_actions uses), on each source's states. "
  "sd = population sd over the LEGAL actions of one state (states with >= 2 legal).")
p(f"  {'states':7s} {'n':>6s} {'sdQ med':>10s} {'sdQ p10':>10s} {'sdQ p90':>10s} "
  f"{'agree':>7s} {'mE med':>10s} {'mE/sd med':>9s} | fires DQfD margin l=c*sd: "
  f"{'c=0':>6s} {'0.25':>6s} {'0.5':>6s} {'1':>6s} | per-head argmax agree: "
  f"{'Q1':>6s} {'Q2':>6s} {'Q3':>6s} | head sd med: {'Q1':>9s} {'Q2':>8s} {'Q3':>8s}")
S4 = {}
for t in SRC:
    d = D[t]
    with torch.no_grad():
        X = torch.as_tensor(d["obs"])
        qh = [nt(X).numpy().astype(np.float64) for nt in nets]
    qs = W[0] * qh[0] + W[1] * qh[1] + W[2] * qh[2]
    dq = float(np.abs(qs - d["q"].astype(np.float64)).max())
    mask = d["mask"]
    two = mask.sum(1) >= 2
    y = d["act"]

    def masked_sd(q):
        qm = np.where(mask, q, np.nan)
        return np.nanstd(qm, axis=1)

    sdq = masked_sd(qs)[two]
    agree = float((d["qry"][:, QC.index("TR")] == y)[mask.any(1)].mean())
    qm = np.where(mask, qs, -np.inf)
    qE = qs[ROWS, np.clip(y, 0, 27)]
    qo = qm.copy()
    qo[ROWS, np.clip(y, 0, 27)] = -np.inf
    mE = (qE - qo.max(1))[two]
    fire = [float((mE < c * sdq).mean()) for c in (0.0, 0.25, 0.5, 1.0)]
    ha = []
    hsd = []
    for h in range(3):
        qq = np.where(mask, qh[h], -np.inf)
        ha.append(float((qq.argmax(1) == y)[mask.any(1)].mean()))
        hsd.append(float(np.median(masked_sd(qh[h])[two])))
    S4[t] = dict(agree=agree, sd_med=float(np.median(sdq)), fire=fire, head_agree=ha,
                 recompute_maxabs=dq)
    p(f"  {t:7s} {int(two.sum()):6d} {np.median(sdq):10.4g} {np.percentile(sdq, 10):10.4g} "
      f"{np.percentile(sdq, 90):10.4g} {agree:7.4f} {np.median(mE):10.4g} "
      f"{np.median(mE / sdq):9.3f} | {'':25s}{fire[0]:6.3f} {fire[1]:6.3f} {fire[2]:6.3f} "
      f"{fire[3]:6.3f} | {'':22s}{ha[0]:6.3f} {ha[1]:6.3f} {ha[2]:6.3f} | {'':12s}"
      f"{hsd[0]:9.4g} {hsd[1]:8.4g} {hsd[2]:8.4g}   (recompute max|dQ|={dq:.2e})")

(RAW / "screens.out").write_text("\n".join(OUT) + "\n")
json.dump(dict(S1={f"{k[0]}|{k[1]}": v for k, v in S1.items()}, D=DM,
               S3={f"{k[0]}->{k[1]}": v for k, v in S3.items()}, S4=S4),
          open(RAW / "screens.json", "w"), indent=1)
