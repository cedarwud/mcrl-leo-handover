# V025 — single-authority register for symbols, thesis, deck and simulator (controller, 2026-09-09 ≈ 03:00 UTC)

Too many parallel versions exist. From now on exactly one artefact per class is authoritative; everything else is history and is never edited, quoted or built from.

> **Controller revision, 2026-09-12.** Four of the six rows below were stale and are corrected in place; the original
> text of each corrected row is preserved underneath it so the change is auditable. **Rows 3 (deck style) and 4 (deck
> skeleton) are unchanged.** The register itself had gone out of date — which is the failure this file exists to
> prevent — so §5 now records how to check it rather than trusting it.

## 1. Authorities in force
| Class | **Authority (the only one to edit or cite)** | Superseded / archive-only |
|---|---|---|
| Symbol table | **`artifacts/chinese-word-v025-unified-symbols-20260909/active-symbol-table-v025-20260909.md`** (100 916 B, 09-09 16:30), with the collision rules of `chinese-word-v023-lcsrs-20260905-r2/SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md` carried over verbatim. **Authority declared by `artifacts/chinese-word-v025-unified-symbols-20260909/SUPERSEDES.md`, not by this register.** | `chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` (sealed; still the comparison basis for the frozen V0.23 thesis and the verbatim base of the merged table); `chinese-word-r1-symbols-20260905-r1/…-r1-…md`; `multi-catfish-v03/v04-web-agent-package-*/docs/ACTIVE-SYMBOL-TABLE-2026-08-31.md`; every `.scratch` copy |
| Thesis (Chinese) | `artifacts/chinese-word-v023-lcsrs-20260905-r2/mcrl-thesis-ZH-v023-method-draft-20260905.docx` (sha256 `367c11f6…`) — **authority retained, see §6 for the ruling and the four reasons** | `chinese-word-r1-symbols-20260905-r1/*.docx`; `.scratch/**/outputs/*.docx`; the EN and bilingual builds. **`artifacts/thesis-v025-merge-20260909/mcrl-thesis-ZH-v025-method-draft-20260909.docx` (sha256 `37a50e46…`) is NOT authority** — it is reusable material and provenance (§6) |
| Deck style and equation pipeline | `artifacts/multi-catfish-teaching-deck-v023-20260905-r1/pilot-build/lc-srs-pilot-native-v4.pptx` with `build_pilot.py` + `native-formulas.json` | `…-native-v1/v2/v3.pptx`, `lc-srs-pilot-authored.pptx` |
| Deck content skeleton | `artifacts/multi-catfish-teaching-deck-v023-20260905-r1/agy-pilot/STORYBOARD.md` (the register's original "38 pages" is the register's own claim and has never been verified by counting) with `PILOT-SLIDE-SPEC.md` and `SCIENCE-CLAIM-MAP.md` | — |
| Successor science | **`.scratch/DOCUMENT-STATUS.md` is the entry point to the in-force list — but it is itself dated 2026-09-11 ≈ 11:45 UTC and does not cover anything after it.** The in-force chain is: Ruling Q5 NO-GO → `…RULING-CEILING-PARITY-B-CHAIN-AND-CATFISH-COUNT-2026-09-11.md` (Ruling 2) → **Amendments 1–15 of the Ruling-2 series** (see the collision warning in §5) → the controller adjudications in `.scratch/catfish2-successor/` and `.scratch/dev-training/`. Numbers: `.scratch/RESULTS-REGISTRY.md` | The **old V0.25 stage-C sealed chain** — priority declarations v1.0–v1.9, the contingency ladder, the stages 6–8 contracts v1/v1.1/v1.2, the CH5 sweep-figure spec, the ACM defect confirmation — **route closed 2026-09-11**; every `DRAFT-C3-*`; the V0.23 LC-SRS successor contract; the legacy physics |
| Simulator | `~/demo/leo-beam-sim` — **frozen; its original unfreeze conditions are VOID (§3) and no new condition has been set** | — |

<details><summary>Original text of the four corrected rows (2026-09-09)</summary>

- **Symbol table** — `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` (65 490 B, 09-05 17:09) with `SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md` as its rule set.
- **Thesis** — as now, but without the statement that the v025 merge exists and is not authority.
- **Successor science** — "the sealed declaration chain v1.0 → v1.9 with errata, the contingency ladder + amendment, the stages 6–8 contract v1 → v1.2, and the controller decision records".
- **Simulator** — "not updated until both: (a) the design freeze takes effect (stage 4g passes its audit), and (b) the a-r0 admission decision is recorded".

</details>

## 2. Working rule
New paper, symbol or deck work is produced as a **delta against the authority** in `.scratch/multi-catfish-v025-paper-lane-20260909/`, never as a new parallel document. The owner merges deltas into the authority when he chooses; nothing else writes to `artifacts/` or `docs/`. Any new symbol must pass the collision audit and be added to the one symbol table, not to a side list.

**Arbitration order when two documents disagree**: physical formula definitions → `2026-08-17-simplified-ee-presentation-spec.md`; design, constants, gates and decision rules → the in-force successor chain above; notation only → the symbol table. The symbol table fixes notation and never changes a design.

## 3. Simulator — the unfreeze conditions are void and must be re-set
`~/demo/leo-beam-sim` still implements the legacy physics (segment-anchored recurrence power, the old service rule, the LC-SRS C3). The original conditions — (a) stage 4g passes its audit, (b) the a-r0 admission decision is recorded — **both belong to the V0.25 stage-C route that closed on 2026-09-11, so neither can ever be satisfied. They are void.** No replacement condition has been set, and setting one is an owner decision.

**Until then the demo shows physics the project no longer uses.** If it is shown to anyone — teaching, a talk, a visitor — it must be labelled as the legacy model. That warning was in the original register and matters more now, because the gap is wider: the frozen model predates the pooled-EE physics finding, the EE ceiling, the oracle cells, and the whole teacher-injection line.

## 4. What happens to the superseded copies
They stay in git history and on disk, unmodified, for provenance. No process reads them. If a later document needs a number from one of them, it must cite the authority instead or record why the archive value is still valid.

## 5. How to check this register before trusting it — it has gone stale once
This file is dated 2026-09-09 ≈ 03:00 UTC. The symbol-table authority moved **the same day at 16:30**, declared in the new directory's own `SUPERSEDES.md` and not here, and the register was not updated for three days. So:

1. **Check the authority directory for a later `SUPERSEDES.md` or equivalent**, not only this register.
2. **`.scratch/DOCUMENT-STATUS.md` is also point-in-time** (2026-09-11 ≈ 11:45 UTC) and does not cover later documents.
3. **Amendment-number collision, unresolved.** `.scratch/multi-catfish-v025-physics-successor/` contains **two** independent Amendment 1/2/3 series with the same filename prefix and overlapping dates:
   - the three-catfish-pilot series — `…AMENDMENT-1-THREE-CATFISH-PILOT-2026-09-11.md`, `…AMENDMENT-2-EE-ONLY-2026-09-11.md`, `…AMENDMENT-3-PREGENERATED-SOURCE-POOLS-2026-09-11.md`;
   - the **Ruling-2 series, which is the live one** — `…AMENDMENT-1-ORACLE-FIRST-SCREEN-2026-09-11.md`, `…AMENDMENT-2-SCENARIO-A-BRANCH-…md`, `…AMENDMENT-3-TEACHERS-LADDER-…-2026-09-12.md`, continuing to Amendment 15.

   **"Amendment 2" alone is ambiguous and must never be cited without its full filename.** The collision was introduced by the Ruling-2 series reusing the numbering; renaming sealed documents is not done, so the mitigation is citation discipline.

## 6. Thesis ruling, 2026-09-12 — authority stays at V0.23
`artifacts/thesis-v025-merge-20260909/mcrl-thesis-ZH-v025-method-draft-20260909.docx` applied **61/61** merge blocks, left the V0.23 authority **byte-identical** (`367c11f6…` before and after), expanded 416 → 1,502 non-empty paragraphs, and lost **zero** baseline OMML equations. It is careful work. It is **not** promoted, for four reasons, any one of which would be sufficient:

1. **It encodes a closed route.** Its own apply report records the adjudication it implements: base score `F = B − η_ref·E`, coordinator ranking objective `G = F + κ·Φ`. That is the V0.25 stage-C coordinator design, closed on 2026-09-11. The live line has no coordinator and no `κ·Φ`; promoting this document would make the authoritative thesis describe a method the project has abandoned.
2. **Un-reviewed new text.** `OPEN-QUESTIONS.md` O-6: the abstract and chapters 1, 2 and 6 (blocks M-A1–M-A4, M-B2–M-B5, M-C1–M-C6, M-G1–M-G3) are **newly written and were never reviewed by the owner**.
3. **Placeholders in the body.** O-1: §5.2.4 carries four `⟨結果待填⟩` fields.
4. **Two unresolved editorial defects.** O-4: deleted equations leave gaps in the numbering and the renumber-or-keep-gaps decision is still open, affecting every cross-reference. O-5: the `D(a)` versus aperture `D` collision is still live in §3.1.2.

**What it is instead**: reusable material and provenance. When the thesis is rewritten around the current line, `MERGED-SECTIONS-ZH.md`, `MERGE-PLAN.md` and the seven open questions are the starting point, and the merge machinery is proven to preserve equations. **The v023 `.pdf` alongside the authority `.docx` is an output, not an authority.**

**Both documents are V0.23-era science.** Nothing from 2026-09-11 onward is in either: the pooled-EE physics finding, the EE ceiling, the oracle cells, T0 representability, the E0/E1 development results, or the Catfish-2 successor line. The rewrite waits on the k = 8 / k = 9 outcome, and must carry the decomposition finding recorded in `.scratch/dev-training/CONTROLLER-HEADLINE-DECOMPOSITION-2026-09-12.md`: roughly half the headline gain over the published baseline is the backbone, not the catfish.
