# Multi-Catfish MCRL R6 document-set QA receipt

Date: 2026-08-30  
Scope: documentation consistency and implementation-contract synchronization  
Verdict: **PASS for authoring use; not scientific efficacy acceptance**

## Files reviewed

- `MULTI-CATFISH-ALGORITHM-DOCSET-R6-2026-08-30.md`
- `MULTI-CATFISH-PAPER-ALGORITHM-V0.5-2026-08-30.md`
- `MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.2-2026-08-30.md`
- `MULTI-CATFISH-NONRESULTS-PAPER-AUTHORING-CONTRACT-V0.2-2026-08-30.md`
- `C2-TEMPORAL-FORK-CANDIDATE-V0.3A-R6-2026-08-30.md`
- `THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.2-2026-08-30.md`
- `decisions/ADR-005-separate-r5-run-authority-from-r6-authoring.md`

## Verification results

1. **Active R5 run authority preserved.** The two R5 documents pinned by the R2
   authorities retain their expected SHA-256 values:

   ```text
   459bd93648b9e46fed27c1ede3b8b0482a34ea9682e395bae19731f13a06575d  docs/C2-TEMPORAL-FORK-CANDIDATE-V0.3-2026-08-29.md
   297bc1934dc995f98796813a326606ec0efa5858ece620ea59a5f11fc00d04aa  docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md
   ```

2. **Authority count synchronized.** The R2 `lr=0.001` authority contains 95
   pinned files; the R6 files use 95 rather than the superseded 79.
3. **C2 suite synchronized.** The C2 V0.3A suite collected 234 tests and the
   full run exited successfully. After adding the current-layout post-run and
   checkpoint-trajectory adapters, the trend/selector/post-run suite passes
   35/35 tests; the broader targeted set including the reused sweep and legacy
   trajectory verifiers passes 45/45 tests.
4. **Runtime semantics synchronized.** R6 distinguishes declared support
   rejection from fatal `C2BackendError`, records the 100-episode cadence, and
   names the actual cross-arm field `mechanism_environment_source_sha256`.
5. **Experiment route synchronized.** R6 records B000/F111/A011/A101/A110,
   public label `Full Multi-Catfish MCRL`, both candidate learning rates, the
   U=100 eligibility comparisons, 4.0% tie band, `0.001` tie preference,
   `STOP_BEFORE_3000`, and fresh-start 3000 requirement.
6. **Historical C2 isolated.** Activation-Churn content remains only in a
   visibly historical section. Current acceptance controls are `C2-CERT-R`,
   `C2-NF`, and `C2-I`.
7. **Markdown structure checked.** All fenced-code delimiters in the seven R6
   files are balanced. No active R6 statement retains `79-file` or `230 tests`.
8. **Independent read-only review.** The final review returned `PASS` with no
   BLOCKER or MAJOR contradiction across the seven files.
9. **Evaluation partition corrected.** A post-run pipeline audit found two
   inherited statements in the V0.5 technical document that said `TRAIN`.
   They now match the executable frozen evaluator: five fresh seeds on the
   canonical held-out `TEST` partition, Main-only masked-greedy evaluation,
   and ratio-of-sums EE. This is a documentation-contract correction, not a
   result or a change to either active matrix.
10. **Post-run closure tested.** For fresh matrices the new adapter independently
    reloads all 75 periodic and five final checkpoint payloads per LR and
    fail-closes on matrix, authority, arm, three-seed, LR/trainer, EP1500
    policy-equivalence, mechanism-source, telemetry, direct-reward, dose, CSV,
    125-cell sweep, arithmetic, and zero-power drift before LR selection. A
    legal treatment resume is endpoint-valid only after its source snapshot,
    segment clock, telemetry, and continuation checkpoint schedule validate;
    it is trajectory-ineligible.
11. **Fresh leakage/compatibility review closed.** The trajectory adapter now
    freshly revalidates both LR matrices and their complete receipts, recomputes
    the selector from the two validated sweep summaries, rejects input rebinding,
    and explicitly requires fresh complete 100--1500EP histories before any
    retrospective checkpoint evaluation.

## Time-stamped operational boundary

At `2026-08-30T08:44:53Z`, both R2 1500-episode matrices reported `running`
with B000 as their first active arm. This receipt does not call them complete.

## R6 file hashes

```text
86dfb9df7286c717dd1ab17b19300d87b6a8b811d963fbb49ebcf65cb67f8292  docs/MULTI-CATFISH-ALGORITHM-DOCSET-R6-2026-08-30.md
d7e61eed450e56b4d43cae546fe24c4ed82af13faa5248206e8807e0cc57f9c3  docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.5-2026-08-30.md
7dbd835f093de67a4f8bf77811c58bd18e1de8ca8309c3ab7dfe6803f1904463  docs/MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.2-2026-08-30.md
aeff958b7843612e66d681d157367200fcec4760b59ab39da98b14c8b5ee8547  docs/MULTI-CATFISH-NONRESULTS-PAPER-AUTHORING-CONTRACT-V0.2-2026-08-30.md
a857f3812ac34da94e24b36653a9b2cb3a6f5969b7903e3a6d499f2fcf6cca49  docs/C2-TEMPORAL-FORK-CANDIDATE-V0.3A-R6-2026-08-30.md
dc044e460e3a61bb1287a3fee725e60beea8202bc6aa4e9e4d5ccd3640720765  docs/THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.2-2026-08-30.md
532972758c8988ee5c560542a274e2d6c4e81e7c0b7d3adabbd94e2ef4926766  docs/decisions/ADR-005-separate-r5-run-authority-from-r6-authoring.md
```

These hashes identify the R6 authoring snapshot only. They are not a replacement
for either active R2 training authority and do not establish EE improvement,
algorithm efficacy, novelty, or Chapter 5 acceptance.
