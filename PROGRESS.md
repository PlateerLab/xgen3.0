# XGEN 3.0 — 진행 현황

## 완료 사항

### Phase 1: 기반 (MVP) ✅

| 항목 | 파일 | 상태 |
|------|------|------|
| 프로젝트 구조 | `pyproject.toml`, `Dockerfile`, 디렉토리 구조 | ✅ |
| `@tool` 데코레이터 | `src/tools/decorator.py` | ✅ |
| Tool Registry | `src/tools/registry.py` | ✅ |
| Agent Core 마스터 루프 | `src/core/agent.py` | ✅ |
| 대화 컨텍스트 | `src/core/context.py` | ✅ |
| LLM 클라이언트 | `src/core/model_client.py` (OpenAI 호환) | ✅ |
| Built-in 도구 | `src/tools/builtin/http.py`, `db.py`, `file.py` | ✅ |
| CLI | `cli.py` (serve, import, run, tools, connect) | ✅ |
| Trace/Log | `src/trace/collector.py`, `exporter.py` | ✅ |
| State Store | `src/store/state.py` (PostgreSQL Checkpointer) | ✅ |
| Agent Store | `src/store/agent_store.py` (Agent 정의 CRUD) | ✅ |
| 실행 이력 | `src/store/history.py` | ✅ |

### Phase 2: AI 개발 + 샌드박스 ✅

| 항목 | 파일 | 상태 |
|------|------|------|
| Docker Sandbox | `src/sandbox/docker.py` (격리실행, 타임아웃, 리소스제한) | ✅ |
| Sandbox @tool | `src/sandbox/runner.py` (execute_code, execute_code_with_test) | ✅ |
| AI 도구 생성 | `src/tools/generator.py` (LLM → 코드생성 → 샌드박스테스트 → 등록) | ✅ |
| Human-in-the-Loop | `src/core/approval.py` (승인 대기 → 승인/거절 → 재개) | ✅ |
| 실패 재개 | `src/core/agent.py` (State Store 연동, resume=True) | ✅ |
| 멀티턴 컨텍스트 저장 | Agent → State Store 자동 체크포인트 | ✅ |

### Phase 3: 플랫폼 통합 ✅

| 항목 | 파일 | 상태 |
|------|------|------|
| MCP 클라이언트 | `src/mcp/client.py` (SSE + STDIO) | ✅ |
| MCP → @tool 브릿지 | `src/mcp/bridge.py` | ✅ |
| graph-tool-call | `src/tools/graph_tool.py` — **실제 패키지(0.13.1) 연동** | ✅ |
| Agent Core 연동 | `_resolve_tools_schema()` — 도구 15개+ 시 자동 검색 모드 | ✅ |
| MCP API | `/api/mcp/connect`, `/api/mcp/servers` | ✅ |
| graph-tool API | `/api/tools/search`, `/api/tools/ingest`, `/api/tools/graph/stats` | ✅ |

### Phase 4: 운영 고도화 ✅

| 항목 | 파일 | 상태 |
|------|------|------|
| 설정 관리 | `src/core/config.py` (환경변수 기반) | ✅ |
| 권한 관리 | `src/core/permissions.py` (ADMIN/DEVELOPER/USER/VIEWER) | ✅ |
| Agent 버전 관리 | `src/store/versioning.py` | ✅ |
| 트리거 | `src/core/triggers.py` (Webhook + 스케줄) | ✅ |

### xgen-workflow API 호환 ✅

| 항목 | 내용 | 상태 |
|------|------|------|
| 요청 모델 | `WorkflowRequest` — xgen-workflow와 동일 필드 | ✅ |
| SSE 이벤트 포맷 | `log`, `tool`, `data`, `end`, `error` — 기존 프론트엔드 호환 | ✅ |
| Deploy 응답 | `{success, content, citations, error}` + Envelope 포맷 | ✅ |
| API 경로 | `/api/workflow/*` 전체 경로 유지 | ✅ |
| input_data 변환 | str/dict/list/None → 자동 메시지 변환 | ✅ |

### graph-tool-call 연동 ✅ (신규)

| 항목 | 내용 | 상태 |
|------|------|------|
| 패키지 | `graph-tool-call 0.13.1` 설치 및 `pyproject.toml` 추가 | ✅ |
| GraphToolManager | `ToolGraph` 래핑 — ingest_from_registry, ingest_openapi, ingest_mcp_tools | ✅ |
| Agent Core 연동 | `_resolve_tools_schema()` — 도구 15개+ 시 자동 graph 검색 | ✅ |
| 호출 이력 | `record_call()` — history-aware retrieval | ✅ |

### xgen-infra 배포 설정 ✅ (신규)

| 파일 | 작업 | 상태 |
|------|------|------|
| `dockerfiles/xgen-agent/Dockerfile` | 생성 (Chromium 제거, 경량) | ✅ |
| `dockerfiles/xgen-agent/Dockerfile.local` | 생성 (Jenkins 로컬 빌드용) | ✅ |
| `k3s/helm-chart/values/xgen-agent.yaml` | 생성 (환경변수, 리소스 설정) | ✅ |
| `k3s/jenkins/config/services.yaml` | xgen-agent 추가 | ✅ |
| `k3s/argocd/projects/xgen.yaml` | dev/prd에 xgen-agent 추가 | ✅ |
| `k3s/argocd/projects/xgen-son.yaml` | dev/prd에 xgen-agent 추가 | ✅ |
| `compose/full-stack/docker-compose.yml` | xgen-agent 서비스 추가 (포트 8010) | ✅ |
| `compose/full-stack/docker-compose.dev.yml` | xgen-agent profile 추가 | ✅ |

### xgen2.0 레포 클론 ✅ (신규)

```
repos/
├── xgen-infra/            ← 빌드/배포 설정 (수정됨)
├── xgen-workflow/         ← 교체 대상 (참고용)
├── xgen-core/             ← 유지 (xgen-agent가 호출)
├── xgen-frontend/         ← 프론트엔드 연동 대상
├── xgen-model/            ← LLM 추론
├── xgen-mcp-station/      ← Phase 3에서 흡수
├── xgen-documents/        ← 유지
└── xgen-backend-gateway/  ← 유지
```

### 실전 검증 ✅

| 테스트 | 환경 | 결과 |
|--------|------|------|
| GPT-4o-mini 단순 대화 | 로컬 Python | ✅ |
| 도구 자동 선택 (get_time, calculate) | 로컬 Python | ✅ |
| file_read 도구 (pyproject.toml) | Docker 단독 | ✅ |
| db_query 도구 (PostgreSQL) | Docker 단독 | ✅ |
| http_request 도구 (httpbin.org) | Docker 단독 | ✅ |
| Agent 저장/목록 (DB CRUD) | Docker 단독 | ✅ |
| **풀스택 compose DB 연동** | compose (PostgreSQL + Redis + xgen-agent) | ✅ |
| **풀스택 compose LLM 대화** | compose (GPT-4o-mini + 도구 7개) | ✅ |
| **풀스택 compose Agent CRUD** | compose (저장/목록/로드) | ✅ |
| Swagger UI | http://localhost:8010/docs | ✅ |

### 테스트 코드 현황

**116개 테스트 전부 통과 (2.27초)**

| 테스트 파일 | 개수 | 대상 |
|-------------|------|------|
| test_api.py | 21 | API 엔드포인트 (CRUD, deploy, trace, schedule 등) |
| test_graph_tool.py | 20 | graph-tool-call 연동 (실제 패키지) |
| test_sse_adapter.py | 11 | SSE 이벤트 포맷 호환 |
| test_models.py | 9 | WorkflowRequest 입력 변환 |
| test_context.py | 8 | 대화 컨텍스트 |
| test_generator.py | 6 | AI 도구 생성기 |
| test_permissions.py | 6 | 권한 관리 |
| test_triggers.py | 6 | 트리거 |
| test_model_client.py | 5 | LLM 응답 파싱 |
| test_mcp.py | 5 | MCP 클라이언트/브릿지 |
| test_trace.py | 5 | Trace 수집기 |
| test_approval.py | 4 | Human-in-the-Loop |
| test_sandbox.py | 4 | Docker 샌드박스 |
| test_tools.py | 4 | @tool + Registry |
| test_config.py | 2 | 환경변수 설정 |

---

## 호환 API 엔드포인트 전체 목록

```
GET  /health
POST /api/workflow/execute/based_id/stream          ← 핵심 SSE 실행
POST /api/workflow/execute/based_id/stream/deploy    ← Deploy SSE (로그 미전송)
POST /api/workflow/execute/deploy/stream             ← Deploy (json/stream 선택)
POST /api/workflow/execute/deploy/result             ← Java Envelope 응답
GET  /api/workflow/execute/status                    ← 실행 상태 목록
GET  /api/workflow/execute/status/{id}               ← 실행 상태 조회
POST /api/workflow/execute/cleanup                   ← 완료 정리
GET  /api/workflow/list                              ← 워크플로우 목록
POST /api/workflow/save                              ← 워크플로우 저장
GET  /api/workflow/load/{workflow_id}                ← 워크플로우 로드
DELETE /api/workflow/delete/{workflow_id}            ← 워크플로우 삭제
POST /api/workflow/rename/workflow                   ← 이름 변경
POST /api/workflow/check/workflow                    ← 존재 확인
GET  /api/workflow/version/list                      ← 버전 목록
GET  /api/workflow/version/data                      ← 버전 데이터
GET  /api/workflow/deploy/load/{user_id}/{wf_id}    ← Deploy 로드
POST /api/workflow/deploy/toggle/{workflow_id}       ← 배포 토글
GET  /api/workflow/deploy/status/{workflow_id}       ← 배포 상태
GET  /api/workflow/deploy/list                       ← 배포 목록
GET  /api/workflow/trace/list                        ← 트레이스 목록
GET  /api/workflow/trace/detail/{trace_id}           ← 트레이스 상세
GET  /api/workflow/trace/by-interaction/{id}         ← 인터랙션별 트레이스
POST /api/workflow/schedule/sessions                 ← 스케줄 생성
GET  /api/workflow/schedule/sessions                 ← 스케줄 목록
GET  /api/workflow/schedule/status                   ← 스케줄 상태
GET  /api/workflow/performance                       ← 성능 통계
POST /api/agent/run                                  ← xgen3.0 전용 (non-streaming)
GET  /api/tools/list                                 ← 도구 목록
POST /api/tools/generate                             ← AI 도구 생성
POST /api/tools/search                               ← graph-tool-call 검색
POST /api/tools/ingest                               ← graph-tool-call 소스 추가
GET  /api/tools/graph/stats                          ← 그래프 통계
POST /api/mcp/connect                                ← MCP 서버 연결
DELETE /api/mcp/disconnect/{name}                    ← MCP 연결 해제
GET  /api/mcp/servers                                ← MCP 서버 목록
POST /api/approval/action                            ← 승인/거절 처리
GET  /api/approval/pending                           ← 대기 승인 목록
GET  /api/sessions                                   ← 세션 목록
DELETE /api/sessions/{session_id}                    ← 세션 삭제
GET  /api/history                                    ← 실행 이력
```

---

## 풀스택 end-to-end 테스트 현황

### 서비스 기동 상태

| 서비스 | 포트 | 상태 |
|--------|------|------|
| PostgreSQL | 5432 | ✅ healthy |
| Redis | 6379 | ✅ healthy |
| xgen-core | 8001 | ✅ healthy (DB + Redis) |
| xgen-agent | 8010 | ✅ ok (도구 7개, DB Store 3개) |
| xgen-frontend | 3000 | ✅ Ready (Next.js 15.5.7 Turbopack) |
| xgen-backend-gateway | 8000 | ✅ running |

### 프론트엔드 접속

- URL: http://localhost:3000
- 로그인: `admin@xgen.local` / `admin1234`
- 로그인 성공 확인 ✅

### compose 실행 방법

```bash
cd repos/xgen-infra/compose/full-stack

# .env 설정
cp .env.dev .env
# GITLAB_TOKEN, MODEL_API_KEY 설정

# 인프라 + core + agent + frontend 기동
docker compose -f docker-compose.dev.yml up -d --build postgresql redis
docker compose -f docker-compose.dev.yml up -d --build git-cloner xgen-core
docker compose -f docker-compose.dev.yml --profile agent up -d --build xgen-agent
docker compose -f docker-compose.dev.yml --profile frontend up -d --build xgen-frontend
```

---

### xgen3.0 전용 프론트엔드 재구성 ✅ (신규)

기존 xgen-frontend(캔버스 에디터 중심)를 xgen3.0 철학에 맞게 **대화 중심 UI**로 완전 재설계.
기존 디자인 시스템(색상, 타이포, 스페이싱, SCSS 패턴)을 계승하되 구조를 근본적으로 변경.

| 항목 | 파일 | 상태 |
|------|------|------|
| 프로젝트 설정 | `frontend/package.json`, `next.config.ts`, `tsconfig.json` | ✅ |
| 디자인 시스템 | `frontend/src/app/_common/_variables.scss`, `globals.css` | ✅ |
| 공통 타입 | `frontend/src/app/_common/types/index.ts` (Agent, Message, Trace, SSE) | ✅ |
| API 클라이언트 | `frontend/src/app/_common/api/` (client, config, agentAPI — SSE 스트리밍 포함) | ✅ |
| 루트 레이아웃 + 사이드바 | `frontend/src/app/layout.tsx`, `Sidebar/` (대화/에이전트/트레이스/설정) | ✅ |
| 대시보드 (/) | `frontend/src/app/page.tsx` (Agent 목록, 통계, 빠른 대화 시작) | ✅ |
| **대화 UI (/chat/[agentId])** | `frontend/src/app/chat/[agentId]/page.tsx` — **핵심 페이지** | ✅ |
| Trace 뷰어 (/trace/[traceId]) | `frontend/src/app/trace/[traceId]/page.tsx` (읽기 전용 Flow Viewer) | ✅ |
| Agent 상세 (/agents/[agentId]) | `frontend/src/app/agents/[agentId]/page.tsx` (개요/도구/이력 탭) | ✅ |
| ChatMessage 컴포넌트 | `ChatMessage/` (Think블록, ToolCall, 승인요청, 복사) | ✅ |
| TraceTimeline 컴포넌트 | `TraceTimeline/` (실행 흐름 타임라인) | ✅ |

**기존 대비 핵심 변경:**

| 기존 xgen-frontend | 새 frontend/ |
|---|---|
| 캔버스 에디터가 메인 (`/canvas`, ReactFlow 드래그앤드롭) | **대화 UI가 메인** (`/chat/[agentId]`) |
| 229개 SCSS 모듈, 61KB ChatInterface.tsx | 12개 SCSS 모듈로 경량화 |
| LangChain 노드 시스템 | `@tool` 기반 도구 표시 |
| LocalStorage 상태관리 | 서버 State Store 연동 |
| 비주얼 에디터 (수정용) | 읽기 전용 Trace 뷰어만 ("수정은 대화로") |

**대화 UI 핵심 기능:**
- SSE 스트리밍: Think → Act → Observe 과정 실시간 표시
- Think 블록: 접이식 추론 과정
- Tool Call: 도구 호출 파라미터/결과 실시간 표시
- Human-in-the-Loop: 승인/거부 버튼이 대화 흐름 안에 자연스럽게 등장
- Trace 링크: 헤더에서 읽기 전용 Flow Viewer로 즉시 이동

---

## 금일 진행 사항 (2026-03-16)

### 독립 Docker 빌드 ✅
- xgen-infra 의존 제거, `docker-compose.yml` 단독 빌드 체계 구축
- `docker compose up -d --build` 한 방으로 postgres + xgen-agent + xgen-agent-frontend 기동
- frontend `Dockerfile` 생성, 소스 볼륨 마운트 (핫리로드)
- `.env` 파일로 API 키 분리

### 프론트엔드 → xgen-agent SSE 연동 ✅
- SSE 이벤트 포맷 매핑 (xgen-workflow 호환 → xgen3.0 프론트엔드)
- Next.js rewrite SSE 버퍼링 문제 해결 (브라우저 → 백엔드 직접 요청)
- CORS 설정 추가
- `WorkflowRequest.interaction_id` null 허용 수정
- 대화 UI에서 LLM 응답 + 도구 호출 SSE 스트리밍 확인

### xgen-core / xgen-documents @tool 래핑 ✅
- `src/tools/builtin/xgen_core.py` — DB 8개 + Config 4개 + Auth 1개 = 13개 도구
- `src/tools/builtin/xgen_documents.py` — RAG 3개 + Embedding 3개 + 문서처리 3개 = 9개 도구
- 총 도구 29개 (7 빌트인 + 13 xgen-core + 9 xgen-documents)
- 15개 초과로 graph-tool-call 자동 검색 모드 동작 확인
- LLM이 "주문 조회해줘" → `core_db_find` 자동 선택 확인

### 프론트엔드 버그 수정 ✅
- `listAgents()` API 응답 형태 매핑 (`{agents:[]}` → 배열)
- `AgentSummary` 필드 변환 (tools→tool_count, status 기본값)
- `<a>` 중첩 에러 수정 (agents 페이지)
- `stats.totalTools` NaN 수정
- 설정 페이지 (`/settings`) 신규 생성 — 서비스 상태, 도구 목록, MCP, 환경정보

### 관찰 가능성 — Trace / 실행 이력 UI ✅

| 항목 | 내용 | 상태 |
|------|------|------|
| Trace 목록 페이지 | `/trace` — 카드형 목록, 페이지네이션, step 배지 | ✅ |
| Trace 상세 페이지 | `/trace/[traceId]` — 실제 데이터 연결 (데모 폴백 제거) | ✅ |
| 실행 이력 페이지 | `/history` — 테이블형, 에이전트 필터, Trace 링크 | ✅ |
| Sidebar 메뉴 | "실행 이력" 추가 (FiClock 아이콘) | ✅ |
| API URL 수정 | `listTraces`, `getTrace` 잘못된 URL → 실제 백엔드 경로 연결 | ✅ |
| Trace step 기록 | Agent Core에서 Think/Tool/Response step을 trace에 자동 기록 | ✅ |
| 실행 이력 자동 기록 | SSE 실행 완료 시 `history_store.record()` 호출 추가 | ✅ |
| 백엔드→프론트 필드 보정 | `normalizeTrace()` — `start_time`→`timestamp`, `duration_ms`→`total_duration_ms` | ✅ |

### Mode A: 에이전트 없이 바로 대화 ✅

plan.md의 핵심 비전 구현 — "하나의 대화창에서 AI가 직접 agent를 개발·실행"

| 항목 | 내용 | 상태 |
|------|------|------|
| 에이전트 관리 도구 | `src/tools/builtin/agent_mgmt.py` — create/list/get/update/delete_agent + list_available_tools (6개) | ✅ |
| graph-tool-call 항상 활성 | 임계값 15 → 0 변경, 도구 수 무관하게 항상 검색 모드 | ✅ |
| 메타 에이전트 불필요 | 별도 프롬프트 없이 graph search가 `create_agent` 등 자동 탐색 | ✅ |
| `/chat` 바로 대화 | 에이전트 선택 없이 default로 즉시 대화 시작 | ✅ |
| 대화 이력 표시 | `/chat` 웰컴 화면에 최근 대화 5건 + 빠른 프롬프트 4개 | ✅ |
| DB 에이전트 로드 | `_create_agent`에서 agent_store.load() → system_prompt/model/approval 자동 적용 | ✅ |
| 총 도구 40개 | 기존 34 + 에이전트 관리 6개 | ✅ |

**동작 흐름:**
```
사용자: "주문 조회 에이전트 만들어줘"
  → graph-tool-call이 create_agent 도구 검색
  → LLM이 list_available_tools → create_agent 순서로 호출
  → DB에 에이전트 정의 저장
  → 사용자에게 결과 보고
```

### Docker Sandbox 복구 ✅

| 항목 | 내용 | 상태 |
|------|------|------|
| docker.sock 마운트 | `docker-compose.yml`에 `/var/run/docker.sock` 볼륨 추가 | ✅ |
| Docker CLI 설치 | Dockerfile에 Docker CLI 설치 스크립트 추가 | ✅ |
| stdin 방식 실행 | 파일 마운트 대신 stdin으로 코드 전달 (컨테이너 경로 공유 문제 해결) | ✅ |
| 보안 플래그 호환 | `--no-new-privileges` → `--security-opt no-new-privileges` | ✅ |
| execute_code 검증 | `print(sum(range(1,11)))` → stdout: "55", exit_code: 0, 328ms | ✅ |
| execute_code_with_test 검증 | `add(1,2)==3` → tests_passed: true, 409ms | ✅ |

### Human-in-the-Loop e2e 검증 ✅

| 항목 | 내용 | 상태 |
|------|------|------|
| _active_agents 등록 | SSE 실행 시 agent 등록, 완료 시 제거 | ✅ |
| 프론트 API 수정 | `/api/workflow/approval` → `/api/approval/action`, request_id + action 스키마 | ✅ |
| SSE approval 이벤트 | log 이벤트의 approval 필드 감지 → `approval_required` 변환 | ✅ |
| ApprovalRequest.request_id | 타입 + SSE 핸들러 + ChatMessage 콜백 전체 연결 | ✅ |

**e2e 테스트 결과:**
```
1. SSE 시작 → approval_required (request_id: apr_617ebd75)
2. GET /api/approval/pending → pending 1건
3. POST /api/approval/action → approve 성공
4. 승인 후 db_query 실행 → SELECT 1 → rows: [{?column?: 1}]
5. LLM 응답 → "결과가 성공적으로 반환되었습니다"
```

### 에이전트 생성 후 전환 ✅

| 항목 | 내용 | 상태 |
|------|------|------|
| ChatMessage 링크 | `create_agent` 성공 시 "에이전트와 대화하기" 링크 자동 표시 | ✅ |
| 링크 이동 | `/chat/{agentName}`으로 즉시 이동 가능 | ✅ |

---

## 다음 진행 순서

### Step 1: create_tool ↔ ToolGenerator 연결
- `create_tool` 호출 시 실제 `ToolGenerator` 파이프라인 실행 (코드 생성 → 샌드박스 테스트 → 등록)
- 현재는 "pending" 반환하고 끝나는 상태

### Step 2: MCP Station 흡수 테스트
- xgen-mcp-station이 하는 역할을 xgen-agent 내장 MCP 클라이언트로 대체 가능한지 확인

### Step 3: API 경로 마이그레이션 (선택)
- `/api/workflow/*` → `/api/agent/*` 점진적 전환

---

## 프로젝트 파일 구조

```
xgen3.0/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml           ← 단독 실행용
├── cli.py
├── plan.md
├── PROGRESS.md                  ← 이 파일
├── agents/
│   └── customer-support.yaml
├── src/
│   ├── api/
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   └── sse_adapter.py
│   ├── core/
│   │   ├── agent.py             ← graph-tool-call 연동 포함
│   │   ├── approval.py
│   │   ├── config.py
│   │   ├── context.py
│   │   ├── model_client.py
│   │   ├── permissions.py
│   │   ├── planner.py
│   │   └── triggers.py
│   ├── tools/
│   │   ├── decorator.py
│   │   ├── registry.py
│   │   ├── generator.py
│   │   ├── graph_tool.py        ← 실제 graph-tool-call 패키지 래핑 (항상 활성)
│   │   └── builtin/ (http, db, file, xgen_core, xgen_documents, xgen_utils, agent_mgmt)
│   ├── sandbox/
│   │   ├── docker.py
│   │   └── runner.py
│   ├── mcp/
│   │   ├── client.py
│   │   └── bridge.py
│   ├── store/
│   │   ├── state.py
│   │   ├── agent_store.py
│   │   ├── history.py
│   │   └── versioning.py
│   └── trace/
│       ├── collector.py
│       └── exporter.py
├── frontend/                    ← xgen3.0 전용 프론트엔드 (대화 중심)
│   ├── package.json             (Next.js 15 + React 19)
│   ├── next.config.ts           (/api/workflow/* 프록시)
│   └── src/app/
│       ├── layout.tsx           (Sidebar + Content)
│       ├── page.tsx             (/ 대시보드)
│       ├── chat/               (★ 바로 대화 시작 — default 에이전트)
│       ├── chat/[agentId]/     (특정 에이전트 대화 UI)
│       ├── trace/              (Trace 목록)
│       ├── trace/[traceId]/    (Trace 상세 — 실행 흐름 타임라인)
│       ├── history/            (실행 이력 — 테이블형)
│       ├── agents/[agentId]/   (Agent 상세)
│       └── _common/            (디자인 시스템, API, 컴포넌트)
├── repos/                       ← xgen2.0 클론 (로컬 실험용)
│   ├── xgen-infra/              ← 배포 설정 수정됨
│   ├── xgen-workflow/
│   ├── xgen-core/
│   ├── xgen-frontend/
│   ├── xgen-model/
│   ├── xgen-mcp-station/
│   ├── xgen-documents/
│   └── xgen-backend-gateway/
├── tests/ (16개 파일, 116개 테스트)
└── tools/                       (커스텀 도구 디렉토리)
```

---

## 환경 정보

| 항목 | 값 |
|------|-----|
| Python | 3.12.10 (로컬), 3.14-slim (Docker) |
| Docker | 29.2.1 |
| LLM | GPT-4o-mini (OpenAI API) |
| DB | PostgreSQL 15.4-alpine |
| graph-tool-call | 0.13.1 |
| 풀스택 compose | `repos/xgen-infra/compose/full-stack/docker-compose.dev.yml` |
| xgen-agent 포트 | 8010 (compose), 8000 (단독) |
| Swagger UI | http://localhost:8010/docs |
