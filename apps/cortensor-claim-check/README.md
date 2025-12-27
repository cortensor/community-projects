<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Logo" width="150">

# **Cortensor-Claim-Check**

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

Minimal fact-checking playground that streams claims through a Cortensor router and surfaces aggregate verdicts, confidence, dispersion, reasoning, and miner votes through a Next.js UI + API.

## Suggested Free Context APIs

When you need supplementary evidence, the following free (or free-tier) APIs are handy starting points:

- **GDELT 2.0 Events API** – machine-coded global news events with location, tone, and actor metadata for rapid corroboration.
- **The Guardian Open Platform** – historic and real-time news search with article metadata and section filters (requires free key).
- **NewsData.io / GNews** – aggregated headlines across mainstream outlets with generous daily quotas for prototyping.
- **MediaStack (free tier)** – JSON feed spanning 7,500+ sources; useful for tracing narrative drift over time.
- **Wikipedia REST / MediaWiki Action API** – structured encyclopedic summaries plus citation chains for baseline fact checks.
- **Internet Archive CDX API** – fetch archived snapshots to verify whether a quoted source actually existed at a specific time.

## 🚀 Getting Started

### Prerequisites

* Node.js (v18 or later)
* pnpm

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/cortensor/community-projects.git
    cd community-projects/apps/Cortensor-Claim-Check
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

## Usage

Once the configuration is complete, run the development server:

```bash
pnpm dev
```

## 👤 Maintainer

  * **@beranalpagion** (Discord)


## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

-----

<div align="center">
<strong>Built with ❤️ for the Cortensor Community</strong>
</div>
