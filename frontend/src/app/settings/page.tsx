'use client';

import { useState, useEffect } from 'react';
import { BASE_URL } from '../_common/api/config';
import styles from './settings.module.scss';
import {
  FiServer,
  FiCpu,
  FiTool,
  FiDatabase,
  FiRefreshCw,
  FiLink,
  FiZap,
} from 'react-icons/fi';

interface HealthData {
  status: string;
  service: string;
  version: string;
}

interface ToolInfo {
  name: string;
  description: string;
}

interface McpServer {
  name: string;
  transport: string;
  tools_count: number;
}

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [healthRes, toolsRes, mcpRes] = await Promise.allSettled([
        fetch(`${BASE_URL}/health`).then((r) => r.json()),
        fetch(`${BASE_URL}/api/tools/list`).then((r) => r.json()),
        fetch(`${BASE_URL}/api/mcp/servers`).then((r) => r.json()),
      ]);

      if (healthRes.status === 'fulfilled') setHealth(healthRes.value);
      if (toolsRes.status === 'fulfilled') setTools(toolsRes.value.tools || []);
      if (mcpRes.status === 'fulfilled') setMcpServers(mcpRes.value.servers || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const toolsByCategory = tools.reduce<Record<string, ToolInfo[]>>((acc, t) => {
    let cat = 'builtin';
    if (t.name.startsWith('core_db')) cat = 'xgen-core DB';
    else if (t.name.startsWith('core_config')) cat = 'xgen-core Config';
    else if (t.name.startsWith('core_auth')) cat = 'xgen-core Auth';
    else if (t.name.startsWith('rag_') || t.name.startsWith('embedding_') || t.name.startsWith('rerank_')) cat = 'xgen-documents';
    else if (t.name.startsWith('document_')) cat = 'xgen-documents';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(t);
    return acc;
  }, {});

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>설정</h1>
        <button className={styles.refreshBtn} onClick={fetchAll} disabled={loading}>
          <FiRefreshCw size={16} className={loading ? styles.spin : ''} />
          새로고침
        </button>
      </header>

      {/* 서비스 상태 */}
      <section className={styles.section}>
        <h2><FiServer size={18} /> 서비스 상태</h2>
        {health ? (
          <div className={styles.statusGrid}>
            <div className={styles.statusCard}>
              <span className={`${styles.dot} ${health.status === 'ok' ? styles.green : styles.red}`} />
              <div>
                <div className={styles.statusLabel}>{health.service}</div>
                <div className={styles.statusValue}>v{health.version} — {health.status}</div>
              </div>
            </div>
            <div className={styles.statusCard}>
              <FiDatabase size={18} />
              <div>
                <div className={styles.statusLabel}>Backend URL</div>
                <div className={styles.statusValue}>{BASE_URL || '(proxy)'}</div>
              </div>
            </div>
          </div>
        ) : (
          <div className={styles.empty}>연결 확인 중...</div>
        )}
      </section>

      {/* 등록된 도구 */}
      <section className={styles.section}>
        <h2><FiTool size={18} /> 등록된 도구 ({tools.length}개)</h2>
        {Object.entries(toolsByCategory).map(([cat, catTools]) => (
          <div key={cat} className={styles.toolCategory}>
            <h3><FiZap size={14} /> {cat} ({catTools.length})</h3>
            <div className={styles.toolList}>
              {catTools.map((t) => (
                <div key={t.name} className={styles.toolItem}>
                  <div className={styles.toolName}>{t.name}</div>
                  <div className={styles.toolDesc}>{t.description}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      {/* MCP 서버 */}
      <section className={styles.section}>
        <h2><FiLink size={18} /> MCP 서버</h2>
        {mcpServers.length > 0 ? (
          <div className={styles.toolList}>
            {mcpServers.map((s) => (
              <div key={s.name} className={styles.toolItem}>
                <div className={styles.toolName}>{s.name}</div>
                <div className={styles.toolDesc}>{s.transport} — {s.tools_count}개 도구</div>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.empty}>연결된 MCP 서버가 없습니다.</div>
        )}
      </section>

      {/* 연결 정보 */}
      <section className={styles.section}>
        <h2><FiCpu size={18} /> 환경 정보</h2>
        <div className={styles.envGrid}>
          {[
            ['CORE_SERVICE_BASE_URL', 'xgen-core 연결'],
            ['DOCUMENTS_SERVICE_BASE_URL', 'xgen-documents 연결'],
            ['MCP_STATION_BASE_URL', 'MCP Station 연결'],
            ['MODEL_BASE_URL', 'LLM API'],
            ['MODEL_NAME', '사용 모델'],
          ].map(([key, label]) => (
            <div key={key} className={styles.envRow}>
              <span className={styles.envKey}>{label}</span>
              <code className={styles.envVal}>{key}</code>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
