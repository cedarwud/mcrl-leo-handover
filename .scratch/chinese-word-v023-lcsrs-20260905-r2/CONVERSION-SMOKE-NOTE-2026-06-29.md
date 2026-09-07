# md → ris.docx conversion smoke test — tracked note (2026-06-29)

Dry-run of the `to-ris-docx` (pandoc 3.10 + ris-style.docx) pipeline on the current MC thesis markdown, to
de-risk Phase C. **Full report + artifacts are gitignored** under `scratch/conversion-test/`:
`SMOKE-REPORT.md`, `test-thesis.docx`, `test-thesis.pdf`, `pages/p-01..45.png`. This note is the tracked digest.

**Inputs:** `mc-modqn-base.md` + `ch4-method.md` + `ch5-experimental-result.md` + `ch6-conclusion.md` (4 chapter
files; REFERENCES.md NOT included). Verified adversarially (7-dim agents + critic, cross-checked PNG vs docx XML).

## Verdict
Conversion is structurally sound: 45 pp, **508 native OMML equations, zero literal LaTeX leaked**, 7 real Word
tables, bilingual abstract intact, 標楷體+Times no body tofu, lists + all 19 `[FIG-*]/[TABLE-*]` placeholders
survive. Math *bodies* (cases / overrightarrow / widehat / mathcal·mathbb·mathbf / nabla / Ω⊤ / frac·sum·sqrt)
all render correctly. Failures are in **numbering, structure, geometry** — not the math.

## Phase C must-fix (detail + line numbers in the full report)
1. **BLOCKER — `\tag{}` eq numbers DROPPED.** pandoc OMML ignores `\tag`; 24/49 display eqs (all of ch3.2 +
   ch4, incl. η_EE 3.28 / J_w 3.39 / 4.1 / ACRM 4.8-4.9) render numberless while prose still says `如式 (3.34)`.
   Fix: pre-pass `\tag{X}` → `\begin{matrix} & EQ & & \text{(X)} \end{matrix}` (the matrix style that already
   numbers 3.1–3.25 correctly).
2. **Glued eq pairs** (`}{\begin{matrix}` at `mc-modqn-base.md` L304/L323/L359 = 3.13/14, 3.18/19, 3.21/22)
   render two-per-line, overflow right margin → split each into its own `$$` block.
3. **Heading hierarchy broken** — ch1-3 titles are bold-BodyText, only ch4-6 `##` → Heading2; **0 Heading1** →
   Word auto-TOC misses all of ch1-3 + chapter titles. Fix: normalize all 4 files to ATX `#`/`##`/`###`.
4. **Page = US Letter + ~1in margins** (ris A4 + 2.5/1.5 cm binding margins NOT applied; output `sectPr` has no
   pgSz/pgMar). Tooling fix: inject A4 pgSz + ris pgMar in `md2docx.sh` post-convert.
5. **References section absent** (REFERENCES.md not in inputs) + **no page numbers** (no header/footer parts).
6. Minor: stray `**\**`→`****` (L36, L94); ~~TABLE-5.3 equal-width columns wrap names mid-word (tune widths)~~.

## Update 2026-06-30 — table column widths FIXED (B7)
The equal-width-column failure (item 6 + the real blocker it masked: the math-heavy `J_w` "value [CI]" columns
of TABLE-5.2 **and** TABLE-5.3 had their trailing exponents **CLIPPED** = silent data loss, verified by
rendering the docx→pdf) is now fixed in `tools/ris_preprocess.py` (`set_table_widths`, B7). For pipe tables with
≥4 columns it rewrites the separator with PROPORTIONAL dash counts: a HARD per-column floor = the widest
unbreakable token (math span / Latin word, which cannot line-break and would otherwise clip), a SOFT cap that
lets long CJK cells wrap to a few lines instead of starving the math columns, scaled so the row exceeds pandoc's
72-col default → the table fills the text width and pandoc emits proportional `<w:gridCol>`. Verified by re-render:
TABLE-5.2 (5-col), TABLE-5.3 (6-col) and the §4.6 arms table (4-col) now show all math values / CIs intact with
no clipping. Residual cosmetic only: a few long labels (`DQN_throughput`) and wide CJK headers wrap to 2 lines
(readable; a mild table-font reduction could remove it if wanted). 2-3 column tables are left byte-identical.

## Preview-only (NOT bugs; docx XML clean, Word fine)
`¿\(3.N\)` on matrix numbers, `□` in eq 3.26 (= U+2001/2009 math-spaces), red `¿¿` in eq 4.6 — LibreOffice OMML
render glitches (XML has 0 backslash / 0 `¿` / 0 `□`). **Validate the final .docx in MS Word, not LibreOffice.**

## Process note
The dry-run docx is a 10:00 snapshot; `ch6-conclusion.md` was edited mid-session (smoothing-note paragraph) →
re-copy CURRENT sources before the final build. The docx is a snapshot, not the final document.
