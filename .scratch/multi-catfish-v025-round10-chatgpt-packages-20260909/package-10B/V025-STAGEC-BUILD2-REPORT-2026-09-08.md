# V0.25 Stage C build 2 report

Date: 2026-09-08. Scope: contract-v1 implementation and synthetic acceptance only. No real/TLE worlds were generated, no sealed artifact was edited, and no successor training was run.

## Result

Build 1 was reworked to the binding `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md` and the controller's 2026-09-08 decisions. The implementation now has explicit A1–A4 information records and matched-anchor catalogue authentication; Φ-inclusive and physical coalition identities; separate action and coalition shards; a scalar permutation-invariant two-layer set head with exact empty/singleton zeros; S3/S0/S_UNI in one selector; four distinct experiment schemas; complete neutral-source declarations; twelve domain-derived learner seeds; crossed-panel inference and zero-outcome rules; and BASE-first runner-timed cancellation with a capability manifest.

The required initial hub update was attempted with `git -C /home/sat/mcrl-hub pull` but failed with `cannot open '.git/FETCH_HEAD': Read-only file system`. The review therefore used the hub's current checkout at `24c9b3bcadd1079dffbf9ca940bcc6b22dd8a559` and read the v1 contract, adjudication, outside QA, and controller-decision document there.

## Pytest gate

Acceptance command and observed result:

```text
/usr/bin/time -f 'ELAPSED=%e' /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/stagec_v025/test_contract_v1_acceptance.py
...                                                                      [100%]
ELAPSED=16.46
```

Broader Stage-C/target regression command and observed result:

```text
/usr/bin/time -f 'ELAPSED=%e' /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/stagec_v025 tests/physics_v025/test_stage2_tapes_targets_state.py
...................................                                      [100%]
ELAPSED=19.06
```

- **T1 passed:** exhaustive 2^3 profiles at each of the three hand-computed steps; additive, synergistic and antagonistic payoffs; dummy credit; nonzero Φ exactly once; future absorbing outage; both reconstruction identities; exact Shapley reporting; oracle C1/C2/C3 removals; learned neutral C3 update; checkpoint knockout; and the four experiment schemas.
- **T2 passed:** per-user information twins with opposite interactions; declared joint-context separation and context-removal failure; empty/singleton anchors; permutation and physical-ID relabelling invariance; post-decision/future-realisation/hidden-state poison rejection through the source extractor; matched catalogue authentication; infeasible independent-profile repair; runner cancellation during both coordinator work and preparation; and additive placebo S3=S_UNI.
- **T3 passed:** canonical raw receipts went through `EvaluationRunner`, the attempt chain, and the real `merge_receipts` path. It covered repeated worlds, unequal energies, paired identical arms, zero-bit and zero-energy/undefined cells, incomplete crossed panels, QoS rejection, injected alternatives, and a least-favourable conjunction null. Monte Carlo uses the same public `infer_cluster_totals` production core called by the merger.

## T3 empirical calibration

The fixed synthetic run used 64 repetitions and 149 two-way pigeonhole bootstrap draws per repetition, 160 dates, a +2% planning alternative, and a +0.5% claim margin. Values after `±` are approximate normal 95% Monte Carlo half-widths for the binomial simulation count; finite bootstrap-draw error is additional.

| Scenario | Quantity | Estimate |
|---|---|---:|
| 3% date SD / 1% seed SD, 12 seeds | interval coverage | 181/192 = 0.9427 ± 0.0329 |
| 5% date SD / 1% seed SD, 5 seeds | interval coverage | 168/192 = 0.8750 ± 0.0468 |
| 5% date SD / 1% seed SD, 12 seeds | interval coverage | 172/192 = 0.8958 ± 0.0432 |
| 10% date SD / 1% seed SD, 12 seeds | interval coverage | 165/192 = 0.8594 ± 0.0492 |
| 5% date SD / 1% seed SD, 5 seeds | component power | 129/192 = 0.6719 ± 0.0664 |
| 5% date SD / 1% seed SD, 5 seeds | conjunction power | 16/64 = 0.2500 ± 0.1061 |
| 5% date SD / 1% seed SD, 12 seeds | component power | 153/192 = 0.7969 ± 0.0569 |
| 5% date SD / 1% seed SD, 12 seeds | conjunction power | 27/64 = 0.4219 ± 0.1210 |
| Least-favourable null, 12 seeds | false conjunction | 1/64 = 0.0156 ± 0.0304 |

The sensitivity coverage row for 5%/1% using the separate 12-seed scenario loop was 184/192 = 0.9583 ± 0.0283. The intentionally small simulation is a software-calibration KAT, not a precise power study: its uncertainty is material, and the observed conjunction power is below the analytic approximation in contract §E.

## `physics_v025` interface assumptions

1. `NetworkOutcome` supplies finite additive `bits`, `joules`, and signed dimensionless `phi`; a beam change is −0.5 and a satellite change is −1.0, so the implemented objective is `B - eta_ref E + kappa_normalization_bits * phi`.
2. The stage-4 adapter supplies the reference, every unilateral counterfactual, and the coalition counterfactual at one matched nominal anchor. `coalition_identity` does not synthesize or query a world.
3. Q1 and Q2 rows receive one legal physical action `(norad_id, beam_chain_id)`, a complete legal mask, the previous committed background excluding the focal user, nominal current/forecast fields, and frozen authority digests. The Q2 candidate-current margin and broadcast incumbent-context margin are distinct.
4. A Q2 forecast contains exactly offsets 1–3, recomputes background power, uses the absorbing-loss convention, and exposes no realised future fading.
5. If calibration supplies κ as bits/user-second, the adapter converts it once by exactly 30.08 seconds. Stage C otherwise accepts only positive `kappa_normalization_bits`.
6. Catalogue profiles are complete, joint nominal evaluation is authoritative, and a resolved profile may not silently rewrite the selected physical identities.
7. Event accounting receives a stable roster and previous/last-served physical profiles, permitting the controller's post-outage re-entry pricing rule and zero-cost cell re-key rule.

These assumptions are executable seams, not evidence that a real `physics_v025` adapter or catalogue has been sealed.

## Work still required before real source generation

The spec lists every remaining `CONTROLLER_DECIDE`: formal V0.23 learner literal values; C3 feature scales; the >4-user capped decomposition and weights; real neutral-source seals; catalogue/CB-2 construction and pruning; the assembler's exact allocation manifest and BASELINE SHA; real operational capability values and cold-cache latency evidence; and any causal operational variant.

In addition, the controller must seal spec v1, the calibration freeze must be in force, the real stage-4 adapter must satisfy the interface KATs, and PHYSICS-GO must be issued. Until then, admission remains HOLD.

## Commit status

A scoped `git add`/commit was attempted, but this checkout exposes `.git` read-only: Git could not create `.git/index.lock`. The completed changes therefore remain in the worktree for the controller/host to commit. Unrelated pre-existing `.tmp/`, `.tmp-prompts-v025/`, and the untracked local controller-decision copy were not modified or selected for staging.
