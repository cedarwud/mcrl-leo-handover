# Integration verification report

Date: 2026-09-02  
Scope: read-only receipt/formula verification and package assembly  
Outcome: VERIFIED_WITH_MATERIAL_OPS3_NAMING_DISCREPANCY

No simulator, learner, training run, replay write, or TEST split was opened for
this integration.

## 1. Receipt integrity — verified fact

Running sha256sum against the original challenger receipt manifest verified all
25 listed files.

The following hashes were independently recomputed:

| Item | SHA-256 | Result |
|---|---|---|
| H-A Stage 1b contract | 2ac39ce557ed23596728d9a83619ce585c9c30e308559bd20f48d08c0e6d1545 | match |
| OPS-3 addendum | b538932006f7e597ee199fb0701a4473587afa81b4580ca76e1dff13f9ea7046 | match |
| Fable decision document | 3f0dc93ffc56a5ef9dd517451a990618f72815e879d4c23067c181e11795cd80 | match |

The challenger itself records failed strict source closure because the current
source tree differs from the sealed V0.4 source manifest. Its results therefore
remain development evidence even though their internal receipt manifest is
complete.

## 2. Independent number recomputation — verified fact

verification/recompute_stage1b.py reads the raw episode rows embedded in the
two packaged result JSON files. It independently:

1. pools each arm as sum(total_bits) / sum(total_energy_j);
2. pools served fraction from raw served-user-step and decision counts;
3. repeats the calculations by initialization lineage;
4. checks every pool against both summaries.pooled_by_arm and
   summaries.pooled_by_arm_and_initialization;
5. recomputes the six primary contrasts.

All checks pass:

| Direction | Pooled | Per initialization |
|---|---:|---:|
| H-A C2: P123/P13 | +11.699953% | +12.492141 / +10.670394 / +12.001460 |
| H-A C3: P123/P12 | -0.484836% | -0.709544 / -0.254835 / -0.488636 |
| H-A C1: P123/P23 | +0.644142% | +0.322195 / +0.946865 / +0.665748 |
| Fable OPS-3 reading C2: O123/P13 | +9.479997% | +9.823131 / +8.478158 / +10.195031 |
| Fable OPS-3 reading C3: O123/O12 | -2.687311% | -3.355799 / -2.072760 / -2.637507 |
| Fable OPS-3 reading C1: O123/O23 | +5.891632% | +5.180581 / +6.284121 / +6.207623 |

Important provenance detail: the OPS-3 result JSON contains only O2, O12, O23,
and O123 rows. The shared P13 comparator for its C2 direction comes from the
H-A result block, whose initial worlds and keyed-field identities were reported
equal across all six seeds.

No arithmetic discrepancy was found.

## 3. OPS-3 formula cross-check — verified fact

The addendum explicitly calls its formula the controller's reading of OPS-3.
Inspection of the sealed challenger runner confirms that it is not the current
exact OPS-3 implementation:

| Dimension | Fable lane runner | Current exact OPS-3 |
|---|---|---|
| Future clock/D2 | satellite_ecef_at(offset) at decision offsets | cloned native D2 tracker, 47 x 0.640-s updates per future decision |
| D2 eligibility | omitted | projected native D2 eligibility required |
| Visibility | focal-user elevation above 0 degrees | satellite-to-physical-cell-centre visibility |
| Persistence | independent chi_k at each offset | absorbing product; no recovery after first loss |
| Interference | decision-time I+N obtained by gamma inversion and frozen | reconstructed frozen served background projected with TLE geometry |
| Decision interval | decimal 30.08 convention supplied by runner | exact canonical 47 x 0.64 clock |
| Gauge | reference subtraction omitted from deployed surface | exact Main-reference subtraction and zero reference row |
| Background integrity | reconstructs from _last_outcome | validates committed associations, segments, and last served link powers; fails closed |

The gauge omission is action-argmax invariant. The D2, visibility,
persistence, interference, clock, and state-validation differences can change
the score ordering, selected actions, or physical outcome. Therefore:

> The O-arm result is validly described as the **Fable lane's OPS-3 reading**.
> It is not a result from source/runtime/ee_axis_ops3_live.py.

The current exact OPS-3 formula/live adapter has mechanics-test evidence but no
opened oracle outcome in this package.

## 4. Evidence interpretation

### Verified facts

- Both challenger formulas have a positive C2 marginal in all three lineages
  and all six TRAIN worlds.
- C1 remains positive in both new-Q2 oracle contexts.
- Frozen C3 is negative in all three lineages in both new-Q2 contexts.
- Both routes mechanically return C3_CONTEXT_FAIL; both overall service guards
  fail.
- The H-A census shows an observable action-specific segment-timing mechanism.

### Inference

The evidence narrows rather than solves the method problem. It materially
supports the existence of a useful deterministic projected-persistence C2
direction, but it makes C3 complementarity the immediate three-head blocker.
It does not prove that a learned Q2 can reproduce the oracle ordering or that
either C2 will pass held-out evaluation.

### Proposals, not applied

After independent adjudication, the following challenger patch-plan items are
reasonable candidates for shared-authority updates:

1. record H-A's positive C2 direction and C3_CONTEXT_FAIL, while retaining
   NO_C2_SELECTED and no-learner status;
2. correct the lambda0 calibration-policy prose without recomputing lambda0;
3. surface the already implied Q2-free C3 marginal of -10.286% in the route
   interaction document;
4. mark the stale link-budget docstring that calls the feasibility gate
   non-binding;
5. remove retired motion-one C2 from presentation/figure authority.

None of these shared files was modified by this package integration.

## 5. Claim ceiling

All Stage 1/1b signs are fail-fast development evidence from six TRAIN worlds
and oracle Q2 surfaces. They are not learned-Q2 efficacy, held-out
confirmation, a Chapter 5 result, or authorization for long episode training.
