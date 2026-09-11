# Declaration — the evaluation contract, and the null-guide control that makes it enforceable

Date: 2026-09-11. Declared **before** any arm is built. Authorises no run by itself.

## The owner's objection, which this encodes

Verbatim: *"要小心不要把一些可以提升 ee 值但是其實跟學習無關的，像是舊的專案用的
penalty 那樣，那要拿來說是 catfish 其實是非常牽強的，重點是沒經過學習"*

The sibling project's `q_row_decorrelation_penalty` raised EE, but it is a **regulariser on
the Q-network**, not a demonstration mechanism. Calling it catfish would be a stretch. The
general form of the objection: **a mechanism that raises EE without learning being involved
is not a learning contribution.**

## Where this project was about to walk into it

**JSRL** — currently the leading candidate, because it has no imitation loss and so cannot
suffer the predicted Q-filter self-disabling — works by letting a **guide policy roll the
first `h` steps** of an episode before the learner takes over. If EE rises because a
non-learned rule is executing a fraction of the actions, **that is not the learner
improving; that is the specialist being run part of the time.** The owner identified this
independently and before it was proposed to them.

## Rule 1 — the evaluation contract (non-negotiable)

**At evaluation, only the learned policy acts. `h = 0`. No rule executes any action, in any
arm, ON or OFF.**

A guide, a demonstration buffer, a margin loss, a pre-training phase — all are
**training-time only**. This is also the original catfish's own endpoint (only the main
agent is deployed), and it is what makes "catfish ON vs OFF ⟹ does EE rise?" a question
about learning rather than about which rule ran.

Every arm's reported figure is a **greedy rollout of the learned policy alone**, on the
frozen harness, with the same estimand: pooled decoded bits over pooled system joules, a
ratio of sums, bits and joules reported separately.

## Rule 2 — `NULL_GUIDE`, the control that enforces rule 1

ON-vs-OFF is not sufficient, because a mechanism can help for reasons that have nothing to
do with the demonstrator being good. So every demonstration arm carries a matched control:

**`NULL_GUIDE`** — identical in every respect (same schedule, same buffer sizes, same demo
fraction, same number of guided steps, same gradient budget), except the guide is a
**randomly initialised network** instead of the measured specialist.

**Pre-declared reading:**

| outcome | meaning |
|---|---|
| specialist arm > `NULL_GUIDE` > OFF | the mechanism helps **and** the demonstrator's quality is what helps. This is the only outcome that supports a catfish claim. |
| specialist arm ≈ `NULL_GUIDE` > OFF | the gain is **the perturbation, not the demonstration**. Exactly the sibling-penalty failure. **Must be reported as such and must not be called catfish.** |
| specialist arm > OFF, `NULL_GUIDE` ≈ OFF | consistent with a real demonstration effect; the strongest available evidence. |
| nothing separates | reported as null. |

`NULL_GUIDE` costs one extra arm per mechanism. That is the price of being able to make the
claim at all.

## Rule 3 — what may not be called catfish

A mechanism qualifies as a catfish/demonstration contribution only if **all** hold:

1. It acts on the **training** process, never on the deployed decision path.
2. Its effect depends on the **demonstrator being better** — i.e. it separates from
   `NULL_GUIDE`.
3. The deployed artefact is the learned policy alone.
4. Its ON/OFF contrast is measured on **pooled EE**, not on a loss, a collapse diagnostic,
   a win rate, a beam count, or the trained scalar.

A Q-network regulariser, a replay-sampling change that helps regardless of data quality, or
anything whose benefit survives replacing the specialist with noise **fails condition 2 and
is not a catfish**, however much it raises EE. It may still be reported — as what it is.

## What was decided today, and what was not

**Decided, because none of it depends on an open question:**

- the evaluation contract and `NULL_GUIDE` above;
- **`B0`**: the three verified defects fixed — per-head bootstrap
  (`modqn.py:536-552`), the outage free ride (`outage_gate.py:10-27`), the uncalibrated
  logged scalar (`modqn.py:1302`) — objective, physics, weights, discount, lr and
  architecture **untouched**. Every arm needs `B0`; the frozen checkpoint cannot be the
  causal control while those defects stand. **Dispatched, with a 500-episode pilot.**
- **backbone JSRL**, with DQfD and the faithful RIS catfish as comparator arms. JSRL is the
  only candidate with no imitation loss, so the predicted self-disabling failure is
  structurally impossible in it; ~60-110 lines against DQfD's ~470-640, with `update()`
  untouched.

**Not decided, and not blocking `B0`:**

- whether the declared endpoint becomes constrained EE. Both cross-model reviews returned
  PROCEED WITH CHANGES, **both conditioned on it being a new prospective study rather than
  a retroactive rescue**. That is a thesis-framing decision and it is the owner's.

## Amendment, same day — rule 3 was stricter than the source paper and is withdrawn

The owner: *"只要在敘事上是合理的就好，因為 ris 的 catfish 的很多機制其實也是一樣，
沒有真的那麼嚴格 … 如果要求這麼多的話，那可能真的會找不到可以用的演算法"*, and asked
whether JSRL and the sibling's penalty can both be narrated as catfish.

**They can, and rule 3's four-condition test is withdrawn as a naming gate.** It set a
higher bar than the source paper meets, which is self-defeating: the RIS catfish's own five
mechanisms include two with no published counterpart at all.

**JSRL is not a stretch — it is catfish mechanism M3.** The RIS catfish has a *periodic
intervention* mode in which the catfish agent intervenes in the main agent's training.
JSRL's guide prefix is that intervention, applied to the action sequence instead of the
batch composition, and specified far more precisely. Framing it as a narrative risk was the
controller's error.

**The penalty is also narratable, and more tightly than the controller first said.**
`srank` / row-decorrelation penalties prevent the value representation collapsing into
redundant rows. The catfish metaphor is, literally, *preventing a population from becoming
homogeneous and complacent without a predator*. "Prevent representation collapse" and
"prevent homogenisation" are the same sentence, not an analogy stretched to fit — a closer
mapping than "a second agent with a different discount factor". It is also **the one
sibling mechanism with a measured positive effect**. Dispatched as an arm (PENALTYARM).

## What is still held, and why it is not strictness

**Rule 1 (evaluation contract) stands**, on two grounds that are not about purity:
- **JSRL itself requires `h -> 0` by the end of training.** Evaluating at `h > 0` is not
  the published method.
- If a rule executes a fraction of the actions at evaluation, that fraction of the reported
  EE is the rule's, not the learner's. Any referee asks this first.

**Rule 2 (`NULL_GUIDE` / `NULL_PENALTY`) is re-framed, not withdrawn.** It was wrongly
presented as a purity gate. It is a **which-knob diagnostic**: if the null control matches
the real arm, the effect is the perturbation, and the fastest route to more EE is then to
optimise the perturbation directly rather than to keep searching for a better demonstrator.
It blocks nothing, runs in parallel, costs one arm (1.32 h), and saves an entire dead
branch. Reported either way, and a perturbation effect is a usable result, not a failure.

## Gates still outstanding, each cheap, any one fatal

- **FEASFRONT** — is the trained policy even on the Pareto frontier of simple rules with
  memory? If a hysteresis or consolidation rule reaches its EE at its handover rate, the
  learner has no demonstrated job and this whole line closes.
- **JSRL coverage sweep** — does the guide hand the learner states it cannot reach? Flat
  coverage in `h` means the mechanism is inert. Zero gradient steps, minutes.
- **Representability** — BC top-1 on the specialist from the same observation.
- **DR-1** — whether a ratio objective is trainable off-policy at all.
