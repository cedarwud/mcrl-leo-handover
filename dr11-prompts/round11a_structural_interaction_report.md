# Structural interaction in energy-priced satellite user assignment

## Decision

**The stated objective class is neither submodular nor supermodular in general when expressed as a function of coordinated user reassignment moves. There is no valid structural argument that forces the coalition residual to be non-positive.**

This conclusion does not depend exclusively on the hard decoder. Coordinated exchanges can be complementary even for a smooth, concave congestion reward; fixed beam and satellite activation charges produce another independent source of complementarity. The margin-selected ACM rule supplies a particularly sharp, analytically identifiable activation mechanism.

For the bandwidth and lower DVB-S2 modes in the supplied package, a singleton beam can require **two arrivals before any mode becomes selectable** when the fading reserve is

\[
2.05 < -10\log_{10}q \leq 4.58\quad\text{dB},
\]

provided the resulting nominal power remains below its cap. A deterministic three-user example following the stated physical accounting has all six possible unilateral moves strictly harmful, an improving two-user consolidation, and both positive and negative mixed differences in one fixed move set. Its equations, numerical values, and reproducible arithmetic are given below.

**What remains parameter-dependent is not the general possibility of positive interaction. It is whether the frozen approximately 100-user instance contains an admissible, sufficiently valuable, prospectively useful joint move, particularly after its quality-of-service, proposal, execution, and deadline restrictions.** A counterexample to a universal curvature theorem is not an oracle certificate for C3, and it is not evidence that a learned third mechanism has positive marginal value.

## 1. The scoring rule and an important distinction about the rate target

The relevant assignment score is

\[
F(a)=B(a)-\eta E(a)-\Phi(a),\qquad \eta\geq0.
\]

The price is fixed across every comparison. The analysis concerns this score, not the ratio \(B/E\), and not an objective whose price is recalibrated separately for each coalition.

The supplied v1.8 amendment, item 5, explicitly describes the traffic as full-buffer throughput and the 50 Mbit/s target as a **power-control setpoint rather than a demand model**. Its item 8 and the later Stage4h report distinguish target mode, transmitted mode, and realised decoding. The v1.9 amendment, items 1–3, puts the fading quantile only into the predicted wanted-link reception, leaving nominal power and predicted interference unchanged. These supplied declarations control the interpretation here; they are project evidence, not external literature.

This matters because “every served user must deliver 50 Mbit/s” is not equivalent to the implemented scoring rule. Let the target mode have the smallest threshold among modes that meet the instantaneous requirement:

\[
t(n)\in\arg\min_{m:\,Wc_m/n\geq r^*}\gamma_m,
\qquad \Gamma(n)=\gamma_{t(n)}.
\]

For nominal target-tracking power, including the cap,

\[
\frac{hp}{N+I}\leq\Gamma(n).
\]

If \(q<1\), every selected transmitted mode satisfies

\[
\gamma_{m_{\rm tx}}\leq q\frac{hp}{N+I}<\Gamma(n).
\]

By the definition of the minimum-threshold target, such a mode cannot itself meet \(Wc_m/n\geq r^*\). Thus, under these exact assumptions, successful transmissions at the backed-off mode deliver less than the target average rate. Decoding successfully and attaining the rate target are different events.

The package includes a separate PHY floor that is microscopically above the exact lowest-mode threshold because of decimal rounding. More generally, a genuinely larger floor or an explicit power reserve can invalidate the strict inequality argument. The correct condition is therefore the implemented \(q\Gamma(n)\) comparison, rather than a floating-point statement that every arbitrarily tiny margin must change the selected mode. This numerical qualification does not affect a practical reserve of several dB.

If 50 Mbit/s is instead imposed as a literal hard service constraint, the feasible domain must be specified again; the current equations can make that hard guarantee unattainable. That would be a feasibility/model-consistency issue, not a submodularity theorem. The counterexamples below concern the declared full-buffer credited-bit score and do not claim to pass an additional rate-attainment guard.

## 2. The precise submodularity question

Fix an anchor \(a^0\), one proposed destination for each user in a move set \(A\), an exogenous physical realisation or a specified expectation, and all price and penalty conventions. For \(S\subseteq A\), execute exactly those proposed moves and define

\[
g(S)=F(a_S),\qquad v(S)=g(S)-g(\varnothing).
\]

Non-moving users keep their assignments, but their power, interference, airtime-dependent outcomes, and decoding must still be recomputed whenever the model requires it. Holding those outcomes fixed would define a different game.

Submodularity is the diminishing-returns condition

\[
\Delta_i g(S)\geq\Delta_i g(T),\qquad S\subseteq T,\ i\notin T,
\]

or, equivalently on a complete Boolean subset domain,

\[
\Delta_{ij}g(S)
=g(S\cup\{i,j\})-g(S\cup\{i\})-g(S\cup\{j\})+g(S)\leq0
\]

for every distinct pair and every context excluding that pair. Supermodularity reverses the inequalities. These are standard set-function definitions.[^1]

The coalition residual in the question is

\[
\Psi_A=v(A)-\sum_{i\in A}v(\{i\}).
\]

If **this particular induced move function** is submodular, then the proposed stopping argument is valid. Order the moves as \(i_1,\ldots,i_k\). Telescoping and diminishing returns give

\[
\begin{aligned}
v(A)&=\sum_{r=1}^{k}\left[g(\{i_1,\ldots,i_r\})-g(\{i_1,\ldots,i_{r-1}\})\right]\\
&\leq\sum_{r=1}^{k}\left[g(\{i_r\})-g(\varnothing)\right]
=\sum_{i\in A}d_i.
\end{aligned}
\]

Hence \(\Psi_A\leq0\). If all singleton moves are non-positive, the coalition cannot improve the score.

There are three limitations to this otherwise correct proof. First, the required curvature is that of **moves from this anchor**, not of a user-addition objective on another domain. Second, each singleton must use the same destination as in the coalition; replacing it with that user's separately optimised destination changes the residual. Third, constraints may remove intermediate subsets from the domain. A complete-assignment space with exclusivity, hard rate constraints, or joint restrictions is not automatically a Boolean lattice on which this proof applies.

A single positive \(\Psi_A\) disproves submodularity on the associated complete move domain. Conversely, observing non-positive residuals in a bounded set of coalitions does not establish submodularity. Nor does a positive residual guarantee an improving joint move: the stronger condition is

\[
\Psi_A> -\sum_{i\in A}d_i.
\]

Unilateral optimality must also concern the same objective and information view. A nominal or predicted unilateral optimum is not automatically a realised-score unilateral optimum.

## 3. Why ordinary congestion intuition does not settle reassignment

Concave functions of non-negative resource counts are a standard source of submodularity for **adding elements**. For instance, a sum of discrete-concave beam occupancy rewards is submodular in a ground set of user–beam edges.[^1] A classic cellular association formulation by Ye and coauthors uses logarithmic utility and equal resource fractions, leading to load terms of the form \(-n_b\log n_b\). That is a particular utility model, not the present credited-bits objective.[^2]

A reassignment, however, simultaneously removes one edge and adds another. That transformation does not preserve the same diminishing-returns orientation.

### A smooth counterexample with no decoding threshold

Consider two users initially on separate beams, with the score

\[
H(a)=\sum_u w_{u,a_u}-n_X(a)^2-n_Y(a)^2.
\]

Each user's original edge has weight zero; its other edge has weight \(1/2\). Both users propose swapping beams. The four values are

| Move subset | Occupancies | Edge reward | Score |
|---|---:|---:|---:|
| None | \((1,1)\) | 0 | \(-2\) |
| First user only | \((0,2)\) | \(1/2\) | \(-7/2\) |
| Second user only | \((2,0)\) | \(1/2\) | \(-7/2\) |
| Both users | \((1,1)\) | 1 | \(-1\) |

Both unilateral gains equal \(-3/2\), the joint gain is \(+1\), and

\[
\Psi_{\{1,2\}}=-1-(-7/2)-(-7/2)+(-2)=4>0.
\]

Nevertheless, viewed as a set function of added assignment edges, the same expression is modular edge reward plus a sum of concave count functions. The edge-addition function is submodular. The induced swap function is not.

More generally, for the congestion term \(-\|n\|_2^2\), let a move have occupancy direction \(z_i=e_{\mathrm{destination}(i)}-e_{\mathrm{source}(i)}\). Direct expansion gives

\[
\Delta_{ij}H=-2z_i^\top z_j.
\]

Opposite exchanges produce a positive value; arrivals from distinct sources into the same destination produce a negative value. This is an elementary derivation, not an asserted theorem about the satellite simulator.

The correct broader terminology is **exchange local search** or **discrete concavity of assignment objectives**. Murota's discrete convex analysis supplies local-to-global results under specific exchange axioms, such as appropriate forms of \(M\)- or \(M^\natural\)-concavity. Those axioms and the required exchange neighbourhood must be established; a one-user local optimum alone supplies neither.[^9]

## 4. What the hard threshold can and cannot imply

A hard threshold does not automatically make every function non-submodular. Its placement and the ways moves combine matter.

For a simple cardinality threshold on \(m\) potential helpful moves,

\[
h(S)=C\,\mathbf1\{|S|\geq k\},\qquad C>0,
\]

one sufficient move (\(k=1\)) creates an OR/coverage-type submodular function. Requiring all moves (\(k=m\)) creates an AND/unanimity-type supermodular function. An interior threshold \(1<k<m\) is neither: the marginal jumps from zero to \(C\) near activation and returns to zero after saturation. For example, a two-of-three threshold has a positive pair difference at the empty context and a negative pair difference with the third move already present.

This is a standard complementarity structure. Chen, Teng, and Zhang explicitly use the value of obtaining at least two items as an example motivating measures beyond submodularity. In a different application, Mossel and Roch show that threshold-based influence is submodular only under appropriate local activation assumptions; for general threshold distributions, the relevant composed activation functions must satisfy the required shape condition. These sources document the mathematical issue, not a theorem about satellite reception.[^6][^5]

### An interference-relief condition

For one victim whose transmitted mode, desired received signal, and credited airtime remain fixed, write

\[
B_v(S)=C\,\mathbf1\{I(S)\leq L\},\qquad
L=\frac{S_{\rm rx}}{\gamma_{\rm tx}}-N.
\]

Suppose two moves reduce interference by \(\delta_i,\delta_j>0\). Let the initial shortfall be \(r=I_0-L>0\). Then

\[
\max(\delta_i,\delta_j)<r\leq\delta_i+\delta_j
\]

produces victim-bit values \((0,0,0,C)\) for neither, either singleton, and both moves. The victim's contribution to the mixed difference is \(+C\). If either singleton already rescues it, the corresponding values \((0,C,C,C)\) instead produce \(-C\).

For the entire network, the necessary accounting is still

\[
\Psi_F=\Psi_B-\eta\Psi_E-\Psi_\Phi.
\]

A rescued victim is a positive component, not a proof that all displaced users, energy terms, and signalling effects leave a positive total.

### The crucial power-control qualification

The interference example must not be applied while silently freezing power that the actual model re-solves. In the fully uncapped nominal target-tracking regime,

\[
p=\Gamma(n)\frac{N+I}{h}
\quad\Longrightarrow\quad
\mathrm{SINR}_{\rm nominal}=\Gamma(n),\qquad
\mathrm{SINR}_{\rm pred}=q\Gamma(n).
\]

With occupancy and \(q\) unchanged, nominal interference relief lowers required power rather than raising these SINRs. It cannot, by itself, change the predicted selected mode in that regime. Strong candidates for an interference-driven mode or decode transition instead involve a cap-binding desired transmitter, a cap-active-set change, or a distinction between realised interference and the nominal denominator used by the controller.

Every proposed witness must therefore be re-evaluated with the same coupled power solver and transmission-mode rule as the original score. Interference-dependent association literature does not make this dependency disappear: Alizadeh and Vu explicitly model association-dependent interference and develop a swapping method for their resulting nonlinear association problem.[^3]

## 5. The occupancy inversion has an exact policy-level explanation

For an uncapped link, the transmitted mode is selected from

\[
m_{\rm tx}(n)=\arg\max_{m:\,\gamma_m\leq q\Gamma(n)}c_m,
\]

with NO_MODE if the set is empty. Consequently,

\[
\mathrm{NO\_MODE}\quad\Longleftrightarrow\quad q\Gamma(n)<\gamma_{\min}.
\]

A power cap can only reduce predicted SINR relative to \(q\Gamma(n)\), so the inequality remains a sufficient NO_MODE certificate even when capped. Its reverse implies activation only when the actual nominal SINR is large enough, for example when the desired link is uncapped.

If the singleton target is exactly the lowest mode, \(\Gamma(1)=\gamma_{\min}\), then any \(q<1\) makes the singleton unselectable. This is stronger than an unlucky realised fade: no mode is selected in the first place. It should be reported separately from a selected codeword failing its realised decode check.

An increase in occupancy raises the nominal target in discrete jumps, which can make \(q\Gamma(n)\) reach the lowest selectable mode. This is **load-induced mode activation under the specified control policy**, not a physical law that loading a beam improves its channel. The name here is descriptive; the literature reviewed did not reveal a unique established name for this exact combination of target tracking, post-power margin selection, and NO_MODE behaviour.

For a beam with anchor occupancy \(n\), a useful first diagnostic is

\[
k_* = \min\{k\geq1:\ q\Gamma(n+k)\geq\gamma_{\min}\}.
\]

If \(k_*>1\), fewer arrivals cannot trigger this particular activation. If the set is empty over all permitted occupancies, no amount of permitted loading can rescue that link through this mechanism. With link-specific quantiles, the test is applied separately to each resident's \(q\), followed by the cap and realised-decode checks.

After activation, successful decoding additionally requires

\[
Z\Gamma(n+k)\geq\gamma_{m_{\rm tx}}
\]

when realised interference equals the nominal value and \(Z\) is the wanted-link fade relative to nominal. With random interfering links, their actual denominator must replace this simplification. The selection quantile alone is not a universal network outage guarantee.

### A concrete window from the package's bandwidth and DVB-S2 entries

The supplied mechanism calculation uses \(W=500/3\) MHz, roll-off \(\alpha=0.2\), and a common 1.7 dB implementation margin. The necessary target modes for occupancies one through three are:

| Occupancy | Required SE, bit/s/Hz | Target MODCOD | Table efficiency, bit/symbol | Ideal threshold, dB |
|---:|---:|---|---:|---:|
| 1 | 0.3 | QPSK 1/4 | 0.490243 | -2.35 |
| 2 | 0.6 | QPSK 2/5 | 0.789412 | -0.30 |
| 3 | 0.9 | QPSK 3/5 | 1.188304 | 2.23 |

Efficiencies are divided by \(1+\alpha\) to obtain the occupied-bandwidth SE used by the package. The corresponding lower DVB-S2 entries were checked against ETSI EN 302 307-1, Table 13. That table gives idealised performance at a specified quasi-error-free operating point; the deterministic all-or-zero decoder is the project's model abstraction, not a universal step law imposed by the standard.[^4]

The condition for occupancies one and two to remain NO_MODE while occupancy three activates is

\[
\frac{\gamma_{\min}}{\Gamma(3)}\leq q<\frac{\gamma_{\min}}{\Gamma(2)}.
\]

The common implementation and roll-off shifts cancel in these threshold ratios:

\[
10^{-4.58/10}\leq q<10^{-2.05/10},
\]

or numerically

\[
\boxed{0.3483373150\leq q<0.6237348355.}
\]

Equivalently,

\[
\boxed{2.05<M\leq4.58\ \mathrm{dB},\qquad M=-10\log_{10}q.}
\]

At the illustrative choice \(M=3\) dB, occupancies one and two select no mode. At occupancy three, the transmitted mode is QPSK 1/3, with occupied-bandwidth SE

\[
c_{\rm tx}=0.656448/1.2=0.54704.
\]

If all three decode, the total beam rate is

\[
Wc_{\rm tx}=91.173333\ \mathrm{Mbit/s},
\]

or 30.391111 Mbit/s per user. This is an explicit example of increased credited bits but not attainment of the 50 Mbit/s setpoint.

The 3 dB reserve is a synthetic parameter, not an assertion about the frozen elevation-specific quantiles. The mechanism script contains only a lower QPSK subset; it must not be used to infer the full simulator's maximum supported occupancy. The calculations above need only the displayed low-occupancy modes, which are also present in the full standard table.

## 6. A complete counterexample including power, energy, and unilateral optimality

A three-user, three-beam fixture establishes that the **entire stated objective**, not just a victim-bit component, can have both signs of interaction. All three beams are orthogonal channels on one satellite. Every user can use each beam. Channels are homogeneous, with the nominal noise-to-gain ratio selected so that singleton RF power is 0.1 W. The realised wanted fade is one, and the illustrative selection reserve is 3 dB.

Use the package's interval and physical-accounting constants:

\[
\begin{aligned}
T&=30.08\ \mathrm{s},& p_{\rm cap}&=1.65\ \mathrm{W},\\
p_{\rm sat}&=5.2178\ \mathrm{W},& \eta_{\rm PA}&=0.35,\\
P_{\rm chain}&=0.2\ \mathrm{W},& P_{\rm common}&=0.338\ \mathrm{W}.
\end{aligned}
\]

The price is \(\eta=19{,}720{,}681.00172232\) bit/J, the reported Stage4h reference price. The fixture deliberately chooses a **synthetic modular switching penalty** of \(1.2\times10^9\) equivalent bits per user moved away from its original beam. It does not purport to reproduce the project's exact handover penalty configuration or geometry.

For homogeneous users on a beam,

\[
p(n)=0.1\frac{\Gamma(n)}{\Gamma(1)},
\]

so powers at occupancies one, two, and three are approximately 0.1000, 0.1603, and 0.2871 W. All are safely uncapped. Equal TDM implies beam PA energy

\[
E_{{\rm PA},b}=T\frac{\sqrt{p(n_b)p_{\rm sat}}}{\eta_{\rm PA}},
\]

not \(n_b\) times this quantity: each of the \(n_b\) identical users is active for only \(T/n_b\). Add \(TP_{\rm chain}\) per active beam and \(TP_{\rm common}\) once for the active satellite. Failed and NO_MODE users still consume this energy, as required by the stated model.

Start with one user per beam. Consider the two users on beams Y and Z moving to X.

| State | Occupancies, up to beam order | Credited bits, Gbit | Energy, J | Switching penalty, Gbit | Score, Gbit-equivalent |
|---|---|---:|---:|---:|---:|
| Anchor | \((1,1,1)\) | 0 | 214.455809 | 0 | -4.229215 |
| Either arrival alone | \((2,1,0)\) | 0 | 162.884899 | 1.2 | -4.412201 |
| Both arrivals | \((3,0,0)\) | 2.742494 | 121.367965 | 2.4 | -2.050965 |

Every one of the six possible unilateral reassignments has gain

\[
d_i=-0.182986533\ \mathrm{Gbit\text{-}equivalent}<0.
\]

The anchor is therefore a strict unilateral optimum over all assignments in this fixture, not merely over a pruned candidate list. The packing pair has

\[
\begin{aligned}
F(a_{\{i,j\}})-F(a^0)&=+2.178249545\ \mathrm{Gbit\text{-}equivalent},\\
\Psi_{\{i,j\}}&=+2.544222612\ \mathrm{Gbit\text{-}equivalent}.
\end{aligned}
\]

To establish **neither**, include three fixed proposed moves in one cube: the resident on X moves to Y, the resident on Y moves to X, and the resident on Z moves to X. The latter two give the positive packing difference above. The first two form a swap; occupancies return to \((1,1,1)\), with no credited bits. Their mixed difference is

\[
\Delta_{\rm swap}g(\varnothing)
=-2\eta(214.455809129487-162.884899041458)
=-2.034026934\ \mathrm{Gbit\text{-}equivalent}<0.
\]

The same objective and same three-move cube thus have one positive and one negative second mixed difference. They are neither submodular nor supermodular.

The script `round11a_counterexample.py` checks all 27 assignments, all six unilateral alternatives, the eight values of that fixed move cube, and its Möbius reconstruction. The result file contains the precise component values. This is a tiny deterministic arithmetic witness, not a satellite simulation or a formal scenario result. Its strict inequalities make the signs robust to sufficiently small perturbations that do not change the relevant mode selections; the universal impossibility claim is therefore not rescued merely by insisting on weak nonzero interference.

The role of the synthetic switching cost is transparent. It makes energy-saving singleton moves unattractive while leaving their interaction unchanged. This is legitimate for a family-level counterexample, but it is exactly why the example must not be relabelled as a witness under every frozen penalty or quality-of-service guard.

## 7. Complementarity from energy and signalling without a decoder threshold

### Fixed beam and satellite charges

Suppose a beam initially contains \(k\geq2\) users. Let all \(k\) leave for already active destination beams. The source's fixed circuit term is saved only after the complete evacuation. Its contribution to the gain is

\[
v_{\rm circuit}(S)=\eta T P_{\rm chain}\,\mathbf1\{A\subseteq S\},
\]

where \(A\) is the set of all users originally occupying that source beam. This is a positive unanimity-game contribution: its sole nonzero Möbius coefficient is at \(A\). The same mechanism applies to the final users leaving a satellite with a switchable common processing increment. The unanimity representation is standard in the algebra of cooperative games.[^7]

There is a dual shared-opening effect: two users individually entering an empty beam would each bear one full opening cost in their singleton counterfactual, whereas the joint assignment opens the beam only once. The negative fixed activation charge therefore contributes positively to the pair residual. Throughput losses and other power costs can still dominate the total.

For a source with more than two users, testing all empty-context pairs is not enough to detect its pure full-evacuation saving. If three users must leave, every singleton and pair can have zero activation saving and only the triple receives it.

### PA curvature does not transfer directly from power to assignment

The fact that \(\sqrt p\) is concave is not a theorem about \(E(a)\): \(p\) itself depends on target-mode jumps, the power cap, the re-solved interference field, channel gains, and the occupants. For heterogeneous equal-TDM users, the PA energy is

\[
E_{{\rm PA},b}=\frac{T}{n_b}\sum_{u:a_u=b}\frac{\sqrt{p_u(a)p_{\rm sat}}}{\eta_{\rm PA}}.
\]

Even removing discrete ACM does not create a universal occupancy-curvature result. For a homogeneous, uncapped Shannon-target example,

\[
p(n)=K(2^{cn}-1),\qquad
E_{{\rm PA},b}(n)=A\sqrt{2^{cn}-1}.
\]

Writing \(\beta=c\ln2\), direct differentiation of the nonconstant factor gives

\[
\frac{d^2}{dn^2}\sqrt{e^{\beta n}-1}
=\frac{\beta^2e^{\beta n}(e^{\beta n}-2)}{4(e^{\beta n}-1)^{3/2}}.
\]

Its continuous curvature changes sign at \(e^{\beta n}=2\). The relevant integer second differences must still be checked. There is no general inference from “square-root PA” to one sign of assignment interaction.

### Penalties and the energy price

A fixed per-user handover penalty is modular on a fixed move cube and cancels from \(\Psi_A\). It nevertheless changes singleton losses and whether a joint move is improving. A bundled signalling fee, shared procedure cost, or state-dependent penalty need not cancel.

At fixed physical assignments and a fixed penalty rule,

\[
\Psi_F(\eta)=\Psi_B-\eta\Psi_E-\Psi_\Phi.
\]

Thus the sign is an affine function of the energy price. If \(\Psi_E>0\), the price must satisfy

\[
\eta<\frac{\Psi_B-\Psi_\Phi}{\Psi_E}
\]

for positive interaction; if \(\Psi_E<0\), dividing reverses the inequality. A positive-bit interaction alone is insufficient. Recalibrating the price or changing the anchor separately for different subsets invalidates this common-function comparison.

## 8. Special cases and what is actually known

| Restricted setting | Valid conclusion |
|---|---|
| Per-user assignment rewards and costs are separable; no occupancy, interference, activation, or joint penalty effects | The induced move score is modular; all residuals vanish. |
| Users are only added to fixed resources, with a sum of discrete-concave count rewards and modular additional terms | Submodular in those additions. This is the standard concave-count case, not arbitrary reassignment. |
| The same addition-only formulation with discrete-convex count rewards | Supermodular in those additions. |
| Reassignment with otherwise smooth concave congestion rewards | No universal sign; the explicit swap counterexample applies. |
| Fixed MODCOD, homogeneous users, always successful decoding, equal TDM | Total beam bits are constant whenever the beam is active. Remaining activation and energy terms determine curvature. |
| Every user actually delivers exactly the same required bits, and the set of users is fixed | Total bits are constant. Curvature is entirely that of \(-\eta E-\Phi\); it is not automatically submodular. |
| Uncapped nominal power tracking, fixed occupancy and quantile | Predicted mode is fixed at the mode supported by \(q\Gamma(n)\). Nominal interference relief affects power, not this selected mode. |
| Hard threshold needing some but not all helpful moves | Generally neither; threshold activation and saturation give opposite mixed signs. |
| Fully shared activation saving | Positive unanimity-type complementarity, possibly at coalition orders greater than two. |
| Expectation over fading | No automatic restoration of submodularity. Distribution and controller response must be analysed. |

The first three entries follow the indicated algebra and standard concave-count construction.[^1] The remaining conclusions are derivations under the restrictions stated in their rows, not broad literature claims about all wireless systems.

### Why averaging fading does not settle the question

An expectation of pointwise submodular functions is submodular, by linearity of the defining inequality. If the pointwise functions are not submodular, averaging may preserve, erase, or reverse a particular mixed difference; no generic restoration theorem follows.

For example, consider a fixed selected mode and fixed desired nominal signal \(S_0\), with an exponential unit-mean wanted power fade \(Z\). If helpful moves remove a total interference \(\sum_{i\in S}\delta_i\), then, in a physically valid region with a positive denominator,

\[
\mathbb E[B(S)]
=C\exp\left[-\frac{\gamma(N+I_0-\sum_{i\in S}\delta_i)}{S_0}\right].
\]

The pair difference is proportional to

\[
\left(e^{\gamma\delta_i/S_0}-1\right)
\left(e^{\gamma\delta_j/S_0}-1\right)>0.
\]

This illustrative calculation is not a claim that the project's Rician–lognormal product is exponential. It shows why replacing a hard realisation by an expectation is not, by itself, a submodularity proof. The actual distribution and nominal/realised interference convention must enter that proof. The analogous distinction between threshold distributions and composed activation-function shape is explicit in Mossel and Roch.[^5]

## 9. The standard decomposition and its pitfalls

The appropriate established terminology is the **Möbius transform of a set function**, also known as its **Harsanyi-dividend decomposition** in cooperative games. Unanimity games provide its basis.[^7]

For the anchored game \(v(\varnothing)=0\), define

\[
\mu(T)=\sum_{U\subseteq T}(-1)^{|T|-|U|}v(U).
\]

Möbius inversion gives

\[
v(A)=\sum_{\varnothing\ne T\subseteq A}\mu(T),
\qquad d_i=\mu(\{i\}).
\]

Therefore the residual being measured has the exact interpretation

\[
\boxed{\Psi_A=\sum_{T\subseteq A:\,|T|\geq2}\mu(T).}
\]

For two users it is a second-order mixed difference. For three or more users it is **the total contribution of all interaction orders above one**, not a pure second-order or pure \(|A|\)-order effect. In particular,

\[
\mu(\{i,j,k\})
=\Psi_{\{i,j,k\}}-\Psi_{\{i,j\}}-\Psi_{\{i,k\}}-\Psi_{\{j,k\}}.
\]

Large positive and negative components can cancel in \(\Psi_A\). A zero residual does not prove that there are no interactions. Likewise, pair coefficients at the anchor do not settle global curvature:

\[
\Delta_{ij}g(S)=\sum_{T\subseteq S}\mu(T\cup\{i,j\}).
\]

Every context matters for a submodularity certificate.

For attribution rather than detection, the Shapley value distributes each dividend equally among its participating users:

\[
\phi_i=\sum_{T\ni i}\frac{\mu(T)}{|T|},
\qquad
\sum_{i\in A}(\phi_i-d_i)=\Psi_A.
\]

Do not replace the singleton sum in the residual with the sum of Shapley values: efficiency makes that new residual identically zero. At explanation order two, Shapley–Taylor retains the anchor singleton effects and distributes higher-order contributions among pairs; the pair totals can then account for the residual. Such pair attributions deliberately include higher-order effects and must not be labelled pure pairwise physical interactions. The distinction between the efficient Shapley–Taylor decomposition and other interaction indices is explicit in the original paper.[^8]

The baseline is part of the estimand. Reversing a move or changing the anchor can change the sign of a mixed difference. In fact, reversing just one of two binary coordinates negates their mixed difference on the same four assignments. An assertion of submodularity under every possible anchor orientation is therefore exceptionally strong: on a fixed binary cube it would force every pair/context mixed difference to vanish.

## 10. Where to look, and what a bounded search can establish

The relevant literature describes positive dependencies, supermodular degree, and supermodular width rather than assuming that every useful interaction is visible as an attractive singleton. These notions explicitly allow complementarity that appears only in a nonempty context or requires a bundle of moves.[^6] Their approximation results generally impose additional assumptions such as non-negative monotonicity. They cannot be transferred as performance guarantees to a signed, non-monotone satellite score without a separate reduction and proof.

A suitable diagnostic search can nevertheless use this structural information.

### 10.1 Occupancy and mode-boundary bundles

For each potential destination, compute the relevant resident-specific values of \(q\Gamma(n)\), the smallest additional occupancy that reaches a mode boundary, and the associated cap headroom. The first activation window derived above identifies a two-arrival bundle that is invisible to single-arrival bit gains. Higher modes or smaller quantiles may require larger bundles. Evaluate losses and new loads on the donor beams as part of the same candidate.

### 10.2 Complete activation events

Include complete source-beam evacuations, final-satellite evacuations where the hardware assumption permits them, and multiple arrivals sharing an otherwise empty destination's activation charge. Coalition size should follow the event's required number of users, not an arbitrary global pair or triple limit. A beam with four indispensable remaining users can have an activation dividend that a three-user neighbourhood cannot expose.

### 10.3 Exchanges and cycles

Include occupancy-preserving swaps and short reassignment cycles. These can avoid the temporary overload or underload that makes each move alone unattractive. This is structurally different from asking only which destination has room for another user. A swapping approach is also present in association-dependent-interference research, though that algorithm's empirical behaviour and guarantees do not transfer directly to the present score.[^3]

### 10.4 Interference and power-cap boundaries

Identify victim links close to a transmitted-mode decode boundary and the interferers capable of changing their denominator. Construct the smallest compatible move bundle that can cover the threshold deficit. Apply this screen with the fully re-solved power/controller response; fixed-power threshold relief is not a faithful proxy for an uncapped exact-target link.

### 10.5 Do not treat singleton ranking as a theorem

Neither the most negative nor the least negative singleton moves are universally the most complementary. If a modular term \(-\sum_{i\in S}c_i\) is added to \(g(S)\), singleton gains change by \(-c_i\), but every mixed difference and every \(\Psi_A\) remains unchanged. Therefore a singleton-based top-k restriction, by itself, has no structural completeness guarantee for interactions.

The supplied neighbourhood note identifies potentially restrictive user and destination pruning. Its causal criticism of a particular ranking can be investigated empirically, but the theoretical correction is not to declare the opposite ranking universally correct. Candidate inclusion should also use shared-resource and threshold dependencies.

### 10.6 Decompose the resulting witness

For each evaluated coalition, report

\[
\Psi_F=\Psi_B-\eta\Psi_{E_{\rm PA}}-\eta\Psi_{E_{\rm chain}}
-\eta\Psi_{E_{\rm common}}-\Psi_\Phi.
\]

Associate changed bit contributions with target-mode changes, transmitted-mode changes, realised decode flips, and airtime changes. Associate energy contributions with PA changes, chain activation, and satellite activation. This identifies whether a positive result is an intended coordination benefit or an artefact of a policy-induced NO_MODE region.

For small diagnostic coalitions, evaluate all subsets and compute their Möbius coefficients. Use the same underlying exogenous world across subset counterfactuals, rather than reusing random draws in an order-dependent manner that assigns different physical fades to different links. Keep the objective price, time horizon, previous-assignment penalty baseline, and solver tie rules fixed.

If each score evaluation has certified absolute numerical error at most \(\epsilon\), the residual for a coalition of size \(k\geq2\) has worst-case error at most \(2k\epsilon\), because its coefficients have absolute sum \(1+k+(k-1)=2k\). A mixed difference exceeding that bound is a numerical sign certificate for the evaluated function; a realised statistical claim needs the appropriate paired uncertainty and prospective validation as well.

A bounded null is a null for that specified neighbourhood and information view. To assert absence of every improving joint move in a finite instance requires an applicable structural theorem or an exact global certificate. The general theorem proposed in the question is unavailable because the counterexamples above refute it.

## 11. Terminology and literature map

| Purpose | Useful established search terms | What they do not establish automatically |
|---|---|---|
| The basic assignment problem | Load-coupled user association; association-dependent interference; joint association and power control | Submodularity or a guarantee for a particular local search |
| Coordinated rather than unilateral changes | Exchange neighbourhood; k-exchange local search; swaps and reassignment cycles; discrete concavity | That a unilateral optimum is globally optimal |
| Positive dependence among moves | Set-function complementarity; supermodular degree; supermodular width | Monotonicity or suitability of a particular approximation theorem |
| Step-dependent success | Threshold activation; threshold complementarity; outage-constrained or goodput-based allocation | That every threshold model has the same curvature |
| Shared hardware savings | Fixed-charge activation; facility opening; complete evacuation; unanimity games | That the bit or PA terms cannot outweigh those savings |
| Attribution by coalition order | Möbius transform; Harsanyi dividends; pseudo-Boolean interaction; Shapley–Taylor indices | Baseline independence or a causal claim about an untested deployment |

There is no single standard theorem identified in the reviewed literature that classifies the exact combination of equal TDM, occupancy-selected target MODCOD, nominal capped power, post-power quantile mode selection, hard realised decoding, and partial-payload activation energy. The general classification here is established by explicit constructions, while the literature supplies the correct definitions, nearby association models, and interaction decompositions.

## 12. Final implication for the project

**Do not report “submodular, therefore C3 cannot have positive interaction.” That conclusion is false for the stated model class.**

The legitimate immediate structural target is an activation or exchange witness whose required bundle is included explicitly. The lowest-mode calculation supplies one exact regime: an uncapped singleton with reserve between 2.05 and 4.58 dB can require two arrivals to become selectable. A complete activation saving or occupancy-preserving exchange supplies a separate target even when that margin interval does not occur.

A positive witness must then be distinguished from an improving witness, and both must be distinguished from an admissible, decision-relevant, prospectively useful C3 mechanism. In particular, an improvement produced by escaping the current NO_MODE convention is not automatically evidence for a broadly valid physical benefit of loading or consolidating beams. The deployment and model-validity questions remain separate.

**The universal impossibility question is settled negatively: positive interaction is mathematically possible. Its existence and usefulness under the frozen scenario's actual quantiles, geometry, guards, and penalties remain to be checked.**

## Sources

External sources are primary research publications, original author manuscripts, or an official technical standard. Project records are listed separately and are not treated as literature.

[^1]: Francis Bach. *Learning with Submodular Functions: A Convex Optimization Perspective*. Foundations and Trends in Machine Learning, 6(2–3), 145–373, 2013. Chapter 2 and Proposition 6.1. [Author manuscript](https://arxiv.org/html/1111.6453).

[^2]: Qiaoyang Ye, Beiyu Rong, Yudong Chen, Mazin Al-Shalash, Constantine Caramanis, and Jeffrey G. Andrews. *User Association for Load Balancing in Heterogeneous Cellular Networks*. IEEE Transactions on Wireless Communications, 12(6), 2706–2716, 2013. Equal-resource allocation and log-utility association formulation. [Author manuscript](https://arxiv.org/html/1205.2833).

[^3]: Alireza Alizadeh and Mai Vu. *Load Balancing User Association in Millimeter Wave MIMO Networks*. Original author manuscript, arXiv:1806.00985v2, January 2019. Association-dependent interference and Worst Connection Swapping. [Manuscript](https://arxiv.org/html/1806.00985v2).

[^4]: ETSI. *EN 302 307-1 V1.4.1 (2014-11): Digital Video Broadcasting (DVB); Second generation framing structure, channel coding and modulation systems …; Part 1: DVB-S2*. Table 13, printed page 36. [Official standard](https://www.etsi.org/deliver/etsi_en/302300_302399/30230701/01.04.01_60/en_30230701v010401p.pdf).

[^5]: Elchanan Mossel and Sébastien Roch. *Submodularity of Influence in Social Networks: From Local to Global*. SIAM Journal on Computing, 2010. Theorem 1 and concluding remarks on necessity and general threshold distributions. [Author manuscript](https://arxiv.org/html/math/0612046v2). [Publication DOI](https://doi.org/10.1137/080714452).

[^6]: Wei Chen, Shang-Hua Teng, and Hanrui Zhang. *Capturing Complementarity in Set Functions by Going Beyond Submodularity/Subadditivity*. ITCS 2019, LIPIcs 124, Article 24. Definitions and examples concerning positive dependence and supermodular width. [Official proceedings](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITCS.2019.24). [Author manuscript](https://arxiv.org/html/1805.04436v3).

[^7]: Ulrich Faigle and Michel Grabisch. *Polynomial representation of TU-games*. Original author manuscript, arXiv:2401.12741v1, 2024. Section 2.1, especially the unanimity basis and Möbius transform. Used for the standard basis representation, not as a claim that this paper originated Harsanyi dividends. [Manuscript](https://arxiv.org/html/2401.12741v1).

[^8]: Mukund Sundararajan, Kedar Dhamdhere, and Ashish Agarwal. *The Shapley Taylor Interaction Index*. ICML 2020, PMLR 119, 9259–9268. Discrete derivatives, efficiency, and order-limited interaction attribution. [Official proceedings](https://proceedings.mlr.press/v119/sundararajan20a.html). [Full paper](https://proceedings.mlr.press/v119/sundararajan20a/sundararajan20a.pdf).

[^9]: Kazuo Murota. *Discrete Convex Analysis: A Tool for Economics and Game Theory*. Journal of Mechanism and Institution Design, 1(1), 151–273, 2016; revised author version, 2022. Exchange axioms and local optimality under discrete concavity. [Journal publication](https://www.mechanism-design.org/arch/v001-1/v001-1-5.html). [Revised manuscript](https://arxiv.org/html/2212.03598).

### Supplied project evidence

All paths below are relative to `r11pkg/` inside `multi-catfish-r11-package-20260909.zip`.

**P1.** `sealed/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.8-AMENDMENT-2026-09-09.md`, items 1–3, 5, and 8: PA convention, hardware and energy boundary, full-buffer/setpoint interpretation, and the distinction between transmitted mode and realised decoding.

**P2.** `sealed/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.9-AMENDMENT-2026-09-09.md`, items 1–3: nominal power unchanged by the quantile, wanted-link-only reserve, and the fading-product/elevation-specific quantile definition.

**P3.** `evidence/figure1_compute.py`, constants, `ACM_TABLE`, `rate_target_mode`, `gamma_required`, and PHY-floor comments: bandwidth, interval, roll-off and implementation conventions, lower-mode data, and floor rounding. This is a mechanism calculation, not a complete substitute for the full simulator.

**P4.** `evidence/V025-ENGINE-STAGE4H-REPORT-2026-09-09.md`, causal-ACM correction and line 80 calibration entry: target/transmitted/realised separation and the supplied reference energy price. The `q` appearing in its runtime rehearsal paragraph is not used here as a fading quantile.

**P5.** `evidence/V025-CONTROLLER-FINDING-FIGURE1-AND-BACKOFF-2026-09-09.md`, `evidence/V025-CONTROLLER-DECISIONS-PROBE-NEIGHBOURHOOD-2026-09-09.md`, and the supplied reserve-sensitivity files: context for the low-load finding and bounded-neighbourhood concern. These records do not establish a universal sign theorem.

The companion Python and JSON files contain a newly constructed synthetic witness. They are independent analytical deliverables and are not additions to, or results from, the frozen project simulator.
