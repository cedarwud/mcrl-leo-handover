You are an independent reviewer from a different model family, reading a committed implementation with a fresh context.
You have file access. Read the artefacts themselves, not summaries. Report in English. Do not edit anything.

TASK: check whether the committed code implements the written contract exactly, and whether any implementation defect
would make the running development experiment uninterpretable. The experiment is already running (development lane only,
no formal evaluation episode is touched), so the useful output is: what must be fixed before the NEXT stage (a 3-seed
ep-300 confirmation and then a formal 1000-episode run), and what is cosmetic.

READ:
1. The contract (revision r2): `/home/u24/papers/mcrl-leo-handover-mc2/.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md`
   — §1 roles and disclosures, §2 the judge, §3 the two rules (`MC2-JGO-v1`, `MC2-ARB-v2`), §5 invariants and the eleven
   required tests, §6 cells/seeds/budget, §7 the declared readings (especially the clause-(vi) activity counts).
2. The implementation, at commit `11466998` on branch `mc2/judge-override-20260912` in
   `/home/u24/papers/mcrl-leo-handover-mc2`: `src/mcrl/algorithms/cf_judge.py`, the diff of
   `src/mcrl/algorithms/cf_dev.py`, `scripts/dev_e0_common.py`, `scripts/run_dev_e0.py`, `scripts/dev_e0_launch.py`,
   and the tests `tests/test_mc2_judge.py`. Use `git -C /home/u24/papers/mcrl-leo-handover-mc2 diff 6136c514 11466998 -- <path>`
   to see exactly what changed, and `git show 6136c514:<path>` for the base.
3. The lane's own report `/home/u24/papers/mcrl-leo-handover-mc2/.scratch/mc2/LANE-A-MC2-JUDGE-2026-09-12.md` and the
   method owner's code read `/home/u24/papers/mcrl-leo-handover-mc2/.scratch/mc2/B/CODE-READ.md` (do not repeat what the
   latter already verified; say so and move on).

ANSWER, with file:line evidence:
A. **Judge fidelity.** Is `κ = (n_served, B − η₀E)` computed from `evaluate_actions((candidate, x_{-u}), deepcopy(rng))`
   with the frozen η₀, strict lexicographic, ties to the incumbent? Is it called after the behaviour action and before
   `env.step`? Can it advance or contaminate any generator, mutate environment state, or leak into the TD target? Is the
   per-step parity assertion against the committed step actually enforced (not just available)?
B. **Rule fidelity.** Does v1 override only when the challenger strictly beats the incumbent, and v2 pick
   `max κ` over `{x_u, a^A, a^B}` with ties `x_u → A → B` and inject only when the winner ≠ `x_u`? Does every margin row
   have exactly one target, with weight `1[target]` and the full-batch normaliser? Is the B/R abstention at the final
   decision step implemented for every cell? Is the shared `B-only` identity rule-independent, and is the claimed
   equivalence of the v1 and v2 code paths for `{B}` actually tested at parameter level?
C. **Nulls and identity.** Does the null draw exactly one uniform legal action per user with a legal action at `t < T−1`
   from a fresh generator at the declared key, never reading the second specialist, and is that generator saved and
   restored on resume? Does the configuration hash cover mechanism id, rule, source set, judge identity (η₀ and key
   order) and null identity? Are arms 1–9 byte-identical in payload to the base commit?
D. **Readings support.** Does the per-episode log carry the raw counts the contract's clause (vi) needs — user-steps with
   at least one legal action over ALL `t` as the denominator, user-steps tagged B for v1, and winner-is-`a^B`-with-
   `a^B ≠ a^A` for v2 — plus per-tag sampled rows, per-tag margin-loss mass, margin dose, judge evaluations and wall? Can
   the declared ep-100 and ep-300 readings be computed from the saved files alone?
E. **Tests.** Do the eleven contract tests exist and do they test what they claim (in particular: gate-shut equivalence to
   the frozen single-teacher arm, the judge's side-effect freedom, the step-parity equality, and the zero-margin rows)?
   Name any test that would pass even if the property were violated.
F. **Anything that would make a positive DEV result uninterpretable**, or that would silently differ at a 1000-episode
   formal run (resume paths, schedule dependence, memory growth, accumulated generator state).

FORMAT: first line exactly `VERDICT: NO-INVALIDATES` or `VERDICT: INVALIDATES-FOUND`. Then a numbered list, each finding
tagged INVALIDATES (must be fixed before the ep-300 confirmation) or NON-BLOCKING, with the smallest concrete fix. Do not
propose new mechanisms, sources, sweeps or versions. Under 1,200 words.
