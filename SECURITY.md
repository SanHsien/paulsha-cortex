# 安全政策

## 支援範圍

本 fork 目前是 research/development fork，不承諾 production SLA。安全修正以目前 `main` 為主；upstream release 的支援狀態由 upstream 維護者決定。

## 私下回報

疑似漏洞請使用 [GitHub Private Vulnerability Reporting](https://github.com/SanHsien/paulsha-cortex/security/advisories/new)，附上受影響 commit、最小重現、影響與已移除敏感資料的診斷資訊。完成修補前不要公開 issue、可直接利用的 PoC、token、個人路徑或 agent session 內容。

## 主要信任邊界

- Candidate、verification、review 與 merge evidence 必須綁定同一不可變 commit。
- Builder 產生的測試敘述與 evidence 都是不受信任輸入；權威 gate 必須獨立重跑。
- Foreign reviewer 不應取得 Candidate 寫入權、home secrets、Docker socket、MCP 或可沿用的遠端 session。
- GitHub token、executor credentials、環境變數與 control files 不得進入 report、issue 或 log。
- Worktree、branch、retry、recovery 與 cleanup 必須限定 exact target，不能以寬鬆 glob 或 agent 自報授權。
- 缺少 sandbox dependency 或 provenance 時應 fail closed，不可靜默降級成 unsandboxed execution。

變更上述邊界時，PR 必須附 threat analysis、regression tests 與失敗時的停止／復原策略。
