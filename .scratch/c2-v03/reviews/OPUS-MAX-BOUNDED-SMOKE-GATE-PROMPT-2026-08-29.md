[non-heavy read-only audit; expected wall time 5--15 minutes]

Act as a fresh-context adversarial reviewer. Do not edit any file and do not
trust prior prose without checking the current bytes. The public method is
Multi-Catfish MCRL. Review only whether the current C2 V0.3 implementation and
evidence carrier are safe to run a local, non-scientific 10-episode
opportunity/dose smoke. This is not authorization for 1500/3000/9000 episodes
and not an EE-efficacy or novelty review.

Read at minimum:

- `.scratch/c2-v03/c2_temporal_fork_episode_runner.py`
- `.scratch/c2-v03/c2_temporal_fork_segment_merge.py`
- `.scratch/c2-v03/verify_c2_v03_resume_parity.py`
- `.scratch/c2-v03/verify_c2_v03_merged_history.py`
- the tests under `.scratch/c2-v03/`
- `artifacts/c2-v03-resume-parity-clock-aware-u10-2ep-20260829.json`
- `artifacts/c2-v03-resume-merged-history-u10-2ep-20260829/merge-receipt.json`
- `artifacts/c2-v03-merged-history-parity-clock-aware-u10-2ep-20260829.json`
- `docs/C2-TEMPORAL-FORK-CANDIDATE-V0.3-2026-08-29.md`
- `docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md`

Known frozen inputs for the proposed smoke:

- arm `F111`
- 10 episodes, 10 users, `max_c2_candidates=1`
- learning rate `0.001`, beta `0.25`
- frozen preregistration `artifacts/PREREG-FROZEN-2026-08-25-R2.json`
- frozen TLE byte identity: count 373, set SHA-256
  `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`
- current host locator `.scratch/tle-frozen-20260820-authority-v1`
- use fresh train/environment/mobility seeds, a fresh output directory, and a
  bounded checkpoint cadence chosen only for the smoke; this does not claim the
  formal every-100-episode long-run cadence has passed.

Audit for result-corrupting defects only:

1. Main transition/update cardinality and no duplicate Main carrier when C2
   owns the joint transaction.
2. Strict `C2 -> Q_2^M` ownership, unchanged canonical `r2`, complete U-by-3
   audit bundle, no private forecast value leaking into Main reward.
3. Actual live option clock/state/mask progression and K0/K1/K>=2 semantics.
4. Resume/checkpoint, chronology, status, telemetry, and ratio-of-sums EE
   integrity at the bounded episode boundary.
5. Whether the proposed 10-episode smoke can validly estimate only opportunity,
   dose, option length, and forecast wall time.

Return one JSON object only with:

- `verdict`: exactly `GO_BOUNDED_10EP_SMOKE` or `REVISE_BEFORE_SMOKE`
- `blocking_findings`: list of concrete findings with file:line evidence
- `nonblocking_longrun_findings`: issues that block later long training but not
  this bounded smoke
- `required_smoke_configuration`: exact parameter and checkpoint guidance
- `allowed_claims`
- `forbidden_claims`
- `tests_or_commands_checked`
- `confidence` and a short rationale

If you cannot inspect a required file or execute a necessary fast check, return
`REVISE_BEFORE_SMOKE` and name the missing evidence. Do not infer effectiveness
from the two-episode K1 event.
