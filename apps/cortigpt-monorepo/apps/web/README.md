# CortiGPT Web Application

The main web interface for CortiGPT - a decentralized AI platform that combines blockchain technology with AI-powered search and chat capabilities.

## 🚀 Overview

CortiGPT Web is a modern, responsive web application that serves as the primary interface for users to interact with the Cortensor AI network. It provides an intuitive chat interface, showcases AI agents, and demonstrates the platform's capabilities.

## ✨ Features

- **AI Chat Interface**: Interactive chat with CortiGPT AI agents
- **Agent Showcase**: Display of available AI agents and their capabilities
- **Modern UI**: Beautiful, responsive design with Tailwind CSS and shadcn/ui
- **Web3 Integration**: Blockchain wallet connection and integration
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Theme Support**: Light and dark mode with system preference detection
- **Real-time Updates**: Live chat and dynamic content updates

## 🏗️ Architecture

### Tech Stack
- **Frontend Framework**: Next.js 15 with React 19
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: Zustand for client-side state
- **AI Integration**: Cortensor OpenAI Provider
- **Web3**: Wagmi and Viem for blockchain integration
- **UI Components**: Radix UI primitives with custom styling
- **Animations**: Framer Motion for smooth transitions

### Project Structure
```
apps/web/
├── src/
│   ├── app/                 # Next.js app router pages
│   ├── components/          # React components
│   │   ├── layout/         # Layout components (Navbar, etc.)
│   │   ├── sections/       # Page sections (Hero, AgentShowcase, etc.)
│   │   └── ui/             # Reusable UI components (shadcn/ui)
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utility functions and configurations
│   ├── providers/          # React context providers
│   ├── stores/             # Zustand state stores
│   └── types/              # TypeScript type definitions
├── public/                 # Static assets
├── tailwind.config.ts      # Tailwind CSS configuration
└── package.json            # Dependencies and scripts
```

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- pnpm package manager
- Access to Cortensor API

### Installation

1. **Navigate to the web app directory**
   ```bash
   cd apps/web
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
   
   # Web3 Configuration
   NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id
   NEXT_PUBLIC_ARBITRUM_SEPOLIA_RPC_URL=your_rpc_url
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

The application will be available at [http://localhost:3001](http://localhost:3001).

## 🎯 Key Components

### Layout Components
- **Navbar**: Main navigation with wallet connection and theme toggle
- **Footer**: Site footer with links and information

### Page Sections
- **Hero**: Main landing section with call-to-action
- **AgentShowcase**: Display of AI agents and their capabilities
- **HowItWorksNew**: Explanation of how the platform works
- **UseCases**: Examples of platform use cases
- **Footer**: Site footer with links and information

### UI Components
- **NeuralBackground**: Animated background with neural network effects
- **NewIntroSplash**: Introduction splash screen for new users
- **ConnectWalletButton**: Web3 wallet connection component
- **MarkdownRenderer**: Markdown content rendering

## 🔧 Configuration

### Tailwind CSS
The application uses Tailwind CSS with custom configuration for:
- Color schemes and themes
- Custom animations and transitions
- Responsive breakpoints
- Component-specific utilities

### shadcn/ui
Pre-configured with shadcn/ui components including:
- Buttons, inputs, and form elements
- Modals, dialogs, and overlays
- Navigation and layout components
- Data display components

### Web3 Configuration
Configured with Wagmi and Viem for:
- Wallet connection (RainbowKit)
- Blockchain network support
- Contract interactions
- Transaction handling

## 🌐 Pages and Routes

### Main Pages
- **Home** (`/`): Landing page with hero section and overview
- **Choose Mode** (`/choose-mode`): Mode selection for AI interaction
- **Chat Interface**: AI chat functionality (when implemented)

### API Routes
- **Chat API**: AI chat endpoints (when implemented)
- **Web3 Integration**: Blockchain interaction endpoints

## 🎨 Styling and Theming

### Design System
- **Color Palette**: Primary, secondary, and accent colors
- **Typography**: Custom font stack with Futura and tech fonts
- **Spacing**: Consistent spacing scale
- **Animations**: Smooth transitions and micro-interactions

### Responsive Design
- **Mobile First**: Optimized for mobile devices
- **Breakpoints**: Tailwind CSS responsive breakpoints
- **Flexible Layouts**: Adaptive layouts for different screen sizes

## 🔌 Integration Points

### AI Services
- **Cortensor Provider**: AI model integration
- **Chat History**: Conversation management
- **Agent Framework**: AI agent interactions

### Web3 Services
- **Wallet Connection**: Multiple wallet support
- **Blockchain Networks**: Arbitrum Sepolia and others
- **Smart Contracts**: Session management and verification

### External Services
- **Tavily Search**: Web search integration
- **Analytics**: Usage tracking and metrics
- **Storage**: Local and cloud storage options

## 🚀 Deployment

### Build Process
```bash
# Build the application
pnpm build

# Start production server
pnpm start
```

### Environment Configuration
Ensure all required environment variables are set in production:
- Cortensor API credentials
- Web3 configuration
- Search provider keys
- Analytics and monitoring

### Performance Optimization
- **Code Splitting**: Automatic route-based code splitting
- **Image Optimization**: Next.js image optimization
- **Bundle Analysis**: Webpack bundle analysis tools
- **Caching**: Static asset caching strategies

## 🧪 Testing

### Development Testing
- **Type Checking**: TypeScript compilation
- **Linting**: ESLint code quality checks
- **Component Testing**: React component testing (when implemented)

### Quality Assurance
- **Responsive Testing**: Cross-device compatibility
- **Browser Testing**: Cross-browser compatibility
- **Performance Testing**: Core Web Vitals optimization

## 🔍 Troubleshooting

### Common Issues
1. **Environment Variables**: Ensure all required variables are set
2. **Dependencies**: Run `pnpm install` if packages are missing
3. **Port Conflicts**: Check if port 3001 is available
4. **API Keys**: Verify Cortensor API access

### Debug Mode
Enable debug logging by setting:
```bash
NODE_ENV=development
DEBUG=*
```

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Cortensor Provider Documentation](../../readmeaboutCortensorOpenaiProvider.md)

## 🤝 Contributing

1. Follow the project's coding standards
2. Test changes across different devices and browsers
3. Ensure responsive design principles are maintained
4. Update documentation for new features

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../../LICENSE) file for details.

---

Built with ❤️ using modern web technologies and the Cortensor AI platform.
