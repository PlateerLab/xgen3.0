"""xgen-agent CLI — import, run, serve 명령."""

from __future__ import annotations

import argparse
import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("xgen-agent")


def main():
    parser = argparse.ArgumentParser(
        prog="xgen-agent",
        description="XGEN 3.0 — 대화 기반 AI Agent Runtime",
    )
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령")

    # serve
    serve_parser = subparsers.add_parser("serve", help="API 서버 시작")
    serve_parser.add_argument("--host", default="0.0.0.0", help="바인드 호스트 (기본: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="포트 (기본: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="자동 리로드 (개발용)")

    # import
    import_parser = subparsers.add_parser("import", help="도구 파일/디렉토리 import")
    import_parser.add_argument("path", help="도구 파일 또는 디렉토리 경로")

    # tools
    subparsers.add_parser("tools", help="등록된 도구 목록 출력")

    # run
    run_parser = subparsers.add_parser("run", help="Agent 대화 실행 (CLI)")
    run_parser.add_argument("--agent", default="default", help="Agent 이름")
    run_parser.add_argument("--model-url", default=None, help="모델 API URL")
    run_parser.add_argument("message", nargs="?", help="실행할 메시지 (없으면 대화 모드)")

    # connect (Phase 3: MCP / graph-tool)
    connect_parser = subparsers.add_parser("connect", help="외부 도구 소스 연결")
    connect_sub = connect_parser.add_subparsers(dest="connect_type")

    mcp_parser = connect_sub.add_parser("mcp", help="MCP 서버 연결")
    mcp_parser.add_argument("--name", required=True, help="서버 이름")
    mcp_parser.add_argument("--url", help="SSE URL")
    mcp_parser.add_argument("--command", help="STDIO 명령")
    mcp_parser.add_argument("--transport", default="sse", choices=["sse", "stdio"])

    graph_parser = connect_sub.add_parser("graph-tool", help="graph-tool-call 소스 연결")
    graph_parser.add_argument("--source", required=True, help="OpenAPI 스펙 URL")
    graph_parser.add_argument("--name", default="default", help="소스 이름")

    args = parser.parse_args()

    if args.command == "serve":
        _cmd_serve(args)
    elif args.command == "import":
        _cmd_import(args)
    elif args.command == "tools":
        _cmd_tools()
    elif args.command == "run":
        asyncio.run(_cmd_run(args))
    elif args.command == "connect":
        asyncio.run(_cmd_connect(args))
    else:
        parser.print_help()


def _cmd_serve(args):
    """API 서버 시작."""
    import uvicorn

    logger.info("xgen-agent 서버 시작: %s:%d", args.host, args.port)
    uvicorn.run(
        "src.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def _cmd_import(args):
    """도구 파일/디렉토리 import."""
    from pathlib import Path
    from src.tools.registry import ToolRegistry

    registry = ToolRegistry()
    path = Path(args.path)

    if path.is_file():
        count = registry.load_from_file(path)
    elif path.is_dir():
        count = registry.load_from_directory(path)
    else:
        logger.error("경로가 존재하지 않습니다: %s", args.path)
        sys.exit(1)

    logger.info("도구 %d개 import 완료: %s", count, registry.list_names())


def _cmd_tools():
    """등록된 Built-in 도구 목록."""
    from src.tools.registry import ToolRegistry
    from src.tools.builtin import http, file, db  # noqa: F401
    from src.tools.builtin import xgen_core, xgen_documents  # noqa: F401
    from src.tools.builtin import xgen_utils  # noqa: F401
    from src.sandbox import runner  # noqa: F401
    from src.tools.decorator import get_registered_tools

    registry = ToolRegistry()
    for spec in get_registered_tools():
        registry.register(spec)

    tools = registry.list_tools()
    print(f"\n등록된 도구 ({len(tools)}개):\n")
    for t in tools:
        print(f"  - {t.name}: {t.description}")
    print()


async def _cmd_run(args):
    """Agent 대화 실행."""
    import os
    from src.core.agent import Agent
    from src.core.model_client import ModelClient
    from src.tools.registry import ToolRegistry
    from src.tools.builtin import http, file, db  # noqa: F401
    from src.tools.builtin import xgen_core, xgen_documents  # noqa: F401
    from src.tools.builtin import xgen_utils  # noqa: F401
    from src.sandbox import runner  # noqa: F401
    from src.tools.decorator import get_registered_tools

    registry = ToolRegistry()
    for spec in get_registered_tools():
        registry.register(spec)

    model_url = args.model_url or os.environ.get("MODEL_BASE_URL", "http://localhost:11434/v1")
    model_client = ModelClient(
        base_url=model_url,
        api_key=os.environ.get("MODEL_API_KEY", ""),
        model=os.environ.get("MODEL_NAME", "default"),
    )

    agent = Agent(
        name=args.agent,
        model_client=model_client,
        tool_registry=registry,
    )

    if args.message:
        # 단일 메시지 실행
        result = await agent.run(args.message)
        print(f"\n{result}\n")
    else:
        # 대화 모드
        print("xgen-agent 대화 모드 (종료: exit/quit)\n")
        while True:
            try:
                user_input = input("사용자> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user_input.lower() in ("exit", "quit", ""):
                break

            result = await agent.run(user_input)
            print(f"\nAgent> {result}\n")

    await model_client.close()


async def _cmd_connect(args):
    """외부 도구 소스 연결."""
    from src.tools.registry import ToolRegistry

    registry = ToolRegistry()

    if args.connect_type == "mcp":
        from src.mcp.client import MCPServerConfig, MCPTransport
        from src.mcp.bridge import MCPBridge

        bridge = MCPBridge(registry)
        config = MCPServerConfig(
            name=args.name,
            transport=MCPTransport(args.transport),
            url=args.url,
            command=args.command,
        )
        count = await bridge.connect(config)
        print(f"\nMCP 서버 '{args.name}' 연결 완료: {count}개 도구 등록")
        for name in registry.list_names():
            print(f"  - {name}")
        print()

    elif args.connect_type == "graph-tool":
        from src.tools.graph_tool import GraphToolLoader, GraphToolSource

        source = GraphToolSource(name=args.name, source_url=args.source)
        loader = GraphToolLoader(source)
        count = await loader.load_openapi_spec()
        print(f"\ngraph-tool-call: {count}개 도구 로드 완료 (소스: {args.source})")
        await loader.close()

    else:
        print("사용법: xgen-agent connect mcp --name ... --url ...")
        print("        xgen-agent connect graph-tool --source ...")


if __name__ == "__main__":
    main()
