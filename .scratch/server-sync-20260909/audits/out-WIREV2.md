Completed the 22-anchor view-only rebuild.

- New corpus: [corpus](/home/sat/mcrl-v025-design-ws/artifacts/v025-stagec-c3-coalition-q1v2-20260910-BUILD_NOT_CLAIM/corpus)
- Report: [CORPUS-V2-WIRING-2026-09-10.md](/home/sat/mcrl-v025-design-ws/CORPUS-V2-WIRING-2026-09-10.md)
- Verification receipt: [BUILD_NOT_CLAIM-corpus-v2-verification.json](/home/sat/mcrl-v025-design-ws/artifacts/v025-stagec-c3-coalition-q1v2-20260910-BUILD_NOT_CLAIM/BUILD_NOT_CLAIM-corpus-v2-verification.json)
- Q1 digest: `66ed4a3f9222ac7f20f4334ffab92f6164d2dad203cbac7f7d4e1728ae4ad654`
- Reader: `PASS_WITH_IN_PROCESS_Q1_V2_REGISTRY_ADAPTER`; an independent re-open also passed.
- Rows: 21,532 C1/C2 and 4,552 C3.
- Shared C1/C2/C3 physics digest: `38e1998…30b55`.
- No physics rerun, learner training, or EE claim.
- Peak RSS: 614,445,056 bytes; one Python process, `nice=15`, BLAS threads pinned to one.
- Sealed builder, pilot, runner, and parent artifacts remained unchanged.

The raw matrix rank is 14. Measured effective dimension is 13 because this exact-path prefix has two documented constants: `missing_incumbent` and the pre-existing cap-saturated power ratio. Schema-defined effective dimension remains 14.

Two failed write-once attempts were preserved under `/tmp/v025-stagec-c3-coalition-q1v2-failed-{census,rank}`; no source or running-training data was touched.
