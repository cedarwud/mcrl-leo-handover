# 6. Conclusion

## 6.1 Summary

This study uses the Multi-Objective Deep Q-Learning Network (MODQN) as the baseline for handover in multi-beam low Earth orbit satellite networks and builds the Multi-Catfish Reinforcement Learning (MCRL) framework on that architecture. Its three objectives correspond to angle-aware system energy efficiency, handover cost, and load balancing. MCRL applies experience shaping and reward shaping during training. After training, only the main agent is retained, and each user continues to select the highest-valued feasible action independently.

## 6.2 Contributions

The main work can be summarized as follows.

For angle-aware system energy efficiency, the first reward is the sum of the selected-link EE contributions, $r_{1,u}(t)=\sum_{s,v}x_{u,s,v}(t)\eta_{u,s,v}(t,\boldsymbol{\theta})$. The off-axis angle first affects $G^{T}$ and then enters the wanted-link numerator directly as $H_{u,s,v}(t)G^{T}(\theta_{u,s,v})$ in Eq. (3.10) and the SINR in Eq. (3.13); the angle-aware RF power is determined by Eqs. (3.11)–(3.12), the same unique link SINR determines throughput, and Eqs. (3.15)–(3.17) form shared system power and EE. The main chain no longer uses target-SINR inversion, a second SINR, or concept-level caps/`min`/`max`. If the existing Chapter 5 numbers came from the legacy runtime, they require runtime parity with the new contract and a rerun before they can be treated as evidence for the revised formulas.

For multi-objective catfish training, the main side and catfish side each contain three Q-networks corresponding to energy efficiency, handover, and load balancing; the three catfish-side networks share one environment trajectory and replay buffer. Energy-efficiency stratification, asymmetric discounting, and periodic mixed-batch intervention change the experiences and the within-episode return weighting used by the catfish side. The paired competitive reward changes only its first objective. After training, only the main side is retained.

## 6.3 Limitations and Future Work

System power includes the power amplifier, active-beam RF chains, satellite-shared baseband power, and beam-training and handover event energies. The current setting uses $E_{\mathrm{tr}}=E_{\mathrm{ho}}=0$, while other satellite hardware, signal-processing, and control power are outside the model. Future work can extend these power sources and reassess their effects on energy efficiency and method comparisons.

The current model is defined for one simulated environment and includes idealized assumptions in both the energy-efficiency definition and the environment settings. The performance difference between MCRL and the baseline remains to be determined by complete experiments; later studies can examine different user counts, constellation conditions, and environments closer to practical systems.
