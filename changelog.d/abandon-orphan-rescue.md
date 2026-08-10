### Fixed
- **abandon 孤兒救援窄放行（issue 410 建議 2）**：work item 改名／重識別後，舊識別 authority 失去 issue／openspec 映射，run refs 與 authority 恆不相等，嚴格相等守衛使孤兒 run 永遠不可 abandon、其 issue 認領持續與新識別相撞。僅在「authority 兩類映射皆空、run 仍留 refs」的孤兒簽名下放行（expected_run_id／actor／reason 強制項與單一 ongoing 檢查不變、evidence 照常落盤）；authority 映射非空的真 refs 漂移維持 fail-closed。
