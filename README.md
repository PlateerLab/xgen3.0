# YAMMI

**Conversational AI Agent Runtime Platform** — Build, run, and deploy AI agents through a single chat interface.

xgen-agent replaces the traditional visual workflow editor (xgen-workflow) with a conversation-first approach: the AI itself develops, executes, verifies, and deploys agents and workflows. No drag-and-drop nodes. No complex abstractions. Just tools and conversation.

## Key Principles

1. **Shell Only** — No visual editor, no node system. Runtime + tool interface only.
2. **AI-first, Human-compatible** — Whether AI or human creates it, the output format is identical.
3. **Simple Architecture** — Everything composes at the Tool level. No unnecessary abstractions.
4. **Single Agent** — Multi-agent orchestration is unnecessary. Tools are sufficient.
5. **Observability from Day 1** — Execution logs and tracing are built-in, not bolted on.

## Architecture

```
                    xgen-agent-frontend (port 3000)
                    Conversation UI — single input
                              |
                    xgen-agent (port 8010)
                    ┌─────────────────────────────────┐
                    │  Agent Core (Think→Act→Observe)  │
                    │  Tool Registry (40 tools)        │
                    │  State Store (Checkpointer)      │
                    │  Trace / Log                     │
                    │  Docker Sandbox                  │
                    └─────────┬───────────────────────┘
                              |
              ┌───────────────┼───────────────┐
              v               v               v
         xgen-core       xgen-documents    External APIs
         (port 8001)     (port 8002)       (MCP, etc.)
         DB / Config     RAG / Embedding
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-org/xgen-agent.git
cd xgen-agent

# 2. Set environment
cp .env.example .env
# Edit .env — set MODEL_API_KEY (OpenAI or compatible)

# 3. Launch everything
docker compose up -d --build

# 4. Open browser
open http://localhost:3000
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `xgen-agent-frontend` | 3000 | Conversation UI (Next.js 15) |
| `xgen-agent` | 8010 | Agent runtime + API |
| `xgen-core` | 8001 | Database & config management |
| `postgres` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis (config cache) |

### API Documentation

Swagger UI is available at `http://localhost:8010/docs`

## How It Works

### The Master Loop

```python
while True:
    response = await model.generate(messages, tools=available_tools)
    if not response.tool_calls:
        return response.text           # Done — return answer
    for tool_call in response.tool_calls:
        result = await tool_registry.execute(tool_call)
        messages.append(tool_result(result))  # Feed back to model
```

The agent follows a **Think → Act → Observe** loop inspired by Claude Code's architecture. The LLM decides which tools to call, executes them, observes results, and iterates until it can answer.

### Tool System

All tools are defined with the `@tool` decorator — the single universal interface:

```python
from xgen_agent import tool

@tool(
    name="query_customer",
    description="Query customer info from DB by customer_id. Returns name, contact, and signup date.",
    parameters={
        "customer_id": {"type": "string", "description": "Customer ID (e.g., CUST-001)"}
    }
)
async def query_customer(customer_id: str) -> dict:
    ...
```

### Three Tool Sources

| Source | Description |
|--------|-------------|
| `@tool` (Built-in + Custom) | Python functions with decorator. Same format whether AI or human creates them. |
| `MCP` | External MCP server connections (STDIO + SSE). |
| `graph-tool-call` | Search-based dynamic loading. Always active — queries find the right tools from 40+. |

### Registered Tools (40)

**Built-in (7):** http_request, file_read, file_write, file_list, db_query, execute_code, execute_code_with_test

**xgen-core Integration (13):** core_db_tables, core_db_schema, core_db_find, core_db_find_by_id, core_db_insert, core_db_update, core_db_delete, core_db_query, core_config_get, core_config_set, core_config_list, core_config_search, core_auth_headers

**xgen-documents Integration (9):** rag_search, rag_collections, rag_collection_documents, embedding_query, embedding_documents, rerank_documents, document_extract_text, document_generate_metadata, document_supported_types

**Agent Management (6):** create_agent, list_agents, get_agent, update_agent, delete_agent, list_available_tools

**Utility (5):** send_email, read_table_data, write_table_data, ml_inference, run_workflow

## Agent Definition

Agents are defined in YAML and stored in PostgreSQL:

```yaml
name: customer-support
description: Customer inquiry response agent
model: gpt-4o-mini
tools:
  - core_db_find
  - core_db_schema
  - rag_search
  - http_request
system_prompt: |
  You are a customer support agent.
  Query customer data and order history to answer inquiries.
approval_required:
  - "DELETE *"
```

## Frontend

The frontend is a **conversation-first UI** built with Next.js 15 + React 19:

- **Chat** (`/chat`) — Start a conversation immediately. No agent selection needed. AI creates agents on demand.
- **Chat with Agent** (`/chat/[agentId]`) — SSE streaming with Think blocks, tool call visualization, approval buttons
- **Dashboard** (`/`) — Agent overview and quick chat start
- **Agent Management** (`/agents`) — List, create, and configure agents
- **Trace List** (`/trace`) — Paginated trace list with step badges and duration
- **Trace Detail** (`/trace/[traceId]`) — Read-only execution flow timeline with expandable steps
- **Execution History** (`/history`) — Full execution log with agent filter and trace links
- **Settings** (`/settings`) — Service status, tool registry, MCP connections

No visual workflow editor. Modifications happen through conversation.

## SSE Event Flow

The chat interface receives real-time SSE events:

```
event: log          → "Thinking... (iteration 1)"
event: tool         → Tool call: core_db_find({table: "orders"})
event: tool         → Tool result: {success: true, data: [...]}
event: log          → "Thinking... (iteration 2)"
data: {type: data}  → "Here are your recent orders: ..."
data: {type: end}   → Stream finished
```

## Project Structure

```
xgen-agent/
├── src/
│   ├── api/            # FastAPI endpoints + SSE adapter
│   ├── core/           # Agent Core (master loop, context, planner)
│   ├── tools/          # Tool registry, @tool decorator, builtins
│   │   └── builtin/    # http, file, db, xgen_core, xgen_documents, agent_mgmt
│   ├── sandbox/        # Docker code execution
│   ├── mcp/            # MCP client + bridge
│   ├── store/          # State, agent definitions, history (PostgreSQL)
│   └── trace/          # Execution log collector + exporter
├── frontend/           # Next.js 15 conversation UI
├── tests/              # 116 tests (pytest)
├── docker-compose.yml  # Full stack: postgres + redis + core + agent + frontend
├── Dockerfile          # Agent backend image
└── plan.md             # Architecture & design document
```

## API Endpoints

### Core Endpoints

```
POST /api/workflow/execute/based_id/stream       # SSE streaming chat
POST /api/workflow/save                          # Save agent definition
GET  /api/workflow/list                          # List agents
GET  /api/tools/list                             # List registered tools
POST /api/tools/search                           # graph-tool-call search
POST /api/approval/action                        # Approve/reject pending action
GET  /api/approval/pending                       # List pending approvals
GET  /api/history                                # Execution history
GET  /api/workflow/trace/list                    # Trace list (paginated)
GET  /api/workflow/trace/detail/{trace_id}       # Trace detail
GET  /health                                     # Health check
```

### Compatibility

xgen-agent maintains full API compatibility with xgen-workflow endpoints under `/api/workflow/*`. This allows drop-in replacement without frontend changes.

## Development

### Run Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v   # 116 tests, ~2.3s
```

### Local Development (without Docker)

```bash
# Terminal 1: Backend
pip install -e .
python cli.py serve   # Starts on port 8000

# Terminal 2: Frontend
cd frontend && npm install && npm run dev   # Starts on port 3000
```

### CLI Commands

```bash
python cli.py serve              # Start API server
python cli.py import ./tools/    # Import custom tools
python cli.py tools              # List registered tools
python cli.py run "Hello"        # Run agent from CLI
python cli.py connect mcp --url  # Connect MCP server
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+, FastAPI |
| Frontend | Next.js 15, React 19, TypeScript |
| Database | PostgreSQL 16 |
| Cache | Redis 8 |
| LLM | OpenAI API compatible (GPT-4o-mini, Claude, local LLM) |
| Sandbox | Docker containers |
| MCP | STDIO + SSE client |
| Tool Search | graph-tool-call 0.13.1 |

## Benchmarking

Architecture decisions were informed by analysis of 7 frameworks:

- **CrewAI** → `@tool` decorator pattern
- **LangGraph** → State Store (Checkpointer)
- **AutoGen** → Docker sandbox, MCP integration
- **OpenAI Agents SDK** → Single agent loop (no multi-agent needed)
- **Claude Agent SDK** → Think → Act → Observe master loop
- **Dify** → Sandbox isolation strategy
- **Coze** → Execution tracing from day 1

**Deliberately excluded:** Visual workflow editors, multi-agent orchestration, LangChain dependency, deep abstraction layers.

## Roadmap

- [x] Phase 1: MVP — Agent Core, @tool, Registry, State Store, Trace
- [x] Phase 2: AI Development — Docker Sandbox, AI tool generation, Human-in-the-Loop
- [x] Phase 3: Platform Integration — MCP client, graph-tool-call, Frontend
- [x] Phase 4: Operations — Permissions, versioning, triggers, config management
- [x] Phase 4.5: Observability UI — Trace viewer, execution history, approval e2e
- [x] Phase 4.5: Mode A — Direct chat, agent creation via conversation, graph search always-on
- [ ] Phase 5: Production — OpenTelemetry, Langfuse, multi-tenant isolation

## License

Proprietary. Internal use only.
