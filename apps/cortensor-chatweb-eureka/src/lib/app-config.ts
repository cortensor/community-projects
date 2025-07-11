// src/lib/app-config.ts
export const appConfig = {
  app: {
    name: process.env.NEXT_PUBLIC_APP_NAME || "My AI Assistant",
    version: process.env.NEXT_PUBLIC_APP_VERSION || "1.1.0",
    assistant: "COR Assistant",
  },
  chat: {
    maxMessagesPerSession: 100,
    enableExport: true,
    maxInputLength: parseInt(process.env.NEXT_PUBLIC_MAX_INPUT_LENGTH || "4000", 10),
    // Pastikan variabel ini ada di .env.local Anda
    staticSessionId: process.env.NEXT_PUBLIC_LLM_SESSION_ID || "92", 
  },
  cortensor: {
    routerUrl: process.env.CORTENSOR_ROUTER_URL,
    apiKey: process.env.CORTENSOR_API_KEY,
    completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL,
  }
};
