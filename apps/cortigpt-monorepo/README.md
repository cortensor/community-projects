# Cortensor Main Monorepo 🚀

> **A comprehensive monorepo containing the complete Cortensor ecosystem - a decentralized AI platform that combines blockchain technology with AI-powered search and chat capabilities.**

[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![pnpm](https://img.shields.io/badge/pnpm-10.12.3+-blue.svg)](https://pnpm.io/)
[![Next.js](https://img.shields.io/badge/Next.js-15.4.6-black.svg)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.1.0-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📖 Table of Contents

- [Overview](#-overview)
- [Architecture](#️-architecture)
- [Project Structure](#-project-structure)
- [Applications](#-applications)
- [Packages](#-packages)
- [Quick Start](#-quick-start)
- [Development](#-development)
- [Deployment](#-deployment)
- [Environment Variables](#-environment-variables)
- [Available Scripts](#️-available-scripts)
- [Technology Stack](#-technology-stack)
- [Key Features](#-key-features)
- [API Reference](#-api-reference)
- [Contributing](#-contributing)
- [Support](#-support)
- [License](#-license)

## 🚀 Overview

**Cortensor** is a decentralized AI platform that provides verifiable, trustless intelligence through a network of distributed miners. This monorepo contains all the components needed to build, deploy, and interact with the Cortensor network.

### What's Included

- **🌐 Web Application** - Full-featured AI chat interface with Web3 integration
- **🔌 Browser Extension** - Cross-browser AI assistant with sidepanel interface
- **🖥️ API Server** - Scalable backend for AI services and chat management
- **🤖 AI Package** - Shared AI integration library with Mastra framework

## 🏗️ Architecture

This monorepo follows modern monorepo architecture principles using:

- **📦 Package Manager**: pnpm with workspace support for efficient dependency management
- **⚡ Build System**: Turborepo for optimized, parallel builds across applications
- **🎯 Frontend**: Next.js 15 with React 19 for modern, performant web applications
- **🎨 Styling**: Tailwind CSS with shadcn/ui for consistent, accessible design
- **🤖 AI Integration**: Cortensor OpenAI Provider for decentralized AI capabilities
- **🔗 Blockchain**: Web3 integration with Wagmi and Viem for blockchain interactions

## 📁 Project Structure

```
cortigpt-monorepo/
├── 📁 apps/                          # Application packages
│   ├── 🌐 web/                       # Main web application (Next.js 15)
│   │   ├── src/
│   │   │   ├── app/                  # Next.js App Router
│   │   │   ├── components/           # Reusable UI components
│   │   │   ├── hooks/                # Custom React hooks
│   │   │   ├── lib/                  # Utility libraries
│   │   │   ├── providers/            # Context providers
│   │   │   └── stores/               # State management
│   │   └── public/                   # Static assets
│   ├── 🔌 extension/                 # Browser extension (WXT + React)
│   │   ├── entrypoints/              # Extension entry points
│   │   ├── components/               # Extension-specific components
│   │   ├── hooks/                    # Extension hooks
│   │   └── public/                   # Extension assets
│   └── 🖥️ server/                    # API server (Next.js 15)
│       └── src/
│           └── app/
│               └── api/              # API routes
├── 📦 packages/                      # Shared packages
│   └── 🤖 ai/                       # AI integration package
│       ├── src/
│       │   ├── mastra/               # Mastra AI framework
│       │   │   └── agents/           # AI agent definitions
│       │   └── constants.ts          # Shared constants
│       └── package.json
├── 📄 pnpm-workspace.yaml            # Workspace configuration
├── ⚡ turbo.json                      # Turborepo configuration
├── 🚂 railway.json                   # Railway deployment config
└── 📋 package.json                   # Root package configuration
```

## 🎯 Applications

### 🌐 Web App (`apps/web`)

**Port**: 3001  
**Purpose**: Main web interface for CortiGPT with full AI chat capabilities

**Features**:
- 🤖 **AI Chat Interface**: Complete CortiGPT chat experience with Cortensor AI models
- 🔗 **Web3 Integration**: Full wallet connection with MetaMask, WalletConnect, and more
- 🎨 **Modern UI**: Beautiful, responsive design with Tailwind CSS and shadcn/ui
- 🌓 **Theme System**: Light/dark mode with system preference detection
- 📱 **Responsive Design**: Optimized for desktop, tablet, and mobile devices

**Tech Stack**: Next.js 15, React 19, Tailwind CSS, shadcn/ui, Framer Motion

### 🔌 Browser Extension (`apps/extension`)

**Name**: CortiGPT  
**Purpose**: Browser-side AI assistant with modern sidepanel interface

**Features**:
- 📱 **Sidepanel Interface**: Modern browser sidepanel experience across all browsers
- 🔄 **Dual Mode**: Web2 and Web3 chat interfaces for different use cases
- 🌐 **Cross-Browser**: Full support for Chrome, Firefox, Edge, and Safari
- 🤖 **AI Assistant**: Direct CortiGPT integration with real-time responses
- 💾 **Local Storage**: Persistent settings and chat history

**Tech Stack**: WXT Framework, React 19, Tailwind CSS, shadcn/ui

**Browser Support**:
- **Chrome**: Manifest V3 with native sidepanel
- **Edge**: Manifest V3 with native sidepanel
- **Firefox**: Manifest V2 with panel implementation
- **Safari**: Manifest V2 with popover interface

### 🖥️ API Server (`apps/server`)

**Port**: 3002  
**Purpose**: Scalable backend API for AI services and chat management

**Features**:
- 🔌 **Chat API**: `/api/chat` endpoint for AI interactions
- 👥 **Session Management**: User and chat ID handling with authentication
- 🤖 **Cortensor Integration**: Direct AI model access with web search capabilities
- 🔒 **Security**: Input validation, CORS, and rate limiting
- 📊 **Logging**: Comprehensive request and error logging

**Tech Stack**: Next.js 15, TypeScript, AI SDK integration

## 📦 Packages

### 🤖 AI Package (`packages/ai`)

**Purpose**: Shared AI integration library for all applications

**Features**:
- 🧠 **Mastra Framework**: AI agent management and orchestration
- 🔌 **Cortensor Provider**: Direct AI model integration with custom configuration
- 🌐 **Web Search**: Tavily integration for real-time information retrieval
- 📝 **Shared Types**: Common TypeScript interfaces across applications
- 🛠️ **Utility Functions**: Reusable AI helpers and constants

**Exports**:
- `cortiGPTAgent` - Main AI agent instance
- `CHAT_HISTORY_LIMIT` - Chat history management constant
- `mastra` - Mastra framework instance

## 🚀 Quick Start

### Prerequisites

- **Node.js**: 18+ (LTS recommended)
- **pnpm**: 10.12.3+
- **Git**: Latest version

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cortigpt-monorepo
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   ```

3. **Set up environment variables**
   ```bash
   # Copy environment files for each app
   cp apps/web/.env.example apps/web/.env.local
   cp apps/extension/.env.example apps/extension/.env.local
   cp apps/server/.env.example apps/server/.env.local
   ```

4. **Configure environment variables** (see [Environment Variables](#-environment-variables))

5. **Start development**
   ```bash
   pnpm dev
   ```

## 🛠️ Development

### Development Commands

```bash
# Start all applications
pnpm dev

# Start specific applications
pnpm dev:web          # Web app only (port 3001)
pnpm dev:extension    # Extension only
pnpm dev:server       # Server only (port 3002)

# Build all applications
pnpm build

# Type checking across monorepo
pnpm check-types

# Mastra development
pnpm mastra:dev       # Start Mastra development server
pnpm mastra:build     # Build Mastra application
```

### Development URLs

- **Web App**: http://localhost:3001
- **API Server**: http://localhost:3002
- **Extension**: Build and load in browser

### Hot Reload

All applications support hot reload for development:
- **Web App**: Next.js Fast Refresh
- **Extension**: WXT hot reload
- **Server**: Next.js API route hot reload

## 🚀 Deployment

### Railway.app Deployment (`apps/server`)

The server is configured for easy deployment on Railway.app:

```bash
# Build and deploy server
pnpm build:server
pnpm deploy:server
```

**Railway Configuration** (`railway.json`):
- **Build Command**: `pnpm install --filter=server && SKIP_ENV_VALIDATION=true pnpm build --filter=server`
- **Start Command**: `pnpm start --filter=server`
- **Restart Policy**: On failure with 10 max retries

### Other Deployment Options

- **Web App**: Deploy to Vercel, Netlify, or any Next.js-compatible platform
- **Extension**: Package and submit to browser stores
- **Server**: Deploy to Railway, Heroku, or any Node.js platform

## 🔐 Environment Variables

### Required Variables

```bash
# Cortensor AI Platform
CORTENSOR_API_KEY=your_cortensor_api_key
CORTENSOR_BASE_URL=https://api.cortensor.network

# Web Search (Tavily)
TAVILY_API_KEY=your_tavily_api_key

# Web3 Configuration
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_walletconnect_project_id
NEXT_PUBLIC_ARBITRUM_SEPOLIA_RPC_URL=your_arbitrum_sepolia_rpc_url
```

### Environment File Structure

```
apps/
├── web/
│   └── .env.local          # Web app environment variables
├── extension/
│   └── .env.local          # Extension environment variables
└── server/
    └── .env.local          # Server environment variables
```

## 📋 Available Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `pnpm dev` | Start all applications in development mode | `pnpm dev` |
| `pnpm build` | Build all applications for production | `pnpm build` |
| `pnpm start` | Start the server application | `pnpm start` |
| `pnpm check-types` | Run TypeScript type checking across all apps | `pnpm check-types` |
| `pnpm dev:web` | Start only the web application | `pnpm dev:web` |
| `pnpm dev:extension` | Start only the extension | `pnpm dev:extension` |
| `pnpm dev:server` | Start only the server | `pnpm dev:server` |
| `pnpm build:server` | Build only the server | `pnpm build:server` |
| `pnpm deploy:server` | Deploy the server | `pnpm deploy:server` |
| `pnpm mastra:dev` | Start Mastra development server | `pnpm mastra:dev` |
| `pnpm mastra:build` | Build Mastra application | `pnpm mastra:build` |

## 🔧 Technology Stack

### Frontend & UI
- **React 19** - Latest React with concurrent features and improved performance
- **Next.js 15** - Full-stack React framework with App Router
- **Tailwind CSS** - Utility-first CSS framework for rapid UI development
- **shadcn/ui** - Beautiful, accessible UI components built on Radix UI
- **Framer Motion** - Production-ready animation library for React

### AI & Backend
- **Cortensor OpenAI Provider** - Decentralized AI model integration
- **Mastra** - AI agent framework for building intelligent applications
- **Vercel AI SDK** - AI development toolkit with streaming support
- **Tavily** - Web search integration for real-time information retrieval

### Blockchain & Web3
- **Wagmi** - React hooks for Ethereum with TypeScript support
- **Viem** - TypeScript interface for Ethereum with modern APIs
- **RainbowKit** - Beautiful wallet connection UI for Web3

### Development Tools
- **TypeScript** - Type-safe JavaScript for better development experience
- **Turborepo** - High-performance monorepo build system
- **ESLint** - Pluggable JavaScript linting utility
- **Prettier** - Opinionated code formatter for consistent code style

## 🌟 Key Features

- **🤖 Decentralized AI**: Powered by the Cortensor network for verifiable intelligence
- **🔗 Web3 Integration**: Full blockchain wallet support and integration
- **🧠 AI Agents**: Intelligent chat assistants with context awareness
- **🌐 Web Search**: Real-time information retrieval from the web
- **📱 Cross-Platform**: Web app and browser extension for all devices
- **🎨 Modern UI**: Beautiful, responsive design with accessibility features
- **🔒 Type Safety**: Full TypeScript support across all applications
- **⚡ Performance**: Optimized builds and fast development experience

## 📚 API Reference

### Server API Endpoints

#### POST `/api/chat`
Main chat interaction endpoint for AI conversations.

**Request Body**:
```typescript
{
  messages: Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
  }>
}
```

**Query Parameters**:
- `userAddress`: User's blockchain address
- `chatId`: Unique chat session identifier

**Response**:
```typescript
{
  id: string;
  role: 'assistant';
  content: Array<{
    type: 'text';
    text: string;
  }>
}
```

### AI Package Exports

```typescript
// Main AI agent
import { cortiGPTAgent } from '@repo/ai/server';

// Constants
import { CHAT_HISTORY_LIMIT } from '@repo/ai/server';

// Mastra framework
import { mastra } from '@repo/ai/server';
```

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### Development Setup

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Run tests and checks**
   ```bash
   pnpm check-types
   pnpm build
   ```
5. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
6. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request**

### Contribution Guidelines

- Follow the existing code style and conventions
- Add TypeScript types for new features
- Update documentation for API changes
- Test your changes across all applications
- Ensure all builds pass before submitting

## 🆘 Support

### Getting Help

- **🐛 Bug Reports**: Open an issue on GitHub with detailed information
- **💡 Feature Requests**: Use GitHub issues to suggest new features
- **📚 Documentation**: Check the documentation in each app's README
- **🔧 Technical Issues**: Review the Cortensor provider documentation

### Community Resources

- **GitHub Issues**: [Repository Issues](https://github.com/ezejaemmanuel/cortigpt-monorepo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ezejaemmanuel/cortigpt-monorepo/discussions)
- **Documentation**: [Cortensor Docs](https://docs.cortensor.network)

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **🌐 Website**: [Cortensor Network](https://cortigpt.jatique.dev)
- **📚 Documentation**: [Cortensor Docs](https://docs.cortensor.network)
- **🔌 Provider**: [Cortensor OpenAI Provider](https://www.npmjs.com/package/cortensor-openai-provider)
- **🐙 Repository**: [GitHub Repository](https://github.com/ezejaemmanuel/cortigpt-monorepo)

---

**Built with ❤️ by [Jatique](https://github.com/ezejaemmanuel) using modern web technologies and decentralized AI principles.**

*Empowering the future of AI with blockchain technology.*
