"""전역 설정 관리."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class XgenConfig:
    """환경변수 기반 설정."""

    # 서비스 연동
    core_service_url: str = ""
    documents_service_url: str = ""
    mcp_station_url: str = ""

    # 모델
    model_base_url: str = ""
    model_api_key: str = ""
    model_name: str = "default"

    # DB
    database_url: str = ""

    # 서버
    host: str = "0.0.0.0"
    port: int = 8000

    # 샌드박스
    sandbox_image: str = "python:3.12-slim"
    sandbox_timeout: int = 30
    sandbox_memory: str = "256m"

    @classmethod
    def from_env(cls) -> XgenConfig:
        """환경변수에서 설정 로드."""
        return cls(
            core_service_url=os.environ.get("CORE_SERVICE_BASE_URL", "http://xgen-core:8000"),
            documents_service_url=os.environ.get("DOCUMENTS_SERVICE_BASE_URL", "http://xgen-documents:8000"),
            mcp_station_url=os.environ.get("MCP_STATION_BASE_URL", "http://xgen-mcp-station:8000"),
            model_base_url=os.environ.get("MODEL_BASE_URL", "http://localhost:11434/v1"),
            model_api_key=os.environ.get("MODEL_API_KEY", ""),
            model_name=os.environ.get("MODEL_NAME", "default"),
            database_url=os.environ.get("DATABASE_URL", ""),
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "8000")),
            sandbox_image=os.environ.get("SANDBOX_IMAGE", "python:3.12-slim"),
            sandbox_timeout=int(os.environ.get("SANDBOX_TIMEOUT", "30")),
            sandbox_memory=os.environ.get("SANDBOX_MEMORY", "256m"),
        )
