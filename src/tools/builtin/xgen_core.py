"""xgen-core API 연동 도구 — DB 조회/수정, Config 관리, 인증."""

from __future__ import annotations

import os
import httpx

from src.tools.decorator import tool

CORE_URL = os.environ.get("CORE_SERVICE_BASE_URL", "http://xgen-core:8000")
API_KEY = os.environ.get("XGEN_INTERNAL_API_KEY", "xgen-internal-key-2024")

_HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
}


async def _core_request(method: str, path: str, payload: dict | None = None) -> dict:
    """xgen-core 공통 HTTP 요청."""
    async with httpx.AsyncClient(timeout=60) as client:
        url = f"{CORE_URL}{path}"
        if method == "GET":
            resp = await client.get(url, headers=_HEADERS)
        else:
            resp = await client.post(url, headers=_HEADERS, json=payload or {})
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════
# DB 도구
# ═══════════════════════════════════════════════════

@tool(
    name="core_db_tables",
    description="xgen-core DB의 테이블 목록을 조회한다. 어떤 테이블이 있는지 모를 때 먼저 호출한다.",
    parameters={},
)
async def core_db_tables() -> dict:
    return await _core_request("GET", "/api/data/db/tables")


@tool(
    name="core_db_schema",
    description="xgen-core DB 테이블의 스키마(컬럼 이름, 타입, nullable 등)를 조회한다. 쿼리를 작성하기 전에 테이블 구조를 확인할 때 사용한다.",
    parameters={
        "table_name": {"type": "string", "description": "조회할 테이블 이름 (예: workflows, users)"},
    },
)
async def core_db_schema(table_name: str) -> dict:
    return await _core_request("POST", "/api/data/db/table/schema", {"table_name": table_name})


@tool(
    name="core_db_find",
    description="xgen-core DB에서 조건으로 레코드를 조회한다. conditions에 key=value 또는 key__like__=패턴, key__gte__=값 등 연산자를 사용할 수 있다. 연산자: __like__, __not__, __gte__, __lte__, __gt__, __lt__, __in__, __notin__",
    parameters={
        "table_name": {"type": "string", "description": "테이블 이름"},
        "conditions": {"type": "object", "description": "검색 조건 (예: {\"user_id\": 1, \"status__like__\": \"%active%\"})"},
        "limit": {"type": "integer", "description": "최대 반환 건수 (기본 50)", "optional": True},
        "offset": {"type": "integer", "description": "건너뛸 건수 (기본 0)", "optional": True},
        "orderby": {"type": "string", "description": "정렬 기준 컬럼 (기본 id)", "optional": True},
    },
)
async def core_db_find(
    table_name: str,
    conditions: dict | None = None,
    limit: int = 50,
    offset: int = 0,
    orderby: str = "id",
) -> dict:
    payload = {
        "table_name": table_name,
        "conditions": conditions or {},
        "limit": limit,
        "offset": offset,
        "orderby": orderby,
    }
    return await _core_request("POST", "/api/data/db/find-by-condition", payload)


@tool(
    name="core_db_find_by_id",
    description="xgen-core DB에서 특정 ID의 레코드 1건을 조회한다.",
    parameters={
        "table_name": {"type": "string", "description": "테이블 이름"},
        "record_id": {"type": "integer", "description": "레코드 ID"},
    },
)
async def core_db_find_by_id(table_name: str, record_id: int) -> dict:
    return await _core_request("POST", "/api/data/db/find-by-id", {
        "table_name": table_name,
        "record_id": record_id,
    })


@tool(
    name="core_db_insert",
    description="xgen-core DB 테이블에 새 레코드를 삽입한다.",
    parameters={
        "table_name": {"type": "string", "description": "테이블 이름"},
        "data": {"type": "object", "description": "삽입할 데이터 (예: {\"name\": \"홍길동\", \"email\": \"hong@test.com\"})"},
    },
)
async def core_db_insert(table_name: str, data: dict) -> dict:
    return await _core_request("POST", "/api/data/db/insert", {
        "table_name": table_name,
        "data": data,
    })


@tool(
    name="core_db_update",
    description="xgen-core DB 테이블의 레코드를 조건으로 업데이트한다.",
    parameters={
        "table_name": {"type": "string", "description": "테이블 이름"},
        "updates": {"type": "object", "description": "변경할 데이터 (예: {\"status\": \"active\"})"},
        "conditions": {"type": "object", "description": "대상 조건 (예: {\"id\": 1})"},
    },
)
async def core_db_update(table_name: str, updates: dict, conditions: dict) -> dict:
    return await _core_request("POST", "/api/data/db/update-by-condition", {
        "table_name": table_name,
        "updates": updates,
        "conditions": conditions,
    })


@tool(
    name="core_db_delete",
    description="xgen-core DB 테이블에서 조건에 맞는 레코드를 삭제한다. 주의: 삭제 후 복구 불가.",
    parameters={
        "table_name": {"type": "string", "description": "테이블 이름"},
        "conditions": {"type": "object", "description": "삭제 조건 (예: {\"id\": 1})"},
    },
)
async def core_db_delete(table_name: str, conditions: dict) -> dict:
    return await _core_request("POST", "/api/data/db/delete-by-condition", {
        "table_name": table_name,
        "conditions": conditions,
    })


@tool(
    name="core_db_query",
    description="xgen-core DB에 Raw SQL 쿼리를 실행한다. SELECT, INSERT, UPDATE, DELETE 모두 가능. 복잡한 JOIN이나 서브쿼리가 필요할 때 사용한다.",
    parameters={
        "query": {"type": "string", "description": "실행할 SQL 쿼리 (예: SELECT * FROM users WHERE id = $1)"},
        "params": {"type": "array", "description": "쿼리 파라미터 ($1, $2 등에 바인딩)", "optional": True},
    },
)
async def core_db_raw_query(query: str, params: list | None = None) -> dict:
    return await _core_request("POST", "/api/data/db/query", {
        "query": query,
        "params": params or [],
    })


# ═══════════════════════════════════════════════════
# Config 도구
# ═══════════════════════════════════════════════════

@tool(
    name="core_config_get",
    description="xgen-core 설정 값을 조회한다. 환경변수명(env_name)으로 검색한다.",
    parameters={
        "env_name": {"type": "string", "description": "설정 이름 (예: LLM_API_KEY, DEFAULT_MODEL)"},
        "default": {"type": "string", "description": "설정이 없을 때 기본값", "optional": True},
    },
)
async def core_config_get(env_name: str, default: str = "") -> dict:
    return await _core_request("POST", "/api/data/config/get-value", {
        "env_name": env_name,
        "default": default,
    })


@tool(
    name="core_config_set",
    description="xgen-core에 설정 값을 저장한다.",
    parameters={
        "env_name": {"type": "string", "description": "설정 이름"},
        "value": {"type": "string", "description": "설정 값"},
        "category": {"type": "string", "description": "설정 카테고리 (예: llm, system)", "optional": True},
    },
)
async def core_config_set(env_name: str, value: str, category: str = "general") -> dict:
    return await _core_request("POST", "/api/data/config/set", {
        "config_path": env_name,
        "config_value": value,
        "data_type": "string",
        "category": category,
        "env_name": env_name,
    })


@tool(
    name="core_config_list",
    description="xgen-core의 모든 설정 목록을 카테고리별로 요약 조회한다.",
    parameters={},
)
async def core_config_list() -> dict:
    return await _core_request("GET", "/api/data/config/summary")


@tool(
    name="core_config_search",
    description="xgen-core 설정을 패턴으로 검색한다. 설정 이름이 정확히 기억나지 않을 때 사용.",
    parameters={
        "pattern": {"type": "string", "description": "검색 패턴 (예: LLM, MODEL, API)"},
    },
)
async def core_config_search(pattern: str) -> dict:
    return await _core_request("POST", "/api/data/config/search", {"pattern": pattern})


# ═══════════════════════════════════════════════════
# 인증 (Session Station)
# ═══════════════════════════════════════════════════

@tool(
    name="core_auth_headers",
    description="외부 API 호출에 필요한 인증 헤더를 가져온다. auth_profile_id로 등록된 인증 프로필의 토큰/쿠키를 반환한다.",
    parameters={
        "auth_profile_id": {"type": "string", "description": "인증 프로필 ID (예: bo_mall, external_api)"},
        "user_id": {"type": "string", "description": "사용자 ID", "optional": True},
    },
)
async def core_auth_headers(auth_profile_id: str, user_id: str = "1") -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{CORE_URL}/api/session-station/v1/auth-context/{auth_profile_id}/headers",
            headers={"X-User-ID": user_id},
        )
        resp.raise_for_status()
        return resp.json()
