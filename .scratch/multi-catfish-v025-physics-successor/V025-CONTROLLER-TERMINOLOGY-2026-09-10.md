# Controller note — what to call the thing the third route predicts, and why "coordination" was the wrong word
Recorded 2026-09-10 after the owner said they had understood the design as three independent components and asked why coordination kept appearing. The confusion was mine to fix: I used one word for three different things all day. `DIAGNOSTIC_NOT_CLAIM`.

## The structural fact the owner needed
The three routes are **not three parallel, same-shaped things**:

- the first and second are **per-user** — they score each user's candidate action on its own, and the reference proposal is a per-user argmax over their sum;
- the third predicts **Ψ = ΔF(A) − Σ dᵢ**, which is *defined* as what is left over after the per-user terms are summed.

**If users were independent, Ψ would be identically zero and the third route would have nothing to predict.** So the interaction is not an extra component bolted on — it is that route's entire job description.

## The three things I called "coordination"
1. the third route itself, which predicts the interaction residual;
2. joint multi-user moves against one-at-a-time moves, which is a property of the **search**, not of any component;
3. the ranking rule that combines the three heads' outputs.

These are different objects. Using one word for all three is why the owner could not tell whether coordination was part of the design or something I had introduced.

## Better names, by layer
**The estimand — what the third route predicts.** *Interaction term* is the general-purpose name and fits our eight arms exactly, since they are the complete 2³ factorial. In cooperative game theory the same object is the **Harsanyi dividend**, the Möbius transform coefficient, and for coalitions of size three or more our Ψ is the sum of all Möbius coefficients above first order. Information theory calls the positive case **synergy**. Economics and networking call the cross-user part an **externality** — which our own target-design review already used, as *cross-user externality*.

**The mechanism — why interaction exists here.** **Inter-user coupling**, and it has two concrete sources in this system: equal-airtime sharing inside a beam, where one more occupant raises the required spectral efficiency for *everyone* in that beam; and co-channel interference between beams through the cross-gain matrix. The solver is literally a **coupled power fixed point**. This name is better than "coordination" because it names the cause rather than the response.

**The comparison — joint against unilateral.** The unilateral certified endpoint is a **Nash equilibrium** of the association game: no single user wishes to deviate alone. The bounded joint optimum is the coordinated optimum over that candidate family. The gap between them is an instance of the **price of anarchy**.

That framing also explains the magnitude we measured rather than excusing it. Gaps of a few per cent between a converged equilibrium and the coordinated optimum are **typical** for association and load-balancing games. Our corrected span of roughly one per cent is what that literature would predict, and the load-regime sweep's failure to enlarge it — even pushed to two hundred users and a rate target that reaches 3.36 against a table maximum of 3.71 — is consistent with it being a property of the problem class rather than of our operating point.

**The architecture.** A **permutation-invariant set head**, in the Deep Sets and Set Transformer line, which is the literature the decomposition-conditioning round already cited.

## Recommended usage
| what is meant | say |
|---|---|
| the quantity the third route predicts | **interaction term**, noting it generalises the Harsanyi dividend |
| why interaction exists | **inter-user coupling** — shared airtime within a beam, co-channel interference between beams |
| the joint-versus-unilateral gap | the efficiency gap between the unilateral (Nash) fixed point and the coordinated optimum, an instance of the price of anarchy |
| the third head's architecture | permutation-invariant set head |

"Coordination" is not wrong, but it is ambiguous across all four rows, and I used it that way for a full day.
