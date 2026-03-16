"""Agent 버전 관리 — Agent 정의의 변경 이력 추적."""

from __future__ import annotations

import json
import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_versions (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    definition JSONB NOT NULL,
    change_note TEXT DEFAULT '',
    created_by VARCHAR(255) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_name, version)
);
CREATE INDEX IF NOT EXISTS idx_versions_agent ON agent_versions(agent_name);
"""


class VersionStore:
    """Agent 정의 버전 관리.

    - save_version(): 현재 정의를 새 버전으로 저장
    - list_versions(): 버전 이력 조회
    - load_version(): 특정 버전 로드
    - rollback(): 이전 버전으로 롤백
    """

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._database_url, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await conn.execute(CREATE_TABLE_SQL)
        logger.info("VersionStore 초기화 완료")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def save_version(
        self,
        agent_name: str,
        definition: dict[str, Any],
        change_note: str = "",
        created_by: str = "system",
    ) -> int:
        """새 버전 저장. 버전 번호 반환."""
        if not self._pool:
            raise RuntimeError("VersionStore 미초기화")

        async with self._pool.acquire() as conn:
            # 최신 버전 번호 조회
            latest = await conn.fetchval(
                "SELECT COALESCE(MAX(version), 0) FROM agent_versions WHERE agent_name = $1",
                agent_name,
            )
            new_version = latest + 1

            await conn.execute(
                """
                INSERT INTO agent_versions (agent_name, version, definition, change_note, created_by)
                VALUES ($1, $2, $3, $4, $5)
                """,
                agent_name,
                new_version,
                json.dumps(definition, ensure_ascii=False),
                change_note,
                created_by,
            )

        logger.info("Agent '%s' v%d 저장", agent_name, new_version)
        return new_version

    async def list_versions(self, agent_name: str) -> list[dict]:
        """버전 이력 조회."""
        if not self._pool:
            raise RuntimeError("VersionStore 미초기화")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT version, change_note, created_by, created_at
                FROM agent_versions
                WHERE agent_name = $1
                ORDER BY version DESC
                """,
                agent_name,
            )
        return [
            {
                "version": row["version"],
                "change_note": row["change_note"],
                "created_by": row["created_by"],
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    async def load_version(self, agent_name: str, version: int) -> dict[str, Any] | None:
        """특정 버전 로드."""
        if not self._pool:
            raise RuntimeError("VersionStore 미초기화")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT definition FROM agent_versions WHERE agent_name = $1 AND version = $2",
                agent_name,
                version,
            )
        if not row:
            return None
        return json.loads(row["definition"]) if isinstance(row["definition"], str) else row["definition"]

    async def get_latest_version(self, agent_name: str) -> int:
        """최신 버전 번호."""
        if not self._pool:
            raise RuntimeError("VersionStore 미초기화")

        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COALESCE(MAX(version), 0) FROM agent_versions WHERE agent_name = $1",
                agent_name,
            )
