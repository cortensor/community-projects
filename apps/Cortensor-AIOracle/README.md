<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

# **Cortensor-AIOracle**

<p>
<a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
<a href="./STATUS.md"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
<a href="#"><img src="https://img.shields.io/badge/Next.js-15.2-blue.svg" alt="Next.js Version"></a>
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

Cortensor-AIOracle is an AI-powered oracle that uses a consensus mechanism across multiple large language models to provide accurate and reliable answers to complex questions. By leveraging a variety of AI models, it minimizes the risk of hallucinations and provides a more robust and trustworthy response.

## ✨ Features

* **Multi-Model Consensus:** Enhances accuracy by generating a consensus-based answer from multiple AI models.
* **Real-Time Web Search:** Integrates with web search to provide up-to-date information.
* **Configurable Model Selection:** Allows you to tailor the oracle to your specific needs by selecting from a range of supported models.
* **Data Freshness Alerts:** Ensures that you are aware of the age of the information being used to generate the answer.
* **Consensus Visualization:** Provides a transparent view of the consensus process.

## 🚀 Getting Started

### Prerequisites

* Node.js (v18 or later)
* pnpm

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/cortensor/community-projects.git
    cd community-projects/apps/Cortensor-AIOracle
    ```

2.  **Install dependencies:**

    ```bash
    pnpm install
    ```

3.  **Set up environment variables:**

    Copy the `.env.example` file to a new file named `.env` and fill in the required API keys and configuration values.

    ```bash
    cp .env.example .env
    ```

  ### Oracle Facts Storage

  Oracle facts are stored in a SQLite database (and imported once from `data/oracle-facts.json` if present).

  - `ORACLE_FACTS_DB_PATH` (optional): Path to the SQLite file. Defaults to `data/oracle-facts.sqlite`.

## Usage

Once the configuration is complete, run the development server:

```bash
pnpm dev
```

## 👤 Maintainer

  * **@beranalpagion** (Discord)

## 🤝 Contributing

Contributions are welcome\! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

-----

<div align="center">
<strong>Built with ❤️ for the Cortensor Community</strong>
</div>
