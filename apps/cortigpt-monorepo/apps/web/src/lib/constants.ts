// Contract addresses and constants
export const COR_TOKEN_ADDRESS = '0xF9C355394e7b3F147e8aFEBF95B3Ebbf688457f3' as const

// Web search functionality
export const SEARCH_MARKER = '[**search**]' as const

// AI response cleanup patterns
export const AI_RESPONSE_CLEANUP_PATTERNS = [
  /<\/s>/g // Remove </s> tags anywhere in responses
] as const

// Session configuration defaults
export const DEFAULT_SESSION_CONFIG = {
  minNumOfNodes: BigInt(1),
  maxNumOfNodes: BigInt(3),
  redundant: BigInt(1),
  numOfValidatorNodes: BigInt(0),
  mode: BigInt(0), // 0: Ephemeral, 1: Hybrid, 2: Dedicated
  reserveEphemeralNodes: false,
  sla: BigInt(1), // 0: Low, 1: Medium, 2: High
  modelIdentifier: BigInt(1),
  reservePeriod: BigInt(300), // 1 hour
  maxTaskExecutionCount: BigInt(5)
} as const

// System instructions for AI chat
export const SYSTEM_INSTRUCTIONS = `You are Cortigpt AI, an intelligent assistant powered by a decentralized network of miners. You provide helpful, accurate, and concise responses to user queries. You have access to the conversation history to maintain context and provide coherent responses.

Key guidelines:
- Be helpful and informative
- Maintain conversation context using the provided history
- Keep responses concise but comprehensive
- If you're unsure about something, acknowledge it honestly
- Focus on providing practical and actionable advice when appropriate` as const

// Chat history configuration
export const CHAT_HISTORY_CONFIG = {
  maxHistoryMessages: 4, // Last 4 messages (2 user + 2 AI)
  includeSystemInstructions: true
} as const

// Task configuration defaults
export const DEFAULT_TASK_CONFIG = {
  nodeType: BigInt(0), // 0: ephemeral, 1: hybrid, 2: dedicated
  promptType: BigInt(0), // 0: default - eliza bot, 1: raw, 2: system template & input
  promptTemplate: '',
  clientReference: 'web-dashboard-cortensor',
  llmParams: [
    BigInt(128), // maxTokens
    BigInt(70),  // temperature (scaled by 100, so this is 0.7)
    BigInt(100), // topP (scaled by 100, so this is 1.0)
    BigInt(40),  // topK
    BigInt(100), // repeatPenalty (scaled by 100, so this is 1.0)
    BigInt(0),   // presencePenalty
    BigInt(0)    // frequencyPenalty
  ] as const
} as const


