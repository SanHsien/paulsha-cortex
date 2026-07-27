"""#223（design #208 H.3）：decomposition_depth 進可觀測面（cortex list）。

WorkflowRun.to_dict() 現在恆帶 ``decomposition_depth`` 鍵；Monitor 的 workflow
registry row 驗證器（``_validate_workflow_v2_row``）對未知鍵 fail-closed
（見 providers.py:448 ``keys - REQUIRED - OPTIONAL`` 一命中就 raise），比照
#222 sizing_score/sizing_band 的既有模式，新欄位必須同步補進
``_WORKFLOW_V2_OPTIONAL_ROW_KEYS`` 白名單，否則任何一筆 run 落地後
``cortex list`` 會整批拒絕。
"""

from __future__ import annotations

from paulsha_cortex.monitor.providers import _validate_workflow_v2_row


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "run_id": "workflow-decomposition-depth-223",
        "repo": "hamanpaul/paulsha-cortex",
        "work_id": "decomposition-depth-work",
        "current_phase": "plan",
        "issue_refs": [],
        "pr_refs": [],
        "openspec_refs": [],
    }
    row.update(overrides)
    return row


def test_row_with_decomposition_depth_is_accepted() -> None:
    _validate_workflow_v2_row(_row(decomposition_depth=1))


def test_row_without_decomposition_depth_still_accepted() -> None:
    _validate_workflow_v2_row(_row())
