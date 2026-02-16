# Cortensor AI Package

A comprehensive AI integration package that provides Cortensor AI model integration, agent management, and AI framework compatibility for the Cortensor ecosystem.

## 🚀 Overview

The Cortensor AI Package (`@repo/ai`) is a shared library that provides AI capabilities across all applications in the Cortensor monorepo. It integrates with the Cortensor network, manages AI agents, and provides a unified interface for AI interactions.

## ✨ Features

- **Cortensor Integration**: Direct integration with Cortensor AI models
- **Agent Framework**: Mastra agent framework integration
- **AI SDK Compatibility**: Vercel AI SDK integration
- **Web Search**: Built-in web search capabilities
- **Session Management**: AI conversation session handling
- **Type Safety**: Full TypeScript support
- **Framework Agnostic**: Works with any React-based application

## 🏗️ Architecture

### Tech Stack
- **AI Framework**: Mastra for agent management
- **AI Provider**: Cortensor OpenAI Provider
- **Search Integration**: Tavily web search
- **Runtime**: Node.js 18+
- **Package Manager**: pnpm workspace

### Project Structure
```
packages/ai/
├── src/
│   ├── index.ts             # Main package exports
│   ├── server.ts            # Server-side exports
│   ├── constants.ts         # Shared constants
│   ├── types.ts             # TypeScript type definitions
│   ├── utils.ts             # Utility functions
│   └── mastra/              # Mastra agent framework
│       ├── index.ts         # Mastra configuration
│       └── agents/          # AI agent definitions
│           └── cortigpt-agent.ts  # CortiGPT agent
├── package.json             # Package configuration
└── tsconfig.json            # TypeScript configuration
```

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- pnpm package manager
- Access to Cortensor API
- Tavily API key (for web search)

### Installation

The package is automatically available in the monorepo workspace. For external projects:

```bash
pnpm add @repo/ai
```

### Environment Setup

Required environment variables:
```bash
# Cortensor API
CORTENSOR_API_KEY=your_api_key
CORTENSOR_BASE_URL=https://your_api_url

# Web Search (Tavily)
TAVILY_API_KEY=your_tavily_key
```

## 🔌 Usage

### Basic Import

```typescript
// Import main exports
import { CHAT_HISTORY_LIMIT } from '@repo/ai';

// Import server-side exports
import { mastra, cortiGPTAgent } from '@repo/ai/server';
```

### Using the CortiGPT Agent

```typescript
import { cortiGPTAgent } from '@repo/ai/server';

// Generate a response using the agent
const response = await cortiGPTAgent.generate({
  messages: [
    { role: 'user', content: 'Hello, how are you?' }
  ],
  sessionId: 12345
});

console.log(response.text);
```

### Using Mastra Framework

```typescript
import { mastra } from '@repo/ai/server';

// Access the configured Mastra instance
const agents = mastra.agents;

// Use specific agents
const cortiGPT = agents.cortiGPTAgent;
const response = await cortiGPT.generate({
  messages: userMessages,
  sessionId: sessionId
});
```

## 🧠 AI Agents

### CortiGPT Agent

The main AI agent that provides intelligent chat capabilities:

```typescript
import { cortiGPTAgent } from '@repo/ai/server';

// Agent configuration
const agent = cortiGPTAgent;

// Features
// - Cortensor AI model integration
// - Web search capabilities
// - Session management
// - Dynamic instruction generation
// - Memory handling
```

#### Agent Capabilities

- **Natural Language Processing**: Understands and responds to user queries
- **Web Search Integration**: Can search the web for real-time information
- **Context Awareness**: Maintains conversation context across sessions
- **Dynamic Instructions**: Generates context-aware instructions
- **Memory Management**: Handles chat history and session state

#### Web Search Usage

The agent supports web search through special markers:

```typescript
// Force web search
const searchQuery = "[search] What are the latest AI developments?";

// Prevent web search
const noSearchQuery = "[no-search] Tell me a joke";

// Default behavior (prompt-based)
const normalQuery = "Hello, how are you?";
```

## 🔧 Configuration

### Mastra Configuration

The package provides a pre-configured Mastra instance:

```typescript
import { mastra } from '@repo/ai/server';

// Configuration includes:
// - CortiGPT agent
// - Logging setup
// - Error handling
// - Performance monitoring
```

### Agent Configuration

Each agent can be configured with specific parameters:

```typescript
// Agent configuration options
const agentConfig = {
  name: 'CortiGPT',
  instructions: 'Custom instructions for the agent',
  model: cortensorModel({
    sessionId: 12345,
    maxTokens: 4096,
    temperature: 0.4,
    webSearch: {
      mode: 'prompt',
      provider: createTavilySearch({
        apiKey: process.env.TAVILY_API_KEY,
      }),
      maxResults: 2
    }
  })
};
```

## 🌐 Web Search Integration

### Built-in Tavily Provider

```typescript
import { createTavilySearch } from 'cortensor-openai-provider';

const searchProvider = createTavilySearch({
  apiKey: process.env.TAVILY_API_KEY,
  maxResults: 5,
  searchDepth: 'advanced'
});
```

### Custom Search Providers

Implement custom search providers:

```typescript
import type { WebSearchProvider, WebSearchResult } from 'cortensor-openai-provider';

class CustomSearchProvider implements WebSearchProvider {
  async search(query: string, maxResults?: number): Promise<WebSearchResult[]> {
    // Your custom search implementation
    return [
      {
        title: "Example Result",
        url: "https://example.com",
        snippet: "This is an example search result"
      }
    ];
  }
}
```

## 📊 Constants and Configuration

### Chat History Limit

```typescript
import { CHAT_HISTORY_LIMIT } from '@repo/ai';

// Default chat history limit
console.log(CHAT_HISTORY_LIMIT); // Output: 100
```

### Available Constants

- `CHAT_HISTORY_LIMIT`: Maximum number of messages to keep in chat history
- Additional constants can be added as needed

## 🔌 Integration Examples

### Next.js API Route

```typescript
// app/api/chat/route.ts
import { cortiGPTAgent } from '@repo/ai/server';
import { NextRequest } from 'next/server';

export async function POST(req: NextRequest) {
  const { messages, sessionId } = await req.json();
  
  try {
    const response = await cortiGPTAgent.generate({
      messages,
      sessionId
    });
    
    return Response.json({ 
      response: response.text,
      sessionId 
    });
  } catch (error) {
    return Response.json({ error: 'AI generation failed' }, { status: 500 });
  }
}
```

### Express.js Server

```typescript
import express from 'express';
import { cortiGPTAgent } from '@repo/ai/server';

const app = express();
app.use(express.json());

app.post('/api/chat', async (req, res) => {
  const { messages, sessionId } = req.body;
  
  try {
    const response = await cortiGPTAgent.generate({
      messages,
      sessionId
    });
    
    res.json({ response: response.text });
  } catch (error) {
    res.status(500).json({ error: 'AI generation failed' });
  }
});
```

### React Component

```typescript
import { useState } from 'react';
import { cortiGPTAgent } from '@repo/ai/server';

function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [sessionId] = useState(12345);

  const sendMessage = async (content: string) => {
    const userMessage = { role: 'user', content };
    const newMessages = [...messages, userMessage];
    
    try {
      const response = await cortiGPTAgent.generate({
        messages: newMessages,
        sessionId
      });
      
      setMessages([...newMessages, { role: 'assistant', content: response.text }]);
    } catch (error) {
      console.error('Failed to generate response:', error);
    }
  };

  return (
    <div>
      {/* Chat UI implementation */}
    </div>
  );
}
```

## 🚀 Development

### Local Development

```bash
# Navigate to the package directory
cd packages/ai

# Install dependencies
pnpm install

# Type checking
pnpm check-types

# Mastra development
pnpm mastra:dev

# Mastra build
pnpm mastra:build
```

### Adding New Agents

1. **Create agent file** in `src/mastra/agents/`
2. **Export agent** from `src/mastra/index.ts`
3. **Update types** in `src/types.ts` if needed
4. **Test integration** with the main application

### Example Agent

```typescript
// src/mastra/agents/custom-agent.ts
import { Agent } from '@mastra/core';
import { cortensorModel } from 'cortensor-openai-provider';

export const customAgent = new Agent({
  name: 'CustomAgent',
  instructions: 'You are a custom AI agent.',
  model: cortensorModel({
    sessionId: 12345,
    temperature: 0.7,
    maxTokens: 1000
  })
});
```

## 🧪 Testing

### Type Checking

```bash
# Run TypeScript compilation
pnpm check-types
```

### Integration Testing

Test the package with the main applications:

```bash
# Test with web app
cd apps/web && pnpm dev

# Test with server
cd apps/server && pnpm dev

# Test with extension
cd apps/extension && pnpm dev
```

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure package is built: `pnpm build`
   - Check TypeScript configuration
   - Verify export paths

2. **Agent Configuration**
   - Verify environment variables
   - Check Cortensor API access
   - Validate search provider configuration

3. **Session Management**
   - Ensure unique session IDs
   - Check memory usage
   - Verify cleanup processes

### Debug Mode

Enable debug logging:

```bash
NODE_ENV=development
DEBUG=*
LOG_LEVEL=debug
```

## 📚 Additional Resources

- [Cortensor Provider Documentation](../../readmeaboutCortensorOpenaiProvider.md)
- [Mastra Framework Documentation](https://mastra.ai)
- [Vercel AI SDK Documentation](https://sdk.vercel.ai)
- [Cortensor Network Documentation](https://docs.cortensor.network)

## 🤝 Contributing

1. Follow the project's coding standards
2. Test new agents thoroughly
3. Update documentation for new features
4. Ensure backward compatibility

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../../LICENSE) file for details.

---

Built with ❤️ using the Mastra framework and Cortensor AI platform.
