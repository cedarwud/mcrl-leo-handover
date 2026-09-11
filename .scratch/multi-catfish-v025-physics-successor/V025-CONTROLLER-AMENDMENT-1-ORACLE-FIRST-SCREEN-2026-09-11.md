# Amendment 1 to Ruling 2 — oracle-first: every candidate mechanism gets a no-training rollout of its ideal version before any training

Date: 2026-09-11, ~14:55 UTC. Amends `V025-CONTROLLER-RULING-CEILING-PARITY-B-CHAIN-AND-CATFISH-COUNT-2026-09-11.md`
(§3 references; adds the screen). Written before the ceiling, the LP probe or any oracle cell has reported. Owner's
proposal ("每一個候選機制，先做出它的 oracle 版本跑一次 rollout，完全不訓練，再決定要不要訓練") adopted as a standing rule.

## 1. The rule

A mechanism is trained only after its **ideal version** — the decisions a learner would make if it had perfectly learned
what the mechanism asks it to learn — has been rolled out on the 24 evaluation episodes (and the 24 calibration episodes
for the tie-in) with the environment's counterfactual evaluator, no training, and has beaten the reference rule under the
declared reading. If the ideal version does not beat the rule, training it cannot, and the mechanism is dropped there.
Every cell carries served fraction, per-served-user rate mean / p10 / min and lit beams; a cell whose gain the
rate-floor condition does not preserve is throughput-degenerate and does not count.

## 2. The oracle table — two axes, and each cell at two information levels

The owner's table has an information axis (what the decision can see) and a credit axis (what it optimises). One
addition is essential: **each cell exists at two information levels**, because the deployable per-user policy acts on
the observation, while the exact difference reward needs the realised step.

| decision sees ↓ / optimises → | own bits (congestion payoff) | equal-share energy (CF3 as built) | **difference reward** `D_u = F(a) − F(a_{−u}, a_u^ref)`, `F = bits − η·joules` | exact joint objective |
|---|---|---|---|---|
| **only itself, simultaneous** (current contract) | OWN_BITS rule: 93.8 M (eval) — measured | A1–A3: 98.6–102.0 M (eval) — measured | **cell A**: A-real = simultaneous best response to the rule's joint action with the realised evaluator (credit ceiling); A-nom = the LP-prev(c, m) best cell (deployable approximation; running) | — |
| **+ current-step lighting of earlier users** (sequential decisions) | — | — | **cell B**: B-real = one sequential sweep from the rule's joint action with the realised evaluator; B-nom = LP-seq best cell (running) and the ceiling's nominal-information variant (running) | — |
| **fully joint** (coordinator) | — | — | — | **corner**: the constrained centralised search (running; lower bound on the one-step optimum) |

Definitions fixed now: the reference joint action for the simultaneous oracle is `A m=2dB`'s action at that step
(the pilot's own best rule); the sequential oracle uses the fixed user order 0..99 and reports one alternative order
(99..0) on ≥ 6 episodes as an order-sensitivity check; `η` for the oracles is the step's own bits/joules under the
reference action (Dinkelbach price at the reference), not a trained value; all oracles are one-step myopic and are
therefore **lower bounds of each mechanism's ceiling**, which is the conservative direction for a screen.

## 3. Decision rules (declared before any cell is read)

Reference = `A m=2dB` on the same episode set, paired per-episode sem; the +3.3 % and +4.5 % thresholds of the ruling
are reused, not redefined.
1. **A-real ≤ rule + 3.3 %** → the difference-reward credit has no room even with perfect information: **B1 is dropped
   without training.**
2. **A-real wins, and B-real ≤ A-real + 3.3 %** → the credit change alone is the fix; observation and contract stay;
   B1 proceeds (training question in §4). Sequential decoding is not pursued.
3. **B-real ≥ A-real + 3.3 %** → the learner must see the current-step lighting pattern: B2 (sequential decisions) is
   the path; B1 alone is not.
4. **Only the corner is high** (both A-real and B-real ≤ rule + 3.3 %) → coordination is required; entering C is the
   owner's decision (deployment contract and paper skeleton change), never automatic.
5. **Deployability gate on top of 2–3**: the nominal-information cell of the chosen path (A-nom for B1, B-nom for B2) must
   itself be ≥ rule + 4.5 % with served ≥ 0.995 and the rate floor preserved; if the realised cell wins but the nominal
   cell does not, the credit is right and the **information** is wrong — the next screen is an observation redesign
   (what to add so that the nominal cell approaches the realised one), still before any training.

## 4. Training, when it comes, asks a different question

The first training run of a passed mechanism asks **"does the learner catch its own oracle?"** — not "does it beat the
baseline". Reading: learner ≥ rule + 50 % × (nominal-cell gain over the rule) on the evaluation set, seed-mean, ≥ 2 of 3
seed pairs, served ≥ 0.995, rate floor preserved (the 50 % is the owner's number, ruling §3). Catching the oracle =
mechanism usable; not catching it = a learning problem, reported as such, no automatic advance. Every mechanism arm keeps
a matched random control of identical size and schedule (evaluation contract rule 2) — that control is what exposed the
static-pool null this time.

## 5. Catfish under this screen

Catfish become meaningful only after cell A or B passes, and what they teach is a **beam-lighting pattern / regime**,
not a per-user action. Candidate sources are screened by the same no-training method — rollout, then the three
count criteria of ruling §4 (frontier non-dominance; action disagreement ≥ 25 % on shared states with non-contained
state coverage; marginal value once a signal exists). The count is whatever the screen returns.

## 6. Execution

- A-nom / B-nom: the LP probe (running on the H4 agent's harness) and the ceiling's nominal variant (running).
- A-real / B-real (+ order sensitivity): dispatched to the same harness as soon as the LP grid finishes (≈ 2,800
  evaluations per step ≈ 20 s; 24 episodes on 4 processes ≈ 20–30 min per cell); parity discipline (ruling §1) applies to
  these cells as to the search.
- No training starts before the cells are read against §3 (ruling §5).

## 7. Summary

Old loop: design → train for days → read the result → find it infeasible. New loop: design → roll out the ideal version
in minutes → drop on the spot if it loses → train only what passed, asking whether the learner catches its oracle.
The random-control arm rescued the pilot after the fact; the screen is there so the next round is stopped before it.
