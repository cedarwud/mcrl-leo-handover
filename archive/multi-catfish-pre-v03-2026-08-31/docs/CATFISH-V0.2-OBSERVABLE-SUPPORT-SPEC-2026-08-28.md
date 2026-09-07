# Multi-Catfish MCRL V0.2 Observable-Support Specification

Status: **frozen candidate authority before support census or routed pilot**  
Date: 2026-08-28  
Public method name: **Multi-Catfish MCRL**  
Runtime support version: `V0.2_OBSERVABLE_ELIGIBILITY`

## 1. Scope and evidence ceiling

This document freezes the next executable three-role candidate. It supersedes
V0.1/V0.4 descriptions wherever they require per-anchor future rollout
certification, all-head donor transfer, or post-training coordination. It does
not change the canonical MODQN environment, action mask, reward definitions,
reward calibration, Main scalarization, TLE split, or Main-only evaluator.

The design is currently **mechanistically coherent and testable, not
efficacy-proven**. A support census establishes only that a role has learnable
choices. A one-episode routed run establishes only executable plumbing and
nonzero donor receipts. Only fresh-seed Main-only evaluation may establish an
EE trend; only the later preregistered matched long run may support a Chapter 5
efficacy claim.

## 2. Fixed shared carrier

Training owns four independent learner states: Main and three one-objective
specialists `C1`, `C2`, and `C3`. In manuscript notation the Main networks are
`Q_j^M` and the specialist networks are `Q_j^F`, for `j in {1,2,3}`. Each
specialist owns independent online/target parameters, optimizer, RNG, replay,
and policy version.

Every specialist branch executes a complete joint environment transition and
retains the unchanged `U x 3` canonical reward matrix. There is no action
voting, auction, coordinator, reward summation, or post-training specialist at
evaluation/deployment. Only the saved Main MODQN selects the final action.

Main retains its canonical replay sample in every update. A routed role donor
can affect only its matching Main objective:

- `C1 -> Q_1^M`;
- `C2 -> Q_2^M`;
- `C3 -> Q_3^M`.

For an available role donor, the matching objective loss is frozen as
`0.75 L_Main + 0.25 L_Cj`. Missing or unusable donors have effective dose zero;
their dose is never borrowed by another role. `C1` contributes all admissible
joint rows because canonical `r1` is a system-EE decomposition. `C2` and `C3`
contribute only their declared focal row. Their nonfocal rows may be evaluated
only as no-gradient audit diagnostics.

Before either `C2` or `C3` executes, a fail-closed assertion requires every
nonfocal action to equal the detached frozen-Main greedy action. The branch may
differ at zero rows (explicit defer) or at exactly its declared focal row.
Each step records the focal, differing-row set, and hashes of the Main and
executed joint-action vectors.

## 3. Common Catfish operator

Each role uses the same four-stage operator:

1. **Observe and trigger** from the current state, valid action mask, physical
   `(NORAD, cell)` IDs, incumbent association, detached Main surface, and the
   role's own RNG.
2. **Propose** a valid source-specific action or bounded physical option.
3. **Execute and learn** the realised complete branch, including bad outcomes;
   no realised reward sign may retrospectively admit or delete it.
4. **Route diagonally** to the matching Main objective only when the applicable
   development or formal consumer gate authorizes the source.

Online eligibility must not read realised reward, EE, fading outcome,
successor state, future RNG, forecast rollout, or counterfactual branch.

## 4. C1: energy-frontier Catfish

`C1` retains the original RIS-lineage EXP/ACRM idea while keeping canonical
`r1` and the LEO environment unchanged.

- Its verified offline EXP prefill uses paired executed `local_snr_greedy` and
  `masked_uniform` source trajectories from the frozen corpus. Prefill trains
  `Q_1^F` only and never enters Main directly.
- Online `C1` executes one complete joint action every logical step.
- The informed source is `Q_1^F` epsilon-greedy; its dose-matched control is
  masked uniform over the same valid support.
- ACRM may shape only the private `C1` update by comparing the executed C1
  branch with the detached Main comparator under the copied pre-outcome RNG
  state. Main always receives the branch's unchanged canonical `r1` column.
- A routed `C1` bundle targets `Q_1^M` using all admissible rows.

`C1` directly targets system EE but is not presumed beneficial: its singleton
must still improve fresh-seed Main-only EE against the matched baseline.

## 5. C2: activation-onset continuity Catfish

`C2` directly learns unchanged canonical `r2 = -Psi_u`. Its purpose is to
create experience at handover decisions where scalarized Main is about to open
a cold destination even though a choice between the incumbent and one or more
other already-warm actions is visible. The incumbent itself is not required to
have positive lagged demand.

For user `u`, let the current incumbent be recoverable in the valid slot table,
let `a_u^M` be the detached Main greedy action, and let the state's
`n_{s,v}(t-1)` block give finite nonnegative integer lagged ungated demand.
`u` is eligible exactly when:

1. `a_u^M` is valid and differs from the incumbent;
2. the destination selected by `a_u^M` has lagged demand zero; and
3. the support consisting of the incumbent plus every other valid action with
   lagged demand at least one contains at least two distinct actions.

If more than one user is eligible, the C2 RNG chooses the focal user. `Q_2^F`
then performs epsilon-greedy selection within that focal support. Selection is
bound to the physical `(NORAD, cell)` ID for a fixed `H=3` executed-step option;
slot indices are remapped every step and an unmappable physical ID terminates
the option. Realised service failure may also terminate the behaviour option;
that post-outcome termination rule never filters admission, and the executed
failure transition remains in replay. C2 learns only the focal row's unchanged canonical `r2`. A routed
donor targets only `Q_2^M`.

This trigger does not assert prospectively that the selected choice will have
better `r2` or EE. It makes the relevant continuity choice observable and
learnable; realised `r2`, service, power, and EE are measured afterwards.

## 6. C3: same-satellite load-relocation Catfish

`C3` directly learns unchanged canonical `r3 = -U_{b_u}`. Its purpose is to
create experience at a spatial load-balancing decision while avoiding a
satellite-level handover by construction.

User `u` is eligible exactly when:

1. its incumbent is recoverable in the valid slot table;
2. detached Main proposes to remain on that same physical source;
3. a different valid beam on the same satellite is already warm, with lagged
   demand at least one; and
4. the source lagged demand is at least two users larger than that destination
   lagged demand.

The focal support contains the source action first as an explicit defer-to-Main
choice, followed by every qualifying same-satellite destination. If more than
one user is eligible, the C3 RNG chooses the focal user. Selecting the source
executes Main's action and opens no option. Selecting a relocation binds its
physical ID for `H=3` executed steps, with the same remap and fail-closed
behaviour-layer termination rules as C2; termination never removes the
executed transition from replay. C3 learns only the focal row's unchanged canonical
`r3`; a routed donor targets only `Q_3^M`.

Canonical state encoding exposes both required inputs to `Q_3^F` and `Q_3^M`:
the incumbent is recoverable from the access block and lagged demand occupies
the fourth state block, normalized only by the fixed number of users.

This predicate is not a promise of lower system power or higher EE. Moving load
can change bandwidth sharing, rate, feasibility, beam activation, and power,
so the indirect EE effect remains an empirical singleton and ablation result.

## 7. Counterfactual evidence is audit-only

Four-offset counterfactual replay remains permitted for bounded Stage-0
measurement and scientific audit, never for online admission. In particular,
the completed 9-focal by 8-candidate TLE scan showed that 9 of 72 candidates
strictly improved both hold-window and full-window system `r2`, but only two
candidates survived the older full certificate and they occurred at different
focals. That receipt killed the V0.1 per-anchor certificate as a scalable
runtime mechanism; it did not select the V0.2 predicates or the support floor.

Historical receipt:
`.scratch/catfish-stage0/receipts/c2-anchor-seed2026082801-9x8.json`  
SHA-256:
`b2272894705de737e7d6c2a61c6173c397744c8df10055feeaea57c08a6d5607`

## 8. Pre-outcome support census frozen before execution

The support census uses the canonical TRAIN partition and exact frozen TLE file
set SHA-256
`427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`.
It uses the already-trained baseline final-episode Main checkpoint:

`artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`  
SHA-256:
`e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`

The checkpoint is greedy, detached, and never updated. The three fixed
`(environment seed, mobility seed)` pairs are:

1. `(2026082811, 2026082821)`;
2. `(2026082812, 2026082822)`;
3. `(2026082813, 2026082823)`.

Each pair runs ten independently reset episodes of ten logical steps, for 300
logical steps total. The frozen Main action is executed only to advance the
canonical state. Reward and successor outcome are not inputs to either support
predicate or to the threshold.

The a-priori premise floor is the same for both roles:

- `C2`: at least 10% of the 300 logical steps expose at least one support of
  size two or greater;
- `C3`: at least 10% of the 300 logical steps expose at least one support of
  size two or greater.

Thus each role requires at least 30 exposed logical steps. The floor is fixed
before seeing census counts and must not be relaxed after failure. `C1` is
scheduled every step and is outside this premise census.

## 9. Evidence sequence and stop rules

1. Focused unit and integration tests must pass, including state visibility,
   focal-only donor gradients, nonfocal identity, physical-ID remap, immutable
   provenance, and Main-only evaluator isolation.
2. The frozen support census must pass both role floors. A failing role is
   `NO-GO` for the present predicate; do not compensate by changing reward,
   denominator, seeds, split, or floor after inspection.
3. A real one-episode `F111 --development-route-all` run must produce valid
   C1, C2, and C3 specialist replay receipts and nonzero matching Main donor
   doses. This is plumbing evidence only.
4. A bounded matched short-episode arm matrix may then estimate direction.
   Evaluation is held-out TEST, Main-only, ratio-of-sums EE in bits/J.
5. A fresh-context cross-model review checks feasibility, complexity, leakage,
   and whether a materially simpler or stronger alternative was missed.
6. Only after those gates, and only after explicit user notification, may the
   9000-episode matched experiment be launched on the Ubuntu training server.

No selector threshold, `H`, donor dose, reward, action mask, or support floor
may be changed in response to census or one-episode outcomes. Any later revision
must receive a new version, new source hashes, and a new independent pilot.

## 10. Fixed seed namespaces

- C1 specialist: `train_seed + 10001`;
- C2 specialist: `train_seed + 20003`;
- C3 specialist: `train_seed + 30007`;
- support census: the three environment/mobility pairs in Section 8;
- counterfactual Stage-0 audits: separate domain-separated forecast RNG and
  never the live training RNG.

The public paper and figure language must remain `Multi-Catfish MCRL`. Legacy
internal filenames or schemas containing `smc-er` are archival carrier names,
not the method name.
