"""에이전트 관리 도구 — 메타 에이전트가 다른 에이전트를 생성/조회/수정할 때 사용."""

from __future__ import annotations

import json
import logging
from typing import Any

from src.tools.decorator import tool

logger = logging.getLogger(__name__)

# NOTE: 이 도구들은 Agent Core에서 직접 실행되지 않고,
# routes.py의 execute_stream에서 agent_store를 통해 실제 DB 작업을 수행한다.
# 여기서는 "도구 스키마"만 정의하고, 실제 실행은 _agent_mgmt_store에 위임.

_agent_store_ref = None  # app.py에서 주입
_tool_registry_ref = None


def set_agent_store(store):
    """app.py startup에서 AgentStore 참조를 주입."""
    global _agent_store_ref
    _agent_store_ref = store


def set_tool_registry(registry):
    """app.py startup에서 ToolRegistry 참조를 주입."""
    global _tool_registry_ref
    _tool_registry_ref = registry


@tool(
    name="create_agent",
    description=(
        "새로운 AI 에이전트를 생성하고 저장한다. "
        "에이전트 이름, 설명, 사용할 도구 목록, 시스템 프롬프트 등을 설정한다. "
        "이미 같은 이름의 에이전트가 있으면 업데이트한다. "
        "예: '고객 문의 에이전트를 만들어줘' → name='customer-support', tools=['db_query', 'http_request']"
    ),
    parameters={
        "name": {
            "type": "string",
            "description": "에이전트 이름 (영문 kebab-case 권장, 예: customer-support)",
        },
        "description": {
            "type": "string",
            "description": "에이전트가 하는 일에 대한 설명",
        },
        "tools": {
            "type": "array",
            "description": "사용할 도구 이름 목록 (예: ['db_query', 'http_request', 'file_read'])",
        },
        "system_prompt": {
            "type": "string",
            "description": "에이전트의 시스템 프롬프트 (역할, 행동 지침 등)",
        },
        "model": {
            "type": "string",
            "description": "사용할 LLM 모델 이름 (기본값: 현재 모델)",
            "optional": True,
        },
        "approval_required": {
            "type": "array",
            "description": "승인 필요 액션 패턴 목록 (예: ['DELETE *'])",
            "optional": True,
        },
    },
)
async def create_agent(
    name: str,
    description: str,
    tools: list[str] | None = None,
    system_prompt: str = "",
    model: str = "default",
    approval_required: list[str] | None = None,
) -> dict:
    if not _agent_store_ref:
        return {"status": "error", "error": "DB 미연결 — 에이전트를 저장할 수 없습니다"}

    agent_def = {
        "name": name,
        "description": description,
        "tools": tools or [],
        "system_prompt": system_prompt,
        "model": model,
        "approval_required": approval_required or [],
    }

    try:
        result = await _agent_store_ref.save(agent_def)
        return {
            "status": "success",
            "message": f"에이전트 '{name}' 생성 완료",
            "agent": agent_def,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@tool(
    name="list_agents",
    description=(
        "등록된 모든 에이전트 목록을 조회한다. "
        "각 에이전트의 이름, 설명, 사용 도구, 모델 등을 확인할 수 있다."
    ),
    parameters={},
)
async def list_agents_tool() -> dict:
    if not _agent_store_ref:
        return {"agents": [], "message": "DB 미연결"}

    try:
        agents = await _agent_store_ref.list_agents()
        return {
            "agents": [
                {
                    "name": a["name"],
                    "description": a["description"],
                    "model": a["model"],
                    "tools": a["tools"],
                    "created_at": a.get("created_at", ""),
                }
                for a in agents
            ],
            "count": len(agents),
        }
    except Exception as e:
        return {"agents": [], "error": str(e)}


@tool(
    name="get_agent",
    description=(
        "특정 에이전트의 상세 정보를 조회한다. "
        "시스템 프롬프트, 도구 목록, 승인 설정 등 전체 설정을 확인할 수 있다."
    ),
    parameters={
        "name": {
            "type": "string",
            "description": "조회할 에이전트 이름",
        },
    },
)
async def get_agent_tool(name: str) -> dict:
    if not _agent_store_ref:
        return {"status": "error", "error": "DB 미연결"}

    try:
        agent = await _agent_store_ref.load(name)
        if not agent:
            return {"status": "not_found", "message": f"에이전트 '{name}' 없음"}
        return {"status": "found", "agent": agent}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@tool(
    name="update_agent",
    description=(
        "기존 에이전트의 설정을 수정한다. "
        "도구 추가/제거, 시스템 프롬프트 변경, 모델 변경 등에 사용한다. "
        "변경하고 싶은 필드만 전달하면 된다."
    ),
    parameters={
        "name": {
            "type": "string",
            "description": "수정할 에이전트 이름",
        },
        "description": {
            "type": "string",
            "description": "새 설명 (변경 시에만)",
            "optional": True,
        },
        "tools": {
            "type": "array",
            "description": "새 도구 목록 (변경 시에만)",
            "optional": True,
        },
        "system_prompt": {
            "type": "string",
            "description": "새 시스템 프롬프트 (변경 시에만)",
            "optional": True,
        },
        "model": {
            "type": "string",
            "description": "새 모델 (변경 시에만)",
            "optional": True,
        },
    },
)
async def update_agent(
    name: str,
    description: str | None = None,
    tools: list[str] | None = None,
    system_prompt: str | None = None,
    model: str | None = None,
) -> dict:
    if not _agent_store_ref:
        return {"status": "error", "error": "DB 미연결"}

    try:
        existing = await _agent_store_ref.load(name)
        if not existing:
            return {"status": "not_found", "message": f"에이전트 '{name}' 없음"}

        # 변경된 필드만 업데이트
        if description is not None:
            existing["description"] = description
        if tools is not None:
            existing["tools"] = tools
        if system_prompt is not None:
            existing["system_prompt"] = system_prompt
        if model is not None:
            existing["model"] = model

        await _agent_store_ref.save(existing)
        return {
            "status": "success",
            "message": f"에이전트 '{name}' 수정 완료",
            "agent": existing,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@tool(
    name="delete_agent",
    description="에이전트를 삭제한다. 되돌릴 수 없으니 주의.",
    parameters={
        "name": {
            "type": "string",
            "description": "삭제할 에이전트 이름",
        },
    },
)
async def delete_agent_tool(name: str) -> dict:
    if not _agent_store_ref:
        return {"status": "error", "error": "DB 미연결"}

    try:
        deleted = await _agent_store_ref.delete(name)
        if deleted:
            return {"status": "success", "message": f"에이전트 '{name}' 삭제 완료"}
        return {"status": "not_found", "message": f"에이전트 '{name}' 없음"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@tool(
    name="list_available_tools",
    description=(
        "에이전트에 할당할 수 있는 사용 가능한 도구 전체 목록을 조회한다. "
        "도구 이름, 설명, 소스(builtin/custom/mcp)를 확인할 수 있다. "
        "에이전트를 만들 때 어떤 도구를 넣을지 결정하는 데 사용한다."
    ),
    parameters={},
)
async def list_available_tools() -> dict:
    if not _tool_registry_ref:
        return {"tools": [], "message": "ToolRegistry 미연결"}

    tools = []
    for name in _tool_registry_ref.list_names():
        spec = _tool_registry_ref.get(name)
        if spec:
            tools.append({
                "name": spec.name,
                "description": spec.description,
            })
    return {"tools": tools, "count": len(tools)}
