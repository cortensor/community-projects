<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

# **Cortensor ChatWeb EUREKA**

*An Advanced, Context-Aware Web Interface for the Cortensor Network*

<p>
<a href="./LICENSE"\><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
<a href="./STATUS.md"\><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
<a href="\#"\><img src="https://img.shields.io/badge/Next.js-15.x-blue.svg" alt="Next.js Version"\></a>
<a href="[https://t.me/cortensor](https://t.me/cortensor)"\><img src="https://img.shields.io/badge/Telegram-%232CA5E0.svg?logo=telegram\&logoColor=white" alt="Telegram"\></a>
</p>

<p align="center">
<a href="#-features"\>Features</a> •
<a href="#-architecture-overview"\>Architecture</a> •
<a href="#-prerequisites"\>Prerequisites</a> •
<a href="#-installation--setup"\>Installation</a> •
<a href="#-usage"\>Usage</a>
</p>
</div>

**Cortensor ChatWeb EUREKA** is a modern, web-based chat application built with Next.js that demonstrates a robust and efficient way to interact with the Cortensor AI network. It provides a seamless, real-time conversational experience with the "Eureka" AI persona, featuring advanced state management and user-centric controls.

This project has evolved to serve as a comprehensive example of a production-ready frontend application that handles the nuances of a decentralized AI network, including response aggregation and client-side context isolation.

## ✨ Features

  * **Advanced AI Persona**: Interact with "Eureka," an AI configured with a detailed system prompt for professional, accurate, and context-aware responses.
  * **Local-First Chat History**: Create, load, and delete multiple chat histories that are stored exclusively in the user's browser, ensuring privacy and fast access.
  * **Frontend-Managed Context Isolation**: Guarantees that conversations remain separate and coherent by only sending the active chat's history to the AI, even while using a single static server session.
  * **Toggleable Memory Mode**: A UI switch gives users direct control over the AI's conversational memory, allowing them to choose between deep, context-aware dialogue or quick, single-turn queries.
  * **Response Aggregation & Selection**: The backend intelligently processes responses from multiple decentralized AI miners, filters out invalid data, and selects the most complete answer to present to the user.
  * **Modern & Responsive UI**: Built with Shadcn/UI and Tailwind CSS, featuring a multi-line input, clear loading states, and a clean, responsive design.

## 🏛️ Architecture Overview

This application uses a unique and efficient architecture to solve common challenges in decentralized networks:

1.  **Static Server Session**: The application utilizes a single, static `session_id` (defined in `.env.local`) for all communications with the Cortensor network. This eliminates the need for complex on-chain session creation for each user, making the app instantly available.
2.  **Client-Side History Management**: All chat histories ("New Chat" instances) are managed as separate entries in the browser's `localStorage`. The "New Chat" button is a client-side only operation.
3.  **Context Isolation at the Source**: To prevent context mixing, the frontend is responsible for sending **only the relevant message history** of the currently active chat to the backend. This ensures the AI's context is always clean and specific to the ongoing conversation.

## 📋 Prerequisites

Before running this application, you must have access to a fully operational Cortensor backend infrastructure. The core requirements are:

  * A configured **Cortensor Node**
  * **cortensord**: The Cortensor daemon service.
  * A running **Router Node** that the web application can connect to.

For complete, step-by-step instructions on setting up this backend, please follow the official **[Router Node Setup Guide](https://docs.cortensor.network/getting-started/installation-and-setup/router-node-setup)**.

## 🔧 Installation & Setup

This project is located within the `Cortensor Community Projects` monorepo. Follow these steps to set it up.

1.  **Clone the Main Repository**
    Clone the central hub where all community projects reside.

    ```bash
    git clone https://github.com/cortensor/community-projects.git
    cd community-projects
    ```

2.  **Navigate to the Project Directory**
    This web app is located in the `apps/` directory.

    ```bash
    cd apps/cortensor-chatweb-eureka
    ```

3.  **Install Dependencies**
    From the **root** of the `community-projects` monorepo, run the pnpm install command. This will install dependencies for all projects, including this one.

    ```bash
    # Run this from the root directory: /community-projects/apps/cortensor-chatweb-eureka
    apt install npm
    npm install -g pnpm
    pnpm install --force
    ```
    
4.  **Configure Environment Variables**
    Create a file named `.env.local` in the root directory and populate it with your credentials.

    ```ini
    # App Configuration
    NEXT_PUBLIC_APP_NAME="Cortensor AI Chat"
    NEXT_PUBLIC_APP_VERSION="1.1.0"

    # Cortensor API Configuration (ensure your router URL is correct)
    CORTENSOR_ROUTER_URL="http://your_router_ip:5010"
    CORTENSOR_API_KEY="your_api_key_here"
    NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL="http://your_router_ip:5010/api/v1/completions"

    # Static Session ID
    # This ID will be used for all conversations from this application instance.
    NEXT_PUBLIC_LLM_SESSION_ID=

    # LLM Parameters
    NEXT_PUBLIC_MAX_INPUT_LENGTH=
    LLM_TIMEOUT=
    LLM_MAX_TOKENS=
    ```

## 🚀 Usage

Once the configuration is complete, run the development server:

```bash
pnpm dev
```

The application will be available at [http://localhost:3000](https://www.google.com/search?q=http://localhost:3000). Open it in your browser; a "New Chat" will be created automatically, and you can begin your conversation.

## 👤 Maintainer

  * **@beranalpagion** (Discord)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
