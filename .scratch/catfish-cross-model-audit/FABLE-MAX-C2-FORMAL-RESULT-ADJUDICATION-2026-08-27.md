# Fable Max C2 formal-result adjudication — 2026-08-27

## Review identity

- Reviewer: `claude-fable-5`, effort max, fresh read of the frozen C2 authority and formal artifacts
- Session: `e723920f-0462-4d0a-8156-c14b3368e5db`
- Formal JSON: `c2-time-only-identity-scale-seeds-2026082401-2026082410-v1.json`
- Recomputed JSON SHA-256: `38a5e38e3803e1e6f0cacc12a95e2cf99c4b890c96926e66c33c4e792a77c463`
- Exact requested verdict: **`DROP_C2_TIME_ONLY_EE_DIRECTION`**

This is a scientific/usefulness rejection of C2 time-only as an EE specialist at the
authorized `Delta = 30.08 s` clock. It is not an engineering failure and does not
invalidate `IDENTITY_SCALE_PASS`.

## Independently checked facts

- Exit status, local/server artifact hashes, reviewed-runner binding, all 15 authority
  checks, all 9 input-parity checks, and all identity/ledger checks close.
- The 1,000 focal rows contain 758 eligible and 242 ineligible rows. Exactly one
  eligible row is service-unsafe; removing it does not change the inference.
- Main reference interruption-time damage at the primary clock is `0.3250%`, with
  ten-seed t95 `[0.3145%, 0.3356%]`.
- The maximum observed damage reaches the structural ceiling
  `0.142 / 30.08 = 0.472%`.
- Exact-stay over all 758 eligible rows gives `+42,400.2 bits/J`, 393/758 positive
  rows, 7/10 positive seed means, and ten-seed t95
  `[-29,845, +108,138] bits/J`, which crosses zero.
- The 757-row service-safe subset gives `+42,895.6 bits/J`, 393/757 positive rows,
  7/10 positive seed means, and t95 `[-29,212, +108,330] bits/J`; the conclusion is
  unchanged.
- The non-primary `0.640 s` D2 sensitivity is much larger and stable, but it belongs
  to a different multi-step interruption-state/environment contract and cannot
  authorize the present C2 design.

## Reasoning

The reference-damage estimate and the paired exact-stay effect answer different
questions, but both reject advancing the present EE-specialist direction. The first
shows that the entire recoverable pool is structurally tiny at `30.08 s`; the second
shows that a blanket no-handover counterfactual is not seed-robust. State mapping may
change learnability or selection, but it cannot enlarge the `T_max / Delta` pool.

Even the descriptive post-outcome oracle `mean(max(0, paired_delta))` is about
`388,317 bits/J`, roughly `0.423%` of mean `eta0`. It is not a deployable policy and
does not alter the scale ruling.

The ruling follows the predeclared drop language in the C2 spec and ADR-004: if the
effect is negligible at the primary clock, C2 fails as an EE specialist and may only
be reconsidered under a separately specified continuity/QoS endpoint. No post-hoc
threshold is introduced.

## Reward-pathology record

No reward implementation or training is authorized. Any future continuity/QoS or
new-clock design must close all of the following before execution:

1. A hard served-to-unserved safety gate, so outage/re-entry cannot exploit `T = 0`.
2. The complete ledger-consistent reward `(B0 - L) / E0`, not the isolated
   `-R*T/E0` term, so lowering the served rate cannot shrink the only penalty.
3. One undiscounted rate array shared by `B0` and `L`, with no second discount.
4. Outcome-blind proposal before result evaluation; no result filtering or fitted
   thresholds.
5. `E0 > 0` and the frozen payload-only denominator boundary.
6. Explicit re-entry/excess-event accounting in the same reward vector.

## Authorized next action

The smallest next gate is documentation-only: freeze the C2-EE closure, include the
757-row sensitivity, retain C2 only as an explicitly new continuity/QoS hypothesis,
and state that operationalizing the `0.640 s` clock requires a new ADR and a new
multi-step environment contract. C2 state mapping, reward implementation, and
training are not authorized by this review.

## Claim ceiling

The formal shadow verifies C2's algebra and source/artifact provenance. It does not
validate C2 as an EE-improving Catfish. At the primary clock, the reviewed verdict is
to drop the time-only EE direction.
