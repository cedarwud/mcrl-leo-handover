Completed and verified both development scoring panels.

- [Full report](</home/sat/mcrl-v025-panelfix-ws/SCORING-PANEL-FIX-2026-09-10.md>)
- [panel-q1v1.json](</home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v1.json>) — C3 240, SHA-256 `dc5df10b17250f298ab7bbaa2a099c895204a83f3b2f8d2c93ef73cc94e50134`
- [panel-q1v2.json](</home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v2.json>) — C3 236, SHA-256 `b5a2c365a1c1936399530dd98e509a464a56d88bb9857f03d611c3fde3643638`

Both real-scorer acceptance runs exited `0`:

| Panel | Real checkpoint | Seed / epoch | F6/F7/F8 | Peak RSS |
|---|---|---|---|---:|
| q1v1 | production v1 | `6407676579069309528` / 500 | 9 / 5 / 5 | 526,446,592 B |
| q1v2 | schema v2 | `6407676579069309528` / 500 | 9 / 5 / 5 | 521,703,424 B |

Verified outcomes:

- The 240→236 derivation is exact: Q1 width 16→15 makes member width `2×Q1+6`, or 38→36; sum/max pooling duplicates that two-field reduction, producing C3 240→236.
- All physical panel content was authenticated as exact physics on real development anchors. No fixture value survives, so `synthetic_smoke_not_evidence` is correctly `false`. The report precisely limits what that flag now asserts.
- Outcomes and pooled fixed-point/anytime quantities are unchanged. Only the authorized schema encodings differ.
- The builder now fails closed instead of truncating. The historical 237-width fixture was rejected with an explicit width error.
- No authoritative shared C3-width declaration currently exists. The scorer derives the expected width from the checkpoint matrix and compares it with whatever vectors the panel contains.
- The report specifies—but does not implement—the requested authenticated, schema-digest-keyed encoder contract.
- No evaluation-only dates were read, and nothing was written into either live training directory.

The debugging workflow materially produced the failing regression case that proves silent truncation is gone; scope controls kept changes confined to the local builder, verifier, panels, receipts, and report. This work computes no separate EE and makes no route claim.
