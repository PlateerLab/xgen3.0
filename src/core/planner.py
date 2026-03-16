"""실행 계획 수립 — Phase 1에서는 단순 패스스루."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Plan:
    """실행 계획."""

    steps: list[str]
    metadata: dict[str, Any] | None = None


class Planner:
    """Phase 1: 별도 계획 수립 없이 LLM에 직접 위임.

    Phase 2+에서 복잡한 계획 수립 로직 추가 가능.
    """

    async def create_plan(self, user_input: str, available_tools: list[str]) -> Plan | None:
        """현재는 None 반환 — LLM이 자체 판단."""
        return None
