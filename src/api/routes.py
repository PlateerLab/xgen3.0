"""FastAPI 엔드포인트 — xgen-workflow 완전 호환 + xgen3.0 확장."""

from __future__ import annotations

import json
import os
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.core.agent import Agent
from src.core.model_client import ModelClient
from src.tools.registry import ToolRegistry
from src.trace.collector import TraceCollector
from src.api.models import (
    WorkflowRequest,
    SaveWorkflowRequest,
    ApprovalActionRequest,
    GenerateToolRequest,
)
from src.store.history import HistoryStore
from src.api.sse_adapter import agent_event_to_sse, make_deploy_response, make_envelope_response

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════
# 헬퍼
# ═══════════════════════════════════════════════════

def _get_model_client(model: str | None = None) -> ModelClient:
    base_url = os.environ.get("MODEL_BASE_URL", "http://localhost:11434/v1")
    api_key = os.environ.get("MODEL_API_KEY", "")
    model_name = model or os.environ.get("MODEL_NAME", "default")
    return ModelClient(base_url=base_url, api_key=api_key, model=model_name)


async def _create_agent(request: Request, req: WorkflowRequest) -> tuple[Agent, ModelClient]:
    tool_registry: ToolRegistry = request.app.state.tool_registry
    trace_collector: TraceCollector = request.app.state.trace_collector
    state_store = request.app.state.state_store
    agent_store = request.app.state.agent_store

    agent_name = req.workflow_name or req.workflow_id or "default"
    system_prompt = req.system_prompt or ""
    model = req.model
    approval_patterns = req.approval_required

    # DB에서 에이전트 정의 로드 시도
    if agent_store:
        agent_def = await agent_store.load(agent_name)
        if agent_def:
            system_prompt = system_prompt or agent_def.get("system_prompt", "")
            model = model or agent_def.get("model")
            if not approval_patterns:
                approval_patterns = agent_def.get("approval_required")

    model_client = _get_model_client(model)

    agent = Agent(
        name=agent_name,
        model_client=model_client,
        tool_registry=tool_registry,
        system_prompt=system_prompt,
        trace_collector=trace_collector,
        state_store=state_store,
        approval_patterns=approval_patterns,
    )
    return agent, model_client


# ═══════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════

@router.get("/health")
async def health():
    return {"status": "ok", "service": "xgen-agent", "version": "0.2.0"}


# ═══════════════════════════════════════════════════
# 실행 (execution.py 호환)
# prefix: /api/workflow/execute
# ═══════════════════════════════════════════════════

@router.post("/api/workflow/execute/based_id/stream")
async def execute_stream(req: WorkflowRequest, request: Request):
    """핵심 엔드포인트 — SSE 스트리밍 실행.

    xgen-workflow와 동일한 SSE 이벤트 포맷:
      event: log, event: node_status, event: tool
      data: {"type": "data", "content": "..."}
      data: {"type": "end", "message": "Stream finished"}
    """
    agent, model_client = await _create_agent(request, req)
    history_store: HistoryStore | None = request.app.state.history_store
    trace_collector: TraceCollector = request.app.state.trace_collector
    _start_time = __import__("time").time()

    async def event_generator():
        result_text = ""
        status = "completed"
        try:
            async for event in agent.run_stream(
                req.message,
                session_id=req.interaction_id,
                resume=req.resume,
            ):
                if event.get("type") == "done":
                    result_text = event.get("data", "")
                elif event.get("type") == "error":
                    status = "failed"
                    result_text = str(event.get("data", {}).get("error", ""))
                sse_events = agent_event_to_sse(event, skip_detail_log=False)
                for sse in sse_events:
                    yield sse
        except Exception as e:
            logger.exception("Agent 실행 오류")
            status = "failed"
            result_text = str(e)
            yield {
                "data": json.dumps(
                    {"type": "error", "detail": str(e)}, ensure_ascii=False
                )
            }
        finally:
            await model_client.close()
            # 실행 이력 기록
            if history_store:
                duration_ms = (__import__("time").time() - _start_time) * 1000
                # trace_id 가져오기
                traces = trace_collector.list_traces(session_id=req.interaction_id)
                trace_id = traces[-1].trace_id if traces else ""
                trace_data = traces[-1].to_dict() if traces else {}
                try:
                    await history_store.record(
                        trace_id=trace_id,
                        session_id=req.interaction_id or "",
                        agent_name=req.workflow_name or req.workflow_id or "default",
                        user_input=req.message,
                        result=result_text if isinstance(result_text, str) else str(result_text),
                        trace_data=trace_data,
                        duration_ms=duration_ms,
                        status=status,
                    )
                except Exception:
                    logger.exception("실행 이력 기록 실패")

    return EventSourceResponse(event_generator())


@router.post("/api/workflow/execute/based_id/stream/deploy")
async def execute_stream_deploy(req: WorkflowRequest, request: Request):
    """Deploy 모드 SSE — 세부 로그(log, node_status, tool) 미전송."""
    agent, model_client = await _create_agent(request, req)

    async def event_generator():
        try:
            async for event in agent.run_stream(
                req.message,
                session_id=req.interaction_id,
                resume=req.resume,
            ):
                sse_events = agent_event_to_sse(event, skip_detail_log=True)
                for sse in sse_events:
                    yield sse
        except Exception as e:
            logger.exception("Agent 실행 오류")
            yield {
                "data": json.dumps(
                    {"type": "error", "detail": str(e)}, ensure_ascii=False
                )
            }
        finally:
            await model_client.close()

    return EventSourceResponse(event_generator())


@router.post("/api/workflow/execute/deploy/stream")
async def execute_deploy_stream(req: WorkflowRequest, request: Request):
    """Deploy 전용 API — json/stream 응답 지원."""
    agent, model_client = await _create_agent(request, req)

    try:
        if req.response_format == "stream":
            # SSE 스트리밍
            async def gen():
                async for event in agent.run_stream(req.message, session_id=req.interaction_id):
                    for sse in agent_event_to_sse(event, skip_detail_log=True):
                        yield sse
                await model_client.close()

            return EventSourceResponse(gen())
        else:
            # JSON 응답
            result = await agent.run(req.message, session_id=req.interaction_id)
            await model_client.close()
            return make_deploy_response(result)
    except Exception as e:
        await model_client.close()
        return make_deploy_response("", error=str(e))


@router.post("/api/workflow/execute/deploy/result")
async def execute_deploy_result(req: WorkflowRequest, request: Request):
    """Java Client용 Envelope 응답."""
    agent, model_client = await _create_agent(request, req)

    try:
        result = await agent.run(req.message, session_id=req.interaction_id)
        return make_envelope_response(result)
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "code": "500",
            "message": str(e),
            "payload": {},
        }
    finally:
        await model_client.close()


@router.get("/api/workflow/execute/status")
async def execution_status(
    request: Request,
    user_id: str | None = Header(default=None),
):
    """모든 실행 상태 조회."""
    # TODO: 실행 상태 추적 구현
    return {"executions": []}


@router.get("/api/workflow/execute/status/{execution_id}")
async def execution_status_by_id(execution_id: str, request: Request):
    """특정 실행 상태 조회."""
    return {"execution_id": execution_id, "status": "unknown"}


@router.post("/api/workflow/execute/cleanup")
async def execution_cleanup():
    """완료된 실행 정리."""
    return {"status": "ok", "cleaned": 0}


# ═══════════════════════════════════════════════════
# Agent 실행 (xgen3.0 전용 — non-streaming)
# ═══════════════════════════════════════════════════

@router.post("/api/agent/run")
async def agent_run(req: WorkflowRequest, request: Request):
    agent, model_client = await _create_agent(request, req)
    try:
        result = await agent.run(req.message, session_id=req.interaction_id, resume=req.resume)
        return {"result": result, "interaction_id": req.interaction_id}
    finally:
        await model_client.close()


# ═══════════════════════════════════════════════════
# 기본 CRUD (basic_operations.py 호환)
# prefix: /api/workflow
# ═══════════════════════════════════════════════════

@router.get("/api/workflow/list")
async def list_workflows(
    request: Request,
    user_id: str | None = Header(default=None),
):
    """워크플로우 목록 조회."""
    agent_store = request.app.state.agent_store
    if not agent_store:
        return {"agents": [], "message": "DB 미연결 — DATABASE_URL 설정 필요"}
    agents = await agent_store.list_agents()
    return {"agents": agents}


@router.post("/api/workflow/save")
async def save_workflow(req: SaveWorkflowRequest, request: Request):
    """워크플로우 저장."""
    agent_store = request.app.state.agent_store
    if not agent_store:
        raise HTTPException(status_code=503, detail="DB 미연결 — DATABASE_URL 설정 필요")

    agent_def = {
        "name": req.workflow_name or req.workflow_id,
        "description": req.description,
        "model": req.model,
        "tools": req.tools or [],
        "system_prompt": req.system_prompt,
        "approval_required": req.approval_required or [],
        "config": {
            "workflow_id": req.workflow_id,
            "workflow_name": req.workflow_name,
            "content": req.content.model_dump() if hasattr(req.content, "model_dump") else req.content,
            **(req.config or {}),
        },
    }
    result = await agent_store.save(agent_def)
    return result


@router.get("/api/workflow/load/{workflow_id}")
async def load_workflow(
    workflow_id: str,
    request: Request,
    user_id: str | None = None,
):
    """워크플로우 로드."""
    agent_store = request.app.state.agent_store
    if not agent_store:
        raise HTTPException(status_code=503, detail="DB 미연결")
    agent_def = await agent_store.load(workflow_id)
    if not agent_def:
        raise HTTPException(status_code=404, detail=f"워크플로우 '{workflow_id}' 없음")
    return agent_def


@router.delete("/api/workflow/delete/{workflow_id}")
async def delete_workflow(workflow_id: str, request: Request):
    """워크플로우 삭제."""
    agent_store = request.app.state.agent_store
    if not agent_store:
        raise HTTPException(status_code=503, detail="DB 미연결")
    deleted = await agent_store.delete(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"워크플로우 '{workflow_id}' 없음")
    return {"status": "deleted", "workflow_id": workflow_id}


# ─── 버전 관리 ───

@router.get("/api/workflow/version/list")
async def list_versions(
    workflow_id: str,
    user_id: str | None = None,
    request: Request = None,
):
    """워크플로우 버전 목록."""
    version_store = getattr(request.app.state, "version_store", None)
    if not version_store:
        return {"versions": [], "message": "DB 미연결"}
    versions = await version_store.list_versions(workflow_id)
    return {"versions": versions}


@router.get("/api/workflow/version/data")
async def get_version_data(
    workflow_id: str,
    version: int,
    user_id: str | None = None,
    request: Request = None,
):
    """특정 버전 데이터 조회."""
    version_store = getattr(request.app.state, "version_store", None)
    if not version_store:
        raise HTTPException(status_code=503, detail="DB 미연결")
    data = await version_store.load_version(workflow_id, version)
    if not data:
        raise HTTPException(status_code=404, detail=f"버전 {version} 없음")
    return data


# ─── 배포 관리 (deploy.py 호환) ───

@router.get("/api/workflow/deploy/load/{user_id}/{workflow_id}")
async def deploy_load(user_id: str, workflow_id: str, request: Request):
    """Deploy용 워크플로우 로드."""
    agent_store = request.app.state.agent_store
    if not agent_store:
        raise HTTPException(status_code=503, detail="DB 미연결")
    agent_def = await agent_store.load(workflow_id)
    if not agent_def:
        raise HTTPException(status_code=404, detail=f"워크플로우 '{workflow_id}' 없음")
    return agent_def


@router.post("/api/workflow/deploy/toggle/{workflow_id}")
async def deploy_toggle(workflow_id: str, request: Request):
    """배포 상태 토글."""
    # TODO: 배포 상태 관리 구현
    return {"workflow_id": workflow_id, "deployed": True}


@router.get("/api/workflow/deploy/status/{workflow_id}")
async def deploy_status(workflow_id: str, request: Request):
    """배포 상태 조회."""
    return {"workflow_id": workflow_id, "deployed": False}


@router.get("/api/workflow/deploy/list")
async def deploy_list(request: Request):
    """배포된 워크플로우 목록."""
    return {"deployed": []}


# ─── 기타 호환 엔드포인트 ───

@router.post("/api/workflow/rename/workflow")
async def rename_workflow(
    old_name: str, new_name: str, workflow_id: str, request: Request
):
    """워크플로우 이름 변경."""
    return {"status": "ok", "old_name": old_name, "new_name": new_name}


@router.post("/api/workflow/check/workflow")
async def check_workflow(workflow_name: str, request: Request):
    """워크플로우 존재 여부 확인."""
    agent_store = request.app.state.agent_store
    if not agent_store:
        return {"exists": False}
    agent = await agent_store.load(workflow_name)
    return {"exists": agent is not None}


# ═══════════════════════════════════════════════════
# 트레이스 (trace.py 호환)
# prefix: /api/workflow/trace
# ═══════════════════════════════════════════════════

@router.get("/api/workflow/trace/list")
async def trace_list(
    page: int = 1,
    page_size: int = 20,
    workflow_id: str | None = None,
    status: str | None = None,
    request: Request = None,
):
    """트레이스 목록."""
    collector: TraceCollector = request.app.state.trace_collector
    traces = collector.list_traces()
    # 간단한 페이지네이션
    start = (page - 1) * page_size
    end = start + page_size
    paginated = traces[start:end]
    return {
        "traces": [t.to_dict() for t in paginated],
        "total": len(traces),
        "page": page,
        "page_size": page_size,
    }


@router.get("/api/workflow/trace/detail/{trace_id}")
async def trace_detail(trace_id: str, request: Request):
    """트레이스 상세."""
    collector: TraceCollector = request.app.state.trace_collector
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"트레이스 '{trace_id}' 없음")
    return trace.to_dict()


@router.get("/api/workflow/trace/by-interaction/{interaction_id}")
async def trace_by_interaction(interaction_id: str, request: Request):
    """인터랙션별 트레이스."""
    collector: TraceCollector = request.app.state.trace_collector
    traces = collector.list_traces(session_id=interaction_id)
    return {"traces": [t.to_dict() for t in traces]}


# ═══════════════════════════════════════════════════
# 스케줄 (schedule.py 호환) — 스텁
# prefix: /api/workflow/schedule
# ═══════════════════════════════════════════════════

@router.post("/api/workflow/schedule/sessions")
async def create_schedule_session(request: Request):
    """스케줄 세션 생성."""
    return {"status": "not_implemented"}


@router.get("/api/workflow/schedule/sessions")
async def list_schedule_sessions(request: Request):
    """스케줄 세션 목록."""
    return {"sessions": []}


@router.get("/api/workflow/schedule/sessions/{session_id}")
async def get_schedule_session(session_id: str):
    return {"session_id": session_id, "status": "not_found"}


@router.delete("/api/workflow/schedule/sessions/{session_id}")
async def delete_schedule_session(session_id: str):
    return {"status": "deleted", "session_id": session_id}


@router.get("/api/workflow/schedule/status")
async def schedule_status():
    return {"status": "idle", "active_sessions": 0}


# ═══════════════════════════════════════════════════
# 성능 (performance.py 호환) — 스텁
# ═══════════════════════════════════════════════════

@router.get("/api/workflow/performance")
async def get_performance(
    workflow_name: str | None = None,
    workflow_id: str | None = None,
):
    return {"stats": {}, "workflow_id": workflow_id}


@router.delete("/api/workflow/performance")
async def delete_performance(
    workflow_name: str | None = None,
    workflow_id: str | None = None,
):
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════
# Human-in-the-Loop 승인 API
# ═══════════════════════════════════════════════════

_active_agents: dict[str, Agent] = {}


@router.post("/api/approval/action")
async def approval_action(req: ApprovalActionRequest):
    for agent in _active_agents.values():
        approval_req = agent.approval.get_request(req.request_id)
        if approval_req:
            if req.action == "approve":
                agent.approval.approve(req.request_id, req.reason)
            else:
                agent.approval.reject(req.request_id, req.reason)
            return {"status": "ok", "request_id": req.request_id, "action": req.action}
    raise HTTPException(status_code=404, detail=f"승인 요청 '{req.request_id}' 없음")


@router.get("/api/approval/pending")
async def list_pending_approvals(session_id: str | None = None):
    pending = []
    for agent in _active_agents.values():
        for req in agent.approval.list_pending(session_id):
            pending.append(req.to_dict())
    return {"pending": pending, "count": len(pending)}


# ═══════════════════════════════════════════════════
# AI 도구 생성
# ═══════════════════════════════════════════════════

@router.post("/api/tools/generate")
async def generate_tool(req: GenerateToolRequest, request: Request):
    from src.tools.generator import ToolGenerator

    tool_registry: ToolRegistry = request.app.state.tool_registry
    model_client = _get_model_client()
    generator = ToolGenerator(model_client=model_client, tool_registry=tool_registry)
    try:
        return await generator.generate(req.description)
    finally:
        await model_client.close()


# ═══════════════════════════════════════════════════
# 도구 관리
# ═══════════════════════════════════════════════════

@router.get("/api/tools/list")
async def list_tools(request: Request):
    registry: ToolRegistry = request.app.state.tool_registry
    tools = registry.list_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in tools
        ],
        "count": len(tools),
    }


# ═══════════════════════════════════════════════════
# MCP 관리
# ═══════════════════════════════════════════════════

class MCPConnectRequest(BaseModel):
    name: str
    transport: str = "sse"
    url: str | None = None
    headers: dict[str, str] | None = None
    command: str | None = None
    args: list[str] | None = None


@router.post("/api/mcp/connect")
async def mcp_connect(req: MCPConnectRequest, request: Request):
    from src.mcp.client import MCPServerConfig, MCPTransport
    from src.mcp.bridge import MCPBridge

    tool_registry: ToolRegistry = request.app.state.tool_registry
    if not hasattr(request.app.state, "mcp_bridge"):
        request.app.state.mcp_bridge = MCPBridge(tool_registry)

    bridge: MCPBridge = request.app.state.mcp_bridge
    config = MCPServerConfig(
        name=req.name,
        transport=MCPTransport(req.transport),
        url=req.url,
        headers=req.headers or {},
        command=req.command,
        args=req.args or [],
    )
    try:
        count = await bridge.connect(config)
        return {"status": "connected", "server": req.name, "tools_loaded": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP 연결 실패: {e}")


@router.delete("/api/mcp/disconnect/{server_name}")
async def mcp_disconnect(server_name: str, request: Request):
    if not hasattr(request.app.state, "mcp_bridge"):
        raise HTTPException(status_code=404, detail="MCP bridge 없음")
    from src.mcp.bridge import MCPBridge
    bridge: MCPBridge = request.app.state.mcp_bridge
    await bridge.disconnect(server_name)
    return {"status": "disconnected", "server": server_name}


@router.get("/api/mcp/servers")
async def list_mcp_servers(request: Request):
    if not hasattr(request.app.state, "mcp_bridge"):
        return {"servers": []}
    from src.mcp.bridge import MCPBridge
    bridge: MCPBridge = request.app.state.mcp_bridge
    return {"servers": bridge.list_servers()}


# ═══════════════════════════════════════════════════
# graph-tool-call
# ═══════════════════════════════════════════════════

class GraphToolSearchRequest(BaseModel):
    query: str
    max_results: int = 10
    source_url: str | None = None


class GraphToolIngestRequest(BaseModel):
    source_url: str
    source_type: str = "openapi"  # openapi, mcp_server
    server_name: str | None = None
    headers: dict[str, str] | None = None


@router.post("/api/tools/search")
async def search_graph_tools(req: GraphToolSearchRequest, request: Request):
    """graph-tool-call 기반 도구 검색.

    GraphToolManager가 초기화되어 있어야 한다.
    source_url이 주어지면 해당 OpenAPI에서 즉석 생성.
    """
    from src.tools.graph_tool import GraphToolManager, GraphToolConfig

    # app.state에 graph_tool_manager가 있으면 사용
    manager: GraphToolManager | None = getattr(request.app.state, "graph_tool_manager", None)

    if manager is None and req.source_url:
        # 즉석 생성
        config = GraphToolConfig(max_results=req.max_results)
        manager = GraphToolManager(config)
        manager.ingest_openapi(req.source_url)

    if manager is None:
        # 레지스트리에서 생성
        config = GraphToolConfig(max_results=req.max_results)
        manager = GraphToolManager(config)
        tool_registry: ToolRegistry = request.app.state.tool_registry
        manager.ingest_from_registry(tool_registry)

    results = manager.retrieve_with_scores(req.query, top_k=req.max_results)
    return {
        "tools": [
            {
                "name": r.tool.name,
                "description": r.tool.description,
                "score": round(r.score, 4),
                "confidence": r.confidence,
                "keyword_score": round(r.keyword_score, 4),
                "graph_score": round(r.graph_score, 4),
            }
            for r in results
        ],
        "count": len(results),
    }


@router.post("/api/tools/ingest")
async def ingest_graph_tools(req: GraphToolIngestRequest, request: Request):
    """graph-tool-call에 도구 소스 추가."""
    from src.tools.graph_tool import GraphToolManager, GraphToolConfig

    manager: GraphToolManager | None = getattr(request.app.state, "graph_tool_manager", None)
    if manager is None:
        manager = GraphToolManager(GraphToolConfig())
        request.app.state.graph_tool_manager = manager

    if req.source_type == "openapi":
        count = manager.ingest_openapi(req.source_url)
    elif req.source_type == "mcp_server":
        count = manager.ingest_mcp_server(req.source_url, server_name=req.server_name)
    else:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 소스 타입: {req.source_type}")

    return {
        "status": "ok",
        "source_url": req.source_url,
        "source_type": req.source_type,
        "tools_ingested": count,
        "total_tools": manager.tool_count,
    }


@router.get("/api/tools/graph/stats")
async def graph_tool_stats(request: Request):
    """graph-tool-call 그래프 통계."""
    from src.tools.graph_tool import GraphToolManager

    manager: GraphToolManager | None = getattr(request.app.state, "graph_tool_manager", None)
    if manager is None:
        return {"status": "not_initialized", "stats": {}}
    return {"status": "ok", "stats": manager.get_stats()}


# ═══════════════════════════════════════════════════
# 세션 관리
# ═══════════════════════════════════════════════════

@router.get("/api/sessions")
async def list_sessions(request: Request):
    state_store = request.app.state.state_store
    if not state_store:
        return {"sessions": [], "message": "DB 미연결"}
    sessions = await state_store.list_sessions()
    return {"sessions": sessions}


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    state_store = request.app.state.state_store
    if not state_store:
        raise HTTPException(status_code=503, detail="DB 미연결")
    deleted = await state_store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"세션 '{session_id}' 없음")
    return {"status": "deleted", "session_id": session_id}


# ═══════════════════════════════════════════════════
# 실행 이력
# ═══════════════════════════════════════════════════

@router.get("/api/history")
async def list_history(
    agent_name: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
    request: Request = None,
):
    history_store = request.app.state.history_store
    if not history_store:
        return {"history": [], "message": "DB 미연결"}
    history = await history_store.list_history(
        agent_name=agent_name, session_id=session_id, limit=limit
    )
    return {"history": history, "count": len(history)}
