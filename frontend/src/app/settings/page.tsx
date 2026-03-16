'use client';

import { useState, useEffect, useCallback } from 'react';
import { BASE_URL } from '../_common/api/config';
import { apiFetch } from '../_common/api/client';
import styles from './settings.module.scss';
import {
  FiServer,
  FiCpu,
  FiTool,
  FiDatabase,
  FiRefreshCw,
  FiLink,
  FiZap,
  FiPlus,
  FiTrash2,
  FiCheck,
  FiAlertCircle,
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

const TOOL_CATEGORIES: Record<string, (name: string) => boolean> = {
  'xgen-core DB': (n) => n.startsWith('core_db'),
  'xgen-core Config': (n) => n.startsWith('core_config') || n.startsWith('core_auth'),
  'xgen-documents': (n) => /^(rag_|embedding_|rerank_|document_)/.test(n),
  'Agent 관리': (n) => /^(create_agent|list_agents|get_agent|update_agent|delete_agent|list_available_tools)$/.test(n),
  'Sandbox': (n) => n.startsWith('execute_code'),
  'Utility': (n) => /^(send_email|read_table_data|write_table_data|ml_inference|run_workflow)$/.test(n),
};

function categorize(tools: ToolInfo[]) {
  const result: Record<string, ToolInfo[]> = {};
  for (const t of tools) {
    let cat = 'Built-in';
    for (const [name, test] of Object.entries(TOOL_CATEGORIES)) {
      if (test(t.name)) { cat = name; break; }
    }
    (result[cat] ??= []).push(t);
  }
  return result;
}

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);

  // MCP connect form
  const [mcpName, setMcpName] = useState('');
  const [mcpUrl, setMcpUrl] = useState('');
  const [mcpConnecting, setMcpConnecting] = useState(false);
  const [mcpMessage, setMcpMessage] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const fetchAll = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleMcpConnect = async () => {
    if (!mcpName.trim() || !mcpUrl.trim()) return;
    setMcpConnecting(true);
    setMcpMessage(null);
    try {
      const res = await apiFetch<{ status: string; tools_loaded: number }>('/api/mcp/connect', {
        method: 'POST',
        body: JSON.stringify({ name: mcpName.trim(), transport: 'sse', url: mcpUrl.trim() }),
      });
      setMcpMessage({ type: 'ok', text: `${mcpName} 연결 완료 — 도구 ${res.tools_loaded}개 로드` });
      setMcpName('');
      setMcpUrl('');
      await fetchAll();
    } catch (err) {
      setMcpMessage({ type: 'err', text: `연결 실패: ${(err as Error).message}` });
    } finally {
      setMcpConnecting(false);
    }
  };

  const handleMcpDisconnect = async (name: string) => {
    try {
      await apiFetch(`/api/mcp/disconnect/${name}`, { method: 'DELETE' });
      await fetchAll();
    } catch {
      // ignore
    }
  };

  const toolsByCategory = categorize(tools);

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

      {/* MCP 서버 */}
      <section className={styles.section}>
        <h2><FiLink size={18} /> MCP 서버</h2>

        {mcpServers.length > 0 && (
          <div className={styles.mcpList}>
            {mcpServers.map((s) => (
              <div key={s.name} className={styles.mcpItem}>
                <span className={`${styles.dot} ${styles.green}`} />
                <div className={styles.mcpInfo}>
                  <span className={styles.mcpName}>{s.name}</span>
                  <span className={styles.mcpMeta}>{s.transport} — 도구 {s.tools_count}개</span>
                </div>
                <button
                  className={styles.mcpDisconnect}
                  onClick={() => handleMcpDisconnect(s.name)}
                  title="연결 해제"
                >
                  <FiTrash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* MCP 연결 폼 */}
        <div className={styles.mcpForm}>
          <div className={styles.mcpFormRow}>
            <input
              className={styles.mcpInput}
              placeholder="서버 이름 (예: my-mcp-server)"
              value={mcpName}
              onChange={(e) => setMcpName(e.target.value)}
            />
            <input
              className={`${styles.mcpInput} ${styles.mcpInputWide}`}
              placeholder="SSE URL (예: http://localhost:3001/sse)"
              value={mcpUrl}
              onChange={(e) => setMcpUrl(e.target.value)}
            />
            <button
              className={styles.mcpConnectBtn}
              onClick={handleMcpConnect}
              disabled={mcpConnecting || !mcpName.trim() || !mcpUrl.trim()}
            >
              {mcpConnecting ? <FiRefreshCw size={14} className={styles.spin} /> : <FiPlus size={14} />}
              연결
            </button>
          </div>
          {mcpMessage && (
            <div className={`${styles.mcpMsg} ${styles[mcpMessage.type]}`}>
              {mcpMessage.type === 'ok' ? <FiCheck size={14} /> : <FiAlertCircle size={14} />}
              {mcpMessage.text}
            </div>
          )}
        </div>
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

      {/* 환경 정보 */}
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
