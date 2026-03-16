"""SSE 어댑터 테스트 — xgen-workflow 호환 이벤트 포맷 검증."""

import json
from src.api.sse_adapter import agent_event_to_sse, make_deploy_response, make_envelope_response


def test_thinking_event():
    """thinking → event: log."""
    events = agent_event_to_sse({"type": "thinking", "data": {"iteration": 1}})
    assert len(events) == 1
    assert events[0]["event"] == "log"
    data = json.loads(events[0]["data"])
    assert "Thinking" in data["message"]


def test_thinking_event_skip_detail():
    """deploy 모드에서 thinking → 미전송."""
    events = agent_event_to_sse(
        {"type": "thinking", "data": {"iteration": 1}},
        skip_detail_log=True,
    )
    assert len(events) == 0


def test_tool_call_event():
    """tool_call → event: tool (tool_call)."""
    events = agent_event_to_sse({
        "type": "tool_call",
        "data": {"name": "db_query", "arguments": {"query": "SELECT 1"}},
    })
    assert len(events) == 1
    assert events[0]["event"] == "tool"
    data = json.loads(events[0]["data"])
    assert data["event_type"] == "tool_call"
    assert data["tool_name"] == "db_query"
    assert data["tool_input"]["query"] == "SELECT 1"


def test_tool_result_event():
    """tool_result → event: tool (tool_result)."""
    events = agent_event_to_sse({
        "type": "tool_result",
        "data": {"name": "db_query", "result": {"rows": []}},
    })
    assert len(events) == 1
    assert events[0]["event"] == "tool"
    data = json.loads(events[0]["data"])
    assert data["event_type"] == "tool_result"
    assert data["tool_name"] == "db_query"


def test_tool_events_skip_detail():
    """deploy 모드에서 tool 이벤트 미전송."""
    events = agent_event_to_sse(
        {"type": "tool_call", "data": {"name": "test"}},
        skip_detail_log=True,
    )
    assert len(events) == 0

    events = agent_event_to_sse(
        {"type": "tool_result", "data": {"name": "test", "result": {}}},
        skip_detail_log=True,
    )
    assert len(events) == 0


def test_done_event():
    """done → data(type:data) + data(type:end)."""
    events = agent_event_to_sse({"type": "done", "data": "최종 응답입니다"})
    assert len(events) == 2

    data_event = json.loads(events[0]["data"])
    assert data_event["type"] == "data"
    assert data_event["content"] == "최종 응답입니다"

    end_event = json.loads(events[1]["data"])
    assert end_event["type"] == "end"
    assert end_event["message"] == "Stream finished"


def test_error_event():
    """error → data(type:error)."""
    events = agent_event_to_sse({
        "type": "error",
        "data": {"error": "모델 호출 실패"},
    })
    assert len(events) == 1
    data = json.loads(events[0]["data"])
    assert data["type"] == "error"
    assert "모델 호출 실패" in data["detail"]


def test_approval_required_event():
    """approval_required → event: log."""
    events = agent_event_to_sse({
        "type": "approval_required",
        "data": {"action": "DELETE FROM users", "request_id": "apr_123"},
    })
    assert len(events) == 1
    assert events[0]["event"] == "log"
    data = json.loads(events[0]["data"])
    assert data["level"] == "warning"


def test_make_deploy_response():
    """Deploy JSON 응답."""
    resp = make_deploy_response("결과 텍스트")
    assert resp["success"] is True
    assert resp["content"] == "결과 텍스트"
    assert resp["citations"] == []
    assert resp["error"] is None


def test_make_deploy_response_with_error():
    """Deploy 에러 응답."""
    resp = make_deploy_response("", error="실패")
    assert resp["success"] is False
    assert resp["error"] == "실패"


def test_make_envelope_response():
    """Envelope 응답."""
    resp = make_envelope_response("결과", citations=[{"file": "test.pdf"}])
    assert resp["code"] == "200"
    assert resp["payload"]["content"] == "결과"
    assert len(resp["payload"]["citations"]) == 1
