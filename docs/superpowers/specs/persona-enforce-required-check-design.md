---
status: accepted
work_item: persona-enforce-required-check
---

# persona-enforce-required-check Design

## Decisions

### D1 先做可重跑的歷史回放，再切 enforcement

新增以歷史變更集回放 persona scope 判定的工具與測試，證明零誤殺後才切 `enforce`。回放本身留在 repo 內可重跑。

理由：shadow → enforce 是一次性的信任躍遷。如果只憑「目前看起來沒問題」就切，enforce 上線後的假陽性會直接擋住合法 PR，而當下的壓力會促使 operator 濫用豁免 label——規則反而比 shadow 時更沒有意義。可重跑的回放也讓日後修改 scope 定義時能立即看出影響。

### D2 零誤殺只能靠修正契約達成，不靠放寬檢查

回放發現誤殺時，修正方向限於契約／scope 定義本身；不得以擴大豁免範圍或降低檢查強度來讓回放通過。

理由：後者會讓「零誤殺」變成自我實現的空話。這條寫進 spec 是為了讓實作階段沒有便宜行事的空間。

### D3 違規訊息必須可定位

`persona-scope.yml` 的輸出包含 persona、實際觸及路徑、以及違反的 scope 規則三者。

理由：required check 一旦擋下 PR，作者需要在不讀 workflow 原始碼的情況下知道怎麼修。只回「persona-scope failed」會把成本轉嫁給每一個被擋的人。

### D4 豁免不靜音

套用 `policy-exempt:persona-scope` 時仍輸出違規內容，只是不阻擋合併。

理由：豁免的用途是「這次確實有正當理由」，不是「讓問題消失」。保留輸出讓事後稽核可以看出豁免被用在哪、用了幾次，也能發現契約是否需要調整。

## 風險與緩解

- **切換後出現回放未涵蓋的誤殺**：豁免 label 提供即時出口，且因為豁免不靜音，這類案例會被記錄下來成為修正契約的輸入。
- **required check 造成既有 PR 全面受阻**：回放涵蓋近期已合併 PR，切換前即可估計影響面；若回放顯示大量違規，代表應先修契約而非切換。
- **豁免被常態化使用**：豁免仍輸出違規內容，使用頻率可被觀察；頻繁使用即為契約需要調整的訊號。
