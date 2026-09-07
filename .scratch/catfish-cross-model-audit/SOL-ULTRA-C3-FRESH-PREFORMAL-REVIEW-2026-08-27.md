# Sol Ultra C3 fresh-context pre-formal review

- Date: 2026-08-27 (Asia/Taipei)
- Reviewer: `gpt-5.6-sol`, reasoning effort `ultra`
- Mode: fresh-context, read-only; no long experiment
- Reviewed runner SHA-256:
  `5c1eaf407b9cc49748add2b06dace65018c2a8a6f9ea7c6528a61b9b6c1b0a1b`
- Reviewed launcher SHA-256:
  `35b3452ea8422d86c79804bb131748ce546344851991af761d52eee822e293cc`
- Verdict: `REVISE_BEFORE_FORMAL`

## Blocking findings

1. The byte-pinned helper files were not bound to the modules and symbols
   actually loaded.  The reviewer required resolved-path equality for the C3
   v1 helper, oracle helper, and checkpoint-loader module; module identity for
   `base.v1`; and identity checks for `DEFAULT_INPUT`, `DEFAULT_PREREG`,
   `_sha256`, `_frozen_archive`, `_make_environment`, and
   `_verify_and_load_trainer`.
2. The paired forks shared one `SatelliteSet`/`SatrecArray` with the outer
   rollout while the state receipt excluded SGP4 internals as static.  SGP4
   propagation passes internal records by mutable reference, so that layout
   could not prove independent branch state or outer immutability.  Each branch
   must reconstruct an independent propagator from the same frozen TLE records
   and prove object separation plus equal record/NORAD identity.

## Verified-compliant scope

The reviewer independently accepted the following portions of the pinned
version:

- outcome-blind fading-off proposal construction and restoration;
- unchanged median guard, deterministic power-first tie-breaking, and full
  census retention;
- PA reduction and unilateral marginal-power reward identities with the
  `1e-10 W` gate;
- five disjoint seeds, 5,000 user-steps, non-vacuous support/t95 rules, and
  Q1-only continuation;
- the `_Unserved` clone correction and three-way environment/mobility/age RNG
  checks;
- the formal launcher seed/step/output/no-overwrite/SHA/exit contract;
- the strict claim ceiling.

## Nonblocking cautions retained

- Verify Python, NumPy, Torch, SGP4 2.27, and PyYAML at result acceptance.
- A seed with no selected pair makes the five-seed t interval unestimable; this
  is intentionally stricter than the separate four-of-five support condition.
- Receipt-last publication is not a single multi-file filesystem transaction;
  accept only a present receipt whose two artifact hashes match.

## Post-review delta

The two blockers were addressed by adding explicit helper import/symbol
bindings and reconstructing one independent `SatelliteSet`/`SatrecArray` per
branch from equal frozen records.  The resulting runner SHA-256 is
`dd18fca6c66b8be70e0ebc92366f1d078636faa5995c9b2d86b4159942ca8548`.
This original verdict remains `REVISE_BEFORE_FORMAL` until the bounded multi-step
smoke and a delta review pass.
