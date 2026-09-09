# Does the test harness actually report failure? One hour, and it must run first.

`DIAGNOSTIC_NOT_CLAIM`. Budget 45 minutes.

Before trusting any test in this project, establish that the harness tells the truth. A suite of 2,122 tests recently ran green while a sealed contract clause was being violated, so the baseline assumption is that green means nothing until shown otherwise.

Workspace: make a scratch copy so nothing here is left modified. `cp -a /home/sat/mcrl-v025-pilot-ws /home/sat/mcrl-v025-harness-ws` then `git init` and commit it. **Never modify `/home/sat/mcrl-v025-pilot-ws` itself; two other jobs are editing it right now.** Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. At most 2 processes, `nice -n 15`.

## What to check
1. **Baseline truth.** Run the stage-C and physics test subsets. Record collected, passed, skipped, xfailed, errors, and the exit status. Report how many tests are **skipped or xfailed**, since a skipped test is not a passing test and a large skip count changes what green means.
2. **Failure is visible.** Insert `assert False, "harness probe"` into five separately chosen critical tests, one at a time, and confirm each run reports a failure and a non-zero exit. Name the five. This proves only that the test executes and that failure surfaces, not that its original assertion was useful.
3. **The right code is under test.** Confirm the imported `mcrl` package resolves to this workspace and not to `/home/sat/mcrl-leo-handover/src` through the editable install. Print the resolved `mcrl.__file__`. This has bitten this project before.
4. **Stale artefacts.** Identify any test that reads a cached feature file, checkpoint, or fixture from disk rather than constructing it, since such a test can pass against code it never ran. List them.
5. **Extreme mutation on three critical helpers.** For three functions whose correctness matters scientifically, make each return a constant or become a no-op, and record whether any test fails. A helper that can be emptied with the suite still green is pseudo-tested. Choose the helpers from the coalition feature path, the score decomposition, and the service guard.

## Report
`HARNESS-AUDIT-2026-09-09.md` in the workspace root, printed as your final message. Give the baseline counts, the five probes, the resolved package path, the stale-artefact list, and the three extreme mutations with their outcomes. Lead with a one-line verdict on whether the harness can be trusted to report failure at all.
