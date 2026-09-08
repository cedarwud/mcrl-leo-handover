I'll start by reading the uploaded package.**1. Outcome-driven design — where I would attack, and what defuses it**

(a) *The regime was built to manufacture headroom after 18 failures.* File 01 §2 picks finite demand explicitly because it "可產生 last-user shutdown complementarity" — the one axis whose surplus is non-additive by construction. The §1 blockquote helps; add: "the demand axis was chosen from the five-axis shortlist of §2 by the minimal-change principle before any regime-B simulation output existed; Track B claims *conversion* of declared headroom, never its existence."

(b) *Thresholds were set after seeing E1.* E1 merged 05:59 UTC (file 04); file 03 is stamped 06:15–06:20 UTC; the 5 %/1 % bars sit just above E1's 2.22 %/0.23 %. State it: "thresholds were fixed with knowledge of E1's regime-A values and deliberately above them; no regime-B output existed."

(c) *You screen twice on an oracle version of the outcome variable.* File 03 step 2 ("a point whose oracle marginals are not all positive does not proceed") filters the grid on the same three-marginal conjunction the campaign tests. Defensible only with a rule file 03 lacks: "Grid order and both screens are frozen; a point failing either screen is reported and the next point in order is tested; the campaign runs at the first point passing both, or Track B reports NONE. Because the screens select on *oracle* marginals, the campaign result is a learnability/deployability claim conditional on oracle existence, never a regime claim."

(d) *Weak carriers.* File 01 §4 measures headroom against nearest-eligible/stay/random rules (§7 admits it). The FULL2-B re-check ("comparator-strength falsifier，不回頭換grid") is right but undefined: which thresholds are re-applied, and does the campaign still run if they fail?

**2. Thresholds and selection rule**

The selection rule is sound and should stay: G1→G2→G3 is monotone in departure from regime A, so "first qualifying" is the least-constructed point, and "never the best" is the right protection. Three threshold defects:

- *Absolute, against carriers that are not EE-aware.* Closing a below-average beam raises pooled EE even in full buffer, so against random-masked, J₁ ≥ 5 % will very likely hold at G0 = ∞ too, and the probe cannot separate regime B from regime A. G0 runs anyway (§2), so make the criteria increments over G0 with identical carriers: (J₁/η_ref−1)_Gk − (·)_G0 ≥ 5 % and [(J₁−U₁)/η_ref]_Gk − (·)_G0 ≥ 1 %. Never less conservative, and the only version that isolates the regime effect.
- *Threshold 3 is under-specified.* The surplus needs a λ, and λ_B (§3) does not exist at probe time. Declare λ_probe = η_ref of that carrier at that point. Also report ΣΨ/ΣV(joint witness): if most witness surplus is additive, the point does not discriminate architectures whatever the 0.5 % says.
- *The demand guard leaks.* "≥95 % of users at ≥95 % of demand" lets every user be shaved by 5 % of bits; in a regime whose hypothesis is "hold bits, cut joules", EE gained by goodput shaving is the artefact to exclude. Add pooled delivered bits non-inferior to M12 (paired CI lower bound ≥ −0.1 %) for the witness and every arm.

Also define "positive" in the 3/4 rule (world-level ratio and service; descriptive per file 05 §4), and pre-declare that a null campaign at the selected point reads "not converted at the least-departed qualifying point", not "coordinator fails".

**3. Success criterion**

"C1, C2, C3 each positive" (file 03) should not be the headline. (i) "C3" is not the same object in M123 (a third Q head under one masked argmax) and S3 (a configuration predictor inside a decoder that also owns catalog and atomic execution); DROP_C3 is well-defined only for M123, where it equals M12; in the set family "C3 positive" means S3 > S0 — a learning-value claim. (ii) File 03 says "> 0", file 01 §3 says "≥1 % vs M12, CI lower bound > 0"; in regime A a −0.049 % pooled direction was a STOP (file 08 row 17), so point-estimate marginals are noise. Apply the CI rule to every marginal. (iii) C2 exists to protect service; pre-declare how an EE-neutral but guard-improving C2 is scored, or the conjunction fails for a reason unrelated to coordination.

The primary contrast is the lever regime A never varied (file 08 §4.1): composition. Headline = {M123−M12} against {S0−M12, S3−M12} under identical guards; C1/C2 marginals are a secondary robustness result. Pre-declare the set-family ablations now (S3 vs S0 = learning; S0 vs M12 = decoder; DROP_C1/C2 = proposal-generator ablations) and budget them (§5 prices five arms).

If only the coordinator works, the paper must say: no third additive Catfish exists in either regime; the positive result is a set-level decoder and is not called "C3"; if S0 ≈ S3, learning contributed nothing and the claim is model-based decoding; the result is conditional on a screen-selected point; the "each positive" criterion was declared and not met for the additive family; regime A's negative result stands and no coordinator was run there (unless §5).

**4. Most likely failure mode and its cheap pre-check**

The retrained BASE absorbs the headroom. Under finite demand C1's unilateral target already prices the last-user shutdown, so FULL2-B consolidates on its own; the residual multi-user evacuation surplus against a strong BASE may be far below what fixed-rule carriers show, and the campaign returns S3 ≈ M12 with no way to tell "regime too weak" from "coordinator fails". The planned re-check (file 01 §4) comes only after 75–205 worker-hours of training and target generation (§5).

Pre-check: declare now a fourth fixed carrier — a deterministic demand-aware consolidation rule (stay if demand met; else join the active feasible beam with most spare capacity; open a beam only if none) — and require the thresholds against it too. Cost: one more carrier's acquisition per grid point (E1 ran 12 units in 18 min, file 04). Second cheap check, because it killed ZR (file 08 rows 14–15): re-solve the J catalog with nominal-fading B/E coefficients and evaluate the chosen profiles on the realised tape; if the nominal-selected witness keeps less than half of J₁, S0 is dead before training.

**5. Should Track B exist?**

E1 (file 04) says regime A has 2.2 % headroom, of which 0.23 % is joint-specific. A regime-A coordinator therefore chases a coordination-specific gain below your ≥1 % margin (file 01 §3) and inside regime-A noise. But the 2 % *unilateral* headroom is an oracle-to-deployment gap of the existing heads, and cheap to attack: existing FULL2 checkpoints as proposal generators, E1's certified catalog and tape, a nominal-physics S0 decoder, a one-step kill screen at F1 cost (383 s per world×lineage×2 steps, file 05 §8). It is file 06 §10's "single most informative experiment", in the paper's primary regime, with a certified ceiling.

Recommendation: run that first. Then Track B — in this paper only the sealed probe (regime map with G0-relative thresholds, strong carrier, nominal re-solve, oracle marginals; 12–24 worker-hours), reported as mechanism localisation. The 280–550 worker-hour campaign (file 01 §5) cannot finish before a deadline of "數天"; pre-declare it as follow-up with its contract sealed now. Track B should exist — it is the only place a coordination-specific claim can be tested — but the regime-A screen answers the deployability question the paper actually needs, first.