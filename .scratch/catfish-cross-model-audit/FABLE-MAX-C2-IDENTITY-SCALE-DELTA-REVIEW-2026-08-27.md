# Fable Max C2 identity/scale delta review

- Date: 2026-08-27 (Asia/Taipei)
- Reviewer: `claude-fable-5`, `--effort max`
- Session: `a13297b4-8a07-4a0e-9f44-90d4f7cf3060`
- Mode: read-only; no long experiment
- Reviewed runner SHA-256:
  `815a39e74a2e83fae1484fe9f68279120e9ee2d3ea0750f45cde51443a656a34`
- Verdict: `PASS_TO_FORMAL_IDENTITY_SCALE`

## Closed blocker

The reviewer independently confirmed that the prior executable-helper closure
gap is closed:

- `run_oracle_gate.py` and `run_head_pivotality_probe.py` are byte-pinned and
  fail closed in `_verify_static_authority`;
- actual v2, v1/oracle, and checkpoint-loader import paths must equal the
  pinned paths;
- the four checkpoint helper functions used through `v2.v1` are identity-bound
  to the pinned checkpoint-loader module;
- every check is retained in `frozen_inputs.authority_checks`, and both helper
  paths and hashes are repeated in the result receipt.

The reviewer also verified that the expanded preview-state receipt fields
(`environment._started`, each ledger's `_started`, and pending segment ages)
exist, are stable on the non-committing preview path, and introduce no new bug.

## Blocking findings

None.

## Retained nonblocking cautions

- Verify the formal result's embedded runner SHA against the reviewed SHA.
- Report the 757 service-safe rows descriptively without changing the frozen
  all-758 decision contract.
- A zero-energy edge fails closed before publishing a diagnostic result.
- A different seed order intentionally becomes a non-adjudicated pilot.
- Two receipt subhashes use byte-only or repr encodings; full preview/commit
  parity remains the primary dynamic guard for those fields.

## Authorization ceiling

This pass authorizes only the frozen ten-seed, ten-step, non-training C2
identity/scale run.  It does not authorize reward implementation, replay
transfer, a learning run, an effectiveness claim, or acceptance of the
62/142-ms timing sensitivities as project parameters.
