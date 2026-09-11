**The top three old-project concepts to retry here are (1) specialist demonstrations as margin-free replay, (2) an advantage-gated large-margin loss, and (3) CA-CPBR catfish-only potential shaping with a new potential and a new control signal. The old project recorded failures for the first two, but the causes it recorded are not present in this project. The third was never actually exercised there.**

# Concept harvest: which old-project concepts to retry here, judged by whether each old outcome's cause is present

Date: 2026-09-11. Agent HARVEST. Read-only: no training, no server job, no code run except `ls`/`grep` and one read of an existing JSON summary.

## 0. How to read this

**The rule applied.** An old outcome transfers only if its recorded cause is present here. The verdicts mean:
- **RETRY**: the cause is absent here, or the concept was never exercised.
- **ADAPT**: the idea transfers, but a named component is tied to the old environment, or points the wrong way here.
- **DROP**: only when a measurement or code fact in this project contradicts the concept's premise. That fact is cited.
- **OUT**: the concept changes the deployment boundary, the declared endpoint, or the physics. Those are owner decisions, not transfer questions.

**Evidence tags.**
- **SAY**: the old records say it. Quoted or paraphrased, with the file cited.
- **[I]**: my inference.
- **[V-here]**: a measurement or code fact in this repository.

**Where the old evidence came from.** Six read-only extraction workers read about 300 old documents plus the old code. Their per-concept extracts, with file:line citations, are the audit trail for every old-outcome claim in this report:
- `parts/A-june-design-corpus.md` (62 concepts)
- `parts/B-catfish-v2-early-july.md` (47)
- `parts/C-catfish-v2-late-july.md` (35, plus the lr root-cause file)
- `parts/D-docs-packages.md` (65, plus the 2026-08 handoff)
- `parts/E-code-and-defects.md` (code inventory and trainer defect audit)
- `parts/F-phasec-routec-hazard.md` (35, plus old-environment geometry)

About 250 raw entries collapse into the roughly 60 rows of §3.

**Path abbreviations.**
- `OLD` = `/home/u24/papers/modqn-paper-reproduction`
- `FBD` = `OLD/analysis/family-b-collapse-diagnosis`
- `CV2` = `FBD/catfish-v2`
- `SRC` = `OLD/src/modqn_paper_reproduction`
- `ARCH` = `OLD/archive/src-eras`
- `DOCS` = `OLD/docs`
- `FABLE` = `/home/u24/papers/fable`
- `HERE` = `/home/u24/papers/mcrl-leo-handover/.scratch`

---

## 1. The local-fact panel every verdict is judged against

| id | fact in this project [V-here] | source |
|---|---|---|
| **H-END** | The endpoint is pooled EE, a ratio of sums. The trained objective `0.5r1+0.3r2+0.2r3` is anti-aligned with it: `MAX_NOMINAL_GAIN` beats the checkpoint by +19.8% (13.2 sem), on both bits (1.146×) and joules (0.957×). The gap survives the anchor ablation, ratio 1.1975 → 1.2222. | `HERE/deep-research/00-EVIDENCE-LEDGER.md` |
| **H-FRONT** | The observation-only hysteresis rule `A m=12dB` dominates the checkpoint on pooled EE (+8.9%, +6.7 sem, n=48), on handover rate (0.2258 vs 0.2796, −16.9 sem) **and on the learner's own calibrated scalar** (+1.2232 vs +0.9033). `A m=9dB` is +13.5% at a tied handover rate. The consolidation rules `B1/B2` light 38 beams against 64–72 for the others, and reach +11% EE while cutting both bits and joules roughly in half. At every handover budget the learner sits inside the rule frontier. | `HERE/feasible-frontier/FEASIBLE-FRONTIER-2026-09-11.md` §1, §3, §5 |
| **H-DEMO** | So this project has better-than-learner sources on **both** objectives. Each reads only the learner's own observation (block 1 incumbent, block 2 gain, block 4 loads; FEASFRONT §2). The ruling "no demonstrator on the trained objective" covered only myopic additive rules (FEASFRONT §5.4). | as above |
| **H-COV** | **The JSRL guide prefix hands the learner novel states.** 1-NN novelty ratio R rises from 1.00 at h=0 to 1.40–2.20 for h ≥ 1, and out95 rises from 0.05 to 0.28–0.74. The novelty lives mainly in block 4 (loads) and block 2 (SINR), and it survives on same-incumbent rows. | `HERE/feasible-frontier/scripts/jsrl.out`, `jsrl_blocks.out`, `PROGRESS.md` |
| **H-COLL** | **Collapse is UNDETERMINED.**<br>• G-3 has no thresholds, and `q_margin`/`q_entropy` do not separate a trained policy from a random one.<br>• MODQN is physically spread: 68.7 beams, modal occupancy 4.17%.<br>• Its choices are concentrated by slot: slots 7 and 21 take 69.18% of selections.<br>• **Q-row collinearity has never been measured on the MODQN trainer.** The only measurement is on stage-C heads (0.36–0.48, near the 0.2735 floor). | erratum 24; `HERE/reviews/evidence-bundle-2026-09-11/reports/MODQN-COLLAPSE-2026-09-10.md`; `…/Q-ROW-COLLINEARITY-2026-09-10.md` |
| **H-SPREAD** | Spreading is EE-negative *other things equal*, for two reasons: interference is z-gated and load-unweighted, and `R_beam = B·mean SE`. The one measurement in the declared estimand is z-inplace: **−3.51%** pooled EE, +3.38 beams, n=1, width not controlled. **But** "concentration is a property of the physics" was withdrawn; which beam each user takes (gain) dominates. `max`-over-users beam power is non-standard (dr2), so the sign depends on the model. | erratum 25; erratum 24 §2; erratum 22; `HERE/deep-research/CONSOLIDATED-RULING-2026-09-11.md` §2b |
| **H-DYN** | **Transitions carry state across steps.** Block 1 is the realised incumbent and block 4 is the previous step's loads. The power segment ages while a link is held (0.825 → up to 1.65 W) and resets on any association change. Anchor ablation moves per-arm EE by +0.99% / −1.05% / −1.27% / −2.75%. An episode is 10 × 30.08 s = 5.0 min, against a measured **6.3 min p50** service window at ≥10°, so serving satellites set *within* episodes. Handover rate is 0.28 per user-step, and handovers cost 0 J. | ledger; `src/mcrl/env/dwell.py:25-29`; FEASFRONT §5.3 |
| **H-OBS** | Observation is 112 = [access one-hot, per-candidate SINR with previous-step interference, off-axis θ in rad, previous-step load]. It has no elevation or time-to-exit feature. The action index is user-relative. There is **no per-satellite beam-count cap** ("deliberately no per-satellite beam-count constant anywhere in this project"). | `HERE/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md` follow-up §1, §3 (citing `action_contract.py:60-64`) |
| **H-SERVE** | Served fraction is 0.996–0.999 in every non-random arm. Outages leave ≤ 0.4% of headroom. | FEASFRONT §3 |
| **H-LR** | **This project's own lr sweep reproduces the old lr=0.01 collapse signature.** Calibrated scalar at lr 0.001 is 0.986; at 0.003 it is 0.406; at 0.01 it is −0.892, with argmax_distinct 1.92 of 28 and argmax agreement 0.84. The main run uses 0.001. (The brief's "21/21 route × lr inadmissible" has no source I could locate locally.) | `/home/u24/papers/mcrl-leo-handover/artifacts/training-2026-08-25-rerun01/p6-summary.json` (read this session) |
| **H-DEF** | **Three trainer defects.**<br>• D-1, per-head bootstrap: fixed in `5219995a`, on the shared branch.<br>• D-2, outage free ride: `832471ca`, b0 branch.<br>• D-3, uncalibrated logged scalar: `0acd146c`, b0 branch.<br>The pilot is pending. | `HERE/b0-corrected/PROGRESS.md`; `HERE/penalty-arm/PROGRESS.md` |
| **H-PEN** | **The `srank` penalty has already been measured here** (Kumar, α=1e-3, 500 episodes, D-1 in, D-2 out). OFF 88.89 M, PENALTY 86.00 M, NULL_PENALTY 85.77 M bit/J: no separation from the null arm, and neither beats OFF. The `decorr` penalty was **not** ported, because it needs one step's U=100 Q rows. | `HERE/penalty-arm/PENALTY-ARM-2026-09-11.md` |
| **H-TRAIN** | Trainer: 1-step TD, γ=0.9, one uniform FIFO buffer (50k). None of n-step, margin, PER, pre-training, double-Q or L2. **Three separate Q-networks with three optimisers, so the heads share no parameters.** 1.587 s per training episode. | ledger; catfish-surface §2–§8 |

### 1.1 Differences that make an old verdict non-transferable (the brief's six, corrected, plus eight more)

1. **Environment.** SAY: `family_b` had a hard cap of k_cap = 3 beams per window satellite. Users on a 4th-ranked cell were "cap-bumped" to r1 = 0 (`DOCS/catfish-explainer-package/02-collapse-mechanism.md:42-67`). Here there is no cap (H-OBS) and service is ≈ 0.998 (H-SERVE).
2. **Metric.** Every old catfish-era number is `argmax_EE`, a **mean over users of per-user ratios with unserved users counted as 0** (parts/B §0, verified in `CV2/score_inj_rung1.py:135-140`). SAY: "EE = −674·cap_bump + 601, R² = 0.945 over 25 arms" (`FBD/CATFISH-VS-DQFD-DESIGN-2026-07-15.md` §9.1). Pooled EE was only a side diagnostic, and there it was **nearly policy-insensitive**: "random 5.85e8 ≈ DQN_scalar 5.96e8, within 2%" (`FBD/HANDOFF-coverage-free-ee2-catfish-2026-07-05.md`). Here pooled EE spans 53.1 M (random) to 112.5 M (a rule), a factor of 2.1. The only old line scored on a ratio of sums is the August Phase-I line (parts/D COND-FB-AUG).
3. **Learning rate. The brief's framing is right but needs dating.** SAY: "Flipping ONLY the learning rate (0.01 → 0.001)… doubles argmax EE and lifts worst-user coverage from 0.312 to 0.698" (`FBD/COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md:3-6`). Every June to mid-July MODQN-family arm ran at lr 0.01.
   - **But the late-July and August negatives ran at lr 1e-3:** SCFZA catfish −20.37, full DQfD −83.15, margin-OFF demo replay −42.25, the capacity penalty +89 to +135, and Phase-I B/N 0.73.
   - These are the strongest old negatives. They must be answered on causes other than lr.
4. **Wiring. The brief overgeneralises.** SAY: no old trainer distilled from a frozen copy of its own main (parts/E §1, grep).
   - The "distilled over rounds" wiring belongs only to the June P4, 6-arm and route-C lines: "All arms warm-start from a READ-ONLY copy of (P)", rounds R0–R3, with the main trained by **supervised CE imitation, not env-reward TD** (parts/A COND-P4-6ARM, citing `FBD/p4-coverage-multiteacher-catfish-prereg-2026-06-24-v5.md` §6 and v6 §3).
   - That wiring is exactly where CA-CPBR ran. Every other line trained the main from scratch.
5. **Physics. Old power grew with load: `P_b = min(0.25 + 0.35·√L, 10)`.** SAY: "the entire +54.9% comes from OPENING MORE BEAMS and BALANCING LOAD" (`CV2/ORACLE-AND-CATFISH-ABLATION-VERDICT-2026-07-13.md:56-64`). Handover energy was zero there as here.
   - Here per-beam power is a `max`, the PA takes ~94.8%, and lighting a beam costs ≥ 6.267 W.
   - **The sign of "spreading" flips between the two projects.** Every anti-homogenisation potential or penalty therefore needs its sign re-derived.
6. **Defects.** See §2. In short: defect (a) splits the old evidence into two lineages. (b) is absent from every old environment. (c) is present in almost every family_b trainer.
7. **Decoder.** Most old catfish and injection arms trained through, or were scored through, a coordinated auction decode. SAY: that decode "delivers ~420 EE on its own" and is "exactly invariant" to per-user Q offsets and global rescales (`CV2/DECODE-TRANSFER-FINDING-2026-07-12.md:44-52, 386-388`). Q-side improvements were structurally hard to see. Here deployment is pure per-user argmax.
8. **Temporal structure.** SAY (family_b): 10 steps of 1 s each; the serving window is chosen at reset and frozen; the episode sees "0 / 5000" window exits; and the persistence probe measured "ΔEE at t+1 and t+2 = 0.0000 exactly" (parts/F Part 4; `CV2/NULLSPACE-PROBE-RESULT-2026-07-21.md:19-27`). Here see H-DYN.
9. **Teacher type.** The old better-than-learner teachers (F-mean, G, ORACLE, planners) were joint, congestion-game solvers. SAY: their per-user action "is a function of information the per-user OBSERVATION does not carry… fits LABEL NOISE" (`CV2/CONVERGE-PROBE-RESULT-2026-07-17.md:32-44`). Here the better-than-learner sources read only the learner's own observation (H-DEMO).
10. **Checkpoint selection.** Old runs selected the best-eval checkpoint on the **raw** scalar, which r1 dominates (defect c). The selected checkpoints were early: median 30% of training, and the faithful catfish's was **episode 99 of 3000 on all three seeds** (`CV2/TRAINING-DIVERGES-FINDING-2026-07-12.md:18-32`). Here the scored artefact is a declared checkpoint.
11. **Reward-driven collapse.** SAY: legacy r3 was max−min over *active* beams only. "r3 ≈ FULLY offsets the EE penalty (129% discounted)" and rewarded collapse (`CV2/R3-DISCOUNTED-RESULT-2026-07-14.md:25-31`). Here r3 = −U_{b_u} per user. It is misaligned in a different direction: it rewards spreading (erratum 25).
12. **Outage handling.** SAY: re-entry after an outage is charged φ2 in both projects (parts/D D-35). The r2/r3 free ride on unserved users (defect b) exists only here.
13. **Only one old concept was scored on pooled EE with a healthy lr and no decoder: the August Phase-I line.** It still had k_cap = 3 and defect (a) (parts/D D-33/D-34; parts/E row 15-16).
14. **Pooled EE here moves with the gain-following decision** (erratum 22: "What matters is *which option each user takes* (gain), not how many beams end up open"). The old line's levers were coverage and cap_bump, which do not exist here.

---

## 2. Did the old trainers share this project's three defects? (brief item 6)

Source: `parts/E-code-and-defects.md` §1. Every line there was read by the worker, marked 親驗 (read in person).

| defect | old status | which old verdicts it contaminates |
|---|---|---|
| **(a) per-head bootstrap** (each head's own `max_a'`) | **Lineage P, has it:**<br>• base `MODQNTrainer`, `FamilyBRetrainMODQN`, `offset_fix`<br>• `catfish_faithful_familyb` (main, catfish critic and 70/30 conduit all go through `modqn.py:696/763`)<br>• `modqn_faithful_ablation` and `phase1_trainer` ("paper-faithful", **deliberate**, `trainer.py:700-757`)<br>• archive `catfish_faithful`, `per_objective_catfish`, `coordinated_multi_catfish`<br>• the CA-CPBR CF net (`ARCH/demo_guided_catfish/shaped_q_trainer.py:346-384`)<br>• `ISO_M`<br>**Lineage S, free of it:** every trainer that bootstraps at one scalarised a′ (Double-DQN): route-B, `injection_rung1`, `trainer_std/concat/penalty`, `catfish_pack` (abl9k), `preq_ee`, `family_b_r3`, `sequential_decode` | **Contaminated:**<br>• the June paper-baseline and family_b retrains<br>• the P1 faithful catfish on family_b (`CV2/FAITHFUL-CATFISH-EFFECT-VERDICT-2026-07-08.md`)<br>• the June per-objective and coordinated multi-catfish pilots<br>• the CA-CPBR CF critic<br>• **August Phase-I, R5/R6 prefill and the EXP isolation, B/N 0.73.** This is the old negative closest to this project's conditions, and it is (a)-contaminated.<br>• The ISO "collapse lives in the MODQN value-decomposition bundle" finding changed (a) and the head architecture together (parts/E row 21).<br>**Not contaminated:** SCFZA catfish, every DQfD/injection wave, z-score, the capacity penalty, and abl9k ACRM. |
| **(b) outage free ride** (r2 = r3 = 0 when unserved) | **Absent from every old environment.** Old r3 was one global number shared by all users (`env/family_b_step.py:1455`), and r2 was charged on the action whether or not the link was admitted (parts/E §1). | Nothing. But **porting any old mechanism brings no protection against (b)**, so D-2 must land before any arm runs here. |
| **(c) uncalibrated logged scalar** | **Present in nearly every family_b-era trainer.** Replay received calibrated rewards while `EpisodeLog` and the best-eval checkpoint selector used the raw scalar, which r1 dominates (raw r1 scale ~1e9–1e15). A related defect, D7: the logged `r1_mean` is 10× the per-step EE (`faithful_catfish_trainer.py:549`). | **Every old "best checkpoint" was in effect picked on r1, and usually early** (item 10 above). A mechanism's early transient help was scored while its late harm was not. |

**Inferred [I].** Defect (a) interacts badly with off-policy injected data, because each head's own max over-estimates independently. So the August Phase-I finding that "the intervention conduit is the only active ingredient and it harms the endpoint" (parts/D D-34) cannot be read as clean evidence against injection until it is re-run on a shared-a′ trainer.

---
