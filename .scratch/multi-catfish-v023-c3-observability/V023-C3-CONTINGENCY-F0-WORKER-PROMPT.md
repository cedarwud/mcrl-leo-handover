# Worker task — C3 contingency F0 formula seam

Compute class: **non-heavy** implementation and test-only work.  Stay in the
current environment.  Do not run a simulator, training, physical episode,
matched pilot, or TEST split.

Work only in a new isolated directory:

`.scratch/multi-catfish-v023-c3-contingency/`

Read before acting:

1. `.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md`
2. `artifacts/multi-catfish-c3-fable-cleanroom-20260904-r1/FABLE-C3-SOURCE-AUDIT.md`, especially Sections 7D, 7F, and 8
3. `src/mcrl/env/link_budget.py` canonical fixed/system power accounting
4. `src/mcrl/env/step.py` action-evaluation fields
5. Existing pure-function contract style in
   `src/mcrl/runtime/ee_axis_coalition_residual_c3.py`

Implement only F0:

- a pure, deterministic cost-share function for one complete physical profile;
- exact conservation checks showing the sum of served-user beam and active-
  satellite cost shares equals canonical profile network energy/power under the
  declared interval convention;
- reference-centred CSE (`D`) and energy-share-only EC (`F`) targets exactly as
  frozen in the contingency ladder;
- immutable typed inputs/outputs, finite-value and shape validation, explicit
  unserved handling, no clipping/sign filter/compatibility gate/rescaling;
- unit tests covering one-user, shared beam, shared satellite, beam extinction,
  new beam, unserved user, centring, permutation invariance, conservation,
  nonfinite rejection, and a deliberately forged nonconserving profile.

Do not integrate with the V0.23 Gate, edit any `src/`, `docs/`, authority,
preflight, manifest, server launcher, current run, or existing artifact.  Do
not choose worlds, seeds, thresholds, or learner architecture.  This seam must
remain inert unless explicitly imported.

Use `apply_patch` for authored files.  Run only the new focused tests plus
`git diff --check` for your owned directory.  At completion, report changed
files, exact test command/result, formula interpretation, and any blocker.
Then stop.
