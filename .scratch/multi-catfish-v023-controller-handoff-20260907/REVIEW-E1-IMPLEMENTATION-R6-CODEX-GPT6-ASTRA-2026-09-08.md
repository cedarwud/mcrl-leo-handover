R6：未發現阻擋封存的問題。

- **入口順序：** pin 是三個 `main()` 的首個操作，早於參數解析、數值執行與 bindings capture：[runner:2444](.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:2444)、[preflight:53](.scratch/multi-catfish-v023-c3-existence-e1/build_e1_preflight_manifest.py:53)、[authority:109](.scratch/multi-catfish-v023-c3-existence-e1/build_e1_launch_authority.py:109)。Imports 在前；檢查的初始化未見 NumPy／Torch 平行運算。
- **拒絕邏輯：** [runner:134](.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:134) 設定 inter-op／intra-op 為 1；late-call `RuntimeError` 轉為 `E1Error`，入口輸出錯誤並回傳 2；另有設定後讀回驗證。
- **Bindings：** [runner:511](.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:511) 驗證兩種 thread count；[runner:545](.scratch/multi-catfish-v023-c3-existence-e1/run_v023_c3_existence_e1.py:545) 記錄兩者及 `interop_pinned_by`。
- **測試覆蓋：** [tests:1053](.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:1053)、[1108](.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:1108)、[1135](.scratch/multi-catfish-v023-c3-existence-e1/test_run_v023_c3_existence_e1.py:1135) 分別涵蓋三入口成功、模擬 inter-op 20 拒絕、late-call 拒絕。
- **科學內容：** pass 5 至目前 checkout 的 E1 diff 僅涉及 runtime pin、bindings 標記及測試；公式、seeds、thresholds、estimands 未改。合約 SHA-256 完整吻合提供值。

本次僅靜態只讀核查，未重跑測試或 server preflight。可依序進行 server **preflight → authorities → dry-run**。

ASTRA_E1_IMPL=READY_TO_SEAL