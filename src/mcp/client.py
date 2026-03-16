"""MCP 클라이언트 — STDIO + SSE 프로토콜 지원.

MCP (Model Context Protocol) 서버에 연결하여
외부 도구를 xgen-agent의 Tool Registry에 통합한다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class MCPTransport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"


@dataclass
class MCPTool:
    """MCP 서버에서 제공하는 도구."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str  # 어떤 MCP 서버에서 왔는지


@dataclass
class MCPServerConfig:
    """MCP 서버 연결 설정."""

    name: str
    transport: MCPTransport
    # SSE
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    # STDIO
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


class MCPClient:
    """MCP 서버에 연결하여 도구를 조회하고 실행하는 클라이언트.

    지원 프로토콜:
    - SSE: HTTP SSE 기반 MCP 서버 (xgen-mcp-station 등)
    - STDIO: 프로세스 기반 MCP 서버 (로컬 실행)
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._tools: dict[str, MCPTool] = {}
        self._http_client: httpx.AsyncClient | None = None
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    # ─── 연결 ───

    async def connect(self) -> None:
        """MCP 서버에 연결."""
        if self.config.transport == MCPTransport.SSE:
            await self._connect_sse()
        elif self.config.transport == MCPTransport.STDIO:
            await self._connect_stdio()

    async def disconnect(self) -> None:
        """연결 해제."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None

    # ─── SSE ───

    async def _connect_sse(self) -> None:
        """SSE 기반 MCP 서버 연결."""
        if not self.config.url:
            raise ValueError("SSE 연결에 URL이 필요합니다.")

        self._http_client = httpx.AsyncClient(
            base_url=self.config.url,
            headers=self.config.headers,
            timeout=30.0,
        )

        # 초기화: tools/list 호출
        await self._discover_tools_sse()
        logger.info(
            "MCP SSE 연결 완료: %s (%d 도구)",
            self.config.name,
            len(self._tools),
        )

    async def _discover_tools_sse(self) -> None:
        """SSE 서버에서 사용 가능한 도구 목록 조회."""
        if not self._http_client:
            return

        # JSON-RPC 형식 요청
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
        }

        try:
            resp = await self._http_client.post("/", json=payload)
            resp.raise_for_status()
            data = resp.json()

            tools = data.get("result", {}).get("tools", [])
            for t in tools:
                mcp_tool = MCPTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                    server_name=self.config.name,
                )
                self._tools[f"mcp:{self.config.name}:{t['name']}"] = mcp_tool

        except Exception as e:
            logger.error("MCP 도구 목록 조회 실패 (%s): %s", self.config.name, e)

    async def call_tool_sse(self, tool_name: str, arguments: dict) -> dict:
        """SSE 서버에서 도구 실행."""
        if not self._http_client:
            return {"error": "MCP 서버 미연결"}

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        try:
            resp = await self._http_client.post("/", json=payload)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                return {"error": data["error"]}
            return data.get("result", {})

        except Exception as e:
            return {"error": f"MCP 도구 호출 실패: {e}"}

    # ─── STDIO ───

    async def _connect_stdio(self) -> None:
        """STDIO 기반 MCP 서버 연결 (프로세스 시작)."""
        if not self.config.command:
            raise ValueError("STDIO 연결에 command가 필요합니다.")

        env = {**self.config.env} if self.config.env else None

        self._process = await asyncio.create_subprocess_exec(
            self.config.command,
            *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # 초기화
        await self._send_stdio({"jsonrpc": "2.0", "id": self._next_id(), "method": "initialize"})
        await self._discover_tools_stdio()
        logger.info(
            "MCP STDIO 연결 완료: %s (%d 도구)",
            self.config.name,
            len(self._tools),
        )

    async def _send_stdio(self, payload: dict) -> dict | None:
        """STDIO로 JSON-RPC 요청 전송."""
        if not self._process or not self._process.stdin or not self._process.stdout:
            return None

        line = json.dumps(payload) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

        # 응답 읽기
        try:
            resp_line = await asyncio.wait_for(
                self._process.stdout.readline(), timeout=10.0
            )
            if resp_line:
                return json.loads(resp_line.decode())
        except asyncio.TimeoutError:
            logger.warning("STDIO 응답 타임아웃: %s", self.config.name)
        return None

    async def _discover_tools_stdio(self) -> None:
        """STDIO 서버에서 도구 목록 조회."""
        resp = await self._send_stdio({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
        })

        if not resp:
            return

        tools = resp.get("result", {}).get("tools", [])
        for t in tools:
            mcp_tool = MCPTool(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
                server_name=self.config.name,
            )
            self._tools[f"mcp:{self.config.name}:{t['name']}"] = mcp_tool

    async def call_tool_stdio(self, tool_name: str, arguments: dict) -> dict:
        """STDIO 서버에서 도구 실행."""
        resp = await self._send_stdio({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        })

        if not resp:
            return {"error": "STDIO 응답 없음"}
        if "error" in resp:
            return {"error": resp["error"]}
        return resp.get("result", {})

    # ─── 공통 API ───

    async def call_tool(self, full_name: str, arguments: dict) -> dict:
        """도구 실행 (transport에 따라 SSE/STDIO 분기).

        full_name: "mcp:server_name:tool_name" 형식
        """
        # full_name에서 실제 도구 이름 추출
        parts = full_name.split(":")
        tool_name = parts[-1] if len(parts) >= 3 else full_name

        if self.config.transport == MCPTransport.SSE:
            return await self.call_tool_sse(tool_name, arguments)
        elif self.config.transport == MCPTransport.STDIO:
            return await self.call_tool_stdio(tool_name, arguments)
        return {"error": f"미지원 transport: {self.config.transport}"}

    def list_tools(self) -> dict[str, MCPTool]:
        """이 서버의 도구 목록."""
        return dict(self._tools)
