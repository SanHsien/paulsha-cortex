"""#223（design #208 H.3）：work_bridge.workflow_status() 新增 needs_decomposition。

claim.py 完全透過 workflow_status() 取得 active_status（見 work_actions.py:
``active_status=workflow_status(canonical_run)``），這是新舊子系統唯一的橋接
點，所以此處只需驗證 facet -> status 的對應本身，不需要重複 claim 層的行為。
"""

from __future__ import annotations

from types import SimpleNamespace

from paulsha_cortex.coordinator.work_bridge import workflow_status


def _run(*, status: str = "ongoing", facets: tuple[str, ...] = ()) -> SimpleNamespace:
    return SimpleNamespace(status=status, facets=facets)


def test_needs_decomposition_facet_surfaces_as_needs_decomposition_status() -> None:
    assert workflow_status(_run(facets=("needs_decomposition",))) == "needs_decomposition"


def test_needs_human_still_takes_priority_over_needs_decomposition() -> None:
    # 深度逾限時 manager 只會設 needs_human（不會兩個 facet 並存），但橋接函式
    # 本身的優先序仍要固定：needs_human 是既有、最高優先序的終止 facet。
    run = _run(facets=("needs_decomposition", "needs_human"))
    assert workflow_status(run) == "needs_human"


def test_blocked_still_surfaces_when_no_higher_priority_facet_present() -> None:
    assert workflow_status(_run(facets=("blocked",))) == "blocked"


def test_done_and_superseded_status_are_unaffected() -> None:
    assert workflow_status(_run(status="done")) == "done"
    assert workflow_status(_run(status="superseded")) == "blocked"


def test_plain_ongoing_run_without_facets_stays_ongoing() -> None:
    assert workflow_status(_run()) == "ongoing"
