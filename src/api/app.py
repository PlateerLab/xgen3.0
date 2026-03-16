"""FastAPI 앱 진입점."""

from __future__ import annotations

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.routes import router
from src.tools.registry import ToolRegistry
from src.store.agent_store import AgentStore
from src.store.state import StateStore
from src.store.history import HistoryStore
from src.trace.collector import TraceCollector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# 전역 인스턴스
tool_registry = ToolRegistry()
trace_collector = TraceCollector()
agent_store: AgentStore | None = None
state_store: StateStore | None = None
history_store: HistoryStore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 리소스 관리."""
    global agent_store, state_store, history_store

    # Built-in 도구 로드 (Phase 1 + Phase 2 sandbox)
    from src.tools.builtin import http, file, db  # noqa: F401
    from src.tools.builtin import xgen_core, xgen_documents  # noqa: F401
    from src.tools.builtin import xgen_utils  # noqa: F401
    from src.tools.builtin import agent_mgmt  # noqa: F401 — 에이전트 관리 도구
    from src.sandbox import runner  # noqa: F401 — execute_code, execute_code_with_test
    from src.tools.decorator import get_registered_tools

    for spec in get_registered_tools():
        tool_registry.register(spec)

    logging.getLogger(__name__).info(
        "Built-in 도구 %d개 로드: %s", len(tool_registry.list_names()), tool_registry.list_names()
    )

    # MCP 자동 연결 (MCP_STATION_BASE_URL이 설정된 경우)
    mcp_station_url = os.environ.get("MCP_STATION_BASE_URL", "")
    if mcp_station_url:
        await _auto_connect_mcp(app, mcp_station_url)

    # DB Store 초기화 (DATABASE_URL이 있을 때만)
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        agent_store = AgentStore(database_url)
        state_store = StateStore(database_url)
        history_store = HistoryStore(database_url)
        await agent_store.initialize()
        await state_store.initialize()
        await history_store.initialize()
        # 에이전트 관리 도구에 store 참조 주입
        from src.tools.builtin.agent_mgmt import set_agent_store
        set_agent_store(agent_store)
        logging.getLogger(__name__).info("DB Store 초기화 완료")

    # 에이전트 관리 도구에 tool_registry 주입 (DB 유무와 무관)
    from src.tools.builtin.agent_mgmt import set_tool_registry
    set_tool_registry(tool_registry)

    # 앱 state에 등록
    app.state.tool_registry = tool_registry
    app.state.trace_collector = trace_collector
    app.state.agent_store = agent_store
    app.state.state_store = state_store
    app.state.history_store = history_store

    yield

    # 종료
    if agent_store:
        await agent_store.close()
    if state_store:
        await state_store.close()
    if history_store:
        await history_store.close()


async def _auto_connect_mcp(app: FastAPI, mcp_station_url: str):
    """MCP Station에서 사용 가능한 MCP 서버 목록을 가져와 자동 연결."""
    _logger = logging.getLogger(__name__)
    try:
        import httpx
        from src.mcp.client import MCPServerConfig, MCPTransport
        from src.mcp.bridge import MCPBridge

        bridge = MCPBridge(tool_registry)
        app.state.mcp_bridge = bridge

        # MCP Station에서 서버 목록 조회
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{mcp_station_url}/api/mcp/servers")
            if resp.status_code != 200:
                _logger.warning("MCP Station 응답 실패 (%d), 건너뜀", resp.status_code)
                return
            servers = resp.json().get("servers", [])

        if not servers:
            # 서버 목록 없으면 SSE로 직접 연결 시도
            _logger.info("MCP Station에서 서버 목록 없음, SSE 직접 연결 시도: %s", mcp_station_url)
            try:
                config = MCPServerConfig(
                    name="mcp-station",
                    transport=MCPTransport.SSE,
                    url=f"{mcp_station_url}/sse",
                )
                count = await bridge.connect(config)
                _logger.info("MCP Station SSE 연결 완료: %d개 도구", count)
            except Exception as e:
                _logger.warning("MCP Station SSE 연결 실패: %s", e)
            return

        # 각 서버에 연결
        total_tools = 0
        for server in servers:
            name = server.get("name", "unknown")
            url = server.get("url") or server.get("sse_url")
            if not url:
                continue
            try:
                config = MCPServerConfig(
                    name=name,
                    transport=MCPTransport.SSE,
                    url=url,
                )
                count = await bridge.connect(config)
                total_tools += count
                _logger.info("MCP 서버 '%s' 연결: %d개 도구", name, count)
            except Exception as e:
                _logger.warning("MCP 서버 '%s' 연결 실패: %s", name, e)

        _logger.info("MCP 자동 연결 완료: %d개 서버, %d개 도구", len(servers), total_tools)
    except Exception as e:
        _logger.warning("MCP 자동 연결 중 오류 (무시): %s", e)


app = FastAPI(
    title="xgen-agent",
    description="XGEN 3.0 — 대화 기반 AI Agent Runtime",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
