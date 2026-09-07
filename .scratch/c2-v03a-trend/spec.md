# C2 V0.3A intermediate-trend launcher specification

Completion criterion: an authority-bound public arm launcher can execute the
V0.3A five-arm design at 1,500 or 3,000 episodes with the frozen formal
training schedule, records the verified C1 EXP prefill for every treatment
arm, emits a loadable Main checkpoint every 100 episodes, and labels C3 routing
as developmental until its Main-consumer gate is closed.  A 100-user Ubuntu
throughput smoke must exercise the same path before either 1,500-episode matrix
is launched.

Public seams under test:

- `run_c2_v03_episode_loop(..., c1_corpus_manifest=...)` for the treatment
  runtime and exact-resume carrier;
- `validate_v03a_trend_authority(...)` for fail-closed experiment identity;
- `c2_v03a_trend_arm.py` CLI for one authority-bound arm;
- `c2_v03a_trend_matrix.py` CLI for the matched five-arm queue and receipt.

The 1,500/3,000 outputs are one-seed intermediate trend screens.  They are not
Chapter 5, formal efficacy, deployment, or 9,000-episode authorization.
