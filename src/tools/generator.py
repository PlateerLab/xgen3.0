"""AI 도구 생성기 — LLM이 코드를 생성하고 샌드박스에서 테스트 후 등록."""

from __future__ import annotations

import logging
import re
import textwrap
import uuid
from pathlib import Path
from typing import Any

from src.core.model_client import ModelClient
from src.sandbox.docker import DockerSandbox, SandboxConfig
from src.tools.decorator import tool, ToolSpec
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

TOOL_GENERATION_PROMPT = """\
사용자가 요청한 도구를 Python 코드로 작성해줘.

**규칙:**
1. 반드시 `@tool` 데코레이터를 사용해야 한다
2. `from src.tools.decorator import tool` import 필수
3. async 함수여야 한다
4. description은 AI가 언제 이 도구를 사용할지 판단할 수 있도록 구체적으로 작성
5. 반환값은 dict 형태
6. 코드만 출력하고 설명은 하지 마

**예시:**
```python
from src.tools.decorator import tool

@tool(
    name="calculate_sum",
    description="두 숫자의 합을 계산한다. a와 b를 받아 합계를 반환한다.",
    parameters={
        "a": {"type": "number", "description": "첫 번째 숫자"},
        "b": {"type": "number", "description": "두 번째 숫자"},
    }
)
async def calculate_sum(a: float, b: float) -> dict:
    return {"sum": a + b}
```

**사용자 요청:**
{request}
"""


class ToolGenerator:
    """AI가 도구를 생성 → 테스트 → 등록하는 파이프라인.

    1. LLM에게 코드 생성 요청
    2. 샌드박스에서 문법/실행 테스트
    3. 통과하면 Tool Registry에 등록
    4. 도구 파일을 tools/ 디렉토리에 저장
    """

    def __init__(
        self,
        model_client: ModelClient,
        tool_registry: ToolRegistry,
        tools_dir: str | Path = "tools",
    ):
        self.model_client = model_client
        self.tool_registry = tool_registry
        self.tools_dir = Path(tools_dir)
        self.tools_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, request: str) -> dict[str, Any]:
        """사용자 요청에서 도구 생성.

        Returns:
            {"status": "success|failed", "name": "도구명", "code": "코드", ...}
        """
        # Step 1: LLM에게 코드 생성 요청
        code = await self._generate_code(request)
        if not code:
            return {"status": "failed", "error": "코드 생성 실패"}

        # Step 2: 코드에서 도구 이름 추출
        tool_name = self._extract_tool_name(code)
        if not tool_name:
            return {"status": "failed", "error": "도구 이름을 추출할 수 없음", "code": code}

        # Step 3: 샌드박스에서 문법 테스트
        test_result = await self._test_code(code)
        if not test_result["passed"]:
            return {
                "status": "failed",
                "error": "코드 테스트 실패",
                "code": code,
                "test_output": test_result,
            }

        # Step 4: 파일 저장
        file_path = self.tools_dir / f"{tool_name}.py"
        file_path.write_text(code, encoding="utf-8")

        # Step 5: Registry에 등록
        try:
            loaded = self.tool_registry.load_from_file(file_path)
            return {
                "status": "success",
                "name": tool_name,
                "code": code,
                "file": str(file_path),
                "loaded": loaded,
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": f"레지스트리 등록 실패: {e}",
                "code": code,
                "file": str(file_path),
            }

    async def _generate_code(self, request: str) -> str | None:
        """LLM에게 코드 생성 요청."""
        prompt = TOOL_GENERATION_PROMPT.format(request=request)

        response = await self.model_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        if not response.text:
            return None

        # 코드 블록 추출
        code = self._extract_code_block(response.text)
        return code

    async def _test_code(self, code: str) -> dict:
        """샌드박스에서 코드 문법 테스트.

        import 에러를 피하기 위해 decorator를 모킹해서 테스트.
        """
        test_wrapper = textwrap.dedent(f"""\
            # @tool 데코레이터 모킹 (샌드박스 환경에는 src가 없으므로)
            def tool(**kwargs):
                def decorator(fn):
                    fn._tool_spec = kwargs
                    return fn
                return decorator

            # src.tools.decorator를 모킹
            import types
            mock_module = types.ModuleType("src.tools.decorator")
            mock_module.tool = tool
            import sys
            sys.modules["src"] = types.ModuleType("src")
            sys.modules["src.tools"] = types.ModuleType("src.tools")
            sys.modules["src.tools.decorator"] = mock_module

            # 생성된 코드 실행
            {self._indent_code(code)}

            print("SYNTAX_OK")
        """)

        sandbox = DockerSandbox(SandboxConfig(timeout=15))
        result = await sandbox.execute(test_wrapper)

        return {
            "passed": result.success and "SYNTAX_OK" in result.stdout,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
        }

    def _extract_code_block(self, text: str) -> str:
        """마크다운 코드 블록에서 코드 추출."""
        # ```python ... ``` 패턴
        pattern = r"```(?:python)?\s*\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # 코드 블록이 없으면 전체 텍스트를 코드로 간주
        return text.strip()

    def _extract_tool_name(self, code: str) -> str | None:
        """코드에서 @tool(name="...") 추출."""
        match = re.search(r'@tool\([^)]*name\s*=\s*["\']([^"\']+)["\']', code)
        if match:
            return match.group(1)
        return None

    def _indent_code(self, code: str) -> str:
        """코드를 실행 가능한 형태로 유지 (들여쓰기 없이)."""
        # exec()로 실행
        escaped = code.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        return f'exec("""{escaped}""")'


# AI 도구 생성을 위한 빌트인 도구
@tool(
    name="create_tool",
    description="사용자의 자연어 설명을 바탕으로 새로운 도구(@tool)를 AI가 자동 생성한다. 코드를 생성하고 샌드박스에서 테스트한 뒤 Tool Registry에 등록한다. 예: '주문 내역을 조회하는 도구를 만들어줘'",
    parameters={
        "description": {
            "type": "string",
            "description": "만들고 싶은 도구에 대한 자연어 설명",
        },
    },
)
async def create_tool(description: str) -> dict:
    # NOTE: 실제 실행 시에는 Agent가 이 도구를 호출하면
    # ToolGenerator를 통해 코드 생성 → 테스트 → 등록 파이프라인이 실행됨.
    # 이 함수는 직접 호출되지 않고, Agent Core에서 특별 처리됨.
    return {
        "status": "pending",
        "message": f"도구 생성 요청: {description}",
        "note": "Agent Core에서 ToolGenerator를 통해 처리됩니다.",
    }
