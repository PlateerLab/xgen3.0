'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { saveAgent, listTools } from '../../_common/api/agentAPI';
import styles from './new-agent.module.scss';
import {
  FiArrowLeft,
  FiSave,
} from 'react-icons/fi';

interface ToolItem {
  name: string;
  description: string;
  source: string;
}

const MODEL_OPTIONS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'claude-sonnet', label: 'Claude Sonnet' },
  { value: 'claude-haiku', label: 'Claude Haiku' },
  { value: 'claude-opus', label: 'Claude Opus' },
];

export default function NewAgentPage() {
  const router = useRouter();

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [model, setModel] = useState('claude-sonnet');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [approvalRequired, setApprovalRequired] = useState('');

  // UI state
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    listTools()
      .then((data) => {
        setTools(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        // demo tools for development
        setTools([
          { name: 'builtin:http', description: 'HTTP 요청 도구', source: 'builtin' },
          { name: 'builtin:db', description: '데이터베이스 쿼리 도구', source: 'builtin' },
          { name: 'builtin:file', description: '파일 읽기/쓰기 도구', source: 'builtin' },
          { name: 'mcp:slack', description: 'Slack 메시지 전송', source: 'mcp' },
          { name: 'mcp:github', description: 'GitHub API 연동', source: 'mcp' },
        ]);
      })
      .finally(() => setToolsLoading(false));
  }, []);

  const handleToolToggle = (toolName: string) => {
    setSelectedTools((prev) =>
      prev.includes(toolName)
        ? prev.filter((t) => t !== toolName)
        : [...prev, toolName]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!name.trim()) {
      setError('에이전트 이름은 필수입니다.');
      return;
    }
    if (!description.trim()) {
      setError('설명은 필수입니다.');
      return;
    }

    setSaving(true);

    try {
      const approvalList = approvalRequired
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const agentData = {
        workflow_name: name.trim(),
        workflow_id: name.trim().toLowerCase().replace(/\s+/g, '-'),
        name: name.trim(),
        description: description.trim(),
        model,
        tools: selectedTools,
        system_prompt: systemPrompt.trim(),
        ...(approvalList.length > 0 && { approval_required: approvalList }),
      };

      await saveAgent(agentData);
      setSuccess('에이전트가 저장되었습니다.');
      setTimeout(() => {
        router.push('/agents');
      }, 1000);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : '저장 중 오류가 발생했습니다.'
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link href="/agents" className={styles.backBtn}>
          <FiArrowLeft size={16} />
        </Link>
        <h1 className={styles.title}>새 에이전트</h1>
      </header>

      <form className={styles.form} onSubmit={handleSubmit}>
        {/* Name */}
        <div className={styles.field}>
          <label className={styles.label}>
            이름 <span className={styles.required}>*</span>
          </label>
          <input
            type="text"
            className={styles.input}
            placeholder="예: customer-support"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        {/* Description */}
        <div className={styles.field}>
          <label className={styles.label}>
            설명 <span className={styles.required}>*</span>
          </label>
          <input
            type="text"
            className={styles.input}
            placeholder="에이전트가 하는 일을 간략히 설명하세요"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {/* Model */}
        <div className={styles.field}>
          <label className={styles.label}>모델</label>
          <select
            className={styles.select}
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* System Prompt */}
        <div className={styles.field}>
          <label className={styles.label}>시스템 프롬프트</label>
          <textarea
            className={styles.textarea}
            placeholder="에이전트의 행동 지침을 작성하세요..."
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
          />
        </div>

        {/* Tools */}
        <div className={styles.field}>
          <label className={styles.label}>
            도구 선택
            {selectedTools.length > 0 && (
              <span style={{ fontWeight: 400, color: '#6b7280', marginLeft: 8 }}>
                ({selectedTools.length}개 선택됨)
              </span>
            )}
          </label>
          <div className={styles.toolsSection}>
            {toolsLoading ? (
              <div className={styles.toolsLoading}>도구 목록을 불러오는 중...</div>
            ) : tools.length === 0 ? (
              <div className={styles.toolsEmpty}>사용 가능한 도구가 없습니다.</div>
            ) : (
              <div className={styles.toolsGrid}>
                {tools.map((tool) => (
                  <label key={tool.name} className={styles.toolCheckbox}>
                    <input
                      type="checkbox"
                      checked={selectedTools.includes(tool.name)}
                      onChange={() => handleToolToggle(tool.name)}
                    />
                    <div className={styles.toolInfo}>
                      <div className={styles.toolName}>{tool.name}</div>
                      <div className={styles.toolDesc}>{tool.description}</div>
                    </div>
                    <span className={`${styles.toolSource} ${styles[tool.source] || ''}`}>
                      {tool.source}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Approval Required */}
        <div className={styles.field}>
          <label className={styles.label}>승인 필요 액션</label>
          <input
            type="text"
            className={styles.input}
            placeholder='예: DELETE *, mcp:slack:send_message'
            value={approvalRequired}
            onChange={(e) => setApprovalRequired(e.target.value)}
          />
          <div className={styles.hint}>쉼표로 구분하여 입력하세요.</div>
        </div>

        {/* Messages */}
        {error && (
          <div className={`${styles.message} ${styles.errorMsg}`}>{error}</div>
        )}
        {success && (
          <div className={`${styles.message} ${styles.successMsg}`}>{success}</div>
        )}

        {/* Actions */}
        <div className={styles.actions}>
          <button
            type="submit"
            className={styles.submitBtn}
            disabled={saving}
          >
            <FiSave size={16} />
            {saving ? '저장 중...' : '에이전트 저장'}
          </button>
          <Link href="/agents" className={styles.cancelBtn}>
            취소
          </Link>
        </div>
      </form>
    </div>
  );
}
