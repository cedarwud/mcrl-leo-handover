# C3 reward-aligned Stage-0 specification — scalarized Main V3

Date: 2026-08-28  
Status: prospective, deterministic pre-outcome support specification; **no
runner, census, outcome, seed reveal, learner, or training is authorized**

## 1. Authority and historical boundary

This specification translates the C3 clauses of
`docs/THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.1-2026-08-28.md`
into a bounded Stage-0 engineering contract. At drafting time that authority
has SHA-256
`eda80c6688b79c3e311116d3599c14644251655dd569bcaeb3425fa683a485db`.
The reviewed closure must re-hash the live bytes; the value above is inventory,
not permission to ignore later drift.

The following V2 surfaces are historical evidence and remain byte-for-byte
unchanged:

- `.scratch/catfish-design-data/C3-REWARD-ALIGNED-STAGE0-SPEC-V2-2026-08-27.md`
  (draft-time SHA-256
  `810fe8f91dd8d8755681de5b8f76756e25c140cd3f5a44000aca097764b36554`);
- `.scratch/catfish-stage0/c3_reward_aligned_core.py` (draft-time SHA-256
  `e7a6184a5cb20a8dab09f4438e0a801b8fd2619cd85f3c01020642b0339ad031`);
- `.scratch/catfish-stage0/run_c3_stage0.py`, the historical environment
  adapter (draft-time SHA-256
  `8b3c254856393bffc00b6fb438083357be1995dc99fd3ab0d2a72be8b154c3a1`);
- their historical tests, closure inputs, manifests, and outputs.

V2 is useful factual inventory for physical-ID remapping, twin reconstruction,
eligible-load identities, option state, and complete receipt concepts. It is
not V3 authority. In particular, the historical adapter selects Main with
Q1-only weights, and the V2 core lets forecast power relief break a `C3-GAP`
tie. Neither behavior is allowed by V3. Historical outcome rules, revealed
seed surfaces, and result schemas must not be relabelled or reused as V3.

If this specification conflicts with the acceptance contract, canonical
runtime reward or physics, or a later reviewed authority, execution stops and
a new prospective version is required. A scratch adapter may not silently
resolve the conflict.

Before any V3 census, seed, or outcome was authorized, a Fable Max audit
returned `REVISE_BEFORE_STAGE0`. Controller adjudication selected the wider of
the two prospective alternatives: retain complete-power nonincrease at every
offset, remove the unnecessary requirement for one strict power decrease, and
retain strict useful-bits/EE-surplus certification. This admits both
energy-saving and power-tied/useful-bit-improving paths while keeping every
candidate strictly forecast-EE-positive. It is a pre-outcome design correction,
not a result-driven rescue.

## 2. Stage-0 question and claim type

The V3 Stage-0 question is deliberately pre-outcome:

> At frozen scalarized-Main anchors, does the canonical simulator expose
> same-satellite, high-to-low, already-active one-user relocations that retain
> the exact strict canonical `r_3` construction identity through a three-step
> hold, preserve a strict system-total `r_3` advantage through first release,
> and remain inside complete-power, useful-bits, EE-surplus, service, identity,
> and causality safeguards?

A positive deterministic fixture result proves only that the engineering
semantics are implemented as specified. A later separately authorized
pre-outcome support census could measure opportunity frequency. Neither result
shows that `Q_3^F` can learn a useful ordering, that Main can observe or consume
the distinction, that realised fading preserves the forecast, or that Main-only
EE improves.

## 3. Exact scalarized Main reference

`M-REF` uses the corrected Main checkpoint read-only with the deployed
scalarized action surface:

```text
Q_M^sc(s,a) = 0.5 Q_1^M(s,a) + 0.3 Q_2^M(s,a) + 0.2 Q_3^M(s,a).
```

The operational V3 adapter must call the checkpoint-backed equivalent of:

```python
encoded = trainer.encode_states(states)
q = trainer.scalarized_q_values(
    encoded, objective_weights=(0.5, 0.3, 0.2)
)
actions = masked_greedy_actions(q, masks)
```

Before inference it must assert that the trainer's configured objective weights
are exactly `(0.5, 0.3, 0.2)`. Existing masked-greedy tie behavior is retained.
The valid-action Q rows, masks, candidate-table order, selected indices, and
selected physical IDs are receipted. There is no epsilon, Q1-only fallback,
candidate-specific weight row, reward rescaling, or Catfish action in `M-REF`.

Scalarized Main also supplies every non-focal action in both forecast forks and
the focal action after release. A candidate cannot substitute a Q1-only helper
at any of those seams.

## 4. Frozen horizon, anchor, and branch geometry

V3 freezes:

```text
HOLD_STEPS = 3
FIRST_RELEASE_OFFSET = 3
CERTIFICATE_OFFSETS = [0, 1, 2, 3]
```

Offsets `0..2` are the forced relocation-and-hold intervals. At offset `3`,
the option is released before action selection and the focal user again takes
its exact scalarized-Main action. The first-release interval is part of the
certificate and may not be omitted, treated as termination, or moved outside
the window. An anchor with fewer than four complete intervals remaining is
ineligible.

An anchor is eligible for candidate construction only when:

1. reset plus the exact scalarized-Main physical-action prefix reconstructs
   the complete mutable state and candidate tables field-by-field;
2. every deep twin has the same complete anchor fingerprint and digest but is
   a distinct object;
3. the focal user was served immediately before offset `0` on a physical
   source pair `(norad_id, cell_id)`;
4. scalarized Main selects that continuing source at offset `0` with no current
   handover or re-entry event; and
5. four complete forecast intervals remain.

The reference option binds the scalarized-Main-selected source at offsets
`0..2`; a candidate binds one declared destination at those offsets. Both
release to scalarized Main at offset `3`. This paired hold isolates the declared
one-user spatial relocation. It is not a claim that forcing the reference
source is ordinary Main deployment.

Forecast construction is fading-off and pre-outcome. No realised fading,
future outcome, training, validation, confirmatory, or historical Stage-0 seed
may be opened. Any future forecast schedule and RNG lineage require a separate
closure-bound authorization; this document contains no seed values or seed
manifest.

## 5. Physical-ID candidate grammar and hard-safe identity

A candidate is identified only by a unique physical pair
`(norad_id, cell_id)`. Candidate-table indices are interval-local and never
persistent identity. Duplicate table rows mapping to one physical pair fail the
anchor; they never give that destination extra weight.

Exactly one candidate form exists:

1. at offset `0`, relocate the focal user once from source `(s,v)` to one
   declared, distinct destination `(s,v')` on the same satellite;
2. the destination must already be active in the reference fork without the
   focal user;
3. hold that exact destination physical ID at offsets `1` and `2`; and
4. release to scalarized Main at offset `3`.

At each forced offset the source and destination must remap uniquely, the
declared focal actions must be mask-valid, recurrence/link power must be finite
and no greater than the canonical per-link ceiling, and the focal user must be
served on its declared pair. A second relocation, redraw, table-index binding,
hidden fallback, early expiry, shortened horizon, or substitution after an
invalid hold excludes the candidate. The first failed interval remains in the
diagnostic receipt.

For every offset, scalarized Main independently computes every non-focal user's
physical action in the reference and candidate fork. The candidate survives
only if all non-focal actions are exactly equal as `NO_OP` or physical IDs.
Equal table indices or equal aggregate statistics are insufficient. The
reference non-focal physical script is then executed in both forks and must
remain uniquely remappable and mask-valid.

Through the full four-interval certificate:

- every user served in the reference at an offset remains served in the
  candidate at that offset;
- the focal user is served in both forks without outage or re-entry;
- no event other than the candidate's declared initial same-satellite event is
  hidden or discarded;
- preview and committed results agree for associations, service, handover
  classes, recurrence/link power, active sets, rate, complete power, and the
  unmodified reward vectors; and
- active-beam and active-satellite sets are identical between forks.

Any branch-local scalarized-Main disagreement for a non-focal user fails the
candidate rather than being forced out of the receipt.

## 6. Unchanged canonical `r_3` and exact strict-load identity

The adapter consumes the unmodified canonical reward matrix emitted by the
environment. It neither derives a private C3 reward nor changes reward scale:

```text
r_{3,u}(t) = -U_{s,v}(t)
```

for a served user on physical beam `(s,v)`; the canonical environment behavior
for an unserved user remains unchanged. At every offset the system total must
match the exact eligible-load identity:

```text
sum_u r_{3,u}(t) = -sum_{s,v} U_{s,v}(t)^2.
```

At each forced offset `0..2`, reconstruct both eligible-load maps independently
from the served physical associations. The reference source load includes the
focal user and the reference destination load excludes it. Candidate and
reference maps must differ only by source `-1` and destination `+1`; their
positive keys must equal their active-beam keys, and the load sum must equal
the served-user count.

The source and destination loads must satisfy the exact integer guard:

```text
U_src^M(t) >= U_dst^M(t) + 2.
```

The supplied canonical reward totals must then satisfy exactly:

```text
Delta sum_u r_{3,u}(t)
  = sum_u r_{3,u}^C(t) - sum_u r_{3,u}^M(t)
  = 2 * (U_src^M(t) - U_dst^M(t) - 1) > 0.
```

`eligible_load_by_beam` is the construction authority. Lagged or ungated
`demand_by_beam` is diagnostic input for the observational-alias gate and may
never substitute for eligible load.

The single-user algebraic identity applies only while the declared source and
destination are forced at offsets `0..2`. Offset `3` records the canonical
reward vectors produced after both branches release to scalarized Main. The
candidate must have a strictly greater system-total `r_3` sum over offsets
`0..2`, and that cumulative advantage must remain strictly greater over
offsets `0..3`. A release cost may reduce the margin, but a delayed loss that
erases it fails. Focal-only improvement cannot substitute for either system
total.

## 7. Complete canonical power and energy safeguard

No beam count, focal-link power, payload-only power, fixed-only power, or
time-only surrogate may certify C3. Every offset in both forks must execute the
complete canonical power chain in `src/mcrl/env/step.py` and
`src/mcrl/env/link_budget.py`:

```text
p_{u,s,v}(t) = p^0 G^T(theta(tau)) / G^T(theta(t))
p_{s,v}(t)   = max over served users of p_{u,s,v}(t)
xi_{s,v}(t)  = min{xi_max, xi_max sqrt(p_{s,v}(t)/p_sat)}
P^p_{s,v}(t) = p_{s,v}(t) / xi_{s,v}(t)
P^f(t)       = sum_s [N^act_s P_cir + 1{N^act_s>0} P_BB]
P^N(t)       = P^f(t) + sum over active beams P^p_{s,v}(t).
```

The canonical diagnostic must expose, per interval, each served user's
recurrence inputs and output, the per-beam maximum RF power, PA efficiency and
supply power, active-beam counts by satellite, circuit power, once-per-active-
satellite baseband power, fixed power, and complete `P^N`. V3 independently
reconstructs the component identities from these supplied canonical terms and
fails on a relative discrepancy greater than `1e-9`. This is an identity
check, not a scratch implementation of link physics. If the public canonical
outcome does not expose a required component, implementation stops until a
read-only canonical ledger is reviewed and tested.

Across offsets `0..3`, candidate complete system power must be no greater than
reference complete system power at every offset. Equality at all four offsets
is allowed at this layer; the later strict EE-surplus gate then requires a
power-tied candidate to obtain its strict forecast EE advantage through useful
bits. Every sign comparison is applied only after the component identity and
finite checks pass. The historical superseded per-link PA charging form is
diagnostic only and cannot enter the certificate.

Using the existing `30.08 s` decision interval, complete certificate energy is

```text
E^M = 30.08 * sum_{t=0}^{3} P_M^N(t)
E^C = 30.08 * sum_{t=0}^{3} P_C^N(t).
```

Both energy sums must be finite and strictly positive. Energy saving, when
present, is a receipt diagnostic rather than a separately required support
condition, reward, score, or ranking tie-breaker.

## 8. Useful-bits nonloss and strict EE-surplus proxy

For the identical fading-off four-interval window, use system useful bits from
the canonical rate/service outcome and the complete system joules above:

```text
B^M = 30.08 * sum_t system_throughput_bps_M(t)
B^C = 30.08 * sum_t system_throughput_bps_C(t)
eta^M = B^M / E^M.
```

A candidate must pass both exact binary tests:

```text
B^C >= B^M
(B^C - B^M) - eta^M (E^C - E^M) > 0.
```

All four accumulations and the surplus must be finite; `E^M>0` and `E^C>0`
are mandatory. Useful-bits equality is allowed only when the strict surplus
still passes. Zero energy, `0/0`, NaN, infinity, epsilon denominators,
tolerance-based useful-bits nonloss, or a zero/negative surplus fails closed.

The surplus inequality is exactly equivalent to strict improvement of the
four-interval fading-off ratio of sums, `B^C/E^C > B^M/E^M`, when both energies
are positive. It is therefore the strict forecast-EE membership condition. It
is not a realised-fading or Main-only efficacy claim.

The useful-bits result and EE-surplus result are one membership bit per
candidate. Their magnitudes, energy saving, power margin, physical-ID order,
and service margin must not rank candidates, break a tie, become canonical or
private reward, define a TD label, change replay weight, select a checkpoint,
or alter later admission after an outcome. Permuting candidate rows must leave
every support set unchanged.

These are fading-off screening proxies only. They are not a realised useful-
bits guarantee, a stochastic EE claim, or a replacement for later Main-only
ratio-of-sums EE evaluation.

## 9. Certificate layers

V3 reports a nested waterfall with distinct denominators and reasons:

1. scheduled anchor;
2. qualifying scalarized-Main continuing-source anchor;
3. unique same-satellite, already-active physical-ID candidate;
4. full-window hard-safe candidate;
5. exact strict-load and unchanged canonical-`r_3` candidate;
6. complete-system-power candidate;
7. useful-bits-nonloss and strict-EE-surplus candidate;
8. through-release system-total-`r_3`, service, event, and identity candidate;
9. final certified choice.

A candidate enters a layer only after every earlier layer passes. Every failure
retains its first failed offset and reason. Load and power have different units
and are never added, normalized into a joint score, or exposed as reward.
Unsupported anchors and zero-choice anchors remain explicit rows; they are not
omitted or imputed as a zero effect.

Before any census result is opened, V3 freezes the same symmetric opportunity
budget as C2:

```text
5 census partitions x anchor steps 1..6 x 5 focal users = 150 rows.
```

The five focal users at each step come from a closure-bound deterministic
permutation. Step `0` is excluded because reset has no immediately previous
served source. Every scheduled row, including a nonqualifying anchor or zero
certified choices, must be retained without imputation.

The support floor is also frozen before outcomes:

- each of the five partitions contains at least one anchor with at least two
  distinct final certified physical-ID choices;
- at least 20 such two-choice anchors exist in total; and
- every counted choice passes all nine layers over the complete four-offset
  certificate.

Passing yields only `C3_V3_STAGE0_SHADOW_READY`. Missing either the per-partition
or pooled floor is `C3_V3_SUPPORT_FAIL`; the floor may not be lowered after the
census. Exact partition identifiers, deterministic permutation material, RNG
namespaces, and hashes remain absent until a separate no-outcome engineering
closure. Fixture success cannot be used to choose a favorable schedule or
floor.

## 10. Frozen non-learning controls

The Stage-0 support ladder is:

- `reference`: bind the scalarized-Main-selected source at offsets `0..2`,
  then release to scalarized Main at offset `3`;
- `C3-SAFE-R`: uniform physical-ID draw from the full-window hard-safe support
  before strict load, complete power, useful-bits, surplus, and release
  certification;
- `C3-LOAD-R`: uniform physical-ID draw from strict-load support before the
  complete-power, useful-bits, surplus, and release safeguards;
- `C3-CERT-R`: uniform physical-ID draw from the identical final certified
  support; and
- `C3-GAP`: inside that identical final certified support, maximize only the
  cumulative direct-objective load gap
  `sum_{t=0}^{2}(U_src^M(t)-U_dst^M(t))`, then use a frozen physical-ID tie
  order.

`C3-GAP` must not use power relief, energy saving, useful-bit margin, EE-surplus
magnitude, link margin, or service margin as a tie-breaker. This is a deliberate
V3 correction to the historical V2 core. `C3-CERT-R` and `C3-GAP` have exactly
the same membership; they differ only in uniform choice versus a declared
non-learning canonical-`r_3` construction ranking.

For a fixed anchor, the source-load term is common across destinations, so
maximizing `C3-GAP` is exactly the same within-window ordering as maximizing the
canonical system-`r_3` relocation gain. A later `C3-I` can beat `C3-GAP` on the
direct endpoint only through extended or episode-total canonical `r_3` after
the certificate window. Any matched pilot must freeze that endpoint, its
margin, and a minimum count of multi-choice certified anchors before outcomes.

Random controls require separate, closure-bound RNG objects and namespaces in
any future runner. No namespace or seed value is opened here, and no outcome
may trigger redraw, deletion, or support change.

`C3-I` is absent from Stage-0. No `Q_3^F` is instantiated, trained, queried, or
simulated by hand-written ranking. A later learned C3 would have to rank only
inside the identical certified set, learn only unchanged canonical `r_3`, and
beat both `C3-CERT-R` and `C3-GAP` under a separately authorized matched pilot.
This specification does not authorize that pilot.

## 11. Observational-alias and dual specialist/consumer gate

C3 constructs support from current post-feasibility
`eligible_load_by_beam`. The current specialist and Main state surfaces expose
lagged/ungated demand, which can alias states that require different C3 support
decisions. Therefore even perfect Stage-0 support leaves C3 shadow-only and
does not establish that `Q_3^F` can learn the ordering.

Before any bundle is routed or any nonzero C3 donor dose exists, a separate
gate must prove at least:

1. the exact executed decision-relevant C3 distinction is observable to the
   specialist `Q_3^F` at selection and TD time, or a preregistered state
   revision resolves the specialist alias;
2. the same distinction is observable to the Main `Q_3^M` consumer at the
   time it must act, or a preregistered state revision resolves the Main alias;
3. the complete atomic bundle retains the unmodified canonical reward vector,
   physical action, masks, source age, and behavior provenance;
4. C3 donor loss can affect only the matching Main `Q_3^M`, with non-target
   objectives audited under `no_grad` and no sequential double-step;
5. zero C3 dose is byte-exact with canonical Main for parameters, optimizer,
   replay, and RNG state;
6. focal-versus-atomic credit, off-support, duplicate, and scalarized action-
   pivotality guards pass; and
7. Main-only deployment still uses the exact `(0.5,0.3,0.2)` scalarization.

Until both gates pass, effective `beta_3=0`, no C3 bundle enters Main replay,
and no Stage-0 observation can be described as learned specialist value or Main
transfer. If either alias gate fails, the remedy is a new matched,
preregistered observability design—not training or routing C3 anyway.

## 12. Required deterministic fixtures

Before any support census, focused deterministic tests must prove at least:

1. a fixture where Q1-only and `(0.5,0.3,0.2)` rankings differ selects the
   scalarized-Main physical action; weight drift fails before inference;
2. candidate-table reordering preserves physical-ID remapping, while duplicate
   or malformed physical IDs fail closed;
3. one same-satellite relocation plus three declared holds and first release is
   accepted; a cross-satellite move, inactive destination, second relocation,
   redraw, hidden fallback, expiry, or short release window is rejected;
4. one changed non-focal physical action rejects the candidate even when table
   indices, counts, or aggregate metrics match;
5. independently reconstructed reference/candidate loads differ by exact
   source `-1` and destination `+1`, meet the integer `+2` guard, reproduce
   `-sum_b U_b^2`, and match the exact one-user canonical-`r_3` delta; every
   off-by-one, lagged-demand substitution, or reward rewrite fails;
6. full-window active-beam, active-satellite, served-user, service, event, and
   preview/commit identities pass positively and fail under one injected
   mismatch;
7. complete power reconstruction covers recurrence, per-beam max, PA
   efficiency/supply, circuit, and once-per-active-satellite baseband terms;
   it catches payload-only, fixed-only, beam-count, and superseded per-link PA
   totals;
8. per-offset complete system-power nonincrease passes, including equality-only
   at this layer; a release-interval increase, non-finite power, or non-positive
   accumulated energy fails, and an equality-only window must later obtain its
   strict EE surplus from useful bits;
9. system-total canonical `r_3` is strict over the hold and remains strict
   through first release; a focal win with system loss, delayed erasure,
   omitted release row, outage, re-entry, served-to-unserved transition, or
   undeclared event fails;
10. useful-bits equality can pass with strict positive surplus, while useful-
    bits loss, zero/non-finite energy, zero/negative surplus, epsilon
    denominators, or tolerance shortcuts fail;
11. row-order permutation leaves SAFE/LOAD/CERT membership unchanged;
    `C3-CERT-R` and `C3-GAP` use identical final support, proxy magnitudes never
    rank, each random control uses exactly its declared layer, and `C3-I`
    cannot be constructed;
12. eligible-load versus lagged-demand observational aliases remain separately
    visible for specialist and Main in the receipt and neither can be silently
    declared safe;
13. support-floor aggregation requires exact coverage of all 150 scheduled
    rows, at least one two-choice anchor in each partition, and at least 20
    pooled, without imputation;
14. anchor/twin field equality, fingerprinting, complete four-offset receipt,
    and deterministic repeatability fail closed under injected drift; and
15. import/call guards prove that no learner, optimizer, replay mutation,
    checkpoint update, operational seed manifest, outcome reader, or Main
    routing path ran.

Fixture inputs and expected receipts must be hash-bound in a later engineering
closure. Fixture pass means engineering semantics only, not opportunity
frequency, learning, efficacy, or scientific acceptance.

## 13. Prospective receipt contract

Every future V3 anchor receipt must include:

- V3 schema/status, exact authority/source hashes, current revision and dirty
  state, dependency versions, constants, and overwrite refusal;
- scalarized weights, policy mode, valid-action Q rows, masks, selected table
  indices and physical IDs, checkpoint identity, and prefix identity;
- the full anchor fingerprint object and digest, twin field equality, distinct
  object identities, fading-disabled proof, and any later closure-bound RNG
  lineage without exposing unrelated outcome namespaces;
- source/destination grammar, same-satellite and already-active facts,
  physical-ID remapping at every offset, and first failure offset/reason;
- independently computed non-focal scalarized-Main scripts for both forks,
  executed physical scripts, service/event/active-set identities, and
  preview/commit parity;
- reference/candidate eligible-load maps, served-user reconstruction, exact
  squared-load totals, canonical per-user reward vectors, per-offset one-user
  deltas, hold sums, first-release rows, and full-window system totals;
- the complete canonical power ledger and independent component identity,
  per-offset `P^N`, complete joules, useful bits, `eta^M`, EE surplus, and the
  binary safeguard decisions;
- membership and exclusion at every certificate layer, exact control support,
  uniform-draw provenance when later authorized, `C3-GAP` direct load-gap
  inputs, and proof that proxy magnitude did not rank; and
- explicit `C3-I absent`, `beta_3=0`, `no training`, `no outcome`,
  `specialist alias gate unresolved/passed`, and `Main consumer gate
  unresolved/passed` fields.

Every scheduled row must remain present, including reconstruction failure,
nonqualifying Main action, zero candidates, and every certificate exclusion.
A partial future output is a failure receipt and cannot be combined with a
later rerun. No existing output path may be overwritten.

## 14. Implementation delta and historical-file map

V3 must be added beside, not patched into, the historical surfaces.

| Surface | V3 disposition |
|---|---|
| `.scratch/catfish-design-data/C3-REWARD-ALIGNED-STAGE0-SPEC-V2-2026-08-27.md` | Preserve as historical. Its outcome/seed/directional gate is not V3 evidence. |
| `.scratch/catfish-stage0/c3_reward_aligned_core.py` | Preserve as historical V2 core. Its physical/load helpers are inventory only; its power-relief `C3-GAP` tie-break, RNG selection, outcome aggregation, and Stage-0 decision are not V3 authority. |
| `.scratch/catfish-stage0/run_c3_stage0.py` | Preserve as historical adapter. Its Q1-only `_main_actions()`, power-primary schema, old arms, seed/closure behavior, and outcome execution cannot run V3. |
| `.scratch/catfish-stage0/test_c3_reward_aligned_core.py` and `test_run_c3_stage0.py` | Preserve. Passing historical tests cannot close V3. |
| new V3 pure core and focused tests | Implement only physical grammar, exact load/reward identities, complete-power identity, release/service/proxy guards, layered support, and controls. Import no learner, replay, outcome, or historical selector/aggregate. |
| new V3 canonical environment adapter and integration tests | Future separate review. It must use exact scalarized Main, common-anchor forks, canonical reward/power/service outcomes, full receipts, and no-overwrite behavior. It may reuse only explicitly allowlisted mechanical helpers with equivalence tests and closure hashes. |
| canonical power diagnostic | If required terms are unavailable, add a read-only structured ledger in the canonical environment under separate reviewed implementation authority; do not create a scratch physics model. |
| V3 freezer, manifest, census, or result | Absent and unauthorized. No schedule, seed, outcome, or training manifest may be created from this document. |

The future implementation review must assign concrete new V3 filenames and an
explicit helper allowlist before code is written. It must not monkey-patch a
historical module's Main policy, selector, schema, seed namespace, or
scientific decision.

## 15. Stop rules

Stop before any census and report engineering failure if:

- authority, Main weights, masks, physical-ID identity, horizon, twin,
  fingerprint, preview/commit, or non-focal physical identity drifts;
- Q1-only selection or a candidate-specific scalarization is observed;
- a destination is cross-satellite, not already active, not strictly lower
  load, multiply represented, invalid, unserved, redrawn, or hidden behind a
  fallback;
- eligible-load reconstruction, squared-load identity, exact one-user delta,
  unchanged canonical reward vectors, hold strictness, or through-release
  strictness fails;
- complete power omits recurrence, PA, circuit, or baseband terms, disagrees
  with the canonical ledger, is non-finite/non-positive, or violates the
  per-offset safeguard;
- useful bits, energy, surplus, service, event, active-set, or full-window
  receipt guards fail;
- a proxy magnitude affects ordering, tie-breaking, reward, TD, replay,
  checkpoint choice, probability, or post-outcome admission;
- either the specialist-observability or Main-consumer alias gate is bypassed,
  or effective `beta_3` becomes nonzero;
- a historical file/output would be overwritten or relabelled; or
- any outcome, seed manifest, training, learner, optimizer, replay mutation,
  checkpoint update, or Main routing path is opened.

There is no post-outcome rescue. Any future outcome-bearing version must freeze
its horizon, candidate grammar, strict identity, complete-power terms, proxy
inequalities, service/event guards, controls, support floor, schedule, and
disjoint seed set before opening an outcome. A failure requires a new version,
closure, and wholly fresh authority; the failed receipt remains disclosed.

## 16. Allowed claims and current decision

Before implementation, the only allowed claim is that V3 is a prospective,
falsifiable engineering specification aligned to the named acceptance
contract.

After deterministic fixtures pass, one may claim only that the declared V3
engineering semantics pass those fixtures. A separately authorized support
census could additionally report the prospectively frozen support frequency,
but it would still be pre-outcome mechanism evidence.

One may not claim C3 learning, realised `r_3` improvement, Main transfer,
stochastic useful-bits non-degradation, power or EE efficacy, Main-only EE
improvement, singleton acceptance, three-positive Catfish success, training
readiness, effectiveness, or novelty. `C3-I` remains absent, C3 remains
shadow-only, effective `beta_3=0`, and formal training remains **NO-GO**.
