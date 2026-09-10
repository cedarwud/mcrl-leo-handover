Completed the 20-anchor diagnostic.

Key verified findings:

- Exact Ψ changed the argmax at **14/20 anchors** and **48/80 anchor-seed decisions**.
- Learned Ψ changed it at **20/20 anchors** and **75/80 decisions**.
- Legal catalogue sizes: **948–1,000** rows; none were singleton catalogues.
- Context was absent for **15,532/19,620 rows (79.164%)**.
- No top-two ranking was within 1 ULP; **zero changes were tie-break flips**.
- Every detected change moved the committed 48-boundary capped B/E pair.
- Current v2 coalition encoding cannot directly restore the saved v1 learned C3 checkpoints; the authenticated execution-era v1 snapshot was used read-only and this is recorded as an owed repair.

Artifacts:

- [C3-ARGMAX-REACHABILITY-2026-09-10.md](/home/sat/mcrl-v025-coalgen-ws/C3-ARGMAX-REACHABILITY-2026-09-10.md)
- [results.json](/home/sat/mcrl-v025-coalgen-ws/.scratch/c3-reach/results.json)
- [measurement harness](/home/sat/mcrl-v025-coalgen-ws/.scratch/c3-reach/measure.py)

Internal reaggregation, deterministic anchor-0 replay, hashes, process limits, interpreter, niceness, and thread constraints all passed verification.
