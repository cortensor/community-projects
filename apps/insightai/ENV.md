# Environment Variables for InsightAI

Create a `.env.local` file in the root directory with these variables:

```env
# Cortensor Router Configuration
# Get Router URL from Cortensor Discord/Telegram

# Router URL (e.g., https://router.cortensor.network or your local router)
CORTENSOR_ROUTER_URL=

# API Key (default-dev-token for development)
CORTENSOR_API_KEY=default-dev-token

# Set to "true" to force demo mode (useful for development/testing)
USE_MOCK=true
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CORTENSOR_ROUTER_URL` | URL of the Cortensor Router node | (none - enables demo mode) |
| `CORTENSOR_API_KEY` | Bearer token for API authentication | `default-dev-token` |
| `USE_MOCK` | Force demo mode even with router configured | `true` |

## Getting Router Access

1. Join [Cortensor Discord](https://discord.gg/cortensor)
2. Request Router v1 access in the developer channels
3. You'll receive a router URL like `https://router-1.cortensor.network`
4. Update your `.env.local` with the URL and set `USE_MOCK=false`
