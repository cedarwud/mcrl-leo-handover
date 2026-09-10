Implemented and verified.

- Required report: [SCORING-PANEL-2026-09-10.md](/home/sat/mcrl-v025-witness-ws/SCORING-PANEL-2026-09-10.md:1)
- Panel: [stagec-scoring-panel-first20-v1.json](/home/sat/mcrl-v025-witness-ws/artifacts/stagec-scoring-panel-first20-v1.json)
- Producer: [build_stagec_scoring_panel.py](/home/sat/mcrl-v025-witness-ws/scripts/build_stagec_scoring_panel.py:537)
- Construction receipt: [stagec-scoring-panel-first20-v1.receipt.json](/home/sat/mcrl-v025-witness-ws/artifacts/stagec-scoring-panel-first20-v1.receipt.json)
- Scorer log: [panelbuild-dry-run-score-final.log](/home/sat/mcrl-v025-witness-ws/.scratch/panelbuild-dry-run-score-final.log)

Final results:

- 20 anchors, global prefix 000–019
- 19,780 common-catalogue profiles
- First-improvement traversal explicitly recorded
- PANELCEIL reused for 12 anchors
- Exact source views used for 18 anchors; 147 missing reference actions regenerated with exact physics
- Panel SHA-256: `92d5a80ff018c066ec95507da0f63bf4be5fa6802b3d15fafb8247b069dd53fb`
- Real scorer verdict: **PASS**, exit 0; F6/F7/F8 rows `9/5/5`
- Producer peak RSS: `2,096,029,696` bytes
- Scorer peak RSS: `523,374,592` bytes

The nominated checkpoint is correctly marked as synthetic smoke—not EE evidence. Its C3 width is 237 versus the current production encoder’s 240; the missing authenticated C3 training-corpus issue is documented explicitly. No sealed or prohibited files were modified.
