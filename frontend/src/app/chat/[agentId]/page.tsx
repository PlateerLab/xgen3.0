'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import type { Message, SSEEvent, Agent } from '../../_common/types';
import { streamChat, respondApproval, getAgent, listHistory as fetchSessionHistory } from '../../_common/api/agentAPI';
import ChatMessage from '../../_common/components/ChatMessage';
import {
  saveSessionId,
  loadSessionId,
  saveMessages,
  loadMessages,
  historyToMessages,
} from '../../_common/utils/chatSession';
import styles from './page.module.scss';
import {
  FiSend,
  FiPaperclip,
  FiStopCircle,
  FiBox,
  FiActivity,
  FiMessageSquare,
  FiDatabase,
  FiTool,
  FiSearch,
} from 'react-icons/fi';

const EXAMPLE_PROMPTS = [
  { icon: FiDatabase, text: 'DB 테이블 목록 조회해줘' },
  { icon: FiTool, text: '사용 가능한 도구 알려줘' },
  { icon: FiSearch, text: '최근 실행 로그 확인해줘' },
  { icon: FiMessageSquare, text: '이 에이전트가 할 수 있는 일 알려줘' },
];

export default function ChatPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [traceId, setTraceId] = useState<string | null>(null);
  const [agentInfo, setAgentInfo] = useState<Agent | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load agent info
  useEffect(() => {
    getAgent(agentId)
      .then(setAgentInfo)
      .catch(() => setAgentInfo(null));
  }, [agentId]);

  // Restore session from sessionStorage → fallback to backend history
  useEffect(() => {
    const cached = loadMessages(agentId);
    const sid = loadSessionId(agentId);
    if (cached.length > 0) {
      setMessages(cached);
      if (sid) setSessionId(sid);
      return;
    }
    if (sid) {
      setSessionId(sid);
      fetchSessionHistory(undefined, sid, 100)
        .then((res) => {
          const restored = historyToMessages(res.history ?? []);
          if (restored.length > 0) setMessages(restored);
        })
        .catch(() => {});
    }
  }, [agentId]);

  // Persist messages + sessionId to sessionStorage on change
  useEffect(() => {
    if (messages.length > 0) saveMessages(agentId, messages);
  }, [messages, agentId]);

  useEffect(() => {
    if (sessionId) saveSessionId(agentId, sessionId);
  }, [sessionId, agentId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
    }
  }, [input]);

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;

      // Add user message
      const userMsg: Message = {
        id: `u-${Date.now()}`,
        role: 'user',
        content: trimmed,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setIsStreaming(true);

      // 현재 assistant 메시지 ID를 추적 (도구 호출 후 새 메시지 생성용)
      let currentAssistantId = `a-${Date.now()}`;
      let hasToolCalls = false;

      const addAssistantMsg = () => {
        const msg: Message = {
          id: currentAssistantId,
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          is_streaming: true,
        };
        setMessages((prev) => [...prev, msg]);
      };

      // 최초 assistant 메시지
      addAssistantMsg();

      const updateAssistant = (updater: (msg: Message) => Message) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === currentAssistantId ? updater(m) : m))
        );
      };

      // 도구 호출 이후 새 assistant 메시지를 맨 아래에 추가
      const ensureNewAssistantAfterTools = () => {
        if (hasToolCalls) {
          currentAssistantId = `a-${Date.now()}-reply`;
          addAssistantMsg();
          hasToolCalls = false;
        }
      };

      abortRef.current = streamChat(
        agentId,
        trimmed,
        sessionId,
        // onEvent
        (event: SSEEvent) => {
          const { data } = event;

          switch (event.event) {
            case 'message_start':
              if (data.session_id) {
                setSessionId(data.session_id as string);
              }
              if (data.trace_id) {
                setTraceId(data.trace_id as string);
              }
              break;

            case 'content_delta':
              ensureNewAssistantAfterTools();
              updateAssistant((m) => ({
                ...m,
                content: m.content + (data.text || ''),
              }));
              break;

            case 'think_start':
              updateAssistant((m) => ({
                ...m,
                think: '',
              }));
              break;

            case 'think_delta':
              updateAssistant((m) => ({
                ...m,
                think: (m.think || '') + (data.text || ''),
              }));
              break;

            case 'tool_call_start':
              updateAssistant((m) => ({
                ...m,
                tool_calls: [
                  ...(m.tool_calls || []),
                  {
                    id: (data.tool_call_id as string) || `tc-${Date.now()}`,
                    tool: data.tool as string,
                    params: (data.params as Record<string, unknown>) || {},
                  },
                ],
              }));
              break;

            case 'tool_call_done':
              hasToolCalls = true;
              setMessages((prev) => [
                ...prev,
                {
                  id: `tr-${Date.now()}`,
                  role: 'tool' as const,
                  content: '',
                  timestamp: new Date().toISOString(),
                  tool_result: {
                    tool_call_id: data.tool_call_id as string,
                    tool: data.tool as string,
                    result: data.result,
                    duration_ms: (data.duration_ms as number) || 0,
                    success: (data.success as boolean) ?? true,
                    error: data.error as string | undefined,
                  },
                },
              ]);
              break;

            case 'approval_required':
              updateAssistant((m) => ({
                ...m,
                approval: {
                  request_id: (data.request_id as string) || '',
                  action: data.action as string,
                  reason: data.reason as string,
                  status: 'pending' as const,
                },
                is_streaming: false,
              }));
              break;

            case 'error':
              ensureNewAssistantAfterTools();
              updateAssistant((m) => ({
                ...m,
                content: m.content + `\n\n오류: ${data.message || '알 수 없는 오류'}`,
                is_streaming: false,
              }));
              setIsStreaming(false);
              break;

            case 'done':
              updateAssistant((m) => ({
                ...m,
                is_streaming: false,
              }));
              setIsStreaming(false);
              break;
          }
        },
        // onDone
        () => {
          updateAssistant((m) => ({
            ...m,
            is_streaming: false,
          }));
          setIsStreaming(false);
        },
        // onError
        (err) => {
          ensureNewAssistantAfterTools();
          updateAssistant((m) => ({
            ...m,
            content: m.content + `\n\n연결 오류: ${err.message}`,
            is_streaming: false,
          }));
          setIsStreaming(false);
        }
      );
    },
    [isStreaming, agentId, sessionId]
  );

  const handleSend = useCallback(() => {
    sendMessage(input);
  }, [input, sendMessage]);

  const handleStop = () => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setMessages((prev) =>
      prev.map((m) => (m.is_streaming ? { ...m, is_streaming: false } : m))
    );
  };

  const handleApproval = async (requestId: string, approved: boolean) => {
    try {
      await respondApproval(requestId, approved);
      setMessages((prev) =>
        prev.map((m) =>
          m.approval?.request_id === requestId
            ? {
                ...m,
                approval: {
                  ...m.approval,
                  status: approved ? 'approved' : 'denied',
                },
              }
            : m
        )
      );
    } catch {
      // handle error
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const displayName = agentInfo?.name || agentId;
  const displayDesc = agentInfo?.description || '';

  return (
    <div className={styles.chatPage}>
      {/* Header */}
      <header className={styles.chatHeader}>
        <div className={styles.headerLeft}>
          <FiBox size={18} />
          <div className={styles.headerInfo}>
            <span className={styles.agentName}>{displayName}</span>
            {displayDesc && (
              <span className={styles.agentDesc}>{displayDesc}</span>
            )}
          </div>
        </div>
        <div className={styles.headerRight}>
          {agentInfo && (
            <span className={styles.modelBadge}>{agentInfo.model}</span>
          )}
          {traceId && (
            <Link href={`/trace/${traceId}`} className={styles.traceLink}>
              <FiActivity size={14} />
              Trace
            </Link>
          )}
        </div>
      </header>

      {/* Messages */}
      <div className={styles.messages}>
        {messages.length === 0 && (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>
              <FiBox size={40} />
            </div>
            <h2>{displayName}</h2>
            {displayDesc && <p className={styles.emptyDesc}>{displayDesc}</p>}
            <p className={styles.emptyHint}>
              무엇이든 물어보세요. Agent가 도구를 사용해 답변합니다.
            </p>
            <div className={styles.examplePrompts}>
              {EXAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt.text}
                  className={styles.exampleBtn}
                  onClick={() => sendMessage(prompt.text)}
                >
                  <prompt.icon size={16} />
                  <span>{prompt.text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            message={msg}
            onApprove={handleApproval}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className={styles.inputArea}>
        <div className={styles.inputContainer}>
          <button className={styles.attachBtn} title="파일 첨부">
            <FiPaperclip size={18} />
          </button>

          <textarea
            ref={textareaRef}
            className={styles.textarea}
            placeholder="메시지를 입력하세요... (Shift+Enter: 줄바꿈)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isStreaming}
          />

          {isStreaming ? (
            <button className={styles.stopBtn} onClick={handleStop}>
              <FiStopCircle size={20} />
            </button>
          ) : (
            <button
              className={styles.sendBtn}
              onClick={handleSend}
              disabled={!input.trim()}
            >
              <FiSend size={18} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
