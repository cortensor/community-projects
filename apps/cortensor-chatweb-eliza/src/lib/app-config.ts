/**
 * Configuration file for client and server sides.
 */
export const appConfig = {
  app: {
    name: process.env.NEXT_PUBLIC_APP_NAME || "Cortensor AI Chat",
    version: process.env.NEXT_PUBLIC_APP_VERSION || "1.0.0",
    assistant: "COR Assistant",
  },
  chat: {
    maxMessagesPerSession: 100,
    enableExport: true,
    maxInputLength: parseInt(process.env.NEXT_PUBLIC_MAX_INPUT_LENGTH || "4000", 10),
  },
  cortensor: {
    createUrl: process.env.NEXT_PUBLIC_CORTENSOR_CREATE_URL,
    completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL,
    apiKey: process.env.CORTENSOR_API_KEY,
    sessionId: parseInt(process.env.LLM_SESSION_ID || "6", 10),
    timeout: parseInt(process.env.LLM_TIMEOUT || "180", 10),
  }
};
