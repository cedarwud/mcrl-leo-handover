# Controller decision — MC2 ep-100 selection: NEITHER version qualifies; the label channel is the blocker

Date 2026-09-12. **Development lane**, contract r2 §7 applied literally and nothing else. Every figure below is the
controller's own computation from the 16 raw `devval-ep00100.json` files on `sat`
(`/home/sat/mcrl-v025-mc2-ws/runs-ep100/`), not from lane A's aggregate; lane B's independent recomputation is a second
path and is recorded beside it. Code commit `11466998`, one identity group, config hashes matching
`RUN-MANIFEST.json` and the hash recomputed from its own arm payloads, TLE `427e6a91…`, DEVVAL `9_211_000+i /
9_212_000+i`, 24 episodes, 24 000 user-steps, `smoke: false`, no failed run (lane B: 0 sha256 mismatches, 18 identity
checks per file).

## 1. The matrix (ep 100, 24 DEVVAL episodes, pooled Σbits/Σjoules)

| cell | k10 EE (M bit/J) | k11 EE | seed mean | agree T0 (k10/k11) | activity |
|---|---:|---:|---:|---:|---:|
| `D0` | 93.991 | 100.153 | 97.072 | 0.261 / 0.356 | — |
| **`D3-T0`** (= v1 A-only, strong single Catfish) | **112.710** | **113.250** | **112.980** | 0.673 / 0.697 | 0 |
| `v1 FULL {A,B}` | 109.352 | 110.347 | 109.850 | 0.596 / 0.608 | 30.4 % / 30.2 % |
| `v1 B-null {A,R}` | 110.857 | 109.796 | 110.327 | 0.671 / 0.651 | ≈ 14 % |
| `v2 FULL {x,A,B}` | 110.461 | 109.229 | 109.845 | 0.574 / 0.535 | 23.1 % / 23.1 % |
| `v2 A-only {x,A}` | 108.896 | 109.815 | 109.356 | 0.587 / 0.605 | 0 |
| `v2 B-null {x,A,R}` | 109.384 | 101.258 | 105.321 | 0.580 / 0.438 | — |
| `B-only {B}` | 104.641 | 104.099 | 104.370 | 0.458 / 0.463 | — |

## 2. The declared clauses, evaluated

| clause | v1 `MC2-JGO-v1` | v2 `MC2-ARB-v2` |
|---|---|---|
| (i) FULL vs own A-only ≥ +0.5 % | **−2.771 %** (−2.98 / −2.56) **FAIL** | **+0.451 %** (+1.44 / −0.53) **FAIL** (short by 0.05 pp, and one seed negative) |
| (ii) FULL vs `D3-T0` ≥ +0.5 % | **−2.771 %** **FAIL** | **−2.773 %** (−2.00 / −3.55) **FAIL** |
| (iii) FULL vs B-only > 0 | +5.252 % pass (24/24 and 24/24 paired) | +5.245 % pass (24/24 and 23/24) |
| (iv) FULL vs own B-null > 0 | **−0.428 %** (−1.36 / +0.50) **FAIL** | +4.428 % pass (+0.98 / +7.87) |
| (v) QoS floors per seed vs same-seed `D0` | pass (served drop ≤ +0.0016, p10 ×1.37–1.97, bits ×1.08–1.14) | pass (served drop ≤ −0.0003, p10 ×1.30–2.21, bits ×1.05–1.25) |
| (vi) B activity ≥ 1 % per seed | pass, 30.4 % / 30.2 % | pass, 23.1 % / 23.1 % |
| selection score `mean_k min(…)` | −2.77 % | −2.77 % |

**Neither version qualifies.** Paired per-episode against `D3-T0`: v1 2/24 and 2/24 positive; v2 5/24 and 0/24. The
shortfall is not seed noise or an episode-level coin flip.

Per r2 §7 this goes to the owner. **No relaxation, no third version on my authority, and no single-Catfish downgrade.**

## 3. The smallest blocking reason, stated as narrowly as the data allows

**The label channel is already saturated by the anchor, and replacing any of its labels costs about as much as the
replacement rate — independently of what the replacement says.**

| challenger-override rate in the v1 family (anchor dose 1.0 in all three) | seed-mean EE | vs `D3-T0` |
|---|---:|---:|
| 0 % (`D3-T0`) | 112.980 | — |
| 17.6 % (17.46 / 17.77), content-free random proposals (`v1 B-null`) | 110.327 | −2.35 % |
| 30.3 % (30.38 / 30.24), `T_NEXT`'s proposals (`v1 FULL`) | 109.850 | −2.77 % |

(The override rates are lane B's exact counts from the episode logs — `judge_challenger_wins_c_ne_a` over a denominator
of exactly 100 000 decision rows per cell. My earlier "≈ 14 %" for the null was an estimate and is superseded.)

**Both independent computations agree.** The controller's own read of the 16 raw files and lane B's `b_readout.py`
(49 files fetched, 0 sha256 mismatches, 18/18 identity checks each, full output
`.scratch/mc2/B/ep100/b_readout-ep100.json`) return the same clause values and the same selection scores to three
decimals, and lane B reports no implementation anomaly: final-step abstention exactly 10 000 rows in every challenger
cell and 0 in `v2 A-only`; sampled rows 128 × 999 updates per cell; the null's judge evaluations exceed FULL's
(137–149 k vs 93–117 k), as a proposal that differs from the anchor on nearly every row must; and `D3-T0` reproduces its
k = 8 level (112.71 / 113.25 against 112.49).

`v1 FULL` vs `v1 B-null` is **−0.43 %** seed-mean with per-seed `[−1.36 %, +0.50 %]`: at two seeds the *content* of the
replacement is not distinguishable, while the *cost of replacing* is present in both arms and is ordered by dose.
`agree T0` moves with it (0.673/0.697 → 0.671/0.651 → 0.596/0.608). The same picture holds inside v2, whose A-only cell
is itself 3.2 % below `D3-T0` because it drops the anchor wherever the learner already agrees with it.

What is **not** established: which of the two declared explanations produces the cost. Contract §1 (N-a2) named the
first — the gate conditions on the step's fading draw and on the other users' executed actions, none of which is in the
learner's 113-dim observation, so identical observations can carry different targets and the hinge resolves them toward
the per-observation majority (label noise, not a better target). The probe's own §3 named the second — the composite
rule's rule-level advantage (+6.13 % over T0, 24/24 paired) appeared when *every* user takes the approved override, and
a learner that follows them on part of the states gets a mixture that need not inherit the gain. This matrix does not
separate those two.

### 3b. The output-change measurement separates the two explanations — and it points at the first one

Lane B rolled the ep-100 checkpoints of `D3-T0` and `v1 FULL` (k = 10 and 11) on the 24 DEVVAL episodes, scored both
policies on one host trajectory so the states are literally identical, and reconstructed the v1 gate on those states with
the env generator state compared before and after every judge block and the committed-step parity asserted (so a
side-effect would have aborted the run); all four checkpoints reproduce their DEVVAL file exactly. Tool and artefacts:
`.scratch/mc2/B/b_output_change.py`, `.scratch/mc2/B/out/host-*.json`.

| on identical states (host = `D3-T0`'s trajectory) | follows `a^A` | follows `a^F` | neither | on gate-APPROVED rows: follows `a^F` | on gate-REJECTED rows: follows `a^F` |
|---|---:|---:|---:|---:|---:|
| `D3-T0` k10 | 62.81 % | 7.80 % | 29.39 % | 8.69 % | 7.02 % |
| `v1 FULL` k10 | 48.94 % | **19.02 %** | 32.03 % | **20.17 %** | **18.02 %** |
| `D3-T0` k11 | 62.87 % | 10.93 % | 26.20 % | 12.67 % | 9.47 % |
| `v1 FULL` k11 | 47.47 % | **23.25 %** | 29.28 % | **25.74 %** | **21.16 %** |

1. **The overrides did land.** `v1 FULL` follows the challenger 2.1–2.4 × as often as `D3-T0` does on the same states, and
   the anchor's share falls by almost exactly what the challenger gains (the "neither" share moves only 2–3 pp). This was
   not a case of an ignored intervention.
2. **But the learner did not learn the *condition*.** The increase is the same size on the rows the gate would have
   approved (20.17 / 25.74 %) and on the rows it would have rejected (18.02 / 21.16 %). If the learner had absorbed
   "follow `a^F` where the judge approves", those two columns would separate; they do not.

That is direct evidence for the first declared explanation and against a benign reading of the first: the gate's
condition is a function of the step's fading draw and the other users' executed actions, which the 113-dim observation
does not contain, so **the conditional policy the judge defines is not representable by the student**, and what the
student actually learns is an unconditional drift toward the challenger of roughly the override rate. That single
mechanism also explains why the *content* of the proposal barely matters: a drift of the same size toward a
content-free proposal costs nearly the same as a drift toward `T_NEXT`'s, because the cost comes from leaving the
anchor, not from where it lands.

What this does **not** settle: whether the rule-level composite gain would also have required coordinated adoption
(explanation two). It no longer needs to be settled to act, because explanation one is sufficient to predict the measured
dose-response and is now measured rather than hypothesised.

What **is** established, and worth keeping regardless of what happens next:
1. A judge-arbitrated composition of two specialists is a genuinely better **rule** (+6.13 % over T0, non-learned) and a
   genuinely worse **supervised target** than the anchor alone (−2.8 %, 2/24 and 2/24 paired). Those are not the same
   question, and the project now has both numbers on the same physics.
2. The second specialist does contribute **inside** the arbitration family — `v2 FULL` beats its own A-only on one seed
   (+1.44 %) and its own null on both (+0.98 %, +7.87 %), and both FULL arms beat `B-only` by ≈ +5.2 % on 24/24 and
   23–24/24 paired episodes. It is the family that sits below the unconditional anchor, not the second source's
   contribution inside it.
3. `B-only` (the foresight specialist alone, judge-gated against the learner's own action) is +7.6 % over `D0` — the
   source carries real information; it just cannot be spent by overwriting the anchor's labels.

## 4. The hypothesis that would have to change, and the channel the evidence points at

Falsified in this channel: *"a per-decision better target, by a fixed-price one-step judge, makes a better learner."*

The evidence points at the channel the owner's ruling listed **first** and which I chose not to build first: leave the
anchor's label untouched and let the second specialist intervene through **experience / exploration** — its action
*executed*, with the real reward and the real next state, gated by the same judge against the learner's own action, with
a declared dose and full source accounting. Three reasons, each from the table above: the damage measured here is caused
by label replacement, which that channel never does; the anchor's label channel stays exactly `D3-T0`, so the floor is
the strong single Catfish by construction; and `B-only`'s +7.6 % over `D0` says the source has information to inject.
This is also the CDRL intervention shape (catfish-collected experiences entering the main learner's training) rather
than a relabelling, so it is closer to the original method, not further from it.

A second, narrower option, if the owner prefers to stay in the label channel: make the gate **observable-consistent** —
decide the override on a fading-free, nominal evaluation so that identical observations always carry identical targets.
That attacks explanation (a) directly, but the dose-response above shows the cost is present even for content-free
proposals, so I rank it second.

**Both options are new mechanism versions and neither is authorised by contract r2. They go to the owner.**

## 5. What I am doing with the idle capacity, declared before it is read

Nothing new is launched on the science side. One diagnostic, declared now: the 16 selection-seed runs are **resumed from
their `resume.pt` to ep 300** (the configured budget was always 300 with `--stop-after 100`, so this is the same
configuration identity, not a new run — the only resumable extension the harness allows). The reading, fixed here: the
same clause quantities at ep 200 and ep 300 **on the selection seeds k = 10, 11**, reported as a depth diagnostic and
**never as a confirmation** — a confirmation still requires the three fresh seeds k = 12, 13, 14. The question it
answers is one the owner's decision depends on: E1 showed the `D3-T0` vs `D0` gap shrinking with depth (12.71 → 9.72 →
9.42 %), so the −2.8 % shortfall at ep 100 may narrow, hold, or invert by ep 300. If it inverts, that is a reason to run
a proper fresh-seed confirmation; if it holds, the label channel is closed on depth as well as on dose.
