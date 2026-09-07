<documents>
Read these local sources in order. Treat each as authoritative only for claims
it directly supports.

1. `/home/u24/papers/mcrl-leo-handover/.scratch/catfish-oracle-gate/SPEC-v0-OPUS-INPUT.md`
2. `/home/u24/papers/mcrl-leo-handover/.scratch/catfish-pivotality-probe/HEAD-PIVOTALITY-REPORT-2026-08-26.md`
3. `/home/u24/papers/mcrl-leo-handover/.scratch/catfish-opus-review/OPUS-MAX-EE-MEDIATION-REVIEW-2026-08-26.md`
4. `/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/head_pivotality.py`
5. `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/step.py`
6. `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/action_contract.py`
7. `/home/u24/papers/mcrl-leo-handover/src/mcrl/env/service.py`
8. `/home/u24/papers/mcrl-leo-handover/src/mcrl/algorithms/modqn.py`
9. `/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/energy_efficiency.py`
10. `/home/u24/papers/mcrl-leo-handover/.scratch/catfish-pivotality-probe/main-final-seeds-10-v1.json` only if a numeric detail is needed.
</documents>

<role>
Act as an independent mechanism-design and experimental-validity reviewer for
this exact LEO MODQN host. You advise; you do not own the scientific ruling.
</role>

<goal>
Audit the proposed local-oracle gate before it is implemented or run. Decide
whether it can honestly test the existence of learnable, per-user R2/R3
opportunities that improve immediate system EE beyond a Q1-only baseline,
without becoming a joint optimizer or using post-outcome proposal selection.
</goal>

<review_questions>
1. Is a Q1-only main trajectory plus one-focal-user counterfactual the correct
   smallest opportunity screen? State exactly what it can and cannot prove.
2. Are the R2 minimum-handover/Q1-tiebreak proposal and its symbolic
   handover-burden thresholds mathematically and causally valid under the live
   environment? Identify any missing state or realised-service issue.
3. Are `reuse_active_lower_load` and `open_inactive` genuinely pre-outcome,
   per-user R3 proposal families? Check whether previous radiating/demand state
   supports the claimed same-active-set versus changed-active-set semantics.
4. Verify the `g_eta` identity and whether using exact Q1-baseline `eta0` is
   legitimate as an oracle label while remaining unavailable to a deployable
   pre-action mechanism.
5. Audit focal-user sampling, interaction/SUTVA limitations, seed-level
   inference, and the pre-result 30-case/8-of-10/10% retention rules. Recommend
   minimal replacements only where the current rule would mislead.
6. Check that the gate excludes training-time outcome filtering, joint action
   coordination, deployment override, and double counting of whole-system EE.
7. Give the smallest exact patch set to the spec before implementation and the
   maximum defensible claim if the patched gate passes.
</review_questions>

<constraints>
[non-heavy review] Read only. Do not edit files, launch training, browse the
web, or use subagents. Preserve the current checkpoint/reward baseline. Treat
the three-role design as a hypothesis rather than a required conclusion. Do
not invent `T_HO`, `E_HO`, or literature values. Distinguish repository fact,
mathematical implication, and untested design proposal. Keep the response under
2500 words and focused on decision-changing findings.
</constraints>

<output>
Use exactly these sections:

1. `VERDICT`: one of `APPROVE`, `APPROVE_WITH_PATCHES`, or `REJECT` plus two
   sentences.
2. `FATAL_OR_LOAD_BEARING_ISSUES`: numbered findings with source lines.
3. `SPEC_PATCHES`: exact replacement wording/formulas or `NONE`.
4. `IMPLEMENTATION_CONTRACT`: minimal inputs, outputs, invariants, and parity
   checks.
5. `DECISION_RULES`: retain/revise/drop outcomes for R2 and each R3 family.
6. `CLAIM_CEILING`.
</output>

<query>
Review `SPEC-v0-OPUS-INPUT.md` now. Optimize for an honest, executable
falsifier rather than preserving three roles.
</query>
