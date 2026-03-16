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
    from src.sandbox import runner  # noqa: F401 — execute_code, execute_code_with_test
    from src.tools.decorator import get_registered_tools

    for spec in get_registered_tools():
        tool_registry.register(spec)

    logging.getLogger(__name__).info(
        "Built-in 도구 %d개 로드: %s", len(tool_registry.list_names()), tool_registry.list_names()
    )

    # DB Store 초기화 (DATABASE_URL이 있을 때만)
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        agent_store = AgentStore(database_url)
        state_store = StateStore(database_url)
        history_store = HistoryStore(database_url)
        await agent_store.initialize()
        await state_store.initialize()
        await history_store.initialize()
        logging.getLogger(__name__).info("DB Store 초기화 완료")

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
