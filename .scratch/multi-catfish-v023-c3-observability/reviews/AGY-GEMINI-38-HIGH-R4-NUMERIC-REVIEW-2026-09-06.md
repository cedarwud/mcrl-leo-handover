# Agy Gemini 3.8 Flash High R4 numeric review

Date: 2026-09-06  
Conversation id: `31a0d4c5-44d8-4302-98d0-402662b69eb1`  
Scope: read-only review of the coalition-identity roundoff scale  
Final token: **`PASS_SCOPED_NUMERIC_FIX`**

## Verified review findings

- The identity is assembled from delta-domain rate terms and energy deltas
  priced in bits; the large common reference totals cancel before the checked
  identity is formed.
- `_identity_roundoff_scale` includes the unilateral and joint rate deltas,
  priced energy deltas, and the derived terms participating in the final two
  sides, while intentionally excluding the common reference totals.
- The bound remains `max(1e-12, 1024 * eps * work_scale)`, approximately
  `2.27e-13` of the active arithmetic work scale.
- `verify()` independently recomputes vector components and the sparse Q3
  surface before applying the final identity tolerance.  The reviewer found
  no omitted arithmetic term and did not find a route by which this tolerance
  could conceal a material formula or source mismatch.
- The deterministic cancellation regression and material-corruption
  regression exercise the intended pass/fail boundary.

## Claim boundary

This is an independent numerical-integrity review.  It does not establish a
C3 scientific result and does not replace the isolated real-world replay or
the full Gate.
