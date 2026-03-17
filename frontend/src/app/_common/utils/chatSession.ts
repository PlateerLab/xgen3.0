/**
 * 대화 세션 관리 — sessionStorage 기반
 *
 * 페이지 이동 시에도 세션이 유지되도록 sessionStorage에 저장.
 * agentId별로 독립적인 세션을 관리.
 */

import type { Message, HistoryEntry } from '../types';

const SESSION_KEY_PREFIX = 'xgen_chat_session_';
const MESSAGES_KEY_PREFIX = 'xgen_chat_messages_';

function sessionKey(agentId: string): string {
  return `${SESSION_KEY_PREFIX}${agentId}`;
}

function messagesKey(agentId: string): string {
  return `${MESSAGES_KEY_PREFIX}${agentId}`;
}

/** sessionId 저장 */
export function saveSessionId(agentId: string, sessionId: string): void {
  try {
    sessionStorage.setItem(sessionKey(agentId), sessionId);
  } catch { /* SSR or quota exceeded */ }
}

/** sessionId 복원 */
export function loadSessionId(agentId: string): string | null {
  try {
    return sessionStorage.getItem(sessionKey(agentId));
  } catch {
    return null;
  }
}

/** 메시지 배열 저장 (페이지 이동 시 보존) */
export function saveMessages(agentId: string, messages: Message[]): void {
  try {
    sessionStorage.setItem(messagesKey(agentId), JSON.stringify(messages));
  } catch { /* quota exceeded — 무시 */ }
}

/** 메시지 배열 복원 */
export function loadMessages(agentId: string): Message[] {
  try {
    const raw = sessionStorage.getItem(messagesKey(agentId));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/** 세션 클리어 (새 대화 시작 시) */
export function clearSession(agentId: string): void {
  try {
    sessionStorage.removeItem(sessionKey(agentId));
    sessionStorage.removeItem(messagesKey(agentId));
  } catch { /* ignore */ }
}

/**
 * 백엔드 HistoryEntry[] → Message[] 변환
 *
 * 실행 이력을 대화 메시지 형태로 복원한다.
 * trace_data의 step 정보로 도구 호출도 복원.
 */
export function historyToMessages(entries: HistoryEntry[]): Message[] {
  const messages: Message[] = [];

  // 오래된 순서로 정렬 (id 오름차순)
  const sorted = [...entries].sort((a, b) => (a.id ?? 0) - (b.id ?? 0));

  for (const entry of sorted) {
    // 사용자 메시지
    if (entry.user_input) {
      messages.push({
        id: `h-u-${entry.id}`,
        role: 'user',
        content: entry.user_input,
        timestamp: entry.created_at || new Date().toISOString(),
      });
    }

    // trace_data에서 도구 호출 복원
    let traceData: { steps?: Array<Record<string, unknown>> } = {};
    if (entry.trace_data) {
      try {
        traceData = typeof entry.trace_data === 'string'
          ? JSON.parse(entry.trace_data)
          : entry.trace_data;
      } catch { /* ignore */ }
    }

    const steps = traceData.steps || [];
    for (const step of steps) {
      if (step.type === 'tool_call' && step.tool) {
        // 도구 호출 결과
        messages.push({
          id: `h-t-${entry.id}-${step.tool}`,
          role: 'tool',
          content: '',
          timestamp: entry.created_at || new Date().toISOString(),
          tool_result: {
            tool_call_id: `h-tc-${entry.id}-${step.tool}`,
            tool: step.tool as string,
            result: step.result,
            duration_ms: (step.duration_ms as number) || 0,
            success: (step.success as boolean) ?? true,
          },
        });
      }
    }

    // 어시스턴트 응답
    if (entry.result) {
      messages.push({
        id: `h-a-${entry.id}`,
        role: 'assistant',
        content: entry.result,
        timestamp: entry.created_at || new Date().toISOString(),
      });
    }
  }

  return messages;
}
