# CortiGPT - Decentralized AI Platform

> **A comprehensive monorepo for decentralized AI chat and search capabilities powered by the Cortensor network**

## 🚀 Quick Overview

CortiGPT is a complete AI platform that combines blockchain technology with AI-powered search and chat capabilities. This project is part of the [Cortensor Community Projects](https://github.com/cortensor/community-projects).

### What's Included

- **🌐 Web Application** - Full-featured AI chat interface with Web3 integration
- **🔌 Browser Extension** - Cross-browser AI assistant with sidepanel interface  
- **🖥️ API Server** - Scalable backend for AI services and chat management
- **🤖 AI Package** - Shared AI integration library with Mastra framework

## 🛠️ Tech Stack

- **Frontend**: Next.js 15, React 19, Tailwind CSS, shadcn/ui
- **AI Integration**: Cortensor OpenAI Provider, Mastra Framework
- **Blockchain**: Wagmi, Viem, RainbowKit
- **Development**: TypeScript, Turborepo, pnpm

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- pnpm 10.12.3+
- Git

### Installation

1. **Clone and install dependencies**
   ```bash
   git clone https://github.com/cortensor/community-projects.git
   cd community-projects/apps/cortigpt-monorepo
   pnpm install
   ```

2. **Set up environment variables**
   ```bash
   # Copy environment files for each app
   cp apps/web/.env.example apps/web/.env.local
   cp apps/extension/.env.example apps/extension/.env.local
   cp apps/server/.env.example apps/server/.env.local
   ```

3. **Configure your API keys**
   - Get your Cortensor API key from [Cortensor Network](https://cortensor.network)
   - Get Tavily API key for web search
   - Set up WalletConnect project ID for Web3 features

4. **Start development**
   ```bash
   pnpm dev
   ```

## 🌐 Live Demo

- **Website**: [cortigpt.jatique.dev](https://cortigpt.jatique.dev)
- **Original Repository**: [github.com/Ezejaemmanuel/cortigpt-monorepo](https://github.com/Ezejaemmanuel/cortigpt-monorepo)

## 📱 Applications

| App | Port | Description |
|-----|------|-------------|
| Web App | 3001 | Main web interface with AI chat |
| API Server | 3002 | Backend API for AI services |
| Extension | - | Browser extension (build and load) |

## 🔑 Key Features

- **🤖 Decentralized AI**: Powered by Cortensor network for verifiable intelligence
- **🔗 Web3 Integration**: Full blockchain wallet support
- **🧠 AI Agents**: Intelligent chat assistants with context awareness
- **🌐 Web Search**: Real-time information retrieval
- **📱 Cross-Platform**: Web app and browser extension
- **🎨 Modern UI**: Beautiful, responsive design

## 📚 Documentation

For detailed documentation, setup instructions, and API reference, see the main [README.md](./README.md) file.

## 🤝 Contributing

This project is actively maintained. For contributions:

1. Check the [original repository](https://github.com/Ezejaemmanuel/cortigpt-monorepo) for the latest updates
2. Follow the contribution guidelines in the main README
3. Test your changes across all applications

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

## 🔗 Links

- **Original Repository**: [Ezejaemmanuel/cortigpt-monorepo](https://github.com/Ezejaemmanuel/cortigpt-monorepo)
- **Cortensor Network**: [cortensor.network](https://cortensor.network)
- **Documentation**: [docs.cortensor.network](https://docs.cortensor.network)
- **Community Projects**: [cortensor/community-projects](https://github.com/cortensor/community-projects)

---

*This project is part of the Cortensor community ecosystem, bringing decentralized AI to everyone.*
