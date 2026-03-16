"""Built-in 파일 처리 도구."""

from __future__ import annotations

from pathlib import Path

from src.tools.decorator import tool


@tool(
    name="file_read",
    description="파일 내용을 읽어 반환한다. 텍스트 파일을 UTF-8로 읽으며, 파일이 없으면 에러를 반환한다.",
    parameters={
        "path": {"type": "string", "description": "읽을 파일 경로 (예: /data/config.json)"},
        "encoding": {
            "type": "string",
            "description": "인코딩 (기본: utf-8)",
            "optional": True,
        },
    },
)
async def file_read(path: str, encoding: str = "utf-8") -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {"error": f"파일이 존재하지 않습니다: {path}"}
    if not file_path.is_file():
        return {"error": f"파일이 아닙니다: {path}"}

    content = file_path.read_text(encoding=encoding)
    return {
        "path": str(file_path),
        "content": content,
        "size": file_path.stat().st_size,
    }


@tool(
    name="file_write",
    description="파일에 내용을 쓴다. 기존 파일이 있으면 덮어쓰고, 없으면 새로 생성한다. 디렉토리가 없으면 자동 생성한다.",
    parameters={
        "path": {"type": "string", "description": "쓸 파일 경로"},
        "content": {"type": "string", "description": "파일에 쓸 내용"},
        "encoding": {
            "type": "string",
            "description": "인코딩 (기본: utf-8)",
            "optional": True,
        },
    },
)
async def file_write(path: str, content: str, encoding: str = "utf-8") -> dict:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding=encoding)
    return {
        "path": str(file_path),
        "size": file_path.stat().st_size,
        "status": "written",
    }


@tool(
    name="file_list",
    description="디렉토리 내 파일/폴더 목록을 반환한다. 패턴 필터링을 지원한다.",
    parameters={
        "path": {"type": "string", "description": "목록을 조회할 디렉토리 경로"},
        "pattern": {
            "type": "string",
            "description": "글로브 패턴 (예: *.py). 미지정 시 전체 목록",
            "optional": True,
        },
    },
)
async def file_list(path: str, pattern: str = "*") -> dict:
    dir_path = Path(path)
    if not dir_path.exists():
        return {"error": f"경로가 존재하지 않습니다: {path}"}
    if not dir_path.is_dir():
        return {"error": f"디렉토리가 아닙니다: {path}"}

    entries = []
    for item in sorted(dir_path.glob(pattern)):
        entries.append({
            "name": item.name,
            "path": str(item),
            "is_dir": item.is_dir(),
            "size": item.stat().st_size if item.is_file() else None,
        })
    return {"path": str(dir_path), "entries": entries, "count": len(entries)}
