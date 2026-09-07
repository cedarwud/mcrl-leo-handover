# C3 V3 Fable Max review and controller adjudication

Date: 2026-08-28  
Review type: read-only, pre-outcome, cross-model design audit  
Model: Claude Fable 5, effort max  
Session: `b43737e9-9c38-4361-8715-fb187bcf26f4`  
Model verdict: `REVISE_BEFORE_STAGE0`

## Cross-model findings

The reviewer found no fatal defect requiring abandonment of the three-role
design. It independently matched the canonical `r_3` identity, complete power
chain, decision interval, Main scalarization, diagonal C3-to-Q3 routing, and
Main-only deployment boundary.

Its blocking findings before Stage-0 freeze were:

1. the acceptance contract incorrectly claimed unconditional structural power
   nonincrease at the initial relocation; canonical recurrence can leave an
   already-active destination below `p^0`, so a new segment can raise its beam
   maximum;
2. requiring at least one strict power decrease made C3 unnecessarily narrow
   and would exclude a power-tied but useful-bit-improving strict-EE path;
3. `C3-GAP` is algebraically the exact within-window canonical system-`r_3`
   ordering, so learned C3 added value over GAP must appear after the
   certificate window;
4. the current eligible-load versus lagged/ungated Main-state load remains a
   real alias for both the specialist and Main consumer; and
5. both routed updater functions admitted durable bundle IDs before returning
   from replay warm-up, burning experience that had not been learned.

The reviewer also identified a C2 receipt-order defect: a missing release was
reported before an earlier hold-interval failure.

## Controller adjudication and completed revisions

No seed, census, training run, or outcome was opened before this decision.

- Selected the wider prospective C3 alternative because the research target is
  empirical effectiveness: complete power may never increase at any offset,
  while strict EE surplus remains mandatory. A power-tied candidate therefore
  needs a strict useful-bit gain; an energy-saving candidate may pass with equal
  useful bits. Both are exact strict forecast ratio-of-sums EE improvements.
- Corrected the false structural-power statement in the acceptance contract.
- Disclosed the exact `C3-GAP` equivalence and restricted learned added-value
  claims to extended or episode-total canonical `r_3`.
- Updated the C3 pure core and focused tests to the widened gate and strengthened
  strict typing, physical-ID, power-ledger, and alias-input validation.
- Added two-phase durable-ledger admission in both routed updater carriers:
  warm-up defers without consuming, duplicate preflight occurs before sampling,
  and durable commit occurs only after successful finite optimizer updates.
- Corrected C2 first-failure ordering and added a dual-failure fixture.
- Shifted the future C2 census anchors from reset-inclusive steps `0..5` to
  eligible steps `1..6`, preserving 150 attempts without a known-impossible
  reset row.

## Unresolved gates

- C3 support may still be sparse because four-offset non-focal action and
  active-set identity are intentionally strong. No frequency claim exists until
  a prospectively frozen census runs.
- Historical posthoc rows show nonempty multi-choice strict-load opportunities
  but do not instantiate V3 certification.
- The observational alias is unresolved. No C3 bundle may be routed and
  effective `beta_3` stays zero until a preregistered decision-time observability
  design passes for both `Q_3^F` and Main `Q_3^M`.
- A positive pure-core fixture is not support, learning, transfer, or EE
  evidence.

Controller status after revision: candidate for one fresh-context freeze audit;
formal training remains NO-GO.
