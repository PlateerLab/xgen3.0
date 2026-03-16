'use client';

import type { TraceStep } from '../../types';
import { formatDuration } from '../../utils/formatTime';
import styles from './TraceTimeline.module.scss';
import { FiCpu, FiTool, FiMessageSquare, FiAlertCircle, FiShield } from 'react-icons/fi';

interface TraceTimelineProps {
  steps: TraceStep[];
  totalDuration: number;
}

const STEP_ICONS = {
  think: FiCpu,
  tool_call: FiTool,
  response: FiMessageSquare,
  error: FiAlertCircle,
  approval: FiShield,
};

export default function TraceTimeline({ steps, totalDuration }: TraceTimelineProps) {
  return (
    <div className={styles.timeline}>
      <div className={styles.header}>
        <span className={styles.title}>실행 흐름</span>
        <span className={styles.total}>총 {formatDuration(totalDuration)}</span>
      </div>

      <div className={styles.steps}>
        {steps.map((step, i) => {
          const Icon = STEP_ICONS[step.type] || FiCpu;
          const widthPct = totalDuration > 0
            ? Math.max((step.duration_ms / totalDuration) * 100, 2)
            : 100 / steps.length;

          return (
            <div key={i} className={styles.step}>
              <div className={styles.stepIndicator}>
                <div className={`${styles.dot} ${styles[step.type]}`}>
                  <Icon size={12} />
                </div>
                {i < steps.length - 1 && <div className={styles.line} />}
              </div>

              <div className={styles.stepContent}>
                <div className={styles.stepHeader}>
                  <span className={`${styles.stepType} ${styles[step.type]}`}>
                    {step.type === 'think' && '추론'}
                    {step.type === 'tool_call' && step.tool}
                    {step.type === 'response' && '응답'}
                    {step.type === 'error' && '오류'}
                    {step.type === 'approval' && '승인 대기'}
                  </span>
                  <span className={styles.stepDuration}>
                    {formatDuration(step.duration_ms)}
                  </span>
                </div>

                <div className={styles.bar}>
                  <div
                    className={`${styles.barFill} ${styles[step.type]}`}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>

                {step.type === 'think' && step.input_tokens != null && (
                  <div className={styles.stepMeta}>
                    {step.model} | {step.input_tokens} in / {step.output_tokens} out
                  </div>
                )}

                {step.type === 'tool_call' && step.params && (
                  <div className={styles.stepMeta}>
                    params: {JSON.stringify(step.params).slice(0, 80)}
                    {JSON.stringify(step.params).length > 80 ? '...' : ''}
                  </div>
                )}

                {step.error && (
                  <div className={styles.stepError}>{step.error}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
