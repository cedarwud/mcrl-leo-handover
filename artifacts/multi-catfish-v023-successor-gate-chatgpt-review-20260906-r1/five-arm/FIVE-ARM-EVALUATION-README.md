# V0.23 five-arm physical-evaluation binding

This directory contains pre-execution plumbing only. It binds five separately
frozen policy artifacts to the existing V0.23 source-ablation plan and a common
TRAIN-development physical world grid.

The fixed arms are `FULL`, the authenticated pre-Catfish `BASELINE`, and
`DROP_C1`, `DROP_C2`, `DROP_C3`. The DROP arms are source ablations: all three
policy routes remain present, but the named route was trained with its declared
equal-budget neutral source. A post-hoc head drop is rejected.

The binding additionally rejects TEST, episode training, outcome-selected
checkpoints, aliased arm checkpoints, non-fixed policies, and evaluation budgets
that do not end on a 100-episode checkpoint boundary.

It does not run the simulator or learner, choose scientific thresholds, or
authorize an evaluation. The later runner must supply Gate-admitted policy
artifacts and a separately frozen evaluation contract.

`v023_five_arm_eval_results.py` is the matching pure receipt layer. It checks
complete matched five-arm coverage, common world/fading/initial-state identity,
policy and source provenance, fixed-policy boundaries, and exact per-episode
bits/energy identities. It computes only descriptive pooled ratio-of-sums EE
and service contrasts; scientific adjudication remains explicitly `None`.
