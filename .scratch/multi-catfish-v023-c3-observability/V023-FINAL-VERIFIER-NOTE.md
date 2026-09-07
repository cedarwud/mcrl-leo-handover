# V0.23 independent final verifier note

## Scope

`verify_v023_lcsrs_final.py` is a read-only, standard-library/NumPy verifier
for the frozen V0.23 LC-SRS source, fit, and composition panel.  It does not
import a production adapter, simulator, learner, PyTorch, or TEST data.  It
reopens each source and composition NPZ rather than trusting a merge summary or
persisted PASS/predicate booleans.

The entry point requires exactly 8 source shards, 48 fit shards, and 48
composition shards.  It authenticates the sealed source-manifest child hashes,
world/seed/arm identities, sidecar byte hashes and array metadata; joins source
and composition records by exact world/seed/anchor/pair/draw identities; and
recomputes the physical, learner, composition, service, denominator, and
Section-14 precedence predicates.

## Verified implementation facts

* Source arithmetic is delegated only to the existing independent scientific
  and fit verifiers, loaded by file path and never through a production package.
  The final verifier then performs its own composition reopen and cross-arm
  checks.
* Every composition shard's Q1/Q2/Q1+Q2 surface, native mask/action vectors,
  three physical roles, 32 draw IDs, bits/energy/service counts, nonmutation
  flags, common-field digests, ratio cross-products/tolerances, pair classes,
  partial-ratio signs, collateral vectors, selected-11 topology, and all
  denominators are recomputed from raw arrays.
* Source/composition joins include the sealed preflight/source/field roots,
  Q1/Q2/Q1+Q2, all anchor digests, pair IDs/source/destination identities,
  target rows, all four profile action/physical arrays, and common-field rows.
  INFORMED and MATCHED_PLACEBO are independently checked to share the exact B,
  teacher, and physical surfaces; only their fitted Q3 surface may differ.
* Composition EE is a complete ratio-of-sums.  Seed-level values are computed
  first and then averaged as required by Section 12.  Service is compared with
  INFORMED versus matched B, not versus placebo.  Zero selected-11 and
  nonpositive EE denominators fail closed.
* Section 14 is implemented in the frozen precedence order:
  `INVALID_RUN` -> `INSUFFICIENT_PAIRS` -> `STOP_PHYSICS` ->
  `STOP_OBSERVABILITY` -> `REDESIGN_INTERFACE` ->
  `GO_FIXED_LEARNER_SCREEN_CONTRACT`.

## Current schema/API boundary

The source adapter serializes the fields required for an independent C2
diagnostic: target-free OPS-3 state/features, persistence/rate/power arrays,
per-anchor horizon and timing lists, Q1/Q2 reference digests, repriced target
digests, and per-pair target-free diagnostics.  The final verifier recomputes
the feature-major state digest, persistence/terminal-zero and beyond-horizon
conditions, repriced target values, opening/mask consistency, Q2 exposure, and
diagnostic multiplier/target-free flags.  The repriced terms have shape
`(U,H,A)` and are averaged over `H`; the frozen interval is the native
`47 * 0.64 s` binary value.  Timing receipts are checked against the
phase-dependent `H=min(3,9-phase)` schedule, `H*47` native indices, 640 ms
sample spacing, and every-47th-sample endpoints.  Horizon-zero anchors must
carry three empty lists.  The q2-state digest is read only from
`anchor.q2_context`, and `c2_diagnostic` is the single diagnostic object whose
`rows` member is validated.

Q1+Q2 references are independently recomputed from the exact float32 carrier
`float32(q1 + q2)` with native masked lowest-index ties.  C2 deltas and their
target sign/rank diagnostics are then centered on that recomputed reference;
the persisted `reference_actions` and row values are checked as witnesses, not
used as an unverified selector.

If a future artifact omits any of those fields, or changes their schema without
raising the frozen artifact version, the final verifier returns `INVALID_RUN`
before any scientific token.  It records the missing field in `errors`; it does
not infer a timing result from Q2 values or relax a predicate.  A valid but
weak C1/C2 diagnostic is still serialized as `HOLD_C1`, `HOLD_C2`, or
`HOLD_C1_C2` independently of the Section-14 C3 decision.

This is a verifier implementation note, not a scientific efficacy result.  A
`GO_FIXED_LEARNER_SCREEN_CONTRACT` token would authorize only the next frozen
learner-screen contract; it would not authorize episode training or support a
C1/C2/C3/EE efficacy claim.

## Focused synthetic coverage

`tests/test_w201_ee_axis_lcsrs_final_verifier.py` covers a positive all-predicate
token, each Section-14 failure precedence, positive composition recomputation,
zero selected-11 and zero-energy denominators, cross-arm identity mismatch,
tampered receipt seals, and independence of Section-9 HOLD from Section-14.  It
also covers the native-horizon averaging axis, phase-1..9 D2 index/timing
schedule (including phase-9 empty lists), exact float32 Q1+Q2 selection,
context-only state-digest placement, single-object C2 diagnostics, and C2
target sign/rank recomputation.
