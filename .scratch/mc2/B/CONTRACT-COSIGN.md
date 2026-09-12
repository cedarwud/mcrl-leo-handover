STATUS: COSIGNED r2
STATUS: COSIGNED r1

# MC2 contract: lane B (method owner) co-sign (r2 note on top, then r1, then r0 detail)

## r2 note

- Read once, ~05:40Z: sha256 `37b3404ebc337dde1b5e548f86fdfd2bd290c7e4e018271e1220bd53cb397ca8`.
- Committed as `b6573b58`; `git show b6573b58:<file> | sha256sum` is the same blob, so this co-sign covers that commit.

**r2 is faithful.**
- It adopts R1-1 as §7 (ii), plus FULL vs D3-T0 in ep-300 survival and the min over the three ratios in the selection score.
- It adopts R1-2, R1-3, R1-4, F-1, F-2 and F-3.
- The N-items (N-a1 to N-a4, B-only dose, B-null not dose-matched, fallback multiplicity) are carried as disclosures.
- My §4 corrections are in, including the cap disclosure and the absent Phase-1, dual-agent and dual-memory rows.
- The citations are corrected: DQfD as loss form, DAgger, the Q-filter, and MAMBA/MAPS as concept only, with the correct author list.
- New test (11) is added.
- No formula, rule, seed or cell changed, so this is a readings and disclosure revision and needs no new launch gate.

**One non-blocking nit.** §7 "Reported beside" says B-null's approval rate "is expected to be far lower". That direction is unmeasured. Suggested wording: "expected to differ (direction measured by the P0 controller probe)".

`b_readout.py` implements the r2 §7 rules exactly: clauses (i)–(vi), the selection score, the primary, and the ep-300 gate with the F-2 fallback rule.

## r1 review

- Reviewed 2026-09-12 ~05:15Z: contract working tree sha256 `62e8c209a780c90cb56e0a853e18fe61905a31ed89e648413554d976a5b7b725`; r0 was `67e175bd`.
- Committed as `9d3625c4`. The blob sha256 is identical (`62e8c209…b7b725`, checked with `git show 9d3625c4:<file> | sha256sum`), so this co-sign covers commit `9d3625c4`.

**Verdict.** Nothing in r1 has to change before the first counted run. Lane A may launch the 16-run ep-100 matrix once its tests pass.
- r1 closes two r0 items: V2-1 (v2's drop-ones are now declared) and F-2 (the fallback order is declared).
- **One item changes a decision: R1-1.** It must be closed in the §7 text before the first ep-100 file is read. It needs no new cell and no code.

### Checked, holds

**Shared B-only equivalence.**
- v1 `{B}`: incumbent `x_u`; target `a^B` iff κ(a^B) ≻ κ(x_u) strictly, otherwise no target.
- v2 `{x_u, a^B}` with ties to `x_u`: the winner is `a^B` iff κ(a^B) ≻ κ(x_u) strictly.
- Common to both: no call and no margin when `a^B = x_u`; B absent at T−1; `w = 1[target]`; full-batch mean; no null stream; the judge has no side effects, so the number of evaluations cannot move the trajectory.
- So every row gets the same label and the trajectory is identical.
- Requirements:
  - the shared cell's config payload must carry a rule-independent identity (no v1/v2 rule id in it);
  - the promised test must compare at the level of parameter sha256 after a few episodes, not labels only.

**v2 loss and causality.**
- The winner is a sequence of strict comparisons in the declared order: w = x_u; if κ(a^A) ≻ κ(w) then w = a^A; if κ(a^B) ≻ κ(w) then w = a^B. This equals "max κ, ties x_u > A > B".
- A target exists only when the winner ≠ `x_u`. Otherwise w = 0 with normaliser |batch|, so the dose is not refilled.
- The stored transition is `x_u` with its real reward. Judge output is only a label. CRN and call placement are the same as v1.
- Disclose one design fact: v2 drops the T0 margin on every row where the learner already plays T0's action (`x_u = a^A` → no margin). `A-only-v2` is therefore a judge-gated T0 (a Q-filter on T0 with the simulator as critic), not `D3-T0`.

### Must close before the first ep-100 read (text only; does not block launch)

**R1-1: v2 is never compared against D3-T0 (changes a decision).**
- v2 qualifies against `A-only-v2` and is scored for selection against it, never against `D3-T0`. Yet r1 §3 says "`D3-T0` stays the strong-T0 baseline for v2".
- `A-only-v2` drops the anchor on agreement rows, so it can be materially weaker than `D3-T0`. Then:
  - FULL-v2/A-only-v2 − 1 can be large while FULL-v2 < `D3-T0`;
  - v2 can qualify, and win the selection, because its min-margin is measured against a weaker baseline;
  - v2 can then pass ep-300 survival.
- The result would be a two-catfish "success" that scores below the existing single catfish.
- Smallest fix:
  - add "seed-mean FULL-v2 vs `D3-T0` ≥ +0.5 %" to v2's ep-100 qualification;
  - add "FULL-v2 vs `D3-T0` seed-mean ≥ +1.0 % with ≥ 2/3 seeds > 0" to v2's ep-300 survival;
  - score both versions as the seed-mean over k of min(FULL/own-A-only − 1, FULL/`D3-T0` − 1, FULL/B-only − 1). For v1 this equals the r1 expression, because v1's A-only is `D3-T0`.
- `b_readout.py` prints the r1-as-written verdict and the R1-1 verdict side by side.

**R1-2: define "seed-mean of min(...)".** State it as the mean over k of the per-seed min. That is the literal reading; the min of the seed-means can differ.

**R1-3: define v2 "B wins ≥ 1 % of decision rows".**
- Count rows whose winner is `a^B` with `a^B ≠ a^A`. When `a^A = a^B ≠ x_u` wins, the tie order makes it an A win.
- Use all t, pool over training episodes 1..100, and evaluate per seed (same denominator as F-1).
- Log the counts.

**R1-4: align §6 with §7.** §6 still reserves k = 15–17 "only if v1's confirmation seeds were consumed and v2 needs its own". r1 §7 now uses them for the concurrent non-primary.

**Still open from r0:** F-1 (override-rate definition) and F-3 (floor quantities), below.

### Non-blocking

- **The fallback gives two shots at the DEV gate.** They are pre-declared, fixed-order and on disjoint seeds, which is acceptable for a DEV screen.
  - Disclose in any report that two versions were confirmed and which one survived.
  - Hygiene: nobody, including lane B's tooling, reads the non-primary's k = 15–17 files until the primary's ep-300 verdict is written.
- **Selection on 2 seeds carries winner's-curse bias.** Confirmation on fresh k = 12–14 is the correction already in place.
- **Margin dose depends on the learner in every v2 cell.** That holds for FULL-v2, A-only-v2 and B-null-v2, not only B-only. Report per-episode doses for all of them.

### Answer to the controller's r2 list and the agy r1 review

I read `.scratch/mc2/agy/AGY-CONTRACT-REVIEW-r1.md` itself, not the summary. **None of the points below is INVALIDATES in my judgement.** Each is one line, with my r0/r1 item in brackets.

1. **B-only comparator/dose asymmetry: agree, non-blocking** [N-a4, N-b3]. FULL − B-only bundles A's margin, B's comparand change (`a^A` → `x_u`) and the dose. No content-clean alternative exists.
2. **B-null not dose-matched: agree, non-blocking** [(c)6].
   - It identifies whether T_NEXT's proposal beats a uniform proposal under the same judge, gate, anchor and abstention.
   - It does not identify foresight, the judge's own value, the dose-matched effect, or whether the privileged information is necessary.
   - Correction to agy 5.3: the direction of the override-rate gap ("random rarely beats T0") is unmeasured. r2 should say "differs, direction unmeasured; both rates reported".
3. **One-step judge vs T_NEXT's t+1 information; no "learned foresight" claim: agree, non-blocking** [N-a1]. Read the declared P0 pre-training diagnostic (override rate at T0's background) before the ep-100 files, so that a structural ≈ 0 is not later reported as "B inert".
4. **Judge labels depend on unobservables: agree, non-blocking** [N-a2].
   - Refinement: joules and served are fading-free (angle recurrence, feasibility), so only ΔB carries the fading noise.
   - The hinge resolves conflicting labels to the per-observation majority. This is label noise, not k = 8-type dilution.
5. **Multiplicity of the fixed-order fallback: agree, non-blocking for a DEV screen** [r1 non-blocking].
   - Either option is acceptable if declared before any ep-300 result exists: keep two attempts and disclose them, or take agy's stricter "fallback exploratory only".
   - Hygiene either way: nobody reads k = 15–17 before the primary's verdict is written.
6. **§4 wording: agree** [(d)].
   - Add two points: "the main learner is the only thing updated" describes MC2, not a retained CDRL property; and the cap disclosure (`J_E = 0` iff the target is the argmax, for any m ≥ 0).
7. **Cite Nair 2018 (Q-filter) and Ross 2011 (DAgger): agree** [(e), `LITERATURE-DELTA.md`].
   - Also correct the Cheng/Liu sentence. Their methods use learned oracle values as a policy-gradient baseline and choose which oracle to roll out; they do not select supervised targets.
   - Cheng is not an author of 2306.10259.

**agy #1 (v2 code absent), procedural.** I agree with the controller's ruling and would tighten the trigger: v2's code and hash must be committed before any ep-100 DEVVAL file of **any** selection cell exists, D0/D3-T0 included. D3-T0's level is exactly the information that could steer v2's design.

**Not documentation-only.**
- R1-1 changes the §7 decision rule: v2's qualification and survival must include FULL-v2 vs D3-T0, and the selection score takes the min including D3-T0.
- R1-2 (per-seed min, then seed-mean), R1-3 (B-win definition), F-1 (override-rate denominator and window) and F-3 (floor quantities) are reading definitions.
- None of these touches code or cells, so the r1 co-sign stays valid for launch. They must be in r2, or explicitly ruled out with a reason, before the first ep-100 file is read. `b_readout.py` computes both the r1-as-written verdict and the R1-1 verdict until then.

## r0 review (kept; V2-1 and F-2 below are closed by r1)

- Contract: `.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md` (commit `67e175bd`).
- Code read at `6136c514`/`67e175bd`: `cf_dev.py`, `cf_teacher.py`, `cf_tnext.py` (sha256 `86f0d6ee…77df91e1f`, as §5 says), `cf_multi_sources.py`, `cf_credit.py`, `cf_ratio.py`, `env/step.py` (`evaluate_actions`, `_evaluate_selected_actions`, `_resolve_physics`, `_rewards`, `_observe`, `_draw_fading`), `env/service.py::resolve_service`, `scripts/dev_e0_common.py`, `scripts/run_dev_e0.py`.
- Sources checked for §4: `07-true-catfish-formulas.md`, `00-README-START-HERE.md`, `CATFISH-MECHANISM-FACTS-2026-09-11.md`, `DQFD-FAMILY-GROUNDING-2026-09-11.md`. Three papers were fetched: arXiv 2007.00795, 2306.10259 and 1709.10089 (see `LITERATURE-DELTA.md`).

**Verdict.** No finding requires a change before the first counted v1 run (ep 100, k = 10, 11). Lane A may launch once its own §5 tests 1–10 pass. The remaining items fall into three groups:

- **F-1 to F-3** must be closed in the contract text before the first ep-100 DEVVAL file is read. They do not block the launch.
- **V2-1** blocks any `MC2-ARB-v2` launch. It does not block v1.
- **N-items** are corrections to wording or disclosure. None of them changes the run.

## INVALIDATES

None.

## Close before the first ep-100 file is read (does not block the launch)

**F-1: the §7 "override rate ≥ 1 % of decision rows" check has three open choices.** The numerator, the denominator and the window are not fixed, and the choice could flip a borderline continuation.
- Smallest fix: declare
  - numerator = FULL user-steps tagged B;
  - denominator = user-steps with at least one legal action, over all t, including T−1 where B abstains;
  - window = pooled over training episodes 1..100;
  - evaluated per seed, with each seed required to reach 1 %.
- Lane A must log both counts per episode.

**F-2: what follows a v1 failure at ep 300 is not written down.** §6 reserves k = 15–17 "if v1's confirmation seeds were consumed and v2 needs its own". That implies v2 may run after a v1 DEV-survival failure. §7 only says "If both versions fail …".
- Smallest fix: one sentence stating either "a v1 failure at ep 300 opens v2 (selection on k = 10, 11 with D0 and A-only reused; confirmation on k = 15–17)" or "a v1 failure at ep 300 goes to the owner; v2 is not run".

**F-3: the floor quantities should be named exactly.**
- served drop = `D0.served − FULL.served` (a fraction of user-steps) ≤ 0.005.
- p10 = `per_served_user_rate_p10_bps` of the DEVVAL file. It is a percentile pooled over all 24 episodes. The file does not store per-episode rates, so it cannot be recomputed and is read as stored.
- bits = pooled `bits`.
- "positive" means strictly > 0.
- All three floors must hold per seed.

## Blocks v2 launch only

**V2-1: v2 has no correct drop-one of B.**
- v2 releases the anchor: candidates `{x_u, a^A, a^B}`, with margin only when the winner ≠ `x_u`.
- Dropping B from v2 therefore gives `{x_u, a^A}`, a judge-gated T0 margin. That is not `D3-T0`.
- §7 reuses A-only (= `D3-T0`) for v2. So "FULL_v2 vs A-only" would drop B and also turn A from gated into unconditional.
- v2's B-only `{x_u, a^B}`, with ties to `x_u` and abstention at T−1, is identical to v1's B-only and can be reused if the identity is identical.
- Smallest fix, before v2 runs: declare the v2 drop-one of B as the gated `{x_u, a^A}` cell, and declare the v2 B-null (presumably `{x_u, a^A, a^R}`). Alternatively, state that FULL_v2 vs `D3-T0` is "vs the unconditional anchor" and is not a drop-one.

## Non-blocking findings

### (a) Identity

**N-a1: the judge credits only step t, but B's declared specialty pays off at t+1.**
- `T_NEXT` ranks by "the same `(norad, cell)` is visible at t+1" and then by the nominal t+1 gain (`cf_tnext.py:255-269`).
- κ scores step t only (§2).
- A foresight benefit that shows up only at t+1 cannot pass the gate. The overrides that reach the learner are T_NEXT proposals that are also one-step κ-better than the incumbent.
- So v1 tests "one-step-judge-filtered T_NEXT". It does not test foresight as such, and v2 has the same judge. A double failure would be ambiguous between "B carries no value" and "a one-step judge cannot see B's value".
- Fix, text only: amend the §1 "specialty" and "challenge" rows accordingly.
- Also recommended, since it is already declared: read the §7 P0 pre-training diagnostic (the judge override rate at T0's joint background) before the ep-100 files. If it is ≈ 0, the ≥ 1 % check fails for structural reasons, and the report should say so rather than "B inert".

**N-a2: the judge is a third, privileged information channel.**
- In the training env there is no keyed fading field, so fading is drawn from `env_rng`.
- The observation's SINR uses an observation-time fading draw (`event="observation"`, `step.py:1226-1231`), `p0` at every candidate, and the previous step's interference.
- The judge's κ uses the fresh physics-time draw of step t (`event="physics"`, `step.py:899-904`), the current interference from `x_{-u}`, and the exact system power.
- None of the learner, T0 or T_NEXT sees these.
- Energy and served status do not depend on fading: link power follows the angle recurrence (`step.py:771-820`), and served = chosen and feasible (`service.py:241-254`). ΔB does depend on fading.
- The override decision is therefore partly a function of noise the learner cannot observe. The margin hinge resolves conflicting targets on the same observation toward the per-observation majority (derivation: for d = S_A − S_B inside ±m, E[L] = m + d(2p−1)). So this is label noise, not dilution.
- Consequences:
  - The realised override rate overstates the learnable B content.
  - "FULL vs A-only" measures T_NEXT and the judge's information together.
  - Only FULL vs B-null isolates T_NEXT's proposals.
- Say this in §1.

**N-a3: T_NEXT is not free of T0.** T0's score is the third key of T_NEXT's lexicographic order (`cf_tnext.py:264-269`), so it decides exact ties on `(persists, nominal_gain)`. Those ties are rare except among unusable slots, which have gain 0. The final-step fallback is literally T0's action (`cf_tnext.py:319-331`), and §1's abstention removes it correctly. The claim "no T0 content reaches B-only" should read "except through T_NEXT's third tie-break key".

**N-a4: the drop-one is not symmetric.**
- Removing B gives `D3-T0`, a clean drop-one.
- Removing A also changes B's comparand from `a^A` to `x_u`, where `x_u` is ε-greedy.
- So FULL − B-only = A's margin, plus A's role as B's comparand, plus the dose difference (B-only dose < 1, not refilled).
- There is no content-clean alternative: gating B against `a^A` without A's margin would leak A's action into B-only. The contract's choice is right, but §1 should state what the comparison bundles together.
- The "not an RL agent" disclosure is correct: T0 and T_NEXT are scripted rules, and nothing learns except the main network.

### (b) Loss conflict

**N-b1: one target per row, confirmed by construction.** The target is one of `a^A`, `a^B`, `a^R` or NONE, and the learner's score never chooses between them. B cannot dilute A in the k = 8 sense. B can displace A on override rows toward an action that is κ-better at the behaviour background, with realised fading and at a fixed price. That is not guaranteed to be pooled-EE-better, and §4's last sentence already says so.

**N-b2: A-only is arm 4 itself.** A-only has the same mechanism, code path and payload. At k = 10, 11 its payload differs from the k = 8 run only in `seed_index` and the seeds, so A-only is `D3-T0` by identity and not by test. The bit-identity that needs proving is that the new arm with B disabled, or with the gate forced shut, equals arm 4. That is §5 test 2, and it must run the judge and the T_NEXT context while shut so that it proves the judge has no side effects.

**N-b3: B-only is coherent as the drop-one of A.** Its incumbent is the executed `x_u`, rows without an override carry zero margin, and the normaliser stays |batch| (dose < 1, not refilled). It is effectively a Q-filter with the simulator as critic (see `LITERATURE-DELTA.md`).
- Its override dose is front-loaded: at ε ≈ 1 the comparand is a random action.
- Report B-only's per-episode dose beside the result, so that a B-only deficit is not read as "B has no content".

### (c) Data causality: verified

1. **Common random numbers are exact for any candidate vector.**
   - `_evaluate_selected_actions` deep-copies the generator (`step.py:700`).
   - The physics fading draw runs over all candidate-window satellites, `_satellite_positions(decision)`, and so does not depend on the action vector (`step.py:891-904`).
   - The only state written, `self._segments` (`step.py:855-862`), is snapshotted and restored in `finally` (`step.py:701-705`).
   - Handovers are classified with `commit=False` (`step.py:706-708`, `1084-1088`).
   - `frozen_driver_positions` restores the bound methods on exit (`cf_credit.py:162-168`).
   - Per-candidate bits, joules and served are therefore physical. This is the same evaluator whose base vector B1 asserts equal to the committed step on every step (`cf_credit.py:359-363`).
2. **No reward, next state or action is misattributed.** The stored transition is the executed `x_u` with its real reward and its real `s'`. Judge output enters only the label, never a reward or a TD target.
3. **The served-first key is sound.**
   - Service has no beam cap: served = not no-op and link-feasible (`service.py:221-254`). Another user's feasibility depends only on that user's own link.
   - Hence Δn_served ∈ {−1, 0, +1} and reflects u's own service. Served-first means "never prefer u in outage over u served".
   - Without it, an outage (0 bits and 0 joules for u, `service.py:241-246`) would beat any served candidate whose marginal B − η₀E < 0. That is the free ride, and the key closes it.
   - η₀ equals `ETA0_EXPECTED` = 110 507 234.834 444 57 bit/J (`dev_e0_common.py:110`).
4. **The judge and the null cannot perturb the real env or RNG, subject to the implementation.** Lane A must:
   - pass `self._env_rng`, never `_train_rng`;
   - call the judge after `select_actions` and before `env.step`;
   - draw the null from a fresh `default_rng((9_243_000, k))`, unconditioned on judge outcomes, with exactly one draw per user with a legal action at t < T−1;
   - never build a `TeacherContext` for B-null.

   These are checked in `CODE-READ.md`.
5. **B's final-step abstention is the right mechanism.** At t = T−1 T_NEXT returns T0's action, so without abstention B-only would inject T0 wherever the judge prefers T0 over `x_u`. In FULL, abstention and the fallback give the same result (`a^B = a^A`, so no call). R also abstains, so B-null is matched.
6. **FULL vs B-null.** B-null has the same anchor, judge, gate, key and abstention, with a uniform legal proposal from its own stream, so it is a fair content null.
   - It identifies whether T_NEXT's specific proposals, filtered by this judge and on top of the anchor, beat content-free proposals filtered the same way. Random proposals plus the judge amount to a stochastic one-step best response to `x_{-u}`.
   - It does not identify:
     - that foresight is the active ingredient, rather than any informed non-T0 proposal;
     - the value of the judge itself (there is no ungated arm);
     - a dose-matched effect: override rates will differ, and B-null calls the judge on about 27/28 of rows against about 60 % for FULL;
     - whether the judge's privileged step-t information (N-a2) is necessary.
   - Report both override rates beside the ratio.
7. **Seeds.**
   - `9_243_000` is not yet in `DEV_NULL_KEY_BASES` (`cf_dev.py:94`), and `MAX_DEV_SEED_INDEX` = 9 (`cf_dev.py:99`). Both change as §6 says.
   - `dev_triple(k)` for k ≤ 19 stays inside the DEV ranges and does not touch P0's `9_202_500+i` / `9_203_500+i`.
   - The derived seeds (train + 70 001 / 80 000 + k / 90 211) stay inside their declared ranges for k ≤ 19.
   - sat has no run directory `*-k1[0-9]` under `/home/sat/mcrl-v025-*/` and no RUN-MANIFEST with `seed_index` 10–19 (checked 2026-09-12).

### (d) CDRL mapping (§4): claims to correct before any write-up

- **Row "competition (ACRM)": "kept" overstates.**
  - ACRM's comparand is the **main agent's** result on the same task, used as a reward term for a **learning** catfish (`07:103-118`).
  - In v1 FULL the comparand is the **anchor A**. Only B-only (and v2) compares against the learner's executed ε-greedy action, which is not its greedy action.
  - Correct "kept" to: "a same-state, same-background comparison decides whether B's proposal is used".
  - Add to "changed": "FULL compares B to A, not to the main learner; the lead is a gate; there is no reward term and no catfish learner".
- **Row "M1": "judge-approved B proposals become intervention samples" is inaccurate.** B's action is never executed or stored as an experience. What passes the filter is a label on the learner's own transition. M1 routes **experiences** by EE into a second memory (`07:78-83`). Retained: only "a value filter decides which specialist output enters training" (relative, SIL-like, not absolute).
- **Row "M3": "the main learner is the only thing updated" describes MC2, not CDRL.** CDRL also trains the catfish agent (`07:134-151`). Retained: only the direction, "the intervention acts on the main learner's update". State plainly that M3's conduit is not retained: there are no catfish-collected experiences, no 70/30 mix and no random period. A label is applied to every sampled row, at dose 1.0 in FULL.
- **Missing rows to add, each marked absent:**
  - Phase-1 solver-seeded catfish replay (`07:32-53`);
  - the dual-agent rollout / learning catfish;
  - two replay memories.
- **Cap disclosure (explainer binding rule `00:150-160`, `07:334`).** The D3 term is zero if and only if the target is the argmax (for any m ≥ 0), so the margin pulls the greedy policy toward the per-row target and never past it. Anything beyond the specialists can come only from TD. Say so. Also, `specialist` is used in all prose (code identifiers may stay "teacher").

### (e) Literature (§4, last paragraph): corrections, detail in `LITERATURE-DELTA.md`

- **DQfD.** The loss form is Hester et al.'s. DQfD applies `J_E` only to demonstration transitions (λ2 = 0 on self-generated data). MC2, like the E0/E1 `D3-T0` channel, applies it to the learner's own replay rows, with the specialist queried on the learner's state. That is DAgger-style on-state expert querying: cite Ross, Gordon & Bagnell (AISTATS 2011) as well.
- **Cheng et al. 2020 and Liu et al. 2023.** Neither selects a supervised target by comparing oracle values.
  - MAMBA uses f^max(s) = max_k V̂^k(s), with oracle value functions learned from oracle roll-outs, as the baseline of a GAE-style policy-gradient advantage.
  - MAPS adds a per-state UCB or ensemble rule to choose which oracle to **roll out**.
  - What MC2 shares with them is only the idea "per state, defer to the better oracle".
  - Correct "per-state selection among several oracles by comparing their value / advantage" to that. Note also that the author list for 2306.10259 is Liu, Yoneda, Wang, Walter, Chen. Cheng is not an author.
- **Nair et al. 2018 (Q-filter)** is the closer precedent for the gate and should be cited. It is a per-sample indicator that applies the imitation term only where Q(s, a_demo) > Q(s, π(s)). MC2 replaces the learner's critic with the simulator's one-step counterfactual under CRN, and in FULL it compares against another specialist's action rather than the learner's.
- **"What MC2 adds"** survives, scoped to "none of these three papers compares two specialists' actions under an evaluator to pick one supervised target". It is not a literature-wide novelty claim.

### (f) Readings (§7)

- **Estimand.** `EE_X,k / EE_Y,k − 1` on pooled Σbits/Σjoules over DEVVAL `9_211_000+i` / `9_212_000+i`, i < 24. Seed-mean = arithmetic mean over k of the per-seed ratios. This is unambiguous and computable from the raw files. The independent readout tool (`b_readout.py`) computes it without lane A's aggregator.
- **Forking paths.** Remaining ones are F-1 to F-3 and V2-1 above. "One short decision" is the controller's and is not a reading.
- **Reported beside the ep-300 gate.**
  - Per-source margin-loss share and sampled rows per tag need per-update tag counts in the episode log. Lane A should log them.
  - DEVVAL greedy agreement with `a^B` needs T_NEXT on the DEVVAL states. `b_output_change.py` does this from the checkpoint.

## Implementation points for lane A (checked in `CODE-READ.md`)

1. The judge is called between `select_actions` and `env.step`, with `self._env_rng`, inside `frozen_driver_positions`, and only on the candidate vectors `(c, x_{-u})` / `(inc, x_{-u})`. There is no call when `c == inc`.
2. Loss: `w_row ∈ {0, 1}`, with `Σ_rows w·hinge / |batch|`. NONE rows are never passed to `d3_margin_loss` with a fake target. FULL with the gate shut must reproduce `d3_margin_loss(...).mean()` bit for bit.
3. T_NEXT is never called, or its output is discarded before the gate, at t = T−1 in B-only and FULL. The null never builds a context.
4. The null draws from its own fresh generator `(9_243_000, k)`, which is saved and restored on resume. It is not shared with `(9_241_000, k)`.
5. Hash payload: mechanism id, source set, T_NEXT identity, judge id with η₀ and key order, null id with key. Arms 1–9 payloads are byte-identical to base.
6. Per-episode logs: counts by tag, override count, decision rows, judge evaluations, judge wall, and κ-lead summary.
