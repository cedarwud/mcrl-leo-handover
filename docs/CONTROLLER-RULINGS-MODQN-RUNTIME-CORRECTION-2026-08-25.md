# MODQN runtime correction rulings (2026-08-25)

**Status: ACCEPTED.  RE-EVALUATE = YES.  RETRAIN = YES.**

The controller instruction `按照你的建議進行` authorizes the two bounded
runtime repairs, their regression tests, a visible corrective freeze, and the
corrected rerun.  It does not authorize changing reward definitions, numerical
thresholds, seeds, learning-rate arms, stopping rules, or the P6 selector after
seeing new results.

## R-1 — Warm-start history identity

Historical satellite positions are identified by
`(segment_age_steps, norad_id)`.  Each user must retrieve the position for that
user's sampled age.  Keying only by NORAD is invalid because later ages
overwrite earlier ages for every tracked satellite.

The public `reset -> step` regression forces ages `{1, 2, 4, 7, 9}` and checks
the realised first-step link power against each user's own back-projected
position.  It failed before the repair and passes with the age-aware key.

## R-2 — Candidate-state fading grain

Rician gain and shadow loss are one joint draw per
`(user_id, norad_id, observation_step)`.  All beams from the same satellite
share that path.  When a NORAD appears in both the current candidate set and
the previous-radiating interference set, candidate SINR must reuse the current
candidate draw; only previous-only NORADs receive an additional draw.

The public `reset -> step` regression instruments the stochastic boundary.  Its
fixture has two overlapping NORADs: the defective path consumed 400 Rician and
shadow elements, while the unique-path contract requires 360.  It failed before
the repair and passes after overlap reuse.

## R-3 — Corrective freeze without rewriting history

`artifacts/PREREG-FROZEN-2026-08-25.json` supersedes the 2026-08-24 seal and
adds only the two machine-readable runtime invariants above plus correction
provenance.

- 2026-08-23 and 2026-08-24 artifacts remain byte-preserved and independently
  verifiable.
- The 2026-08-25 self-digest is
  `d469d81fab617485b86897180ff52bacc2c514ca604bb676ab1585c8b15560f6`.
- Its byte SHA-256 is
  `2f8377d73a1ae0190df13a2b59b7d02803dd5769a7d577d94e17e1b613a8c8c2`.
- A regression removes only the two added invariant fields and correction
  provenance, then requires every remaining section to equal the 2026-08-24
  record exactly.

## R-4 — Existing result boundary

The completed 2026-08-24 P6/main artifacts remain valid evidence of what the
defective implementation executed.  They are not an accepted baseline for the
intended environment, cannot unlock Catfish intake, and cannot support final
EE, collapse, LR-selection, or r1/r2/r3 contribution claims.

## R-5 — Corrected rerun gate

Before new P6/main training:

1. run the targeted regressions, full suite, numerical oracles, and a short
   paired pilot locally;
2. rerun corrected P3 calibration and P7 warm-start measurements, and refresh
   affected P2/power/outage measurements;
3. apply the already-frozen selection mappings.  If corrected P3 inputs imply
   a different resolved scale, stop and seal that deterministic resolution
   visibly before training;
4. run all three matched P6 arms and the independent main run on the Ubuntu
   server under a fresh source/config fingerprint.

Catfish integration remains blocked until this chain completes.

## R-6 — Corrective probe execution addendum

The frozen record specifies the probe sampling distribution but does not specify
the probe epoch realisation seed.  The historical launchers cannot fill that
gap: `scripts/run_probes.py` is an 8-episode smoke run, while
`scripts/run_probe_p3.py` is a 12-episode, one-policy diagnostic.  Neither is
the frozen 200/200/100-episode grid.

Before observing any corrected probe result, the controller therefore seals
`artifacts/CORRECTED-PROBE-PROTOCOL-2026-08-25.json` as a post-freeze execution
addendum:

- keep the pre-result historical probe master seed `20260823`;
- assign `SeedSequence` children 0/1/2 to environment, mobility and action, and
  child 3 only to `EpisodeStartSampler`;
- draw one 200-epoch train-split schedule, shared by every matched arm; P7 uses
  the same first 100 epochs;
- run P2 at 200 episodes for each `N in {2,3,4}`, P3 at 200 episodes for each of
  the three reference policies, and P7 at 100 episodes for both frozen
  warm-start arms;
- use the frozen reference-policy seed `20260822` and apply the `c1`/`c3`
  selection mappings only to `stay-if-possible`.

The addendum self-digest is
`0d778ccdbbaf016310e1b541c421d98f95b06c993bc509a637ef37d386824560`.
It does **not** retroactively claim that the preregistration contained the
missing epoch seed.

## R-7 — P3 estimand correction

The frozen Q-F rule says `c1` is the p95 of `r1` over **served** steps.  The
historical P3 accumulator reported its `r1` quantiles over all decision steps,
including outage zeros; the old artifact's count of 12,000 rather than its
served count exposes the mismatch.  The corrected probe now reports both
series explicitly:

- `r1`: all decision steps, retained for descriptive comparability;
- `r1_over_served_steps`: the only input accepted by the Q-F mapping.

If either corrected `c1` or corrected `c3` differs from the currently resolved
value, the runner completes the measurements but exits with P6 blocked.  A new
visible corrective seal must apply the already-declared mapping before P6; no
training launcher may choose a value itself.

The existing continuous `c1` artifact literal is stored to three decimal
places (`2471140.576`), while its historical raw p95 retained more digits.
Equality is therefore tested by `ROUND_HALF_UP` to those three stored decimal
places; this is a comparison precision rule, not permission to tune a
tolerance after observing the corrected value.

## R-8 — Completion integrity

`complete` requires more than consuming an epoch list.  Each result is checked
against `episodes * users * 10` actual user-decision rows: 200,000 for every P2
arm and P3 policy, and 100,000 for every P7 arm.  Missing/early-terminal rows
fail the run.

The execution manifest fingerprints every Python file under `src/mcrl`, the
launcher, `pyproject.toml`, the corrective protocol, the prereg artifact, and
the installed Python/NumPy/SGP4/PyYAML/Torch versions.  The fingerprint is
rechecked around every arm; the live TLE file set is revalidated before the
schedule is drawn and again before completion.  Any mid-run input drift marks
the run failed and cannot unlock P6.

## R-9 — Corrected probe verdict

The formal Ubuntu-server rerun completed every declared arm and row count. Its
status 2 is the intended calibration stop, not a runtime crash. Under the
frozen `stay-if-possible` selection policy:

- corrected served-step `r1` p95 is `2029238.4328742754`, which becomes
  `2029238.433` only for the presealed comparison with `2471140.576`;
- corrected rounded served-step `abs(r3)` p95 remains `6`;
- P7 outage is `0.06312` in the main arm and `0.05207` in the fixed-age
  sensitivity arm.

Therefore Q-F mismatches, Q-D does not, and the first 2026-08-25 seal cannot
directly unlock P6. Full results and hashes are recorded in
`docs/POST-RUN-CORRECTED-PROBES-2026-08-25.md`.

## R-10 — Deterministic Q-F re-freeze

The Q-F rule is not reopened. It already says to use the p95 of `r1` over
served steps and says not to round the continuous bit/J value. The next seal
therefore resolves `c1 = 2029238.4328742754` exactly. The three-decimal rule in
R-7 was only a result-before equality test against the old three-decimal
literal; it is not the representation policy for a new resolved value.

The R2 seal may change only Q-F's probe label, corrected measurement evidence,
resolved value and corrective-resolution metadata, plus top-level refreeze
provenance. Every other numerical value, seed, threshold, stopping rule,
learning-rate arm and P6 selector remains identical to the first 2026-08-25
seal. The training launcher must verify the full evidence chain before P6.

The resulting canonical artifact is
`artifacts/PREREG-FROZEN-2026-08-25-R2.json`, with self-digest
`3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`
and byte SHA-256
`8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`.
It was generated with the project environment's SGP4 2.27. A rejected
system-Python candidate used SGP4 2.25; it was never canonical and was retained
under `.scratch/` rather than overwriting either seal.
