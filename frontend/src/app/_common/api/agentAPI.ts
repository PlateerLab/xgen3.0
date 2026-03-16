import { apiFetch, apiSSE } from './client';
import type { Agent, AgentSummary, Session, Trace, SSEEvent } from '../types';

// --- Agent CRUD ---
// /api/workflow/* 하위호환 경로 사용

export async function listAgents(): Promise<AgentSummary[]> {
  const res = await apiFetch('/api/workflow/list');
  const agents = res.agents ?? res;
  if (!Array.isArray(agents)) return [];
  return agents.map((a: Record<string, unknown>) => ({
    id: String(a.id ?? a.workflow_id ?? ''),
    name: String(a.name ?? a.workflow_name ?? ''),
    description: String(a.description ?? ''),
    model: String(a.model ?? ''),
    tool_count: Array.isArray(a.tools) ? a.tools.length : Number(a.tool_count ?? 0),
    status: (a.status as AgentSummary['status']) ?? 'active',
    last_run: a.updated_at as string | undefined,
  }));
}

export async function getAgent(agentId: string): Promise<Agent> {
  return apiFetch(`/api/workflow/deploy/load/${agentId}`);
}

export async function saveAgent(agent: Partial<Agent>): Promise<Agent> {
  return apiFetch('/api/workflow/save', {
    method: 'POST',
    body: JSON.stringify(agent),
  });
}

export async function deleteAgent(agentId: string): Promise<void> {
  return apiFetch(`/api/workflow/delete/${agentId}`, {
    method: 'DELETE',
  });
}

// --- Session ---

export async function listSessions(agentId: string): Promise<Session[]> {
  return apiFetch(`/api/workflow/sessions?agent_id=${agentId}`);
}

export async function getSession(sessionId: string): Promise<Session> {
  return apiFetch(`/api/workflow/sessions/${sessionId}`);
}

// --- Chat (SSE Streaming) ---

export function streamChat(
  agentId: string,
  message: string,
  sessionId: string | null,
  onEvent: (event: SSEEvent) => void,
  onDone?: () => void,
  onError?: (error: Error) => void
): AbortController {
  return apiSSE(
    '/api/workflow/execute/based_id/stream',
    {
      workflow_name: agentId,
      workflow_id: agentId,
      input_data: message,
      interaction_id: sessionId,
    },
    (eventType, rawData) => {
      try {
        const parsed = JSON.parse(rawData);

        // xgen-workflow SSE 포맷 → xgen3.0 프론트엔드 포맷 변환
        if (eventType === 'log') {
          // log 이벤트 → think 계열로 매핑
          const msg = parsed.message || '';
          if (msg.startsWith('Thinking')) {
            onEvent({ event: 'think_start', data: {} });
            onEvent({ event: 'think_delta', data: { text: msg } });
            onEvent({ event: 'think_done', data: {} });
          }
          return;
        }

        if (eventType === 'tool') {
          // tool 이벤트 → tool_call 계열로 매핑
          if (parsed.event_type === 'tool_call') {
            onEvent({
              event: 'tool_call_start',
              data: {
                tool_call_id: `tc-${Date.now()}`,
                tool: parsed.tool_name,
                params: parsed.tool_input || {},
              },
            });
          } else if (parsed.event_type === 'tool_result') {
            onEvent({
              event: 'tool_call_done',
              data: {
                tool_call_id: `tc-${Date.now()}`,
                tool: parsed.tool_name,
                result: parsed.result,
                duration_ms: 0,
                success: true,
              },
            });
          }
          return;
        }

        // data-only 이벤트 (event 필드 없음 = "message")
        if (parsed.type === 'data') {
          onEvent({
            event: 'content_delta',
            data: { text: parsed.content || '' },
          });
        } else if (parsed.type === 'end') {
          onEvent({ event: 'done', data: {} });
        } else if (parsed.type === 'error') {
          onEvent({
            event: 'error',
            data: { message: parsed.detail || 'Unknown error' },
          });
        }
      } catch {
        // 파싱 실패 시 텍스트로 처리
        onEvent({ event: 'content_delta', data: { text: rawData } });
      }
    },
    onDone,
    onError
  );
}

// --- Approval ---

export async function respondApproval(
  sessionId: string,
  approved: boolean
): Promise<void> {
  return apiFetch('/api/workflow/approval', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, approved }),
  });
}

// --- Trace ---

export async function getTrace(traceId: string): Promise<Trace> {
  return apiFetch(`/api/workflow/trace/${traceId}`);
}

export async function listTraces(
  agentId: string,
  limit = 20
): Promise<Trace[]> {
  return apiFetch(`/api/workflow/traces?agent_id=${agentId}&limit=${limit}`);
}

// --- Tools ---

export async function listTools(): Promise<
  { name: string; description: string; source: string }[]
> {
  return apiFetch('/api/tools/list');
}
