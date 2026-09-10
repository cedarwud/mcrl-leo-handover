# Figure plan — and what each figure requires the runs to record

**2026-09-10 13:00 UTC. Written before the first training run, because a figure specification
is an input to a measurement specification, not an output of one.** Deciding the axes after
the run risks discovering the run did not record what a figure needs.

The thesis currently contains **two** images in total: one historical-baseline diagram in
§2.1 Related Work, and the system model in §3.1.1. **There are no results figures.**

Every axis below names its reference, information class, estimand and numerator, because a
figure inherits those from its data and a mislabelled axis is the same defect as a mislabelled
number.

---

## A. Figures that do not depend on the training outcome — buildable now

### F1 — Anytime quality curve *(the motivation figure)*

- **y:** pooled EE, Mbit/J, declared full-buffer numerator
- **x:** wall-clock search budget, seconds, log or linear from 0 to convergence
- **marks:** the contract's **10 s coordinator budget** (v1 §F2) and the **30.08 s** anchor
  interval; the converged fixed point as an asymptote
- **status: measured.** `ANYTIME-UNILATERAL-2026-09-10.md`, SEALED pooled curve:
  base `3.724824` → 10 s `15.336646` → 20 s `22.535029` → 30.08 s `25.846321` →
  convergence `30.786890`
- **why it is the motivation:** at the contract's own budget the search holds `42.91%` of its
  prize. That gap is what a learned coordinator exists to close.
- **must state:** traversal order (first-improvement), provisioning rule, panel identity

### F2 — The value ladder *(where the EE actually lives)*

- **y:** pooled EE, Mbit/J
- **x:** categorical — carrier incumbent · one-shot per-user best response · unilateral fixed
  point · bounded joint optimum
- **status: `PANELCEIL` is computing this on the training panel.** Must be one panel; the
  existing `+0.899%` (8 anchors) and `+100.7%` (20 anchors) are **on different panels and may
  not be stacked**.
- **must state:** which fixed point, since traversal order alone moves it by `8.13%` (SEALED) /
  `1.62%` (MARGIN_Q) — roughly nine times the coordination band

### F3 — Per-date distribution of the coordination gain

- **y:** relative pooled EE gain over the unilateral fixed point, %
- **x:** date (30 TRAIN dates), sorted or as a distribution
- **marks:** mean `+0.717%`, 95% t interval `[+0.436%, +0.997%]`, and the **4 of 30
  non-positive dates**
- **status: measured**, `CEILING30-MARGIN-2026-09-10.md:34`, date SD `0.751%`
- **why it matters:** it shows the effect's spread honestly, and the non-positive dates are
  part of the result, not noise to be smoothed

### F4 — Regime map

- **y:** coordination gain, %
- **x:** offered load (users) — **second panel:** rate target (Mbit/s)
- **status: measured**, 11 points, **never above 1%** on any axis swept, including 200 users
  and 80 Mbit/s
- **why it matters:** it is the evidence that the coordination band is not a regime artefact,
  and it bounds what any decomposition can partition

### F5 — Mode-selection headroom at fixed power *(diagnostic, clearly labelled)*

- **y:** pooled EE, Mbit/J
- **x:** categorical selection rule — declared · stale-CQI at 0 dB · stale-CQI at −1 dB ·
  realised-SINR oracle
- **also plot:** decode-failure rate on a second axis, since a rule that raises credited bits
  while raising failures is not a gain
- **status: measured**, `MODE-CAUSAL-REACHABILITY-2026-09-10.md`; **carrier-assignment panel,
  base `3.89` Mbit/J** — must be labelled as such and **must not** be presented as transferable
  to the fixed point

---

## B. Figures that require the training run — and the fields they need recorded

### F6 — Ablation

- **y:** pooled EE, Mbit/J, declared full-buffer numerator
- **x:** categorical arm — `ALL_NEUTRAL_CONTROL` (**the reference**) · `DROP_C1` · `DROP_C2` ·
  `DROP_C3` · `FULL`
- **also plot, per amendment 2:** the **all-knockout** selection computed from the `FULL`
  checkpoint, so the primary contrast can be shown not to be a knockout contrast
- **requires the run to record:** per-arm pooled bits, pooled joules, committed selection per
  anchor, served count, rate-target attainment, deadline-miss rate

### F7 — Training trajectory

- **y:** contrast `FULL − ALL_NEUTRAL_CONTROL`, relative %
- **x:** epoch, at the five checkpoints (100/200/300/400/500)
- **also plot:** each `FULL − DROP_Ci`
- **why:** the pre-declared continuation rule is about **convergence, not direction** — a flat
  contrast and a moving one are different findings, and only this figure distinguishes them
- **requires the run to record:** the contrast at **every** checkpoint, not only the last

### F8 — Recovered fraction under budget *(the acceleration axis)*

- **y:** pooled EE attained as a fraction of the certified fixed point's, %
- **x:** wall-clock budget, with the contract's 10 s marked
- **series:** each learned arm, **plus the anytime incumbent at the same budget** — the receipt
  requires the comparator to be the anytime incumbent, not the base configuration
- **requires the run to record:** physics evaluations consumed per arm, and wall-clock to
  decision, so "acceleration" has a denominator

---

## C. What this changes about the training run

The first-run pre-declaration already requires per-arm pooled EE, the contrasts at every
checkpoint, service co-reports and deadline misses. **F8 adds two fields that were not
required: physics evaluations consumed per arm, and wall-clock to decision.** Without them the
acceleration axis cannot be plotted and a second run would be needed.

**Added to the run's recording requirements.**

## D. Count

**Eight figures**, of which **five are buildable now** (F1–F5) and three wait on the run.
Method figures for the three routes wait on the decomposition decision and are not listed here.
