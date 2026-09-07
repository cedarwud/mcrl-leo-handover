# V0.14 learner tracer

Public seams:

1. A route-local action-set scorer maps one feature-major state matrix and an
   explicit legal-action mask to one 28-action Q surface.
2. A route-local pairwise learner updates exactly one independent head from an
   `EEAxisPairBatch` using the frozen normalized pairwise target and gauge.

Completion criterion: the same public learner supports the 448-dimensional
Q2 state (16 action-local features, no globals) and the 287-dimensional Q3
state (10 action-local features and 7 globals), passes permutation/masking,
fit, and checkpoint tests, and does not modify or construct Q1.
