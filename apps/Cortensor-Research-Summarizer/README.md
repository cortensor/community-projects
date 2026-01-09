<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

# **Cortensor Research Summarizer**

<p>
<a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
<a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
<a href="#"><img src="https://img.shields.io/badge/Next.js-15.2-blue.svg" alt="Next.js Version"></a>
</p>

<p align="center">
<a href="#-overview">Overview</a> •
<a href="#-features">Features</a> •
<a href="#-getting-started">Getting Started</a> •
<a href="#-usage">Usage</a> •
<a href="#-maintainer">Maintainer</a> •
<a href="#-contributing">Contributing</a> •
<a href="#-license">License</a>
</p>
</div>

## 📚 Overview

A modern web application that intelligently summarizes articles from URLs using AI. Built with Next.js and integrated with the Cortensor Network for powerful content analysis.

## ✨ Features

- **Smart URL Processing**: Automatically extracts and analyzes content from any article URL
- **AI-Powered Summarization**: Uses Cortensor Network for intelligent content analysis
- **Key Insights Extraction**: Automatically identifies and highlights the most important points
- **Search Enhancement**: Finds additional relevant sources when needed for comprehensive analysis
- **Modern Interface**: Clean, responsive design with real-time processing indicators
- **Export Options**: Download summaries in multiple formats (JSON, Markdown)

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- Cortensor API key (get from [Cortensor Network](https://docs.cortensor.network/))

### Installation
```bash
npm install
# Create .env.local and add your required env vars
npm run dev
```

Note: after changing `.env.local`, restart the dev server so changes take effect.

Visit `http://localhost:3000` and start summarizing articles!

2. **Environment Configuration**:
Create a `.env.local` file:
```env
# Required: Cortensor Router Configuration
CORTENSOR_API_KEY=your_cortensor_api_key_here
# Base URL only (the app will call: $CORTENSOR_BASE_URL/api/v1/completions)
CORTENSOR_BASE_URL=https://<routerip>:5010

# Optional: Google Search API (for additional source search)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here

# Optional: Tavily API (alternative search provider)
TAVILY_API_KEY=your_tavily_api_key_here

# Application Configuration
MAX_SUMMARY_LENGTH=500
MIN_SUMMARY_PARAGRAPHS=3
```

3. **Start the development server**:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📝 Usage

1. Enter any article URL in the input field
2. Click "Summarize Article"
3. Watch the AI analyze the content
4. Get a professional summary with key insights
5. Export results in your preferred format

## 📄 License

This project is licensed under the MIT License

---

<div align="center">
<strong>Built with ❤️ for the Cortensor Community<
