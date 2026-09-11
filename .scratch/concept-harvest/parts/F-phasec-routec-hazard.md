# Cluster F — phase-C forward design, route-C "newalgo", hazard/criticality lineage (old project extraction)

Extractor: read-only worker, 2026-09-11. Old repo root = `/home/u24/papers/modqn-paper-reproduction` (abbrev `OLD/`).
Some load-bearing run records live in the sibling workspace `/home/u24/papers/fable/` (abbrev `FABLE/`), cited
by the old repo but not inside it; I read only the cited sections.
Convention: "records SAY" = quoted/cited; **[I]** = my inference. Dates are 2026.

Common old-env facts (apply to every family_b run below unless stated):
- env = `family_b` (Walker-δ 53°, 180/9/1, h=780 km; Earth-fixed hex cells R≈22.6 km, FR3 3-colouring; SINR with
  FSPL + RX pattern `G_rx(α)=clip(32−25log10 α,−10,35) dBi` + Rician K=20 dB; hard cap K=3 users/beam (over-cap →
  `cap_bump` → r1=0); 28 action slots = 4 window-rank × (own cell + 6 neighbours); episode = 10 steps × 1 s;
  serving window selected at reset and frozen for the episode). Source: `OLD/archive/thesis-route-c/thesis-narrative-restored-2026-07-17/00-newalgo-overview.md:74`,
  `OLD/analysis/family-b-collapse-diagnosis/pivot-mechanism-feasibility.md:95-99`, `env-misdesign-and-redesign-direction-2026-06-19.md:16-23`.
- backbone = Sun2024 MODQN: 3 per-objective DQN heads, linear scalarisation Ω=[0.5,0.3,0.2], **per-user
  independent argmax** over shared Q (`00-newalgo-overview.md:83`; `pivot-mechanism-feasibility.md:34-41`).
- disease: B0 3/3 seeds collapse to one beam (modal 0.996–1.000, active 1.00–1.03, M1 ≈1500 Mbps ≈26% of RANDOM)
  (`reconciled-direction-rec-v3-2026-06-19.md:29-31`; `FABLE/p0-ledger.md:121-132`).
- trainer lr for these B0 runs: not stated in the files I read in this cluster [I: the later root-cause note blaming
  lr=0.01 is outside this cluster; the env-foundation dir contains separate `…lr001…`, `…lr0003…`, `…lr003…` preregs,
  i.e. lr was later swept].

---

## Part 1 — Route-C "newalgo" (Criticality-Aware Multi-Catfish MODQN)

**What "newalgo" is (records SAY):** "我的演算法 = Criticality-Aware Multi-Catfish MODQN" — one principle ("exogenous
geometric criticality", ephemeris-derivable, zero-learning, deployment-available) injected at 3 points: ① state
(Claim A), ② catfish replay routing key (Claim B, the only headline), ③ catfish reward shaping (geometry-PBRS
replacing ACRM) (`00-newalgo-overview.md:18-33`). Internal code names PED-Strat / B3h (`00-newalgo-overview.md:55`).
Backbone MODQN is "G1-locked", untouched; the catfish wrapper is training-time only, deploy = main per-user argmax
(`02-core-algorithm.md:28,85-107`; `03-catfish-vs-newalgo-diff.md:41`).
**What happened to it:** the whole folder is now "ARCHIVED / SUPERSEDED … not the current manuscript, formula,
experiment, or implementation authority" (`thesis-narrative-restored-2026-07-17/INDEX.md:3-5`). Its framing was
"READINESS-ONLY … B3f/B3h/esc … gated, prereg R-01..R-08 未跑" (`00-newalgo-overview.md:5`). The B3h heavy pilot was
never run; pre-flight measurements killed its published keys (see F-3), the pivot-feasibility review judged the
catfish/c_k/B3h lever "same wall, LOW odds" (`pivot-mechanism-feasibility.md:56-76`), and on 2026-06-19 the line was
superseded by the env-redesign reframe (`env-misdesign-and-redesign-direction-2026-06-19.md:3-6`: "This SUPERSEDES
the family_b Option-1 / Track-B / symmetry-breaker / v2+v3 reconciliation line").

### F-1. Claim A — analytic geometric criticality features in state (B1 arm; old label "hazard state augmentation", "Temporal Hazard State")
- mechanism (one line): append 3 deterministic ephemeris features per candidate — F1 residual visibility time
  `min(τ_exit,T_cap)/T_cap`, F2 co-channel alignment forecast `max_{δ∈[0,H]} [G_rx(α_i(t+δ))−G_rx(α_i(t))]`, F3
  elevation rate `ė/ė_max` — to the baseline 5B-dim per-user state via a sibling encoder with disabled-parity.
- intervention point: representation
- defined in: `OLD/archive/thesis-route-c/thesis-narrative-restored-2026-07-17/01-core-formulas.md:134-155`; algorithm `02-core-algorithm.md:63-76`; code `FABLE/r3fixed/sibling/hazard_features.py` (cited `01-core-formulas.md:136`).
- run status: built (sibling module, tests); **B1 never trained as a heavy arm**; ran only as cheap eval assays
  (B0-policy-gap separability assay, U400, 440²/460² band, seeds not stated in excerpt; pre-flight degeneracy sweep
  seeds {42,137,271} × 48 orbital phases × U=100 = 14,400 samples, `FABLE/sdd-b3h-hazard-keyed-routing-DRAFT.md:182-184`).
- run conditions: family_b / "r3fixed cap_bump band" regime (larger-geometry 440–460², U400) for the assay; metric =
  directionless Mann-Whitney AUC of hazard summaries for planner-bumped vs served users, frozen τ_orth=0.55; no
  learning (no lr); features computed with window membership **area-global, frozen per episode**.
- recorded outcome: "best directionless AUC ≤ 0.543 over all 4 band points (< frozen τ_orth 0.55) … Mechanical verdict
  **O-NEG-orth**" (`FABLE/r3fixed/largergeo-regime-prereg.md:127-129`). codex-blessed wording: "closes the cheap
  B1-hazard cap_bump separability lever, not hazard generally and not all possible trained B1 uses … r1-EE / r2-HO
  … remain open-but-unevidenced" (`…:141-148`). LATEST: `pivot-mechanism-feasibility.md:52` table lists "B1-hazard
  (FD-4 O-NEG)" as a closed/dead lever; `track-b-strategic-rec-2026-06-19.md:91` counts "B1-hazard" as the 1st of the
  "static eats it" streak; `env-misdesign…-2026-06-19.md:113-116`: "F1/F2/F3 + TLE geometry are DETERMINISTIC →
  realism/STATE, NOT headroom (rehabilitated as STATE in a dynamic env, not as the win-source)".
- recorded cause: "F1=area-global (same all users); F3=elevation-rate quasi-uniform in 200×90 km; F2 channel thin ≤1.5
  dB + 'avoid-interference REINFORCES collapse' (Trap-A) … **Baseline already has per-user state, still 3/3 collapse**"
  (`pivot-mechanism-feasibility.md:52`); "B1(純 hazard state aug)機制上與塌縮根因錯配" (`FABLE/p0-ledger.md:171`);
  independent geometry kill: "Family-B cells Earth-fixed、window per-episode 凍結 … cell 半徑 22.6km … 「dwell~10s」證偽"
  (`OLD/fable.md:242-244`).
- inferred cause [I]: the features were (a) nearly constant across users because the window/rank was defined at the
  area centre and frozen, and (b) nearly constant within a 10 s episode, so they could neither break the per-user
  argmax symmetry nor carry foresight. Both are env-construction facts, not facts about the feature idea.
- premises the concept depends on: satellites/beams move materially relative to users within a decision horizon
  (non-trivial τ_exit, F3 sign changes, interference dips); per-user heterogeneity of the features; a decode that can
  use per-user differences; the feature carrying value a forecast-static cannot capture (the 06-19 VoI test).

### F-2. Claim B — criticality-keyed per-objective catfish replay routing (B3h; old labels "PED-Strat", "c_k routing key", "hazard-keyed routing")
- mechanism (one line): replace CDRL's endogenous single-axis stratification key (EE-reward quantile) with exogenous
  per-objective geometric keys `c_EE=f2⁺`, `c_HO=max(1−f1,1[exit])`, `c_LB=churn/cell-crowding`; route a transition to
  catfish_k iff `c_k ≥ Q_q(window_k)` (rolling quantile), 3 parallel catfish, 70/30 injection into main.
- intervention point: experience
- defined in: `01-core-formulas.md:170-183`, pseudocode `02-core-algorithm.md:80-108`; SDD `FABLE/sdd-b3h-hazard-keyed-routing-DRAFT.md`; built modules `fable/r3fixed/sibling/{criticality_features,criticality_stratifier}.py` "8/8 + 4/4 test" (`01-core-formulas.md:193`).
- run status: built (stratifier + features, unit tests), **never trained** (B3f/B3h "gated … R-01..R-08 未跑", `00-newalgo-overview.md:5,100-101`); zero-training pre-flight ran (14,400 samples).
- run conditions: pre-flight on family_b locked 200×90 km regime, frozen-window geometry, no checkpoint; metric =
  per-user std / zero fraction / admit fraction at q=0.8.
- recorded outcome: "κ_HO … zero% **99.6%** … admit @ q=0.8 **100% ALL-PASS** … **DEAD as quantile key**"; "κ_EE … per-USER
  std **0.005**"; live only "κ_LB cell-crowding (0.346) ≫ F3 (0.038)" (`FABLE/sdd-b3h…DRAFT.md:188-196`). LATEST:
  `pivot-mechanism-feasibility.md:56-76`: "catfish/c_k/B3h has NO concrete escape mechanism … it is **'same wall, LOW
  odds,' NOT 'a different wall'** … Escape prior: **LOW**". Required 4-arm discriminator before any run: B3h≫B3f,
  ≫random-Q, ≫wrong-objective-Q, ≫phase-shuffled-κ placebo (`FABLE/sdd-b3h…DRAFT.md:219-222`). Novelty: prior-art scan
  "Claim B … 3.5/5，成立。查無「幾何 hazard 為條件的 replay 路由 + per-objective」先例" (`OLD/fable.md:214-218`).
- recorded cause: "Curation cannot manufacture a per-user distinction the state does not carry: identical-input users
  get identical shared-Q → identical argmax, regardless of which transitions trained it" (`pivot-mechanism-feasibility.md:66-67`);
  deploy decode unchanged: "catfish discarded at inference" (`…:54`). Also: the only live per-user axis
  (cell-crowding = beam loads) "is ALREADY in the baseline state and it still collapsed" (`…:65-66`).
- inferred cause [I]: the key's degeneracy is inherited from F-1's geometry (area-global frozen window, 10 s episode).
  The "routing can't create per-user distinctions" argument is specific to a shared-Q + per-user-independent-argmax
  decode; in a set-level/joint decoder it would not apply in the same form.
- premises: keys with real per-transition/per-user variance; a learner whose deployed decision can express
  what the routed experience teaches (not argmaxed away); a baseline pathology that is an experience-distribution
  problem rather than a decode problem.

### F-3. B2 — criticality-priority replay diagnostic arm (old label "hazard-priority replay", non-promotable)
- mechanism (one line): no catfish; main learner's own replay sampled with `P(τ)∝c(τ)^β`, `c=max(1−f1(serving), f2⁺(serving), 1[forced exit])`, computed once at insertion (exogenous, stationary — contrasted with PER's |TD|).
- intervention point: experience
- defined in: `01-core-formulas.md:185-188`; carve-out `FABLE/draft-b2-hazard-replay-carveout-decision-record.md:9-13` (needed because old PROJECT-STATE §6 do-not-re-propose list contains "Prioritized Replay").
- run status: designed ("run-now … 診斷臂, non-promotable", `00-newalgo-overview.md:99`); I found no run record [I: never run].
- run conditions: n/a.
- recorded outcome: none. Governance: "B2 永不作為候選勝利路線" (`draft-b2…:10`); review consensus "A4 ≈ PER 撞 do-not-re-propose … 降為不可 promote 的診斷控制臂" (`OLD/fable.md:246-248`).
- recorded cause: n/a.
- premises: same as F-1 (non-degenerate c); attribution matrix B3 vs B2 vs B1.

### F-4. Geometry-based PBRS replacing ACRM (old label "hazard-PBRS"; ③ injection point)
- mechanism (one line): replace CDRL's non-potential competitive lead `r^S=r^CF−r^M` with `r_k + γΦ_k(s',t')−Φ_k(s,t)`, Φ_k a per-objective geometric potential built from F1/F2/F3 (dynamic PBRS, Devlin&Kudenko 2012).
- intervention point: reward
- defined in: `02-core-algorithm.md:101-103`; `05-provenance.md:66-80`; `FABLE/draft-acrm-potential-shaping-decision-record.md`.
- run status: never built as a trained arm ("B3h-pbrs … 採用, gated", `02-core-algorithm.md:128`; decision record: "Status = candidate TODO, gated on env-fix", `draft-acrm…:162`).
- run conditions: n/a.
- recorded outcome: adopted on paper 2026-06-16, novelty "~2.5/5 次要" (`00-newalgo-overview.md:14`). Self-caveat: "policy-invariant → collapse 若仍 reward-optimal 則不能破,只助探索/速度;價值繫於 env-fix" (`05-provenance.md:80`). Later reopened in general form: "PBRS reopened (env+reward co-design; NOT formula-copy …)" (`env-misdesign…:125-127`).
- recorded cause: n/a (never run).
- premises: a potential that actually varies within the episode; the pathology being exploration/speed rather than a
  fixed point of the true objective (policy invariance means PBRS cannot move the optimum).

### F-5. CDRL catfish shell transplanted to value-based MODQN, per-objective ×3 (dual-agent, asymmetric discount γ^M≤γ^CF, per-objective ACRM, 70/30 periodic injection)
- mechanism (one line): 3 parallel own-axis catfish (EE/HO/LB), each with its own replay, larger discount, own ACRM
  `r^C_k=r_k+η(r^CF_k−r^M_k)`; periodically main trains on 70% main + 30% catfish buffers; catfish discarded at deploy.
- intervention point: experience (+ reward for ACRM)
- defined in: `01-core-formulas.md:96-130`; `02-core-algorithm.md:32-59,85-107`; `03-catfish-vs-newalgo-diff.md:17-29`.
- run status: this route-C form (B3f bridge = catfish shell with η-quantile key) never run. [Other clusters hold the
  catfish-faithful SDD-06/07 runs; `FABLE/p0-ledger.md:157` says "catfish 在 faithful env 從沒跑過" as of 06-13.]
- run conditions: n/a in this cluster.
- recorded outcome: v3 reconciliation: "catfish core ∈ DQfD/PER" (novelty application-tier, `reconciled-direction-rec-v3:162-165`);
  bit-identical ledger fact: "catfish 跑 1467×/ep 但 deployed policy 不動 = 路徑機制不移終點" (`OLD/fable.md:325-326`).
  06-19: "CATFISH = RE-CONCEIVE for the dynamic env's failure modes … NOT the auto 3-per-objective DQN form; CORE
  (injection) preserved; catfish-off ablation must drop" (`env-misdesign…:124-126`).
- recorded cause: "Training-time tricks get **argmax'd away** at deployment unless they change **which beam each user
  picks relative to others**" (quoted in `FABLE/p0-ledger.md:155`).
- premises: injected experience changes the deployed decision; per-objective split is the useful axis (06-19 says it is not — split by failure mode instead, see F-9).

### F-6. RH-Gate — representation-health pre-training gate
- mechanism (one line): methodological backstop — check representation health (from the offset-saturation lesson; lit neighbours ReDo dormant-neuron / effective rank) before trusting training.
- intervention point: other (training diagnostic)
- defined in: `00-newalgo-overview.md:113`; lit cut `OLD/fable.md:232-234`.
- run status: never built as far as this cluster shows [I].
- recorded outcome: "方法學保底 … 非 headline 機制" (`00-newalgo-overview.md:113`). The related A1-ReDo plasticity arm: "A1-ReDo (plasticity remedy) = only informative arm but its decisive version belongs on the redesigned env → non-load-bearing here" (`env-misdesign…:63-65`).
- premises: collapse being a representation/plasticity failure (primacy bias) rather than a decode/objective property.

---

## Part 2 — family_b collapse-diagnosis lineage (06-13 → 06-28): hazard/criticality, Claim B, DR/credit, decode, regime

### F-7. PED-Strat — Pareto-pivotal experience stratification (original claude-report "方向 1", later merged into Claim B)
- mechanism (one line): route a transition to catfish-j iff removing objective j from the reward vector changes the
  transition's non-dominated status (non-dominated sorting + crowding), replacing CDRL's scalar EE-quantile threshold.
- intervention point: experience
- defined in: `FABLE/review-report/claude-report.md:77-86` (repo cites it via `OLD/fable.md:232-237`). Later the label
  "PED-Strat / B3h" was re-used for the *geometric* criticality key (F-2) (`00-newalgo-overview.md:30,55`) — i.e. the
  Pareto-pivotal key was replaced by the exogenous-geometry key during 06-14→06-15.
- run status: never built (as Pareto-pivotal).
- run conditions: proposed on "去飽和 MODQN (新錨點)" (the de-saturated baseline later found to be 0/3 strict / mis-checkpointed, `OLD/fable.md:11-13`).
- recorded outcome: Tier-1 recommendation (Novelty 4 / Feasibility 4 / Defensibility 5, `claude-report.md:84-86`); own
  risk stated: "若去飽和 baseline 已自行展開 … catfish 邊際空間可能很小 → 可能再得 tie" (`:82`). LATEST: absorbed into
  F-2 and dies with it; 06-20 Agent-4 lit review: "M1 reward-keying is itself a documented cause of premature
  convergence" (`b-pivot-decision-map-2026-06-20.md:48-50`).
- recorded cause: n/a (never run).
- premises: that "wrong experience fed to catfish" is why catfish failed to move the deployed policy; that deployed policy responds to routing.

### F-8. Other review-bank catfish-layer variants (claude-report 方向 2/3/4/6/7/8/9/10) — DOM-Lead, ΩCat, AdmitGate, PhaseStrat, HO-Split, VoE-Critic, DivCat, IW-Inject
All: never built; only proposed in `FABLE/review-report/claude-report.md:88-187`; repo cites DivCat↔DvD, IW-Inject↔SEAC,
AdmitGate↔uncertainty action-advising (`OLD/fable.md:232-235`). One line each (records SAY):
- DOM-Lead (reward): ACRM lead redefined as Pareto-dominance margin / hypervolume diff (`:88-97`); own risk: ACRM "貢獻最小" in original ablation.
- ΩCat (exploration/experience): catfish perturbs scalarisation weights Ω to generate experience exposing neglected objectives; main keeps fixed Ω (`:99-108`).
- AdmitGate (experience): per-objective learned admission gate — inject foreign experience only if it lowers objective-j held-out TD error; replaces fixed 70/30 schedule (`:110-119`).
- PhaseStrat (experience): catfish threshold conditioned on orbital phase / elevation band (non-stationary) (`:132-141`).
- HO-Split (representation/experience): split r2 head into intra/inter-satellite handover sub-values + a challenger targeting expensive inter-sat HOs (`:143-152`).
- VoE-Critic (experience): learned auxiliary head predicting each transition's marginal Pareto-coverage/hypervolume contribution, used as routing key (`:154-163`).
- DivCat (penalty/loss): determinantal (DvD) diversity regulariser among the 3 catfish so they don't homogenise "像使用者一樣" (`:165-174`).
- IW-Inject (loss): per-objective importance weighting of injected off-policy samples (`:176-185`), Tier 3, "正當性弱".
- premises shared by all: catfish-injected experience can move the deployed per-user-argmax policy. The 06-13/06-17
  record says that premise failed on family_b ("catfish 跑 1467×/ep 但 deployed policy 不動", `OLD/fable.md:325-326`).
  [I] DivCat is the only one aimed at homogenisation, but at the catfish population, not across users.

### F-9. Review-bank "structural" directions (chatgpt-report): Viability-Reserve, Marginal Congestion Credit, Semi-Markov Dwell, Occupancy-Response, Interruption-Budget MORL, Observation-Lag, Transition-Graph Consistency
Records: `OLD/fable.md:284-286` ("idea 不受 shift 影響;但 repo 刻畫全 stale (pre-SDD-11, README-only)"); definitions in
`FABLE/review-report/chatgpt-report.md:49-126`. All idea-level; run status never built EXCEPT Marginal Congestion
Credit, which became DR-MODQN (F-10). One line each:
- Temporal Hazard State Reconstruction (representation) = the origin of F-1: "snapshot state … 可能不是充分狀態 … remaining coverage / channel slope / beam overlap horizon / candidate-set decay" (`:49-58`).
- Viability-Reserve Handover (objective/decode): protect future feasible-action-set size / overlap window / successor slack; "logging metric first, then constraint or auxiliary decision score" (`:59-67`); own risk: may be collinear with existing Γ/G.
- Marginal Congestion Credit Assignment (reward): replace global max-min r3 with the user's counterfactual marginal effect on congestion (difference reward) (`:69-77`).
- Semi-Markov Dwell Commitment (action/decode): action = (beam, committed dwell) or defer/commit (`:79-87`).
- Occupancy-Response Modeling (representation): predict how own handover changes near-future occupancy; load is endogenous (`:89-97`).
- Interruption-Budgeted MORL (objective): handover interruptions as a session budget / hard constraint, not a soft penalty (`:99-107`).
- Observation-Lag Robustness (representation): stale/time-stamped observations + history (`:109-117`).
- Transition-Graph Consistency (decode/regulariser): orbital-overlap/beam-adjacency transition graph as sequence prior against route traps (`:119-126`).
- premises [I]: Viability-Reserve, Semi-Markov Dwell, Observation-Lag and Transition-Graph all presume beams/satellites
  move relative to users within the decision horizon ("moving-beam dynamics", `:66`) — exactly the premise the
  fable5-cli MAJOR-1 geometry review said family_b lacked (see geometry section).

### F-10. DR-MODQN — marginal-congestion difference reward D_i + symmetry-breaker, faithful decode (old labels "Option-1", "Candidate 1", "KEEP-A", "DR-Catfish")
- mechanism (one line): train a sibling MODQN on `D_i = G(z) − G(z_{−i})` (team-sum r1 leave-one-out counterfactual at the
  K=3 admission boundary, exact fading replay), keep per-user argmax decode, add a "generalization-safe symmetry-breaker"
  (per-user identity/ordering/anti-correlation) so identical-state users don't co-stampede; handover-aware.
- intervention point: reward (+ representation for the breaker)
- defined in: `OLD/analysis/family-b-collapse-diagnosis/reconciled-direction-rec-v3-2026-06-19.md:284-288`; route choice `track-b-strategic-rec-2026-06-19.md:176-179`; breaker design file exists `analysis/family-b-collapse-diagnosis/symmetry-breaker-design-2026-06-19.md` (not in my list; not read).
- run status: never trained. Cheap proxies ran: "corrected screen G-B (binding; single-step) **+2.57e-5 / +1.47e-5 /
  −5.45e-5**, out_corr 0.950 / 0.975 / 0.997" (3 seeds) (`reconciled…v3:48`); existence hook "s600, 1/3 seeds … ≈+1.2292e-4 …
  active=10, out_corr 0.66" (`:49`).
- run conditions: family_b as-is (K=3 cap, frozen window, 10×1 s), metric = calibrated weighted J_w [0.5,0.3,0.2] vs WEAK
  static RSS_max +1.2292081e-4 (FIELD bar); cheap single-step screen (no lr stated); decode = faithful per-user argmax.
- recorded outcome: "the fresh round CONFIRMS v2's direction … It does NOT raise the win-prior" (`reconciled…v3:15-16`);
  "WIN-PRIOR = LOW, directly-evidenced" (`:170`); "the temporal-displacement flaw (credit on realized load, decode on stale
  load) makes mechanism-fail (T0) the single most-likely heavy outcome" (`:336-337`). LATEST: superseded same day by the
  env-redesign reframe (`env-misdesign…-2026-06-19.md:3-6`); 06-21 round-2 (5/5): "keep the baseline MODQN frozen
  INCLUDING the per-user independent argmax, and use a training-only catfish to teach THAT to spread … WILL NOT WORK"
  (`round2-deepresearch-synthesis-2026-06-21.md:9-12`). Novelty: "`D_i` ∈ the WLU/COMA/QUICR difference-reward class"
  (`reconciled…v3:162`).
- recorded cause: "Q_i ≡ Q_j → every user argmaxes the SAME beam (state-aliasing / symmetry)" (`round2…:11-12`); "a raw
  random tag self-nulls in training; user-IDs destroy generalization — this is the open design risk" (`reconciled…v3:323-324`).
- inferred cause [I]: the credit signal was never tested at scale; what was falsified is "credit alone through an
  unchanged simultaneous argmax on stale load". The D_i idea is decode-agnostic.
- premises: a K-capped shared resource (the counterfactual is only non-trivial at the admission boundary); a decode
  that can act on differentiated values; a symmetry-breaking input.

### F-11. Spread catfish + sticky catfish, failure-mode-bound routing key, collapse-triggered intervention (blind chatgpt "algo/" proposal, folded into Option-1)
- mechanism (one line): two specialist catfish split by FAILURE MODE not objective — "spread" injects de-homogenised
  non-churning high-value segments, "sticky" injects low-churn r2-protecting segments; routing key = high calibrated-weighted
  segment return ∧ de-homogenisation evidence (occupancy entropy / active / low out_corr) ∧ bounded handover; intervention
  share raised when active drops / out_corr rises instead of fixed 70/30.
- intervention point: experience
- defined in: `reconciled-direction-rec-v3-2026-06-19.md:94-99, 290-300`.
- run status: never built.
- recorded outcome: "a concrete, faithful-decode-compatible form for the catfish that earns its place" (`:295-296`); but the
  whole KEEP line was LOW-prior and superseded (see F-10). Round-2 (06-21) re-converged on "collapse/dissent-TRIGGERED (fire
  when active-beams < θ_spread 7.56 or argmax-agreement high), routed to the collapsing users' replay" (`round2…:25-26`).
- recorded cause: n/a.
- premises: churn (r2) being what sank faithful spread (`f` analysis) — later corrected: f's loss was also r3 + cap_bump
  ("not 'merely a churn artifact' (r3 is ~co-equal to r2; codex BLOCKER)", `f-on-weighted-findings.md:42-43`).

### F-12. Supervised faithful policy `f` (imitation of planner labels through per-user-argmax) — TEST-f preview
- mechanism (one line): supervised CE imitation of the non-faithful constructive planner's per-step actions by a per-user-argmax net; used as a "preview/upper bound" of what a faithful learner can reach.
- intervention point: other (demonstration/imitation; diagnostic)
- defined in: `f-on-weighted-findings.md:1-20`; `track-b-strategic-rec-2026-06-19.md:58-69`.
- run status: ran (5 eval seeds, 48 phases; eval-only on existing weights `supervised-f-weights.pt`).
- run conditions: family_b as-is; metric = calibrated weighted [0.5,0.3,0.2] (cap-enforced); lr not stated; trained from scratch by supervision (not RL, not distilled from a frozen main).
- recorded outcome: "W_f = −5.33e-5 … 5.7 bands BELOW the zero-learning faithful floor (+1.25e-4); all 5 seeds negative" ;
  served 0.654, active 9.58, cap_bump 0.327, handover 38.45 (`f-on-weighted-findings.md:10-17`). Positive side: "a learned
  faithful policy CAN spread + ~2× the served-throughput of the zero-learning faithful floor" (`:26-28`). LATEST (06-19
  correction): the bar it was judged against was re-set to the WEAK +1.23e-4; f still fails it (`:33-39`).
- recorded cause: "Served 0.999 is reached ONLY by the constructive K-aware planner … A SIMULTANEOUS per-user argmax does not
  run that joint construction → f over-piles → cap_bump 0.327" (`:51-57`); churn "GRATUITOUS, from imitating the per-step planner" (`:47-49`).
- premises: K=3 hard cap (makes admission a joint-construction problem); frozen-window geometry (makes staying ≈ optimal).

### F-13. Deploy-time load-biased decode over frozen Q (Ye-bias / Holder deploy-augment; "decode override")
- mechanism (one line): at inference `argmax_b(Q − λ·μ_b·σ_u)` with online per-assignment load, no retraining.
- intervention point: decode/deployment
- defined in: `materiality-verdict.md:21-25`.
- run status: ran (eval-only; 32/288 strided phases, 3 train seeds × 5 policies × 160 eval ep/cell, `materiality-verdict.md:8-10`).
- run conditions: family_b; frozen collapsed B0 Q (angle_aware_EE r1); metric = M1, active, modal, ζ.
- recorded outcome: "λ 0→4: active 1→11, modal 1.0→0.19 … lifts M1 1539 → 6115 (λ=2, > RANDOM 5828)" (`:22-24`). LATEST:
  "Deploy-time Ye-bias ceiling ≈ RANDOM … un-collapse ≠ win" (`:57-58`); classed as hollow deploy-repair ("item 6 = the
  Ye/Holder DEPLOY-repair (invariant 6)", `reconciled…v3:156`). Separate 06-21 probe: "a free sequential decode over the
  FROZEN collapsed Q does nothing → Q is load-insensitive" (`NEXT-SESSION-sdd-handoff-2026-06-21.md:22-23`), yet forced
  spread through the override showed a "Q-informed vs Q-drowned GAP … 5/5 SNR-spatial … median GAP ~0.14" (`:24-27`).
- recorded cause: collapse is "reward-SUBoptimal … the per-user-argmax *decode*, not the Q-content, pins the collapse" (`materiality-verdict.md:17-25`).
- premises: shared K-capped beams; values carry usable spatial signal.

### F-14. Learned forward "coordination decoder" (A1 vs A1c, route B PM-13c) and LP-round solver
- mechanism (one line): one-pass forward decode with load tie-break over a (proxy) Q, versus a zero-learning LP-round assignment solver for cap_bump.
- intervention point: decode/deployment
- defined in: `FABLE/r3fixed/largergeo-regime-prereg.md:157-199` (cited in `pivot-mechanism-feasibility.md:53`).
- run status: ran (eval-only; U400, r3fixed cap_bump 440²/460² band; SNR-proxy Q, no learning).
- run conditions: larger-geometry regime (not base family_b); metric = cap_bump coordination gap G_coord.
- recorded outcome: "O-MIXED … cheap SNR-proxy lex forward decoder is **anti-helpful** (… cb_fwd ≈0.91 ≫ planner ≈0.45) …
  **LP-round** … closes **64–82%** of G_coord" (`largergeo…:169-172`); "LP relaxation is **TIGHT** … not combinatorially
  hard" (`:162-163`). LATEST: "HONEST FLOOR = SCOPED-NEGATIVE for PM-13c route B" (`:245`); v3: "Candidate 2 (coordination
  decode) = AVOID as headline … LP eats 64–82%" (`track-b-strategic-rec:54-55`).
- recorded cause: "decodes from the ALREADY-homogenized Q (acts after collapse in representation space)" + deflation by LP (`pivot-mechanism-feasibility.md:53`).
- premises: the coordinated optimum being hard to reach cheaply (it wasn't: LP tight).

### F-15. Sequential / occupancy-conditioned decode for the contribution (round-1/round-2 convergence) → became route-B "fork ②" capacity-auction decode
- mechanism (one line): replace simultaneous per-user argmax with sequential/auto-regressive decode updating a running
  virtual load per user (O(N), single pass); later implemented as bid `b_u(a)=Σ_k ω_k Q_k(s_u,a)` + coordinated
  capacity-auction / bipartite matching under k_cap.
- intervention point: decode/deployment
- defined in: `round1-deepresearch-synthesis-2026-06-20.md:12-13`; `round2…:13-15`; implemented framework per
  `local-controller-handoff-2026-06-28.md:21-22,38-40` (code `src/modqn_paper_reproduction/route_b_factorial/`, not read here).
- run status: ran — "The heavy 2×2 factorial RAN" + k_cap∈{3,15} done, {6,9,12} in flight at 06-28 (`local-controller-handoff:21-28`). Seeds/episodes not in this file.
- run conditions: family_b; metric = "EE/calib J_w, NOT throughput" (`:59-60`); training side = "χ_u congestion-context
  state-augmentation, asymmetric per-objective γ, value-stratified replay — NOT the old `thesis/` D_k-PBRS" (`:38-39`).
- recorded outcome: approved narrative "GENUINELY wins (beats baseline MODQN …; best multi-objective point; dominates
  DQN_scalar on the fairness frontier; k_cap is a cause of MODQN collapse)" (`:23-25`); RED LINE: "NO false causal claim
  ('catfish proven to drive the win' …) — A2≈A1 + cross-over say the DECODE drives de-collapse" (`:63-65`). [Detailed
  numbers belong to another cluster.]
- recorded cause: decode is the de-collapse engine; catfish ≈ no separable contribution (A2≈A1).
- premises: K-capped shared beams; coordinated assignment being where value lies (on family_b the LP/planner already gets it — the hollow-win worry F-14).

### F-16. Centralised non-learning best-response planner as catfish source, injected as PBRS potential and/or counterfactual credit (round-2 converged mechanism; "BRCA planner")
- mechanism (one line): a training-only coordinate-ascent/best-response planner supplies Φ (served-demand / occupancy
  entropy / −load-variance / congestion potential) for PBRS and/or COMA/WLU difference credit, fired only on collapse/dissent
  states; plus F1/F2/F3 congestion state-aug; plus sequential decode.
- intervention point: reward + experience (+ representation, decode)
- defined in: `round2-deepresearch-synthesis-2026-06-21.md:19-31`; SDD brief `NEXT-SESSION-sdd-handoff-2026-06-21.md:32-46`.
- run status: SDD-brief only in this cluster; the implemented route-B used a different training side (F-15: "NOT the old D_k-PBRS").
- recorded outcome: "HYPOTHESIS (converged but unproven)" (`round2…:74`); "the 'use PBRS + F1/F2/F3' convergence is PARTLY
  revealed-induced" (`:52-53`); "catfish risks being decoration on a decode fix" (`:79`).
- recorded cause: n/a.
- premises: the planner's advantage is not already delivered by the decode itself (it largely was, per F-15 RED LINE).

### F-17. Adaptive / learned state-adaptive scalarisation of the 3 per-objective Q heads (decode axis)
- mechanism (one line): replace fixed Ω in `_scalarize_q_values` with a learned state-adaptive combiner of Q1..Q3.
- intervention point: decode/deployment (objective combination)
- defined in: `hard-ee-regime-C-EVPI-result-verdict.md:43-47`.
- run status: proposed; "Next = its cheap deploy-test (adaptive combiner on frozen B0's 3 Q-tables vs Ye-bias + fixed-scalar)"; no result in this cluster [I: status unknown here].
- recorded outcome: "the untried, theory-backed (Agorio fixed-scalarization-insufficient), catfish-attributable bet" (`:45-46`).
- premises: the Q heads individually carry differentiated information that a fixed linear mix destroys.

### F-18. Hard-EE temporal regime (injected correlated demand / energy-budget coupling) + scenario-MPC bar; EVPI screen
- mechanism (one line): break per-step separability by adding a cross-step coupling (energy budget/battery, correlated
  demand with a 2-state Markov process, cross-time PF fairness) so foresight/learning could beat a per-step static.
- intervention point: objective (+ env)
- defined in: `hard-ee-regime-feasibility-verdict.md:36-83`; result `hard-ee-regime-C-EVPI-result-verdict.md`.
- run status: ran as a zero-learning EVPI probe (6 (ρ,contrast) cells, "reduced run (16/cell vs frozen 200×5)").
- run conditions: finite-horizon PF-EE r1 + injected 2-state Markov demand (NOT family_b-as-is, `reconciled…v3:266-268`); metric = EVPI (clairvoyant − scenario-MPC)/|clairvoyant|, ε-floor 0.02.
- recorded outcome: "EVPI … mean 0.000242; max 0.000326 = 61× BELOW the frozen ε-floor 0.02"; "VSS (scenario-MPC − myopic):
  mean 0.00082 (tiny)"; verdict "temporal/hard-EE-regime A-path = DEAD" (`EVPI-result:7-13,1`). Feasibility verdict: "On the
  FROZEN MODQN + catfish vehicle: a defensible hard-EE learning win is NOT cleanly constructible" (`feasibility:44-47`).
  Caveat: "low-prior-CONFIRMED dead for this instantiation, NOT 'provably impossible forever'" (`EVPI-result:31-32`).
- recorded cause: "the faithful env is deterministic-orbit + i.i.d.-fading → zero learnable temporal structure → VSS gap ~0
  by construction" (`feasibility:38`); "the cross-time-fairness coupling barely broke separability" (`EVPI-result:12-13`);
  catfish R4: "if the temporal state is observable, plain MODQN learns the same shadow-price (catfish credit ≈ 0); if hidden,
  the memoryless net … can't track it" (`feasibility:40`).
- premises: learnable temporal structure (correlated uncertainty), Markov-observable temporal state, a classical bar that is
  distribution-aware (scenario-MPC).

### F-19. Per-step foresight static (forecast_eta_held) and η-EE classical search — the "EE is per-step separable" finding
- mechanism (one line): test whether 10-step foresight or diverse classical search beats the per-step η_EE bar on family_b.
- intervention point: other (headroom probe)
- defined in: `intra-episode-closing-findings.md:15-33`; `eta-ee-findings.md`.
- run status: ran (16 phases × 2 seeds 600/700; eval-only).
- run conditions: family_b; metric = true η_EE r1 (system EE, bits/J) at qos≈1.0; bar = `planner_then_balance_t12` 4.721e12.
- recorded outcome: "forecast_eta_held (10-step foresight, held) 4.336e12 — NONE beats the bar by > ε. Foresight loses to
  per-step" (`intra-episode…:22-25`); "η_EE on family_b is a per-step-separable assignment problem … family_b offers no
  evidenced learning-EE-win → ROUTE-CHANGE" (`:38-42`). Earlier: "collapse b0 has the LOWEST η_EE (0.96–1.02e12)" — "η_EE
  does NOT reward concentration" (`eta-ee-findings.md:37-39`); zero-learning `planner_then_balance` 4.650e12 beat the probe
  frontier by +5.8% (`:27-33`).
- recorded cause: "r1_throughput + the η_EE credit are current-step-only; the sole cross-step state … feeds rewards only via
  prev→cur `_handover_penalty → r2` … Fading is i.i.d. per step" (`intra-episode…:28-33`).
- premises for transfer [I]: in an env where power/EE carries cross-step state (e.g. segment-anchored power, handover energy)
  the separability argument does not hold as stated.

### F-20. Handover-at-matched-QoS as win axis (sticky_planner static) — the "static eats it" pattern
- mechanism (one line): win where memoryless static re-solving churns (r2), via learned temporal stickiness.
- intervention point: objective
- defined in: `win-target-clarification.md:31-36`; tested `axis-headroom-findings.md`.
- run status: ran (static probe, 16 phases × 2 eval seeds).
- recorded outcome: zero-learning sticky_planner "holds full planner QoS (0.9999) at 1/10th the churn (7.84 vs 79.16)"
  (`axis-headroom-findings.md:26-29`) → "Handover-at-matched-QoS is NOT a defensible learning win axis as-is" (`:46`).
  Weighted-metric version: sticky_planner +3.18e-4 vs faithful rss_max +1.23e-4 (`weighted-balance-headroom-findings.md:14-17`).
- recorded cause: "a churn-penalized static policy — keep each user's previous action while its decision-time estimated
  rate … is still ≥ QoS floor" suffices (`axis-headroom-findings.md:25-28`); window frozen so "a constant action yields handover [0]×10" (`:21-24`).
- premises: static re-solvers churn gratuitously; env where staying is not already near-optimal.

### F-21. Coverage-aware decode repair and DAgger/hard-phase fine-tune for a distilled amortised net (06-24, "(P)" net)
- mechanism (one line): (L2a) decode-time pass reassigning sub-QoS users to feasible beams using the env rate estimator;
  (L2b) DAgger / coverage-objective fine-tune toward the sticky teacher.
- intervention point: decode/deployment (L2a); experience/demonstration (L2b)
- defined in: `tail-user-coverage-diagnosis-findings-2026-06-24.md:45-89`.
- run status: L2a ran (net-0, sealed eval seeds, 2 bound settings); L2b never run in this cluster.
- run conditions: family_b; (P) = "offline-CE-distilled from sticky's per-step actions" (`:85-86`) — i.e. a net trained by
  distillation from a zero-learning teacher, not RL; metric = J_w (calibrated weighted), min-coverage, speedup vs teacher.
- recorded outcome: (P) diagnosis: "48 / 96 (50%)" phases with a zero-coverage user; "(P) uses MORE active beams than the
  teacher … yet starves more users" (`:19-39`). L2a: J_w 4.6767e-4 → 4.8414e-4 (103.5%), min-coverage 0.000 → 0.000,
  speedup 21.8× → 6.2× (`:63-68`); "a cheap decode patch does NOT cleanly win" (`:82`).
- recorded cause: "min-coverage = converged greedy fixed-point … No single-user beam swap can serve the worst-user-worst-phase
  without un-serving another → needs the teacher's JOINT/simultaneous coordination" (`:74-78`); "(P) … lost its temporal
  coverage-stability; small per-step matching errors compound in hard phases" (`:85-86`).
- premises: teacher reachable and cheap to query at train time; min-coverage defined as a temporal minimum.

### F-22. Catfish GENERIC-validity kill test on DeepSea / MountainCar (P1) and the 5-angle "catfish very-low-prior" verdict
- mechanism (one line): test catfish on its most favourable single-agent sparse/deceptive turf vs tuned-ε DQN, NoisyNets, bootstrapped DQN, PER, DQfD controls, rliable stats.
- intervention point: other (method validity test)
- defined in: `b-pivot-decision-map-2026-06-20.md:62-76`.
- run status: designed (inference contract written); no result in this cluster [I: not known whether it ran].
- recorded outcome (prior, not evidence): "catfish is AGENT-LEVEL anti-stagnation; LEO failure is USER-LEVEL coordination →
  axis mismatch" (`:36-37`); "all 3 components DOMINATED-BY-SIMPLER … M2: Curse of Diversity (ICLR 2024); M3: SUPER (NeurIPS
  2023) shows M3's exact 30%-uncorrected-heterogeneous regime is WORSE than no-sharing; M1 reward-keying is itself a documented
  cause of premature convergence" (`:47-50`); A1-ReDo "strongest training-side plasticity fix FIRED yet 3/3 still collapsed"
  (`:29-30`). Binding user decision same file: drop strong-static/MPC comparison; win-bar = beat plain MODQN + weak static (`:3-15`).
- premises: catfish mechanism is anti-stagnation at agent level; whether the target env's failure is agent-level or user-level.

### F-23. Environment redesign toward demand dynamics (time-varying correlated demand + per-cell queues), catfish "re-conceived"
- mechanism (one line): move headroom source from geometry to demand uncertainty/queues a forecast-static cannot capture;
  keep F1/F2/F3 only as realism state; re-conceive catfish as demand-anticipating/de-congesting experience injection.
- intervention point: other (env) + objective
- defined in: `env-misdesign-and-redesign-direction-2026-06-19.md:37-51,100-132`.
- run status: design-level; EVPI screen of an injected-demand variant killed the temporal version (F-18); 06-20 deep research:
  "demand/queue-EVPI learning-win = HOLLOW ('MPC eats it')" (`b-pivot-decision-map:31-35`).
- recorded outcome: binding VoI rule: "Keep a feature iff a forecast-static can't capture its VoI" (`env-misdesign:113-116`);
  anti-recurrence: "Do NOT re-add a hard cap as an unexamined default" (`:74-75`); "Sun2024 … has NO hard cap" (`:29-32`).
- recorded cause: env choices "not made for the MODQN RL contribution" (K=3 cap, Walker-180 for the visual project) (`:16-23`).
- premises: headroom must come from non-deterministic structure.

### F-24. Catfish shared-policy exploration lesson — SOFT-DISCARD paper (arXiv 2601.05509, "How Exploration Breaks Cooperation in Shared-Policy MARL")
- see Part 4 (read after the PDF).
