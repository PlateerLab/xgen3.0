"""MCP → @tool 브릿지 — MCP 도구를 Tool Registry에 통합."""

from __future__ import annotations

import logging
from typing import Any

from src.mcp.client import MCPClient, MCPTool, MCPServerConfig, MCPTransport
from src.tools.decorator import ToolSpec
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPBridge:
    """MCP 서버 연결을 관리하고, 도구를 Tool Registry에 등록.

    MCP 도구 → ToolSpec 변환 → Registry에 등록
    → Agent Core가 MCP 도구도 일반 도구처럼 사용 가능
    """

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self._clients: dict[str, MCPClient] = {}

    async def connect(self, config: MCPServerConfig) -> int:
        """MCP 서버에 연결하고 도구를 Registry에 등록.

        Returns:
            등록된 도구 수.
        """
        client = MCPClient(config)
        await client.connect()

        self._clients[config.name] = client

        # MCP 도구를 ToolSpec으로 변환하여 Registry에 등록
        count = 0
        for full_name, mcp_tool in client.list_tools().items():
            spec = self._mcp_to_spec(full_name, mcp_tool, client)
            self.tool_registry.register(spec)
            count += 1

        logger.info(
            "MCP 서버 '%s' 연결 완료: %d 도구 등록", config.name, count
        )
        return count

    async def disconnect(self, server_name: str) -> None:
        """MCP 서버 연결 해제 및 도구 제거."""
        client = self._clients.pop(server_name, None)
        if not client:
            return

        # 해당 서버의 도구 Registry에서 제거
        for full_name in client.list_tools():
            self.tool_registry.unregister(full_name)

        await client.disconnect()
        logger.info("MCP 서버 '%s' 연결 해제", server_name)

    async def disconnect_all(self) -> None:
        """모든 MCP 서버 연결 해제."""
        for name in list(self._clients.keys()):
            await self.disconnect(name)

    def list_servers(self) -> list[dict]:
        """연결된 MCP 서버 목록."""
        return [
            {
                "name": name,
                "transport": client.config.transport.value,
                "url": client.config.url,
                "tools": list(client.list_tools().keys()),
            }
            for name, client in self._clients.items()
        ]

    def _mcp_to_spec(
        self, full_name: str, mcp_tool: MCPTool, client: MCPClient
    ) -> ToolSpec:
        """MCPTool → ToolSpec 변환."""
        # MCP input_schema를 xgen parameters 형식으로 변환
        parameters = {}
        schema_props = mcp_tool.input_schema.get("properties", {})
        required = mcp_tool.input_schema.get("required", [])

        for param_name, param_schema in schema_props.items():
            parameters[param_name] = {
                "type": param_schema.get("type", "string"),
                "description": param_schema.get("description", ""),
            }
            if param_name not in required:
                parameters[param_name]["optional"] = True

        # 도구 실행 함수 — 클로저로 client 캡처
        async def mcp_executor(**kwargs) -> dict:
            return await client.call_tool(full_name, kwargs)

        return ToolSpec(
            name=full_name,
            description=f"[MCP:{mcp_tool.server_name}] {mcp_tool.description}",
            parameters=parameters,
            fn=mcp_executor,
            is_async=True,
        )


async def connect_mcp_sse(
    tool_registry: ToolRegistry,
    name: str,
    url: str,
    headers: dict[str, str] | None = None,
) -> MCPBridge:
    """SSE MCP 서버에 간편 연결."""
    bridge = MCPBridge(tool_registry)
    config = MCPServerConfig(
        name=name,
        transport=MCPTransport.SSE,
        url=url,
        headers=headers or {},
    )
    await bridge.connect(config)
    return bridge


async def connect_mcp_stdio(
    tool_registry: ToolRegistry,
    name: str,
    command: str,
    args: list[str] | None = None,
) -> MCPBridge:
    """STDIO MCP 서버에 간편 연결."""
    bridge = MCPBridge(tool_registry)
    config = MCPServerConfig(
        name=name,
        transport=MCPTransport.STDIO,
        command=command,
        args=args or [],
    )
    await bridge.connect(config)
    return bridge
