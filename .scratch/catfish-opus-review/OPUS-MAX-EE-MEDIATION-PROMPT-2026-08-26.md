<documents>
Read these sources in order. They are all local and authoritative only for the
claims they actually contain.

1. `/home/u24/papers/mcrl-leo-handover/.scratch/catfish-opus-review/OPUS-MAX-REVIEW-2026-08-26.md`
2. `/home/u24/papers/mcrl-leo-handover/.scratch/catfish-opus-review/DESIGN-CANDIDATE-v0.md`
3. `/home/u24/papers/mcrl-leo-handover/docs/POST-RUN-VALIDATION-CORRECTED-R2-2026-08-26.md`
4. `/home/u24/papers/mcrl-leo-handover/docs/CATFISH-DESIGN-FREEZE-GATE-2026-08-26.md`
5. `/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/modqn.py`
6. `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/step.py`
7. `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/service.py`
8. `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/action_contract.py`
9. `/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/energy_efficiency.py`
10. `/home/u24/papers/mcrl-figures/docs/portfolio/ris-full-paper-blind-v1/paper-blind.md`, especially section 4.2.2.

The working trees contain user WIP. Treat every file as read-only.
</documents>

<role>
Act as an independent mechanism-design reviewer for this exact multi-objective
LEO handover host. You do not own the final scientific ruling and you are not
implementing or training anything.
</role>

<decision_context>
The author prioritises actual effectiveness over a neat three-role story. The
desired architecture nevertheless has three training-time Catfish challengers:
R1 targets Q1/system EE directly, R2 targets the handover reward, and R3 targets
physical-beam load. Only one Main policy is deployed. Per-user action selection
uses the weighted scalarised surface `0.5*Q1 + 0.3*Q2 + 0.2*Q3`.

The unresolved question is not whether R2 and R3 can improve their own direct
endpoints. It is whether their specialised exploration/training experiences can
causally improve final system EE after all three heads are combined into one
action. The current design gate's `EE >= 95% of removal arm` rule establishes at
most bounded harm, not positive EE improvement.
</decision_context>

<goal>
Recommend the strongest technically coherent Catfish design under the live
physics and trainer. Decide whether R2 and R3 can defensibly act as indirect EE
optimisers, what carrier makes that possible, and what evidence would prove or
falsify their marginal EE contribution.
</goal>

<questions>
1. Under the implemented EE, rate, power, handover, segment, and load equations,
   identify the exact causal paths and sign ambiguities from R2 to EE and from R3
   to EE. Distinguish a structural implication from a plausible hypothesis.
2. Compare these carriers:
   A. role-specific banks with Q1-only/Q2-only/Q3-only auxiliary gradients;
   B. role-specific proposal/branch generation whose complete `(r1,r2,r3)`
      transition is consumed by the existing shared full-vector update;
   C. any concrete third carrier that is stronger than both.
   Select one or reject all. Account for final scalarised-action effectiveness,
   cross-head cancellation, off-policy bias, and matched-compute controls.
3. Should R2/R3 challenge only inside an EE-near-tie or Q1-admissible action
   set? If yes, give a pre-outcome formula and explain how it avoids merely
   turning both roles into R1 clones. If no, give the better trigger.
4. Can R2 honestly improve EE when handover penalty itself does not subtract
   bits or add joules? Decide among retaining pure R2, redesigning it as a
   temporal/ping-pong specialist, requiring a physical handover-cost model, or
   dropping it. Do not preserve a third role for symmetry.
5. Can R3 add information beyond R1 when lower load raises `B/U` but can also
   activate more beams and power? Specify whether R3 should be independent,
   system-level/cross-user, coupled to R1, or dropped.
6. Give the smallest non-heavy checkpoint/branch prototype, followed by the
   minimum heavy matched experiment, that identifies: head pivotality, physical
   action flips, one-step or horizon EE mediation, role marginal effects, and
   R1/R2/R3 interactions.
7. Replace the current 95% EE safeguard with exact decision rules appropriate
   to each possible claim: positive EE improvement, EE non-inferiority plus a
   secondary-objective gain, or a disclosed Pareto trade-off.
8. State the maximum defensible contribution claim if the proposed tests pass.
</questions>

<constraints>
Perform a read-only review. Do not edit files, launch training, use subagents,
or browse the web. Do not change the frozen baseline reward definitions merely
to make the Catfish story work. A separate physical-model change may be named
only if current equations make a desired claim impossible. Preserve the
distinction among repository fact, inference, and untested proposal. The branch
decision must be pre-outcome and every valid realised branch must be retained;
do not reintroduce positive-outcome admission. Exclude post-training auction,
coordination, messaging, and deployment-time action override.
</constraints>

<output>
Keep the answer operational and use these sections:

1. `VERDICT`: exactly one of `KEEP_THREE`, `KEEP_CONDITIONAL_THREE`,
   `MERGE_OR_DROP`, or `REJECT_DIRECTION`, followed by two sentences.
2. `DIRECT_ANSWER`: whether optimising R2/R3 can indirectly improve EE in this
   implementation, with separate answers for R2 and R3.
3. `CAUSAL_AUDIT`: equations/path, sign, confounders, and file-line evidence.
4. `CARRIER_DECISION`: select A, B, C, or rejection and give the exact training
   data/update flow.
5. `ROLE_SPEC`: one row per Catfish with trigger, proposal, learned signal,
   final EE mechanism, and falsifier.
6. `PROOF_PROTOCOL`: local prototype, heavy matched experiment, metrics, and
   controls.
7. `DECISION_RULES`: exact outcomes for keep, couple, relabel, or drop.
8. `REQUIRED_SPEC_PATCHES`: minimal edits needed to the current design before
   implementation.
9. `CLAIM_CEILING`.
</output>

<query>
Resolve the R2/R3-to-EE mechanism question now. Treat three roles as a desired
hypothesis, not a required conclusion.
</query>
