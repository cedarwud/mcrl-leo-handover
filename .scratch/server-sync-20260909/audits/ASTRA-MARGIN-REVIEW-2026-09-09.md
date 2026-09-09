**KEEP_AND_DOCUMENT.**

Your scalar calculation is correct for **actually executed extra power with a frozen denominator**; it does not refute the original argument.

The decisive evidence is the review that produced v1.9. It explicitly distinguishes **power imagined during scoring** from **power actually transmitted**:

> “Thus §1 can predict bits using increased power that execution never supplies.”

That is the original objection, and it is correct. [Original adjudication, §B](/home/sat/mcrl-hub/.scratch/multi-catfish-v023-controller-handoff-20260907/round9/ADJUDICATION-V16-PREREGISTRATION-CODEX-GPT6-ASTRA-2026-09-09.md:21)

Under [v1.6 §1](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.6-AMENDMENT-2026-09-09.md:6), scoring recomputed power using attenuated gains, while executed physics explicitly remained unchanged. For the isolated example:

- Scoring uses \(p_m=p_N/q\), predicts \(qh\,p_m/N=\Gamma\), and credits service.
- Execution still uses \(p_N\), giving \(qh\,p_N/N=q\Gamma\) under that fade.
- **The supposed reserve exists only in the scoring calculation.**

Your rebuttal changes execution to \(p_m\). That creates a legitimate alternative controller, but it answers a different question.

**V1.9’s compressed wording nevertheless needs correction.** “More power and more interference” should identify the hypothetical scoring quantities; “no reserve” should identify the unchanged execution. Read as a universal assertion that physical power margins cannot work, the sentence is wrong. Read in its documented origin, the objection is sound. Stojanovic and Chan support your executed-power construction for their SNR model; they do not invalidate this prediction/execution distinction. [Paper, printed p. 2968](https://www.mit.edu/~millitsa/resources/pdfs/icc02.pdf)

Items 2 and 3 do not establish a general coupled-system impossibility theorem. They specify a wanted-link stress scenario. Whether that scenario represents a SINR quantile depends on the fading dependence—and your engine has a particularly consequential dependence.

For the coupled solve, define, within one fixed TDM slot,

\[
u_i=\frac{\Gamma_iN_i}{h_{ii}},\qquad
A_{ij}=\frac{\Gamma_i h_{ji}}{h_{ii}},\qquad
Q=\operatorname{diag}(q_i).
\]

The current controller iterates

\[
p^{k+1}=\min(c,u+Ap^k).
\]

Your proposed wanted-link-only reserve constraint produces

\[
p^{k+1}=\min(c,Q^{-1}u+Q^{-1}Ap^k).
\]

These are componentwise caps. They correspond directly to the [engine’s power update](/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/architectures.py:361).

**The capped map does not diverge mathematically.** Starting at zero, its iterates are increasing and bounded by the caps; continuity gives convergence. Positive noise also gives uniqueness. That does not guarantee finishing within the engine’s finite iteration limit, and, more importantly, **convergence does not certify reserve feasibility**.

For the proposed uncapped system, the conditions are

\[
\rho(Q^{-1}A)<1,\qquad
p_q=(I-Q^{-1}A)^{-1}Q^{-1}u.
\]

All proposed reserve constraints are feasible under individual caps precisely when this solution exists and \(p_q\le c\). With common \(q\), the spectral condition tightens from \(\rho(A)<1\) to \(\rho(A)<q\).

If those conditions hold, the coupled fixed point does recover

\[
\frac{q_i h_{ii}p_i}{N_i+\sum_jh_{ji}p_j}=\Gamma_i.
\]

So coupling does **not** invalidate the conditional 90% argument when interference really stays fixed. It changes the required power, sometimes drastically.

For a symmetric system,

\[
p_N=\frac{u}{1-\rho},\qquad
p_q=\frac{u}{q-\rho},\qquad
\frac{p_q}{p_N}=\frac{1-\rho}{q-\rho}.
\]

That multiplier is generally larger than \(1/q\), and grows without bound as \(\rho\) approaches \(q\).

I checked constructed two-beam examples using the engine’s 2,000 km, 10° boresight gain convention, \(\Gamma_1=0.717495\), \(q=0.429235\), and cap 1.65 W. Scintillation is excluded from nominal gain here, consistently with the provider; the noise-only nominal requirement is 0.247703 W.

| Nominal coupling \(\rho(A)\) | Current power per beam | Proposed capped power |
|---:|---:|---:|
| 0 | 0.247703 W | 0.577080 W |
| 0.20 | 0.309629 W | 1.080563 W |
| 0.30 | 0.353862 W | 1.650000 W |
| 0.45 | 0.450370 W | 1.650000 W |

At \(\rho=0.30\), the proposed uncapped requirement is 1.916683 W. At \(\rho=0.45\), its uncapped fixed point does not exist, yet the capped solver converges in four iterations. Thus cap hits can increase from neither beam to both beams without any numerical failure.

There is also a direct counterexample to your predicted availability improvement. Using current thresholds and \(q\), I constructed a capped beam A with three identical users and a beam B with one user:

| | Current rule | Proposed amendment |
|---|---:|---:|
| A/B power | 1.65 / 0.300495 W | 1.65 / 0.700070 W |
| A/B margin-adjusted SINR | 0.772457 / 0.307974 | 0.658144 / 0.717495 |
| A/B selected mode | QPSK 1/4 / `NO_MODE` | `NO_MODE` / QPSK 1/4 |

**The boost rescues one user while stranding three.** Both solves converge. The normalized inputs were \(h/N=(1.25454545,2.39164931)\) and cross-gain matrix \(H_{\rm cross}/N=((0,0.5),(0.001,0))\). This is a constructed counterexample, not an observed probe result, but it is enough to defeat monotonic service-rescue reasoning.

The 90% interpretation has a more fundamental problem than your adjudication recognizes: **same-satellite interference shares the wanted link’s fading multiplier**.

The provider keys fading by user, satellite, and time; the interference path reuses that multiplier for every beam from that satellite. [Wanted-gain construction](/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/provider_legacy.py:683), [interference construction](/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/tapes.py:397)

Let \(I_s\) denote same-satellite nominal interference and \(I_k\) interference grouped by other satellites. Then

\[
\mathrm{SINR}_{\rm realised}
=\frac{S G}{N+I_sG+\sum_k I_kG_k}.
\]

With only same-satellite interference, the theoretical 90% constraint is

\[
qS\ge\Gamma(N+qI_s),
\]

**not** your more conservative \(qS\ge\Gamma(N+I_s)\). Equivalently, the appropriate shared-fading power equation is

\[
p=Q^{-1}u+Ap.
\]

Only the noise load increases; the coupling matrix stays unchanged. With common \(q\), \(p=p_N/q\) then really does achieve the intended quantile success event, despite nominal SINR not being \(\Gamma/q\).

This matters numerically:

- At \(\rho=0.20\) above, the shared-fading construction needs **0.721350 W**. Your proposed equation spends **1.080563 W**, approximately 50% more RF, and achieves **98.43%** decoding.
- At \(\rho=0.30\), your equation fails its reserve test at the **1.65 W cap**, yet actual shared-fading decoding at that power is **99.73%**.
- At \(\rho=0.45\), your proposed uncapped equation is infeasible, while the shared-fading quantile construction needs **1.049237 W**, within the cap.

Therefore, some of the amendment’s apparent “physical infeasibility” would itself be generated by a conservative controller choice.

This also limits v1.9 item 2’s rationale. Unchanged SIR under common attenuation can be the **correct physical cancellation** in this engine. It is not automatically evidence that a margin construction is defective.

I quantified the random-interference issue using the declared Rician/shadow/scintillation distribution. The following scenarios place a link exactly at equality in your proposed wanted-only constraint. Interference supplies half of nominal \(N+I\); the independent interferer has the wanted link’s elevation.

| Elevation | Noise only | Same-satellite interference | One independent satellite |
|---:|---:|---:|---:|
| 10° | 89.90% | 98.79% | 91.14% |
| 60° | 89.99% | 97.41% | 86.26% |
| 80° | 89.93% | 97.05% | 85.86% |

In the independent-interference limit, decoding falls to approximately **82.80% at 60°** and **82.55% at 80°**. The sign is not universally pessimistic: at 10°, this independent-interference example exceeds 90%. Nominal interference is not its mean; the engine’s mean fading gain is approximately 0.858 at 10° and 1.252 at 60°.

Shared-fading entries used numerical integration; independent entries used two million draws, with approximately ±0.06 percentage-point or smaller 95% sampling uncertainty. These are conditional results for your channel model, **not fleet averages**. Actual-provider reconstruction stopped at the missing `sgp4` dependency, so I cannot honestly give a population-weighted reliability or cap-frequency change.

Two further qualifications apply:

- The implemented quantile is estimated from 200,000 draws and rounded to a 0.5° elevation bin. It is not exactly the true quantile. Near the steep 80–90° shadow-table transition, checked bin endpoints give noise-only success between approximately **88.57% and 91.47%**.
- A 90% decode probability is not a 50 Mbit/s delivered-rate guarantee. At occupancy two, the target mode delivers 54.8203 Mbit/s when decoded; 90% of that is **49.3383 Mbit/s**.

For the activation mechanism, your arithmetic identifies a real effect **of this controller**. The nominal power budget rises with occupancy; that can enable a previously unavailable mode. It does not prove a positive whole-objective interaction after donor-beam losses, energy, interference, and movement costs.

The finding also overgeneralizes its elevation coverage: at **80°**, the actual \(q=0.328885\) is below the activation window’s lower bound. “Every realistic elevation” is false.

The shared-payload-pool defense cannot rescue this implementation. The engine imposes individual beam caps; its 64.35 W aggregate and 100 W reference are explicitly **not live aggregate constraints**. [Constants](/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/constants_v025.py:88) V1.8 also explicitly distinguishes its assumed beam/chain architecture from shared-amplifier payloads.

Nevertheless, **a nominal power-allocation policy followed by ACM within that allocation is a legitimate benchmark controller**. Unused hardware capacity does not make such a policy mathematically inconsistent. Its particular allocation rule can be inefficient and its coordination effects strongly policy-dependent.

The important contextual fact you omitted is that [v1.8 item 5](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.8-AMENDMENT-2026-09-09.md:9) already declares \(r^*\) a **power-control setpoint, not a demand model**. Your back-off theorem therefore establishes a reported performance consequence, not automatically a violated service obligation. ETSI supports fixed-power ACM generally; it does not validate your particular occupancy-based allocation or unexplained `NO_MODE` radiation. [ETSI §4.4.1](https://www.etsi.org/deliver/etsi_tr/102300_102399/10237601/01.02.01_60/tr_10237601v010201p.pdf)

Taking your stated freeze as operative, your adjudication has not met its burden for replacement. The [freeze rule](/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-DESIGN-FREEZE-AND-CLOSURE-RULE-2026-09-09.md:8) requires all four conditions, including an identified certificate consequence and a failing-now/passing-after test. A test demanding robust attainment of \(r^*\) would introduce a requirement that the setpoint declaration does not contain.

Most of a day could satisfy the overnight allowance; cost would not excuse an established correctness failure. But you have established an alternative controller, not the necessity of replacing this one. Moreover, your proposed alternative still needs decisions about shared fading, independent interference, and cap handling. A compulsory second controller experiment would expand that unresolved scope.

**Keep the sealed primary, correct the rationale, and make the controller dependence central to the method and claims.** The activation effect cannot be advertised as an inherent satellite constraint. It can be reported as an interaction arising under the declared controller. Preserve the already-sealed robustness diagnostic.

Separately, these are the overstatements in your adjudication. I have grouped repeated versions of the same claim; the two explicitly provisional engine checks are now resolved.

1. **“That reasoning does not hold.”**  
   This also underlies the document title and §1 heading. The original reasoning correctly criticized scoring with power execution never supplies. Your rebuttal silently changes execution.

2. **“nominal SINR becomes `Γ/q`, which is above threshold, not at it;”** and **“realised SINR is `Γ·G/q`, so decoding succeeds exactly when `G ≥ q`, which is probability 0.90 by the definition of `q`;”**  
   These require executed extra power, the appropriate fixed denominator, matching normalization, no clipping, and an exact quantile. The later qualifications are good, but they prevent using these statements as an unconditional refutation. The same restriction applies to “The nominal link sits above threshold and the lower-decile faded link sits at threshold.”

3. **“The defect is our particular composition: solve power to leave exactly zero nominal headroom, then demand headroom while forbidding any power adjustment.”**  
   You establish an undesirable consequence of the composition. Calling it a correctness defect requires a service obligation beyond the declared power-control setpoint.

4. **“Ordinary fixed-power ACM does not do that, because it never removes the headroom in the first place.”**  
   Unsupported universal statement. Fixed-power ACM does not guarantee adequate headroom relative to every requested mode.

5. **“So a backed-off user decodes but never meets `r*`.”**  
   Decoding remains conditional on the realised channel. The rate shortfall is correct for a strictly lower-threshold mode at unchanged airtime; its status as a specification violation is not.

6. **“At occupancy 2 the backed-off mode delivers 34.04 Mbit/s against a 50 Mbit/s target.”**  
   Under the actual quantile, occupancy two selects `NO_MODE` and delivers zero. 34.04 Mbit/s is the hypothetical successfully decoded QPSK 1/4 rate.

7. **“Zero-payload transmission at full power needs its own justification.”**  
   `NO_MODE` transmissions use computed power, not necessarily the cap. Your later correction does not repair this earlier wording.

8. **“For a bits-minus-price-times-joules objective, muting it is preferable unless a signalling or synchronisation purpose is modelled.”**  
   Valid as a local comparison with positive energy price, permitted muting, and other transmissions held fixed. A profile change that triggers coupled power re-solving needs a separate comparison. The unexplained radiation remains a legitimate modeling weakness.

9. **“My reported figures are mutually inconsistent and I did not notice.”**  
   Your paragraph establishes different denominators, not inconsistency. “Not directly comparable” is supported; the conditional availability bound is correct.

10. **“If its selection has the same shape as the figure’s, it is silently choosing a lower-throughput mode in part of the range, which would suppress credited bits and therefore energy efficiency everywhere.”**  
    “Everywhere” overstates even the hypothetical effect. More importantly, the suspected engine bug is absent: both [scalar selection](/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/acm.py:72) and [batch selection](/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/batch.py:408) maximize efficiency. You correctly labeled this provisional; it should now be closed.

11. **“The evidence does not show that the engine double-counts; it shows that nothing rules it out.”**  
    Current source rules it out in the provider path: [nominal gain explicitly removes scintillation](/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/provider_legacy.py:413), and the complete fading product supplies it once. The figure’s normalization remains a separate check.

12. **“The figure’s fixed 2,000 km at 10 degrees and the link-closure ledger’s 550 km and 1,100 km cases must be reconciled, or the paper will carry two link budgets that do not describe the same system.”**  
    Different geometries can describe different cases within one system. They need consistent conventions and explicit labels, not necessarily identical budgets.

13. **“The coherent construction for our rate-target controller is to test whether the target mode survives the declared reserve,”**  
    It is **a** coherent conservative construction. The shared-fading constraint is another, materially less restrictive one. Neither is uniquely mandated by the existing setpoint contract.

14. **“subject to the RF cap and payload constraints, and then to distinguish three outcomes explicitly: lower-rate service, rate-target failure, and no data service.”**  
    If “payload constraints” means a shared power pool, that constraint is currently absent. Also, those outcome names overlap: lower-rate service can itself be rate-target failure.

15. **“A binding cap removes the 90 % guarantee, so a cap-induced shortfall must surface as an explicit feasibility failure rather than a silent demotion.”**  
    Binding alone does not remove it. Exact equality at the cap can satisfy the requirement; a lower mode can remain reliable; and failure of your conservative inequality can coexist with more than 99% actual shared-fading reliability.

16. **“Amending the rule will probably reduce the headroom C3 is chasing.”** followed by **“Fewer users will be stranded, availability will rise, contention will fall, and the coordination lever measured this morning will shrink.”**  
    The first is a hypothesis. The second asserts unestablished directions. The constructed cap externality disproves monotonic rescue, and increasing power does not itself reduce occupancy contention.

17. **“Keeping the defective rule would preserve a larger apparent opportunity for C3.”**  
    Neither “defective” nor the net direction of the C3 change has been established. Removing one interaction mechanism does not determine the total effect.

18. **“A coordination gain measured inside a controller-induced outage is not a finding about satellites.”**  
    Too categorical. It can be a finding about a specified satellite controller. It does not establish a controller-independent physical limitation or coordination benefit.

19. **“The alternative is a paper whose headline availability is an artefact of a rule an outside reviewer has already shown to be mathematically misjustified.”**  
    This is a false dichotomy and misstates the original review. The available alternative is an accurately described, explicitly bounded controller study.

The read-only analysis took approximately 11 minutes. No files were modified.
