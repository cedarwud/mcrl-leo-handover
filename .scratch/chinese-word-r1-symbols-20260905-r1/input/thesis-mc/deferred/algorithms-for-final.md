# DEFERRED — Algorithm pseudocode for ch4 (re-insert at FINAL stage)

> NOT thesis content. NOT in the build (build_ris.sh only processes mc-modqn-base / ch4 / ch5 / ch6 /
> REFERENCES). Moved OUT of ch4 on 2026-06-30: at draft stage two formal Algorithm blocks over-reach the
> advisor house-norm (ris.docx 初稿 + thesis.pdf 定稿 each carry ONE algorithm = the training loop, plus a
> flowchart figure). ch4 now keeps the method as prose + eqs + the flowchart figures FIG-4-6 / FIG-4-7 only.
>
> RE-INSERT plan (final stage, USER decision on how many): paste the wanted table(s) back into ch4 —
> Algorithm 1 after eq 4.8 in §4.4 (lead-in: 「上述開集與指派流程整理如演算法 1。」), Algorithm 2 at the end
> of §4.5 (lead-in: 「完整的訓練流程整理如演算法 2。」). Format already verified: renders via the build's
> ris_postprocess B9 (leading-nbsp depth markers -> real left indent, wrapped lines aligned, three-line table,
> OMML math). Do NOT leave any note about this deferral inside the thesis chapters.

| # | **Algorithm 1: Coordinated Beam Allocation (online inference)** |
|:--:|:-------------------------------------------------|
|  | **Input:** combined value $b_u(a)$ for each user $u$ and candidate beam $a\in\mathcal{A}_u(t)$ (Eq. 4.2); per-satellite cap $k_{\mathrm{cap}}$ |
|  | **Output:** joint action $\{a_u(t)\}$ |
| 1 | $O \leftarrow \varnothing$ |
| 2 | **for** each satellite $s\in\mathcal{S}$ **do** |
| 3 | &nbsp;&nbsp;**repeat** $k_{\mathrm{cap}}$ times |
| 4 | &nbsp;&nbsp;&nbsp;&nbsp;**for** each user $u$ **do** $\;o(u)\leftarrow$ $u$'s highest combined value on opened beams in $O$ (0 if none) |
| 5 | &nbsp;&nbsp;&nbsp;&nbsp;**for** each unopened candidate beam $(s,v)$ **do** |
| 6 | &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;$G(s,v)\leftarrow\sum_{u:(s,v)\in\mathcal{A}_u(t)}\max(b_u(s,v)-o(u),\,0)$ (Eq. 4.6) |
| 7 | &nbsp;&nbsp;&nbsp;&nbsp;$(s,v)^{\star}\leftarrow\arg\max_{(s,v)}G(s,v)$ (Eq. 4.7) |
| 8 | &nbsp;&nbsp;&nbsp;&nbsp;**if** $G((s,v)^{\star})\le 0$ **then break** |
| 9 | &nbsp;&nbsp;&nbsp;&nbsp;$O\leftarrow O\cup\{(s,v)^{\star}\}$ |
| 10 | **for** each user $u$ **do** |
| 11 | &nbsp;&nbsp;**if** some candidate beam in $\mathcal{A}_u(t)$ is opened **then** |
| 12 | &nbsp;&nbsp;&nbsp;&nbsp;$a_u(t)\leftarrow\arg\max_{a\in\mathcal{A}_u(t)\cap O}b_u(a)$ (Eq. 4.8) |
| 13 | &nbsp;&nbsp;**else** |
| 14 | &nbsp;&nbsp;&nbsp;&nbsp;$a_u(t)\leftarrow$ fall back to its own best candidate (excluded beyond capacity) |
| 15 | **return** $\{a_u(t)\}$  ($\le k_{\mathrm{cap}}$ beams opened per satellite, Eq. 4.5) |

| # | **Algorithm 2: Angle-Aware Multi-Catfish MODQN Training** |
|:--:|:-------------------------------------------------|
|  | **Input:** environment; objective Q-networks $\theta_1,\theta_2,\theta_3$ and targets $\theta_1^{-},\theta_2^{-},\theta_3^{-}$; discounts $\boldsymbol{\gamma}=[\gamma_1,\gamma_2,\gamma_3]$ (catfish, Eq. 4.1) or shared $\beta$ (plain); $\epsilon$ schedule; priority ratio $\rho$, threshold factor $\lambda$; beam-selection rule (per-user $\arg\max$ or coordinated beam allocation = Algorithm 1) |
|  | **Output:** trained $\theta_1,\theta_2,\theta_3$ |
| 1 | initialize replay buffer |
| 2 | **for** each episode **do** |
| 3 | &nbsp;&nbsp;$s\leftarrow\text{env.reset}()$ |
| 4 | &nbsp;&nbsp;**for** each time step $t$ **do** |
| 5 | &nbsp;&nbsp;&nbsp;&nbsp;compute congestion context $\chi_u(t)$ (Eq. 4.3) and augmented state $\tilde{s}_u=[s_u,\chi_u]$ (Eq. 4.4) for each user |
| 6 | &nbsp;&nbsp;&nbsp;&nbsp;combined value $b_u(a)\leftarrow\sum_{j}\omega_j Q_j(\tilde{s}_u,a)$ (Eq. 4.2) |
| 7 | &nbsp;&nbsp;&nbsp;&nbsp;pick the joint action by the beam-selection rule; add $\epsilon$-greedy exploration in training |
| 8 | &nbsp;&nbsp;&nbsp;&nbsp;execute action; env returns $(r_1{=}\text{EE},\,r_2,\,r_3)$; calibrate to weighted return $J$ |
| 9 | &nbsp;&nbsp;&nbsp;&nbsp;store the whole-step bundle in replay (catfish: $J$ above running mean $+\lambda\cdot\text{std}$ goes to the priority pool) |
| 10 | &nbsp;&nbsp;&nbsp;&nbsp;sample a training batch (catfish: fraction $\rho$ from the priority pool, rest uniform) |
| 11 | &nbsp;&nbsp;&nbsp;&nbsp;**for** each objective $j\in\{1,2,3\}$ **do** |
| 12 | &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;recompute the next action $a'_u$ by the beam-selection rule at the next state |
| 13 | &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;$y_j\leftarrow r_{j,u}(t)+\gamma_j Q_j(\tilde{s}_u(t{+}1),a'_u;\theta_j^{-})$ (Eq. 4.9, Double-DQN) |
| 14 | &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;one-step temporal-difference update on $\theta_j$ (Eq. 4.10) |
| 15 | &nbsp;&nbsp;&nbsp;&nbsp;periodically sync target networks $\theta_j^{-}\leftarrow\theta_j$ |
| 16 | &nbsp;&nbsp;&nbsp;&nbsp;periodically evaluate; keep the weights with the best weighted reward |
| 17 | **return** $\theta_1,\theta_2,\theta_3$ |
