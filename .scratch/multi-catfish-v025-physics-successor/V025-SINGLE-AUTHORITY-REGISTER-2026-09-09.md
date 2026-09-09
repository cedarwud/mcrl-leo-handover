# V025 — single-authority register for symbols, thesis, deck and simulator (controller, 2026-09-09 ≈ 03:00 UTC)

Too many parallel versions exist. From now on exactly one artefact per class is authoritative; everything else is history and is never edited, quoted or built from.

## 1. Authorities in force
| Class | **Authority (the only one to edit or cite)** | Superseded / archive-only |
|---|---|---|
| Symbol table | `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` (65 490 B, 09-05 17:09) with `SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md` as its rule set | `chinese-word-r1-symbols-20260905-r1/…-r1-…md`; `multi-catfish-v03/v04-web-agent-package-*/docs/ACTIVE-SYMBOL-TABLE-2026-08-31.md`; every `.scratch` copy |
| Thesis (Chinese) | `artifacts/chinese-word-v023-lcsrs-20260905-r2/mcrl-thesis-ZH-v023-method-draft-20260905.docx` | `chinese-word-r1-symbols-20260905-r1/*.docx`; `.scratch/**/outputs/*.docx`; the EN and bilingual builds (regenerated later from the Chinese authority) |
| Deck style and equation pipeline | `artifacts/multi-catfish-teaching-deck-v023-20260905-r1/pilot-build/lc-srs-pilot-native-v4.pptx` with `build_pilot.py` + `native-formulas.json` | `…-native-v1/v2/v3.pptx`, `lc-srs-pilot-authored.pptx` |
| Deck content skeleton | `artifacts/multi-catfish-teaching-deck-v023-20260905-r1/agy-pilot/STORYBOARD.md` (38 pages) with `PILOT-SLIDE-SPEC.md` and `SCIENCE-CLAIM-MAP.md` | — |
| Successor science | the sealed declaration chain v1.0 → v1.9 with errata, the contingency ladder + amendment, the stages 6–8 contract v1 → v1.2, and the controller decision records | every draft C3 contract under the handoff directory (`DRAFT-C3-*`), the V0.23 LC-SRS successor contract, and the legacy physics |
| Simulator | `~/demo/leo-beam-sim` — **frozen at its current commit; not updated yet** (see §3) | — |

## 2. Working rule
New paper, symbol or deck work is produced as a **delta against the authority** in `.scratch/multi-catfish-v025-paper-lane-20260909/`, never as a new parallel document. The owner merges deltas into the authority when he chooses; nothing else writes to `artifacts/` or `docs/`. Any new symbol must pass the collision audit and be added to the one symbol table, not to a side list.

## 3. Simulator update is deliberately deferred
`~/demo/leo-beam-sim` still implements the legacy physics (segment-anchored recurrence power, the old service rule, the LC-SRS C3). It is **not** updated until both: (a) the design freeze takes effect (stage 4g passes its audit), and (b) the a-r0 admission decision is recorded. Updating it earlier would mean re-doing the migration for every amendment; three amendments landed today alone. When both conditions hold, the migration is one pass driven by the sealed documents: the rate-target power law with the ACM staircase, the decodability service rule, the per-slot PA energy with the declared boundary, the bounded catalogue and the set-level layer, and the new symbols. Its teaching value is unaffected in the meantime provided the demo is labelled as showing the legacy model.

## 4. What happens to the superseded copies
They stay in git history and on disk, unmodified, for provenance. No process reads them. If a later document needs a number from one of them, it must cite the authority instead or record why the archive value is still valid.
