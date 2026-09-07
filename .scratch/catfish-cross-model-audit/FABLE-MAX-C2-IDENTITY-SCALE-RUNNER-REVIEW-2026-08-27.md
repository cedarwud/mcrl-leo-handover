# Fable Max C2 identity/scale runner pre-formal review

- Date: 2026-08-27 (Asia/Taipei)
- Reviewer: `claude-fable-5`, `--effort max`
- Session: `eeaefe86-ffed-41b8-a498-0be7e9aa3498`
- Mode: read-only; no long experiment
- Reviewed runner SHA-256: `6fc93f1231bc6f6b37b24fa27e07027a15e98f3f066f9cbb50554229d5ddae66`
- Verdict: `REVISE_BEFORE_FORMAL`

## Sole blocking finding

The runner byte-pinned the C2 spec, ADR, source-drift manifest, v2 runner,
v2 spec, v2 receipt, preregistration, checkpoint, launched source, and current
analysis source.  It did not byte-pin two executable helpers that carry the v1
candidate/parity/checkpoint/environment path:

- `.scratch/catfish-oracle-gate/run_oracle_gate.py`
  (`b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb`)
- `scripts/run_head_pivotality_probe.py`
  (`563c5c5fa04068868d02cbce542dc3a15305fd840b766dc919f257ea49dddeb9`)

The reviewer also required the imported module paths to be bound explicitly to
the files whose bytes are checked.  Without these checks, an assertion-only
helper drift could remain absent from the formal receipt even when the dynamic
census stayed unchanged.

## Verified-compliant scope

The review found no blocking error in the following parts:

- payload-boundary time-only algebra, dimensions, and independent identity
  calculation;
- episode-start, unserved, re-entry, phi1, and phi2 event semantics;
- exact-stay construction, proposal-before-outcome ordering, common RNG, and
  preview/commit parity;
- frozen `758` eligible plus one service-unsafe row input-parity contract;
- seed-level aggregation and ten-seed t interval;
- no-overwrite, temporary staging, hash verification, atomic publication, and
  cleanup on failure;
- the claim ceiling: a formal pass authorizes only later R2 mapping,
  state-sufficiency, and isolated-role gates, not reward implementation,
  training, transfer, or effectiveness claims.

## Nonblocking cautions retained

- Report the 757-row service-safe subset descriptively in addition to the
  frozen all-758 aggregation; do not change the preregistered decision rule.
- A zero-energy/zero-EE edge can currently fail closed before publishing a
  diagnostic receipt.
- Formal result intake must verify the post-fix runner SHA-256.
- Formal seed order is intentionally order-sensitive; a different order
  downgrades the run to a non-adjudicated pilot.

## Post-review delta requiring re-review

After the reviewer read the pinned version, two fail-closed changes were made:

1. preview-state hashing was expanded to include environment start state,
   ledger start state, and pending segment ages;
2. both missing helpers, their loaded module paths, and their imported symbol
   bindings were added to the authority checks and formal receipt.

The resulting runner SHA-256 is
`815a39e74a2e83fae1484fe9f68279120e9ee2d3ea0750f45cde51443a656a34`.
This receipt does not promote the original verdict; the delta must pass a
separate pre-formal review.
