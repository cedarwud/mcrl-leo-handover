<documents>
The primary review artifact is:
`/home/u24/papers/mcrl-leo-handover/.scratch/catfish-opus-review/DESIGN-CANDIDATE-v0.md`

Its final section lists the repository evidence to inspect.  Read that artifact
first, then inspect the cited host and independent-mechanism files needed to
test its factual and architectural claims.  The working trees contain existing
user WIP; treat every file as read-only.
</documents>

<role>
Act as an independent adversarial reviewer of a multi-objective reinforcement
learning mechanism design.  You do not own the scientific ruling and you are
not implementing the design.
</role>

<goal>
Decide whether the proposed three-role, head-local Catfish direction is a
coherent and falsifiable next design for this exact MODQN host, or whether its
central carrier should be revised or rejected before implementation.
</goal>

<review_questions>
1. Do R1, R2, and R3 have genuinely distinct responsibilities, triggers,
   intervention state, gradient paths, ablations, and direct endpoints?
2. Is replay/update the correct seam, and can the proposed interface remain
   small while preserving host ownership of Q evaluation and replay mutation?
3. Does the Q-derived regret gate create a self-confirming feedback loop,
   selection bias, scale pathology, or invalid off-policy target?
4. Is a side-effect-free one-step environment branch scientifically valid in
   this coupled multi-user beam-association environment?  Identify exact state,
   RNG, joint-action, dwell, outage, and physical-identity hazards.
5. Is head-local auxiliary replay preferable to sampling a specialist bank and
   updating all three heads?  Explain any bias or loss of Pareto information.
6. Can R2 produce a non-decorative learning signal despite its zero-heavy
   reward and the existing result that does not establish superior handover
   control?
7. Can R3 remain an independently testable role even though load spreading can
   affect R1, and what result would falsify that independence claim?
8. Is this materially distinct from the local EXP/ACRM carriers and the seven
   current Catfish candidates?  Limit this to repository-relative novelty.
9. What is the smallest no-heavy-training prototype that can falsify the
   carrier before a server run?
</review_questions>

<boundaries>
Perform a read-only review.  Do not edit files, launch training, use subagents,
or infer missing evidence as favourable.  Preserve the distinction among
repository fact, technical inference, and untested proposal.  Review all
substantive issues; assign severity rather than suppressing lower-severity
findings.  Keep the final response concise enough to be operational.
</boundaries>

<output>
Return these sections:

1. `VERDICT`: exactly one of `APPROVE_DIRECTION`, `REVISE_DIRECTION`, or
   `REJECT_DIRECTION`, followed by a two-sentence rationale.
2. `FINDINGS`: numbered findings with severity `BLOCKER`, `MAJOR`, `MINOR`, or
   `NOTE`; cite file paths and line numbers wherever repository evidence
   supports the finding.
3. `ROLE_AUDIT`: one row each for R1/R2/R3: valid responsibility, invalid
   overlap, most important missing information, and direct falsifier.
4. `CARRIER_DECISION`: choose verified branch, real-transition-only, a concrete
   third variant, or rejection; state why.
5. `REQUIRED_SDD_CHANGES`: the minimum exact changes required before
   implementation.
6. `MINIMAL_PROTOTYPE`: bounded local tests/replays only, with a pass/fail gate;
   no full training.
7. `CLAIM_CEILING`: what may and may not be claimed if that prototype passes.
</output>

<query>
Audit the frozen design candidate now.  Treat the requested three independent
roles as a hypothesis to attack, not an outcome to preserve.
</query>
