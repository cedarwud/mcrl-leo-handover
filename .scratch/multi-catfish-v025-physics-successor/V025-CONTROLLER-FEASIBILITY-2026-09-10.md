# Feasibility — what would have to be true, checked against what is achieved

**2026-09-10 11:20 UTC. Arithmetic only, on receipts already on disk. No new compute.**
This calculation had never been done. Roughly 100 controller records and 80 KB of adversarial
audit contain no error budget, no required-accuracy figure, and no power statement for the
requirement as it now stands. Every question asked so far has been "what happened when I
measured X", never "what must be true for this to work at all".

---

## 1. Required accuracy of the heads

The composed score at `|A| = 100` is `sum_i d_i + Psi = +480.113 - 440.079 = +40.034`
*(`SELECTOR-DIAGNOSIS-2026-09-09.md` §3, normalised score/kappa units)*.

- Worst-case amplification `(|S| + |R|) / |V| = 22.985x`. A **1%** component error becomes up
  to **23%** error on the quantity actually ranked; **5%** becomes **115%**.
- The margin that must survive: the best single-user move is `8.02` against a summed term of
  `200.4` over 82 users *(`CORPUS-IS-SURROGATE` §2)*. So a per-user error above roughly
  **1.67%** of the summed term can reorder the top pair.

**Required per-user relative accuracy is therefore on the order of 1%, and better where the
top two catalogue rows are close.**

## 2. Achieved accuracy

`C1REAL`, declared target, exact path, held out:

| | sealed `(8,)` head | flexible model, same inputs | floor |
|---|---:|---:|---:|
| LOAO level `R^2` | `-0.2724` | `0.0933` | — |
| LOWO level `R^2` | — | `-0.0714` | — |
| top-1 | `0.1711` | `0.1854` | `0.1716` |

**A negative held-out `R^2` means the predictor is worse than the target's own mean.** Its
relative error exceeds **100%** of the target's spread.

**Required ~1%. Achieved >100%. That is roughly two orders of magnitude, and it is a property
of the target and the inputs, not of the optimiser.** A schema repair is running; it changes
effective dimension from 12 to 14. It would have to close two orders of magnitude.

## 3. Detectability of the required contrasts

| source | fact |
|---|---|
| contract v1 §, 2026-09-08 | a true **+1%** is **not detectable** with ~160 dates **under any seed count** if the date SD is ~5% |
| contract v1.1 amendment, 2026-09-09 | measured **three**-contrast conjunction power `0.675` at `delta* = +2%`, 16 seeds, 160 dates |
| requirement, 2026-09-10 08:55 | **six** contrasts, not three |
| corrected coordination band | `+0.899%` (8 anchors) / `+1.29%` (20 anchors) |
| archive erratum, 2026-09-09 | **166** TRAIN dates available against ~160 needed — **1.04x** headroom |
| `FINDING-ONE-DATE` | the learner has **D = 1** date; "at fixed D, adding seeds drives the contrast variance to `Sigma_date/D` and no further, **so more seeds cannot help**" |
| `learner.py:40` | the code runs **12** seeds; v1.1 requires **16**. This silently under-powers every conjunction test |

**Arithmetic.** If three contrasts conjoin at power `0.675`, a per-contrast power of
`0.675^(1/3) = 0.877` gives a six-contrast conjunction of `0.456` **under independence**. The
six contrasts share arms and are positively correlated, so the true figure is **higher than
`0.456` and lower than `0.675`** — the exact value is not derivable from the receipts, and I
do not claim it.

**That approximation is not load-bearing.** The direct statement is: the project's own contract
says `+1%` is undetectable with this archive **under any seed count**, and the band being
chased is `+0.899%` to `+1.29%`.

## 4. The conclusion this forces

**Two independent walls, either of which is sufficient:**

1. **Accuracy.** The heads must be ~1% accurate on a per-user quantity they currently predict
   worse than its own mean.
2. **Detectability.** Even with perfect heads, an effect in the `+0.9%` to `+1.3%` band cannot
   be established as significant with 166 dates, by the project's own power analysis — and the
   learner currently has one date.

**Neither wall is moved by fixing the corpus, repairing the schema, changing the decomposition,
or training longer.** Wall 1 is about the information in the inputs versus the margin in the
ranking. Wall 2 is about the archive versus the effect size.

## 5. What this does not say

- It does **not** say the mechanism is absent. The corrected coordination band is positive and
  measured: `+0.899%` and `+1.29%`.
- It does **not** say the heads are useless. Ordering `0.5889`, held out, is above chance.
- It does **not** settle whether a different decomposition has a larger band — but the band is
  a property of the physics, and the price-of-anarchy reading already put it near one per cent.
- It does **not** authorise abandoning anything. It states what would have to be true.

## 6. The choices this leaves, stated without preference

1. **Enlarge the effect.** Find a regime or an action space where the coordination band is
   materially larger than one per cent. The regime map has been swept and was non-monotone and
   below one per cent everywhere tested, including at 200 users and 80 Mbit/s.
2. **Enlarge the archive.** Generate more independent dates. `FINDING-ONE-DATE` names world
   generation as the longest-lead item, and it is blocked on an owner decision open since
   2026-09-09 that has not been re-raised. **This is the only wall-2 remedy that exists.**
3. **Change the claim** to one the evidence can carry: the exact ladder with intervals, the
   learned surrogate as *acceleration* of search against a stated deadline, the set-level
   correction reported at its measured size, and the negative results as negative results.
4. **Change the estimand** so the ranked quantity is not a near-cancelling difference. Two
   candidate decompositions exist; whether either enlarges the band is unmeasured.

**Options 1 and 2 are experiments. Option 3 is a decision. Option 4 is a design change.** None
of them is training, and training does not become informative until at least one is settled.

---

# ERRATUM to this record — 2026-09-10 11:35 UTC, before it was sent to any reviewer

**Section 1's amplification argument is withdrawn.** It used
`+480.113 / -440.079 / +40.034` and the `22.985x` figure from
`SELECTOR-DIAGNOSIS-2026-09-09.md`. `PATH-ARTEFACT-CHECKS-2026-09-10.md`, produced three hours
before this record, found that exact cancellation to be **inside the sampled mixed-path
artefact envelope**: over eight sampled anchors `|99*epsilon|` spans `127.2` to `2107.1` kappa,
`|Psi| = 440.079` sits inside it, and step 16 matches both magnitude (`-440.93`) and sign.
Its verdict: the `22.99x` conditioning figure is **not established**.

**I recorded that, and then used the same numbers as the basis of a wall three hours later.**
This is the same failure as the day's other retractions: a finding that was present, correct
and filed, and not applied.

**What survives, on path-clean evidence only.**

`8.02` (best single-user move), `200.4` (summed surpluses over 82 users) and the `20.5x` ratio
come from a different probe — `TARGET-DESIGN-2026-09-10.md` — which **explicitly corrected the
path mixing**: *"I corrected the probe to force both through `evaluate_many`. All numbers below
are from the corrected run."* It verified its gauge exactly: the target at the base action is
`0.0` in all 2,400 groups. Those numbers are clean.

**But the strongest form of wall 1 needs no derived arithmetic at all:**

> `C1REAL`: the sealed head's held-out **top-1 accuracy is `0.1711`**; the **constant
> predictor's floor is `0.1716`**. The flexible high-capacity model on the same inputs reaches
> `0.1854`.

**A head whose argmax agrees with the truth no more often than a constant predictor cannot
systematically select better configurations.** That is a direct measurement, path-clean, with
no conditioning argument, no amplification factor and no cancellation.

**Wall 2 is untouched.** It rests on the project's own power analysis and the archive count,
neither of which involves the evaluation path.

**Revised statement of the two walls:**

1. **Selection accuracy.** The declared C1 head's argmax is at the constant-predictor floor,
   and a high-capacity model on the same inputs barely moves it. *(A repaired schema, effective
   dimension 12 -> 14, is being re-tested.)*
2. **Detectability.** The contract states `+1%` is undetectable with ~160 dates under any seed
   count at date SD ~5%; the band being chased is `+0.899%` to `+1.29%`; the archive holds 166
   dates; the learner has one.
