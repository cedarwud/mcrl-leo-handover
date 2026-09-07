# C1 post-gate micro-screen adjudication V0.1

Date: 2026-08-28  
Status: cross-model review and no-step diagnostic complete; not a method
freeze, routing authority, or formal-training authorization  
Bound evidence: `artifacts/smc-er-c1-authority-20260828/`

## Executive ruling

The current C1 composite must not enter formal training.  The sealed
four-episode screen independently reproduced `STOP_AND_REDESIGN_C1`: the
C1-informed branch achieved lower fresh-seed Main-only system EE than its
matched-neutral branch even though the upstream C1 source-quality gate had
passed.  This is a directional failure of the tested **C1-BOTH composite under
the current full-vector/all-head Main-consumer routing**, not evidence that C1,
EXP, ACRM, or objective-specific Catfish mechanisms are universally
ineffective.

The protected core remains:

- the canonical system EE and `r1/r2/r3` definitions;
- three independent objective specialists and one scalarized Main MODQN;
- executed atomic experience bundles, not post-training action fusion;
- Main-only deployment, with no auction, coordination, or Catfish override;
- C1 EXP and ACRM remaining private to the C1 specialist unless a separately
  preregistered component test rejects one of them.

The unresolved seam is how a specialist-origin bundle contributes gradients to
the three Main objective heads.  The V0.1 concept freeze and V0.4 paper method
currently say that every donor's full reward vector updates every Main head.
That statement and its figure arrows are no longer camera-ready.

## Sealed facts

The one allowed screen execution and its independent replay report:

| Quantity | C1-informed | Matched-neutral | Difference |
|---|---:|---:|---:|
| Aggregate ratio-of-sums EE | 90.591676 Mbit/J | 94.288819 Mbit/J | -3.697142 Mbit/J |
| Served fraction | 0.9996 | 0.9966 | +0.0030 |

The mean paired EE difference is `-3.783079 Mbit/J`; only one of five paired
evaluation seeds is positive.  All structural and service guards pass.  The
sealed claim ceiling is exactly:

```text
ONE_SEED_4EP_DIRECTIONAL_SCREEN_NOT_ROUTING_AUTHORITY_NOT_CHAPTER5
```

Both arms used the same relative dose and schedule: 31 specialist-prefill
bundles, 40 admitted C1 bundles, one warm-up step, and 39 applied Main updates.
Each applied update contained one Main source unit and one C1 source unit.  The
independent validator exactly replayed all ten evaluation points and initial
parity.

There is also a verified carrier mismatch that must be corrected in the next
revision.  In routed mode, `update_main_with_source_quota` consumes one
canonical replay RNG sample but discards the sampled batch; it substitutes the
current complete Main bundle in the loss.  Therefore the two treatment arms
remain mutually matched, but their Main-origin update is not the unchanged
canonical replay update used by zero-dose MODQN.  This does not erase the
sealed informed-versus-neutral failure.  It does prevent the present routed
carrier from being treated as a clean additive Catfish intervention over the
baseline.

The separate source-quality result remains upstream-only evidence.  It shows
that the local-SNR source is better than its masked-uniform source control in
that frozen source protocol; it does not establish downstream Main efficacy.

## What the result does not identify

The informed and neutral branches differ jointly in source corpus, specialist
learning history, online behavior, and private ACRM use.  The sealed screen has
no zero-dose arm.  It therefore cannot causally separate:

1. EXP prefill;
2. private ACRM;
3. learned C1 behavior versus its direct local-SNR source;
4. full-vector/all-head routing;
5. absolute C1 dose;
6. state-distribution shift; or
7. interaction with the routed carrier's replacement of the canonical Main
   replay batch; or
8. a four-episode transient under one training seed.

The observed C1-informed donor stream has higher `r1` but a worse `r3`
distribution than the neutral stream.  Because the current consumer applies
each C1 bundle's `r1`, `r2`, and `r3` TD losses to `Q_1^M`, `Q_2^M`, and
`Q_3^M`, respectively, cross-head opposition is a plausible mechanism.  It is
not yet a sealed causal finding.

## Candidate redesigns under review

| Candidate | Definition | Main advantage | Main risk |
|---|---|---|---|
| Current all-head | Each C1 bundle updates all three Main heads | Preserves all observed cross-objective consequences | Directionally failed; donor distribution can move non-target heads against its own target action |
| Direct anchor | Route executed local-SNR or matched-random bundles without the learned C1 specialist | Maximum attribution and minimum learner complexity | Weakens the intended RIS-style EXP/ACRM Catfish mechanism |
| EXP-only C1 | Keep the C1 specialist and EXP; freeze `eta=0` | Separates EXP from ACRM | Still leaves behavior-distribution and routing questions |
| Role-targeted | C1 real TD loss updates only `Q_1^M`; C2 only `Q_2^M`; C3 only `Q_3^M`; withheld losses are audited without gradient | One role, one head; smallest routing change; clearer multi-Catfish attribution | Non-target consequences reach those heads only through Main-origin experience and may remain off-support |
| Outcome-gated/adaptive | Admit or reweight donor samples from realized rewards | Can suppress harmful samples | Invalid as the next test: post-outcome selection and new tuning freedom invite result procurement |

Outcome-gated admission, Pareto cherry-picking, adaptive source weights, and
post-training coordination are excluded from the next candidate.

## Independent alternative reviews

The post-result reviews were asked to search alternatives, not merely certify
the current design:

- Fable Max preferred retaining the learned C1 specialist, EXP, and ACRM while
  changing only the Main interface to role-targeted injection.
- A fresh-context Sol Ultra review preferred removing the active C1 learner and
  using a direct local-SNR anchor under Q1-only routing, because that maximises
  immediate causal identification and exposes the fewest moving parts.
- Both independently rejected formal training under the current all-head,
  50-percent source-weight carrier.  Both required a no-step source/head
  gradient audit before another outcome-bearing campaign.

The disagreement is substantive: it trades the intended RIS-lineage Catfish
mechanism against causal simplicity.  It is not resolved by model voting.

## Controller adjudication before the gradient audit

The first candidate remains **the learned C1 specialist with role-targeted Main
injection and full-vector audit retention**.  The direct anchor is frozen as the
explicit fallback/reference rather than silently discarded.  This ordering is
based on the observed fact that the learned informed C1 collection trajectory
itself retained higher descriptive EE and service than its neutral trajectory;
that observation is not a matched-anchor efficacy result, so the preference is
provisional.

The revised consumer must preserve the actual canonical Main replay update.  A
routed role augments only its corresponding objective loss:

```text
L_j = (1 - beta_j) L_MainReplay,j + beta_j L_Cj,j
L_k = L_MainReplay,k                                  for k != j
```

`L_MainReplay` must use the exact canonical sampled minibatch rather than merely
consume and discard its RNG sample.  The complete unmodified specialist reward
vector and atomic bundle remain in the receipt; non-target TD losses are
computed under `no_grad` for audit only.  An absent, shadowed, or unusable role
sets its effective `beta_j` to zero and must be byte-exact with the canonical
Main update for that head.  This is objective-aligned experience routing, not
reward shaping.

The only preregistration candidate to be checked mechanically is
`beta_j = 0.25`; the failed carrier's effective 0.50 mix is retained only as a
descriptive comparator.  There will be no dose sweep.  If the fixed 0.25 donor
gradient fails the predeclared norm guard, this candidate stops rather than
being rescaled until it passes.

## Completed posthoc no-step gradient audit

The audit is archived as
`artifacts/smc-er-c1-authority-20260828/c1-posthoc-source-head-gradient-audit-v1.json`
with SHA-256
`bb34d440ffa0a8a1395cd3c41fe4d8953d96e687eb74397971a8a91392076cb2`.
Its fixed claim ceiling is
`POSTHOC_NO_STEP_GRADIENT_DIAGNOSTIC_ONLY_NOT_ROUTING_AUTHORITY_NOT_EFFICACY`.

The audit used 40 exact online Main/C1 bundle pairs per arm and excluded all 31
EXP-prefill bundles per arm.  It reconstructed byte-identical initial Main
online and target networks, applied reward calibration exactly once for all
480 arm/source/bundle/head combinations, constructed no optimizer, performed
no parameter step, and proved identical parameter bytes before and after.

| Arm/head | Mean Main gradient L2 | Mean C1 gradient L2 | Mean cosine | Negative-cosine pairs |
|---|---:|---:|---:|---:|
| informed Q1 | 1.8524 | 1.5867 | 0.6131 | 2/40 |
| informed Q2 | 1.0701 | 1.1195 | 0.4511 | 5/40 |
| informed Q3 | 0.5408 | 0.3878 | 0.4471 | 3/40 |
| neutral Q1 | 1.6683 | 0.5095 | 0.4423 | 1/40 |
| neutral Q2 | 1.1659 | 0.6971 | 0.3354 | 6/40 |
| neutral Q3 | 0.4720 | 0.2052 | 0.2537 | 12/40 |

At the fixed descriptive 75/25 mixture, the weighted C1 gradient norm is below
the weighted Main norm for every arm/head aggregate.  This closes only the
mechanical norm check.  It does not prove that a 25-percent dose improves EE or
that all-head opposition caused the sealed failure.  A first-order action-rank
claim was correctly left unsupported because the sealed method defines no
parameter-space step and a raw gradient does not uniquely specify the Adam
update.

Controller ruling after this audit: do not delete the learned C1/EXP/ACRM path
yet.  Advance **learned C1 plus canonical-Main-preserving Q1-only routing** to
implementation and reference-equivalence gates, while retaining direct-anchor
Q1-only routing as the preregistered fallback/control.  This is an engineering
authorization to implement and test the interface, not routing or efficacy
authorization.

## Required non-outcome gates before a new screen

1. **Static and gradient isolation:** the posthoc no-step audit is complete;
   the production updater must still perturb a C1 bundle and prove that only
   `Q_1^M` receives specialist-origin gradients; analogous tests apply to C2
   and C3.  Compute and receipt the withheld per-head losses under `no_grad`.
2. **Canonical replay preservation:** the exact batch sampled by the unchanged
   Main replay RNG must enter `L_MainReplay`; consuming and discarding that
   sample is a hard failure.
3. **Zero-dose parity:** all specialists in shadow must delegate exactly to the
   canonical Main update, including parameter, optimizer, replay, and RNG
   state.
4. **Role-targeted reference equivalence:** an independently implemented
   reference updater must match the production updater for all three roles,
   shortages, and atomic row weighting.
5. **Policy-retention diagnostic:** on common pre-outcome anchors and cloned
   physics RNG, compare learned C1, direct local-SNR, and masked-uniform actions.
   This development-only diagnostic asks whether EXP/ACRM retained the source
   advantage; it may not be presented as preregistered efficacy evidence.
6. **Document/hash closure:** revise the method and figure-arrow semantics only
   after the routing decision, then bind code, tests, specification, seed
   derivation, and prior-seed exclusion before any outcome seed is revealed.

## Minimal new developmental screen

If the non-outcome gates pass, freeze one new three-arm, four-episode screen:

- `Z`: zero C1 dose, canonical Main update;
- `N`: matched-uniform C1 under role-targeted routing; and
- `I`: informed EXP+ACRM C1 under role-targeted routing.

Use a new, mechanically derived training/environment/mobility seed tuple and
five new paired evaluation seeds disjoint from every checkpoint, source gate,
corpus, Gate 2, and prior efficacy-screen seed.  Require exact three-way initial
parity, identical update schedules and denominators, a single execution ledger,
and independent replay of all 15 evaluation points.

Developmental continuation requires all structural guards plus:

1. aggregate and mean-paired `EE_I - EE_N > 0`;
2. at least four of five `I-N` paired EE differences are positive;
3. `EE_I >= EE_Z` as a harm anchor;
4. served fraction is no more than 0.005 below either control; and
5. the receipt proves that C1 real TD loss entered only `Q_1^M`.

A pass grants only a longer matched pilot.  A fail moves C1 routing to
shadow-only/component-ablation status; thresholds, seeds, routing coefficients,
or admission logic must not be changed after outcome reveal to rescue the arm.

## Formal-training gate

Formal training is currently `NO-GO`.  It may be reconsidered only after:

- the architecture comparison is adjudicated;
- the selected routing implementation passes the non-outcome gates;
- the new sealed developmental screen passes;
- a longer matched multi-seed pilot passes its own preregistration; and
- a final independent code/spec/seed review confirms that the implementation
  matches the revised method.

The present result is useful precisely because it stopped an expensive formal
campaign before the unresolved consumer seam was scaled to C2 and C3.
