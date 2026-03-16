'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import type { AgentSummary } from './_common/types';
import { listAgents } from './_common/api/agentAPI';
import { formatRelativeTime } from './_common/utils/formatTime';
import styles from './page.module.scss';
import {
  FiBox,
  FiMessageSquare,
  FiActivity,
  FiTool,
  FiPlus,
  FiArrowRight,
} from 'react-icons/fi';

export default function Dashboard() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch(() => {
        // demo data for development
        setAgents([
          {
            id: 'demo-1',
            name: 'customer-support',
            description: '고객 문의 응답 agent. DB 조회 + 주문 내역 확인.',
            model: 'claude-sonnet',
            tool_count: 4,
            status: 'active',
            last_run: new Date().toISOString(),
          },
          {
            id: 'demo-2',
            name: 'data-analyst',
            description: '데이터 분석 및 리포트 생성 agent.',
            model: 'gpt-4o',
            tool_count: 6,
            status: 'active',
            last_run: new Date(Date.now() - 3600000).toISOString(),
          },
          {
            id: 'demo-3',
            name: 'code-reviewer',
            description: '코드 리뷰 및 개선 제안 agent.',
            model: 'claude-sonnet',
            tool_count: 3,
            status: 'draft',
          },
        ]);
      })
      .finally(() => setLoading(false));
  }, []);

  const stats = {
    totalAgents: agents.length,
    activeAgents: agents.filter((a) => a.status === 'active').length,
    totalTools: agents.reduce((sum, a) => sum + (a.tool_count || 0), 0),
  };

  return (
    <div className={styles.dashboard}>
      {/* Header */}
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>대시보드</h1>
          <p className={styles.subtitle}>AI Agent 현황 및 관리</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <Link href="/agents/new" className={styles.primaryBtn} style={{ background: '#059669' }}>
            <FiPlus size={18} />
            에이전트 만들기
          </Link>
          <Link href="/chat" className={styles.primaryBtn}>
            <FiPlus size={18} />
            새 대화 시작
          </Link>
        </div>
      </header>

      {/* Stats */}
      <div className={styles.stats}>
        <div className={styles.statCard}>
          <div className={`${styles.statIcon} ${styles.blue}`}>
            <FiBox size={20} />
          </div>
          <div>
            <div className={styles.statValue}>{stats.totalAgents}</div>
            <div className={styles.statLabel}>전체 Agent</div>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={`${styles.statIcon} ${styles.green}`}>
            <FiActivity size={20} />
          </div>
          <div>
            <div className={styles.statValue}>{stats.activeAgents}</div>
            <div className={styles.statLabel}>활성 Agent</div>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={`${styles.statIcon} ${styles.purple}`}>
            <FiTool size={20} />
          </div>
          <div>
            <div className={styles.statValue}>{stats.totalTools}</div>
            <div className={styles.statLabel}>등록된 도구</div>
          </div>
        </div>
      </div>

      {/* Agent List */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>에이전트 목록</h2>
          <Link href="/agents" className={styles.seeAll}>
            전체 보기 <FiArrowRight size={14} />
          </Link>
        </div>

        {loading ? (
          <div className={styles.loading}>
            <div className={styles.spinner} />
          </div>
        ) : (
          <div className={styles.agentGrid}>
            {agents.map((agent) => (
              <div key={agent.id} className={styles.agentCard}>
                <div className={styles.agentHeader}>
                  <div className={styles.agentName}>{agent.name}</div>
                  <span
                    className={`${styles.status} ${styles[agent.status]}`}
                  >
                    {agent.status === 'active' ? '활성' : agent.status === 'draft' ? '초안' : '비활성'}
                  </span>
                </div>
                <p className={styles.agentDesc}>{agent.description}</p>
                <div className={styles.agentMeta}>
                  <span className={styles.metaItem}>
                    <FiBox size={12} /> {agent.model}
                  </span>
                  <span className={styles.metaItem}>
                    <FiTool size={12} /> {agent.tool_count}개 도구
                  </span>
                  {agent.last_run && (
                    <span className={styles.metaItem}>
                      마지막 실행: {formatRelativeTime(agent.last_run)}
                    </span>
                  )}
                </div>
                <div className={styles.agentActions}>
                  <Link
                    href={`/chat/${agent.id}`}
                    className={styles.chatBtn}
                  >
                    <FiMessageSquare size={14} />
                    대화
                  </Link>
                  <Link
                    href={`/agents/${agent.id}`}
                    className={styles.detailBtn}
                  >
                    상세
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
