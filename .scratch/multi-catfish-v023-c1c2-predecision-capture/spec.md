# V0.23 C1/C2 predecision capture bridge

## Completion criterion

The new bridge must expose deterministic, outcome-blind helpers that:

1. identify only physical Main departures from contemporaneous slot tables;
2. reproduce the frozen C2 hold-if-legal, otherwise maximum candidate-SINR
   non-Main-rival rule with canonical ties;
3. emit the exact V2 capture shape and C2 anchor digest consumed by
   `materialize_v023_c1c2.py`;
4. preserve TRAIN-only provenance and refuse forbidden outcome/TEST fields; and
5. provide a lazy server entrypoint that performs no work on import and refuses
   to overwrite a capture; and
6. authenticate and merge exactly worlds `2026121705` through `2026121712`
   before global source selection, with panel neutral seeds supplied explicitly
   by the later frozen learner-screen contract.

The runtime path may reuse the authenticated V0.23 source adapter only after
an explicit launch.  It must not perform learner updates, episode-policy
training, open TEST, or persist candidate outcomes.
