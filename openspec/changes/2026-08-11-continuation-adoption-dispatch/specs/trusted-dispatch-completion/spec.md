---
status: accepted
work_item: continuation-adoption-dispatch
---

## ADDED Requirements

### Requirement: Continuation slice MUST宣告式指定既有worktree或既有branch，MUST NOT重用既有分支強制reset路徑

系統MUST提供一種新的slice型態（continuation slice），透過frontmatter新增
`continuation`欄位宣告adopt既有的worktree（`existing_worktree`絕對路徑）或
既有branch（`existing_branch`）。dispatch MUST NOT為此類slice呼叫既有
worktree建立路徑中「同名branch存在時強制reset到base」的分支（現行
`ScriptWorktreeCreator.create()`對既有同名branch的行為），該行為會摧毀
continuation本應保留的既有commit歷史。既有（未宣告`continuation`）slice的
dispatch行為MUST維持位元不變。

#### Scenario: spec宣告existing_worktree

- **WHEN** slice spec的frontmatter含`continuation.existing_worktree: <abs
  path>`且該路徑為目標repo的合法既有git worktree
- **THEN** dispatch對此slice MUST NOT建立新worktree，MUST直接以該既有路徑
  作為builder job的worktree

#### Scenario: 既有slice不受影響

- **WHEN** slice spec未宣告`continuation`欄位
- **THEN** dispatch行為與現行完全一致，仍一律建立新worktree／
  `feature/<slice_id>`branch

### Requirement: Adoption MUST先驗證repo歸屬與in-flight佔用，dirty worktree MUST NOT在未顯式宣告下被adopt

Adoption前，系統MUST驗證`existing_worktree`／`existing_branch`確實屬於目標
repo（同一git common dir），MUST確認registry中沒有其他in-flight job已佔用
同一worktree路徑或branch名稱。宣告`existing_worktree`但其working tree非
乾淨（`git status --porcelain`非空）時，系統MUST要求spec同時顯式宣告
`continuation.adopt_dirty: true`；未宣告時MUST fail-closed拒絕整次
adoption，不得靜默略過dirty狀態逕行派工。

#### Scenario: dirty worktree未顯式宣告adopt_dirty

- **WHEN** `existing_worktree`路徑非乾淨且spec未宣告`adopt_dirty: true`
- **THEN** adoption fail-closed拒絕，不建立job，不消耗該slice的派工嘗試

#### Scenario: worktree已被其他in-flight job佔用

- **WHEN** `existing_worktree`與某個仍在`IN_FLIGHT_STATUSES`的既有job的
  `worktree`欄位相同
- **THEN** adoption fail-closed拒絕，錯誤訊息指出衝突的既有job

### Requirement: Continuation candidate仍MUST滿足既有exact-candidate純度不變量，MUST NOT為dirty adoption放寬退出邊界檢查

Continuation slice的candidate仍MUST通過現行`run_result_verification`的
全部退出邊界檢查（worktree乾淨、candidate已較dispatch base前進、
dispatch base為candidate的ancestor）。「adopt dirty worktree」僅適用於
builder session開始時繼承的進入邊界狀態，MUST NOT被解讀為放寬job結束時
的純度要求。

#### Scenario: continuation candidate結束時仍dirty

- **WHEN** continuation slice的builder job結束但worktree仍有未commit變更
- **THEN** verification MUST將該slice導向`needs_human`，與非continuation
  slice完全相同的判定路徑

#### Scenario: mid-merge遭abort而非完成

- **WHEN** 進入adoption時worktree存在`MERGE_HEAD`，builder job結束時該
  merge已被abort（candidate不含target分支最新內容）
- **THEN** verification的ancestry檢查MUST判定dispatch base非candidate的
  ancestor，導向`needs_human`，不得建立CompletionRecord

### Requirement: Adopted worktree的生命週期MUST NOT併入coordinator既有的worktree回收範圍

系統的既有worktree回收機制（`cortex work gc`）MUST維持只掃描其配置的
worktree pool root邊界內的worktree，對adoption使用的既有外部路徑
MUST NOT自動介入回收（建立、刪除、reset）。

#### Scenario: adopted worktree路徑落在pool root之外

- **WHEN** `existing_worktree`路徑不在coordinator配置的worktree pool root
  之下
- **THEN** `cortex work gc`的掃描結果MUST NOT包含該路徑作為任何分類項目
