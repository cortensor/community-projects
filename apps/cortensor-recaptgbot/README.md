<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

# **Cortensor-RecapTGBot**

<p>
<a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
<a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
<a href="#"><img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version"></a>
</p>

<p align="center">
<a href="#-features">Features</a> •
<a href="#-getting-started">Getting Started</a> •
<a href="#-usage">Usage</a> •
<a href="#-maintainer">Maintainer</a> •
<a href="#-contributing">Contributing</a> •
<a href="#-license">License</a>
</p>
</div>

Async Telegram bot that fetches **original posts** from an X account (default: `@cortensor`) over a date range, asks a Cortensor router node to format them as a “Dev Update & Recap”, then posts the result into a Telegram chat.

## Features
- Fetches X posts via X API v2 (Bearer Token).
- Includes posts, quote posts, retweets, and self-threads; excludes replies to other accounts.
- Generates a strict “Dev Update & Recap” format via Cortensor router `/api/v1/completions`.
- Posts recap into `TARGET_CHAT_ID`.
- Commands: `/recap`, `/recapdays N`, `/recaprange YYYY-MM-DD YYYY-MM-DD`, `/setinterval N` (admin-only).

## 🚀 Getting Started

### Prerequisites

* Python 3.8+
* pip

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/cortensor/community-projects.git
    cd community-projects/apps/Cortensor-RecapTGBot
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**

    Create a `.env` file in the project's root directory and add the following, filling in your specific details:

    ```
    TELEGRAM_BOT_TOKEN=your_telegram_bot_token
    CORTENSOR_API_URL=your_cortensor_api_url
    CORTENSOR_API_KEY=your_cortensor_api_key
    CORTENSOR_SESSION_ID=your_cortensor_session_id
    ```

## Usage

1.  **Run the bot:**

    ```bash
    python -m src.main
    ```

2.  **Interact with the bot on Telegram:**
- Manual: Trigger `/recap` (last `RECAP_INTERVAL_DAYS`), `/recapdays N`, or `/recaprange YYYY-MM-DD YYYY-MM-DD`.
- Auto: If `AUTO_RECAP_ENABLED=1`, the bot will post every `RECAP_INTERVAL_DAYS` at `RECAP_POST_HOUR_UTC`.

## 👤 Maintainer

* **@beranalpagion** (Discord)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

<div align="center">
<strong>Built with ❤️ for the Cortensor Community</strong>
</div>
