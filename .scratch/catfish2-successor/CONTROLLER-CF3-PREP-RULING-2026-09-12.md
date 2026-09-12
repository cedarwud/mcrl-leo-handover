# Controller ruling on CF3-PREP — the `T_B` / `T_E` decomposition is not worth running

Date 2026-09-12. Ruling on the design-only note `CF3-PREP-DESIGN-NOTE-2026-09-12.md` (`7ae2df6a`). **No `T_B`/`T_E`
round is opened. This changes nothing in Amendment 15, which remains sealed to three families, and it is not a fourth
family by another name.** The note collected no candidate outcome, and neither does this ruling.

## 1. Accepted: not worth running

The lane was asked whether `T_DELTA = ΔB − η₀·ΔE` can be cleanly decomposed into `T_B` and `T_E` without changing the
simulator or inventing coefficients. It answered no, and gave four reasons I accept. The two decisive ones:

**`T_E` is not well-defined in this physics.** Joules are SINR- and interference-free, so `ΔE` is **exactly zero** for
every candidate joining a lit beam below its maximum. The argmin is then resolved by the action-slot index — and
Amendment 15 §2A forbids treating the user-relative slot number as a physical identity. `T_E` would be a
tie-break masquerading as a source. That is a physics fact about v023, not a tuning problem, and no authorised
constant could repair it.

**The split opens no new information axis.** T0 = LP-prev(1,0) is already a crude scalarisation of exactly this pair
(`cf_credit.py:34-35`). Separating the two terms does not reach information T0 lacks; it re-weights information T0
already carries. That is the same defect that closed the original Stage 0 at zero survivors, and Amendment 15 §6's
successor clause requires a new source to target information T0 does **not** already use.

**The precedent the lane nearly missed and then found.** Stage 0 already specified, measured and **rejected** this
exact bisection one information level down — link endpoint 0.1982, activation endpoint 0.2567, with the recorded
conclusion that *the `c = 1` mixture, not either term, is where the value sits*. The lane then did the right thing
under the project's standing rule that an old failure transfers only when its cause is also present: it asked whether
the cause transfers, judged it criterion-level and therefore likely to, and named the one way it might not.

The tautology defect is inherited exactly, one term each — `R_u` is in the candidate set, so `ΔB(T_B) ≥ 0` and
`ΔE(T_E) ≤ 0` are guaranteed, and any `CR` or better-fraction computed on a source's own term is ≈ 1 or ≈ ∞ by
construction. The note's §5.1 gives a workable design fix (never self-score a gate; cross-score; pre-gate on
`disagreement(T_i, T_DELTA)`), which is worth keeping for any future privileged source **whether or not it is ever
`T_B`**.

Compute was never the blocker: ~2,638 evaluations/step, both sources plus `T_DELTA` from one pass, ≈ 1.5 CPU-hours
and ~25 minutes on four shards. **The reason not to run it is that its result would not be interpretable, not that it
is expensive.**

## 2. A retrospective finding that strengthens the `T_DELTA` closure

Re-reading `T_DELTA` against the standard `T_TAIL` later produced — the candidate's **own pure-T0-imitation
baseline** — gives a number nobody had computed at the time. Verified by me from figures I had already checked
independently:

| source | disagreement with T0 | trivial baseline (`1 − disagreement`) | clone top-1 / `A_repr` | **margin over trivial** |
|---|---|---|---|---|
| **`T_NEXT`** | 0.5964 | 0.4036 | 0.5714 | **+0.168** |
| `T_DELTA` | 0.79121 | 0.2088 | 0.2198 (selected clone) | **+0.011** |
| `T_TAIL` | 0.4118 | 0.5882 | 0.4635 | **−0.125** |

(BC gives `T_DELTA` +0.022; the selected soft clone gives +0.011. The lane's slightly different disagreement figure,
0.79046 against my 0.79121, changes nothing.)

**`T_DELTA`'s clone beat "learn nothing" by about one percentage point** — an order of magnitude below `T_NEXT`, and
its clone-versus-T0 agreement of 0.39/0.51 against the teacher's 0.21 is collapse toward T0, the same mechanism that
later killed `T_TAIL`.

This does not change the `T_DELTA` verdict, which was already CLOSED on the non-degeneracy failure (the passing clone
reached its EE ratio by shedding 18 % of the bits). It **strengthens** it: `T_DELTA` was failing on representability
as well, and we could not see it at the time because the trivial-baseline standard did not exist yet — it was derived
from `T_TAIL`'s data two candidates later. Recorded so the closure rests on the fuller picture.

**The consequence for the portfolio is worth stating plainly: of four sealed candidates, exactly one clears its own
trivial baseline, and it clears it by 0.168.** `T_NEXT`'s admission looks better after this scrutiny than before it,
and that scrutiny was not designed to favour it.

## 3. Disposition

CF3-PREP is closed. Its note is kept for two things and nothing else: the `T_E` degeneracy finding, which is a
permanent physics fact about v023 and should stop this idea being re-proposed; and the §5.1 non-self-scoring gate
design, which any future privileged-source screen should reuse. **It is not authority for a fourth family**, and the
question of whether a third-Catfish round ever happens remains the owner's, conditional on `T0 + T_NEXT` succeeding.

The critical path is unchanged: Lane M's integration closure, then the k = 8 five-cell matrix, then a concurrent
k = 9 on an unambiguous pass. Formal S1 remains PARKED.
