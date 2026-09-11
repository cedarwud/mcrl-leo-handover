# Prompt for ChatGPT (general reasoning mode) — paste after uploading `mcrl-validity-package-2026-09-11.zip`

You are an independent, first-principles reviewer with no prior involvement. Argue against the design wherever the evidence allows, then give the strongest fair counter and a verdict. Read the attached package yourself; do not trust any summary in it — including the controller's own documents, which are one party's interpretation. Where two documents disagree, say so.

## The question (the owner's words)

> 這整個設計真的是可行、合理的嗎 … 以目前設計的 ee 公式、reward function 還有整個專案的物理環境跟參數設定來說，這幾個演算法是真的能夠提升 ee 值的嗎 … 而不是毫無根據的在亂設計，盲目的做測試跟訓練，失敗後再在那個小框框裡面找錯誤 … 其實很可能一開始就是在走一條死的路

Is the box itself right? Not "how should we react to a result", but "can this formulation, with this physics, this reward and these learners, raise the declared objective at all — or was it a dead path from the start?"

## What is in the package (read in this order)

1. `README.md` — the setting in one page, and how numbers may and may not be compared (two TLE archives; never compare across them).
2. `docs/HANDOFF-2026-09-11.md` §2–§5, `docs/DOCUMENT-STATUS.md` §0 — what is being tested and which documents are in force.
3. The design under test: `docs/V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md`, Amendments 1–3, `docs/DECLARATION-ADDENDUM.md` (binding implementation choices), `docs/V025-CONTROLLER-FORECAST-…-lines1-57.md` (the controller's own pre-result forecast and blind spots).
4. The endpoint and rulings: constrained endpoint, errata 25/26/27/28, penalty ruling, "catfish attaches to MODQN", plan, evaluation contract, B0 ruling, catfish-screens record.
5. Measurement reports (no training in any of them; each carries its own evidence tags and TLE archive): `reports/FEASIBLE-FRONTIER…` (rule frontier), `CATFISH-SCREENS…` (representability), `BEAM-POWER-ACCOUNTING…` (power model), `EE-MAGNITUDE-RECONCILIATION…`, `CAP-PENALTY…` (pooled EE is degenerate without a service floor), `B0-CORRECTED-BASELINE…`, `CONCEPT-HARVEST…`, `DQFD-FAMILY-GROUNDING…`, `CATFISH-MECHANISM-FACTS…`, `ACRM-PROVENANCE…`, `CF3-CODE-REVIEW…` (contains the 0-of-240 argmax probe). `docs/RESULTS-REGISTRY.md` §0 lists the condition traps.
6. **The code is the ground truth for the physics and the learners**: `code/link_budget.py` (rate; beam, supply, fixed and system power), `code/step.py` (`_resolve_physics`, `evaluate_actions`, served/outage, handover classes), `code/interference.py`, `code/antenna.py`, `code/constants.py`, `code/energy_efficiency.py`, `code/modqn.py` (baseline A0, eq. 16), `code/cf_ratio.py` (the ratio learner A1–A3), `code/cf_sources.py` (the three rules), `code/run_cf3_pilot.py`, `code/cf3_eval.py`, `code/b0_pooled_ee_eval.py` (evaluation estimand).
7. Two prior reviews, to be checked rather than trusted: `reports/VALIDITY-AUDIT-AGY-BLIND-…` (a Gemini review; verdict DEAD-PATH) and `reports/CONTROLLER-CHECK-…` (the controller's list of that review's verified numeric errors, plus a bits-per-beam decomposition of the pinned-archive rules).
8. `briefs/` — the brief given to the internal blind auditor and the brief of a running ceiling measurement (centralised Dinkelbach coordinate ascent with a service floor). Comment on whether that measurement is the right instrument.

Deliberately **not** included: any result of the 12-run pilot that just finished. Please reason without it.

## Answer these, tagging each claim [V] verified in the package / [D] derived arithmetic / [I] inferred / [R] relayed from outside knowledge

A. Is the objective well-posed and improvable by a policy? (pooled EE = Σ full-buffer Shannon bits / Σ consumed joules over 10 steps × 30.08 s × 100 users; beam assignment as the only action, 28 masked per-user actions; no power control; zero-joule handovers; equal-share energy label `E_u = P_sys·dt/U`; service floor −0.5 pp; handover only reported.)
B. Where would EE headroom physically come from? Use one archive at a time (the pinned-archive block in `docs/CF3-PILOT-PROGRESS-lines1-148-prelaunch.md` lines 48–62 gives EE, joules, beams, served, handover per rule). Decompose into bits / joules / lit beams; compute marginal EE of the beams separating `B1_NO_NEW_BEAM` from `A m=2dB`; relate to the power model in `code/link_budget.py`; say what the lever is and whether a per-user policy on the 112/113-dim observation can pull it. Check the controller's decomposition table in `reports/CONTROLLER-CHECK-…` and say whether you agree.
C. The ceiling: nothing measured yet on this harness. Is the planned centralised search the right instrument? What outcome would make the direction dead / alive?
D. Can the ratio learner reach any headroom? (three heads, argmax `Q_B − eta·Q_E`, eta fixed to episode 500 then set twice from the policy's own EE, gamma 1, shared continuation bootstrap, 10,000 updates in 1000 episodes; equal-share `E_u` identical across users — the `eta·E` term changed the argmax in 0 of 240 probed decisions). Is the per-user argmax of a system-level ratio identifiable at all? What separates "under-optimised" from "misaligned" from "unrepresentable", given the frozen 9000-episode MODQN reached 93.9 M against a one-line rule's 112.2 M (pinned archive, same episodes)?
E. Do demonstration / competitive-replay mechanisms (DQfD, R2D3, CER, JSRL, the "catfish" lineage) have evidence of gains in a dense-reward, 10-step, near-myopic, 28-action problem? As implemented here they are static replay pools (15 of 128 minibatch rows, raw rewards, no imitation loss). What is the strongest prior for "no effect"?
F. Is "beat baseline MODQN (eq. 16, r1/r2/r3 0.5/0.3/0.2, gamma 0.9)" a meaningful success gate if it can be met by dropping `r2`/`r3`? What claim would survive peer review; what would a referee demand beside A0?
G. Claims table: ≥ 12 load-bearing claims, each measured / inferred / assumed, with the artefact.
H. Dead-end risks, each with the single cheapest measurement that settles it.
I. Verdict: SOUND / SOUND-WITH-NAMED-FIXES / UNDECIDABLE-UNTIL-<measurement> / DEAD-PATH — and if dead or shaky, the better-posed problem (objective, action space such as power control or beam sleep, horizon, baseline, and what would make RL necessary at all rather than a one-line rule). Say plainly if the honest paper is "a hysteresis rule beats MODQN on EE".

Write the answer in English with a short Traditional Chinese executive summary at the top. Quote numbers only with their conditions (harness, power accounting, host + TLE archive, estimand, n).
