# C2 activation-churn Stage-0 specification — scalarized Main V3

Date: 2026-08-28  
Status: prospective, non-training shadow/census specification; **formal
training remains NO-GO**

## 1. Decision and authority

This document specifies the first implementable Stage-0 gate for the
**Activation-Churn-Aware Temporal-Continuity C2** adopted by:

1. `docs/THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.1-2026-08-28.md`;
2. `docs/THREE-CATFISH-EE-POSITIVE-CROSS-MODEL-ADJUDICATION-2026-08-28.md`;
3. the canonical runtime power, service, handover, and Main-policy code named
   in section 14; and
4. this V3 specification for the bounded Stage-0 implementation details.

If these surfaces disagree, the acceptance contract and adjudication control
the scientific meaning, the canonical runtime controls executable physics and
rewards, and this document must be revised under a new version before any
census is run. A runner must never silently resolve a conflict.

The historical V2 candidate remains unchanged at
`.scratch/catfish-design-data/C2-PERSISTENCE-SCALARIZED-STAGE0-CANDIDATE-SPEC-V2-2026-08-28.md`
(draft-time SHA-256
`a9e6ca763264c07d5079e2b989007b869fecb6520d0ae9a28ddb53071b835cd7`).
Its runners, manifests, tests, and outputs remain historical. They are not V3
evidence and must not be edited, re-hashed as V3, or executed with V3 inputs.

This V3 gate may implement deterministic fixtures and a pre-outcome support
census. It performs no optimizer step, replay insertion, TD update, checkpoint
selection, specialist training, Main routing, stochastic efficacy evaluation,
or formal seed reveal. Effective C2 dose remains zero.

## 2. Question and claim type

The Stage-0 question is deliberately narrower than an efficacy question:

> At frozen scalarized-Main temporal boundaries, does the canonical simulator
> expose enough physical-ID stay or one-relocation-and-hold choices that avoid
> a short-lived activation or reduce complete system energy, while strictly
> improving system-total canonical `r_2` through first release and passing
> pre-outcome useful-bits and EE-surplus safeguards?

A positive answer identifies **certified, rankable support for a future C2
learner**. It does not show that `Q_2^F` can learn a useful ordering, that its
bundles can influence scalarized Main, that realised fading preserves the
forecast sign, that Main-only EE improves, or that C2 is one of three
EE-positive Catfish roles.

## 3. Exact frozen Main reference

`M-REF` is the corrected Main checkpoint acting read-only and masked-greedily
on the exact deployed scalarized surface:

```text
Q_M^sc(s,a) = 0.5 Q_1^M(s,a) + 0.3 Q_2^M(s,a) + 0.2 Q_3^M(s,a).
```

The runner must call the checkpoint-backed equivalent of:

```python
encoded = trainer.encode_states(states)
q = trainer.scalarized_q_values(
    encoded, objective_weights=(0.5, 0.3, 0.2)
)
actions = masked_greedy_actions(q, masks)
```

It must first assert that `trainer.config.objective_weights` is exactly
`(0.5, 0.3, 0.2)`. There is no epsilon, policy RNG, Q1-only fallback,
candidate-specific weight row, reward re-scaling, or Catfish action at this
gate. The existing masked-greedy tie behavior is retained and the selected
physical ID, valid-action Q rows, masks, and candidate-table ordering are
receipted.

The no-option reference is recomputed independently from the common anchor.
It is not reconstructed by replacing a candidate's focal action after that
candidate has advanced state.

## 4. Frozen horizon and anchor

V3 freezes:

```text
HOLD_STEPS = 3
FIRST_RELEASE_OFFSET = 3
CERTIFICATE_OFFSETS = [0, 1, 2, 3]
```

Offsets `0..2` are the three executed hold intervals. At offset `3`, the
focal option is released and that branch's focal user again takes its exact
scalarized-Main action. The certificate includes all four intervals. An
episode with fewer than four remaining intervals is not an eligible anchor;
V3 does not shorten `H`, impute the missing release, or treat episode end as a
successful `off` transition.

An anchor is eligible for candidate construction only if:

- reset plus the frozen scalarized-Main physical-action prefix reproduces the
  complete mutable-state, observation, candidate-table, ledger, segment,
  previous-map, age-RNG, environment-RNG, and mobility-RNG fingerprint;
- the focal user has a physical incumbent `(norad_id, cell_id)` that was served
  immediately before offset `0`;
- `M-REF` leaves that incumbent at offset `0` for a distinct served physical
  association; and
- four full forecast intervals remain.

Every fork is a deep twin of the same anchor. Full field equality and the
fingerprint SHA-256 are both mandatory; digest equality alone is insufficient.

## 5. Physical-ID candidate grammar

A candidate is keyed only by the physical pair `(norad_id, cell_id)`. A
candidate-table index is never persistent identity. Duplicate actions mapping
to one physical pair fail the anchor rather than giving that pair extra weight.

Exactly two candidate forms exist:

1. **incumbent hold:** use the served incumbent at offsets `0..2`; or
2. **one declared relocation plus hold:** at offset `0`, relocate once to one
   declared non-incumbent physical pair and use that same pair at offsets
   `0..2`.

At offset `3`, both forms release to scalarized Main. No candidate may relocate
twice, redraw a physical ID, substitute a table index, use a hidden fallback,
or terminate early and still remain certified.

For every hold offset, the declared pair must remap uniquely, its action mask
must be valid, recurrence power must be finite and no greater than the
canonical per-link ceiling, and the focal user must be served on that pair.
The interval that first violates any condition is retained in the diagnostic
receipt and the candidate is excluded from certified support.

## 6. Common-anchor forecast and non-focal identity

The certificate is computed before any realised-outcome execution with fading
disabled in every fork. Forecast environment and mobility RNGs use separate,
V3-specific domain-separated namespaces; neither may alias, copy, or consume a
future realised fading/mobility stream. All branches start with equal RNG-state
hashes but distinct generator objects. Any fading or shadowing draw is a
certificate failure.

For each offset, the runner must independently compute the scalarized-Main
physical action of every non-focal user in `M-REF` and in each candidate fork.
The candidate survives only if, for every non-focal user and every offset:

```text
physical_action_candidate == physical_action_M-REF.
```

Equality is on `NO_OP` or `(norad_id, cell_id)`, never on a table index. The
reference non-focal script is then the script executed in both forks, and it
must remain uniquely remappable and action-valid in each. Thus only the focal
physical action differs. If branch-local Main would choose another non-focal
physical action, the candidate fails rather than forcing that disagreement out
of the receipt.

Forecast preview and committed step results must be identical for physical
associations, service, handover classes, recurrence/link power, active sets,
rate, complete power, and canonical reward vectors. Every interval, including
a failed one, is archived.

## 7. Activation-churn and complete-energy certificate

### 7.1 Exact `off -> on -> off` identity

Active beams are the post-feasibility physical pairs in
`resolution.active_beams`. An active satellite is a NORAD ID with at least one
active beam. Let the pre-anchor state be offset `-1` and first release be
offset `3`.

A reference beam pulse exists only when one physical beam:

- is inactive in `M-REF` at `-1`;
- is active for one non-empty contiguous run wholly inside offsets `0..2`;
- is inactive again no later than offset `3`; and
- is inactive in the candidate fork at every offset `-1..3`.

A reference satellite pulse uses the identical identity after projecting the
active-beam set to NORAD IDs. A run that begins before the anchor, remains on
after first release, has a gap and reactivation, or is also activated by the
candidate is not the required pulse. The receipt records beam and satellite
pulses separately and does not double-count a satellite pulse as additional
scientific support.

### 7.2 Complete canonical power and energy

No beam-count, focal-link-power, fixed-power-only, or time-only surrogate may
certify C2. At each offset, both forks must execute the complete canonical
power chain already implemented by `src/mcrl/env/step.py` and
`src/mcrl/env/link_budget.py`:

```text
p_{u,s,v}(t) = p^0 G^T(theta(tau)) / G^T(theta(t))
p_{s,v}(t)   = max over served users of p_{u,s,v}(t)
xi_{s,v}(t)  = min{xi_max, xi_max sqrt(p_{s,v}(t)/p_sat)}
P^p_{s,v}(t) = p_{s,v}(t) / xi_{s,v}(t)
P^f(t)       = sum_s [N^act_s P_cir + 1{N^act_s>0} P_BB]
P^N(t)       = P^f(t) + sum over active beams P^p_{s,v}(t).
```

This includes circuit power, once-per-active-satellite baseband power,
per-beam PA supply power, and the physical-link recurrence state. The V3
receipt must expose, per interval, link recurrence inputs/output, beam max
power, PA efficiency and supply power, active-beam counts by satellite,
`P^f`, and `P^N`. It must independently recompute `P^N` from these components
and require relative agreement no worse than `1e-9`. The superseded per-link
PA charging form is diagnostic only and cannot enter any certificate.

Using the existing decision interval `30.08 s`, accumulated energy is the sum
of complete `P^N * 30.08` over offsets `0..3`. Both energies must be finite and
strictly positive.

### 7.3 Mechanism condition

A hard-safe candidate enters the activation-churn layer only if at least one
of these predeclared conditions is true:

- `M-REF` has the exact beam or satellite pulse above and the candidate avoids
  it; or
- complete accumulated reference energy is strictly greater than complete
  accumulated candidate energy.

The receipt records which condition passed. A resource pulse alone is not an
energy claim, and lower energy alone is not called an `off -> on -> off`
event.

## 8. Canonical `r_2`, release, and service certificate

The runner consumes the unmodified canonical reward matrix emitted by the
environment. It does not derive `r_2` from candidate IDs or an auxiliary event
counter. For each branch and offset it records every user's
`r_2 in {0, -varphi_1, -varphi_2}` and its handover class.

Through first release, a candidate must satisfy all of the following:

1. the sum of canonical `r_2` over **all users and hold offsets `0..2`** is
   strictly greater for the candidate than for `M-REF`;
2. the sum over **all users and all four offsets `0..3`** remains strictly
   greater after first release, so merely shifting the same event to offset
   `3` cannot pass;
3. the focal and system first-release event costs are reported separately. A
   release event is not automatically a failure when the full-window strict
   improvement survives, but it may not be omitted, relabelled as termination,
   or moved outside the certificate;
4. the focal user is served at every offset in both forks and has no outage or
   re-entry; and
5. no user served in `M-REF` at an offset becomes unserved in the candidate at
   that offset.

These are system-level direct-objective and loophole guards. A focal-only
`r_2` improvement is reported but cannot certify support. No positive pooled
mean, later recovery, or episode-total result can repair a failure inside the
four-interval certificate.

## 9. Binary useful-bits and EE-surplus proxies

For the same four fading-off intervals, use system useful bits and complete
system joules already defined by the acceptance contract:

```text
B^M = 30.08 * sum_t system_throughput_bps_M(t)
B^C = 30.08 * sum_t system_throughput_bps_C(t)
E^M = 30.08 * sum_t P^N_M(t)
E^C = 30.08 * sum_t P^N_C(t)
eta^M = B^M / E^M.
```

The candidate must pass both binary tests:

```text
B^C >= B^M
(B^C - B^M) - eta^M (E^C - E^M) > 0.
```

All four accumulations and the surplus must be finite, and `E^M>0` and
`E^C>0`. Zero energy, `0/0`, NaN, infinity, an epsilon denominator, or a
numerical floor fails closed. The useful-bits comparison has no tolerance or
hidden percentage allowance.

These are fading-off **screening proxies only**. Their output is one pass/fail
bit per candidate plus auditable raw terms. The surplus magnitude, useful-bit
margin, energy saving, activation count, link margin, physical-ID order, and
forecast `r_2` margin must not rank certified candidates, break a tie, become
a reward or TD label, change replay weight, select a checkpoint, or admit/drop
a later realised bundle. Permuting the certified candidate list must leave the
certified set unchanged.

## 10. Certificate layers and controls

The runner reports distinct denominators and exclusions at each layer:

1. scheduled anchor;
2. qualifying scalarized-Main departure anchor;
3. unique physical-ID candidate;
4. full-window hard-safe candidate;
5. non-focal-identity candidate;
6. activation-pulse or complete-energy candidate;
7. strict system-total canonical-`r_2` and no-delayed-event candidate;
8. service/useful-bits/positive-energy/EE-surplus candidate; and
9. certified choice.

The required control ladder is frozen as follows:

| Arm | Exact Stage-0 meaning |
|---|---|
| `M-REF` | Exact read-only masked-greedy scalarized Main with no focal option. |
| `C2-PERSIST-R` | Uniform physical-ID draw from the broader full-window hard-safe support before activation, energy, `r_2`, useful-bits, and surplus certification. |
| `C2-STAY` | Incumbent-hold form when it is full-window hard-safe; otherwise explicitly unsupported, with no trigger-time redraw. The later stochastic pilot must freeze scalarized-Main fallback on the interval after an observed termination; fallback never rescues or certifies the terminating interval. |
| `C2-CHURN-CERT-R` | Uniform physical-ID draw from the identical final certified set. |
| `C2-I` | **Absent from Stage-0.** Future learned `Q_2^F` ranking inside the identical certified set, learning only unchanged canonical `r_2`. |

Random controls use separately namespaced, closure-bound RNGs and never use a
proxy magnitude as a probability. `C2-PERSIST-R` diagnoses persistence plus
support screening; `C2-CHURN-CERT-R` is the later learned-ranking comparator.
Neither is evidence that `C2-I` exists.

`C2-I` cannot be instantiated until a separate training authorization,
role-targeted atomic-bundle carrier, Main-consumer isolation gate, and frozen
pilot protocol exist. At that later gate it must beat both
`C2-CHURN-CERT-R` and `C2-STAY` on first-release and episode-total canonical
`r_2`, and must pass the separate fresh-seed Main-only EE contract. Stage-0
does not simulate that result with a hand-written ranking.

## 11. Frozen support census

The V3 support census is non-outcome mechanism measurement. Its schedule and
census identifiers must be frozen in a closure-bound manifest before the
census runs, in a namespace distinct from every development, role-gate,
training, validation, and confirmatory seed namespace. This document contains
no census or future outcome seed values.

The schedule retains the V2 geometry budget but removes its structurally
ineligible reset row: five census partitions, anchor steps `1..6`, and five
focal users per step selected by a frozen deterministic permutation. Step `0`
cannot satisfy the required immediately-previous served incumbent and is not a
scientific opportunity denominator. All 150 scheduled anchor attempts are
reported; unsupported rows are never omitted or imputed as zero effect.

The Stage-0 support floor is fixed before the census:

- every one of the five census partitions contains at least one anchor with
  **at least two distinct certified physical-ID choices**;
- at least 20 such two-choice anchors exist in total; and
- every counted choice passes every layer in section 10 over the complete
  four-interval window.

The census also reports the full distribution of certified-choice counts,
incumbent versus relocation forms, beam-pulse versus satellite-pulse versus
energy-only mechanisms, all exclusion reasons, and overlap with C3-eligible
anchors. It must not select the most favorable partition, focal user, anchor,
or candidate.

Passing the floor yields only `C2_V3_STAGE0_SHADOW_READY`. Missing the floor is
`C2_V3_SUPPORT_FAIL`: C2 remains absent and effective `beta_2=0`. Rare support
is a mechanism failure, not a zero-effect efficacy result and not permission to
lower the floor.

## 12. Required deterministic fixtures

Before any support census, targeted tests must prove at least these cases:

1. a fixture where Q1-only and `(0.5,0.3,0.2)` rankings differ selects the
   scalarized-Main physical action, and weight drift fails before inference;
2. candidate-table reordering preserves physical-ID remapping, while duplicate
   physical IDs fail closed;
3. incumbent hold and exactly one relocation-plus-hold are accepted, while a
   second relocation, redraw, hidden fallback, early expiry, or short release
   window is rejected;
4. one changed non-focal physical action, even with equal table indices or
   equal aggregate metrics, rejects the candidate;
5. positive and negative beam and satellite `off -> on -> off` sequences cover
   pre-active, post-release-active, gapped, reactivated, and candidate-shared
   resources;
6. complete power reconstruction includes recurrence, beam max, PA efficiency,
   PA supply, circuit, and once-per-active-satellite baseband terms, and catches
   the superseded per-link PA sum;
7. strict system-total canonical `r_2` passes during the hold and remains
   strict through first release; a focal win with a system loss, a delayed-only
   event, an omitted release event, outage, re-entry, or served-to-unserved
   transition fails;
8. useful-bits equality is allowed, but zero/non-finite energy, negative or zero
   surplus, epsilon denominators, and proxy-tolerance shortcuts fail;
9. candidate-order permutation proves proxies are binary and cannot rank;
10. `C2-PERSIST-R`, `C2-STAY`, and `C2-CHURN-CERT-R` draw/use exactly their
    declared supports, while `C2-I` cannot be constructed;
11. support-floor aggregation requires at least one two-choice anchor in each
    partition and at least 20 total, never imputing unsupported anchors; and
12. anchor/twin fingerprint, RNG object/lineage separation, preview/commit
    parity, exact closure hashing, no-overwrite output, and deterministic
    repeatability all fail closed under injected drift.

Fixture inputs and expected receipts are hash-bound. Passing fixtures proves
engineering semantics only, not opportunity frequency or scientific effect.

## 13. Receipt contract

The immutable closure receipt must bind exact hashes for this specification,
the V3 core/runner/tests/freezer, both authority documents, V2 historical
inputs used as adapters, the corrected preregistration and Main checkpoint,
the canonical runtime source bundle, dependency versions, frozen TLE
inventory, census schedule, constants, RNG namespaces, and raw plus
duration-normalized test outputs. Authority drift invalidates the closure.

The support-census receipt must include:

- schema/status, closure hash, runner/test hashes, current revision and dirty
  state, runtime versions, census-manifest hash, and overwrite refusal;
- exact scalarized weights, policy mode, valid-action Q tables, masks, selected
  indices and physical IDs, checkpoint hash, and Main prefix hash;
- per-anchor full fingerprint object and hash, twin equality, RNG object and
  lineage receipts, and forecast-fading-disabled proof;
- candidate grammar/form, physical-ID remapping at every offset, hard-safe and
  service decisions, termination/exclusion reason, and non-focal physical
  scripts for both independently computed forks;
- pre-anchor and per-offset active beam/satellite sets, exact activation
  sequences, pulse resource IDs, and mechanism-condition result;
- per-user recurrence inputs/output, per-beam maximum RF power, PA efficiency
  and supply power, active counts by satellite, circuit/baseband/fixed power,
  complete `P^N`, independent power-identity result, useful bits, joules,
  `eta^M`, and EE surplus;
- all canonical reward vectors and handover classes, focal and system `r_2`
  sums, first-release event and service guards, and preview/commit equality;
- membership and exclusion at every support layer; declared control support,
  uniform-draw RNG receipt, and proof that no learned arm ran; and
- per-partition and pooled support denominators, two-choice-floor decisions,
  choice-count/mechanism distributions, every engineering failure, final
  decision, and the exact claim boundary.

Every scheduled anchor has one row, including reconstruction failure, no Main
departure, zero candidates, or certificate failure. A partial output is
written only as a failure receipt and cannot be aggregated with a later rerun.

## 14. Runner and test delta map

V3 must be added beside, not patched into, the historical surfaces.

| Surface | V3 action |
|---|---|
| `.scratch/catfish-stage0/run_c2_stage0.py` | Preserve. Its `_main_actions()` is Q1-only and its `C2-PRE` selector ranks by focal `r_2` then link margin; neither is V3 authority. Reuse only audited low-level anchor, physical-ID, RNG, and receipt helpers through explicit imports whose hashes are closure-bound. |
| `.scratch/catfish-stage0/run_c2_scalarized_stage0.py` | Preserve. It fixes scalarized Main but delegates the V2 support, selector, arms, and aggregate. It cannot serve as the V3 operational runner. |
| V2 specification, tests, freezer, manifests, outputs | Preserve byte-for-byte as historical evidence. No V3 seed or schema may be accepted by them. |
| new `.scratch/catfish-stage0/c2_activation_churn_core.py` | Implement pure candidate grammar, activation-sequence identity, complete-energy reconstruction checks, canonical-`r_2`/release/service guards, binary proxy guards, support layers, and floor aggregation. It must import no learner or replay implementation. |
| new `.scratch/catfish-stage0/run_c2_activation_churn_stage0.py` | Implement exact scalarized `M-REF`, common-anchor branch construction, non-focal identity, full forecast receipts, controls, and the 150-row support census. Refuse legacy/formal outcome seed manifests and existing output paths. |
| new `.scratch/catfish-stage0/test_c2_activation_churn_core.py` | Cover pure deterministic fixture items 2–11 above. |
| new `.scratch/catfish-stage0/test_run_c2_activation_churn_stage0.py` | Cover checkpoint policy, anchor/twin/RNG/preview integration, complete receipt, closure drift, no-training imports/calls, and no-overwrite behavior. |
| new `.scratch/catfish-stage0/freeze_c2_activation_churn_stage0.py` and test | Hash the reviewed V3 surfaces and tests, then create only the separate non-outcome census manifest. It must not derive or reveal training, validation, confirmatory, or outcome-bearing role-gate seeds. |

The V3 runner may use canonical `StepEnvironment` evaluation/step results, but
must not fork or duplicate power, service, handover, or reward semantics. If
the current public outcome lacks a required power component, add a read-only
canonical diagnostic receipt in the later implementation change and bind its
tests; do not reconstruct a second scientific model in the scratch runner.

No operational V3 runner may call the V2 `_select_pre()` or `_aggregate()` or
temporarily monkey-patch a historical module's scientific selector. Reusing a
mechanical helper does not import the old claim or seed namespace.

## 15. Stop rules and no-rescue rule

Stop before the census, or emit `C2_V3_ENGINEERING_FAIL`, if any of the
following occurs:

- an authority, checkpoint, preregistration, runtime-source, dependency, TLE,
  fixture, schedule, constant, or RNG-namespace hash drifts;
- Main weights/masks/policy are not exact, or Q1-only selection is observed;
- an anchor/twin/RNG/preview/commit/non-focal physical identity fails;
- the four-interval horizon or first-release interval is incomplete;
- a candidate uses a table index as identity, hidden fallback, repeated
  relocation, early termination, outcome-conditioned deletion, or incomplete
  interval receipt;
- power omits recurrence, PA, circuit, or baseband terms, violates the
  independent identity, or has non-finite/non-positive certificate energy;
- canonical reward vectors are unavailable or a locally reimplemented `r_2`
  disagrees with them;
- a proxy magnitude affects ranking, reward, TD, replay, admission after
  realised outcomes, checkpoint choice, or control probability;
- a legacy/output file would be overwritten, a historical seed/output would be
  relabelled, or a future outcome seed would be opened; or
- any training, optimizer, replay mutation, specialist/Main update, or Main
  routing path is invoked.

After a valid census, missing the frozen support floor stops at
`C2_V3_SUPPORT_FAIL`. Passing stops at `C2_V3_STAGE0_SHADOW_READY`. Neither
decision authorizes a pilot or training.

There is no post-outcome rescue. After any outcome-bearing seed or result is
opened in a later authorized version, `H`, release, activation identity,
energy terms, proxy inequalities, service guard, anchor floor, candidate
grammar, controls, dose, checkpoint, schedule, or seed set may not be relaxed,
retuned, or selectively replaced. A redesign requires a new spec version,
closure, namespace, preregistration, and wholly fresh disjoint seeds; the
failed version and all negative/partial receipts remain disclosed.

## 16. Allowed claims

Before implementation, the only claim is that this is a prospective,
falsifiable Stage-0 specification.

After deterministic fixtures pass, one may claim only that the V3 engineering
semantics pass those fixtures. After a support-census pass, one may additionally
claim that the frozen scalarized-Main census exposed the declared minimum of
two-choice, activation-churn-aware certified anchors under fading-off forecast
semantics.

One may not claim C2 learning, C2-to-Main transfer, realised or fresh-seed EE
improvement, stochastic non-degradation, singleton acceptance, three-positive
Catfish success, `C123` superiority, training readiness, effectiveness, or
novelty. Formal training remains **NO-GO** until separately authorized after
the carrier, evaluator, Main-consumer, opportunity, and preregistration gates.

## 17. Bounded implementation questions

These questions must be resolved during V3 implementation review, before the
closure is hashed. They do not permit changes to the certificate above:

1. `ActionEvaluation` currently exposes total and fixed power but not every PA
   component required by the V3 receipt. Should the canonical environment add
   one read-only structured power ledger, or should an existing canonical
   diagnostic object be extended? A scratch-only second power implementation
   is forbidden either way.
2. Which audited legacy helpers can be imported without importing V2 selector,
   aggregate, schema, or seed behavior? The implementation must list the exact
   helper allowlist and add equivalence tests; otherwise V3 should use a new
   standalone branch adapter over canonical `StepEnvironment`.
3. What closure-bound derivation and storage mechanism will create the five
   non-outcome census partitions while proving they are disjoint from all
   outcome-bearing namespaces? No value may be revealed until that mechanism
   and its repository-wide disjointness check are reviewed.
4. The future stochastic pilot's post-termination scalarized-Main fallback is
   outside this fading-off census. Its exact timing and receipt must be frozen
   in that later pilot specification; it cannot be inferred from a favorable
   outcome or used to alter V3 support.
