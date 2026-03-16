"""실행 이력 저장소 — 감사 로그."""

from __future__ import annotations

import json
import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS execution_history (
    id SERIAL PRIMARY KEY,
    trace_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    user_input TEXT DEFAULT '',
    result TEXT DEFAULT '',
    trace_data JSONB DEFAULT '{}',
    duration_ms FLOAT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_history_session ON execution_history(session_id);
CREATE INDEX IF NOT EXISTS idx_history_agent ON execution_history(agent_name);
"""


class HistoryStore:
    """실행 이력 저장 — 누가, 언제, 무엇을 실행했는지."""

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._database_url, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await conn.execute(CREATE_TABLE_SQL)
        logger.info("HistoryStore 초기화 완료")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def record(
        self,
        trace_id: str,
        session_id: str,
        agent_name: str,
        user_input: str,
        result: str,
        trace_data: dict[str, Any] | None = None,
        duration_ms: float = 0,
        status: str = "completed",
    ) -> None:
        """실행 이력 한 건 저장."""
        if not self._pool:
            raise RuntimeError("HistoryStore 미초기화")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO execution_history
                    (trace_id, session_id, agent_name, user_input, result, trace_data, duration_ms, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                trace_id,
                session_id,
                agent_name,
                user_input,
                result,
                json.dumps(trace_data or {}, ensure_ascii=False, default=str),
                duration_ms,
                status,
            )

    async def list_history(
        self,
        agent_name: str | None = None,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """이력 조회."""
        if not self._pool:
            raise RuntimeError("HistoryStore 미초기화")

        query = "SELECT * FROM execution_history WHERE 1=1"
        params: list[Any] = []

        if agent_name:
            params.append(agent_name)
            query += f" AND agent_name = ${len(params)}"
        if session_id:
            params.append(session_id)
            query += f" AND session_id = ${len(params)}"

        params.append(limit)
        query += f" ORDER BY created_at DESC LIMIT ${len(params)}"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
