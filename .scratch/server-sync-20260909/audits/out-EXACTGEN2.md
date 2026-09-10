Completed EXACTGEN2.

- Reconciled rate: 60.978 s/anchor exact versus 0.920 s fallback, 66.26×. Ideal three-process projections: 30.49 minutes for 90 anchors and 60.98 minutes for 180.
- Generated 93 deadline-complete prefix anchors: all 90 world-1 anchors and world-2 anchors 0–2, totaling 90,938 rows.
- Maximum worker RSS: 1.824 GiB.
- C1 argmax disagreement: 57.9570%; C2: 49.4409%.
- C1 gauge, both decomposition residuals, and per-user attribution residual: exactly 0.0.
- All surrogate fields matched the sealed fallback rows for 90,938/90,938 rows.
- Runner and sealed-corpus hashes were identical before and after. The fallback flag was changed only on imported module objects in-process.
- The worker process finished an admitted batch 137.557 seconds after the deadline; those three late anchors were excluded and quarantined. The retained prefix completed at 21,271.574 seconds.

Outputs:

- [Required report](/home/sat/mcrl-v025-datepool-ws/EXACT-SOURCE-BUILD-2026-09-10.md)
- [Build manifest](/home/sat/mcrl-v025-datepool-ws/artifacts/v025-exact-source-20260910-BUILD_NOT_CLAIM/BUILD_NOT_CLAIM-manifest.json)
- [Verification results](/home/sat/mcrl-v025-datepool-ws/artifacts/v025-exact-source-20260910-BUILD_NOT_CLAIM/BUILD_NOT_CLAIM-verification.json)
- [Artifact directory](/home/sat/mcrl-v025-datepool-ws/artifacts/v025-exact-source-20260910-BUILD_NOT_CLAIM)
