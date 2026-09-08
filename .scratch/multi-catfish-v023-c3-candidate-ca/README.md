# V0.23 C3 candidate C-A

This directory is the complete implementation package for the C-A TRAIN-development oracle kill screen. It does not train a learner, open TEST, or make an efficacy claim.

## Plainest reading

- The deployed proposal catalogue groups users by their detached BASE action physical key. The runner separately rebuilds E1's realised-served-occupancy catalogue with E1's imported joint builder. Any difference is recorded and blocks support.
- Every subset of every deployed proposal is a complete action vector. It is evaluated once with `StepEnvironment.evaluate_actions` for the current interval and at each of the three imported OPS-3 projection offsets with frozen users, cloned D2/TLE projection, median/no-fading channels, absorbing loss, joint load/interference, and canonical network power.
- The characteristic value is allocated with the complete, exact rational Shapley sum. The declared current C1/C2 overlap is subtracted without clipping or sign filtering. Only the proposal's member/action row receives the resulting `z`.
- Deployment is `float64(float32(Q1+Q2)) + z/kappa`, masked, with the lowest legal index winning exact ties and `-1` only for an all-false mask. The complete deployed vector is physically evaluated once. BASE alone is committed between steps 0 and 1.
- Merge uses one exact ratio of pooled binary64 sums and the exact service fraction. It emits support only if every contract condition passes; all applicable no-support reasons are retained.

## Required runtime

Use `/home/sat/mcrl-leo-handover/.venv/bin/python`, set `PYTHONPATH=/home/sat/mcrl-v023-codex-ws-cand-a/src`, set `TMPDIR=/home/sat/mcrl-v023-codex-ws-cand-a/.tmp`, and set `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1`. The runner also imports and invokes E1's Torch single-thread pin before any mode.

## Seal order

1. Run `--estimate` against the read-only E1 output. The controller chooses the per-proposal `2^m` cap from that receipt; no cap is inferred by this package.
2. Resolve every C-A contract freeze placeholder, record the chosen cap/output and implementation digests, replace the draft/no-launch markers, make the controller-owned contract `0444`, and place a matching `<contract>.sha256` sidecar beside it.
3. Run the tests and implementation review. Any code change after this point changes the preflight inputs.
4. Build the preflight with `build_ca_preflight_manifest.py --profile-count-cap CAP`. It is write-once and includes the sealed contract, E1 terminal receipt SHA-256, F2 lineage authorities, PREREG, TLE archive, runtime, formulas, and code files.
5. Build a separate exact invocation authority with `build_ca_launch_authority.py`. Its `--launch-arguments` must name one `--unit W:L` or `--merge` command and bind the same cap, output root, preflight, authority path, E1 root, and (for units) TLE root.
6. Acquire all 12 fresh unit tapes. Each file is `0444` with hash readback; the shared ledger refuses work beyond 57,600 worker-seconds. `PROFILE_COUNT_EXCEEDED`, interruption, or budget exhaustion is `INCOMPLETE`, never truncation.
7. Run the separately authorised `--merge`. It authenticates all units and publishes one write-once terminal receipt.

The formal output root must be an absolute path beneath this candidate directory. This enforces the ownership boundary and prevents any E1, F0/F1/F2, OPS-3, TLE, contract, or other donor tree from being used as an output target.

`--dry-run` deliberately checks the contract seal before the preflight. While the supplied contract remains unsealed, its expected result is `CA_ERROR: C-A contract is not sealed...` and exit code 2.

The estimate reports current subset evaluations, the two C1 opening-source evaluations per proposal member, three OPS-3 offset evaluations per subset, their combined count, and F1-equivalent worker-hours. The combined estimate is deliberately conservative: joint projection overhead may be larger, and the fixed E1 realised-catalogue replay plus composed evaluations are disclosed but not added to the F1 profile scaling.
