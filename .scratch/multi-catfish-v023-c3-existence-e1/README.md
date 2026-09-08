# C3 existence screen E1 computational core

This package implements the engineering lane for E1. It does not create or
freeze the E1 contract, train a learner, open TEST, or claim efficacy.

## Plainest readings

- `U1` is the exact best pooled bits / pooled joules obtainable by choosing
  BASE or one legal unilateral physical profile at each anchor, while pooled
  service stays at least `s_BASE - 0.001`. It is a ceiling only for that
  restricted at-most-one-changed-user class.
- `J1` uses BASE or one complete joint witness profile at each anchor. Each
  witness moves every BASE-served user on one origin beam to one physical
  destination legal for all of them. It is evaluated as a complete joint
  action. It is a lower bound on unrestricted joint potential; closure says
  only that this fixed catalog had no headroom.
- The optimizer does not average per-anchor ratios. `e1_estimands.py` applies
  exact rational Dinkelbach iterations. Every inner problem is solved by an
  exact dynamic program over pooled integer served counts. The terminal proof
  has `max(B - qE) = 0` over all service-feasible choices, while its chosen
  profile has equality. Positive energy then proves that no feasible profile
  selection exceeds `q`.
- BASE is committed between the ten canonical anchors. Counterfactual
  profiles do not advance the environment.
- The four physical worlds are fresh derived seeds, but the three Q1/Q2
  checkpoint lineages are reused authenticated lineages. This is matched
  TRAIN-development physical evidence, not fresh training.
- A HEADROOM result establishes neither accessible information, learnability,
  simultaneous learned composition, trajectory improvement, generalization,
  nor paper efficacy.

World derivation is SHA-256 of ASCII domains
`C3_EXISTENCE_E1/world/1..4`, first eight digest bytes as big-endian, masked
to positive int63:

1. `861587764845384088`
2. `3943897440191533562`
3. `5747196377242098234`
4. `4004348767321774260`

The package imports F1 profile conversion, candidate enumeration,
mask/tie/NOOP validation, physical profile capture, and write-once machinery;
F0 conservation; F2 lineage authentication and world-by-lineage conventions;
and the native `StepEnvironment.evaluate_actions` physics path. No predecessor
is copied or edited.

## Files and use

- `e1_estimands.py`: exact `solve_u1`, `solve_j1`, and certificate verifier.
- `run_v023_c3_existence_e1.py`: joint catalog builder, E1 tape verifier,
  `--unit`, `--merge`, `--dry-run`, immutable receipts, and `INVALID_RUN`.
- `build_e1_preflight_manifest.py`: writes the code/binding manifest once.

The controller-placed draft
`V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md` must be sealed with a
read-only `.md.sha256` sidecar, then its absolute path and SHA-256 must be
bound in a launch authority. This package deliberately did not create or edit
that reserved file.

Build and check the preflight after code review:

```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-existence-e1/build_e1_preflight_manifest.py
./.venv/bin/python .scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py --dry-run
```

Run one authorized unit later (a physical simulator run, not part of this
implementation handoff):

```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py \
  --unit 861587764845384088:2026092101 \
  --launch-authority /absolute/path/to/authority.json \
  --tle-root /absolute/path/to/tle-root \
  --output /absolute/path/to/e1-output
```

After all twelve units exist, `--merge` authenticates them and writes the
terminal U1/J1 decision. All tapes, manifests, and receipts are write-once and
read-only. Any unit or merge integrity failure seals an `INVALID_RUN` receipt.

Implementation tests are unit fixtures only:

```bash
./.venv/bin/python -m pytest -q .scratch/multi-catfish-v023-c3-existence-e1
```
