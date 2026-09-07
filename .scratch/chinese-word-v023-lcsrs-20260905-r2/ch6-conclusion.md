# 6. Conclusion

## 6.1 Summary

本稿提出與 current method 對齊的 Multi-Catfish Reinforcement Learning（MCRL）方法草稿。方法層的 Main 只有一個最終目標：在完整評估範圍以 network ratio-of-sums energy efficiency 計算總 delivered bits 與總 network energy 的比值。部署端固定使用恰好三個獨立 Q surface：$Q_1$、$Q_2$ 與 $Q_3$；三者在共同 safe mask 下無權重相加，經一次 masked $\arg\max$ 只執行一個 Main action。

三條 route 各有明確角色。C1 以 focal current-slot own-rate 加上完整 opening-step marginal network-energy surplus 建立第一路來源；RIS EXP／ACRM 只作 training-source 與 comparison lineage。C2 是目前固定的 OPS-3 projected-persistence route，於本稿中仍 present but empirically unqualified。C3 是 strict two-user Local Coalition-Shapley Spatial Residual Surplus（LC-SRS）：training-only teacher 以 00、10、01、11 四個 matched current-slot profiles 產生 scoped residual label，deployment student 則從 deterministic relational C3View 學習 reference-centred scalar $Q_3$。

## 6.2 Contributions

本研究目前可在方法層整理出下列貢獻：

1. 將 Main-only network ratio-of-sums EE 與第三章的角度、功率、SINR、throughput 及系統耗能物理鏈接合，並保持每個 served segment 的起始與 continuity 語意。
2. 將 C1、C2、C3 明確分成三個獨立 Q surface 的 route-specific learning source；三路使用同一 native safe-mask contract，但不以 legacy reward 向量、vote 或多代理部署方式解釋。
3. 定義 C3 的 exact two-user four-profile teacher、$z_{3,i}=e_i+\Psi/2$ paper target、deterministic relational C3View、shared token scorer 與 reference-centred scalar output。teacher 的 privileged profile outcome 不進入 deployment state。
4. 保留 single-pass deployment boundary：$Q_1+Q_2+Q_3$ 直接無權重相加後只做一次 masked $\arg\max$，不加入 coordinator、auction、joint decoder、fallback、retry 或 post-selection repair。

## 6.3 Limitations and Future Work

本稿是 current method-aligned draft，不是 empirical-final。C3 method core 的公式與 interface 已明確限定，但 gate outcome 尚未開啟；因此不能由方法定義推論 C3 的 learnability、composition benefit、EE efficacy 或 FULL-over-ablation ordering。C1 的 qualification 與 C2 的 OPS-3 qualification 同樣保持開放，RIS EXP／ACRM 也不構成已驗證的效果證據。

Chapter 5 的既有實驗章在本次支線保持 byte-for-byte 不變，其中的設定與結果仍屬既有 provenance，不能偷偷改寫成 V0.23 實證。後續若要回答 learnability 或 composition 問題，必須依另行凍結的執行契約完成可追溯的 source、learner、physical 與 deployment receipts，再更新實驗章與結論；在此之前，本章只保留方法描述與限制。
