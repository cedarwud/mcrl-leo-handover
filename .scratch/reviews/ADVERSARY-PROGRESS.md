# ADVERSARY progress notes (checkpoint for a resumed reviewer)

Reviewer: Claude adversary sub-agent, 2026-09-11. Output: `ADVERSARY-NARRATIVE-2026-09-11.md` (same dir).

## Evidence read in full (primary, on sat, read-only)
- rank2-ws STATIC-BASELINE-FAMILY-CLEANPATH (six static arms; RSS_MAX 41.62, 1200 served, 24.75% attain; BASE 11.03, 960 served; RANDOM 11.23, 1102 served)
- crowd-ws CROWDING-COST (crowded 46.11, monotone negative EE slope vs active beams, N=2 exception; no load term in V0.25 objective)
- beamcap-ws BEAM-CAPACITY-REALISM (crowded 2.5% attainment, 29.7 Mb/s mean, min 0.65 Mb/s; 50 Mb/s is a synthetic setpoint, not demand)
- ceiling2-ws CEILING-CLEAN-AND-LEVERS (clean coordination ceiling +0.84%; support saturates at |A|<=1)
- coord-ws COORDINATION-VALUE (k=1 improves EE from RSS_MAX and crowded at 12/12; 0/5,814 multiuser improving moves in catalogue support; F rejects +7.85 Mbit/J)
- etafix-ws ETA-EXCHANGE-RATE (no eta orders six arms; RSS_MAX argmax at every eta; Dinkelbach 1 step; 9/12 anchors still fall at eta*; own-EE pricing tautological)
- approach-ws APPROACHING-THE-INSTRUMENTS (no per-option gain feature; a0 differs from RSS on median 92.5 users)
- c2target-ws C2-TARGET-VALUE (oracle C2 +0.68% CI [-3.6,+5.7]; FULL=C2_ONLY at 30/30 changed anchors; C2_ONLY -21.4% vs C1_ONLY; endpoint single-step open-loop)
- zscoring-ws Z-VIEW-SCORING (DROP marginals; DROP_C3 > FULL in all three runs; C2 marginal flips v1->v2 on same labels; 500 updates, unconverged)
- convscore-ws CONVERGED-EXACT-SCORING (20/20 panel anchors are training anchors: all learned scores in-sample; converged runs pending)
- solo-ws: scripts only, no report (SOLO launched 00:30Z 09-11). triobj-ws: only triobj-definitions.json (mtime 00:40Z 09-11). c3reach/hcell: empty. multistep: script only, empty logs.
- Also read: modqn step.py reward (r3 = -(max-min beam throughput)/U), MODQN-COLLAPSE headline, MODQN-BRIDGE headline (84/112 fields not derivable), BASIN2 headline.
- Local (one party's interpretation): priority declaration v1.0, v1.1, v1.9; MODQN comparator binding; rulings OBJECTIVE-IS-STRUCTURAL, CONCEPT-TRANSFER.

## Running objections (settled)
1. Post hoc decomposition: triobj LQ argmax = RSS_MAX, BC argmax = exact min cover = crowded endpoint; both EEs measured 6-8 h before triobj file was written. Necessity passes by construction.
2. Necessity vs BASE non-discriminating: RANDOM passes (11.234 > 11.028, served 1102 >= 960).
3. Mechanism: RSS gain over BASE is 71% joules; crowded 103% joules. "Bits side" is mostly an energy lever. Time side has no EE channel (Phi not in EE; primary cell interruption off; single-step open-loop endpoint).
4. Pareto pair = two non-learned configs each reached by ONE objective alone; contradicts "points no single route reaches". Attainment declared not demand.
5. Trained evidence shows dominance/substitution, not trade-off (Q1v1 DROP_C3 dominates FULL on EE, served, attainment; C2 overrides C1 in oracle).
6. Claim 4: linear price already picks argmax on six-arm set; triobj's ratio rule ignores LQ/BC/P entirely; fixed-objective-space rule is the linear weighting claim 4 rejects.
7. Baseline: P = MODQN r2; BC = sign-flipped MODQN r3; the method's distinguishing content may be "drop r3". MODQN V0.25 gate unmeasured.

## Status
- [x] evidence read
- [x] objections settled
- [x] review file written and complete (INCOMPLETE marker removed)
