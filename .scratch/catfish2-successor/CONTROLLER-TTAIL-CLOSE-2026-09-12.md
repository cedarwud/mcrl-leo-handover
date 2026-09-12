# Controller adjudication — `T_TAIL` closes; and the `A_repr` floor is not source-independent

Date 2026-09-12. Read against Amendment 15 §2B and §5. Figures re-derived by me from Lane Q's report and checked for
internal consistency against its own P0 counts (`d3ef4b02`, results `a47315cb`, code `bf907367`).

## 1. Distinctness passes; `A_repr` fails

| gate | value | line | verdict |
|---|---|---|---|
| distinctness | **0.41176** (`t = 1…9`) / 0.42017 (all steps) | ≥ 0.25 | PASS |
| **`A_repr`** | **0.4635** | ≥ 0.50 | **FAIL**, short by 0.0365 |

**`T_TAIL` closes before learner training**, per Amendment 15 §5. No retry with another clone family, split or
temperature — the protocol was frozen before fitting.

## 2. The failure is much worse than 0.0365, and this is the finding worth keeping

Lane Q measured the right control: **a clone carrying none of the privileged information — pure T0 imitation —
scores 0.5885 against `T_TAIL`.** That is not a coincidence, it is arithmetic: `T_TAIL` agrees with T0 on
`1 − 0.41176 = 0.58824` of decisions, so a perfect T0 clone scores ≈ 0.588 by construction. Predicted 0.58824,
measured 0.5885 — agreement to three decimals.

**So the frozen 0.50 floor sits *below* the trivial baseline for this source, and `T_TAIL`'s clone lands 0.125 below
that baseline.** The clone is *worse than learning nothing*. Supporting numbers, all pointing the same way: clone
top-1 is **0.0966** where `T_TAIL` differs from T0 against 0.7201 where it agrees — **under a tenth** of the
distinctive information survives; the clone matches T0 71.4 % against the teacher's 58.9 %, so the mechanism is
**collapse toward T0**, not collapse onto a few actions (28 slots used, entropy 3.183); all four TEST episodes sit at
0.441–0.488, each below its own floor; and 0/10,000 bootstrap draws reach 0.50.

## 3. What this means for the gate itself — and, honestly, for `T_NEXT`

**The `A_repr ≥ 0.50` floor is not source-independent.** A source's trivial baseline is its own agreement rate with
T0, so the floor is only meaningful for a source that disagrees with T0 more than half the time:

| source | disagreement | trivial baseline (pure-T0 clone) | `A_repr` | margin over trivial |
|---|---|---|---|---|
| `T_NEXT` | 0.5964 | ≈ 0.4036 | 0.5714 | **+0.168** |
| `T_TAIL` | 0.4118 | ≈ 0.5882 (measured 0.5885) | 0.4635 | **−0.125** |

**I am not changing the gate, and this does not rescue or re-decide anything.** `T_TAIL` fails the frozen 0.50 floor
on its own terms; the trivial-baseline analysis explains *why* the failure is decisive rather than marginal. And
applying the stricter reading to `T_NEXT` is a test its admission survives — it clears its own trivial baseline by
+0.168, more than twice its +0.0714 margin over the nominal floor. **That is corroboration, not retro-fitting: the
stricter standard was derived from `T_TAIL`'s data and `T_NEXT` was admitted before it existed, so it could have
overturned the admission and did not.**

**Recorded for any future source screen**: `A_repr ≥ 0.50` should be read alongside the candidate's own
pure-T0-imitation baseline. A fixed floor cannot serve sources with different agreement rates.

## 4. The consistency audit passed exactly, and my alternative hypothesis was wrong

I required `base_survived_not_chosen == 0` before any distinctness number could be read. It is **0**, and all 10,084
disagreements decompose onto a tail filter — 25 on served, 10,059 on p10, **0** on the T0 score. My explanation (1)
holds: served and p10 *filter* heavily (9.08 % and 99.38 % of decisions) while *uniquely deciding* almost never
(0.0 % and 0.68 %), which is why 0.41 disagreement coexists with the T0 score deciding 99.32 % of the time.

**My explanation (2) was wrong and is structurally excluded.** I hypothesised that T0's score might be evaluated
under a different lit set than the joint action was built under. It cannot be: `R_u` is the first legal argmax of the
*same* `t0_scores` row, and that score reads only raw `channel_quality` and previous-step `beam_loads`
(`cf_teacher.py:72-81`) — **it carries no lit set at all.** The concern was worth raising and the measurement
answered it against me.

The honest description of the source is therefore **"T0 restricted to the actions surviving a service-tail
filter"** — which is exactly why its clone collapses toward T0 and why the privileged tail information does not
survive the 113-dim bottleneck.

`served` and p10 were cited at `file:line` as required; 24 tests green; 11 named mutants each individually red,
including `B − ηE` promoted above the tail terms and both trajectory-mutation variants. The cost projection was 15.5 %
conservative (realised 4,943 s ≈ 21 min against 5,847 s projected), from mean legal actions 26.24 rather than the
smoke's 28.0.

## 5. Portfolio state

| source | outcome |
|---|---|
| `T_H` | CLOSED — no separation from seed variation on two seeds |
| `T_DELTA` | CLOSED — clone reached `R_repr ≥ 0.5` only by shedding 18 % of the bits |
| **`T_NEXT`** | **ADMITTED** — the sole survivor; clears both gates and its own trivial baseline |
| `T_TAIL` | CLOSED — `A_repr` 0.4635, below both the floor and its own trivial baseline |

**Three of the four sealed candidates are closed and no fourth family may be added** (Amendment 15 §1). `T_NEXT`'s
k = 8 five-arm matrix is now the only path to a second Catfish, and it proceeds exactly as declared: `delta_DEV`
frozen at +1.0 %, the Bernoulli-matched null at `p_singleton = 9395/24000`, `--episodes 300 --stop-after 100`. The
drop-one criterion decides, and nothing from P0 or `A_repr` substitutes for it.

**If k = 8 fails, Amendment 15 §9 applies without exception**: the search stops, nothing is relaxed or swept, no
source is reopened, the single-source S1 is **not** launched under a "Multi-Catfish" framing, and the evidence returns
to the owner. Formal S1 remains PARKED and untouched.
