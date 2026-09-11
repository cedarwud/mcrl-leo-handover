# Ruling — parity first; the ceiling scenarios stand; the B-chain has stop conditions; the number of catfish is measured, not preset; nothing trains while we wait

Date: 2026-09-11, ~14:40 UTC (server clock). **Written before any ceiling number is known**: the base search (24 evaluation
episodes) is still running, its counterfactual-vs-committed parity check is pending, and the nominal-information,
rate-floor, compound and unconstrained variants have just started. The LP rule probe is running. This ruling
supplements `V025-CONTROLLER-RULING-Q5-NO-GO-AND-CEILING-SCENARIOS-2026-09-11.md`; it changes no threshold declared
there. Owner confirmed the four points of the 14:20 UTC exchange ("我確認那四點，可以直接寫成裁定") and required that the
ruling decide the next step automatically when the numbers arrive.

## 1. Parity comes first (controller discipline; in force now)

The centralised search scores candidate joint actions with the environment's counterfactual evaluator and then commits
the chosen action to the real environment. **Until the ceiling agent reports that the evaluator's per-step bits and
joules equal the committed step's (max |Δ| per step recorded, with the threshold it declares), no number produced by
the search may appear in any document, decision, message or external statement.** This clause outranks every other
condition. Consequence for the record: the interim per-episode figures the controller quoted at 14:10 UTC (from the
search logs) are **withdrawn as provisional** and are not to be repeated until parity is reported PASS; the
`WORK-QUEUE-DECISIONS` entry that quoted them carries this note.

Standard wording once parity passes: the local search yields **a lower bound on the centralised one-step optimum**
("at least this much room"), never "the ceiling is X".

## 2. The three scenarios and their thresholds are unchanged

A: constrained (service-floor) search ≤ +3.3 % over `A m=2dB` on the 24 evaluation episodes (paired). B: nominal-information
unilateral point ≥ +4.5 % over the rule with served ≥ 0.995 and bits ratio ≥ 0.95. C: only the joint / compound search is
high. Between thresholds: unresolved, no training. Nobody changes these after the numbers exist. Two clarifications
that add conditions rather than move thresholds:
- **Information level.** The number that can be a target for any deployable per-user policy is the **nominal-information**
  point (observation-only scoring), not the realised-counterfactual search. A realised-information gain that the nominal
  variant does not reproduce is evidence for C at most, never for B.
- **Throughput tail.** Pooled EE is blind to per-user rate; the service floor counts served users only. A gain that the
  **rate-floor** variant (no served user below 50 % of its rate under `A m=2dB` at the same step) does not preserve is a
  throughput-degenerate gain and does not count toward A/B/C. Every EE figure in this line is reported with served
  fraction and the per-served-user rate mean / p10 / min.

## 3. The B-chain: fixed order, each stage with a pass condition and a stop; nothing advances automatically past a fail

Let `G_nom` = the nominal-information unilateral point's gain over `A m=2dB` on the 24 evaluation episodes (paired,
rate-floor-preserved). Each stage keeps the deployment contract (per-user decision, 10-step episodes, no coordinator),
carries its own pre-registered declaration, a matched null control (evaluation contract rule 2), the pinned archive, and
the same evaluation as CF3 (24 evaluation episodes, per-episode reseeded, final checkpoint, seed-mean with the 2-of-3
seed-pair rule).

| stage | change | pass condition (measured at CF3 scale: 3 seeds × 1000 episodes, unless the owner sets otherwise) | on fail |
|---|---|---|---|
| **B1 — credit** | replace equal-share `E_u` by a **difference reward** `D_u = F(a) − F(a_{−u}, a_u^ref)` at the step, `F = bits − η·joules`, computed by the environment's own counterfactual evaluator (`evaluate_actions_without_user`, common random numbers), with an explicit outage charge; architecture and observation unchanged | recovers **≥ 50 % of `G_nom`**: `(EE_learner − EE_rule) / (EE_nominal − EE_rule) ≥ 0.5` on the evaluation set, seed-mean, ≥ 2 of 3 seed pairs, served ≥ 0.995, rate floor preserved. **The 50 % is the owner's number: default proposed by the reviewer, awaiting the owner's explicit confirmation or replacement.** | stop; re-evaluate the credit design; **no automatic advance to B2** |
| **B2 — information** | sequential decisions within the step: user k sees the beams already chosen by users < k this step (observation carries the current-step lighting pattern); credit as in B1 | same criterion, against the **sequential** nominal reference (LP-seq / sequential nominal search) | stop; re-evaluate; **no automatic advance to C** |
| **C — coordinator** | centralised training, joint / set-level critic, CTDE or a coordinator | **not a stage of the chain.** It changes the deployment contract and the paper's skeleton; **entering it is the owner's decision**, taken on the ceiling's C-evidence, never triggered by a B failure |

Before any stage trains, the sources it would use as catfish must pass the **source-value screen** at that stage's scale
(the source's pool beats random-legal pools of identical size and schedule, A2-vs-A3 style); a source that does not is
not a catfish, whatever its name.

## 4. The number of catfish is measured (controller's operational definition; awaiting the owner's confirmation)

A candidate source (a rule, an LP(c, m) cell, a regime extracted from the search's solutions, or a learned policy) occupies
one catfish slot only if **all three** hold:
1. **Frontier non-dominance**: on the (pooled EE, served fraction, p10 per-user rate) frontier on the evaluation set, no
   other retained candidate weakly dominates it.
2. **Distinctness on shared states**: against every other retained candidate, action disagreement ≥ 25 % on the same
   states, and its visited-state distribution is not contained in the other's (CFSCREEN's state-coverage measure: out-of-
   95th-percentile share ≥ 0.2 in at least one observation block). Proposed numbers, set from CFSCREEN's scale (C1 vs C2
   disagreed 35–55 % yet C2's states lay inside C1's — that pair fails this test, which is the lesson).
3. **Marginal value at the current scale**: once a source-value signal exists, dropping it lowers the learner's EE by more
   than the between-seed SD (2-of-3 seed pairs). Measured only after (1)–(2) and only inside a stage that passed.

The count of catfish is the number of candidates satisfying all three; one, two, four are all admissible answers. "Three"
is never written before the count is measured. Items 1–2 are measurable before any training; item 3 is not.

## 5. What is not authorised while we wait

Until the ceiling agent has reported **parity, the pooled base-search result, the nominal-information variant, the
rate-floor variant and the compound variant**, **no learner training run starts** — not a "quick look", not a single seed,
not a re-run of an existing arm. Allowed: read-only rollouts of rules and existing checkpoints, pool generation for
candidate sources, curation, writing. This clause exists so that the waiting time is not used to iterate inside the box.

## 6. Who decides what

| item | decided by | status |
|---|---|---|
| parity before any citation (§1) | controller discipline | in force |
| three scenario thresholds (§2) | already declared; nobody changes them | in force |
| B-chain pass ratio (§3, the 50 %) | **owner, now** | default written; **awaiting confirmation** |
| entering C (§3) | **owner** | not automatic |
| operational catfish count (§4) | controller proposes, **owner confirms** | **awaiting confirmation** |
| paper framing | owner, after the ceiling numbers | open |

## 7. Standard phrasing from now on (three corrections adopted)

- The lever is **bits per lit beam**, not "fewer beams": `B1_NO_NEW_BEAM` at 39 beams scores below `A m=2dB` at 63
  (104.19 vs 112.20 M bit/J, pinned calibration set); consolidation raises EE only when it removes low-bit beams.
- The trained energy head **changes 11–42 % of decisions** (H4 probe, 9 final checkpoints) but has **no consistent
  effect on EE** (−8.1 … +3.1 %); "inert" is wrong, "does not deliver EE" is right.
- The local centralised search gives a **lower bound on the centralised one-step optimum**, not a ceiling.
