# What is actually sealed, and what I have been wrongly treating as sealed

**2026-09-10 14:10 UTC. Verified mechanically by grepping the contract
(`V025-STAGES-6-8-CONTRACT-v1` and amendments) and every priority declaration v1.0-v1.9.**

Prompted by the owner pointing out that the learning rate is not a sealed value and that its
appropriateness is a **convergence** question, not a tuning question. The check then generalised.

---

## The audit

| constant | in contract or a declaration? | where it actually lives |
|---|---|---|
| `learning_rate` | **NO** | `learner.py:48, :53, :58`, plus an inconsistent default `0.02` at `:334` |
| `gauge_beta` | **NO** | `learner.py:44-62` |
| hidden layer sizes | **NO** | `learner.py:44-62` |
| activation | **NO** | `learner.py:44-62` |
| Adam betas | **NO** | `learner.py:44-62` |
| checkpoint cadence | **NO** | `learner.py`, `CHECKPOINT_EVERY_SOURCE_EPOCHS` |
| **epoch cap 2000** | **NO** | an implementation guard in `learner.py` |
| catalogue caps (8,192 / 1,500 rows) | **NO** | probe/engine literals |
| seed count 16 | **YES** (2 docs) | v1.1 amendment |
| **10 s coordinator budget** | **YES** (2 docs) | contract v1 §F2 |
| decision margin `+0.5%` | **YES** (6 docs) | contract v1 |
| three forecast offsets | **YES** (1 doc) | contract §C2 |

## What I got wrong, and how often

I have written **"the sealed head literals, unchanged"** into most worker prompts today. The
head literals are **not sealed**. They are implementation defaults, and the file even
contradicts itself: three per-route values plus a fourth default of `0.02`.

I have also written that the **"sealed checkpoint format rejects more than 2,000 epochs"**, and
used it to conclude that a 9,000-epoch protocol **"cannot be expressed"**. That bound is an
implementation guard, not a sealed protocol. It can be changed by changing code, with the
consequences that follow — it is not a scientific constraint.

**This is the same error three times today in a different guise:** treating a question of
**instrument validity or implementation** as a question of **scientific sealing**. The other
two were the training gate G1 (which asked me to predict a measurement before permitting it)
and the feasibility wall built on a figure I had myself recorded as not established.

## The distinction I had been collapsing

- **Scientific sealing** — the objective, the numerator, the fading-quantile scoring
  convention, the service guard, the decision margin, the arm inventory's meaning. Changing
  these requires a **declared policy change** with a rationale independent of any result.
- **Compatibility pinning** — parameter shapes that a checkpoint schema digest depends on,
  values that earlier receipts were produced under. Changing these requires a **new version**
  and re-running affected comparisons. It is bookkeeping, not adjudication.
- **Implementation defaults** — learning rate, activation, layer widths, cadences, caps.
  Changing these requires only that the change be **declared before the measurement that
  judges it**, and that the selection criterion be stated and outcome-independent.

**A learning rate that diverges makes a measurement invalid.** Checking it is mandatory, not
permitted. `LRSWEEP` was dispatched at 14:02 on that basis: seven points per route across three
orders of magnitude, **selected by convergence only, with no EE quantity computed in that job
at all.**

## One genuinely sealed thing with an undefined term

Contract v1 §F2 seals the **10 s** budget — *"on the declared worker count"*. **A grep finds
no declaration of that worker count anywhere in the contract or any amendment.**

`SELECTOR-LATENCY-2026-09-10.md` measured the deployed path on **one worker on a machine at
load ~15**, and found median `12.014 s` with a 65% miss rate. **Against an undefined worker
count, that measurement cannot be compared to the budget as a compliance verdict** — it
establishes that one contended worker does not suffice, and that `_catalogue_with_census`
(median `8.299 s`) dominates.

**Owed:** the declared worker count must be named before any deadline-compliance claim is made
in either direction. Until it is, latency results are reported as measured configurations, not
as passes or failures against §F2.

## What this does not license

It does not license changing anything to make a result come out. Every one of the unsealed
values above still obeys the same rule: **declare the change and its selection criterion before
the measurement that judges it, and make the criterion independent of the outcome.** The
difference is only in what kind of declaration is required, and from whom.
