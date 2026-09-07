# Fable Max review of SMC-ER v0.3 — 2026-08-27

## Identity

- Reviewer: `claude-fable-5`, effort max
- Session: `66c58f85-e160-4671-b32e-6b3484232732`
- Reviewed file SHA-256:
  `e0bedb7aac35544b8be166fe3be343a7fc998fa572c2365d236c918503f25999`
- Independently recomputed SHA: exact match
- Verdict: **`PASS_TO_CARRIER_SMOKE`**

The pass is a method-coherence verdict, not an effectiveness or G-6 release.
Fable found no architecture-level blocker but required the following exact
specification closures before the relevant execution stage.

## Required before smoke specification freeze

1. Define who generates every action in C3's deterministic H3 roll-forward,
   including the non-focal physical action sequence, focal reference/candidate
   holds, geometry evolution, and infeasibility failure semantics.
2. Define C1 behavior as masked epsilon-greedy from C1's own Q1 and RNG, and
   identify the frozen policy that generates the executed EXP corpus.
3. Treat zero C3 support in a stochastic 20–30-episode smoke as a valid support
   receipt that blocks a pilot, not an engineering smoke failure; deterministic
   fixtures must cover certificate and termination paths.

## Required before sealed C3 shadow

4. Resolve the contradiction between support in four of five seeds and a
   five-seed t interval. Either compute over supported seeds with the correct
   degrees of freedom or require support in all five; never impute a zero-
   support seed mean.

## Required before short pilot

5. State that C3 informed treatment and the C3 slot in the full treatment are
   unavailable unless the new sealed H3 shadow passes. The prior adjudication
   authorizes only that non-training shadow.
6. Evaluate C2 through the first post-release interval and over the full
   episode, so an event shifted just beyond H2 cannot be scored as removed.
7. Define C1's matched control for both mechanisms: same action-trajectory dose
   and equal-size/equal-injection corpus with uninformed stratum identity.

## Other verified findings

- C1/C2/C3 are distinct in objective, private signal, time scale, and support.
- C2's persistence option can use one-step TD if option behavior is represented
  correctly; every early termination/outage must remain in replay.
- C3's pre-outcome certificate and post-execution private reward are not
  outcome leakage when selection reads only the deterministic certificate.
- Private signals can remain isolated from Main if exact unshaped vector
  transfer and single calibration are enforced.
- A 20–30 episode smoke is adequate for exact engineering equivalence, and a
  200–300 episode pilot is only a directional screen.
- v0.3 does not resurrect the failed C2 time-only or C3 median variants.
- The novelty ceiling is appropriately narrow.

## Permissible claim ceiling

SMC-ER may be described as a proposed three-specialist, training-time
experience-routing architecture with canonical Main reward vectors and zero
specialist dose at deployment. No effectiveness, EE improvement, learnability,
joint superiority, generalization, or global novelty claim is authorized.
