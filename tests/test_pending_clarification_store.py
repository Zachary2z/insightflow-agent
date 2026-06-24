import pytest

from workspaces.store import WorkspaceStore


def test_pending_clarification_store_persists_and_completes_run(tmp_path):
    from workspaces.pending_clarification_store import PendingClarificationNotFoundError, PendingClarificationStore

    workspace_store = WorkspaceStore(tmp_path / "workspaces")
    workspace = workspace_store.create_workspace("Clarification Workspace")
    store = PendingClarificationStore(workspace_store)

    pending = store.create_pending_run(
        workspace_id=workspace["workspace_id"],
        run_id="run_1",
        original_question="帮我分析渠道表现",
        question_understanding={"intent": {"dimension": "channel"}, "missing_slots": ["time_range"]},
        clarification_question="你希望分析哪个时间范围？",
        raw_result={"status": "waiting_for_clarification"},
    )

    loaded = store.load_pending_run(workspace["workspace_id"], pending["pending_run_id"])
    assert loaded["pending_run_id"] == pending["pending_run_id"]
    assert loaded["workspace_id"] == workspace["workspace_id"]
    assert loaded["original_question"] == "帮我分析渠道表现"
    assert loaded["system_understanding"]
    assert loaded["clarification_question"] == "你希望分析哪个时间范围？"
    assert loaded["missing_fields"] == ["time_range"]
    assert loaded["status"] == "pending"

    completed = store.complete_pending_run(
        workspace_id=workspace["workspace_id"],
        pending_run_id=pending["pending_run_id"],
        clarification_answer="最近 90 天",
        resolved_question="分析最近 90 天各渠道表现并给出预算建议。",
    )
    assert completed["status"] == "completed"
    assert completed["clarification_answer"] == "最近 90 天"
    assert completed["resolved_question"] == "分析最近 90 天各渠道表现并给出预算建议。"

    reloaded = store.load_pending_run(workspace["workspace_id"], pending["pending_run_id"])
    assert reloaded["status"] == "completed"

    with pytest.raises(PendingClarificationNotFoundError):
        store.load_pending_run(workspace["workspace_id"], "pending_missing")


def test_pending_clarification_store_isolates_workspace_ids(tmp_path):
    from workspaces.pending_clarification_store import PendingClarificationNotFoundError, PendingClarificationStore

    workspace_store = WorkspaceStore(tmp_path / "workspaces")
    first = workspace_store.create_workspace("First Workspace")
    second = workspace_store.create_workspace("Second Workspace")
    store = PendingClarificationStore(workspace_store)

    pending = store.create_pending_run(
        workspace_id=first["workspace_id"],
        run_id="run_1",
        original_question="帮我看看销售情况",
        question_understanding={"missing_slots": ["dimension"]},
        clarification_question="请确认分析维度？",
        raw_result={"status": "waiting_for_clarification"},
    )

    with pytest.raises(PendingClarificationNotFoundError):
        store.load_pending_run(second["workspace_id"], pending["pending_run_id"])
