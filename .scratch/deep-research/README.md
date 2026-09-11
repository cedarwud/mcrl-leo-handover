# Deep Research package — 2026-09-11

## How to use

Each `DR-*.md` is self-contained **except** that `00-EVIDENCE-LEDGER.md` must be pasted
above it. Ledger + one DR prompt = one Deep Research run. **Run them separately** — they
ask different questions of different literatures and a combined prompt will return a
shallower answer on all three.

| | question | why it cannot be answered here |
|---|---|---|
| **DR-1** | how to actually maximise a ratio of sums with an off-policy discrete RL agent | two cross-model reviews recommended a two-critic architecture and **neither sourced it**; this is the architecture decision and it currently rests on assertion |
| **DR-2** | is this simulator's handover and payload physics defensible, and what operating point is realistic | needs standards and the LEO/NTN modelling literature, not this codebase; two reward premises already fail *inside* the model and nobody has checked what the field does instead |
| **DR-3** | what the field reports, what a referee expects, and whether a contribution survives | **never done** — this project has only ever compared against itself |

## What to send and what not to

**Send**: literature synthesis, standards provenance, "does anyone do X", formulation
comparisons, novelty positioning, referee-objection forecasting.

**Do not send**: anything needing this repo's code or data. Deep Research cannot read
`step.py`, cannot run the harness, cannot check a hash. Every number in the ledger was
measured here and should be given to it as **context**, never asked of it.

**Do not ask it to adjudicate the endpoint decision.** That is already with two
cross-model reviewers (agy, codex `gpt-6-astra`) who have the full evidence bundle. A
third opinion formed from a summary is worth less than either, and three opinions invite
picking the congenial one.

## Priority if only one can be run

**DR-1.** It decides the architecture, it is the only one whose answer changes what gets
built, and it is the one where both existing reviews converged on a recommendation without
a citation between them. DR-3 is second: it is cheap, it has never been done, and it can
reveal that the intended contribution is already published — which is better to learn now
than after the training runs.

## Standing caution for whoever reads the answers

The ledger's numbers are measurements from this codebase; the DR answers will be claims
from papers. **Do not let a paper's claim overwrite a local measurement**, and do not let a
local measurement be used to dismiss a paper's method without checking the method's
assumptions first. Where they conflict, that conflict is the finding.

Deep Research output is a **starting point for verification, not a citation**. Every
load-bearing claim it returns must be checked against the actual paper before it enters a
declaration or the thesis — this project has already been bitten by a citation
("SASR / Shen et al.") that does not resolve to any paper.
