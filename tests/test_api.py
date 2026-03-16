"""FastAPI API 엔드포인트 테스트 — xgen-workflow 호환 검증."""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ─── Health ───

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "xgen-agent"


# ─── 도구 목록 ───

def test_list_tools(client):
    resp = client.get("/api/tools/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] > 0
    tool_names = [t["name"] for t in data["tools"]]
    assert "http_request" in tool_names
    assert "file_read" in tool_names
    assert "db_query" in tool_names


# ─── 워크플로우 CRUD (xgen-workflow 호환) ───

def test_list_workflows_no_db(client):
    resp = client.get("/api/workflow/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agents"] == []


def test_save_workflow_no_db(client):
    resp = client.post("/api/workflow/save", json={
        "workflow_name": "test-wf",
        "workflow_id": "wf-001",
    })
    assert resp.status_code == 503


def test_delete_workflow_no_db(client):
    resp = client.delete("/api/workflow/delete/wf-001")
    assert resp.status_code == 503


def test_check_workflow_no_db(client):
    resp = client.post("/api/workflow/check/workflow?workflow_name=test")
    assert resp.status_code == 200
    assert resp.json()["exists"] is False


# ─── 배포 관리 ───

def test_deploy_list(client):
    resp = client.get("/api/workflow/deploy/list")
    assert resp.status_code == 200
    assert resp.json()["deployed"] == []


def test_deploy_status(client):
    resp = client.get("/api/workflow/deploy/status/wf-001")
    assert resp.status_code == 200
    assert resp.json()["deployed"] is False


def test_deploy_toggle(client):
    resp = client.post("/api/workflow/deploy/toggle/wf-001")
    assert resp.status_code == 200


# ─── 트레이스 (xgen-workflow 경로) ───

def test_trace_list(client):
    resp = client.get("/api/workflow/trace/list")
    assert resp.status_code == 200
    data = resp.json()
    assert "traces" in data
    assert "total" in data
    assert "page" in data


def test_trace_detail_not_found(client):
    resp = client.get("/api/workflow/trace/detail/없는거")
    assert resp.status_code == 404


def test_trace_by_interaction(client):
    resp = client.get("/api/workflow/trace/by-interaction/default")
    assert resp.status_code == 200
    assert "traces" in resp.json()


# ─── 스케줄 ───

def test_schedule_sessions_list(client):
    resp = client.get("/api/workflow/schedule/sessions")
    assert resp.status_code == 200
    assert resp.json()["sessions"] == []


def test_schedule_status(client):
    resp = client.get("/api/workflow/schedule/status")
    assert resp.status_code == 200


# ─── 성능 ───

def test_performance(client):
    resp = client.get("/api/workflow/performance?workflow_id=wf-001")
    assert resp.status_code == 200


# ─── 실행 상태 ───

def test_execution_status(client):
    resp = client.get("/api/workflow/execute/status")
    assert resp.status_code == 200
    assert resp.json()["executions"] == []


def test_execution_cleanup(client):
    resp = client.post("/api/workflow/execute/cleanup")
    assert resp.status_code == 200


# ─── 세션/이력 ───

def test_sessions_no_db(client):
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert resp.json()["sessions"] == []


def test_history_no_db(client):
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert resp.json()["history"] == []


# ─── MCP ───

def test_mcp_servers_empty(client):
    resp = client.get("/api/mcp/servers")
    assert resp.status_code == 200
    assert resp.json()["servers"] == []


# ─── 버전 ───

def test_version_list_no_db(client):
    resp = client.get("/api/workflow/version/list?workflow_id=wf-001")
    assert resp.status_code == 200
    assert resp.json()["versions"] == []
