'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import type { AgentSummary } from '../_common/types';
import { listAgents } from '../_common/api/agentAPI';
import { formatRelativeTime } from '../_common/utils/formatTime';
import styles from './agents.module.scss';
import {
  FiBox,
  FiTool,
  FiMessageSquare,
  FiSearch,
  FiPlus,
} from 'react-icons/fi';

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch(() => {
        setAgents([
          { id: 'demo-1', name: 'customer-support', description: '고객 문의 응답 agent', model: 'claude-sonnet', tool_count: 4, status: 'active', last_run: new Date().toISOString() },
          { id: 'demo-2', name: 'data-analyst', description: '데이터 분석 agent', model: 'gpt-4o', tool_count: 6, status: 'active' },
          { id: 'demo-3', name: 'code-reviewer', description: '코드 리뷰 agent', model: 'claude-sonnet', tool_count: 3, status: 'draft' },
        ]);
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = agents.filter(
    (a) =>
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>에이전트</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className={styles.searchBox}>
            <FiSearch size={16} />
            <input
              type="text"
              placeholder="에이전트 검색..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Link
            href="/agents/new"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.5rem 1.5rem',
              background: '#2563eb',
              color: '#fff',
              borderRadius: '0.75rem',
              fontSize: '0.875rem',
              fontWeight: 500,
              transition: 'all 0.15s ease',
              whiteSpace: 'nowrap',
            }}
          >
            <FiPlus size={16} />
            새 에이전트
          </Link>
        </div>
      </header>

      {loading ? (
        <div className={styles.loading}><div className={styles.spinner} /></div>
      ) : (
        <div className={styles.list}>
          {filtered.map((agent) => (
            <div key={agent.id} className={styles.row}>
              <Link href={`/agents/${agent.id}`} className={styles.rowLink}>
                <div className={styles.rowIcon}>
                  <FiBox size={18} />
                </div>
                <div className={styles.rowInfo}>
                  <div className={styles.rowName}>
                    {agent.name}
                    <span className={`${styles.badge} ${styles[agent.status]}`}>
                      {agent.status === 'active' ? '활성' : agent.status === 'draft' ? '초안' : '비활성'}
                    </span>
                  </div>
                  <div className={styles.rowDesc}>{agent.description}</div>
                </div>
                <div className={styles.rowMeta}>
                  <span><FiBox size={12} /> {agent.model}</span>
                  <span><FiTool size={12} /> {agent.tool_count}</span>
                  {agent.last_run && (
                    <span>{formatRelativeTime(agent.last_run)}</span>
                  )}
                </div>
              </Link>
              <Link
                href={`/chat/${agent.id}`}
                className={styles.rowChat}
              >
                <FiMessageSquare size={14} />
              </Link>
            </div>
          ))}

          {filtered.length === 0 && (
            <div className={styles.empty}>
              검색 결과가 없습니다.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
