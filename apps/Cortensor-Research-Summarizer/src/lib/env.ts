import 'server-only';

function optionalString(name: string): string | undefined {
  const value = process.env[name];
  const trimmed = typeof value === 'string' ? value.trim() : '';
  return trimmed ? trimmed : undefined;
}

function requiredString(name: string): string {
  const value = optionalString(name);
  if (!value) {
    throw new Error(`${name} is required. Set it in .env.local and restart the server.`);
  }
  return value;
}

function intWithDefault(name: string, defaultValue: number): number {
  const raw = optionalString(name);
  if (!raw) return defaultValue;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : defaultValue;
}

function floatWithDefault(name: string, defaultValue: number): number {
  const raw = optionalString(name);
  if (!raw) return defaultValue;
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : defaultValue;
}

function boolWithDefault(name: string, defaultValue: boolean): boolean {
  const raw = optionalString(name);
  if (!raw) return defaultValue;
  return ['1', 'true', 'yes', 'y', 'on'].includes(raw.toLowerCase());
}

function normalizeBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, '');
}

export const env = {
  // App
  APP_DEBUG_LOGS: boolWithDefault('APP_DEBUG_LOGS', false),
  MIN_SUMMARY_PARAGRAPHS: intWithDefault('MIN_SUMMARY_PARAGRAPHS', 3),

  // Cortensor router
  CORTENSOR_API_KEY: requiredString('CORTENSOR_API_KEY'),
  CORTENSOR_BASE_URL: normalizeBaseUrl(requiredString('CORTENSOR_BASE_URL')),
  CORTENSOR_SESSION: intWithDefault('CORTENSOR_SESSION', 6),

  // Cortensor model/tuning
  CORTENSOR_PROMPT_TYPE: intWithDefault('CORTENSOR_PROMPT_TYPE', 1),
  CORTENSOR_TIMEOUT: intWithDefault('CORTENSOR_TIMEOUT', 300),
  CORTENSOR_PRECOMMIT_TIMEOUT: intWithDefault('CORTENSOR_PRECOMMIT_TIMEOUT', 90),
  CORTENSOR_MAX_TOKENS: intWithDefault('CORTENSOR_MAX_TOKENS', 6000),
  CORTENSOR_FALLBACK_MAX_CONTEXT_TOKENS: intWithDefault('CORTENSOR_FALLBACK_MAX_CONTEXT_TOKENS', 5000),
  CORTENSOR_PROMPT_TOKEN_RESERVE: intWithDefault('CORTENSOR_PROMPT_TOKEN_RESERVE', 1200),
  CORTENSOR_MAX_CONTENT_CHARS: intWithDefault('CORTENSOR_MAX_CONTENT_CHARS', 9500),
  CORTENSOR_AVG_CHARS_PER_TOKEN: floatWithDefault('CORTENSOR_AVG_CHARS_PER_TOKEN', 3),
  CORTENSOR_TEMPERATURE: floatWithDefault('CORTENSOR_TEMPERATURE', 0.3),
  CORTENSOR_TOP_P: floatWithDefault('CORTENSOR_TOP_P', 0.9),
  CORTENSOR_TOP_K: intWithDefault('CORTENSOR_TOP_K', 40),
  CORTENSOR_PRESENCE_PENALTY: floatWithDefault('CORTENSOR_PRESENCE_PENALTY', 0),
  CORTENSOR_FREQUENCY_PENALTY: floatWithDefault('CORTENSOR_FREQUENCY_PENALTY', 0),
  CORTENSOR_STREAM: boolWithDefault('CORTENSOR_STREAM', false),

  // Search providers
  TAVILY_API_KEY: optionalString('TAVILY_API_KEY'),
  GOOGLE_API_KEY: optionalString('GOOGLE_API_KEY'),
  GOOGLE_SEARCH_ENGINE_ID: optionalString('GOOGLE_SEARCH_ENGINE_ID'),

  // News providers
  NEWSAPI_API_KEY: optionalString('NEWSAPI_API_KEY'),
  GNEWS_API_KEY: optionalString('GNEWS_API_KEY'),
  MEDIASTACK_API_KEY: optionalString('MEDIASTACK_API_KEY'),
  NASA_API_KEY: optionalString('NASA_API_KEY'),

  // Fetcher
  ARTICLE_FETCH_TIMEOUT_MS: intWithDefault('ARTICLE_FETCH_TIMEOUT', 60000),
  JINA_READER_BASE_URL: normalizeBaseUrl(optionalString('JINA_READER_BASE_URL') ?? 'https://r.jina.ai'),
} as const;

export function debugLog(...args: unknown[]) {
  if (env.APP_DEBUG_LOGS) {
    console.log(...args);
  }
}
