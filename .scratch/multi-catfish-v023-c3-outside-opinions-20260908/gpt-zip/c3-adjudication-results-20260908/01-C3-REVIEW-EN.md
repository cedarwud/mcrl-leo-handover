# C3 research-line adjudication

Review date: 2026-09-08  
Source: multi-catfish-c3-chatgpt-review-package-20260908-r1.zip  
This file preserves the complete substantive review delivered in the conversation. Chat-only citation paths have been converted to portable relative links; this packaging step adds no experiment or new adjudication.

**1. The record rejects the tested C3 implementations. It does not establish that every third-head mechanism is impossible.**

The practical conclusion is nevertheless severe: **no tested C3 is currently admissible, and none deserves another tuning or rescue cycle.**

I read the package in the requested order and inspected the relevant contracts and code. The ZIP contains the F1 receipt and detailed R7 reporting, but not the underlying physical tapes; the conclusions below distinguish reported experimental evidence from code inspection and mathematical deductions.

| Question | What the record establishes | What remains unproven |
|---|---|---|
| **(a) Target family** | The specified PNFE/MONE, ZR successors, LC-SRS admission hypothesis, and D/F contingencies failed their respective contracts. LC-SRS’s prescribed physical signature failed despite correct coalition arithmetic. | That **every** bits/energy externality or global-objective difference utility is useless. The chronology includes positive intermediate oracle results, including V0.20 exact **+0.985%**. |
| **(b) Learner observability** | Several ZR representations failed. **R7 observability passed:** balanced accuracy **0.705 vs 0.626**, Spearman **0.839**, and **8/8** world wins. | That R7’s prediction quality is sufficient for useful decisions, or that another target is observable from the permitted state. “C3 cannot learn anything” is directly contradicted by R7. |
| **(c) Composition** | The tested target/interface combinations repeatedly failed under simultaneous per-user additive selection. R7 learned composition was **−0.660%**, with topology consistency **379/707 = 0.536**. | Composition was never independently varied, so its isolated causal contribution is unidentified. Neither alternative composition nor every possible additive third head has been falsified. |
| **(d) Horizon and deviation** | Current-slot targets repeatedly failed admission. However, the history was **not exclusively unilateral**: V0.11 anticipated joint responses, and LC-SRS evaluated four two-user profiles. | A genuine multi-step externality with physical branch continuation, or a joint action target that retains coordinated execution. |
| **(e) Anchor/world regime** | R7 failed on its eight declared development worlds; D/F failed on one world, one lineage, and two BASE-trajectory anchors. | Universal failure across policies, operating regimes, or subsequent trained checkpoints. Those possibilities are untested—not reasons to replace unfavorable worlds. |

Sources: [01-CHRONOLOGY.md](evidence/01-CHRONOLOGY.md), [02-R7-STOP-PHYSICS-RESULT.md](evidence/02-R7-STOP-PHYSICS-RESULT.md), [03b-F1-r2-receipt.json](evidence/03b-F1-r2-receipt.json).

Two distinctions matter:

- **Gate failure is not statistical proof of universal harm.** R7’s **−0.0493%, 2/8 positive worlds** conclusively fails its declared admission rule. It does not establish a negative population effect with quantified confidence.
- **F1 BASE is not the pre-Catfish MODQN baseline.** It is the older V0.20 repriced Q1/Q2 checkpoint, lineage 2026092101, rung 003000. It is also not the forthcoming 100-epoch C1/C2 successor. [F1-README.md](evidence/10-PHYSICS-AND-CODE/F1-README.md)

**2. The central failure is converting a predicted allocation into an improving joint decision.**

**Learnability and factoredness are different properties.** A signal can be predictable while giving the wrong incentives. For a global utility \(G\), a difference utility

\[
D_u(a_u,a_{-u})
=G(a_u,a_{-u})-G(a_u^0,a_{-u})
\]

preserves unilateral action rankings when the subtracted baseline is independent of the action being compared. This alignment is separate from how easily the utility can be learned. It also does not guarantee improvement when everyone simultaneously changes against an obsolete background. These are explicit distinctions in the [COIN analysis by Lawson and Wolpert](https://cdn.aaai.org/AAAI/2002/AAAI02-051.pdf).

R7 establishes useful prediction of its declared labels. It does **not** establish that:

- the labels rank the full deployed scores correctly;
- errors are small on decisions near an argmax boundary;
- both coalition members adopt compatible actions;
- other users preserve the assumed destination topology;
- the resulting joint configuration improves pooled EE.

The coalition identity

\[
\sum_i(\ell_i+z_{3,i})=G_\lambda(11)-G_\lambda(00),
\qquad G_\lambda=B-\lambda E,
\]

is an accounting identity for named physical profiles. It neither makes its right-hand side positive nor identifies it with arbitrary learned \(Q_1+Q_2+Q_3\) decisions. The code explicitly disclaims exactness for partial adoption, hybrid profiles, learned Q sums, and deployment closure. [ee_axis_coalition_residual_c3.py](evidence/10-PHYSICS-AND-CODE/ee_axis_coalition_residual_c3.py)

That explains why the R7 results are compatible rather than contradictory:

- Prescribed source **11 vs 00: −0.0493%**.
- Exact teacher composition: **+0.335%**.
- Learned composition: **−0.660%**.

They evaluate different constructions. The approximately **0.995 percentage-point** teacher-to-learner gap is additional evidence of failure in realizing the teacher’s decisions; it does not rescue the failed source hypothesis.

**Coordination is a substantive obstacle.** Emptying a beam may require several users to leave together. A unilateral departure can incur costs without removing the beam’s circuitry or satellite overhead. Conversely, several individually attractive deviations can jointly expand activation or interfere with one another. V0.10 already recorded positive summed unilateral surpluses in all 60 diagnostics, while the realized joint direction reversed in 28. LC-SRS partially addressed joint valuation, but distributed its value back into independently selected action cells.

A 28-action OPS-3 input describes **one user’s alternatives**. It is not a joint action space. Adding that input to Q3 alone does not provide coordinated execution. Methods such as [Deep Coordination Graphs](https://proceedings.mlr.press/v119/boehmer20a.html) explicitly retain pairwise joint payoffs and use a corresponding joint maximization procedure; importing only the payoff idea loses that connection.

**κ is not an established explanation for failure.** The correct distinction is

\[
Q_1+Q_2+z_3/\kappa
\quad\text{for raw-bit oracle targets,}
\qquad
Q_1+Q_2+Q_3
\quad\text{for the already-normalized learned head.}
\]

Here \(\kappa=10{,}097{,}071{,}012.757404\) bits. Dividing learned Q3 again would be wrong. The completed F1 used the correct conversion. Common normalization supplies compatible units; it does not ensure compatible calibration.

For \(f_u=Q_{1,u}+Q_{2,u}\), an alternative beats the reference only when

\[
Q_{3,u}(a)-Q_{3,u}(b_u)
>
f_u(b_u)-f_u(a).
\]

Sign accuracy and Spearman do not directly test this inequality. C3 can be ineffective on some margins and disruptive on others. Indeed, the V0.14 memo reports an earlier selected correction median of **\(0.47\kappa\)** against a base margin median of **\(0.18\kappa\)**: C3 was not universally drowned. Changing its relative weight would be a new intervention, not a unit repair. [06-COMPOSITION-RULING.md](evidence/06-COMPOSITION-RULING.md), [V0.14 probe adjudication](evidence/09-PRIOR-DESIGN-ADJUDICATIONS/v014-q3-probe-stop-design-adjudication-2026-09-03.md).

**D/F expose a further alignment problem.** Let \(s_u=\mathrm{share}_u\), so conservation gives \(E=\sum_v s_v\). Their declared formulas imply

\[
z_F=\lambda\Delta s_{-u},
\qquad
z_D=\Delta B_{-u}+\lambda\Delta s_{-u}.
\]

Thus their correction positively rewards increases in energy allocated to others. It is not automatically a global-surplus externality. Using the coalition code’s physical own term \(\ell_u=\Delta B_u-\lambda\Delta E\),

\[
\ell_u+z_D=\Delta B_{\rm total}-\lambda\Delta s_u,
\]

which differs from \(\Delta B_{\rm total}-\lambda\Delta E\). This is diagnostic algebra—not an identity for the learned Q1/Q2 scores.

The F1 totals are consistent with excessive energy expansion:

| Candidate | Delivered bits | Network energy | EE |
|---|---:|---:|---:|
| D | +6.928% | +8.367% | −1.328% |
| F | +14.749% | +20.202% | −4.536% |

This does **not** prove that the energy term caused the entire loss, and it authorizes **no sign-flip replay**. It does show why D/F’s failure cannot stand in for a test of every factored global-surplus utility. [04-CONTINGENCY-LADDER.md](evidence/04-CONTINGENCY-LADDER.md), [c3_contingency_f0.py](evidence/10-PHYSICS-AND-CODE/c3_contingency_f0.py).

**The pooled objective must remain explicit.** For pooled baseline totals \(B_0,E_0\),

\[
\frac{B_0+\Delta B}{E_0+\Delta E}>\frac{B_0}{E_0}
\iff
\Delta B-\eta_0\Delta E>0,
\qquad \eta_0=B_0/E_0.
\]

A positive nonfocal bit effect is insufficient. A positive \(B-\lambda E\) change also need not imply positive EE when \(\lambda\ne\eta_0\). This comparison identity provides no permission to retune the frozen training price.

Finally, **fixed-policy evaluation cannot teach Q3 to recover**. More evaluation episodes improve measurement; they do not improve its parameters. F1 is narrower still: it commits BASE between anchors, so it does not measure D/F’s own evolving trajectory.

**3. Four candidates merit consideration, ranked by what is worth investigating next. Only the first merits immediate expenditure.**

**First: a correctly scoped existence diagnostic.**

This is a diagnostic, not a new Catfish algorithm.

At each declared BASE anchor \(t\), define

\[
\mathcal U_t=\{b_t\}\cup
\{b_t[u\leftarrow a]:a\text{ legal}\}.
\]

Compute the service-constrained pooled ceiling

\[
U_1=
\max_{\substack{c_t\in\mathcal U_t\\
S(c)\ge S(b)-0.001}}
\frac{\sum_t B_t(c_t)}{\sum_t E_t(c_t)}
-\eta_{\rm BASE}.
\]

This permits at most one changed user **per fixed anchor**. It optimizes the pooled ratio; separately maximizing each anchor’s EE is not equivalent because energy weights change.

- **Why worthwhile:** it separates lack of local physical opportunity from a bad target or selector.
- **Why not already falsified:** none of the recorded targets exhaustively maximized this objective over this domain.
- **Falsifier:** \(U_1=0\), within numerical precision, means no strictly profitable feasible intervention in that finite class. Since BASE is included, **\(U_1<0\) is impossible for a valid maximum**.
- **Cheapest screen:** existing unilateral tape arithmetic, once authenticated; fresh comparable tape generation has the observed reference cost of about six minutes per world × two anchors.

**The proposed “per-user best-response upper bound” needs correction.** Applying everyone’s individually optimal unilateral response simultaneously is a joint intervention, not an upper bound. It can lose despite positive unilateral opportunities. Conversely, no profitable unilateral move does not exclude a profitable coalition that an additive score surface could jointly induce.

Therefore, a zero result closes only the specified local opportunity class. A separate literal simultaneous-execution diagnostic can test composition, but must not be called an upper bound.

A positive realized-fading maximum is also only a **clairvoyant ceiling**. V0.20/V0.21 already show why this distinction matters. Evidence for usability requires selection from permitted predecision information or declared auxiliary expectations, followed by separately keyed physical evaluation.

**Second: a joint coalition target with joint execution.**

For a prospectively specified coalition \(C\), retain the action-dependent joint value

\[
T_C(a_C)=
\mathbb E\!\left[
G_\lambda(b_{-C},a_C)-G_\lambda(b)
\mid I_t
\right].
\]

For two users, the interaction is

\[
\Psi_{uv}(a_u,a_v)
=G_\lambda(a_u,a_v)
-G_\lambda(a_u,b_v)
-G_\lambda(b_u,a_v)
+G_\lambda(b_u,b_v).
\]

- **First-principles reason:** shared activation costs are nonseparable. Joint selection can realize savings unavailable to isolated moves.
- **What is genuinely new:** retain the joint payoff surface and execute a compatible bundle. Another \(\Psi/2\) allocation to independent action cells would repeat LC-SRS.
- **Falsifier:** the predeclared coalition domain offers no positive service-feasible pooled opportunity, or its information-feasible selector fails after actual joint execution.
- **Cheapest screen:** a bounded, physically defined coalition catalogue, with all membership and action-enumeration rules fixed before evaluation.

This is the strongest substantive research direction, **but it changes the deployment architecture unless the existing interface can demonstrably realize the bundle**. It belongs naturally in follow-up work.

The six-minute claim does not cover exhaustive joint search. With 100 users and 27 alternatives each, all two-user alternatives already number up to **3,608,550 per anchor**. The stored F1 tape contains unilateral profiles and selected D/F joints; unseen joints require new physical evaluations.

**Third: C3 as a restricted tie-breaker or veto.**

Define an outcome-independently fixed band

\[
\mathcal A_u^\epsilon
=\{a\text{ legal}:f_u(b_u)-f_u(a)\le\epsilon\},
\qquad
a_u^*=\arg\max_{a\in\mathcal A_u^\epsilon}\widehat D_u(a),
\]

where \(\widehat D_u\) predicts a declared global-objective difference.

- **First-principles reason:** bound the sacrifice in Q1+Q2’s score while using C3 to distinguish near-equivalent alternatives.
- **Why not falsified:** this composition rule was never tested.
- **Falsifier:** no action exposure, nonpositive pooled EE, or service failure under literal full-roster execution.
- **Cheapest screen:** score the fixed band from a unilateral tape, then physically evaluate its selected joint vector at each anchor.

This bounds **score sacrifice**, not EE loss. It does not solve simultaneous coordination automatically. ε needs an independent justification—such as an existing score-error bound—and cannot be chosen from favorable observed margins. It is a new method contract, not an R7 repair.

**Fourth: a genuine horizon-H externality.**

With continuation policy and horizon fixed independently,

\[
z_{3,u}^{(H)}(a)=
\mathbb E\!\left[
\sum_{h=0}^{H-1}
(\Delta B_h-\lambda\Delta E_h)
-\Delta L_{u,H}
\mid I_t
\right],
\]

where \(L_{u,H}\) explicitly identifies the contribution already assigned to C1/C2.

- **First-principles reason:** handover costs and consolidation benefits can occur at different times.
- **Why not falsified:** the existing C3 targets are current-slot constructions; BASE-anchor tapes do not test counterfactual trajectories.
- **Falsifier:** no information-feasible, service-preserving pooled gain over the declared horizon under actual continuation, or failure to compose with the frozen heads.
- **Cheapest screen:** cloned paired physical branches for a bounded predefined action catalogue, before learner training.

This requires a precise non-overlap derivation. C2 already averages projected own-surplus over up to three future decision offsets; merely extending that projection is not a new externality. D2’s substep machinery helps implementation but does not supply free counterfactual rollouts. [ee_axis_ops3.py](evidence/10-PHYSICS-AND-CODE/ee_axis_ops3.py)

**Wonderful-Life Utility is a design criterion, not a fifth rescue candidate.** The necessary check is whether changes in the **complete deployed score**, with others fixed, preserve the physical objective’s action ranking. Establishing that property for Q3 alone is insufficient after adding Q1+Q2. Even exact unilateral factoredness does not guarantee profitable simultaneous updates. Likewise, [COMA](https://arxiv.org/abs/1705.08926) uses counterfactual credit inside a specified critic-and-policy-gradient construction; it does not justify arbitrary additive deployment bonuses.

**4. Choose (i): one terminal existence diagnostic now, while C1/C2 proceeds. Default to excluding C3 from this paper’s working method.**

**There is still a legitimate research path, but currently a weak one-week completion prospect.** I would fund the cheap diagnostic because it can distinguish physical opportunity, information access, and composition. I would not fund another sequence of target variants.

My subjective probability that C3 becomes usable within approximately one week is **10%**—approximately **5% if the current per-user information and additive deployment interface must remain unchanged**. These are judgment estimates, not frequencies inferred from eight independent trials; the attempts share substantial structure.

“Usable” means an observable, deployable third mechanism that passes prospective admission and demonstrates a positive marginal under the declared physical and service evaluation. Another positive oracle or prediction gate is insufficient.

The result that would change my assessment is:

> A prospectively fixed, information-feasible selector achieves positive pooled EE under actual permitted composition across the complete declared panel, preserves service, and exposes an independently justified route to a distinct third mechanism.

That would raise my one-week estimate to roughly **20–25%** and justify considering one bounded learner admission. A positive clairvoyant maximum alone would barely change it.

A zero local ceiling, or opportunity that disappears under permitted information or composition, would end further C3 expenditure **for this paper**. Joint or longer-horizon research could remain follow-up work.

The diagnostic must have a single frozen domain, panel, uncertainty treatment, and terminal interpretation before computation. It must not re-run D/F or LC-SRS on replacement worlds. Reusing the opened F1 tape is legitimate for a disclosed retrospective existence analysis, but cannot serve as independent confirmation.

The sealed C1/C2 experiment remains separate, and its success is still to be established. Its declaration requires retrained neutral-source ablations and the unchanged MODQN comparator; a future C3 result must not silently alter that experiment. [07-C1C2-SUCCESSOR-DECLARATION.md](evidence/07-C1C2-SUCCESSOR-DECLARATION.md)

**5. Suggested Chapter 5 wording:**

Across eight grouped C3 design families, no candidate satisfied the complete preregistered admission requirements, although several intermediate oracle and mechanics tests were positive. In LC-SRS R7, held-out prediction passed (balanced accuracy 0.705 versus 0.626 for matched placebo), but the prescribed 11-versus-00 physical comparison reduced pooled EE by 0.049%, and learned composition reduced EE by 0.660% relative to its frozen Q1/Q2 reference. The predeclared CSE and EC contingencies subsequently reduced pooled EE by 1.328% and 4.536%, respectively, in a two-anchor TRAIN screen, with CSE also failing service non-inferiority. We therefore excluded C3 from the separately declared C1/C2 evaluation, retained the unsuccessful development record without retrospective changes to acceptance rules, and interpret these findings as failures of the tested target–information–composition combinations rather than proof that coordination-based auxiliary learning is impossible.
