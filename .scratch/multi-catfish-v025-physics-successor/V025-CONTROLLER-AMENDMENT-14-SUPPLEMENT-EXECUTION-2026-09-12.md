# Supplement to Amendment 14 — execution clarification, not a new scientific branch

Date: 2026-09-12. **Owner supplement.** It opens no branch, no candidate, no lane, no reviewer and no architecture
search. The three-lane allocation is sufficient and is capped there.

## 1. Lane priority

| priority | lane | disposition |
|---|---|---|
| **1** | `CF2S-PHASE-A` (`T_H`) | critical path: finish clean tests and the equivalence receipt, commit the frozen implementation, then launch the declared DEV k = 6 three-arm canary. **No additional review gate before that canary.** |
| **2** | `CF2S-PHASE-B0` (`T_DELTA`) | runs in parallel; Amendment 14's only authorised fallback, and what prevents a second serial wait if `T_H` fails |
| **3** | `S1-PREP` | let the running commands finish; complete implementation, tests, mutants, DEV-only preflight, manifest and report; commit; then **PARK** |

Once `S1-PREP` is parked: **no fresh-context S1 review is dispatched**, no further heavy S1 test cycle runs, no `sat`
compute goes to S1, and formal / calibration / CONFIRM stay untouched. The final S1 review waits until the successor
lane is adjudicated and the **actual** final S1 manifest is known.

`CURATE-2` and the original `CATFISH2-DISCOVERY` are **closed and are not resumed**.

## 2. Correction — the Phase-B0 "no optimizer step" wording conflicted with §7d

My brief said "No optimizer step, ever", while Amendment 14 §7d requires a **learned** `R_repr` clone. Resolved
prospectively:

**"No optimizer step" means no RL learner training and no `D3-T_DELTA` learner update.** One narrow exception is
authorised: **after** the exact-path parity and the no-training `T_DELTA` diagnostic are complete, Phase B0 may fit
**one** supervised representability clone, solely for §7d.

Binding conditions: reuse the existing T0 / T_SEQ protocol as literally as possible (same 113-dim deployable
observation, same clone family, training protocol and held-out reading rule); freeze architecture, optimiser, epoch
budget, split and seeds **before** fitting; no architecture search, epoch sweep, feature addition or observation
redesign; teacher labels may use privileged `T_DELTA` while the clone's **input** may use only the frozen 113-dim
deployed student observation; the clone may not modify `T_DELTA`, D3, the deployed learner or the observation; the
only output that counts is the `R_repr ≥ 0.5` admission gate; and **if the existing harness cannot be mapped to
`T_DELTA` without a substantive methodological change, stop and return the mismatch to the controller.**

`D3-T_DELTA` RL training stays forbidden unless this gate passes and the controller promotes it. The B0 PROGRESS file
must now read: *"No RL learner optimizer step; the one frozen supervised `R_repr` probe of §7d is the only
exception."*

## 3. Correction — how the `T_DELTA` "cheap" path is read and described

The first engineering smoke measured: 100 decisions; action identity 1.0; maximum relative score deviation
≈ **1.84e-14**; full path 2900 physics evaluations ≈ 33.6 s; "cheap" path 2801 physics evaluations ≈ 27.9 s.

**3a. That smoke is not yet the §7b parity gate.** Its `top1_top2_margin` statistic is **empty**, so the sample
contains no decision with a real competing action, and 100/100 argmax identity there proves nothing about argmax
stability. The DEV parity sample must be extended until it contains a nontrivial set of decisions with **at least two
legal actions**, and the gate requires all four: action identity **on those competing-action decisions**; the score
deviation; the **minimum positive** top-1/top-2 margin; and the demonstration that the score error is far too small to
flip an argmax. **The teacher and the evaluator may not be changed to make this easier.**

**3b. The candidate sweep is not `O(U²)` and must not be described that way.** B1's `O(U²)` arithmetic replaces the
**without-user baseline**; it does not remove the need to evaluate the focal user's alternative legal actions. 2801
versus 2900 physics evaluations is the proof: **candidate evaluation is the dominant cost.** The correct name is the
**cheap exact baseline path**. **No approximation or surrogate-development lane may be opened to optimise it.**

After parity passes, the exact B0 diagnostic runs on `sat` in **at most 4 independent shards** — parallelising the
already-declared measurement, **not redesigning it for speed**. If the measured runtime is prohibitive, the
**projection is reported before** any change to the state sample or protocol.

## 4. Resource priority

Local S1 construct-only / mutant work and the Phase-A full pytest already in flight are **not killed mid-command**.
Once the current `S1-PREP` batch drains, no further CPU-heavy S1 work launches. **Phase A has local priority; Phase A
and Phase B0 have `sat` priority.** No cap-penalty, B2, exact-DR or original Catfish-2 work reopens.

## 5. Review discipline

**No reviewer is created for the Phase-A k = 6 canary or the B0 discovery screen.** They are DEV elimination tests
with explicit tests, mutants and pre-declared reading rules, and that is the point of having written those rules down
first.

A fresh-context / adversarial review is **reserved for the next actual one-way decision**: before freezing a
successful two-Catfish FULL mechanism, or before the final formal S1 manifest is launched. **Formal S1 remains HOLD
however clean the fallback `S1-PREP` becomes.**

## 6. What the next controller update covers, and nothing else

1. Phase-A preflight / commit and the k = 6 launch and result.
2. B0's **nontrivial** parity result, then its diagnostic and `R_repr` status.
3. `S1-PREP` reaching PARKED.

No additional research branch opens without owner or controller instruction.
