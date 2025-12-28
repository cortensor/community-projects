/**
 * API Configuration
 * Backend API endpoint configuration
 */

export const API_CONFIG = {
  // Backend API URL - defaults to localhost:3001
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:3001',
  
  // Timeout for API requests (ms)
  TIMEOUT: 30000,
  
  // Endpoints
  ENDPOINTS: {
    HEALTH: '/health',
    CHALLENGE: '/challenge',
    MONITOR: '/monitor',
    AUTO_CHALLENGE: '/auto-challenge',
    VERDICT_GENERATE: '/verdict/generate',
    VERDICT_SUBMIT: '/verdict/submit',
    VERDICT_EXECUTE: '/verdict/execute',
    DISPUTE_SETTLE: '/dispute/settle',
    DISPUTE: (id: string) => `/dispute/${id}`,
    MINER_TRUST_SCORE: (address: string) => `/miner/${address}/trust-score`,
    QUEUE_STATS: '/queue/stats',
    TEST_GENERATE_EVIDENCE: '/test/generate-evidence',
    TEST_HEALTH_CORTENSOR: '/test/health-cortensor',
  },
};


