# Controller adjudication of the `T_DELTA` S diagnostic — two of the three gates are tautological; proceed on the third

Date 2026-09-12. Every figure re-derived by me from `results/DIAG-S.json` in the B0 worktree. The lane stopped at the
gate, declared no verdict, and disclosed the problem with its own result before I could find it.

## 1. Verified

| quantity | value |
|---|---|
| decisions | 24,000 (DEVVAL `9_211_000+i / 9_212_000+i`, i = 0…23, T0's own greedy trajectory) |
| **disagreement** | **0.79121** (18,989 / 24,000) |
| candidate-better fraction | 0.99958 |
| `CR` | 6717.06 |
| Σ positive / Σ negative | 1.18352e14 / 1.76196e10 bits |
| median Δ | +4.712e9 |
| **QoS-invalid fraction** | **0.06325** (1,201 / 18,989) |
| chosen outage | **0** |

Cheap-path parity **PASSED** on 4,000 DEV decisions, **all with ≥ 2 legal actions and no exact ties**: 4000/4000
action identity, max relative score deviation 2.684e-14 against a **minimum** top-1/top-2 margin of 9.257e5 bits —
**9.13 orders of magnitude** of headroom. The lane also corrected its own framing: the cheap path removes only the
100 without-`u` evaluations from ~2,901 per step (**3.6 %**), so it ran S on the **full evaluator throughout** and
said so rather than falling back silently.

## 2. Two of the three gates are near-arithmetic identities, and I verified the algebra

`D_u(a) = B_u^D(a | R_{−u}) − η₀ E_u^D(a | R_{−u})`. The `without-u` term does not depend on `a`, so

    D_u(a) − D_u(R_u) = [B_total(a, R_{−u}) − B_total(R_u, R_{−u})] − η₀ [E_total(a, R_{−u}) − E_total(R_u, R_{−u})] ≡ Δ(a)

— the baseline cancels exactly. And `T_DELTA ≡ argmax_a D_u(a) = argmax_a Δ(a)`, while T0's own action `R_u` is one of
the legal candidates. Therefore **`Δ(T_DELTA's choice) ≥ 0` always, by construction.**

The data confirm it almost exactly: better-fraction 0.99958 rather than 1.000 (10 exceptions in 24,000, the unserved
edge cases), and `Σ negative / Σ positive = 1.5e-4`.

**So `CR = 6717` and candidate-better = 0.99958 carry essentially no information about this candidate.** They are
properties of the construction. In Stage 0 the same gate meant something because seven *independent* rules were
scored against a Δ none of them optimised; here the candidate **is** the argmax of the scoring functional. This is the
project's recorded "near-tautological result" failure mode — the move class and the reference share a construction —
and it must never be reported as evidence of complementarity. **A `CR` of 6717 in the paper would be a red flag to a
reviewer, not a strong result.**

The lane found this itself and disclosed it as something for me to weigh rather than as a verdict. That is the
behaviour that makes its numbers usable.

## 3. What actually survives as evidence

1. **Disagreement 0.79121** — not guaranteed by construction, and it clears the inherited 25 % convention by a wide
   margin. `T_DELTA` is genuinely behaviourally distinct from T0.
2. **QoS-invalid 0.06325, the lowest of any arm measured on these episodes** — its 79 % different choices are the
   least QoS-destructive measured here. Not guaranteed.
3. **Zero outage choices** — the validated outage charge holds closed. Not guaranteed.

What is **not** established by S: anything about whether `T_DELTA`'s advice is usable by a learner. That was always
the real question for a privileged teacher.

## 4. Ruling: the inherited gates pass; authorise the declared J/C + frozen `R_repr` stage

Read literally, all three inherited gates pass (0.79121 ≥ 0.25; 0.99958 ≥ 0.30; 6717 ≥ 0.5), so the owner's close
condition is not met and closing now would be closing on the strength of an **uninformative** reading. Two of the
gates should be treated as vacuous, but the one that is informative passes overwhelmingly and the QoS evidence is
genuinely favourable.

The decisive test was never "does `T_DELTA` beat T0 on `T_DELTA`'s own objective" — it does, by definition. It is
**§7d: can a 113-dim deployable clone carry the information?** `T_SEQ` — a structurally similar privileged
teacher whose advantage was counterfactual rather than a feature — died exactly there at `R_repr` 0.13–0.15. That
screen is cheap, frozen and pre-declared, and running it is the whole reason §7d exists.

**Authorised: the already-declared J/C + frozen `R_repr` stage. `R_repr ≥ 0.5` is the decision gate. Nothing beyond
it is authorised — no RL training, no D3-T_DELTA arm, no integration work.**

## 5. Pre-registered before the stage runs, so it cannot become a post-hoc excuse

**The herding concern is registered now.** `T_DELTA` is a *unilateral* best response around T0's joint reference and
79 % of users would move. Applying that simultaneously is exactly the construction the oracle cells measured as
**throughput-degenerate**: A-real herds 65–100 of 100 users per step with p10 at 0.27 × the rule and a ~4-step
oscillation. The declared standalone joint rollout (the `J` of `J/C`) is the diagnostic for this, and §7c's rule
stands unchanged: **a joint-rollout failure is not by itself disqualifying and must not be read as absence of useful
per-user specialist information.** But it must be measured and reported, and the concern is on the record before the
number exists.

**Reporting discipline for the stage**: `CR` and candidate-better must be reported as near-arithmetic identities of
the construction, explicitly, wherever they appear. They may not be cited as evidence of complementarity in the
report, the registry or the paper.

## 6. The mapping deviation, ratified

The T0 / T_SEQ screens read `R_repr` on the formal-evaluation and calibration sets, which Amendment 14 §5 forbids this
lane. The lane's declared substitute — **DEVVAL split into disjoint halves A (i = 0…11) and B (i = 12…23), reported
separately** — preserves what the two-set protocol is for: an admission read on two disjoint sets rather than one.
**Ratified.**

Two conditions. First, **the halves carry 12 episodes each rather than 24, so each estimate is noisier than the T0
screen's and that must be stated with the numbers** — a marginal `R_repr` near 0.5 on 12 episodes is not the same
evidence the T0 screen produced on 24. Second, the reference endpoints are already measured
(`A m=2dB` 112,695,867 / 110,451,526; T0 118,456,992 / 116,858,218 bit/J), so the admission denominators are fixed at
**5.761 M (A)** and **6.407 M (B)**: the clone must beat the rule by ≥ 2.88 M and ≥ 3.20 M respectively to reach
`R_repr = 0.5`. Those denominators are frozen by this ruling and may not be recomputed after the clone is fitted.

## 7. If `R_repr` fails

`T_DELTA` closes, and with `T_H` already closed the bounded Catfish-2 search returns to the owner as **exhausted**
under Amendment 14 §11 — with the single-source S1 as the prepared fallback and the framing decision the owner's.

---

# ERRATUM, 2026-09-12 — §6's frozen denominators were wrong and are withdrawn

Raised by the owner before any clone outcome existed. I verified it against the pre-outcome declaration and the owner
is right. **§6 above is superseded by this erratum; the original text is left standing so the error is auditable.**

## What I got wrong

`PROGRESS-PHASE-B0.md` line 82 declares, prospectively: **"teacher = the `T_DELTA` joint rollout (**J**) on the same
set."** Lines 79–81 declare **rule = `A m=2dB`**, with a `rule = T0` variant reported only as a **sensitivity**.

I froze `EE(T0) − EE(A m=2dB)` = 5,761,125 (A) and 6,406,692 (B) as the admission denominators. Those are **T0
headroom**, not teacher headroom — and worse, they take a quantity declared for a different role (T0 as an alternative
*rule*) and use it as the *teacher* term. That is not the declared protocol, and I reinterpreted it rather than
reading it.

`J` has not run, so the declared denominator **cannot be known yet**. My instinct to freeze it immediately was right
about the discipline and wrong about the arithmetic: freezing a number that does not exist yet produced a wrong number
instead of a commitment.

## The correct contract

For each declared half `h`:

    den_h      = EE(J_h) − EE(rule_h)
    R_repr_h   = [ EE(clone_h) − EE(rule_h) ] / [ EE(J_h) − EE(rule_h) ]

with `rule = A m=2dB` and `J_h` the exact `T_DELTA` joint rollout on the same half. **The T0–rule gaps are retained
only as a labelled sensitivity/context number and are not the admission denominator.** The hard-coded `5_761_125` and
`6_406_692` must be removed from `cf2s_agg.py` as admission denominators.

## How the anti-outcome-shopping discipline is preserved instead

`J` is independent of clone fitting, so the commitment still happens before any outcome is read: (1) J may run
concurrently with C; (2) when J lands, compute `EE(J_h) − EE(rule_h)` for both halves; (3) record the two values and
their source hashes; (4) **freeze them before reading any closed-loop clone outcome**; (5) only then compute the point
`R_repr`. That is a genuine pre-commitment without substituting T0 for the declared teacher.

## Bootstrap — also corrected

Holding the denominator fixed inside the bootstrap is **not** the inherited protocol. The T_SEQ screen resampled the
**same episode indices** for clone, teacher and rule together and recomputed

    R_repr_b = [ EE(clone_b) − EE(rule_b) ] / [ EE(teacher_b) − EE(rule_b) ]

on every draw. Use that same procedure. It matters here because each declared half carries only 12 episodes. The
bootstrap stays **supplementary**, exactly as in the inherited screen — **no new lower-confidence-bound admission rule
is invented.** The admission rule remains the inherited point rule: `R_repr ≥ 0.5` on **both** declared halves for at
least one declared clone, subject to the existing non-degeneracy checks.

## Pre-declared now: what happens if the denominator is not positive

The herding pathology registered in §5 makes this a live possibility. If, on either half, **`EE(J_h) ≤ EE(rule_h)`**,
then the positive-headroom interpretation of `R_repr` is undefined for the inherited admission screen. In that case:

- **do not** substitute T0 as teacher;
- **do not** take an absolute value of the denominator;
- **do not** flip the inequality;
- **do not** invent an action-accuracy threshold;
- **do not** call a negative or undefined ratio a representability pass.

Mark that half's inherited `R_repr` admission test **not applicable / non-identifiable, because the declared teacher
supplies no positive EE headroom over the rule**, report the held-out imitation and regret metrics diagnostically, and
**stop before any RL learner training** for controller adjudication. This would **not** prove the per-user privileged
information useless; it would mean the inherited closed-loop instrument cannot supply its intended admission evidence
for this teacher. **The instrument is not repaired after seeing J.**
