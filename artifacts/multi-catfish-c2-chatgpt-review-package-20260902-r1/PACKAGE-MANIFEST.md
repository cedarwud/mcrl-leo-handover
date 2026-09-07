# Package manifest

Snapshot date: 2026-09-02  
Package status: REVIEW_INPUT__NO_C2_SELECTED__FABLE_STAGE1B_INTEGRATED  
Compute class: non-heavy, read-only review  
Purpose: independent C2/C3 method adjudication; no training authorization

## Entry files

| File | Role |
|---|---|
| START-HERE.md | Integrated state, claim ceiling, candidates, and reading order |
| CHATGPT-REVIEW-PROMPT.md | Standalone package-evidence adjudication prompt |
| CHATGPT-DEEP-RESEARCH-PROMPT.md | Independent primary-literature and theory challenge prompt |
| INTEGRATION-VERIFICATION.md | Receipt, number, and exact-OPS-3 discrepancy audit |
| EVIDENCE-MAP.md | Claim-to-document/source index |
| SOURCE-PATH-MAP.md | Original-to-package path translation |
| MANIFEST.sha256 | Integrity hashes for every other packaged file |

## Directory roles

| Directory | Contents | Evidence level |
|---|---|---|
| docs/ | Current/historical contracts, reviews, results, failure analyses, exact OPS-3 contract and checkpoints | Mixed; no challenger authority patch applied |
| evidence/ | Older receipts plus H-A, Fable OPS-3-reading, and census JSON | Primary machine-readable development evidence |
| fable-cleanroom-lane/ | Challenger decision, contracts, reports, audits, runner, census scripts, and preserved original receipt manifest | Development evidence, not authority |
| source/env/ | Simulator physics and action/service snapshot | Primary implementation snapshot |
| source/runtime/ | EE routes plus exact current OPS-3 formula/live adapter | Primary implementation snapshot |
| source/algorithms/ | Shared and retired learner/deployment implementations | Primary implementation snapshot |
| source/runners/ | Older evaluation/adapter excerpts | Supporting snapshot |
| source/tests/ | Exact OPS-3 formula/live-adapter mechanics tests | Mechanics evidence only |
| verification/ | Independent Stage 1b raw-row recomputation script | Package verification |

## Integrated interpretation

- H-A and the Fable lane's OPS-3 reading both show a positive C2 marginal on
  six TRAIN-development worlds, but both receive C3_CONTEXT_FAIL and fail the
  overall service guard.
- The Fable O-arm is not the current exact OPS-3 result. Exact OPS-3 has
  mechanics-test evidence only; its declared outcome worlds remain unopened.
- The Fable option-value proposal remains unrun.
- No C2 is selected, no Q2 learner is authorized, and no held-out or Chapter 5
  efficacy claim exists.
- The two prompts use the same package but must run in independent fresh
  contexts; their replies are merged only after both finish.
- The package is sufficient for method/formula adjudication, not for executing
  the simulator or reproducing training from scratch.

## Integrity rule

MANIFEST.sha256 is the sole package-wide manifest and excludes itself. The
preserved fable-cleanroom-lane/RECEIPT-DIR-MANIFEST.sha256 authenticates the
larger original challenger artifact and is evidence, not a second package
manifest.
