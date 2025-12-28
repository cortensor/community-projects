# Cortensor Main Monorepo - Release Notes

## Version History

### v1.0.0 - January 2025 🚀
**Production Release - Complete CortiGPT Ecosystem**

#### 🎉 What's New
- **Complete Monorepo**: Web app, browser extension, API server, and AI package
- **Modern Stack**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **AI Integration**: Cortensor AI models with web search capabilities
- **Web3 Ready**: Wallet integration with Wagmi and RainbowKit

#### 🌐 Web Application (`apps/web`)
- **AI Chat Interface**: CortiGPT chat with Cortensor AI models
- **Web3 Integration**: MetaMask, WalletConnect support
- **Modern UI**: Responsive design with shadcn/ui components
- **Port**: 3001

#### 🔌 Browser Extension (`apps/extension`)
- **Sidepanel Interface**: Modern browser sidepanel experience
- **Dual Mode**: Web2 and Web3 chat interfaces
- **Cross-Browser**: Chrome, Firefox, Edge, Safari support
- **AI Assistant**: Direct CortiGPT integration

#### 🖥️ API Server (`apps/server`)
- **Chat API**: `/api/chat` endpoint for AI interactions
- **Session Management**: User and chat ID handling
- **Cortensor Integration**: Direct AI model access
- **Port**: 3002

#### 📦 AI Package (`packages/ai`)
- **Mastra Framework**: AI agent management
- **Cortensor Provider**: AI model integration
- **Web Search**: Tavily integration for real-time information

## Quick Start

```bash
# Install dependencies
pnpm install

# Start all apps
pnpm dev

# Individual development
pnpm dev:web          # Web app (port 3001)
pnpm dev:extension    # Extension
pnpm dev:server       # Server (port 3002)
```

## Deployment

### Railway.app Deployment (`apps/server`)
```bash
# Build and deploy server
pnpm build:server
pnpm deploy:server
```

**Railway Configuration** (`railway.json`):
- **Build Command**: `pnpm install --filter=server && SKIP_ENV_VALIDATION=true pnpm build --filter=server`
- **Start Command**: `pnpm start --filter=server`
- **Restart Policy**: On failure with 10 max retries

### Environment Variables
```bash
# Server (.env.local)
CORTENSOR_API_KEY=your_api_key
TAVILY_API_KEY=your_tavily_key

# Web App (.env.local)
CORTENSOR_API_KEY=your_api_key
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id

# Extension (.env.local)
VITE_CORTENSOR_API_KEY=your_api_key
VITE_WALLETCONNECT_PROJECT_ID=your_project_id
```

## Build Commands

```bash
# Build all applications
pnpm build

# Build specific apps
pnpm build:server
pnpm build:web
pnpm build:extension

# Extension packaging
cd apps/extension
pnpm zip
```

## Dependencies

- **Core**: Next.js 15, React 19, TypeScript 5
- **AI**: Cortensor OpenAI Provider, Mastra Framework
- **Web3**: Wagmi, Viem, RainbowKit
- **UI**: Tailwind CSS, shadcn/ui, Framer Motion
- **Build**: pnpm, Turborepo

## Browser Support

- **Chrome**: Manifest V3 with sidepanel
- **Edge**: Manifest V3 with native sidepanel
- **Firefox**: Manifest V2 with panel implementation
- **Safari**: Manifest V2 with popover interface

---

**Next Release**: v1.1.0 (February 2025)
- Extension store launches
- Enhanced AI capabilities
- Performance optimizations
