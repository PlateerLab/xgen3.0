'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import type { Trace } from '../../_common/types';
import { getTrace } from '../../_common/api/agentAPI';
import { formatDuration } from '../../_common/utils/formatTime';
import TraceTimeline from '../../_common/components/TraceTimeline';
import styles from './page.module.scss';
import {
  FiArrowLeft,
  FiClock,
  FiBox,
  FiCpu,
  FiTool,
  FiMessageSquare,
  FiChevronDown,
  FiChevronRight,
} from 'react-icons/fi';

export default function TracePage() {
  const { traceId } = useParams<{ traceId: string }>();
  const [trace, setTrace] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  useEffect(() => {
    getTrace(traceId)
      .then(setTrace)
      .catch(() => {
        // Demo data
        setTrace({
          trace_id: traceId,
          session_id: 'session-demo',
          agent: 'customer-support',
          timestamp: new Date().toISOString(),
          total_duration_ms: 3465,
          steps: [
            {
              type: 'think',
              timestamp: new Date().toISOString(),
              duration_ms: 2100,
              model: 'claude-sonnet',
              input_tokens: 1200,
              output_tokens: 350,
            },
            {
              type: 'tool_call',
              timestamp: new Date().toISOString(),
              duration_ms: 45,
              tool: 'query_customer',
              params: { customer_id: 'CUST-001' },
              result: { customer: { name: '홍길동', email: 'hong@example.com' } },
              success: true,
            },
            {
              type: 'tool_call',
              timestamp: new Date().toISOString(),
              duration_ms: 120,
              tool: 'query_orders',
              params: { customer_id: 'CUST-001' },
              result: { orders: [{ id: 'ORD-001', total: 35000 }] },
              success: true,
            },
            {
              type: 'response',
              timestamp: new Date().toISOString(),
              duration_ms: 1200,
              text: '고객님의 최근 주문은 ORD-001 (35,000원) 입니다.',
            },
          ],
        });
      })
      .finally(() => setLoading(false));
  }, [traceId]);

  if (loading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
      </div>
    );
  }

  if (!trace) {
    return (
      <div className={styles.error}>Trace를 찾을 수 없습니다.</div>
    );
  }

  const stepIcons = {
    think: <FiCpu size={14} />,
    tool_call: <FiTool size={14} />,
    response: <FiMessageSquare size={14} />,
    error: <FiCpu size={14} />,
    approval: <FiCpu size={14} />,
  };

  return (
    <div className={styles.tracePage}>
      {/* Header */}
      <header className={styles.header}>
        <Link href="/trace" className={styles.backBtn}>
          <FiArrowLeft size={16} />
        </Link>
        <div className={styles.headerInfo}>
          <h1>Trace: {traceId.slice(0, 12)}...</h1>
          <div className={styles.headerMeta}>
            <span><FiBox size={12} /> {trace.agent}</span>
            <span><FiClock size={12} /> {formatDuration(trace.total_duration_ms)}</span>
            <span>{new Date(trace.timestamp).toLocaleString('ko-KR')}</span>
          </div>
        </div>
      </header>

      <div className={styles.content}>
        {/* Timeline */}
        <div className={styles.timelineSection}>
          <TraceTimeline
            steps={trace.steps}
            totalDuration={trace.total_duration_ms}
          />
        </div>

        {/* Step Details */}
        <div className={styles.detailsSection}>
          <h2 className={styles.sectionTitle}>단계별 상세</h2>
          <div className={styles.stepList}>
            {trace.steps.map((step, i) => (
              <div key={i} className={styles.stepDetail}>
                <button
                  className={styles.stepDetailHeader}
                  onClick={() => setExpandedStep(expandedStep === i ? null : i)}
                >
                  <span className={`${styles.stepIcon} ${styles[step.type]}`}>
                    {stepIcons[step.type]}
                  </span>
                  <span className={styles.stepLabel}>
                    {step.type === 'think' && '추론'}
                    {step.type === 'tool_call' && step.tool}
                    {step.type === 'response' && '응답'}
                    {step.type === 'error' && '오류'}
                    {step.type === 'approval' && '승인'}
                  </span>
                  <span className={styles.stepTime}>
                    {formatDuration(step.duration_ms)}
                  </span>
                  {expandedStep === i ? (
                    <FiChevronDown size={14} />
                  ) : (
                    <FiChevronRight size={14} />
                  )}
                </button>

                {expandedStep === i && (
                  <div className={styles.stepBody}>
                    {step.type === 'think' && (
                      <div className={styles.meta}>
                        <div>모델: {step.model}</div>
                        <div>입력 토큰: {step.input_tokens}</div>
                        <div>출력 토큰: {step.output_tokens}</div>
                      </div>
                    )}
                    {step.type === 'tool_call' && (
                      <>
                        <div className={styles.codeBlock}>
                          <div className={styles.codeLabel}>Parameters</div>
                          <pre>{JSON.stringify(step.params, null, 2)}</pre>
                        </div>
                        {step.result && (
                          <div className={styles.codeBlock}>
                            <div className={styles.codeLabel}>Result</div>
                            <pre>{JSON.stringify(step.result, null, 2)}</pre>
                          </div>
                        )}
                      </>
                    )}
                    {step.type === 'response' && step.text && (
                      <div className={styles.responseText}>{step.text}</div>
                    )}
                    {step.error && (
                      <div className={styles.errorText}>{step.error}</div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
