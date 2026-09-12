# MC2: literature delta (lane B, 2026-09-12)

This is a targeted check, not a review. Hester et al. is taken from the project's `DQFD-FAMILY-GROUNDING-2026-09-11.md` and was not redone. Cheng, Liu and Nair were fetched from arXiv / PMLR / NeurIPS this session. Tags: [STATED] = in the paper; [INFERRED] = lane B's reading. The DAgger entry is from memory and was not fetched this session.

## Citations

1. Todd Hester, Matej Vecerik, Olivier Pietquin, Marc Lanctot, Tom Schaul, Bilal Piot, Dan Horgan, John Quan, Andrew Sendonaris, Ian Osband, Gabriel Dulac-Arnold, John Agapiou, Joel Z. Leibo, Audrunas Gruslys. "Deep Q-learning from Demonstrations." AAAI Conference on Artificial Intelligence (AAAI), 2018. arXiv:1704.03732.
2. Ching-An Cheng, Andrey Kolobov, Alekh Agarwal. "Policy Improvement via Imitation of Multiple Oracles." Advances in Neural Information Processing Systems 33 (NeurIPS), 2020, pp. 5587–5598. arXiv:2007.00795.
3. Xuefeng Liu, Takuma Yoneda, Chaoqi Wang, Matthew R. Walter, Yuxin Chen. "Active Policy Improvement from Multiple Black-box Oracles." Proc. 40th International Conference on Machine Learning (ICML), PMLR 202:22320–22337, 2023. arXiv:2306.10259. **Cheng is not an author.** The contract's "Liu et al." is right.
4. Ashvin Nair, Bob McGrew, Marcin Andrychowicz, Wojciech Zaremba, Pieter Abbeel. "Overcoming Exploration in Reinforcement Learning with Demonstrations." IEEE International Conference on Robotics and Automation (ICRA), 2018, pp. 6292–6299. doi:10.1109/ICRA.2018.8463162. arXiv:1709.10089.
5. Recommended in addition, from memory, verify the string before use: Stéphane Ross, Geoffrey J. Gordon, J. Andrew Bagnell. "A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning." AISTATS 2011, PMLR 15:627–635. arXiv:1011.0686 (DAgger).

## What MC2 borrows and what it does not

**Hester et al. (DQfD).** MC2 borrows the large-margin loss form, `J_E = max_a[Q(s,a) + l(a_E,a)] − Q(s,a_E)`, at an unchanged project margin m = 0.15 and λ_E = 1. It does not borrow:
- the application domain: DQfD applies `J_E` only to demonstration transitions, with "λ2 = 0" on self-generated data [STATED, via the grounding doc §1.1]. MC2, like the E0/E1 `D3-T0` channel, applies it to the learner's own replay rows, with the specialist queried on the learner's state.
- the demonstration buffer, pre-training, n-step loss, prioritised demo replay and L2.

MC2 is therefore "DQfD's margin as a relabelling loss", not DQfD. The on-state expert query is DAgger's idea (Ross et al. 2011), so both should be cited. The explainer's cap applies unchanged: `J_E = 0` if and only if the target is the argmax, so the term never pulls past the target [STATED in the grounding doc §1.2: "makes the greedy policy … imitate the demonstrator"].

**Cheng et al. (MAMBA).**
- Oracle actions are not observed. The learner rolls in until a random switch time, then a uniformly chosen oracle k rolls out. Each oracle's value function V̂^k is learned online from those roll-outs, and f̂^max(s) = max_k V̂^k(s) (Eq. 5) [STATED §2, Alg. 1].
- f̂^max is used as the value baseline of a GAE-style advantage in a **policy-gradient** update (Eqs. 12, 17–18). λ = 0 recovers AggreVaTe(D) [STATED §4].
- The guarantee is competitive with the state-wise max of oracle values, up to regret, policy-class and approximation terms (Thm 1) [STATED §3.2]. The paper notes that π^max "is not necessarily the same as following the highest-value oracle" [STATED §3.1].

MC2 borrows only the concept: per state, defer to whichever of several oracles is better. It does not borrow learned oracle values, roll-outs from switch times, the policy-gradient update, or the guarantee. MC2 makes no guarantee claim, and this one does not transfer. MAMBA does not pick a supervised target by comparing oracles.

**Liu et al. (MAPS / MAPS-SE).**
- "Black-box" means oracles are given "without access to their value functions" [STATED §3].
- It reuses MAMBA's f^max, loss and theorem [STATED §3, §5.1]. Oracle values are learned from oracle roll-outs: a return average, or an ensemble of value networks in continuous spaces [STATED §3.1, §4.1].
- The new element is a per-state **active selection of which oracle to roll out**, by UCB: `k* = argmax_k V̂^k(s) + sqrt(2H² log(2/δ)/N_k(s))`, or V̂^k + σ_k (Eq. 12). MAPS-SE also decides when to stop rolling in (Eqs. 13–14) [STATED §4].
- The guarantee is a sample-complexity gain in identifying the best oracle (Thms 2–3) [STATED §5].

MC2 borrows nothing mechanical: there is no oracle roll-out, no learned value, no UCB and no policy gradient. What it shares is the concept of per-state oracle selection. MC2's selection chooses a **label**, not a roll-out oracle.

**Nair et al. (Q-filter). This is the closer precedent for MC2's gate and should be cited.**
- Behaviour cloning toward a single demonstration action is applied per sample only where the learner's own critic prefers it: `L_BC = Σ_i ‖π(s_i) − a_i‖² · 1[Q(s_i,a_i) > Q(s_i,π(s_i))]` (Eq. 8) [STATED §IV-C]. The critic is the DDPG critic, trained on both buffers [STATED §III-B, §IV-A].
- MC2 borrows the structure: a supervised term toward one proposed action, gated per sample by a strict value comparison against an incumbent. MC2's B-only is the same shape, with the incumbent being the learner's executed action.
- MC2 does not borrow the evaluator. MC2 uses the simulator's one-step counterfactual with common random numbers and a fixed-price surrogate, a privileged training-only judge, instead of the learner's critic. In FULL the comparand is another specialist's action (the anchor), not the learner's.
- Nair reports "mixed results on the longer horizon tasks" for the filter [STATED §VIII-B].

**Net statement for §4.** DQfD supplies the loss form and DAgger the on-state query. The Q-filter is the precedent for the gate. MAMBA/MAPS are the precedent for "per-state defer to the better of several oracles". The narrow MC2-specific element survives: none of these three compares **two specialists'** actions under an evaluator to pick one supervised target [INFERRED, these three papers only]. That element is a simulator-judged relabelling rule, with no guarantee, and it is not a literature-wide novelty claim.
