C3 shards were not built: the existing physics contains only defaults and singleton evaluations—no real multi-user joint outcomes—so constructing `Psi_A` would require an invalid proxy.

The requested report is at [C3-COALITION-SHARDS-2026-09-10.md](/home/sat/mcrl-v025-datepool-ws/C3-COALITION-SHARDS-2026-09-10.md).

Key verified results:

- Authenticated prefix: 15/180 anchors, `global-000` through `global-014`.
- Configurations: 15 defaults, 13,225 singletons, 0 multi-user.
- Reader dry-run: `FAIL_CLOSED` with the expected missing-C3 error.
- Existing physics cost: mean 438.728 seconds and 3,534.667 boundary evaluations per anchor.
- Verification peak RSS: 148,410,368 bytes; generation receipts peaked at 1,930,498,048 bytes.
- Runner and pilot files remained byte-identical.
- No sealed or `EXACTGEN2`-owned artefact was modified. Only the report was created.
- No learner was trained and no EE claim is made.
