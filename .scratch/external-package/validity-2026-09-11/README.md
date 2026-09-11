# Package: validity of the "learned EE beam assignment + catfish replay" direction — pre-result artefacts (2026-09-11)

Built for an external reviewer (ChatGPT general mode → `PROMPT-CHATGPT-GENERAL.md`; ChatGPT Deep Research → `PROMPT-CHATGPT-DEEPRESEARCH.md`).
Nothing in this package depends on the 12-run pilot that finished on 2026-09-11; its results are deliberately excluded so the
review is independent of one noisy 3-seed outcome.

## The setting in one page
- Simulator: LEO multi-beam constellation, 100 users, 4 satellites × 7 beams = 28 per-user actions (masked by legality),
  10 decision steps of 30.08 s per episode, Starlink TLE ephemerides, Shannon rate with per-beam bandwidth shared among the
  beam's users (full buffer, no demand cap), consumed power = PA supply power per lit beam (from the beam's `max` user power,
  TDM) + circuit power per beam + baseband per satellite. Handovers cost zero joules. Code: `code/link_budget.py`, `code/step.py`.
- Objective (owner decision, `docs/…CONSTRAINED-ENDPOINT…` + Amendment 2): **pooled EE = Σ bits / Σ joules** over an episode
  set, ratio of sums, subject to a **service floor** (served fraction within −0.5 pp of the no-catfish reference); handover
  rates are reported, not constrained.
- Baseline A0 = MODQN (paper key `PAP-2024-MORL-MULTIBEAM` in the docs; the algorithm lineage is Tajmajer's modular
  multi-objective DQN with decision values, FedCSIS 2018): eq. (16) per-head max, reward 0.5·r1(EE) + 0.3·r2(handover
  penalty: −0.5 same-satellite, −1.0 satellite change) + 0.2·r3(load), gamma 0.9. `code/modqn.py`; deviations from the paper
  in `docs/DEVIATION-REGISTER.md`.
- New learner A1 (`code/cf_ratio.py`): three Q-heads (bits B, energy E, handover H) on the 112-dim observation + a
  remaining-steps feature, greedy `argmax_a [Q_B − eta·Q_E]`, `eta` = Dinkelbach price (held for 500 episodes, then set from the
  policy's own calibration EE at 500 and 750), gamma 1, shared continuation bootstrap, `E_u = P_sys·dt/U` (equal share).
- Catfish arm A2 = A1 + static replay pools from three scripted rules (`A m=2dB` hysteresis, `A m=12dB` hysteresis,
  `B1_NO_NEW_BEAM` consolidation; `code/cf_sources.py`), 5 rows each in every 128-row minibatch, raw rewards, no imitation loss.
  A3 = A1 + three random-legal pools (null control). Pilot: 3 seeds × 1000 episodes per arm (results excluded here).
- Key pre-result measurements (pinned TLE archive `427e6a91…`, 24 calibration episodes, per-episode reseeded, consumed `max`
  power, host sat; `docs/CF3-PILOT-PROGRESS-lines1-148-prelaunch.md` lines 48–62): `A m=2dB` 112.20 Mbit/J (62.98 lit beams,
  2.8926e6 J), `MAX_NOMINAL_GAIN` 110.51, `B1_NO_NEW_BEAM` 104.19 (38.57 beams, 1.7867e6 J), `A m=12dB` 100.99, frozen
  9000-episode MODQN 93.90 (66.63 beams, 3.0011e6 J), random 51.87. A probe found the `eta·E` term changed the learner's argmax in
  0 of 240 decisions (`reports/CF3-CODE-REVIEW…`).

## How numbers may and may not be compared (read `docs/RESULTS-REGISTRY.md` §0)
- Two TLE archives exist: **pinned `427e6a91…`** (the pilot, the premeasure block above) and **unpinned local `e07f3e1e…`**
  (`reports/FEASIBLE-FRONTIER…`, `CATFISH-SCREENS…`, `BEAM-POWER-ACCOUNTING…`, `CAP-PENALTY…`). Numbers from the two archives
  differ by ~1 % and must never sit in one comparison.
- Sibling-project EE values (146–620 "Mbit/J") use a radiated-only denominator and are not comparable (`reports/EE-MAGNITUDE…`).
- Non-learned rules are diagnostics; the owner's success gate is "beat baseline MODQN" only.

## File map
- `docs/` — handoff, document status, results registry (503 rows), the declaration + amendments + implementer's addendum,
  the pre-result forecast (lines 1–57), endpoint and rulings, errata 25/26/27/28, deviation register.
- `reports/` — measurement reports (each states its evidence tags and archive), the pilot code review, a Gemini blind review
  (verdict DEAD-PATH) and the controller's check of that review's numeric errors + a bits-per-beam decomposition.
- `code/` — physics (`link_budget.py`, `step.py`, `interference.py`, `antenna.py`, `constants.py`, `action_contract.py`,
  `d2.py`, `energy_efficiency.py`), baseline `modqn.py`, the ratio learner `cf_ratio.py`, rules `cf_sources.py`, pilot driver
  `run_cf3_pilot.py`, evaluators `cf3_eval.py` / `b0_pooled_ee_eval.py`, pools `cf3_pools.py`.
- `briefs/` — the internal blind-audit brief and the ceiling-measurement brief.
