# Part 1/Part 2 → active symbol table → Chinese Word alignment audit

Date: 2026-09-05 (Asia/Taipei)  
Scope: read-only audit of the four Part 1/Part 2 review decks, the active
symbol table, and the pure-Chinese thesis source/output.  No PPTX, thesis
source, DOCX, simulator, training run, Chapter 5, web package, or shared
authority was edited.

## 1. Authority and input files

The formal symbol authority is:

`/home/u24/papers/modqn-paper-reproduction/docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-symbol-table.md`

The Chinese Word source chain is the `thesis-mc/` front door described by:

`/home/u24/papers/modqn-paper-reproduction/thesis-mc/README.md`

The relevant Chinese sources and generated output are:

- `thesis-mc/mc-modqn-base.md`
- `thesis-mc/ch4-method.md`
- `thesis-mc/outputs/mcrl-thesis-ZH.docx`

The four review inputs audited were:

- `/home/u24/pptx-craft/review/part1-link-quality-and-modqn-en.pptx`
- `/home/u24/pptx-craft/review/part1-link-quality-and-modqn-en-zh-notes.pptx`
- `/home/u24/pptx-craft/review/part2-angle-aware-energy-efficiency-en.pptx`
- `/home/u24/pptx-craft/review/part2-angle-aware-energy-efficiency-en-zh-notes.pptx`

Input SHA-256 values observed at audit time:

```text
5bd8034a2181ff8952b43c6029162998b4a0223e8f13da3b900b44c9b093c9d3  part1-link-quality-and-modqn-en.pptx
44fd28e66ff8c9e4e4f35348ca86e09f93735a82cd57d8fb78b51f9d6b084d44  part1-link-quality-and-modqn-en-zh-notes.pptx
6510b1c5c1d3074d9a89742bd03be03c958cb64cbfe06a246ba8f231789867ad  part2-angle-aware-energy-efficiency-en.pptx
7afe866fd10aae83bef84e9a772d2dfdee7f6c31c7dc26798869935dfcea5cb0  part2-angle-aware-energy-efficiency-en-zh-notes.pptx
82da73640d0184abda86f1a1f792ffab35cc1339f81372d10a52b4a5e947a49b  2026-08-17-simplified-ee-symbol-table.md
1e9e6e31f0da20ef541aaed8695a1f85af229464bde83671e94acdfc35a84b29  mc-modqn-base.md
bea6c70e83b402b168ffcd27c36d56b1c0c744d00a9f8d29eb73144831adb945  ch4-method.md
e47c45edbcc5341be3b28cfeb77244fb97b0998a7bd68f19aca87bb878cb829b  mcrl-thesis-ZH.docx
```

The external repositories were already dirty: the symbol table, both Chinese
source files, and the DOCX are modified in `modqn-paper-reproduction`; the
four review PPTX files are untracked in `pptx-craft`.  They were therefore
treated as user WIP and not overwritten.

## 2. Audit method and validation

- Read the PPTX skill instructions and used `markitdown` plus the skill's
  `office/unpack.py` workflow.  The four decks were unpacked under `/tmp` and
  their raw `ppt/slides/slide*.xml` native OMML was inspected.
- Parsed the OMML `m:t` tokens and the associated math run properties.  This
  distinguishes a true symbol change from text-only slide narration and
  checks italic/bold math styling where relevant.
- Read the current symbol authority at §10.0 and §§10.2/10.12, then compared
  the Chinese Markdown source and the generated DOCX OOXML.  The DOCX was not
  manually edited because the README declares it a generated output.
- Re-ran `sha256sum` on every input above.  No source, deck, DOCX, or authority
  file changed during this audit.

## 3. What is in scope as new R1 EE/power notation

Original MODQN-only material (sets, activation, load, handover/Q-network
training, and the old P3 throughput-fairness formula) was not used to propose
new notation.  The following R1 physical chain was retained for comparison:

`d/alpha -> theta -> G^T/F/mu -> H/L/G^R -> p -> I/gamma -> R -> xi/P^p -> P^N -> eta -> r_1`.

No C2/C3/Expected-ZR/ZR symbols occur in Part 1 or Part 2.  Those provisional
symbols must not be added to the active table from these decks.

## 4. Part 1 and Part 2 findings

### 4.1 Matches to the active table

The following formulas use the same base symbols and single-letter owner
indices as the active table (apart from the explicit fixed parameter
`theta_{3dB}` discussed below):

| Deck location | Native formula role | Result |
|---|---|---|
| Part 1 slide 9 | `theta_{u,s,v}(t)` off-axis angle | Symbol roles match; vector boldness issue is listed below. |
| Part 1 slide 10 | `G^T(theta,theta_{3dB}) = G_0 F(theta,theta_{3dB})` | Formula structure matches. |
| Part 1 slide 14 | `gamma_{u,s,v}(t,theta_{u,s,v},theta_{3dB})` | Matches the unique actual SINR. |
| Part 1 slide 15 | `R_{u,s,v}(t,theta_{u,s,v},theta_{3dB})` | Matches the rate definition. |
| Part 2 slide 3 | segment-start inverse-gain power recurrence | Matches the active `p` recurrence. |
| Part 2 slide 4 | SINR | Matches. |
| Part 2 slide 5 | rate | Matches. |
| Part 2 slide 6 | beam max aggregation and `P^p=p/xi` | Semantics match; system-angle argument is not bold in the deck. |
| Part 2 slide 7 | `P^N=P^f+sum z P^p` | Semantics match; system-angle argument is not bold in the deck. |
| Part 2 slide 8 | selected-link `eta` and `r_{1,u}` | Semantics match; system-angle argument is not bold in the deck. |

The Part 2 English and English-with-Chinese-notes decks are formula-identical
for their seven labeled native OMML formulas.

### 4.2 Confirmed notation/formula discrepancies

These are the deltas that must be resolved before the decks are treated as
symbol-table-parity references.  This report does not edit the decks.

1. **Full-width versus half-angle in Part 1 slide 10.**

   - Part 1 English native formula `a09_half_power` states
     `F(theta,theta_{3dB})|_{theta=theta_{3dB}}=0.5` and
     `G^T(...)=G_0/2`.
   - The active table and the Chinese-notes slide state the half-power point
     at `theta=theta_{3dB}/2`; the Chinese-notes inline formula gives
     `F=0.5` there.
   - The active Chinese source at `mc-modqn-base.md:192` explicitly declares
     `theta_{3dB}` to be the **full** HPBW and uses
     `R_b=h_s tan(theta_{3dB}/2)`.  Therefore the English `a09_half_power`
     formula is stale/wrong relative to the active authority.

2. **Bessel denominator in Part 1 slide 11.**

   - Part 1 English `a10_mu` uses
     `2.07123 sin(theta) / sin(theta_{3dB})`.
   - Part 1 Chinese-notes `a10_mu` uses
     `2.07123 sin(theta) / sin(theta_{3dB}/2)`, which matches the table and
     Chinese source Eq. (3.9), `mc-modqn-base.md:180`.
   - This is a real EN/ZH deck disagreement, not just formatting.

3. **Slant-range elevation index in Part 1 slide 8.**

   - Both Part 1 decks display `alpha_{u,s,v}(t)` in the slant-range formula.
   - The active table and Chinese source use `alpha_{u,s}(t)` because
     elevation is user--satellite geometry, not beam-owned geometry
     (`mc-modqn-base.md:143`, table §10.2).  The slide should be normalized to
     the two-index form in a future deck pass.

4. **Vector notation in Part 1 slide 9.**

   - Both Part 1 decks use italic `v_{u,s,v}` and `r_{u,s,v}` in the raw OMML
     without a bold/vector marker.
   - The active table and source require `\mathbf{v}_{u,s,v}` and
     `\mathbf{r}_{u,s,v}` (`mc-modqn-base.md:152`; table §10.2).  Without the
     vector marker, these can be confused with the beam index `v` and scalar
     link symbols.

5. **System-wide angle argument is not bold in the decks.**

   Part 1 `a15_ee`/`a15_r1` and Part 2 `b09_beam_mapping`, `b10_supply`,
   `b08_system`, and `b10_reward` use plain `theta` in system-level arguments,
   for example `P^N(t,theta,theta_{3dB})` and
   `r_{1,u}(t,theta,theta_{3dB})`.  The active table requires the full system
   state `P^N(t,\boldsymbol{theta},theta_{3dB})` and
   `r_{1,u}(t,\boldsymbol{theta},theta_{3dB})` (§§10.2, 10.12; source
   `mc-modqn-base.md:274,355,403`).  The link-local arguments
   `theta_{u,s,v}` in `p`, `gamma`, `R`, and `eta` are correctly not bold.

6. **Conceptual shorthand omits dependent arguments in Part 1.**

   Part 1 slide 11 writes the pattern terms as `J_1(mu)` and `J_3(mu)`
   rather than `J_1(mu(theta,theta_{3dB}))` and
   `J_3(mu(theta,theta_{3dB}))`; slide 12 writes
   `L_f+L_g+L_c+L_s` without the function arguments.  These are acceptable
   only as explicitly declared teaching shorthand.  They are not the active
   authority's full definitions, which retain the arguments (`mc-modqn-base.md:180,206-210`).

### 4.3 Existing parameter-name exceptions

The active table's §10.0 rule requires single-letter role indices and says not
to invent long `req`/`contrib`/provenance labels.  It does not currently remove
the established physical parameter names used in the expanded power model.
The Chinese source/Word includes, among others:

`theta_{3dB}`, `xi_{max}`, `p_{sat}`, `N^{act}`, `P_{cir}`, `P_{BB}`,
`P_{RF}`, `P_{DC}`, `G_{R,min}`, `G_{R,max}`, `theta^R_{min}`,
`A_{zen}`, `I^{intra}`, and `I^{inter}`.

Locations include `mc-modqn-base.md:216-224,277-290,330-338,342-350` and
the corresponding active-table rows around §10.2.  These are existing
engineering/physical labels, not newly introduced Catfish route variables.
`theta_{3dB}` is explicitly authorized by the current authority as the fixed
beamwidth parameter.  If the author's “no two-letter sub/superscript” rule is
intended to cover the *expanded* PA/circuit equations too, the table and Word
source require a deliberate policy decision; blind renaming would create a
new formula contract and is outside this audit.  For the visible conceptual
R1 chain and all new route symbols, the base symbols and role indices are
single-letter.

## 5. Chinese Word/source alignment result

### Verified aligned portions

The current Chinese Markdown source already follows the table for the active
R1 chain:

- angle pattern and full-width convention: `mc-modqn-base.md:158-192`;
- channel factor: `mc-modqn-base.md:194-230`;
- segment-start and recurrent `p`: `mc-modqn-base.md:235-268`;
- beam aggregate, `P^p`, `P^N`, and `eta`: `mc-modqn-base.md:270-376`;
- `r_{1,u}` and reward vector: `mc-modqn-base.md:397-454`.

The generated DOCX's raw OOXML preserves the same distinction: in the
system-level equations (3.12a), (3.15), (3.16), (3.17), (3.25), and (3.29),
the `theta` run used as the full-system argument carries math style
`m:sty val="bi"` (bold italic), while link-local `theta_{u,s,v}` runs are
italic.  Plain-text extraction alone drops this bold distinction; it is not a
Word formula mismatch.

For reproducible Word locations, the equation paragraphs are in
`word/document.xml` of the DOCX at these 1-based `<w:p>` ordinals (the
ordinal is only a locator; the equation number is the stable paper-facing
identifier):

| Word equation | OOXML paragraph ordinal | Alignment result |
|---|---:|---|
| (3.9) | 79 | `theta_{3dB}/2` and the HOBS `J_1/J_3` pattern match. |
| (3.12a) | 104 | Local angle is unbold; the system-angle argument inside `p` is bold italic. |
| (3.15) | 114 | `P^p_{s,v}(t,\boldsymbol{theta},theta_{3dB})` and `xi_{s,v}` match. |
| (3.15a) | 116 | Existing expanded PA labels (`xi_{max}`, `p_{sat}`) are present; see §4.3. |
| (3.16) | 122 | `P^N(t,\boldsymbol{theta},theta_{3dB})` is bold italic in OOXML. |
| (3.17) | 125 | Local `theta_{u,s,v}` and system `\boldsymbol{theta}` are distinguished. |
| (3.25) | 134 | `r_{1,u}(t,\boldsymbol{theta},theta_{3dB})` is aligned. |
| (3.29) | 147 | Reward-vector system-angle argument is aligned. |

The DOCX also has a later Chapter 5 prose/formula block (`word/document.xml`
paragraph 265) with a shortened `r_{1,u}(t)=...\eta_{u,s,v}(t,theta)` display.
That is Chapter 5 material and was not edited or used to reopen the active
formula contract.

### No safe edit applied

The source and generated DOCX are outside this worker's writable root and are
already dirty user work.  The Word README also requires a source-first rebuild;
manually patching `mcrl-thesis-ZH.docx` would break the source/output chain.
Consequently, no edit was applied.  A future authorized source pass should:

1. keep the current source/table notation as the baseline;
2. resolve the deck-only deltas above (especially full HPBW and
   `alpha_{u,s}`) before using the decks as visual references;
3. decide whether detailed `xi_{max}`/PA/circuit tokens remain in the visible
   Chinese paper or are moved to prose/implementation detail under the
   single-letter policy;
4. rebuild the Chinese DOCX from the source and rerun the repository's
   three-DOCX structural/parity checks.

No C3 formula, Expected-ZR/ZR token, lambda value, learner expression, or
efficacy claim was frozen or changed.

## 6. Changed files and stop condition

Changed in this worker's writable tree (one new audit receipt only):

`/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v021-expected-zr/SYMBOL-ALIGNMENT-REPORT-2026-09-05.md`

No other file in the current repository was modified.  The delegated audit is
complete; return control to the parent agent.  Before any source/table/DOCX
edit, obtain an explicit writable checkout/authority handoff and re-check the
dirty state because the hashes above are point-in-time observations.
