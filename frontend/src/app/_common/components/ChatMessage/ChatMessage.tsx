'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '../../types';
import { formatDuration } from '../../utils/formatTime';
import styles from './ChatMessage.module.scss';
import {
  FiUser,
  FiCpu,
  FiTool,
  FiChevronDown,
  FiChevronRight,
  FiCopy,
  FiCheck,
  FiAlertTriangle,
  FiClock,
  FiLoader,
  FiCheckCircle,
  FiXCircle,
  FiMessageSquare,
} from 'react-icons/fi';

interface ChatMessageProps {
  message: Message;
  onApprove?: (requestId: string, approved: boolean) => void;
}

function CodeBlock({
  language,
  value,
}: {
  language: string;
  value: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={styles.codeBlock}>
      <div className={styles.codeHeader}>
        <span className={styles.codeLang}>{language || 'code'}</span>
        <button className={styles.codeCopyBtn} onClick={handleCopy} title="복사">
          {copied ? <FiCheck size={13} /> : <FiCopy size={13} />}
          <span>{copied ? '복사됨' : '복사'}</span>
        </button>
      </div>
      <SyntaxHighlighter
        style={oneLight}
        language={language || 'text'}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: '0 0 8px 8px',
          fontSize: '0.8125rem',
          lineHeight: 1.6,
        }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
}

export default function ChatMessage({ message, onApprove }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [thinkOpen, setThinkOpen] = useState(false);
  const [toolOpen, setToolOpen] = useState<Record<string, boolean>>({});

  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleTool = (id: string) => {
    setToolOpen((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Markdown components with syntax highlighting
  const markdownComponents = useMemo(
    () => ({
      // Block code: pre > code — render with syntax highlighter
      pre(props: { children?: React.ReactNode }) {
        const { children } = props;
        // react-markdown wraps block code in <pre><code>
        // Extract the code element's props
        const child = children as React.ReactElement<{
          className?: string;
          children?: React.ReactNode;
        }>;
        if (child?.props) {
          const className = child.props.className || '';
          const match = /language-(\w+)/.exec(className);
          const value = String(child.props.children).replace(/\n$/, '');
          return <CodeBlock language={match ? match[1] : ''} value={value} />;
        }
        return <pre>{children}</pre>;
      },
      // Inline code
      code(props: { className?: string; children?: React.ReactNode }) {
        const { children, ...rest } = props;
        return (
          <code className={styles.inlineCode} {...rest}>
            {children}
          </code>
        );
      },
      table(props: React.HTMLAttributes<HTMLTableElement>) {
        return (
          <div className={styles.tableWrapper}>
            <table {...props} />
          </div>
        );
      },
    }),
    []
  );

  // Tool result message (separate message type)
  if (isTool && message.tool_result) {
    const tr = message.tool_result;
    return (
      <div className={`${styles.message} ${styles.toolMessage}`}>
        <div className={styles.avatar}>
          <FiTool size={16} />
        </div>
        <div className={styles.body}>
          <div
            className={`${styles.toolResult} ${
              tr.success ? styles.toolSuccess : styles.toolError
            }`}
          >
            <div className={styles.toolResultHeader}>
              {tr.success ? (
                <FiCheckCircle size={14} className={styles.toolSuccessIcon} />
              ) : (
                <FiXCircle size={14} className={styles.toolErrorIcon} />
              )}
              <span className={styles.toolResultName}>{tr.tool}</span>
              <span className={styles.toolResultStatus}>
                {tr.success ? '성공' : '실패'}
              </span>
              {tr.duration_ms > 0 && (
                <span className={styles.toolDuration}>
                  <FiClock size={11} />
                  {formatDuration(tr.duration_ms)}
                </span>
              )}
            </div>
            {tr.error && (
              <div className={styles.toolErrorText}>{tr.error}</div>
            )}
            {tr.success && tr.result != null && (
              <details className={styles.toolResultDetail}>
                <summary>결과 보기</summary>
                <pre className={styles.toolResultPre}>
                  {typeof tr.result === 'string'
                    ? tr.result
                    : JSON.stringify(tr.result, null, 2)}
                </pre>
              </details>
            )}
            {/* create_agent 성공 시 바로 대화하기 링크 */}
            {tr.tool === 'create_agent' && tr.success && tr.result != null && (() => {
              const r = tr.result as Record<string, unknown>;
              const agent = r.agent as Record<string, string> | undefined;
              const agentName = agent?.name || (r.name as string) || '';
              if (!agentName) return null;
              return (
                <Link href={`/chat/${agentName}`} className={styles.agentLink}>
                  <FiMessageSquare size={13} />
                  {agentName} 에이전트와 대화하기
                </Link>
              );
            })()}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.message} ${isUser ? styles.user : styles.assistant}`}>
      <div className={styles.avatar}>
        {isUser ? <FiUser size={18} /> : <FiCpu size={18} />}
      </div>

      <div className={styles.body}>
        {/* Think Block */}
        {message.think && (
          <div className={styles.thinkBlock}>
            <button
              className={styles.thinkToggle}
              onClick={() => setThinkOpen(!thinkOpen)}
            >
              {thinkOpen ? <FiChevronDown size={14} /> : <FiChevronRight size={14} />}
              <span className={styles.thinkLabel}>
                {message.is_streaming && !message.content
                  ? '추론 중...'
                  : '추론 과정'}
              </span>
              {message.is_streaming && !message.content && (
                <FiLoader size={12} className={styles.spinIcon} />
              )}
            </button>
            {thinkOpen && (
              <div className={styles.thinkContent}>{message.think}</div>
            )}
          </div>
        )}

        {/* Tool Calls */}
        {message.tool_calls?.map((tc) => (
          <div key={tc.id} className={styles.toolCall}>
            <button
              className={styles.toolHeader}
              onClick={() => toggleTool(tc.id)}
            >
              <FiTool size={14} className={styles.toolIcon} />
              <span className={styles.toolName}>{tc.tool}</span>
              <span className={styles.toolBadge}>호출</span>
              {toolOpen[tc.id] ? (
                <FiChevronDown size={14} />
              ) : (
                <FiChevronRight size={14} />
              )}
            </button>
            {toolOpen[tc.id] && (
              <pre className={styles.toolParams}>
                {JSON.stringify(tc.params, null, 2)}
              </pre>
            )}
          </div>
        ))}

        {/* Content with Markdown */}
        {message.content && (
          <div className={`${styles.content} ${!isUser ? styles.markdownContent : ''}`}>
            {isUser ? (
              <>
                {message.content}
              </>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={markdownComponents}
              >
                {message.content}
              </ReactMarkdown>
            )}
            {message.is_streaming && <span className={styles.cursor} />}
          </div>
        )}

        {/* Approval */}
        {message.approval && message.approval.status === 'pending' && (
          <div className={styles.approval}>
            <div className={styles.approvalHeader}>
              <FiAlertTriangle size={16} />
              <span>승인 필요</span>
            </div>
            <div className={styles.approvalAction}>{message.approval.action}</div>
            <div className={styles.approvalReason}>{message.approval.reason}</div>
            <div className={styles.approvalButtons}>
              <button
                className={styles.approveBtn}
                onClick={() => onApprove?.(message.approval?.request_id || '', true)}
              >
                승인
              </button>
              <button
                className={styles.denyBtn}
                onClick={() => onApprove?.(message.approval?.request_id || '', false)}
              >
                거부
              </button>
            </div>
          </div>
        )}

        {/* Actions */}
        {!isUser && message.content && !message.is_streaming && (
          <div className={styles.actions}>
            <button onClick={handleCopy} title="복사">
              {copied ? <FiCheck size={14} /> : <FiCopy size={14} />}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
