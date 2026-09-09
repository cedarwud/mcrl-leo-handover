# V0.25 Stage C build 3 report — 2026-09-08

Status: `BUILD3=READY_FOR_REAUDIT`; synthetic acceptance only. Admission remains `HOLD`. No real worlds were opened, no TEST data were used, and no sealed artifact was edited.

## Verification

Final tests use Python 3.13.3 and pytest 9.1.1 from `/home/sat/mcrl-leo-handover/.venv`, with `PYTHONPATH=src`.

- Fast integrated gate: `116 passed, 1 deselected` for `tests/physics_v025 tests/stagec_v025 -k 'not T3'`.
- Raw-merger calibration gate: `. [100%]` (`1 passed`; shell `real 17m44.028s`) for `tests/stagec_v025/test_contract_v1_acceptance.py -k T3`.
- Combined targeted result: 117/117 passed (116 fast integrated tests plus the one full-scale T3 calibration test).
- `python -m compileall -q src/mcrl/stagec_v025 tests/stagec_v025`: PASS.
- `git diff --check`: PASS.

## Build-2 audit closure

| Audit area | Build-3 binding |
|---|---|
| S3, T1 and T2 production path | The acceptance fixture now connects source extraction, authenticated source and coalition shards, the heterogeneous Adam learner, checkpoint identity, the set-conditioned `ProfileSelector`, three evaluation steps, canonical receipts, and terminal merge. T2 training uses bracketing twins and evaluates an unseen midpoint; no acceptance test calls `fit_closed_form`. S3 rejects missing checkpoint identity or catalogue/context laundering. Checkpoint knockouts authenticate the deployed checkpoint and permitted route. Repair and deadline tests use `ProfileSelector`, not `DeploymentAdapter`. |
| T3 real merger | Every Monte Carlo world is emitted by `EvaluationRunner.build_calibration_receipt` through the production step serializer. `merge_receipts` authenticates the receipt, validates each raw row, independently calls `reaggregate_steps`, and invokes the production two-way inference and claim rules. |
| Experiment schemas | All four definitions produce distinct `BoundExperiment` records. Allocation, attempt, conformance, step and unit-receipt records carry the exact schema/definition/execution/checkpoint binding. Mislabelling and allocation of `NAMED_NOT_RUN` are negative KATs. |
| Legacy learner and checkpoints | Q1 `(8,)` ReLU/Adam, Q2 `(100,50,50)` tanh/Adam, and C3 `(64,64)` ReLU/Adam are implemented with the copied learning rates, beta/gauge and effective objective weights (C2/C3 are unweighted in the heterogeneous seam). The 2,000-epoch/no-early-selection rule is bounded in the trainer. Full heads and Adam moments/cursors serialize; 100-epoch checkpoints are write-once, authenticated, loadable, and rebound to their file SHA-256. The unsealed draft spec records absolute legacy file:line provenance. |
| F2 cancellation | `ProfileSelector.select_timed` runs selection in a forked process. Deadline expiry calls `kill()` and `join()`, records the killed PID, and returns the parent-validated BASE. The slow-coordinator KAT proves it returns before the injected worker finishes. |
| A1–A4 and feature provenance | Action evaluations seal source, forecast-method, visible-primitive and TLE provenance. Extraction recomputes the dependency-allowlist digest and rejects future-TLE access. `HeadsInformation` is constructed from source rows. Coordinator and arm interfaces carry source/catalogue provenance; both selector and runner require the A4 matched-information authenticator. |
| B5 larger evacuations | Every lexicographic size-four subset is emitted with the complete original user inventory, common decomposition digest and uniform `1 / choose(n,4)` weight. The five-user KAT authenticates all five rows and unit total weight. |
| C4 and C6 | The merger reports paired FULL>S_UNI EE inference, the three QoS comparisons, paired FULL>S0 learned value, per-arm latency/compute distributions and decision nonadditivity. Its report schema encodes that exact zero C3 marginal terminates the positive claim and never permits outcome-contingent redesign. |
| D1, D5, E, F1 and F3 | Allocation validates the external baseline SHA-256, exact experiment binding, global successor-development disjointness, matched-information digest, and training/evaluation physics equality. Rows and receipts carry retrospective/causal TLE provenance. Step and capability latency samples are mandatory, finite and nonempty. T3 calibration now enters the raw production merger. |

## T3 calibration

Design: 200 Monte Carlo replications per cell, 160 dates, two unequal-energy worlds per date×learner-seed cell, planning alternative +2%, claim margin +0.5%, 49 two-way bootstrap draws per replication. Values are estimate ± approximate binomial 95% Monte Carlo half-width.

| Date SD | Seed SD | Learner seeds | Interval coverage | Three-contrast conjunction power |
|---:|---:|---:|---:|---:|
| 5% | 1% | 5 | 0.8633 ± 0.0275 | 0.3800 ± 0.0673 |
| 5% | 1% | 12 | 0.8783 ± 0.0262 | 0.4950 ± 0.0693 |
| 5% | 1% | 16 | 0.8933 ± 0.0247 | 0.6750 ± 0.0649 |
| 5% | 1% | 24 | 0.9083 ± 0.0231 | 0.6750 ± 0.0649 |
| 3% | 1% | 5 | 0.8267 ± 0.0303 | 0.5950 ± 0.0680 |
| 3% | 1% | 12 | 0.8933 ± 0.0247 | 0.9200 ± 0.0376 |
| 3% | 1% | 16 | 0.9200 ± 0.0217 | 0.9800 ± 0.0194 |
| 3% | 1% | 24 | 0.9233 ± 0.0213 | 1.0000 ± 0.0049 |

The run authenticated and reaggregated 7,296,000 raw receipts containing 29,184,000 raw step rows. The values above are calibration measurements, not Stage-C scientific results, and no target power value is treated as a pass criterion.

## Remaining `CONTROLLER_DECIDE`

Only real-run seal values remain:

1. `CONTROLLER_DECIDE COALITION-FEATURE-SCALES`
2. `CONTROLLER_DECIDE NEUTRAL-SOURCE-SEALS`
3. `CONTROLLER_DECIDE CATALOGUE-CB2`
4. `CONTROLLER_DECIDE FORMAL-ALLOCATION-MANIFEST`
5. `CONTROLLER_DECIDE OPERATIONAL-CAPABILITY-VALUES`
6. `CONTROLLER_DECIDE CAUSAL-OPERATIONAL-VARIANT`

These require controller authority or real operational measurements and were not fabricated under the synthetic-only/no-sealed-edits constraint. `FORMAL-LEARNER-LITERALS` and `LARGER-EVACUATION-CAP` are no longer controller decisions in build 3.

## Final review

### Standards

No repository-specific coding-standard document applies beyond `pyproject.toml`. The final working-tree diff passes compilation and whitespace checks. The smell review found no unresolved correctness-risk smell; repeated authority fields are deliberate authenticated domain records, and the legacy linear/deployment classes remain compatibility surfaces outside the production acceptance path.

### Spec

Review against the build-2 audit, contract v1, and controller decision record found no unresolved synthetic implementation requirement. The review did find two issues before final verification—T2 originally reused its fitted feature points, and the legacy `(1,2,3)` loss-weight declaration was initially treated as active for C2/C3. Both were corrected: T2 is now held out, and the effective objectives match the heterogeneous trainer. The six items above remain external seal/authority decisions rather than simulated completions.
