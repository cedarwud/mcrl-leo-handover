Built the C3 coalition extension successfully.

- 22-anchor prefix: `global-000`–`global-021`
- 4,552 coalition rows
- Sizes: `{2: 4236, 3: 155, 4: 82, 5: 35, 100: 44}`
- Joint evaluation: mean 4.614247 s/anchor
- Singleton Ψ: exactly zero for 17,132/17,132
- Exact decomposition residual: `0/1`
- Runner reader dry-run: `PASS`
- Peak RSS: 1,980,329,984 bytes
- All 44 JSONL sidecars verified
- No learner trained; no EE claim

The report documents the observed batch-surface default discrepancy and how stored `d_i` and fresh `ΔF(A)` were kept internally path-consistent.

Files:

- [Build report](/home/sat/mcrl-v025-coalgen-ws/C3-COALITION-BUILD-2026-09-10.md)
- [Verification manifest](/home/sat/mcrl-v025-coalgen-ws/artifacts/v025-stagec-c3-coalition-20260910-BUILD_NOT_CLAIM/BUILD_NOT_CLAIM-coalition-verification.json)
- [Combined reader-ready corpus](/home/sat/mcrl-v025-coalgen-ws/artifacts/v025-stagec-c3-coalition-20260910-BUILD_NOT_CLAIM/corpus)

Strict scope was maintained: only the owned output, report, and build scratch were added; sealed inputs and pilot bytes remained unchanged.
