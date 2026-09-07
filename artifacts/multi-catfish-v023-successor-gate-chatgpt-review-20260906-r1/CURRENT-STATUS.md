# Current status — V0.23 LC-SRS successor-gate review

Status date: 2026-09-06 (Asia/Taipei)  
Package directory: `artifacts/multi-catfish-v023-successor-gate-chatgpt-review-20260906-r1/`

## Provenance legend

Every statement in this file is labelled by its evidence boundary:

- **COPIED-AUTHORITY** — a regular-file copy of a repository document or
  script. The original path is in `SOURCE-PATH-MAP.md`; content integrity is
  in `MANIFEST.sha256`.
- **HANDOFF-VERIFIED** — a current fact supplied by the root agent at package
  assembly. It is preserved as a fact for adjudication, but the named late
  result/review file was not present at the initial package check. If a late
  file is added before sealing, that file becomes the direct evidence and is
  listed in the map and manifest.
- **INFERENCE / CAUTION** — an interpretation that a reviewer may test; it is
  not an additional result.
- **ABSENT-AT-CHECK** — a requested late artifact was not present when the
  package was first checked. This is not evidence that the underlying run or
  review did not happen.

## Frozen method and gate

**COPIED-AUTHORITY:** `authority/METHOD-FREEZE.md` freezes the Chapter-4
LC-SRS method core and explicitly leaves learnability, composition benefit,
C1/C2 qualification, FULL-over-ablation ordering, and EE efficacy open. Its
own execution boundary is `NO-GO`.

**COPIED-AUTHORITY:** `authority/LC-SRS-GATE-CONTRACT.md` freezes the bounded
TRAIN-development observability/source-to-learner question, eight ordered
TRAIN worlds (`2026121705`–`2026121712`), three student seeds
(`2026135101`–`2026135103`), 32 common-field draws, the raw informed-versus-
matched-placebo learner predicates, physical/composition/service predicates,
and the no-rescue rules. It does not authorize episode training or TEST.

**COPIED-AUTHORITY:** `authority/R6-RELAUNCH-DECISION.md` records the
pre-launch R6 correction to the fit-receipt digest domain and the conditional
fresh-server preparation boundary. It is a preparation/launch decision, not
an efficacy result; the newer R6 outcome below is labelled separately.

## R6 raw gate outcome

**HANDOFF-VERIFIED:** The root agent reports that R6 remains failed under the
frozen raw informed-minus-placebo sign-accuracy predicate. The supplied exact
values are:

| Quantity | Value | Interpretation |
|---|---:|---|
| Informed Spearman | `0.8367467202782021` | Reported learner association; not efficacy |
| Informed raw sign accuracy | `0.8293051359516616` | Frozen raw sign component |
| Matched-placebo raw sign accuracy | `0.7915407854984894` | Same raw sign component for placebo |
| Informed minus placebo raw gap | `0.03776435045317217` | `0.8293051359516616 - 0.7915407854984894` |
| Frozen required gap | `0.05` | Not reached; raw predicate fails |
| Positive sign-labelled rows | `1038` | `78.4%` of `1324` rows |
| Negative sign-labelled rows | `286` | `21.6%` of `1324` rows |

The values above are not a claim that R6 had a valid final result seal, a
passed physical gate, a passed composition gate, or learned EE efficacy. A
reviewer must not replace the failed raw predicate with a post-hoc metric.

**HANDOFF-VERIFIED:** Development-only balanced accuracies by seed were
reported as follows. The order is the three fixed student seeds; the values
are descriptive development diagnostics, not the frozen R6 decision:

| Arm | Development-only balanced accuracy by seed |
|---|---|
| Informed | `[0.6076, 0.7227, 0.7047]` |
| Matched placebo | `[0.5584, 0.5970, 0.5807]` |

**INFERENCE / CAUTION:** The class distribution and these descriptive values
can motivate asking whether one prospective balanced-sign estimand should be
pre-registered before a new gate. They cannot retroactively rescue R6, alter
the frozen threshold, or justify selecting the metric after opening a new
outcome.

## Separate execution defects

**HANDOFF-VERIFIED:** R6 also had a separate composition replay-digest/runtime
environment defect. The root stopped the full R6 execution and retained the
evidence. Repairing that defect can establish or invalidate execution
integrity for a replay, but cannot reverse the already reported raw
informed-minus-placebo gap below `0.05`.

**INFERENCE / CAUTION:** Adjudicate scientific predicate failure and
execution/replay failure as two distinct axes. A green repair check is not a
scientific pass; a raw scientific failure is not erased by a runtime repair.

## C1/C2 target-generation state

**HANDOFF-VERIFIED:** The first C1/C2 target-generation attempt failed before
physics because `_network_snapshot` was referenced at the wrong module level.
A tested correction/relaunch is in progress. This is a process/launch state,
not a C1/C2 scientific negative result and not authorization to run here.

The copied five-arm and observability documents remain the review surface;
they do not certify that the correction has completed.

## Five-arm execution seam

**COPIED-AUTHORITY / HANDOFF-VERIFIED:** The current five-arm runner in
`five-arm/v023_real_five_arm_episode_runner.py` is an admission/receipt seam
that expects an injected real execution adapter/callback. Its companion
README and spec explicitly state that no default invocation runs a simulator
and that a complete real execution path still requires separately admitted
artifacts and a real environment/TLE adapter. It is therefore not evidence of
completed five-arm execution.

## Independent Astra Ultra direction

**HANDOFF-VERIFIED:** A fresh Astra Ultra read-only adjudication concluded
`CONTINUE_LCSRS_FRESH_GATE`: retain LC-SRS as the candidate; do not
auto-promote CSE or EC. It allowed one prospective fresh TRAIN gate to
pre-register a balanced-sign estimand while reporting raw accuracy and
retaining physical, composition, and service requirements. If that gate fails,
there is no second metric revision.

**HANDOFF-VERIFIED:** Astra also cautioned that Fable's CSE “joint exact”
claim may overextend a within-configuration cost-conservation identity to a
sum of separately evaluated unilateral counterfactuals. The copied
`authority/ROOT-FABLE-C3-ADJUDICATION.md` contains the explicit algebraic
counterexample and must be treated as a scope warning, not as an automatic
CSE promotion.

## Late-artifact check

**ABSENT-AT-CHECK:** At initial package assembly, these requested late files
were not present:

- `evidence/R6-FIT-SCREEN-VERIFIED.json`
- `reviews/ASTRA-ULTRA-PROCESS-ADJUDICATION.md`

The package assembly performs one final read-only recheck before manifest
sealing. If either file arrives, it is copied as a regular file, its direct
provenance replaces the corresponding handoff-only status, and it is added to
`EVIDENCE-MAP.md`, `SOURCE-PATH-MAP.md`, `PACKAGE-MANIFEST.md`, and
`MANIFEST.sha256`.

## Claim ceiling

No statement above establishes C1/C2/C3 efficacy, a positive full-policy
marginal, a successful five-arm physical run, deployment readiness, or a
scientific promotion of CSE/EC. The only proposed next direction is a fresh,
prospectively contracted TRAIN gate with no metric revision after failure.
