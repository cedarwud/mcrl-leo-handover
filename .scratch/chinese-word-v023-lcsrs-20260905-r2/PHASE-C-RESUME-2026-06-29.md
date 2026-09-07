# Phase-C RESUME handoff (2026-06-29, controller session hit usage limit ~11:00, resets 14:30 Asia/Taipei)

> Read with `CURRENT-STATE.md` + `WRITING-HANDOFF.md`. This is the live "where Phase C stopped" note.
> Session limit cut two in-flight background tasks mid-run. Nothing in-flight was committed. HEAD = `c2224f4`.

## DONE + COMMITTED this session (verified)
- **research-visual-lab** (figures, sibling repo): `4cba8e9` fig2/3/4/cmp layout polish (controller eyeballed cmp+fig2);
  `90b65b7` (concurrent session) added the 4 ch4 detail figs **FIG-A..D incl. the controller polish agent's output**
  (FIG-B candidate-pair bus rerouted / FIG-C panel-(b) blue+orange brackets split to 2 lanes / FIG-D GENERAL pool
  symmetric + canvas tightened). **All 4 (A-D) + cmp + fig2 visually verified by controller (Chrome render).** FIG-4
  icon series `322a0d9..e992dfd` = concurrent session.
- **modqn repo** (thesis text + result figs): `8858702` figs→RAW means (smoothing artifact removed); `bbd8b89`
  ch5/ch6 k_cap win-zone re-derived to RAW+CI (dropped "k≤12 win / flip k=13"); `42912d3` translation glossary;
  `c2224f4` ch4 FIG-A..D captions + ch6 §6.3 smoothing→raw + WRITING-HANDOFF. **agy Gemini-Pro G6 = SOUND**
  (RED LINES hold, data consistency perfect, captions safe, bidirectional balance OK).

## IN-FLIGHT, CUT BY LIMIT — NOT committed, NOT reviewed
1. **EN translation** → `thesis-mc/en/` : `ch4-method.en.md`, `ch5-experimental-result.en.md`, `ch6-conclusion.en.md`
   = DRAFTED but **UNREVIEWED** (workflow `wrcgv3tlx` review stage never folded back). `mc-modqn-base.en.md`
   (abstract + ch1-3) = **NOT produced** (the chapter with the LOCKED title + the EN-abstract 2-missing-points fix).
   Authority for terms = `thesis-mc/TRANSLATION-GLOSSARY.md` (LOCKED PART-A / FORBIDDEN PART-B / honest PART-C).
2. **docx conversion tooling** → `thesis-mc/tools/` : `build_ris.sh`, `ris_preprocess.py`, `ris_postprocess.py`
   = CREATED but **UNVERIFIED** (agent cut before running + checking the conversion). Intended to fix ⑤'s
   BLOCKERS B1 (`\tag`→matrix), B2 (glued eqs split), B4 (A4/margins), B5 (references + page#). MUST be run +
   verified before trusting.

## RESUME ORDER (after limit reset / account switch)
1. Finish `mc-modqn-base.en.md` translation: TITLE verbatim (glossary A1, do-not-alter, ends "MODQN"); EN abstract
   re-translated + ADD the 2 points missing vs the ZH abstract (`mc-modqn-base.md:34`): (i) "coverage + EE lead at
   ALL capacity settings" (grounded); (ii) scope "no longer leads" to the WEIGHTED METRIC only.
2. Review ALL 4 EN chapters refute-by-default (glossary LOCKED used / FORBIDDEN absent: auction/bid/decode/distill/
   starve/decorative/Inference-Only; RED LINES: no false catfish-causation [de-collapse = the coordinated beam
   allocation step, A2≈A1], no raw-scalar win over DQN_scalar, no beats-Sun2024, no solved-root-cause; r1=EE never
   throughput; fidelity vs ZH numbers; student voice no AI-meta) + cross-model agy when available.
3. VERIFY the tooling: run `thesis-mc/tools/build_ris.sh` on current ZH → confirm 49/49 display eqs numbered
   (esp. 3.28/3.39/4.1/4.8-4.9), A4 pgSz, references present, page numbers. Fix residuals. (B1 is the BLOCKER.)
4. Source fixes (apply to BOTH ZH + EN): **B3** ch1-3 bold-headings → ATX `#`/`##`/`###` (0 Heading1 → Word TOC
   misses ch1-3); **B6** stray `**\**` (mc-modqn-base.md L36/L94), TABLE-5.3 column widths.
5. **`s̃_u` figure-notation alignment** (research-visual-lab): figures use `s_u^aug` (FIG-A ×1, FIG-B ×6, FIG-4 uses
   `s_u⊕χ_u`), thesis ch4 uses `\tilde{s}_u` (×7). Unify to `s̃_u` (thesis = authority). Refs + Ω/ω already aligned.
   Coordinate — a concurrent session was active in research-visual-lab.
6. Assemble + convert + **verify in REAL MS Word** (⑤: LibreOffice `¿`/`□`/red = preview glitches, NOT bugs; the
   docx XML is clean). Re-copy CURRENT sources before the final build (dry-run was a 10:00 snapshot).
7. Commit EN + tooling path-scoped once reviewed + verified.

## ✅ UPDATE — account-switched resume (~11:10) — EN translation + docx tooling DONE
- **EN translation = DONE + committed `bf1bbf7`** (`thesis-mc/en/*.en.md`, all 4 chapters COMPLETE).
  Reviewed: mc-modqn-base/ch4/ch6 = workflow-refute SOUND + controller; ch5 = controller SOUND. Title verbatim,
  abstract 2 points in, FORBIDDEN-EN clean, RED LINES held, r1=EE, math/[FIG]/cites preserved, ATX headings.
- **docx tooling = VERIFIED + committed `bf1bbf7`** (`thesis-mc/tools/{ris_preprocess.py,build_ris.sh,ris_postprocess.py}`).
  Built BOTH ZH (`mc-thesis-ris.docx`) and EN (`mc-thesis-ris-EN.docx`) under `scratch/conversion-test/`:
  **B1 49/49 eqs numbered · B2 glued split · B4 A4+margins · B5 footer page# · references in · 0 LaTeX leak ·
  EN Heading1→Word TOC works (B3 self-fixed in the EN ATX headings).**
- **RE-SCOPED remaining (the finishing pass — figures + final assembly):**
  1. **Figure finalization FIRST** (research-visual-lab; concurrent session was iterating FIG-4): `s̃_u` notation
     align (figs `s_u^aug` → thesis `s̃_u`, FIG-A/B/4); confirm FIG-4 done. THEN rasterize all figs → PNG.
  2. **Figure INSERTION**: replace the 13 `[FIG-*]` text placeholders (FIG-1..5, FIG-5.1..5.4, FIG-A..D) with
     `![caption](png)` + render the [FIG-*] captions → rebuild docx. (Currently placeholders render as text.)
  3. **Real MS Word verify** (cannot run here; ⑤: LibreOffice glitches ≠ bugs; the docx XML is clean).
  4. Minor: cross-model **agy voice check** on EN PENDING (agy timed out — low-risk, content/RED-LINE solidly
     verified); B3 ZH-headings (only if the ZH docx is a deliverable; EN is fine); B6 stray `**\**` L36/94;
     EN `[FIG]` unescaped vs ZH `\[FIG\]` (harmless as text); **grounded/hypothesis confidence tags appear in
     prose in BOTH ZH+EN** §5.6/ch6 (fidelity-correct; PART-C suggested stripping → author's content call).

## ✅✅ DONE 2026-06-29 (commit `20e283c`) — FULL BILINGUAL docx BUILT + verified
- **Tooling (new, path-scoped):** `thesis-mc/tools/build_bilingual.py` (deterministic EN/ZH block
  interleaver — walks both block sequences in lockstep, aborts on any structural divergence) +
  `thesis-mc/tools/build_bilingual.sh` (reuses the verified ris pipeline). Assembled markdown:
  `thesis-mc/en/bilingual/bi-{mc-modqn-base,ch4-method,ch5-experimental-result,ch6-conclusion}.md`.
- **Policy applied (USER-confirmed via AskUserQuestion):** headings → one combined ATX heading
  ("EN / ZH" where ZH is Chinese; English-only where the ZH source heading is itself English — also
  fixes B3 for ch1-3); **equations → ONCE** (byte-identical EN/ZH; eq 4.8's `\text{}` label carried by
  EN); prose/lists/[FIG-*] captions/table captions → **EN block then ZH block**; **tables → EN grid
  then ZH grid** (label columns genuinely differ: EN names vs ZH B0/A1/A2 codes). Front matter = ZH
  bilingual title page; abstract = approved SAMPLE spliced verbatim.
- **Output (gitignored):** `scratch/conversion-test/mc-thesis-ris-bilingual.docx` — **90pp A4, 49/49
  display eqs numbered, 1075 OMML, 0 LaTeX leak, references in, page#**; all 13 [FIG-*] stay TEXT
  placeholders (figures still gated). PDF rendered + 6 pages eyeballed (title/abstract, motivation,
  3.1 eqs, ch4 2×2 table EN+ZH grids, TABLE-5.5, references) — interleave clean, Times+標楷體 correct.
- **Fidelity PROVEN mechanically:** every source prose/table/math block present verbatim in the
  bilingual output → reviewed EN prose untouched, ZH untouched, RED LINES safe by construction.
  G1 `modqn.py` `aa877676` untouched.
- **Remaining (unchanged gates):** figure insertion (replace [FIG-*] with `![](png)` once
  research-visual-lab rasterizes) → rebuild; **real MS-Word verify** (LibreOffice narrow-column
  exponent wrap in TABLE-5.5 = preview glitch, NOT a bug — OMML clean); optional agy voice check.

## ★ NEXT TASK (USER-confirmed) — build the FULL BILINGUAL (EN→ZH interleaved) thesis docx   [✅ DONE above]
- **Format LOCKED** (USER approved the abstract sample): per logical chunk (theme / paragraph-group, "not too
  small" — abstract = 4 chunks), an **EN paragraph immediately followed by its ZH paragraph**, alternating.
  TEMPLATE = `thesis-mc/en/abstract-bilingual-SAMPLE.md` (built + rendered OK: EN Times justified, ZH 標楷體,
  A4, page#). Sample docx = `scratch/conversion-test/abstract-bilingual-SAMPLE.docx`.
- **Inputs:** EN = `thesis-mc/en/{mc-modqn-base,ch4-method,ch5-experimental-result,ch6-conclusion}.en.md`
  (committed `bf1bbf7`, reviewed SOUND); ZH = `thesis-mc/{same names}.md`. Align EN chunk ↔ ZH chunk at the
  same boundaries (the EN was translated sentence-aligned from the ZH).
- **★ Math/figure rule (decide + maybe ask USER):** equations (`$$...$$`/`\tag`), `[FIG-*]`/`[TABLE-*]`
  placeholders, and citations appear **ONCE per section, NOT duplicated per language** — only the PROSE
  interleaves. Suggested: EN prose → ZH prose → then the shared eq/figure block once (or keep eqs in the EN
  flow and have the ZH prose reference them). ch3/ch4 are math-heavy → get this right (the abstract had no math
  so it was trivial).
- **Build:** assemble per-chapter bilingual markdown (e.g. `thesis-mc/en/bilingual/*.md`) → convert with the
  verified tooling (`thesis-mc/tools/build_ris.sh`, generalize it to take the bilingual files) → output
  `scratch/conversion-test/mc-thesis-ris-bilingual.docx`. `[FIG-*]` stay as TEXT placeholders (figures still
  GATED on the research-visual-lab session). Preview via `soffice --headless --convert-to pdf` + read the PDF.
- Keep all the EN-review guarantees (glossary LOCKED terms, RED LINES, r1=EE) — the EN prose is already
  reviewed; do NOT re-edit it, only interleave with the ZH.

## INVARIANTS / CAUTIONS
- G1 `modqn.py` `aa877676` + EUV `env/family_b_*.py` `389eaaef` = untouched all session. Commits path-scoped only.
- ⚠ **Shared multi-session checkout:** a CONCURRENT session committed in BOTH repos this session (research-visual-lab
  FIG-4 + modqn ②③④⑤). Always `git status`/`git log` before committing; use `git commit -- <paths>` (ignores the
  shared index). ③ (worker) wrote `.agent-memory/MEMORY.md` (normally controller-single-writer) — verified accurate;
  controller reclaims single-writer.
- Heavy compute (none needed for Phase C) → server + HARD USER go-server gate. ROOT-Q (collapse env/state/algo) UNRESOLVED.
