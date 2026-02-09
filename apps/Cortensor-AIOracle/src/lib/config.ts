const sessionIdEnv = process.env.NEXT_PUBLIC_OSS20B_SESSION_ID || process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID || '5'
const parsedSessionId = Number.parseInt(sessionIdEnv, 10)
const parsedTimeout = Number.parseInt(process.env.LLM_TIMEOUT || '300', 10)
const parsedMaxTokens = Number.parseInt(process.env.LLM_MAX_TOKENS || '4096', 10)
const parsedMaxInput = Number.parseInt(process.env.NEXT_PUBLIC_MAX_INPUT_LENGTH || '2000', 10)

export const CORTENSOR_CONFIG = {
  ROUTER_URL: process.env.CORTENSOR_ROUTER_URL!,
  API_KEY: process.env.CORTENSOR_API_KEY!,
  COMPLETIONS_URL: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL!,
  SESSION_ID: Number.isFinite(parsedSessionId) ? parsedSessionId : 5,
  TIMEOUT: Number.isFinite(parsedTimeout) ? parsedTimeout : 300,
  MAX_TOKENS: Number.isFinite(parsedMaxTokens) ? parsedMaxTokens : 4096,
  MAX_INPUT_LENGTH: Number.isFinite(parsedMaxInput) ? parsedMaxInput : 2000
}

export const ORACLE_CONFIG = {
  MIN_CONSENSUS: parseInt(process.env.ORACLE_MIN_CONSENSUS || '3'),
  CONFIDENCE_THRESHOLD: parseFloat(process.env.ORACLE_CONFIDENCE_THRESHOLD || '0.8'),
  APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || 'AI Oracle',
  APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION || 'v1.0'
}

export const WEB3_CONFIG = {
  SESSION_V2_ADDRESS: process.env.NEXT_PUBLIC_SESSION_V2_ADDRESS!,
  SESSION_QUEUE_V2_ADDRESS: process.env.NEXT_PUBLIC_SESSION_QUEUE_V2_ADDRESS!
}
