# Cortensor API Server

A Next.js-based API server that provides backend services for the Cortensor AI platform, including AI chat endpoints and integration with the Cortensor network.

## 🚀 Overview

The Cortensor API Server is a lightweight, scalable backend service that handles AI interactions, manages sessions, and provides a bridge between the frontend applications and the Cortensor AI network. It's built with Next.js 15 for optimal performance and developer experience.

## ✨ Features

- **AI Chat API**: RESTful endpoints for AI chat interactions
- **Session Management**: Handles AI conversation sessions
- **Cortensor Integration**: Direct integration with Cortensor AI models
- **Web Search**: Web search capabilities through Tavily integration
- **Scalable Architecture**: Built for horizontal scaling
- **Type Safety**: Full TypeScript support
- **API Documentation**: OpenAPI/Swagger documentation support

## 🏗️ Architecture

### Tech Stack
- **Backend Framework**: Next.js 15 with App Router
- **Runtime**: Node.js 18+
- **AI Integration**: Cortensor OpenAI Provider
- **Search**: Tavily web search integration
- **State Management**: In-memory and persistent storage options
- **API Design**: RESTful API with JSON responses

### Project Structure
```
apps/server/
├── src/
│   ├── app/                 # Next.js app router
│   │   ├── api/            # API route handlers
│   │   │   └── chat/       # Chat API endpoints
│   │   ├── globals.css     # Global styles
│   │   ├── layout.tsx      # Root layout
│   │   └── page.tsx        # Home page
│   ├── lib/                # Utility functions and configurations
│   ├── types/              # TypeScript type definitions
│   └── middleware.ts       # Request/response middleware
├── public/                 # Static assets
├── next.config.ts          # Next.js configuration
└── package.json            # Dependencies and scripts
```

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- pnpm package manager
- Access to Cortensor API
- Tavily API key (for web search)

### Installation

1. **Navigate to the server directory**
   ```bash
   cd apps/server
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   ```

   Required environment variables:
   ```bash
   # Cortensor API
   CORTENSOR_API_KEY=your_api_key
   CORTENSOR_BASE_URL=https://your_api_url
   
   # Web Search (Tavily)
   TAVILY_API_KEY=your_tavily_key
   
   # Server Configuration
   PORT=3002
   NODE_ENV=development
   ```

### Development

```bash
# Start development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Type checking
pnpm check-types

# Linting
pnpm lint
```

The server will be available at [http://localhost:3002](http://localhost:3002).

## 🔌 API Endpoints

### Chat API

#### POST `/api/chat`
Main endpoint for AI chat interactions.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "sessionId": 12345,
  "enableSearch": false,
  "modelConfig": {
    "temperature": 0.7,
    "maxTokens": 1000
  }
}
```

**Response:**
```json
{
  "response": "Hello! I'm doing well, thank you for asking. How can I help you today?",
  "sessionId": 12345,
  "timestamp": "2024-01-01T00:00:00.000Z",
  "usage": {
    "promptTokens": 10,
    "completionTokens": 20,
    "totalTokens": 30
  }
}
```

#### GET `/api/chat/sessions/:sessionId`
Retrieve chat session information.

#### DELETE `/api/chat/sessions/:sessionId`
Clear a chat session.

### Health Check

#### GET `/api/health`
Server health status endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "version": "1.0.0"
}
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CORTENSOR_API_KEY` | Cortensor API authentication key | Yes | - |
| `CORTENSOR_BASE_URL` | Cortensor API base URL | Yes | - |
| `TAVILY_API_KEY` | Tavily search API key | No | - |
| `PORT` | Server port number | No | 3002 |
| `NODE_ENV` | Environment mode | No | development |
| `UPSTASH_REDIS_REST_URL` | Redis connection URL | No | - |
| `UPSTASH_REDIS_REST_TOKEN` | Redis authentication token | No | - |

### Next.js Configuration
The server uses Next.js 15 with custom configuration for:
- API route handling
- CORS configuration
- Request/response middleware
- Performance optimization

## 🧠 AI Integration

### Cortensor Provider
The server integrates with Cortensor AI models through the `@repo/ai` package:

```typescript
import { cortiGPTAgent } from '@repo/ai';

// Use the agent for chat interactions
const response = await cortiGPTAgent.generate({
  messages: userMessages,
  sessionId: sessionId
});
```

### Web Search Integration
Web search capabilities through Tavily integration:

```typescript
import { createTavilySearch } from 'cortensor-openai-provider';

const searchProvider = createTavilySearch({
  apiKey: process.env.TAVILY_API_KEY,
  maxResults: 5
});
```

### Session Management
- **Session Persistence**: Maintains conversation context
- **Memory Management**: Automatic cleanup of old sessions
- **State Tracking**: Tracks user interactions and preferences

## 🔒 Security & Middleware

### CORS Configuration
Configured for cross-origin requests with proper security headers.

### Rate Limiting
Built-in rate limiting for API endpoints to prevent abuse.

### Input Validation
Zod schema validation for all incoming requests.

### Authentication
API key validation for Cortensor integration.

## 📊 Monitoring & Logging

### Health Checks
- **Liveness Probe**: `/api/health` endpoint
- **Readiness Probe**: Dependency health checks
- **Metrics**: Performance and usage metrics

### Logging
- **Request Logging**: All API requests and responses
- **Error Logging**: Detailed error information
- **Performance Logging**: Response time tracking

### Metrics
- **Request Count**: Total API requests
- **Response Time**: Average response times
- **Error Rate**: Error percentage
- **Active Sessions**: Current active chat sessions

## 🚀 Deployment

### Production Build
```bash
# Build the application
pnpm build

# Start production server
pnpm start
```

### Environment Configuration
Ensure all production environment variables are set:
- Cortensor API credentials
- Search provider keys
- Monitoring and logging configuration
- Security settings

### Scaling Considerations
- **Horizontal Scaling**: Stateless design for easy scaling
- **Load Balancing**: Support for multiple server instances
- **Caching**: Redis integration for session caching
- **Database**: Optional database integration for persistence

## 🧪 Testing

### API Testing
- **Endpoint Testing**: Test all API endpoints
- **Integration Testing**: Test with Cortensor API
- **Load Testing**: Performance under load
- **Security Testing**: Authentication and validation

### Development Testing
- **Type Checking**: TypeScript compilation
- **Linting**: ESLint code quality checks
- **Unit Testing**: Individual function testing (when implemented)

## 🔍 Troubleshooting

### Common Issues

1. **Cortensor API Errors**
   - Verify API key and base URL
   - Check network connectivity
   - Validate request format

2. **Search Integration Issues**
   - Verify Tavily API key
   - Check search provider configuration
   - Validate search query format

3. **Session Management Problems**
   - Check Redis connection (if enabled)
   - Verify session ID format
   - Monitor memory usage

### Debug Mode
Enable debug logging:
```bash
NODE_ENV=development
DEBUG=*
LOG_LEVEL=debug
```

### Log Analysis
- **Request Logs**: API endpoint access logs
- **Error Logs**: Detailed error information
- **Performance Logs**: Response time analysis

## 📚 Additional Resources

- [Next.js API Routes](https://nextjs.org/docs/api-routes/introduction)
- [Cortensor Provider Documentation](../../readmeaboutCortensorOpenaiProvider.md)
- [AI Package Documentation](../../packages/ai/README.md)
- [Tavily Search API](https://tavily.com/docs)

## 🤝 Contributing

1. Follow the project's coding standards
2. Test API endpoints thoroughly
3. Update API documentation for new endpoints
4. Ensure proper error handling and validation

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../../LICENSE) file for details.

---

Built with ❤️ using Next.js and the Cortensor AI platform.
