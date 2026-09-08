# Slice D — Service, QoS, Actions, Masks, Candidates, Handover, and Dwell Audit

## Bottom line

`served` is not a QoS measure. It is a Boolean user-step indicator meaning: a legal action was selected and its nominal recurrence-derived transmit power did not exceed \(p_{\max}\). It is evaluated before realized SINR and rate, has no minimum-rate requirement, and ignores admission, capacity, delay, and reliability.

The near-universal 100/100 service result is therefore largely constructed by the action contract and the handover reset: masks usually offer many actions, and every newly selected physical association restarts at \(p_0=0.825\text{ W}<p_{\max}\). This makes movement a route around continuing-segment power infeasibility. Consequently, the 0.001 service margin is not a meaningful QoS guard.

## Ranked summary

| Rank | Assumption | Evidence | Standard/literature comparison | Likely distortion | Magnitude | Verdict |
|---:|---|---|---|---|---|---|
| 1 | `served` represents delivered service/QoS | `service.py:21-31,40-50,222-251,289-301`; `step.py:958-971`; `test_w17_step_environment.py:196-205,754-789` | 3GPP QoS includes rate, delay, error rate, priority, and averaging-window properties—not merely power feasibility ([ETSI TS 23.501](https://www.etsi.org/deliver/etsi_TS/123500_123599/123501/18.05.00_60/ts_123501v180500p.pdf)) | Makes availability look perfect while arbitrarily low rates count as service | Potentially order-one; observed throughput can fall 5.3% with unchanged 100% service | **FIX** |
| 2 | Handover reset is neutral to service availability | `step.py:770-862`; `test_w17_step_environment.py:482-516`; `test_w07_r3_and_feasibility.py:70-78` | A mobility event should preserve service subject to measured interruption/QoS, not manufacture fresh link feasibility ([ITU-T Y.3204](https://www.itu.int/epublications/en/publication/itu-t-y-3204-2023-09-fixed-mobile-and-satellite-convergence-service-continuity-for-imt-2020-networks-and-beyond/en)) | Staying can cause outage; moving resets power to a guaranteed-feasible value | Structural, potentially dominant | **FIX** |
| 3 | \(\Phi_1=0.5,\Phi_2=1.0\) and the event classes represent physical handover cost | `action_contract.py:398-456`; `R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md:53-86,116-145,173-209` | Beam switching can be lower-layer mobility and need not be an RRC cell handover ([ETSI TS 38.300](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/18.01.00_60/ts_138300v180100p.pdf)) | Arbitrary penalties can dominate physical interruption costs and conflate re-entry with handover | Document estimates interruption at only about 0.1–0.5% of a 30.08 s step | **FIX** |
| 4 | Candidate masks express coordination/resource feasibility | `candidates.py:15-24,51-57,165-201,271-368`; `action_contract.py:326-369`; `R3-AND-EXECUTION-MASK-NOTES.md:96-155` | A visibility shortlist is reasonable, but it is not admission control or QoS feasibility | Masks are often almost fully open, while frozen top-four identities can exclude the one useful satellite | Live check: initially 28/28 actions per user; later minima 21/28 | **SENSITIVITY** |
| 5 | The 0.001 service margin protects performance | successor declaration `:101-130`; physical runner `:940-987`; result JSON `artifacts/multi-catfish-c3-astra-pro-review-20260905-r1/evidence/02-v020-repriced-c3-result.json:1` | A guard should measure the requirement it claims to protect | Permits material throughput loss while the guard remains exactly satisfied | 0.001 equals one failed user-step per 1000; artifact shows about −5.32% bits with 100% service | **FIX** |
| 6 | \(N=4\) is a handover dwell constraint | `dwell.py:41-85,92-104,156-220`; `test_w05_dwell.py:49-117` | A dwell/minimum-residence rule constrains switching; this implementation constrains candidate/anchor refresh | Does not prevent per-step handovers; can instead hide new candidates or cause boundary rekeys | \(4\times30.08=120.32\) s, not 4 or 40 s | **FIX** |
| 7 | Empty-mask/no-op behavior is consistent between training and evaluation | `action_contract.py:71-89,574-608`; `test_w16_no_op_action.py:35-90`; physical runner `:1240-1301`; `runtime/outage_gate.py:10-25` | Fail-closed behavior is valid only if consistently represented in trajectories and metrics | Base environment records no-op, legacy training can drop it, successor evaluation aborts | Unknown frequency; catastrophic contract mismatch when encountered | **FIX** |
| 8 | Training and deployment use equivalent mask information | heterogeneous trainer `:224-353`; `ee_axis_two_route_model.py:136-157,275-320`; physical runner `:1006-1073` | Legal-action masking should be consistent and tested under deployment mask distributions | C1 only validates sampled legality; C2 conditions on the mask; deployment uses current masks | Unknown without mask-pattern shift tests | **SENSITIVITY** |
| 9 | `ALL_NEUTRAL_CONTROL` and `BASELINE` are interchangeable controls | V0.3 algorithm spec `:237-252`; successor declaration `:34-58,101-130` | Distinct training controls and external baselines should remain distinct | Conflation would invalidate causal interpretation | Interpretive rather than numerical | **KEEP** |

## Findings and known-answer tests

### 1. Exact meaning of `served`

`resolve_service()` receives actions, slot tables, and `link_infeasible`; it does not receive realized SINR or rate (`service.py:185-251`). A user is served when the action is valid and the recurrence-derived transmit power is within its ceiling. Realized SINR and Shannon rate are calculated only afterward (`step.py:958-971`).

Thus `served` means **nominal power-feasible association for one user-step**. It is neither:

- a minimum-rate predicate;
- a realized-SINR predicate;
- an admission/capacity predicate;
- a service-continuity or latency predicate.

The deleted `required_sinr()` explicitly confirms that the former 1 Mbps floor is no longer live (`service.py:289-301`).

**Known-answer test:** Give a valid action with \(p\le p_{\max}\), then force realized SINR to \(10^{-12}\). Current expected result: `served=True` and a tiny positive Shannon rate. A QoS-service predicate with a 1 Mbps requirement must return false.

### 2. Why service saturates at 100/100

Four mechanisms make saturation likely:

1. A no-op is illegal whenever any action is available (`action_contract.py:574-608`).
2. Candidate masks commonly contain 21–28 valid actions per user.
3. A new association starts at \(p_0\), which is below \(p_{\max}\) (`step.py:770-822`).
4. No minimum realized rate must be met.

A read-only 100-user, 10-step check produced 100 served at every step under a stay-if-possible policy. Under random masked actions, 61 outages occurred at the episode warm start, followed by 900/900 served user-steps. This is consistent with mobility resets curing the only live service gate.

The existing artifact is even more decisive: both policies report full service, while total bits change from \(114.27\times10^{12}\) to \(108.19\times10^{12}\), approximately −5.32% (`02-v020-repriced-c3-result.json:1`).

**Known-answer test:** Compare two fixed trajectories with equal valid-action and power-feasibility flags but realized rates of 10 Mbps and 1 bit/s. Current service scores must be identical. Any claim that the score measures delivered QoS is thereby falsified.

### 3. The 0.001 service margin

The physical evaluation pools 100 users over 10 steps, so an episode contains 1000 service opportunities. A 0.001 margin permits an average of one extra failure per episode.

More importantly, the margin is applied to the wrong variable: it guards nominal association feasibility rather than rate, carried traffic, or continuity. It cannot detect the observed 5.3% throughput reduction.

**Known-answer test:** Set baseline and treatment service counts to 1000/1000, but reduce every treatment rate by 20%. The current service guard passes exactly. A valid QoS guard must detect the degradation through preregistered rate/traffic/availability criteria.

### 4. Candidate sets and coordination

Each user receives four satellite identities and seven local cell positions. Eligibility is occupancy plus satellite and cell visibility at a 0° horizon (`candidates.py:15-24,51-57,341-368`). The mask excludes recurrence power feasibility, realized interference, beam capacity, satellite capacity, admission, and minimum rate.

Therefore the mask does not solve coordination. Many users can select the same satellite or beam; every cell with positive eligible load activates, with no beam-count ceiling (`service.py:127-147`; `R3-AND-EXECUTION-MASK-NOTES.md:96-155`).

At the same time, frozen top-four identities can make useful coordination impossible: a newly eligible fifth satellite cannot enter until a dwell boundary, while cached identities that become ineligible are simply masked (`candidates.py:271-338`).

The comment that link feasibility “can only narrow the mask” is misleading (`candidates.py:15-24`): live power infeasibility does not narrow the decision mask; it turns the already-selected action into outage.

**Known-answer test:** Construct five geometrically eligible satellites. Cache satellites 1–4, then make all four ineligible while satellite 5 remains eligible. Before the boundary, expect an empty mask/no-op; at the boundary, expect satellite 5 to appear. Report this candidate-recall loss separately from physical unavailability.

### 5. Dwell \(N=4\)

The implementation refreshes the earth-fixed cell anchor and frozen satellite identities every four decision steps (`dwell.py:92-104,156-203`). It does not impose minimum residence on the selected association: a controller may choose a different valid satellite or cell on every intervening step.

Conversely, it can temporarily forbid movement to a newly eligible satellite outside the cached four. A boundary rekey may also change cell identity without a policy-requested move, producing both a \(\Phi_1\) event and a fresh \(p_0\) segment.

The time interpretation is inconsistent. The live decision interval is 30.08 s, so \(N=4\) means 120.32 s. `dwell.py:206-220` defaults to a 1 s step, while tests and older documentation discuss 10 s movement (`test_w05_dwell.py:109-117`; `LINK-BUDGET-NOTES.md:185-201`).

**Known-answer test:** With both associations valid, select A at step 0 and B at step 1 under \(N=4\). The switch should be accepted, proving \(N\) is not minimum residence. Separately, cross the boundary at step 4 and verify whether an anchor-induced cell change resets power and charges \(\Phi_1\).

### 6. Handover classes and hidden free events

The ledger uses realized physical identity `(NORAD, cell)`:

- episode start: free;
- previously unserved to served: \(\Phi_2\), even for the same identity;
- same satellite, different cell: \(\Phi_1\);
- different satellite: \(\Phi_2\);
- same satellite and cell: free;
- current outage: free until any later re-entry (`action_contract.py:421-456`).

This is internally deterministic but not physically closed. The project’s own provenance review states that same-satellite beam changes need not be cell handovers, re-entry is not automatically a successful handover, and the \(\Phi\) mapping remains `NOT_CLOSED` (`R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md:116-145,173-209`).

A renewal to the same beam is **not** an explicit action. Selecting the same `(NORAD, cell)` continues the segment, irrespective of action-index changes. Renewal requires leaving and returning, suffering an outage, or a boundary rekey that changes physical identity.

The central asymmetry is:

- staying may increase \(p\) until outage;
- moving starts at \(p_0\);
- an outage drops the old segment;
- re-entry starts another \(p_0\) segment.

Thus neither stay nor move is universally free: same-association stay is free of \(\Phi\) but exposed to accumulated power; movement pays \(\Phi\) in training but buys a power reset; terminal outage can avoid the later re-entry penalty.

**Known-answer test:** Let continuing association A require \(2.0\) W and new association B start at \(0.825\) W, with \(p_{\max}=1.65\) W. Current behavior must make A unserved and B served. That proves the action class itself alters feasibility, independently of realized channel quality.

### 7. No-op and training/deployment masks

The environment admits `NO_OP=-1` only for an empty row and marks it unserved (`action_contract.py:71-89`). The successor physical runner instead rejects any empty mask before policy execution (`physical_runner.py:1240-1301`). Legacy outage handling can also omit no-op/all-invalid transitions from replay, effectively making the dark interval absent from the learned return (`runtime/outage_gate.py:10-25`).

Legal-action semantics are otherwise broadly aligned, but learner exposure differs:

- C1 validates stored masks and sampled pairs but its forward model is not mask-conditioned.
- C2 consumes mask-dependent action-set summaries.
- Deployment chooses masked \(Q_1+Q_2\) using the current mask.

**Known-answer test:** Feed an all-false mask. The base environment should select no-op and record an unserved opportunity. The training data path and physical runner must do the same, rather than dropping the transition or aborting. Then repeat with rare mask patterns absent from training to measure deployment shift.

### 8. `ALL_NEUTRAL_CONTROL` and `BASELINE`

The old `ALL_NEUTRAL_CONTROL`/N000 arm is a retrained learner with neutral source labels. It is a pairwise-learning control, not the external MODQN baseline (`MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC.md:237-252`).

The current successor removes all-neutral training and evaluates:

- `FULL2`;
- `DROP_C1`;
- `DROP_C2`;
- external authenticated `BASELINE`.

That separation is correct and should be retained. `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md:61-72,188-195` is stale relative to the September 7 successor declaration and should not be treated as current authority.

**Known-answer test:** Inspect model provenance for every arm. `BASELINE` must resolve to the external pre-Catfish policy; no successor checkpoint may be relabeled `ALL_NEUTRAL_CONTROL`. A neutral-source retraining, if restored, must remain a fifth and separately named arm.

## Code–documentation disagreements

- `ServiceResolution.served` still mentions surviving an “execution mask” (`service.py:100-101`), although that mask was deleted and the live gate is post-selection power feasibility.
- `action_contract.py:326-334` describes `cell_reachable` as including link feasibility; the live caller supplies geometric cell visibility only.
- `PREREG-DRAFT.md:223,257` retains a 1 Mbps/\(\gamma_{\rm req}\) QoS floor, while live code explicitly deletes that contract.
- Dwell documentation reasons in 1 s or 10 s increments, while the live control interval is 30.08 s.
- The document named `CURRENT-MULTI-CATFISH-AUTHORITY.md` describes an obsolete three-surface design; the successor has two Catfish heads and no all-neutral arm.

## The three assumptions I would overturn first

1. **Overturn “served = service/QoS.”** Rename it to `power_feasible_association` and separately preregister a delivered-service endpoint based on rate/traffic and continuity.
2. **Overturn “handover reset is neutral.”** Remove the automatic \(p_0\) feasibility benefit from the service contract or evaluate it as an explicit experimental sensitivity; otherwise mobility manufactures availability.
3. **Overturn “\(\Phi_1/\Phi_2\) are physically meaningful handover costs.”** Replace the identity-based constants with declared interruption/energy events—or retain them only as openly synthetic regularization arms.