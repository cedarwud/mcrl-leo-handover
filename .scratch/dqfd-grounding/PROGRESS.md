# DQFDGROUND progress — COMPLETE 2026-09-11

Output: `/home/u24/papers/mcrl-leo-handover/.scratch/dqfd-grounding/DQFD-FAMILY-GROUNDING-2026-09-11.md` (444 lines)

- [x] Q1 DQfD spec — arXiv:1704.03732 full text + Supplementary. J(Q)=J_DQ+λ1 J_n+λ2 J_E+λ3 J_L2; λ=1.0/1.0/1e-5; margin 0.8; k=750,000 pre-train steps on demo data only; ε_d=1.0 / ε_a=0.001; α=0.4, β0=0.6; n=10; γ=0.99; τ=10,000; demos NEVER evicted; demo fraction EMERGES from prioritised replay, is not declared.
- [x] Q2 Ablations — Fig 2 left (λ1=0, λ2=0, both degrade; supervised removal worst, n-step "nearly as large"); Fig 2 right (RBS / HER / ADET all worse than DQfD; "Having a supervised loss is critical"). 41/42 vs PDD DQN; 39/42 vs imitation; beats best demo on 14/42, worst demo on 29/42.
- [x] Q3 Demonstrator quality — yes, the margin anchors. Named as a defect by POfD (ICML 2018), MCPO (1911.07109), Nair (1709.10089). Fixes: Q-filter (1709.10089), no-imitation-loss (DDPGfD 1707.08817), occupancy matching (POfD), soft constraint (MCPO), self-imitation (1806.05635), tiny demo ratio (R2D3 1909.01387: optimum ≈1/256).
- [x] Q4 Multiple demonstrators — pooling dominates; R2D3 pooled 3 experts into ONE buffer. Per-demonstrator buffers only in Policy Distillation (different problem), ZPD (workshop), DMDE (paywalled). NO paper anywhere sweeps the NUMBER of demonstrators. Closest: ZPD Table 2 (best single teacher wins 0/9).
- [x] Q5 Multi-objective + demos — near-empty. Only arXiv:2404.04857 and arXiv:1809.08343 have a genuinely one-objective demonstrator; both CONFINE the demo signal to its own reward component. MOIRL line is a different problem.
- [x] Q6 Mapping table — (i) supported as class but catfish parameterisation = RBS = published negative; (ii) partial (source split yes, absolute value threshold NOT FOUND); (iii) NOT FOUND; (iv) exists as HER/R2D3 ρ and evidence is NEGATIVE at 30% (R2D3 optimum 0.39%), random period NOT FOUND; (v) NOT FOUND + Ng/Harada/Russell 1999 warning.
- [x] Table D2 (DQfD) — 15 specified, 4 UNSPECIFIED (learning rate, optimizer, minibatch size, buffer capacity; plus β annealing schedule).
- [x] Table D1 (catfish) — RIS paper specifies exactly ONE runnable number (70/30). EE_high, γ^M, γ^CF, intervention period, η all UNSPECIFIED in the paper. Also flagged: code computes r^C = r^CF + η(r^CF − r^M), substituting r^CF for the paper's r.

## Nothing left open
Two items are flagged in-report as unverifiable rather than open:
- DMDE (Information Sciences 648, 2023) and MD2-GAIL (Neurocomputing 457, 2021) are paywalled; per-demonstrator buffer claims unverified.
- The RIS paper's "SASR / Shen et al." citation could not be matched to any paper; the SASR located is Ma et al. ICLR 2025 arXiv:2408.03029 and does not resemble ACRM.
