# Corrected R2 MODQN post-run validation (2026-08-26)

## Material Passport

- Origin Skill: `academic-research-suite` experiment-agent
- Origin Mode: `validate`
- Origin Date: 2026-08-26
- Verification Status: `ANALYZED_WITH_EXACT_EVALUATION_REPLAY_AND_POSTRUN_METRIC_REPAIR`
- Version: `validation_v2`

## Executive verdict

The corrected MODQN run **completed normally**: no non-finite failure or late
numerical divergence was observed.  All four 9,000-episode arms are finite and
complete, the selected learning rate is unambiguously `0.001`, and the
independent main run settles near 91 Mbit/J during its low-epsilon training
tail.  A deterministic final-checkpoint replay reports **90.52 Mbit/J**,
**99.90% service**, 38.73 Gbit/s, and 428.46 W.

The formal Catfish go/no-go result is nevertheless **UNREADABLE**, not
“Catfish unnecessary.”  The numeric threshold branch alone returns
`unnecessary` for the selected P6 arm and main run, but its frozen null
precondition fails: the untrained greedy null is already concentrated at only
2--3 action slots and 90--99% agreement, while the episode-0 executed random
proxy uses 27--28 slots at only 9--10% agreement.  Two implementation/record
semantic mismatches further prevent a defensible formal verdict:

1. `active_beam_count` counts distinct **relative action indices**, not physical
   `(norad_id, cell_id)` beams.  The main training-tail median is four slots,
   while the separate final-checkpoint replay serves through about 69 physical
   beams per step; they are different estimands and cannot share one label.
2. The frozen record says to normalise by the **per-user** Q range; the
   launched implementation computed `mean(margin) / mean(range)`, not
   `mean(margin / range)`.  The diagnostic implementation is now repaired,
   but the original 9,000-row histories cannot be reconstructed because they
   did not retain per-user Q rows.

Within the currently readable descriptive indicators, the corrected baseline
does not show joint Q/action sharpening: main-tail Q entropy remains 0.9966 and
its normalised margin 0.0552, while the physical replay shows broad beam use and
only 4.17% mean maximum load share.  This does not establish absence of
collapse, because the formal criterion is unreadable; it only says the present
run supplies no positive evidence for the claimed joint pathology.

The EE number is **not low relative to the available internal baselines**.  On
the same ten train-split evaluation seeds, main wins all 10/10 paired seed
comparisons.  Its pooled arithmetic-mean EE ratios are 51--68% higher; these
are not means of per-seed percentages, and the 68% random-masked contrast also
contains a service difference (99.90% versus 93.83%).  This is a conditional
internal descriptive comparison, not a held-out, literature, causal, or SOTA
claim.

## Measurement-repair addendum

The measurement-only patch now computes
`mean((top1 - top2) / (top1 - bottom1))`, labels the legacy
`active_beam_count` as relative action-slot occupancy, reports actual physical
beams separately, uses tail-1000 medians in future status summaries, and makes
the PREREG rebuild operate on the exact frozen 373-file view.  The new
heterogeneous-range oracle distinguishes the two Q-margin formulas:
`0.019802` from the launched ratio-of-means implementation versus the correct
per-user result `0.505`.

Final-checkpoint replay on the fixed ten evaluation seeds gives the following
main-model first-to-last means:

| Metric | First | Last |
|---|---:|---:|
| Relative action slots | 3.3 | 10.1 |
| Action-slot agreement | 0.533 | 0.437 |
| Effective physical beams | 66.0 | 70.7 |
| Physical maximum load share | 3.90% | 4.01% |
| Repaired per-user Q-margin | 0.0640 | 0.1375 |
| Q-entropy | 0.9964 | 0.9952 |

Thus the final policy shows modest Q sharpening while action choice and actual
physical use disperse.  This is not joint collapse.  Because it is a
post-result final-checkpoint diagnostic rather than the unavailable corrected
tail-1000 history, it cannot retroactively repair the formal criterion.  It is
nevertheless sufficient to reject collapse severity as the trigger for the
next Catfish design stage.  The next gate is the R2/R3 objective-inclusion
factorial in `CATFISH-DESIGN-FREEZE-GATE-2026-08-26.md`.

## Evidence and integrity boundary

| Item | Result |
|---|---:|
| Canonical record digest | `3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4` |
| Canonical record byte SHA-256 | `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543` |
| Launched training-source SHA-256 | `544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4` |
| Current diagnostic-source SHA-256 | `fa86cf49c3fbd0e9ddc2d324adbfcbe6d315fce9905d78b4e4b7f6b968823668` |
| Source relationship | intentionally different after measurement-only patch; checkpoints and reward path unchanged |
| Runs / episodes | 4 complete / 36,000 total |
| Pipeline exit | zero; complete at 2026-08-25 19:39:51 UTC |
| Episode-log hashes | all four match status records |
| Final-checkpoint hashes | all four match status records and server receipts |
| Frozen TLE view | 373 files, manifest hash matched |
| Recorded server dependencies | Python 3.13.3, Torch 2.13.0, NumPy 2.5.2, SGP4 2.27, PyYAML 6.0.3 |
| Local replay dependencies | Python 3.12.3, Torch 2.13.0+cpu, NumPy 2.5.2, SGP4 2.27, PyYAML 6.0.3 |
| P6 checkpoint replay | exact for all three arms; maximum absolute difference 0 |
| Current full suite | 822 passed, 1 skipped, 0 failed (823 collected) |
| Full training rerun | **not performed**; checkpoint replay is not 15-hour training reproducibility |

The main checkpoint has no stored P6-style greedy row against which to demand a
byte-for-byte numeric replay match.  Its physical evaluation is deterministic
from the frozen final checkpoint and matched inputs, but carries that narrower
verification status.

## P6 selection and run health

| Learning rate | Mean calibrated scalar reward | Sample SD | Same rank on seeds | Replay EE (Mbit/J) | Service | Physical beams | Infeasible outage |
|---:|---:|---:|---:|---:|---:|---:|---:|
| **0.001** | **0.9856** | 0.1190 | 10/10 first | **93.62** | 99.85% | 68.34 | 0.15% |
| 0.003 | 0.4055 | 0.1532 | 10/10 second | 80.24 | 99.93% | 56.54 | 0.07% |
| 0.01 | -0.8919 | 0.1638 | 10/10 third | 35.87 | 91.77% | 45.06 | 8.23% |

The selector reproduces `0.001`; it beats both alternatives on every frozen
evaluation seed, the modal ordering is identical on all seeds, and Kendall's
W is 1.0.  The `0.01` arm did not crash, but it is scientifically poor: low EE,
large outage, and action-slot concentration.  The **main-run** low-epsilon
training blocks from episodes 2,000--8,999 remain roughly 91.1--92.0 Mbit/J,
with finite losses and no late-run divergence.

The near-tie random control changes only 3.0% of decisions in the selected arm
and changes system EE by about +0.016 Mbit/J on average.  This supports low
sensitivity to that particular near-tie randomisation, not LR ordering
stability; the separate 10/10 ordering and Kendall W=1 results support the
latter.

## EE in physical units and matched references

The episode log's `r1_mean` is not directly a mean system EE.  Each episode
sums ten step-level user contributions and divides by 100 users.  Because the
user contributions add exactly to system EE at each step,

`mean step system EE = r1_mean * users / steps = r1_mean * 10`.

That conversion gives 91.13 Mbit/J over the main run's last 1,000 training
episodes.  Exact physical checkpoint replay gives the more direct result below.

| Policy | EE (Mbit/J) | Service | Throughput (Gbit/s) | Power (W) | Physical beams | Max physical-beam share |
|---|---:|---:|---:|---:|---:|---:|
| **MODQN main** | **90.52** | **99.90%** | **38.73** | 428.46 | 68.64 | 4.17% |
| nearest-eligible | 59.81 | 99.48% | 16.31 | 264.91 | 41.42 | 6.21% |
| stay-if-possible | 59.86 | 99.48% | 16.30 | 264.48 | 41.41 | 6.18% |
| random-masked | 53.78 | 93.83% | 24.96 | 482.52 | 76.85 | 3.43% |

Pooled arithmetic-mean main/reference EE ratios are 1.514, 1.512, and 1.683
respectively; they are ratios of pooled means, not averages of per-seed ratios.
At the evaluation-seed level main wins 10/10 pairs against every reference;
mean paired improvements are 30.72, 30.66, and 36.74 Mbit/J.  The ten seeds are
the units of comparison; the 100 temporally nested replay steps are not treated
as 100 independent replicates.  The random-masked ratio is especially
conditional because its service is only 93.83%, versus main's 99.90%.

Only `stay-if-possible` is the R2 record's declared reference policy.
Nearest-eligible and random-masked are fixed rule policies already present in
the code/probe set, but this three-policy main comparison was added post-run and
is descriptive.  It uses the train split and cannot establish held-out
generalisation, superiority to published methods, or a causal reward effect.

## Formal collapse reading

The controller criterion requires the last-1,000 median movement of
`collapse_first` relative to episode 0, with both action-family and Q-family
indicators moving together.  The correct raw-log calculation is:

| Run | Episode-0 greedy `(slots, agreement, margin, entropy)` | Tail median | Movement toward saturation | Numeric branch if null were readable |
|---|---|---|---|---|
| P6 0.001 | `(2, .99, .2263, .9994)` | `(4, .64, .0494, .9965)` | `(-2.00, -35.00, -.2287, .0029)` | unnecessary |
| P6 0.003 | `(2, .99, .2263, .9994)` | `(2, .87, .0524, .9956)` | `(0.00, -12.00, -.2249, .0038)` | unnecessary |
| P6 0.01 | `(2, .99, .2263, .9994)` | `(1, 1.00, .0391, .9826)` | `(1.00, 1.00, -.2420, .0168)` | uncertain; action family only |
| Main | `(3, .90, .0829, .9991)` | `(4, .60, .0552, .9966)` | `(-.50, -3.00, -.0302, .0026)` | unnecessary |

That numeric branch is not the final verdict.  The criterion explicitly says a
near-saturated episode-0 null is unreadable, yet it supplied no numeric
near-saturation threshold.  The observed contrast with the executed random
proxy is decisive: P6 starts at `(28 slots, .10 agreement)` when executed, and
main at `(27, .09)`, while their untrained greedy readings are `(2, .99)` and
`(3, .90)`.  The frozen assumption that an untrained greedy argmax is close to
random is false in these runs.

Three implementation findings reinforce the claim ceiling:

- `active_beam_count = unique(selected_action_indices)`.  Action indices are
  per-user relative `(satellite_slot, beam_slot)` positions.  They are useful
  for action-slot homogenisation, but they do not count physical beams and
  cannot alone substantiate physical resource collapse.
- The implementation's Q margin is `mean(top1-top2) / mean(top1-bottom)`.  The
  record's per-user wording naturally specifies
  `mean((top1-top2)/(top1-bottom))`.  They differ when user Q ranges differ;
  existing tests lock the former instead of testing the frozen wording.  A
  two-user heterogeneous-range oracle gives 0.0198 under the live formula and
  0.505 under the per-user formula, a 25.5x difference.
- `status.json` summarises the final 100 episodes with a mean and includes
  last-step/drift fields.  The controller verdict requires the final 1,000
  `collapse_first` medians.  Raw logs preserve the needed old values, but the
  status summary must not be quoted as the verdict.

Therefore the only defensible formal label is **UNREADABLE**.  Descriptively,
main and the selected arm do not show joint action-plus-Q sharpening, and the
physical replay does not show beam concentration.

## What R1, R2, and R3 are actually doing

The last-1,000 main episodes have calibrated weighted-magnitude shares of
**63.17% R1 / 19.49% R2 / 17.34% R3**.  These are contribution magnitudes,
not causal effects.

### R1: energy efficiency

R1 is the additive user decomposition of the global system ratio:
`sum_u r1_u = sum_u R_u / P_system`.  Replay rechecks this identity at every
step.  R1 is the dominant scalarised term and main's 90.52 Mbit/J exceeds all
three simple references.  This is the only objective for which the current
run gives a direct favourable internal performance result.

### R2: handover penalty

R2 is not another EE term.  It is exactly `0`, `-phi1`, or `-phi2` from realised
association identity and can affect EE only indirectly by changing the learned
action sequence.  In the main tail it accounts for 19.49% of weighted reward
magnitude.  Across the last 1,000 training episodes it records a mean of 245.7
handover events per episode; each episode contains 1,000 user-step
opportunities.  It is therefore certainly not numerically absent.

However, across all ten final-main evaluation seeds the replay contains 514
`phi1` and 2,276 `phi2` events in 10,000 user-step opportunities: a 27.90%
event rate.  Stay-if-possible has 0 `phi1` and 1,741 `phi2` (17.41%);
nearest-eligible has 102 and 1,741 (18.43%).  Thus the current data do **not**
establish that R2 achieved superior handover control.  A matched remove-R2 arm
can estimate R2's marginal effect relative to the full model.

### R3: physical load count

R3 is exactly the negative realised eligible load of the user's physical beam.
Main uses 68.64 physical beams with 4.17% mean maximum share, compared with
about 41.4 beams and 6.2% for nearest/stay.  Random spreads further (76.85 beams,
3.43%) but loses service and EE.  This is consistent with a useful R3 trade-off,
but it is not proof that R3 caused the spread.

R3 and R1 are also partly aligned: spreading users reduces the `B/U` load
penalty in rate, which can improve EE.  That is why the user hypothesis that
“R3 can affect R1” is correct, and why reward-share arithmetic cannot tell us
whether R3 adds independent information.  The factorial ablation described
below is required.

## Formula and regression audit

The following live formulas match the intended corrected baseline and passed
their direct replay identities:

- R1 uses realised link rate divided by common system power; no epsilon is
  added to the denominator, and positive throughput at zero power fails closed.
- Per-user R1 contributions sum to system EE.
- R2 comes from physical association identity, not action-index changes;
  replay separates `phi1`, `phi2`, and re-entry.
- R3 uses the same physical eligible-load counts as rate and activation.
- Calibration is divide-by-fixed-scales with
  `(c1, c2, c3) = (2029238.4328742754, 1, 6)` and weights `(0.5, 0.3, 0.2)`.
- The run fingerprint binds every `src/mcrl/*.py`, the training launcher,
  `pyproject.toml`, dependency versions, seeds, trainer config, R2 digest, and
  frozen TLE file-set hash.  The analyzer verifies each run-fingerprint
  self-hash, roles, LR, seeds, trainer-config hash, checkpoint metadata, and P6
  row completeness.  Before the diagnostic repair, the current training
  source matched the launched hash.  The v2 analyzer now records both the
  immutable launched hash and the intentionally different diagnostic-source
  hash plus the explicit drift reason; the three stored P6 evaluation replays
  still match exactly with zero numeric difference.

The local replay dependency labels do not exactly match the Ubuntu training
environment: Python is 3.12.3 rather than 3.13.3 and Torch carries a `+cpu`
build suffix.  The three P6 checkpoint evaluations nevertheless reproduce every
stored scalar/vector result with zero numeric difference.  This supports the
evaluation path, but it does not turn the local machine into a fully matched
training environment or prove end-to-end training reproducibility.

The two prior full-suite failures were non-hermetic TLE-test defects, not model
failures.  The live-superset test now requires retention of the documented
coverage rather than an immutable newest date, while the PREREG rebuild creates
an exact temporary view from the recorded 373-file manifest.  The repaired
suite is green: 822 passed, 1 skipped, 0 failed.

## Statistical and inference audit

| Check | Disposition |
|---|---|
| Pre-result selector used as written | pass |
| Incomplete/non-finite arms excluded | pass; none excluded |
| Paired seeds used for P6/reference contrasts | pass |
| Temporal steps treated as independent replicates | avoided |
| P6 ranking stability reported | pass; 10/10 and W=1 |
| Effect size reported rather than p-value alone | pass |
| Multiple exploratory metrics promoted to selector | avoided |
| Train split distinguished from held-out | pass |
| Reward magnitude confused with causal effect | avoided |
| Post-result criterion rewrite | avoided; verdict remains unreadable |
| Missing/failed checks disclosed | pass; prior TLE failures repaired and full suite green |

## Decision and next experiment boundary

Do **not** launch a Catfish mechanism training run from this result yet.  The
prospective measurement-repair step is complete:

1. preserve existing artifacts and rename the old metric conceptually to
   `active_action_slot_count`; report actual radiating physical-beam count and
   concentration beside it;
2. freeze one exact Q-margin aggregation formula and add a heterogeneous-range
   regression that distinguishes ratio-of-means from mean-of-ratios;
3. make future producer summaries use the frozen tail-1000 median;
4. make the freeze-rebuild test use the recorded 373-file manifest; and
5. replay the existing final checkpoints on the fixed ten evaluation seeds
   with action-slot and physical-beam metrics kept separate.

The old episode-0 null was not rewritten after seeing results.  Its formal
verdict remains unreadable; the repaired checkpoint diagnostic is explicitly a
new descriptive measurement and not a retroactive threshold substitute.

The repaired checkpoint diagnostic finds no joint representation/physical
collapse.  The honest contribution direction is therefore not “three agents
curing a collapse”; it must be framed and tested as objective-specialist
exploration.  The next required experiment is the pre-result matched 2x2 set
in `CATFISH-DESIGN-FREEZE-GATE-2026-08-26.md`: full, remove-R2, remove-R3, and
remove-both.  The single-removal arms estimate marginal effects relative to
full; the fourth arm estimates R2/R3 interaction.  This heavy training belongs
on the Ubuntu server.  No post-training auction or coordination mechanism is
part of this recommendation.

## Reproduction entry point

The machine-readable analysis is produced by:

```bash
.venv/bin/python scripts/analyze_corrected_postrun.py \
  --replay \
  --source-tle-root /home/u24/demo/tle_data/starlink/tle \
  --analysis-source-drift-reason \
  "post-run diagnostic-only repair: per-user q_margin, action-slot semantics, and tail-1000 median; reward and checkpoint weights unchanged" \
  --output artifacts/CATFISH-MEASUREMENT-REPLAY-2026-08-26.json
```

Its claim ceiling is explicit: artifact integrity and final-checkpoint replay
are verified; full training reproducibility, held-out generalisation, Catfish
causality, and independent R2/R3 effects remain unverified.
