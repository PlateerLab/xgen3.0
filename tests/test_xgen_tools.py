"""xgen-core / xgen-documents @tool 래핑 테스트."""

import pytest
from src.tools.decorator import get_registered_tools
from src.tools.registry import ToolRegistry


@pytest.fixture(scope="module")
def registry():
    """모든 빌트인 도구를 로드한 레지스트리."""
    from src.tools.builtin import http, file, db  # noqa: F401
    from src.tools.builtin import xgen_core, xgen_documents  # noqa: F401
    from src.sandbox import runner  # noqa: F401

    reg = ToolRegistry()
    for spec in get_registered_tools():
        reg.register(spec)
    return reg


class TestToolRegistration:
    """도구가 올바르게 등록되는지 확인."""

    def test_total_tool_count(self, registry):
        assert len(registry.list_names()) >= 29

    def test_builtin_tools(self, registry):
        names = registry.list_names()
        for name in ["http_request", "file_read", "file_write", "file_list", "db_query"]:
            assert name in names

    def test_xgen_core_db_tools(self, registry):
        names = registry.list_names()
        for name in [
            "core_db_tables", "core_db_schema", "core_db_find",
            "core_db_find_by_id", "core_db_insert", "core_db_update",
            "core_db_delete", "core_db_query",
        ]:
            assert name in names

    def test_xgen_core_config_tools(self, registry):
        names = registry.list_names()
        for name in ["core_config_get", "core_config_set", "core_config_list", "core_config_search"]:
            assert name in names

    def test_xgen_core_auth_tool(self, registry):
        assert "core_auth_headers" in registry.list_names()

    def test_xgen_documents_rag_tools(self, registry):
        names = registry.list_names()
        for name in ["rag_search", "rag_collections", "rag_collection_documents"]:
            assert name in names

    def test_xgen_documents_embedding_tools(self, registry):
        names = registry.list_names()
        for name in ["embedding_query", "embedding_documents", "rerank_documents"]:
            assert name in names

    def test_xgen_documents_doc_tools(self, registry):
        names = registry.list_names()
        for name in ["document_extract_text", "document_generate_metadata", "document_supported_types"]:
            assert name in names

    def test_sandbox_tools(self, registry):
        names = registry.list_names()
        for name in ["execute_code", "execute_code_with_test"]:
            assert name in names


class TestToolSchema:
    """도구 스키마가 올바른지 확인."""

    def test_core_db_find_has_parameters(self, registry):
        spec = registry.get("core_db_find")
        assert spec is not None
        assert "table_name" in spec.parameters
        assert "conditions" in spec.parameters

    def test_rag_search_has_parameters(self, registry):
        spec = registry.get("rag_search")
        assert spec is not None
        assert "collection_id" in spec.parameters
        assert "query" in spec.parameters

    def test_all_tools_have_description(self, registry):
        for tool in registry.list_tools():
            assert tool.description, f"{tool.name}에 description이 없습니다"

    def test_openai_schema_format(self, registry):
        """모든 도구가 OpenAI function calling 형식으로 변환 가능한지."""
        for tool in registry.list_tools():
            schema = tool.to_openai_schema()
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]


class TestGraphToolIntegration:
    """graph-tool-call이 15개 초과 시 자동 활성화되는지."""

    def test_should_use_search(self, registry):
        from src.tools.graph_tool import GraphToolManager, GraphToolConfig

        config = GraphToolConfig()
        manager = GraphToolManager(config)
        manager.ingest_from_registry(registry)

        assert manager.tool_count >= 29
        assert manager.should_use_search

    def test_retrieve_relevant_tools(self, registry):
        from src.tools.graph_tool import GraphToolManager, GraphToolConfig

        config = GraphToolConfig(max_results=5)
        manager = GraphToolManager(config)
        manager.ingest_from_registry(registry)

        results = manager.retrieve("DB 테이블 조회")
        assert len(results) > 0
        tool_names = [r.name for r in results]
        # core_db 계열 도구가 상위에 나와야 함
        assert any("core_db" in name or "db" in name for name in tool_names)
