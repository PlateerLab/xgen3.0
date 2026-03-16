const isDev = process.env.NODE_ENV === 'development';

export const devLog = {
  log: (...args: unknown[]) => isDev && console.log('[XGEN]', ...args),
  warn: (...args: unknown[]) => isDev && console.warn('[XGEN]', ...args),
  error: (...args: unknown[]) => isDev && console.error('[XGEN]', ...args),
  info: (...args: unknown[]) => isDev && console.info('[XGEN]', ...args),
};
