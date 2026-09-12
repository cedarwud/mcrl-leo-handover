# Controller record — the k = 8 matched null, `p_singleton`, and Lane M's READY definition

Date 2026-09-12. **Owner execution delta**, recorded before any k = 8 outcome exists. It invokes the exception clause
Amendment 15 §6 already anticipated; it changes no gate, no `delta_DEV`, and no source definition.

## 1. The fixed two-proposal null is rejected as the scientific comparator

Lane M demonstrated the matching defect prospectively. For `FULL{T0, Ti}`, `|A_CF| = 1` whenever the two teachers
agree and `2` when they disagree, whereas the old random two-proposal null is cardinality 2 whenever at least two
legal actions exist. It therefore does not match a FULL arm whose teachers sometimes agree — and a set of two is
mechanically easier to satisfy than a set of one, so an unmatched null would not be a like-for-like control.

**`RANDOM-LEGAL-SET-BERNOULLI-MATCHED-v1` is selected as the k = 8 scientific null.** The old fixed null may remain in
engineering code and history; it is **not** a k = 8 comparator. **Both nulls may not be run with a choice made later.**

## 2. `p_singleton`, verified by me from the raw artefact

Frozen: **`p_singleton(T_NEXT) = 9395 / 24000 = 0.39145833333333335`**.

Re-derived from `results-lane-n/P0-DATASET.npz` rather than from any report:

- `9395 + 14605 = 24000` exactly.
- The npz carries the `t = 1…9` block only (21,600 rows). Counting `y == t0` there gives **8,717 agreements /
  12,883 disagreements**, i.e. disagreement **0.5964352** — reproducing Lane N's headline to seven decimals.
- The residual `t = 0` block is therefore `9395 − 8717 = 678` agreements of 2,400 → 0.2825, i.e. `t = 0` disagreement
  0.7175. Consistent.
- **Legality: `mask.sum(1)` over all 21,600 rows has min 21, max 28, mean 26.04, with zero rows at 0 legal and zero
  rows at 1 legal.** Every row admits at least two legal actions, so **no forced-singleton correction is required** —
  the owner's independent check is confirmed against the artefact. (The `t = 0` block is not in the npz; Lane N's
  activation accounting gives it 28 legal actions per row, all legal at reset, which is consistent.)

**Frozen into the run identity**: numerator `9395`, denominator `24000`, the exact rational, the decimal
representation, the `T_NEXT` source identity, the P0 artefact digest, and the matched-null identity. `p_singleton` and
the null mechanism identity **must enter the configuration hash**, and the null must read **no per-state agreement
information** — only its declared DEV-NULL stream.

## 3. A step-structure caveat, declared now because I found it before any k = 8 result

`p_singleton` is a **marginal** rate, and the singleton rate is not uniform across the episode:

| step block | decisions | agreements | singleton rate |
|---|---|---|---|
| `t = 0` | 2,400 | 678 | 0.2825 |
| `t = 1…8` | 19,200 | 6,317 | 0.3290 |
| **`t = 9`** | 2,400 | **2,400** | **1.0000** |
| all | 24,000 | 9,395 | 0.3915 |

`t = 9` is singleton **by construction** — it is `T_NEXT`'s mandatory final-step T0 fallback, not agreement. So a
uniform Bernoulli at 0.3915 over-produces singletons at `t = 0…8` and under-produces them at `t = 9`, even though the
marginal matches exactly.

**I am implementing the marginal exactly as frozen and not modifying it.** A step-conditional null would match more
closely, but the owner froze the marginal, I am seeing this decomposition before any outcome exists, and switching now
would substitute my judgement for a prospective freeze. **The correct treatment is to measure it, not to pre-empt it.**

Amendment 15 §7 already requires the FULL arm's teacher-set cardinality distribution to be reported. That requirement
is extended: report the realised FULL `|A_CF| = 1` rate **and its per-step breakdown**, against both the frozen
`p_singleton` and the null's realised singleton rate. Two known sources of divergence must be read together —

1. this step-structure mismatch, and
2. the fact that `p_singleton` is estimated on the **P0 (T0-committed) state distribution**, while the k = 8 FULL arm
   visits the **learner's own** states,

— and if the realised rates diverge materially from 0.3915, the FULL-versus-null comparison carries that caveat
explicitly. I make no claim about which direction either effect pushes; establishing that would need evidence I do not
have.

## 4. Identity discipline

The Bernoulli-matched null is a different mechanism from `RANDOM-LEGAL-SET-NO-REPLACEMENT-v1` and **must produce a
different config hash and run-manifest key**. No collision with the old fixed-null identity is permitted. Whether arm
9 is parameterised over `(null_id, p_singleton)` or a new engineering arm number is used is secondary; the binding
requirement is that the k = 8 null manifest uniquely identifies the Bernoulli-matched mechanism and the exact
`p_singleton`.

## 5. The k = 8 matrix, and what may not be reinvented

- `T0-only` = frozen arm 4 (`D3-T0`).
- `T_NEXT-only` = the **generic singleton** `{T_NEXT}` — Lane M proved the generic singleton path bit-identical to
  ordinary single-teacher D3 in loss, gradient and the tested training trajectory, so **no redundant `D3-T_NEXT`
  mechanism may be invented**. The singleton identity receipt must stay green and the manifest must make the two
  generic configurations distinct.
- `FULL` = generic `{T0, T_NEXT}`.
- The **exact committed `T_NEXT`** from Lane N `25448632` is used — `src/mcrl/algorithms/cf_tnext.py`, its
  `tnext_actions(...)` and its canonical `source_identity()`. **The `A_repr` clone is an admission instrument, not the
  teacher**, and `T_NEXT` may not be inferred from the 113-dim observation.

## 6. Schedule

`--episodes 300 --stop-after 100`, never `--episodes 100`, because `epsilon_decay_episodes()` depends on the
configured budget and shortening it would silently change the learner. This is the same boundary E0, E1 and Phase A
used, which is what makes k = 8 comparable to them. The manifest must bind configured episodes = 300, stop-after =
100, read depth = 100 **before launch**.

## 7. The training-only teacher-context seam

`T_NEXT` needs the live `ScenarioDriver`, the current `StepObservation.candidates`, and the episode-step / final-step
identity. All three already exist in the frozen trainer environment — `TrainerEnvironment.reset()` already returns
`states, masks, StepObservation` and the trainer merely discards the third value. The seam is **minimum and
additive**, and must not alter the 113-dim learner observation, replay state, network architecture, the deployment or
inference path, environment physics, or the RNG schedule. **Existing sources such as T0 must remain behaviourally and
config-identical.**

**Before any k = 8 learner process exists**, the admitted source must be reproduced through the new seam on the frozen
P0 environment, comparing the Lane-N path against the Lane-M training-time path, requiring action identity on every
tested decision, identical legality, identical final-step fallback, no RNG mutation and no environment-state mutation.
The authoritative Lane-N action-trace digest is
`0568b2220a02898527e2a3d4dbc609da0c0aaf2f24dca81a282f9d555fbd9bee`. **If the seam does not reproduce the admitted
source, the seam is repaired — `T_NEXT` is not changed.**

## 8. READY, and then launch

Lane M is k = 8 READY only when all ten exist as concrete artefacts: the final clean/mutant receipt; the exact
committed `T_NEXT` in the integration tree; the training-only seam; the full source-action identity receipt; the
Bernoulli-matched null selected; `p_singleton = 9395/24000` frozen in the config identity; the singleton `Ti-only`
identity confirmed; the prospective k = 8 run manifests; the 300/stop-after-100 schedule asserted; and a named-path
commit whose hash has been read back from git.

On READY, launch the five cells at fresh **k = 8** immediately — **do not wait for `T_TAIL`**. The reading is
unchanged and frozen: `FULL − T0-only ≥ +1.0 %` relative pooled EE, `FULL − T_NEXT-only ≥ +1.0 %`, `FULL >` the
matched null, and the QoS floors (served ≥ −0.5 pp vs D0, p10 ≥ 0.5 × D0, bits ≥ 0.95 × D0). **Nothing from P0 or
`A_repr` substitutes for these drop-one comparisons.**

## 9. Out of scope

No reopening of `T_DELTA` or `T_H`, no redesign of `T_NEXT`, no fourth Catfish family, **no enabling of the
unaccepted Bessel memo** (its sealed-sample parity receipt does not exist), no new review, and formal S1 stays closed.
