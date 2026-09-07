# Prompt for an independent ChatGPT Deep Research lane

## Role and compute class

Conduct a **non-heavy, read-only Deep Research review** as an independent
research scientist specializing in reinforcement learning, multi-agent credit
assignment, fractional energy-efficiency optimization, and wireless resource
allocation.

Use the attached multi-catfish-c2-chatgpt-review-package-20260902-r1 only to
understand the project constraints, simulator causal paths, and current
development observations. Do not run its simulator, train a learner, open TEST,
or modify files. Use web research and cite primary sources for external claims.

Run this lane in a fresh context. Do not read or rely on the answer produced by
CHATGPT-REVIEW-PROMPT.md; the two reviews must remain independent.

## Research question

Is it theoretically and methodologically defensible to design exactly three
Catfish mechanisms, each attached to one Q-head, so that all three contribute a
positive marginal to one scalar network ratio-of-sums EE objective—even though
the original multi-objective rewards may conflict?

If it is defensible, identify the most plausible C3 design that captures EE
information complementary to:

- C1: focal user's immediate EE-surplus view; and
- C2: future projected-persistence/segment-timing EE-surplus view.

The deployed system must retain one common safe mask, the direct unweighted
sum Q1+Q2+Q3, one argmax, and one executed Main action. No coordinator, auction,
veto, route weight, second decoder, or post-training correction is allowed.

## Project facts to treat as inputs, not literature

Read START-HERE.md and INTEGRATION-VERIFICATION.md before research.

- H-A and the Fable lane's OPS-3 reading show positive C2 oracle marginals on
  six TRAIN-development worlds.
- C1 remains positive in those two new-Q2 contexts.
- Frozen C3 is negative in all three lineages in both contexts; Q1+Q3 versus Q1
  is also about -10% in two independent development blocks.
- These are oracle/development signs, not learned or held-out efficacy.
- The Fable O-arm is not a result of the current exact OPS-3 adapter.
- No C2 is selected and no learner or long training is authorized.

Do not reinterpret these observations as published evidence.

## Required research lanes

### 1. Formal scalar-objective analysis

Starting from a true action advantage A_EE(s,a), analyze when a decomposition

A_EE(s,a) = A1(s,a) + A2(s,a) + A3(s,a)

can make the full argmax at least as good as every drop-one policy. Distinguish:

- exact versus approximate decomposition;
- nonnegative versus strictly positive FULL-minus-DROP marginals;
- redundant components that cannibalize one another's apparent gain;
- harmful components caused by approximation, observability, off-policy
  evaluation, scale, or simultaneous-agent interaction;
- whether some two-head combination may be worse than a singleton while all
  three FULL-minus-DROP conditions still hold.

Provide a short proof, construction, or counterexample for each consequential
claim. Do not equate this scalar-aligned decomposition with simultaneous
improvement of three conflicting legacy rewards.

### 2. Literature grounding

Search and reconcile primary literature on the most relevant concepts,
including:

- fractional programming or fixed-multiplier surplus formulations for energy
  efficiency;
- value decomposition and residual value/advantage learning;
- difference rewards, counterfactual baselines, marginal-contribution credit,
  and multi-agent externality assignment;
- decentralized execution when many agents act on a shared snapshot;
- interference, congestion/load, activation-power, and beam-association
  externalities in wireless or satellite resource allocation;
- failure modes from double counting, nonstationarity, herding, and
  off-policy counterfactual targets.

Prefer original papers, official proceedings, journal versions, standards, and
first-party technical documentation. Use survey papers only to orient the
search or reconcile terminology. For each major conclusion, cite a directly
supporting primary source with title, authors/publisher, year, DOI or stable
URL, and scope limitation.

### 3. Map theory back to the package

Audit whether the current three roles are a plausible non-overlapping
decomposition of one EE advantage or merely three heuristics. In particular:

- identify which parts of bits and network energy C1 and projected-persistence
  C2 already cover;
- identify the remaining action-caused non-focal residual available to C3;
- distinguish immediate physical externality from later policy cascades and
  reward-only handover quantities;
- determine whether that residual is observable at decision time and can be
  learned by one action-aligned Q3 without deployment coordination;
- explain why the existing victim-burden C3 can be negative even if the
  underlying spatial-externality channel is real.

Treat package code/receipts as project evidence and external papers as general
evidence. Clearly label any bridge between them as an inference.

### 4. C3 alternatives

Propose at most three materially distinct C3 mechanisms, then rank them. For
each specify:

- exact physical estimand and sign;
- whether it is an exact component, a difference reward, a residual target, or
  an auxiliary surrogate;
- non-overlap with C1 and C2;
- common lambda0/kappa unit compatibility;
- decision-time action-aligned state;
- outcome-independent Catfish source;
- how it avoids simultaneous-agent herding or stale-background misuse without
  adding a deployment coordinator;
- minimum no-training oracle/falsification test;
- clear stop rule and main scientific risk.

Give one formula-complete recommended C3. Do not repair the observed C3 by
post-hoc sign reversal, Q3 rescaling, rung reselection, seed changes, or relaxed
thresholds.

### 5. Feasibility judgment

Answer separately:

1. Is a three-positive-marginal construction possible in function space?
2. Is it identifiable from the current simulator's physical channels?
3. Is it plausibly learnable and deployable under the fixed architecture?
4. Does current evidence favor normal complementarity/cannibalized gains, or a
   structural reason that one of C2/C3 must be harmful?
5. What evidence would falsify the three-Catfish thesis before expensive
   training?

Do not assign an unsupported numerical probability. State confidence and the
evidence gap that controls it.

## Evidence discipline

- Build a compact claim-to-source ledger while researching.
- Separate formal result, sourced empirical finding, project-specific verified
  fact, inference, and proposal.
- Seek disconfirming as well as supporting evidence.
- Do not cite search-result pages, tertiary summaries, or unverifiable claims.
- Do not claim that development oracle signs prove learned efficacy.
- Do not recommend changing the final EE formula to make the method pass.
- Stop when the central claims have primary support and further searching is
  unlikely to change the conclusion.

## Required response

1. Direct answer
2. Formal possibility and counterexamples
3. Primary-literature synthesis
4. Mapping to C1/C2/C3
5. Ranked C3 designs
6. Formula-complete recommended C3 and no-training test
7. Falsification conditions and research gaps
8. Claim-to-source ledger
9. Final research classification

End with exactly one classification and no text after it:

THEORY_SUPPORTS_THREE_HEAD_SEARCH

THREE_HEAD_POSSIBLE_BUT_C3_IDENTIFIABILITY_UNRESOLVED

TWO_HEAD_MORE_DEFENSIBLE

THREE_HEAD_STRUCTURALLY_UNSUPPORTED
