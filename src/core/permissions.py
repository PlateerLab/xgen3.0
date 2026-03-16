"""권한 관리 — 역할별 도구 접근 제어."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Role(str, Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    USER = "user"
    VIEWER = "viewer"


@dataclass
class Permission:
    """도구 접근 권한."""

    tool_pattern: str  # 도구 이름 패턴 (예: "db_*", "mcp:*", "*")
    allowed_roles: list[Role]
    deny_roles: list[Role] = field(default_factory=list)


class PermissionManager:
    """역할 기반 도구 접근 제어.

    - ADMIN: 모든 도구 접근 가능
    - DEVELOPER: 대부분 도구 + 샌드박스
    - USER: 읽기 도구만
    - VIEWER: 조회만 (도구 실행 불가)
    """

    # 기본 권한 정책
    DEFAULT_POLICIES = [
        Permission(tool_pattern="*", allowed_roles=[Role.ADMIN]),
        Permission(
            tool_pattern="execute_code*",
            allowed_roles=[Role.ADMIN, Role.DEVELOPER],
        ),
        Permission(
            tool_pattern="db_query",
            allowed_roles=[Role.ADMIN, Role.DEVELOPER],
        ),
        Permission(
            tool_pattern="file_write",
            allowed_roles=[Role.ADMIN, Role.DEVELOPER],
        ),
        Permission(
            tool_pattern="file_read",
            allowed_roles=[Role.ADMIN, Role.DEVELOPER, Role.USER],
        ),
        Permission(
            tool_pattern="file_list",
            allowed_roles=[Role.ADMIN, Role.DEVELOPER, Role.USER],
        ),
        Permission(
            tool_pattern="http_request",
            allowed_roles=[Role.ADMIN, Role.DEVELOPER, Role.USER],
        ),
    ]

    def __init__(self, policies: list[Permission] | None = None):
        self._policies = policies or self.DEFAULT_POLICIES

    def check(self, tool_name: str, role: Role) -> bool:
        """도구 접근 가능 여부 확인.

        ADMIN은 항상 허용. 나머지는 정책 검사.
        """
        if role == Role.ADMIN:
            return True

        import fnmatch

        for policy in self._policies:
            if fnmatch.fnmatch(tool_name, policy.tool_pattern):
                if role in policy.deny_roles:
                    return False
                if role in policy.allowed_roles:
                    return True

        # 기본 거부
        return False

    def filter_tools(self, tool_names: list[str], role: Role) -> list[str]:
        """역할에 따라 사용 가능한 도구만 필터링."""
        return [name for name in tool_names if self.check(name, role)]

    def add_policy(self, policy: Permission) -> None:
        """정책 추가."""
        self._policies.append(policy)
