# Opus Max C3/R3 and C1 source decision receipt

- Date: 2026-08-27
- Reviewer: Claude Opus 5, effort max
- CLI session: `bd43447d-d970-4bab-a3ec-7751995de6aa`
- Result UUID: `cce795de-bf3e-408a-95d6-9dd15ab91124`
- Mode: read-only bounded design decision
- Verdict: `REVISE`

## Decision

1. Adopt reward-aligned C3. C3 learns the unchanged canonical load reward
   `z3_u=r3_u=-U_{b_u}`. Its pre-outcome support is restricted to
   same-satellite relocations that strictly improve load balance at every
   certified interval and persistently relieve payload power.
2. For reference-fork pre-move loads, with the source load including the focal
   user and the destination load excluding it,

   ```text
   Delta sum_u r3_u = 2 * (U_source - U_destination - 1).
   ```

   Strict improvement is therefore equivalent to the integer condition
   `U_source >= U_destination + 2` at every certified interval.
3. The old marginal-power quantity is demoted from C3 learning reward to
   certificate, shadow-ranking, identity, and supporting diagnostic only.
4. Adopt the external ADR-004 source decision: `local_snr_greedy` is the named
   LEO-native generator and `masked_uniform` is its neutral control. Frozen-Main
   self-distillation is deferred, not silently substituted.
5. The immutable EXP prefill enters C1 specialist replay only. It never enters
   Main replay, Main source quotas, Main evaluation, checkpoint selection, or
   the headline metric. Only later actually executed C1-branch bundles may
   route their exact canonical reward vector to Main.

## Required scientific cautions

- The stricter joint load-and-power certificate may have very little support;
  support filters must be counted separately and failure permanently closes
  this last persistent-power route under the current gate budget.
- Within-window R3 improvement is true by certificate construction and is not
  an empirical result. The empirical endpoint must extend through the first
  post-release interval and episode total against matched controls.
- Main-consumer representability is unresolved. Main currently observes lagged
  ungated demand, whereas C3's certificate and canonical R3 use current eligible
  load. No C3 bundle may enter Main until the named alias/consumer gate tests
  that mismatch.
- Power and R3 statistics have different units and must never be summed or
  presented as one reward.
- The source generator is selected for identification and artifact decoupling,
  not because it is empirically established as superior.

## Notation ruling applied by the controller

The reviewer suggested a shorthand that would replace the active manuscript's
user-count symbol. That suggestion is not adopted because the active symbol
authority requires `U` as the cardinality of `mathcal U`. The manuscript will
avoid ambiguous `U_s/U_d` shorthand and write physical beam loads explicitly
as `U_{s,v}` and `U_{s,v'}`. Paper superscripts/subscripts remain single-letter
roles or physical indices.

## Claim ceiling

This decision establishes an algebraically coherent proposed design only. It
does not establish support, representability, learnability, power benefit, EE
benefit, three-role survival, effectiveness, novelty, or final results.
