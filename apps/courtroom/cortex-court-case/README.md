# 🎨 Cortensor Judge - Frontend

<div align="center">

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

**Modern React Frontend for Decentralized AI Dispute Resolution**

[Features](#-features) • [Getting Started](#-getting-started) • [Project Structure](#-project-structure) • [Development](#-development)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Development](#-development)
- [Building for Production](#-building-for-production)
- [Configuration](#-configuration)
- [Components](#-components)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Overview

The Cortensor Judge frontend is a modern, responsive web application built with React and TypeScript. It provides an intuitive interface for users to interact with the decentralized dispute resolution system, including:

- **Dashboard** - Overview of active disputes and network statistics
- **Courtroom** - Real-time dispute feed and case management
- **Cases** - Browse and search through dispute cases
- **Validators** - View and monitor validator performance
- **Documentation** - System documentation and guides

---

## ✨ Features

### 🔗 **Wallet Integration**
- Seamless MetaMask wallet connection
- Automatic network switching
- Multi-wallet support (MetaMask, WalletConnect, Rainbow)
- Connection state management

### 📊 **Real-Time Updates**
- Live dispute feed
- Real-time validator statistics
- Dynamic case status updates
- Interactive dashboards

### 🎨 **Modern UI/UX**
- Beautiful, responsive design
- Smooth animations and transitions
- Dark/light theme support
- Mobile-friendly interface

### 🔍 **Advanced Features**
- Case search and filtering
- Detailed case views
- Validator performance metrics
- Evidence visualization

---

## 🛠️ Technology Stack

### Core
- **React 18.3** - UI library
- **TypeScript 5.8** - Type safety
- **Vite 5.4** - Build tool and dev server

### Styling
- **Tailwind CSS 3.4** - Utility-first CSS
- **Framer Motion 12.2** - Animation library
- **shadcn/ui** - Component library
- **Lucide React** - Icon library

### Web3
- **Wagmi 3.1** - React hooks for Ethereum
- **RainbowKit 2.2** - Wallet connection UI
- **Viem 2.4** - Ethereum library

### State Management
- **TanStack Query 5.9** - Server state management
- **React Router 6.3** - Routing

### Utilities
- **Axios 1.13** - HTTP client
- **Zod 3.25** - Schema validation
- **Sonner 1.7** - Toast notifications

---

## 📁 Project Structure

```
cortex-court-case/
├── public/                 # Static assets
│   ├── favicon.ico
│   └── robots.txt
│
├── src/
│   ├── components/         # React components
│   │   ├── ui/            # shadcn/ui components
│   │   ├── layout/         # Layout components (Navbar, Footer)
│   │   ├── sections/      # Page sections
│   │   ├── effects/        # Animation effects
│   │   ├── ConnectionMonitor.tsx
│   │   └── NetworkSwitcher.tsx
│   │
│   ├── pages/             # Page components
│   │   ├── Index.tsx       # Landing page
│   │   ├── Courtroom.tsx   # Main courtroom view
│   │   ├── Cases.tsx       # Cases listing
│   │   ├── CaseDetail.tsx  # Case details
│   │   ├── Validators.tsx  # Validators page
│   │   ├── Docs.tsx        # Documentation
│   │   └── TestConnection.tsx
│   │
│   ├── hooks/             # Custom React hooks
│   │   ├── useWallet.ts    # Wallet connection hook
│   │   ├── use-mobile.tsx  # Mobile detection
│   │   └── use-toast.ts    # Toast notifications
│   │
│   ├── services/          # API services
│   │   └── api.ts         # API client
│   │
│   ├── config/           # Configuration
│   │   ├── wagmi.ts      # Wagmi configuration
│   │   └── api.ts        # API configuration
│   │
│   ├── utils/            # Utility functions
│   │   └── addLocalhostNetwork.ts
│   │
│   ├── data/             # Mock data
│   │   └── mockData.ts
│   │
│   ├── lib/              # Library utilities
│   │   └── utils.ts      # Common utilities
│   │
│   ├── App.tsx           # Main app component
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
│
├── package.json
├── vite.config.ts        # Vite configuration
├── tailwind.config.ts    # Tailwind configuration
├── tsconfig.json         # TypeScript configuration
└── README.md             # This file
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18.0.0 or higher
- **npm** or **yarn**
- **MetaMask** browser extension

### Installation

1. **Navigate to the frontend directory**
   ```bash
   cd cortex-court-case
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Open your browser**
   ```
   http://localhost:8080
   ```

### Environment Setup

The frontend connects to:
- **Backend API**: `http://localhost:3001` (default)
- **Blockchain RPC**: `http://127.0.0.1:8545` (Hardhat)

These can be configured in `src/config/api.ts` and `src/config/wagmi.ts`.

---

## 💻 Development

### Available Scripts

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Build for development
npm run build:dev

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Development Server

The Vite dev server runs on `http://localhost:8080` with:
- Hot Module Replacement (HMR)
- Fast refresh
- TypeScript type checking
- ESLint integration

### Code Structure

#### Components
- **UI Components** (`src/components/ui/`) - Reusable shadcn/ui components
- **Layout Components** (`src/components/layout/`) - Navbar, Footer
- **Section Components** (`src/components/sections/`) - Page sections
- **Custom Components** - ConnectionMonitor, NetworkSwitcher

#### Pages
- **Index** - Landing page with hero and features
- **Courtroom** - Main dispute resolution interface
- **Cases** - Browse and search cases
- **CaseDetail** - Detailed case view
- **Validators** - Validator dashboard
- **Docs** - Documentation and guides

#### Hooks
- **useWallet** - Wallet connection and state management
- **use-mobile** - Responsive design utilities
- **use-toast** - Toast notification management

---

## 🏗️ Building for Production

### Build Command

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

### Build Output

```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── ...
└── ...
```

### Preview Production Build

```bash
npm run preview
```

This serves the production build locally for testing.

---

## ⚙️ Configuration

### API Configuration

Edit `src/config/api.ts`:

```typescript
export const API_BASE_URL = 'http://localhost:3001';
```

### Wagmi Configuration

Edit `src/config/wagmi.ts` to configure:
- Supported chains
- RPC endpoints
- Wallet connectors

### Tailwind Configuration

Edit `tailwind.config.ts` to customize:
- Theme colors
- Fonts
- Spacing
- Breakpoints

---

## 🧩 Components

### Key Components

#### ConnectionMonitor
Monitors MetaMask connection state and syncs with wagmi.

#### NetworkSwitcher
Automatically switches to the correct blockchain network.

#### useWallet Hook
Provides wallet connection functionality:
```typescript
const { 
  address, 
  isConnected, 
  connect, 
  disconnect 
} = useWallet();
```

### UI Components

Built with shadcn/ui, including:
- Buttons, Cards, Badges
- Dialogs, Dropdowns, Menus
- Forms, Inputs, Selects
- Tables, Charts, Progress bars

---

## 🔧 Troubleshooting

### Wallet Connection Issues

**Problem**: MetaMask not connecting

**Solutions**:
1. Ensure MetaMask is installed and unlocked
2. Add Localhost 8545 network to MetaMask
3. Check browser console for errors
4. Try refreshing the page

### Network Issues

**Problem**: Cannot connect to backend

**Solutions**:
1. Verify backend is running on port 3001
2. Check CORS configuration
3. Verify API URL in `src/config/api.ts`

### Build Issues

**Problem**: Build fails

**Solutions**:
1. Clear `node_modules` and reinstall
2. Check Node.js version (>= 18.0.0)
3. Clear Vite cache: `rm -rf node_modules/.vite`

### TypeScript Errors

**Problem**: Type errors

**Solutions**:
1. Run `npm run typecheck`
2. Ensure all dependencies are installed
3. Check `tsconfig.json` configuration

---

## 📚 Additional Resources

- [React Documentation](https://react.dev)
- [Vite Documentation](https://vitejs.dev)
- [Wagmi Documentation](https://wagmi.sh)
- [Tailwind CSS Documentation](https://tailwindcss.com)
- [shadcn/ui Documentation](https://ui.shadcn.com)

---

## 🤝 Contributing

When contributing to the frontend:

1. Follow the existing code style
2. Use TypeScript for all new code
3. Add proper type definitions
4. Write descriptive commit messages
5. Test your changes thoroughly

---

## 📝 License

This project is licensed under the MIT License.

---

<div align="center">

**Built with ❤️ using React, TypeScript, and modern web technologies**

[Back to Main README](../README.md)

</div>

