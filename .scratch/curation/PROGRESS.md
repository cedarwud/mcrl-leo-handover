# CURATE — progress

Task: RESULTS-REGISTRY.md, DOCUMENT-STATUS.md, curation/PROVENANCE-HEADER.md. Read-mostly; create new index files only.

| step | status | note |
|---|---|---|
| 0. inventory `.scratch/` + v025 dir | done 2026-09-11 | 222 files in v025 dir; ~120 dated 09-10/09-11 |
| 1. read errata 17-28 + 09-11 rulings | done | all 09-11 controller docs read |
| 2. read remaining 09-10/09-11 controller docs | done | all ~110 docs dated 09-10/09-11 read (batches in session scratchpad b4..b16.txt) |
| 3. read report dirs (feasible-frontier, catfish-surface, beam-power-accounting, b0-corrected, penalty-arm, cap-penalty, ee-magnitude, zclose, zscore-transfer, ...) | done | read myself: ee-magnitude, feasible-frontier, beam-power-accounting, b0-corrected (+PROGRESS R6 pin b924c8a0), penalty-arm, cap-penalty. Forked (outputs to session scratchpad rows-A/B/C.md): A = acrm/dqfd/catfish-facts/reward-history/lfd/deep-research/reviews/thesis-deltas/design-state; B = catfish-surface/zclose/zscore-transfer/concept-harvest/catfish-screens; C = V0.25 server reports over read-only ssh |
| 4. write RESULTS-REGISTRY.md | done | `.scratch/RESULTS-REGISTRY.md` (503 rows) |
| 5. write DOCUMENT-STATUS.md | done | new doc appeared mid-task: `V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md` (16:58 local) — read, IN FORCE, top of list; CF3PILOT agent running in `.scratch/cf3-pilot/` |
| 6. write PROVENANCE-HEADER.md | done | `.scratch/curation/PROVENANCE-HEADER.md` |

## Resume after usage limit (2026-09-11 ~11:10 UTC)

- rows-A.md (170 rows), rows-B.md (143 rows), rows-C.md (129 rows) all exist in the scratchpad with all
  three sections (rows / comparisons / directory status) — COMPLETE despite A and C agents reporting failure
  (they had finished writing before the limit). No re-fork needed; no new agents spawned.
- Incorporate: TLE pin file_set `427e6a91…8fe9` (b924c8a0); local unpinned `e07f3e1e…` used by
  catfish-surface / FEASFRONT / CFSCREEN / anchor-ablation / POWERACCT / EEGAP bridge. NOT-COMPARABLE groups.
- Next: step 4 (write RESULTS-REGISTRY.md), then finish DOCUMENT-STATUS.md (draft already written).
- ~11:20 UTC: read all of rows-A/B/C. Writing my own rows (FF/BP/B0/PA/CP/EM/CT/PI) to scratchpad
  `rows-D.md`, then assembling RESULTS-REGISTRY.md with scratchpad `assemble.py` (host normalisation,
  sibling rows split into their own section, V025 power-accounting label fix for fork-B rows).

## Sub-agents spawned by CURATE (all `fork`, read-only, launched ~09:00 UTC 2026-09-11)

All three write only to this session's scratchpad
`/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/e9fba164-4724-465f-8afa-7891b4efee90/scratchpad/`.
Their results ARE still needed (they feed RESULTS-REGISTRY.md rows and the comparison list).
If interrupted: resume with SendMessage to the agent id; if not resumable, re-run the same slice and
check whether its output file already exists first.

| agent id | covers | writes | still needed? |
|---|---|---|---|
| `a4644bab74d559124` | registry rows A: acrm-provenance, dqfd-grounding, catfish-facts, reward-history, lfd-family-screen, deep-research, reviews, thesis-deltas, design-state | `scratchpad/rows-A.md` | no — consumed |
| `a35d4634cf4c5439e` | registry rows B: catfish-surface, zclose, zscore-transfer, concept-harvest, catfish-screens | `scratchpad/rows-B.md` | no — consumed |
| `a360dd6a762afdefe` | registry rows C: V0.25 server reports cited by 09-10/09-11 controller docs (read-only ssh sat) | `scratchpad/rows-C.md` | no — consumed |
- ~11:40 UTC: step 4 DONE — `.scratch/RESULTS-REGISTRY.md` written by scratchpad `assemble.py`
  (503 rows: 442 this project + 61 sibling reference-only; 30 in-force cross-condition comparisons in §4a).
  Incorporated coordinator facts: TLE pin 427e6a91 vs unpinned e07f3e1e (NOT-COMPARABLE groups §1a/§1b);
  CFSCREEN "only episode 0 paired" (paired stats CS-33 / B0-12 marked INVALID-AS-PAIRED); `A m=2dB` reads
  the incumbent. New docs read: AMENDMENT-1-THREE-CATFISH-PILOT, RECORD-CATFISH-SCREENS; B0 report round 2.
- Next: step 5 — finish DOCUMENT-STATUS.md (add the two new docs, B0 round 2, catfish-screens report).

- ~11:50 UTC: step 5 DONE. **ALL STEPS DONE.** Outputs: `.scratch/RESULTS-REGISTRY.md`, `.scratch/DOCUMENT-STATUS.md`, `.scratch/curation/PROVENANCE-HEADER.md`. No agents running. No existing file edited.
