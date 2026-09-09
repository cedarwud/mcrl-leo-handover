# Controller finding — the C3 encoder is fed the one thing the contract forbids, and the test meant to catch it tests nothing
Recorded 2026-09-09. Verified by reading the executing code. This is the most likely single explanation for why the learned C3 component has never worked.

## 1. What the contract requires
`V025-STAGES-6-8-CONTRACT-v1.2-AMENDMENT-2026-09-09.md` §C2, verbatim: the encoder's input must contain "the **pairwise cross-gain terms among the affected beams** (not only a scalar interference summary — a summary can hide exactly the difference that flips a coupled fixed point)."

## 2. What the code does
`scripts/run_v025_pilot_c3.py::_coalition_context` computes the pairwise terms and then destroys them:

```python
relations = _cross_gain_terms(tape, step_index, affected)
beams = tuple(
    AffectedBeamContext(
        ...
        interference_summary=math.fsum(
            gain for _source, target, gain in relations if target == ...
        ),
```

`AffectedBeamContext` in `src/mcrl/stagec_v025/coalitions.py` carries `beam_key`, `occupancy_before`, `occupancy_after`, `active_before`, `active_after`, `shared_capacity`, **`interference_summary: float`** and `capacity_margin`. There is **no pairwise field of any kind**. The global feature block likewise carries only the sum and the max of the same relations.

So the pairwise structure is computed and then collapsed into precisely the scalar the contract names and forbids, in a field literally called `interference_summary`.

## 3. Why this is fatal to the mechanism we verified
The verified mechanism is: a victim's deficit is covered only when **two specific aggressors** are relieved together; either alone leaves it below threshold. A separate diagnostic measured that population at 23.556 % of the interference-limited users, about 8.8 users per hundred per anchor.

Representing that requires knowing *which* aggressors and *how much each contributes*. A single summed scalar cannot distinguish "one aggressor carrying 74 % of the interference" from "fourteen weak ones summing to the same total", and those two cases have opposite consequences for whether a two-member coalition helps. **The head is structurally unable to represent the only mechanism we have verified.**

It also explains the pilot's behaviour, which had no explanation before. FULL selected the all-users coalition at all ten anchor-seeds and never a size between 2 and 6. With only sums available, a larger coalition touches more beams and yields a larger summary, so the features carry a signal that is close to monotone in coalition size and little else. The learner was choosing the biggest set because that is nearly the only thing its features could see.

## 4. The acceptance test that should have caught it does not test it
The same amendment says: "Acceptance test T2 is extended: the information-twin pair must be separable with the full context and **provably ambiguous when the cross-gain block is removed**."

`tests/stagec_v025/test_contract_v1_acceptance.py::test_T2_information_twins_reversal_and_additive_placebo` contains **zero** occurrences of `cross_gain` or `interference`. The extension was never implemented.

What T2 does instead is construct contexts labelled `synergy`, `antagonistic` and `additive`, then assert the head predicts synergy on the one labelled synergy. That tests that the head can fit a supplied label. It does not test whether the physical features suffice to tell the cases apart, which is the only thing the requirement was about. It is a tautological test in the precise sense recorded earlier in this project: it cannot fail for the reason it exists.

## 5. What follows
This is a **DEFECT with a demonstrated basis**: the required field is absent from the dataclass, and the test named to enforce it does not mention the subject.

The repair is bounded and does not touch the physics: carry the per-pair terms into the context, extend the head's encoder to consume a variable-length pair block, and implement T2 as written so that removing the block makes the twins provably indistinguishable. No threshold, sign, seed, horizon, price, service guard or acceptance rule changes.

Until it is repaired, **no result from the learned C3 arm is evidence about whether coordination has value**, in either direction. Every previous learned null was measured on a head that could not see the mechanism. That includes the minimal pilot's numbers.

## 6. Standing
This records a code finding. It authorises no run and creates no gate. It does not change the sealed contract; the contract already requires what is missing.
