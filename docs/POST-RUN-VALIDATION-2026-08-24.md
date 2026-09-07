# MCRL P6-to-Main Post-Run Validation

> **Superseded for baseline acceptance (2026-08-25).** A later runtime audit
> confirmed warm-start age overwrite and duplicate candidate fading draws in
> the exact source bytes used here.  This report remains a valid completion
> receipt for that defective implementation, but none of its EE, LR-selection,
> collapse, or Catfish conclusions apply to the intended corrected baseline.
> See `CONTROLLER-RULINGS-MODQN-RUNTIME-CORRECTION-2026-08-25.md`.

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-08-24T19:20:28+08:00
- Verification Status: ANALYZED
- Version Label: validation_v1
- Integrity Pass Date: 2026-08-24T19:20:28+08:00
- Upstream Dependencies: corrected preregistration `01b0d85cedbd67f80a24c2adf7ff4181c728070111d06334e8dc55f07f52c022`

## Validation Report

- **Source:** Ubuntu server run `/home/sat/mcrl-leo-handover/artifacts/training-2026-08-24`
- **Pipeline status:** `complete`
- **P6 status:** three finite, complete 9,000-episode arms; ten shared final-policy evaluation seeds per arm
- **Selected learning rate:** `0.001`, by the frozen mean calibrated scalar-reward selector
- **Main status:** `complete`, 9,000/9,000 episodes with independent seeds `(42, 1337, 7)`
- **Finished:** 2026-08-24 17:35:21 Asia/Taipei; elapsed 15 h 47 min 23 s
- **Overall Confidence:** `CAUTION`

`CAUTION` does not mean the run failed. The run and its artifacts completed cleanly.
It means that the preregistration froze no numerical collapse cutoff, the main run has
one seed triplet, and the P6 final-policy evaluation uses the train split. These data
support a descriptive B17 answer, not a held-out or population-level performance claim.

## Controller-facing outcome

The selected arm and independent main run **do not reproduce the near-single-beam
catastrophic collapse seen at `alpha = 0.01`**. They do retain substantial policy
concentration. In the main tail-100 window, greedy choices move from 2.51 active beams
and 74.35% argmax agreement at the first decision to 7.77 beams and 51.12% agreement
at the last decision. The within-episode direction is de-concentrating, but the absolute
last-step agreement remains high.

Therefore the evidence-backed B17 answer is:

> **Catastrophic collapse: not reproduced at the selected learning rate. Residual
> concentration: present.**

The frozen materials provide no cutoff that would turn those two observations into a
stronger binary label. The specific premise that a selected plain-MODQN baseline
catastrophically collapses and therefore needs a catfish mechanism is not supported by
this run. This is a controller/editorial gate; this validation does not rewrite Chapter 5
or authorize a new mechanism.

## Guard and integrity receipts

- Fresh server `validate` run: `server guards PASS`; this executes
  `PreregRecord.verify()`, the P6 protocol and live ephemeris checks, actual environment
  construction, and `assert_ready_to_train()`.
- Corrected preregistration self-digest:
  `01b0d85cedbd67f80a24c2adf7ff4181c728070111d06334e8dc55f07f52c022`.
- P6 `excluded_nonfinite_or_incomplete` is empty. Contrary to the prior expectation,
  `alpha = 0.01` remained finite and completed; its poor score and collapse pattern are
  results, not reasons to alter or rerun the protocol.
- All four locally mirrored episode logs match the SHA-256 stored in their completed
  status records.
- All four server-side final checkpoints match their completed status records:

| Run | Episode-log SHA-256 | Final-checkpoint SHA-256 |
|---|---|---|
| P6 `0.01` | `4a1bdbf8e599ce1eaddce2e6dbb17ae0c70103789595ce69065f0c7929b23464` | `31750e15994a2358d21abffb7e43bdd0b3ee7db323e45a44a10152e7404730d5` |
| P6 `0.003` | `6b05cbd4043987b060edaec53b5f6eb7189d8bccf61865c970d8166207b2e354` | `e042f7f8981f745cbe52d9db051c4231a3e27ae37cff56d7b6bb3355afdc2fb8` |
| P6 `0.001` | `575c8852663aeb658a236aca232a9abc1c13b57785499dfa33c9477ab8f2609f` | `311f4022a82d69510ab744754e7e304a25a1387efbd1f84c8727066ad496f7ac` |
| Main `0.001` | `61d4668eca261b221c34c170164f0b70d4b03ebd60043d0272c966899fe5b011` | `c24ee59bfde7d9b324b40dccdae3132571ae31da7753c9f71dcaaddca1a8a351` |

The checkpoint bytes remain on the Ubuntu server. The local evidence mirror contains
the status, summary, training log, and all episode-log JSON files; it deliberately does
not duplicate 365 MB of checkpoint payloads.

## P6 frozen-selector result

The primary selector is exactly the preregistered mean calibrated scalar reward over
ten shared evaluation seeds. Standard deviations and paired wins below are descriptive
diagnostics and did not override that selector.

| `alpha` | Status | Mean calibrated scalar reward | Sample SD | Tail greedy beams, first to last | Tail greedy agreement, first to last |
|---:|---|---:|---:|---:|---:|
| `0.01` | complete | -0.995032 | 0.129040 | 1.06 to 1.67 | 0.9902 to 0.8400 |
| `0.003` | complete | 0.353003 | 0.145727 | 2.20 to 7.56 | 0.8156 to 0.5562 |
| `0.001` | complete, selected | **0.503674** | 0.171866 | 2.62 to 6.94 | 0.7479 to 0.5343 |

Selection diagnostics:

- `0.001` beats `0.003` on 9/10 shared evaluation seeds; mean paired difference
  `+0.150671`.
- `0.001` beats `0.01` on 10/10 seeds; mean paired difference `+1.498706`.
- Modal order is `0.001 > 0.003 > 0.01` on 90% of seeds; Kendall's `W = 0.91`.
- No p-value, significance threshold, or diagnostic veto was preregistered; none is
  introduced after observing the results.

## P6 collapse four, tail-100 episodes

These are greedy-policy readings. Executed action counts agree closely in the final
epsilon regime and are retained in the episode logs.

| `alpha` | Point | Active beams | Argmax agreement | Normalized Q margin | Q entropy |
|---:|---|---:|---:|---:|---:|
| `0.01` | first | 1.06 | 0.9902 | 0.04876 | 0.98486 |
| `0.01` | last | 1.67 | 0.8400 | 0.05496 | 0.98308 |
| `0.003` | first | 2.20 | 0.8156 | 0.06462 | 0.99585 |
| `0.003` | last | 7.56 | 0.5562 | 0.15588 | 0.99218 |
| `0.001` | first | 2.62 | 0.7479 | 0.04329 | 0.99682 |
| `0.001` | last | 6.94 | 0.5343 | 0.24444 | 0.99591 |

`alpha = 0.01` is the only arm with a near-single-beam first-step policy and near-unanimous
agreement. It completed without a non-finite exception, so the earlier expectation that it
would abort is empirically false for this frozen run.

## Main collapse result, tail-100 episodes

Q margin and entropy come from the Q surface and therefore have no separate executed
version. Active-beam count and agreement are shown for both greedy and actually executed
actions.

| Point | Greedy beams | Executed beams | Greedy agreement | Executed agreement | Q margin | Q entropy |
|---|---:|---:|---:|---:|---:|---:|
| First | 2.51 | 3.33 | 0.7435 | 0.7372 | 0.04187 | 0.99641 |
| Last | 7.77 | 8.41 | 0.5112 | 0.5068 | 0.22432 | 0.99627 |
| Last minus first | **+5.26** | **+5.08** | **-0.2323** | **-0.2304** | **+0.18245** | -0.00014 |

The positive beam-count drift and negative agreement drift oppose within-episode collapse.
The absolute agreement levels still show homogenization, while entropy remains close to
one. The safe interpretation is partial de-concentration, not fully diverse allocation.

## Calibrated objective contribution shares

For each window, the calculation follows the live contract:
`contribution_j = omega_j * mean(abs(r_j)) / c_j`; shares normalize the three positive
magnitudes to 100%. They are not the signed scalar reward.

| Window | `r1` EE | `r2` handover | `r3` load | Status |
|---|---:|---:|---:|---|
| Reference policy | 43.5% | 14.3% | 42.2% | frozen pre-training comparison |
| Main, all 9,000 episodes | 53.49% | 26.84% | 19.67% | includes epsilon decay |
| Main, tail 1,000 | 57.27% | 21.57% | 21.16% | descriptive sensitivity |
| Main, tail 100 | **57.62%** | **20.92%** | **21.47%** | final-policy descriptive window |
| Tail-100 minus reference | +14.12 pp | +6.62 pp | -20.73 pp | descriptive difference |

The preregistered narrative correctly anticipated that the handover share would rise.
The larger redistribution is from `r3` toward `r1`; nominal weights `(50, 30, 20)` do
not describe the observed contribution magnitudes. The tail-100 and tail-1,000 estimates
are close, but the reporting window itself was not frozen as a formal selector, so both
are disclosed.

## Statistical findings and warnings

| Finding | Test | Value | Effect size | Confidence |
|---|---|---|---|---|
| P6 learning-rate selection | frozen mean ranking | `0.001` ranks first, 9/10 modal order | paired mean vs `0.003`: `+0.150671` | SOLID for this sweep |
| Catastrophic-collapse reproduction | descriptive tail-100 collapse four | main 2.51 to 7.77 beams; agreement 0.7435 to 0.5112 | no frozen categorical cutoff | CAUTION |
| Objective balance | magnitude-share decomposition | tail-100 57.62 / 20.92 / 21.47 | reference delta +14.12 / +6.62 / -20.73 pp | CAUTION |

Warnings:

1. P6 evaluation is on the train split. It selects a learning rate under the frozen
   protocol but is not held-out generalization evidence.
2. Main uses one frozen seed triplet and has no independent post-training test-split
   evaluation in this artifact set.
3. No numerical B17 collapse threshold was preregistered. A threshold invented now
   would be outcome-adaptive.
4. The logs do not contain the full outage and action-mask accounting needed to revisit
   the separate claim that geometry and power gates are non-binding under the learned
   policy.
5. P6, Main, and the objective-share calculation establish baseline behavior only; they
   do not test a catfish intervention or a comparative contribution claim.

## Fallacy scan

- **Coverage:** 11/11 statistical fallacy types checked.

| Fallacy | Severity | Finding |
|---|---|---|
| Simpson's paradox | CAUTION | No subgroup table is present, so aggregate collapse and reward shares cannot rule out geometry-, time-, or user-stratum reversals. |
| Ecological fallacy | CAUTION | Aggregate beam/agreement statistics do not imply that every user received the same behavior or service. |
| Berkson's paradox | NOTE | No admission-conditioned sample was identified; the explicit train-split restriction is reported separately. |
| Collider bias | NOTE | No covariate-adjusted regression or conditioned causal estimate is made. |
| Base-rate neglect | NOTE | No classifier, sensitivity, specificity, PPV, or NPV claim is made. |
| Regression to the mean | NOTE | Arms were preregistered, not selected from extreme pre-test outcomes; no pre-post causal claim is made. |
| Survivorship bias | NOTE | All three P6 arms and Main completed; no arm was excluded as incomplete or non-finite. |
| Look-elsewhere effect | NOTE | Three arms and the selector were frozen; diagnostic metrics did not alter selection. |
| Garden of forking paths | CAUTION | The training protocol was frozen, but tail-100/tail-1,000 reporting windows are post-run descriptive views and are both disclosed. |
| Correlation is not causation | CAUTION | A single main seed and no intervention comparison cannot establish a general mechanism or catfish effect. |
| Reverse causality | NOTE | Not applicable to the controlled LR sweep; no observational directional claim is made. |

## Reproducibility verdict

- **Method:** artifact-integrity verification plus fresh server guards; no full training rerun
- **Verdict:** `CANNOT_VERIFY` for full experiment reproducibility
- **Reason:** an exact rerun would repeat approximately 15 h 47 min of heavy server
  training. It was not silently launched as part of post-run validation.

This report is therefore `ANALYZED`, not `VERIFIED` under the experiment-agent contract.
The byte-matched logs, checkpoints, fingerprints, preregistration digest, and completed
pipeline receipt establish integrity of this run; they are not a second independent run.

## Authority boundary

This report closes the post-run controller evidence request. It does **not** by itself:

- authorize changing the corrected preregistration or rerunning with tuned settings;
- promote the train-split P6 scores into held-out performance claims;
- fill Chapter 5, slides, or thesis tables;
- authorize a catfish implementation or contribution claim.

Those are separate controller/editorial decisions after accepting the mixed B17 result.
