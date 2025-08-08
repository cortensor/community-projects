<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

# **Eureka AI**

*Professional Dark-Mode AI Chat Interface for Cortensor Network*

<p>
<a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
<a href="./STATUS.md"\><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
<a href="#"><img src="https://img.shields.io/badge/Next.js-15.2-blue.svg" alt="Next.js Version"></a>
</p>

<p align="center">
<a href="#-features">Features</a> •
<a href="#-architecture-overview">Architecture</a> •
<a href="#-installation--setup">Installation</a> •
<a href="#-mobile-optimization">Mobile</a> •
<a href="#-usage">Usage</a>
</p>
</div>

**Eureka AI** is a professional, production-ready AI chat interface built with Next.js 15 and TypeScript. Featuring a sleek dark-only theme, mobile-first responsive design, and advanced AI interaction capabilities including DeepSeek R1 reasoning mode support.

This application serves as the definitive frontend for Cortensor Network, providing seamless integration with multiple AI models, real-time streaming responses, and sophisticated mobile keyboard handling.

## ✨ Features

### 🎨 **User Interface**
  * **Dark Mode Only**: Professional dark theme optimized for extended usage
  * **Mobile-First Design**: Optimized keyboard handling and touch interactions
  * **Responsive Layout**: Adaptive sidebar and chat interface for all screen sizes
  * **Glass Morphism**: Modern backdrop blur effects and translucent components

### 🤖 **AI Capabilities**  
  * **Multi-Model Support**: DeepSeek R1, Llama 3.1 (soon), and Llava 1.5 integration
  * **Deep Thinking Mode**: Advanced reasoning display for DeepSeek R1 models
  * **Memory Mode Toggle**: Control conversation context and AI memory
  * **Real-Time Streaming**: Live response streaming with thinking process visualization

### 📱 **Mobile Optimization**
  * **Stable Keyboard Handling**: Fixed positioning without layout jumps
  * **Touch-Friendly Controls**: Optimized button sizes and interactions
  * **iOS Safari Compatible**: Proper viewport handling and scroll behavior
  * **Mobile Controls**: Dedicated mobile interface with simplified controls

### 💾 **Data Management**
  * **Local Storage**: Browser-based chat history with privacy protection
  * **Session Management**: Multiple concurrent chat sessions

## 🏛️ Architecture Overview

### **Frontend Architecture**
- **Next.js 15**: App Router with TypeScript and Tailwind CSS
- **State Management**: React hooks with localStorage persistence  
- **Component System**: Shadcn/UI with custom mobile-optimized components
- **Responsive Design**: CSS Grid and Flexbox with mobile-first approach

### **Backend Integration**
- **Cortensor API**: Direct integration with decentralized AI network
- **Response Aggregation**: Intelligent filtering and selection of best responses
- **Error Handling**: Comprehensive error management and fallback systems
- **Rate Limiting**: Built-in request throttling and queue management

### **Mobile Features**
- **Keyboard Detection**: Advanced mobile keyboard state management
- **Fixed Positioning**: Stable chat input without transform-based positioning
- **Touch Optimization**: Enhanced touch targets and gesture handling

## 📋 Prerequisites
Before running this application, ensure you have:

### **System Requirements**
  * **Node.js 18+**: Latest LTS version recommended
  * **pnpm**: Package manager (faster than npm/yarn)
  * **Git**: For version control and repository management

### **Cortensor Network Access**
  * **Cortensor API Endpoint**: Access to Testnet or Devnet6
  * **Session ID**: Valid session identifier for API calls
  * **Network Configuration**: Proper environment variables setup

For Cortensor Network setup, follow the **[Official Documentation](https://docs.cortensor.network/)**.

## 🔧 Installation & Setup

### **Quick Start**

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/cortensor/community-projects.git
    cd community-projects/apps/eurekaai
    ```

2.  **Install Dependencies**
    ```bash
    pnpm install
    # or
    npm install
    ```

3.  **Environment Configuration**
    Create `.env.local` file in the root directory:
    ```env
    # App Configuration
    NEXT_PUBLIC_APP_NAME="Eureka AI"
    NEXT_PUBLIC_APP_VERSION="1.0.0"

    # Cortensor API Configuration (Replace with your actual server)
    CORTENSOR_ROUTER_URL="http://your_cortensor_router_ip:5010"
    NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL="http://your_cortensor_router_ip:5010/api/v1/completions"

    # Session IDs (Configure based on your Cortensor setup)
    NEXT_PUBLIC_LLM_SESSION_ID=1
    NEXT_PUBLIC_DEEPSEEK_SESSION_ID=2

    ```

## 🚀 Usage

Once the configuration is complete, run the development server:

```bash
pnpm dev
```

## 👤 Maintainer

  * **@beranalpagion** (Discord)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

<div align="center">
<strong>Built with ❤️ for the Cortensor Community</strong>
</div>
