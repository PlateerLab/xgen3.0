# xgen-agent

XGEN 2.0 AI Agent Runtime — 대화 기반 agent/workflow 개발 플랫폼

## 비전

XGEN을 설치하면 **하나의 대화창**에서 AI가 직접 agent와 workflow를 개발·실행·검증·배포한다.
사람이 만든 도구도 동일한 방식으로 import하여 사용할 수 있다.

## 핵심 원칙

1. **껍데기만 존재** — 비주얼 에디터, 노드 시스템 없음. 런타임과 도구 인터페이스만 제공
2. **AI-first, Human-compatible** — 모델이 좋으면 AI가 개발, 아니면 사람이 개발. 결과물 포맷은 동일
3. **단순한 구조** — 복잡한 추상화 없이 도구(Tool) 단위로 모든 것을 조합
4. **고객사별 독립** — 각 고객사가 자신만의 agent/workflow를 대화로 구축
5. **관찰 가능성 우선** — 실행 로그, 트레이싱을 1일 차부터 내장

## 벤치마킹 요약

7개 프레임워크/플랫폼 분석 후 설계에 반영:

| 프레임워크 | 핵심 패턴 | xgen-agent에 반영한 것 |
|-----------|----------|----------------------|
| **CrewAI** | Role-based 팀, @tool 데코레이터 | `@tool` 데코레이터 패턴 (도구 정의 표준) |
| **LangGraph** | 상태 그래프, Checkpointer | State Store (세션 복구, 실패 재개) |
| **AutoGen** | Actor model, Docker 샌드박스 | Docker 기반 코드 격리, MCP 통합 |
| **OpenAI Agents SDK** | Handoff, 경량 오케스트레이션 | 단일 에이전트 루프 (멀티에이전트 불필요) |
| **Claude Agent SDK** | 파일시스템 + Bash 직접 실행 | 마스터 루프 (Think → Act → Observe) |
| **Dify** | 비주얼 워크플로우, DifySandbox | 샌드박스 격리 전략 (화이트리스트, 네트워크 격리) |
| **Coze** | 노코드 봇 빌더, Coze Loop | 실행 추적/평가 (Observability) |

### 반영하지 않은 것

- **비주얼 워크플로우 에디터** (Dify, Coze) — 노드 조립/연결 작업을 AI 모델이 직접 수행하므로 에디터 불필요. 단, **읽기 전용 Flow 뷰어는 제공** (아래 참조)
- **멀티에이전트 오케스트레이션** (CrewAI Crews, AutoGen GroupChat) — 2026년 기준 과대선전, 단일 에이전트로 충분
- **LangChain 의존성** (LangGraph) — 독립 런타임 유지
- **4계층 추상화** (AutoGen Studio/AgentChat/Core/Extensions) — 복잡도 증가 대비 이점 부족

### 핵심 인사이트

> **"도구 설계의 패러다임 역전"** — 2026년, 인간이 도구를 "AI가 이해할 수 있도록" 설계하는 것이 새로운 규범.
> AI가 만들든 사람이 만들든, `@tool` + 자연어 description이 핵심이다.

## 동작 모드

### Mode A: AI 개발 (모델 사양 충분)

```
사용자: "고객 문의를 받아서 DB 조회하고 응답하는 agent 만들어줘"
    ↓
AI 모델이 직접:
  1. 필요한 도구 파악 (DB 연결, 검색, 응답 생성)
  2. 도구가 없으면 코드 생성 → 샌드박스에서 테스트
  3. agent 구성 (도구 조합 + 프롬프트)
  4. 실행 & 검증
  5. 배포
```

### Mode B: 수동 개발 (폐쇄망/저사양)

```
개발자가 직접:
  1. @tool 데코레이터로 도구 작성 (AI가 이해할 description 필수)
  2. import하여 등록
  3. agent 구성 (YAML)
  4. 테스트 & 배포
```

### 공통점

두 모드 모두 최종 결과물은 동일한 구조:

```
agent/
├── agent.yaml          # agent 정의 (이름, 설명, 사용 도구 목록)
├── tools/
│   ├── query_db.py     # 도구 구현 (@tool 데코레이터)
│   ├── search.py
│   └── ...
└── prompts/
    └── system.md       # 시스템 프롬프트
```

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                   xgen-frontend                  │
│              (대화 UI — 단일 입력창)               │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                  xgen-agent                      │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │Agent Core│  │ Sandbox  │  │  Trace / Log  │  │
│  │          │  │ (Docker) │  │               │  │
│  │ 대화→계획 │  │ 격리실행  │  │ 실행이력 수집  │  │
│  │ →실행→검증│  │ 타임아웃  │  │ 도구호출 추적  │  │
│  │ →피드백   │  │ 리소스제한│  │ 에러 트레이싱  │  │
│  └────┬─────┘  └──────────┘  └───────────────┘  │
│       │                                          │
│  ┌────▼──────────────────────────────────────┐   │
│  │          Tool Registry                     │   │
│  │                                            │   │
│  │  @tool         MCP          graph-tool     │   │
│  │  (Built-in +   (외부 MCP    (검색 기반     │   │
│  │   Custom)      서버 연결)    동적 로딩)     │   │
│  └────────────────────────────────────────────┘   │
│                                                   │
│  ┌────────────────────────────────────────────┐   │
│  │       State Store (Checkpointer 패턴)       │   │
│  │                                             │   │
│  │  세션 컨텍스트 저장 / 실패 시 재개            │   │
│  │  Human-in-the-Loop (승인 대기 → 재개)        │   │
│  │  Agent 정의 + 도구 코드 버전 관리             │   │
│  └────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      xgen-core    xgen-model   외부 API
      (기존 XGEN    (LLM 추론)   (MCP 등)
       기능 연동)
```

## 핵심 컴포넌트

### 1. Agent Core (마스터 루프)

Claude Code에서 검증된 Think → Act → Observe 루프:

```python
# 마스터 에이전트 루프 (단일 루프, 단순 설계)
while True:
    # Think: 다음 단계 추론
    response = await model.generate(messages, tools=available_tools)

    # 종료 조건: 도구 호출 없는 텍스트 응답
    if not response.tool_calls:
        return response.text

    # Act: 도구 실행
    for tool_call in response.tool_calls:
        result = await tool_registry.execute(tool_call)
        messages.append(tool_result(result))

    # Observe: 결과를 컨텍스트에 추가 → 다음 루프
```

특징:
- 헤드 모델(Claude, GPT, 로컬 LLM 등)과 통신
- 멀티턴 대화 컨텍스트 유지
- 도구 호출 결정 및 실행
- 실행 결과 검증 및 피드백 루프
- **단일 에이전트 설계** — 멀티에이전트는 불필요 (도구로 충분)

### 2. Tool Registry

모든 도구를 통합 관리하는 레지스트리. **`@tool` 데코레이터가 유일한 인터페이스.**

```python
from xgen_agent import tool

@tool(
    name="query_customer",
    description="고객 정보를 DB에서 조회한다. customer_id로 검색하며 이름, 연락처, 가입일을 반환한다.",
    parameters={
        "customer_id": {"type": "string", "description": "고객 ID (예: CUST-001)"}
    }
)
async def query_customer(customer_id: str) -> dict:
    result = await db.fetch("SELECT * FROM customers WHERE id = $1", customer_id)
    return {"customer": result}
```

도구 소스 3가지:
- **@tool (Built-in + Custom)**: 데코레이터로 정의된 Python 함수. AI가 만들든 사람이 만들든 동일
- **MCP**: 외부 MCP 서버 연결 (STDIO + SSE). 기존 xgen-mcp-station 역할 흡수
- **graph-tool-call**: 도구가 많을 때 검색 기반 동적 로딩. 컨텍스트 윈도우 절약

### 3. Sandbox (Docker 격리)

AI가 생성한 코드를 안전하게 실행하는 격리 환경. AutoGen DockerCodeExecutor + DifySandbox 참고:

```python
from xgen_agent.sandbox import DockerSandbox

sandbox = DockerSandbox(
    image="python:3.12-slim",
    timeout=30,              # 30초 타임아웃
    memory_limit="256m",     # 메모리 제한
    network="none",          # 네트워크 차단 (필요 시 허용)
    work_dir="/tmp/sandbox"
)

result = await sandbox.execute("""
import pandas as pd
df = pd.read_csv('/data/orders.csv')
print(df.describe().to_json())
""")
# → {"stdout": "...", "stderr": "", "exit_code": 0}
```

격리 전략:
- **Docker 컨테이너**: 프로세스/파일시스템/네트워크 격리
- **타임아웃**: 무한 루프 방지 (기본 30초)
- **리소스 제한**: CPU, 메모리 상한
- **네트워크 제어**: 기본 차단, 화이트리스트 방식 허용
- **실행 로그**: 모든 입출력 기록 (Trace에 연동)

### 4. State Store (Checkpointer 패턴)

LangGraph Checkpointer에서 검증된 상태 지속성 패턴:

```python
from xgen_agent.store import StateStore

store = StateStore(db_url="postgresql://...")

# 세션 상태 자동 저장 (매 도구 호출마다)
await store.checkpoint(
    session_id="user_123_session_456",
    state={
        "messages": [...],
        "tool_results": [...],
        "current_plan": {...}
    }
)

# 실패 시 마지막 성공 지점에서 재개
state = await store.resume(session_id="user_123_session_456")

# Human-in-the-Loop: 승인 대기
await store.pause_for_approval(
    session_id="...",
    action="DELETE FROM orders WHERE id = 123",
    reason="위험한 DELETE 쿼리 — 사용자 승인 필요"
)
# → 사용자가 승인하면 해당 지점에서 재개
```

기능:
- **세션 복구**: 네트워크 끊김, 서버 재시작 후에도 마지막 지점에서 재개
- **실패 재개**: 도구 실행 실패 시 성공한 단계까지 보존, 실패 단계만 재실행
- **Human-in-the-Loop**: 위험한 액션(DB 삭제, 외부 API 호출 등)에서 상태 저장 → 승인 대기 → 재개
- **Agent 정의 저장**: agent.yaml + 도구 코드 버전 관리
- **실행 이력**: 감사 로그 (누가, 언제, 무엇을 실행했는지)

### 5. Trace / Log (1일 차부터 내장)

Coze Loop, LangSmith에서 확인한 교훈: Observability는 나중이 아니라 처음부터.

```python
# 모든 도구 호출이 자동으로 추적됨
{
    "trace_id": "tr_abc123",
    "session_id": "user_123_session_456",
    "timestamp": "2026-03-16T10:30:00Z",
    "agent": "customer-support",
    "steps": [
        {
            "type": "think",
            "model": "claude-sonnet",
            "input_tokens": 1200,
            "output_tokens": 350,
            "duration_ms": 2100
        },
        {
            "type": "tool_call",
            "tool": "query_customer",
            "params": {"customer_id": "CUST-001"},
            "result": {"customer": {...}},
            "duration_ms": 45
        },
        {
            "type": "tool_call",
            "tool": "query_orders",
            "params": {"customer_id": "CUST-001"},
            "result": {"orders": [...]},
            "duration_ms": 120
        },
        {
            "type": "response",
            "text": "고객님의 최근 주문은...",
            "total_duration_ms": 3500
        }
    ]
}
```

### 6. Flow Viewer (읽기 전용 시각화)

AI가 만든 agent의 실행 흐름을 사람이 직관적으로 확인할 수 있는 읽기 전용 뷰어.

**에디터가 아니라 뷰어다:**
- Dify/Coze는 사람이 노드를 드래그해서 **조립**하는 에디터
- Flow Viewer는 AI가 만든 결과를 사람이 **확인**하는 뷰어
- 수정이 필요하면? 대화로 AI에게 지시 → AI가 수정 → 뷰어에 반영

**두 가지 시각화:**

1. **Agent 구조 뷰** — agent가 어떤 도구를 어떤 순서로 쓰는지

```
┌──────────────┐
│ 사용자 입력   │
└──────┬───────┘
       ▼
┌──────────────┐     ┌──────────────┐
│ query_customer├────►│ query_orders │
└──────┬───────┘     └──────┬───────┘
       │                    │
       ▼                    ▼
┌──────────────────────────────┐
│         응답 생성             │
└──────────────────────────────┘
```

2. **실행 Trace 뷰** — 실제 실행된 경로, 각 단계 소요 시간, 입출력

```
[Think] 2.1s → [query_customer] 45ms → [query_orders] 120ms → [Response] 1.2s
  │                │                      │                       │
  │                ├─ input: CUST-001     ├─ input: CUST-001     ├─ "고객님의..."
  │                └─ output: {name:...}  └─ output: [{...}]     └─ total: 3.5s
```

Flow Viewer는 Trace/Log 데이터를 기반으로 렌더링하므로 별도 데이터 구조가 불필요하다.
프론트엔드(xgen-frontend)에서 구현하며, 백엔드는 Trace 데이터만 제공하면 된다.

## Tool 인터페이스

### Python으로 도구 만들기 (수동 — Mode B)

```python
# tools/query_customer.py
from xgen_agent import tool

@tool(
    name="query_customer",
    description="고객 정보를 DB에서 조회한다. customer_id로 검색하며 이름, 연락처, 가입일을 반환한다.",
    parameters={
        "customer_id": {"type": "string", "description": "고객 ID (예: CUST-001)"}
    }
)
async def query_customer(customer_id: str) -> dict:
    result = await db.fetch("SELECT * FROM customers WHERE id = $1", customer_id)
    return {"customer": result}
```

> **중요**: `description`은 AI가 "이 도구를 언제 쓸지" 판단하는 유일한 근거.
> "고객 정보 조회"보다 "고객 정보를 DB에서 조회한다. customer_id로 검색하며 이름, 연락처, 가입일을 반환한다."가 훨씬 효과적.

### AI가 도구 만들기 (대화 — Mode A)

```
사용자: "주문 내역을 조회하는 도구를 만들어줘. PostgreSQL orders 테이블이야"

AI:
  1. DB 스키마 조회 (information_schema)
  2. @tool 데코레이터로 도구 코드 생성
  3. 샌드박스에서 테스트 실행
  4. 테스트 통과 → Tool Registry에 등록
  → "query_orders 도구를 만들었어. 테스트 결과 정상 동작해."
```

### 도구 import (CLI)

```bash
# 디렉토리에서 일괄 import (@tool 데코레이터가 있는 .py 파일 자동 탐지)
xgen-agent import ./my-tools/

# 단일 파일 import
xgen-agent import ./query_customer.py

# MCP 서버 연결
xgen-agent connect mcp --url http://localhost:3000/sse

# graph-tool-call로 대량 도구 검색 기반 등록
xgen-agent connect graph-tool --source http://api.example.com/openapi.json
```

## Agent 정의

```yaml
# agent.yaml
name: customer-support
description: 고객 문의 응답 agent
model: claude-sonnet        # 사용할 모델 (없으면 기본 모델)

tools:
  - query_customer           # 커스텀 도구
  - query_orders             # 커스텀 도구
  - builtin:http             # 빌트인 도구
  - mcp:slack                # MCP 연결 도구

system_prompt: |
  너는 고객 지원 담당이야.
  고객 정보를 조회하고, 주문 내역을 확인해서 답변해.

# 위험 액션 승인 필요 여부
approval_required:
  - "DELETE *"               # DELETE 쿼리
  - "mcp:slack:send_message" # 외부 메시지 발송

triggers:                    # 선택사항: 자동 실행 조건
  - type: webhook
    path: /support
  - type: schedule
    cron: "0 9 * * *"
```

## 기존 xgen 서비스와의 관계

| 기존 | 변경 |
|------|------|
| xgen-workflow | **xgen-agent로 대체** |
| xgen-mcp-station | xgen-agent의 MCP 연결 기능으로 흡수 |
| xgen-core | 유지 (기존 XGEN 기능) |
| xgen-backend-gateway | 유지 (라우팅) |
| xgen-frontend | 대화 UI 강화 |
| xgen-model | 유지 (LLM 추론) |
| xgen-documents | 유지 (문서/RAG) |

## 기술 스택

- **언어**: Python 3.12+ (FastAPI)
- **샌드박스**: Docker 컨테이너 (AI 생성 코드 격리 실행)
- **상태 저장**: PostgreSQL (Checkpointer, 실행 이력, agent 정의)
- **모델 연동**: xgen-model 또는 외부 API (Claude, OpenAI, 로컬 LLM)
- **MCP**: MCP 클라이언트 내장 (STDIO + SSE)
- **도구 검색**: graph-tool-call (대량 도구 동적 로딩)
- **트레이싱**: 내장 (추후 Langfuse/OpenTelemetry 연동 가능)

## 개발 로드맵

### Phase 1: 기반 (MVP)
- [ ] 프로젝트 구조 세팅 (pyproject.toml, FastAPI)
- [ ] `@tool` 데코레이터 및 Tool 인터페이스 정의
- [ ] Tool Registry (파일 기반, 메모리 캐시)
- [ ] Agent Core 마스터 루프 (Think → Act → Observe)
- [ ] Built-in 도구 (HTTP, DB 쿼리, 파일 읽기)
- [ ] CLI (`xgen-agent import`, `xgen-agent run`)
- [ ] **Trace/Log 기본 구조** (실행 로그 수집)
- [ ] **State Store 기본** (PostgreSQL, 세션 저장/복구)

### Phase 2: AI 개발 + 샌드박스
- [ ] Docker Sandbox 환경 (격리 실행, 타임아웃, 리소스 제한)
- [ ] AI 도구 생성 기능 (코드 생성 → 샌드박스 테스트 → 등록)
- [ ] 멀티턴 대화 컨텍스트 (State Store 연동)
- [ ] Human-in-the-Loop (승인 대기 → 재개)
- [ ] 실패 재개 (Checkpointer 패턴)

### Phase 3: 플랫폼 통합
- [ ] xgen-frontend 대화 UI 연동
- [ ] xgen-backend-gateway 라우팅 추가
- [ ] MCP 클라이언트 (STDIO + SSE)
- [ ] graph-tool-call 연동 (검색 기반 동적 로딩)
- [ ] 고객사별 namespace 격리

### Phase 4: 운영 고도화
- [ ] 실행 이력 대시보드
- [ ] 권한 관리 (역할별 도구 접근 제어)
- [ ] Agent 버전 관리
- [ ] Webhook / 스케줄 트리거
- [ ] Langfuse / OpenTelemetry 연동

## 디렉토리 구조

```
xgen-agent/
├── src/
│   ├── core/               # Agent Core 엔진
│   │   ├── agent.py        # 마스터 루프 (Think → Act → Observe)
│   │   ├── planner.py      # 실행 계획 수립
│   │   └── context.py      # 대화 컨텍스트 관리
│   ├── tools/
│   │   ├── registry.py     # Tool Registry
│   │   ├── decorator.py    # @tool 데코레이터 정의
│   │   └── builtin/        # 빌트인 도구
│   │       ├── http.py     # HTTP 호출
│   │       ├── db.py       # DB 쿼리
│   │       └── file.py     # 파일 처리
│   ├── sandbox/
│   │   ├── runner.py       # 코드 실행 엔진
│   │   └── docker.py       # Docker 컨테이너 격리
│   ├── mcp/
│   │   ├── client.py       # MCP 클라이언트 (STDIO + SSE)
│   │   └── bridge.py       # MCP → @tool 변환
│   ├── store/
│   │   ├── state.py        # State Store (Checkpointer)
│   │   ├── agent_store.py  # Agent 정의 저장
│   │   └── history.py      # 실행 이력
│   ├── trace/
│   │   ├── collector.py    # 실행 로그 수집
│   │   └── exporter.py     # 외부 시스템 연동 (Langfuse 등)
│   └── api/
│       └── routes.py       # FastAPI 엔드포인트
├── tools/                   # 기본 제공 커스텀 도구 예제
├── agents/                  # 기본 제공 agent 정의 예제
├── tests/
├── Dockerfile
├── pyproject.toml
└── README.md
```

## xgen-workflow 교체 가이드

xgen-agent가 xgen-workflow를 대체하려면 인프라 설정과 다른 서비스 수정이 필요하다.

### 현재 xgen-workflow의 역할

```
xgen-frontend
    │  /api/workflow/* (REST)
    ▼
xgen-workflow (277개 .py, 9.2MB)
    │
    ├──→ xgen-core        (CORE_SERVICE_BASE_URL → /api/data/db/*, /api/data/config/*)
    ├──→ xgen-documents   (DOCUMENTS_SERVICE_BASE_URL → /api/embedding/*, /api/document-processor/*)
    └──→ xgen-mcp-station (MCP_STATION_BASE_URL → /api/mcp/*)
```

### xgen-workflow의 현재 API 엔드포인트

xgen-agent가 최소한 대체해야 할 핵심 엔드포인트:

| 분류 | 엔드포인트 | 용도 | xgen-agent 대응 |
|------|-----------|------|-----------------|
| **실행** | `POST /api/workflow/execute/based_id/stream` | 워크플로우 스트림 실행 | Agent Core 대화 실행 |
| **실행** | `POST /api/workflow/execute/based_id/stream/deploy` | 배포 모드 실행 | Agent 배포 실행 |
| **CRUD** | `GET /api/workflow/list` | 목록 조회 | Agent 목록 조회 |
| **CRUD** | `POST /api/workflow/save` | 저장 | Agent 정의 저장 |
| **CRUD** | `GET /api/workflow/deploy/load/{user_id}/{workflow_id}` | 로드 | Agent 로드 |
| **도구** | `/api/tools/*` | 도구 관리 | Tool Registry API |
| **MCP** | `/api/mcp/*` | MCP 통신 | MCP 클라이언트 |
| **헬스** | `GET /health` | 헬스 체크 | 동일 |

### 인프라 수정 파일 (xgen-infra)

#### P0: 필수 (서비스 교체)

| 파일 | 수정 내용 |
|------|----------|
| `k3s/helm-chart/values/xgen-workflow.yaml` | → `xgen-agent.yaml`로 교체 (serviceName 변경) |
| `k3s/argocd/projects/xgen.yaml` | `xgen-workflow` → `xgen-agent` (dev/prd 2곳) |
| `k3s/argocd/projects/xgen-son.yaml` | `xgen-workflow` → `xgen-agent` (prd/dev 2곳) |
| `k3s/argocd/projects/xgen-aww.yaml` | `xgen-workflow` → `xgen-agent` (aww 1곳) |
| `k3s/argocd/projects/xgen-jeju.yaml` | `xgen-workflow` → `xgen-agent` (prd/dev 2곳) |
| `k3s/argocd/projects/lotteimall.yaml` | `xgen-workflow` → `xgen-agent` (prd/dev 2곳) |
| `k3s/jenkins/config/services.yaml` | `xgen-workflow` → `xgen-agent` (repo, dockerfile 경로) |
| `k3s/jenkins/values-override.yaml` | 서비스 목록에서 이름 변경 |

#### P1: Dockerfile + API

| 파일 | 수정 내용 |
|------|----------|
| `dockerfiles/xgen-workflow/` | → `dockerfiles/xgen-agent/`로 교체. 주의: 현재 Chromium 포함된 별도 Dockerfile 사용 |
| xgen-frontend | `/api/workflow/*` 경로를 `/api/agent/*`로 변경 필요 (또는 하위 호환 유지) |

#### P2: 모니터링

| 파일 | 수정 내용 |
|------|----------|
| `k3s/observability/pod-restarter/cronjob.yaml` | `xgen-workflow` → `xgen-agent` |
| `k3s/observability/grafana/dashboards.yaml` | deployment 이름 변경 |
| `k3s/observability/grafana/alert-rules.yaml` | 알림 규칙 서비스명 변경 |

### 다른 서비스 수정 사항

#### xgen-frontend (수정 필요)

프론트엔드가 `xgen-workflow`를 호출하는 API 경로:

```
/api/workflow/list                              → 목록 조회
/api/workflow/save                              → 저장
/api/workflow/execute/based_id/stream           → 스트림 실행 (SSE)
/api/workflow/execute/based_id/stream/deploy    → 배포 모드 실행 (SSE)
/api/workflow/deploy/load/{user_id}/{id}        → 로드
/api/workflow/delete/{id}                       → 삭제
/api/workflow/copy                              → 복사
/api/workflow/share                             → 공유
/api/tools/*                                    → 도구 관리
/api/mcp/*                                      → MCP 관리
```

**선택지 2가지:**
1. **API 경로 유지** (`/api/workflow/*`) — xgen-agent에서 동일 prefix로 서빙. 프론트엔드 수정 최소화
2. **API 경로 변경** (`/api/agent/*`) — 프론트엔드 API 클라이언트 전면 수정. 깨끗하지만 작업량 큼

**권장: 1단계에서는 `/api/workflow/*` 유지 → 안정화 후 점진적으로 `/api/agent/*`로 마이그레이션**

#### xgen-backend-gateway (수정 불필요)

- gateway에서 workflow로의 직접 라우팅 설정 없음
- Kubernetes 내부 DNS (`http://xgen-workflow:8000`)로 통신
- Service 이름이 `xgen-agent`로 바뀌면 DNS도 자동 변경

#### xgen-core (수정 불필요)

- workflow가 core를 호출하는 구조 (역방향 의존 없음)
- core는 workflow의 존재를 모름

#### xgen-documents (수정 불필요)

- workflow가 documents를 호출하는 구조 (역방향 의존 없음)

#### xgen-mcp-station (장기적으로 흡수)

- 현재: workflow → mcp-station 호출
- 향후: xgen-agent에 MCP 클라이언트 내장 후 mcp-station 서비스 제거 가능
- **당장은 유지**, Phase 3에서 흡수

### 교체 순서

```
Phase 0: API 호환 레이어 (즉시 교체 가능하게)
  └─ xgen-agent에서 /api/workflow/* 경로 유지 (하위 호환)
  └─ /health 엔드포인트 동일하게 구현
  └─ 환경변수 동일 (CORE_SERVICE_BASE_URL 등)

Phase 1: 인프라 교체
  ├─ Dockerfile 준비 (dockerfiles/xgen-agent/)
  ├─ Helm values 생성 (xgen-agent.yaml)
  ├─ Jenkins 서비스 등록
  ├─ ArgoCD 프로젝트 업데이트 (5개 파일)
  └─ xgen-son 서버에서 먼저 검증

Phase 2: 프론트엔드 연동
  ├─ 기존 workflow UI는 유지하되 agent 대화 UI 추가
  ├─ SSE 스트리밍 경로 연동
  └─ Flow Viewer 구현

Phase 3: mcp-station 흡수
  ├─ MCP 클라이언트 xgen-agent에 내장
  ├─ mcp-station 서비스 제거
  └─ ArgoCD에서 mcp-station 삭제
```

### 환경변수 (xgen-agent에서 유지해야 할 것)

```yaml
# xgen-agent.yaml (Helm values)
config:
  CORE_SERVICE_BASE_URL: "http://xgen-core:8000"
  DOCUMENTS_SERVICE_BASE_URL: "http://xgen-documents:8000"
  MCP_STATION_BASE_URL: "http://xgen-mcp-station:8000"   # Phase 3까지 유지
```

## 참고 자료

### 벤치마킹 대상
- [CrewAI](https://github.com/crewAIInc/crewAI) — @tool 데코레이터, Role-based 에이전트
- [LangGraph](https://github.com/langchain-ai/langgraph) — 상태 그래프, Checkpointer 지속성
- [AutoGen](https://github.com/microsoft/autogen) — Docker 샌드박스, MCP 통합
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) — Handoff, 경량 오케스트레이션
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/sdk) — 마스터 루프, 파일시스템 중심
- [Dify](https://github.com/langgenius/dify) — DifySandbox, Workflow as Tool
- [Coze](https://github.com/coze-dev/coze-studio) — Coze Loop, 실행 추적/평가

### 관련 기술
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) — 도구 통합 표준
- [graph-tool-call](https://github.com/SonAIengine/graph-tool-call) — 검색 기반 도구 동적 로딩
- [E2B](https://e2b.dev/) — 프로덕션급 코드 샌드박스 (Firecracker microVM)
- [Daytona](https://daytona.io/) — 고속 AI 코드 실행 환경

