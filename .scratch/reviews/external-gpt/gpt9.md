Owner direction: start **parallel Catfish-2+ discovery now**, using the same fast-iteration philosophy, but do not disturb or delay the Catfish-1 convergence funnel.

I have read the latest controller assessment and adopt its stricter interpretation:

* D3 is an **injection mechanism**, not a Catfish.
* T0 is currently a **candidate source with very strong transfer evidence**, not yet a certified Catfish until D3-null / k2 closes the causal marginal.
* A source only earns Catfish status if it is not merely a renamed score term: it must satisfy the project's existing frontier / distinctness / positive-marginal logic and ultimately survive a drop-one causal test.
* The old static/offline three-source implementation is closed. Existing policies may be reused as controls, but do not presume they are viable Catfish.

## 1. Do not touch the Catfish-1 critical path

DEVHARNESS continues independently:

`D3-null k0/k1 -> k2 D0/D3-T0/D3-null -> provisional freeze -> E1`

The D3-null implementation is already committed as `05aadf1b...`; its fresh-context review reports 22/22 clean tests green, all 7 named D3-null mutants red, bit-identical stop/resume, and verdict "development training runs may proceed."

CATFISH2-DISCOVERY must not reopen, redesign or gate that work.

Use a separate worktree / result root and DEV / DEVVAL namespaces only.

## 2. Stage 0 is discovery only: NO learner training

The goal is to identify at most two sources that are scientifically capable of becoming an additional Catfish before spending training compute.

Use the existing 24 DEVVAL episodes and current physics/action contract.

For every candidate, collect:

* pooled EE;
* bits;
* joules;
* served fraction;
* per-served-user rate mean / p10 / minimum;
* active beams;
* H_inter / H_intra;
* action agreement / disagreement with T0;
* disagreement with MAX_NOMINAL_GAIN and the frozen MODQN reference where cheap.

Then compute a **value-weighted disagreement / complementarity diagnostic** against T0.

On states where Candidate and T0 choose different legal actions, use the existing CRN `evaluate_actions` machinery, holding all other users' actions fixed, and record Candidate-vs-T0 unilateral:

* Δbits;
* Δjoules;
* `Δ(bits - eta0 * joules)`;
* whether the candidate improves p10 / protects a served user where a meaningful same-step measure is available;
* Candidate>T0 fraction;
* T0>Candidate fraction;
* median / p10 / p90 value difference;
* QoS-invalid fraction.

This diagnostic may use privileged physics for **measurement only**. The source policy itself must remain deployable from the declared observation, unless explicitly classified as privileged and subjected to the existing representability test before any learner canary.

## 3. Do NOT lead with the old B1 / A-m12 policies

The latest controller assessment is accepted: existing measurements indicate `B1_NO_NEW_BEAM` and `A m=12dB` are largely dominated by T0 on EE / per-user-rate behaviour, and the LP-family rules overlap heavily.

Therefore:

* `MAX_NOMINAL_GAIN`
* `A m=2dB`
* `A m=12dB`
* `B1_NO_NEW_BEAM`

may be included cheaply as **reference/control policies**, but they are not the primary Catfish-2 hypotheses unless the new Stage-0 analysis reveals previously unmeasured non-dominated complementarity.

Do not spend 100-episode learner runs on a dominated old source merely because code already exists.

## 4. Primary new candidate family: QoS / rate-tail specialist

Design the minimum observation-compatible teacher whose purpose is explicitly different from T0:

**protect service quality / weak-user rate rather than maximise the same EE-consolidation score.**

The physical narrative should be:

* T0 pushes the EE / activation-cost lever;
* Catfish-Q protects the throughput / service-quality tail when consolidation would overload a beam or make an association fragile.

Before implementing the policy, verify exactly which quantities are available in the current deployable 113-dim observation.

Important: do **not** silently use "the weakest other user on that beam", realised future rate, other users' private channel state, or any quantity absent from the deployed observation.

If exact weakest-user QoS is not observable:

1. construct the simplest observation-only risk proxy from quantities already present, such as own candidate channel quality, previous beam occupancy and the fixed rate / ACM threshold information;
2. state exactly what it approximates;
3. do not add a new observation feature in this discovery lane.

If the scientifically preferable QoS teacher inherently requires privileged information, keep it as a separate diagnostic teacher and run the existing representability procedure before considering it deployable. Do not confuse a strong oracle with a valid Catfish.

Use physical constants / existing rate targets / ACM thresholds already defined by the system. Do not introduce a free coefficient grid.

At most **two prospectively specified QoS variants**, and preferably one.

## 5. Secondary candidate family: rate-qualified consolidation

The second new mechanism worth screening is consolidation that does NOT blindly prefer an already-lit beam.

Construct a minimal observation-only rule of the form:

> consolidate / avoid a new beam only when the candidate association still clears a pre-existing rate-quality criterion; otherwise allow the stronger link.

This is deliberately different from old `B1_NO_NEW_BEAM`, which uses a hard restriction and has already looked dominated.

Again:

* use existing physical/rate thresholds rather than tuning a new coefficient;
* no parameter grid;
* one prospectively defined variant first.

Its intended mechanism is:
**save activation energy only when the throughput sacrifice is acceptable.**

## 6. T0 decomposition is a diagnostic hypothesis, not a narrative decision

T0 is:

`log2(1 + gain) - 1*(previous beam load == 0)`

so it visibly contains a link-quality pressure and an activation-price pressure.

However, that does NOT by itself create two Catfish.

Run a cheap decomposition analysis only:

* link endpoint: `MAX_NOMINAL_GAIN` / `c=0`;
* activation-heavy endpoint: existing B1 / corresponding high-c behaviour;
* fused T0: `c=1`.

Measure:

* standalone frontier position;
* T0 disagreement;
* value-weighted complementarity;
* whether either endpoint owns a meaningful subset of states in which it is better than the fused T0.

Do NOT launch separate D3 learner runs for the endpoints unless Stage 0 establishes genuine non-redundant value.

Only if two specialist policies later each carry transferable positive marginal and FULL beats both drop-one variants may the paper reinterpret T0 as a fixed fusion of two Catfish.

Otherwise T0 remains one candidate Catfish. No salami-slicing.

## 7. Representability is part of Stage 0, not a later surprise

For each genuinely new candidate that survives the raw rollout/complementarity screen:

* verify it is a deterministic function of the current deployable observation where claimed;
* if this is not algebraically exact, collect the candidate's 28-action score/action labels and run the same cheap BC / soft representability clone logic already used for T0/T_SEQ;
* use the existing `R_repr >= 0.5` development/admission convention rather than inventing a new threshold.

A strong source that the student observation cannot represent is not taken to a D3 learner canary.

Run these clone jobs in parallel; they are discovery work and must not block D3-null/k2.

## 8. Stage-0 selection: maximum two survivors

Apply the project's existing Catfish-count logic rather than naming sources first and justifying them later.

A candidate may advance only if it has all of:

1. deployability / adequate representability;
2. a non-dominated or clearly complementary position in `(EE, served, p10)` space;
3. meaningful behavioural distinctness from T0;
4. a state subset with positive value-weighted complementarity rather than disagreement for disagreement's sake;
5. no obvious QoS collapse.

Do not invent an arbitrary new numerical success threshold after seeing results. If Amendment 4 does not numerically define one of these development diagnostics, write the short development reading rule before counted Stage-0 evaluation.

Advance **at most the best two**.

If zero qualify, report zero. Do not manufacture a Catfish count.

## 9. Only then run a 100-episode transfer canary

For each Stage-0 survivor only:

* reuse the already-working D3 large-margin injection;
* DEV k=0;
* 100 episodes;
* same student / ratio learner / credit / optimisation configuration as the current D3-T0 development line;
* matched random-legal null with its own declared DEV-NULL generator identity;
* compare against the existing D0 protocol at the same depth.

This answers:

`does this candidate contain transferable information under the already-working injection channel?`

Immediately close a candidate if it does not beat its matched null / D0 directionally without QoS degradation.

Only a k0 survivor gets k1.

Do not run any new candidate to 300 at this stage.

## 10. Multi-teacher integration comes after two sources independently survive

Do not yet implement an arbitrary sum of two D3 margin losses.

Multiple teachers can issue conflicting target actions, so before the first `T0 + C2` training run, declare a minimal arbitration/gating rule prospectively.

Prefer a rule grounded in each teacher's own confidence/advantage or a state-dependent gate; do not resolve conflict by silently giving T0 or the new source an arbitrary weight.

Then the minimum multi-Catfish development test is:

* FULL = T0 + C2;
* DROP_T0;
* DROP_C2;
* matched null/control.

The Catfish count is earned by **positive drop-one causal marginal**, not by the number of named heuristics or terms in one score.

Do not design a 3- or 4-Catfish controller until the two-source case works.

## 11. Parallel execution / fast iteration

This lane must stay lightweight and concurrent with Catfish-1 closure.

Stage 0:

* parallel rollouts / complementarity / representability;
* no training;
* existing policy code reused where possible;
* no formal seeds;
* no hyperparameter grid.

Stage 1:

* maximum two candidates × one 100-episode k0 canary initially;
* k1 only for survivors.

No exact-DR learner training.
No B2 reopening.
No long oracle search.
No changes to the frozen Catfish-1 learner architecture.

Use immutable short versions and record the exact source definition before each counted run.

## 12. First report from CATFISH2-DISCOVERY

Return one compact table containing:

* candidate name;
* exact deployable score / rule;
* information used;
* standalone EE / served / p10;
* Pareto status;
* T0 action disagreement;
* value-weighted complementarity;
* representability result;
* classification:
  `DROP / CONTROL ONLY / CANARY-ELIGIBLE`.

Then state:

* whether the T0 decomposition is supported or rejected as a multi-Catfish interpretation;
* which 0–2 candidates, if any, advance to D3 @100;
* the exact prospective reading rule used for that decision.

Do not wait for Catfish-1 freeze to produce this Stage-0 table.

Goal: by the time `D3-null -> k2 -> freeze` completes, Catfish-2 should already have a scientifically filtered shortlist rather than starting discovery from zero.
