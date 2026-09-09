# Round 13A (deep research): learning a set-level interaction term that is a residual

## The problem
I need to train a model to predict the **interaction** in a coalition value, and every attempt so far has failed. I want to know whether the way I have set it up is a known-hard or known-broken formulation, and what the established alternatives are.

## Setup
About 100 agents each choose one of a few dozen discrete actions. A joint assignment `a` has a scalar value `F(a)`. Fix an anchor `a0`. For a coalition `A` moving together to `a_A`:

```
d_i   = F(a_i, a0_-i) - F(a0)        each member moving alone
Psi_A = F(a_A) - F(a0) - sum_i d_i   the interaction residual
```

I train a set-conditioned head `Psi_hat(Z, a0, A, a_A)` to predict `Psi_A`, anchored so that it returns exactly zero for the empty set and for singletons. The coordinator then uses it to choose a coalition.

## The questions

1. **Is regressing on a residual the right formulation at all?** `Psi` is a second-order difference of a quantity whose first-order parts are learned or evaluated separately. In my data `Psi` is often small compared with `F`, so the target is a difference of large similar numbers. Is there a standard treatment of this variance and identifiability problem, and is there a better parameterisation, for example learning `F` directly and deriving the interaction, or learning the Mobius coefficients?

2. **What architectures actually work for set-valued inputs with pairwise structure?** The value depends on pairwise couplings between members and shared resources, not only on member-wise features. Deep sets and their sum-decomposable form cannot represent pairwise interaction by construction. Set transformers and graph networks can. What is the evidence on which works for this shape of problem, and what are the failure modes?

3. **Feature sufficiency, which is my live concern.** I have just found that my encoder received only a **scalar sum** of the pairwise coupling terms rather than the terms themselves. Is there a principled way to prove that a feature set is sufficient to represent a target set function, rather than discovering insufficiency after months of null results? I am looking for something constructive, for example an identifiability argument or a designed pair of inputs that must be indistinguishable without the feature.

4. **Training signal.** My labels come from exactly evaluating the four counterfactuals per coalition, which is expensive, so I have far more anchors than labelled coalitions. Is there a standard way to get more signal per evaluation, for example by exploiting the Mobius structure so that one coalition evaluation constrains many subsets?

5. **A specific symptom I want diagnosed.** My trained selector picks the all-agents coalition at every anchor and never a small one, even where small profitable coalitions provably exist. Given that its features were the sums described in question 3, is a near-monotone-in-size feature signal the sufficient explanation, or does this symptom also point at something else, such as the head's scale at low training epochs, or the selection rule?

## What I will do with the answer
Decide whether to keep the residual formulation with better features, or to change the target and the architecture before spending more compute. Please distinguish established results from your own inference, and say when the honest answer is that this is an open problem.
