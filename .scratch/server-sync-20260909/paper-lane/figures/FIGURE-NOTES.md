# FIGURE-NOTES — provenance, symbol decisions and known gaps

Covers `figure1-angle-power-ee.*`, `figure1-data.csv`, `figure2-architecture.*`
and the two result-figure specifications in this directory.

---

## 1. Figure 1 — how it was produced, and why you can trust it

**It is a recomputation, not a transcription.** `figure1_compute.py` implements
only the closed-form equations of the "Exact equations" block of
`V025-ANGLE-POWER-EE-NOTE-2026-09-08.md`. No value from that note's results
table appears in the compute path. In particular:

- the radiation pattern uses an **ascending-series Bessel implementation**
  written here, not `scipy` (the argument range is `μ ∈ [0, 2.07123]`, where the
  series converges quickly);
- the ACM ladder is the standard DVB-S2 / EN 302 307-1 QPSK table
  (`η_m`, `Es/N0`), from which `Γ_r(n_b)` is derived rather than copied;
- the cap-hit angle is found by **bisection** on `G^T(θ)`, not read off.

**Validation.** `figure1_selftest.py` checks the recomputation against two
external oracles and passes all checks:

| Check | Result |
|---|---|
| Free-space path gain, `L(10°)`, angle-independent product `C`, noise `N`, `p_sat` | exact to ≤ 1.1e-16 relative |
| `Γ_r(1)`, `Γ_r(2)`, `Γ_r(4)` | reproduce the sealed values to ≤ 2.2e-16 |
| Cap-hit angle for `n_b = 4` | **0.853069795148802°** — all 15 digits |
| `G^T(θ)` series vs `scipy.special.jv`, 400 angles | worst 3.0e-15 relative |
| All 16 hand-computed KAT rows (gain, power, MODCOD, bits, energy, EE) | pass |
| The four structural properties (monotone power, flat at cap, falling EE, constant-RF `b0`) | pass |

**Two findings worth recording.**

1. **`γ_PHY,min` is a separate sealed constant, not the lowest MODCOD
   threshold.** Deriving it from QPSK 1/4 gives `0.7174947934871672`, but the
   sealed `Γ_r(1)` is `0.717494793565848` — a 1.1e-10 relative difference. The
   discrepancy resolves exactly if `γ_PHY,min` is the **service threshold**
   carried as a rounded-dB literal, `−1.44181246 dB`, which sits fractionally
   *above* the exact QPSK 1/4 threshold, so the `max()` in `Γ_r` selects it.
   This is consistent with the successor's service rule
   ("served ⇔ SINR ≥ −1.4418 dB after joint resolution") and is encoded as
   `SERVICE_THRESHOLD_DB` in the compute module.
2. **The note's `0.853070` table rows are evaluated at the exact cap-hit
   angle**, not at the printed rounding. One ULP past the cap-hit angle the
   `n_b = 4` link is capped and drops a MODCOD, so those rows only reproduce at
   full precision. The self-test evaluates them at `SEALED_CAP_HIT_DEG`.

**Curve coincidence.** Above the cap-hit angle the `n_b = 4` and `b0` curves
coincide exactly in both panels. That is correct physics, not a plotting bug:
both then transmit at `p⁺ = 1.65 W` with the same realised SINR, hence the same
MODCOD, bits and energy.

---

## 2. Symbol decisions for Figure 1 — and three places the authority is silent

The instruction was "symbols exactly as in the authority table"
(`active-symbol-table-v023-20260905.md`). Four conflicts arose between that
table and the v0.25 successor vocabulary. Each is resolved in favour of the
table, with the successor term recorded here.

| Concept | Successor writes | **Authority table** | Decision |
|---|---|---|---|
| Beam occupancy | `n_b` | **`U_{s,v}(t)`** — 「波束 $(s,v)$ 目前服務的使用者數」, `[V]` ×3 | **Used `U_{s,v}`.** The table contains no `n_b`; its only lowercase beam counter is `n_{s,v}(t−1)`, a *pre-filter demand* count, which is a different quantity. `n_b ≡ U_{s,v}` is recorded in the CSV header comment. |
| Required RF power | "required power / cap" | `p^r`, `P^r` **deleted** (§9); use `p_{u,s,v}` = 「實際 RF 發射功率」 | **Used `p_{u,s,v}`.** `p_req` survives in the table only in prose and violates its own no-multi-letter-subscript rule. Under `a-r0` the committed power *is* `p_{u,s,v}`, so the axis is exact. |
| Off-axis angle | — | `θ_{u,s,v}`, 「偏軸角」 `[V]` §10.2 | **Used 偏軸角.** The table also contains 「離軸角」 once, in the concept-deck layer; §10.2 governs thesis body notation and the thesis text uses 偏軸角 16 times, 離軸角 zero. |
| Energy efficiency | pooled `ΣB/ΣE` | `η^N` 「network ratio-of-sums EE」 `[V]` §10.13.1 | **Used `η^N`**, not the per-link `η_{u,s,v}`. The plotted quantity is total beam bits over total beam energy — a ratio of sums — which is `η^N`'s definition, explicitly 「不是 per-row EE 平均」. |

**Three genuine gaps in the v0.23 authority**, flagged rather than papered over:

1. **Spectral efficiency and ACM are not in the table at all** — zero occurrences
   of 頻譜效率 or ACM across 769 lines. The v0.23 rate law is continuous Shannon
   (式 3.14). The successor's discrete MODCOD ladder is new physics, so the ACM
   annotation on Figure 1 uses the successor's own vocabulary and the mode names
   are carried in `figure1-data.csv` rather than on the axis. **This needs a
   symbol-table amendment before the figure goes into the thesis.**
2. **There is no "fixed-RF reference" identifier.** `grep` over both source trees
   returns zero hits. The figure therefore uses the successor's document
   identifier `b0` in the legend and annotates the line with the attested
   `p⁺ = 1.65 W（每波束 RF 輸出上限）` rather than coining 「固定射頻參考」.
3. **`E(x)` has no Chinese term** in the table, and `Δt` is marked retired. The
   figure avoids both by plotting energy only implicitly, through `η^N`.

**Units.** The table attests `bit/J` and never `Mbit/J` (zero occurrences), so
the EE axis is `bit/J` with a `×10⁷` multiplier shown by the axis formatter.
Angles use 「（度）」 with full-width parentheses, matching the table's Chinese
prose style (§4 line 123).

**Fonts.** Noto Serif CJK TC for Traditional Chinese, STIX for maths — a serif
pairing consistent with the deck's Times New Roman invariant. `pdf.fonttype=42`
and `svg.fonttype=none` keep the text selectable and re-styleable.

---

## 3. Figure 2 — what was inherited and what was added

**Inherited verbatim from `CORE-FLOW-DRAFT.svg`:** the three-lane swimlane
geometry (`x = 30 / 555 / 1075`, widths `490 / 470 / 495`), the full colour
palette and its route semantics, the Times New Roman 28/24/20 px type scale with
no intermediate sizes, the rounded-rectangle vocabulary (panels `rx=10`, cards
`rx=8`, badges `rx=4 h=34`), the 15 px left pad / 26 px first baseline / 28 px
line pitch rhythm, the four arrow markers, and the drop-shadow filter.

**Added, because the successor needs devices the draft had no use for:**

| Device | Encoding | Why |
|---|---|---|
| Information boundary | violet dashed vertical separator + two labelled ribbons | The draft had no information boundary; the successor's whole claim rests on `I_heads` vs `I_coordinator`. |
| Deadline / fallback path | amber dashed path with its own arrowhead | Mandatory in the successor and counted in `B` and `E`, so it cannot be left implicit. |
| Nominal → realised | green dashed separator before the endpoint card | The single most load-bearing invariant: selection is approximated, the endpoint never is. |

The draft uses **no dashing at all**, so dashing was free as a new semantic
channel — but because it is new, all three meanings are declared in a footer
legend. The draft's legend role was played by its header status pills; those are
kept and re-purposed (`PRIMARY: a-r0`, `ENDPOINT: 48 BOUNDARIES`, `PRE-SEALED`).

**One deliberate deviation.** The draft is entirely English; Figure 2 stays
English for continuity with it, even though Figure 1 is captioned in Chinese per
the thesis. If the thesis requires a Chinese Figure 2, the generator centralises
every string and can be re-run.

**Text fitting.** `figure2_build.py` carries an approximate Times New Roman
advance-width model and refuses silently-overflowing strings; the build currently
reports zero overflow warnings. This caught six real overflows during
development, including one ribbon line that had escaped checking entirely.

**Rendering.** SVG is the source. PNG and PDF are produced with headless Chrome
(no `rsvg`/`inkscape`/`cairosvg` on this host).

---

## 4. Reproducing

```
python figure1_compute.py     # writes figure1-data.csv
python figure1_selftest.py    # validates against the sealed KAT; exits non-zero on failure
python figure1_render.py      # writes figure1-angle-power-ee.{pdf,svg,png}
python figure2_build.py       # writes figure2-architecture.svg
google-chrome --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --screenshot=figure2-architecture.png --window-size=1600,1098 figure2-architecture.svg
google-chrome --headless --disable-gpu --no-sandbox \
  --no-pdf-header-footer --print-to-pdf=figure2-architecture.pdf figure2-architecture.svg
```

Requires `numpy`, `matplotlib`, `scipy` (self-test only) and a CJK serif font.

---

## 5. Scope discipline

No result number appears in any figure or specification in this directory.
Figure 1 is a **mechanism** figure computed from sealed physics constants;
Figure 2 is structural. Figures 3 and 4 exist only as specifications with
`⟨結果待填⟩` slots, and both specs carry explicit prohibition lists covering
Track F / pilot numbers, TEST-split quantities, and the sealed wording rules.
