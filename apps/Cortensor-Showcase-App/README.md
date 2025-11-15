<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Cortensor Logo" width="150">

# **Cortensor Showcase App**

<p>
<a href="./LICENSE"><img src="https://img.shields.io/badge/license-TBD-lightgrey.svg" alt="License"></a>
<a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
<a href="#"><img src="https://img.shields.io/badge/Stack-HTML%20%7C%20CSS%20%7C%20JS-orange.svg" alt="Tech Stack"></a>
</p>

<p align="center">
<a href="#-overview">Overview</a> •
<a href="#-features">Features</a> •
<a href="#-quick-start">Quick Start</a> •
<a href="#-usage">Usage</a> •
<a href="#-content-management">Content Management</a> •
<a href="#-maintainer">Maintainer</a> •
<a href="#-contributing">Contributing</a> •
<a href="#-license">License</a>
</p>
</div>

## 📚 Overview

Cortensor Showcase App is a polished catalog experience for highlighting Cortensor-powered applications, bots, and demos. It combines a fast static front-end with an Express-powered helper server for uploads, admin publishing, and an integrated AI chatbot backed by the Cortensor Network.

## ✨ Features

- **Curated Gallery**: Present Cortensor apps and bots with hero cards, detail pages, and galleries.
- **Search & Tag Filtering**: Instantly filter by keywords, tags, or type to surface the right project.
- **Leaderboards**: Track click activity to spotlight trending experiences.
- **Admin Workflow**: Publish updates through a protected admin view that writes to `assets/data.json`.
- **AI Chatbot Assistant**: Embedded chat widget that routes through a configurable Cortensor proxy and optional local RAG index.
- **Static Friendly**: Ships as plain HTML/CSS/JS so it can be hosted anywhere, yet supports a Node helper server when needed.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Cortensor API credentials (Bearer token + session id)

### Installation
```bash
git clone https://github.com/cortensor/community-projects.git
cd apps/Cortensor-Showcase-App
npm install
```

### Environment Configuration
Create `env.local.json` (or edit the existing file) with your settings:

```json
{
  "API_BASE_URL": "/proxy",
  "API_BEARER": "your_cortensor_token",
  "API_SESSION_ID": "session_id",
  "CHAT_STREAM": false,
  "CHAT_USE_PROXY": true,
  "CHAT_PERSONA_NAME": "Eureka",
  "ADMIN_ID": "admin",
  "ADMIN_PIN": "xxxx",
  "RAG_ENABLE": true
}
```

If you plan to regenerate the docs RAG index, also configure crawler credentials inside `scripts/crawl_docs.js` as needed.

### Start the development server
```bash
npm run dev
# or
node server.js
```

Visit `http://localhost:3002` to browse the showcase and interact with the chatbot.

## 📝 Usage

1. Browse the grid to discover Cortensor-powered experiences.
2. Click a card to view the detail page with full description and galleries.
3. Use the search bar and tag chips to narrow results.
4. Open the chatbot widget (bottom-right) to ask questions about the showcase.
5. Access `/admin.html` (requires PIN) to publish updated catalog data.

## 👩‍💻 Maintainer

- **@beranalpa** (Discord)

## 📄 License

License information will be published soon. Until then, please contact the maintainer for usage questions.

---

<div align="center">
<strong>Built with ❤️ for the Cortensor Community</strong>
</div>