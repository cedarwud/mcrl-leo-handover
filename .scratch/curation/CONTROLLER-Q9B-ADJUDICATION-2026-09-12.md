# Controller adjudication of the Q9b curation findings

Date 2026-09-12. Q9b added 178 registry rows (`e37b5843`) and, more valuably, surfaced seven problems. This document
rules on each. Every number below I re-derived myself from raw artefacts; where I could not, I say so.

## 1. `OR-17` — the herding move count. **CORRECTED, conclusion strengthened.**

Two figures circulated for the same quantity: "72–96 of 100" (`ORACLE-CELLS-2026-09-11.md:236`) and "66–99 of 100"
(`BRANCH-NUMBERS-FLOOR-R1-EVAL.md:34` **and Amendment 4 §2**).

I re-derived `n_moved` from the 240 raw per-step records in `.scratch/h4-probe/results-oracle/`:

| cell | per-step range | mean | p10–p90 |
|---|---|---|---|
| A-real R1 evaluation, **unfloored** | **65–100** | 82.6 | 71–96 |
| A-real R1 evaluation, **floored** | **58–100** | 79.9 | 66–96 |

**Neither published figure is the range.** Both are undeclared interior quantiles, and they describe **different
cells**: "72–96" is the unfloored p10–p90; "66–99" matches the floored p10–p90's lower bound but **not** its upper —
I cannot reproduce 99 from any aggregation of the raw data.

**Ruling:** the correction is written into Amendment 4 §2 as a dated controller note with the original sentence left
standing, so the change is auditable rather than silent. **The herding conclusion is unaffected and was understated**:
the true maximum is 100 of 100 users moving in a single step in both cells, which strengthens the finding that
A-real's advantage is not a per-user deviation gain. Nothing downstream changes.

## 2. `OR-19` — `n_disallowed_floor_only` present or absent. **OPEN, gates nothing.**

ORACLE-CELLS says the field is in every v4 item (floor-only 277,407 / 377,093); BRANCH-NUMBERS says it is absent and
the count unavailable. Totals agree. I have **not** re-derived this. It gates no decision — A-real is not being
pursued and B2 is closed — so it stays open and labelled `CONFLICT` in the registry rather than consuming time now.
ORACLE-CELLS calling it "a clarification, not a discrepancy" understates it, and the registry row says so.

## 3. The `E0-` family carries no PROVENANCE block. **RULED: the missing facts are supplied here, verified.**

Neither E0 document states the harness, MDP modifiers, user count, numerator convention, power accounting or the
DEVVAL episode seeds — and the E0 freeze is what fixes E1 and therefore S1. That is a real hole in the audit trail.

What I verified directly, from `runs-e1-d0-d3/E0-1-D0-equal_share-k3/devval-ep00300.json` on `sat` and from the tree:

- **DEVVAL episode seeds**: `[[9211000, 9212000], [9211001, 9212001], … [9211023, 9212023]]` — exactly the declared
  namespace `9_211_000+i / 9_212_000+i`, i = 0…23, **24 episodes**. Read from the result file, not from a document.
- **TLE archive**: pinned `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`, asserted per run.
- **Estimand**: pooled ratio-of-sums (Σ bits / Σ joules, divided once), full-buffer Shannon, no demand cap.
- **Power accounting**: consumed, per-beam max over served users.
- **Users**: 100. **Host**: `sat`.

**Action:** these must be written into `E0-BATCH-1-2026-09-12.md` as a PROVENANCE block and the `E0-` rows updated to
cite it. Assigned, not yet done.

## 4. ~110 cells with `cap` / `segment-anchor` / `interruption` = UNKNOWN. **RULED: resolved, they are tree properties.**

CURATE-2 correctly refused to infer these from `EE-CEILING`, because a curator may not make cross-document
inferences. A controller may, once it is verified rather than assumed. `EE-CEILING-2026-09-11.md:7-9` states, for
commit `102b2d4d`: **cap = not present in the tree (off); segment anchor = on (`SEGMENT_START_POWER_W`, warm start
"uniform-episode-length", not ablated); interruption = not present (off); users 100.**

These are properties of the **tree**, not of a run, so they transfer to every cell built on the same tree. I verified
the transfer rather than assuming it:

- `git merge-base --is-ancestor 102b2d4d 05aadf1b` → **true**.
- `git diff --name-only 102b2d4d 05aadf1b -- src/` → only `cf_credit.py`, `cf_dev.py`, `cf_ratio.py`, `cf_teacher.py`,
  all under `algorithms/`. **No `env/` file changed between the two commits**, so the MDP modifiers are byte-identical.

**Ruling:** every family run on `102b2d4d` or `05aadf1b` — `H4-`, `LP-`, `OR-`, `T0R-`, `TSQ-`, `B1C-`, `E0-` and E1 —
carries `cap off / segment anchor on / interruption off / users 100`. The registry may replace `UNKNOWN` with that,
**citing this ruling and the two git facts**, not `EE-CEILING` directly.

## 5. `B1C` ran on the local WSL2 laptop **with the pinned archive**. **RULED: §0 trap 1 is incomplete.**

Trap 1 currently reads as though host implies archive: local ⇒ unpinned, sat ⇒ pinned. B1's runs break that mapping.
Left as is, a future reader will mis-classify the B1 numbers by host alone.

**Ruling:** §0 trap 1 must state explicitly that **host does not imply archive**, that the pinned local copy is
`/home/u24/mcrl-runtime/tle-pinned-427e6a91`, and that only the `file_set_sha256` decides comparability. Assigned.

## 6. Five circulating values for checkpoint `e6b063ef…`. **RULED, and this one constrains S1.**

The registry now carries multiple mutually incomparable values for the same frozen 9,000-episode checkpoint, across
different episode sets, archives and harness variants. **None of them is comparable to another, and none of them is
the S1 baseline.**

> **Correction to my own enumeration, 2026-09-12**, raised by CURATE-2 while executing this ruling and verified by me.
> My original list of "five values" was wrong in two ways, and the ruling below is unaffected — in fact strengthened.
> (a) I wrongly included `SV-MZ-01`'s **90,866,329.62**: its own source calls it a **from-scratch `MODQN_RAW` retrain**
> with the checkpoint merely hashed, so it is **not a measurement of `e6b063ef…` at all**. It stays marked not-citable,
> but for a different reason, and the distinction is recorded rather than blurred.
> (b) I missed two that I had no way to see from my grep: `EC-01` **89,911,720** and `EC-02` **93,902,816.57**.
> The correct count is **six measured values** of this checkpoint — `EC-01` 89,911,720; `FF-04` = `CS-16` = `BP-01`
> 93,110,907.97; `DR-03` = `CS-02` 93,137,893.02; `FF-05` 93,787,980.20; `EC-02` 93,902,816.57; `E0-02` 94,413,179 —
> **spanning 4.5 %**, plus three further figures under non-default accountings or ablated physics that the same trap
> covers: `BP-02` 94,111,458.32 (TDM), `BP-03` 80,465,428.82 (ADDITIVE), `CS-14` 92,130,894.38 (`ablate_anchor`).

**Ruling, binding on the paper:** Amendment 13 §2 makes the S1 rollout of `e6b063ef…` on the **formal evaluation set,
under the same protocol as the six trained arms**, the *only* authoritative figure for the published 9,000-episode
reference. **No pre-S1 value for this checkpoint may be cited as the baseline**, in the paper or in any comparison,
and the five existing rows stay in the registry as historical measurements with their conditions attached. If the S1
rollout lands materially away from all five, that is expected — they were measured under different conditions — and
it is not evidence of a problem.

## 7. `OR-22` — the reverse-order B-real cell is HELD. **RULED: a caveat that travels with the number.**

Because the reverse-order sweep was never run, nothing in the project separates "sequential information is worth
+25.35 %" from "**this particular sweep order** is worth +25.35 %". B2 was closed on `TSQ-03` (T_SEQ representability
0.13–0.15), which is an independent reason and is unaffected — so **the closure stands and no work reopens**.

**Ruling:** the sweep-order caveat is **attached permanently to the +25.35 % oracle figure**. Wherever that number
appears — registry, draft, slides — it carries: *one sweep order only; the reverse-order cell was never measured, so
the split between sequential information and order artefact is unmeasured.* Do not cite the oracle gap as evidence of
the value of sequencing without it.

## 8. Two things Q9b flagged that need no ruling

- `E0-BATCH-1` self-supersedes inside one file (line 309 adopts τ = 1, line 395 withdraws it for τ = 0.3). That is the
  Amendment 8 §3b correction landing mid-document; the registry rows point at line 395. Correct as recorded.
- E0's "+19.8 % over baseline MODQN" numerically collides with the old `CT-03` / `CS-06` "+19.8 %". Unrelated
  procedures, coincidental digits. Flagged in the registry; no action.
