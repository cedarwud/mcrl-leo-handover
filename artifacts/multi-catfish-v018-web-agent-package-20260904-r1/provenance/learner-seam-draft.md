# V0.18 relational Q3 learner seam (provisional)

Status: IMPLEMENTATION-ONLY DRAFT. NOT AUTHORITY. DO NOT TRAIN.

This file fixes one public seam before any V0.18 outcome is opened:

```text
RelationalZRC3QNetwork.forward(
    action_context,                 # [N,A,7]
    victim_tokens,                  # [N,A,V,6]
    action_mask,                    # [N,A]
    victim_mask,                    # [N,A,V]
    positive_credit_compatible,     # [N,A]
    reference_actions,              # [N]
) -> Q3                              # [N,A]
```

Completion criterion: a single shared victim scorer produces one finite,
native-mask-preserving, reference-centred Q3 surface; victim permutation leaves
the surface unchanged; reference actions are exactly zero; masked victims and
illegal actions cannot affect the result; positive victim predictions count
only when the predecision compatibility bit is true; negative predictions
always count.  No environment, realised counterfactual, RNG, Q1, Q2, action
decoder, learner update, or TEST data may cross this seam.

The module is provisional preparation only.  It is not authorized for source
learning unless the frozen V0.18 analytic diagnostic returns
`PASS_ANALYTIC_DIAGNOSTIC` and a separate learner contract is frozen before any
learner outcome.
