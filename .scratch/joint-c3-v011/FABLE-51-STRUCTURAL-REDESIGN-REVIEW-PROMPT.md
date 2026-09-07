<operating_mode>
You are operating autonomously. The user is not watching in real time and cannot answer questions mid-task, so asking 'Want me to…?' or 'Shall I…?' will block the work. For reversible actions that follow from the original request, proceed without asking. Stop only for destructive actions or genuine scope changes the user must decide. Offering follow-ups after the task is done is fine; asking permission before doing the work is not.

This is a read-only scientific design review. Do not edit files, run a simulator,
start training, open TEST data, or change any authority. Read independent files
in parallel where possible. Deliver the complete review in this response.
</operating_mode>

<goal>
Fresh-context adjudication of the smallest theoretically justified structural
redesign for Catfish C3 after the frozen V0.11 joint-C3 oracle failed. Determine
whether C1 and/or C2 must also change, and propose at most two C3 candidate
formulas suitable for one new preregistered TRAIN-only oracle screen.
</goal>

<documents>
Read these before answering:

1. `docs/MULTI-CATFISH-MCRL-V011-JOINT-C3-ORDERED-ORACLE-PREREG-2026-09-03.md`
2. `artifacts/multi-catfish-v011-joint-c3-ordered-oracle-20260903-r1/RESULT-SUMMARY.md`
3. `artifacts/multi-catfish-v011-joint-c3-ordered-oracle-20260903-r1/server-run/merged/result.json`
4. `src/mcrl/runtime/ee_axis_joint_c3.py`
5. `src/mcrl/runtime/ee_axis_ops3.py`
6. `src/mcrl/runtime/ee_axis_matched_opening.py`
7. The simulator source that defines canonical total delivered bits, network
   power/activation, action semantics, and state transitions. Locate only the
   files needed to verify the causal argument.

First derive your diagnosis from the formula, simulator, and V0.11 receipts.
Only afterward, if useful, compare it with `gpt-dr.md` and `gpt.pdf`; do not let
those reports substitute for an independent derivation.
</documents>

<verified_result_snapshot>
All 15 frozen TRAIN-only shards completed; mechanics and 3000/3000 service
passed for every comparison. No learner or TEST data was used.

- AP-MONE vs C3-free `Q1+O2`: EE -4.443940%; bits +34.2964%; energy +40.5420%;
  0/3 positive lineages; method mechanics passed.
- M1-D vs C3-free: EE -1.489437%; bits +43.2513%; energy +45.4172%; 0/3
  positive; every lineage contained a five-sweep nonconvergence.
- exact-O1+C3 vs exact-O1 without C3: EE -1.196711%; bits +29.7086%; energy
  +31.2796%; 1/3 positive; every lineage contained a five-sweep
  nonconvergence.
- Frozen decision: `JOINT_C3_STRUCTURAL_REDESIGN_REQUIRED`.
- Standalone verifier reproduced the hashes, pooled ratios, gates, and decision.
</verified_result_snapshot>

<immutable_product_constraints>
- Exactly three independent 28-action heads/Catfish mechanisms.
- One common safe mask, left-to-right unweighted `Q1 + Q2 + Q3`, one masked
  argmax, one executed Main action.
- No deployed sweep, auction, coordinator, mixer, learned head weight, sign
  flip, post-training override, or second decoder.
- The only final objective is canonical ratio-of-sums EE. No requirement that
  legacy r2/r3 metrics improve.
- A C3 oracle/teacher may use training-time physical counterfactuals, but the
  learned Q3 must use decision-time physical state only and cannot consume
  Q1/Q2 scores, rankings, actions, arm labels, targets, outcomes, or future
  information.
- Preserve matched keyed physics, legal masks, native actions, and one-action
  deployment equivalence.
</immutable_product_constraints>

<design_questions>
1. Authenticate the causal reading of the V0.11 failure. Is the dominant issue
   current-slot non-focal credit, joint non-additivity, temporal energy/state
   carryover, fixed-lambda versus ratio-of-sums mismatch, a C1/C2 ownership
   boundary, or a combination? Separate verified fact from inference.
2. Decide whether the currently promising C1+OPS3-C2 backbone should remain
   fixed for the next screen. Do not call it confirmed: O2 is an oracle, not a
   learned Q2.
3. Derive at most two candidate C3 targets from the EE numerator/denominator.
   For each give:
   - one-sentence physical role distinct from C1 and C2;
   - exact target formula, reference action, units, sign, and zero convention;
   - non-overlap/double-counting argument;
   - why it should reduce joint energy expansion rather than merely raise bits;
   - decision-time state features a Q3 learner may use;
   - a concrete falsifier and principal risk.
4. Explicitly adjudicate these families rather than silently inventing a scale:
   one-sided harmful-externality/activation regret; activation-neutral spatial
   redistribution; full-horizon coalition/residual credit. Reject any family
   that cannot remain an independent additive Q3 at deployment.
5. Specify one ordered, non-cherry-picking preregistration for the selected one
   or two candidates on new TRAIN worlds. Include arms, comparisons, minimum
   mechanics, EE/service gates, interaction diagnostics, stop conditions, and
   estimated compute class. It must answer whether C3 has positive marginal EE
   on top of C1+C2; standalone C3 performance is not the primary gate.
</design_questions>

<evidence_discipline>
Treat V0.11 as development evidence from one TRAIN world and oracle heads, not
efficacy. Do not tune sign, scale, clipping threshold, horizon, seed, user
order, sweep count, or acceptance threshold against the observed outcome.
Distinguish verified fact, inference, and proposal. A mathematical identity is
not empirical efficacy, and an oracle PASS would authorize only a later
learnability preregistration.
</evidence_discipline>

<output>
Use clear technical prose with formulas where needed; avoid mannered or
repetitive prose. Return these sections:

1. `Verdict`
2. `Causal diagnosis`
3. `C1/C2 disposition`
4. `Ranked candidate table` (maximum two candidates)
5. `Recommended formula and bookkeeping proof`
6. `Next frozen oracle contract`
7. `Claims that remain prohibited`

End with exactly one token:
`REDESIGN_C3_ONLY`, `REDESIGN_C1_C3`,
`REDEFINE_C2_C3_BOUNDARY`, or `STOP_THREE_HEAD_STRUCTURALLY`.
</output>
