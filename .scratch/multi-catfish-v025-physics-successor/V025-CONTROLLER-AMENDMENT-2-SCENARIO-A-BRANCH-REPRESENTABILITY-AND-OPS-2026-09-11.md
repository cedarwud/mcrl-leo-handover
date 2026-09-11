# Amendment 2 to Ruling 2 — scenario A written before it happens; representability before training; a second reference for A-real; coordination depth from the sweeps; four operating rules

Date: 2026-09-11, ~15:00 UTC. Amends `V025-CONTROLLER-RULING-CEILING-PARITY-B-CHAIN-AND-CATFISH-COUNT-2026-09-11.md` and its
Amendment 1 (oracle-first screen). Written before the ceiling's parity result, the pooled base-search number, the LP grid,
or any oracle cell has been read. Source: the owner's five points of 14:45 UTC, adopted with two precision notes (§1, §2).

## 1. Coordination depth from the existing sweeps (free) — with one correction

The base search is repeated sweeps of unilateral best responses. **Sweep 1 is a *sequential* pass** (user k already sees
users < k's new choices), so the EE after sweep 1 is cell **B-real**, not A-real; the converged value is the joint search;
the intermediate sweeps measure how many layers of mutual adjustment the gain needs. The ceiling agent is asked to report
the step EE after sweeps 1/2/3 (from its recorded η trajectories) and the share of the final gain over `A m=2dB` reached
after sweep 1, for the base and the compound-move variant. **A-real (simultaneous best response to a fixed reference) is a
separate cell** and is being measured on the H4 harness. Reading: most of the gain in sweep 1 → one layer of visibility
suffices (B territory); gain only at sweeps 3+ → that share is "coordination-only" (C territory), and its size is reported.

## 2. A second reference action for A-real

A-real anchored only at `A m=2dB`'s joint action explores that rule's operating point (≈ 63 lit beams). If the good region
sits elsewhere (fewer, better-placed beams), a single reference can under-estimate the difference-reward credit and we
would wrongly drop it. **`B1_NO_NEW_BEAM`'s joint action is the second reference**; both A-real and B-real are run from
both. Reading: results that differ a lot between references = the mechanism is start-point sensitive (itself a finding
that argues for B2/C rather than B1); results that agree = the A-real conclusion is robust. Cost: one extra cell each.

## 3. Representability screen between "oracle passed" and "training starts"

For any cell that passes Amendment 1 §3 rules 1–3: train the CFSCREEN behaviour-cloning probe (the learner's own
Q-architecture on the learner's own observation) to predict the oracle's actions; report held-out top-1 and the
**closed-loop pooled EE of the clone** on the evaluation set. **Pass iff the clone retains ≥ 50 % of the oracle's gain over
`A m=2dB`** (the same 50 % as the learner criterion; if the clone cannot, the learner cannot, and the training criterion is
meaningless). ~30–60 min, no learner training. Precedent: CFSCREEN's 0.71 top-1 / ~70 % consolidation recovery for
`B1_NO_NEW_BEAM` explained C3's result before C3 was ever trained.

## 4. Scenario A, written now (constrained lower bound ≤ +3.3 % over `A m=2dB`)

If A occurs, the box itself is wrong: the action space has neither of the two levers the wireless-EE literature treats as
primary (power control, sleep), and beam choice alone is nearly solved by a rule. The candidate levers, in order, each with
the question it must answer first and a no-training screen:

| # | lever | literature question (to be answered by the owner's Deep Research run; unanswered = not started) | cheapest screen (no training) | proceed only if |
|---|---|---|---|---|
| A1 | **per-beam power control** (the recurrence fixes `p` between 0.825 W and 1.65 W; `P_DC ∝ √p`) | is power control the primary EE lever in LEO multi-beam EE papers, and by how much? | accounting on existing eval logs: the share of PA joules above the minimum `p` that keeps each beam's served users at their current SE ("power headroom", no rollout) | headroom ≥ 10 % of joules |
| A2 | **beam sleep / activation as an explicit action** (today a beam is dark only if nobody chose it) | do sleep-mode papers report EE gains at full service, or only under low load? | the ceiling's lit-beam counts (pending parity) and a "sleep oracle" rule: switch off beams with < k users or SE below a threshold, reassign their users, rollout | sleep oracle ≥ +3.3 % over the rule with served ≥ 0.995 and rate floor kept |
| A3 | **handover interruption / signalling energy** (today 0 J, 0 bits per event) | what per-event cost do LEO handover papers assign, and does it change rankings? | re-score existing eval logs with 0.062 / 0.142 s interruption per inter-satellite event (erratum 25 sensitivity) plus a literature signalling-energy value | rankings between rules and learners change |
| A4 | **demand-capped / bursty traffic** (full-buffer numerator today) | does EE optimisation with queues (race-to-sleep) create room that full buffer hides? | registry rows on the demand-capped numerator (the +113 % → +0.27 % precedent); a queueing model is a physics change | owner decision — it changes the endpoint |

Each lever is a **physics/action-space change** and re-opens the ceiling question for the new box: the oracle-first
screen (Amendment 1) applies again from the top. **Fallback, also written now**: the diagnostic paper — "a one-line
hysteresis rule beats the published multi-objective DQN by ~20 % pooled EE on a geometry-resolved multi-beam LEO physics
with a consumed-power model, because the DQN's handover and load terms price zero-energy events and its per-user credit
cannot see the only lever (bits per lit beam)"; main table = `A m=2dB`, `MAX_NOMINAL_GAIN`, `B1`, the centralised lower
bound, MODQN (best reading and 9,000 episodes), A1–A3, each with served, rate p10, handovers per user-minute; diagnostics =
rule frontier, power accounting, cap decomposition, representability, H4, LP grid, oracle cells. This is not acceptance of
failure; it is so that scenario A does not become an improvised discussion.

## 5. The question to ask before the next round starts

What, in the new direction, is the thing that — if it does not hold — makes everything after it moot? Answer, in order:
(1) parity of the counterfactual evaluator (if it fails, no search number exists); (2) the realised difference-reward cell
A-real/B-real beating the rule (if not, the whole B-chain is moot, untrained); (3) the nominal cell of the chosen path
clearing the deployability gate (if not, the credit is right but the observation is wrong — redesign the observation
before any learner); (4) for scenario A, the power-headroom accounting (if power control has no room here either, A1 is
dead before it is built). Measure these first; nothing else is scheduled ahead of them.

## 6. Operating rules (adopted; bought with time these two days)

1. **Data from fixed policies is generated once, in parallel, before use** (pools cut A2/A3 from 6.6 s to ~2 s per
   episode); the same applies to oracle rollouts and reference actions.
2. **Concurrency is measured, not assumed**: single-process speed first, then the count. 18 training processes on 20 cores
   (8P + 12E, no SMT) ran ~3× slower each; the working cap is ~10–12 concurrent compute processes. (At 14:38 UTC the
   ceiling agent had 19 running against a cap of 10; nothing is killed, nothing new launches until ≤ 10.)
3. **Any multi-hour launch gets a fresh-context agy read of the actual diff first** (10–15 min; it caught four launch-control
   defects that would have corrupted the pilot's record).
4. **Progress files carry detached PIDs, commands, cwd, outputs; launchers are idempotent** — this is what let the pilot be
   stopped, restarted, and resumed across three quota interruptions.

## 7. Agent-quota note (operational)

The sonnet agent running the LP grid hit a **weekly** API limit at 14:45 UTC (resets 04:00 Asia/Taipei); its detached
grid keeps running on `sat`. An opus agent took over the LP finish and the oracle cells (`.scratch/h4-probe/LP-AND-ORACLE-
TASK.md`). Model choice for the rest of today: opus for measurement/instrument work, Fable for the audit's phase 2b,
agy for cross-model checks; no sonnet until the reset.
