---
status: accepted
work_item: terminal-result-contract
---

# terminal-result-contract Design

## Decisions

### D1 envelope 以版本欄位開新，不就地擴充舊形狀

新增帶 `schema_version` 的 canonical result envelope，而不是在既有 terminal payload 上逐欄補丁。

理由：既有形狀的「成功偏置」來自欄位集合本身（失敗與 needs_human 沒有對等的表達位置），就地補欄位會讓新舊兩種讀法並存，harvest 必須猜測對方用哪一種。版本欄位讓 harvest 可以明確分流，舊形狀走既有相容路徑並記可觀測的 legacy 標記。

### D2 gate evidence 由 manager 重驗，不信 card 自述

`passed` 的採信條件是 manager 端能重新讀到並驗證 gate evidence，而不是 card 宣稱跑過。

理由：這是本 issue 的核心。既有設計已有 `_write_status_evidence` 與 evidence hash 機制，重驗成本低（讀檔＋比 hash），而信任成本高（一次假 passed 就是一次錯誤交付）。採信門檻放在 manager 側，才能讓「模型可以說謊」這件事不影響結果正確性。

### D3 矛盾偵測優先於狀態採信

harvest 先做確定性 cross-check（gate command 結果 vs terminal 宣稱狀態），矛盾即 fail closed，之後才進入正常的狀態處理。

理由：矛盾是強訊號，且判定成本固定。把它排在最前面，可以避免「先按 passed 走一段流程、後面才發現不對」造成的部分副作用（例如已經推進 phase 或建立 delivery 前置）。

### D4 normalization 採白名單，且單次嘗試

wrapper normalization 只認明確列舉的外層鍵形狀，且對同一個確定性 mismatch 只嘗試一次修復；修不掉就終止為可操作錯誤，不回派模型。

理由：確定性錯誤重試模型不會改善結果，只會複製成本——這正是 retry storm 的成因。寬鬆解析（例如遞迴尋找第一個看起來像 canonical 的 dict）會把未知形狀悄悄吞掉，讓契約破口從「明顯失敗」變成「安靜的錯誤資料」，比失敗更糟。

### D5 retry 計數與 validation path 進 status surface

schema retry 的計數器、最後一次 validation path 與 reason 都寫進 status／inspect 可見的欄位。

理由：#261 的成本問題之所以難察覺，是因為 retry 發生在模型呼叫層、operator 只看得到「還在跑」。把計數暴露出來，異常重試在面板上就是可見的數字，不需要翻 job jsonl。

### D6 診斷資訊與 authority 分離儲存

parse 失敗時保留的 observed HEAD／job id／失敗原因，寫在明確標示為唯讀診斷的欄位，與授予 candidate authority 的欄位不共用。

理由：#260 已經出現過「有 candidate 但不能 bind」的情境，兩者混用會讓後續 recovery 難以判斷某個 SHA 究竟是「觀察到的」還是「已授權的」。

## 風險與緩解

- **既有 card 全數需要對齊新 envelope**：以版本欄位分流，舊形狀維持可讀並記 legacy 標記，避免一次性大改造成全面停擺。
- **重驗 gate evidence 增加 harvest 成本**：僅在宣稱 `passed` 時重驗，failed／needs_human 路徑不受影響；重驗以讀檔與比 hash 為主，不重跑昂貴 gate。
- **白名單過窄可能誤殺合法輸出**：normalization 失敗終止為可操作錯誤而非靜默丟棄，operator 可從 validation path 直接看出是哪個形狀未涵蓋，再決定是否擴充白名單。
