# BLIND claim-structure review — progress notes (independent reviewer, 2026-09-11)

Status: DONE — answer written to BLIND-CLAIM-STRUCTURE-2026-09-11.md (COMPLETE). Did NOT read any controller ruling/note/erratum,
nor `PROMPT-BLIND.md` / `agy-blind/` (other reviewers' material) in this directory.

## Evidence read (primary, all on `sat`, read-only)
- [x] rank2 STATIC-BASELINE-FAMILY-CLEANPATH (RSS_MAX 41.62, FP 31.03, MYOPIC 31.08, RANDOM 11.23, BASE 11.03)
- [x] crowd CROWDING-COST (EE falls monotonically with active beams; crowded 46.11; no load term in F; TDM not max-power)
- [x] beamcap BEAM-CAPACITY-REALISM (crowded = partial service, 2.5% attainment; no hard cap)
- [x] ceiling2 CEILING-CLEAN-AND-LEVERS (clean coordination ceiling +0.84%; nested support +0.34%, saturated at |A|<=1+evac)
- [x] coord COORDINATION-VALUE (k=1 EE-improving from RSS_MAX 12/12; F rejects 3,671 EE gains, accepts 24,278 EE losses; 0/5,814 multiuser improvers in catalogue)
- [x] basin BASIN-BARRIER (k=1 F-improving from BASE; F order != EE order; F-first-improvement from RSS_MAX -> 31.81)
- [x] etafix ETA-EXCHANGE-RATE (no eta orders arms like EE; Dinkelbach eta*=41.62; descent persists per-anchor 9/12)
- [x] approach APPROACHING-THE-INSTRUMENTS (Q1/Q2 lack per-option gain; a0 92.5 users from RSS_MAX; catalogue binds C3)
- [x] c2target C2-TARGET-VALUE (oracle C2 +0.68% [-3.60,+5.73]; 0 under tie-break; endpoint blind to horizon; C1/C2 argmax agree 29.6%)
- [x] zscoring Z-VIEW-SCORING (learned five-arm marginals, 3 runs; C3 negative in all 3; sum of single-route marginals ~0 vs joint +10..+22)
- [x] convscore CONVERGED-EXACT-SCORING (all scores in-sample 20/20; converged runs pending; Z-VIEW labels were exact, not surrogate)
- [x] scale INTERACTION-SCALE (exact psi flips argmax 100/480; learned 36/480; different panel R2)
- [x] qcollinear Q-ROW-COLLINEARITY (no collinear-Q pathology; C2 rank deficit)
- [x] first-line summaries only: MODQN-REFERENCE (gate unmeasured), MODQN-BRIDGE (84/112 fields missing), EXACT93, RAW-DUP, Q1-V3/V4, C3-LEARNABILITY, KILL-TRIAGE, HORIZON, Q2-V2
- [x] solo / triobj / c3reach / hcell / multistep: NO report landed as of 00:42 UTC 2026-09-11 (only scripts/logs; not used as evidence)

## Contracts read (local)
- [x] STAGES-6-8 CONTRACT v1, v1.1, v1.2 (C1+C3 = dF identity; C6 zero-results rule; v1.2 item 3 admissible learned claims)
- [x] PRIORITY DECLARATION v1.8 (full-buffer numerator; energy boundary), v1.9 (C2 tie-break => zero oracle; per-arm ranking keys), v1.6 §2 grep
- [x] DESIGN-FREEZE-AND-CLOSURE-RULE; MODQN-COMPARATOR-BINDING
- [x] V0.3 authoring contract §1 (survival = combined score on held-out EE)
- [x] DESIGN-STATE-2026-09-10 (treated as interpretation; two statements contradicted by measurements: per-beam max power; demand-capped numerator)
- [x] code: src/mcrl/runtime/energy_efficiency.py r1 (eq 3.25); sat run_v025_matrix_probe.py catalogue (s0-top-two = gain-ranked whole-network proposals)

## Running findings (settled)
1. Routes are one objective by definition: C1 + C3 = F(a_A) - F(a0) exactly; C2 = continuation of same F. Not distinct objectives.
2. That objective F = B - eta_ref E - Phi misranks pooled EE for every eta (ETAFIX, BASIN2, COORDVALUE) -> "each route raises EE" is not guaranteed even at oracle.
3. Learned ablations (in-sample, 500-step, dev panel): C1 marginal positive pooled 3/3 runs (sign-consistent 1/3); C2 sign schema-dependent; C3 negative 3/3; DROP_C3 is best arm in all 3 runs (~43 Mbit/J).
4. Sum of single-route marginals ~ -1.6 / +10.3 / -0.1 vs FULL-ALL_NEUTRAL +10.7 / +22.0 / +19.2 -> substitutes, not additive.
5. Oracle C2 null at the only existing endpoint; horizon value unmeasured (instrument missing; MULTISTEP in progress).
6. C3: no coordination barrier; clean F-coordination ceiling <1%; catalogue lacks improving multi-user moves; learned C3 harmful.
7. Nothing compared to RSS_MAX or MODQN on a common panel; MODQN unmeasured; everything in-sample, one date, 1-2 worlds.
8. Oracle C1's gain over BASE runs mostly through the catalogue's gain-ranked s0-top-two proposals (83/93 picks) -> C1 value beyond a gain heuristic is unmeasured.

## Answer file
`BLIND-CLAIM-STRUCTURE-2026-09-11.md` — COMPLETE (2026-09-11).
