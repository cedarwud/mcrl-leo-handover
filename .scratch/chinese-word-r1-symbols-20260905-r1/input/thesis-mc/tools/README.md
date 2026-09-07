# thesis-mc/tools — MC thesis → ris-style Word (.docx) build

> **★ To convert the Multi-Catfish thesis Markdown to the ris-style Word
> document, run ONE command:**
>
> ```bash
> bash thesis-mc/tools/build_ris.sh thesis-mc/outputs  # -> thesis-mc/outputs/mcrl-thesis-ZH.docx
> ```
>
> Do **NOT** hand-run `pandoc` on the thesis Markdown directly, and do **NOT**
> use `conf-demo/build_paper.sh` for the thesis — that one is the *IEEE
> two-column conference PDF* path, a different output with none of the fixes
> below. This `build_ris.sh` pipeline is the thesis Word path.

## What it is

`build_ris.sh` is a **repo-local wrapper** around the global `to-ris-docx`
skill (`~/.claude/skills/to-ris-docx/md2docx.sh` + `ris-style.docx`). The skill
does the generic Markdown→docx conversion (pandoc, 標楷體+Times, 1.5 spacing,
native OMML equations). The wrapper adds the thesis-specific pre/post fixes that
pandoc + the reference doc do not emit on their own. **Sources are read-only —
everything runs on COPIES** (a translation/edit workflow reads the `.md` live).

## Pipeline

```
build_ris.sh
  ├─ ris_preprocess.py   (pandoc PRE-pass, on copies)
  │     B1  \tag{X} eq numbers -> matrix-wrapped numbered eqs (pandoc drops \tag)
  │     B2  split glued $$..$$ matrix pairs into one block each
  │     B7  table column widths + alignment (proportional widths; math/Latin
  │         tokens never clip; all columns left-aligned = house norm)
  │     --references: trim REFERENCES.md to the citation list
  ├─ md2docx.sh          (the to-ris-docx SKILL: pandoc + ris-style.docx)
  ├─ ris_postprocess.py  (docx POST-pass)
        B4  A4 page size + ris binding margins
        B5  centered PAGE-number footer
        B8  three-line (三線表) table borders + bold header row +
            zero the inherited first-line indent in table cells
        B12 list marker-to-text anchor = 360 twips in every list level — half
            Word's former 720-twip fallback — with an explicit number tab;
            each nested level's marker position remains unchanged
  └─ apply_cover.py      (replace generated front matter with the canonical
                          outputs/thesis-cover.docx body; restart body at page 1)
```

## House-norm table style (matches `catfish/thesis.pdf`, same advisor)

All tables render as **三線表** (booktabs): top rule + header rule + bottom
rule, **no vertical lines, no inner grid**, **bold header**, **left-aligned
columns**. There is **no full-grid path** — the advisor's reference thesis uses
三線表 for every table, including categorical/comparison tables. Long cell text
wrapping to 2-3 lines is normal (reference cells wrap to 4-5 lines).

Border/width logic keys off table shape automatically; nothing to configure
per table. If a specific table ever needs a different treatment, change the
constants/branch in `ris_preprocess.set_table_widths` /
`ris_postprocess.add_three_line_borders` — do not add markup to the `.md`.

## Rules

- **Validate the final `.docx` in MS Word, not LibreOffice** — LibreOffice has
  OMML render glitches (`¿`/`□` on matrix eq numbers) that Word does not; the
  docx XML is clean (see `../CONVERSION-SMOKE-NOTE-2026-06-29.md`).
- The wrappers default to `thesis-mc/outputs`. The three coherent outputs are
  `mcrl-thesis-ZH.docx`, `mcrl-thesis-EN.docx`, and `mcrl-thesis-bilingual.docx`.
- `../outputs/thesis-cover.docx` is the canonical cover-page source for all
  three variants. Every wrapper requires it and replaces the Markdown-generated
  cover before publishing; there is no fallback to the old cover text.
- English-only build: `build_en.sh`; EN sources are under `../en/`.
- Bilingual build: `build_bilingual.sh`.
- To update all three deliverables together, use `build_all.sh`. It stages the
  ZH, EN, and bilingual DOCX files from one read-only input snapshot, proves
  that the live manuscript/figure/tool inputs did not change during the build,
  regenerates the bilingual Markdown a second time and requires byte identity,
  checks DOCX image/equation/heading/caption parity plus pure-English visible
  text, then publishes all three files with `mcrl-thesis-build-receipt.txt`
  written last as the validity marker.

## Files

| file | role |
|------|------|
| `build_ris.sh` | orchestrator (run this) |
| `build_en.sh` | English-only variant |
| `assemble_english.py` | temp-only EN front-matter/abstract assembly + visible-CJK guard |
| `ris_preprocess.py` | pandoc pre-pass (eq numbering, glued-split, table widths/align) |
| `ris_postprocess.py` | docx post-pass (A4, page#, 三線表 borders, bold header, indent) |
| `build_bilingual.sh` | bilingual variant |
| `build_all.sh` | receipt-gated three-version build + same-source receipt |
| `apply_cover.py` | fail-closed canonical-cover body/style importer + section/page-number split |
| `verify_three_docx.py` | OOXML cover/image/equation/heading/caption/language parity gate |
| `test_build_bilingual.py` | fail-closed regression tests for abstract and inline-symbol provenance |
| `test_ris_postprocess.py` | list-gap regression tests, including nested bullets and an ordered-list negative control |
| `test_apply_cover.py` | cover-prefix, section-break, style-resolution, and idempotence regression tests |
