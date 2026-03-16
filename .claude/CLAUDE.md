# XGEN 3.0 — xgen-agent

대화 기반 AI Agent Runtime 플랫폼. 기존 xgen-workflow를 대체한다.

참고 (XGEN2.0) : https://gitlab.x2bee.com/xgen2.0
gitlab token (내꺼) : PjWcZQ8X4v61zxDzu3do

TODO 짜가면서 작업진행한다
xgen2.0 을 참고하되 깃랩 xgen2.0을 함부로 수정하지 않도록한다.

## 프로젝트 한줄 요약

> 하나의 대화창에서 AI가 직접 agent와 workflow를 개발·실행·검증·배포하는 플랫폼.

## 핵심 원칙

1. **껍데기만 존재** — 비주얼 에디터 없음. 런타임 + 도구 인터페이스만 제공
2. **AI-first, Human-compatible** — AI가 만들든 사람이 만들든 결과물 포맷 동일
3. **단순한 구조** — 복잡한 추상화 없이 Tool 단위로 조합
4. **단일 에이전트** — 멀티에이전트 불필요, 도구로 충분
5. **관찰 가능성 1일차부터** — Trace/Log 내장

## 기술 스택

- **언어**: Python 3.12+, FastAPI
- **샌드박스**: Docker 컨테이너
- **상태 저장**: PostgreSQL (Checkpointer, 실행 이력, agent 정의)
- **모델 연동**: xgen-model 또는 외부 API (Claude, OpenAI, 로컬 LLM)
- **MCP**: STDIO + SSE 클라이언트 내장
- **도구 검색**: graph-tool-call (대량 도구 동적 로딩)

## 디렉토리 구조

```
xgen-agent/
├── src/
│   ├── core/               # Agent Core (Think → Act → Observe 루프)
│   │   ├── agent.py        # 마스터 루프
│   │   ├── planner.py      # 실행 계획 수립
│   │   └── context.py      # 대화 컨텍스트 관리
│   ├── tools/
│   │   ├── registry.py     # Tool Registry
│   │   ├── decorator.py    # @tool 데코레이터
│   │   └── builtin/        # 빌트인 도구 (http, db, file)
│   ├── sandbox/
│   │   ├── runner.py       # 코드 실행 엔진
│   │   └── docker.py       # Docker 격리
│   ├── mcp/
│   │   ├── client.py       # MCP 클라이언트
│   │   └── bridge.py       # MCP → @tool 변환
│   ├── store/
│   │   ├── state.py        # State Store (Checkpointer)
│   │   ├── agent_store.py  # Agent 정의 저장
│   │   └── history.py      # 실행 이력
│   ├── trace/
│   │   ├── collector.py    # 실행 로그 수집
│   │   └── exporter.py     # 외부 연동 (Langfuse 등)
│   └── api/
│       └── routes.py       # FastAPI 엔드포인트
├── tools/                   # 커스텀 도구 예제
├── agents/                  # agent 정의 예제
├── tests/
├── Dockerfile
├── pyproject.toml
└── README.md
```

## 핵심 패턴

### @tool 데코레이터 — 유일한 도구 인터페이스

```python
from xgen_agent import tool

@tool(
    name="도구명",
    description="AI가 판단할 수 있도록 구체적 설명 필수",
    parameters={"param": {"type": "string", "description": "설명"}}
)
async def my_tool(param: str) -> dict:
    ...
```

### Agent Core 마스터 루프

```python
while True:
    response = await model.generate(messages, tools=available_tools)
    if not response.tool_calls:
        return response.text
    for tool_call in response.tool_calls:
        result = await tool_registry.execute(tool_call)
        messages.append(tool_result(result))
```

### Agent 정의 (YAML)

```yaml
name: agent-name
description: 설명
model: claude-sonnet
tools: [tool1, tool2, builtin:http, mcp:slack]
system_prompt: |
  프롬프트
approval_required:
  - "DELETE *"
```

## 도구 소스 3가지

| 소스 | 설명 |
|------|------|
| `@tool` | Python 함수 데코레이터. AI/사람 동일 포맷 |
| `MCP` | 외부 MCP 서버 연결 (STDIO + SSE) |
| `graph-tool-call` | 검색 기반 동적 로딩 (대량 도구용) |

## 기존 서비스 관계

| 서비스 | 상태 |
|--------|------|
| xgen-workflow | **xgen-agent로 대체** |
| xgen-mcp-station | Phase 3에서 흡수 (당장은 유지) |
| xgen-core | 유지 (xgen-agent가 호출) |
| xgen-backend-gateway | 유지 |
| xgen-frontend | 대화 UI 강화 |
| xgen-model | 유지 |
| xgen-documents | 유지 |

## API 호환

- 1단계: `/api/workflow/*` 경로 유지 (하위 호환)
- 안정화 후: `/api/agent/*`로 점진 마이그레이션

### 핵심 엔드포인트

```
POST /api/workflow/execute/based_id/stream      → Agent 대화 실행 (SSE)
POST /api/workflow/execute/based_id/stream/deploy → Agent 배포 실행
GET  /api/workflow/list                          → Agent 목록
POST /api/workflow/save                          → Agent 저장
GET  /health                                     → 헬스 체크
```

## 환경변수

```
CORE_SERVICE_BASE_URL=http://xgen-core:8000
DOCUMENTS_SERVICE_BASE_URL=http://xgen-documents:8000
MCP_STATION_BASE_URL=http://xgen-mcp-station:8000
```

## 개발 로드맵

- **Phase 1 (MVP)**: 프로젝트 구조, @tool, Registry, Agent Core 루프, CLI, Trace 기본, State Store
- **Phase 2**: Docker Sandbox, AI 도구 생성, Human-in-the-Loop, 실패 재개
- **Phase 3**: Frontend 연동, Gateway, MCP 내장, graph-tool-call, namespace 격리
- **Phase 4**: 대시보드, 권한 관리, 버전 관리, 트리거, OpenTelemetry

## 코드 컨벤션

- Python 3.12+ async/await 기반
- FastAPI 라우터 패턴
- 도구는 반드시 `@tool` 데코레이터 + 상세 description
- 테스트: `tests/` 디렉토리, pytest

## 참고

- 상세 설계: `plan.md`
