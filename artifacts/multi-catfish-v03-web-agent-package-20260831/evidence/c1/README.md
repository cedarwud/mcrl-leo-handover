# C1 canonical authority byte archive — 2026-08-28

This directory is a byte-for-byte durability copy of the `/tmp` authority used
to close the C1 Source Gate, corpus, and pre-transfer Gate 2 before the
post-gate four-episode developmental efficacy-screen freeze.

The live receipts retain their original absolute `/tmp` paths and must not be
silently rebound to these copies.  If the live files are lost, restore these
bytes to the exact original paths and rerun all independent validators before
continuing.  `verification-v2.json` is the current Source Gate verification;
the sibling `verification.json` is historical and superseded.

## Frozen hashes

```text
25463681f598f62f1486b5889ab1192c2192c97fb83565c609419f7cc77f6774  smc-er-c1-source-gate-a-canonical-tle-20260828-v3/c1-source-gate-a-result.json
94bca141f556fffa560ebda76cad287870217f1512f74ff8880d4a400890ace4  smc-er-c1-source-gate-a-canonical-tle-20260828-v3/receipt.json
fe5397c06973d4c3c04fffd59bde03110131dd04fe26aa1af3e432a26c6fa381  smc-er-c1-source-gate-a-canonical-tle-20260828-v3/verification-v2.json
6f0abd73a0eb43e64e9f7235e71e5a39f7ee0ef11de7211ed6db60790951f5e6  smc-er-c1-source-gate-a-canonical-tle-20260828-v3/verification.json
fc11614b32794ffde2e1954ff4a78fc7de4ed307c2e602eb4973f0121bd11616  smc-er-c1-exp-corpus-canonical-tle-20260828-v3/c1-exp-corpus-manifest.json
3f4b8b09a65f7867309a9f5cdb3dedcffba103caac0da16b062642565448905b  smc-er-c1-exp-corpus-canonical-tle-20260828-v3/c1-exp-corpus.npz
8c6e951ecf7c40abe066c1e40b725a5fca39648694c7b89a25af1a67c8dd645f  smc-er-c1-exp-corpus-canonical-tle-20260828-v3/verification.json
e3749736fcc61a7026072a5010b70b10eece319a75e16e1566f00c00aa86e6d3  smc-er-c1-pretransfer-gate2-canonical-tle-20260828-v4/c1-pretransfer-consumer-gate-raw.json
f69459ddfc8b968c08f2b7bea51a55311de640b1b66852875619f4a187e8d402  smc-er-c1-pretransfer-gate2-canonical-tle-20260828-v4/c1-pretransfer-consumer-gate-result.json
38917d35343a1d7fa637b6ad78711837c6e6c15f375e6c1e33c59f10126658a3  smc-er-c1-pretransfer-gate2-canonical-tle-20260828-v4/verification.json
b92e53c9396f3789bb043b28aec496f23893c63a44aa0a049d239378341c07a3  c1-canonical-tle-corrective-replay-verification-v1.json
```

Repository-side seed-provenance correction:

```text
540039bdf06ce3448b63ff58e1e665b5843a68ebdffc768f2f3ce4c5270b294f  .scratch/smc-er-short-ep/C1-SOURCE-GATE-A-SEED-PROVENANCE-CORRECTION-V1-2026-08-28.json
```

## Post-gate developmental screen

The single frozen campaign was executed once.  Its independently replayed
decision is `STOP_AND_REDESIGN_C1`, under the strict ceiling
`ONE_SEED_4EP_DIRECTIONAL_SCREEN_NOT_ROUTING_AUTHORITY_NOT_CHAPTER5`.
This is not a formal efficacy result and does not authorise C1, C2, or C3
routing in a later campaign.

```text
1e406f1b3be13a972bfab92b04dde7d24402140c2540821b509e0dcc094e6bc3  smc-er-c1-postgate-efficacy-freeze-20260828-v1/c1-efficacy-microscreen-closure-v1.json
7eef5b4220cd09f56ed018f78833138fae10db75ffbfa6f32d3c83fb0414aac8  smc-er-c1-postgate-efficacy-freeze-20260828-v1/c1-efficacy-microscreen-seeds-v1.json
728912edf04bc8cee74332f6e05745b60a40aa0955e58eb4fe1765b2136e8992  smc-er-c1-postgate-efficacy-screen-20260828-v1/c1-postgate-efficacy-microscreen-raw.json
7130ec2ffa4127ecc998fbd3a1bdf5508491639747f146296faf36e2ad408e81  smc-er-c1-postgate-efficacy-screen-20260828-v1/c1-postgate-efficacy-microscreen-result.json
84b318e78ae8be3bf0d639a2f6f7f8222a2328aa8a24acfa4a7f689063210184  smc-er-c1-postgate-efficacy-screen-20260828-v1/independent-verification.json
```

The `smc-er-c1-posthoc-initial-baseline-same-eval-seeds-20260828-v1`
directory is explicitly post-outcome diagnostic evidence.  It was not part of
the frozen decision rule and must never be represented as a preregistered arm.

## Posthoc source/head gradient diagnostic

The following deterministic result uses the already sealed carrier bundles,
constructs no optimizer, applies no optimizer step, and leaves all Main
parameter bytes unchanged:

```text
bb34d440ffa0a8a1395cd3c41fe4d8953d96e687eb74397971a8a91392076cb2  c1-posthoc-source-head-gradient-audit-v1.json
```

Its claim ceiling is
`POSTHOC_NO_STEP_GRADIENT_DIAGNOSTIC_ONLY_NOT_ROUTING_AUTHORITY_NOT_EFFICACY`.
It is a redesign diagnostic only.  It cannot select a dose, authorize routing,
rescind the sealed `STOP_AND_REDESIGN_C1`, or be reported as Chapter 5
efficacy evidence.
