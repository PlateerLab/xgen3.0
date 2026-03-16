'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import type { Message, SSEEvent, AgentSummary, HistoryEntry } from '../_common/types';
import { streamChat, listAgents, listHistory } from '../_common/api/agentAPI';
import ChatMessage from '../_common/components/ChatMessage';
import { formatRelativeTime, formatDuration } from '../_common/utils/formatTime';
import styles from './chat.module.scss';
import {
  FiSend,
  FiStopCircle,
  FiBox,
  FiMessageSquare,
  FiClock,
  FiZap,
  FiTool,
  FiActivity,
  FiChevronDown,
  FiChevronUp,
} from 'react-icons/fi';

const QUICK_PROMPTS = [
  { icon: FiZap, text: '고객 문의 에이전트 만들어줘' },
  { icon: FiTool, text: '사용 가능한 도구 알려줘' },
  { icon: FiBox, text: '등록된 에이전트 목록 보여줘' },
  { icon: FiMessageSquare, text: '안녕! 뭘 할 수 있어?' },
];

export default function ChatIndex() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showAgents, setShowAgents] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load agents + history
  useEffect(() => {
    listAgents().then(setAgents).catch(() => {});
    listHistory(undefined, undefined, 20)
      .then((res) => setHistory(res.history ?? []))
      .catch(() => {});
  }, []);

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

      const userMsg: Message = {
        id: `u-${Date.now()}`,
        role: 'user',
        content: trimmed,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setIsStreaming(true);

      const assistantId = `a-${Date.now()}`;
      const assistantMsg: Message = {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        is_streaming: true,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      const updateAssistant = (updater: (msg: Message) => Message) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? updater(m) : m))
        );
      };

      // default 에이전트 (메타 에이전트)로 대화
      abortRef.current = streamChat(
        'default',
        trimmed,
        sessionId,
        (event: SSEEvent) => {
          const { data } = event;
          switch (event.event) {
            case 'message_start':
              if (data.session_id) setSessionId(data.session_id as string);
              break;
            case 'content_delta':
              updateAssistant((m) => ({
                ...m,
                content: m.content + (data.text || ''),
              }));
              break;
            case 'think_start':
              updateAssistant((m) => ({ ...m, think: '' }));
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
            case 'error':
              updateAssistant((m) => ({
                ...m,
                content: m.content + `\n\n오류: ${data.message || '알 수 없는 오류'}`,
                is_streaming: false,
              }));
              setIsStreaming(false);
              break;
            case 'done':
              updateAssistant((m) => ({ ...m, is_streaming: false }));
              setIsStreaming(false);
              break;
          }
        },
        () => {
          updateAssistant((m) => ({ ...m, is_streaming: false }));
          setIsStreaming(false);
        },
        (err) => {
          updateAssistant((m) => ({
            ...m,
            content: m.content + `\n\n연결 오류: ${err.message}`,
            is_streaming: false,
          }));
          setIsStreaming(false);
        }
      );
    },
    [isStreaming, sessionId]
  );

  const handleStop = () => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setMessages((prev) =>
      prev.map((m) => (m.is_streaming ? { ...m, is_streaming: false } : m))
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const hasMessages = messages.length > 0;

  return (
    <div className={styles.chatPage}>
      {/* Header */}
      <header className={styles.chatHeader}>
        <div className={styles.headerLeft}>
          <FiZap size={18} />
          <span className={styles.headerTitle}>XGEN Assistant</span>
        </div>
      </header>

      {/* Messages area */}
      <div className={styles.messagesArea}>
        {!hasMessages ? (
          <div className={styles.welcomeState}>
            <div className={styles.welcomeIcon}>
              <FiZap size={40} />
            </div>
            <h1>무엇을 도와드릴까요?</h1>
            <p className={styles.welcomeDesc}>
              에이전트를 만들거나, 도구를 활용하거나, 무엇이든 물어보세요.
            </p>

            {/* Quick Prompts */}
            <div className={styles.quickPrompts}>
              {QUICK_PROMPTS.map((p) => (
                <button
                  key={p.text}
                  className={styles.quickBtn}
                  onClick={() => sendMessage(p.text)}
                >
                  <p.icon size={16} />
                  <span>{p.text}</span>
                </button>
              ))}
            </div>

            {/* Recent History */}
            {history.length > 0 && (
              <div className={styles.recentSection}>
                <h3 className={styles.recentTitle}>
                  <FiClock size={14} />
                  최근 대화
                </h3>
                <div className={styles.recentList}>
                  {history.slice(0, 5).map((h) => (
                    <div
                      key={h.id}
                      className={styles.recentItem}
                      onClick={() => sendMessage(h.user_input)}
                    >
                      <span className={styles.recentInput}>{h.user_input}</span>
                      <span className={styles.recentMeta}>
                        {h.agent_name} · {formatRelativeTime(h.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Registered Agents */}
            {agents.length > 0 && (
              <div className={styles.agentsSection}>
                <button
                  className={styles.agentsToggle}
                  onClick={() => setShowAgents(!showAgents)}
                >
                  <FiBox size={14} />
                  등록된 에이전트 ({agents.length})
                  {showAgents ? <FiChevronUp size={14} /> : <FiChevronDown size={14} />}
                </button>
                {showAgents && (
                  <div className={styles.agentList}>
                    {agents.map((agent) => (
                      <Link
                        key={agent.id}
                        href={`/chat/${agent.id}`}
                        className={styles.agentOption}
                      >
                        <FiBox size={16} />
                        <div className={styles.agentOptionInfo}>
                          <span className={styles.agentOptionName}>{agent.name}</span>
                          <span className={styles.agentOptionDesc}>{agent.description}</span>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className={styles.inputArea}>
        <div className={styles.inputContainer}>
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
              onClick={() => sendMessage(input)}
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
