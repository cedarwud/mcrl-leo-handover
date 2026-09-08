# Slice E assumptions audit — reward, targets, training, Catfish

Paths are relative to `/home/sat/mcrl-leo-handover-e1`. Read-only static audit; no TEST data opened.

## Executive finding

The successor’s endpoint accounting is internally consistent with the simulator’s current system-power function, but the learned objective is not the endpoint objective. Q1 omits immediate non-focal throughput externalities, Q2 is a frozen-background three-step oracle, and the legacy baseline was trained with a different reward containing Φ and an incorrect multi-head bootstrap. All of these mechanisms inherit the non-standard gain-inversion recurrence and must be rebuilt—not merely re-evaluated—under fixed-EIRP plus ACM physics.

## Ranked summary

| Rank | Assumption | Implementation | Docs / declaration | Standard status | Distortion | Magnitude | Verdict |
|---:|---|---|---|---|---|---|---|
| 1 | Gain-inversion recurrence is valid reward physics | `src/mcrl/env/step.py:770-810`; `src/mcrl/runtime/ee_axis_ops3.py:17-27,571-595` | Explicitly frozen by OPS-3 | Non-standard forward-link control; handover reset creates artificial renewal value | EE, all policy comparisons, C1/C2 labels and states | Potentially dominant; every handover resets power to 0.825 W | **FIX** |
| 2 | Q1+Q2 represents endpoint EE surplus | `ee_surplus_targets.py:250-264`; `ee_axis_ops3.py:729-786` | Successor declares only Q1/Q2: `.scratch/.../V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md:64-76` | A system objective must retain system-rate externalities | C1/C2 marginals and learned action ordering | Immediate omitted loss can scale with 99 non-focal users | **FIX** |
| 3 | Legacy summed r1 is the episode EE objective | `energy_efficiency.py:251-260`; `modqn.py:650-668`; endpoint `ee_axis_evaluation.py:172-210` | r1 described as a global decomposition | True for one time step only; sum-of-ratios ≠ ratio-of-sums | Baseline training and checkpoint choice | Ordering reversal can be arbitrarily large | **FIX** |
| 4 | Independent per-head Bellman maxima form a valid scalarized TD target | `modqn.py:511-550` | Comment calls it vanilla MODQN | Inconsistent with one deployed joint action unless heads are policy-conditional | Legacy BASELINE policy | Can create an unattainable sum of all heads’ maxima | **FIX** |
| 5 | λ is a stable, exogenous energy price | `.scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md:17-42`; active adapter `.../v023_lcsrs_source_adapter.py:149-150` | Declared as already-opened TRAIN BASE EE | Dinkelbach reference prices are valid only for the same aggregate/reference physics | C1/C2 signs and magnitudes | λ rose 39.3%; 76/1680 C1 signs flipped | **FIX** |
| 6 | Dropping empty-mask/outage transitions is harmless | `modqn.py:1248-1267`; `replay_buffer.py:30-56` | Code itself says this makes outage “FREE” | Invalid MDP sampling; outage/no-op needs explicit transition semantics | Legacy training signal and service behavior | Unknown drop rate; potentially severe selection bias | **FIX** |
| 7 | Legacy evaluation is RNG-isolated from training | `step.py:407-452,491-536`; `modqn.py:622-690` | Undocumented | Evaluation should not advance training randomness | Reproducibility, checkpoint selection | One evaluation reset consumes 100 persistent age draws | **FIX** |
| 8 | κ is merely a harmless normalization constant | `ee_axis_calibration.py:43-75`; `ee_axis_ops3.py:741-782` | κ = Main bits/decision | Common scaling is harmless, but κ is also the physical outage loss | Q1/Q2 balance and persistence preference | Each failed future offset contributes −10.097 Gb, or −1 after normalization | **SENSITIVITY** |
| 9 | Legacy reward calibration and “best weighted reward” evaluation use the same objective | `reward_calibration.py:43-75`; `modqn.py:1269-1277,667-668,1336-1358` | `trainer_spec.py:81-105` says best weighted reward | Training and checkpoint selection should use identical units | Which baseline checkpoint is selected | Raw r1 is about 10⁶ while r2/r3 are order 1 | **FIX** |
| 10 | Catfish drops isolate a head’s causal contribution | `v023_two_route_learner_orchestrator.py:61-67,653-694`; selectors `ee_axis_c1_selector.py:823-895`, `ee_axis_c2_neutral_source.py:457-545` | Drops declared as equal-budget neutral replacement | Source intervention, not component removal; distribution matching matters | Reported C1/C2 marginals | C1 is profile-matched; C2 is only count-matched | **DECLARE** |
| 11 | Φ makes baseline and successor policies objective-comparable | `step.py:1094-1103`; `action_contract.py:398-455`; successor Q1/Q2 formulas above | Φ documented as utility penalty, not joules | Valid regularizer if shared; invalid as an undisclosed cross-policy objective change | BASELINE-vs-successor comparisons and handover rates | Inter-satellite event contributes −0.3 after legacy scalarization | **FIX** |
| 12 | `ee_axis_state`’s four “C2” temporal features are successor C2 inputs | `ee_axis_state.py:49-59,282-335`; actual Q2 schema `ee_axis_v014_q2_state.py:24-46`; deployment `...physical_runner.py:1023-1047` | Successor says Q1=228D, Q2=448D: declaration `64-71` | Schema names and consumers should agree | Interpretation and fixed-EIRP migration | Two 228D fields and three Q2 required-power fields lose meaning | **FIX** |
| 13 | Successor marginal watts use the endpoint power definition | `step.py:864-888,973-1028`; `ee_axis_ops3.py:458-526`; endpoint runner `...physical_runner.py:954-987` | OPS-3 declares canonical max-per-beam power | Correct conditional on retained power physics | Power accounting itself | Exact, modulo counterfactual background assumptions | **KEEP** |

## Detailed findings and known-answer tests

1. **The recurrence contaminates both targets and policy state.** A new segment takes the current gain as its start gain, forcing `p=p0`; continuing service uses the old start gain (`step.py:783-809`). OPS-3 repeats this recurrence at every projected offset (`ee_axis_ops3.py:571-595`). Consequently C1 sees handover energy savings and C2 forecasts persistence using the same manufactured ramp.

   **Known-answer test:** give two otherwise identical actions the same current gain but different historical start gains. Under fixed EIRP their transmit and supply powers must be equal. Any differing target, feasibility result, or action value proves recurrence leakage.

2. **Q1+Q2 omits immediate non-focal throughput.** The exact V0.3 identity is `z1 focal bits − λ·all opening Δenergy + z3 non-focal bits + z2 future system surplus` (`ee_surplus_targets.py:250-279`). Successor Q1 consumes only `zeta1_focal_surplus_bits` (`ee_axis_opening_dataset.py:347-385`), while Q2 contains future focal rate and marginal power under frozen background (`ee_axis_ops3.py:729-786`). Removing Q3/C3 therefore removed `z3`; Q1+Q2 is not system surplus.

   **Known-answer test:** candidate gives focal `+1` bit, another user `−10` bits, and `ΔE=0`; let all future terms be zero. Endpoint surplus is `−9`, but successor Q1+Q2 is `+1`. The candidate must lose in an endpoint-aligned scorer.

3. **Legacy r1 matches only a single-step system ratio.** Summing users’ `R_u/P_system` exactly recovers that step’s `ΣR/P` (`energy_efficiency.py:167-180`). Training then sums/discounts those ratios across time, whereas evaluation divides accumulated bits by accumulated joules (`ee_axis_evaluation.py:183-210`).

   **Known-answer test:** policy A has `(R,P)=(10,1),(0,99)`; B has `(1,1),(1,1)`. Legacy reward prefers A, `10>2`; endpoint EE prefers B, `0.1<1` bit/J.

4. **Legacy per-head bootstrap is a utopia target.** Each head independently computes `max_a Q_j(s',a)` (`modqn.py:535-550`), although deployment chooses one action after scalarization. Successor pairwise learning correctly has no bootstrap: Q1 explicitly regresses a supervised pair difference (`v023_heterogeneous_trainer.py:265-282`) and Q2 consumes an already-normalized pair target (`326-336`).

   **Known-answer test:** at the next state let `Q1=[10,0]`, `Q2=[0,10]`, equal weights, zero reward. Code bootstraps vector `(10,10)` with scalar value 10; either realizable action has scalar value 5.

5. **λ was repaired operationally, but remains endogenous and physics-specific.** The active `118424222.8550065` bit/J is pooled EE from 12 already-opened TRAIN rows of a learned BASE arm (`...LAMBDA-REPRICING...md:27-36`). It replaced `84994621.12635651`; the audit found 4.524% C1 sign flips (`.../q1-repricing/Q1-REPRICING-AUDIT.md:45-62`). The generic OPS-3 module still exposes the old default at `ee_axis_ops3.py:66`; only the active adapter overrides it.

   **Known-answer test:** for reference `(B0,E0)=(100,10)`, set `λ=B0/E0=10`. For every candidate verify `sign[(B−B0)−λ(E−E0)] = sign[B/E−B0/E0]`. Repeat after fixed-EIRP+ACM recalibration; old λ must fail admission.

6. **Empty masks are treated three incompatible ways.** Legacy action selection emits `NO_OP_ACTION` (`modqn.py:324-353`), replay discards that transition and any transition leading to a non-terminal empty next mask (`1248-1267`), while successor deployment rejects every empty mask row (`ee_axis_two_route_model.py:147-157`). Thus evaluation assumes away a state training claims to support.

   **Known-answer test:** make a legal action lead to a non-terminal all-false next mask. The transition must yield a defined outage/no-op target and remain in replay; deployment must implement the same next-state semantics rather than abort.

7. **Legacy evaluation consumes training’s warm-start RNG.** `_age_rng` is spawned once and persists across resets (`step.py:407-452,534-536`). Evaluation supplies a fresh `eval_rng`, but an existing `_age_rng` ignores it and advances the training stream. Evaluation cadence therefore changes later training worlds, and evaluation results depend on previous training/evaluation calls.

   **Known-answer test:** clone trainer state. On clone A perform one evaluation before the next training reset; on clone B do not. Their next `_pending_segment_age` must be identical. Current code will differ.

8. **κ has two incompatible interpretations.** It was derived as one Main window’s `useful_bits/(steps·users)` (`ee_axis_calibration.py:70-75`; fixture values at `tests/test_w53_ee_axis_calibration.py:16-30`). In OPS-3 it is also the outage disutility before the same κ normalizes Q2. Changing κ therefore changes the balance between throughput/energy and service loss, not merely numerical conditioning.

   **Known-answer test:** candidate fails all three offsets while a zero-surplus reference persists. Confirm `Q2(candidate)−Q2(reference)=−1`. Double κ without changing physical bits: if the normalized physical-surplus contribution halves, κ is policy semantics, not pure scaling.

9. **Legacy checkpoint evaluation ignores training calibration.** Replay stores calibrated rewards (`modqn.py:1269-1277`), but evaluation scalarizes raw episode rewards (`650-668`) to select the secondary checkpoint (`1336-1358`). This contradicts the “best-weighted-reward” label in `trainer_spec.py:81-105`.

   **Known-answer test:** compare raw episode vectors A=`(2e6,−1,0)` and B=`(1.9e6,0,6)`. Raw scalarization selects A; using `c1=2029238.43,c2=1,c3=6` selects B. Training and checkpoint code must agree.

10. **Catfish is dataset routing, not reward injection.** FULL2/DROP arms are trained from informed/neutral source mappings (`v023_two_route_learner_orchestrator.py:61-67`); all deploy both heads. C1 injects lower-frontier anchor/user selection plus physical pair labels (`ee_axis_c1_selector.py:823-895`). C2 injects hold-or-max-lagged-SINR-rival sampling; neutral samples the same row count uniformly without replacement (`ee_axis_c2_neutral_source.py:1-22,457-545`). Nothing is injected at inference beyond learned Q values.

   **Known-answer test:** after one C1 and one C2 round, assert route/source mappings exactly FULL2=`I/I`, DROP_C1=`N/I`, DROP_C2=`I/N`, and verify every arm still deploys `argmax_mask(Q1+Q2)`. Separately balance C2 neutral samples by anchor/user/action strata; unequal strata expose the source-distribution confound.

11. **Handover treatment differs by policy family, not by joule accounting.** Endpoint, C1 and C2 add zero handover energy. Legacy MODQN separately receives `−Φ1` or `−Φ2` (`action_contract.py:408-455`; `step.py:1094-1103`). Its Q2 Bellman head also propagates future Φ. The successor heads contain no Φ; any stay preference comes only from dwell/masks, incumbent/persistence state, service-risk labels, and the hold/rival source. The recurrence itself pushes the opposite way by rewarding renewal.

   **Known-answer test:** make stay and switch produce identical rates and physical power. Endpoint EE and successor physical-surplus targets must tie; legacy reward must differ by exactly Φ. Cross-family comparisons must then be labelled as different training objectives or retrained consistently.

12. **The feature attribution in the prompt/code name is stale.** The four fields named `EE_AXIS_C2_CONTEXT_FEATURES` are appended to the 228D state (`ee_axis_state.py:49-59,282-335`), but current successor C2 consumes a separate 448D OPS-3 state (`ee_axis_v014_q2_state.py:24-46`). The 228D state is now Q1 input. Under fixed EIRP, previous recurrence power becomes constant/zero, gain-to-segment-start ratio no longer predicts power, while age and missing-incumbent remain handover/service-history features. In actual Q2, the three projected required-power ratios must likewise be replaced or declared constant.

   **Known-answer test:** perturb only the four tail fields of the 228D state while holding the 448D Q2 state fixed; successor Q2 must not change. Under fixed EIRP, changing segment-start gain must not change any Q2 required-power feature or target.

13. **The watt function is otherwise shared.** Runtime endpoint uses maximum required link power per physical beam, then PA supply plus fixed active-satellite power (`step.py:864-888,973-1028`). C1 records candidate/reference full `system_power_w`; OPS-3 reconstructs existing-beam power with `max(background,candidate)` and the same helpers (`ee_axis_ops3.py:458-526`). Stage C integrates that field as joules (`...physical_runner.py:954-987`).

   **Known-answer test:** with two users requiring 1 W and 2 W on one beam, RF beam power must be 2 W, not 3 W, in endpoint, C1 branches and Q2 marginal power. Moving the 1 W user to a new beam must activate exactly one additional beam and, if applicable, one satellite fixed term.

## Fixed-EIRP + ACM consequence

λ and κ cannot be carried forward. Fixed EIRP removes segment-age power ramps and handover resets; ACM replaces continuous Shannon-rate changes with MCS thresholds. Rebuild C1/Q2 states and labels, derive λ from a prospectively fixed reference policy under the new physics, and separate κ’s numerical normalization from an explicitly declared service-loss cost. All compared learned policies, including BASELINE, require retraining under the same physics and objective.

## Status of the 2026-08-31 findings

- **λ multiplier:** fixed in the active successor adapter and repriced datasets, but not in the generic OPS-3 default. **Partially fixed.**
- **Per-head bootstrap:** eliminated in the successor’s supervised pairwise trainer, but unchanged in legacy MODQN. **Partially fixed.**
- **r1 aggregation:** fixed in Stage-C evaluation through pooled ratio-of-sums, but not in legacy training reward or legacy best-checkpoint evaluation. **Partially fixed.**

## TRAIN/evaluation leakage conclusion

Stage C is explicitly TRAIN development, uses matched worlds across arms, and keeps TEST closed (`...SUCCESSOR-SCIENTIFIC-DECLARATION...md:101-119`). Its source worlds and physical-evaluation world-seed namespaces are distinct, so I found no direct Stage-A/Stage-C world-ID reuse. It nevertheless provides no held-out efficacy evidence, and earlier internal-validation sources were folded into repricing (`...LAMBDA-REPRICING...md:44-83`); those sources are no longer independent validation. Legacy MODQN additionally has the concrete bidirectional `_age_rng` leak described above.

## Three assumptions I would overturn first

1. **Remove the segment-anchored gain-inversion recurrence** and rebuild all targets, features, checkpoints and comparisons under fixed-EIRP+ACM.
2. **Reject Q1+Q2 as an endpoint-surplus decomposition** until immediate non-focal rate externalities and a consistent service objective are restored.
3. **Retire the legacy MODQN training target/objective**: use ratio-consistent returns, one scalarized next action for all objective components, explicit outage transitions, and isolated evaluation RNGs.