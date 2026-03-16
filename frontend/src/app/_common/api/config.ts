// SSE 스트리밍은 Next.js rewrite로 프록시하면 버퍼링됨.
// 브라우저에서 직접 백엔드로 요청해야 함.
function resolveBackendUrl(): string {
  // 서버 사이드에서는 컨테이너 내부 URL
  if (typeof window === 'undefined') {
    return process.env.BACKEND_URL || 'http://xgen-agent:8000';
  }
  // 클라이언트(브라우저)에서는 호스트 기준으로 8010 포트
  return process.env.NEXT_PUBLIC_BACKEND_URL || `${window.location.protocol}//${window.location.hostname}:8010`;
}

export const BASE_URL = resolveBackendUrl();

export const API_CONFIG = {
  BASE_URL,
  TIMEOUT: 30000,
  DEFAULT_HEADERS: {
    'Content-Type': 'application/json',
  },
};

export const APP_CONFIG = {
  LANGUAGE: process.env.NEXT_PUBLIC_LANGUAGE || 'ko',
  DEBUG_MODE: process.env.NODE_ENV === 'development',
  SHOW_THINK_BLOCK: process.env.NEXT_PUBLIC_SHOW_THINK_BLOCK === 'true',
  SHOW_TOOL_OUTPUT: process.env.NEXT_PUBLIC_SHOW_TOOL_OUTPUT === 'true',
};
