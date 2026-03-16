"""Built-in DB 도구 — PostgreSQL 쿼리 실행."""

from __future__ import annotations

import os
import asyncpg

from src.tools.decorator import tool


@tool(
    name="db_query",
    description="PostgreSQL 데이터베이스에 SQL 쿼리를 실행한다. SELECT는 결과 행을, INSERT/UPDATE/DELETE는 영향받은 행 수를 반환한다. 기본적으로 환경변수 DATABASE_URL에 설정된 DB에 접속한다.",
    parameters={
        "query": {
            "type": "string",
            "description": "실행할 SQL 쿼리 (예: SELECT * FROM users WHERE id = $1)",
        },
        "params": {
            "type": "array",
            "description": "쿼리 파라미터 목록 ($1, $2, ... 바인딩). 없으면 빈 배열",
            "optional": True,
        },
        "database_url": {
            "type": "string",
            "description": "PostgreSQL 접속 URL (미지정 시 환경변수 DATABASE_URL 사용)",
            "optional": True,
        },
    },
)
async def db_query(
    query: str,
    params: list | None = None,
    database_url: str | None = None,
) -> dict:
    dsn = database_url or os.environ.get("DATABASE_URL", "")
    if not dsn:
        return {"error": "DATABASE_URL이 설정되지 않았습니다."}

    conn = await asyncpg.connect(dsn)
    try:
        query_upper = query.strip().upper()
        if query_upper.startswith("SELECT") or query_upper.startswith("WITH"):
            rows = await conn.fetch(query, *(params or []))
            return {
                "rows": [dict(row) for row in rows],
                "count": len(rows),
            }
        else:
            result = await conn.execute(query, *(params or []))
            return {"status": result}
    finally:
        await conn.close()
