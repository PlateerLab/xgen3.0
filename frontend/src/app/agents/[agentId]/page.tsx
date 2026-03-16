'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import type { Agent, Trace } from '../../_common/types';
import { getAgent, listTraces } from '../../_common/api/agentAPI';
import { formatRelativeTime, formatDuration } from '../../_common/utils/formatTime';
import styles from './page.module.scss';
import {
  FiArrowLeft,
  FiMessageSquare,
  FiBox,
  FiTool,
  FiCpu,
  FiShield,
  FiActivity,
  FiClock,
} from 'react-icons/fi';

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'overview' | 'tools' | 'history'>('overview');

  useEffect(() => {
    Promise.all([
      getAgent(agentId).catch(() => ({
        id: agentId,
        name: agentId,
        description: '데모 Agent입니다.',
        model: 'claude-sonnet',
        tools: ['query_customer', 'query_orders', 'builtin:http', 'mcp:slack'],
        system_prompt: '너는 고객 지원 담당이야.\n고객 정보를 조회하고, 주문 내역을 확인해서 답변해.',
        approval_required: ['DELETE *', 'mcp:slack:send_message'],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: 'active' as const,
      })),
      listTraces(agentId, 10).catch(() => [
        {
          trace_id: 'tr-demo-1',
          session_id: 's-1',
          agent: agentId,
          timestamp: new Date().toISOString(),
          total_duration_ms: 3465,
          steps: [],
        },
        {
          trace_id: 'tr-demo-2',
          session_id: 's-2',
          agent: agentId,
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          total_duration_ms: 1230,
          steps: [],
        },
      ]),
    ]).then(([agentData, tracesData]) => {
      setAgent(agentData);
      setTraces(tracesData);
      setLoading(false);
    });
  }, [agentId]);

  if (loading || !agent) {
    return <div className={styles.loading}><div className={styles.spinner} /></div>;
  }

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <Link href="/agents" className={styles.backBtn}>
          <FiArrowLeft size={16} />
        </Link>
        <div className={styles.headerInfo}>
          <h1>{agent.name}</h1>
          <p>{agent.description}</p>
        </div>
        <Link href={`/chat/${agent.id}`} className={styles.chatBtn}>
          <FiMessageSquare size={16} />
          대화 시작
        </Link>
      </header>

      {/* Tabs */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${tab === 'overview' ? styles.activeTab : ''}`}
          onClick={() => setTab('overview')}
        >
          개요
        </button>
        <button
          className={`${styles.tab} ${tab === 'tools' ? styles.activeTab : ''}`}
          onClick={() => setTab('tools')}
        >
          도구 ({agent.tools.length})
        </button>
        <button
          className={`${styles.tab} ${tab === 'history' ? styles.activeTab : ''}`}
          onClick={() => setTab('history')}
        >
          실행 이력
        </button>
      </div>

      {/* Tab Content */}
      <div className={styles.content}>
        {tab === 'overview' && (
          <div className={styles.overview}>
            {/* Info Cards */}
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}>
                <div className={styles.infoLabel}><FiCpu size={14} /> 모델</div>
                <div className={styles.infoValue}>{agent.model}</div>
              </div>
              <div className={styles.infoCard}>
                <div className={styles.infoLabel}><FiTool size={14} /> 도구</div>
                <div className={styles.infoValue}>{agent.tools.length}개</div>
              </div>
              <div className={styles.infoCard}>
                <div className={styles.infoLabel}><FiBox size={14} /> 상태</div>
                <div className={styles.infoValue}>{agent.status}</div>
              </div>
              <div className={styles.infoCard}>
                <div className={styles.infoLabel}><FiClock size={14} /> 생성</div>
                <div className={styles.infoValue}>
                  {formatRelativeTime(agent.created_at)}
                </div>
              </div>
            </div>

            {/* System Prompt */}
            <div className={styles.section}>
              <h3>시스템 프롬프트</h3>
              <pre className={styles.codeBlock}>{agent.system_prompt}</pre>
            </div>

            {/* Approval Required */}
            {agent.approval_required && agent.approval_required.length > 0 && (
              <div className={styles.section}>
                <h3><FiShield size={14} /> 승인 필요 액션</h3>
                <div className={styles.tagList}>
                  {agent.approval_required.map((action, i) => (
                    <span key={i} className={styles.tag}>{action}</span>
                  ))}
                </div>
              </div>
            )}

            <p className={styles.editHint}>
              수정이 필요하면 대화에서 Agent에게 지시하세요.
            </p>
          </div>
        )}

        {tab === 'tools' && (
          <div className={styles.toolList}>
            {agent.tools.map((tool, i) => {
              const isBuiltin = tool.startsWith('builtin:');
              const isMcp = tool.startsWith('mcp:');
              const source = isBuiltin ? 'builtin' : isMcp ? 'mcp' : 'custom';

              return (
                <div key={i} className={styles.toolItem}>
                  <FiTool size={16} />
                  <span className={styles.toolItemName}>{tool}</span>
                  <span className={`${styles.sourceBadge} ${styles[source]}`}>
                    {source}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {tab === 'history' && (
          <div className={styles.historyList}>
            {traces.length === 0 ? (
              <div className={styles.emptyHistory}>실행 이력이 없습니다.</div>
            ) : (
              traces.map((trace) => (
                <Link
                  key={trace.trace_id}
                  href={`/trace/${trace.trace_id}`}
                  className={styles.historyRow}
                >
                  <FiActivity size={14} />
                  <span className={styles.historyId}>
                    {trace.trace_id.slice(0, 12)}...
                  </span>
                  <span className={styles.historyDuration}>
                    {formatDuration(trace.total_duration_ms)}
                  </span>
                  <span className={styles.historyTime}>
                    {formatRelativeTime(trace.timestamp)}
                  </span>
                </Link>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
