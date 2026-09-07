# Catfish objective-specialist design-freeze gate (2026-08-26)

## Material Passport

- Origin Skill: `academic-research-suite` experiment-agent
- Origin Mode: `plan`
- Origin Date: 2026-08-26
- Verification Status: `PLANNED_NOT_LAUNCHED`
- Version Label: `code_plan_v1`

## Decision now

The corrected final-checkpoint replay does not support a joint-collapse target.
Across the ten fixed evaluation seeds, the main model moves from the first to
the last decision of an episode as follows:

| Metric | First-step mean | Last-step mean | Reading |
|---|---:|---:|---|
| Distinct relative action slots | 3.3 | 10.1 | disperses |
| Argmax agreement | 0.533 | 0.437 | disperses |
| Effective physical beams | 66.0 | 70.7 | disperses |
| Physical maximum load share | 3.90% | 4.01% | approximately flat |
| Per-user-normalised Q margin | 0.0640 | 0.1375 | sharper Q |
| Normalised Q entropy | 0.9964 | 0.9952 | slightly sharper Q |

This is Q-only sharpening with action/physical dispersion, not joint
representation-and-action collapse.  It is a new post-run checkpoint
diagnostic, not a reconstruction of the frozen episode-0 to tail-1000
criterion: the original logs did not retain per-user Q rows or physical beam
identities.

Consequently, a collapse-triggered Catfish cannot be the design authority.
The remaining defensible question is whether R2 and R3 are independently useful
training targets, and whether R3's effect is actually mediated by or coupled to
R1.  The following 2x2 gate must answer that before three independent
reward-specialist Catfish roles are frozen.

## Experiment overview

- **Title**: R2/R3 objective-inclusion factorial for Catfish role selection
- **Objective**: estimate the marginal and interaction effects of exposing the
  policy scalarisation to R2 and R3 while leaving all reward definitions and
  Q-head updates intact.
- **Type**: matched MODQN training plus fixed-seed checkpoint replay
- **Learning rate**: `0.001`, already selected by the completed P6 protocol
- **Episodes**: 9,000 per arm
- **Training seeds**: the same main train/environment/mobility seeds for every
  arm in the screen
- **Evaluation seeds**: the existing ten fixed P6 evaluation seeds
- **Split**: train split for the first design screen; held-out generalisation is
  a later claim gate and must not be inferred from this screen

## Four arms

Only scalarisation weights change.  R1/R2/R3 reward vectors, calibration,
replay labels, three Q-head TD updates, environment, epsilon schedule, network,
seeds, and evaluation procedure remain identical.  Remaining weights are
renormalised so the configured weights sum to one; this preserves their ratio
and does not change the greedy argmax relative to an equivalent common scaling.

| Arm | R2 included | R3 included | Objective weights `(R1,R2,R3)` |
|---|---:|---:|---:|
| `full` | 1 | 1 | `(0.5, 0.3, 0.2)` |
| `minus-r2` | 0 | 1 | `(5/7, 0, 2/7)` |
| `minus-r3` | 1 | 0 | `(5/8, 3/8, 0)` |
| `r1-only` | 0 | 0 | `(1, 0, 0)` |

The factors mean “available to action scalarisation,” not “reward was no
longer measured.”  All three raw and calibrated rewards must still be logged
and evaluated in every arm.

## Primary endpoints

The evaluation seed, rather than each nested decision step, is the comparison
unit.

| Target | Primary endpoint | Required supporting endpoints |
|---|---|---|
| R1 | paired seed episode-mean system EE (bits/J) | throughput, consumed power, service fraction, zero-over-zero |
| R2 | paired seed `phi1 + phi2` incidence per user-decision | `phi1`, served-to-served `phi2`, re-entry `phi2`, total handover penalty |
| R3 | paired seed raw R3 and maximum physical-beam load share | maximum/mean load, effective physical beams, service fraction |
| Interaction | difference-in-differences for R2 and R3 primary endpoints | the same interaction on EE and service safeguards |

Corrected Catfish diagnostics are reported beside these endpoints:
`active_action_slot_count`, action-slot agreement, per-user-normalised
Q-margin, Q-entropy, effective physical beams, and maximum physical load share.
No field named `active_beam_count` may be described as a physical beam count.

## Pre-result decision rules

For the one-training-seed design screen, an inclusion effect is provisionally
actionable only if:

1. its direct endpoint improves in the expected direction on at least 8 of the
   10 paired evaluation seeds;
2. the paired 95% bootstrap interval for the mean direct effect excludes zero;
3. mean service does not fall by more than 0.5 percentage points; and
4. mean EE is at least 95% of the corresponding removal arm when R2 or R3 is
   added.

These rules select a mechanism-design target; they do not estimate
training-seed uncertainty.  If a direct effect changes sign depending on the
other factor, or the interaction interval excludes zero, the objectives are
treated as coupled.  If any result misses the directional-consistency rule or
touches a safeguard, the screen is `AMBIGUOUS` and must be repeated with at
least three independent training seeds before a design freeze.

## Catfish role decision table

| Factorial result | Permitted design conclusion |
|---|---|
| R2 and R3 both independently useful; no sign-changing interaction | Three training-time specialists may be designed: EE, handover persistence, and load balance |
| R2 useful; R3 useful only through R1/R3 interaction | Do not create an independent R3 Catfish; use a coupled EE-load specialist |
| R3 useful; R2 fails its direct handover endpoint | Do not create an R2 Catfish; redesign R2 before Catfish work |
| Neither direct endpoint passes | At most an R1 specialist is justified; three Catfish would be decorative |
| Any ambiguous or safeguard-failing cell | No design freeze; run the multi-training-seed confirmation |

If the first row passes, the candidate new training-time carrier is
**objective-regret-gated counterfactual replay**: three reward-specific
specialists propose transitions, each specialist admits only experiences with
positive advantage for its own objective and a precommitted cross-objective
harm budget, and the main learner samples the three audited banks.  This is not
post-training coordination.  It is still only a candidate architecture until
the factorial identifies three defensible targets and matched random-admission
controls are frozen.

The existing `catfish-mechanisms` library is not yet that design.  Its current
menu explicitly labels per-objective banks/ACRM and starvation-triggered mix as
engineering adaptations, does not implement one Catfish per reward, and none
of its seven candidates fixes both collapse families in the synthetic testbed.
Its collapse formula and baseline-intake pins also predate the repaired R2
measurement and must be revised in that repository before any integration.

## Expected duration and design-freeze date

The corrected server pipeline consumed 15:49:16 for four 9,000-episode runs;
the independent main arm consumed about 3:58.  A strictly sequential four-arm
factorial is therefore budgeted at **16--18 hours**, plus **1--2 hours** for
artifact transfer, exact checkpoint replay, paired analysis, and ruling.

If launched on 2026-08-26 and all four cells pass, the **mechanism-design
architecture can be frozen on 2026-08-27**.  If the screen is ambiguous and
three training seeds are required, budget roughly **2--3 days** on the server.
Neither date means that the eventual Catfish implementation has already proved
effective; that requires a later candidate-versus-matched-control training
experiment.

## Ubuntu server worker handoff

> **Heavy worker — run on the Ubuntu server, not WSL. Estimated wall time:
> 16--18 hours sequential, or about 8--12 hours with carefully verified
> two-way parallelism and sufficient CPU/RAM.**

Setup before opening the worker:

1. SSH to the Ubuntu training server.
2. Sync this repository plus the canonical R2 prereg, corrected probe bundle,
   completed checkpoints, and `CATFISH-MEASUREMENT-REPLAY-2026-08-26.json`.
3. Confirm the Python environment and recorded dependency versions; run the
   server validation command against the exact 373-file frozen TLE view.
4. Open a fresh Codex worker session in the synced repository.
5. Paste the following prompt.  Do not launch training until implementation
   tests, a fresh immutable factorial manifest, output-path emptiness, and
   controller preflight all pass.

```text
[heavy | estimated 16-18 h sequential]

Implement and execute the pre-result R2/R3 objective-inclusion factorial in
docs/CATFISH-DESIGN-FREEZE-GATE-2026-08-26.md. Preserve the canonical R2 prereg
bytes and all completed baseline artifacts. Create a separate immutable
factorial manifest and a fresh output directory. The four arms are full,
minus-r2, minus-r3, and r1-only with the exact normalized weights in the gate.
Only action scalarisation weights may differ; all three reward vectors and Q
heads remain live and logged. Fingerprints must include arm ID, exact weights,
code, dependencies, TLE manifest, trainer config, and seeds. Add red-capable
tests for arm construction, fingerprint non-reuse, no-op/full equivalence,
resume parity, and corrected Catfish metric semantics. Run the existing server
preflight and full test suite before launch. Train under tmux with durable
per-arm status/checkpoint/log receipts and no silent retries. After completion,
evaluate all final checkpoints on the ten fixed evaluation seeds, report paired
R1/R2/R3 endpoints, physical beams/load, corrected Q/action diagnostics, and
the 2x2 interaction. Apply the frozen decision table without changing it after
seeing results. Do not integrate catfish-mechanisms, coordination, auction, or
deployment-time action overrides in this experiment.
```

## Expected outputs

| Output | Success criterion |
|---|---|
| immutable factorial manifest | self-hash valid; exact arm weights/seeds/source/TLE/dependencies pinned |
| four arm directories | 9,000 contiguous finite episode rows and final checkpoint hash per arm |
| factorial replay JSON | ten evaluation seeds per arm; corrected action/Q/physical metrics complete |
| paired factorial report | marginal R2, marginal R3, interaction, safeguards, and decision-table result |
| terminal receipt | zero exit, start/finish time, maximum RSS, no hidden retry |

