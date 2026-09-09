All three wait-loops have now expired on their own; nothing left to stop, and no work is outstanding.

**Final state of this task.** The v2 map was delivered in full as the report, followed by an erratum correcting two defects I found in my own bookkeeping when I re-counted the emitted labels: a duplicated decision ID (`D43` → Stage-1 UTC/frame item renumbered `D65`) and three wrong totals on the summary line. The authoritative final line is:

```
MAP: VERIFIED=44 REFUTED=37 DECIDED=61 OPEN=25 BLOCKING_MATRIX=7 BLOCKING_TRAINING=11
```

Everything was read-only with respect to `/home/sat/mcrl-hub-copy`; no project file was written. The one filesystem action beyond reading was `sha256sum` over the decision records, which is how Appendix C's sixteen unsealed-but-binding hashes were produced and how the eleven sidecar seals were re-verified (15/15 recorded hashes match).

Three things I'd flag as the map's load-bearing findings rather than its bookkeeping:

- **Stage C's report and its audit disagree outright** — `READY_FOR_REAUDIT` at 117/117 tests versus `NOT_READY, IMPLEMENTED=10/28, T1=T2=T3=FAIL` — and contract v1.1's sealed power/coverage table came from `_merge_calibration_receipts`, the very branch the audit rules out of contract and which accepted a receipt carrying `split="TEST"`. That is O31, and it is the highest-value item on the training side.
- **The claim-panel date arithmetic (O26) is new and was not in v1.** 166 TRAIN dates, six already consumed by successor development, six more seed-derived R2 domains coming, against a ≈160-date panel with a 150–170 validator range. I could not reconcile it from the sources, so it is marked OPEN rather than resolved in either direction.
- **The engine's correctness trajectory is genuinely sound** — 15 tautological KATs removed and replaced by 22 independent discriminators at 4d, provider at 46/50 with rewritten oracles. What blocks the matrix is compute (24.66 s against a 10 s budget) and the fact that no formal artefact has ever been run, not physics faithfulness.

One caveat worth stating plainly: the code tree is not present in the hub snapshot, so every `file:line` citation in the map is reproduced from the audits rather than verified against source by me.
