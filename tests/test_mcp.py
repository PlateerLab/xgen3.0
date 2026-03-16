"""MCP 클라이언트/브릿지 단위 테스트 (네트워크 호출 없이)."""

from src.mcp.client import MCPServerConfig, MCPTransport, MCPTool, MCPClient
from src.mcp.bridge import MCPBridge
from src.tools.registry import ToolRegistry


def test_mcp_server_config_sse():
    """SSE 설정 생성."""
    config = MCPServerConfig(
        name="slack",
        transport=MCPTransport.SSE,
        url="http://localhost:3000/sse",
    )
    assert config.transport == MCPTransport.SSE
    assert config.url == "http://localhost:3000/sse"


def test_mcp_server_config_stdio():
    """STDIO 설정 생성."""
    config = MCPServerConfig(
        name="local",
        transport=MCPTransport.STDIO,
        command="python",
        args=["-m", "my_mcp_server"],
    )
    assert config.transport == MCPTransport.STDIO
    assert config.command == "python"


def test_mcp_tool_structure():
    """MCPTool 구조."""
    tool = MCPTool(
        name="send_message",
        description="Slack 메시지 전송",
        input_schema={
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "채널"},
                "text": {"type": "string", "description": "메시지"},
            },
            "required": ["channel", "text"],
        },
        server_name="slack",
    )
    assert tool.name == "send_message"
    assert "channel" in tool.input_schema["properties"]


def test_mcp_bridge_to_spec():
    """MCPTool → ToolSpec 변환."""
    registry = ToolRegistry()
    bridge = MCPBridge(registry)

    mcp_tool = MCPTool(
        name="get_weather",
        description="날씨 조회",
        input_schema={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "도시"},
            },
            "required": ["city"],
        },
        server_name="weather-server",
    )

    # 더미 클라이언트
    config = MCPServerConfig(name="weather-server", transport=MCPTransport.SSE, url="http://fake")
    client = MCPClient(config)

    spec = bridge._mcp_to_spec("mcp:weather-server:get_weather", mcp_tool, client)

    assert spec.name == "mcp:weather-server:get_weather"
    assert "[MCP:weather-server]" in spec.description
    assert "city" in spec.parameters
    assert spec.is_async is True


def test_mcp_bridge_to_spec_optional_params():
    """optional 파라미터 변환."""
    registry = ToolRegistry()
    bridge = MCPBridge(registry)

    mcp_tool = MCPTool(
        name="search",
        description="검색",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색어"},
                "limit": {"type": "number", "description": "결과 수"},
            },
            "required": ["query"],  # limit은 optional
        },
        server_name="search-server",
    )

    config = MCPServerConfig(name="s", transport=MCPTransport.SSE, url="http://fake")
    client = MCPClient(config)

    spec = bridge._mcp_to_spec("mcp:s:search", mcp_tool, client)
    assert spec.parameters["query"].get("optional") is not True
    assert spec.parameters["limit"]["optional"] is True
