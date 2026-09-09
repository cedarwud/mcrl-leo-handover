The peer is still iterating on the deck build. I'll let the monitor finish rather than race it — here's where things stand.

**Done and verified (`figures/`, entirely my lane, no collisions):**

- **Figure 1** — recomputed from the sealed equations, not transcribed. Independent Bessel series + bisection; `figure1_selftest.py` passes every check against the sealed KAT: all three Γ_r values, the cap-hit angle to all 15 digits (0.853069795148802°), the pattern vs scipy to 3e-15, and all 16 oracle rows. Two findings recorded: γ_PHY,min is a *separate sealed service-threshold constant* (−1.44181246 dB) rather than the lowest MODCOD threshold, and the note's `0.853070` rows are evaluated at the exact cap-hit angle. PDF+SVG+PNG+CSV.
- **Figure 2** — extends `CORE-FLOW-DRAFT.svg`'s exact lane geometry and palette; adds three declared dash semantics (information boundary, deadline/fallback, nominal→realised), all in a legend since the draft used no dashing. PDF now single-page at the figure's own aspect.
- **FIG3-SPEC / FIG4-SPEC** — axes, units, interval construction, and the point most easily got wrong: the drawn bar is the central 95% percentile interval but **the decision is the one-sided 2.5th-percentile lower bound**, with the measured under-coverage (0.89–0.92 vs 0.95 nominal) mandatory on the figure and no post-hoc widening.
- **FIGURE-NOTES.md** — provenance plus four symbol conflicts resolved toward the authority table (`U_{s,v}` not `n_b`; `p_{u,s,v}` since `p^r` was deleted; 偏軸角; `η^N`) and three genuine gaps flagged: **ACM/spectral efficiency appear nowhere in the v0.23 symbol table**, there is no attested "fixed-RF reference" identifier, and `Mbit/J` is unattested. These need a symbol-table amendment before the figure enters the thesis.
- **STORYBOARD-DELTA.md** — 38 pages verdicted (9 KEEP / 18 REWRITE / 11 DELETE + 10 NEW), with the invalidation traced to the three named succession events, and two DELETE verdicts explicitly flagged as resting on absence-from-corpus rather than a retiring document.

**One thing I need to flag rather than resolve unilaterally:**

Another agent is concurrently writing the deck deliverables into the *same* `slides/` directory — `v025-deck-skeleton.pptx`, `native_math.py`, `build_v025_deck.py`, `deck_content.py`, `build-report.json`. It is still actively building (last write 70 seconds ago; the deck has grown 34 → 37 slides). I verified it read-only: 37 slides, 18 well-formed OMML equations, 0 malformed, symbol-authority-correct LaTeX (`U_{s,v}`, `p_{u,s,v}`, `G^T(θ,θ_3)`, `γ⁻ = −1.4418 dB`).

I did **not** overwrite any of it, and I stopped building my own competing deck. Producing `v025-deck-skeleton.pptx` from my lane would mean destroying an in-progress artifact I didn't create, at the exact same path — that is not a call I should make silently. I've preserved my delta at `_work/STORYBOARD-DELTA-opus5-lane.md` in case the peer overwrites `slides/STORYBOARD-DELTA.md` with its own.

`slides/OUTLINE.md` does not exist yet. Once the peer settles I'll either confirm it wrote one, or write one that mirrors the deck that actually exists — writing it now would both race the build and describe a deck that is still changing.
