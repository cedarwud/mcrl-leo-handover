# PROGRESS — CURATE-2 (Q9b: append 2026-09-11/12 registry rows)

Agent: CURATE-2. Read-only on measurements. Task: append registry sections for
H4- / LP- / OR- / EC- / T0R- / TSQ- / B1C- / E0- to `.scratch/RESULTS-REGISTRY.md`.
Do NOT curate E1.

Resume rule: read this file top-to-bottom; the last `DONE` step is the last completed
step. Everything is idempotent (edits are appends to named sections; re-check whether
the section header already exists before re-appending).

## Step log

- [DONE] S0 2026-09-12 — read `.scratch/RESULTS-REGISTRY.md` §0 (six condition traps, not five)
  and §1a rows for the exact 12-column schema; read `.scratch/curation/PROVENANCE-HEADER.md`.
  Schema: `ID | value | what it is | physics / harness | estimand | power accounting |
  host + TLE archive | tree / commit / flags | policy / checkpoint | n | source (file:line) | status`.
  Section-header convention: `### <n><letter>. <title> — <N> rows`. Registry is 866 lines,
  last section `### 4x.g. Declared branch — 1 row`.
- [DONE] S1 — read `V025-CONTROLLER-AMENDMENT-4-OWNER-GATES-B2-BRANCH-AND-CATFISH-COUNT-2026-09-12.md`
  (§1 five continue-eligibility conditions; §2 three B2 entry conditions; §3 catfish count).
- [DONE] S2 — read all 10 source documents end to end (H4-PROBE, LP-PROBE, ORACLE-CELLS,
  BRANCH-NUMBERS-FLOOR-R1-EVAL, CONTROLLER-INDEPENDENT-AGGREGATE, EE-CEILING, T0-REPRESENTABILITY,
  T-SEQ-REPRESENTABILITY, B1-CREDIT-IMPLEMENTATION, E0-BATCH-1, E0-FREEZE).
  Pre-checks run: no value or commit of these families already appears in the registry
  (`grep` for 110,507,234 / 112,195,917 / 107,000,983 / 51,866,475 / 114,129,570 / 134,129,417 /
  102b2d4d / 63b02dc0 / 05aadf1b / 772481c4 / a4c8ce12 — all 0 hits), so **no existing row is
  superseded** by anything added here.
  Facts established for the trap columns:
  * Every family is on the **pinned** archive `427e6a91…8fe9`. B1C- is the exception on host:
    it ran on the **local WSL2 laptop with the pinned archive asserted** — a host/archive pair §0
    trap 1 does not list — and reproduces the sat pinned reference rolls bit-for-bit.
  * The E0 documents carry **no PROVENANCE block at all** (grep for PROVENANCE / consumed /
    per-beam / users 100 / MODQN-harness / full-buffer over both E0 files and the dev-lane
    PROGRESS.md returns nothing) → physics, power accounting, users and the DEVVAL episode seeds
    are UNKNOWN for every E0- row.
  * Cross-checked LP calibration LP-prev(0,0) p10 95.02 vs EE-CEILING's cal MAX_NOMINAL_GAIN p10
    95.0 — agree, no conflict.
- [DONE] S3 — appended `## 5.` with eight `### 5a..5h` sections to `.scratch/RESULTS-REGISTRY.md`
  (file 866 → 1290 lines). Machine check: **178 rows, every one exactly 12 columns**; 8 header rows,
  8 separator rows; counts H4- 18, LP- 27, OR- 22, EC- 24, T0R- 18, TSQ- 19, B1C- 23, E0- 27.
  Idempotency: re-running S3 would duplicate the sections — check for the string
  `## 5. Probes, screens, ceilings and development results` before re-appending.
- [DONE] S4 — added a CURATE-2 paragraph to "How the rows were built" naming the eight prefixes,
  the extraction method, the UNKNOWN policy, the two CONFLICTs and the fact that no pre-existing
  row is superseded.
- [DONE] S5 — wrote `.scratch/curation/CURATE2-2026-09-12.md` (per-family counts, status wording and
  the one judgement call, supersessions, both CONFLICTs, every UNKNOWN with what would resolve it,
  eight highest-risk rows, five things flagged as possibly wrong in source documents).
- [DONE] S6 — committed named paths only (`.scratch/RESULTS-REGISTRY.md`,
  `.scratch/curation/CURATE2-2026-09-12.md`, `.scratch/curation/PROGRESS-CURATE2.md`).

## Receipts

- Read-only discipline held: no script was run that produces a number; `sat` was never contacted
  (every server artefact cited was already mirrored under `.scratch/`); no worktree created;
  `git add` used named paths only.
- CONFLICTs recorded as rows: **OR-17** (72–96 vs 66–99 users moving per step) and **OR-19**
  (`n_disallowed_floor_only` present vs absent).
- UNKNOWN blocks: the CF3-pilot MDP modifiers (cap / segment anchor / interruption) across
  H4-/LP-/OR-/T0R-/TSQ-/B1C-, and the entire provenance of the E0 lane including the DEVVAL
  episode seeds.
