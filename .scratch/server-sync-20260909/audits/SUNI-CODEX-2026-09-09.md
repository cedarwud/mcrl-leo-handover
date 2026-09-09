The present arm is valid as a deployment comparison, but its fallback-inclusive contrast cannot satisfy C4’s certified-unilateral attribution requirement; this does not invalidate the study.

Independent adjudication, 9 September 2026. I inspected the contracts, their relevant amendments, the CH5 specification, the JSON, and the selection/profiling code. I did not consult the parallel adjudication. Only this report was written.

On question 2, the decisive evidence is already in the sealed documents. Contract v1.2, item 6, explicitly calls budget-limited S_UNI an operational comparator, requires a completed-neighbourhood certificate for the “beyond exhaustive unilateral improvement” claim, and permits an offline certified diagnostic. The controller’s proposal therefore partly implements a distinction already required by the contract. The CH5 phrase “the honest comparator” does not override that qualification. [Contract amendment][amendment]; [CH5 specification][figure].

An operational policy includes its stopping and fallback rules. Comparing FULL with that policy on all anchors, counting fallback bits and energy, is honest evidence about the two implementations under the stated resources. But superiority could arise because FULL finishes useful work while S_UNI does not. It would not establish superiority to the local optimum that S_UNI never reached. This problem has no magic threshold at 88%: any uncertified fallback can break that interpretation. At the observed rate it is especially consequential.

For example, a purely additive problem can give BASE a score of 0, either unilateral improvement 1, and their combination 2. A joint selector returning 2 beats a timed-out unilateral selector returning 0, although completed unilateral search also reaches 2. The timeout contrast alone has not identified interaction value. C4’s other requirements—FULL versus DROP_C3, QoS, and decision-relevant nonadditivity—remain necessary, but they cannot turn an unfinished search into a certified comparator. [C4][contract].

Thus this finding defeats using the current contrast to discharge the certified-unilateral requirement. It does not establish that FULL lacks coordination value, invalidate a separate learned-source contrast, or predict the unopened panel’s result. Restricting the comparison to the 11 successful anchors would not repair the all-anchor estimand: completion selects which cases are compared.

The numerical audit materially changes the premise. Recomputing the supplied JSON gives:

| Observation | Verified result |
|---|---:|
| Cutoff-screened anchors | 90 |
| `DEADLINE_FALLBACK_BASE` | 79/90, 87.8% |
| Recorded selection wall ≥10 s | 0/90 |
| Selection wall: median / p95 / maximum | 9.223 / 9.412 / 9.975 s |
| Recorded selection wall >9.5 s | 3/90 |
| Zero accepted updates | 53: 42 interrupted searches + 11 certificates |
| Selected configurations equal to carrier BASE | **90/90** |
| Completed uncapped records | **17**, from 20 selected out of 90 |

All 11 successful screens certified BASE. The other 79 returned it on cutoff, including 37 that had made tentative updates before discarding them. Consequently this diagnostic arm equals BASE in its returned configurations everywhere, not merely on 88% of anchors. Certification status still distinguishes the 11 successes from the 79 failures. [Profile JSON][profile].

The uncapped records contain 12 zero-update runs with median **7.827 s**, and five runs requiring **46, 50, 80, 86, and 86 updates**, taking **548.559–876.406 s**. The **8.879 s** median is for all 17 completed uncapped records, not the easy subgroup. These anchors were deliberately selected using screening status and timing. They demonstrate very different observed computational demands, but cannot establish two statistical populations or their prevalence.

The scope is one prepared world, `V025_PROBE_R2/world/1`, 30 steps and three carriers, with one process. These are correlated diagnostic cases, not 90 independent held-out worlds. The profiler supplies the previous carrier BASE as incumbent; it does not measure an independently evolving S_UNI policy trajectory. Its reported wall covers the selection routine after evaluator construction, not full end-to-end deployment. The cutoff constants are unchanged, but the routine is instrumented. No FULL outcomes or realised pooled-EE contrast appear in this JSON. [Profiler setup and timing][profiler]; [sample selection][sampling].

On question 1, **yes to separating completed-search quality from deadline-constrained delivery; no to treating the two comparisons as interchangeable or silently replacing C4.** Call the existing policy `S_UNI_budget` and the completed reference `S_UNI_cert`, or use equally explicit labels. “Without the deployment cutoff, run the fixed procedure to certification” is more precise than “unlimited compute”: freeze its starting profile, information, objective, legal moves, tie rule, numerical tolerances and stopping certificate. It must not acquire future information, realised outcomes for selection, extra restarts, or a newly tuned search policy.

Giving this reference more computation creates a meaningful, deliberately demanding question: does the deployed FULL procedure outperform this specified completed unilateral procedure on the declared endpoint? A positive result can support that comparison even though the reference is not deployable. A negative result does not erase a deployment advantage over the budgeted arm. Neither result establishes superiority to every unilateral algorithm or to a global optimum: S_UNI reaches a local optimum determined by its starting point and update rule.

**For avoiding a false coordination attribution, the fallback-weakened comparator is the worse asymmetry.** Extra compute for the reference removes the explanation that the unilateral search simply ran out of time. For an equal-resource deployment claim, however, the budgeted arm is the appropriate comparator; the uncapped reference cannot replace it.

There is a further qualification: more nominal-objective optimization does **not** guarantee better held-out realised pooled EE. The selection objective includes a fixed energy multiplier and preference terms; the endpoint is a realised ratio over trajectories. Therefore uncapping S_UNI is not mathematically guaranteed to make C4 harder, and the direction of the endpoint change cannot be inferred from fallback counts. The project itself records this objective-versus-ratio distinction. [Objective-gap note][objective].

Report two distinct kinds of offline evidence. At matched states, a certified reference can diagnose joint headroom; an improving joint move from its local optimum, with every legal unilateral increment nonpositive within tolerance, directly demonstrates escape requiring a joint move under that objective. For a held-out pooled-EE comparison of policies, run a separate offline rollout on the predeclared exogenous worlds, letting each policy carry its own committed state and charging the same physical endpoint. Offline computation must use information available at the simulated decision time, with its hypothetical immediate application stated. One-step shadow choices along another policy’s trajectory are not that alternative policy’s closed-loop EE.

Keep deadline-constrained, all-anchor performance primary for deployment. Report the offline reference separately, including certification coverage and cost. If computational limits leave offline cases unresolved, label them unresolved; do not substitute BASE and still call the reference certified, or pool only convenient completions into an all-anchor claim. Preserve the other C4 conditions and its inferential rule. Also keep the oracle FULL/S0 used in the CH5 physics figures distinct from learned FULL/S3 in C4: the figure specification explicitly describes oracle scoring. [Figure definitions][figure]; [C4][contract].

On question 3, **the guard has a legitimate purpose; its precise size is not vindicated by these measurements, and manufacturing the 88% rate has not been demonstrated.** The implementation reserves 0.5 s because evaluator calls are non-preemptible. It additionally refuses the next batch when remaining guarded time is no greater than `max(0.25 s, maximum observed batch duration)`. It also checks time after batches. This is proactive stopping, not merely rejecting an otherwise completed result whose wall exceeds 9.5 s. [Guard and batch admission][guard].

Accordingly, zero observed 10 s overruns is compatible with the guard doing its job. Cancellation censors the completion time that would have occurred without it. Conversely, an unnecessarily pessimistic reserve can discard work that would finish: these data do not prove optimal calibration. One screened miss later certified BASE in 8.879 s, while two screened successes later needed 10.408 and 11.088 s. Timing near the boundary varies. The five completed long searches show that a genuine convergence burden exists which another half-second cannot cure on those cases; they do not identify how many of the other misses would be rescued.

The principled rule is to derive and validate the reserve from non-preemptible work, cancellation, bookkeeping and the actual commitment boundary on declared hardware, using an outcome-independent engineering criterion. Account explicitly for what the 10 s timer includes and what F2 already reserves elsewhere in the 30.08 s interval. Do not choose a guard to obtain a desired fallback rate or favourable EE. A justified engineering correction is possible, but these data do not supply that justification for any particular replacement value. [Timing contract][timing].

On question 4, **zero iterations does not make the arm meaningless, and the stated interpretation of the counter is wrong.** The counter increments after a completed neighbourhood scan changes the current profile; it does not count alternatives evaluated. The code can also accept objective ties by deterministic configuration order, so “accepted updates” is more accurate than “strict improvements” for this field. Each of the 12 zero-update uncapped records proposed 2,700 alternatives and recorded 2,748 exact solves. [Selection and counter][counter]; [profile][profile].

For the 11 certified screens, zero updates is a substantive result: the initial BASE already satisfied the implemented local-optimum condition. For the 42 interrupted zero-update screens, it means that no update was accepted before interruption, not that nothing was evaluated or that BASE was locally optimal. The arm is informative about operational failure and, where certification completes, local optimality. What is absent in the other cases is the certificate needed for the stronger attribution. Allowing a tentative best-so-far profile to commit might define a useful different deployment policy, but it would change the sealed atomic-final-profile rule and would not provide the missing certificate.

On question 5, **outcome blindness alone does not authorize a C4 amendment under this project’s freeze discipline.** Adding the already-authorized offline diagnostic and correcting operational/certified labels need not redefine C4. Making an uncapped comparator load-bearing in place of the current matched-budget comparator is a scientific change: it changes the comparison being required and needs an explicit amendment to the affected contract and reporting rules. It cannot be implemented merely by relabelling a curve. Contract A4 expressly includes deadline and fallback matching. [A4][matching]; [existing offline authorization][amendment].

The freeze rule admits a late change only if all four conditions hold: it can change the sign of a named load-bearing certificate or the admission branch; it names a test that fails now and passes after the change, executable within an hour; it has independent confirmation; and it requires no rerun of completed work, or the rerun fits one overnight window. The current admission rule still requires S0 to beat certified S_UNI. [Freeze rule][freeze]; [current admission rule][admission].

This finding plausibly affects that certificate and the interpretation of C4, and the timing/certificate evidence can be independently verified. But those facts do not themselves demonstrate the required failing/passing test or the rerun budget. A concrete test would use a tiny fixture with a known profitable unilateral move, force an early cutoff, and check that an uncertified BASE return cannot be accepted as certified evidence. If the existing gate already rejects it, that test confirms the safeguard; it does not establish a defect that justifies replacing the estimand. Any proposed replacement also needs its own conformance test and cost accounting. No such before/after demonstration was performed in this read-only adjudication.

I could not verify the literal stage-4g audit-pass trigger from the inspected artifacts. However, the subsequent sealed run decision expressly applies closure at stage 4h and forbids another design pass before the matrix. Prior amendment frequency is therefore not sufficient precedent for reopening the design. My judgement is: **the diagnostic split is already admissible; a load-bearing C4 replacement is conditionally admissible through the recorded exception process, not established as admissible merely because no panel result exists.** Without satisfying that process, report the deployment result and offline diagnostic, and withhold the unsupported attribution. [Closure decision][closure].

On question 6, these are the controller’s incorrect or overstated sentences and formulations:

1. **“If S_UNI falls back to BASE on 88 per cent of anchors, that comparison is close to free, and the error is in the direction that flatters the coordination claim.”** The attribution concern is sound, and all 90 returned BASE here. But no FULL result or pooled EE is supplied, so ease of winning and the endpoint direction are unmeasured. FULL might tie or lose; completed S_UNI need not improve realised EE. The demonstrated defect would be assigning a certified-search interpretation to fallback outputs.

2. **“That reads like an offline reference quantity, not a deployable policy, but it is nonetheless run under the deployment deadline.”** The certified procedure and its deadline wrapper are different objects. Running the wrapper is legitimate, and v1.2 already distinguishes their evidentiary roles. Reading C2 alone misses that amendment.

3. **“The guard is 0.5 s, so anything finishing after 9.5 s is declared a miss although nothing exceeded 10 s.”** The explanation is incomplete: 76 of the 79 recorded misses returned before 9.5 s under proactive batch admission. These are interrupted returns, not evidence that certification finished before 10 s. The recorded timing also excludes parts of end-to-end execution.

4. **“Removing the cutoff entirely, the same anchors need up to 876.4 s and 86 best-response iterations to converge, against a median of 8.9 s for the easy ones.”** The extrema are supported for the completed diagnostic subset. There are only 17 uncapped records, not 90; the easy zero-update median is 7.827 s, while 8.879 s is the median across all 17.

5. **“Those are two populations, not one distribution with a tail.”** The selected records exhibit a pronounced gap and two observed kinds of search effort. A deliberately selected, incomplete sample does not distinguish a population mixture from a heavy-tailed distribution or establish prevalence.

6. **“Split it into two arms: S_UNI computed without the deadline as the quality comparator, and a separate deadline-limited unilateral arm as the deployability comparator. Report both.”** Correct direction, incomplete specification. Distinguish matched-state shadow diagnostics from an offline policy rollout, fix the search and information access, handle missing certificates, and state which contrast supports which claim. Offline reporting is already authorized; substituting it into C4 is a separate decision.

7. **“The controller believes the present single arm conflates two different questions and that the 88 per cent fallback is the symptom.”** Correct if the same curve is being used to claim both deployment superiority and superiority to completed unilateral search. The sealed amendment already separates those questions; the immediate problem may be enforcement and labelling rather than a missing scientific distinction.

8. **“The comparator spent nine seconds and evaluated no improving move at all.”** Unsupported by the counter. Zero accepted updates includes extensive candidate evaluation, interrupted scans, and successful certificates. It cannot establish that no improving candidate was evaluated.

9. **“The project has amended sealed documents repeatedly, always outcome-blind.”** Too broad. The v1.6 amendment explicitly discloses inspection of development SMOKE numbers. Blindness to formal confirmatory outcomes is a narrower claim, and neither form of blindness overrides the later closure rule. [Disclosure][disclosure].

10. **“A policy that cannot finish is a policy that does not act.”** Here it acts by executing validated BASE. That is a well-defined deployment policy, but its action cannot be represented as the result of completed unilateral optimization.

Audit identity: JSON SHA-256 `1822ba08742a7a55244cfacf18d966f20484074e9478b5fff7d6b0a77934b1e6`; recorded source commit `75c5c78c`; artifact classification `DIAGNOSTIC_NOT_CLAIM`. Statistics above describe the inspected 17-row uncapped snapshot.

[contract]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:22
[matching]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:9
[timing]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md:39
[amendment]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1.2-AMENDMENT-2026-09-09.md:10
[figure]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-CH5-SWEEP-FIGURE-SPECIFICATION-2026-09-09.md:5
[profile]: /home/sat/mcrl-v025-certprofile-ws/.scratch/cert-profile/s-uni-profile.json
[profiler]: /home/sat/mcrl-v025-certprofile-ws/scripts/profile_s_uni_certification.py:30
[sampling]: /home/sat/mcrl-v025-certprofile-ws/scripts/profile_s_uni_certification.py:158
[guard]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:3099
[counter]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:3175
[objective]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md:21
[freeze]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-DESIGN-FREEZE-AND-CLOSURE-RULE-2026-09-09.md:8
[admission]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.9-AMENDMENT-2026-09-09.md:10
[closure]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-TONIGHT-RUN-DECISION-2026-09-09.md:15
[disclosure]: /home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md:3
