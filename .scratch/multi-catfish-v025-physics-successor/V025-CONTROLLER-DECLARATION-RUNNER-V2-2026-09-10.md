# Declaration — runner v2: raise the epoch cap, add the declared decay, keep v1 byte-identical

Date: 2026-09-10 ~17:22Z · Controller
**Written before any EE exists on the exact corpus. No EE quantity has been computed from it.**

## What blocked

`EXACT-CORPUS-TRAINING-2026-09-10.md` (`/home/sat/mcrl-v025-exacttrain-ws`) assembled the exact
corpus and passed every label check, then **stopped before creating an output directory**:

> the required runner, SHA-256 `4885705…c797d66`, accepts only **1–2,000 epochs** and implements
> the legacy **constant-rate, exact-budget/no-early-selection** contract. It cannot express the
> declared 4,000-update step decay and cadence-100 stability stopping rule without changing the
> sealed implementation or inventing a new runner and held-out split.

`DECAY` measured first-admissibility for step decay at **2,200 updates**. The cap is 2,000.
**It is short by 200.**

## The three-layer test, applied

- **Scientific sealing?** No. `V025-CONTROLLER-WHAT-IS-ACTUALLY-SEALED-2026-09-10.md` lists the
  **2000-epoch cap** explicitly among the things that are **not sealed**, alongside lr,
  `gauge_beta`, hidden layers, activation, Adam betas, checkpoint cadence and catalogue caps.
  That listing was written this morning, before any of today's results.
- **Compatibility pinning?** Yes. Three completed runs carry launch receipts binding
  `4885705…c797d66`. **Runner v1 stays byte-identical and those receipts remain valid.**
- **Implementation default?** Yes, and the rule for those is: **declare before the judging
  measurement.** This is that declaration, and no EE from the exact corpus exists yet.

## Authorised

**Runner v2, as a new file with a new digest. v1 is not edited.**

1. **Epoch cap `1–4,000`.** The 2,000 literal was an implementation default, never a scientific
   choice.
2. **Step-decay schedule support**, expressing the already-declared schedule
   (`V025-CONTROLLER-DECLARATION-SCHEDULE-CHOICE-2026-09-10`): from `1e-3`, factor `0.1` after
   2,000 updates and again after 3,000. **Constant rate remains available and remains the
   default**, so v2 can reproduce v1's behaviour exactly.
3. **Nothing else changes.** Not the architecture, not the arms, not the corpus contract, not
   the fixture gate, not the checkpoint format, not the cadence semantics.

**A v1-equivalence test is required**: run v2 with a constant rate on the same corpus and seed
and show it reproduces a v1 checkpoint **bit-for-bit**. Without that, v2 is not usable, because
a silent behavioural change would be indistinguishable from a result.

## Not authorised

**Do not put the stopping rule inside the runner.** The runner already writes cadence-100
checkpoints; the pre-declared stability criterion is applied to that checkpoint sequence
**offline**, exactly as `DECAY` and `HORIZON` applied it. Adding a held-out split and
early-selection to the training loop would change the runner's exact-budget contract, and that
**is** a scientific change — it would let the training loop select against held-out data.

**Do not rescale the decay schedule to fit a 2,000 cap.** Compressing the decay points to
1,000/1,500 because 2,200 exceeds 2,000 would be choosing a schedule against a constraint
discovered after the schedule was declared. Raise the cap instead; it is the free variable.

## Why this is not the move it might resemble

I have attacked sealed declarations three times this project on bad grounds. This is not that:
the object being changed was **listed as unsealed this morning, in writing, before any of
today's measurements**; the change is a version, not an edit; v1 remains valid for the runs
that used it; and the declaration precedes the measurement it affects. If any of those four
were untrue I would not authorise it.
