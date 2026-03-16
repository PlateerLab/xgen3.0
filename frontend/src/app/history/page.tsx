'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import type { HistoryEntry } from '../_common/types';
import { listHistory, listAgents } from '../_common/api/agentAPI';
import { formatDuration, formatRelativeTime } from '../_common/utils/formatTime';
import styles from './history.module.scss';
import {
  FiClock,
  FiBox,
  FiUser,
  FiMessageSquare,
  FiCheckCircle,
  FiXCircle,
  FiActivity,
  FiFilter,
  FiAlertCircle,
} from 'react-icons/fi';

const STATUS_MAP: Record<string, { label: string; icon: React.ReactNode; className: string }> = {
  completed: { label: '완료', icon: <FiCheckCircle size={14} />, className: 'completed' },
  failed: { label: '실패', icon: <FiXCircle size={14} />, className: 'failed' },
  cancelled: { label: '취소', icon: <FiXCircle size={14} />, className: 'cancelled' },
};

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterAgent, setFilterAgent] = useState<string>('');
  const [agentNames, setAgentNames] = useState<string[]>([]);

  // Load agent names for filter dropdown
  useEffect(() => {
    listAgents()
      .then((agents) => setAgentNames(agents.map((a) => a.name)))
      .catch(() => {});
  }, []);

  const fetchHistory = useCallback(() => {
    setLoading(true);
    setError(null);
    listHistory(filterAgent || undefined, undefined, 100)
      .then((res) => {
        setHistory(res.history ?? []);
        setCount(res.count ?? 0);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filterAgent]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  if (loading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorPage}>
        <FiAlertCircle size={32} />
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <FiClock size={24} />
          <h1>실행 이력</h1>
          <span className={styles.count}>{count}건</span>
        </div>

        {/* Filter */}
        <div className={styles.filters}>
          <FiFilter size={14} />
          <select
            className={styles.select}
            value={filterAgent}
            onChange={(e) => setFilterAgent(e.target.value)}
          >
            <option value="">전체 에이전트</option>
            {agentNames.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
      </header>

      {history.length === 0 ? (
        <div className={styles.empty}>
          <FiClock size={48} />
          <h2>실행 이력이 없습니다</h2>
          <p>Agent와 대화하면 실행 이력이 자동으로 기록됩니다.</p>
        </div>
      ) : (
        <div className={styles.table}>
          <div className={styles.tableHeader}>
            <span className={styles.colStatus}>상태</span>
            <span className={styles.colAgent}>에이전트</span>
            <span className={styles.colInput}>입력</span>
            <span className={styles.colResult}>결과</span>
            <span className={styles.colDuration}>소요시간</span>
            <span className={styles.colTime}>시간</span>
            <span className={styles.colTrace}>Trace</span>
          </div>

          {history.map((entry) => {
            const status = STATUS_MAP[entry.status] || STATUS_MAP.completed;
            return (
              <div key={entry.id} className={styles.tableRow}>
                <span className={`${styles.colStatus} ${styles[status.className]}`}>
                  {status.icon}
                  <span className={styles.statusLabel}>{status.label}</span>
                </span>

                <span className={styles.colAgent}>
                  <FiBox size={12} />
                  {entry.agent_name}
                </span>

                <span className={styles.colInput} title={entry.user_input}>
                  <FiUser size={12} />
                  <span className={styles.truncate}>{entry.user_input || '-'}</span>
                </span>

                <span className={styles.colResult} title={entry.result}>
                  <FiMessageSquare size={12} />
                  <span className={styles.truncate}>{entry.result || '-'}</span>
                </span>

                <span className={styles.colDuration}>
                  {formatDuration(entry.duration_ms)}
                </span>

                <span className={styles.colTime}>
                  {formatRelativeTime(entry.created_at)}
                </span>

                <span className={styles.colTrace}>
                  {entry.trace_id ? (
                    <Link
                      href={`/trace/${entry.trace_id}`}
                      className={styles.traceLink}
                    >
                      <FiActivity size={12} />
                      Trace
                    </Link>
                  ) : (
                    <span className={styles.noTrace}>-</span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
