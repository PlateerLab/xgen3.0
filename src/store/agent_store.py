"""Agent 정의 저장소 — YAML 기반 agent 정의 CRUD."""

from __future__ import annotations

import json
import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    model VARCHAR(100) DEFAULT 'default',
    tools JSONB DEFAULT '[]',
    system_prompt TEXT DEFAULT '',
    approval_required JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""


class AgentStore:
    """Agent 정의 CRUD — PostgreSQL."""

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._database_url, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await conn.execute(CREATE_TABLE_SQL)
        logger.info("AgentStore 초기화 완료")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def save(self, agent_def: dict[str, Any]) -> dict:
        """Agent 정의 저장 (upsert)."""
        if not self._pool:
            raise RuntimeError("AgentStore 미초기화")

        name = agent_def["name"]
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_definitions (name, description, model, tools, system_prompt, approval_required, config)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    model = EXCLUDED.model,
                    tools = EXCLUDED.tools,
                    system_prompt = EXCLUDED.system_prompt,
                    approval_required = EXCLUDED.approval_required,
                    config = EXCLUDED.config,
                    updated_at = NOW()
                """,
                name,
                agent_def.get("description", ""),
                agent_def.get("model", "default"),
                json.dumps(agent_def.get("tools", []), ensure_ascii=False),
                agent_def.get("system_prompt", ""),
                json.dumps(agent_def.get("approval_required", []), ensure_ascii=False),
                json.dumps(agent_def.get("config", {}), ensure_ascii=False),
            )
        return {"name": name, "status": "saved"}

    async def load(self, name: str) -> dict[str, Any] | None:
        """Agent 정의 로드."""
        if not self._pool:
            raise RuntimeError("AgentStore 미초기화")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_definitions WHERE name = $1", name
            )
        if not row:
            return None
        return self._row_to_dict(row)

    async def list_agents(self) -> list[dict]:
        """등록된 Agent 목록."""
        if not self._pool:
            raise RuntimeError("AgentStore 미초기화")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM agent_definitions ORDER BY updated_at DESC"
            )
        return [self._row_to_dict(row) for row in rows]

    async def delete(self, name: str) -> bool:
        """Agent 삭제."""
        if not self._pool:
            raise RuntimeError("AgentStore 미초기화")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM agent_definitions WHERE name = $1", name
            )
        return result != "DELETE 0"

    def _row_to_dict(self, row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "model": row["model"],
            "tools": json.loads(row["tools"]) if isinstance(row["tools"], str) else row["tools"],
            "system_prompt": row["system_prompt"],
            "approval_required": (
                json.loads(row["approval_required"])
                if isinstance(row["approval_required"], str)
                else row["approval_required"]
            ),
            "config": json.loads(row["config"]) if isinstance(row["config"], str) else row["config"],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }
