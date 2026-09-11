# Erratum 23 — the demonstrator comparison was cross-quantity, and the specialist was a search winner

> **PROVENANCE WARNING (added 2026-09-11 by the controller after CURATE):** this document contains at least one comparison between numbers produced under different conditions (physics/harness, estimand, host + TLE archive, or paired vs unpaired). Before citing any number from it, look it up in `.scratch/RESULTS-REGISTRY.md` (conditions per row, §2 lists the cross-condition comparisons) and check this document's status in `.scratch/DOCUMENT-STATUS.md`. Text below is unchanged.

Date: 2026-09-11. Withdraws claims I made to the owner earlier today.

## What I said

> 增益指派規則（專家）62.50 Mbit/J … 學到的 `a0`（q1-v1）41.28 … **21 個單位的差距，就是
> catfish 要注入的東西。**

and, to two agents in writing, that `GAIN_IN_SET` is *"the strongest non-learned reference
on record, so it is the one C1 has to beat."*

## What is true

**1. `41.28` is not an EE. It is a mean active-beam count.**
`/home/sat/mcrl-v025-probe-ws/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md:30` is a row under the
column header *"Active beams mean [range]"* at `:25`, and that document states at `:5`:
*"This is a design-phase diagnostic, not a performance or EE claim."*
**I subtracted a beam count from an energy efficiency and reported the difference as a
gap to be closed.**

The near-coincidence that let it pass unchallenged: `RSS_MAX` pooled EE on the same panel
family is **41.621560** Mbit/J. Two different quantities, two decimal places apart.

**2. The learner's EE on that panel was never measured.**
`BEAM-COUNT-CAP-2026-09-10.md:279-289`, heading verbatim: **"Part 3 — where the current
policies land: NOT COMPLETED"** — *"stopped by the controller's cost-control instruction
before its first anchor completed. No projected number is reported and none should be
inferred."* The counts it does cite are on the 22 TRAIN anchors, not the 12-anchor panel,
and *"carry no EE."*

**So there was never a measured learned-policy EE to compare against. The gap did not
exist in either direction.**

**3. `62.502712` is not a declared rule's score.** It is the `CAP_050` **search winner** —
nine declared rules plus local search plus nested smaller-cap winners. The best *declared
rule* at C=50 is **52.042303**. The label `GAIN_IN_SET` appears nowhere in the beamcount
workspace; it is a name applied afterwards to a search output
(`/home/sat/mcrl-v025-specprofile-ws/PROGRESS.md:47`).

> **Correction to this item, 2026-09-11, from SPECPROFILE's parity check.** I wrote that
> 62.502712 was "selected on boundary-0 EE, which overstates the full-48 endpoint",
> implying the figure itself is inflated. **It is not: 62.502712 reproduces exactly at the
> full-48 endpoint**, to six decimals, as do 52.042303, 41.621560 and 11.027760. Only the
> **selection** was boundary-0, not the reported score. The overstatement warning is still
> real but applies elsewhere — a matched-budget free polish raises boundary-0 EE while
> *lowering* the full-48 endpoint (62.502712 → 59.516177), which is the effect quantified.
> I over-corrected: in fixing a cross-quantity error I introduced a second wrong claim
> about the same number. The search-winner-vs-declared-rule distinction stands and is the
> part that matters.

**4. The two physics do not share an action space.** MODQN's action is `a = 7l + j`, 4
satellite slots x 7 **user-relative** cell slots (`action_contract.py:14-16, 40, 43, 68`),
beam activation is **derived** (`z = 1{U>0}`, `step.py:1027`), and the cap **does not
exist by ruling** (`action_contract.py:60-64`). V0.25 options are global
`(norad_id, cell_id)` over 9 satellites / 370 beams with the active set as an **explicit
capped decision variable** (`run_v025_matrix_probe.py:435-439`). Only the max-gain clause
ports, and that clause **is `RSS_MAX`** — the weakest member of the V0.25 family, below
even the crowded min-cover's 46.11.

## The failure shape

This is the recorded four-fields failure exactly: I carried a number without its
**estimand**. Reference point, information class and numerator were all in the source
document; I did not read them. It is also the second time this week a headline comparison
turned out to be between two different quantities (erratum 19, the contaminated reference
scale).

It went unchallenged for a full day because the two numbers were plausible against each
other. **Plausibility is what makes a cross-quantity comparison survive.**

## What survives, measured on the MODQN harness itself

The follow-up ran a five-arm scripted probe, 8 episodes each, frozen seeds, no `update()`
call. Harness validity check: the random arm reproduces the frozen run's own episodes 0-7
to +2.4% on r1 and +0.2% on r2, so it is the same harness.

| arm | r1_mean | vs trained | calibrated scalar |
|---|---:|---:|---:|
| `MAX_NOMINAL_GAIN` | 1.107376e+07 | **+23.9%** | **+0.0013** |
| trained `e6b063ef...`, last 100 ep | 8.938629e+06 | — | **+0.8859** |
| `RANDOM_MASKED` | 5.543606e+06 | −38.0% | −1.4077 |

Ratio-controlled for RNG position: rule/random 1.998 vs learned/random 1.650.
Generation cost 4.5408 s/ep locally; 50 episodes already overfills the 50,000 buffer.

**A better-than-learner demonstrator on r1 does exist on the MODQN action space, is
realizable from the observation alone (an argmax over one state block — so the network
can represent it, which is what `J_E` requires), and costs minutes.**

## The failure reason moves, it does not disappear

The only expressible better-than-learner demonstrator is better on **r1 only** and is far
worse than the learner on the objective MODQN actually trains: **+0.0013 vs +0.8859**.
`J_E` would supervise the scalarized decision surface toward a rule that ignores two of
its three terms — the margin loss pulling away from the objective while TD pulls back,
with `lambda_2` tuning that fight rather than weighting an aligned signal. This is the
same risk DQFDGROUND flagged from POfD and ZPD, now measured locally rather than cited.

## Next measurement, declared before it runs

A **myopic demonstrator on the scalarized objective**, not on r1. `r2` is predictable at
decision time (the incumbent's slot is in observation block 1) and `r3` from block 4. The
crude two-term `GAIN_PER_LOAD` arm already tests worse, so the real three-term version is
what must be measured. **If no expressible rule beats the learner on the scalarized
objective, there is no demonstrator here and the whole demonstration-RL line closes** —
that outcome is declared now and will be reported if it occurs.

## Corrections issued

- C1VSGAIN: told that 62.502712 is a boundary-0 search winner, that the declared-rule
  figure is 52.042303, and that the "one C1 has to beat" instruction was wrong as given.
- SPECPROFILE: told the same, so its parity check and its report label the target
  correctly.
- Arm declaration (`...-DECLARATION-TWO-ARM-DEMO-UTILISATION-2026-09-11.md`) — the
  demonstrator named there is superseded pending the scalarized-objective measurement.
