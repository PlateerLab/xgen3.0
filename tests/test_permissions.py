"""권한 관리 테스트."""

from src.core.permissions import PermissionManager, Role, Permission


def test_admin_access_all():
    """ADMIN은 모든 도구 접근 가능."""
    mgr = PermissionManager()
    assert mgr.check("execute_code", Role.ADMIN) is True
    assert mgr.check("db_query", Role.ADMIN) is True
    assert mgr.check("some_random_tool", Role.ADMIN) is True


def test_developer_access():
    """DEVELOPER 권한 범위."""
    mgr = PermissionManager()
    assert mgr.check("execute_code", Role.DEVELOPER) is True
    assert mgr.check("db_query", Role.DEVELOPER) is True
    assert mgr.check("file_read", Role.DEVELOPER) is True
    assert mgr.check("file_write", Role.DEVELOPER) is True


def test_user_access():
    """USER 권한 — 읽기만."""
    mgr = PermissionManager()
    assert mgr.check("file_read", Role.USER) is True
    assert mgr.check("http_request", Role.USER) is True
    assert mgr.check("execute_code", Role.USER) is False
    assert mgr.check("db_query", Role.USER) is False


def test_viewer_access():
    """VIEWER — 기본 거부."""
    mgr = PermissionManager()
    assert mgr.check("file_read", Role.VIEWER) is False
    assert mgr.check("execute_code", Role.VIEWER) is False


def test_filter_tools():
    """역할별 도구 필터링."""
    mgr = PermissionManager()
    all_tools = ["execute_code", "db_query", "file_read", "http_request", "file_write"]

    admin_tools = mgr.filter_tools(all_tools, Role.ADMIN)
    assert len(admin_tools) == 5

    user_tools = mgr.filter_tools(all_tools, Role.USER)
    assert "file_read" in user_tools
    assert "http_request" in user_tools
    assert "execute_code" not in user_tools


def test_custom_policy():
    """커스텀 정책 추가."""
    mgr = PermissionManager()
    mgr.add_policy(Permission(
        tool_pattern="custom_*",
        allowed_roles=[Role.USER, Role.DEVELOPER],
    ))
    assert mgr.check("custom_tool", Role.USER) is True
    assert mgr.check("custom_other", Role.DEVELOPER) is True
