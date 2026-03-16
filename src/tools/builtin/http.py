"""Built-in HTTP 도구."""

from __future__ import annotations

import httpx

from src.tools.decorator import tool


@tool(
    name="http_request",
    description="HTTP 요청을 보낸다. GET, POST, PUT, DELETE 등을 지원하며, URL과 메서드를 지정하고 선택적으로 헤더와 바디를 포함할 수 있다.",
    parameters={
        "method": {
            "type": "string",
            "description": "HTTP 메서드 (GET, POST, PUT, DELETE, PATCH)",
            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
        },
        "url": {"type": "string", "description": "요청할 URL (예: https://api.example.com/data)"},
        "headers": {
            "type": "object",
            "description": "요청 헤더 (선택사항)",
            "optional": True,
        },
        "body": {
            "type": "object",
            "description": "요청 바디 — JSON 형식 (선택사항, POST/PUT/PATCH에서 사용)",
            "optional": True,
        },
        "timeout": {
            "type": "number",
            "description": "타임아웃 초 (기본 30초)",
            "optional": True,
        },
    },
)
async def http_request(
    method: str,
    url: str,
    headers: dict | None = None,
    body: dict | None = None,
    timeout: float = 30.0,
) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=body if body else None,
        )
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
        }
