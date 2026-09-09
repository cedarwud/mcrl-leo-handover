Workspace: the current directory, `/home/sat/mcrl-v025-c1c2suff-ws`. Read-only access to sibling `mcrl-v025-*-ws` workspaces and to `/home/sat/mcrl-v023-codex-audits/parallel-20260909/` is fine. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment, and modify nothing sealed.

`DIAGNOSTIC_NOT_CLAIM`. Design analysis only. No training run, no policy run. Change no constant, threshold, sign, seed, horizon, price, guard or acceptance rule; modify no sealed artefact, manifest, contract or acceptance test.

# The question, and why it is the only one that matters here

The project owner's requirement is fixed and simple: **each of three learned routes must individually raise pooled energy efficiency**, and the ordering full-system > any-two > control must hold. The sealed contract implements this at §C3 as a **neutral-source substitution** experiment: for each named route, that route's training source is replaced by a neutral one while **all heads are retained, updated and deployed**. The arms are the full system, three leave-one-out arms, an all-neutral control, and an external baseline.

The sealed score structure is fixed at §B4 as an identity treated as a known-answer test:

    C1(config) = Σ_{i∈A} d_i ,  C3(config) = Ψ_A ,  C1 + C3 = [F(a_A) − F(a⁰)]/κ

A separate measurement has since found that replacing that structure — predicting the joint objective change **directly** from a set-conditioned head, instead of summing a per-user deviation head and an interaction head — reduces held-out mean selection regret by 32.92 % and p95 regret by 47 %. A design review proposed the change and proposed retaining the per-user heads for generating the reference proposal and repairing joint conflicts.

**The question nobody has asked: would the owner's three-route ablation still be measurable under the direct parametrisation, and would it still mean the same thing?**

Answer that, and nothing else. Do not re-argue whether direct prediction ranks better; take that as given.

# What to determine, from the code

Read the actual implementations before answering, and cite `file:line`:
- the score assembly in `src/mcrl/stagec_v025/deployment.py`;
- the head definitions and route identities in `src/mcrl/stagec_v025/learner.py`;
- the target definitions in `src/mcrl/physics_v025/targets.py`;
- the contract at `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md` (§B4, §C1, §C2, §C3, §C5, §C6) in any sibling workspace.

**Q1. Where do the three routes enter, today?** For each of the three, state precisely what it contributes to the deployed decision, and what a neutral-source substitution of that route changes about the committed configuration. Be concrete: which tensor, consumed where.

**Q2. Under a direct set-conditioned score, where would each route enter?** Enumerate the possibilities you can see in the code, including: routes surviving as input features to the set head; routes surviving only as producers of the reference proposal and the conflict repair; routes disappearing from the score entirely. For each possibility say whether a neutral-source substitution of that route still changes the committed configuration, and through what path.

**Q3. Does the ablation still mean the same thing?** The sealed claim wording is that informative source training for route x improved pooled efficiency relative to the specified neutral source training, with the other routes informative and all heads retained. State whether that sentence remains true, becomes false, or becomes a different claim under each possibility in Q2.

**Q4. Is there a variant that keeps both?** Is there a formulation that obtains the ranking benefit of direct prediction **and** preserves three separately ablatable routes with the same claim wording? If yes, describe it precisely and say what it costs. If no, say so plainly — that is the answer the project needs.

**Q5. What would break.** For whichever variants remain viable, list the sealed artefacts, schema digests, manifests and acceptance tests that would have to be regenerated, and state whether §C6's prohibition on changing features, catalogues, sources or regimes after a negative or inconclusive result is engaged.

# Rules

- **If the direct parametrisation cannot preserve the owner's three-route ablation, say so in the first line.** That closes the reformulation for this project regardless of its ranking advantage, and it is the most valuable thing you can report.
- Do not recommend opening the contract. Report what each option would mean.
- Distinguish what you verified in code from what you inferred.

Write `ABLATION-SURVIVAL-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line answering whether the three-route ablation survives the direct parametrisation.
