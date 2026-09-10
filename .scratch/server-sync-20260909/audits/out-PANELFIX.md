I stopped before rebuilding because the requested v2 panel cannot pass the real scorer if only C3 changes.

Verified by running code:

- Original panel + real v1 epoch-500 checkpoint exits `2` with the reported C3 width error.
- Peak RSS: `523,587,584` bytes.
- Live directories were read-only; no evaluation-only dates were read.
- No EE was computed and no route claim was made.

Derived exactly from source:

- Q1-v1 width: 16.
- Q1-v2 width: 15, after removing two indicators and adding one elevation field.
- C3 member width is `2 × Q1 width + 6`: v1 `38`, v2 `36`.
- Full C3 width is  
  `1 + 2×member_width + 4×7 + (32×4+1) + 6`.
  Therefore:
  - v1: `1 + 76 + 28 + 129 + 6 = 240`
  - v2: `1 + 72 + 28 + 129 + 6 = 236`

This is exact. The ordered pairwise block remains fixed at 129 fields; the four-field reduction comes from the two member pools—sum and max—each losing two fields. See [coalitions.py](/home/sat/mcrl-v025-retrain-ws/src/mcrl/stagec_v025/coalitions.py:56) and [q1_schema_v2.py](/home/sat/mcrl-v025-design-ws/q1_schema_v2.py:73).

The required additional panel changes are:

- `panel-q1v2`: C1 state vectors must change from width 16 to the real checkpoint’s width 15. The scorer explicitly validates C1 vectors against checkpoint-derived widths at [score_stagec_checkpoints.py](/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py:318).
- Both rebuilt panels: `synthetic_smoke_not_evidence` must change from `true` to `false`; otherwise the scorer reports “SYNTHETIC SMOKE — NOT EVIDENCE,” not an accepted scoring result.

Width defect:

- 236: real Q1-v2 checkpoint, derived by the production encoder formula.
- 237: synthetic fixture and supplied panel; the builder truncated the six-field global suffix to three fields.
- 240: real Q1-v1 checkpoint and full production context.

There is no authoritative C3 schema-width constant enforced across producer and scorer. The builder reads widths from checkpoint weights and permits suffix truncation ([builder](/home/sat/mcrl-v025-witness-ws/scripts/build_stagec_scoring_panel.py:147)); its receipt merely labels 240 as `production_full_width`. The scorer likewise derives width from checkpoint weights and compares it with whatever vector length the panel contains—no declared C3 constant is consulted.

Smallest recurrence-prevention binding: define one authenticated C3 encoder contract keyed by the Q1 schema digest, declaring member width, pool layout, pairwise block, ordered global suffix, and resulting full width. Store its digest in both checkpoint and panel; require the builder to emit the complete declared vector and the scorer to compare contract digests before scoring.

Please authorize the minimal exceptions—Q1-v2 C1 re-encoding and flipping the two synthetic markers—so I can build and run the mandatory real-checkpoint acceptance scores.
