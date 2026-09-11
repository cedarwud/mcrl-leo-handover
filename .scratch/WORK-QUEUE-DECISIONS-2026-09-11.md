# Work-queue decisions — 2026-09-11, new controller session (~12:15 UTC server clock)

Owner instruction (HANDOFF §6b): before dispatching ANY queued item, review each one — is it really needed, should its content change, can it be done faster or cheaper — and state the decision per item. Nothing was pre-approved.

**State at review (read-only checks on `sat`, 12:05–12:12 UTC server):** all 12 pilot runs `complete` at 1000 episodes; the detached post-job (PID 3438182) is evaluating final checkpoints (10 of 12 `eval/*.log` present); `REPORT-DONE` not yet written. **The controller has not read any pilot number** (no `readings.jsonl`, no eval JSON, no report) and will not until both blind audits are written. Server: load ≈10 on 20 cores, 69 GB available, `/tmp` 1.1 G of 46 G.

## Decisions per item

| # | item | decision | what changed and why | executor / cost | status |
|---:|---|---|---|---|---|
| Q1 | EE ceiling on the MODQN harness | **DO NOW, revised** | Still the single cheapest measurement of the biggest risk ("is there room above the rules"), and Q2 needs it in its phase 2. Revisions to the stopped brief (recovered from the old session transcript): (1) primary episode set = the pilot's 24 **evaluation** episodes, per-episode reseeded, so the ceiling pairs per episode with the pilot arms; references also on the 24 calibration episodes for the bit-exact placebo (RANDOM 51,866,475.485…; `A m=2dB` 112,195,917.54); (2) **benchmark `evaluate_actions` first and declare the sweep budget / episode coverage before the counted run** — the original brief had no cost control; (3) **service floor inside the search** (a move that unserves a served user is disallowed), with the unconstrained variant only as a labelled stress bound — pooled EE without a floor is degenerate (CAPPENALTY 1.162× at 58 % served); (4) lever split (bits-only / joules-only) kept; a nominal-information variant added only if cheap; (5) blind to the pilot's outputs; own server workspace, ≤ 4 processes, `nice 16`, 5 GB cap, pilot worktree's reseeded harness reused. | Claude **opus** (instrument has several traps: pairing, pin, floor, cost). Compute on `sat`, orchestrated from here. ~2–3 h wall incl. search. | dispatched |
| Q2 | Validity audit of the whole direction, blind then unblinded | **DO NOW — the owner's explicit request** | Brief written from §2b: well-posedness (A), physical source of headroom with a bits/joules/beams decomposition (B), the ceiling as an instrument (C), learner identifiability incl. the equal-share `E_u` / 0-of-240 probe and the Dinkelbach-in-DQN schedule (D), demonstration literature under two search framings (E), baseline fairness and what a referee would demand (F), claims table measured/inferred/assumed (G), dead-end risks with the cheapest settling measurement each (H), verdict + better-posed problem (I), and a ruling on Q4–Q7 (J). Reads artefacts and code, not summaries; forbidden paths listed (incl. FORECAST lines ≥ 58 and gpt4.md, which quote an early progress reading). **Two isolated blind reviewers** with the same brief — Fable (fresh context, Agent tool) and agy Gemini 3.8 Flash (High) — neither sees the other; blind derivations landing in the same place count as evidence, divergence is a red flag (memory: adversarial-review-before-overturning). Phase 2: each is given the pilot report and the ceiling result and asked whether the verdict changes. | Fable + agy; no server compute; ~1–2 h each, parallel. | dispatched. **agy finished in ~10 min with DEAD-PATH**; controller check found cross-archive numbers, arithmetic errors, a non-existent citation and a wrong description of Q4–Q7 (`.scratch/reviews/validity-agy/CONTROLLER-CHECK-2026-09-11.md`) → retained as hypotheses, not weighted as an independent derivation; agy's next use is an adversarial check of the Fable report. Fable audit running. |
| Q3 | Read the pilot report under the declared reading | **DO, split in two** | (3a) A fresh sonnet agent executes TAKEOVER §4 the moment `REPORT-DONE` exists (copy back with sha256 verification, write `CF3-PILOT-2026-09-11.md` from the generated tables, commit named paths); its final message to the controller carries **no numbers and no branch** so the controller stays blind. (3b) The controller reads the report only after both blind audits are written, then runs phase 2 of Q2. A background waiter on `REPORT-DONE` triggers 3a. | Claude sonnet, ~20 min. | 3a waiting on `REPORT-DONE`; 3b held |
| Q4 | Energy credit with explicit outage charge | **HOLD (gated on Q2)** | Unchanged in content; the audit is asked to rule on whether it is worth doing at all (J). Building it before the box is validated is the failure the owner named. | — | gated |
| Q5 | Full-length runs, seeds 0–4, drop-one arms | **HOLD (gated on pilot branch 1 + Q2)** | Cost note for the decision: 20 runs × 3000 ep at ~3–4 s/ep under 12-way contention ≈ two waves × ~3.5 h; needs Q7 first to be cheaper. | — | gated |
| Q6 | Demonstration-utilisation arms (faithful online catfish, DQfD margin, bounded ACRM, JSRL) | **HOLD (gated on a source-value signal + Q2)** | Forecast blind spot A (dense reward, 10-step horizon → demonstrations may have nothing to do) is a structural objection the audit answers first (E). | — | gated |
| Q7 | Speed-ups for Q5 (shared target forwards 12→3, concurrency benchmark, offline progress evals, mmap pools) | **DEFER until the Q2 blind verdict** | Only pays off if Q5 runs; the concurrency benchmark needs an idle server (pilot evaluation + ceiling search occupy it now). The shared-target-forward change is small (~1 h sonnet + bit-identity test on a short run) and can start the moment Q5 is approved. Nothing is lost by waiting a few hours. | Claude sonnet later | deferred |
| Q8 | Housekeeping (b0 worktree/branch; old codex watch loops on sat) | **VERIFIED, NOT EXECUTED — needs owner OK** | (a) `git merge-base --is-ancestor` says branch `b0/corrected-baseline-20260911` is **not** an ancestor of HEAD: four commits (832471ca D-2, 0acd146c D-3, 923d68b0 pilot driver, ccbbb048 fixup) are not on `wip/multi-catfish-v023-20260907`; the handoff's "all merged" may mean their content was ported as separate commits, but that is unverified — a content diff is needed before deleting. (b) On `sat`, three idle codex marker-watch loops (PIDs 1209666, 1332348, 1430512; `sleep 60` bash loops, > 2 days old) and `watch_stall2.sh` (PID 2469243, 1 day) are stale; `watch_health.sh` (PID 3291897) is the health monitor and stays. Cost of leaving them is nil; killing waits for the owner's OK per the handoff. | Claude haiku when approved | proposed |
| Q9 (new) | Curation: registry rows and document-status entries for the pilot and the ceiling; handoff update | **DO after Q3b** | Every citable pilot/ceiling number must land in `.scratch/RESULTS-REGISTRY.md` with its condition fields before it is quoted anywhere. | Claude sonnet, ~30 min | pending |
| Q10 (new, owner offer 12:45 UTC) | External review via ChatGPT: a pre-result artefact package + two prompts (general validity question; Deep Research on the literature questions that need no pilot result) | **DONE — package built, handed to the owner** | `.scratch/external-package/validity-2026-09-11/` (README, `PROMPT-CHATGPT-GENERAL.md`, `PROMPT-CHATGPT-DEEPRESEARCH.md`, docs/reports/code/briefs) zipped as `.scratch/external-package/mcrl-validity-package-2026-09-11.zip` (zip untracked). Pilot results excluded on purpose. Owner runs it; the answers are cross-checked against artefacts before use (as with agy). A second, post-result package follows phase 2 if wanted. | owner (ChatGPT) | handed over |

Owner note 12:45 UTC: agy may be used for cross-model help (`--model "Gemini 3.7 Flash (High)"` as typed; the 3.8 Flash (High) name worked at 12:23 today, so 3.8 stays the default and 3.7 is the fallback if 3.8 errors).

## Outcomes as of ~13:05 UTC (controller unblinded after the Fable blind report landed)

- **Fable blind audit** (`.scratch/validity-audit/VALIDITY-AUDIT-BLIND-2026-09-11.md`): **DEAD-PATH as framed.** Physics: joules per beam-step are policy-invariant (187.7–193.0 J across the six pinned premeasure arms), so pooled EE ≈ mean spectral efficiency per lit beam; a max-gain/hysteresis rule nearly maximises the per-user part; the only lever above the rules is co-channel interference across the joint lighting pattern (a coordination problem the per-user contract cannot express); the ratio learner is effectively an own-bits DQN (0/240 argmax flips from the energy term); static rule pools are DQfD's worst-arm configuration in a dense-reward problem; "beat A0" is reachable by dropping r2/r3 and says nothing about learning. Kill/alive thresholds for the ceiling: ≤ +3 % over `A m=2dB` → dead; ≥ +10 % with the nominal-information unilateral point capturing half → a per-user learner with a correct credit could have a job. Q rulings: Q5/Q6/Q7 no; Q4 conditional. Independently matches the controller's own bits-per-beam arithmetic (`.scratch/reviews/validity-agy/CONTROLLER-CHECK-…`), which it never saw.
- **Blindness incident (controller's fault):** the commit subject "agy blind validity audit (DEAD-PATH) …" reached the Fable reviewer through the git-status block of its environment context after a resume; it disclosed this and states its analysis was formed before. Recorded; memory `blind-review-hygiene-2026-09-11` written.
- **Pilot** (`.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md`; pinned, 24 evaluation episodes 9_111_000+i, final checkpoint, 3 seeds): seed-mean pooled EE A0 84.21 / A1 98.64 / A2 102.03 / A3 101.24 M bit/J; C-S non-inferior; **declared branch 1** (A2 > A3 and A2 > A1, each 2 of 3 seed pairs). Magnitudes: A1 vs A0 +17.1 % (3/3); A3 vs A1 +2.6 % (3/3); A2 vs A1 +3.4 % (2/3); **A2 vs A3 +0.78 % (2/3, one pair decided by 0.05 %)**. On the calibration episodes (same set as the premeasure) the 1000-episode readings are A1 102.9 / A2 106.2 / A3 105.4 against `A m=2dB` 112.2, `MAX_NOMINAL_GAIN` 110.5, `B1` 104.2: every learned arm sits below the one-line rule. A0's calibration reading fell from 95.6 (ep 500) to 86.4 (ep 1000). A1–A3 handover ~0.5 inter-satellite per user-step (~1.1 per user-minute) vs A0 ~0.19.
- Controller reading (pending phase 2 of the audit): the branch-1 call is formally correct under the pre-declared rule, but the directed-vs-random margin is below resolution at 3 seeds, random pools also beat A1, and the substantive results are the objective change over an unstable A0 and the learned arms' position under the rule. The pre-declared branch-1 plan (full-length runs + drop-one arms) is therefore **not executed**; the owner decides after phase 2 and the ceiling.
- **Fable phase 2a (13:00 UTC, section K of its report): verdict unchanged.** Rows of its claims table moved from inferred to measured on the pilot: joules per beam-step 189.4–191.3 J for all 12 runs; bits per beam-step A0 < A1 < A3 ≈ A2; learned arms −5.3…−8.3 % vs `A m=2dB` on the calibration set (A1 102.9 / A2 106.2 / A3 105.4 vs 112.2); directed-vs-random null (A2 − A3 +0.78 M, Welch t ≈ 0.8; AUC/900 identical 102.9 / 102.8 / 103.2); pools of any kind +2.6…+3.4 % at the final checkpoint only (a coverage/regularisation effect on `Q_B`, read as **branch 2 in substance** and, under evaluation-contract rule 2, "perturbation, not catfish"); A1 > A0 +17 % = misalignment (+7…+10 % at A0's best readings; A1(1000) 102.9 > MODQN(9000) 93.9 > A0(1000) 86.4 on the same calibration set) plus A0's late decline (seed 2: 92.6 → 78.5 between 750 and 1000; between-seed SD 6.6 %); learners re-anchor at 0.47–0.58 inter-satellite handovers per user-step (≈1.1/min, 2.7× A0) and still sit below the rules. Recommendation: Q5 no; report branch 1 as formal only; defensible gate number is +9–10 %, labelled as a diagnosis of MODQN's reward; wait for the ceiling; cheap follow-up = η→0 argmax-flip probe on the final checkpoints (H4).
- **Dispatched 13:15 UTC: H4PROBE** (sonnet, measurement only, own sat workspace, ≤ 3 processes): η→0 / 2η argmax-flip fractions and closed-loop EE on the 9 final checkpoints, plus an explicit own-bits greedy rule and the two reference rules on both episode sets, placebo-tied to the pilot's eval JSON. Pure diagnostic under the standing autonomy; no design change.
- Dispatched at ~13:05: Fable phase 2a (pilot result) by SendMessage; CEILING2 brief amendment (per-user throughput reporting; conditional variants: rate floor, nominal-information, compound beam-emptying moves, multi-init — only if the base search exceeds +3 %); agy adversarial check of the Fable audit (`.scratch/reviews/validity-agy-2/`); Q9a curation (sonnet).

## agy adversarial check of the Fable audit (13:20 UTC; `.scratch/reviews/validity-agy-2/AGY-CHECK-OF-FABLE-AUDIT-2026-09-11.md`) — controller adjudication

Verdict: 8/14 checks CONFIRMED, 6 WRONG-or-caveat, **DEAD-PATH SURVIVES WITH CORRECTIONS**. Re-derived by the controller (not counted):
- Accepted corrections: (a) "beam count cancels" is first-order only — mean SE per beam depends on the lighting pattern (the Fable audit's own marginal-EE arithmetic shows it); (b) I/N ≈ 5.9 is a CAPPENALTY figure from the pre-pin archive with retrained OFF weights — magnitude does not transfer to the pinned physics, the lever's existence does; (c) the 104/240 = 43 % figure is own-bits argmax vs the user's **unilateral** system-objective argmax (others fixed), not a joint argmax; (d) the arXiv link `2605.02416` for Sun et al. 2024 is wrong (2026 identifier); the project's thesis reference list (`.scratch/chinese-word-v023-lcsrs-20260905-r2/REFERENCES.md:137`, VERIFIED-LOCAL) gives the MODQN baseline as Sun et al., IEEE Commun. Lett. 28(12), 2024, DOI `10.1109/LCOMM.2024.3470890` — confirmed by the controller by grep; (e) "static pools = DQfD's worst arms" is overdrawn: R2D3/DDPGfD are themselves margin-free replay mixing (with n-step, PER and a ~1/256 ratio) — the fair statement is "R2D3-style mixing without n-step/PER at 30× the swept ratio, in a dense-reward problem"; (f) the ±3 % / ±10 % ceiling thresholds were judgement, not derivation.
- Not accepted as material: "throughput ≠ service" is a wording point (the audit's claim that pooled EE is blind to halved per-user rates stands); "Dinkelbach could act through continuation value" is possible in principle and is exactly what the H4 probe measures on the trained checkpoints.
- None of the corrections touches the load-bearing chain: joules per beam-step policy-invariant → EE = bits per lit beam → rules dominate every learned arm on the same episodes → energy term inert (0/240) → replay effect non-specific (A2 ≈ A3).

**Phase 2b reading rule for the ceiling, declared now (before any ceiling number is known to the controller), adopting the check's MDE-based proposal:**
- Paired per-episode comparison on the 24 evaluation episodes against `A m=2dB` (107,000,984 bit/J on that set, per the ceiling agent's reference run).
- **Dead for any learner**: constrained (service-floor) centralised search ≤ +3.3 % (≈ representability loss 1.3 % + 1.96 × paired sem).
- **Alive for a per-user learner only if** the nominal-information unilateral point exceeds the rule by ≥ 4.5 % (MDE at 5 seeds with seed SD ≈ 2.5 %, plus representability) with served ≥ 0.995 and bits ratio ≥ 0.95 vs the rule.
- Gains present only in the realised-information joint search → coordination/observability problem: a redesign of the decision contract (centralised or CTDE), not a fix of this learner.
- Between the two thresholds: report as "room too small to resolve with the seeds we can afford"; no training is launched on it.

## Owner rulings, ~13:35 UTC (`V025-CONTROLLER-RULING-Q5-NO-GO-AND-CEILING-SCENARIOS-2026-09-11.md`)

| item | ruling | executed |
|---|---|---|
| Q5 | **NO-GO** (the current three-catfish implementation is closed for full-length training; the multi-catfish question stays open) | recorded; nothing launched |
| paper framing | **not decided now**; decided after the ceiling under the three pre-declared scenarios A/B/C in the ruling | — |
| Q8 part 1 | kill the four stale watcher loops on `sat`; keep `watch_health.sh` | **done 13:38 UTC**: PIDs 1209666, 1332348, 1430512 (`bash -c seen=""; while true …` codex marker loops) and 2469243 (`watch_stall2.sh`) killed by exact PID after cmdline check; 3291897 alive |
| Q8 part 2 | `b0/corrected-baseline-20260911`: content-equivalence audit → archive tag → then worktree removal; **no branch deletion** | **audit done 13:50 UTC** (`.scratch/b0-corrected/B0-BRANCH-EQUIVALENCE-AUDIT-2026-09-11.md`, commit `7a7c47ab`): `0acd146c` and `ccbbb048` ported byte-identically; `832471ca` (flat D-2 floor) and `923d68b0` (shared-env eval harness) are **superseded in HEAD by later in-ancestry fixes** (`c00aca3e` per-step floor; `363845e8` fresh-env fix) — nothing is lost. Annotated tag `archive/b0-corrected-baseline-20260911` created at `ccbbb048`. Worktree left in place (clean, unused): the agent applied the strict "byte-identical" bar, and the controller's own removal attempt was blocked by the permission classifier. **Owner can remove it with `git worktree remove /home/u24/papers/mcrl-leo-handover-b0`** (reversible; branch and tag remain). |
| ChatGPT deep research | yes, in a new conversation | owner runs it with the delivered package |
| Q7 | no | closed |
| Q4 | wait for the ceiling (scenario B makes it top priority) | gated |
| Q6 | paused until source value / controllability is shown | gated |

## H4 probe result (13:55 UTC; `.scratch/h4-probe/H4-PROBE-2026-09-11.md`; both placebos bit-for-bit, all 9 deployed rollouts bit-identical to the pilot's eval JSONs)

Pinned archive, sat, 24 evaluation episodes, final checkpoints, inference-time η/λ variation only:
- **The energy head is not inert at the decision level on the trained networks**: switching η → 0 changes 11.0–42.2 % of the 24,000 decisions per checkpoint (A1 15 %, A2 22 %, A3 36 %; λ → 1 report-only: 44–62 %). The CF3REVIEW figure "0/240" was a one-step contrast of **raw rewards** and does not transfer to trained `Q_E`, which has learned action-dependent (continuation) values. **Correction to the Fable audit's rows 5–7 and to the controller's own earlier wording ("the energy term never acts")**: it acts; whether it helps is the question.
- **Its effect on pooled EE is small and inconsistent in sign**: closed-loop η → 0 changes EE by −8.1 … +3.1 % (mean −1.5 %): A1 +0.7 %, A2 +1.5 % (removing the energy term slightly *improves* both), A3 −6.6 % (all three seeds). Doubling η: A1 −2.0 %, A2 −13.3 %, A3 +0.6 %. So the learned energy signal does not deliver EE; it perturbs decisions, and for A1/A2 the deployed η is on the wrong side of neutral. This supports the audit's substantive point (equal-share credit yields no usable energy lesson) while refuting its "decorative / inert" wording.
- **The explicit own-bits greedy rule `(1/(load+1))·log2(1+γ)` scores below every learner**: evaluation set 93.76 vs A1 98.64 / A3 101.24 / A2 102.03 / MAX_NOMINAL_GAIN 104.67 / `A m=2dB` 107.00; calibration set 98.70 vs A1 102.9 / A3 105.4 / A2 106.2 / 110.51 / 112.20. It lights fewer beams (57.9) and churns most (H_inter 0.77). **Correction to the audit's D.i / K.4 characterisation "the learner is structurally an own-bits DQN"**: the learners are not reducible to that rule; they sit between it and max-gain. The learners' 5–8 % shortfall below `A m=2dB` stands; its mechanism (own-bits congestion vs under-optimisation vs representation) is **not** established by this probe.
- None of this changes the ruling (Q5 NO-GO) or the ceiling scenarios; it goes to Fable in phase 2b together with the ceiling, and to the registry (Q9b).

## Fast-iteration track (14:30 UTC, owner asked for faster iteration; pure measurement, no training, no new arms)

- **LP probe** (H4 agent resumed): the physics reading (EE ≈ bits per lit beam; joules ≈ constant per lit beam) turned into a deployable two-parameter rule family **LP(c, m)**: score(a) = log2(1+γ_a) − c·[beam a unlit], c ≈ η·P_beam/B_w ≈ 4.2 bit/s/Hz, with the `A m` hysteresis hold; c = 0 is `MAX_NOMINAL_GAIN`, c → ∞ is `B1_NO_NEW_BEAM`. Two information levels: **LP-prev** (simultaneous, previous-step loads) and **LP-seq** (sequential within the step, current-step choices of earlier users visible). Full grid c ∈ {0,1,2,3,4.2,6,8,12} × m ∈ {0,2,6} on both episode sets; in-family placebos (LP-prev(0,0) = MAX_NOMINAL_GAIN, LP-prev(0,2) = A m=2dB bit-for-bit). **Declared reading**: (i) best LP-prev ≥ +3.3 % over `A m=2dB` (paired, served ≥ 0.995) → a simultaneous per-user rule already pulls the lever and the beam-lighting price is the right credit; (ii) only LP-seq does → the lever needs current-step visibility (sequential decoding), not a coordinator; (iii) neither → per-user one-step information is insufficient. Cells with p10 rate < 50 % of the rule's are flagged throughput-degenerate. Rules stay diagnostics and candidate sources, never a gate. ~45 min.
- What this buys: an answer to the owner's "option 1 vs option 2 vs coordinator" question from rules alone, before any learner is redesigned, and a measured candidate source set for the next catfish definition ("as many sources as there are non-dominated lighting regimes").
- **Withdrawal note (14:40 UTC, ruling §1):** the interim search-log figures quoted in the 14:10 message to the ceiling agent and to the owner (per-episode 1.48–1.54e8 bit/J, "≈ +40 %") are **provisional and withdrawn** until the ceiling agent reports the counterfactual-vs-committed parity check as PASS and the pooled 24-episode result. They must not be repeated anywhere before that.
- **Ruling 2 written 14:40 UTC** (`V025-CONTROLLER-RULING-CEILING-PARITY-B-CHAIN-AND-CATFISH-COUNT-2026-09-11.md`): parity first; thresholds unchanged; B-chain B1 (difference reward) → B2 (sequential visibility) with a pass condition of ≥ 50 % of the nominal gap (owner to confirm the 50 %) and no automatic advance; C only by owner decision; operational catfish-count definition (three criteria, owner to confirm); no learner training until parity + pooled + nominal + rate-floor + compound are reported.
- Ceiling variants run in parallel (cap raised to 10 at 14:10 UTC; nominal / rate-floor / compound / free started alongside the base search).

## Oracle-first screen adopted (14:55 UTC; `V025-CONTROLLER-AMENDMENT-1-ORACLE-FIRST-SCREEN-2026-09-11.md`)

Standing rule from now on: no mechanism trains before its ideal version has been rolled out with the counterfactual evaluator and has beaten `A m=2dB` under declared rules. Table = information axis (simultaneous / sequential-visible / joint) × credit axis (own bits / equal share / difference reward / exact joint), **each cell at realised and nominal information**. Cells: A-real, A-nom (= LP-prev best, running), B-real, B-nom (= LP-seq best + the ceiling's nominal variant, running), corner (= ceiling search, running). Decision rules 1–5 declared (A-real ≤ rule + 3.3 % → drop difference reward untrained; B-real ≥ A-real + 3.3 % → sequential visibility; only corner → owner decides on C; the nominal cell of the chosen path must itself clear +4.5 % or the next screen is an observation redesign). Training then asks "does the learner catch its own oracle" (≥ 50 % of the nominal cell's gain; owner's number) with matched random controls. A-real/B-real queued on the H4/LP harness behind the LP report (~20–30 min per cell).

## Parallel track while waiting (2026-09-12 00:30 Taipei = 16:30 UTC; none of it trains — Ruling 2 §5 respected)

1. **B1-CREDIT** (opus, engineering lane): difference-reward credit + analytic lighting-price approximation for the ratio
   learner, in a new worktree `b1/difference-reward-20260912` from `102b2d4d`; fail-then-pass tests with named mutants;
   no-training diagnostic (argmax-change fraction under the new credit vs 0/240 under equal share); cost benchmark. Puts B1
   on the starting line the moment A-real passes; shelved if it fails.
2. **Save what the next screen needs**: the oracle-cell agent saves (observation, oracle action) pairs per cell; the ceiling
   agent reports whether each variant saved per-step joint actions (for replay). The representability screen (clone the
   teacher from the learner's own observation) then runs without re-running any oracle.
3. **Deep Research addendum** for the owner (`.scratch/external-package/validity-2026-09-11/PROMPT-CHATGPT-DEEPRESEARCH-ADDENDUM-PRIVILEGED-TEACHERS.md`):
   privileged-teacher distillation, the imitation gap, DQfD with a privileged teacher, centralised-expert → decentralised
   policies in wireless, difference rewards in resource allocation, the catfish literature, how many teachers.
4. Deferred to conserve opus quota: paper evidence tables (sonnet after its weekly reset 04:00 Taipei).

## Design note — how the catfish line survives (not a declaration; contingent on the ceiling and the oracle cells)

Three layers, fixed in this order: **(0) what the student can learn** — credit and observation (equal share cannot see the
lever; the difference reward can); **(1) what a catfish teaches** — its source (the pilot's rule sources carried nothing
beyond random data); **(2) how it is injected** — static replay (pilot), DQfD margin, faithful RIS competitive replay /
bounded ACRM, JSRL. Layer 2 was never what failed and can be kept whole. What changes is layers 0 and 1:
- The injection mechanisms stay: **DQfD-style margin** becomes the natural channel for distilling a **privileged teacher**
  (an oracle cell or the centralised search) into the per-user student; faithful RIS catfish stays as the lineage comparator.
  A DQfD margin toward a rule source has the rule as its oracle, so it cannot beat the rule (CFSCREEN: the `A m=2dB` clone
  loses 1.3 %); toward a teacher above the rule it has a real job, bounded by the representability screen.
- The pilot's three sources collapse under the measured-count definition (Ruling 2 §4): `A m=12dB`'s states lie inside
  `A m=2dB`'s (fails distinctness); `B1_NO_NEW_BEAM` is dominated on (EE, served, per-user rate). One rule source remains —
  the reference itself.
- New candidate catfish, each admitted only by the oracle-first screen, the representability screen and the three count
  criteria: LP(c, m) lighting-price cells above the rule; the simultaneous difference-reward oracle (A-real); the sequential
  oracle (B-real, privileged "sees earlier users"); the centralised search (privileged joint teacher); the rate-floor
  search (service-respecting teacher). The count is whatever survives — possibly more than three, possibly fewer.
- In scenario A none of these exists on this physics, and the fallback of Amendment 2 §4 applies.

## Scenario status and external documents (2026-09-12 ~01:15 Taipei = 17:15 UTC)

- Owner pasted `dr19.md` (Deep Research addendum on privileged teachers) and `gpt6.md` (fresh-context reading of repo and
  sat). Controller check: `.scratch/reviews/external-gpt/DR19-GPT6-CONTROLLER-CHECK-2026-09-12.md` — every gpt6 number
  verified against the artefacts; dr19 adopted on method, corrected on the catfish lineage (the mechanism family is
  peer-reviewed: CER/CuSP/Sukhbaatar/Hughes, erratum 26; only the name and the RIS thesis are not) and on teacher cost.
- **Parity PASS** (recorded by the ceiling agent, 580 steps exact) → search numbers citable as lower bounds; the 14:40 withdrawal
  note is lifted for the verified numbers.
- **Scenario A excluded** (+41.4 % constrained lower bound, 24/24; +23.9 % rate-floored, 6 ep). **B's nominal condition met by a
  deployable witness** (LP-prev(1,0): eval +6.66 %, cal +4.75 %, bits ≥ 0.95, served ≥ 0.998). B1 / B2 / C pending A-real/B-real.
- **Amendment 3 to Ruling 2** (`…-AMENDMENT-3-TEACHERS-LADDER-AND-SCENARIO-STATUS-2026-09-12.md`): teacher ladder T0 (LP rule,
  admitted by the oracle screen) / T_DR / T_SEQ / T_JOINT with costs; representability metric `R_repr` with one-hot and
  soft-advantage clones; causal ladder D0–D4 for when training is authorised; learner criterion proposed as `ρ ≥ 0.5 × R_repr`
  (owner to confirm); **B2 reclassified as an execution-contract change → owner decision**.
- Dispatched/queued: oracle agent saves per-user 28-action advantage vectors; ceiling agent re-runs rate-floor 0:6 with a
  joint-action dump (T_JOINT labels) after its fill cells; B1 agent's follow-on = T0 representability screen (local BC probe).
- Q9b (registry rows for H4, LP, ceiling, oracle): after the ceiling and oracle reports; sonnet after its weekly reset.

## Owner decisions 17:30 UTC (Amendment 4 to Ruling 2: `…-AMENDMENT-4-OWNER-GATES-B2-BRANCH-AND-CATFISH-COUNT-2026-09-12.md`)

- Learner gate `ρ ≥ 0.5 × R_repr` = **continue-eligibility for short-episode mechanism screening only**, conjunctive with
  2/3 seed-pair direction, service + rate floor, beating the matched null teacher, and a gain beyond seed noise; never a paper
  threshold (confirmation runs with more seeds / CI later).
- **B2 = pre-approved conditional branch**: only if B-real − A-real ≥ +3.3 pp after the rate-floor replay, service/rate floor
  kept, and the extra value representable from the B2 observation; entered as an explicit execution-contract change with B1
  kept as comparator. A-real(R1) eval verified: +5.93 % but p10 0.27× the rule (herding) → authorises nothing yet.
- Catfish count: (a) non-dominance, (b) distinctness incl. value-weighted disagreement / advantage separation from the 28-action
  vectors, (c) causal marginal by drop-one; the 25 % / 0.2 numbers are pre-screen diagnostics; 1–4 catfish all acceptable.
- **b0 worktree removed** 17:30 UTC; branch and archive tag kept.

## Critical path shortened (17:45 UTC; `…-AMENDMENT-5-CRITICAL-PATH-AND-EARLY-D0-T0-PROPOSAL-2026-09-12.md`)

Part I adopted (owner's eight instructions; no Amendment 4 gate relaxed): B-real(R1) independently aggregated and provisional
(+29.5 %, p10 1.14×; B − A +23.6 points unfloored); oracle CPU on the floored R1 cells, then floored R1 calibration (clone data
for B2 condition 3); one oracle pass stores everything later uses; T0 representability lane now (T0REPR); D0–D4 harness built by
the B1 agent without training; first stage = D0 + D1..D4 with T0 and a matched null each (9 arms × 3 seeds); D2 primary, D3
required comparator, D4 gating test, D1 lineage baseline; downstream list fixed. Part II (early branch-invariant D0/T0 runs)
**not adopted** — pros/cons and a conditional recommendation written for the owner.

## Development-first (18:12 UTC; Amendment 6: `…-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md`)

Owner direction (`gpt7.md`): E0 / E1 development runs alongside the unchanged formal S1 regime; development kernel frozen (ratio
learner; T0 = LP-prev(1,0) anchor teacher; D0, D2-T0 primary, D2-null, D3-T0 comparator); DEV / DEVVAL / DEV-NULL / CONFIRM seeds
declared and committed (`9a3aafa4`) before any development result; first E0 batch frozen (arms 1–4 equal_share, optional 5–6
lighting_price diagnostics; DEV triple k=0; 300 episodes; η fixed at η_0). Re-triage: LP-ORACLE shortened, T0REPR verdict-first,
B1 engineering-core commit now, CEILING2 stopped (complete), DEVHARNESS dispatched. Exact-DR learner arms still wait for Amendment 1
rule 1 on the rate-floored A-real.

## T0 representability — ADMITTED (18:10 UTC; `.scratch/t0-repr/T0-REPRESENTABILITY-2026-09-12.md` line 1)

Closed-loop `R_repr` of the declared 100-epoch clones (learner architecture, learner observation, 180 training-like episodes, held out
by episode; placebo bit-for-bit on both sets): **evaluation 0.930 (one-hot BC) / 0.976 (soft, τ = 3 chosen on VAL); calibration 0.952 /
1.052** — both clones pass on both sets (Amendment 3 §3). T0's action is a deterministic function of the learner's observation
(300,000 / 300,000 decisions), so its conditional entropy is 0. The 400-epoch sensitivity is being finished. Consequence: condition (a)'s
T0 part of Amendment 5 Part II is met; T0 is an admissible anchor teacher for E0 / S1.

## Floored oracle cells read (18:22 UTC, controller-computed, provisional): B2 indicated, not entered

`.scratch/h4-probe/BRANCH-NUMBERS-FLOOR-R1-EVAL.md`. Rate-floored R1 evaluation, 24 episodes, parity 0: **A-real-floor +6.10 %**
over `A m=2dB` but **p10 0.282 ×** the rule's (throughput-degenerate — the per-move floor cannot stop simultaneous herding, so its
gain does not count); **B-real-floor +25.35 %**, served 0.99887, bits ratio 1.321, **p10 1.632 ×** (not degenerate);
**B − A = +19.25 pp**. Declared rules: rule 2 (credit alone) does not hold; **rule 3 holds** (the learner needs current-step
lighting information → the B2 path); **rule 5 currently fails for B2** — every deployable sequential nominal cell is
throughput-degenerate (LP-seq(1,0) bits 0.712; LP-seq(2,0) served 0.988, p10 0.41 ×; the ceiling's nominal search bits −51.7 %),
so the declared next step is an **observation-redesign screen**, not training. Amendment 4 §2: condition 1 met, condition 2 only
for B-floor, condition 3 (T_SEQ representability on the augmented observation) pending the floored **calibration** cells (5/24,
running). **B2 is indicated but not entered** — it remains the owner's decision, B1 stays as comparator, no threshold moved, no
learner training authorised. The development lane (Amendment 6, T0 anchor teacher) is unaffected.

Also at 18:16 UTC: all four opus sub-agents were killed by an opus session limit (resume scheduled for 04:07 Taipei);
**B1's engineering-core commit `63b02dc0` exists**, so DEVHARNESS can start at step 1 on resume; the `sat` oracle shards and the
local B1 lighting-price lanes kept running.

## B1 engineering core committed; credit diagnostics and cost (18:38 UTC, agent-reported, its report pending)

`63b02dc030180b83889387b031bd1c7dff4754f5` on `b1/difference-reward-20260912`: `cf_credit.py`, the `credit_mode` wiring,
`tests/test_cf_credit.py` — **9 tests green, 13 named mutants red, lighting-price path tests green**; an engineering checkpoint,
not scientific validation. Harness placebo exact on both episode sets. Diagnostics on 2,000 decisions: the **one-step argmax
flips** under equal share in 3/2000 (0.15 %, reproducing the CF3 review's 0-of-240), under the **lighting price in 89.4 %**, under
the **exact difference reward in 43.3 %**; the difference credit agrees with the unilateral system best response in 1,982/2,000,
the 18 exceptions being decisions whose system best response is an outage alternative that the declared outage charge refuses.
**Cost of the exact difference credit: +17.0 s/episode rule-like, +43.7 s/episode under random exploration, ≈ 6.2 h per
1000-episode run locally (~11× CF3 A1)** — a planning constraint for any formal exact-DR arm. **Early lighting-price screen signal
(2 evaluation episodes, evaluator variant, provisional): +26.7 % EE at served 1.000 but bits ratio 0.865 and 41 lit beams vs 61 —
the bits-ratio gate (≥ 0.95) is the one at risk; the nominal-bits variant runs ~8 % below the rule.** If the screen fails, the
lighting-price credit cannot carry Amendment 5 Part II's early runs; under Amendment 6 §6 its E0 arms 5–6 remain permissible as
labelled development diagnostics only.

## T0 representability lane CLOSED (18:47 UTC, commit `a4c8ce12`)

Report `.scratch/t0-repr/T0-REPRESENTABILITY-2026-09-12.md`. Verdict unchanged (T0 admitted). Two results worth carrying:
- **Longer training raises open-loop accuracy but not closed-loop EE.** The 400-epoch clones improve held-out top-1 (0.8929 →
  0.9063 BC, 0.9448 → 0.9697 soft) yet their closed-loop `R_repr` is *lower* (evaluation 0.890 / 0.946; calibration 0.947 /
  0.984) than the declared 100-epoch clones (0.930 / 0.976; 0.952 / 1.052). This is why the screen's metric is closed-loop
  headroom recovery, not action accuracy — it must stay that way for the privileged teachers' screens (T_DR / T_SEQ).
- **T0's conditional entropy given the learner's observation is exactly 0**: its action is recomputed from the observation
  (`obs_snr/ln2 − 1·[obs_load == 0]`, masked argmax) on 300,000/300,000 decisions and on 24,000/24,000 in both closed-loop sets.
  Scale for comparison: marginal H(a_T0) = 3.3168 bits, uniform over the legal set 4.7090 bits, BC held-out cross-entropy
  0.4122 bits. So a non-privileged anchor teacher costs the student no information gap; any gap measured later for T_DR / T_SEQ
  is attributable to their privilege.

## Two lanes closed out, 20:15–20:20 UTC

**B1 lighting-price screen: FAIL** (`.scratch/b1-credit/B1-CREDIT-IMPLEMENTATION-2026-09-12.md`, first line; the mutant re-run's
verdict column and the commit follow). Realised-bits variant +24.6 % / +24.9 % at η = η₀ / 1.0e8 but bits ratio 0.867 / 0.920
against the ≥ 0.95 gate (6 evaluation episodes, 42.7–45.2 lit beams vs the rule's 61.8); observation-level variant **loses**
7.1–7.4 % on all 24 evaluation and 24 calibration episodes (bits 0.55, p10 0.38). Engineering core green (9 tests, 13 mutants
red, `equal_share` bit-identical to CF3). Under the **difference** credit the one-step argmax moves in 866/2000 decisions
(43.3 %) against 3/2000 (0.15 %) for equal share, at ≈ 6.2 h per 1000-episode run (≈ 11 × CF3 A1). **Consequences:**
Amendment 5 Part II has **no admissible credit** — the contingency cannot fire on lighting price, and exact-DR arms keep their
formal restriction; E0a is unaffected because it runs `equal_share`; the LP *rule* family (LP-prev(1,0)) is untouched — a rule
and a credit with the same name land on opposite sides of the gate, which is exactly why the owner required this screen.

**B1 lane CLOSED** 20:25 UTC: commits `63b02dc0` (engineering core) and `d75c18be` (diagnostics, screen scripts and
`docs/b1-credit/`). Four facts to carry beyond the FAIL verdict:
- **Physics of "without u", established by reading and by test**: removing a user changes only the shared beam's bandwidth
  denominator, that beam's power when u is its unique maximum-power user, and the extinction of the beam or satellite. Joules
  are independent of interference and fading, so the difference credit's energy term **equals the analytic lighting price
  exactly** (largest observed discrepancy 6.3e-12 J, and 0.0 J in the screen).
- **The outage free ride is real and quantified**: an unserved user's bits and joules are both exactly 0, so a pure difference
  reward scores an outage 0 while **52.2 % of served decisions score D < 0**. The declared charge (`E_out = E_max = 268.35 J =
  2.2248 s_E`, `B_out = min(0, the worst served alternative's B)`) makes outage never preferable for any `η ≥ 0`; in 60
  closed-loop episodes it was never chosen (served = 1.00000).
- **Credit influence on decisions** (same 2,000 decisions): equal share 3, lighting price 1,787, difference 866; the difference
  credit agrees with the unilateral system best response in 1,982/2,000, and every one of the 18 mismatches is a decision whose
  system best response is an outage.
- **Cost**: 15.0 ms per counterfactual evaluation, +1.70 s per step, +17.0 s per rule-like episode and +43.7 s under random
  exploration, ≈ 6.2 h per 1000-episode run. An incremental formulation, verified but not wired, would bring this to `O(U²)`
  arithmetic — the thing to build if an exact-DR formal arm is ever authorised.

**Oracle lane closed** (`.scratch/h4-probe/ORACLE-CELLS-2026-09-11.md`, `LP-PROBE-2026-09-11.md`). Its aggregation **matches the
controller's independent one field for field**; `BRANCH-NUMBERS-FLOOR-R1-EVAL.md` needs no correction. New facts: A-real-floor
has **32.2 % of served user-steps under the rate floor** even with the per-move floor, because 72–96 of 100 users move each
step — the floor moved its pooled EE by only +0.18 pp and its degeneracy is mechanistic, not a threshold artefact;
B-real-floor is monotone by construction (0 violations) and paid 4.17 pp for the floor (+29.52 % → +25.35 %); the **B2 teacher
calibration set is ready** (+22.551 %, 24/24, 0 violations). Verification: parity exactly 0 on all 1,200 committed steps, 122
replays reproduced, 72,000 decisions reconstructable from the saved advantage vectors. **HELD and recorded**: A-floor
calibration, both R2 cells (the R2 rule itself scores −3.98 % on this set) and the **reverse-order sensitivity** — so nothing yet
separates "sequential information helps" from "this 0..99 order helps"; the B2 lane was given a cheap clone-level
order-robustness check to close that gap.

## E0a LAUNCHED 20:29:10 UTC — first optimizer steps of the development line

`MCRL-Dev-v0.1` at dev commit `772481c4` (minimum E0 surface `f9042150` + two test-harness files; `cf_ratio.py`, `cf_credit.py`
and `modqn.py` untouched), sat `/home/sat/mcrl-v025-dev-e0-ws/tree`, root `runs-e0a`, DEV triple k = 0
(9,201,000 / 9,202,000 / 9,203,000), `--stop-after 100` on the frozen 300-episode configuration, full 24-episode DEVVAL at 100.

| arm | PID | config hash |
|---|---|---|
| D0 / equal_share | 3570617 | `5d4f54e019a4e44f` |
| D2-T0 / equal_share | 3570618 | `3dd5e6f1d14922da` |
| D2-null / equal_share, `default_rng((9_231_000, 0))` | 3570619 | `c19d2596c5a745a7` |

Preflight: `tests/test_cf_dev.py` **20 passed**, **22/22 named mutants red**; a real gap was caught on the way (the `d3_no_margin`
mutant stayed green because the fixture's best legal alternative sat outside the margin, so the margin term never bound — the
fixture now binds it). Process level on sat: stop at episode 2, resume, policy bit-identical, DEV-NULL generator state identical,
a second launch while live started nothing, the launcher fail-closed on a changed config. Review: agy fresh context, fixed
prompt, **0 INVALIDATES / 1 BIASES**, "may proceed (arms 1–3 unconditionally; arm 4 after tightening one unit-test assertion)" —
the BIASES item was the D3 fixture, fixed before the launch commit; a second pass on `772481c4` is running.

**Proof of life at episode 25** (not a result): TD losses (B, E, H) ≈ 2.3e-1 / 3.1e-2 / 9.4e-2 in all three arms; teacher loss
3.168 for D2-T0 and 3.269 for D2-null, exactly 0 for D0; greedy agreement with T0 0.277 (D0) / **0.457 (D2-T0)** / 0.281
(D2-null) — the injection channel moves the student toward the teacher and the matched null does not.

DEVVAL reference frame, rolled once on the 24 DEVVAL episodes: T0 = LP-prev(1,0) **117.66 M**, `A m=2dB` 111.58 M,
`MAX_NOMINAL_GAIN` 110.03 M, RANDOM 51.99 M bit/J; T0's stored labels reproduce at 100.00 %, the null at 3.76 % (chance).

Next: the DEVVAL readout at episode 100 decides E0b — whether to continue the three arms to 300, whether to add `D3-T0` (after
its test assertion is tightened), and any development-parameter change, each as a new version with its own config hash.

## E0a readout at episode 100 (20:52 UTC) — the teacher's *content* separates from its *loss term*

Second agy pass on the launch commit `772481c4`: **0 INVALIDATES, 0 BIASES**. All three arms `stopped-at` 100 episodes,
216–217 s wall, 10 updates per episode, replay full. DEVVAL (24 episodes, greedy, fresh env per episode; references on the same
set: T0 = LP-prev(1,0) 117.66 M, `A m=2dB` 111.58 M, `MAX_NOMINAL_GAIN` 110.03 M, RANDOM 51.99 M bit/J):

| arm | DEVVAL EE (M bit/J) | vs D0 | served | rate p10 | beams | agreement with T0 | T0 regret |
|---|---:|---:|---:|---:|---:|---:|---:|
| D0 | 103.06 | — | 0.99842 | 7.65e7 | 64.63 | 0.381 | 0.959 |
| **D2-T0** | **107.43** | **+4.24 %, 23/24 paired** | 0.99817 | **1.08e8** | 63.47 | **0.538** | **0.405** |
| D2-null | 100.96 | −2.04 % | 0.99708 | 7.12e7 | 63.67 | 0.376 | 1.021 |

**Reading (development, direction only, one seed, a third of the E0 ceiling — no statistical claim).** D0 learns (behaviour EE
5.49e7 → 1.02e8, served 0.944 → 0.995, `Q_E` loss down ~8×) but sits below both one-line rules. D2-T0 leads D0 on every axis
here and beats D2-null 24/24 paired, while **D2-null lands below D0** — identical loss shape, weight, temperature, mask and
gradient path with permuted scores. So in this mechanism the gain is the **teacher's information**, not the extra loss term.
That is the contrast with the CF3 pilot, where static pools made directed and random indistinguishable (+0.78 %): the change is
labels on student-visited states with a soft target, not pool replay. Carried caveat (inferred, not measured): at τ = 3 the
target is nearly uniform over ~26 legal actions, so only ~0.11 nats of the cross-entropy is learnable.

**E0b authorised (controller, 20:55 UTC)**: wave 1 = resume the three arms to 300 on unchanged hashes (intentional resume of
MCRL-Dev-v0.1), add `D3-T0` `9a1a67c4` fresh to 300 with DEVVAL at 100/200/300, and the **paired k = 1 replicate**
`50c9d4a0` / `67d3dc6e` / `28b99027` to 100 (promoted because every reading so far rests on one seed); wave 2 = the τ sweep on
D2-T0 (τ = 1 `cd424977`, τ = 0.3 `b2c124ae`), replicated at k = 1 only if a τ wins; **deferred**: the α sweep, and learning
rate / clipping / target cadence remain unproposed. ≤ 8 development processes while the B2 lane runs.

**E0b wave 1 launched 20:58 UTC**, seven processes verified alive at commit `772481c4`, code digest `ccbcb02d5b7c`, pinned TLE,
`nice -n 10`, MemoryMax 5G: the three k = 0 arms **resumed** from episode 100 in `runs-e0a` under the unchanged manifest and
hashes (same trajectory, DEVVAL at 200 and 300; PIDs 3577210/3577211/3577212); `D3-T0` `9a1a67c4` **fresh** to 300 in
`runs-e0b-d3` (PID 3577336, DEVVAL 100/200/300) after `DEV_MUTANT=d3_no_margin` was re-verified RED at the launch commit; the
**k = 1** replicate `50c9d4a0` / `67d3dc6e` / `28b99027` **fresh** to 100 in `runs-e0b-k1` (PIDs 3577470/3577471/3577472). The
replicate keeps the frozen 300-episode configuration stopped at 100 rather than a 100-episode configuration, so ε-decay and the
authorised hashes are unchanged. Expected: k = 1 ~21:10–21:15, k = 0 resumes ~21:20–21:35, D3-T0 ~21:30–21:45 UTC. Wave 2 (τ
sweep) queued, B4 deferred.

## B2 lane CLOSED 21:00 UTC — condition 3 FAILS, B2 is not entered (`.scratch/b2-representability/T-SEQ-REPRESENTABILITY-2026-09-12.md`)

`R_repr(T_SEQ)` = **0.150 (one-hot BC) / 0.129 (soft τ = 0.3)** on the 24 evaluation episodes and **0.092 / 0.051** on the 24
calibration episodes, against the 0.5 admission line; 0 of 10,000 bootstrap resamples reach 0.5 on any arm. Neither clone is
throughput-degenerate (served 0.9966–0.9977, bits ratio 0.951–0.979, p10 1.04–1.15 × the rule), so this is a **representability
shortfall, not a collapsed rate tail**. Placebos exact: `A m=2dB` bit-identical on both sets, the teacher's pooled EE re-derived
(134,129,417.19 evaluation / 137,497,201.09 calibration), 26 replays reproducing actions, observations and committed bits and
joules at max |Δ| = 0.

Four findings that decide more than the verdict:
1. **Changing the execution contract buys nothing.** The best T_SEQ clone reaches **+3.81 %** over `A m=2dB` — below the
   simultaneous, observation-only rule LP-prev(1,0) at **+6.66 %** under the *unchanged* contract, and below the T0 clones'
   +6.20 % / +6.50 % on the same episodes.
2. **The declared current-step context block is worth ≈ 0**: ablation moves `R_repr` by +0.040, −0.011, +0.009, −0.038 (mean
   ≈ 0.0001, both signs) and 0.008 bits per decision open-loop.
3. **It is not a missing-feature problem.** A non-deployable diagnostic clone given the teacher's *entire* joint context scores
   held-out top-1 0.3573, no better than with (0.3665) or without (0.3650) the context block. **The sequential oracle's advantage
   lives in the counterfactual evaluation itself, not in any feature a per-user observation could carry.**
4. **Physical form of the failure**: T_SEQ wins by lighting *more* beams (66.9 vs 63.3) for 32 % more bits; every clone lights
   *fewer* (58.8–60.9) for 2–4 % fewer bits, falling back to the LP/T0 lever. The controller's reverse-order check retains
   84 % / 92 % of the (small) value, so it is not an order artefact; the teacher itself was only measured forward.

**Consequences.** Amendment 1 rule 3 pointed at B2; Amendment 4 §2 condition 3 now fails, so **B2 is not entered and B1 keeps the
contract** — no threshold moved, the decision followed the pre-declared rule. The observation-redesign screen that rule 5
indicated is answered in the negative for the obvious candidate: adding the current-step lighting pattern is worth nothing. The
privileged teachers' value is, on this evidence, **unteachable to a per-user student** — the imitation gap the literature review
predicted, now measured; the same mechanism argument applies to T_DR, whose advantage is also counterfactual. The teacher that
does transfer is the non-privileged anchor T0 (`R_repr` 0.93–0.98), which is exactly the one the development line is using.
**Named cheapest test that could overturn this negative** (not run, the owner's call, ~35 min): ~17 further floored B-real
calibration cells plus a multi-seed closed-loop refit. Three things argue it would not change the reading: held-out top-1 is flat
from 12 training episodes, the torch-seed spread (0.109 / 0.063) exceeds the data increment, and the full-context diagnostic caps
fidelity regardless.

## Development freeze reached 23:0x UTC — provisional algorithm frozen (`.scratch/dev-training/E0-FREEZE-PROVISIONAL-ALGORITHM-2026-09-12.md`)

Every number below re-derived by the controller from the DEVVAL JSONs, keyed by `(run_root, mechanism, seed, depth, config hash)`.
All at the 100-episode depth, 24 DEVVAL episodes, paired per episode:

| seed | D0 | D3-T0 | D3-T0 vs D0 | D3-null | D3-null vs D0 | D3-T0 served / p10 / min rate |
|---|---:|---:|---|---:|---|---|
| k = 0 | 103.06 M | **112.44 M** | +9.11 %, 24/24 | 57.47 M | −44.24 %, 0/24 | 0.99862 / 1.19e8 / 6.6e6 |
| k = 1 | 99.30 M | **112.55 M** | +13.34 %, 24/24 | 60.55 M | −39.03 %, 0/24 | 0.99850 / 1.15e8 / 4.8e6 |
| k = 2 | 103.53 M | **113.08 M** | +9.23 %, 24/24 | 46.92 M | −54.68 %, 0/24 | 0.99813 / 1.25e8 / 6.8e6 |

D3-null's preflight was clean (22/22 tests green, every named D3-null mutant red individually, fresh-context review of the delta
only: 0 INVALIDATES / 0 BIASES) and it was committed (`05aadf1b`) before staging, as required. The promotion rule fixed in
advance fired: D3-T0 beats the paired D0 and the matched null in the same direction on both k = 0 and k = 1 with no QoS collapse,
so it was labelled **provisional primary injection mechanism**, the k = 2 trio ran, direction and QoS held, and the provisional
algorithm is **frozen**: **B1 execution contract + the current ratio learner + T0 + D3 large-margin injection (m = 0.15,
λ_E = 1.0)**, with **D2-T0 (τ = 0.3)** as the strongest soft comparator and D3-null as the matched null, code `05aadf1b`.
Against the frozen MODQN eq-(16) baseline on DEVVAL (94.41 M) D3-T0 is +19.8 / +19.2 / +19.8 % at k = 0/300, k = 1/100 and
k = 2/100 — **development reference only, not formal evidence**. Item A applied (comparator τ = 0.3, no superiority claimed,
D2 tuning closed) and item D applied (`dev_e0_aggregate.py`, commit `27f69edf`, keys every result by
`run_root + config_hash + seed_index + checkpoint_episode`, refuses to merge differing records, 23 results re-emitted).

**Two controller caveats to carry into S1, recorded now:**
1. **The D3 null is a hard null, and beating it is a low bar.** An unconditional large margin toward a uniform random legal
   action is actively destructive: served collapses to 0.923–0.929 and the minimum served-user rate falls to 0.58, 0.042 and
   8.8 bit/s. It rules out "the margin term alone helps", which is its job under evaluation-contract rule 2, but the informative
   contrasts are **D3-T0 vs D0 (+9 to +13 %)** and D3-T0 vs D2-T0 (+3 to +4.6 %). A referee may ask for a **plausible-but-
   uninformative** teacher as a second null (for instance a same-family rule at a different operating point, or hold-the-incumbent)
   — cheap to add at S1 and worth pre-empting.
2. **Hard and soft injection behave asymmetrically with a bad teacher.** The soft null (permuted scores) cost about 2 %, the hard
   null cost 39–55 %. So D3 amplifies whatever the teacher is: excellent when the teacher is good, destructive when it is not.
   That is a design fact for any later privileged or imperfect teacher, and an argument for the gated margin the literature
   review recommended if such a teacher is ever injected.

## E1 launched 23:08 UTC — nine runs, frozen backbone, fresh seeds (`.scratch/dev-training/E1-LAUNCH-2026-09-12.md`)

Code `05aadf1b` (the frozen provisional algorithm), digest `7440236979d6`, cwd `tree-v0.4`, all fresh starts, 300 episodes,
DEVVAL at 100/200/300, `nice -n 10`, MemoryMax 5G, nine processes with the Catfish-2 lane keeping its three.

| arm | k = 3 | k = 4 | k = 5 | root |
|---|---|---|---|---|
| D0 | `945927542022` (PID 3616542) | `673611ca6da3` (3616543) | `ddd5bab02457` (3616544) | `runs-e1-d0-d3` |
| **D3-T0** | `ccca3463753d` (3616545) | `ce689b57833f` (3616546) | `9bf13b57e608` (3616547) | `runs-e1-d0-d3` |
| D2-T0 τ = 0.3 | `87e8fce4b4d8` (3616588) | `9905fcc0a2f1` (3616589) | `bab4ac8d4656` (3616590) | `runs-e1-d2tau0p3` |

Seeds k = 3, 4, 5 verified unused before launch (only k = 0/1/2 appear in any earlier result). D3-null is not re-run; the length
stays 300 so ε decays over the frozen 67 episodes; the backbone was verified frozen in every payload. Only **ep 300** decides;
100 and 200 are divergence, bug and QoS tripwires. Structural note from the launch: `--tau` is part of every arm's config hash,
so D0 and D3-T0 run in one root at the frozen default (a value neither mechanism reads) and only the soft comparator carries
`--tau 0.3` in its own root — recording τ on arms that ignore it would have changed their hashes and misdescribed them.
Expected finish 23:25–23:45 UTC; the controller re-derives the ep-300 numbers from the JSONs before recording the verdict.

## Sequencing actually in force

1. Now, in parallel: Q1 (ceiling, sat), Q2-Fable (blind), Q2-agy (blind), background wait for `REPORT-DONE` → Q3a (report writer).
2. When both blind audits exist: controller reads the pilot report (Q3b), then phase 2 of Q2 (unblind both reviewers with the pilot report + ceiling), then Q9.
3. Q4–Q7 are decided by the owner on the phase-2 verdict; none is dispatched before that.

## What was deliberately not done

- No new arm, no training, no design change, no edit to any sealed document.
- The controller did not open `sat:ws/eval/`, `ws/report/`, `readings.jsonl` or `PROGRESS.md` lines 149–182.
- Q7 was not started "because it can run any time": it competes for the server with Q1 and only matters if Q5 runs.

---

# 2026-09-12 — E1 closed, Catfish-2 closed at zero, S1 frozen

## E1 (Amendment 10) — `D3-T0` PASSES

Full record and provenance in `.scratch/dev-training/E1-RESULT-2026-09-12.md` (`1dd29ab5`); freeze and the S1 proposal
in `.scratch/dev-training/E1-FREEZE-AND-S1-PROPOSAL-2026-09-12.md` (`5cab1fb1`). Read by the controller from the nine
ep-300 DEVVAL JSONs under `run_root + config_hash + seed_index + checkpoint_episode`, pinned TLE asserted, 27 cells,
9 distinct config hashes, zero collisions.

`D3-T0` vs paired `D0` on fresh DEV k = 3/4/5: **+7.88 / +10.46 / +9.91 %**, seed mean **+9.42 %**, direction 3/3.
`D2-T0 τ = 0.3`: +8.96 / +8.85 / +9.38 %, mean +9.06 %. QoS floors met with room — worst Δserved −0.054 pp (floor
−0.5), worst p10 ratio 1.144 × (floor 0.5 ×, so p10 *improved* 14–52 %), worst bits ratio 1.0428 (floor 0.95).
Paired per-episode **144/144 positive**, minimum +1.55 %.

**Neither Amendment 10 §4 reopen condition fired.** D2 wins only on k = 3 (+1.00 %) and loses on k = 4 (−1.45 %) and
k = 5 (−0.49 %) — not across the board, not consistent, not substantive.

Two things recorded prospectively, both before the owner ruled:
1. **The gain decays with depth but the decay decelerates** — 12.71 % → 9.72 % → 9.42 % at ep 100/200/300; the last
   100 episodes moved it only 0.3 pp, with both arms flattening ~9.5 pp apart. S1's depth was already fixed at 1000,
   so no depth can be chosen from this; a materially smaller gap at S1 is a legitimate outcome, not a bug.
2. **Closer imitation of T0 does not help more** — ep-300 `t0_agreement` is 0.36 (D0), 0.70–0.72 (D3-T0), 0.74–0.75
   (D2-T0). The soft arm tracks T0 more closely on all three seeds and scores slightly lower. T0 is a prior the
   learner improves on, not a target to converge to.

## Catfish-2 Stage 0 — zero survivors, and the controller's independent check

Agent report and artefacts at `99263da9`. **Controller re-derivation from `results/STAGE0-AGGREGATE-A11.json`
confirms every headline claim**: `C_Q_local` CR 0.5037 at disagreement 0.0024; `C_Q_global` 0.4798 / 0.0760;
`C_RC_local` 0.4229 / 0.2311; `A_m12dB` 0.4847 / 0.5286. Every arm with disagreement ≥ 0.25 has CR ≤ 0.485; the only
arm with CR ≥ 0.5 differs from T0 on 0.24 % of decisions; **all nine arms have negative Δ mean *and* negative Δ
median**. `LPend_c0` matches `MAX_NOMINAL_GAIN` and `LPend_chigh` matches `B1_NO_NEW_BEAM` in every column, so the
decomposition endpoints do reproduce their controls exactly, as claimed.

The T0 decomposition is **rejected**; T0 remains one source. Per Amendment 13 §6: `A m=12dB` is **not** promoted
despite its near miss, the CR threshold does **not** move, and no `D3-A12` canary runs. A successor lane must target
information T0 does not already use — not another reweighting of the same two observation blocks.

**Consequence for the narrative: there is one catfish, and it now has fresh-seed stability evidence.** The
multi-catfish line is closed for now, and that is stated plainly rather than packaged as a positive.

## S1 is frozen (Amendment 13, owner)

Six trained arms — `D0`, `D3-T0`, `D3-null`, `D3-XEP`, `D2-T0 τ = 0.3`, `MODQN eq.(16) @1000` — plus the frozen
`e6b063ef…` @9000 rolled once as the separately labelled published reference. Baseline **Option A**: the 9000-episode
checkpoint is not a conjunctive veto, and beating only the 1000-episode baseline is claimed as *same-budget
superiority*. Fresh formal namespaces `S1-TRAIN 9_251_000/9_252_000/9_253_000 + k` and `S1-NULL (9_261_000, k)`;
DEV streams may not be reused. `T0-XEP` keeps its one sealed DEV-NULL reference trajectory.

Conditional launch authority is granted against eight preflight conditions (Amendment 13 §7). **The controller runs
the fresh-context review and presses the button; S1-PREP does not launch.** The complete 18-run matrix launches
together — the formal set is never partially opened.
