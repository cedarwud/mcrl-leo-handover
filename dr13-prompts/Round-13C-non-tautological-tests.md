# Round 13C (Q&A): how do you write a test that proves a feature set is sufficient?

## What happened
A sealed contract in my project required that a model's encoder receive "the pairwise coupling terms among the affected resources, not only a scalar summary — a summary can hide exactly the difference that flips the outcome". The same amendment said an acceptance test must be extended so that "the pair must be separable with the full context and provably ambiguous when the coupling block is removed".

The code computed the pairwise terms and then summed them into a scalar before the model saw them. The acceptance test that was supposed to catch this contains zero mentions of the coupling terms. What it does instead is construct an input labelled "synergy", train on it, and assert the model predicts synergy. It passed for months while the requirement was violated.

## The general question
That test cannot fail for the reason it exists. I want to know how to systematically avoid writing tests of that shape, because I suspect I have more of them.

1. **Is there a name for this failure mode**, and an established taxonomy of tests that pass regardless of whether the property holds? I know about tautological assertions and about tests that assert on their own fixtures, but I want the fuller picture.

2. **How do you test feature sufficiency?** The strongest form I can think of is: construct two inputs that are byte-identical without the feature and have opposite correct answers, then assert that with the feature they are distinguishable and without it they are literally the same object, so no model can separate them. Is that the established technique, does it have a name, and what are its limits?

3. **Mutation testing and its relatives.** Would mutation testing have caught this, given that deleting the feature block would not have failed any test? What is the practical cost of applying it to a research codebase, and are there lighter-weight approximations that catch most of it?

4. **Contract-to-test traceability.** My contract is a sealed document in prose and the tests are separate. Is there an established discipline for proving that every clause of a specification has a test that can actually fail when the clause is violated, short of formal methods?

5. **Auditing what I already have.** Given a test suite of a few hundred tests written alongside the code by the same process, what is the highest-yield way to find the ones that cannot fail? I would rather spend a day finding them than another month trusting them.

## Why I am asking
This defect plausibly explains months of null experimental results: the model could not represent the mechanism because its features had been collapsed, and the test that guarded the requirement was decorative. I want the process fix, not just the one repair.
