const parseNumberEnv = (value: string | undefined, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const sanitizeUrl = (value: string) => value.replace(/\/$/, '');
const routerBase = sanitizeUrl(process.env.CORTENSOR_ROUTER_URL ?? 'http://localhost:5010');

export const CORTENSOR_ROUTER = {
  baseUrl: routerBase,
  apiKey: process.env.CORTENSOR_API_KEY ?? '',
  completionsUrl: sanitizeUrl(process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL ?? `${routerBase}/api/v1/completions`),
};

export const LLM_PARAMETERS = {
  sessionId: parseNumberEnv(
    process.env.NEXT_PUBLIC_SESSION_ID ?? process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID,
    0,
  ),
  validationSessionId: parseNumberEnv(
    process.env.NEXT_PUBLIC_VALIDATION_SESSION_ID ?? process.env.NEXT_PUBLIC_SESSION_ID,
    0,
  ),
  maxInputLength: parseNumberEnv(process.env.NEXT_PUBLIC_MAX_INPUT_LENGTH, 2000),
  maxTokens: parseNumberEnv(process.env.LLM_MAX_TOKENS, 4096),
  timeoutSeconds: parseNumberEnv(process.env.LLM_TIMEOUT, 300),
  modelName: process.env.MODEL_NAME ?? 'Deepseek R1',
  promptType: parseNumberEnv(process.env.PROMPT_TYPE, 1),
};

export const TASK_FETCH_SETTINGS = {
  requiredMinerResults: parseNumberEnv(process.env.REQUIRED_MINER_RESULTS, 3),
  taskDetailsRetryAttempts: parseNumberEnv(process.env.TASK_DETAILS_RETRY_ATTEMPTS, 3),
  taskDetailsRetryDelayMs: parseNumberEnv(process.env.TASK_DETAILS_RETRY_DELAY_MS, 5000),
};

export const TAVILY_SETTINGS = {
  apiKey: process.env.TAVILY_API_KEY ?? '',
  searchUrl: process.env.TAVILY_API_URL ?? 'https://api.tavily.com/search',
};
