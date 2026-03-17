// 일반 REST API → Next.js 프록시(같은 origin) — CORS 문제 없음
// SSE 스트리밍 → 백엔드 직접 연결 — Next.js rewrite 버퍼링 방지

/** REST API — 같은 origin 프록시 경유 */
export const BASE_URL = typeof window === 'undefined'
  ? (process.env.BACKEND_URL || 'http://xgen-agent:8000')
  : '';

/** SSE 스트리밍 전용 — 백엔드 직접 */
export const STREAM_URL = typeof window === 'undefined'
  ? (process.env.BACKEND_URL || 'http://xgen-agent:8000')
  : `${window.location.protocol}//${window.location.hostname}:8010`;

export const API_CONFIG = {
  BASE_URL,
  STREAM_URL,
  TIMEOUT: 30000,
  DEFAULT_HEADERS: {
    'Content-Type': 'application/json',
  },
};

export const APP_CONFIG = {
  LANGUAGE: 'ko',
  DEBUG_MODE: process.env.NODE_ENV === 'development',
  SHOW_THINK_BLOCK: false,
  SHOW_TOOL_OUTPUT: false,
};
