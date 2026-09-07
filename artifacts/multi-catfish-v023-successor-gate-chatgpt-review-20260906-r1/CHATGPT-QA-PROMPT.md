# GPT-6 Astra Pro/ChatGPT QA adjudication prompt

## Goal

Act as an independent senior scientific-methods, reinforcement-learning, and
wireless-systems reviewer. Adjudicate whether the project should continue the
frozen LC-SRS line through one new prospective TRAIN gate, promote a CSE/EC
contingency, or stop and redesign C3 after the one-shot V0.23 R6 gate. Return
one evidence-grounded decision, not a plan to execute it.

## Context and authority

Read `START-HERE.md` first, then `CURRENT-STATUS.md`, `CLAIM-CEILING.md`,
`EVIDENCE-MAP.md`, and `SOURCE-PATH-MAP.md`. Inspect the copied authority and
implementation files named there. Use the current frozen method and gate
contract as the controlling project design; use the R6 and Astra facts in
`CURRENT-STATUS.md` only with their stated provenance. If an optional late
direct result or review file is present, prefer it for that claim and say so.
Do not turn absence of a file into a negative result.

The fixed LC-SRS method is a two-user current-slot four-profile teacher
(`00`, `10`, `01`, `11`) with

\[
z_{3,i}=e_i+\Psi/2,
\qquad \sum_i(\ell_i+z_{3,i})=G(11)-G(00).
\]

The privileged physical profiles and labels stay in training. Deployment has
one deterministic predecision relational `C3View`, one scalar Q3 surface,
one common native safe mask, and one literal masked argmax of
`Q1 + Q2 + Q3`. There is no coordinator, auction, joint decoder, iterative
allocation, fallback, or post-selection repair. C1 and C2 remain separate
diagnostic routes; deployment efficacy is not established by this package.

The current R6 handoff facts are:

| Quantity | Value |
|---|---:|
| Informed Spearman | `0.8367467202782021` |
| Informed raw sign accuracy | `0.8293051359516616` |
| Matched-placebo raw sign accuracy | `0.7915407854984894` |
| Frozen raw gap | `0.03776435045317217` |
| Frozen required gap | `0.05` |
| Positive / negative sign-labelled rows | `1038 / 286` (`78.4%` positive) |

The frozen raw predicate therefore fails. Development-only balanced
accuracies by the three fixed seeds were informed
`[0.6076, 0.7227, 0.7047]` and matched placebo
`[0.5584, 0.5970, 0.5807]`. These are imbalance diagnostics, not a license
to rescue R6 or select a new metric after seeing outcomes.

The handoff also reports a separate R6 composition replay-digest/runtime
environment defect; full R6 was stopped and evidence retained. The first
C1/C2 target-generation attempt failed before physics because
`_network_snapshot` was referenced at the wrong module level; a tested
correction/relaunch is in progress. The copied five-arm runner is an
admission/receipt skeleton requiring an injected real adapter, not a complete
physical execution path. A fresh Astra Ultra read-only direction was
`CONTINUE_LCSRS_FRESH_GATE`: retain LC-SRS, do not auto-promote CSE/EC, and
consider one prospective fresh TRAIN gate with a pre-registered balanced-sign
estimand while retaining raw accuracy and all physical/composition/service
requirements. There is no second metric revision if that gate fails. Treat
that direction as a handoff input to audit, not as an authority verdict.

## Success criteria

Your review is successful only if it does all of the following:

1. Gives a direct adjudication of scientific legitimacy: what the R6 raw
   failure does and does not establish; whether the class imbalance makes a
   balanced-sign estimand a legitimate *prospective* complement; and why this
   cannot change the frozen R6 decision.
2. Gives a direct adjudication of integration readiness: separate the frozen
   method, gate/receipt plumbing, target-generation correction, composition
   runtime defect, and absent real five-arm adapter execution. Identify what
   is ready for review, what is only a seam, and what blocks a new contract.
3. Audits process flaws, including digest-domain binding, the wrong-module
   `_network_snapshot` failure, evidence retention, metric shopping risk,
   development-versus-efficacy language, and the Fable CSE “joint exact”
   overclaim. Distinguish an execution defect, a design limitation, and a
   scientific failure.
4. Specifies exactly one next contract if work should continue: estimand(s),
   arm/comparator set, unopened TRAIN worlds and lineage/seed pairing, raw and
   balanced reporting, physical/composition/service predicates, provenance
   bindings, preregistration requirements, compute class, and hard stop. If
   you choose a different terminal direction, state the exact reason and
   minimum contract it would require.
5. Selects one and only one final token from the required set below. Do not
   default to the supplied Astra direction without checking the copied files.

## Required audit questions

### A. R6 result and metric legitimacy

Check the arithmetic and the frozen threshold. Explain why a 78.4% positive
label mix can make raw sign accuracy optimistic, but also why the supplied
balanced values are development-only and cannot be substituted retroactively.
Assess whether a future balanced-sign estimand could be frozen before a fresh
outcome, with raw sign accuracy still reported and no second metric revision.
Require an explicit definition of the balanced estimand, denominators,
zero/unsupported-row handling, cluster/world aggregation, and the rule that
the final decision cannot switch between raw and balanced metrics after
outcomes open.

### B. Scientific and integration boundary

Read `authority/LC-SRS-GATE-CONTRACT.md` and `authority/METHOD-FREEZE.md`.
Check the exact LC-SRS identity, predecision-state boundary, matched-placebo
logic, leave-one-world-out structure, literal one-pass composition, service
guard, and no-rescue rules. Explain which evidence would be needed to call a
future result observable, learnable, composable, or efficacious. Do not call a
fit association, oracle sign, mechanics test, checksum, or runner receipt an
EE result.

Read `fast-screen/compute_fit_screen.py` and static-inspect its metric
definition and frozen threshold. Read the files in `five-arm/` and state why
the injected-adapter seam is not a completed real five-arm run. Do not execute
the files or the simulator.

### C. Candidate and CSE adjudication

Use `authority/CONTINGENCY-LADDER.md` to reconstruct the locked order: LC-SRS
first, CSE second, EC third. Use all three Fable files, especially
`authority/ROOT-FABLE-C3-ADJUDICATION.md`, to decide whether a same-configuration
cost-conservation identity proves anything about a sum of separately evaluated
unilateral counterfactuals. Do not call CSE or EC promoted merely because a
formula is simple or physically plausible. If you recommend a candidate,
state its exact pre-outcome formula/units and falsifier; do not invent an
unbounded candidate family or a post-outcome hybrid.

### D. Decision discipline

Compare these four dispositions:

- `CONTINUE_LCSRS_FRESH_GATE`: retain LC-SRS and freeze one new prospective
  TRAIN gate with raw plus a predeclared balanced-sign estimand, retaining
  physical/composition/service requirements and forbidding a second metric
  revision;
- `PROMOTE_CSE_FAST_ROUTE`: promote CSE only if the package actually supports
  a scientifically valid, pre-outcome promotion, not by assertion;
- `PROMOTE_EC_FAST_ROUTE`: same standard for EC;
- `STOP_AND_REDESIGN_C3`: stop the LC-SRS route and require a new C3 contract
  because the evidence supports redesign rather than another bounded gate.

If selecting the first token, do not prescribe episode-policy training. A
simulator or multi-world rollout projected above about 30 minutes is **heavy**
and belongs on the Ubuntu server under a new authorization; a read-only
contract review is **non-heavy**. State this classification in the next
contract section.

## Evidence labels and response format

Tag each material statement as one of `[COPIED-AUTHORITY]`, `[HANDOFF-VERIFIED]`,
`[ABSENT-AT-CHECK]`, `[INFERENCE]`, or `[PROPOSAL]`. Cite package-relative
paths (and section names or line numbers when available). Keep verified facts,
inferences, launch/running state, and scientific/controller acceptance
separate.

Return 1,800–2,600 words in this structure:

1. Executive adjudication
2. R6 arithmetic, metric legitimacy, and claim boundary
3. Scientific legitimacy of LC-SRS and integration-readiness audit
4. Process-flaw and evidence-provenance audit
5. LC-SRS versus CSE versus EC disposition
6. One exact next contract (or exact redesign/stop contract)
7. Risks, falsifiers, and remaining claim ceiling
8. Final decision

Do not run training, simulation, a rollout, TEST, or any project command. Do
not edit, rename, delete, or generate files. Do not tune any R6 threshold,
sign rule, seed, horizon, formula, scale, or candidate after outcome. Do not
make claims beyond the package evidence.

The final line must contain exactly one token from this set, with no code
fence, punctuation, explanation, or text after it:

`CONTINUE_LCSRS_FRESH_GATE`

`PROMOTE_CSE_FAST_ROUTE`

`PROMOTE_EC_FAST_ROUTE`

`STOP_AND_REDESIGN_C3`
