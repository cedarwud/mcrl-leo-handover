# 6. Conclusion

## 6.1 Summary

This study uses the Multi-Objective Deep Q-Learning Network (MODQN) as the baseline for handover in multi-beam low Earth orbit satellite networks and builds the Multi-Catfish Reinforcement Learning (MCRL) framework on that architecture. Its three objectives correspond to angle-aware system energy efficiency, handover cost, and load balancing. MCRL applies experience shaping and reward shaping during training. After training, only the main agent is retained, and each user continues to select the highest-valued feasible action independently.

本研究以多目標深度 Q 學習網路（MODQN）作為多波束低軌衛星換手的基準，並在此架構上建立鯰魚多目標強化式學習（MCRL）。三個目標分別對應角度感知系統能量效率、換手成本與負載平衡。MCRL 在訓練期間使用經驗塑形與獎勵塑形。完成訓練後只保留主代理，且每位使用者仍從可行候選中各自選出價值最高的動作。

## 6.2 Contributions

The main work can be summarized as follows.

本研究的主要工作可整理如下。

For angle-aware system energy efficiency, the first reward is the sum of the selected-link EE contributions, $r_{1,u}(t)=\sum_{s,v}x_{u,s,v}(t)\eta_{u,s,v}(t,\boldsymbol{\theta})$. The off-axis angle first affects $G^{T}$ and then enters the wanted-link numerator directly as $H_{u,s,v}(t)G^{T}(\theta_{u,s,v})$ in Eq. (3.10) and the SINR in Eq. (3.13); the angle-aware RF power is determined by Eqs. (3.11)–(3.12), the same unique link SINR determines throughput, and Eqs. (3.15)–(3.17) form shared system power and EE. The main chain no longer uses target-SINR inversion, a second SINR, or concept-level caps/`min`/`max`. If the existing Chapter 5 numbers came from the legacy runtime, they require runtime parity with the new contract and a rerun before they can be treated as evidence for the revised formulas.

在角度感知系統能量效率方面，第一個獎勵使用所選鏈路 EE 貢獻的總和，$r_{1,u}(t)=\sum_{s,v}x_{u,s,v}(t)\eta_{u,s,v}(t,\boldsymbol{\theta})$。偏軸角先由式 (3.7) 影響 $G^{T}$，再在式 (3.10) 以 $H_{u,s,v}(t)G^{T}(\theta_{u,s,v})$ 直接進入式 (3.13) 的 wanted-link numerator；角度感知 RF power 由式 (3.11)–(3.12) 決定，同一個唯一鏈路 SINR 再決定 throughput，並透過式 (3.15)–(3.17) 形成共同系統功率與 EE。本文不再以 target SINR、需求功率反推、第二套 SINR 或概念層 cap／`min`／`max` 描述主鏈；第五章的既有數值若來自 legacy runtime，須待新契約完成 runtime parity 並重跑後才能作為新版公式的實證。

For multi-objective catfish training, the main side and catfish side each contain three Q-networks corresponding to energy efficiency, handover, and load balancing; the three catfish-side networks share one environment trajectory and replay buffer. Energy-efficiency stratification, asymmetric discounting, and periodic mixed-batch intervention change the experiences and the within-episode return weighting used by the catfish side. The paired competitive reward changes only its first objective. After training, only the main side is retained.

在多目標鯰魚訓練方面，主代理與鯰魚代理各包含三個 Q 網路，分別對應能量效率、換手與負載平衡；鯰魚代理的三個網路共享同一條環境軌跡與經驗池。能效分層、非對稱折扣與週期性混合批次介入改變鯰魚代理所使用的經驗與回合內回報加權。配對競爭獎勵**只**調整鯰魚代理的第一個目標。訓練完成後只保留主代理。

## 6.3 Limitations and Future Work

System power includes the power amplifier, active-beam RF chains, satellite-shared baseband power, and beam-training and handover event energies. The current setting uses $E_{\mathrm{tr}}=E_{\mathrm{ho}}=0$, while other satellite hardware, signal-processing, and control power are outside the model. Future work can extend these power sources and reassess their effects on energy efficiency and method comparisons.

本文的系統功率包含功率放大器、啟用波束的射頻鏈、衛星共用的基頻功率，以及波束訓練與換手事件能量。目前設定 $E_{\mathrm{tr}}=E_{\mathrm{ho}}=0$，而其他衛星硬體、訊號處理與控制功率未納入模型。後續可擴充這些功率來源，並重新檢查其對能量效率與方法比較的影響。

The current model is defined for one simulated environment and includes idealized assumptions in both the energy-efficiency definition and the environment settings. The performance difference between MCRL and the baseline remains to be determined by complete experiments; later studies can examine different user counts, constellation conditions, and environments closer to practical systems.

目前模型以單一模擬環境為對象，能量效率定義與環境設定也包含理想化假設。MCRL 與基準方法的效能差異仍待完整實驗判定；後續可在不同使用者數、星座條件與更接近實際的環境中檢查方法的適用範圍。
