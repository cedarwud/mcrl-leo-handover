# Package manifest

Snapshot date: 2026-09-02  
Package status: `REVIEW_INPUT__OPS3_SELECTED_FOR_FORMULA_PROBE__NO_C2_ACCEPTED`  
Purpose: independent C2 formula/design adjudication; no training authorization

## Entry files

| File | Role |
|---|---|
| `START-HERE.md` | Scope, frozen boundaries, verified status, candidates, and reading order |
| `CURRENT-C2-DIAGNOSIS.md` | Compact supersession-aware diagnosis and exact unresolved questions |
| `CHATGPT-REVIEW-PROMPT.md` | Prompt to paste after uploading the archive |
| `EVIDENCE-MAP.md` | Claim-to-document/source index |
| `IMPLEMENTATION-SEAM-AUDIT.md` | Read-only map of reusable OPS-3 physics seams and implementation traps |
| `SOURCE-PATH-MAP.md` | Original-to-package path translation |
| `MANIFEST.sha256` | Integrity hashes for all other packaged files |

## Directory roles

| Directory | Contents | Authority level |
|---|---|---|
| `docs/` | Current authority, preregistrations, result summaries, failure analyses, Fable review, OPS-3 review and frozen formula-probe contract | Mixed; top supersession plus later sealed evidence overrides older prose |
| `evidence/` | Copied JSON receipts for route interaction and C2 V0.4/V0.5/V0.6/V0.7 findings | Primary numerical/mechanical evidence within this package |
| `source/env/` | Simulator physics and action/service semantics | Primary implementation snapshot |
| `source/runtime/` | EE targets, state/source generators, gates, and retired C2 implementations | Primary implementation snapshot; presence does not imply a live method |
| `source/algorithms/` | Shared and retired learner/deployment implementations | Primary implementation snapshot |
| `source/runners/` | Evaluation/adaptor excerpts used to interpret receipts | Supporting evidence; package is not a runnable repository |

## Important interpretation rules

- OPS-3 is selected for formula implementation and a bounded no-training oracle
  probe only; it is not an accepted C2.
- Fable option value is the reserved alternative, not a concurrent live route.
- The earlier projected-shaping draft is retained as design lineage, not a third
  accepted candidate.
- V0.5, V0.6, and V0.7 source files are deliberately included as negative
  evidence; none is the current C2.
- C1/C3 evidence is included because a replacement Q2 must preserve all three
  `FULL > DROP-Cj` marginals in the same policy context.
- The package is sufficient for design review and formula-probe specification,
  not for executing the simulator or reproducing training from scratch.
