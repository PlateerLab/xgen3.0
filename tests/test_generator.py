"""AI 도구 생성기 단위 테스트 (네트워크 없이)."""

from src.tools.generator import ToolGenerator
from src.tools.registry import ToolRegistry
from src.core.model_client import ModelClient


def _make_generator():
    client = ModelClient(base_url="http://fake", model="test")
    registry = ToolRegistry()
    return ToolGenerator(client, registry, tools_dir="tools")


def test_extract_code_block():
    """마크다운 코드 블록 추출."""
    gen = _make_generator()

    text = '''여기 코드입니다:
```python
print("hello")
```
끝.'''
    assert gen._extract_code_block(text) == 'print("hello")'


def test_extract_code_block_no_language():
    """언어 표시 없는 코드 블록."""
    gen = _make_generator()

    text = '''```
x = 1 + 2
```'''
    assert gen._extract_code_block(text) == "x = 1 + 2"


def test_extract_code_block_plain_text():
    """코드 블록이 없으면 전체 텍스트 반환."""
    gen = _make_generator()
    assert gen._extract_code_block("just plain code") == "just plain code"


def test_extract_tool_name():
    """@tool(name=...) 추출."""
    gen = _make_generator()

    code = '''
from src.tools.decorator import tool

@tool(
    name="my_tool",
    description="테스트",
    parameters={}
)
async def my_tool():
    pass
'''
    assert gen._extract_tool_name(code) == "my_tool"


def test_extract_tool_name_single_quotes():
    """작은따옴표 name."""
    gen = _make_generator()
    code = "@tool(name='another_tool', description='설명')"
    assert gen._extract_tool_name(code) == "another_tool"


def test_extract_tool_name_not_found():
    """@tool이 없는 코드."""
    gen = _make_generator()
    assert gen._extract_tool_name("def hello(): pass") is None
