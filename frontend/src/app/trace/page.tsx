'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import type { Trace } from '../_common/types';
import { listTraces } from '../_common/api/agentAPI';
import { formatDuration, formatRelativeTime } from '../_common/utils/formatTime';
import styles from './trace.module.scss';
import {
  FiActivity,
  FiClock,
  FiBox,
  FiCpu,
  FiTool,
  FiMessageSquare,
  FiChevronLeft,
  FiChevronRight,
  FiAlertCircle,
} from 'react-icons/fi';

const STEP_TYPE_ICONS: Record<string, React.ReactNode> = {
  think: <FiCpu size={12} />,
  tool_call: <FiTool size={12} />,
  response: <FiMessageSquare size={12} />,
  error: <FiAlertCircle size={12} />,
};

const PAGE_SIZE = 20;

export default function TraceListPage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listTraces(page, PAGE_SIZE)
      .then((res) => {
        setTraces(res.traces ?? []);
        setTotal(res.total ?? 0);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

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

  if (traces.length === 0) {
    return (
      <div className={styles.emptyPage}>
        <FiActivity size={48} />
        <h1>실행 트레이스</h1>
        <p>아직 실행된 트레이스가 없습니다.</p>
        <p className={styles.hint}>Agent와 대화하면 트레이스가 자동으로 기록됩니다.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <FiActivity size={24} />
          <h1>실행 트레이스</h1>
        </div>
        <span className={styles.count}>총 {total}건</span>
      </header>

      <div className={styles.traceList}>
        {traces.map((trace) => {
          const stepSummary = trace.steps.reduce<Record<string, number>>((acc, s) => {
            acc[s.type] = (acc[s.type] || 0) + 1;
            return acc;
          }, {});

          return (
            <Link
              key={trace.trace_id}
              href={`/trace/${trace.trace_id}`}
              className={styles.traceCard}
            >
              <div className={styles.cardHeader}>
                <span className={styles.traceId}>{trace.trace_id.slice(0, 12)}...</span>
                <span className={styles.duration}>
                  <FiClock size={12} />
                  {formatDuration(trace.total_duration_ms)}
                </span>
              </div>

              <div className={styles.cardBody}>
                <div className={styles.agentBadge}>
                  <FiBox size={12} />
                  {trace.agent}
                </div>
                <div className={styles.stepBadges}>
                  {Object.entries(stepSummary).map(([type, count]) => (
                    <span key={type} className={`${styles.stepBadge} ${styles[type]}`}>
                      {STEP_TYPE_ICONS[type]}
                      {count}
                    </span>
                  ))}
                </div>
              </div>

              <div className={styles.cardFooter}>
                <span className={styles.timestamp}>
                  {formatRelativeTime(trace.timestamp)}
                </span>
                <span className={styles.stepCount}>{trace.steps.length}단계</span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            className={styles.pageBtn}
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            <FiChevronLeft size={16} />
          </button>
          <span className={styles.pageInfo}>
            {page} / {totalPages}
          </span>
          <button
            className={styles.pageBtn}
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            <FiChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
