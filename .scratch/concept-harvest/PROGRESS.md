# HARVEST — PROGRESS

Agent: HARVEST (read-only). Report: `CONCEPT-HARVEST-2026-09-11.md` (this dir).
Resume rule: continue from the first unchecked cluster; do not re-read checked clusters
unless a note below says a follow-up is needed.

## Clusters

- [x] 0. This project's state: `00-EVIDENCE-LEDGER.md`, `CONSOLIDATED-RULING-2026-09-11.md`,
      `V025-CONTROLLER-RULING-CONCEPT-TRANSFER-2026-09-10.md`, erratum 20, erratum 26 (read 2026-09-11)
- [ ] 1. Prior 44-concept sweep `SIBLING-CONCEPT-TRANSFER-2026-09-10.md` (local copy in reviews/evidence-bundle)
- [ ] 2. Old project: catfish-v2/, prereg/verdict files, CA-CPBR, 6-arm verdict
- [ ] 3. Old project: newalgo-design-v0-candidates, catfish-last-design-candidates, development-direction, thesis-narrative-frame, PRIOR-ART-CARDS
- [ ] 4. Old project: shared_q_isolation (penalties, EXP, ACRM), lr=0.01 root cause, other design notes
- [ ] 5. Old trainer defect check (per-head bootstrap / outage free ride / uncalibrated scalar) in archive/src-eras
- [ ] 6. docs/catfish-explainer-package
- [ ] 7. Synthesis table + shortlist + multi-catfish candidates -> report

## Notes

- 2026-09-11: cluster 1 (prior 44-concept sweep) read. It filtered on V0.25 stage-C facts F1-F9,
  several now obsolete (routes dead; catfish attaches to MODQN trainer). Many rejections were
  "no present fact identifies X as binding" — not a contradicting measurement. Re-judge.
- 2026-09-11: dispatched 5 extraction sub-agents (background), each writes to `parts/`:
  A = June design corpus, B = catfish-v2 07-08..07-12 + PRIOR-ART-CARDS, C = catfish-v2 07-13..07-21
  + LR root cause, D = docs/explainer packages + 08 handoffs, E = old code inventory + trainer
  defect check. On resume: if a `parts/X-*.md` exists and looks complete, do not re-dispatch X.
- Meanwhile controller (me) reads this project's current measurements: catfish-facts, lfd-family-screen,
  dqfd-grounding, feasible-frontier, Q-ROW-COLLINEARITY, MODQN-COLLAPSE, b0/penalty progress.
- DONE local-fact panel (to cite in report):
  L-FRONT: FEASFRONT — hysteresis `A m=9/12dB` beat trained on pooled EE AND trained scalar (+1.22 vs +0.90)
    AND handover; B1/B2 consolidation 38 beams +11% EE; D_HOLD low-ho; => better-than-learner teachers
    exist on BOTH objectives (overturns "no demonstrator on trained objective", which was myopic-additive only).
  L-PEN: PENALTYARM srank α=1e-3 500ep (D-1 in, D-2 not): OFF 88.89M, PENALTY 86.00M, NULL 85.77M; null.
    decorr kind NOT ported (needs per-step U=100 Q rows; minibatch lacks them).
  L-COLL: collapse UNDETERMINED (erratum 24); MODQN physically spread 68.7 beams but slot-concentrated
    (slots 7,21 = 69%) (MODQN-COLLAPSE); Q-row collinearity measured ONLY on stage-C heads, never MODQN.
  L-Z: MODQNZ z-inplace −3.51% pooled EE, +3.38 beams, n=1 (erratum 24).
  L-SPREAD: erratum 25 (interference z-gated load-unweighted; R_beam = B*mean SE) => spreading EE-negative
    ceteris paribus; erratum 22: "concentration" as beam-count property withdrawn on V0.25 panel (gain dominates).
    dr2: max-over-users power is non-standard (model-dependent).
  L-LR: this project's own P6 sweep (artifacts/training-2026-08-25-rerun01/p6-summary.json): lr 0.001 scalar
    0.986, 0.003 0.406, 0.01 −0.892 with argmax_distinct 1.92/28 and agreement 0.84 — lr=0.01 collapse
    reproduces here; main runs at 0.001. "21/21 route x lr inadmissible" source not located locally.
  L-B0: D-1 5219995a (shared branch); D-2 832471ca, D-3 0acd146c on b0 branch; pilot pending.
- Added 6th extraction agent F (phase-c-forward, analysis/phase-c, thesis-route-c newalgo narrative,
  hazard/criticality "Claim B" lineage, fable salvage map, env-rebuild-bodyfixed geometry) ->
  `parts/F-phasec-routec-hazard.md`. Reason: those dirs were outside A-E.
- B complete (47 concepts) and D complete (65 concepts) — both read by controller. Key conditions:
  B: lr 0.01 all MODQN arms, mean-of-ratios EE, coordinated decode dominates (washes out Q), k_cap=3
  cap-exclusion, P∝√load, best ckpt early (faithful catfish ep 99), per-head bootstrap recorded.
  D: Aug Phase-I (D-33/D-34) is the CLOSEST-condition old negative: lr 1e-3, ratio-of-sums EE, from
  scratch, but k_cap=3 ON, per-head bootstrap ON (SDD-01 B1), ADR-003 physics; faithful catfish B/N 0.73,
  intervention-only active & harmful; local_snr_greedy prefill NO-PROMOTION (H/B 0.88), source only
  proven vs uniform, never vs learner. Capacity penalty (+89, 6/6) depends on k_cap (absent here).
  Lead to check at synthesis: old "hazard" lever killed because family_b cells Earth-fixed + frozen
  windows (fable.md); here beams drift relative to users (FEASFRONT C1_SAT_LOCK note) => cause may be absent.
