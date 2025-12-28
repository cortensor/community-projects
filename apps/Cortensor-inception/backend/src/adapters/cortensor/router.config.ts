// Router config is optional when using the on-chain SDK instead of HTTP router.
// Avoid throwing at module import time so tests and SDK-only deployments do not fail.
export const CortensorRouterConfig = {
  baseUrl: process.env.CORTENSOR_ROUTER_URL || "",
  apiKey: process.env.CORTENSOR_API_KEY || "",
  defaultTimeoutMs: process.env.CORTENSOR_DEFAULT_TIMEOUT_MS
    ? Number(process.env.CORTENSOR_DEFAULT_TIMEOUT_MS)
    : 8000,
};

export default CortensorRouterConfig;
