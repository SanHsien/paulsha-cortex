# fork 分岔量改由 upstream-check 當場算

- `tools/check_upstream_updates.py` 新增 `fork_status()`：以 `upstream_baseline.json` 的 `reviewed_through` 為共同基準，算出本 fork 的 ahead 與 upstream 的 behind，連同兩邊的短 SHA 一起寫進報告。每次執行都會印，包含「沒有新 release」的安靜週次——原本那種執行完全不帶資訊。
- `docs/FORK.md` 的水位快照移除寫死的 `ahead 44 / behind 202`。那個數字隨每次 commit 變動，寫下的當下就開始過期（合併 #13／#14 後實際已是 56）。文件只保留穩定的 SHA 與決策，分岔量指向 workflow run summary 的 Fork status 或本機執行。
- fork status 算不出來時只在報告裡標示無法計算，不讓整個 upstream 檢查變紅——它與「上游有沒有動」無關。
