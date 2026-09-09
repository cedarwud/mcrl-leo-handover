# BUILD-NOTES — how `v025-deck-skeleton.pptx` was produced

The brief asked for the deck to be built with `build_pilot.py` and the
native-formula pipeline on the wmnlab template, and for an exact statement if
that pipeline could not be reused as is. It could not be reused unmodified.
This file says precisely why, what was substituted, and what is still unverified.

---

## 1. What the V0.23 pipeline is

`multi-catfish-teaching-deck-v023-20260905-r1/pilot-build/` runs in two stages:

1. **Authoring** — `build_pilot.py` opens the wmnlab template, strips the
   slide-level shapes off one template slide, draws cards and text boxes with
   python-pptx, and places each equation as a **named autoshape** whose only
   paragraph is the marker `[[PPT_NATIVE_MATH:<id>]]`.
2. **Native-math injection** — a second tool consumes `native-formulas.json`
   (`id`, `slide`, `shape_name`, `match_text`, `latex`, `font_face`,
   `font_size_pt`, `force_italic`, `align`, `insets_in`, `require_autoshape`)
   and replaces each marker paragraph with an `a14:m` / OMML math zone. Its
   output is `lc-srs-pilot-native-v4.pptx`.

Stage 2 is the part that makes the equations native and editable in PowerPoint.

---

## 2. Why it could not be reused as is — three blockers

**Blocker 1 — the template path does not exist on this host.**
`build_pilot.py:17` hard-codes `TEMPLATE = /home/u24/pptx-craft/assets/wmnlab.pptx`.
There is no `/home/u24` on this machine. The same asset is present at
`/home/sat/pptx-wrap/assets/templates/wmnlab.pptx`
(13.333" × 7.5", the `標題投影片` / `標題及物件` / … master, three sample slides).
**Resolution:** the template path is re-pointed. The asset itself is unchanged
and is still the wmnlab template, so this is a path fix, not a substitution.

**Blocker 2 — the stage-2 injector is not installed.**
The tool that consumes `native-formulas.json` lived under `/home/u24/pptx-craft/`,
which is absent. Nothing on this filesystem accepts that manifest schema; a
search for `require_autoshape` / `match_text` across the machine returns only
the V0.23 artefacts themselves and unrelated files. The nearest relative is
`leo-beam-sim-render/courseware/c120-lora-leo-deck/insert-native-equations.py`,
but it hard-codes two LoRa equations, reads no manifest, and emits Cambria Math,
so it cannot drive this deck.
**Resolution:** `native_math.py` reimplements stage 2 — see §3.

**Blocker 3 — `build_pilot.py` authors exactly one slide.**
Its `build()` renders a single hard-coded pilot slide (V0.23 storyboard page 23)
and then deletes the other two template slides. That page is **DELETE** in
`STORYBOARD-DELTA.md`, and the successor arc is 34 slides.
**Resolution:** `build_v025_deck.py` keeps `build_pilot.py`'s primitives and
contract — `_remove_shape`, `_set_text`, `_text_box`, `_card`, `_formula_host`,
the marker convention, the colour constants, the "keep the master, strip the
slide-level shapes" rule — and generalises `build()` to a content-driven loop
over `deck_content.DECK`.

Environment note: `python-pptx` was not installed for any interpreter on this
host, so it was installed into a throwaway virtualenv at `/tmp/v025deck-venv`
(python-pptx 1.0.2). No system Python was modified.

---

## 3. The stage-2 reimplementation, and what it is checked against

`native_math.py` is a LaTeX-subset → OMML converter plus an injector. It is not
a guess at the V0.23 dialect: the dialect was **recovered from the shipped
artefact** by unpacking `lc-srs-pilot-native-v4.pptx` and reading
`ppt/slides/slide3.xml`. The reimplementation emits the same structures:

| Element | V0.23 artefact | This build |
|---|---|---|
| Paragraph | `<a:p><a:pPr algn="ctr"/><a14:m>…</a14:m></a:p>` | same |
| Wrapper | `<m:oMathPara><m:oMath>` with `a14`/`m` declared on `a14:m` | same |
| Run | `<m:r><a:rPr lang altLang sz i dirty><a:latin/><a:ea/><a:cs/></a:rPr><m:t>` | same |
| Sub / sup | `m:sSub`, `m:sSup` with `m:e` + `m:sub` / `m:sup` | same, plus `m:sSubSup` |
| Fraction | `m:f` with `m:fPr/m:type[@m:val='bar']` | same |
| n-ary | `m:nary` with `m:chr`, `m:limLoc='undOvr'`, `m:subHide`/`m:supHide`, zero-width placeholder run in the hidden slot | same |
| Delimiters | `m:d` with `m:begChr` / `m:sepChr` / `m:endChr` / `m:grow` | same |
| Typeface | Times New Roman, `sz="2000"`, `i="1"` on every run | same |

Two deliberate departures, both recorded here rather than buried:

1. **Upright runs exist now.** The V0.23 pilot forced `i="1"` on every run
   because none of its four formulas contained a function name or a unit. This
   deck needs `min` and `dB` upright, so `\mathrm{…}` and function names emit
   `i="0"`. `force_italic` still governs everything else.
2. **Two glyph classes get a per-run Cambria Math override.** Times New Roman
   has no Mathematical Script or Double-Struck block, so `\mathcal{…}` and
   `\mathbb{1}` would otherwise render as missing glyphs. The symbol authority
   depends on script `𝒦` being visually distinct from upright capital `K`, so
   those runs — and only those — carry `a:latin typeface="Cambria Math"`.
   Every other run stays Times New Roman.

The converter **fails closed**: an unknown macro raises rather than silently
dropping a token, and the injector raises if a named host is missing, is not an
autoshape, or does not contain its marker.

---

## 4. Reproduce

```
cd .scratch/multi-catfish-v025-paper-lane-20260909/slides
/tmp/v025deck-venv/bin/python native_math.py        # converter smoke test
/tmp/v025deck-venv/bin/python build_v025_deck.py    # -> v025-deck-skeleton.pptx
/tmp/v025deck-venv/bin/python make_outline.py       # -> OUTLINE.md
```

| File | Role |
|---|---|
| `build_v025_deck.py` | authoring stage (generalised `build_pilot.py`) |
| `deck_content.py` | the 34-slide `DECK` object — all prose and speaker notes |
| `native-formulas-v025.json` | equation manifest, V0.23 schema, supersedes `native-formulas.json` |
| `native_math.py` | LaTeX→OMML converter + injector (reimplemented stage 2) |
| `make_outline.py` | emits `OUTLINE.md` from the same `DECK` object |
| `build-report.json` | per-equation injection record and the fit estimate |

---

## 5. What was verified

- **34 slides**, built on the wmnlab template with its master, layouts and
  slide-number field intact.
- **18 native OfficeMath equations** injected; **zero** `[[PPT_NATIVE_MATH:…]]`
  markers survive in the output.
- **Font sizes are exactly {28, 24, 20} pt** across 442 runs — no 26, 22, 18, 16
  or 14 pt anywhere. Every run is Times New Roman except the script/blackboard
  math glyphs of §3.
- **One speaker note per slide**, all 34 non-empty.
- **No shape falls outside the 13.333" × 7.5" canvas.**
- `⟨結果待填⟩` appears on slides 1, 8, 17, 20, 23, 24, 30, 31, 32. **No result
  numbers appear anywhere in the deck.**
- The package re-opens cleanly through python-pptx after injection, and every
  slide part is well-formed XML.

## 6. What was NOT verified — read this before presenting

- **No visual render.** Neither LibreOffice nor PowerPoint is installed on this
  host (`soffice` is absent), so unlike the V0.23 pilot — which shipped
  `render-v3/` and `render-v4/` — this deck has **never been rasterised**.
  Text fit is a static estimate at 0.46 em average advance, reported as
  `overflow_estimate` in `build-report.json`; 11 shapes sit between 1.01× and
  1.08× of the estimate's budget, which is inside the estimator's own error but
  is not a measurement. One render pass on a machine with PowerPoint is the
  right next step, and the math-host boxes are the first thing to check.
- **PowerPoint's edit / save / reopen path for the injected math zones is not
  claimed.** The XML matches a shipped V0.23 artefact element for element, which
  is strong evidence, not a test.
- **LibreOffice handling of the `a14:m` native choice is not claimed.** No SVG
  fallback picture is embedded; if a LibreOffice preview is ever needed, that
  fallback has to be added.
- **The three template sample slides are removed from the slide-id list but
  their parts remain in the package**, along with their notes parts. This is the
  same behaviour as `build_pilot.py`, whose output shipped that way; PowerPoint
  tolerates it, but it explains why the package contains 37 notes parts for 34
  slides.
- **Figures are not produced.** `CORE-FLOW-DRAFT.svg` contradicts the two-layer
  deployment and still needs a redraw; no diagram in this deck is imported from
  the V0.23 set.
