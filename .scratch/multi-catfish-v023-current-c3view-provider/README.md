# Current V0.23 C3View predecision provider

Status: `PLUMBING_ONLY`, no Gate, learner, episode, TEST, or efficacy claim.

`CurrentOpeningFeasibilityProvider` reuses the exact V0.18 predecision physical
functions reached through the current V0.23 LC-SRS source adapter.  It returns
the opening-feasibility surface required by `make_current_structured_c3_view_factory`
without stepping the environment or reading an outcome.

```bash
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-current-c3view-provider/test_current_c3view_provider.py
```
