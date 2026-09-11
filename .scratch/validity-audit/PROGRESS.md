# Validity audit (blind) — PROGRESS

Agent: fresh-context blind validity auditor (Claude). Started 2026-09-11.
Brief: `.scratch/validity-audit/PROMPT-BLIND.md` (read in full).
Output: `.scratch/validity-audit/VALIDITY-AUDIT-BLIND-2026-09-11.md`.

## Blindness log
- No `ssh sat`, nothing under `/home/sat/`.
- Forbidden files not opened (list in brief). Any accidental pilot-number sighting will be logged here.
- INCIDENT (12:36 UTC, on resume): the environment's git-status block showed a new commit subject line "agy blind validity audit (DEAD-PATH) + controller check: cross-archive numbers and wrong citations, kept as hypotheses only". I did NOT open `.scratch/reviews/validity-agy/`; the other reviewer's verdict word reached me through the commit subject only. No pilot number was seen. My verdict below is derived independently from the artefacts and code; this sighting is disclosed in the report.
- `.scratch/cf3-pilot/report/` now exists (untracked); not opened.

## Reading status
- [x] PROMPT-BLIND.md
- [x] HANDOFF-2026-09-11.md §2–§8 (skipped §1)
- [x] DOCUMENT-STATUS.md §0–§1
- [x] cf3-pilot/PROGRESS.md lines 1–148 (premeasure captured; note: HOLD section mentions ep-100 progress readings of the ABORTED 10:25 launch (A1 s1/s2/s3 100.6M/90.9M/100.8M) — aborted, not a result; logged here for transparency)
- [x] forecast lines 1–57
- [x] Declaration + Amendments 1–3 + DECLARATION-ADDENDUM
- [x] Endpoint + errata 25/27/28/29 + rulings (penalty, catfish-attaches, plan, eval contract, trained-objective, B0)
- [x] Measurement reports (item 5): FEASFRONT, CFSCREEN, POWERACCT, EEGAP, CAPPENALTY, B0, HARVEST, DQFDGROUND, CATFISHFACT, ACRM (first 260 lines), CF3REVIEW, agy-1, agy-2; registry §0/§3/§4a; ee-ceiling PROMPT.md only (its logs/results/scripts dirs NOT opened)
- [x] Code (item 6) DONE 12:30 UTC: constants.py, link_budget.py, step.py, interference.py, antenna.py, action_contract.py, service.py, d2.py, candidates.py, energy_efficiency.py, modqn.py, b0_pooled_ee_eval.py, state_encoding.py, trainer_spec.py (grep), outage_gate.py, replay_buffer.py; worktree 102b2d4d: cf_ratio.py, cf_sources.py, run_cf3_pilot.py, cf3_eval.py, cf3_pools.py, cf3_premeasure.py, cf3_common.py, tests/test_cf_ratio.py. (Interrupted by API limit 12:30; resumed 12:36 with context intact.)
- [x] External reviews gpt2/3/5 (gpt4 not opened)
- [x] MODQN paper located by web search: Y. Sun, Y. Zhai, W. Wu, P. Si, F. R. Yu, IEEE Commun. Lett. 28(12):2834-2838, 2024 (existence [V]; contents NOT read -> eq.(16)/weights/gamma are [R] from project code+docs). Sun-Zhu-Peng 2024 H_bar=0.004 budget: only via dr2.md/registry DR-16 [R]; paper not read. Literature searches done (CER, JSRL, DQfD family, fractional RL).

## Analyses status
- [x] A [x] B [x] C [x] D [x] E [x] F [x] G [x] H [x] I [x] J — REPORT WRITTEN 12:44 UTC: `VALIDITY-AUDIT-BLIND-2026-09-11.md` (first line = bold verdict DEAD-PATH as framed; then 繁中 executive summary; then sections A-J, claims table, risks table, queue table). Verified on disk after the second interruption (12:48 UTC). AUDIT COMPLETE. Phase 2 (pilot result + ceiling) not sought; awaiting the coordinator.

## Notes / running findings
- Section-B arithmetic (derived from premeasure, pinned, 24 cal ep = 240 steps): J per beam-step 187.7-193.0 for every arm (6.24-6.42 W/beam) -> power per lit beam is policy-invariant; bits/beam-step: TRAINED 1.76e10, C1 2.15e10, C2 1.92e10, B1 2.01e10, MNG 2.12e10, RANDOM 0.98e10 -> EE differences are entirely bits-per-lit-beam (mean spectral efficiency per beam). Marginal EE of the 24.4 beams C1 lights beyond B1 = 1.25e8 bit/J (> either pooled EE): adding gain-following beams is EE-positive at the margin. Per-user rate: C1 451 Mbit/s vs B1 258 Mbit/s (B1 halves throughput at ~same EE). Noise/beam 5.575e-13 W; CAPPENALTY OFF interference 3.29e-12 W -> I/N ~5.9 (interference-limited); cap-3 I/N ~0.68. P_DC(p0)=5.93 W, P_DC(p_max)=8.38 W. One-beam energy share per user label = 1.88 J = 1.56% of s_E.
- A0 head magnitudes (frozen ckpt last log): 0.5*r1c=+2.37, 0.3*r2c=-0.74, 0.2*r3c=-0.71 -> r2+r3 = 61% of the r1 term.
- Premeasure (pinned 427e6a91, sat, 24 cal episodes, no training): eta_0=110,507,234.83 (MAX_NOMINAL_GAIN); RANDOM 51.87M; TRAINED 93.90M/66.6 beams/3.0011e6 J; C1 A2dB 112.20M/62.98 beams/2.8926e6 J; C2 A12dB 100.99M/71.55/3.2685e6; C3 B1 104.19M/38.57/1.7867e6. s_B=1.3329e10 bits/user-step, s_E=120.617 J/user-step.
- CF3REVIEW probe: eta*E term changed argmax in 0/240 decisions; own-bits spread median 1.85 vs own-energy spread 0.0156 (units s_B, s_E).
- dE_sys diag: C3 vs incumbent, 50% within ±1.21 J; bimodal at ±188 J (= 6.267 W x 30.08 s = one beam).
- POWERACCT: PA share ~94% of P_sys; per-beam P_DC = 6.527*sqrt(p) W; p0=0.825 W -> ~5.93 W per beam; fixed 0.338 W/beam + 0.2 W/sat.
- EEGAP: EE ≈ (B/3)*SE/P_beam; beam count cancels at first order in denominator; CAPPENALTY: fewer beams raise SE via interference (numerator).
- FEASFRONT (unpinned): frontier flat 111.2–112.5M from m=2..6 dB; B1 halves bits and joules; learner dominated.
- CFSCREEN: only ep 0 paired on old harness; BC top-1 C1 0.84, C2 0.94, C3 0.71; probe of B1 reproduces ~70% of consolidation.
- DQFDGROUND: seeding w/o pretraining+margin = RBS/HER = DQfD's worst arms; R2D3 optimum demo ratio ~0.4%.


## Phase 2a (12:51-12:56 UTC)
- Unblinded ONE file: `.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md` (read in full). Nothing else opened.
- Section K appended below a double separator; blind part untouched. Verdict unchanged (DEAD-PATH as framed). Key: A2-A3 +0.78% (t 0.8; one pair by 0.05M), AUC identical; A1>A0 +17% = misalignment (+7..10%) + A0 late decline; all learned arms 5-8% below A m=2dB on the calibration set; J/beam-step 189-191 for all 12 runs.
- Awaiting phase 2b (ceiling).
