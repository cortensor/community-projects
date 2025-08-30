// API configuration for different environments

// Check if we're in development environment
const isDevelopment = import.meta.env.MODE === 'development' || import.meta.env.DEV

// Development base URL
const DEVELOPMENT_BASE_URL = 'https://cortensor-server-api-production.up.railway.app'

// Production base URL - can be configured via environment variable
// You can also define this in constants.ts if needed
const PRODUCTION_BASE_URL = "https://cortensor-server-api-production.up.railway.app"

// Export the base URL based on environment
export const API_BASE_URL = isDevelopment ? DEVELOPMENT_BASE_URL : PRODUCTION_BASE_URL

// Export individual URLs for clarity
export const BASE_URLS = {
  development: DEVELOPMENT_BASE_URL,
  production: PRODUCTION_BASE_URL,
  current: API_BASE_URL
} as const

// Helper function to get full API endpoint
export const getApiEndpoint = (path: string): string => {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}
