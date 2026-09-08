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

The package imports F1 profile conversion, candidate enumeration, and physical
profile capture;
F0 conservation; F2 lineage authentication and world-by-lineage conventions;
and the native `StepEnvironment.evaluate_actions` physics path. No predecessor
is copied or edited. E1 provides thin local validation-only and BASE-only
wrappers because F1 has no entry points that avoid legacy D/F target evaluation
and `Q + z/kappa` composition. The wrappers use donor physical identities and
profiles while applying only E1's declared BASE rule.

## Files and use

- `e1_estimands.py`: exact `solve_u1`, `solve_j1`, and certificate verifier.
- `run_v023_c3_existence_e1.py`: joint catalog builder, E1 tape verifier,
  `--unit`, `--merge`, `--dry-run`, immutable receipts, `INCOMPLETE`, and
  global `INVALID_RUN` invalidation.
- `build_e1_preflight_manifest.py`: writes the code/binding manifest once.

Certificates store every retained DP value and backpointer plus a final
backtrace. Counts at or above the required-service threshold are represented
by the threshold state. This is an exact compression because all such states
have identical future feasibility, so only their best score under the declared
tie rule can affect later steps.

The controller-placed draft
`V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md` must be sealed with a
read-only `.md.sha256` sidecar, then its absolute path and SHA-256 must be
bound in a launch authority. This package deliberately did not create or edit
that reserved file.

Build and check the preflight after code review:

```bash
/home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v023-c3-existence-e1/build_e1_preflight_manifest.py
/home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py --dry-run
```

Run one authorized unit later (a physical simulator run, not part of this
implementation handoff):

```bash
/home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py \
  --unit 861587764845384088:2026092101 \
  --launch-authority /absolute/path/to/authority.json \
  --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
  --output /absolute/path/to/e1-output
```

The frozen launch authority has an exact key set. It binds the absolute
checkout/output/TLE roots, PREREG file and semantic digest, the rebuilt TLE
manifest digest, and the exact command arguments. The runner accepts only the
bound output root and canonical TLE root.

After all twelve units exist, `--merge` authenticates them and writes the
terminal U1/J1 decision. A premature merge exits with
`E1_MERGE_WAITING <n> units missing` and writes no terminal. Tapes, manifests,
and receipts are mode `0444`, write-once, and reopened/hash-verified. SIGINT,
SIGTERM, the default 57,600 worker-second cross-unit budget, and exact-solver
iteration exhaustion publish a separate immutable `INCOMPLETE` receipt; these
receipts do not occupy a unit or terminal path and therefore do not prevent a
later resume. Integrity/authentication failure publishes global `INVALID_RUN`;
an invalidation beside an already published COMPLETE supersedes that result.

Implementation tests are unit fixtures only:

```bash
/home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q .scratch/multi-catfish-v023-c3-existence-e1
```

## E1 fix pass 1 changelog

1. Certificate: serialized exact DP values/backpointers and final backtrace;
   added strict proof-field validation, stored-coefficient rehashing, and an
   independent rational witness/recurrence checker.
2. Tape: added lossless little-endian float32 Q1+Q2 bytes, strict dtype/shape
   decoding, direct masked first-index BASE authentication, and BASE F0 record.
3. Profile boundary: enforced 100 users and the canonical interval on BASE,
   unilateral, and joint profiles; routed E1 through local validation/BASE-only
   wrappers with no legacy D/F or residual-composition call.
4. Preflight/authority: contract seal is now the first write gate; E1 tests,
   every F2 binding including the multi-lineage loader, RNG/keyed-field code,
   PREREG, rebuilt TLE manifest, roots, interpreter/environment, and exact
   arguments are frozen.
5. Publication/lifecycle: added immutable readback, a worker-budget ledger,
   resumable INCOMPLETE receipts, merge WAITING, solver-resource classification,
   and global invalidation for corrupted existing evidence.
6. Tests: added exact variable-energy oracles, certificate mutations, Q/BASE
   refusals, canonical profile checks, complete synthetic authentication flow,
   lifecycle/corruption checks, and all declared catalog edge cases.
