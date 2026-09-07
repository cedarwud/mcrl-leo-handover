# V0.18 R4 scale-aware full-cache equivalence check

Status: `FROZEN_BEFORE_CHECK`

Date: 2026-09-04 (Asia/Taipei)

## Why R4 exists

R3 remains a valid `STOP_R2_CACHE_EQUIVALENCE` receipt.  It stopped at the
complete `delta` tensor after all-branch non-focal rate and interference
primitive checks had passed.  R3 used a fixed `1e-9`-bit absolute tolerance
on a difference of rates whose `(noise + interference)` denominator is
necessarily reassociated by the cache.  A pre-execution numerical analysis by
Opus Max showed that this tolerance lies below the attainable floating-point
floor even for an algebraically correct cache.

This contract creates one bounded, non-aborting R4 equivalence check.  It does
not reinterpret R3 as a pass, change either implementation, alter C3, select a
training candidate, or authorize a learner or episode run.

The read-only external adjudication is:

- `.scratch/multi-catfish-v018-relational-zr/reviews/OPUS-MAX-R3-CACHE-NUMERICAL-ADJUDICATION-2026-09-04.md`;
- SHA-256:
  `1346f1b9e6ae76f1e0c9a515d88b20374168e55d736e2fff3609ddfe1088ec2d`;
- verdict: `GO_R4_SCALE_AWARE_EQUIVALENCE`.

The preserved R3 evidence is:

- contract SHA-256:
  `2cd580080435a7809d8b9a565cd5906ad06e02d21f6cf8d16300a6f4b55d7c29`;
- result SHA-256:
  `dfb13a54a57023529e1e75d27e3b7816143a11313392bc6497c3f5207420a651`;
- receipt SHA-256:
  `8ae7c53ecc5f023b68a855f2118bfdcff4229b4d009638b31153781a84f6d909`.

## Frozen scientific and data surface

R4 retains the R3 surface without substitution:

- previously opened TRAIN world `2026104901`; TEST unopened;
- frozen Q1/Q2 lineage `2026092101`;
- `100` users and the initial predecision anchor only;
- contexts `h=12`, `h=1`, and `h=2`;
- every native legal focal-user/action branch; no sampling or mask reduction;
- at most `18` fork workers; parallelism changes wall time only;
- no environment action, realised outcome, exact teacher, learner update, or
  episode training;
- the preregistered frozen TLE file set and keyed fading field remain fixed.

The sealed implementation identities remain:

- R1 branch reference:
  `6a3d61940175f0e4e422fa4ac9818fd64652dd4f6e699408f6189cec164425a2`;
- R2 cached runtime:
  `e66f61d7ad8833115eb0542ca2b4ea6718a23ecc26aa0729f5cf879c64cf6166`;
- base preregistration:
  `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`.

R4 changes only the comparison instrument and its reporting.  The frozen
instrument identities are:

- R4 equivalence runner:
  `dfe68dc863ae73afaa6c39141249b72df410057e543cef1eda6c32bc68ad2fe4`;
- R4 server sync wrapper:
  `145759b05d08256ecacbc3f3e16d32f80cf4cd9c9b8cad188b7bb9202e2dede7`;
- R4 server run wrapper:
  `8f7b9e377e4166276be5a3dfd9e127a537207a46a91b9fbc2850ce88b134c982`;
- W178 comparison-instrument tests:
  `699750e47e1df9985366528216702b21b480433e543d9e7954e501eed59f7c1a`.

The complete code-manifest digest is supplied separately to the sync and run
wrappers, because a manifest that contains this contract cannot recursively
contain its own digest.  The runner must authenticate every manifest entry and
the server preflight receipt/log before opening the frozen TRAIN world, then
bind their digests into both `result.json` and `receipt.json`.

## Fixed numerical model

Let `eps = np.finfo(np.float64).eps`, `C = 64`, `T` be the frozen decision
interval, `B` the frozen beam bandwidth, `N` the frozen noise power, `L` the
candidate beam load, and `r0`, `ra`, `I0`, and `Ia` be the reference/candidate
rate and interference values reconstructed by the sealed R1 path.

For each legal `(u,a,v)` non-focal entry, define the pre-outcome delta bound

```text
b_delta = C * eps * T * (
    (B / max(L,1)) / ln(2)
    * (1 + (abs(I0) + abs(Ia)) / (N + abs(Ia)))
    + max(abs(r0), abs(ra), 1)
)
```

The bound accounts for reassociation of the interference sum, its Shannon-rate
lever arm, reference subtraction, and interval multiplication.  It is not
fitted to the observed R3 maximum.  A delta entry passes only when its absolute
R1/R2 deviation is no greater than `b_delta` and no greater than the separate
hard ceiling `1e-3` bits.  Focal, illegal, and structurally zero-coupling
entries retain exact requirements described below.

For the sixth victim token

```text
asinh((Ia - I0) / N)
```

the fixed per-entry bound is

```text
b_token = C * eps * (
    (abs(I0) + abs(Ia)) / N
    + max(abs(token_R1), abs(token_R2), 1)
)
```

using the global Lipschitz bound `|asinh'(x)| <= 1`.  This bound applies only
to victim-token column 5.  It does not loosen any discrete or context feature.

For transparency, R4 must report normalized maxima under diagnostic constants
`C in {1, 8, 64, 512, 4096}`.  Only the predeclared `C=64` condition is the
mechanical gate; the complete sensitivity table is evidence against hidden
post-outcome tuning and must be persisted even on STOP.

## Fixed acceptance conditions

R4 returns `PASS_R2_CACHE_EQUIVALENCE` only if all three contexts satisfy all
of the following:

1. Every non-focal primitive rate satisfies `rtol=1e-12`, `atol=1e-9` and
   every non-focal primitive interference satisfies `rtol=1e-12`,
   `atol=1e-18`; these R3 gates are unchanged.
2. Every legal non-focal `delta` entry satisfies the `C=64` propagated bound
   and the independent `1e-3`-bit hard ceiling.
3. Complete centred `q3` retains the unchanged `rtol=1e-12`, `atol=1e-9`
   gate.  It is not rescaled or compared only after aggregation.
4. `action_context`, victim-token columns 0--4, `action_mask`, `victim_mask`,
   `positive_credit_compatible`, and `reference_actions` are byte/value exact.
   Victim-token column 5 alone uses `b_token`.
5. For every branch, integer beam-load maps and max-selected beam-power maps
   reconstructed from R2 cache inputs equal the R1 branch maps exactly.
6. Focal entries are excluded exactly: both delta diagonals and cached focal
   rates are zero, and all focal victim masks are false.
7. Candidate interference is exact wherever the victim has zero coupling to
   both changed beam keys.  Candidate rate and `delta` are additionally exact
   only when that victim's beam load is unchanged; zero interference coupling
   alone must not erase a real same-beam load effect.  Coupling coverage and
   colour/same-cell exclusions are verified.
8. Any cache clamp is counted.  Its pre-clamp negative residual must be within
   the already-existing `64*eps*reference_scale` invariant and the matching R1
   physical interference must be zero.
9. Duplicate focal/action pairs that resolve to the same full branch vector
   produce identical stored rate and interference arrays; silent inconsistent
   overwrite is forbidden.
10. R1 and R2 masked argmax actions are exactly identical for every user.
    Maximum score deviation, minimum legal top-two margin, and their ratio are
    recorded; a zero score deviation yields JSON `null`, not a non-finite
    number.
11. The interleaved-anchor no-stale-state test and the complete focused
    cross-module suite, including the R4-bound tests, pass under the sealed
    bytes.
12. Source, code, contract, data, checkpoint, output, and no-action/no-TEST
    identities are authenticated in a write-once receipt.

## Non-aborting evidence requirement

The comparison instrument must finish all legal branches in all three contexts
even when a numerical or invariant condition fails.  It must persist, for each
surface and context, the count of violations, maximum absolute deviation,
maximum normalized deviation, worst indices, rate/interference scales, action
identity, and all invariant counters.  An unexpected execution exception may
still fail closed, but must write its own STOP receipt.

Any failed condition returns `STOP_R2_CACHE_EQUIVALENCE`.  R4 cannot be repaired
after outcome by changing `C`, the hard ceiling, tolerances, world, lineage,
context, horizon, mask, action subset, formula, or sealed implementation.

## Claim ceiling

A pass establishes implementation equivalence only for the complete frozen R4
surface.  It authorizes preparation of the separate R2 performance addendum
and a fresh analytic-R2 code manifest.  It is not C3 efficacy, a learned-C3
result, an episode result, or authorization for short/long training.
