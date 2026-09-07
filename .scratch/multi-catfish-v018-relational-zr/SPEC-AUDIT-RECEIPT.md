# V0.18 relational-ZR spec audit receipt

Status: READ-ONLY REVIEW RECEIPT, NOT AUTHORITY.

Date: 2026-09-04 (Asia/Taipei)

An independent code-grounded explorer reviewed `spec.md` twice against the
V0.15/V0.17 contracts and current simulator source.

Initial verdict: `SPEC_NEEDS_PATCH`.

The first pass required:

- an exact branch-level compatibility predicate rather than an unsupported
  claim that seven compressed features were sufficient;
- an explicit same-satellite/different-cell and different-satellite co-channel
  victim predicate;
- focal, padded, and invalid victim exclusion before pooling/normalisation;
- a strict separation between observed SINR proxy values and deterministic
  unit-fading/zero-shadow nominal coefficients.

The second pass required explicit all-empty-reference handling, a `c[v] != -1`
guard, an opening-conditioned changed-key set, and an unambiguous ordered
float64 beam-power byte comparison.

After those local patches, the final verdict was `SPEC_COHERENT` with no
remaining blocker. The review found the compatibility branches mechanically
consistent with current service, beam-power, active-satellite, and network-
power construction. It made no efficacy claim and ran no simulation, learner,
or TEST data.
