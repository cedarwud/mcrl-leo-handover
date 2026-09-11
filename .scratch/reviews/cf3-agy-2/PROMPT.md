You are a fresh-context reviewer from a different model family. Read the ACTUAL code yourself; do not rely on any summary. Do not edit anything. Be fast and concrete: this review gates a training launch.

Repository worktree: /home/u24/papers/mcrl-leo-handover-cf3 (branch cf3/pilot-20260911). Review ONLY this diff: `git -C /home/u24/papers/mcrl-leo-handover-cf3 diff e8a04ccf..f297334e` (commits e28100b1, 5938450b, 99252ef8, d04d9dbe, f297334e). An earlier review of the code up to ca678414 found no invalidating defects; this diff adds launch-control fixes and a design change.

What the diff is supposed to do:
1. Learning-check failure path: the episode log is persisted before the episode-500 gate runs; the saved status, resume state and log count agree; no synthesised episode count.
2. DECISION.json has a single writer (or a lock), PID-unique temp files, and records code commit, calibration sha, TLE sha, A1 seed values, the random reference and the gate episode; a stale decision whose fingerprint does not match is rejected. A missing decision because an A1 run died must be a loud failure/wait, never a silent "stopped" that the launcher treats as complete.
3. The resume fingerprint and a RUN-MANIFEST.json include the code commit and sha256 of the core files (cf_ratio.py, cf_sources.py, driver, declaration + amendments, pool generator); launch and resume fail closed on mismatch.
4. A process-level stop/resume test exists and exercises the real driver.
5. The launcher detects live runs by PID plus command line and cwd, fails loudly if a process fails to start, and launches exactly 12 planned runs (A0/A1/A2/A3 x seeds 0-2).
6. Amendment 3 (read /home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-3-PREGENERATED-SOURCE-POOLS-2026-09-11.md): catfish sources (and NULL3 random sources) are pre-generated pools of 100 episodes (100,000 transitions) per seed per source, on pool seeds disjoint from training, calibration and evaluation seeds; each source buffer is loaded once and never appended; minibatch stays 113 main + 5 per source; loading pools does not touch the main environment RNG; A2 and A3 pools are generated identically except the policy.

Look for: anything that would make the 12-run batch produce a wrong, unfair or uninterpretable result; seed-range collisions (one collision between pool mobility seeds and env seeds was already found and fixed in d04d9dbe — check there is no other); pools that are not what A2/A3 actually load; any path where a failure is swallowed; tests that pass without testing the property.

Output: findings with severity (INVALIDATES / BIASES / COSMETIC), concrete failure scenario, file:line; verified-by-reading vs inferred. First line: one bold sentence with the count of INVALIDATES and BIASES and whether the launch may proceed. Write to /home/u24/papers/mcrl-leo-handover/.scratch/reviews/cf3-agy-2/CF3-AGY-REVIEW-2.md
