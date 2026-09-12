VERDICT: INVALIDATES-FOUND

### 1. Protocol Contradiction on Concurrent v1/v2 Selection vs. Implementation [INVALIDATES]
* **Evidence:** Contract r1 (§0, lines 3–7; §7, lines 142–143) mandates that `MC2-JGO-v1` and `MC2-ARB-v2` run **concurrently at ep 100** across an 8-cell × 2-seed = 16-run selection matrix (`D0`, `D3-T0`, shared `B-only`, `FULL-v1`, `B-null-v1`, `A-only-v2`, `FULL-v2`, `B-null-v2`). However:
  1. `MC2-ARB-v2`, `A-only-v2`, and `B-null-v2` do not exist in the codebase ([cf_judge.py:77](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L77) defines only `MECHANISM_IDS = {"MC2-JGO": "MC2-JGO-v1"}`; [dev_e0_common.py:69-72](file:///home/u24/papers/mcrl-leo-handover-mc2/scripts/dev_e0_common.py#L69-L72) and [dev_e0_launch.py:32](file:///home/u24/papers/mcrl-leo-handover-mc2/scripts/dev_e0_launch.py#L32) register only Arm 10 v1).
  2. Lane A’s execution plan ([PROGRESS-A.md:14-16](file:///home/u24/papers/mcrl-leo-handover-mc2/.scratch/mc2/PROGRESS-A.md#L14-L16)) explicitly schedules launching 10 runs for v1 while leaving v2 as "not launched".
* **Impact:** Launching counted selection runs under contract r1 without v2 executes an incomplete and unexecutable matrix, invalidating the declared prospective selection protocol.
* **Smallest Concrete Fix:** Either amend the contract back to staged sequential evaluation (reverting r1’s concurrency mandate so v1 runs alone and v2 is evaluated only if v1 fails selection), OR implement and test `MC2-ARB-v2` before the first counted selection run launches.

---

### 2. Specialist Identity, Roles, and Drop-One Asymmetry (Point A) [NON-BLOCKING]
* **Identity & Information:** Catfish-A ($T_0$) and Catfish-B ($T_{\text{NEXT}}$) are genuinely distinct, scripted, deterministic heuristics reading different information:
  - $T_0$ ([cf_teacher.py:125-147](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_teacher.py#L125-L147)) evaluates current step $t$ nominal SINR and previous beam loads.
  - $T_{\text{NEXT}}$ ([cf_tnext.py:134-253, 305-373](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_tnext.py#L134-L253)) evaluates deterministic forward ephemeris geometry at $t+1$ (`driver.satellite_ecef_at(1)`), holding user positions at $t$, with nominal $t+1$ gain. Their disagreement rate on P0 is 59.6% ([CONTROLLER-K8-FAIL-AND-SEARCH-EXHAUSTED-2026-09-12.md:86](file:///home/u24/papers/mcrl-leo-handover/.scratch/catfish2-successor/CONTROLLER-K8-FAIL-AND-SEARCH-EXHAUSTED-2026-09-12.md#L86)). Neither is an RL agent.
* **Removability:**
  - Removing B yields Arm 4 (`D3-T0`, [cf_teacher.py:519-537](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_teacher.py#L519-L537)), which is an exact, unpolluted retrained baseline ([cf_judge.py:88-90](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L88-L90)).
  - Removing A yields B-only ([cf_judge.py:269-284](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L269-L284)), where B is gated against the learner's executed action $x_u$, rows where B does not win carry weight $w=0$, and vacated dose is unrefilled ([cf_dev.py:986-994](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_dev.py#L986-L994)).
* **Asymmetry:** Gating B against $a^A$ in FULL but against $x_u$ in B-only means `FULL − B-only` bundles A's margin with the shift in B's comparator and the dose change. This is structurally unavoidable (gating against $a^A$ in B-only would leak $T_0$), but should be explicitly documented.

---

### 3. Margin Target Uniqueness and Non-Dilution (Point B) [NON-BLOCKING]
* **Target Selection:** Every margin row has exactly one scalar target `target[u]` ([cf_judge.py:267, 282](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L267)). It is selected strictly by the teacher rules and pre-step judge $\kappa_u$, completely independent of the student network's score $S(s, a)$ ([cf_judge.py:276-284](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L276-L284)).
* **Dilution vs. Cancellation:**
  - The set-valued dilution of k=8 (`d3_set_margin_loss`, [cf_teacher.py:539-576](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_teacher.py#L539-L576)) is eliminated because $|A_{CF}| \le 1$.
  - In v1, B cannot dilute A; it can only *override* A when $\kappa(a^B) \succ \kappa(a^A)$.
  - In v2, if $x_u \succ a^A$ and $x_u \succ a^B$, the margin is cancelled entirely ($w=0$).
* **A-Only Parity:** In v1, A-only is Arm 4 (`D3-T0`) by identity ([cf_judge.py:88-90](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L88-L90); [dev_e0_common.py:68](file:///home/u24/papers/mcrl-leo-handover-mc2/scripts/dev_e0_common.py#L68)). `weighted_margin_loss` with $w=1$ reproduces `d3_margin_loss` bit-for-bit ([cf_judge.py:42-44, 297-299](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L42-L44)).

---

### 4. Counterfactual Causality and Surrogate Honesty (Point C) [NON-BLOCKING]
* **Physical Counterfactual:** Evaluating $(a, x_{-u})$ via `evaluate_actions` ([step.py:643-705](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/env/step.py#L643-L705)) correctly evaluates focal user $u$'s unilateral deviation against the executed background under common random numbers.
* **State/Reward Attribution:** Clean. Transitions $(s_u, x_u, r_u, s'_u, \text{done})$ pushed to replay ([cf_dev.py:1221-1231](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_dev.py#L1221-L1231)) record only the executed action and committed environment outcome. The TD update ([cf_dev.py:1018](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_dev.py#L1018)) is completely isolated from judge evaluations.
* **RNG Isolation:** `evaluate_actions` deep-copies `rng` ([step.py:700](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/env/step.py#L700)). `StepJudge.assert_committed_parity` ([cf_judge.py:202-214](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L202-L214); [cf_dev.py:1192-1193](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_dev.py#L1192-L1193)) asserts bit-identical parity between pre-step base evaluation and post-step committed outcome.
* **No User Shedding:** $\kappa$ uses strict lexicographic order with `served` count first ([cf_judge.py:115-121](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L115-L121)). An action shedding a user cannot beat an incumbent serving that user.
* **Honest Surrogate:** Contract §2 (lines 51–54) and [cf_judge.py:5-7, 64-66](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L5-L7) explicitly label $\kappa$ a fixed-price training surrogate ($B - \eta_0 E$), disclaiming any direct EE improvement claims.

---

### 5. Identification Bounds of the B-null (Point D) [NON-BLOCKING]
* **What it Identifies:** B-null ([cf_judge.py:82-86](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L82-L86); [cf_dev.py:1053-1054](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_dev.py#L1053-L1054)) draws $a^R \sim \text{Uniform}(\text{legal}_u)$ from `(9_243_000, k)` and filters it through the exact same judge $\kappa$. Comparing `FULL vs B-null` isolates the heuristic proposal quality of $T_{\text{NEXT}}$ against random actions subjected to the same 1-step judge filter.
* **What it Does Not Identify:**
  1. It does not measure the standalone efficacy of $T_{\text{NEXT}}$ without a judge.
  2. It does not isolate temporal foresight from non-temporal alternative heuristics.
  3. It does not match override dose: because $T_0$ is strong, a uniform random action will rarely beat $a^A$, making B-null’s override rate much lower than FULL's, confounding proposal quality with intervention frequency.
* **Fairness:** Structurally identical. In compute, B-null triggers more evaluations (~96% of rows where $a^R \ne a^A$) than FULL (~60% where $a^B \ne a^A$).

---

### 6. Multiple Testing Inflation in Fixed-Order Fallback (Point E) [NON-BLOCKING]
* **Evidence:** In §7 (lines 150–153), if both v1 and v2 qualify at selection, the primary is confirmed on seeds 12–14; if the primary fails, the non-primary is evaluated on reserve seeds 15–17. If either passes, MC2 claims DEV survival (lines 154–160).
* **Multiplicity:** While selection criteria and fallback order are pre-specified, allowing two sequential 3-seed confirmation attempts without alpha correction inflates the family-wise Type I error (roughly doubling the false survival rate under the null).
* **Recommendation:** Specify that if the primary fails confirmation at ep 300, DEV survival fails; reserve-seed evaluation of v2 is exploratory only.

---

### 7. Contractual Claim Inaccuracies in §4 (Point F) [NON-BLOCKING]
* **Discrepancies with CDRL Thesis:**
  1. *ACRM Competition:* §4 claims competition on the same task is kept. In v1 FULL, B competes against Catfish-A ($a^A$), not against the main learner.
  2. *M1 Stimulus:* §4 claims judge-approved proposals become intervention samples. In CDRL, M1 routed actual executed experiences to a second replay buffer; MC2 merely applies a loss label to the learner's own transitions.
  3. *M3 Intervention:* CDRL trained two concurrent agents with a 70/30 batch mix; MC2 trains a single learner with fixed scripted teachers.
  4. *Missing Disclosures:* §4 omits noting the complete absence of Phase-1 solver seeding, dual replay memories, and dual-agent rollouts.
  5. *Literature Citations:* Cheng et al. and Liu et al. learn value functions from oracle rollouts, rather than simulation-based oracle selection. DAgger (Ross et al., 2011) and Q-filter (Nair et al., 2018) should be cited instead.

---

### 8. Horizon Mismatch and Unobservable Noise in Judge Feedback (Point G) [NON-BLOCKING]
* **Temporal Horizon Mismatch:** $T_{\text{NEXT}}$ is designed for $t+1$ association persistence and foresight ([cf_tnext.py:10-24](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_tnext.py#L10-L24)). However, the judge $\kappa$ evaluates only step $t$ ([cf_judge.py:9-14](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/algorithms/cf_judge.py#L9-L14)). Any $T_{\text{NEXT}}$ action trading off a small step-$t$ rate to secure persistence at $t+1$ will be rejected by the judge. A positive result cannot be cleanly attributed to learned foresight.
* **Unobservable Physical Noise:** The judge evaluates $\kappa$ using the physical step-$t$ fading draw ([step.py:899](file:///home/u24/papers/mcrl-leo-handover-mc2/src/mcrl/env/step.py#L899)) and exact concurrent user interference, neither of which exists in the student's 113-dim pre-step observation. This injects partial-observability label noise into the student's margin targets.
