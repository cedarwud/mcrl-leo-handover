You are an independent reviewer with no prior involvement in this project. You have one directory
of evidence, `./evidence/` (read `./evidence/README.md` first). Work only from it.

# BLIND — what claim structure does the evidence actually support?

A research project builds a learned handover / beam-assignment method for multi-beam LEO satellites.
Its **target metric is system energy efficiency, EE = pooled decoded bits / pooled system joules**.
The method adds **three learned "routes" (C1, C2, C3)** on top of a baseline. The owner's requirement
is that the method's three routes each raise EE.

The baseline is a multi-objective DQN whose reward has three components: **r1 = EE** (a per-link
decomposition summing to system EE, paper eq. 3.25, `r1 = sum x * eta`), **r2 = -Psi** (handover),
**r3 = -U** (negative occupancy of the user's beam, i.e. load balance). See
`evidence/declarations/CONTROLLER-QUESTIONS-2026-08-22.md` and `evidence/code/`.

The routes' declared definitions and survival criterion are in `evidence/declarations/` (the paper
authoring contract, the stage-C contract, and the physics declarations with their amendments).

## Answer, based ONLY on the evidence

1. **The strongest defensible scientific claim** this project could make about a three-route method,
   stated as the claim a careful reviewer would accept.
2. **The claim structure the evidence supports** — for example (examples only, not suggestions):
   three routes each adding EE additively; routes that are redundant estimators of one quantity;
   genuinely distinct objectives with trade-offs; a two-route method plus a negative result; something
   else. Say which evidence decides it.
3. **The evidence that is missing** for the strongest claim, and the single measurement that would
   most change your answer.
4. **What the project must not claim.**

Propose the structure the evidence supports, not an attractive one — including "the evidence
supports no three-route claim" if that is where it leads.

## Standards

- Separate what the evidence **establishes**, what it **suggests**, and **your inference**.
- Distinguish learner-free measurements from measurements on trained models, and in-sample from
  out-of-sample (one report finds all route scores so far are in-sample).
- Mark any literature appeal you cannot verify from the bundle as unverified.
- Run no experiments. Read and reason.

Write your answer to `./BLIND-REVIEW.md`, first line one bolded sentence stating the strongest
defensible claim and the claim structure the evidence supports; then your full reasoning.
