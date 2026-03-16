'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { AgentSummary } from '../_common/types';
import { listAgents } from '../_common/api/agentAPI';
import styles from './chat.module.scss';
import {
  FiMessageSquare,
  FiBox,
  FiArrowRight,
  FiActivity,
  FiTool,
  FiLoader,
} from 'react-icons/fi';

export default function ChatIndex() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    listAgents()
      .then((list) => {
        setAgents(list);
        // 에이전트가 하나면 바로 대화 페이지로
        if (list.length === 1) {
          router.replace(`/chat/${list[0].id}`);
        }
      })
      .catch(() => {
        setAgents([
          {
            id: 'demo-1',
            name: 'customer-support',
            description: '고객 문의 응답 에이전트',
            model: 'claude-sonnet',
            tool_count: 4,
            status: 'active',
          },
          {
            id: 'demo-2',
            name: 'data-analyst',
            description: '데이터 분석 및 시각화',
            model: 'gpt-4o',
            tool_count: 6,
            status: 'active',
          },
        ]);
      })
      .finally(() => setLoading(false));
  }, [router]);

  return (
    <div className={styles.selectPage}>
      <div className={styles.selectContent}>
        <div className={styles.selectIcon}>
          <FiMessageSquare size={36} />
        </div>
        <h1>대화 시작하기</h1>
        <p className={styles.selectDesc}>
          Agent를 선택하여 대화를 시작하세요.
          <br />
          AI가 도구를 활용해 작업을 수행합니다.
        </p>

        {loading ? (
          <div className={styles.loadingState}>
            <FiLoader size={24} className={styles.spinIcon} />
            <span>에이전트 목록 로딩 중...</span>
          </div>
        ) : agents.length === 0 ? (
          <div className={styles.emptyAgents}>
            <FiBox size={32} />
            <p>등록된 에이전트가 없습니다.</p>
          </div>
        ) : (
          <div className={styles.agentList}>
            {agents.map((agent) => (
              <Link
                key={agent.id}
                href={`/chat/${agent.id}`}
                className={styles.agentOption}
              >
                <div className={styles.agentOptionIcon}>
                  <FiBox size={20} />
                </div>
                <div className={styles.agentOptionInfo}>
                  <div className={styles.agentOptionName}>{agent.name}</div>
                  <div className={styles.agentOptionDesc}>{agent.description}</div>
                  <div className={styles.agentOptionMeta}>
                    <span className={styles.agentMetaItem}>
                      <FiActivity size={11} />
                      {agent.model}
                    </span>
                    <span className={styles.agentMetaItem}>
                      <FiTool size={11} />
                      도구 {agent.tool_count}개
                    </span>
                    <span
                      className={`${styles.agentStatus} ${
                        agent.status === 'active' ? styles.statusActive : styles.statusInactive
                      }`}
                    >
                      {agent.status === 'active' ? '활성' : agent.status}
                    </span>
                  </div>
                </div>
                <FiArrowRight size={16} className={styles.agentOptionArrow} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
