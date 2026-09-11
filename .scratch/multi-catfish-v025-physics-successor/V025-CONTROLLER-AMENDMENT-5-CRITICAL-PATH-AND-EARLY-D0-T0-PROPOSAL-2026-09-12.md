# Amendment 5 to Ruling 2 — a shorter critical path without relaxing any Amendment 4 gate (Part I, adopted); early branch-invariant D0/T0 runs (Part II, proposal only)

Date: 2026-09-11 ~17:45 UTC (2026-09-12 ~01:45 Taipei). Part I records the owner's eight instructions and how they were
executed; it changes sequencing and data capture only — **no scientific threshold of Ruling 2 or Amendments 1–4 is changed**.
Part II evaluates a proposal the owner asked to have assessed before any decision; it is **not in force**.

## Part I — adopted

**I.1 B-real(R1) evaluation is complete and independently aggregated — provisional.** Controller recomputation from the raw
per-episode JSONs equals the oracle agent's figures to the printed digit: B-real(R1) +29.52 % over `A m=2dB` (paired +29.95 ±
1.03 %, 24/24), served 0.99913, p10 1.14 × the rule's, bits ratio 1.32, parity 0; A-real(R1) +5.93 %, p10 0.27 ×; B − A =
+23.6 points unfloored (`.scratch/h4-probe/CONTROLLER-INDEPENDENT-AGGREGATE-2026-09-12.md`). Consequence: **B2 is a
conditional branch to be prepared in parallel now**; it is not declared passed before the rate-floored cells and the
representability condition (Amendment 4 §2).

**I.2 Oracle CPU goes to the critical path.** Already executed by the oracle agent at 17:20:40 UTC (v1 shards stopped by exact
PID after cmdline + cwd checks; v4 shards launched 17:23 with the rate-floored A-real / B-real R1 evaluation cells first). New
order after those: **B-real-floor R1 calibration, then A-real-floor R1 calibration** (training data for the T_SEQ / T_DR
representability clones, which B2 condition 3 needs), then R2, reverse order, unfloored calibration tie-ins. The ceiling agent is
capped at 4 processes; its remaining items are downstream.

**I.3 One expensive oracle pass feeds every later use.** v4 items store observation, mask, reference action, chosen action,
the per-decision 28-action advantage vector and a disallow mask (in the floored kinds the union of the service floor and the
rate floor; a rate-floor-only per-candidate mask is added in the next deployed version without restarting the running
shards), plus order, `joint_ref` and `joint_chosen`, from which B-real's earlier-user same-step context is reconstructed
unambiguously (context for user u = chosen actions of the users before u in the order, reference actions after). The same pass
serves the B1/B2 gates, the T_DR / T_SEQ representability screens, and later soft-advantage teacher labels. The 50 v1 items
(A/B R1 evaluation, 2 A-real R2) carry no advantage vectors; they are not re-run for that.

**I.4 T0 representability runs now, in its own lane** (no dependency on B1): ≥ 100 training-like episodes, one-hot and soft
clones, closed-loop `R_repr` on both episode sets, placebo first. The queued "after B1" serialisation is cancelled.

**I.5 The D0–D4 harness is built now, without optimizer training** — by the B1-credit agent after its credit commit (same
files; a genuine dependency): one switchable implementation (`--mechanism D0..D4`, `--teacher none | T0 | null-*`,
`--credit` from `cf_credit.py`); a teacher interface (T0 = LP-prev(c=1, m=0) computed from the raw user state; matched null
teachers; an offline label provider for the privileged teachers' oracle npz, stubbed and tested on a smoke npz); D1 static
replay (PoolBuffer), D2 on-student-state soft distillation (KL toward softmax(teacher scores / τ) on the deployed scalar
score), D3 DQfD large margin on the deployed scalar score, D4 the D3 margin with a gate that is computable without extra
counterfactual evaluations (primary gate: apply only where the teacher's score margin of its action over the student's current
action is ≥ ε; alternative value gate behind a flag, not run in the first stage); placebos (each mechanism at weight 0 ≡ D0
bit-identically; D0 with `equal_share` and no teacher ≡ CF3 A1; T0 labels reproduce the LP rule's actions exactly; null teachers
carry no information); named mutants per loss; frozen configs; the cf3_launch-pattern launcher; a cost benchmark per arm.
Hyperparameters (τ, α schedule, margin m and weight, gate ε) are declared in the frozen config with their sources (CFSCREEN's
margin scale 0.14–0.16 in the heads' units; DQfD defaults), not tuned.

**I.6 The first stage is single-teacher injection with T0.** T0 is the **non-privileged anchor teacher**; the privileged
candidate catfish are T_DR / T_SEQ / T_JOINT. First-stage arms, each with 3 seeds × 1000 episodes and the CF3 evaluation:
`D0`, `D1-T0`, `D2-T0`, `D3-T0`, `D4-T0`, and a matched null for every teacher arm — `D1-null` (random-legal policy pools of
identical size and seed schedule), `D2-null` (T0's score vector randomly permuted among the legal actions per state, seeded; same
τ and weight), `D3-null` and `D4-null` (margin toward a seeded random legal action; same weight and gate rule). Multi-teacher
composition and drop-one are entered only after the best D arm passes, against D0 and its matched null, the full Amendment 4 §1
screening gate (ρ ≥ 0.5 × R_repr, 2/3 seed pairs, service + rate floor, beyond seed noise).

**I.7 Method priority (does not change any comparison).** D2 (on-student-state / soft distillation) is the primary candidate;
D3 (unconditional DQfD margin) is the required comparator; D4 tests whether gating adds value; D1 is the static-replay lineage
baseline. All nine arms run as declared regardless of this ordering.

**I.8 Downstream, not blockers of the first T0 stage:** ceiling initB1 / initrand, R2 oracle cells, reverse order, the
unfloored calibration tie-ins, Q9 curation, the full ceiling report, T_JOINT label completion. They continue at lower CPU
priority and are read when they land.

## Part II — proposal: branch-invariant D0/T0 short runs before the rate-floor B1/B2 adjudication (NOT adopted)

**Proposal.** If the B1 credit passes its tests and cost check and T0's `R_repr ≥ 0.5`, allow the first-stage arms (I.6) to start
before the rate-floored B1/B2/C adjudication is complete. They remain comparators under B1 and B2 (and the per-user baseline
under C), and their results may not be used to change any B1/B2/C gate.

**For**
1. Every branch needs these arms: they *are* the B1 ladder; under B2 the B1 contract is kept as comparator; under C they are the
   per-user baseline. T0 is non-privileged, so no arm's definition depends on the oracle outcome.
2. The gates are already pre-declared and depend only on oracle cells, so the arms cannot move them by construction.
3. Idle CPU during the adjudication is used.
4. If the D0 credit is the **lighting-price** credit, its ideal version is the LP rule family, which has already passed the
   oracle-first screen (LP-prev(1,0): +6.66 % evaluation, +4.75 % calibration, both gates held) — the oracle-first principle is
   met for that credit without waiting.

**Against**
1. **Oracle-first for the exact difference reward.** The exact-DR credit's ideal version is A-real; Amendment 1 rule 1 drops that
   credit untrained if the rate-floored A-real is ≤ rule + 3.3 %. Training D0 with exact DR before that reading can train a
   mechanism the screen would kill.
2. **Forking paths.** Early D0/T0 readings could colour the reading of the oracle adjudication or the choice of branch.
3. **CPU contention.** 27 runs (9 arms × 3 seeds) compete with the critical-path oracle cells; at 18 concurrent processes on
   this 8P + 12E CPU each process ran ~3× slower (pilot HOLD, 2026-09-11).
4. **Launch risk.** A new harness launched fast is where the pilot's four launch-control defects lived; the fresh-context agy
   review of the actual diff and process-level tests must not be skipped for speed.
5. **Small real saving.** The harness (credit commit → harness → tests → agy review) is the longer pole: its earliest launch is
   ≈ 20:00–20:30 UTC, while the floored evaluation cells land ≈ 18:10 and the floored calibration cells plus the T_SEQ clone
   ≈ 19:30–20:00. The proposal saves time **only if the adjudication slips** past the harness.

**Controller recommendation: adopt as a contingency, with these conditions** (each keeps an existing safeguard intact):
- (a) B1 credit tests green, named mutants red, cost check done; T0 `R_repr ≥ 0.5` for at least one clone on both episode sets.
- (b) The harness passes the fresh-context agy diff review (0 INVALIDATES / 0 BIASES) and process-level stop/resume tests.
- (c) **Credit rule:** if D0 uses the lighting-price credit, it may start early (its oracle has passed); if it uses the exact
  difference reward, D0 and every arm using that credit wait for Amendment 1 rule 1 on the rate-floored A-real.
- (d) **Sealed results:** the runs' readings, evaluations and reports go to a sealed directory; the controller and the owner do
  not open them until the B1/B2/C adjudication is written and committed (process health only is monitored, as for the pilot's
  blind audit).
- (e) **CPU:** launch only after the floored evaluation cells have landed, or with 4 cores reserved for the oracle agent and the
  training capped at 8 concurrent processes until the floored calibration cells are done.
- (f) The nine first-stage arms and their matched nulls are frozen as in I.6 before launch; no arm is added or dropped on early
  results; no B1/B2/C gate is changed by them.

Decision: **the owner's.** Until then Part II is not in force, and ruling §5 plus Amendment 1 §6 stand as written.
