"""xgen-documents API 연동 도구 — RAG 검색, 임베딩, 문서 처리."""

from __future__ import annotations

import os
import httpx

from src.tools.decorator import tool

DOCS_URL = os.environ.get("DOCUMENTS_SERVICE_BASE_URL", "http://xgen-documents:8000")

_HEADERS = {
    "Content-Type": "application/json",
    "X-User-ID": "1",
    "X-User-Name": "xgen-agent",
    "X-User-Admin": "true",
}


async def _docs_request(method: str, path: str, payload: dict | None = None) -> dict:
    """xgen-documents 공통 HTTP 요청."""
    async with httpx.AsyncClient(timeout=60) as client:
        url = f"{DOCS_URL}{path}"
        if method == "GET":
            resp = await client.get(url, headers=_HEADERS)
        else:
            resp = await client.post(url, headers=_HEADERS, json=payload or {})
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════
# RAG 검색
# ═══════════════════════════════════════════════════

@tool(
    name="rag_search",
    description="RAG 컬렉션에서 자연어로 문서를 검색한다. 벡터 유사도 + 키워드 하이브리드 검색을 지원한다. 질문에 답하기 위해 관련 문서를 찾을 때 사용한다.",
    parameters={
        "collection_id": {"type": "string", "description": "검색할 컬렉션 ID"},
        "query": {"type": "string", "description": "검색 쿼리 (자연어)"},
        "top_k": {"type": "integer", "description": "반환할 최대 결과 수 (기본 5)", "optional": True},
        "use_reranking": {"type": "boolean", "description": "Reranker로 결과 재정렬 (기본 true)", "optional": True},
        "hybrid_search": {"type": "boolean", "description": "하이브리드 검색 사용 (기본 true)", "optional": True},
    },
)
async def rag_search(
    collection_id: str,
    query: str,
    top_k: int = 5,
    use_reranking: bool = True,
    hybrid_search: bool = True,
) -> dict:
    return await _docs_request("POST", f"/api/retrieval/collections/{collection_id}/search", {
        "query": query,
        "top_k": top_k,
        "use_reranking": use_reranking,
        "hybrid_search": hybrid_search,
    })


@tool(
    name="rag_collections",
    description="RAG 컬렉션 목록을 조회한다. 어떤 문서 컬렉션이 있는지 확인할 때 사용한다.",
    parameters={},
)
async def rag_collections() -> dict:
    return await _docs_request("GET", "/api/retrieval/collections")


@tool(
    name="rag_collection_documents",
    description="특정 RAG 컬렉션에 포함된 문서 목록을 조회한다.",
    parameters={
        "collection_id": {"type": "string", "description": "컬렉션 ID"},
        "limit": {"type": "integer", "description": "최대 반환 건수 (기본 20)", "optional": True},
    },
)
async def rag_collection_documents(collection_id: str, limit: int = 20) -> dict:
    return await _docs_request("GET", f"/api/retrieval/collections/{collection_id}/documents?limit={limit}")


# ═══════════════════════════════════════════════════
# 임베딩
# ═══════════════════════════════════════════════════

@tool(
    name="embedding_query",
    description="텍스트를 벡터 임베딩으로 변환한다. 유사도 비교나 벡터 검색에 사용할 임베딩을 생성할 때 사용한다.",
    parameters={
        "text": {"type": "string", "description": "임베딩할 텍스트"},
    },
)
async def embedding_query(text: str) -> dict:
    return await _docs_request("POST", "/api/embedding/query-embedding", {"text": text})


@tool(
    name="embedding_documents",
    description="여러 문서 텍스트를 일괄 임베딩한다. 대량 문서를 벡터화할 때 사용한다.",
    parameters={
        "texts": {"type": "array", "description": "임베딩할 텍스트 배열"},
    },
)
async def embedding_documents(texts: list[str]) -> dict:
    return await _docs_request("POST", "/api/embedding/document-embeddings", {"texts": texts})


@tool(
    name="rerank_documents",
    description="쿼리와 문서 목록을 받아 관련성 순으로 재정렬한다. 검색 결과의 정밀도를 높일 때 사용한다.",
    parameters={
        "query": {"type": "string", "description": "기준 쿼리"},
        "documents": {"type": "array", "description": "재정렬할 문서 텍스트 배열"},
        "top_k": {"type": "integer", "description": "상위 K개만 반환 (기본 5)", "optional": True},
    },
)
async def rerank_documents(query: str, documents: list[str], top_k: int = 5) -> dict:
    return await _docs_request("POST", "/api/embedding/reranker/rerank", {
        "query": query,
        "documents": documents,
        "top_k": top_k,
    })


# ═══════════════════════════════════════════════════
# 문서 처리
# ═══════════════════════════════════════════════════

@tool(
    name="document_extract_text",
    description="파일에서 텍스트를 추출한다. PDF, DOCX, PPT, 이미지 등을 지원한다. MinIO에 저장된 파일 경로를 지정한다.",
    parameters={
        "minio_bucket": {"type": "string", "description": "MinIO 버킷 이름"},
        "minio_object_name": {"type": "string", "description": "MinIO 오브젝트 경로"},
        "file_extension": {"type": "string", "description": "파일 확장자 (예: pdf, docx, pptx)"},
    },
)
async def document_extract_text(minio_bucket: str, minio_object_name: str, file_extension: str) -> dict:
    return await _docs_request("POST", "/api/document-processor/extract-text-from-file", {
        "minio_bucket": minio_bucket,
        "minio_object_name": minio_object_name,
        "file_extension": file_extension,
    })


@tool(
    name="document_generate_metadata",
    description="텍스트에서 자동으로 메타데이터(요약, 키워드, 주제, 개체명, 감정 등)를 생성한다.",
    parameters={
        "text": {"type": "string", "description": "메타데이터를 추출할 텍스트"},
    },
)
async def document_generate_metadata(text: str) -> dict:
    return await _docs_request("POST", "/api/document-info-generator/generate-metadata", {"text": text})


@tool(
    name="document_supported_types",
    description="xgen-documents가 지원하는 파일 타입 목록을 조회한다.",
    parameters={},
)
async def document_supported_types() -> dict:
    return await _docs_request("GET", "/api/document-processor/supported-types")
