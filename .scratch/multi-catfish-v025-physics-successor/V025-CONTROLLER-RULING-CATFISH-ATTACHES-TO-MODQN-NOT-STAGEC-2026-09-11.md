# Ruling — catfish attaches to the MODQN trainer, not to stage-C; C1/C2/C3 are not catfish

> **PROVENANCE WARNING (added 2026-09-11 by the controller after CURATE):** this document contains at least one comparison between numbers produced under different conditions (physics/harness, estimand, host + TLE archive, or paired vs unpaired). Before citing any number from it, look it up in `.scratch/RESULTS-REGISTRY.md` (conditions per row, §2 lists the cross-condition comparisons) and check this document's status in `.scratch/DOCUMENT-STATUS.md`. Text below is unchanged.

Date: 2026-09-11
Status: ruling. Supersedes no sealed artefact. Does not authorise any run.

## What was verified (CATFISHFACT, `.scratch/catfish-facts/CATFISH-MECHANISM-FACTS-2026-09-11.md`)

1. **The original catfish is five training-time mechanisms**, quoted from the sibling's
   explainer package (`07-true-catfish-formulas.md`):
   - **Phase 1** — an *external solver* (DFT codebook enumeration → WMMSE → max-EE
     candidate) whose exemplary solutions are *stored into the catfish replay memory,
     serving as the INITIAL experience replay data* (`07:34-53`).
   - **M1** EE-threshold separation into two buffers (`EE >= EE_high` → catfish).
   - **M2** asymmetric discounts `gamma^main <= gamma^catfish`.
   - **M3** randomized periodic intervention, ~70% main / 30% catfish into the
     **main** agent's batch.
   - **ACRM** `r^C = r + eta*(r^CF - r^M)`.
   Only the main agent is deployed; **no coordinator at inference** (`00:32`).

2. **The stage-C learner is not an RL learner.** `learner.py:279-280`:
   *"No reward, next state, target network, discount, or bootstrap exists."*
   **Four of the five mechanisms have no surface to attach to in stage-C.**

3. **C1/C2/C3 are a decomposition of one scalar objective**, not catfish. The project's
   own code says it: `ee_axis_source_selectors.py:3` calls C3 a *"source construction
   rule"*; `ee_axis_c1_selector.py:58` states *"ACRM is pair construction, not an
   additive reward or selector score."* The intersection with the catfish mechanism
   set is **empty**.

4. **The frozen MODQN checkpoint `e6b063ef...1b09c28b` was trained with r1 = system EE**,
   after the throughput→EE switch. Verified from the checkpoint's own embedded
   `trainer_config`: `"r1_reward_label": "system-energy-efficiency"`,
   `"r1_reward_provenance": "paper eq. (3.25): r1 = sum_{s,v} x * eta"`, and the
   **absence** of `r1_reward_mode` (the positive signature of the post-P-20 build).
   Hash-bound source tree `code_sha256 = 544fcf07...`. Run 2026-08-25 15:41→19:39 UTC.
   **The comparator baseline was not trained on throughput.**

5. **Correction to the sibling package**: `07:249` claims no config anywhere enables
   ACRM. `presets.py:110-120` (`acrm_full()`) and `:138-150` (`acrm_annealed()`) do set
   `acrm_enabled=True`. Whether any run used them is unestablished — CATFISHSURFACE
   is checking.

## The ruling

**Catfish is not a reward route and never was.** The owner's reading — *"C2/C3 那裡沒有路"* —
is correct, and the reason is more basic than an empirical failure: **that was never
where the mechanism lives.** C1/C2/C3 inherited the name.

Therefore a "multi-catfish" design does **not** mean more reward routes. It means
**more seeded experience streams in a DQN training loop**, each defined by an external
specialist that beats the learned policy on a declared outcome.

## What this project now has that the sibling did not

| requirement of the original | status here |
|---|---|
| an external specialist that beats the learned policy | **yes** — `GAIN_IN_SET` 62.502712 Mbit/J vs learned `a0` (q1-v1) 41.28 |
| the trained objective is EE | **yes** — verified in item 4 above |
| no collapse confound masking the measurement | **yes** — collapse and z lines closed in both physics |
| a DQN loop with buffer/discount/two-agent surface | **OPEN** — CATFISHSURFACE |
| the specialist's policy expressible in the state | **OPEN** — APPROACH showed per-option gain is absent from Q1 v2 / Q2 v2; Q1 v3/v4 built for this |

## Count

**One new catfish is supported by the evidence; two and three are not, yet.**
A catfish is defined by its specialist. Only **one** non-dominated specialist is measured
(`GAIN_IN_SET` dominates `RSS_MAX`, the crowded endpoint, and the certified fixed points).
**Adding a second catfish before a second, measured, mutually non-dominating specialist
exists would repeat erratum-level mistake of C1/C2/C3 — three names for one object.**

The second catfish earns its place only if SPECPROFILE shows `GAIN_IN_SET` **fails** a
declared co-primary guard (service availability, handover rate, or Phi-priced handover
cost). Then the second specialist is the constrained rule that passes it, and the main
agent learns under two competing streams. That is the outstanding measurement.

## Endpoint (unchanged, not re-tuned)

Catfish ON vs catfish OFF ⟹ does **pure per-user argmax-EE** rise, on the frozen
48-episode harness. ON/OFF alone is **not** sufficient for merit: the frozen rule
requires two-axis Pareto dominance over the same-contract BC k-NN floor
(`00:134-136`). No new gate is created here.

## Declared failure modes

- If `GAIN_IN_SET` satisfies every declared guard, the learner has **no demonstrated job**
  and the contribution is the rule, not the method. This must be reported as such.
- If CATFISHSURFACE returns **(c) structural**, the delta is a trainer rewrite and the
  cost must go to the owner before any code is written.
- If C1VSGAIN shows exact C1 does not beat `GAIN_IN_SET`, the current three-route design
  has no value even at the oracle layer and the 37 frozen trainings are killed under the
  pre-declared rule in `V025-CONTROLLER-DECLARATION-TRAINING-PAUSE-2026-09-11.md`.

## Process

My previous framing (the multi-objective trade-off narrative) was rejected unanimously by
six fresh-context cross-model reviews. **This design goes to the same reviewers before
anything is locked.** I do not adjudicate my own proposal.
