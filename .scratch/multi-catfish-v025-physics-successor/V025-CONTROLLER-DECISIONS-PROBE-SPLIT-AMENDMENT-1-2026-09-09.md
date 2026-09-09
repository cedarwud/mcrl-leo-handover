# Amendment 1 to the probe-split decision — the pre-fix arm is stopped, and the first corrected attempt was discarded
Recorded 2026-09-09, server clock 07:47 UTC. **No regime has reported a verdict on either arm.** Both actions below are taken on code-and-configuration facts, not on any observed result.

The parent record is `V025-CONTROLLER-DECISIONS-ACM-FIX-PROBE-SPLIT-2026-09-09.md`. That record said the pre-fix arm would be allowed to finish and would serve as the "before" arm of a paired contrast. That is withdrawn, for the reason below.

## 1. The pre-fix arm is not a paired contrast, so it is stopped
A paired contrast isolates one difference. An audit of the running arm found **three** simultaneous differences from the corrected arm, not one:

1. **Superseded physics.** Its `acm.py`, `resolution.py`, `batch.py`, `tapes.py`, `provider_legacy.py`, `channel.py`, `architectures.py` and `adapter.py` all differ from the stage-4h tree. Its batch kernel still computes `eligible_modes = realised_sinr >= thresholds`, the genie form.
2. **Stale prices.** Its calibration cache holds sampled genie-ACM values, for example `eta_ref = 2.705769e+07` bit/J for `a-r0`, against the corrected sealed `1.972068e+07`. Since `eta_ref = B_ref / E_ref` and `kappa = B_ref / (U · N_ref)` are enforced as identities, every price moves with credited bits. Both terms of `F = B − eta_ref·E − Phi` are therefore wrong, and not by a common factor.
3. **An uncertified anchor.** Its own log records `step 0: u iterations=2 sweeps=2 termination=BUDGET_LIMITED_MID_SWEEP wall=93.7s`. The probe's entire argument is that at a certified unilateral optimum every legal single move is non-improving, so an improving joint move must carry `Psi_A^u > 0`. With `u` uncertified that premise is simply not established.

A comparison that differs in three ways at once attributes nothing. Reading a difference between the arms as "the ACM correction created the interaction" would be unsupportable, and reading a pre-fix null as evidence about the corrected physics was already ruled out in the parent record. The arm was therefore stopped at 07:44 UTC with no verdict read.

## 2. The first corrected attempt was discarded before producing anything
The workspace `mcrl-v025-probe-ws-acmfix`, created at 06:13, was **half-corrected**. Its eight physics modules were current, but its `run_v025_matrix_probe.py` was the superseded 215,791-byte build containing **zero** occurrences of `fading_quantile_alpha` and **zero** of `realised_outcome`, against 30 and 9 in the stage-4h build.

Under that combination the run would have evaluated with `fading_quantile_alpha = None`, hence `quantile = 1.0`: causal mode selection with **no fading reserve at all**. That is a third semantics, neither the genie rule nor the sealed 10th-percentile rule, and it appears in no declaration. It was stopped at 07:43 and the workspace is quarantined as `mcrl-v025-probe-ws-acmfix-BROKEN-stale-runner`.

## 3. What replaces both
`/home/sat/mcrl-v025-probe-ws-acm2`, a clean `git archive` of engine commit `75c5c78c` ("Finish V0.25 stage 4h physics gate"), with only the three existence-probe scripts copied in. Verified: runner 277,997 bytes, 30 `fading_quantile_alpha`, 9 `realised_outcome`; all eight physics modules byte-identical to the engine and all eight different from the pre-fix tree.

Three standing traps are written into its instructions:
* every world and calibration tape is built **fresh in this workspace**, because `tapes.py` and `provider_legacy.py` differ between trees;
* the calibration cache directory starts **empty**, because the cache is keyed on regime name alone with no physics digest and would otherwise load genie prices silently;
* the unilateral budget is raised until `u` is genuinely certified, and the certification rate is a headline number. Certified and uncertified anchors are reported separately and never pooled.

## 4. Why raising the unilateral budget is not tuning
A longer unilateral search returns a **better** `u`, which raises the bar that any improving joint move must clear. The change is therefore conservative against the C3 hypothesis, not favourable to it. It also is not a scientific parameter: it is the compute budget of an offline analysis whose termination status is reported either way.

## 5. Cost of the two discarded attempts
About four core-hours and two hours of wall time. Both were stopped on inspection of code and configuration, before either could report. The alternative was a decisive experiment answering a question about physics we do not intend to publish.
