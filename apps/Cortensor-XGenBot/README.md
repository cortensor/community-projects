<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

# **Cortensor-XGenBot**

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

Cortensor-XGenBot is a powerful Telegram bot designed to generate engaging content for X (formerly Twitter), including tweets, threads, and replies. It offers a suite of inline controls to refine and perfect your social media posts.

## ✨ Features

* **Multiple Modes:** Generate content in Thread, Tweet, or Reply mode.
* **Customizable Tone & Length:** Tailor the output with various tones (e.g., concise, informative, technical) and length presets (short, medium, long, auto).
* **Interactive Controls:** Refine your content with inline buttons to regenerate, adjust tone and length, edit individual lines, and get hashtag suggestions.
* **Reply Context Awareness:** Simply paste a link to an X post, and the bot will fetch the content to generate a relevant reply.
* **User-Specific Defaults:** Configure your preferred tone, length, post count, and default hashtags using the `/settings` command.

## 🚀 Getting Started

### Prerequisites

* Python 3.8+
* pip

### Installation

1.  **Clone the repository:**

    ```bash
    git clone [https://github.com/cortensor/community-projects.git](https://github.com/cortensor/community-projects.git)
    cd community-projects/apps/Cortensor-XGenBot
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
    MODEL_PROVIDER=gpt-oss
    MODEL_NAME=gpt-oss-20b
    DEFAULT_TONE=concise
    DEFAULT_HASHTAGS=#AI #Tech
    ```

## Usage

1.  **Run the bot:**

    ```bash
    python -m src.main
    ```

2.  **Interact with the bot on Telegram:**

    * Send `/start` to begin.
    * Use the interactive keyboard to choose between creating a "New Thread," "New Tweet," or "Reply."
    * Follow the prompts to provide your topic and customize the output.

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
