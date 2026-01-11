<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

# **Analyst Bot**

*A comprehensive Telegram bot that provides AI-powered cryptocurrency analysis, portfolio management, and automated Dollar Cost Averaging (DCA) features using Cortensor's decentralized AI network*

<p>
<a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
<a href="./STATUS.md"><img src="https://img.shields.io/badge/status-production--ready-success.svg" alt="Status"></a>
<a href="#"><img src="https://img.shields.io/badge/Next.js-15.2-blue.svg" alt="Next.js Version"></a>
<a href="https://t.me/cortensor"><img src="https://img.shields.io/badge/Telegram-%232CA5E0.svg?logo=telegram&logoColor=white" alt="Telegram"></a>
</p>

<p align="center">
<a href="#-features">Features</a> •
<a href="#-architecture-overview">Architecture</a> •
<a href="#-installation--setup">Installation</a> •
<a href="#-mobile-optimization">Mobile</a> •
<a href="#-usage">Usage</a>
</p>
</div>

## 🚀 Features

### 📊 AI-Powered Analysis
- Real-time cryptocurrency market analysis
- AI-generated insights and recommendations
- Scheduled analysis with customizable intervals
- Multiple data sources integration (Alpha Vantage, CoinGecko)

### 💼 Portfolio Management
- Track multiple cryptocurrency holdings
- Multi-currency support (USD, IDR, EUR, JPY)
- Real-time portfolio valuation
- Currency conversion with user preferences

### 🔄 Dollar Cost Averaging (DCA)
- Automated DCA scheduling (daily, weekly, monthly)
- Multi-timezone support for proper execution timing
- Real-time notifications with execution details
- Portfolio integration with automatic updates
- Main currency system (USD base with automatic conversion)

### ⚙️ User Settings & Customization
- Timezone configuration per user
- Currency preference settings
- Notification controls
- Alert thresholds customization

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Telegram Bot Token
- Alpha Vantage API Key
- Virtual environment (recommended)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/beranalpa/analyst-bot.git
   cd analyst-bot
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   # Create .env file or export variables
   export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
   export ALPHA_VANTAGE_API_KEY="your_alpha_vantage_key"
   ```

5. **Run the bot:**
   ```bash
   python -m src.main
   ```

## 📱 Usage

### Basic Commands

- `/start` - Initialize bot and show welcome message
- `/help` - Display all available commands
- `/analyze <symbol>` - Get AI analysis for a cryptocurrency
- `/settings` - Configure bot preferences

### Portfolio Commands

- `/add_asset <symbol> <quantity>` - Add asset to portfolio
- `/remove_asset <symbol>` - Remove asset from portfolio
- `/view_portfolio` - View current portfolio with valuations
- `/clear_portfolio` - Clear all portfolio assets

### DCA Commands

- `/dca add <symbol> <amount> <currency> <frequency> <time>` - Create DCA schedule
- `/dca list` - View all DCA schedules
- `/dca stats <dca_id>` - View DCA performance statistics
- `/dca pause <dca_id>` - Pause DCA schedule
- `/dca resume <dca_id>` - Resume DCA schedule
- `/dca delete <dca_id>` - Delete DCA schedule

### Settings Commands

- `/settings currency <currency>` - Set preferred currency (USD, IDR, EUR, JPY)
- `/settings timezone <timezone>` - Set timezone (e.g., Asia/Jakarta)
- `/settings notifications <on|off>` - Toggle notifications

### Examples

```bash
# Add Bitcoin to portfolio
/add_asset bitcoin 0.5

# Create daily DCA for Ethereum
/dca add ethereum 50000 idr daily 15:00

# Set currency to Indonesian Rupiah
/settings currency IDR

# Set timezone to Jakarta
/settings timezone Asia/Jakarta
```

## 🏗️ Architecture

### Core Components

- **`src/main.py`** - Application entry point and bot initialization
- **`src/bot/handlers.py`** - Telegram command handlers and user interactions
- **`src/core/dca_worker.py`** - Background DCA execution engine
- **`src/utils/database.py`** - Data persistence layer using TinyDB
- **`src/services/market_data_api.py`** - Market data integration

### Key Features

- **Timezone-Aware Scheduling:** Each user's DCA executes in their configured timezone
- **Main Currency System:** USD as base currency with automatic conversion
- **Async Notification System:** Non-blocking notifications with proper event loop handling
- **Multi-Currency Support:** Seamless conversion between USD, IDR, EUR, JPY

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token | Yes |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key for market data | Yes |

### Database Structure

The bot uses TinyDB with the following databases:
- `data/dca.db` - DCA schedules and execution history
- `data/portfolio.db` - User portfolio holdings
- `data/user_settings.db` - User preferences and settings
- `data/tasks.db` - Analysis task queue
- `data/schedules.db` - Scheduled analysis jobs

## 🚦 Project Status

- ✅ **Active Development** - Actively maintained and updated
- ✅ **Production Ready** - Stable for production use
- ✅ **Full Feature Set** - Complete DCA and portfolio management
- ✅ **Multi-Currency Support** - USD, IDR, EUR, JPY
- ✅ **Timezone Support** - Per-user timezone configuration

## 🤝 Contributing

We welcome contributions! Please see our [development workflow](https://github.com/cortensor/cortensor-community-projects#-development-workflow) for guidelines.

## 👤 Maintainer

- **@beranalpa** (Discord: @beranalpagion)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
