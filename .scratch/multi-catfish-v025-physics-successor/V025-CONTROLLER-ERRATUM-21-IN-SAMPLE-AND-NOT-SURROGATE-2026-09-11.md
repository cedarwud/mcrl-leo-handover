# Erratum 21 — every route marginal so far is in-sample, and the runs were NOT on surrogate labels

Date: 2026-09-11 ~00:35Z · Controller · Found by CONVSCORE, not by me
Source: `/home/sat/mcrl-v025-convscore-ws/CONVERGED-EXACT-SCORING-2026-09-11.md`

## 1. All scoring is in-sample

**All 20 scoring-panel anchors are training anchors (20/20)**, world 1, steps 0-6, global
`000-019`, for every run and every panel combination; row by row, **19,617/19,617 decision
states identical**. Several panels were built directly from the corresponding run's training
files (identical SHA-256). The training sets have 22 anchors, so only `020`/`021` lie outside the
panel — **there is no non-overlapping panel anchor**.

**Casualties:** every route marginal reported to date, including
`Z-VIEW-SCORING-2026-09-10.md` in full (e.g. Q1 v2 `FULL - DROP_C1 = +12.691200`, +42.9183%,
16/16) and the one-seed `panel-q1v1` scoring behind `V025-CONTROLLER-PREDECLARATION-C3-NEGATIVE`.
In-sample scoring inflates a head's apparent contribution. **Those numbers remain valid as
paired, same-footing comparisons between runs; none is evidence of generalisation.**

Representation diagnostics (`SCALE`, `COLLAPSE`, `QCOLLINEAR`, `RAWDUP`, the learned-`a0` part
of `APPROACH`) were also measured on training anchors. They describe the trained heads on the
data they saw; label them so.

**Not affected:** every learner-free result — `STATICS2`, `CROWDCOST`, `CEILING2`, `COORDVALUE`,
`BASIN2`, `BEAMCAP` — reads no checkpoint.

## 2. The trainings were on exact labels, not surrogates

I stated repeatedly that the v1 / v2 / z runs were trained on surrogate labels whose argmax
disagrees with exact labels on C1 51.68%, C2 55.27%, C3 81.82%, and I used that as the main
reason those runs "could not be read". **That was wrong.** CONVSCORE compared the six training
corpora row by row: **0 label differences** against exact22 (21,532 C1/C2 rows; 4,552 C3 rows;
the v1 C3 files are byte-identical to exact22's). Both runner versions discard the
`exact_source_view` extension and read the same base label field.

The disagreement rates compare **exact labels with the sealed fallback**; no training corpus used
the fallback as its label. The surrogate finding (`v025-corpus-carries-surrogate-labels`) is
about **a different 176,223-row pilot corpus**. I extended it to runs it did not describe.

**Consequences:**
- The C3 negatives — v1 `-10.04` (16/16), v2 `-1.20` (14/16), z `-2.25` (15/16) — were on
  **exact labels**. Their remaining confounds are **non-convergence (500 constant-rate updates)
  and in-sample scoring**. In-sample scoring *favours* a head; C3 was negative anyway.
- The C1/C2 competition (C2 +6.13 under Q1 v1 -> -1.15 under v2) **is on exact labels**; it is
  not a label artefact. Whether it survives convergence is open.
- `EXACTTRAIN`/`EXACT93`'s value is **not** "removing the label defect" — the labels were already
  exact. Their value is the converged schedule and, for EXACT93, 93 anchors.
- `exact22` vs Z-VIEW Q1 v1 is a pure **schedule** comparison: same labels, schema, panel, seeds.

## 3. An undeclared change found in the process

The step-decay schedule was declared "from `1e-3`" on `DECAY`'s evidence, **which was measured on
C3 only**. Runner v2 applies one starting rate to all heads. **C1's literal was `1e-2`**
(`LRSWEEP`). So every step-decay run starts C1 **10x slower** than its literal. Not
outcome-selected — no EE existed — but not examined either. Recorded here; it must be stated
wherever a step-decay C1 number is reported, and a per-route start rate is a candidate for the
next generation.

## 4. Operational notes

- exact22 training was killed once (codex usage-policy error, 23:48Z) at seed
  `6114226365011333154`, update 3,200; auto-resumed 23:53Z. **That seed is marked RESUMED**; its
  4,000 checkpoint is scored only with that label unless resume is shown bit-exact.
- `panel-q1v1`'s receipt records 20 view paths whose current contents no longer match the
  recorded SHA-256 (replaced after the build; the difference is in unread surrogate-comparison
  records). A provenance break; the scored fields are unaffected.

## What replaces it

An **out-of-sample** development scoring panel built from anchors disjoint from **every** training
corpus, including the 93-anchor exact set (`OOSPANEL`, dispatched now). Until it exists, **no
route marginal is reported as more than an in-sample paired comparison.**
