import { BASE_URL } from './config';

interface FetchOptions extends RequestInit {
  timeout?: number;
}

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { timeout = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    });

    if (!res.ok) {
      const errorBody = await res.text().catch(() => '');
      throw new Error(`API ${res.status}: ${errorBody || res.statusText}`);
    }

    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export function apiSSE(
  path: string,
  body: Record<string, unknown>,
  onEvent: (event: string, data: string) => void,
  onDone?: () => void,
  onError?: (error: Error) => void
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE_URL}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`SSE ${res.status}: ${res.statusText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = 'message';
        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            onEvent(currentEvent, line.slice(5).trim());
            currentEvent = 'message';
          }
        }
      }

      onDone?.();
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError?.(err as Error);
      }
    }
  })();

  return controller;
}
