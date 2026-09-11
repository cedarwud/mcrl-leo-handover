You are a fresh-context engineering reviewer from a different model family. Read the ACTUAL code yourself; do not rely on any summary. Do not edit anything. Be fast and concrete: this review gates a short development training run (not a formal experiment).

Repository worktree: <WORKTREE>. Review ONLY this diff: `git -C <WORKTREE> diff <BASE>..<HEAD>`.

What the diff is supposed to add: **D3-null**, the matched null for the D3 large-margin teacher injection of the development harness (`.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md` §2, §3, §6 — read them). Required properties:
1. The D3 loss, its margin, its weight lambda_E, its schedule, its legal-action mask and its gradient path are IDENTICAL to D3-T0; the only difference is the action the margin points at.
2. That action is a seeded uniform random LEGAL action drawn from the already-declared DEV-NULL namespace `default_rng((9_241_000, k))`, independent of T0.
3. T0's action must not enter ANY loss input of the null arm (the T0 action may be stored for diagnostics only if no loss can read it).
4. The null generator must consume no trainer stream (train / env / mobility RNG untouched) and must survive stop/resume.
5. Teacher weight zero must still reduce to D0 exactly.
6. The version identity (configuration hash) must cover the null identity, so D3-null at k=0, at k=1 and D3-T0 are different versions.
7. No formal evaluation (9_111_000+i / 9_112_000+i), calibration (9_121_000+i / 9_122_000+i) or CONFIRM (9_311_000+i / 9_312_000+i) seed may be reachable from any development path.

Look for: anything that would make the null a weak or leaky control — a draw that is not uniform over the legal set, a draw that can land on an illegal action, any dependence on T0's scores or action, a shared generator with the student's exploration or the environment, a null identity missing from the hash or the manifest, a resume that loses the null stream, failures swallowed, and tests that pass without testing the property (check that the named mutants really turn them red: `DEV_MUTANT=<name> pytest tests/test_cf_dev.py -k <test>`).

Output: findings with severity (INVALIDATES / BIASES / COSMETIC), concrete failure scenario, file:line; verified-by-reading vs inferred. First line: one bold sentence with the count of INVALIDATES and BIASES and whether the D3-null development runs may proceed. Write to <OUTFILE>.
