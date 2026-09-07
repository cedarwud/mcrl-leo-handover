# Opus Max adjudication — Fable C3 target redesign and CSE algebra

Work class: **non-heavy**. Stay in the current environment. This is a concise,
read-only scientific adjudication. Do not run simulator worlds, harvest
sources, train learners, open TEST, or modify current authority/code/contracts.

<role>
Act as the independent final challenger for one high-impact design fork in
Multi-Catfish MCRL. The final system must retain exactly Q1, Q2, Q3 and one
unweighted masked argmax Q1+Q2+Q3, with canonical ratio-of-sums EE as the only
end objective and no deployment coordinator/gate/auction/fallback.
</role>

<task>
Adjudicate the report
`artifacts/multi-catfish-c3-fable-cleanroom-20260904-r1/FABLE-C3-SOURCE-AUDIT.md`.
Focus on whether its evidence actually requires redesigning R3, and whether
its proposed cost-share externality (CSE) target is mathematically sound for
the unilateral-training/simultaneous-deployment interface. Do not treat either
the Fable report or the current V0.20 draft as authority.
</task>

<inputs>
- `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`
- `src/mcrl/runtime/ee_axis_zero_marginal_c3.py`
- `src/mcrl/runtime/ee_axis_relational_zr_c3.py`
- `src/mcrl/runtime/ee_surplus_targets.py`
- `src/mcrl/runtime/ee_axis_evaluation.py`
- the simulator power/rate functions directly referenced by the Fable report
- `artifacts/multi-catfish-v018-relational-zr-20260904-r2/contracts/result.json`
- `artifacts/multi-catfish-v018-relational-zr-20260904-r2/contracts/independent-validation.json`
- `artifacts/multi-catfish-v019-relational-q3-learner-20260904-r1/server-run/gate-output/report/result.json`
- `.scratch/multi-catfish-v020-c3-source-audit/v019-train-decision-geometry.json`
- `.scratch/multi-catfish-v020-c3-candidate-screen/CANDIDATE-DESIGN-DRAFT.md`
- the Fable report named above
</inputs>

<questions>
1. Re-derive the matched-reference EE sign identity and state exactly what a
   stale fixed lambda invalidates. Does lambda0 < current background EE by
   itself invalidate ZR, which is unilateral-delta-energy zero and
   lambda-invariant, or does it invalidate the Q1/Q2 background and therefore
   confound interpretation only?
2. Decide whether the observed ZR signature (bits fall, energy falls more, EE
   rises, active beams fall) is a legitimate EE-improving C3 mechanism that can
   be named consolidation, or evidence that the R3 target is causally wrong.
   Separate target semantics, joint policy side effect, and user-requested
   positive EE marginality.
3. Audit the proposed CSE equations algebraically. Let share_u(x) sum to P^N(x)
   for one common joint configuration x. Distinguish carefully between:
   - shares evaluated on one common joint transition;
   - each user's separately evaluated unilateral counterfactual c^(u,a);
   - the sum of configuration-level shares;
   - the sum of unilateral utility differences.
   Determine whether the proposed
   z3_CSE = DeltaB_nonfocal - lambda(Delta share_u - Delta P^N), together with
   unchanged z1 = DeltaB_focal - lambda DeltaP^N, really yields the claimed
   global-surplus/additivity property under simultaneous deployment. Give a
   two-user/two-beam counterexample if it does not.
4. Check for double counting or cancellation between unchanged C1, unchanged
   C2, and CSE. State the exact quantity represented by z1+z3_CSE for one
   unilateral action, and what summing those scores across users represents.
5. Assess the Fable claim that V0.19 is primarily a learner-objective failure
   but secondarily a wrong-target failure. State which conclusion is directly
   established by receipts and which is inference.
6. Determine the smallest decisive next step. Compare:
   A. retain ZR, fix feature conditioning and decision-aligned learning;
   B. first reprice lambda consistently for every affected head/background,
      then compare ZR against alternatives;
   C. replace R3 with CSE as written;
   D. amend CSE or use a different cost/congestion externality target.
   Prefer a bounded test using already-opened TRAIN components when it can
   answer the question before any fresh heavy panel.
7. State the minimum C1/C2 consequence. In particular, say whether changing
   lambda requires relabelling/retraining Q2 as well as Q1 before a coherent
   three-head comparison.
</questions>

<evidence_boundary>
All V0.12/V0.13/V0.18/V0.19 results are development/oracle or learner-gate
evidence, not efficacy. Do not infer learned C3 success from an oracle, and do
not infer structural impossibility from one learner failure. Preserve the
user's actual criterion: eventually FULL must exceed DROP-C1, DROP-C2, and
DROP-C3, and each drop arm must exceed BASELINE; pairwise coalition positivity
beyond those arms is not an extra requirement.
</evidence_boundary>

<output>
Create only:
`artifacts/multi-catfish-c3-opus-adjudication-20260904-r1/OPUS-C3-FABLE-ADJUDICATION.md`

Keep it under 2,500 words. Include:
- a claim-by-claim verdict table for the seven questions;
- the complete CSE algebra/counterexample;
- one recommended next test with fixed inputs, outputs, pass/fail rule, compute
  class, and estimated wall time;
- the implications for the current V0.20 learner screen;
- a short list of claims that remain prohibited.

End with exactly one token on its own line:
- `RETAIN_ZR_REDESIGN_LEARNER`
- `REPRICE_ALL_HEADS_THEN_COMPARE_TARGETS`
- `REDESIGN_R3_TO_CSE`
- `REDESIGN_R3_OTHER`
- `STOP_THREE_HEAD_ROUTE`

Return only a concise completion summary and the report path after writing the
file.
</output>
