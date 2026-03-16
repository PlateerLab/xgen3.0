"""설정 관리 테스트."""

import os
from src.core.config import XgenConfig


def test_config_defaults():
    """기본값."""
    config = XgenConfig()
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.sandbox_timeout == 30
    assert config.sandbox_image == "python:3.12-slim"


def test_config_from_env(monkeypatch):
    """환경변수에서 로드."""
    monkeypatch.setenv("CORE_SERVICE_BASE_URL", "http://core:9000")
    monkeypatch.setenv("MODEL_BASE_URL", "http://model:5000/v1")
    monkeypatch.setenv("MODEL_NAME", "claude-sonnet")
    monkeypatch.setenv("DATABASE_URL", "postgresql://db:5432/xgen")
    monkeypatch.setenv("PORT", "9999")
    monkeypatch.setenv("SANDBOX_TIMEOUT", "60")

    config = XgenConfig.from_env()
    assert config.core_service_url == "http://core:9000"
    assert config.model_base_url == "http://model:5000/v1"
    assert config.model_name == "claude-sonnet"
    assert config.database_url == "postgresql://db:5432/xgen"
    assert config.port == 9999
    assert config.sandbox_timeout == 60
