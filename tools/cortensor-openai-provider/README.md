# Cortensor OpenAI Provider

 🚧 **EXPERIMENTAL - ACTIVELY IN DEVELOPMENT** 🚧

OpenAI-compatible provider for Cortensor AI models, designed to work seamlessly with Vercel AI SDK and popular agent frameworks.

## Features

- 🔄 **OpenAI Compatibility**: Drop-in replacement for OpenAI provider
- 🎯 **Session Management**: Built-in session handling for conversation continuity
- 🔀 **Request/Response Transformation**: Seamless format conversion between OpenAI and Cortensor APIs
- 🔍 **Web Search Integration**: Built-in web search capabilities with Tavily provider support
- 🔧 **Custom Search Providers**: Flexible web search provider interface for custom implementations
- 📘 **TypeScript Support**: Full type safety with comprehensive TypeScript definitions
- 🤖 **Agent Framework Ready**: Compatible with Mastra, Convex, and other AI agent frameworks
- ⚡ **Lightweight**: Minimal dependencies for optimal performance

> **Note**: Streaming responses are currently disabled and will be available in future releases.

## Installation

```bash
pnpm add cortensor-openai-provider
# or
npm install cortensor-openai-provider
# or
yarn add cortensor-openai-provider
```

### Dependencies

The package includes the following key dependencies:
- `@ai-sdk/openai-compatible`: OpenAI compatibility layer
- `@tavily/core`: Built-in web search provider (Tavily integration)
- `ai`: Peer dependency for Vercel AI SDK integration

> **Note**: The `@tavily/core` dependency is included for the built-in web search functionality, but you can use custom search providers without requiring a Tavily API key.

## Environment Setup

```bash
# .env.local or .env
CORTENSOR_API_KEY=your_cortensor_api_key_here
CORTENSOR_BASE_URL=https://your-cortensor-api-url.com

# Optional: For web search functionality
TAVILY_API_KEY=your_tavily_api_key_here
```

> **Important**: Both `CORTENSOR_API_KEY` and `CORTENSOR_BASE_URL` are required environment variables. `TAVILY_API_KEY` is optional and only needed if you want to use the built-in Tavily web search provider.

## 🔍 Web Search Integration

The Cortensor OpenAI Provider includes powerful web search capabilities that allow your AI models to access real-time information from the internet. This feature supports multiple search providers and flexible configuration options.

### Search Modes

The web search functionality supports three different modes:

- **`prompt`** (default): Search is triggered by `[search]` markers in user messages
- **`force`**: Always perform web search for every request
- **`disable`**: Completely disable web search functionality

### Search Directives

You can control search behavior using special markers in your messages:

- **`[**search**]`**: Forces a web search for this message (removed from final prompt)
- **`[**no-search**]`**: Prevents web search for this message (removed from final prompt)

### Built-in Tavily Provider

```typescript
import { cortensorModel, createTavilySearch } from 'cortensor-openai-provider';
import { generateText } from 'ai';

// Create Tavily search provider
const tavilySearch = createTavilySearch({
  apiKey: process.env.TAVILY_API_KEY, // Optional if set in environment
  maxResults: 1,
  searchDepth: 'advanced'
});

// Use with cortensorModel
const result = await generateText({
  model: cortensorModel({
    sessionId: 12345,
    webSearch: {
      mode: 'prompt', // 'prompt' | 'force' | 'disable'
      provider: tavilySearch,
      maxResults: 1
    }
  }),
  messages: [{ 
    role: 'user', 
    content: '[**search**] What are the latest developments in AI?' 
  }],
});
```

### Custom Search Providers

You can implement your own search provider by following the `WebSearchProvider` interface:

```typescript
import type { WebSearchProvider, WebSearchResult } from 'cortensor-openai-provider';

// Option 1: Implement WebSearchProvider interface
class CustomSearchProvider implements WebSearchProvider {
  async search(query: string, maxResults?: number): Promise<WebSearchResult[]> {
    // Your custom search implementation
    const results = await yourSearchAPI(query, maxResults);
    
    return results.map(result => ({
      title: result.title,
      url: result.url,
      snippet: result.description,
      publishedDate: result.date // optional
    }));
  }
}

// Option 2: Use a simple function
const customSearchFunction = async (query: string, maxResults?: number) => {
  // Your search logic here
  return [
    {
      title: "Example Result",
      url: "https://example.com",
      snippet: "This is an example search result"
    }
  ];
};

// Use either approach
const model = cortensorModel({
  sessionId: 12345,
  webSearch: {
    mode: 'prompt',
    provider: new CustomSearchProvider(), // or customSearchFunction
    maxResults: 3
  }
});
```

### Web Search Configuration

```typescript
interface WebSearchConfig {
  mode: 'prompt' | 'force' | 'disable';
  provider?: WebSearchProvider | ((query: string, maxResults?: number) => Promise<WebSearchResult[]>);
  maxResults?: number; // Default: 5
}
```

### Search Result Format

Search results are automatically formatted with numbered citations and included in the model's response:

```markdown
**Sources:**
[1] [First Result Title](https://example1.com)
[2] [Second Result Title](https://example2.com)
[3] [Third Result Title](https://example3.com)
```

This format follows modern AI chatbot best practices, similar to platforms like Perplexity AI, providing clean numbered citations that make it easy to reference specific sources.

## Quick Start

### Basic Usage with Vercel AI SDK

```typescript
import { cortensorModel } from 'cortensor-openai-provider';
import { generateText } from 'ai';

const result = await generateText({
  model: cortensorModel({
    sessionId: 12345,
    modelName: 'cortensor-chat',
    temperature: 0.7,
    maxTokens: 3000,
  }),
  messages: [{ role: 'user', content: 'Hello!' }],
});

console.log(result.text);
```

### Environment Variables Required

```bash
# .env.local or .env
CORTENSOR_API_KEY=your_cortensor_api_key_here
CORTENSOR_BASE_URL=https://your-cortensor-api-url.com
```

## Agent Framework Integration

### 🤖 Mastra Agents

```typescript
import { cortensorModel } from 'cortensor-openai-provider';
import { Agent, createMastra } from '@mastra/core';

const mastra = createMastra({
  agents: {
    cortensorAgent: new Agent({
      name: 'cortensor-agent',
      instructions: 'You are a helpful AI assistant.',
      model: cortensorModel({
        sessionId: 11111,
        modelName: 'cortensor-chat',
        temperature: 0.7,
        maxTokens: 256,
      }),
    }),
  },
});

// Use the agent
const response = await mastra.agents.cortensorAgent.generate({
  messages: [{ role: 'user', content: 'Hello!' }],
});
```

### 🔄 Convex Agents

```typescript
// convex/agents.ts
import { cortensorModel } from 'cortensor-openai-provider';
import { generateText } from 'ai';
import { mutation } from './_generated/server';
import { v } from 'convex/values';

export const sendMessage = mutation({
  args: {
    conversationId: v.id('conversations'),
    message: v.string(),
    sessionId: v.number(),
  },
  handler: async (ctx, { conversationId, message, sessionId }) => {
    const conversation = await ctx.db.get(conversationId);
    if (!conversation) throw new Error('Conversation not found');

    const messages = [...conversation.messages, { role: 'user' as const, content: message }];

    const result = await generateText({
      model: cortensorModel({
        sessionId,
        modelName: 'cortensor-chat',
        temperature: 0.7,
        maxTokens: 512,
      }),
      messages,
    });

    const aiMessage = { role: 'assistant' as const, content: result.text };
    const updatedMessages = [...messages, aiMessage];

    await ctx.db.patch(conversationId, {
      messages: updatedMessages,
      updatedAt: Date.now(),
    });

    return { message: result.text };
  },
});
```

## Framework Examples

### Next.js API Route

```typescript
// app/api/chat/route.ts
import { cortensorModel, createTavilySearch } from 'cortensor-openai-provider';
import { generateText } from 'ai';
import { NextRequest } from 'next/server';

// Create search provider (can be reused across requests)
const searchProvider = createTavilySearch({
  maxResults: 3,
  searchDepth: 'basic'
});

export async function POST(req: NextRequest) {
  const { messages, sessionId, enableSearch = false } = await req.json();

  const result = await generateText({
    model: cortensorModel({
      sessionId,
      modelName: 'cortensor-chat',
      temperature: 0.7,
      maxTokens: 256,
      // Enable web search if requested
      ...(enableSearch && {
        webSearch: {
          mode: 'prompt',
          provider: searchProvider,
          maxResults: 3
        }
      })
    }),
    messages,
  });

  return Response.json({ response: result.text });
}
```

#### Usage with Web Search

```typescript
// Client-side usage
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    sessionId: 12345,
    enableSearch: true,
    messages: [{
      role: 'user',
      content: '[**search**] What are the latest AI developments in 2024?'
    }]
  })
});
```

### Express.js Server

```typescript
import express from 'express';
import { cortensorModel } from 'cortensor-openai-provider';
import { generateText } from 'ai';

const app = express();
app.use(express.json());

app.post('/api/chat', async (req, res) => {
  const { messages, sessionId } = req.body;
  
  const result = await generateText({
    model: cortensorModel({
      sessionId,
      modelName: 'cortensor-chat',
      temperature: 0.7,
      maxTokens: 256,
    }),
    messages,
  });
  
  res.json({ response: result.text });
});
```

## API Reference

### `cortensorModel(config)`

Creates a Cortensor model instance with session management.

**Parameters:**
- `config` (object, required):
  - `sessionId` (number, required): Session ID for conversation continuity
  - `modelName` (string, optional): Model name (default: 'cortensor-chat')
  - `temperature` (number, optional): Sampling temperature 0.0-2.0 (default: 0.7)
  - `maxTokens` (number, optional): Maximum tokens to generate (default: 3000)
  - `topP` (number, optional): Top-p sampling parameter (default: 0.95)
  - `topK` (number, optional): Top-k sampling parameter (default: 40)
  - `presencePenalty` (number, optional): Presence penalty -2.0 to 2.0 (default: 0)
  - `frequencyPenalty` (number, optional): Frequency penalty -2.0 to 2.0 (default: 0)
  - `stream` (boolean, optional): Enable streaming (default: false, currently disabled)
  - `timeout` (number, optional): Request timeout in seconds (default: 60)
  - `promptType` (number, optional): Prompt type identifier (default: 1)
  - `promptTemplate` (string, optional): Custom prompt template (default: '')
  - `webSearch` (object, optional): Web search configuration
    - `mode` ('prompt' | 'force' | 'disable'): Search mode (default: 'prompt')
    - `provider` (WebSearchProvider | function): Search provider instance or function
    - `maxResults` (number, optional): Maximum search results (default: 3)

### `createCortensorProvider(config?)`

Creates a custom Cortensor provider with specific configuration.

**Parameters:**
- `config` (object, optional):
  - `apiKey` (string, optional): Override API key
  - `baseURL` (string, optional): Override base URL
  - `timeout` (number, optional): Request timeout
  - `sessionTimeout` (number, optional): Session timeout

### `clearModelConfigurations(sessionId?)`

Clears stored model configurations.

**Parameters:**
- `sessionId` (number, optional): Clear configs for specific session, or all if omitted

## Session Management

Sessions maintain conversation context across multiple requests:

```typescript
// Use consistent sessionId for conversation continuity
const sessionId = 98765;

const model = cortensorModel({
  sessionId,
  modelName: 'cortensor-chat',
  temperature: 0.7,
  maxTokens: 256,
});

// All requests with this model will share the same session
const response1 = await generateText({ model, messages: [...] });
const response2 = await generateText({ model, messages: [...] });

// Clear session when done
import { clearModelConfigurations } from 'cortensor-openai-provider';
clearModelConfigurations(sessionId);
```

## Error Handling

```typescript
try {
  const result = await generateText({
    model: cortensorModel({
      sessionId: 12345,
      modelName: 'cortensor-chat',
      temperature: 0.7,
      maxTokens: 3000,
    }),
    messages,
  });
} catch (error) {
  console.error('Cortensor API error:', error);
  // Handle error appropriately
}
```

## Development Status

### Current Status
- ✅ Basic OpenAI compatibility
- ✅ Session management with automatic cleanup
- ✅ **Web search integration with Tavily provider**
- ✅ **Custom web search provider support**
- ✅ **Search directives and flexible search modes**
- ✅ Full TypeScript support with comprehensive types
- ✅ Agent framework integration (Mastra, Convex)
- ✅ Request/response transformation
- ✅ Error handling and validation
- ❌ Streaming responses (coming in future releases)
- ❌ Image handling (planned)
- ❌ Advanced prompt template handling (experimental)

### Known Limitations
- Streaming is currently disabled
- Image processing not yet supported
- Prompt template functionality may not work reliably
- Web search requires external API keys (Tavily or custom provider)

## Roadmap

### 🚀 Upcoming Features

#### Support for LanguageModelV2
- **Enhanced model capabilities**: Leverage Cortensor's advanced language models with LanguageModelV2 interface
- **Batch processing**: Support for processing multiple requests in parallel
- **Advanced model features**: Full compatibility with AI SDK's LanguageModelV2 specification
- **Improved type safety**: Enhanced TypeScript support for LanguageModelV2 methods
- **Better error handling**: Comprehensive error management for LanguageModelV2 operations

### Streaming Support
- **Real-time streaming responses**: Enable streaming for real-time AI responses
- **Stream cancellation**: Support for cancelling ongoing streams
- **Backpressure handling**: Proper stream flow control
- **Error recovery**: Graceful handling of stream interruptions

#### Multimodal Support
- **Image input handling**: Support for image uploads and processing
- **Vision model integration**: Connect with Cortensor's vision capabilities
- **File attachment support**: Handle various file formats
- **Base64 image encoding**: Automatic image format conversion

#### Advanced Prompt Engineering
- **Custom prompt templates**: Robust template system with variable substitution
- **Template validation**: Ensure prompt templates are properly formatted
- **Template library**: Pre-built templates for common use cases
- **Dynamic prompt generation**: Context-aware prompt modification

#### Tool Calling & Enhanced Features
- **Tool calling**: Proper tool/function calling capabilities for agent interactions
- **Function calling**: Support for external function execution
- **Persistent sessions**: Database-backed session storage
- **Rate limiting**: Built-in request throttling
- **Caching layer**: Response caching for improved performance
- **Metrics and monitoring**: Usage analytics and performance tracking

> **Note**: Some features depend on capabilities that are not yet available in the Cortensor network infrastructure. This provider is designed to work seamlessly with the Cortensor network as new features become available.

### 🔬 Experimental Features

> **Note**: These features are experimental and may not work reliably in the current version.

- **Prompt Templates**: Basic template support is available but may have limitations
- **Custom Model Parameters**: Advanced model configuration options
- **Session Persistence**: Experimental session storage mechanisms

### 🌐 Cortensor Network Integration

This provider is specifically built to work with the Cortensor network infrastructure. For comprehensive documentation on building with Cortensor network, including API reference and integration guides, visit:

**📚 [Cortensor Web2 API Reference](https://docs.cortensor.network/getting-started/web2-api-reference)**

The provider abstracts the complexity of direct API calls while maintaining full compatibility with Cortensor's RESTful endpoints for sessions, tasks, miners, and completions.

## Contributing

This is an experimental package. Contributions, feedback, and bug reports are welcome!

## License

MIT License

## Support

For issues and questions, please open an issue on the repository.