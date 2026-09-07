# Sol Ultra C3 delta pre-formal review

- Date: 2026-08-27 (Asia/Taipei)
- Reviewer: `gpt-5.6-sol`, reasoning effort `ultra`
- Mode: read-only narrow delta review
- Final runner SHA-256:
  `6b0c8177b0ec436925d5e9c1eb8533a3906cfe8980033e43be23923dfb578a55`
- Final launcher SHA-256:
  `7136a72587be5ae55a312776d6780484fe6c11e6bb639acf448cb3ee7799826c`
- Verdict: `PASS_TO_FORMAL_SHADOW`

## Closed blockers

- Helper provenance is fail-closed through resolved import-path checks,
  `base.v1` module identity, and identity checks for all six imported
  checkpoint-loader bindings.  The checks run before preregistration,
  checkpoint, or seed consumption and propagate to both result and receipt.
- Each paired branch reconstructs an independent `SatelliteSet`, `SatrecArray`,
  and complete `Satrec` graph from equal frozen TLE records.  Three-way object
  separation, record equality, and NORAD ordering are checked alongside the
  environment, mobility, age-RNG, candidate, and outer-state predicates.
- All stale provenance text was corrected to describe independent propagator
  reconstruction.

## Dynamic engineering evidence

- Three-step development smoke, seed `2026082701`: 300 user-steps, one paired
  row, multi-step Q1 continuation required, all 25 clone predicates true,
  zero engineering failures, exit 0.
- One-step current authority/publication pilot: all nine helper checks and all
  artifact/source checks true; JSON and NPZ hashes committed by a receipt
  published last.  It is `PILOT_NOT_ADJUDICATED` and is not scientific data.
- The final runner differs from the current-runner authority pilot only in an
  internal docstring correction; the reviewer reconstructed and accepted that
  hash delta.

## Blocking findings

None.

## Retained cautions and authorization ceiling

- Accept a formal bundle only when the receipt exists and its JSON/NPZ hashes
  match; receipt-last is the commit protocol, not a filesystem transaction.
- Engineering smoke/pilot evidence is not a formal scientific result.
- The pass authorizes only the frozen five-seed, ten-step, non-training shadow.
  It does not authorize reward/runtime changes, training, Main transfer, or
  effectiveness/novelty claims.
