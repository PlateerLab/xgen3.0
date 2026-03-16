"""API 요청/응답 모델 — xgen-workflow 호환."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ─── 실행 요청 (xgen-workflow 호환) ───

class WorkflowRequest(BaseModel):
    """워크플로우/에이전트 실행 요청 — xgen-workflow와 동일한 필드."""

    workflow_name: str = ""
    workflow_id: str = ""
    input_data: str | dict[str, Any] | list[dict[str, Any]] | None = None
    interaction_id: str | None = "default"
    selected_collections: list[str] | None = None
    selected_files: list[str | dict[str, Any]] | None = None
    user_id: int | str | None = None
    additional_params: dict[str, dict[str, Any]] | None = None
    bypass_agents: list[str] | None = None
    include_logs: bool = True
    include_node_status: bool = True
    include_tool_events: bool = True
    response_format: str = "json"  # "json" | "stream"
    parallel_chat_code: str | None = None

    # xgen3.0 확장 필드
    system_prompt: str | None = None
    model: str | None = None
    resume: bool = False
    approval_required: list[str] | None = None

    @property
    def message(self) -> str:
        """input_data를 문자열 메시지로 변환."""
        if isinstance(self.input_data, str):
            return self.input_data
        if isinstance(self.input_data, dict):
            # dict에서 첫 번째 값 또는 전체를 문자열로
            if "message" in self.input_data:
                return str(self.input_data["message"])
            if "input" in self.input_data:
                return str(self.input_data["input"])
            return str(self.input_data)
        if isinstance(self.input_data, list):
            return str(self.input_data)
        return ""


# ─── 저장 요청 ───

class WorkflowData(BaseModel):
    """워크플로우 데이터 — 노드/엣지/뷰."""

    workflow_name: str = ""
    workflow_id: str = ""
    view: dict[str, Any] = Field(default_factory=dict)
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    interaction_id: str = "default"


class SaveWorkflowRequest(BaseModel):
    """워크플로우 저장 요청 — xgen-workflow 호환."""

    workflow_name: str
    workflow_id: str
    content: WorkflowData | dict[str, Any] | None = None
    user_id: int | str | None = None

    # xgen3.0 확장
    description: str = ""
    model: str = "default"
    tools: list[str] | None = None
    system_prompt: str = ""
    approval_required: list[str] | None = None
    config: dict[str, Any] | None = None


# ─── 승인 ───

class ApprovalActionRequest(BaseModel):
    request_id: str
    action: str  # "approve" | "reject"
    reason: str = ""


# ─── 도구 생성 ───

class GenerateToolRequest(BaseModel):
    description: str


# ─── Deploy 응답 ───

class DeployResponse(BaseModel):
    """Deploy API JSON 응답."""

    success: bool = True
    content: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class EnvelopeResponse(BaseModel):
    """Java Client용 Envelope 응답."""

    timestamp: str = ""
    code: str = "200"
    message: str = "Success"
    payload: dict[str, Any] = Field(default_factory=dict)
