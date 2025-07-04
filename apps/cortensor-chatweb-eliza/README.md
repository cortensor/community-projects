<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

  # **Cortensor ChatWeb ELIZA**

  *Your Conversational Gateway to the Cortensor API*

 <p>
<a href="./LICENSE"\><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"\></a>
<a href="./STATUS.md"\><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"\></a>
<a href="\#"\><img src="https://img.shields.io/badge/Next.js-15.x-blue.svg" alt="Next.js Version"\></a>
<a href="[https://t.me/cortensor](https://t.me/cortensor)"\><img src="https://img.shields.io/badge/Telegram-%232CA5E0.svg?logo=telegram\&logoColor=white" alt="Telegram"\></a>
</p\>

<p align="center">
<a href="\#-features"\>Features</a> •
<a href="\#-prerequisites"\>Prerequisites</a> •
<a href="\#-installation--setup"\>Installation</a> •
<a href="\#-usage"\>Usage</a>
</p>
</div>

**Cortensor ChatWeb ELIZA** is a modern, web-based chat application built with Next.js that connects to the Cortensor AI network. It provides a responsive and seamless interface for real-time conversations with an AI assistant. This project serves as a comprehensive example of how to integrate a frontend application with Cortensor's decentralized AI capabilities, featuring session management, persistent history, and a clean user experience.

## ✨ Features

  * **Real-time Chat Interface**: Engage in fluid conversations with the COR Assistant through a modern web UI.
  * **Session Management**: Create, load, and delete chat sessions directly in the interface.
  * **Persistent Chat History**: Conversations are automatically saved to the browser's local storage for continuity.
  * **Responsive Design**: A clean, modern UI built with Shadcn/UI and Tailwind CSS that works on both desktop and mobile devices.
  * **Easy Configuration**: All API keys and endpoints are managed securely through a `.env.local` file.

## 📋 Prerequisites

Before running this web application, it is crucial to understand that it acts as a client for the Cortensor network. Therefore, you must have access to a fully operational Cortensor backend infrastructure.

The core requirements for the backend are:

  * A configured **Cortensor Node**
  * **cortensord**: The Cortensor daemon service.
  * A running **Router Node** that the web application can connect to.

For complete, step-by-step instructions on setting up this backend infrastructure, please follow the official **[Router Node Setup Guide](https://docs.cortensor.network/getting-started/installation-and-setup/router-node-setup)**.

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
    cd apps/cortensor-chatweb-eliza
    ```

3.  **Install Dependencies**
    From the **root** of the `community-projects` monorepo, run the pnpm install command. This will install dependencies for all projects, including this one.

    ```bash
    # Run this from the root directory: /community-projects
    apt install npm
    npm install -g pnpm
    pnpm install --force
    ```

4.  **Configure Environment Variables**
    Create a file named `.env.local` inside the `apps/cortensor-chatweb-eliza` directory and populate it with your credentials.

    ```ini
    # App Configuration
    NEXT_PUBLIC_APP_NAME="Cortensor AI Chat"
    NEXT_PUBLIC_APP_VERSION="1.0.1"

    # Cortensor API Configuration
    NEXT_PUBLIC_CORTENSOR_CREATE_URL="http://yourip:5010/api/v1/create"
    NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL="https://yourip:5010/api/v1/completions"
    CORTENSOR_API_KEY="your_api_key_here"

    # LLM Parameters
    NEXT_PUBLIC_MAX_INPUT_LENGTH=4000
    LLM_TIMEOUT=180
    LLM_SESSION_ID=6
    ```

## 🚀 Usage

Once the configuration is complete, you can run the application from the **root of the monorepo** using pnpm's `--filter` flag:

```bash
pnpm --filter cortensor-chatweb-eliza dev
```

The application will be available at [http://localhost:3000](https://www.google.com/search?q=http://localhost:3000). Open it in your browser, create a "New Chat," and begin your conversation.

## ⚙️ Configuration

The following variables must be set in your `.env.local` file for the application to function correctly:

  * `NEXT_PUBLIC_CORTENSOR_CREATE_URL`: The full URL to the `/create` endpoint of the Cortensor API.
  * `NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL`: The full URL to the `/completions` endpoint of the Cortensor API.
  * `CORTENSOR_API_KEY`: The authorization key (Bearer Token) to access the Cortensor API.
  * `NEXT_PUBLIC_MAX_INPUT_LENGTH`: The maximum character length for a user's input message.
  * `LLM_TIMEOUT`: The timeout in seconds for the LLM to respond.
  * `LLM_SESSION_ID`: The session ID required by the API payload to maintain conversation context.

## 👤 Maintainer

  * **@beranalpagion** (Discord)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
