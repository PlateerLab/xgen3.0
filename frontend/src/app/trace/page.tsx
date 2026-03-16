'use client';

import styles from './trace.module.scss';
import { FiActivity } from 'react-icons/fi';

export default function TraceIndex() {
  return (
    <div className={styles.emptyPage}>
      <FiActivity size={48} />
      <h1>실행 트레이스</h1>
      <p>Agent 대화에서 실행된 Trace를 확인할 수 있습니다.</p>
      <p className={styles.hint}>대화 페이지 헤더의 &quot;Trace&quot; 버튼으로 접근하세요.</p>
    </div>
  );
}
