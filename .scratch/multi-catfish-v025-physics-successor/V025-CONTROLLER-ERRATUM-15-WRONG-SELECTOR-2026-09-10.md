# Erratum 15 — I gave both strategic reviewers the wrong selector

**2026-09-10. Verified by the controller reading the code directly. No sealed artefact,
constant, threshold, sign, seed, horizon, price, guard or acceptance rule is changed.**

**The deployed learned arms select by CATALOGUE ARGMAX with the interaction term inside the
score, not by single-user first-improvement. C3 is therefore not structurally locked out of
the deployed selection, and the first-move obstruction argument does not apply to it.**

## What I told the reviewers

The `DECOMP` prompt I wrote and sent to both astra and fable stated, as a fact about the
system:

> "The deployed selector is deterministic cyclic **first-improvement** over **single-user
> moves**, users in sealed order, each user's sealed legal options in sealed order, strict
> exact-binary64 improvement, under a served-count guard referenced to the nearest-eligible
> baseline."

That description is accurate — **of `harness/anytime.py`**, the search used by MULTISTART and
CTRLCEIL, and of the `S_UNI` comparator. **It is not the learned-arm selector.**

## What the code actually does

`scripts/run_v025_pilot_c3.py:1542-1563` (verified in `/home/sat/mcrl-v025-arch-ws`, same
structure in the retrain and harness workspaces):

```python
for config in legal_catalogue:
    context = contexts.get(config.configuration_id)
    ...
    for arm in PILOT_ARMS:
        model = models[(seed, arm)]
        score = math.fsum(deltas_by_arm[arm][(user, config.mapping[user])]
                          for user in anchor.mapping)
        if context is not None:
            score += model.interaction(context)          # <- C3 enters here
        learned_scores_by_arm[arm].append((score, config.configuration_id, config))
...
for arm in PILOT_ARMS:
    selections[(seed, arm)] = min(learned_scores_by_arm[arm],
                                  key=lambda row: (-row[0], row[1]))[2]
```

This is an **argmax over the whole legal catalogue**, with the interaction term added to every
row's score and ties broken by lexicographic `configuration_id`. There is no incumbent, no
move set, and no first move. **A C3 head can change which configuration wins at any anchor
where the catalogue holds more than one row and the interaction term separates them.**

Corroborating structure elsewhere: `stagec_v025/deployment.py:62` declares
`SelectorMode = Literal["S3", "S0", "S_UNI"]`; `ProfileSelector.select` (`:647`) runs the
single-user loop **only** in the `S_UNI` branch, and runs `for profile in (base_profile,
*catalogue)` with `additive + interaction` for `S3` and `S0`. `synthetic.py:372` maps learned
arms to `"S0" if arm == "S0" else "S3"`. `merge.py:680` and `acceptance.py:78` treat `S0` and
`S_UNI` as **supportive comparators**, listed separately from `LEARNED_ARMS`
(`learner.py:28`).

## What this invalidates

**fable's Theorem 1** — "the residual head is hard zero on singletons, so strict improvement
never fires and the committed configuration is the seed regardless of C3" — is a correct
theorem **about `S_UNI`**. `S_UNI` does not take the model at all
(`deployment.py:690-712`). It says nothing about the learned arms.

**fable's Theorem 2** — that everything ORACLE_SET gains over UNILATERAL lies outside the
single-user move set — is likewise about the comparator, not the deployed selector.

**astra's PANELAUDITA "C3 structural blind spot"** rests on the same premise ("only
single-user moves with strict improvement are permitted"). It needs re-examination on the
same grounds. Both reviewers flagged that they could not authenticate the deployed entry
point and asked which selector was sealed; **astra explicitly declined to promote its own
inspection of `ProfileSelector` into a verified fact.** They were right to hedge and I
supplied the error.

## What this does NOT invalidate

- The **empirical** observations stand: `DROP_C3` changed 0 proposed assignments at 3/3
  anchors, and in the r8 panel smoke `FULL` and `DROP_C3` committed byte-identical
  assignments under both rules. Those are receipts, not derivations.
- **The explanation for them is now open.** A structural impossibility has been replaced by
  an empirical question with at least three candidate causes, none yet established:
  (a) the interaction term is too small relative to the spread of additive scores across
  catalogue rows; (b) `contexts.get(config.configuration_id)` returns `None` for most or all
  rows, so the term never enters; (c) the panel bridge defect already proven for `MARGIN_Q`.
- The **conditioning** finding is untouched. `+480.113 - 440.079 = +40.034` and the 22.99x
  error amplification are properties of the decomposition, not of the selector.
- Everything about the surrogate corpus is untouched.

## Why this happened

I wrote the premise from the search harness I had been reading all day — `anytime.py`, in
MULTISTART and CTRLCEIL — and did not check it against the learned-arm path before asserting
it to two reviewers as a fact. **Neither reviewer could have caught it: I gave them the
premise and told them the selector contract was authoritative.** Both nonetheless flagged
the entry point as unauthenticated, which is the only reason this surfaced within the hour.

This is the third time today a conclusion has turned on which of two code paths was actually
running (`MARGIN_Q`'s bridge, `evaluate` vs `evaluate_many`, and now this). The common
failure is asserting which path executes without running it.

## Immediate consequences

1. `DECOMP` is re-dispatched to both reviewers with the corrected premise and this erratum.
2. The question "why did `DROP_C3` change nothing" is re-opened as an **empirical** question
   and dispatched as `C3REACH`, to measure at how many anchors the interaction term changes
   the catalogue argmax, and to report the `contexts` coverage.
3. The pre-declared reading rule for `RESIDTOGGLE` is **unchanged**. It measures the residual
   ceiling on the reported objective and does not depend on this erratum.
